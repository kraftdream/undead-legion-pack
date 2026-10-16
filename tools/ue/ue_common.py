"""Shared constants and import helpers for the tools/ue/ scripts (run inside the UE 5.8 editor)."""
import os, sys, glob, json
try:
    import unreal
except ImportError:          # system Python (the MCP-driven builders) only needs the constants and the name map
    unreal = None

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# the Epic-skeleton project (skeletons_ue_epic, 2026-10-05) is the one that is built; its exports live in Export_UE_Epic/
# (the Mixamo project skeletons_ue is kept as it is, its Export_UE/ folder was cleared on 2026-10-05)
_PROJ = unreal.Paths.project_dir().replace("\\", "/").rstrip("/") if unreal else ""
# skeletons_ue54 (2026-10-16) is the UE 5.4 twin of the Epic project: the same skeleton and exports, built without the MCP
UE54 = _PROJ.endswith("skeletons_ue54") or os.environ.get("UL_UE54") == "1"
EPIC = ((_PROJ.endswith("skeletons_ue_epic") or UE54) if unreal
        else (os.environ.get("UL_EPIC") == "1" or "--epic" in sys.argv))      # system Python: UL_EPIC=1 or --epic
EXPORT = os.path.join(REPO, "Export_UE_Epic" if EPIC else "Export_UE")
WEAPONS_EXPORT = os.path.join(REPO, "Export_UE_Epic", "Weapons")
# the Epic skeleton's names for the bones the build steps touch (Rig/epic_skeleton.json; the Mixamo names otherwise)
EPIC_NAMES = {"Root": "root", "Hips": "pelvis", "Spine1": "spine_04", "Head": "head",
              "LeftShoulder": "clavicle_l", "RightShoulder": "clavicle_r", "LeftHand": "hand_l", "RightHand": "hand_r",
              "LeftWeaponSocket": "hand_l", "RightWeaponSocket": "hand_r"}
EPIC_FINGERS = {"Left": ["index_metacarpal_l", "middle_metacarpal_l", "ring_metacarpal_l", "pinky_metacarpal_l", "thumb_01_l"],
                "Right": ["index_metacarpal_r", "middle_metacarpal_r", "ring_metacarpal_r", "pinky_metacarpal_r", "thumb_01_r"]}


# ABP_UndeadSkeleton's float variables and their class defaults (build_abp.py adds the variables through the MCP, ue_build.py
# `abp_defaults` writes the defaults onto the class: the MCP add leaves every float at 0, and FadeSpeed 0 froze the held block, the
# finger idles and the grip fists in the Epic project, 2026-10-05; the Mixamo project's asset had them set by hand once)
ABP_FLOATS = {"BlockAlpha": 0.0, "BlockTarget": 0.0, "Twitch1": 1.0, "Twitch2": 1.0, "Twitch3": 1.0,
              "FingerL": 1.0, "FingerR": 1.0, "FingerTargetL": 1.0, "FingerTargetR": 1.0,
              "GripL": 0.0, "GripR": 0.0, "GripTargetL": 0.0, "GripTargetR": 0.0, "FadeSpeed": 6.6667}


def bn(name):
    """A bone's name in the open project's skeleton."""
    return EPIC_NAMES.get(name, name) if EPIC else name
UNITY = os.path.join(REPO, "skeletons", "Assets", "UndeadLegion")
PKG = "/Game/UndeadLegion"
SKEL = PKG + "/Characters/SKEL_UndeadLegion"
CHARACTERS = ["SkeletonKnight", "SkeletonArcher", "SkeletonAssassin", "SkeletonMage", "SkeletonNecromancer", "SkeletonWarrior"]
WEAPONS = ["H1Sword", "H1Dagger", "H1Axe", "H1Mace", "H2Longsword", "H2Axe", "H2Recurvebow", "H2MagicStuff", "H1Wand",
           "H1HeaterShield", "H1RoundShield", "Arrow"]
RIGGED_WEAPONS = ["H2Recurvebow"]            # skinned to its own 8-bone rig (the string pull), CLAUDE.md 8
EAL = unreal.EditorAssetLibrary if unreal else None
DEFAULT_PIPELINE = "/Interchange/Pipelines/DefaultAssetsPipeline"


def set_socket(sk, loc, rot):
    """A socket's local transform (5.8: set_socket_local_transform; 5.4 has no such function, the properties are editable)."""
    if hasattr(sk, "set_socket_local_transform"):
        sk.set_socket_local_transform(unreal.Transform(loc, rot, unreal.Vector(1, 1, 1)))
    else:
        sk.set_editor_property("relative_location", loc)
        sk.set_editor_property("relative_rotation", rot)
        sk.set_editor_property("relative_scale", unreal.Vector(1, 1, 1))


def log(*a):
    print("[ue_build]", *a)


def clips_manifest():
    return {c["name"]: c for c in json.load(open(os.path.join(REPO, "Animations", "clips.json")))["clips"]}


# ------------------------------------------------------------------------------------------ pipelines

def pipeline(name, skeleton=None, meshes=True, anims=False, physics=False, statics=False):
    """A pipeline ASSET (Interchange's override_pipelines takes asset paths): the engine default duplicated
    and configured. Rewritten on every call so a change here reaches the asset.
    UE 5.4: skeletal meshes and clips go through the legacy importer (legacy_import), so this returns its settings instead."""
    if UE54 and not statics and name != "IP_Weapon_Rigged":
        return {"skeleton": skeleton, "anims": anims and not meshes, "physics": physics}
    path = PKG + "/Pipelines/" + name
    if not EAL.does_asset_exist(path):
        EAL.duplicate_asset(DEFAULT_PIPELINE, path)
    p = unreal.load_asset(path)
    csp = p.common_skeletal_meshes_and_animations_properties
    csp.set_editor_property("skeleton", skeleton)
    csp.set_editor_property("import_only_animations", anims and not meshes)
    cmp = p.common_meshes_properties
    cmp.set_editor_property("recompute_normals", False)
    cmp.set_editor_property("recompute_tangents", True)
    cmp.set_editor_property("import_lods", False)
    if statics:
        cmp.set_editor_property("force_all_mesh_as_type", unreal.InterchangeForceMeshType.IFMT_STATIC_MESH)
    mp = p.mesh_pipeline
    mp.set_editor_property("import_skeletal_meshes", meshes and not statics)
    mp.set_editor_property("import_static_meshes", statics)
    mp.set_editor_property("create_physics_asset", physics)
    mp.set_editor_property("import_morph_targets", False)
    if statics:
        mp.set_editor_property("import_collision" if UE54 else "collision", False)   # 5.4: bImportCollision
    ap = p.animation_pipeline
    ap.set_editor_property("import_animations", anims)
    ap.set_editor_property("import_bone_tracks", anims)
    mat = p.material_pipeline
    mat.set_editor_property("import_materials", False)
    mat.texture_pipeline.set_editor_property("import_textures", False)
    EAL.save_asset(path, only_if_is_dirty=False)
    return unreal.SoftObjectPath(path + "." + name)


def legacy_import(fbx, dest, name, skeleton=None, anims=False, physics=False):
    """UE 5.4: the legacy FBX importer for the character meshes and clips. 5.4's Interchange keeps Blender's `Armature`
    node as an extra ROOT BONE (94 bones, `Armature` above `root`: root motion would come from a bone that never moves);
    the legacy importer skips a root null named Armature (FbxMainImport.cpp, bIsBlenderArmatureBone), as 5.8's Interchange
    does. Settings mirror pipeline(): no materials, no textures, the normals imported, tangents computed, no LODs, no morphs."""
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION if anims else unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("import_mesh", not anims)
    ui.set_editor_property("import_animations", anims)
    ui.set_editor_property("create_physics_asset", physics)
    ui.set_editor_property("automated_import_should_detect_type", False)
    if skeleton is not None:
        ui.set_editor_property("skeleton", skeleton)
    sk = ui.skeletal_mesh_import_data
    sk.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sk.set_editor_property("import_morph_targets", False)
    sk.set_editor_property("convert_scene", True)
    sk.set_editor_property("force_front_x_axis", False)
    ad = ui.anim_sequence_import_data
    ad.set_editor_property("convert_scene", True)
    ad.set_editor_property("force_front_x_axis", False)
    ad.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    ad.set_editor_property("import_bone_tracks", True)
    ad.set_editor_property("remove_redundant_keys", False)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", fbx)
    t.set_editor_property("destination_path", dest)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    t.set_editor_property("options", ui)
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    a = unreal.load_asset(dest + "/" + name)
    if a is None:
        log("!! legacy import produced nothing:", fbx, list(t.get_editor_property("imported_object_paths")))
    return a


def interchange(fbx, dest, name, pipe):
    if UE54 and isinstance(pipe, dict):
        return legacy_import(fbx, dest, name, **pipe)
    mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
    sd = unreal.InterchangeManager.create_source_data(fbx)
    p = unreal.ImportAssetParameters()
    p.is_automated, p.replace_existing = True, True
    p.destination_name = name
    p.override_pipelines = [pipe]
    mgr.import_asset(dest, sd, p)
    # 5.4's Interchange names an animation-only import <name>_Anim (5.8 uses the destination name as given)
    if not EAL.does_asset_exist(dest + "/" + name) and EAL.does_asset_exist(dest + "/" + name + "_Anim"):
        EAL.rename_asset(dest + "/" + name + "_Anim", dest + "/" + name)
    a = unreal.load_asset(dest + "/" + name)
    if a is None:
        log("!! import produced nothing:", fbx)
    return a


