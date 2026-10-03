"""SMPL motion (.npz from tools/gvhmr_export.py) -> the armature .blend the retarget reads.

    blender -b -P tools/smpl_to_armature.py -- IN.npz "External Anims/Video/<name>_arm.blend"

One bone per SMPL-X body joint (+ the two static knuckles), named as SMPL names them, head at the
performer's rest joint, REST ORIENTATION = IDENTITY (every bone points +Y, 5 cm long, like
glb_nodes_to_armature's bones). With identity rest frames a pose bone's quaternion IS the SMPL
local rotation and the pelvis' location is its world offset from the rest, so the armature
reproduces the SMPL forward kinematics exactly. The rest is SMPL's flat T-pose (feet at z = 0),
facing -Y like the rig, so the retarget takes it with its default `--bind tpose` and
`--rename smpl`:

    blender -b Animations/skeleton_anim.blend -P tools/glb_retarget.py -- \
        --glb "External Anims/Video/<name>_arm.blend" --rename smpl --name <Clip> --mode action ...
"""
import bpy, sys, os
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]
z = np.load(src)
names = [str(n) for n in z["names"]]
parents = [int(p) for p in z["parents"]]
rest, quat, transl, fps = z["rest"], z["quat"], z["transl"], float(z["fps"])
F = quat.shape[0]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = int(round(fps)); scene.render.fps_base = scene.render.fps / fps
scene.frame_start, scene.frame_end = 1, F
arm_data = bpy.data.armatures.new("Src"); arm = bpy.data.objects.new("SrcArmature", arm_data)
arm_data.display_type = 'STICK'; arm.show_in_front = True
scene.collection.objects.link(arm); bpy.context.view_layer.objects.active = arm; arm.select_set(True)

bpy.ops.object.mode_set(mode='EDIT')
ebs = []
for i, n in enumerate(names):
    eb = arm_data.edit_bones.new(n)
    h = Vector(rest[i].tolist())
    eb.head = h; eb.tail = h + Vector((0, 0.05, 0)); eb.roll = 0.0       # identity rest orientation
    eb.use_deform = False
    ebs.append(eb)
for i, p in enumerate(parents):
    if p >= 0:
        ebs[i].parent = ebs[p]; ebs[i].use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')
# sanity: every rest matrix is the identity rotation
for b in arm_data.bones:
    assert (b.matrix_local.to_quaternion().angle < 1e-4), b.name


def _all_fcurves(a):
    if hasattr(a, "fcurves"):
        return list(a.fcurves)
    out = []
    for layer in a.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out += list(bag.fcurves)
    return out



act = bpy.data.actions.new("SMPL_" + os.path.splitext(os.path.basename(dst))[0])
act.use_fake_user = True
arm.animation_data_create(); arm.animation_data.action = act
frames = np.arange(1, F + 1, dtype=np.float32)
for i, n in enumerate(names):
    pb = arm.pose.bones[n]; pb.rotation_mode = 'QUATERNION'
    paths = [("rotation_quaternion", k, quat[:, i, k]) for k in range(4)]
    if parents[i] < 0:
        loc = transl - rest[i][None, :]
        paths += [("location", k, loc[:, k]) for k in range(3)]
    for prop, k, vals in paths:
        dp = 'pose.bones["%s"].%s' % (n, prop)
        pb.keyframe_insert(prop, index=k, frame=1, group=n)     # creates the slot / channelbag (Blender 5 layered actions)
        fc = next(c for c in _all_fcurves(act) if c.data_path == dp and c.array_index == k)
        fc.keyframe_points.clear()
        fc.keyframe_points.add(F)
        co = np.empty(2 * F, dtype=np.float32); co[0::2] = frames; co[1::2] = vals
        fc.keyframe_points.foreach_set("co", co)
        fc.keyframe_points.foreach_set("interpolation", [bpy.types.Keyframe.bl_rna.properties["interpolation"].enum_items["LINEAR"].value] * F)
        fc.update()


# check: Blender's evaluated joints against the body model's own posed joints (exporter run without resampling)
if "joints_check" in z.files:
    jc = z["joints_check"]; worst = 0.0
    for f in range(0, F, max(1, F // 20)):
        scene.frame_set(f + 1)
        for i in range(22):
            worst = max(worst, ((arm.matrix_world @ arm.pose.bones[names[i]].head) - Vector(jc[f, i].tolist())).length)
    print("[smpl->armature] FK check against the body model: worst joint error %.2f mm" % (worst * 1000))
scene.frame_set(1)
hz = (arm.matrix_world @ arm.pose.bones["pelvis"].head).z
print("[smpl->armature] %d bones, %d frames @ %.2f fps, pelvis z frame 1 %.3f (rest %.3f)" % (len(names), F, fps, hz, rest[0][2]))
os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(dst), compress=True)
print("[smpl->armature] wrote", dst)
