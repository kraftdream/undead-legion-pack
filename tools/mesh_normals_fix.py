"""Find and fix inside-out faces in a character file; write the result to prod_copy.blend.

    blender -b SkeletonMage/prod.blend -P tools/mesh_normals_fix.py [-- --save] [--render DIR]

Unity culls back faces, so a face wound inward is a hole. Two kinds of fault exist:
  * INCONSISTENT winding inside one connected island (some faces flipped relative to
    their neighbours) - bmesh recalc_face_normals repairs it and, for a CLOSED island,
    also orients the whole shell outward.
  * an OPEN island (a cloth strip, a hood, a single-layer sleeve) that is consistent
    but wound as a whole towards the body - recalc cannot know which side is out, so
    the island is voted: its area-weighted normals against the direction from the
    nearest point on the BODY mesh surface (the bare skeleton); negative -> flip it.
    The Body itself is closed bone shells and gets the recalc only.
Per mesh it reports islands, how many faces recalc changed, how many islands the vote
flipped, and the area fraction of open-island faces that face the body after the fix.
`--render DIR` writes Workbench front/back renders WITH back-face culling before and
after, which is what Unity shows.

With --save the fixed file is written to <Character>/prod_copy.blend; prod.blend is
never modified.
"""
import bpy, bmesh, os, sys, math
import numpy as np
from mathutils import Vector, kdtree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAVE = "--save" in argv
RENDER = argv[argv.index("--render") + 1] if "--render" in argv else None
char = os.path.basename(os.path.dirname(bpy.data.filepath))
meshes = sorted([o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("WGT")], key=lambda o: o.name)
body = bpy.data.objects["Body"]

# body surface KD-tree (world space; objects are at identity after rig_sync)
kd = kdtree.KDTree(len(body.data.vertices))
for v in body.data.vertices:
    kd.insert(body.matrix_world @ v.co, v.index)
kd.balance()


def islands_of(bm):
    seen = set(); out = []
    for f in bm.faces:
        if f.index in seen: continue
        stack = [f]; isl = []
        while stack:
            g = stack.pop()
            if g.index in seen: continue
            seen.add(g.index); isl.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen: stack.append(h)
        out.append(isl)
    return out


def fix(ob):
    me = ob.data; M = ob.matrix_world; M3 = M.to_3x3()
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    n_isl = 0; recalc_changed = 0; voted = 0; open_area = 0.0; open_inward = 0.0
    for isl in islands_of(bm):
        n_isl += 1
        before = {f.index: f.normal.copy() for f in isl}
        bmesh.ops.recalc_face_normals(bm, faces=isl)
        recalc_changed += sum(1 for f in isl if f.normal.dot(before[f.index]) < 0)
        is_open = any(len(e.link_faces) == 1 for f in isl for e in f.edges)
        if not is_open or ob is body:
            continue
        score = 0.0; area_sum = 0.0; inward = 0.0
        for f in isl:
            c = M @ f.calc_center_median(); a = f.calc_area()
            near = kd.find(c)[0]
            away = (c - near); away = away.normalized() if away.length > 1e-9 else Vector((0, 0, 1))
            d = (M3 @ f.normal).normalized().dot(away)
            score += a * d; area_sum += a
            if d < 0: inward += a
        if score < 0:
            bmesh.ops.reverse_faces(bm, faces=isl); voted += 1
            inward = area_sum - inward
        open_area += area_sum; open_inward += inward
    bm.to_mesh(me); me.update()
    bm.free()
    return n_isl, recalc_changed, voted, (open_inward / open_area if open_area else 0.0)


def render(tag):
    if not RENDER: return
    for o in bpy.data.objects:
        if o.type == 'ARMATURE' or o.name.startswith("WGT"): o.hide_render = True
    for o in meshes: o.hide_render = False; o.hide_viewport = False
    sc = bpy.context.scene
    # EEVEE with back-face culling ON THE MATERIALS: that is what Unity's default
    # single-sided materials do. (Workbench's culling flag is viewport-only.)
    sc.render.engine = 'BLENDER_EEVEE'
    for m in bpy.data.materials:
        m.use_backface_culling = True
    sc.render.resolution_x = 420; sc.render.resolution_y = 672; sc.render.resolution_percentage = 100
    if not any(o.type == 'LIGHT' for o in bpy.data.objects):
        for name, rot, energy in (("_key", (50, 0, 30), 3.0), ("_fill", (60, 0, -120), 1.2), ("_rim", (40, 0, 160), 1.5)):
            ld = bpy.data.lights.new(name, 'SUN'); ld.energy = energy
            lo = bpy.data.objects.new(name, ld); sc.collection.objects.link(lo); lo.rotation_euler = [math.radians(a) for a in rot]
    sc.render.image_settings.file_format = 'PNG'
    sc.world = sc.world or bpy.data.worlds.new("W"); sc.world.color = (0.18, 0.18, 0.2)
    cam = bpy.data.objects.get("_cam")
    if cam is None:
        cd = bpy.data.cameras.new("_cam"); cd.type = 'ORTHO'; cd.ortho_scale = 1.25
        cam = bpy.data.objects.new("_cam", cd); sc.collection.objects.link(cam)
    sc.camera = cam
    os.makedirs(RENDER, exist_ok=True)
    for view, loc, rot in (("front", (0, -6, 0.5), (90, 0, 0)), ("back", (0, 6, 0.5), (90, 0, 180)), ("side", (6, 0, 0.5), (90, 0, 90))):
        cam.location = loc; cam.rotation_euler = [math.radians(a) for a in rot]
        sc.render.filepath = os.path.join(RENDER, "%s_%s_%s.png" % (char, tag, view))
        bpy.ops.render.render(write_still=True)


render("before")
total = 0
for ob in meshes:
    n_isl, changed, voted, inward = fix(ob)
    total += changed + voted
    print("NORMALS %-20s %-10s islands %3d  faces re-wound %4d  open islands flipped %2d  open-cloth area facing the body after %5.1f%%"
          % (char, ob.name, n_isl, changed, voted, 100 * inward))
render("after")
if SAVE and total:
    out = os.path.join(os.path.dirname(bpy.data.filepath), "prod_copy.blend")
    for o in list(bpy.data.objects):
        if o.name in ("_cam", "_key", "_fill", "_rim"): bpy.data.objects.remove(o, do_unlink=True)
    for m in bpy.data.materials:
        m.use_backface_culling = False
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print("NORMALS %s: %d faces / islands changed -> saved %s (prod.blend untouched)" % (char, total, os.path.relpath(out)))
elif SAVE:
    print("NORMALS %s: nothing to fix, no copy written" % char)
