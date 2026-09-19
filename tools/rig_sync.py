"""Replace a character file's rig with the shared one and normalise the file.

    blender -b SkeletonKnight/prod.blend -P tools/rig_sync.py

What it does, in order:
  1. snapshots every mesh's world-space vertices at rest AND under a test pose
  2. deletes the file's own Rigify rig, metarig and widgets
  3. appends Rig/skeleton_rig.blend (RIG-Meta-Rig + Meta-Rig + widgets)
  4. re-points every Armature modifier and parent to the new rig
  5. applies object transforms into the mesh data (flipping normals where the
     scale was negative), so every mesh node exports at identity
  6. drops dangling Armature modifiers and non-bone vertex groups
  7. fixes misspelled collection names
  8. re-snapshots and reports the max vertex deviation, rest and posed
  9. saves in place (no .blend1)

Rest deviation must be 0. Posed deviation is 0 when the file's old rig was
already identical to the library; a file whose rig had drifted reports where.
"""
import bpy, os, sys
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "Rig", "skeleton_rig.blend")
RIG_OBJ, META_OBJ = "RIG-Meta-Rig", "Meta-Rig"
COLL_FIX = {"SeletonAssassin": "SkeletonAssassin", "SeletonWarrior": "SkeletonWarrior"}
TEST_POSE = {  # control bone -> (rotation_euler deg, location)
    "torso": ((0, 0, 25), (0, 0, 0.03)),
    "head": ((20, 0, 30), None),
    "hand_ik.L": (None, (0.05, -0.15, 0.2)),
    "foot_ik.R": (None, (0.05, -0.1, 0.1)),
    "upper_arm_fk.R": ((30, 0, -40), None),
}


def log(*a):
    print("[rig_sync]", *a); sys.stdout.flush()


def meshes():
    return [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("WGT")]


def snapshot():
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    out = {}
    for o in meshes():
        oe = o.evaluated_get(dg); me = oe.to_mesh()
        M = oe.matrix_world
        out[o.name] = ([M @ v.co for v in me.vertices],
                       [(M.to_3x3() @ p.normal).normalized() for p in me.polygons[:50]])
        oe.to_mesh_clear()
    return out


def apply_pose(rig, on):
    import math
    for n, (rot, loc) in TEST_POSE.items():
        pb = rig.pose.bones.get(n)
        if pb is None:
            log("  test pose: no control", n); continue
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = [math.radians(a) for a in rot] if (on and rot) else (0, 0, 0)
        pb.location = loc if (on and loc) else (0, 0, 0)


def compare(a, b, label, normals=True):
    worst = 0.0
    for name in a:
        if name not in b:
            log("  MISSING after sync:", name); continue
        va, vb = a[name][0], b[name][0]
        if len(va) != len(vb):
            log("  vertex count changed:", name); continue
        d = max((x - y).length for x, y in zip(va, vb)) if va else 0.0
        nd = max((1 - x.dot(y)) for x, y in zip(a[name][1], b[name][1])) if a[name][1] else 0.0
        flag = "" if d < 1e-5 else "   <-- moved"
        if normals and nd > 1e-4:
            flag += "   <-- NORMALS FLIPPED"
        log("  %-8s %-12s max dev %.5f m%s" % (label, name, d, flag))
        worst = max(worst, d)
    return worst


def main():
    path = bpy.data.filepath
    assert path and os.path.exists(LIB), (path, LIB)
    old = bpy.data.objects[RIG_OBJ]
    old_meta = bpy.data.objects.get(META_OBJ)
    assert old.matrix_world == Matrix.Identity(4), "old rig not at identity"
    for pb in old.pose.bones:
        pb.matrix_basis.identity()

    ms = meshes()
    log(os.path.relpath(path, ROOT), "-", len(ms), "meshes")
    # the library has no B-bones; take the posed reference without them too, so
    # the posed comparison isolates REST-POSE drift from the (expected) B-bone loss
    for b in old.data.bones:
        b.bbone_segments = 1
    rest0 = snapshot()
    apply_pose(old, True); posed0 = snapshot(); apply_pose(old, False)

    # 2. delete the old rig, metarig and its widgets
    wgts = {pb.custom_shape for pb in old.pose.bones if pb.custom_shape}
    if old_meta:
        wgts |= {pb.custom_shape for pb in old_meta.pose.bones if pb.custom_shape}
    wgts |= {o for o in bpy.data.objects if o.name.startswith("WGT-")}
    for o in list(wgts) + [old] + ([old_meta] if old_meta else []):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        if c.name.startswith("WGTS") and not c.objects and not c.children:
            bpy.data.collections.remove(c)
    # free the datablock NAMES before appending, or the library copies land as .001
    for a in list(bpy.data.armatures):
        if a.users == 0:
            bpy.data.armatures.remove(a)
    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    # 3. append the shared rig
    with bpy.data.libraries.load(LIB, link=False) as (src, dst):
        dst.collections = ["Rig", "WGTS_Rig"]
    rig_col, w_col = bpy.data.collections["Rig"], bpy.data.collections["WGTS_Rig"]
    rig, meta = bpy.data.objects[RIG_OBJ], bpy.data.objects[META_OBJ]
    assert rig.data.library is None and rig.data.name == "RIG-Meta-Rig", rig.data.name
    home = ms[0].users_collection[0]
    for o in (rig, meta):
        rig_col.objects.unlink(o); home.objects.link(o)
    bpy.data.collections.remove(rig_col)
    bpy.context.scene.collection.children.link(w_col)
    bpy.context.view_layer.layer_collection.children["WGTS_Rig"].exclude = True

    bone_names = {b.name for b in rig.data.bones}
    # 4-6. meshes
    for o in ms:
        if o.data.users > 1:
            o.data = o.data.copy()
        M = o.matrix_world.copy()
        if M != Matrix.Identity(4):
            o.data.transform(M)
            if M.to_3x3().determinant() < 0:
                o.data.flip_normals()
        o.parent = rig; o.parent_type = 'OBJECT'
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = Matrix.Identity(4)
        for m in list(o.modifiers):
            if m.type == 'ARMATURE':
                o.modifiers.remove(m)
        m = o.modifiers.new("Armature", 'ARMATURE'); m.object = rig
        bpy.context.view_layer.objects.active = o
        o.modifiers.move(len(o.modifiers) - 1, 0)
        for g in list(o.vertex_groups):
            if g.name not in bone_names:
                log("  drop vertex group", o.name, g.name); o.vertex_groups.remove(g)

    # 7. collections
    for a, b in COLL_FIX.items():
        if a in bpy.data.collections:
            bpy.data.collections[a].name = b; log("  collection", a, "->", b)

    # 8. verify
    rest1 = snapshot()
    apply_pose(rig, True); posed1 = snapshot(); apply_pose(rig, False)
    w_rest = compare(rest0, rest1, "rest")
    w_pose = compare(posed0, posed1, "posed", normals=False)
    assert w_rest < 1e-5, "REST GEOMETRY MOVED - not saving"

    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    log("saved; worst rest %.6f, worst posed %.5f" % (w_rest, w_pose))


main()
