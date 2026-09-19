"""Dump Rig/skeleton_rig.blend's bone table to Rig/skeleton_rig.json.

    blender -b Rig/skeleton_rig.blend -P tools/rig_lib_dump.py

tools/rig_check.py compares character files against this JSON rather than
against a linked copy of the library: a linked armature carries the matrices it
was SAVED with, not evaluated ones, and the two disagree by up to 0.2 deg on the
tiny MCH helper bones. Re-run after every edit of the library.
"""
import bpy, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
arm = bpy.data.objects["RIG-Meta-Rig"].data
out = {b.name: {"parent": b.parent.name if b.parent else None, "deform": b.use_deform,
                "head": list(b.head_local), "tail": list(b.tail_local),
                "axes": [list(b.matrix_local.col[i][:3]) for i in range(3)],
                "segments": b.bbone_segments} for b in arm.bones}
path = os.path.join(ROOT, "Rig", "skeleton_rig.json")
json.dump(out, open(path, "w"), indent=0)
print("[rig_lib_dump]", len(out), "bones ->", path)
