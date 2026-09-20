"""Capture the hand-authored finger grip into a keyed "Grip" action and export it as a clip.

    blender -b Animations/skeleton_anim.blend -P tools/anim_grip_export.py -- [--save]
    blender -b Animations/skeleton_anim.blend -P tools/export_fbx.py -- --clip Grip

The grip was posed on the individual finger controls of BOTH hands (f_index.01.L ...
thumb.03.R) but never keyed: the user's `grip` action keys 68 body controls and no
finger, so the pose exists only in the saved pose state. This reads those 30 controls,
keys them at frames 1 and 2 into a new action `Grip` (every other control at rest, fake
user) and, with --save, writes the file with the `grip` action still assigned. The
exported Skeleton@Grip.fbx is imported like any clip and sampled by the prefab builder
into SkeletonWeapon.gripLeft/gripRight (finger bone local rotations), which the
component applies in LateUpdate to a hand that holds something. The clip is not a
demo state (build_twitch_controller.py skips it).
"""
import bpy, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAVE = "--save" in argv
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
pbs = rig.pose.bones
scene = bpy.context.scene


def log(m):
    print("[grip] " + m)


def is_control(pb):
    n = pb.name
    return not (n.startswith(("DEF-", "ORG-", "MCH-", "VIS_")) or n.endswith(("_ik_target.L", "_ik_target.R")) and False)


fingers = [pb for pb in pbs if pb.name.startswith(("f_index", "f_middle", "f_ring", "f_pinky", "thumb")) and "master" not in pb.name]
captured = {pb.name: (pb.rotation_mode, pb.rotation_quaternion.copy(), pb.rotation_euler.copy(), pb.location.copy()) for pb in fingers}
posed = sum(1 for pb in fingers if (pb.rotation_mode == 'QUATERNION' and pb.rotation_quaternion.angle > 0.01) or (pb.rotation_mode != 'QUATERNION' and max(abs(v) for v in pb.rotation_euler) > 0.01))
log("captured %d finger controls, %d posed (L %d, R %d)" % (len(fingers), posed,
    sum(1 for pb in fingers if pb.name.endswith(".L")), sum(1 for pb in fingers if pb.name.endswith(".R"))))
assert posed >= 20, "the finger controls are not posed in this file"

previous = rig.animation_data.action if rig.animation_data else None
old = bpy.data.actions.get("Grip")
if old is not None:
    bpy.data.actions.remove(old)
act = bpy.data.actions.new("Grip"); act.use_fake_user = True
rig.animation_data_create(); rig.animation_data.action = act
if hasattr(rig.animation_data, "action_slot"):
    slot = act.slots.new(id_type='OBJECT', name=rig.name) if not act.slots else act.slots[0]
    rig.animation_data.action_slot = slot

# every control at rest except the fingers (the IK/FK switches at their rest defaults)
for pb in pbs:
    if pb.name.startswith(("DEF-", "ORG-", "MCH-")) or pb.name in captured:
        continue
    pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
for n, (mode, q, e, loc) in captured.items():
    pb = pbs[n]; pb.rotation_mode = mode; pb.rotation_quaternion = q; pb.rotation_euler = e; pb.location = loc
for f in (1, 2):
    scene.frame_set(f)
    for pb in pbs:
        if pb.name.startswith(("DEF-", "ORG-", "MCH-")):
            continue
        pb.keyframe_insert("location", frame=f, group=pb.name)
        pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=pb.name)
log("action Grip keyed at frames 1..2 (%s)" % ", ".join(sorted(captured)[:4]) + ", ...")

# keep the user's action assigned and the finger pose as it was
rig.animation_data.action = previous
if previous is not None and hasattr(rig.animation_data, "action_slot") and previous.slots:
    rig.animation_data.action_slot = previous.slots[0]
scene.frame_set(0)
for n, (mode, q, e, loc) in captured.items():
    pb = pbs[n]; pb.rotation_mode = mode; pb.rotation_quaternion = q; pb.rotation_euler = e; pb.location = loc
if SAVE:
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath, compress=True)
    log("saved " + os.path.relpath(bpy.data.filepath, ROOT))
