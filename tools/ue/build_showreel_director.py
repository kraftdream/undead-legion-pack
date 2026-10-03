"""Write BP_ShowreelDirector's graphs through the MCP BlueprintTools (system Python, editor running).

    python tools/ue/build_showreel_director.py [FunctionName ...]

The director plays a command timeline (built by tools/ue/showreel_plan.py, set by ue_showreel.py) on one character and moves
the recording camera, the Unity recorder's step loop re-cut:
  T counts from StartTime at BeginPlay (negative: the Movie Render Queue warm-up runs before output frame 0), so a command at
  time t fires on output frame t * 30. Kinds:
    0 PlayLoop(clip)            1 PlayAction(clip, rate = CmdReal) full body   2 EquipLoadout(CmdInt, -1 = hands empty)
    3 WearModule(mesh)          4 RemoveModule(mesh)                          5 SetHeldBlock(CmdInt)
    6 PlayOverlay(clip)         7 root motion on/off (CmdInt) + the follow offset re-based
    8 RecenterSeamless          9 follow the hips (CmdInt: the death camera)  10 SetClipHold(left = CmdInt)
    11 PauseActions (a death's corpse)  12 bow string attached (CmdInt; finds the bow)  13 fire the arrow
    14 show the held arrow again
  FollowCamera (Unity FollowCamera): with root motion the camera's POSITION closes on the character + its offset at
  FollowDamping 1/s; during a death it follows the hips horizontally and sinks DeathDrop cm; its rotation never changes.
  Recenter (Unity RecenterSeamless): the character back on the spawn point facing the spawn yaw, and the camera moved by the
  same rigid transform in the same frame, so the picture does not change.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import bp

BPP = "/Game/UndeadLegion/Demo/Blueprints/BP_ShowreelDirector"
B = {"refPath": BPP + ".BP_ShowreelDirector"}
V = "Variables|Demo|"
C = "Class|BPUndeadSkeleton|"

FUNCS = {
    "RunCommand": ([("i", "int", True)], """
(fn RunCommand (i)
  (bind c (%(V)sGetCharacter))
  (bind clip (Utilities|Array|Get(acopy) (%(V)sGetCmdClip) i))
  (bind n (Utilities|Array|Get(acopy) (%(V)sGetCmdInt) i))
  (switch int (Utilities|Array|Get(acopy) (%(V)sGetCmdKind) i)
    (:0 (%(C)sPlayLoop :self c :Clip clip))
    (:1 (%(C)sPlayAction :self c :Clip clip :Slot "DefaultSlot" :BlendIn 0.15 :BlendOut 0.25
           :Rate (Utilities|Array|Get(acopy) (%(V)sGetCmdReal) i)))
    (:2 (%(C)sEquipLoadout :self c :Index n))
    (:3 (%(C)sWearModule :self c :Module (Utilities|Array|Get(acopy) (%(V)sGetCmdMesh) i)))
    (:4 (%(C)sRemoveModule :self c :Module (Utilities|Array|Get(acopy) (%(V)sGetCmdMesh) i)))
    (:5 (%(C)sSetHeldBlock :self c :Held (== n 1)))
    (:6 (%(C)sPlayOverlay :self c :Clip clip))
    (:7
      (%(C)sSetRootMotion :self c :On (== n 1))
      (%(V)sSetRootMotion (== n 1))
      (%(V)sSetCamOffset (- (Transformation|GetActorLocation :self (%(V)sGetCam)) (%(V)sGetSpawnLocation))))
    (:8 (CallFunction|Recenter))
    (:9 (%(V)sSetFollowHips (== n 1)))
    (:10 (%(C)sSetClipHold :self c :Left (== n 1) :Right false))
    (:11 (%(C)sPauseActions :self c))
    (:12
      (CallFunction|FindBow)
      (%(V)sSetBowAttached (== n 1)))
    (:13 (CallFunction|FireArrow))
    (:14 (Rendering|SetActorHiddenInGame :self (%(V)sGetHeldArrow) :bNewHidden false))))
"""),
    "FindBow": ([], """
(fn FindBow ()
  (for a (Class|BPUndeadSkeleton|GetWeaponActors :self (%(V)sGetCharacter))
    (bind pm (Utilities|Casting|CastToPoseableMeshComponent
               :Object (Actor|GetComponentbyClass :self a :ComponentClass "/Script/Engine.PoseableMeshComponent"))
      (:then
        (%(V)sSetBowMesh pm)
        (%(V)sSetHasBow true))
      (:CastFailed (%(V)sSetHeldArrow a)))))
"""),
    "FireArrow": ([], """
(fn FireArrow ()
  (bind arrow (%(V)sGetHeldArrow))
  (bind sm (Utilities|Casting|CastToStaticMeshComponent
             :Object (Actor|GetComponentbyClass :self arrow :ComponentClass "/Script/Engine.StaticMeshComponent"))
    (:then
      (bind p (Game|SpawnActorfromClass :Class (%(V)sGetArrowClass)
                 :SpawnTransform (Math|Transform|MakeTransform :Location (Transformation|GetSocketLocation :self sm :InSocketName "None")
                                    :Rotation (Transformation|GetActorRotation :self (%(V)sGetCharacter)))
                 :CollisionHandlingOverride "AlwaysSpawn"))
      (Rendering|SetActorHiddenInGame :self arrow :bNewHidden true))
    (:CastFailed)))
"""),
    "UpdateBow": ([("dt", "float", True)], """
(fn UpdateBow (dt)
  (bind pm (%(V)sGetBowMesh))
  (Components|PoseableMesh|ResetBoneTransformbyName :self pm :BoneName "Nock")
  (Components|PoseableMesh|ResetBoneTransformbyName :self pm :BoneName "Limb_U1")
  (Components|PoseableMesh|ResetBoneTransformbyName :self pm :BoneName "Limb_U2")
  (Components|PoseableMesh|ResetBoneTransformbyName :self pm :BoneName "Limb_L1")
  (Components|PoseableMesh|ResetBoneTransformbyName :self pm :BoneName "Limb_L2")
  (bind hand (Transformation|GetSocketLocation :self (Class|Character|GetMesh :self (%(V)sGetCharacter)) :InSocketName "RightHandSlot"))
  (bind brace (Components|PoseableMesh|GetBoneTransformbyName :self pm :BoneName "Brace" :BoneSpace "WorldSpace"))
  (bind loc (Math|Transform|InverseTransformLocation :T brace :Location hand))
  (bind along (- 0.0 (.y loc)))
  (bind lateral (Math|Float|Sqrt (+ (* (.x loc) (.x loc)) (* (.z loc) (.z loc)))))
  (bind gate (* (select (%(V)sGetBowAttached) 1.0 0.0)
                (* (Math|Float|Clamp(Float) :Value (/ (- 50.0 lateral) 5.0) :Min 0.0 :Max 1.0)
                   (Math|Float|Clamp(Float) :Value (/ along 2.5) :Min 0.0 :Max 1.0))))
  (bind target (* (Math|Float|Clamp(Float) :Value along :Min 0.0 :Max 80.0) gate))
  (bind apex (Math|Vector|MakeVector :X (* (.x loc) gate) :Y 0.0 :Z (* (.z loc) gate)))
  (bind up (>= target (%(V)sGetDraw)))
  (bind back (- (%(V)sGetDraw) (* 800.0 dt)))
  (%(V)sSetDraw (select up target (select (> back target) back target)))
  (%(V)sSetApex (select up apex (Math|Vector|Lerp(Vector) :A (%(V)sGetApex) :B apex :Alpha 0.5)))
  (bind k (Math|Float|Clamp(Float) :Value (/ (%(V)sGetDraw) 50.0) :Min 0.0 :Max 1.0))
  (bind u1 (Components|PoseableMesh|GetBoneTransformbyName :self pm :BoneName "Limb_U1" :BoneSpace "ComponentSpace"))
  (Components|PoseableMesh|SetBoneTransformbyName :self pm :BoneName "Limb_U1" :BoneSpace "ComponentSpace"
     :InTransform (Math|Transform|ComposeTransforms :A (Math|Transform|MakeTransform :Rotation (Math|Rotator|MakeRotator :Roll (* -10.0 k) :Pitch 0.0 :Yaw 0.0)) :B u1))
  (bind u2 (Components|PoseableMesh|GetBoneTransformbyName :self pm :BoneName "Limb_U2" :BoneSpace "ComponentSpace"))
  (Components|PoseableMesh|SetBoneTransformbyName :self pm :BoneName "Limb_U2" :BoneSpace "ComponentSpace"
     :InTransform (Math|Transform|ComposeTransforms :A (Math|Transform|MakeTransform :Rotation (Math|Rotator|MakeRotator :Roll (* -14.0 k) :Pitch 0.0 :Yaw 0.0)) :B u2))
  (bind l1 (Components|PoseableMesh|GetBoneTransformbyName :self pm :BoneName "Limb_L1" :BoneSpace "ComponentSpace"))
  (Components|PoseableMesh|SetBoneTransformbyName :self pm :BoneName "Limb_L1" :BoneSpace "ComponentSpace"
     :InTransform (Math|Transform|ComposeTransforms :A (Math|Transform|MakeTransform :Rotation (Math|Rotator|MakeRotator :Roll (* 10.0 k) :Pitch 0.0 :Yaw 0.0)) :B l1))
  (bind l2 (Components|PoseableMesh|GetBoneTransformbyName :self pm :BoneName "Limb_L2" :BoneSpace "ComponentSpace"))
  (Components|PoseableMesh|SetBoneTransformbyName :self pm :BoneName "Limb_L2" :BoneSpace "ComponentSpace"
     :InTransform (Math|Transform|ComposeTransforms :A (Math|Transform|MakeTransform :Rotation (Math|Rotator|MakeRotator :Roll (* 14.0 k) :Pitch 0.0 :Yaw 0.0)) :B l2))
  (Components|PoseableMesh|SetBoneLocationbyName :self pm :BoneName "Nock" :BoneSpace "WorldSpace"
     :InLocation (Math|Transform|TransformLocation :T brace
                    :Location (Math|Vector|MakeVector :X (.x (%(V)sGetApex)) :Y (- 0.0 (%(V)sGetDraw)) :Z (.z (%(V)sGetApex))))))
"""),
    "Recenter": ([], """
(fn Recenter ()
  (bind c (%(V)sGetCharacter))
  (bind cam (%(V)sGetCam))
  (bind old (Transformation|GetActorLocation :self c))
  (bind yaw (- (.yaw (Transformation|GetActorRotation :self c)) (%(V)sGetSpawnYaw)))
  (bind up (Math|Vector|MakeVector :X 0.0 :Y 0.0 :Z 1.0))
  (bind rel (Math|Vector|RotateVectorAroundAxis :InVect (- (Transformation|GetActorLocation :self cam) old) :AngleDeg (- yaw) :Axis up))
  (Transformation|SetActorLocationAndRotation :self c :NewLocation (%(V)sGetSpawnLocation)
     :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (%(V)sGetSpawnYaw)) :bSweep false :bTeleport true)
  (Transformation|SetActorLocation :self cam :NewLocation (+ (%(V)sGetSpawnLocation) rel) :bSweep false :bTeleport true)
  (Transformation|AddActorWorldRotation :self cam :DeltaRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (- yaw))
     :bSweep false :bTeleport true)
  (%(V)sSetCamOffset (Math|Vector|RotateVectorAroundAxis :InVect (%(V)sGetCamOffset) :AngleDeg (- yaw) :Axis up)))
"""),
    "FollowCamera": ([("dt", "float", True)], """
(fn FollowCamera (dt)
  (if (%(V)sGetRootMotion)
    (bind c (%(V)sGetCharacter))
    (bind cam (%(V)sGetCam))
    (bind loc (Transformation|GetActorLocation :self c))
    (bind hips (Transformation|GetSocketLocation :self (Class|Character|GetMesh :self c) :InSocketName "Hips"))
    (bind fh (%(V)sGetFollowHips))
    (bind anchor (Math|Vector|MakeVector :X (select fh (.x hips) (.x loc)) :Y (select fh (.y hips) (.y loc))
                   :Z (select fh (- (.z loc) (%(V)sGetDeathDrop)) (.z loc))))
    (bind k (- 1.0 (Math|Float|Exp (- (* (%(V)sGetFollowDamping) dt)))))
    (Transformation|SetActorLocation :self cam
       :NewLocation (Math|Vector|Lerp(Vector) :A (Transformation|GetActorLocation :self cam) :B (+ anchor (%(V)sGetCamOffset)) :Alpha k)
       :bSweep false :bTeleport true)))
"""),
}
ORDER = ["Recenter", "FollowCamera", "FindBow", "FireArrow", "UpdateBow", "RunCommand"]   # not "Execute": the DSL resolves that to RigVM|Execute

EVENTS = """
(event EventBeginPlay
  (%(V)sSetT (%(V)sGetStartTime))
  (%(V)sSetCursor 0)
  (%(V)sSetCamOffset (- (Transformation|GetActorLocation :self (%(V)sGetCam)) (%(V)sGetSpawnLocation))))

(event EventTick (DeltaSeconds)
  (%(V)sSetT (+ (%(V)sGetT) DeltaSeconds))
  (while (and (< (%(V)sGetCursor) (Utilities|Array|Length :TargetArray (%(V)sGetCmdTime)))
              (<= (Utilities|Array|Get(acopy) (%(V)sGetCmdTime) (Math|Integer|Clamp(Integer) :Value (%(V)sGetCursor) :Min 0
                     :Max (- (Utilities|Array|Length :TargetArray (%(V)sGetCmdTime)) 1))) (%(V)sGetT)))
    (CallFunction|RunCommand :i (%(V)sGetCursor))
    (%(V)sSetCursor (+ (%(V)sGetCursor) 1)))
  (CallFunction|FollowCamera :dt DeltaSeconds)
  (if (%(V)sGetHasBow)
    (CallFunction|UpdateBow :dt DeltaSeconds)))
"""


def fill(code):
    return code % {"V": V, "C": C}


def graph(name):
    return {"refPath": BPP + ".BP_ShowreelDirector:" + name}


def clear(g):
    for n in bp("find_nodes", graph=g, title="") or []:
        p = n["refPath"].split(".")[-1]
        if "FunctionEntry" not in p and "FunctionResult" not in p:
            bp("delete_node", node=n)


if __name__ == "__main__":
    only = sys.argv[1:]
    if not only or "EventGraph" in only:
        clear(graph("EventGraph"))      # first: an event graph calling a renamed function blocks every compile
    have = [g["refPath"].split(":")[-1] for g in bp("list_graphs", blueprint=B)]
    for fn in ORDER:
        if fn not in have:
            g = bp("add_function_graph", blueprint=B, graph_name=fn)
            for pn, t, inp in FUNCS[fn][0]:
                bp("add_function_param", graph=g, param_name=pn, param_type=t, input_param=inp)
    for fn in ORDER:
        if not only or fn in only:
            clear(graph(fn))
            bp("write_graph_dsl", graph=graph(fn), code=fill(FUNCS[fn][1]))
            print("wrote", fn)
    if not only or "EventGraph" in only:
        clear(graph("EventGraph"))
        bp("write_graph_dsl", graph=graph("EventGraph"), code=fill(EVENTS))
        print("wrote EventGraph")
    bp("compile_blueprint", blueprint=B, warnings_as_errors=False)
    print("compiled")
