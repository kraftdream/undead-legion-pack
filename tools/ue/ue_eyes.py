"""The glowing eyes (Unity: Demo/Scripts/SkeletonEyes.cs, base pack since 2026-10-01). Imported by ue_build.py, step `eyes`.

Unity: two unlit spheres of `size` 0.018 m, HDR colour (5, 0.2, 0.1) so Bloom makes them glow, placed at `offset` from the
Head bone in the CHARACTER's frame (x right, y up, z forward) on the bind pose; the prefab builder measures each skull's
socket floor, so the offset is per character (Knight / Archer z 0.071, the other four 0.086). This reads the offsets
straight from the Unity prefabs, so the two engines cannot drift apart.

Unreal: sockets EyeL / EyeR on the Head bone of every body (created by `python tools/ue/ue_weapons.py`, seated here),
M_Eyes (unlit, emissive = the `Color` parameter), and BP_UndeadSkeleton's EyeL / EyeR sphere components (attached to the
sockets by its construction script; `SetEyesVisible`, `SetEyeColor`). Mesh component space: forward +Y, up +Z, the
character's right is -X (the BP yaws the mesh -90).
"""
import os, re
import unreal
from ue_common import (PKG, UNITY, CHARACTERS, EAL, log, bn)

MEL = unreal.MaterialEditingLibrary
MAT = PKG + "/Materials/M_Eyes"
COLOR = unreal.LinearColor(5.0, 0.2, 0.1, 1.0)


def unity_eyes(c):
    txt = open(os.path.join(UNITY, "Prefabs", "Characters", "PF_%s.prefab" % c), encoding="utf-8").read()
    m = re.search(r"offset: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+)\}\s*\n\s*size: ([-\d.e]+)", txt)
    return tuple(float(v) for v in m.groups())


def material():
    if EAL.does_asset_exist(MAT):
        return unreal.load_asset(MAT)
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_Eyes", PKG + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("used_with_skeletal_mesh", True)
    p = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -400, 0)
    p.set_editor_property("parameter_name", "Color")
    p.set_editor_property("default_value", COLOR)
    MEL.connect_material_property(p, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
    return m


def sockets():
    X = unreal.AnimPoseExtensions
    ref = X.get_reference_pose(unreal.load_asset(PKG + "/Characters/SKEL_UndeadLegion"))
    head = X.get_bone_pose(ref, bn("Head"), unreal.AnimPoseSpaces.WORLD)
    for c in CHARACTERS:
        ox, oy, oz, size = unity_eyes(c)
        mesh = unreal.load_asset("%s/Characters/%s/SK_%s" % (PKG, c, c))
        for name, sx in (("EyeL", -1.0), ("EyeR", 1.0)):
            sk = mesh.find_socket(name)
            if sk is None:
                log("!! %s has no %s: run `python tools/ue/ue_weapons.py` first" % (c, name))
                continue
            # character frame (x right, y up, z fwd) -> mesh component space (right = -X, fwd = +Y, up = +Z), cm
            world = head.translation + unreal.Vector(-sx * ox * 100.0, oz * 100.0, oy * 100.0)
            local = head.inverse_transform_location(world)
            sk.set_socket_local_transform(unreal.Transform(local, unreal.Rotator(), unreal.Vector(1, 1, 1)))
        EAL.save_loaded_asset(mesh, False)
        log("%-20s eyes at (±%.1f, fwd %.1f, up %.1f) cm from Head, size %.1f cm" % (c, ox * 100, oz * 100, oy * 100, size * 100))


def components():
    """EyeL / EyeR on BP_UndeadSkeleton: the engine sphere (1 m) scaled to Unity's 0.018 m, M_Eyes, no collision, no shadow."""
    import ue_demo_ui
    bp = unreal.load_asset(PKG + "/Blueprints/BP_UndeadSkeleton")
    mat = material()
    size = unity_eyes("SkeletonKnight")[3]
    for n in ("EyeL", "EyeR"):
        comp = ue_demo_ui._component(bp, unreal.StaticMeshComponent, n)
        comp.set_editor_property("static_mesh", unreal.load_asset("/Engine/BasicShapes/Sphere"))
        comp.set_editor_property("relative_scale3d", unreal.Vector(size, size, size))
        comp.set_material(0, mat)
        comp.set_collision_profile_name("NoCollision")
        comp.set_editor_property("cast_shadow", False)
    L = unreal.BlueprintEditorLibrary
    have = set(str(v) for v in L.list_member_variable_names(bp))
    for name, t in (("EyesVisible", L.get_basic_type_by_name("bool")),
                    ("EyeColor", L.get_struct_type(unreal.LinearColor.static_struct()))):
        if name not in have:
            L.add_member_variable(bp, name, t)
        L.set_blueprint_variable_category(bp, name, unreal.Text("Undead Legion"))
        L.set_blueprint_variable_instance_editable(bp, name, True)
    L.compile_blueprint(bp)
    cdo = unreal.get_default_object(L.generated_class(bp))
    cdo.set_editor_property("EyesVisible", True)
    cdo.set_editor_property("EyeColor", COLOR)
    L.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, False)
    log("eye components on BP_UndeadSkeleton (size %.3f, colour %s)" % (size, COLOR))


def eyes():
    material()
    sockets()
    components()
