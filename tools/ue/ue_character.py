"""BP_UndeadSkeleton (the character) and one child per class, BP_<Character> (imported by ue_build.py).

Unity -> Unreal:
  PF_<Character> prefab            -> BP_<Character>, child of BP_UndeadSkeleton (Character)
  armour map (CharacterPrefabBuilder.ArmorMap) -> DefaultModules on each child: the character's own modules
  ArmorModule.Attach (bones by name) -> a SkeletalMeshComponent per module with SetLeaderPoseComponent(Mesh)
                                        (one shared skeleton, so any module follows any body)
  SkeletonWeapon.loadouts          -> LoadoutNames / LoadoutRight / LoadoutLeft (weapon Blueprint classes)
  hand slots                       -> the RightHandSlot / LeftHandSlot sockets on every body (ue_weapons.py)
  Animator + AC_Skeleton           -> ABP_UndeadSkeleton (build_abp.py)
The graphs (construction script, WearModule, EquipLoadout, PlayLoop, PlayAction...) are written by
tools/ue/build_character.py through the MCP BlueprintTools; this module owns the variables and the defaults.
"""
import unreal
from ue_common import PKG, CHARACTERS, EAL, log

BP = PKG + "/Blueprints/BP_UndeadSkeleton"
ABP_CLASS = PKG + "/Blueprints/ABP_UndeadSkeleton.ABP_UndeadSkeleton_C"
L = unreal.BlueprintEditorLibrary
CAT = "Undead Legion"

# Unity's LoadoutTable (CharacterPrefabBuilder.cs), right hand first
LOADOUTS = [
    ("Sword + shield", "H1Sword", "H1HeaterShield"),
    ("Sword", "H1Sword", None),
    ("Axe + round shield", "H1Axe", "H1RoundShield"),
    ("Mace", "H1Mace", None),
    ("Dagger", "H1Dagger", None),
    ("Two daggers", "H1Dagger", "H1Dagger"),
    ("Longsword (2H)", "H2Longsword", None),
    ("Battle axe (2H)", "H2Axe", None),
    ("Recurve bow", "Arrow", "H2Recurvebow"),
    ("Staff", "H2MagicStuff", None),
    ("Wand", "H1Wand", None),
]
# each character's usual weapon in the demo (Unity: the showreel's / the demo's first pick)
START_LOADOUT = {"SkeletonKnight": "Sword + shield", "SkeletonWarrior": "Axe + round shield", "SkeletonArcher": "Recurve bow",
                 "SkeletonAssassin": "Two daggers", "SkeletonMage": "Staff", "SkeletonNecromancer": "Staff"}
DISPLAY = {c: c.replace("Skeleton", "Skeleton ") for c in CHARACTERS}


def _vars(bp):
    have = set(str(n) for n in L.list_member_variable_names(bp))
    arr = L.get_array_type
    spec = [
        ("DefaultModules", arr(L.get_object_reference_type(unreal.SkeletalMesh)), True),
        ("ArmorComponents", arr(L.get_object_reference_type(unreal.SkeletalMeshComponent)), False),
        ("LoadoutNames", arr(L.get_basic_type_by_name("string")), True),
        ("LoadoutRight", arr(L.get_class_reference_type(unreal.Actor)), True),
        ("LoadoutLeft", arr(L.get_class_reference_type(unreal.Actor)), True),
        ("WeaponActors", arr(L.get_object_reference_type(unreal.Actor)), False),
        ("CurrentLoadout", L.get_basic_type_by_name("int"), False),
        ("StartLoadout", L.get_basic_type_by_name("int"), True),
        ("StartClip", L.get_object_reference_type(unreal.AnimSequenceBase), True),
        ("DisplayName", L.get_basic_type_by_name("string"), True),
        ("FingerIdleLeft", L.get_basic_type_by_name("bool"), True),
        ("FingerIdleRight", L.get_basic_type_by_name("bool"), True),
        ("ClipHoldLeft", L.get_basic_type_by_name("bool"), False),
        ("ClipHoldRight", L.get_basic_type_by_name("bool"), False),
        ("FingersSuspended", L.get_basic_type_by_name("bool"), False),
        # showreel / cinematic helper: one-shots played by themselves after BeginPlay (StartActionDelay, then each
        # after the previous one plus StartActionGap); StartHoldLeft = the start idle holds the left hand (grip_hands L)
        ("StartActions", arr(L.get_object_reference_type(unreal.AnimSequenceBase)), True),
        ("StartActionDelay", L.get_basic_type_by_name("real"), True),
        ("StartActionGap", L.get_basic_type_by_name("real"), True),
        ("StartActionIndex", L.get_basic_type_by_name("int"), False),
        ("StartHoldLeft", L.get_basic_type_by_name("bool"), True),
        ("LoopMontage", L.get_object_reference_type(unreal.AnimMontage), False),
        ("ActionMontage", L.get_object_reference_type(unreal.AnimMontage), False),
        ("HasWeaponLeft", L.get_basic_type_by_name("bool"), False),
        ("HasWeaponRight", L.get_basic_type_by_name("bool"), False),
    ]
    for name, t, editable in spec:
        if name not in have:
            L.add_member_variable(bp, name, t)
        L.set_blueprint_variable_category(bp, name, unreal.Text(CAT))
        L.set_blueprint_variable_instance_editable(bp, name, editable)


def base():
    bp = unreal.load_asset(BP)
    if bp is None:
        f = unreal.BlueprintFactory()
        f.set_editor_property("parent_class", unreal.Character)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("BP_UndeadSkeleton", PKG + "/Blueprints", unreal.Blueprint, f)
    _vars(bp)
    L.compile_blueprint(bp)
    cdo = unreal.get_default_object(L.generated_class(bp))
    # the capsule of the Unity prefab (height 1.8, radius 0.35) and the mesh inside it: feet on the capsule bottom,
    # yawed -90 (the SK assets face +Y, the UE mannequin convention; the actor's forward is +X)
    cap = cdo.get_editor_property("capsule_component")
    cap.set_capsule_size(35.0, 90.0)
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("relative_location", unreal.Vector(0, 0, -90))
    mesh.set_editor_property("relative_rotation", unreal.Rotator(roll=0, pitch=0, yaw=-90))
    mesh.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT)
    mesh.set_editor_property("anim_class", unreal.load_object(None, ABP_CLASS))
    mesh.set_editor_property("skeletal_mesh_asset", unreal.load_asset("%s/Characters/SkeletonKnight/SK_SkeletonKnight" % PKG))
    mesh.set_editor_property("visibility_based_anim_tick_option", unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    wclass = lambda w: unreal.load_object(None, "%s/Weapons/Blueprints/BP_Weapon_%s.BP_Weapon_%s_C" % (PKG, w, w)) if w else None
    # a spawned Character has NO controller by default (AutoPossessAI = PlacedInWorld), and CharacterMovement does not
    # run without one: movement mode stays None and root motion is extracted but never applied (2026-09-30: "skeleton
    # doesn't move when root motion is enabled"). Placed or spawned, it gets an AIController, as an NPC would.
    cdo.set_editor_property("auto_possess_ai", unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
    cdo.set_editor_property("LoadoutNames", [n for n, _, _ in LOADOUTS])
    cdo.set_editor_property("LoadoutRight", [wclass(r) for _, r, _ in LOADOUTS])
    cdo.set_editor_property("LoadoutLeft", [wclass(l) for _, _, l in LOADOUTS])
    cdo.set_editor_property("CurrentLoadout", -1)
    cdo.set_editor_property("StartLoadout", -1)
    cdo.set_editor_property("StartClip", unreal.load_asset(PKG + "/Animations/A_Idle_01"))
    cdo.set_editor_property("StartActionDelay", 0.8)    # the Unity recorder's holdBefore / holdAfter
    cdo.set_editor_property("StartActionGap", 0.9)
    cdo.set_editor_property("FingerIdleLeft", True)
    cdo.set_editor_property("FingerIdleRight", True)
    cdo.set_editor_property("DisplayName", "Undead Skeleton")
    L.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, False)
    log("BP_UndeadSkeleton: %d loadouts" % len(LOADOUTS))
    return bp


def children():
    parent = unreal.load_asset(BP)
    pclass = L.generated_class(parent)
    names = [n for n, _, _ in LOADOUTS]
    for c in CHARACTERS:
        path = "%s/Characters/%s/BP_%s" % (PKG, c, c)
        bp = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
        if bp is None:
            f = unreal.BlueprintFactory()
            f.set_editor_property("parent_class", pclass)
            bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("BP_" + c, "%s/Characters/%s" % (PKG, c), unreal.Blueprint, f)
        L.compile_blueprint(bp)
        cdo = unreal.get_default_object(L.generated_class(bp))
        cdo.get_editor_property("mesh").set_editor_property("skeletal_mesh_asset", unreal.load_asset("%s/Characters/%s/SK_%s" % (PKG, c, c)))
        mods = [unreal.load_asset(a) for a in sorted(EAL.list_assets("%s/Characters/%s/Armor" % (PKG, c), recursive=False))]
        mods = [m for m in mods if isinstance(m, unreal.SkeletalMesh)]
        cdo.set_editor_property("DefaultModules", mods)
        cdo.set_editor_property("DisplayName", DISPLAY[c])
        cdo.set_editor_property("StartLoadout", names.index(START_LOADOUT[c]))
        # inherit the eyes from BP_UndeadSkeleton: a child compiled before a parent variable existed stores the
        # zero value as its own (black eyes, 2026-10-01); reset to the parent's default
        for k in ("EyeColor", "EyesVisible", "StartActionDelay", "StartActionGap"):
            cdo.reset_editor_property(k)
        L.compile_blueprint(bp)
        EAL.save_loaded_asset(bp, False)
        log("BP_%s: %d modules, start loadout %s" % (c, len(mods), START_LOADOUT[c]))
