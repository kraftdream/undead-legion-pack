"""Build the Unreal content of the pack from the export folder of the open project (Export_UE_Epic/ for skeletons_ue_epic; runs INSIDE the UE 5.8 editor).

    python tools/ue/ue_py.py tools/ue/ue_build.py <step> [<step> ...]

Steps, in dependency order ("all" runs them in this order):
    models     SK_<Character> bodies (the Knight's import creates the shared skeleton SKEL_UndeadLegion) and
               the 48 armour modules SK_<Character>_<Module>, every one on that ONE skeleton
    textures   T_<Character>_<part>_{C,N,MS} and T_Weapon_<Name>_{C,N,MS} from the Unity project's Textures/
               (the same files the Unity pack ships: MS = R metallic, A smoothness)
    materials  M_UndeadLegion_Master + MI_<Character>_{Body,Armor}, MI_Weapon_<Name>, assigned to the meshes
    weapons    SM_<Weapon> (static) and SK_H2Recurvebow (the rigged bow)
    clips      A_<Clip> for every Export_UE/Animations/Skeleton@<Clip>.fbx; root motion on the locomotion loops
    measure    bounds, bone count, skeleton sharing, every clip's frames / length / root travel

The Unity pack's layout, re-cut for Unreal, under /Game/UndeadLegion:
    Characters/<Character>/SK_<Character>, Characters/<Character>/Armor/SK_<Character>_<Module>
    Characters/SKEL_UndeadLegion (+ PA_UndeadLegion)        Animations/A_<Clip>
    Weapons/SM_<Weapon>                                      Materials/, Textures/<owner>/
"""
import os, sys, glob, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unreal
import ue_common, ue_materials, ue_anims, ue_weapons, ue_character, ue_demo_ui, ue_eyes
for _m in (ue_common, ue_materials, ue_anims, ue_weapons, ue_character, ue_demo_ui, ue_eyes):
    importlib.reload(_m)
from ue_common import *
from ue_materials import textures, materials, weapons
from ue_anims import clips, montages, measure_clips
from ue_weapons import sockets, weapon_blueprints
from ue_character import base as character, children as character_children
from ue_demo_ui import demo_vars, demo_data, demo_actors, showreel_director, showreel_bow
from ue_eyes import eyes

# ------------------------------------------------------------------------------------------ models

def models(only=None):
    skel = unreal.load_asset(SKEL) if EAL.does_asset_exist(SKEL) else None
    if skel is None:
        # the Knight's import creates the skeleton (and its physics asset); both are then given the pack's names
        dest = PKG + "/Characters/SkeletonKnight"
        mesh = interchange(os.path.join(EXPORT, "Characters", "SkeletonKnight", "SK_SkeletonKnight.fbx"), dest,
                           "SK_SkeletonKnight", pipeline("IP_Body_First", None, physics=True))
        skel = mesh.skeleton
        old = skel.get_path_name().split(".")[0]
        EAL.rename_asset(old, SKEL)
        pa = mesh.get_editor_property("physics_asset")
        if pa is not None:
            EAL.rename_asset(pa.get_path_name().split(".")[0], PKG + "/Characters/PA_UndeadLegion")
        skel = unreal.load_asset(SKEL)
        _fix_redirectors(PKG)
        EAL.save_directory(PKG)
        log("skeleton %s (%d bones)" % (SKEL, len(unreal.AnimPoseExtensions.get_bone_names(unreal.AnimPoseExtensions.get_reference_pose(skel)))))
    body_pipe = pipeline("IP_Body", skel)
    for c in CHARACTERS:
        if only and c not in only:
            continue
        dest = PKG + "/Characters/" + c
        if c != "SkeletonKnight" or not EAL.does_asset_exist(dest + "/SK_" + c):
            m = interchange(os.path.join(EXPORT, "Characters", c, "SK_%s.fbx" % c), dest, "SK_" + c, body_pipe)
            _check_skeleton(m, skel)
        pa = unreal.load_asset(PKG + "/Characters/PA_UndeadLegion")
        m = unreal.load_asset(dest + "/SK_" + c)
        if pa is not None and m is not None:
            m.set_editor_property("physics_asset", pa)
        for f in sorted(glob.glob(os.path.join(EXPORT, "Armor", c, "SK_*.fbx"))):
            n = os.path.basename(f)[:-4]
            m = interchange(f, dest + "/Armor", n, body_pipe)
            _check_skeleton(m, skel)
        EAL.save_directory(dest)
    EAL.save_directory(PKG + "/Characters")


def abp_asset():
    """The Animation Blueprint ASSET on the shared skeleton (its graphs are build_abp.py's). The Mixamo project's was made
    by hand once; the Epic twin needs it scripted (2026-10-05)."""
    path = PKG + "/Blueprints/ABP_UndeadSkeleton"
    if EAL.does_asset_exist(path):
        log("ABP_UndeadSkeleton exists"); return
    f = unreal.AnimBlueprintFactory()
    f.set_editor_property("target_skeleton", unreal.load_asset(SKEL))
    f.set_editor_property("parent_class", unreal.AnimInstance)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("ABP_UndeadSkeleton", PKG + "/Blueprints", unreal.AnimBlueprint, f)
    EAL.save_loaded_asset(bp, False)
    log("ABP_UndeadSkeleton created on " + SKEL)


def save_all():
    """Save every dirty asset under the pack: the MCP-built widgets and graphs stay unsaved in memory (WBP_DemoHeader was missing
    from the Epic project on disk after a complete build, 2026-10-05) and an editor restart would lose them."""
    ok = EAL.save_directory(PKG, only_if_is_dirty=True, recursive=True)
    log("save_all: %s" % ok)


def _check_skeleton(mesh, skel):
    if mesh is None:
        return
    if mesh.skeleton != skel:
        raise RuntimeError("%s is on %s, not the shared skeleton" % (mesh.get_name(), mesh.skeleton.get_path_name() if mesh.skeleton else None))
    log("%-40s ok (shared skeleton)" % mesh.get_name())


def _fix_redirectors(path):
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter(package_paths=[path], recursive_paths=True, class_paths=[unreal.TopLevelAssetPath("/Script/CoreUObject", "ObjectRedirector")])
    reds = [a.get_asset() for a in reg.get_assets(flt)]
    if reds:
        unreal.AssetToolsHelpers.get_asset_tools().fixup_referencers(reds)
        log("fixed %d redirector(s)" % len(reds))


# ------------------------------------------------------------------------------------------ measure

def measure():
    X = unreal.AnimPoseExtensions
    skel = unreal.load_asset(SKEL)
    ref = X.get_reference_pose(skel)
    names = list(X.get_bone_names(ref))
    hips = X.get_bone_pose(ref, bn("Hips"), unreal.AnimPoseSpaces.WORLD).translation
    lh = X.get_bone_pose(ref, bn("LeftHand"), unreal.AnimPoseSpaces.WORLD).translation
    log("skeleton: %d bones, root %s, Hips at (%.2f, %.2f, %.2f) cm, LeftHand x %.1f" % (len(names), names[0], hips.x, hips.y, hips.z, lh.x))
    for c in CHARACTERS:
        m = unreal.load_asset("%s/Characters/%s/SK_%s" % (PKG, c, c))
        if m is None:
            continue
        b = m.get_bounds()
        lo, hi = b.origin - b.box_extent, b.origin + b.box_extent
        mods = EAL.list_assets("%s/Characters/%s/Armor" % (PKG, c), recursive=False)
        log("%-20s z %.2f..%.2f  x %.1f..%.1f  y %.1f..%.1f  modules %d" % (c, lo.z, hi.z, lo.x, hi.x, lo.y, hi.y, len(mods)))


STEPS = {"models": models, "abp_asset": abp_asset, "save_all": save_all, "textures": textures, "weapons": weapons, "materials": materials, "clips": clips, "montages": montages, "measure": measure, "measure_clips": measure_clips, "sockets": sockets, "weapon_blueprints": weapon_blueprints,
         "character": character, "character_children": character_children,
         "demo_vars": demo_vars, "demo_data": demo_data, "demo_actors": demo_actors, "eyes": eyes, "showreel_director": showreel_director, "showreel_bow": showreel_bow}

if __name__ == "__main__":
    args = sys.argv[1:] or ["all"]
    steps = list(STEPS) if args == ["all"] else args
    for s in steps:
        head, _, rest = s.partition(":")
        log("== step", s)
        STEPS[head](*( [rest.split(",")] if rest else []))
