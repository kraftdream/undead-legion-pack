"""Shared constants and import helpers for the tools/ue/ scripts (run inside the UE 5.8 editor)."""
import os, sys, glob, json
import unreal

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPORT = os.path.join(REPO, "Export_UE")
UNITY = os.path.join(REPO, "skeletons", "Assets", "UndeadLegion")
PKG = "/Game/UndeadLegion"
SKEL = PKG + "/Characters/SKEL_UndeadLegion"
CHARACTERS = ["SkeletonKnight", "SkeletonArcher", "SkeletonAssassin", "SkeletonMage", "SkeletonNecromancer", "SkeletonWarrior"]
WEAPONS = ["H1Sword", "H1Dagger", "H1Axe", "H1Mace", "H2Longsword", "H2Axe", "H2Recurvebow", "H2MagicStuff", "H1Wand",
           "H1HeaterShield", "H1RoundShield", "Arrow"]
RIGGED_WEAPONS = ["H2Recurvebow"]            # skinned to its own 8-bone rig (the string pull), CLAUDE.md 8
EAL = unreal.EditorAssetLibrary
DEFAULT_PIPELINE = "/Interchange/Pipelines/DefaultAssetsPipeline"


def log(*a):
    print("[ue_build]", *a)


def clips_manifest():
    return {c["name"]: c for c in json.load(open(os.path.join(REPO, "Animations", "clips.json")))["clips"]}


# ------------------------------------------------------------------------------------------ pipelines

def pipeline(name, skeleton=None, meshes=True, anims=False, physics=False, statics=False):
    """A pipeline ASSET (Interchange's override_pipelines takes asset paths): the engine default duplicated
    and configured. Rewritten on every call so a change here reaches the asset."""
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
        mp.set_editor_property("collision", False)
    ap = p.animation_pipeline
    ap.set_editor_property("import_animations", anims)
    ap.set_editor_property("import_bone_tracks", anims)
    mat = p.material_pipeline
    mat.set_editor_property("import_materials", False)
    mat.texture_pipeline.set_editor_property("import_textures", False)
    EAL.save_asset(path, only_if_is_dirty=False)
    return unreal.SoftObjectPath(path + "." + name)


def interchange(fbx, dest, name, pipe):
    mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
    sd = unreal.InterchangeManager.create_source_data(fbx)
    p = unreal.ImportAssetParameters()
    p.is_automated, p.replace_existing = True, True
    p.destination_name = name
    p.override_pipelines = [pipe]
    mgr.import_asset(dest, sd, p)
    a = unreal.load_asset(dest + "/" + name)
    if a is None:
        log("!! import produced nothing:", fbx)
    return a


