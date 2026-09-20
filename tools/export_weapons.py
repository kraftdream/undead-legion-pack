"""Export the weapons with their grip at the origin, oriented for the socket convention.

    blender -b Weapons/weapons.blend -P tools/export_weapons.py

Writes skeletons/Assets/UndeadLegion/Models/Weapons/SM_<Weapon>.fbx, one per mesh, at
the pack's 1.8x scale. Each mesh is moved so its GRIP POINT is the origin and rotated
so that, after the Y-up export, blade/length runs along +Y (the socket's hilt axis,
CLAUDE.md 2) and the edge plane lies along socket X (across the fingers). A weapon then
attaches to LeftWeaponSocket / RightWeaponSocket with an identity local transform.

The source meshes keep the blade along Blender +Z with the handle below the origin
(H1Sword: pommel at z -0.079, tip at +0.298), so the grip is a small negative-Z offset
into the middle of the handle. Shields attach to the FOREARM (a socket child of the
forearm bone the prefab builder adds); their grip is the boss centre. Nothing is saved
back to weapons.blend.
"""
import bpy, os, math
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "skeletons", "Assets", "UndeadLegion", "Models", "Weapons")
SCALE = 1.8

# name -> (grip point in source metres, rotation about the length axis in degrees)
GRIP = {
    "H1Sword":       (Vector((0, 0, -0.040)), 90),
    "H1Dagger":      (Vector((0, 0, -0.032)), 90),
    "H1Axe":         (Vector((0, 0, -0.034)), 0),
    "H1Mace":        (Vector((0, 0, -0.038)), 0),
    # two-handers: the socket (right hand) sits well up the shaft so the left hand has
    # handle below it (H2Axe handle runs from -0.090 to about +0.15 in source metres)
    "H2Longsword":   (Vector((0, 0, 0.020)), 90),
    "H2Axe":         (Vector((0, 0, 0.040)), 0),
    "H2Longbow":     (Vector((0, 0, 0.0)), 90),
    "H2MagicStuff":  (Vector((0, 0, 0.0)), 0),
    "H1Spellbook":   (Vector((0, 0, 0.0)), 0),
    "H1HeaterShield": (Vector((0, -0.008, -0.02)), 0),
    "H1RoundShield": (Vector((0, -0.02, 0.0)), 0),
    "Arrow":         (Vector((0, 0, -0.10)), 0),
}

os.makedirs(OUT, exist_ok=True)
for name, (grip, roll) in GRIP.items():
    src = bpy.data.objects.get(name)
    if src is None:
        print("[weapons] missing", name); continue
    ob = bpy.data.objects.new("SM_" + name, src.data.copy())
    bpy.context.scene.collection.objects.link(ob)
    M = Matrix.Rotation(math.radians(roll), 4, 'Z') @ Matrix.Translation(-grip)
    ob.data.transform(M)
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
