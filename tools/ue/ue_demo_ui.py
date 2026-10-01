"""Variables and data of the demo widgets (runs inside the editor; imported by ue_build.py, steps demo_vars / demo_data).

The data is the Unity demo's (SkeletonShowcase.Sections, the manifest's layer tags, the section idles), flattened into
parallel arrays on WBP_AnimBrowser's defaults so the graphs stay simple:
  Clips / ClipNames / ClipSections      every button of the ANIMATIONS panel, in the Unity section order
  ClipModes   0 base loop (crossfaded; locomotion keeps its legs under masked clips)
              1 full-body one-shot (DefaultSlot)            2 upper body (UpperBody slot while a locomotion loop plays)
              3 left arm (LeftArm slot ditto)               4 right arm (RightArm slot ditto)
              5 held loop (Block_L_Idle: a toggle, the shield stays up over whatever plays)
              6 twitch toggle (ClipArgs = 1..3)             7 empty-hand finger idle toggle (ClipArgs 0 left, 1 right)
              8 death (holds the last pose 2 s, twitches and finger idles off meanwhile, then the last idle)
              9 additive overlay (Hit_01 / Hit_02: added over whatever plays, nothing changes underneath)
  ClipArgs    for a one-shot: the index of the idle to return to (-1 = the last idle played), else per mode above
  ClipLoco    locomotion loops (masked clips route to their layer over these)
  ClipGrip    the clip holds the LEFT hand on the weapon (Unity's grip_hands: the grip fist on that hand)
"""
import unreal
from ue_common import PKG, CHARACTERS, EAL, log

L = unreal.BlueprintEditorLibrary
UI = PKG + "/Demo/UI"
SECTIONS = [
    ("Idle", [("Idle_01", 0), ("Idle_02", 0), ("Idle_03", 0), ("Idle_1H_Combat", 0)]),
    ("Weapon idles", [("Idle_TwoHanded", 0), ("Idle_Bow", 0), ("Idle_Staff", 0)]),
    ("Locomotion", [(n, 0) for n in ("Walk_Fwd_01", "Walk_Back_01", "Run_Fwd_01", "Strafe_Left_01", "Strafe_Right_01",
                                     "Walk_Fwd_02", "Walk_Back_02", "Run_Fwd_02", "Strafe_Left_02", "Strafe_Right_02")]),
    ("Right arm", [("Attack_R_Stab", 4), ("Attack_R_Slice", 4)]),
    ("Left arm (block = hold)", [("Attack_L_Stab", 3), ("Attack_L_Slice", 3), ("Block_L_Idle", 5)]),
    ("Two-handed", [("Attack_2H_01", 1), ("Attack_2H_02", 1)]),
    ("Bow", [("Shoot_01", 2)]),
    ("Magic", [("Cast_Wand_01", 2), ("Cast_Wand_02", 2), ("Cast_Staff_01", 1)]),
    ("Specials", [("Taunt_01", 1), ("Taunt_02", 1), ("Taunt_03", 1), ("Rally", 2), ("Cutthroat", 1), ("Summon", 1), ("AOE_Cast", 1)]),
    ("Reactions", [("Hit_01", 9), ("Hit_02", 9), ("Stagger_01", 1), ("Stagger_02", 1)]),   # hits: additive overlays
    ("Death", [("Death_01", 8), ("Death_02", 8), ("Death_03", 8), ("Death_04", 8)]),
    ("Twitch (additive, toggle)", [("Twitch_01", 6), ("Twitch_02", 6), ("Twitch_03", 6)]),
    ("Hand idle (empty hand, toggle)", [("Hand_Idle_L", 7), ("Hand_Idle_R", 7)]),
]
RETURN = {"Right arm": "Idle_1H_Combat", "Left arm (block = hold)": "Idle_1H_Combat", "Two-handed": "Idle_TwoHanded",
          "Bow": "Idle_Bow", "Magic": "Idle_Staff"}                 # Unity: each section's idlePreference
GRIP_L = {"Idle_TwoHanded", "Attack_2H_01", "Attack_2H_02", "Cast_Staff_01"}   # manifest grip_hands "L"


def _t(kind, cls=None):
    return {"int": L.get_basic_type_by_name("int"), "bool": L.get_basic_type_by_name("bool"),
            # "float" silently maps to an INT pin type; the Blueprint float type is "real" (double)
            "float": L.get_basic_type_by_name("real"), "string": L.get_basic_type_by_name("string"),
            "transform": L.get_struct_type(unreal.Transform.static_struct()),
            "obj": L.get_object_reference_type(cls) if cls else None, "class": L.get_class_reference_type(cls) if cls else None}[kind]


def _add(bp, spec):
    have = set(str(n) for n in L.list_member_variable_names(bp))
    for name, kind, cls, array, editable in spec:
        if name in have:
            continue
        t = _t(kind, cls)
        L.add_member_variable(bp, name, L.get_array_type(t) if array else t)
        L.set_blueprint_variable_category(bp, name, unreal.Text("Demo"))
        L.set_blueprint_variable_instance_editable(bp, name, editable)


def demo_vars():
    char = L.generated_class(unreal.load_asset(PKG + "/Blueprints/BP_UndeadSkeleton"))
    browser_bp = unreal.load_asset(UI + "/WBP_AnimBrowser")
    button_bp = unreal.load_asset(UI + "/WBP_DemoButton")
    L.compile_blueprint(browser_bp)
    L.compile_blueprint(button_bp)
    button = L.generated_class(button_bp)
    _add(button_bp, [("Browser", "obj", L.generated_class(browser_bp), False, False), ("Kind", "int", None, False, False),
                     ("Index", "int", None, False, False)])
    _add(browser_bp, [
        ("CharacterClasses", "class", char, True, True), ("CharacterNames", "string", None, True, True),
        ("Clips", "obj", unreal.AnimSequenceBase, True, True), ("ClipNames", "string", None, True, True),
        ("ClipModes", "int", None, True, True), ("ClipArgs", "int", None, True, True), ("ClipSections", "int", None, True, True),
        ("ClipLoco", "bool", None, True, True), ("ClipGrip", "bool", None, True, True), ("SectionNames", "string", None, True, True),
        ("AllModules", "obj", unreal.SkeletalMesh, True, True), ("AllModuleOwner", "int", None, True, True),
        ("AllModuleNames", "string", None, True, True), ("LoadoutNames", "string", None, True, True),
        ("SpawnTransform", "transform", None, False, True),
        ("Current", "obj", char, False, False), ("CurrentChar", "int", None, False, False),
        ("CharButtons", "obj", button, True, False), ("ClipButtons", "obj", button, True, False),
        ("ModuleButtons", "obj", button, True, False), ("ModuleButtonMesh", "obj", unreal.SkeletalMesh, True, False),
        ("WeaponButtons", "obj", button, True, False), ("FooterButtons", "obj", button, True, False),
        ("CurrentClip", "int", None, False, False), ("LastIdle", "int", None, False, False), ("BaseLoco", "bool", None, False, False),
        ("RootMotionOn", "bool", None, False, True), ("TurntableOn", "bool", None, False, True), ("EyesOn", "bool", None, False, True),
        ("TwitchOn", "bool", None, True, False), ("BlockHeld", "bool", None, False, False),
        ("ActionClip", "int", None, False, False), ("ActionEnd", "float", None, False, False),
        ("DeathPauseAt", "float", None, False, False), ("DeathResumeAt", "float", None, False, False),
    ])
    for b in (button_bp, browser_bp):
        L.compile_blueprint(b)
        EAL.save_loaded_asset(b, False)
    log("demo widget variables")


def demo_data():
    browser_bp = unreal.load_asset(UI + "/WBP_AnimBrowser")
    L.compile_blueprint(browser_bp)
    cdo = unreal.get_default_object(L.generated_class(browser_bp))
    names, clips, modes, args, secs, loco, grip = [], [], [], [], [], [], []
    order = [n for _, m in SECTIONS for n, _ in m]
    for si, (sec, members) in enumerate(SECTIONS):
        for n, mode in members:
            a = unreal.load_asset(PKG + "/Animations/A_" + n) if EAL.does_asset_exist(PKG + "/Animations/A_" + n) else None
            if a is None:
                log("!! no A_%s, skipped" % n)
                continue
            names.append(n); clips.append(a); modes.append(mode); secs.append(si)
            loco.append(sec == "Locomotion"); grip.append(n in GRIP_L)
            if mode in (1, 2, 3, 4):
                args.append(order.index(RETURN[sec]) if sec in RETURN else -1)
            elif mode == 6:
                args.append(int(n[-2:]))
            elif mode == 7:
                args.append(0 if n.endswith("_L") else 1)
            else:
                args.append(-1)
    # indices in ClipArgs point into the FINAL list (skipped clips shift it): remap by name
    for i, m in enumerate(modes):
        if m in (1, 2, 3, 4) and args[i] >= 0:
            args[i] = names.index(order[args[i]])
    mods, owner, mnames = [], [], []
    for ci, c in enumerate(CHARACTERS):
        for p in sorted(EAL.list_assets("%s/Characters/%s/Armor" % (PKG, c), recursive=False)):
            m = unreal.load_asset(p)
            if isinstance(m, unreal.SkeletalMesh):
                mods.append(m); owner.append(ci); mnames.append(m.get_name().replace("SK_%s_" % c, ""))
    classes = [L.generated_class(unreal.load_asset("%s/Characters/%s/BP_%s" % (PKG, c, c))) for c in CHARACTERS]
    char_cdo = unreal.get_default_object(L.generated_class(unreal.load_asset(PKG + "/Blueprints/BP_UndeadSkeleton")))
    for k, v in (("CharacterClasses", classes), ("CharacterNames", [c.replace("Skeleton", "") for c in CHARACTERS]),
                 ("Clips", clips), ("ClipNames", names), ("ClipModes", modes), ("ClipArgs", args), ("ClipSections", secs),
                 ("ClipLoco", loco), ("ClipGrip", grip), ("SectionNames", [s for s, _ in SECTIONS]),
                 ("AllModules", mods), ("AllModuleOwner", owner), ("AllModuleNames", mnames),
                 ("LoadoutNames", list(char_cdo.get_editor_property("LoadoutNames"))),
                 ("SpawnTransform", unreal.Transform(unreal.Vector(0, 0, 92), unreal.Rotator(roll=0, pitch=0, yaw=180))),
                 ("RootMotionOn", True), ("TurntableOn", False), ("EyesOn", True), ("TwitchOn", [True, True, True]),
                 ("CurrentClip", 0), ("LastIdle", 0), ("ActionClip", -1)):
        cdo.set_editor_property(k, v)
    L.compile_blueprint(browser_bp)
    EAL.save_loaded_asset(browser_bp, False)
    log("demo data: %d clips in %d sections, %d modules, %d characters" % (len(clips), len(SECTIONS), len(mods), len(classes)))


def _bp(path, parent):
    bp = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
    if bp is None:
        name, folder = path.split("/")[-1], path.rsplit("/", 1)[0]
        f = unreal.BlueprintFactory()
        f.set_editor_property("parent_class", parent)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Blueprint, f)
    return bp


def _component(bp, cls, name, parent_name=None):
    """Add a component to a Blueprint's construction script unless one of that name exists."""
    ss = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = ss.k2_gather_subobject_data_for_blueprint(bp)
    by_name = {}
    for h in handles:
        d = lib.get_data(h)
        by_name[str(lib.get_variable_name(d))] = h
    if name in by_name:
        return lib.get_object_for_blueprint(lib.get_data(by_name[name]), bp)
    parent = by_name.get(parent_name, handles[0]) if parent_name else handles[0]
    h, fail = ss.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=parent, new_class=cls, blueprint_context=bp))
    ss.rename_subobject(h, unreal.Text(name))
    return lib.get_object_for_blueprint(lib.get_data(h), bp)


def demo_actors():
    """BP_OrbitPawn (drag to orbit, wheel to zoom: Unity's DemoTurntable), BP_DemoGameMode (that pawn), BP_DemoShowcase
    (puts WBP_AnimBrowser on screen: Unity's SkeletonShowcase host). Graphs: build_demo_logic.py pawn|showcase."""
    D = PKG + "/Demo/Blueprints"
    pawn = _bp(D + "/BP_OrbitPawn", unreal.Pawn)
    root = _component(pawn, unreal.SceneComponent, "Pivot")
    arm = _component(pawn, unreal.SpringArmComponent, "Arm", "Pivot")
    arm.set_editor_property("do_collision_test", False)
    arm.set_editor_property("target_arm_length", 420.0)
    arm.set_editor_property("enable_camera_lag", True)
    arm.set_editor_property("camera_lag_speed", 12.0)
    cam = _component(pawn, unreal.CameraComponent, "Camera", "Arm")
    cam.set_editor_property("field_of_view", 40.0)
    _add(pawn, [("Yaw", "float", None, False, True), ("Pitch", "float", None, False, True), ("Distance", "float", None, False, True),
                ("Target", "obj", unreal.Actor, False, False), ("PivotHeight", "float", None, False, True)])
    L.compile_blueprint(pawn)
    cdo = unreal.get_default_object(L.generated_class(pawn))
    for k, v in (("Yaw", -25.0), ("Pitch", -10.0), ("Distance", 420.0), ("PivotHeight", 5.0)):
        cdo.set_editor_property(k, v)
    EAL.save_loaded_asset(pawn, False)
    gm = _bp(D + "/BP_DemoGameMode", unreal.GameModeBase)
    L.compile_blueprint(gm)
    unreal.get_default_object(L.generated_class(gm)).set_editor_property("default_pawn_class", L.generated_class(pawn))
    L.compile_blueprint(gm)
    EAL.save_loaded_asset(gm, False)
    show = _bp(D + "/BP_DemoShowcase", unreal.Actor)
    L.compile_blueprint(show)
    EAL.save_loaded_asset(show, False)
    log("demo actors: BP_OrbitPawn, BP_DemoGameMode, BP_DemoShowcase")
