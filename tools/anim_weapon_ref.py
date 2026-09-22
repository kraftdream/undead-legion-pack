"""Attach weapons to the hand sockets in the anim file exactly as Unity attaches them.

    blender -b Animations/skeleton_anim.blend -P tools/anim_weapon_ref.py -- --attach H2Recurvebow:L,Arrow:R [--check ACTION:frame] [--save]
    blender -b Animations/skeleton_anim.blend -P tools/anim_weapon_ref.py -- --remove --save

For each NAME:SIDE the mesh is appended fresh from Weapons/prod.blend, put into the export-local
frame (grip at the origin, length +Z, roll: `export_weapons.export_local_mesh`, no 1.8x) and
parented to DEF-weapon.<SIDE> with a Child Of constraint whose local matrix reproduces Unity's
`SkeletonWeapon.AlignGrip(weapon, slot)`: weapon = Slot x Grip^-1 in the socket frame, with the
hand slot and the W_<NAME> prefab's Grip read from Animations/unity_grips.json (written by
tools/unity/dump_grips.py: edit the slot or the Grip in Unity, dump again, re-attach).

Frames: Unity's slot frame is the Blender socket bone frame mirrored in X (the FBX import flips
that axis; +Y hilt and +Z back-of-hand match); Unity's mesh-local axes are the Blender
export-local axes through (x, y, z) -> (-x, z, -y) (Z-up to Y-up plus the same flip). Hence
    local = M . Slot_u . Grip_u^-1 . C,   M = diag(-1, 1, 1),  C = [[-1,0,0],[0,0,1],[0,-1,0]]
(a proper rotation: both mirrors cancel), Unity metres / 1.8 on the translations.

The objects live in the collection Ref_Weapons, named Ref_<NAME>; they are reference only
(never exported: export_fbx.py exports the rig alone for clips) and `--remove` deletes them.
`--check ACTION:frame` prints, on that frame, the arrow's length axis against the draw-hand ->
bow-hand line and the bow's limb axis against the arrow, the same numbers the Unity checks
report, so the placement can be trusted before a pose is authored on it.
"""
import bpy, os, sys, json, math
from mathutils import Vector, Matrix, Quaternion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import export_weapons                                   # tables + export_local_mesh (its export loop only runs as __main__)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(k, d=None):
    return argv[argv.index(k) + 1] if k in argv else d
ATTACH = [a.split(":") for a in arg("--attach", "").split(",") if a]
REMOVE = "--remove" in argv
SAVE = "--save" in argv
CHECK = arg("--check", "")
GRIPS = arg("--grips", os.path.join(ROOT, "Animations", "unity_grips.json"))
PROD = os.path.join(ROOT, "Weapons", "prod.blend")
COLL = "Ref_Weapons"
SCALE = export_weapons.SCALE

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
scene = bpy.context.scene

# ------------------------------------------------------------------ remove
coll = bpy.data.collections.get(COLL)
if coll is None:
    coll = bpy.data.collections.new(COLL); scene.collection.children.link(coll)
names_attached = {n for n, _ in ATTACH}
for ob in list(coll.objects):
    if REMOVE or ob.name[4:] in names_attached:
        print("[weapon-ref] removed", ob.name)
        me = ob.data; bpy.data.objects.remove(ob, do_unlink=True)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)

# ------------------------------------------------------------------ frames
M_ = Matrix(((-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))          # Unity slot -> Blender socket
C_ = Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))         # Blender export-local -> Unity mesh-local


def unity_local(entry):
    """A Unity local transform (pos metres, rot x,y,z,w) as a 4x4 in Blender units."""
    x, y, z, w = entry["rot"]
    m = Quaternion((w, x, y, z)).to_matrix().to_4x4()
    m.translation = Vector(entry["pos"]) / SCALE
    return m


if ATTACH:
    grips = json.load(open(GRIPS, encoding="utf-8"))
    with bpy.data.libraries.load(PROD, link=False) as (src, dst):
        want = [n for n, _ in ATTACH if n in src.objects]
        missing = [n for n, _ in ATTACH if n not in src.objects]
        assert not missing, "not in Weapons/prod.blend: %s" % missing
        dst.objects = want
    appended = {}                                          # a same-named object already in the file renames the appended one to NAME.001
    for o in dst.objects:
        base = o.name[:-4] if len(o.name) > 4 and o.name[-4] == "." and o.name[-3:].isdigit() else o.name
        appended[base] = o
    for name, side in ATTACH:
        src_ob = appended[name]
        me = export_weapons.export_local_mesh(src_ob, name, log=lambda s: print("[weapon-ref]", s))
        me.name = "Ref_" + name
        ob = bpy.data.objects.new("Ref_" + name, me)
        coll.objects.link(ob)
        bone = "DEF-weapon." + side
        assert bone in rig.pose.bones, bone
        assert name in grips["grips"], "no W_%s Grip in %s (run tools/unity/dump_grips.py)" % (name, GRIPS)
        local = M_ @ unity_local(grips["slots"][side]) @ unity_local(grips["grips"][name]).inverted() @ C_
        assert abs(local.to_3x3().determinant() - 1.0) < 1e-6
        con = ob.constraints.new('CHILD_OF')
        con.target = rig; con.subtarget = bone
        con.inverse_matrix = Matrix.Identity(4)
        ob.matrix_basis = local
        print("[weapon-ref] Ref_%s on %s: local offset (%.4f, %.4f, %.4f) rig m, rotation %.0f deg" % (
            name, bone, *local.translation, math.degrees(local.to_quaternion().angle)))
    # the appended source objects (and their materials' textures) are not needed: the meshes were copied
    for o in appended.values():
        me = o.data; bpy.data.objects.remove(o, do_unlink=True)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)

# ------------------------------------------------------------------ check
if CHECK:
    act, fr = CHECK.split(":"); fr = int(fr)
    rig.animation_data.action = bpy.data.actions[act]
    scene.frame_set(fr)
    bpy.context.view_layer.update()
    pbs = rig.pose.bones
    def sockm(side): return rig.matrix_world @ pbs["DEF-weapon." + side].matrix
    for ob in coll.objects:
        name = ob.name[4:]
        side = ob.constraints[0].subtarget[-1]
        expect = sockm(side) @ ob.matrix_basis
        err = (ob.matrix_world.translation - expect.translation).length
        length = (ob.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()   # export-local +Z = the length / hilt axis
        print("[weapon-ref] %s on %s: constraint vs bone-frame placement %.5f m; length axis world (%.2f, %.2f, %.2f), socket +Y (hilt) dot %.3f, socket +X (fingers) dot %.3f" % (
            ob.name, side, err, *length, length.dot((sockm(side).to_3x3() @ Vector((0, 1, 0))).normalized()), length.dot((sockm(side).to_3x3() @ Vector((1, 0, 0))).normalized())))
    if "Ref_Arrow" in coll.objects and any(o.name != "Ref_Arrow" for o in coll.objects):
        arrow = coll.objects["Ref_Arrow"]; bow = next(o for o in coll.objects if o.name != "Ref_Arrow")
        a_side = arrow.constraints[0].subtarget[-1]; b_side = bow.constraints[0].subtarget[-1]
        shaft = (arrow.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
        limbs = (bow.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
        line = (sockm(b_side).translation - sockm(a_side).translation).normalized()
        print("[weapon-ref] %s:%d  arrow shaft . (draw hand -> bow hand) = %.3f (%.0f deg);  bow limbs vs arrow %.0f deg" % (
            act, fr, shaft.dot(line), math.degrees(math.acos(max(-1, min(1, shaft.dot(line))))), math.degrees(math.acos(max(-1, min(1, abs(limbs.dot(shaft))))))))

if SAVE:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
    print("[weapon-ref] saved")
