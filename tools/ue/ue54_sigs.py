"""UE 5.4 signatures of every engine node the DSL graphs use (tools/ue/ue54_dsl.py heads), for the T3D generator
(tools/ue/ue54_t3d.py). Checked against the 5.4 engine headers by `python tools/ue/ue54_sigs.py check`.

Types: bool int real name str text | obj:<class path> cls:<class path> struct:<struct path> enum:<enum path>
       (byte enum) | wild; suffix [] = array, & = by reference (an out param of a function is an OUTPUT pin).
"""

E, U, C = "/Script/Engine.", "/Script/UMG.", "/Script/CoreUObject."
VEC, ROT, XF, LC = "struct:" + C + "Vector", "struct:" + C + "Rotator", "struct:" + C + "Transform", "struct:" + C + "LinearColor"
ATT = "enum:" + E + "EAttachmentRule"
HIT = "struct:" + E + "HitResult"

KML, KSL, KSys, GS, KTL = E + "KismetMathLibrary", E + "KismetStringLibrary", E + "KismetSystemLibrary", E + "GameplayStatics", E + "KismetTextLibrary"


def F(cls, fn, pure, ins=(), outs=(), target=None, header=None):
    """A UFunction node. ins: [(name, type[, default])] in parameter order (the DSL's positional order), outs: [(name, type)];
    target: the class of the hidden-or-not self pin (None = a static library function, self hidden)."""
    return {"kind": "call", "cls": cls, "fn": fn, "pure": pure, "ins": [tuple(i) for i in ins], "outs": [tuple(o) for o in outs],
            "target": target, "header": header}


SIGS = {
    # ---------------------------------------------------------------------------------------------- actors / components
    "Actor|DestroyActor": F(E + "Actor", "K2_DestroyActor", False, target=E + "Actor"),
    "Actor|GetComponentbyClass": F(E + "Actor", "GetComponentByClass", True, [("ComponentClass", "cls:" + E + "ActorComponent")],
                                   [("ReturnValue", "obj:" + E + "ActorComponent")], target=E + "Actor"),
    "Components|DestroyComponent": F(E + "ActorComponent", "K2_DestroyComponent", False, [("Object", "obj:" + C + "Object")],
                                     target=E + "ActorComponent"),
    "Components|GetOwner": F(E + "ActorComponent", "GetOwner", True, outs=[("ReturnValue", "obj:" + E + "Actor")], target=E + "ActorComponent"),
    "Components|SkeletalMesh|GetAnimInstance": F(E + "SkeletalMeshComponent", "GetAnimInstance", True,
                                                outs=[("ReturnValue", "obj:" + E + "AnimInstance")], target=E + "SkeletalMeshComponent"),
    "Components|SkeletalMesh|GetSkeletalMeshAsset": F(E + "SkeletalMeshComponent", "GetSkeletalMeshAsset", True,
                                                     outs=[("ReturnValue", "obj:" + E + "SkeletalMesh")], target=E + "SkeletalMeshComponent"),
    "Components|SkeletalMesh|SetSkeletalMeshAsset": F(E + "SkeletalMeshComponent", "SetSkeletalMeshAsset", False,
                                                     [("NewMesh", "obj:" + E + "SkeletalMesh")], target=E + "SkeletalMeshComponent"),
    "Components|SkinnedMesh|SetLeaderPoseComponent": F(E + "SkinnedMeshComponent", "SetLeaderPoseComponent", False,
                                                      [("NewLeaderBoneComponent", "obj:" + E + "SkinnedMeshComponent"), ("bForceUpdate", "bool", "false"),
                                                       ("bInFollowerShouldTickPose", "bool", "false")], target=E + "SkinnedMeshComponent"),
    "Components|PoseableMesh|ResetBoneTransformbyName": F(E + "PoseableMeshComponent", "ResetBoneTransformByName", False,
                                                         [("BoneName", "name")], target=E + "PoseableMeshComponent"),
    "Components|PoseableMesh|GetBoneTransformbyName": F(E + "PoseableMeshComponent", "GetBoneTransformByName", False,
                                                       [("BoneName", "name"), ("BoneSpace", "enum:" + E + "EBoneSpaces")],
                                                       [("ReturnValue", XF)], target=E + "PoseableMeshComponent"),
    "Components|PoseableMesh|SetBoneTransformbyName": F(E + "PoseableMeshComponent", "SetBoneTransformByName", False,
                                                       [("BoneName", "name"), ("InTransform", XF + "&"), ("BoneSpace", "enum:" + E + "EBoneSpaces")],
                                                       target=E + "PoseableMeshComponent"),
    "Components|PoseableMesh|SetBoneLocationbyName": F(E + "PoseableMeshComponent", "SetBoneLocationByName", False,
                                                      [("BoneName", "name"), ("InLocation", VEC), ("BoneSpace", "enum:" + E + "EBoneSpaces")],
                                                      target=E + "PoseableMeshComponent"),
    "Rendering|SetVisibility": F(E + "SceneComponent", "SetVisibility", False, [("bNewVisibility", "bool"), ("bPropagateToChildren", "bool", "false")],
                                 target=E + "SceneComponent"),
    "Rendering|IsVisible": F(E + "SceneComponent", "IsVisible", True, outs=[("ReturnValue", "bool")], target=E + "SceneComponent"),
    "Rendering|SetActorHiddenInGame": F(E + "Actor", "SetActorHiddenInGame", False, [("bNewHidden", "bool")], target=E + "Actor"),
    # 5.4 has no SetColorParameterValueOnMaterials (5.8 does): the vector version, the colour converted (alpha unused)
    "Rendering|Material|SetVectorParameterValueonMaterials": F(E + "MeshComponent", "SetVectorParameterValueOnMaterials", False,
                                                              [("ParameterName", "name"), ("ParameterValue", VEC)], target=E + "MeshComponent"),
    "Math|Conversions|LinearColorToVector": F(KML, "Conv_LinearColorToVector", True, [("InLinearColor", LC)], [("ReturnValue", VEC)]),
    "Transformation|AttachComponentToComponent": F(E + "SceneComponent", "K2_AttachToComponent", False,
                                                   [("Parent", "obj:" + E + "SceneComponent"), ("SocketName", "name"), ("LocationRule", ATT),
                                                    ("RotationRule", ATT), ("ScaleRule", ATT), ("bWeldSimulatedBodies", "bool")],
                                                   [("ReturnValue", "bool")], target=E + "SceneComponent"),
    "Transformation|AttachActorToComponent": F(E + "Actor", "K2_AttachToComponent", False,
                                               [("Parent", "obj:" + E + "SceneComponent"), ("SocketName", "name"), ("LocationRule", ATT),
                                                ("RotationRule", ATT), ("ScaleRule", ATT), ("bWeldSimulatedBodies", "bool")],
                                               [("ReturnValue", "bool")], target=E + "Actor"),
    "Transformation|GetActorLocation": F(E + "Actor", "K2_GetActorLocation", True, outs=[("ReturnValue", VEC)], target=E + "Actor"),
    "Transformation|GetActorRotation": F(E + "Actor", "K2_GetActorRotation", True, outs=[("ReturnValue", ROT)], target=E + "Actor"),
    "Transformation|GetActorTransform": F(E + "Actor", "GetTransform", True, outs=[("ReturnValue", XF)], target=E + "Actor"),
    "Transformation|GetSocketLocation": F(E + "SceneComponent", "GetSocketLocation", True, [("InSocketName", "name")],
                                          [("ReturnValue", VEC)], target=E + "SceneComponent"),
    "Transformation|SetActorLocation": F(E + "Actor", "K2_SetActorLocation", False,
                                         [("NewLocation", VEC), ("bSweep", "bool"), ("bTeleport", "bool")],
                                         [("SweepHitResult", HIT), ("ReturnValue", "bool")], target=E + "Actor"),
    "Transformation|SetActorTransform": F(E + "Actor", "K2_SetActorTransform", False,
                                          [("NewTransform", XF + "&"), ("bSweep", "bool"), ("bTeleport", "bool")],
                                          [("SweepHitResult", HIT), ("ReturnValue", "bool")], target=E + "Actor"),
    "Transformation|SetWorldRotation": F(E + "SceneComponent", "K2_SetWorldRotation", False,
                                         [("NewRotation", ROT), ("bSweep", "bool"), ("bTeleport", "bool")],
                                         [("SweepHitResult", HIT)], target=E + "SceneComponent"),
    "Transformation|AddActorWorldRotation": F(E + "Actor", "K2_AddActorWorldRotation", False,
                                              [("DeltaRotation", ROT), ("bSweep", "bool"), ("bTeleport", "bool")],
                                              [("SweepHitResult", HIT)], target=E + "Actor"),
    # ---------------------------------------------------------------------------------------------- animation
    "Animation|CreateSlotAnimationasDynamicMontagewithBlendSettings": F(
        E + "AnimMontage", "CreateSlotAnimationAsDynamicMontage_WithBlendSettings", False,
        [("Asset", "obj:" + E + "AnimSequenceBase"), ("SlotNodeName", "name"), ("BlendInSettings", "struct:" + E + "MontageBlendSettings&"),
         ("BlendOutSettings", "struct:" + E + "MontageBlendSettings&"), ("InPlayRate", "real", "1.000000"), ("LoopCount", "int", "1"),
         ("InBlendOutTriggerTime", "real", "-1.000000")],
        [("ReturnValue", "obj:" + E + "AnimMontage")]),
    "Animation|GetPlayLength": F(E + "AnimSequenceBase", "GetPlayLength", True, outs=[("ReturnValue", "real")], target=E + "AnimSequenceBase"),
    "Animation|Montage|MontageGetPosition": F(E + "AnimInstance", "Montage_GetPosition", True, [("Montage", "obj:" + E + "AnimMontage")],
                                              [("ReturnValue", "real")], target=E + "AnimInstance"),
    "Animation|Montage|MontagePause": F(E + "AnimInstance", "Montage_Pause", False, [("Montage", "obj:" + E + "AnimMontage")], target=E + "AnimInstance"),
    "Animation|Montage|MontageResume": F(E + "AnimInstance", "Montage_Resume", False, [("Montage", "obj:" + E + "AnimMontage")], target=E + "AnimInstance"),
    "Animation|Montage|MontagePlay": F(E + "AnimInstance", "Montage_Play", False,
                                       [("MontageToPlay", "obj:" + E + "AnimMontage"), ("InPlayRate", "real", "1.000000"),
                                        ("ReturnValueType", "enum:" + E + "EMontagePlayReturnType", "MontageLength"),
                                        ("InTimeToStartMontageAt", "real", "0.000000"), ("bStopAllMontages", "bool", "true")],
                                       [("ReturnValue", "real")], target=E + "AnimInstance"),
    "Animation|Montage|StopSlotAnimation": F(E + "AnimInstance", "StopSlotAnimation", False,
                                             [("InBlendOutTime", "real", "0.250000"), ("SlotNodeName", "name")], target=E + "AnimInstance"),
    "Animation|RootMotion|SetRootMotionMode": F(E + "AnimInstance", "SetRootMotionMode", False, [("Value", "enum:" + E + "ERootMotionMode")],
                                                target=E + "AnimInstance"),
    # ---------------------------------------------------------------------------------------------- game / input / ui
    "Game|GetPlayerController": F(GS, "GetPlayerController", True, [("PlayerIndex", "int")], [("ReturnValue", "obj:" + E + "PlayerController")]),
    "Game|GetPlayerPawn": F(GS, "GetPlayerPawn", True, [("PlayerIndex", "int")], [("ReturnValue", "obj:" + E + "Pawn")]),
    "Game|Player|GetInputMouseDelta": F(E + "PlayerController", "GetInputMouseDelta", True, outs=[("DeltaX", "real"), ("DeltaY", "real")],
                                        target=E + "PlayerController"),
    "Game|Player|IsInputKeyDown": F(E + "PlayerController", "IsInputKeyDown", True, [("Key", "struct:/Script/InputCore.Key")],
                                    [("ReturnValue", "bool")], target=E + "PlayerController"),
    "Game|Player|WasInputKeyJustPressed": F(E + "PlayerController", "WasInputKeyJustPressed", True, [("Key", "struct:/Script/InputCore.Key")],
                                            [("ReturnValue", "bool")], target=E + "PlayerController"),
    "Input|SetInputModeGameAndUI": F(U + "WidgetBlueprintLibrary", "SetInputMode_GameAndUIEx", False,
                                     [("PlayerController", "obj:" + E + "PlayerController"), ("InWidgetToFocus", "obj:" + U + "Widget"),
                                      ("InMouseLockMode", "enum:/Script/Engine.EMouseLockMode", "DoNotLock"),
                                      ("bHideCursorDuringCapture", "bool", "true"), ("bFlushInput", "bool", "false")]),
    "UserInterface|Viewport|AddtoViewport": F(U + "UserWidget", "AddToViewport", False, [("ZOrder", "int", "0")], target=U + "UserWidget"),
    "Panel|AddChildtoVerticalBox": F(U + "VerticalBox", "AddChildToVerticalBox", False, [("Content", "obj:" + U + "Widget")],
                                     [("ReturnValue", "obj:" + U + "VerticalBoxSlot")], target=U + "VerticalBox"),
    "Widget|AddChildtoHorizontalBox": F(U + "HorizontalBox", "AddChildToHorizontalBox", False, [("Content", "obj:" + U + "Widget")],
                                        [("ReturnValue", "obj:" + U + "HorizontalBoxSlot")], target=U + "HorizontalBox"),
    "Widget|Panel|ClearChildren": F(U + "PanelWidget", "ClearChildren", False, target=U + "PanelWidget"),
    "Widget|SetText(Text)": F(U + "TextBlock", "SetText", False, [("InText", "text")], target=U + "TextBlock"),
    "Class|Button|SetBackgroundColor": F(U + "Button", "SetBackgroundColor", False, [("InBackgroundColor", LC)], target=U + "Button"),
    # ---------------------------------------------------------------------------------------------- math
    "Math|Color|MakeColor": F(KML, "MakeColor", True, [("R", "real"), ("G", "real"), ("B", "real"), ("A", "real", "1.000000")], [("ReturnValue", LC)]),
    "Math|Float|Clamp(Float)": F(KML, "FClamp", True, [("Value", "real"), ("Min", "real"), ("Max", "real")], [("ReturnValue", "real")]),
    "Math|Float|Sqrt": F(KML, "Sqrt", True, [("A", "real")], [("ReturnValue", "real")]),
    "Math|Interpolation|FInterptoConstant": F(KML, "FInterpTo_Constant", True,
                                              [("Current", "real"), ("Target", "real"), ("DeltaTime", "real"), ("InterpSpeed", "real")],
                                              [("ReturnValue", "real")]),
    "Math|Interpolation|VInterpTo": F(KML, "VInterpTo", True, [("Current", VEC), ("Target", VEC), ("DeltaTime", "real"), ("InterpSpeed", "real")],
                                      [("ReturnValue", VEC)]),
    "Math|Rotator|MakeRotator": F(KML, "MakeRotator", True, [("Roll", "real"), ("Pitch", "real"), ("Yaw", "real")], [("ReturnValue", ROT)]),
    "Math|Transform|ComposeTransforms": F(KML, "ComposeTransforms", True, [("A", XF + "&"), ("B", XF + "&")], [("ReturnValue", XF)]),
    "Math|Transform|InverseTransformLocation": F(KML, "InverseTransformLocation", True, [("T", XF + "&"), ("Location", VEC)], [("ReturnValue", VEC)]),
    "Math|Transform|TransformLocation": F(KML, "TransformLocation", True, [("T", XF + "&"), ("Location", VEC)], [("ReturnValue", VEC)]),
    "Math|Transform|MakeTransform": F(KML, "MakeTransform", True, [("Location", VEC), ("Rotation", ROT), ("Scale", VEC, "1.000000,1.000000,1.000000")],
                                      [("ReturnValue", XF)]),
    "Math|Vector|Lerp(Vector)": F(KML, "VLerp", True, [("A", VEC), ("B", VEC), ("Alpha", "real")], [("ReturnValue", VEC)]),
    "Math|Vector|MakeVector": F(KML, "MakeVector", True, [("X", "real"), ("Y", "real"), ("Z", "real")], [("ReturnValue", VEC)]),
    # ---------------------------------------------------------------------------------------------- utilities
    "Utilities|GetObjectName": F(KSys, "GetObjectName", True, [("Object", "obj:" + C + "Object")], [("ReturnValue", "str")]),
    "Utilities|IsValidClass": F(KSys, "IsValidClass", True, [("Class", "cls:" + C + "Object")], [("ReturnValue", "bool")]),
    "Utilities|String|Append": F(KSL, "Concat_StrStr", True, [("A", "str"), ("B", "str")], [("ReturnValue", "str")]),
    "Utilities|String|EqualExactly(String)": F(KSL, "EqualEqual_StrStr", True, [("A", "str"), ("B", "str")], [("ReturnValue", "bool")]),
    "Utilities|String|SelectString": F(KML, "SelectString", True, [("A", "str"), ("B", "str"), ("bPickA", "bool")], [("ReturnValue", "str")]),
    "Utilities|String|ToString(Float)": F(KSL, "Conv_DoubleToString", True, [("InDouble", "real")], [("ReturnValue", "str")]),
    "Utilities|String|ToString(Integer)": F(KSL, "Conv_IntToString", True, [("InInt", "int")], [("ReturnValue", "str")]),
    "Utilities|Text|ToText(String)": F(KTL, "Conv_StringToText", True, [("InString", "str")], [("ReturnValue", "text")]),
    "Utilities|Time|GetGameTimeinSeconds": F(GS, "GetTimeSeconds", True, outs=[("ReturnValue", "real")]),
    "Utilities|Time|SetTimerbyFunctionName": F(KSys, "K2_SetTimer", False,
                                               [("Object", "obj:" + C + "Object"), ("FunctionName", "str"), ("Time", "real"), ("bLooping", "bool"),
                                                ("bMaxOncePerFrame", "bool", "false"), ("InitialStartDelay", "real", "0.000000"),
                                                ("InitialStartDelayVariance", "real", "0.000000")],
                                               [("ReturnValue", "struct:" + E + "TimerHandle")]),
    "Development|PrintString": F(KSys, "PrintString", False,
                                 [("InString", "str", "Hello"), ("bPrintToScreen", "bool", "true"), ("bPrintToLog", "bool", "true"),
                                  ("TextColor", LC, "(R=0.000000,G=0.660000,B=1.000000,A=1.000000)"), ("Duration", "real", "2.000000"),
                                  ("Key", "name", "None")]),
    # Make struct nodes (K2Node_MakeStruct): the members are the input pins, the output is named after the struct
    "Utilities|Struct|MakeMontageBlendSettings": {"kind": "make", "struct": E + "MontageBlendSettings", "out": "MontageBlendSettings",
                                                  "ins": [("Blend", "struct:" + E + "AlphaBlendArgs"), ("BlendMode", "enum:" + E + "EMontageBlendMode", "Standard"),
                                                          ("BlendProfile", "obj:" + E + "BlendProfile")]},
    "Utilities|Struct|MakeAlphaBlendArgs": {"kind": "make", "struct": E + "AlphaBlendArgs", "out": "AlphaBlendArgs",
                                            "ins": [("CustomCurve", "obj:" + E + "CurveFloat"), ("BlendTime", "real", "0.200000"),
                                                    ("BlendOption", "enum:" + E + "EAlphaBlendOption", "Linear")]},
}

# nodes that are not a plain function call
SPECIAL_NODES = {
    "Game|SpawnActorfromClass": "spawn", "UserInterface|CreateWidget": "widget", "Game|AddComponentbyClass": "addcomp",
    "Utilities|Array|Get(acopy)": "arrayget", "Utilities|IsValid": "isvalid",
}

# KismetArrayLibrary (K2Node_CallArrayFunction: the array pin is a wildcard resolved from the connection)
KAL = E + "KismetArrayLibrary"
ARRAY = {
    "Utilities|Array|Add": ("Array_Add", False, [("TargetArray", "wild[]&"), ("NewItem", "wild&")], [("ReturnValue", "int")]),
    "Utilities|Array|Clear": ("Array_Clear", False, [("TargetArray", "wild[]&")], []),
    "Utilities|Array|Length": ("Array_Length", True, [("TargetArray", "wild[]&")], [("ReturnValue", "int")]),
    "Utilities|Array|IsValidIndex": ("Array_IsValidIndex", True, [("TargetArray", "wild[]&"), ("IndexToTest", "int")], [("ReturnValue", "bool")]),
    "Utilities|Array|SetArrayElem": ("Array_Set", False, [("TargetArray", "wild[]&"), ("Index", "int"), ("Item", "wild&"), ("bSizeToFit", "bool")], []),
}

# DSL operators -> KismetMathLibrary (picked by operand type: int / real / object / vector / bool / name)
OPS = {
    "==": {"int": "EqualEqual_IntInt", "real": "EqualEqual_DoubleDouble", "obj": "EqualEqual_ObjectObject", "name": "EqualEqual_NameName",
           "bool": "EqualEqual_BoolBool", "byte": "EqualEqual_ByteByte"},
    "!=": {"int": "NotEqual_IntInt", "real": "NotEqual_DoubleDouble", "obj": "NotEqual_ObjectObject", "name": "NotEqual_NameName",
           "bool": "NotEqual_BoolBool"},
    "<": {"int": "Less_IntInt", "real": "Less_DoubleDouble"}, "<=": {"int": "LessEqual_IntInt", "real": "LessEqual_DoubleDouble"},
    ">": {"int": "Greater_IntInt", "real": "Greater_DoubleDouble"}, ">=": {"int": "GreaterEqual_IntInt", "real": "GreaterEqual_DoubleDouble"},
    "+": {"int": "Add_IntInt", "real": "Add_DoubleDouble", "vec": "Add_VectorVector"},
    "-": {"int": "Subtract_IntInt", "real": "Subtract_DoubleDouble", "vec": "Subtract_VectorVector"},
    "*": {"int": "Multiply_IntInt", "real": "Multiply_DoubleDouble", "vec": "Multiply_VectorVector"},
    "/": {"int": "Divide_IntInt", "real": "Divide_DoubleDouble", "vec": "Divide_VectorVector"},
}

# events (K2Node_Event): DSL name -> (owner class for the override, function, [(output pin, type)])
EVENTS = {
    "EventBeginPlay": (E + "Actor", "ReceiveBeginPlay", []),
    "EventTick": (E + "Actor", "ReceiveTick", [("DeltaSeconds", "real")]),
    "EventEndPlay": (E + "Actor", "ReceiveEndPlay", [("EndPlayReason", "enum:" + E + "EEndPlayReason")]),
    "EventBlueprintUpdateAnimation": (E + "AnimInstance", "BlueprintUpdateAnimation", [("DeltaTimeX", "real")]),
    "UserInterface|EventConstruct": (U + "UserWidget", "Construct", []),
    "UserInterface|EventTick": (U + "UserWidget", "Tick", [("MyGeometry", "struct:/Script/SlateCore.Geometry"), ("InDeltaTime", "real")]),
}

# native properties reached through the DSL's variable heads (K2Node_VariableGet / Set)
NATIVE_VARS = {
    ("Character", "Mesh"): (E + "Character", "obj:" + E + "SkeletalMeshComponent"),
    ("PlayerController", "ShowMouseCursor"): (E + "PlayerController", "bool", "bShowMouseCursor"),
    ("SpringArmComponent", "TargetArmLength"): ("/Script/Engine.SpringArmComponent", "real"),
}


def check():
    """Grep each function's declaration in the 5.4 headers; report missing functions and parameter-name mismatches."""
    import os, re, glob
    root = r"C:\Program Files\Epic Games\UE_5.4\Engine\Source\Runtime"
    hdrs = glob.glob(os.path.join(root, "Engine", "Classes", "**", "*.h"), recursive=True) + \
        glob.glob(os.path.join(root, "UMG", "Public", "**", "*.h"), recursive=True)
    text = {}
    want = {}
    for head, s in SIGS.items():
        if s["kind"] == "call":
            want.setdefault(s["fn"], []).append(head)
    for h in hdrs:
        try:
            t = open(h, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for fn in want:
            for m in re.finditer(r"UFUNCTION\(([^\n]*)\)\s*\n(?:\s*UE_DEPRECATED[^\n]*\n)?\s*([^\n;{]*\b%s\s*\(([^)]*)\)[^;{\n]*)" % re.escape(fn), t):
                text.setdefault(fn, []).append((os.path.basename(h), m.group(1), m.group(2).strip(), m.group(3)))
    bad = 0
    for fn, heads in want.items():
        for head in heads:
            s = SIGS[head]
            found = text.get(fn)
            if not found:
                print("MISSING  %-55s %s" % (head, fn)); bad += 1; continue
            ok = False
            for hfile, spec, decl, params in found:
                names = [re.split(r"[\s&*]+", p.split("=")[0].strip())[-1] for p in params.split(",") if p.strip()]
                pure = "BlueprintPure" in spec and "BlueprintPure=false" not in spec.replace(" ", "") or \
                    (decl.rstrip().endswith("const") and "BlueprintPure=false" not in spec.replace(" ", ""))
                mine = [i[0] for i in s["ins"]] + [o[0] for o in s["outs"] if o[0] != "ReturnValue"]
                if sorted(names) == sorted(mine):
                    ok = True
                    if pure != s["pure"]:
                        print("PURITY   %-55s header says pure=%s (%s)" % (head, pure, hfile)); bad += 1
                    break
            if not ok:
                print("PARAMS   %-55s mine %s | header %s" % (head, [i[0] for i in s["ins"]] + [o[0] for o in s["outs"] if o[0] != "ReturnValue"],
                                                            [(f[0], f[3]) for f in found][:2])); bad += 1
    print("%d problems" % bad)


if __name__ == "__main__":
    check()
