"""Build ABP_UndeadSkeleton's variables, AnimGraph and EventGraph through the Unreal MCP BlueprintTools.

    python tools/ue/build_abp.py          (system Python; the editor must be running with the MCP server up)

The graph is the Unity controller's layer stack (CLAUDE.md 8 "Layered animation"), re-cut for Unreal, flat (the
toolset cannot build state machines):

  BaseA / BaseB players --BlendPosesByBool(UseB, 0.2 s, reset on activation)--> Slot DefaultSlot  -> cache Base
     looping clips crossfade here (PlayBase alternates A/B); root motion comes from these players
     one-shots play as dynamic montages in DefaultSlot (full body; the loop resumes under them)
  Layered(Spine1)     : Base + Slot UpperBody               -> cache Upper   (Unity: UpperBody layer, AM_UpperBody)
  Layered(LeftShoulder): Upper + Slot LeftArm over TwoWayBlend(Upper, Block_L_Idle, BlockAlpha)  -> cache Arms
                         (a HELD block: the Block_L_Idle loop weighted in/out, as Unity's ToggleHeld)
  Layered(RightShoulder): Arms + Slot RightArm
  ApplyAdditive x3    : Twitch_01..03 looping, alpha Twitch1..3 (Unity: TwitchLoop_01..03)     -> cache Body
  Layered(palms)      : Body + per hand TwoWayBlend(Hand_Idle_<side>, Grip fist, Grip<side>), weight Finger<side>
                         (Unity: LeftFingers / RightFingers layers + SkeletonWeapon.ApplyGrip)

Every montage slot is in the skeleton's DefaultGroup (slot groups are not scriptable), so one one-shot at a time
replaces the previous one - the loops, the held block and the twitches are graph players and are never stopped.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import bp, obj, ref
from ue_common import EPIC, EPIC_FINGERS, ABP_FLOATS, bn      # the Epic skeleton's bone names (UL_EPIC=1 / --epic)

ABP = "/Game/UndeadLegion/Blueprints/ABP_UndeadSkeleton"
BPR = ref(ABP)
G = {"refPath": ABP + ".ABP_UndeadSkeleton:AnimGraph"}
EG = {"refPath": ABP + ".ABP_UndeadSkeleton:EventGraph"}
ANIM = "/Game/UndeadLegion/Animations/"

FLOATS = ABP_FLOATS      # ue_common; the DEFAULTS are written by `ue_py.py ue_build.py abp_defaults` after this script (the MCP add leaves 0)


def variables():
    have = {v.get("name") if isinstance(v, dict) else str(v) for v in (bp("list_variables", blueprint=BPR) or [])}
    for n in ("BaseA", "BaseB"):
        if n not in have:
            bp("add_object_variable", blueprint=BPR, name=n, object_class="/Script/Engine.AnimSequenceBase")
    if "UseB" not in have:
        bp("add_variable", blueprint=BPR, name="UseB", type_name="bool")
    for n in FLOATS:
        if n not in have:
            bp("add_variable", blueprint=BPR, name=n, type_name="float")
    for n in ["BaseA", "BaseB", "UseB"] + list(FLOATS):
        bp("set_variable_instance_editable", blueprint=BPR, variable_name=n, instance_editable=True)
        bp("set_variable_category", blueprint=BPR, variable_name=n, category="Undead Legion")


def clear(graph, keep=("AnimGraphNode_Root",)):
    for n in bp("find_nodes", graph=graph, title="") or []:
        p = n["refPath"]
        if not any(k in p.split(".")[-1] for k in keep):
            bp("delete_node", node=n)


def node(type_id, x, y, props=None, show=()):
    n = bp("create_node", graph=G, type_id=type_id, pos={"x": x, "y": y})
    if show:
        sp = json.loads(obj("get_properties", instance=n, properties=["ShowPinForProperties"]))["ShowPinForProperties"]
        for p in sp:
            if p["propertyName"] in show:
                p["bShowPin"] = True
        obj("set_properties", instance=n, values=json.dumps({"ShowPinForProperties": sp}))
    if props:
        cur = json.loads(obj("get_properties", instance=n, properties=["Node"]))["Node"]
        cur.update(props)
        obj("set_properties", instance=n, values=json.dumps({"Node": cur}))
    return n


def pins(n):
    info = bp("get_node_infos", nodes=[n])[0]
    return {("in", p["name"]): p["pin_id"] for p in info["input_pins"]} | {("out", p["name"]): p["pin_id"] for p in info["output_pins"]}


def link(a, ap, b, bp_):
    pa, pb = pins(a), pins(b)
    if ("out", ap) not in pa:
        raise KeyError("%s has no output %s: %s" % (a["refPath"].split(".")[-1], ap, [k for k in pa if k[0] == "out"]))
    if ("in", bp_) not in pb:
        raise KeyError("%s has no input %s: %s" % (b["refPath"].split(".")[-1], bp_, [k for k in pb if k[0] == "in"]))
    bp("connect_pins", output_pin=pa[("out", ap)], input_pin=pb[("in", bp_)])


def get(var, x, y):
    return bp("create_node", graph=G, type_id="Variables|UndeadLegion|Get" + var, pos={"x": x, "y": y})


def player(clip, x, y, loop=True):
    suffix = "(additive)" if clip.startswith("Twitch_") else ""
    return node("Animation|Sequences|Play'A_%s'%s" % (clip, suffix), x, y, props={"bLoopAnimation": loop})


def save(name, src, x, y):
    s = node("Animation|CachedPoses|NewSavecachedpose...", x, y)
    obj("set_properties", instance=s, values=json.dumps({"CacheName": name}))
    link(src, "Pose", s, "Pose")
    return s


def use(name, x, y):
    return bp("create_node", graph=G, type_id="Animation|CachedPoses|Usecachedpose'%s'" % name, pos={"x": x, "y": y})


def slot(name, src, x, y):
    s = node("Animation|Montage|Slot'DefaultSlot'", x, y, props={"slotName": name})
    link(src, "Pose", s, "Source")
    return s


def layered(base, blends, filters, x, y, weights=None):
    """blends: [pose node]; filters: [[bone, ...] per blend]; weights: [var name or None]."""
    n = node("Animation|Blends|Layeredblendperbone", x, y)
    cur = json.loads(obj("get_properties", instance=n, properties=["Node"]))["Node"]
    cur["layerSetup"] = [{"branchFilters": [{"boneName": b, "blendDepth": 0} for b in f]} for f in filters]
    obj("set_properties", instance=n, values=json.dumps({"Node": cur}))
    link(base, "Pose", n, "BasePose")
    for i, b in enumerate(blends):
        link(b, "Pose", n, "BlendPoses_%d" % i)
        if weights and weights[i]:
            link(get(weights[i], x - 250, y + 180 + 60 * i), weights[i], n, "BlendWeights_%d" % i)
    return n


def anim_graph():
    clear(G)
    X = -4200
    a = node("Animation|Sequences|Play'A_Idle_01'", X, -300, props={"bLoopAnimation": True}, show=("Sequence",))
    b = node("Animation|Sequences|Play'A_Idle_01'", X, 0, props={"bLoopAnimation": True}, show=("Sequence",))
    link(get("BaseA", X - 250, -250), "BaseA", a, "Sequence")
    link(get("BaseB", X - 250, 50), "BaseB", b, "Sequence")
    sel = node("Animation|Blends|BlendPosesbybool", X + 400, -150,
               props={"bResetChildOnActivation": True, "blendTime": [0.2, 0.2]})
    link(get("UseB", X + 150, -250), "UseB", sel, "bActiveValue")
    link(b, "Pose", sel, "BlendPose_0")   # BlendListByBool: index 0 = the TRUE pose (GetActiveChildIndex)
    link(a, "Pose", sel, "BlendPose_1")
    # loops play as looping montages in "Base" (root motion only reaches CharacterMovement from montages: graph
    # players' root motion was extracted and dropped, 2026-09-30); the A/B players are the fallback under it
    sb = slot("Base", sel, X + 600, -150)
    s0 = slot("DefaultSlot", sb, X + 850, -150)
    save("Base", s0, X + 1050, -150)

    X = -2900
    up = layered(use("Base", X, -150), [slot("UpperBody", use("Base", X, 50), X + 250, 50)], [[bn("Spine1")]], X + 550, -150)
    save("Upper", up, X + 850, -150)

    X = -2200
    blk = node("Animation|Blends|TwoWayBlend", X + 250, 150)
    link(use("Upper", X, 100), "Pose", blk, "A")
    link(player("Block_L_Idle", X, 250), "Pose", blk, "B")
    link(get("BlockAlpha", X, 400), "BlockAlpha", blk, "Alpha")
    la = layered(use("Upper", X, -150), [slot("LeftArm", blk, X + 500, 150)], [[bn("LeftShoulder")]], X + 800, -150)
    save("Arms", la, X + 1100, -150)

    X = -1300
    ra = layered(use("Arms", X, -150), [slot("RightArm", use("Arms", X, 50), X + 250, 50)], [[bn("RightShoulder")]], X + 550, -150)
    prev, X = ra, -600
    for i in (1, 2, 3):
        aa = node("Animation|Blends|ApplyAdditive", X + 300 * i, -150)
        link(prev, "Pose", aa, "Base")
        link(player("Twitch_%02d" % i, X + 300 * i - 250, 100), "Pose", aa, "Additive")
        link(get("Twitch%d" % i, X + 300 * i - 250, 250), "Twitch%d" % i, aa, "Alpha")
        prev = aa
    # the Hit overlay (Unity: the additive `Hit` layer): additive montages (Hit_01 / Hit_02) in slot Hit over the
    # identity pose, applied on top of whatever plays; their legs and root carry no delta
    hit = node("Animation|Blends|ApplyAdditive", 400, -150)
    link(prev, "Pose", hit, "Base")
    link(slot("Hit", node("Animation|Poses|AdditiveIdentityPose", 0, 300), 200, 300), "Pose", hit, "Additive")
    save("Body", hit, 700, -150)

    X = 800
    hands = []
    for k, (side, lr) in enumerate((("Left", "L"), ("Right", "R"))):
        y = 150 + 400 * k
        tw = node("Animation|Blends|TwoWayBlend", X + 300, y)
        link(player("Hand_Idle_" + lr, X, y), "Pose", tw, "A")
        link(node("Animation|Sequences|Evaluate'A_Grip'", X, y + 150, props={"explicitTime": 0.0}), "Pose", tw, "B")
        link(get("Grip" + lr, X, y + 300), "Grip" + lr, tw, "Alpha")
        hands.append(tw)
    palms = lambda s: EPIC_FINGERS[s] if EPIC else ["%sHandPalm%d" % (s, i) for i in (1, 2, 3, 4)]
    # one layer per hand, chained (the toolset cannot add a second blend pin to one Layered-blend node)
    fin = layered(use("Body", X + 300, -150), [hands[0]], [palms("Left")], X + 700, -150, weights=["FingerL"])
    fin = layered(fin, [hands[1]], [palms("Right")], X + 1000, -150, weights=["FingerR"])
    root = next(n for n in bp("find_nodes", graph=G, title="") if "AnimGraphNode_Root" in n["refPath"])
    link(fin, "Pose", root, "Result")


EVENT_DSL = """
(event EventBlueprintUpdateAnimation (DeltaTimeX)
  (bind speed (Variables|UndeadLegion|GetFadeSpeed))
  (Variables|UndeadLegion|SetBlockAlpha (Math|Interpolation|FInterptoConstant :Current (Variables|UndeadLegion|GetBlockAlpha) :Target (Variables|UndeadLegion|GetBlockTarget) :DeltaTime DeltaTimeX :InterpSpeed speed))
  (Variables|UndeadLegion|SetFingerL (Math|Interpolation|FInterptoConstant :Current (Variables|UndeadLegion|GetFingerL) :Target (Variables|UndeadLegion|GetFingerTargetL) :DeltaTime DeltaTimeX :InterpSpeed speed))
  (Variables|UndeadLegion|SetFingerR (Math|Interpolation|FInterptoConstant :Current (Variables|UndeadLegion|GetFingerR) :Target (Variables|UndeadLegion|GetFingerTargetR) :DeltaTime DeltaTimeX :InterpSpeed speed))
  (Variables|UndeadLegion|SetGripL (Math|Interpolation|FInterptoConstant :Current (Variables|UndeadLegion|GetGripL) :Target (Variables|UndeadLegion|GetGripTargetL) :DeltaTime DeltaTimeX :InterpSpeed speed))
  (Variables|UndeadLegion|SetGripR (Math|Interpolation|FInterptoConstant :Current (Variables|UndeadLegion|GetGripR) :Target (Variables|UndeadLegion|GetGripTargetR) :DeltaTime DeltaTimeX :InterpSpeed speed)))

(fn PlayBase (Clip)
  (if (Variables|UndeadLegion|GetUseB)
    (Variables|UndeadLegion|SetBaseA Clip)
    (Variables|UndeadLegion|SetUseB false)
    (else
      (Variables|UndeadLegion|SetBaseB Clip)
      (Variables|UndeadLegion|SetUseB true))))

(fn SetHandTargets (GripL GripR FingerL FingerR)
  (Variables|UndeadLegion|SetGripTargetL GripL)
  (Variables|UndeadLegion|SetGripTargetR GripR)
  (Variables|UndeadLegion|SetFingerTargetL FingerL)
  (Variables|UndeadLegion|SetFingerTargetR FingerR))

(fn SetBlockTarget (Target)
  (Variables|UndeadLegion|SetBlockTarget Target))

(fn SetTwitchWeight (Index Weight)
  (switch int (- Index 1)
    (:0 (Variables|UndeadLegion|SetTwitch1 Weight))
    (:1 (Variables|UndeadLegion|SetTwitch2 Weight))
    (:2 (Variables|UndeadLegion|SetTwitch3 Weight))))

(fn GetBaseClip ()
  (return (select (Variables|UndeadLegion|GetUseB) (Variables|UndeadLegion|GetBaseB) (Variables|UndeadLegion|GetBaseA))))
"""


def functions():
    have = [str(g["refPath"]).split(":")[-1] for g in bp("list_graphs", blueprint=BPR)]
    SEQ = "/Script/Engine.AnimSequenceBase"
    for fn, params in (("PlayBase", [("Clip", SEQ, True)]), ("GetBaseClip", [("Clip", SEQ, False)]),
                       ("SetHandTargets", [(n, "float", True) for n in ("GripL", "GripR", "FingerL", "FingerR")]),
                       ("SetBlockTarget", [("Target", "float", True)]),
                       ("SetTwitchWeight", [("Index", "int", True), ("Weight", "float", True)])):
        if fn not in have:
            g = bp("add_function_graph", blueprint=BPR, graph_name=fn)
            for pn, t, inp in params:
                if t.startswith("/Script"):
                    bp("add_object_function_param", graph=g, param_name=pn, object_class={"refPath": t}, input_param=inp)
                else:
                    bp("add_function_param", graph=g, param_name=pn, param_type=t, input_param=inp)


def event_graph():
    clear(EG, keep=())
    for fn in ("PlayBase", "GetBaseClip", "SetHandTargets", "SetBlockTarget", "SetTwitchWeight"):
        g = {"refPath": ABP + ".ABP_UndeadSkeleton:" + fn}
        for n in bp("find_nodes", graph=g, title="") or []:
            if "FunctionEntry" not in n["refPath"] and "FunctionResult" not in n["refPath"]:
                bp("delete_node", node=n)
    parts = EVENT_DSL.split(chr(10) + "(fn ")   # functions are written into their own graphs
    bp("write_graph_dsl", graph=EG, code=parts[0])
    for body in parts[1:]:
        name = body.split()[0]
        bp("write_graph_dsl", graph={"refPath": ABP + ".ABP_UndeadSkeleton:" + name}, code="(fn " + body)


if __name__ == "__main__":
    steps = sys.argv[1:] or ["variables", "functions", "anim_graph", "event_graph"]
    for s in steps:
        print("==", s)
        globals()[s]()
    bp("compile_blueprint", blueprint=BPR, warnings_as_errors=False)
    print("compiled")
