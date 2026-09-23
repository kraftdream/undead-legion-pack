"""Turn a skinless node-hierarchy GLB (an Unreal-mannequin capture: 162 nodes, no skin, no mesh)
into the armature GLB the retarget reads.

    blender -b -P tools/glb_nodes_to_armature.py -- SRC.glb DST.glb [--only pelvis,spine_01,...]

Blender imports a GLB without a skin as animated EMPTIES, and glb_retarget.py needs an
armature. Every node becomes a bone whose REST frame is the node's rest world matrix (head at
the node, Y along the node's Y, 5 cm long) - so a bone's rest rotation equals the node's and
the retarget's bind-relative deltas hold - and the empties' animation is baked onto the bones
with visual keying. The file's default node transforms are the bind (the mannequin's A-pose,
metres, pelvis 0.96 m), so the retarget takes it with its default `--bind tpose`.
"""
import bpy, sys, math
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]
only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene; scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=src)
empties = [o for o in bpy.data.objects if o.type == 'EMPTY']
assert empties, "no empties: does the GLB have a skin already?"
# animation range from the imported actions
f0, f1 = 1, 1
for o in empties:
    if o.animation_data and o.animation_data.action:
        r = o.animation_data.action.frame_range; f0 = min(f0, int(r[0])); f1 = max(f1, int(round(r[1])))
scene.frame_start, scene.frame_end = f0, f1
# rest = the file's default node TRS from the JSON, converted the way the importer converts (verified against
# the importer's own frame-0 empties: empty = CONV . W . CONV^-1, CONV = the Y-up -> Z-up axis change).
# (Unlinking the empties' actions and reading their transforms gives frame 0, not the rest: animated
# properties keep their last evaluated values.)
import struct, json
from mathutils import Quaternion
raw = open(src, "rb").read(); jlen = struct.unpack_from("<I", raw, 12)[0]; gl = json.loads(raw[20:20 + jlen])
gnodes = gl["nodes"]; gparent = {}
for i, n in enumerate(gnodes):
    for c in n.get("children", []): gparent[c] = i
def glocal(n):
    if "matrix" in n: return Matrix([n["matrix"][k::4] for k in range(4)])
    x, y, z, w = n.get("rotation", [0, 0, 0, 1]); m = Quaternion((w, x, y, z)).to_matrix().to_4x4()
    sc = n.get("scale", [1, 1, 1]); m = m @ Matrix.Diagonal((sc[0], sc[1], sc[2], 1.0))
    m.translation = Vector(n.get("translation", [0, 0, 0])); return m
def gworld(i):
    m = glocal(gnodes[i]); p = gparent.get(i); return (gworld(p) @ m) if p is not None else m
CONV = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
rest = {}
names_ = {o.name for o in empties}
for i, n in enumerate(gnodes):
    if n.get("name") in names_:
        wm = CONV @ gworld(i) @ CONV.inverted()
        t_ = wm.translation.copy(); wm = wm.to_3x3().normalized().to_4x4(); wm.translation = t_
        rest[n["name"]] = wm
for nm in ("pelvis", "hand_l", "hand_r", "head"):
    if nm in rest: print("[nodes->armature] rest %-8s (%.3f, %.3f, %.3f)" % (nm, *rest[nm].translation))
arm_data = bpy.data.armatures.new("Src"); arm = bpy.data.objects.new("SrcArmature", arm_data)
scene.collection.objects.link(arm); bpy.context.view_layer.objects.active = arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
order = [o for o in empties if only is None or o.name in only]
ebs = {}
for o in order:
    eb = arm_data.edit_bones.new(o.name)
    m = rest[o.name].copy(); m.normalize()
    eb.head = m.translation; eb.tail = m.translation + Vector((0, 0, 0.05))   # a zero-length bone ignores .matrix (every bone came out pointing +Z)
    eb.matrix = m; eb.length = 0.05
    ebs[o.name] = eb
for o in order:
    p = o.parent
    while p is not None and p.name not in ebs: p = p.parent
    if p is not None: ebs[o.name].parent = ebs[p.name]
bpy.ops.object.mode_set(mode='POSE')
for o in order:
    pb = arm.pose.bones[o.name]; pb.rotation_mode = 'QUATERNION'
    c = pb.constraints.new('COPY_LOCATION'); c.target = o                       # location + rotation, NOT transforms: the empties carry the root's 0.01 scale
    c = pb.constraints.new('COPY_ROTATION'); c.target = o
with bpy.context.temp_override(object=arm, active_object=arm, selected_objects=[arm], selected_pose_bones=list(arm.pose.bones), selected_editable_objects=[arm]):
    bpy.ops.nla.bake(frame_start=f0, frame_end=f1, only_selected=False, visual_keying=True, clear_constraints=True, use_current_action=False, bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
for o in empties: bpy.data.objects.remove(o, do_unlink=True)
print("[nodes->armature] %d bones, frames %d..%d @ %d fps, pelvis rest %s" % (len(order), f0, f1, scene.render.fps, tuple(round(v, 3) for v in rest["pelvis"].translation) if "pelvis" in rest else "-"))
# the retarget reads this armature from a .blend (appended: exact bones, exact rest, exact keys). The GLB
# round trip was tried first: the exporter writes an armature as a skin only with a skinned mesh, and the
# importer then re-orients every bone to +Z while keeping the pose - rest and pose no longer paired, the
# retarget's bind-relative deltas came out 124-152 deg on an upright source and the rig folded flat
blend_path = dst[:-4] + ".blend" if dst.lower().endswith(".glb") else dst + ".blend"
for o in list(bpy.data.objects):
    if o.type not in ('ARMATURE',): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("[nodes->armature] wrote", blend_path, "(the retarget source: manifest src_ext blend)")
# and a GLB for viewers (NOT for the retarget): a one-triangle mesh weighted to the pelvis makes the exporter write the skin
me = bpy.data.meshes.new("SkinStub"); me.from_pydata([(0, 0, 0), (0.01, 0, 0), (0, 0.01, 0)], [], [(0, 1, 2)])
stub = bpy.data.objects.new("SkinStub", me); scene.collection.objects.link(stub)
vg = stub.vertex_groups.new(name="pelvis" if "pelvis" in arm.pose.bones else order[0].name); vg.add([0, 1, 2], 1.0, 'REPLACE')
mod = stub.modifiers.new("Armature", 'ARMATURE'); mod.object = arm; stub.parent = arm
arm.select_set(True); stub.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', use_selection=True, export_animations=True, export_skins=True, export_apply=False, export_yup=True, export_force_sampling=True, export_frame_range=False, export_anim_single_armature=True)
print("[nodes->armature] wrote", dst)
