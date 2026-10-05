"""The dev test map for UE5 mannequin animations on our skeletons (skeletons_ue_epic only, 2026-10-05; runs INSIDE the editor).

    python tools/ue/ue_py.py tools/ue/ue_uetest.py assets    # /Game/Dev/UI/WBP_UETestBrowser (child of WBP_AnimBrowser) +
                                                             # /Game/Dev/Blueprints/BP_UETestShowcase (child of BP_DemoShowcase)
    python tools/ue/build_demo_logic.py uetest              # the child showcase's BeginPlay opens the child browser (system Python, MCP)
    python tools/ue/ue_py.py tools/ue/ue_uetest.py data      # the child browser's class defaults: the pack's sections + the UE sections
    python tools/ue/ue_py.py tools/ue/ue_uetest.py map       # /Game/Dev/Maps/UE_AnimTest, the demo map with the child showcase

Everything lives under /Game/Dev, outside the product folder, so the package never carries it (make_production_ue.py copies
Content/UndeadLegion only) and the shipped BP_DemoShowcase / WBP_AnimBrowser stay untouched. The mannequin clips come from
the template content at /Game/Characters/Mannequins (tools/ue/epic_mannequin_content.py copies it from the engine install); they
play on our skeletons because SK_Mannequin lists SKEL_UndeadLegion as a compatible skeleton (epic_demo_probe.py compat sets it;
the shipped SKEL_UndeadLegion carries no such reference). In the browser the UE sections sit under the pack's own: loops as
loops, one-shots returning to MM_Idle, the deaths held like ours.
"""
import importlib, os, sys
import unreal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ue_common import PKG, EAL, log
import ue_demo_ui as DU
import ue_demo_map as DM
DU = importlib.reload(DU); DM = importlib.reload(DM)      # the editor keeps modules cached across runs

L = unreal.BlueprintEditorLibrary
DEV = "/Game/Dev"
UI, BPS, MAPS = DEV + "/UI", DEV + "/Blueprints", DEV + "/Maps"
MANNY = "/Game/Characters/Mannequins/Anims"
BROWSER, SHOWCASE, MAP = UI + "/WBP_UETestBrowser", BPS + "/BP_UETestShowcase", MAPS + "/UE_AnimTest"

# (section, [(clip, mode)]): mode 0 loop, 1 full-body one-shot (returns to MM_Idle), 8 death (held)
UE_SECTIONS = [
    ("UE unarmed (loop)", [(n, 0) for n in ("MM_Idle", "MF_Unarmed_Walk_Fwd", "MF_Unarmed_Walk_Bwd", "MF_Unarmed_Walk_Left", "MF_Unarmed_Walk_Right",
                                           "MF_Unarmed_Jog_Fwd", "MF_Unarmed_Jog_Bwd", "MF_Unarmed_Jog_Left", "MF_Unarmed_Jog_Right")]),
    ("UE attacks", [(n, 1) for n in ("MM_Attack_01", "MM_Attack_02", "MM_Attack_03", "MM_ChargedAttack")]),
    ("UE jump / dash", [("MM_Jump", 1), ("MM_Fall_Loop", 0), ("MM_Land", 1), ("MM_Dash", 1), ("MM_WallJump", 1)]),
    ("UE hit reactions", [(n, 1) for n in ("MM_HitReact_Front_Lgt_01", "MM_HitReact_Front_Lgt_02", "MM_HitReact_Front_Lgt_03", "MM_HitReact_Front_Lgt_04",
                                          "MM_HitReact_Front_Med_01", "MM_HitReact_Front_Med_02", "MM_HitReact_Front_Hvy_01", "MM_HitReact_Back_Med_01")]),
    ("UE deaths (hold)", [(n, 8) for n in ("MM_Death_Front_01", "MM_Death_Front_02", "MM_Death_Front_03", "MM_Death_Back_01", "MM_Death_Left_01", "MM_Death_Right_01")]),
    ("UE rifle", [("MF_Rifle_Idle_ADS", 0), ("MF_Rifle_Walk_Fwd", 0), ("MF_Rifle_Jog_Fwd", 0), ("MM_Rifle_Fire", 1), ("MM_Rifle_Reload", 1), ("MM_Rifle_Equip", 1)]),
    ("UE pistol", [("MF_Pistol_Idle_ADS", 0), ("MF_Pistol_Walk_Fwd", 0), ("MF_Pistol_Jog_Fwd", 0), ("MM_Pistol_Fire", 1), ("MM_Pistol_Reload", 1), ("MM_Pistol_Equip", 1)]),
]
UE_PATHS = {
    "MM_Idle": "Unarmed/MM_Idle", "MM_Jump": "Unarmed/Jump/MM_Jump", "MM_Fall_Loop": "Unarmed/Jump/MM_Fall_Loop", "MM_Land": "Unarmed/Jump/MM_Land",
    "MM_Dash": "Unarmed/Jump/MM_Dash", "MM_WallJump": "Unarmed/Jump/MM_WallJump",
    "MF_Rifle_Idle_ADS": "Rifle/MF_Rifle_Idle_ADS", "MM_Rifle_Fire": "Rifle/MM_Rifle_Fire", "MM_Rifle_Reload": "Rifle/MM_Rifle_Reload", "MM_Rifle_Equip": "Rifle/MM_Rifle_Equip",
    "MF_Pistol_Idle_ADS": "Pistol/MF_Pistol_Idle_ADS", "MM_Pistol_Fire": "Pistol/MM_Pistol_Fire", "MM_Pistol_Reload": "Pistol/MM_Pistol_Reload", "MM_Pistol_Equip": "Pistol/MM_Pistol_Equip",
}
for _n in ("Walk", "Jog"):
    for _d in ("Fwd", "Bwd", "Left", "Right"):
        UE_PATHS["MF_Unarmed_%s_%s" % (_n, _d)] = "Unarmed/%s/MF_Unarmed_%s_%s" % (_n, _n, _d)
        UE_PATHS["MF_Rifle_%s_%s" % (_n, _d)] = "Rifle/%s/MF_Rifle_%s_%s" % (_n, _n, _d)
        UE_PATHS["MF_Pistol_%s_%s" % (_n, _d)] = "Pistol/%s/MF_Pistol_%s_%s" % (_n, _n, _d)
for _n in ("MM_Attack_01", "MM_Attack_02", "MM_Attack_03", "MM_ChargedAttack"):
    UE_PATHS[_n] = "Unarmed/Attack/" + _n
for _sec, _members in UE_SECTIONS:
    for _n, _ in _members:
        if _n.startswith("MM_HitReact"):
            UE_PATHS[_n] = "Rifle/HitReact/" + _n
        elif _n.startswith("MM_Death"):
            UE_PATHS[_n] = "Death/" + _n
PATHS = {n: MANNY + "/" + p for n, p in UE_PATHS.items()}
RETURNS = dict(DU.RETURN)
RETURNS.update({sec: "MM_Idle" for sec, _ in UE_SECTIONS})
LOCO = {"Locomotion", "UE unarmed (loop)", "UE rifle", "UE pistol"}


def assets():
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    if not EAL.does_asset_exist(BROWSER):
        parent = L.generated_class(unreal.load_asset(DU.UI + "/WBP_AnimBrowser"))
        f = unreal.WidgetBlueprintFactory(); f.set_editor_property("parent_class", parent)
        w = tools.create_asset("WBP_UETestBrowser", UI, unreal.WidgetBlueprint, f)
        EAL.save_loaded_asset(w, False); log("created " + BROWSER)
    if not EAL.does_asset_exist(SHOWCASE):
        parent = L.generated_class(unreal.load_asset(PKG + "/Demo/Blueprints/BP_DemoShowcase"))
        f = unreal.BlueprintFactory(); f.set_editor_property("parent_class", parent)
        b = tools.create_asset("BP_UETestShowcase", BPS, unreal.Blueprint, f)
        EAL.save_loaded_asset(b, False); log("created " + SHOWCASE)
    # a `Browser` variable on the child showcase (set in its BeginPlay) so a probe can press the browser's buttons in PIE
    sc = unreal.load_asset(SHOWCASE); L.compile_blueprint(sc)
    DU._add(sc, [("Browser", "obj", L.generated_class(unreal.load_asset(BROWSER)), False, False)])
    L.compile_blueprint(sc); EAL.save_loaded_asset(sc, False)
    missing = [n for n, p in PATHS.items() if not EAL.does_asset_exist(p)]
    log("mannequin clips missing: %s" % (missing or "none"))


def data():
    DU.demo_data(widget=BROWSER, sections=DU.SECTIONS + UE_SECTIONS, paths=PATHS, returns=RETURNS, loco=LOCO)
    # the mannequin clips carry root motion and the browser starts with it ON: in the test map the figure walked out of frame
    # on the first jog, so this browser starts in place (the footer toggle still switches it)
    bp = unreal.load_asset(BROWSER); L.compile_blueprint(bp)
    unreal.get_default_object(L.generated_class(bp)).set_editor_property("RootMotionOn", False)
    L.compile_blueprint(bp); EAL.save_loaded_asset(bp, False)


def map():
    DM.demo(path=MAP, showcase=SHOWCASE, label="UETestShowcase")


if __name__ == "__main__":
    for step in (sys.argv[1:] or ["assets", "data", "map"]):
        globals()[step]()
