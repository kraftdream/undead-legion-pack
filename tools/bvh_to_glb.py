"""Convert a video-mocap BVH into the GLB the retarget reads.

    blender -b -P tools/bvh_to_glb.py -- "P:/attacks sword_swing.bvh" "External Anims/Kimodo/attack_swing2_mocap.glb" [--yup]

The app's BVH is Z-UP (the hips' OFFSET z is the standing height, ~1.01 m) with the rest pose a
T-pose, so it is imported with axis_up Z (`--yup` for a conventional Y-up BVH) and written as a
Y-up GLB with the animation sampled, exactly like the app's own GLB export (52 `*_JNT` joints,
24 fps). Prints the rest positions of the hands, head and hips so a wrong axis choice is visible
(hands at +-0.63 m sideways at 1.44 m = a T-pose standing up).
"""
import bpy, sys

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]
yup = "--yup" in argv
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_anim.bvh(filepath=src, rotate_mode='QUATERNION', axis_forward='-Z' if yup else 'Y', axis_up='Y' if yup else 'Z',
                        update_scene_fps=True, update_scene_duration=True, use_fps_scale=False)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
for n in ("l_hand_JNT", "r_hand_JNT", "head_JNT", "hips_JNT"):
    b = arm.data.bones.get(n)
    if b:
        print("[bvh] rest %-11s (%.2f, %.2f, %.2f)" % (n, *(arm.matrix_world @ b.head_local)))
print("[bvh] imported: %d bones, %d fps, frames %d..%d" % (len(arm.data.bones), bpy.context.scene.render.fps, bpy.context.scene.frame_start, bpy.context.scene.frame_end))
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', export_animations=True, export_skins=True, export_apply=False, export_yup=True,
                          export_force_sampling=True, export_frame_range=False, export_anim_single_armature=True)
print("[bvh] wrote", dst)
