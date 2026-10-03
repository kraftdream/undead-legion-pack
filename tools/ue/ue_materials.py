"""Textures, the master material, material instances and the weapon meshes (imported by tools/ue/ue_build.py).

Textures come from the Unity project's Textures/ folder, the files the Unity pack ships:
<part>_color (sRGB), <part>_normal (OpenGL: green flipped for Unreal), <part>_metallicsmoothness
(R = metallic, A = smoothness; tools/pack_textures.py). The master material reads the MS map as
Metallic = R, Roughness = 1 - A, so both engines shade from the same data.
"""
import os
import unreal
from ue_common import (PKG, UNITY, EXPORT, CHARACTERS, WEAPONS, RIGGED_WEAPONS, EAL, log, pipeline, interchange)

MASTER = PKG + "/Materials/M_UndeadLegion_Master"
MEL = unreal.MaterialEditingLibrary


def _tex_sets():
    out = []
    for c in CHARACTERS:
        for part, P in (("body", "Body"), ("armor", "Armor")):
            files = {k: os.path.join(UNITY, "Textures", c, "%s_%s.png" % (part, f)) for k, f in
                     (("C", "color"), ("N", "normal"), ("MS", "metallicsmoothness"))}
            out.append((PKG + "/Characters/%s/Textures" % c, "T_%s_%s" % (c, P), files))
    for w in WEAPONS:
        files = {k: os.path.join(UNITY, "Textures", "Weapons", "%s_%s.png" % (w, f)) for k, f in
                 (("C", "color"), ("N", "normal"), ("MS", "metallicsmoothness"))}
        out.append((PKG + "/Weapons/Textures", "T_Weapon_%s" % w, files))
    return out


def textures():
    tasks = []
    for dest, prefix, files in _tex_sets():
        for k, f in files.items():
            if not os.path.exists(f):
                continue
            t = unreal.AssetImportTask()
            t.filename, t.destination_path, t.destination_name = f, dest, "%s_%s" % (prefix, k)
            t.automated, t.replace_existing, t.save = True, True, False
            tasks.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    n = 0
    for dest, prefix, files in _tex_sets():
        for k in files:
            tex = unreal.load_asset("%s/%s_%s" % (dest, prefix, k))
            if tex is None:
                continue
            if k == "N":
                # Unity / Blender normal maps are OpenGL (+Y); Unreal expects DirectX: flip green
                tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
                tex.set_editor_property("srgb", False)
                tex.set_editor_property("flip_green_channel", True)
            elif k == "MS":
                tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
                tex.set_editor_property("srgb", False)
            else:
                tex.set_editor_property("srgb", True)
            EAL.save_loaded_asset(tex, False)
            n += 1
    log("textures: %d" % n)


def _free_path(path):
    # delete_asset refuses a loaded material and returns False (creatures pack): rename_asset frees the path
    if EAL.does_asset_exist(path) and not EAL.delete_asset(path):
        EAL.rename_asset(path, path + "_old_%d" % unreal.MathLibrary.random_integer(1 << 30))


def master_material():
    """BaseColor x Tint, Normal, and the MS map -> Metallic (R), Roughness (1 - A). UseMSMap off: the constant
    Metallic / Roughness params (a weapon without a roughness map: Unity's metallic 0 / smoothness 0.35)."""
    _free_path(MASTER)
    at = unreal.AssetToolsHelpers.get_asset_tools()
    m = at.create_asset("M_UndeadLegion_Master", PKG + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_skeletal_mesh", True)
    E = unreal

    def node(cls, x, y):
        return MEL.create_material_expression(m, cls, x, y)

    bc = node(E.MaterialExpressionTextureSampleParameter2D, -900, -300)
    bc.set_editor_property("parameter_name", "BaseColor")
    bc.set_editor_property("texture", unreal.load_asset(PKG + "/Characters/SkeletonKnight/Textures/T_SkeletonKnight_Body_C"))
    tint = node(E.MaterialExpressionVectorParameter, -900, -60)
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    mul = node(E.MaterialExpressionMultiply, -500, -250)
    MEL.connect_material_expressions(bc, "RGB", mul, "A")
    MEL.connect_material_expressions(tint, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    nm = node(E.MaterialExpressionTextureSampleParameter2D, -900, 100)
    nm.set_editor_property("parameter_name", "Normal")
    nm.set_editor_property("texture", unreal.load_asset(PKG + "/Characters/SkeletonKnight/Textures/T_SkeletonKnight_Body_N"))
    MEL.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    ms = node(E.MaterialExpressionTextureSampleParameter2D, -1200, 450)
    ms.set_editor_property("parameter_name", "MetallicSmoothness")
    ms.set_editor_property("texture", unreal.load_asset(PKG + "/Characters/SkeletonKnight/Textures/T_SkeletonKnight_Armor_MS"))
    inv = node(E.MaterialExpressionOneMinus, -800, 560)
    MEL.connect_material_expressions(ms, "A", inv, "")
    cmet = node(E.MaterialExpressionScalarParameter, -800, 700)
    cmet.set_editor_property("parameter_name", "Metallic")
    cmet.set_editor_property("default_value", 0.0)
    crough = node(E.MaterialExpressionScalarParameter, -800, 800)
    crough.set_editor_property("parameter_name", "Roughness")
    crough.set_editor_property("default_value", 0.65)
    sw_m = node(E.MaterialExpressionStaticSwitchParameter, -400, 450)
    sw_m.set_editor_property("parameter_name", "UseMSMap")
    sw_m.set_editor_property("default_value", True)
    MEL.connect_material_expressions(ms, "R", sw_m, "True")
    MEL.connect_material_expressions(cmet, "", sw_m, "False")
    sw_r = node(E.MaterialExpressionStaticSwitchParameter, -400, 650)
    sw_r.set_editor_property("parameter_name", "UseMSMap")
    sw_r.set_editor_property("default_value", True)
    MEL.connect_material_expressions(inv, "", sw_r, "True")
    MEL.connect_material_expressions(crough, "", sw_r, "False")
    MEL.connect_material_property(sw_m, "", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(sw_r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
    log("master material", MASTER)
    return m


def _mi(path, parent, tex_prefix, two_sided):
    name = path.split("/")[-1]
    folder = path[:-len(name) - 1]
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
    if mi is None:
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.MaterialInstanceConstant,
                                                                     unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    have_ms = False
    for k, pname in (("C", "BaseColor"), ("N", "Normal"), ("MS", "MetallicSmoothness")):
        tp = "%s_%s" % (tex_prefix, k)
        tex = unreal.load_asset(tp) if EAL.does_asset_exist(tp) else None
        if tex is not None:
            MEL.set_material_instance_texture_parameter_value(mi, pname, tex)
            have_ms = have_ms or k == "MS"
        elif k == "N":
            MEL.set_material_instance_texture_parameter_value(mi, pname, unreal.load_asset("/Engine/EngineMaterials/FlatNormal"))
    MEL.set_material_instance_static_switch_parameter_value(mi, "UseMSMap", have_ms)
    ov = mi.get_editor_property("base_property_overrides")
    ov.set_editor_property("override_two_sided", True)
    ov.set_editor_property("two_sided", two_sided)
    mi.set_editor_property("base_property_overrides", ov)
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi, False)
    return mi


def _assign(mesh, mi):
    if isinstance(mesh, unreal.StaticMesh):
        for i in range(len(mesh.get_editor_property("static_materials"))):
            mesh.set_material(i, mi)
    else:
        mats = []                      # the elements are struct COPIES: edit them, then write a new list back
        for sm in mesh.get_editor_property("materials"):
            sm.set_editor_property("material_interface", mi)
            mats.append(sm)
        mesh.set_editor_property("materials", mats)
    EAL.save_loaded_asset(mesh, False)


def materials():
    parent = master_material()
    for c in CHARACTERS:
        base = PKG + "/Characters/%s" % c
        tp = base + "/Textures/T_%s" % c
        body = _mi(base + "/Materials/MI_%s_Body" % c, parent, tp + "_Body", False)
        armor = _mi(base + "/Materials/MI_%s_Armor" % c, parent, tp + "_Armor", True)   # torn cloth, open hoods: both faces
        m = unreal.load_asset(base + "/SK_" + c)
        if m:
            _assign(m, body)
        for a in EAL.list_assets(base + "/Armor", recursive=False):
            am = unreal.load_asset(a)
            if isinstance(am, unreal.SkeletalMesh):
                _assign(am, armor)
        log("materials %s" % c)
    for w in WEAPONS:
        mi = _mi(PKG + "/Weapons/Materials/MI_Weapon_%s" % w, parent, PKG + "/Weapons/Textures/T_Weapon_%s" % w, False)
        for mp in (PKG + "/Weapons/SM_" + w, PKG + "/Weapons/SK_" + w):
            if EAL.does_asset_exist(mp):
                _assign(unreal.load_asset(mp), mi)
    log("weapon materials: %d" % len(WEAPONS))


def weapons():
    stat = pipeline("IP_Weapon_Static", None, statics=True)
    rigged = pipeline("IP_Weapon_Rigged", None)
    for w in WEAPONS:
        f = os.path.join(EXPORT, "Weapons", "SM_%s.fbx" % w)
        m = interchange(f, PKG + "/Weapons", ("SK_" if w in RIGGED_WEAPONS else "SM_") + w,
                        rigged if w in RIGGED_WEAPONS else stat)
        if m is not None:
            b = m.get_bounds()
            log("%-16s %-12s extent (%.1f, %.1f, %.1f) origin (%.1f, %.1f, %.1f)" % (w, type(m).__name__, b.box_extent.x,
                b.box_extent.y, b.box_extent.z, b.origin.x, b.origin.y, b.origin.z))
    EAL.save_directory(PKG + "/Weapons")
