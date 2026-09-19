"""Author the pipeline test clip `Test_RootMotion` in Animations/skeleton_anim.blend.

    blender -b Animations/skeleton_anim.blend -P tools/anim_test_clip.py

30 frames at 30 fps (1.0 s): the Rigify `root` control travels exactly 1.0 m forward
(-Y in Blender = +Z in Unity) and yaws 0 -> 30 deg, the torso twists and the head nods.
Not a shipping clip: it exists so the clip export + Unity import can be verified with
known numbers (tools/unity/verify_clip.py expects 1.0 m and 30 deg).
"""
import bpy, math

NAME = "Test_RootMotion"
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
act = bpy.data.actions.get(NAME)
if act is not None:
    bpy.data.actions.remove(act)
act = bpy.data.actions.new(NAME)
rig.animation_data_create()
rig.animation_data.action = act
if hasattr(rig.animation_data, "action_slot"):
    slot = act.slots.new('OBJECT', rig.name) if hasattr(act, "slots") else None
    if slot is not None:
        rig.animation_data.action_slot = slot

def key(bone, frame, loc=None, rot=None):
    pb = rig.pose.bones[bone]
    pb.rotation_mode = 'XYZ'
    if loc is not None:
        pb.location = loc; pb.keyframe_insert("location", frame=frame)
    if rot is not None:
        pb.rotation_euler = [math.radians(a) for a in rot]; pb.keyframe_insert("rotation_euler", frame=frame)

for pb in rig.pose.bones:
    pb.matrix_basis.identity()
key("root", 1, loc=(0, 0, 0), rot=(0, 0, 0))
key("root", 31, loc=(0, -1.0, 0), rot=(0, 0, 30))
key("torso", 1, rot=(0, 0, 0)); key("torso", 16, rot=(0, 0, 20)); key("torso", 31, rot=(0, 0, 0))
key("head", 1, rot=(0, 0, 0)); key("head", 16, rot=(25, 0, 0)); key("head", 31, rot=(0, 0, 0))
for fc in (act.fcurves if hasattr(act, "fcurves") else
           [f for l in act.layers for s in l.strips for cb in s.channelbags for f in cb.fcurves]):
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'
act.use_fake_user = True
bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 31
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath, compress=True)
print("[test_clip] saved", NAME, "frames", act.frame_range[:], "on", rig.name)
