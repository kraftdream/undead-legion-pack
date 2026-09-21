"""Copy the pose on one frame of an action into a one-frame action of its own.

    blender -b Animations/skeleton_anim.blend -P tools/anim_pose_save.py -- --from Idle_Propped:0 --to Propped_Base [--save]

For a reference the user posed on a frame of a GENERATED clip (the retarget deletes and
recreates that action on every rebuild, so the pose would be lost): every control's
location / rotation / custom switches are keyed on frame 1 of the new action, which the
retarget can then read (`--torso-ref`, `--hand-ref`, `--blend-from`).
"""
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(k, d=None):
    return argv[argv.index(k) + 1] if k in argv else d


SRC = arg("--from")
DST = arg("--to")
SAVE = "--save" in argv
src_name, _, src_frame = SRC.partition(":")
src_frame = int(src_frame or 1)

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
pbs = rig.pose.bones
scene = bpy.context.scene
src = bpy.data.actions[src_name]
rig.animation_data.action = src
if hasattr(rig.animation_data, "action_slot") and src.slots:
    rig.animation_data.action_slot = src.slots[0]
scene.frame_set(src_frame)
bpy.context.view_layer.update()
controls = [b.name for b in pbs if not b.name.startswith(("DEF-", "MCH-", "ORG-", "VIS_"))]
state = {}
for n in controls:
    pb = pbs[n]
    props = {k: pb[k] for k in pb.keys() if not k.startswith("_")}
    state[n] = (pb.location.copy(), pb.rotation_quaternion.copy(), pb.rotation_euler.copy(), pb.scale.copy(), props)

old = bpy.data.actions.get(DST)
if old is not None:
    bpy.data.actions.remove(old)
dst = bpy.data.actions.new(DST)
dst.use_fake_user = True
rig.animation_data.action = dst
if hasattr(rig.animation_data, "action_slot"):
    rig.animation_data.action_slot = dst.slots.new('OBJECT', rig.name)
scene.frame_set(1)
for n, (loc, rq, re, sc, props) in state.items():
    pb = pbs[n]
    pb.location = loc
    pb.rotation_quaternion = rq
    pb.rotation_euler = re
    pb.scale = sc
    for k, v in props.items():
        try:
            pb[k] = v
        except Exception:
            pass
    pb.keyframe_insert("location", frame=1, group=n)
    pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=1, group=n)
    for k in props:
        try:
            pb.keyframe_insert('["%s"]' % k, frame=1, group=n)
        except Exception:
            pass
bpy.context.view_layer.update()
print("[pose] %s frame %d -> %s frame 1 (%d controls)" % (src_name, src_frame, DST, len(controls)))
if SAVE:
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath, compress=True)
    print("[pose] saved")
