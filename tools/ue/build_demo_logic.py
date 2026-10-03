"""Write the demo widgets' logic graphs through the MCP BlueprintTools (system Python, editor running).

    python tools/ue/build_demo_logic.py [button|header|browser] [FunctionName ...]

Requires the trees (build_demo_ui.py) and the variables + data (ue_build.py demo_vars demo_data). The browser is
SkeletonShowcase.cs re-cut: characters are SPAWNED on selection (the previous one destroyed), one-shots route to the
masked slots while a locomotion loop plays and play full body otherwise, a one-shot started from an idle puts its
section's idle under itself so the montage blends out onto it, deaths hold 2 s with the twitches and the finger idles
off, Block_L_Idle / twitches / finger idles are toggles.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import bp, umg

UI = "/Game/UndeadLegion/Demo/UI"
V = "Variables|Demo|"
BTN_CLASS = UI + "/WBP_DemoButton.WBP_DemoButton_C"
HDR_CLASS = UI + "/WBP_DemoHeader.WBP_DemoHeader_C"
C = "Class|BPUndeadSkeleton|"
SEL = "(Math|Color|MakeColor :R 0.55 :G 0.72 :B 0.30 :A 1.0)"
NORM = "(Math|Color|MakeColor :R 0.22 :G 0.23 :B 0.26 :A 1.0)"


def ref(bpname, graph=None):
    base = "%s/%s.%s" % (UI, bpname, bpname)
    return {"refPath": base + (":" + graph if graph else "")}


# ---------------------------------------------------------------- WBP_DemoButton / WBP_DemoHeader

BUTTON = {
    "Setup": ([("InBrowser", UI + "/WBP_AnimBrowser.WBP_AnimBrowser_C", True), ("InKind", "int", True), ("InIndex", "int", True),
               ("Caption", "string", True)], """
(fn Setup (InBrowser InKind InIndex Caption)
  (%(V)sSetBrowser InBrowser)
  (%(V)sSetKind InKind)
  (%(V)sSetIndex InIndex)
  (Widget|SetText(Text) :self (Variables|WBP_DemoButton|GetLabel) :InText (Utilities|Text|ToText(String) Caption)))
"""),
    "SetSelected": ([("Selected", "bool", True)], """
(fn SetSelected (Selected)
  (Class|Button|SetBackgroundColor :self (Variables|WBP_DemoButton|GetBtn) :BackgroundColor (select Selected %(SEL)s %(NORM)s)))
"""),
}
HEADER = {
    "SetCaption": ([("Caption", "string", True)], """
(fn SetCaption (Caption)
  (Widget|SetText(Text) :self (Variables|WBP_DemoHeader|GetLabel) :InText (Utilities|Text|ToText(String) Caption)))
"""),
}

# ---------------------------------------------------------------- WBP_AnimBrowser

CUR = "(%(V)sGetCurrent)"
BROWSER = {
    "MakeButton": ([("Kind", "int", True), ("Index", "int", True), ("Caption", "string", True),
                    ("Button", BTN_CLASS, False)], """
(fn MakeButton (Kind Index Caption)
  (bind b (UserInterface|CreateWidget :Class "%(BTN)s" :OwningPlayer (Game|GetPlayerController 0)))
  (Class|WBPDemoButton|Setup :self b :InBrowser self :InKind Kind :InIndex Index :Caption Caption)
  (return b))
"""),
    "AddHeader": ([("Box", "/Script/UMG.VerticalBox", True), ("Caption", "string", True)], """
(fn AddHeader (Box Caption)
  (bind h (UserInterface|CreateWidget :Class "%(HDR)s" :OwningPlayer (Game|GetPlayerController 0)))
  (Class|WBPDemoHeader|SetCaption :self h :Caption Caption)
  (Panel|AddChildtoVerticalBox :self Box :Content h))
"""),
    "BuildCharacters": ([], """
(fn BuildCharacters ()
  (bind box (Variables|WBP_AnimBrowser|GetCharacterList))
  (Widget|Panel|ClearChildren :self box)
  (Utilities|Array|Clear :TargetArray (%(V)sGetCharButtons))
  (for i (range (Utilities|Array|Length :TargetArray (%(V)sGetCharacterNames)))
    (bind b (CallFunction|MakeButton :Kind 0 :Index i :Caption (Utilities|Array|Get(acopy) (%(V)sGetCharacterNames) i)))
    (Panel|AddChildtoVerticalBox :self box :Content b)
    (Utilities|Array|Add :TargetArray (%(V)sGetCharButtons) :NewItem b)))
"""),
    "BuildWeapons": ([], """
(fn BuildWeapons ()
  (bind box (Variables|WBP_AnimBrowser|GetWeaponList))
  (Widget|Panel|ClearChildren :self box)
  (Utilities|Array|Clear :TargetArray (%(V)sGetWeaponButtons))
  (for i (range (Utilities|Array|Length :TargetArray (%(V)sGetLoadoutNames)))
    (bind b (CallFunction|MakeButton :Kind 5 :Index i :Caption (Utilities|Array|Get(acopy) (%(V)sGetLoadoutNames) i)))
    (Panel|AddChildtoVerticalBox :self box :Content b)
    (Utilities|Array|Add :TargetArray (%(V)sGetWeaponButtons) :NewItem b)))
"""),
    "BuildClips": ([], """
(fn BuildClips ()
  (bind box (Variables|WBP_AnimBrowser|GetClipList))
  (Widget|Panel|ClearChildren :self box)
  (Utilities|Array|Clear :TargetArray (%(V)sGetClipButtons))
  (bind secs (%(V)sGetClipSections))
  (for i (range (Utilities|Array|Length :TargetArray (%(V)sGetClipNames)))
    (bind s (Utilities|Array|Get(acopy) secs i))
    (if (or (== i 0) (!= s (Utilities|Array|Get(acopy) secs (select (== i 0) 0 (- i 1)))))
      (CallFunction|AddHeader :Box box :Caption (Utilities|Array|Get(acopy) (%(V)sGetSectionNames) s)))
    (bind b (CallFunction|MakeButton :Kind 1 :Index i :Caption (Utilities|Array|Get(acopy) (%(V)sGetClipNames) i)))
    (Panel|AddChildtoVerticalBox :self box :Content b)
    (Utilities|Array|Add :TargetArray (%(V)sGetClipButtons) :NewItem b)))
"""),
    "BuildFooter": ([], """
(fn BuildFooter ()
  (bind bar (Variables|WBP_AnimBrowser|GetFooterBar))
  (bind info (Variables|WBP_AnimBrowser|GetInfoLabel))
  (Widget|Panel|ClearChildren :self bar)
  (Utilities|Array|Clear :TargetArray (%(V)sGetFooterButtons))
  (bind b0 (CallFunction|MakeButton :Kind 6 :Index 0 :Caption "Root motion"))
  (Widget|AddChildtoHorizontalBox :self bar :Content b0)
  (Utilities|Array|Add :TargetArray (%(V)sGetFooterButtons) :NewItem b0)
  (bind b1 (CallFunction|MakeButton :Kind 7 :Index 1 :Caption "Turntable"))
  (Widget|AddChildtoHorizontalBox :self bar :Content b1)
  (Utilities|Array|Add :TargetArray (%(V)sGetFooterButtons) :NewItem b1)
  (bind b2 (CallFunction|MakeButton :Kind 8 :Index 2 :Caption "Recenter"))
  (Widget|AddChildtoHorizontalBox :self bar :Content b2)
  (Utilities|Array|Add :TargetArray (%(V)sGetFooterButtons) :NewItem b2)
  (bind b3 (CallFunction|MakeButton :Kind 9 :Index 3 :Caption "Eyes"))
  (Widget|AddChildtoHorizontalBox :self bar :Content b3)
  (Utilities|Array|Add :TargetArray (%(V)sGetFooterButtons) :NewItem b3)
  (Widget|AddChildtoHorizontalBox :self bar :Content info))
"""),
    "BuildModules": ([], """
(fn BuildModules ()
  (bind box (Variables|WBP_AnimBrowser|GetModuleList))
  (Widget|Panel|ClearChildren :self box)
  (Utilities|Array|Clear :TargetArray (%(V)sGetModuleButtons))
  (Utilities|Array|Clear :TargetArray (%(V)sGetModuleButtonMesh))
  (bind me (%(V)sGetCurrentChar))
  (bind names (%(V)sGetCharacterNames))
  (bind owners (%(V)sGetAllModuleOwner))
  (bind mods (%(V)sGetAllModules))
  (bind all (CallFunction|MakeButton :Kind 3 :Index 0 :Caption "All (own set)"))
  (Panel|AddChildtoVerticalBox :self box :Content all)
  (bind none (CallFunction|MakeButton :Kind 4 :Index 0 :Caption "None"))
  (Panel|AddChildtoVerticalBox :self box :Content none)
  (for k (range (Utilities|Array|Length :TargetArray names))
    (bind o (select (== k 0) me (select (<= k me) (- k 1) k)))
    (CallFunction|AddHeader :Box box :Caption (Utilities|String|Append (Utilities|Array|Get(acopy) names o) (Utilities|String|SelectString " (own set)" " armour" (== k 0))))
    (for j (range (Utilities|Array|Length :TargetArray mods))
      (if (== (Utilities|Array|Get(acopy) owners j) o)
        (bind b (CallFunction|MakeButton :Kind 2 :Index j :Caption (Utilities|Array|Get(acopy) (%(V)sGetAllModuleNames) j)))
        (Panel|AddChildtoVerticalBox :self box :Content b)
        (Utilities|Array|Add :TargetArray (%(V)sGetModuleButtons) :NewItem b)
        (Utilities|Array|Add :TargetArray (%(V)sGetModuleButtonMesh) :NewItem (Utilities|Array|Get(acopy) mods j))))))
"""),
    "Refresh": ([], """
(fn Refresh ()
  (bind c %(CUR)s)
  (bind me (%(V)sGetCurrentChar))
  (bind cb (%(V)sGetCharButtons))
  (for i (range (Utilities|Array|Length :TargetArray cb))
    (Class|WBPDemoButton|SetSelected :self (Utilities|Array|Get(acopy) cb i) :Selected (== i me)))
  (bind lo (%(C)sGetLoadout :self c))
  (bind wb (%(V)sGetWeaponButtons))
  (for i (range (Utilities|Array|Length :TargetArray wb))
    (Class|WBPDemoButton|SetSelected :self (Utilities|Array|Get(acopy) wb i) :Selected (== i lo)))
  (bind mb (%(V)sGetModuleButtons))
  (bind mm (%(V)sGetModuleButtonMesh))
  (for i (range (Utilities|Array|Length :TargetArray mb))
    (Class|WBPDemoButton|SetSelected :self (Utilities|Array|Get(acopy) mb i) :Selected (%(C)sIsModuleWorn :self c :Module (Utilities|Array|Get(acopy) mm i))))
  (bind fb (%(V)sGetFooterButtons))
  (Class|WBPDemoButton|SetSelected :self (Utilities|Array|Get(acopy) fb 0) :Selected (%(V)sGetRootMotionOn))
  (Class|WBPDemoButton|SetSelected :self (Utilities|Array|Get(acopy) fb 1) :Selected (%(V)sGetTurntableOn))
  (Class|WBPDemoButton|SetSelected :self (Utilities|Array|Get(acopy) fb 3) :Selected (%(V)sGetEyesOn))
  (bind clb (%(V)sGetClipButtons))
  (bind modes (%(V)sGetClipModes))
  (bind args (%(V)sGetClipArgs))
  (bind tw (%(V)sGetTwitchOn))
  (bind cur (%(V)sGetCurrentClip))
  (bind act (%(V)sGetActionClip))
  (bind held (%(V)sGetBlockHeld))
  (bind fl (%(C)sGetFingerIdle :self c :Left true))
  (bind fr (%(C)sGetFingerIdle :self c :Left false))
  (for i (range (Utilities|Array|Length :TargetArray clb))
    (bind m (Utilities|Array|Get(acopy) modes i))
    (bind a (Utilities|Array|Get(acopy) args i))
    (bind sel (or (or (== i cur) (== i act))
                  (or (and (== m 5) held)
                      (or (and (== m 6) (Utilities|Array|Get(acopy) tw (select (== m 6) (- a 1) 0)))
                          (and (== m 7) (select (== a 0) fl fr))))))
    (Class|WBPDemoButton|SetSelected :self (Utilities|Array|Get(acopy) clb i) :Selected sel)))
"""),
    "UpdateInfo": ([("Clip", "int", True)], """
(fn UpdateInfo (Clip)
  (bind anim (Utilities|Array|Get(acopy) (%(V)sGetClips) Clip))
  (bind m (Utilities|Array|Get(acopy) (%(V)sGetClipModes) Clip))
  (bind kind (Utilities|String|SelectString "loop" (Utilities|String|SelectString "death: holds 2 s, then the last idle" (Utilities|String|SelectString "additive overlay" "one-shot" (== m 9)) (== m 8)) (== m 0)))
  (bind line (Utilities|String|Append (Utilities|Array|Get(acopy) (%(V)sGetClipNames) Clip)
               (Utilities|String|Append "   |   " (Utilities|String|Append (Utilities|String|ToString(Float) (Animation|GetPlayLength :self anim))
                 (Utilities|String|Append " s   |   " kind)))))
  (Widget|SetText(Text) :self (Variables|WBP_AnimBrowser|GetInfoLabel) :InText (Utilities|Text|ToText(String) line)))
"""),
    "EndDeathSuspend": ([], """
(fn EndDeathSuspend ()
  (bind c %(CUR)s)
  (bind tw (%(V)sGetTwitchOn))
  (%(C)sSetFingersSuspended :self c :Suspended false)
  (%(C)sSetTwitch :self c :Index 1 :Weight (select (Utilities|Array|Get(acopy) tw 0) 1.0 0.0))
  (%(C)sSetTwitch :self c :Index 2 :Weight (select (Utilities|Array|Get(acopy) tw 1) 1.0 0.0))
  (%(C)sSetTwitch :self c :Index 3 :Weight (select (Utilities|Array|Get(acopy) tw 2) 1.0 0.0)))
"""),
    "ApplyState": ([], """
(fn ApplyState ()
  (bind c %(CUR)s)
  (bind cur (%(V)sGetCurrentClip))
  (%(C)sSetRootMotion :self c :On (%(V)sGetRootMotionOn))
  (%(C)sShowEyes :self c :On (%(V)sGetEyesOn))
  (CallFunction|EndDeathSuspend)
  (%(V)sSetBlockHeld false)
  (%(C)sSetHeldBlock :self c :Held false)
  (%(C)sPlayLoop :self c :Clip (Utilities|Array|Get(acopy) (%(V)sGetClips) cur))
  (%(C)sSetClipHold :self c :Left (Utilities|Array|Get(acopy) (%(V)sGetClipGrip) cur) :Right false)
  (%(V)sSetActionClip -1)
  (%(V)sSetDeathPauseAt 0.0)
  (%(V)sSetDeathResumeAt 0.0)
  (CallFunction|UpdateInfo :Clip cur))
"""),
    "SelectCharacter": ([("Index", "int", True)], """
(fn SelectCharacter (Index)
  (bind old %(CUR)s)
  (Utilities|IsValid old
    (:"Is Valid"
      (Actor|DestroyActor :self old)
      (CallFunction|SpawnSelected :Index Index))
    (:"Is Not Valid"
      (CallFunction|SpawnSelected :Index Index))))
"""),
    "SpawnSelected": ([("Index", "int", True)], """
(fn SpawnSelected (Index)
  (bind a (Game|SpawnActorfromClass :Class (Utilities|Array|Get(acopy) (%(V)sGetCharacterClasses) Index)
            :SpawnTransform (%(V)sGetSpawnTransform) :CollisionHandlingOverride "AlwaysSpawn"))
  (%(V)sSetCurrent a)
  (%(V)sSetCurrentChar Index)
  (CallFunction|ApplyState)
  (CallFunction|BuildModules)
  (CallFunction|Refresh))
"""),
    "Recenter": ([], """
(fn Recenter ()
  (Transformation|SetActorTransform :self %(CUR)s :NewTransform (%(V)sGetSpawnTransform) :bSweep false :bTeleport true))
"""),
    "PlayOneShot": ([("Clip", "int", True), ("SlotCode", "int", True)], """
(fn PlayOneShot (Clip SlotCode)
  (bind c %(CUR)s)
  (bind anim (Utilities|Array|Get(acopy) (%(V)sGetClips) Clip))
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (if (and (%(V)sGetBaseLoco) (> SlotCode 0))
    (switch int (- SlotCode 1)
      (:0 (%(V)sSetActionEnd (+ now (%(C)sPlayAction :self c :Clip anim :Slot "UpperBody" :BlendIn 0.15 :BlendOut 0.25 :Rate 1.0))))
      (:1 (%(V)sSetActionEnd (+ now (%(C)sPlayAction :self c :Clip anim :Slot "LeftArm" :BlendIn 0.15 :BlendOut 0.25 :Rate 1.0))))
      (:2 (%(V)sSetActionEnd (+ now (%(C)sPlayAction :self c :Clip anim :Slot "RightArm" :BlendIn 0.15 :BlendOut 0.25 :Rate 1.0)))))
    (else
      (%(V)sSetActionEnd (+ now (%(C)sPlayAction :self c :Clip anim :Slot "DefaultSlot" :BlendIn 0.15 :BlendOut 0.25 :Rate 1.0)))
      (if (not (%(V)sGetBaseLoco))
        (bind r (Utilities|Array|Get(acopy) (%(V)sGetClipArgs) Clip))
        (bind ret (select (>= r 0) r (%(V)sGetLastIdle)))
        (%(C)sPlayLoop :self c :Clip (Utilities|Array|Get(acopy) (%(V)sGetClips) ret))
        (%(V)sSetCurrentClip ret)
        (%(V)sSetLastIdle ret))))
  (%(V)sSetActionClip Clip)
  (%(C)sSetClipHold :self c :Left (Utilities|Array|Get(acopy) (%(V)sGetClipGrip) Clip) :Right false)
  (CallFunction|UpdateInfo :Clip Clip))
"""),
    "PlayClip": ([("Index", "int", True)], """
(fn PlayClip (Index)
  (bind c %(CUR)s)
  (bind mode (Utilities|Array|Get(acopy) (%(V)sGetClipModes) Index))
  (bind arg (Utilities|Array|Get(acopy) (%(V)sGetClipArgs) Index))
  (bind anim (Utilities|Array|Get(acopy) (%(V)sGetClips) Index))
  (switch int mode
    (:0
      (%(C)sStopActions :self c :BlendOut 0.2)
      (CallFunction|EndDeathSuspend)
      (%(C)sPlayLoop :self c :Clip anim)
      (bind loco (Utilities|Array|Get(acopy) (%(V)sGetClipLoco) Index))
      (%(V)sSetBaseLoco loco)
      (if (not loco)
        (%(V)sSetLastIdle Index))
      (%(V)sSetCurrentClip Index)
      (%(V)sSetActionClip -1)
      (%(V)sSetDeathPauseAt 0.0)
      (%(V)sSetDeathResumeAt 0.0)
      (%(C)sSetClipHold :self c :Left (Utilities|Array|Get(acopy) (%(V)sGetClipGrip) Index) :Right false)
      (CallFunction|UpdateInfo :Clip Index))
    (:1 (CallFunction|PlayOneShot :Clip Index :SlotCode 0))
    (:2 (CallFunction|PlayOneShot :Clip Index :SlotCode 1))
    (:3 (CallFunction|PlayOneShot :Clip Index :SlotCode 2))
    (:4 (CallFunction|PlayOneShot :Clip Index :SlotCode 3))
    (:5
      (%(V)sSetBlockHeld (not (%(V)sGetBlockHeld)))
      (%(C)sSetHeldBlock :self c :Held (%(V)sGetBlockHeld)))
    (:6
      (bind on (not (Utilities|Array|Get(acopy) (%(V)sGetTwitchOn) (- arg 1))))
      (Utilities|Array|SetArrayElem :TargetArray (%(V)sGetTwitchOn) :Index (- arg 1) :Item on :bSizeToFit false)
      (%(C)sSetTwitch :self c :Index arg :Weight (select on 1.0 0.0)))
    (:7
      (%(C)sSetFingerIdle :self c :Left (== arg 0) :On (not (%(C)sGetFingerIdle :self c :Left (== arg 0)))))
    (:8
      (CallFunction|PlayOneShot :Clip Index :SlotCode 0)
      (%(C)sSetTwitch :self c :Index 1 :Weight 0.0)
      (%(C)sSetTwitch :self c :Index 2 :Weight 0.0)
      (%(C)sSetTwitch :self c :Index 3 :Weight 0.0)
      (%(C)sSetFingersSuspended :self c :Suspended true)
      (%(V)sSetDeathPauseAt (- (%(V)sGetActionEnd) 0.3))
      (%(V)sSetDeathResumeAt 0.0))
    (:9
      (%(C)sPlayOverlay :self c :Clip anim)
      (CallFunction|UpdateInfo :Clip Index))))
"""),
    "OnButton": ([("Kind", "int", True), ("Index", "int", True)], """
(fn OnButton (Kind Index)
  (CallFunction|HandleButton :Kind Kind :Index Index)
  (CallFunction|Refresh))
"""),
    "HandleButton": ([("Kind", "int", True), ("Index", "int", True)], """
(fn HandleButton (Kind Index)
  (bind c %(CUR)s)
  (switch int Kind
    (:0 (CallFunction|SelectCharacter :Index Index))
    (:1 (CallFunction|PlayClip :Index Index))
    (:2
      (bind m (Utilities|Array|Get(acopy) (%(V)sGetAllModules) Index))
      (if (%(C)sIsModuleWorn :self c :Module m)
        (%(C)sRemoveModule :self c :Module m)
        (else
          (%(C)sWearModule :self c :Module m))))
    (:3 (%(C)sSetDefaultModulesWorn :self c :Worn true))
    (:4 (%(C)sSetDefaultModulesWorn :self c :Worn false))
    (:5 (%(C)sEquipLoadout :self c :Index Index))
    (:6
      (%(V)sSetRootMotionOn (not (%(V)sGetRootMotionOn)))
      (%(C)sSetRootMotion :self c :On (%(V)sGetRootMotionOn))
      (if (not (%(V)sGetRootMotionOn))
        (CallFunction|Recenter)))
    (:7 (%(V)sSetTurntableOn (not (%(V)sGetTurntableOn))))
    (:8 (CallFunction|Recenter))
    (:9
      (%(V)sSetEyesOn (not (%(V)sGetEyesOn)))
      (%(C)sShowEyes :self c :On (%(V)sGetEyesOn)))))
"""),
}
BROWSER_ORDER = ["MakeButton", "AddHeader", "BuildCharacters", "BuildWeapons", "BuildClips", "BuildFooter", "BuildModules",
                 "UpdateInfo", "EndDeathSuspend", "Refresh", "ApplyState", "Recenter", "SpawnSelected", "SelectCharacter", "PlayOneShot",
                 "PlayClip", "HandleButton", "OnButton"]
BROWSER_EVENTS = """
(event UserInterface|EventConstruct
  (CallFunction|BuildCharacters)
  (CallFunction|BuildWeapons)
  (CallFunction|BuildClips)
  (CallFunction|BuildFooter)
  (CallFunction|SelectCharacter :Index 0))

(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (bind c %(CUR)s)
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (if (and (>= (%(V)sGetActionClip) 0) (and (> now (%(V)sGetActionEnd)) (and (<= (%(V)sGetDeathPauseAt) 0.0) (<= (%(V)sGetDeathResumeAt) 0.0))))
    (%(C)sSetClipHold :self c :Left (Utilities|Array|Get(acopy) (%(V)sGetClipGrip) (%(V)sGetCurrentClip)) :Right false)
    (%(V)sSetActionClip -1)
    (CallFunction|UpdateInfo :Clip (%(V)sGetCurrentClip))
    (CallFunction|Refresh))
  (if (and (> (%(V)sGetDeathPauseAt) 0.0) (> now (%(V)sGetDeathPauseAt)))
    (%(C)sPauseActions :self c)
    (%(V)sSetDeathPauseAt 0.0)
    (%(V)sSetDeathResumeAt (+ now 2.0)))
  (if (and (> (%(V)sGetDeathResumeAt) 0.0) (> now (%(V)sGetDeathResumeAt)))
    (%(V)sSetDeathResumeAt 0.0)
    (%(C)sStopActions :self c :BlendOut 0.4)
    (CallFunction|EndDeathSuspend)
    (%(V)sSetActionClip -1)
    (CallFunction|UpdateInfo :Clip (%(V)sGetCurrentClip))
    (CallFunction|Refresh))
  (if (%(V)sGetTurntableOn)
    (Transformation|AddActorWorldRotation :self c :DeltaRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (* 25.0 InDeltaTime))
       :bSweep false :bTeleport false))
  (bind pawn (Utilities|Casting|CastToBP_OrbitPawn :Object (Game|GetPlayerPawn 0))
    (:then
      (Class|BPOrbitPawn|SetTarget :self pawn :NewTarget c))
    (:CastFailed)))
"""


def fill(code):
    return code % {"V": V, "C": C, "CUR": CUR % {"V": V}, "SEL": SEL, "NORM": NORM, "BTN": BTN_CLASS, "HDR": HDR_CLASS}


def ensure(bpname, funcs, order):
    B = ref(bpname)
    have = [g["refPath"].split(":")[-1] for g in bp("list_graphs", blueprint=B)]
    for fn in order:
        if fn in have:
            continue
        g = bp("add_function_graph", blueprint=B, graph_name=fn)
        for pn, t, inp in funcs[fn][0]:
            if t.startswith("/"):
                bp("add_object_function_param", graph=g, param_name=pn, object_class={"refPath": t}, input_param=inp)
            else:
                bp("add_function_param", graph=g, param_name=pn, param_type=t, input_param=inp)


def clear(g):
    for n in bp("find_nodes", graph=g, title="") or []:
        p = n["refPath"].split(".")[-1]
        if "FunctionEntry" not in p and "FunctionResult" not in p:
            bp("delete_node", node=n)


def write_funcs(bpname, funcs, order, only):
    ensure(bpname, funcs, order)
    for fn in order:
        if only and fn not in only:
            continue
        g = ref(bpname, fn)
        clear(g)
        bp("write_graph_dsl", graph=g, code=fill(funcs[fn][1]))
        print("wrote", bpname, fn)


def button(only):
    write_funcs("WBP_DemoButton", BUTTON, ["Setup", "SetSelected"], only)
    if not only or "EventGraph" in only:
        g = ref("WBP_DemoButton", "EventGraph")
        clear(g)
        umg("BindToEventProperty", widgetBlueprint=ref("WBP_DemoButton"), eventName="OnClicked", propertyName="Btn",
            propertyClass={"refPath": "/Script/UMG.Button"})
        # the bound event reads back as "(event OnClicked(Btn))", which the DSL cannot parse: place the nodes by hand
        ev = bp("find_nodes", graph=g, title="")[0]
        mk = lambda t, x, y: bp("create_node", graph=g, type_id=t, pos={"x": x, "y": y})
        call = mk("Class|WBPAnimBrowser|OnButton", 400, 0)
        gb, gk, gi = mk(V + "GetBrowser", 150, 120), mk(V + "GetKind", 150, 200), mk(V + "GetIndex", 150, 280)
        pins = lambda n: {(("in" if p in i["input_pins"] else "out"), p["name"]): p["pin_id"]
                          for i in bp("get_node_infos", nodes=[n]) for p in i["input_pins"] + i["output_pins"]}
        pe, pc = pins(ev), pins(call)
        bp("connect_pins", output_pin=pe[("out", "then")], input_pin=pc[("in", "execute")])
        bp("connect_pins", output_pin=pins(gb)[("out", "Browser")], input_pin=pc[("in", "self")])
        bp("connect_pins", output_pin=pins(gk)[("out", "Kind")], input_pin=pc[("in", "Kind")])
        bp("connect_pins", output_pin=pins(gi)[("out", "Index")], input_pin=pc[("in", "Index")])
        name = "OnClicked(Btn)"
        print("wrote WBP_DemoButton click ->", name)


def header(only):
    write_funcs("WBP_DemoHeader", HEADER, ["SetCaption"], only)


def browser(only):
    write_funcs("WBP_AnimBrowser", BROWSER, BROWSER_ORDER, only)
    if not only or "EventGraph" in only:
        g = ref("WBP_AnimBrowser", "EventGraph")
        clear(g)
        bp("write_graph_dsl", graph=g, code=fill(BROWSER_EVENTS))
        print("wrote WBP_AnimBrowser EventGraph")


D = "/Game/UndeadLegion/Demo/Blueprints"
PAWN_FUNCS = {"SetTarget": ([("NewTarget", "/Script/Engine.Actor", True)], """
(fn SetTarget (NewTarget)
  (%(V)sSetTarget NewTarget))
""")}
PAWN_EVENTS = """
(event EventTick (DeltaSeconds)
  (bind pc (Game|GetPlayerController 0))
  (if (or (Game|Player|IsInputKeyDown :self pc :Key "RightMouseButton") (Game|Player|IsInputKeyDown :self pc :Key "LeftMouseButton"))
    (bind (dx dy) (Game|Player|GetInputMouseDelta :self pc))
    (%(V)sSetYaw (+ (%(V)sGetYaw) (* dx 2.0)))
    (%(V)sSetPitch (Math|Float|Clamp(Float) :Value (+ (%(V)sGetPitch) (* dy 2.0)) :Min -75.0 :Max 10.0)))
  (if (Game|Player|WasInputKeyJustPressed :self pc :Key "MouseScrollUp")
    (%(V)sSetDistance (* (%(V)sGetDistance) 0.87)))
  (if (Game|Player|WasInputKeyJustPressed :self pc :Key "MouseScrollDown")
    (%(V)sSetDistance (/ (%(V)sGetDistance) 0.87)))
  (%(V)sSetDistance (Math|Float|Clamp(Float) :Value (%(V)sGetDistance) :Min 150.0 :Max 1400.0))
  (bind arm (Variables|Default|GetArm))
  (Transformation|SetWorldRotation :self arm :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch (%(V)sGetPitch) :Yaw (%(V)sGetYaw))
     :bSweep false :bTeleport false)
  (Class|SpringArmComponent|SetTargetArmLength :self arm :TargetArmLength (%(V)sGetDistance))
  (bind t (%(V)sGetTarget))
  (Utilities|IsValid t
    (:"Is Valid"
      (bind goal (+ (Transformation|GetActorLocation :self t) (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z (%(V)sGetPivotHeight))))
      (Transformation|SetActorLocation :self self
         :NewLocation (Math|Interpolation|VInterpTo :Current (Transformation|GetActorLocation :self self) :Target goal :DeltaTime DeltaSeconds :InterpSpeed 6.0)
         :bSweep false :bTeleport true))
    (:"Is Not Valid")))
"""
SHOWCASE_EVENTS = """
(event EventBeginPlay
  (bind pc (Game|GetPlayerController 0))
  (bind w (UserInterface|CreateWidget :Class "/Game/UndeadLegion/Demo/UI/WBP_AnimBrowser.WBP_AnimBrowser_C" :OwningPlayer pc))
  (UserInterface|Viewport|AddtoViewport :self w :ZOrder 0)
  (Class|PlayerController|SetShowMouseCursor :self pc :bShowMouseCursor true)
  (Input|SetInputModeGameAndUI :PlayerController pc :InWidgetToFocus w :InMouseLockMode "DoNotLock" :bHideCursorDuringCapture false))
"""


def actor_bp(name, funcs, events):
    B = {"refPath": "%s/%s.%s" % (D, name, name)}
    have = [g["refPath"].split(":")[-1] for g in bp("list_graphs", blueprint=B)]
    for fn, (params, code) in funcs.items():
        if fn not in have:
            g = bp("add_function_graph", blueprint=B, graph_name=fn)
            for pn, t, inp in params:
                bp("add_object_function_param", graph=g, param_name=pn, object_class={"refPath": t}, input_param=inp)
        g = {"refPath": "%s/%s.%s:%s" % (D, name, name, fn)}
        clear(g)
        bp("write_graph_dsl", graph=g, code=fill(code))
    g = {"refPath": "%s/%s.%s:EventGraph" % (D, name, name)}
    clear(g)
    bp("write_graph_dsl", graph=g, code=fill(events))
    bp("compile_blueprint", blueprint=B, warnings_as_errors=False)
    print("wrote", name)


def pawn(only):
    actor_bp("BP_OrbitPawn", PAWN_FUNCS, PAWN_EVENTS)


def showcase(only):
    actor_bp("BP_DemoShowcase", {}, SHOWCASE_EVENTS)


if __name__ == "__main__":
    args = sys.argv[1:]
    KINDS = ("button", "header", "browser", "pawn", "showcase")
    which = [a for a in args if a in KINDS] or ["header", "pawn", "browser", "button", "showcase"]
    only = [a for a in args if a not in KINDS]
    for w in which:
        globals()[w](only)
    for n in ("WBP_DemoHeader", "WBP_AnimBrowser", "WBP_DemoButton"):
        print(n, umg("CompileWidgetBlueprint", widgetBlueprint=ref(n)))
