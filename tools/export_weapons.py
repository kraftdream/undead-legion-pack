"""Export the weapons with their grip at the origin, oriented for the socket convention.

    blender -b Weapons/prod.blend -P tools/export_weapons.py
    (--only A,B exports a subset; every mesh comes from prod.blend since 4a70422, the Arrow included)

Writes skeletons/Assets/UndeadLegion/Models/Weapons/SM_<Weapon>.fbx, one per mesh, at
the pack's 1.8x scale. Each mesh is moved so its GRIP POINT is the origin and rotated
so that, after the Y-up export, blade/length runs along +Y (the socket's hilt axis,
CLAUDE.md 2) and the edge plane lies along socket X (across the fingers). A weapon then
attaches to LeftWeaponSocket / RightWeaponSocket with an identity local transform.

Weapons/prod.blend (2026-09-20) replaced weapons.blend: five weapons carry UVs and PBR
textures, H1Wand is new, and several meshes were rescaled and given an object scale.
The object transform is applied first. The GRIP table was tuned on weapons.blend (grip z
in source metres along the blade axis, handle below the origin); for a mesh whose extent
changed, the grip is carried over at the same RELATIVE position along the length
(OLD_EXTENT holds the weapons.blend z ranges). Shields attach to the FOREARM (a socket
child of the forearm bone the prefab builder adds); their grip is the boss centre.
Nothing is saved back to the .blend.
"""
import bpy, os, math
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "skeletons", "Assets", "UndeadLegion", "Models", "Weapons")
SCALE = 1.8

# name -> (grip point in weapons.blend source metres, rotation about the length axis in degrees)
GRIP = {
    "H1Sword":       (Vector((0, 0, -0.040)), 90),
    "H1Dagger":      (Vector((0, 0, -0.032)), 90),
    "H1Axe":         (Vector((0, 0, -0.034)), 0),
    "H1Mace":        (Vector((0, 0, -0.038)), 0),
    # two-handers: the socket (right hand) sits well up the shaft so the left hand has
    # handle below it (H2Axe handle runs from -0.090 to about +0.15 in source metres)
    "H2Longsword":   (Vector((0, 0, 0.020)), 90),
    "H2Axe":         (Vector((0, 0, 0.040)), 0),
    "H2Recurvebow":  (Vector((0, 0, -0.005)), 90),   # replaced H2Longbow (commit 4a70422): held at the middle of the riser
    "H2MagicStuff":  (Vector((0, 0, 0.0)), 0),
    # H1Wand (prod.blend, textured since 4a70422): a 0.39 m short staff; handle = the lower part
    "H1Wand":        (Vector((0, 0, -0.10)), 0),
    # H1Spellbook (no UVs, no textures) is not exported: removed from the pack on 2026-09-21 (user
    # request); its grip was (-0.125, -0.033, 0) roll -90 (held by the spine, pages to the palm)
    "H1HeaterShield": (Vector((0, -0.008, -0.02)), 0),
    "H1RoundShield": (Vector((0, -0.02, 0.0)), 0),
    "Arrow":         (Vector((0, 0, -0.10)), 0),
}
# z extent (min, max) of each mesh in weapons.blend, where GRIP was tuned
OLD_EXTENT = {
    "H1Sword": (-0.079, 0.298), "H1Dagger": (-0.063, 0.177), "H1Axe": (-0.067, 0.216), "H1Mace": (-0.076, 0.241),
    "H2Longsword": (-0.088, 0.349), "H2Axe": (-0.090, 0.306), "H2MagicStuff": (-0.146, 0.203),
 "H1HeaterShield": (-0.176, 0.122), "H1RoundShield": (-0.109, 0.109), "Arrow": (-0.117, 0.118),
}

# meshes modelled along another axis: rotated onto +Z (the length axis) before anything else
PRE = {"Arrow": Matrix.Rotation(math.radians(90), 4, 'X')}   # prod.blend's Arrow (real since 4a70422) lies along +Y, head at +Y


def export_local_mesh(src, name, log=print):
    """A copy of src's mesh data in the EXPORT-LOCAL frame at source scale: the object transform
    and PRE applied, the grip point at the origin, the length axis +Z, the roll about it. The
    1.8x scale is NOT applied (tools/anim_weapon_ref.py attaches this in the Blender-scale anim
    file); the export applies it afterwards."""
    grip, roll = GRIP[name]
    me = src.data.copy()
    me.transform(src.matrix_world)                      # apply the object's own scale/rotation
    if name in PRE:
        me.transform(PRE[name])
    zs = [v.co.z for v in me.vertices]
    if name in OLD_EXTENT:
        o0, o1 = OLD_EXTENT[name]; n0, n1 = min(zs), max(zs)
        if abs((n1 - n0) - (o1 - o0)) > 0.005 or abs(n0 - o0) > 0.005:
            t = (grip.z - o0) / (o1 - o0)
            grip = Vector((grip.x, grip.y, n0 + t * (n1 - n0)))
            log("[weapons] %-15s extent %.3f..%.3f (was %.3f..%.3f): grip carried over to z %.3f" % (name, n0, n1, o0, o1, grip.z))
    me.transform(Matrix.Rotation(math.radians(roll), 4, 'Z') @ Matrix.Translation(-grip))
    return me


import sys
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None   # e.g. the Arrow, still exported from weapons.blend
for name, (grip, roll) in (GRIP.items() if __name__ == "__main__" else ()):
    if ONLY is not None and name not in ONLY:
        continue
    src = bpy.data.objects.get(name)
    if src is None:
        print("[weapons] missing", name); continue
    os.makedirs(OUT, exist_ok=True)
    ob = bpy.data.objects.new("SM_" + name, export_local_mesh(src, name))
    bpy.context.scene.collection.objects.link(ob)
    ob.data.transform(Matrix.Scale(SCALE, 4))
    # the Tripo meshes are wound inside out in places (a fully inverted mesh is invisible
    # under back-face culling): make the winding consistent and outward
    import bmesh
    bm = bmesh.new(); bm.from_mesh(ob.data)
    before = [f.normal.copy() for f in bm.faces]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    flipped = sum(1 for f, v in zip(bm.faces, before) if f.normal.dot(v) < 0)
    bm.to_mesh(ob.data); bm.free()
    ob.matrix_world = Matrix.Identity(4)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    path = os.path.join(OUT, "SM_%s.fbx" % name)
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'},
                             apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                             use_mesh_modifiers=True, mesh_smooth_type='OFF', path_mode='AUTO',
                             embed_textures=False, use_custom_props=False, bake_anim=False)
    co = [v.co for v in ob.data.vertices]
    print("[weapons] %-15s -> %s  length %.3f m  (z %.3f..%.3f)  %d faces re-wound of %d" % (name, os.path.relpath(path, ROOT),
          max(c.z for c in co) - min(c.z for c in co), min(c.z for c in co), max(c.z for c in co), flipped, len(ob.data.polygons)))
    bpy.data.objects.remove(ob, do_unlink=True)
