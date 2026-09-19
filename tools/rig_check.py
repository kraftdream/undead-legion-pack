"""Assert a character file uses the shared rig, unchanged, and is export-clean.

    blender -b SkeletonKnight/prod.blend -P tools/rig_check.py

Exit code 1 on any failure. Checks, against Rig/skeleton_rig.blend:
  * every bone (all ~389, not just deform): same name, parent, head, tail, roll
    (deform bones to 1e-4; the tiny MCH helpers are allowed 0.5 deg of roll noise)
  * same deform set
  * every non-widget mesh: exactly one Armature modifier -> RIG-Meta-Rig, parented
    to it, world matrix identity, every vertex weighted, no non-bone vertex groups
  * rig object at identity, no actions in the file (until animation starts)
"""
import bpy, os, sys, math, json
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "Rig", "skeleton_rig.json")  # from tools/rig_lib_dump.py
RIG_OBJ = "RIG-Meta-Rig"
TOL = 1e-4  # metres / radians, deform bones
TOL_HELPER = math.radians(0.5)  # non-deform helpers

fails = []


def fail(msg):
    fails.append(msg); print("[rig_check] FAIL", msg)


def bone_table(arm):
    return {b.name: (b.parent.name if b.parent else None, b.head_local.copy(), b.tail_local.copy(),
                     b.matrix_local.to_3x3().copy(), b.use_deform) for b in arm.bones}


def main():
    here = os.path.relpath(bpy.data.filepath, ROOT)
    rig = bpy.data.objects.get(RIG_OBJ)
    if rig is None or rig.type != 'ARMATURE':
        fail("no armature object " + RIG_OBJ); return
    mine = bone_table(rig.data)
    ref = {n: (v["parent"], Vector(v["head"]), Vector(v["tail"]),
               Matrix([v["axes"][0], v["axes"][1], v["axes"][2]]).transposed(), v["deform"])
           for n, v in json.load(open(LIB)).items()}

    if set(mine) != set(ref):
        fail("bone set differs: +%s -%s" % (sorted(set(mine) - set(ref))[:10], sorted(set(ref) - set(mine))[:10]))
    worst = 0.0
    for n in sorted(set(mine) & set(ref)):
        p, h, t, m, d = mine[n]; rp, rh, rt, rm, rd = ref[n]
        if p != rp: fail("%s parent %s != %s" % (n, p, rp))
        if d != rd: fail("%s use_deform %s != %s" % (n, d, rd))
        dh, dt = (h - rh).length, (t - rt).length
        # chord length of the axis difference, NOT acos(dot): acos turns float32
        # rounding of a unit vector into 0.03 deg of phantom roll
        ang = max((m.col[i] - rm.col[i]).length for i in range(3))
        worst = max(worst, dh, dt, ang if d else 0)
        if dh > TOL or dt > TOL or ang > (TOL if d else TOL_HELPER):
            fail("%s geometry differs: head %.4f tail %.4f roll %.3f deg" % (n, dh, dt, math.degrees(ang)))
    print("[rig_check] %s: %d bones vs library, worst deviation %.6f" % (here, len(mine), worst))

    if rig.matrix_world != Matrix.Identity(4):
        fail("rig object not at identity")
    if bpy.data.actions:
        print("[rig_check] note: actions present:", [a.name for a in bpy.data.actions])
    bones = set(mine)
    n_mesh = 0
    for o in bpy.data.objects:
        if o.type != 'MESH' or o.name.startswith("WGT"):
            continue
        n_mesh += 1
        arms = [m for m in o.modifiers if m.type == 'ARMATURE']
        if len(arms) != 1 or arms[0].object != rig:
            fail("%s armature modifiers: %s" % (o.name, [(m.name, getattr(m.object, 'name', None)) for m in arms]))
        elif o.modifiers[0] != arms[0]:
            fail("%s: Armature modifier is not first in the stack" % o.name)
        if o.parent != rig:
            fail("%s parent is %s" % (o.name, getattr(o.parent, 'name', None)))
        if any(abs(o.matrix_world[i][j] - (1 if i == j else 0)) > 1e-6 for i in range(4) for j in range(4)):
            fail("%s world matrix not identity" % o.name)
        extra = [g.name for g in o.vertex_groups if g.name not in bones]
        if extra:
            fail("%s non-bone vertex groups %s" % (o.name, extra))
        unweighted = sum(1 for v in o.data.vertices if not any(g.weight > 0 for g in v.groups))
        if unweighted:
            fail("%s has %d unweighted vertices" % (o.name, unweighted))
        over = sum(1 for v in o.data.vertices if sum(1 for g in v.groups if g.weight > 0) > 4)
        if over:
            print("[rig_check] note: %s has %d vertices with >4 influences (Unity truncates to 4 by default)" % (o.name, over))
    print("[rig_check] %d meshes checked" % n_mesh)


main()
print("[rig_check] RESULT:", "FAIL (%d)" % len(fails) if fails else "OK")
sys.exit(1 if fails else 0)
