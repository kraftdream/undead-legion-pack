"""Turn IK stretch off in Rig/skeleton_rig.blend (idempotent).

    blender -b Rig/skeleton_rig.blend -P tools/rig_lib_no_stretch.py

Rigify leaves `ik_stretch = 0.1` on the IK chain bones and `IK_Stretch = 1` on the
limb switches. With that, a pinned foot under a lowered pelvis is reached by SHRINKING
the leg 3 % instead of bending the knee further (and the upright idle stretched it
2 %). Blender shows the foot on the floor; Unity's Humanoid keeps rigid bone lengths
and puts the same rotations 2-3 cm under it. Set here, in the library, because a pose
bone's ik_stretch changed on the anim file's library override is NOT saved with the
override - the export session read 0.1 again. The creatures pack shipped every rig
with stretch off for the same reason.
"""
import bpy
rig = bpy.data.objects["RIG-Meta-Rig"]
n = 0
for pb in rig.pose.bones:
    if pb.ik_stretch != 0.0:
        pb.ik_stretch = 0.0; n += 1
    if "IK_Stretch" in pb and pb["IK_Stretch"] != 0.0:
        pb["IK_Stretch"] = 0.0; n += 1
print("[no_stretch] changed", n, "values")
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath, compress=True)
