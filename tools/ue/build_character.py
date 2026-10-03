"""Write BP_UndeadSkeleton's graphs through the Unreal MCP BlueprintTools (system Python, editor running).

    python tools/ue/build_character.py [FunctionName ...]

The Blueprint and its variables come from tools/ue/ue_character.py (run `ue_build.py character` first). The graphs are
the Unity runtime scripts, re-cut:
  SkeletonModules      -> ApplyDefaultModules (construction script), WearModule, RemoveModule, IsModuleWorn,
                          SetDefaultModulesWorn
  SkeletonWeapon       -> EquipLoadout, SpawnWeapon, UpdateHands (grip fist on a hand that holds something or that a
                          clip holds - Unity's grip_hands -, the relaxed finger idle on an empty hand)
  Animator calls       -> PlayLoop (the base loop, crossfaded), PlayAction (a one-shot in a montage slot),
                          StopActions, SetHeldBlock, SetTwitch, SetRootMotion
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import bp, ref

BPP = "/Game/UndeadLegion/Blueprints/BP_UndeadSkeleton"
B = ref(BPP)
V = "Variables|UndeadLegion|"
SEQ = "/Script/Engine.AnimSequenceBase"

# name -> ([(param, type, is_input)], dsl)   type: basic name or an object class path
FUNCS = {
    "AddModuleComponent": ([("Module", "/Script/Engine.SkeletalMesh", True)], """
(fn AddModuleComponent (Module)
  (bind body (Variables|Character|GetMesh))
  (bind sk (Game|AddComponentbyClass :Class "/Script/Engine.SkeletalMeshComponent"))
  (Components|SkeletalMesh|SetSkeletalMeshAsset :self sk :NewMesh Module)
  (Transformation|AttachComponentToComponent :self sk :Parent body :SocketName "None"
     :LocationRule "SnapToTarget" :RotationRule "SnapToTarget" :ScaleRule "SnapToTarget" :bWeldSimulatedBodies false)
  (Components|SkinnedMesh|SetLeaderPoseComponent :self sk :NewLeaderBoneComponent body)
  (Utilities|Array|Add :TargetArray (%(V)sGetArmorComponents) :NewItem sk))
"""),
    "ApplyDefaultModules": ([], """
(fn ApplyDefaultModules ()
  (for c (%(V)sGetArmorComponents)
    (Components|DestroyComponent :self c))
  (Utilities|Array|Clear :TargetArray (%(V)sGetArmorComponents))
  (for m (%(V)sGetDefaultModules)
    (CallFunction|AddModuleComponent :Module m))
  (CallFunction|ApplyEyes))
"""),
    "WearModule": ([("Module", "/Script/Engine.SkeletalMesh", True)], """
(fn WearModule (Module)
  (for c (%(V)sGetArmorComponents)
    (if (== (Components|SkeletalMesh|GetSkeletalMeshAsset :self c) Module)
      (Rendering|SetVisibility :self c :bNewVisibility true :bPropagateToChildren false)
      (return)))
  (CallFunction|AddModuleComponent :Module Module))
"""),
    "RemoveModule": ([("Module", "/Script/Engine.SkeletalMesh", True)], """
(fn RemoveModule (Module)
  (for c (%(V)sGetArmorComponents)
    (if (== (Components|SkeletalMesh|GetSkeletalMeshAsset :self c) Module)
      (Rendering|SetVisibility :self c :bNewVisibility false :bPropagateToChildren false))))
"""),
    "IsModuleWorn": ([("Module", "/Script/Engine.SkeletalMesh", True), ("Worn", "bool", False)], """
(fn IsModuleWorn (Module)
  (for c (%(V)sGetArmorComponents)
    (if (and (== (Components|SkeletalMesh|GetSkeletalMeshAsset :self c) Module) (Rendering|IsVisible :self c))
      (return true)))
  (return false))
"""),
    "SetDefaultModulesWorn": ([("Worn", "bool", True)], """
(fn SetDefaultModulesWorn (Worn)
  (for m (%(V)sGetDefaultModules)
    (if Worn
      (CallFunction|WearModule :Module m)
      (else
        (CallFunction|RemoveModule :Module m)))))
"""),
    "SpawnWeapon": ([("Index", "int", True), ("Left", "bool", True)], """
(fn SpawnWeapon (Index Left)
  (bind cls (select Left (Utilities|Array|Get(acopy) (%(V)sGetLoadoutLeft) Index) (Utilities|Array|Get(acopy) (%(V)sGetLoadoutRight) Index)))
  (if (Utilities|IsValidClass cls)
    (bind a (Game|SpawnActorfromClass :Class cls :SpawnTransform (Transformation|GetActorTransform)
              :CollisionHandlingOverride "AlwaysSpawn"))
    (Transformation|AttachActorToComponent :self a :Parent (Variables|Character|GetMesh)
       :SocketName (select Left "LeftHandSlot" "RightHandSlot")
       :LocationRule "SnapToTarget" :RotationRule "SnapToTarget" :ScaleRule "SnapToTarget" :bWeldSimulatedBodies false)
    (Utilities|Array|Add :TargetArray (%(V)sGetWeaponActors) :NewItem a)
    (if Left
      (%(V)sSetHasWeaponLeft true)
      (else
        (%(V)sSetHasWeaponRight true)))))
"""),
    "EquipLoadout": ([("Index", "int", True)], """
(fn EquipLoadout (Index)
  (for a (%(V)sGetWeaponActors)
    (Actor|DestroyActor :self a))
  (Utilities|Array|Clear :TargetArray (%(V)sGetWeaponActors))
  (%(V)sSetHasWeaponLeft false)
  (%(V)sSetHasWeaponRight false)
  (%(V)sSetCurrentLoadout Index)
  (if (Utilities|Array|IsValidIndex :TargetArray (%(V)sGetLoadoutRight) :IndexToTest Index)
    (CallFunction|SpawnWeapon :Index Index :Left false)
    (CallFunction|SpawnWeapon :Index Index :Left true))
  (CallFunction|UpdateHands))
"""),
    "UpdateHands": ([], """
(fn UpdateHands ()
  (bind hl (or (%(V)sGetHasWeaponLeft) (%(V)sGetClipHoldLeft)))
  (bind hr (or (%(V)sGetHasWeaponRight) (%(V)sGetClipHoldRight)))
  (bind idle (not (%(V)sGetFingersSuspended)))
  (bind abp (Utilities|Casting|CastToABP_UndeadSkeleton :Object (Components|SkeletalMesh|GetAnimInstance :self (Variables|Character|GetMesh)))
    (:then
      (Class|ABPUndeadSkeleton|SetHandTargets :self abp
         :GripL (select hl 1.0 0.0) :GripR (select hr 1.0 0.0)
         :FingerL (select (or hl (and idle (%(V)sGetFingerIdleLeft))) 1.0 0.0)
         :FingerR (select (or hr (and idle (%(V)sGetFingerIdleRight))) 1.0 0.0)))
    (:CastFailed)))
"""),
    "PlayLoop": ([("Clip", SEQ, True)], """
(fn PlayLoop (Clip)
  ; a LOOPING montage in the Base slot, so its root motion reaches CharacterMovement; the old loop blends out
  ; (StopSlotAnimation on Base only) while the new one blends in, and bStopAllMontages false keeps the one-shots
  (bind anim (Components|SkeletalMesh|GetAnimInstance :self (Variables|Character|GetMesh)))
  (Animation|Montage|StopSlotAnimation :self anim :InBlendOutTime 0.2 :SlotNodeName "Base")
  (bind m (Animation|CreateSlotAnimationasDynamicMontagewithBlendSettings :Asset Clip :SlotNodeName "Base"
             :BlendInSettings (Utilities|Struct|MakeMontageBlendSettings :Blend (Utilities|Struct|MakeAlphaBlendArgs :BlendTime 0.2)) :BlendOutSettings (Utilities|Struct|MakeMontageBlendSettings :Blend (Utilities|Struct|MakeAlphaBlendArgs :BlendTime 0.2)) :InPlayRate 1.0 :LoopCount 100000))
  (Animation|Montage|MontagePlay :self anim :MontageToPlay m :InPlayRate 1.0 :bStopAllMontages false)
  (%(V)sSetLoopMontage m))
"""),
    "PlayAction": ([("Clip", SEQ, True), ("Slot", "name", True), ("BlendIn", "float", True), ("BlendOut", "float", True),
                    ("Rate", "float", True), ("Length", "float", False)], """
(fn PlayAction (Clip Slot BlendIn BlendOut Rate)
  ; the previous one-shot stops in the action slots only; the loop montage in Base keeps playing under it
  (CallFunction|StopActions :BlendOut BlendOut)
  (bind anim (Components|SkeletalMesh|GetAnimInstance :self (Variables|Character|GetMesh)))
  (bind m (Animation|CreateSlotAnimationasDynamicMontagewithBlendSettings :Asset Clip :SlotNodeName Slot
             :BlendInSettings (Utilities|Struct|MakeMontageBlendSettings :Blend (Utilities|Struct|MakeAlphaBlendArgs :BlendTime BlendIn)) :BlendOutSettings (Utilities|Struct|MakeMontageBlendSettings :Blend (Utilities|Struct|MakeAlphaBlendArgs :BlendTime BlendOut)) :InPlayRate Rate :LoopCount 1))
  (Animation|Montage|MontagePlay :self anim :MontageToPlay m :InPlayRate Rate :bStopAllMontages false)
  (%(V)sSetActionMontage m)
  (return (/ (Animation|GetPlayLength :self Clip) Rate)))
"""),
    "StopActions": ([("BlendOut", "float", True)], """
(fn StopActions (BlendOut)
  (bind anim (Components|SkeletalMesh|GetAnimInstance :self (Variables|Character|GetMesh)))
  (Animation|Montage|StopSlotAnimation :self anim :InBlendOutTime BlendOut :SlotNodeName "DefaultSlot")
  (Animation|Montage|StopSlotAnimation :self anim :InBlendOutTime BlendOut :SlotNodeName "UpperBody")
  (Animation|Montage|StopSlotAnimation :self anim :InBlendOutTime BlendOut :SlotNodeName "LeftArm")
  (Animation|Montage|StopSlotAnimation :self anim :InBlendOutTime BlendOut :SlotNodeName "RightArm"))
"""),
    "SetHeldBlock": ([("Held", "bool", True)], """
(fn SetHeldBlock (Held)
  (bind abp (Utilities|Casting|CastToABP_UndeadSkeleton :Object (Components|SkeletalMesh|GetAnimInstance :self (Variables|Character|GetMesh)))
    (:then
      (Class|ABPUndeadSkeleton|SetBlockTarget :self abp :Target (select Held 1.0 0.0)))
    (:CastFailed)))
"""),
    "SetTwitch": ([("Index", "int", True), ("Weight", "float", True)], """
(fn SetTwitch (Index Weight)
  (bind abp (Utilities|Casting|CastToABP_UndeadSkeleton :Object (Components|SkeletalMesh|GetAnimInstance :self (Variables|Character|GetMesh)))
    (:then
      (Class|ABPUndeadSkeleton|SetTwitchWeight :self abp :Index Index :Weight Weight))
    (:CastFailed)))
"""),
    "SetRootMotion": ([("On", "bool", True)], """
(fn SetRootMotion (On)
  (bind anim (Components|SkeletalMesh|GetAnimInstance :self (Variables|Character|GetMesh)))
  (if On
    (Animation|RootMotion|SetRootMotionMode :self anim :Value "RootMotionFromEverything")
    (else
      (Animation|RootMotion|SetRootMotionMode :self anim :Value "IgnoreRootMotion"))))
"""),
    "SetClipHold": ([("Left", "bool", True), ("Right", "bool", True)], """
(fn SetClipHold (Left Right)
  (%(V)sSetClipHoldLeft Left)
  (%(V)sSetClipHoldRight Right)
  (CallFunction|UpdateHands))
"""),
    "SetFingersSuspended": ([("Suspended", "bool", True)], """
(fn SetFingersSuspended (Suspended)
  (%(V)sSetFingersSuspended Suspended)
  (CallFunction|UpdateHands))
"""),
    "SetFingerIdle": ([("Left", "bool", True), ("On", "bool", True)], """
(fn SetFingerIdle (Left On)
  (if Left
    (%(V)sSetFingerIdleLeft On)
    (else
      (%(V)sSetFingerIdleRight On)))
  (CallFunction|UpdateHands))
"""),
    "GetFingerIdle": ([("Left", "bool", True), ("On", "bool", False)], """
(fn GetFingerIdle (Left)
  (return (select Left (%(V)sGetFingerIdleLeft) (%(V)sGetFingerIdleRight))))
"""),
    "GetLoadout": ([("Index", "int", False)], """
(fn GetLoadout ()
  (return (%(V)sGetCurrentLoadout)))
"""),
    "PauseActions": ([], """
(fn PauseActions ()
  (Animation|Montage|MontagePause :self (Components|SkeletalMesh|GetAnimInstance :self (Variables|Character|GetMesh))
     :Montage (%(V)sGetActionMontage)))
"""),
    "ApplyEyes": ([], """
(fn ApplyEyes ()
  ; Unity SkeletonEyes: two glowing spheres on the body's EyeL / EyeR sockets (seated per skull by ue_eyes.py); the
  ; relative scale (0.018 of the 1 m engine sphere) is kept
  (bind body (Variables|Character|GetMesh))
  (Transformation|AttachComponentToComponent :self (Variables|Default|GetEyeL) :Parent body :SocketName "EyeL"
     :LocationRule "SnapToTarget" :RotationRule "SnapToTarget" :ScaleRule "KeepRelative" :bWeldSimulatedBodies false)
  (Transformation|AttachComponentToComponent :self (Variables|Default|GetEyeR) :Parent body :SocketName "EyeR"
     :LocationRule "SnapToTarget" :RotationRule "SnapToTarget" :ScaleRule "KeepRelative" :bWeldSimulatedBodies false)
  (CallFunction|ShowEyes :On (%(V)sGetEyesVisible))
  (CallFunction|TintEyes :Color (%(V)sGetEyeColor)))
"""),
    "ShowEyes": ([("On", "bool", True)], """
(fn ShowEyes (On)
  (%(V)sSetEyesVisible On)
  (Rendering|SetVisibility :self (Variables|Default|GetEyeL) :bNewVisibility On :bPropagateToChildren false)
  (Rendering|SetVisibility :self (Variables|Default|GetEyeR) :bNewVisibility On :bPropagateToChildren false))
"""),
    "TintEyes": ([("Color", "LinearColor", True)], """
(fn TintEyes (Color)
  ; HDR colour (Unity default (5, 0.2, 0.1)): above 1 it blooms; a team colour for armies
  (%(V)sSetEyeColor Color)
  (Rendering|Material|SetColorParameterValueonMaterials :self (Variables|Default|GetEyeL) :ParameterName "Color" :ParameterValue Color)
  (Rendering|Material|SetColorParameterValueonMaterials :self (Variables|Default|GetEyeR) :ParameterName "Color" :ParameterValue Color))
"""),
    "PlayOverlay": ([("Clip", SEQ, True), ("Length", "float", False)], """
(fn PlayOverlay (Clip)
  ; an ADDITIVE clip (Hit_01 / Hit_02) in the Hit slot, added over whatever plays (Unity: the additive Hit layer);
  ; nothing else is stopped
  (bind anim (Components|SkeletalMesh|GetAnimInstance :self (Variables|Character|GetMesh)))
  (Animation|Montage|StopSlotAnimation :self anim :InBlendOutTime 0.1 :SlotNodeName "Hit")
  (bind m (Animation|CreateSlotAnimationasDynamicMontagewithBlendSettings :Asset Clip :SlotNodeName "Hit"
             :BlendInSettings (Utilities|Struct|MakeMontageBlendSettings :Blend (Utilities|Struct|MakeAlphaBlendArgs :BlendTime 0.05))
             :BlendOutSettings (Utilities|Struct|MakeMontageBlendSettings :Blend (Utilities|Struct|MakeAlphaBlendArgs :BlendTime 0.15))
             :InPlayRate 1.0 :LoopCount 1))
  (Animation|Montage|MontagePlay :self anim :MontageToPlay m :InPlayRate 1.0 :bStopAllMontages false)
  (return (Animation|GetPlayLength :self Clip)))
"""),
    "NextStartAction": ([], """
(fn NextStartAction ()
  ; plays StartActions[StartActionIndex] full body, then schedules itself after that clip + StartActionGap
  (bind i (%(V)sGetStartActionIndex))
  (if (Utilities|Array|IsValidIndex :TargetArray (%(V)sGetStartActions) :IndexToTest i)
    (bind len (CallFunction|PlayAction :Clip (Utilities|Array|Get(acopy) (%(V)sGetStartActions) i) :Slot "DefaultSlot"
                :BlendIn 0.15 :BlendOut 0.25 :Rate 1.0))
    (Development|PrintString :InString (Utilities|String|Append "StartAction " (Utilities|String|ToString(Integer) i))
       :bPrintToScreen false :bPrintToLog true)
    (%(V)sSetStartActionIndex (+ i 1))
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "NextStartAction"
       :Time (+ len (%(V)sGetStartActionGap)) :bLooping false)))
"""),
}
ORDER = ["ShowEyes", "TintEyes", "ApplyEyes", "AddModuleComponent", "ApplyDefaultModules", "WearModule", "RemoveModule", "IsModuleWorn", "SetDefaultModulesWorn",
         "UpdateHands", "SpawnWeapon", "EquipLoadout", "PlayLoop", "PlayAction", "StopActions", "SetHeldBlock", "SetTwitch",
         "SetRootMotion", "SetClipHold", "SetFingersSuspended", "SetFingerIdle", "GetFingerIdle", "GetLoadout", "PauseActions", "PlayOverlay", "NextStartAction"]

EVENTS = """
(event EventBeginPlay
  (CallFunction|EquipLoadout :Index (%(V)sGetStartLoadout))
  (CallFunction|PlayLoop :Clip (%(V)sGetStartClip))
  (CallFunction|SetClipHold :Left (%(V)sGetStartHoldLeft) :Right false)
  (%(V)sSetStartActionIndex 0)
  (if (> (Utilities|Array|Length :TargetArray (%(V)sGetStartActions)) 0)
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "NextStartAction"
       :Time (%(V)sGetStartActionDelay) :bLooping false)))

(event EventEndPlay (EndPlayReason)
  (for a (%(V)sGetWeaponActors)
    (Actor|DestroyActor :self a))
  (Utilities|Array|Clear :TargetArray (%(V)sGetWeaponActors)))
"""


def graph(name):
    return {"refPath": BPP + ".BP_UndeadSkeleton:" + name}


def ensure_functions():
    have = [g["refPath"].split(":")[-1] for g in bp("list_graphs", blueprint=B)]
    for fn in ORDER:
        if fn in have:
            continue
        g = bp("add_function_graph", blueprint=B, graph_name=fn)
        for pn, t, inp in FUNCS[fn][0]:
            if t.startswith("/Script"):
                bp("add_object_function_param", graph=g, param_name=pn, object_class={"refPath": t}, input_param=inp)
            else:
                bp("add_function_param", graph=g, param_name=pn, param_type=t, input_param=inp)
        print("function", fn)


def clear(g):
    for n in bp("find_nodes", graph=g, title="") or []:
        p = n["refPath"].split(".")[-1]
        if "FunctionEntry" not in p and "FunctionResult" not in p:
            bp("delete_node", node=n)


def write(name, code):
    g = graph(name)
    clear(g)
    bp("write_graph_dsl", graph=g, code=code % {"V": V})
    print("wrote", name)


if __name__ == "__main__":
    only = sys.argv[1:]
    ensure_functions()
    for fn in ORDER:
        if not only or fn in only:
            write(fn, FUNCS[fn][1])
    if not only or "UserConstructionScript" in only:
        # the DSL treats UserConstructionScript as an event: place the call and wire the exec by hand
        g = graph("UserConstructionScript")
        clear(g)
        entry = bp("find_nodes", graph=g, title="")[0]
        call = bp("create_node", graph=g, type_id="CallFunction|ApplyDefaultModules", pos={"x": 300, "y": 0})
        out = [p["pin_id"] for p in bp("get_node_infos", nodes=[entry])[0]["output_pins"] if p["name"] == "then"][0]
        inp = [p["pin_id"] for p in bp("get_node_infos", nodes=[call])[0]["input_pins"] if p["name"] == "execute"][0]
        bp("connect_pins", output_pin=out, input_pin=inp)
        print("wrote UserConstructionScript")
    if not only or "EventGraph" in only:
        g = graph("EventGraph")
        clear(g)
        bp("write_graph_dsl", graph=g, code=EVENTS % {"V": V})
        print("wrote EventGraph")
    bp("compile_blueprint", blueprint=B, warnings_as_errors=False)
    print("compiled")
