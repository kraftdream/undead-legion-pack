"""Retarget a Kimodo GLB (30-joint SOMA human, Mixamo-style names) onto the shared Rigify
rig in Animations/skeleton_anim.blend as a new Action.

    blender -b Animations/skeleton_anim.blend -P tools/glb_retarget.py -- \
        --glb "External Anims/Kimodo/idle_s42.glb" --name Idle --mode idle \
        [--loop 120] [--blend 30] [--src-start 30] [--src-end N] [--time-scale 1.0] [--smooth 0] \
        [--fist 0.3] [--finger-life 0.12] [--hunch 0] [--arm-pose PRESET] [--save]

--arm-pose overrides the arms with an authored IK hand pose that follows the torso:
Kimodo has no props, so "axe on the shoulder" comes back as hanging arms. Presets are
written in the WEAPON SOCKET's own frame (position, +Y = hilt/blade direction, +Z =
back of the hand), see ARM_POSES; the socket frame is converted to the hand IK control
through the rest-pose relation between DEF-hand and DEF-weapon, so a weapon attached
to the socket with identity ends up where the preset says.

Modes
  idle    legs stay on IK with the feet at rest (a planted pose; copying a human's FK
          legs is what skated the creatures' feet); loops.
  loco    FK legs copied from the source; the hips' straight-line travel goes on `root`
          (-> Root in the export, i.e. root motion), the rest stays on `torso`; the loop
          is one gait cycle found from the feet (autocorrelation of ankle-height
          difference) unless --loop is given; the lowest point of the body mesh is kept
          on the floor by a smoothed per-frame hips correction (two-way).
  action  FK legs, root fixed, net hips drift removed (end = start), one-shot; ground
          correction = constant (median stance) + smoothed lift-only.
  death   FK legs, root fixed, hips as authored, one-shot; ground correction two-way and
          slope-limited so the lying body settles on the floor without judder.

Common
  * every mapped joint's WORLD rotation delta from its own bind pose (the GLB's T-pose)
    is applied on top of the target control's rest: target = delta * A * target_rest.
    A is a per-bone rest correction (target rest direction -> source rest direction) on
    the limbs; torso, neck, head and shoulders keep the rig's own rest.
  * hips translation is scaled by the hip-height ratio.
  * fingers: SOMA has none; constant curl (--fist) plus, in idle mode, slow per-finger
    sines (--finger-life) that loop.
  * --time-scale slerp-resamples the source, --smooth low-passes it ([1,2,1] passes).
  * IK_FK, IK_Stretch and ik_stretch are keyed/forced so nothing leaks between clips.
  * frame_set BEFORE posing on every frame: it re-applies the action being written.
"""
import os
import bpy, sys, os, math
from mathutils import Vector, Matrix, Quaternion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(k, d=None):
    return argv[argv.index(k) + 1] if k in argv else d


GLB = os.path.abspath(os.path.join(ROOT, arg("--glb")))
NAME = arg("--name", "Idle")
MODE = arg("--mode", "idle")
assert MODE in ("idle", "loco", "action", "death", "upper"), MODE
LOOP = int(arg("--loop", "0"))                 # 0 = auto (loco) / 120 (idle) / whole source (one-shots)
BLEND = int(arg("--blend", "0"))               # 0 = auto
SRC_START = int(arg("--src-start", "-1"))      # -1 = auto
SRC_END = int(arg("--src-end", "-1"))          # -1 = last source frame
TIME_SCALE = float(arg("--time-scale", "1.0"))
SMOOTH = int(arg("--smooth", "0"))
TIME_WARP = arg("--time-warp", "")             # "A:B": source frames 0..A are played over B frames (a faster wind-up), the rest unchanged
HEAD_SMOOTH = int(arg("--head-smooth", "0"))   # extra [1,2,1] passes on the neck + head source rotations only (a jerky head)
FIST = float(arg("--fist", "0.3")) if "--fingers" not in argv else 0.0
FINGER_LIFE = float(arg("--finger-life", "0.12")) if "--fingers" not in argv else 0.0
HUNCH = math.radians(float(arg("--hunch", "0")))
ARM_POSE = arg("--arm-pose", "")
ARM_KEYS = [(float(k.split(":")[0]), k.split(":")[1]) for k in arg("--arm-keys", "").split(",") if k]  # "0:bow_side,0.3:bow_draw,..."
BLEND_FROM = arg("--blend-from", "")           # ACTION[:frame]: start the clip on this pose and crossfade into the source
BLEND_IN = int(arg("--blend-in", "18"))         # frames of that crossfade
BLEND_FROM_LIFT = float(arg("--blend-from-lift", "0"))   # rig m: extra height on the first frame, faded out over the crossfade
                                                         # (= the blend-from clip's export lift minus this clip's, / 1.8, so the two meet in the engine)
BLEND_TO = arg("--blend-to", "")               # ACTION[:frame]: end the clip on this pose, crossfading over the last --blend-out frames
BLEND_OUT = int(arg("--blend-out", "20"))
ELBOW_POLE = "--elbow-pole" in argv
GROUND = arg("--ground", "")
GROUND_IGNORE = [k for k in arg("--ground-ignore", "").split(",") if k]
PLANT = float(arg("--plant-feet", "0"))         # FK legs: a foot the SOURCE has on the floor is lowered onto the floor through the leg IK when it floats more than this (rig m)
PLANT_ACTIVE = False                           # only in the final pass, after the whole-body grounding is known
PLANT_REACH = 0.985                            # a planted foot may use this much of the leg's length: the knee keeps ~20 deg of bend, never locks
HIP_DROP = None                                # per-frame torso drop (rig m) that brings every planted foot within reach, measured in pass 1b
NEED_DROP = 0.0                                # written by pose() while measuring
RENAME = arg("--rename", "")                   # "jnt": a video-mocap skeleton (hips_JNT, l_arm_JNT ...) renamed to the SOMA/Mixamo names the MAP expects
RENAME_TABLES = {
    "jnt": {"hips_JNT": "Hips", "spine_JNT": "Spine1", "spine1_JNT": "Spine2", "spine2_JNT": "Chest", "neck_JNT": "Neck1", "head_JNT": "Head",
            "l_shoulder_JNT": "LeftShoulder", "l_arm_JNT": "LeftArm", "l_forearm_JNT": "LeftForeArm", "l_hand_JNT": "LeftHand", "l_handMiddle3_JNT": "LeftHandMiddleEnd",
            "r_shoulder_JNT": "RightShoulder", "r_arm_JNT": "RightArm", "r_forearm_JNT": "RightForeArm", "r_hand_JNT": "RightHand", "r_handMiddle3_JNT": "RightHandMiddleEnd",
            "l_upleg_JNT": "LeftLeg", "l_leg_JNT": "LeftShin", "l_foot_JNT": "LeftFoot", "l_toebase_JNT": "LeftToeBase",
            "r_upleg_JNT": "RightLeg", "r_leg_JNT": "RightShin", "r_foot_JNT": "RightFoot", "r_toebase_JNT": "RightToeBase"},
    "mixamo": {"Spine": "Spine1", "Spine1": "Spine2", "Spine2": "Chest", "Neck": "Neck1",       # a Mixamo-named capture (fingers included)
               "LeftUpLeg": "LeftLeg", "LeftLeg": "LeftShin", "RightUpLeg": "RightLeg", "RightLeg": "RightShin"},
}
FINGERS_COPY = "--fingers" in argv               # copy the source's finger joints (two phalanges per finger) instead of the constant curl   # mesh-name substrings left out of the floor measure (Robe,Skirt for kneels: hems hang through the floor)                   # action mode: "twoway" = lowest point on the floor every frame (a clip whose stance changes: kneel -> stand)             # arm IK with a pole vector held outward (authored hands: no elbow inside the body)
PROP = arg("--prop", "")                        # "R:0.69": that hand props on a staff of this length (rig m): its palm is aimed at a floor point straight ahead, at the distance the staff reaches
PROP_SIDE, PROP_LEN = (PROP.split(":")[0], float(PROP.split(":")[1])) if PROP else (None, 0.0)
PROP_POINT = None                               # the floor point, found from the mean hand position in pass 1
PROP_MEAN = None
POSE_REF = arg("--pose-ref", "")               # "ACTION:frame@at": the user's reference pose for output frame `at`; every control's local delta (ref vs the generated frame) is applied while drawn/raised (weight = the anchor mask), exact on `at`
POSE_DELTAS = None                              # {control: (loc delta, rot delta, w_at)} once measured
TORSO_REF = arg("--torso-ref", "")             # ACTION[:frame]: the torso control's world rotation/position from that pose replace the clip's MEAN (the sway stays)
HAND_OFFSET = Vector([float(v) for v in arg("--hand-offset", "0,0,0").split(",")])   # rig m, added to the reference/computed propping hand position
HAND_REF = arg("--hand-ref", "")               # ACTION[:frame]: the propping hand's socket position from that pose (with --prop)
TORSO_REF_POSE = None; HAND_REF_POS = None; TORSO_TRACE = []; TORSO_FIX = None
PROP_VERTICAL = "--prop-vertical" in argv        # the weapon hangs straight down: floor point directly below the hand, the hand pinned at the staff's top height
PROP_DAMP = float(arg("--prop-damp", "0.2"))    # the propping hand keeps this fraction of its motion about its mean position (it rests on the staff)
PROP_TRACE = []
WRIST_TWIST = {k.split(":")[0]: math.radians(float(k.split(":")[1])) for k in arg("--wrist-twist", "").split(",") if k}   # "L:60": turn that forearm about its own axis every frame (+ = counterclockwise seen from the hand looking up the arm)
HAND_CLEAR = {}                                 # "R:0.22,0.18": keep that hand's socket outside an ellipse around the torso (rig m half-widths sideways, front-back)
for k in arg("--hand-clear", "").split(";"):
    if k:
        side_, _, ab = k.partition(":")
        HAND_CLEAR[side_] = tuple(float(v) for v in ab.split(",")) if ab else (0.22, 0.18)
HAND_CLEAR_LOG = {}
AIM_FORWARD = arg("--aim-forward", "")          # "L": twist the upper body so that arm's horizontal direction (shoulder -> hand, over the frames it is raised) points forward
AIM_LINE = arg("--aim-line", "shot")            # which line points forward: shot = draw hand -> bow hand, sight = head -> bow hand, arm = bow shoulder -> bow hand
assert AIM_LINE in ("shot", "sight", "arm")
AIM_OFFSET = math.radians(float(arg("--aim-offset", "0")))   # deg, + = left: where that line is aimed instead of dead ahead
ANCHOR = float(arg("--anchor", "0"))            # 0..1: while drawn, swing the draw arm (FK, about the vertical through its shoulder) until the string hand lies on the sight plane (head -> bow hand): the archer's anchor at the cheek
ANCHOR_GAP = float(arg("--anchor-gap", "0"))    # rig m: the anchored string hand stays this far OUT of the sight plane (user: "not so close to the head")
HEAD_AIM = "--head-aim" in argv                 # while the bow arm is raised, turn the head's yaw to look along the sight line (head -> bow hand)
BOW_SQUARE = "--bow-square" in argv             # while drawn, turn the bow hand so its hilt axis (the bow's limbs) is perpendicular to the arrow
ANCHOR_ROLL = math.radians(float(arg("--anchor-roll", "45")))   # deg: the anchored hand's roll about its fingers from the forearm's zero-twist hand
ANCHOR_ROLL_SIGN = 0.0
ANCHOR_PREV = {}                                # last frame's swing root and swivel sign, for continuity
ANCHOR_LOG = [0.0, 0]
AIM_TRACE = []                                  # pass 1: per frame (aim-line yaw from forward, both hands raised?)
AIM_PEAK = 1.0                                  # the full turn, for the step's lift profile
AIM_BODY = float(arg("--aim-body", "1.0"))      # share of the aim turn taken by the WHOLE body (pelvis + feet); the rest is a spine twist above the pelvis (1 = side-on archer, 0 = pelvis stays on the idle heading)
STEP_LIFT = float(arg("--step-lift", "0.04"))   # rig m: how high the stepping foot lifts mid-transition
HIPS_DROP = float(arg("--hips-drop", "0"))      # rig m: an extra, deliberate crouch on top of the reach drop; with a blend-from/to it fades with the crossfades
AIM_FIX = None                                  # pass 2: per frame yaw to apply to the whole body
PELVIS_FIX = None                               # pass 2: per frame yaw that holds the pelvis on the idle's heading (used by 1 - AIM_BODY)
AIM_HAND = None                                 # pass 2: per frame weight of the string-hand re-aim (both hands raised)
BOW_UP = None                                   # pass 2: per frame weight of the bow squaring (the bow arm raised, smoothed)
ANCHOR_W = None                                 # pass 2: per frame weight of the anchor (the raised mask, smoothed wider: a 120 deg elbow swivel needs ~16 frames)
AIM_HANDS = ("Left", "Right") if AIM_FORWARD == "L" else ("Right", "Left")
STILL = [k for k in arg("--still-joints", "").split(",") if k]   # source joints (renamed, pre-mirror names) whose rotation vs their parent is frozen to the clip's typical value (a hand the tracker lost)
STANCE = {k.split(":")[0]: float(k.split(":")[1]) for k in arg("--stance", "").split(",") if k}   # idle mode: "L:0.03,R:-0.03" moves each resting foot forward (+, rig m)
HEADING = arg("--heading", "auto")             # auto: rotate the source so the hips' mean yaw vs the bind is 0 (a video capture faces wherever the performer stood); keep: as is; <deg>: fixed
HEAD_DAMP = float(arg("--head-damp", "1.0"))    # 0..1: scales the neck+head rotation away from rest (1 = as authored)
TRAVEL_AXIS = arg("--travel-axis", "auto")
LOCK_L = float(arg("--lock-left-hand", "0"))   # >0: pin the left hand on the right hand's weapon this far down the handle (rig m)
LOCK_L_ROLL = math.radians(float(arg("--lock-left-roll", "0")))  # extra roll of the locked left hand about the handle
MIRROR = "--mirror" in argv                     # swap left/right and flip the source across its forward axis (X -> -X)      # loco: auto = dominant axis, x = sideways (strafes), y = forward/back
SAVE = "--save" in argv
LOOPING = MODE in ("idle", "loco")
FK_LEGS = MODE not in ("idle", "upper")   # upper: a one-shot with the legs kept on IK at rest (an upper-body action played over an idle or a walk)

# source joint -> (target control, align rest direction?, source child giving the direction)
MAP = [
    ("Hips",          "torso",          False, None),
    ("Hips",          "spine_fk",       False, None),
    ("Spine1",        "spine_fk.001",   False, None),
    ("Spine2",        "spine_fk.002",   False, None),
    ("Chest",         "spine_fk.003",   False, None),
    ("Neck1",         "neck",           False, None),
    ("Head",          "head",           False, None),
    ("LeftShoulder",  "shoulder.L",     False, None),
    ("RightShoulder", "shoulder.R",     False, None),
    ("LeftArm",       "upper_arm_fk.L", True,  "LeftForeArm"),
    ("LeftForeArm",   "forearm_fk.L",   True,  "LeftHand"),
    ("LeftHand",      "hand_fk.L",      True,  "LeftHandMiddleEnd"),
    ("RightArm",      "upper_arm_fk.R", True,  "RightForeArm"),
    ("RightForeArm",  "forearm_fk.R",   True,  "RightHand"),
    ("RightHand",     "hand_fk.R",      True,  "RightHandMiddleEnd"),
]
LEG_MAP = [
    ("LeftLeg",       "thigh_fk.L",     True,  "LeftShin"),
    ("LeftShin",      "shin_fk.L",      True,  "LeftFoot"),
    ("LeftFoot",      "foot_fk.L",      True,  "LeftToeBase"),
    ("LeftToeBase",   "toe_fk.L",       False, None),
    ("RightLeg",      "thigh_fk.R",     True,  "RightShin"),
    ("RightShin",     "shin_fk.R",      True,  "RightFoot"),
    ("RightFoot",     "foot_fk.R",      True,  "RightToeBase"),
    ("RightToeBase",  "toe_fk.R",       False, None),
]
if FK_LEGS:
    MAP = MAP + LEG_MAP
FINGER_MAP = []
for P, s_ in (("Left", "L"), ("Right", "R")):
    for jn, ctl in (("Thumb", "thumb"), ("Index", "f_index"), ("Middle", "f_middle"), ("Ring", "f_ring"), ("Pinky", "f_pinky")):
        FINGER_MAP += [(P + "Hand" + jn + "1", ctl + ".01." + s_, True, P + "Hand" + jn + "2"),
                       (P + "Hand" + jn + "2", ctl + ".02." + s_, True, P + "Hand" + jn + "3")]
if FINGERS_COPY:
    MAP = MAP + FINGER_MAP                       # the third phalanx follows its parent at rest (the capture's fingertips are noise)
LEVELS = [["torso"], ["spine_fk"], ["spine_fk.001"], ["spine_fk.002"], ["spine_fk.003"],
          ["neck", "shoulder.L", "shoulder.R", "thigh_fk.L", "thigh_fk.R"],
          ["head", "upper_arm_fk.L", "upper_arm_fk.R", "shin_fk.L", "shin_fk.R"],
          ["forearm_fk.L", "forearm_fk.R", "foot_fk.L", "foot_fk.R"],
          ["hand_fk.L", "hand_fk.R", "toe_fk.L", "toe_fk.R"],
          [t for _, t, _, _ in FINGER_MAP if ".01." in t], [t for _, t, _, _ in FINGER_MAP if ".02." in t]]
TARGETS = {t for _, t, _, _ in MAP}
LEVELS = [[t for t in lv if t in TARGETS] for lv in LEVELS]
IKFK_ARMS = ["upper_arm_parent.L", "upper_arm_parent.R"]
IKFK_LEGS = ["thigh_parent.L", "thigh_parent.R"]
FINGER_MASTERS = ["thumb.01_master", "f_index.01_master", "f_middle.01_master", "f_ring.01_master", "f_pinky.01_master"]
FINGERS = [m + "." + s for s in ("L", "R") for m in FINGER_MASTERS]

# --arm-pose presets. Rig units at REST (character ~0.94 m tall, right side = -X,
# forward = -Y, up = +Z). Per hand: socket position, +Y (hilt/blade), +Z (back of hand).
def _norm(v):
    v = Vector(v); return v.normalized()
_UP, _FWD, _DOWN = Vector((0, 0, 1)), Vector((0, -1, 0)), Vector((0, 0, -1))
_R_HANG, _L_HANG = Vector((-0.235, -0.045, 0.47)), Vector((0.235, -0.045, 0.47))
_2H_D = _norm((-0.35, 0.45, 0.82))                # hilt: up, back over the right shoulder, a little outward
_2H_R = Vector((-0.14, -0.10, 0.70))               # right hand just in front of the right shoulder
_2H_L = _2H_R - _2H_D * 0.085                      # left hand a hand's width further down the shaft
ARM_POSES = {
    # weapon resting on the right shoulder, both hands on the hilt
    "two_handed_shoulder": {"R": (_2H_R, _2H_D, _norm((-0.8, -0.6, 0.0))), "L": (_2H_L, _2H_D, _norm((0.4, -0.9, 0.0)))},
    # leaning on a staff planted in front: hands stacked on its upper third, staff along +Y up
    "propped":            {"R": (Vector((-0.035, -0.20, 0.50)), _UP, _FWD), "L": (Vector((0.035, -0.20, 0.55)), _UP, _FWD)},
    # staff held upright at the right side (grip on the upper third of the staff)
    "staff_side":         {"R": (_R_HANG, _UP, _norm((-1, 0, 0)))},
    # bow hanging in the left hand, limbs vertical
    "bow_side":           {"L": (_L_HANG, _UP, _norm((1, 0, 0)))},
    # sword hanging in the right hand, blade forward-down, palm to the thigh
    "sword_side":         {"R": (_R_HANG, _norm((0, -0.75, -0.65)), _norm((-1, 0, 0)))},
    # wand held up in front, forearm raised
    "wand_front":         {"R": (Vector((-0.13, -0.26, 0.60)), _norm((0, -0.9, 0.35)), _norm((0, -0.3, 0.9)))},
    # archery (character faces -Y, right side is -X): bow arm straight out, string hand at
    # the bow grip (nock), then at the right cheek (draw), then snapped back open (release).
    # The string hand's hilt axis points along the arrow so an Arrow on RightWeaponSocket
    # aims forward; its back faces out to the right.
    "bow_aim":            {"L": (Vector((0.06, -0.42, 0.74)), _norm((0.08, 0, 1)), _FWD),
                           "R": (Vector((0.03, -0.36, 0.73)), _FWD, _norm((-0.9, 0, 0.4)))},
    "bow_draw":           {"L": (Vector((0.06, -0.42, 0.74)), _norm((0.08, 0, 1)), _FWD),
                           "R": (Vector((-0.10, -0.06, 0.80)), _FWD, _norm((-0.9, 0, 0.4)))},
    "bow_release":        {"L": (Vector((0.06, -0.42, 0.74)), _norm((0.08, 0, 1)), _FWD),
                           "R": (Vector((-0.22, -0.02, 0.74)), _norm((-0.3, -0.9, 0.3)), _norm((-0.9, 0, 0.4)))},
    # no override (a key that hands the arms back to the source)
    "free":               {},
    # both hands high overhead, palms forward (summoning chant)
    "summon_high":        {"L": (Vector((0.20, -0.10, 1.00)), _norm((0.3, -0.2, 0.9)), _norm((0, 1, 0.2))),
                           "R": (Vector((-0.20, -0.10, 1.00)), _norm((-0.3, -0.2, 0.9)), _norm((0, 1, 0.2)))},
    # arms spread wide at shoulder height, palms forward (taunt)
    "arms_wide":          {"L": (Vector((0.44, -0.04, 0.80)), _norm((1, 0, 0.25)), _norm((0, 1, 0))),
                           "R": (Vector((-0.44, -0.04, 0.80)), _norm((-1, 0, 0.25)), _norm((0, 1, 0)))},
}
for _t, _n in ARM_KEYS:
    assert _n in ARM_POSES or _n in ("base", "base_out"), "unknown arm pose %s" % _n   # base/base_out come from --blend-from
assert ARM_POSE == "" or ARM_POSE in ARM_POSES, "unknown --arm-pose %r (have %s)" % (ARM_POSE, sorted(ARM_POSES))


def log(*a):
    print("[retarget]", *a); sys.stdout.flush()


def update():
    bpy.context.view_layer.update()


def smooth01(u):
    u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


def smooth_series(xs, passes):
    xs = list(xs)
    for _ in range(passes):
        xs = [xs[0]] + [(xs[i - 1] + 2 * xs[i] + xs[i + 1]) / 4.0 for i in range(1, len(xs) - 1)] + [xs[-1]]
    return xs


rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
scene = bpy.context.scene
assert abs(scene.render.fps - 30) < 1e-6
pbs = rig.pose.bones


def controls():
    return [b.name for b in pbs if not b.name.startswith(("DEF-", "MCH-", "ORG-", "VIS_"))]


def zero_pose():
    for pb in pbs:
        pb.matrix_basis.identity()
        if pb.ik_stretch != 0.0:
            pb.ik_stretch = 0.0          # rigid IK chains: see tools/rig_lib_no_stretch.py
    for b in IKFK_ARMS + IKFK_LEGS:
        pbs[b]["IK_FK"] = 0.0
        if "IK_Stretch" in pbs[b]:
            pbs[b]["IK_Stretch"] = 0.0
    update()


def world_rot(pb):
    return (rig.matrix_world @ pb.matrix).to_quaternion()


def bone_dir(pb):
    return ((rig.matrix_world @ pb.matrix).to_3x3() @ Vector((0, 1, 0))).normalized()


def set_world(pb, q, translation=None):
    m = pb.matrix.copy()
    Mw = rig.matrix_world
    Rm = (Mw.inverted().to_3x3() @ q.to_matrix()).to_4x4()
    Rm.translation = m.translation if translation is None else Mw.inverted() @ translation
    pb.matrix = Rm


# ------------------------------------------------------------- 1. target rest
if rig.animation_data is not None:
    rig.animation_data.action = None
zero_pose()
T_rest = {}
for _, tgt, _, _ in MAP:
    pb = pbs[tgt]
    T_rest[tgt] = (world_rot(pb), bone_dir(pb), (rig.matrix_world @ pb.matrix).translation.copy())
hip_z_t = (rig.matrix_world @ rig.data.bones["DEF-spine"].head_local).z
log("mode %s | target hip pivot z %.4f" % (MODE, hip_z_t))
TORSO_REST = (rig.matrix_world @ pbs["torso"].matrix).copy()
PELVIS_FWD_LOCAL = (rig.matrix_world @ pbs["DEF-spine"].matrix).to_3x3().inverted() @ Vector((0, -1, 0))   # the pelvis bone's local axis that points forward at rest
WRIST_REST = {}                                  # hand vs forearm at rest, for limit_wrist()
for _side in ("L", "R"):
    WRIST_REST[_side] = world_rot(pbs["forearm_fk." + _side]).inverted() @ world_rot(pbs["hand_fk." + _side])
HEAD_FACE_LOCAL = rig.data.bones["DEF-spine.006"].matrix_local.to_3x3().inverted() @ Vector((0, -1, 0))   # the head bone's axis that faces forward at rest
# hand IK control <- socket frame: the constant relation at rest between the hand control and the socket bone
FOOTIK_FROM_FOOT = {s: (rig.matrix_world @ pbs["DEF-foot." + s].matrix).inverted() @ (rig.matrix_world @ pbs["foot_ik." + s].matrix) for s in ("L", "R")}
LEG_LEN = {s: ((rig.matrix_world @ pbs["DEF-thigh." + s].matrix).translation - (rig.matrix_world @ pbs["DEF-shin." + s].matrix).translation).length
              + ((rig.matrix_world @ pbs["DEF-shin." + s].matrix).translation - (rig.matrix_world @ pbs["DEF-foot." + s].matrix).translation).length for s in ("L", "R")}
FOOT_SOLE = {s: ((rig.matrix_world @ pbs["DEF-foot." + s].matrix).translation.z,
                 ((rig.matrix_world @ pbs["DEF-toe." + s].matrix) @ Vector((0, pbs["DEF-toe." + s].length, 0))).z) for s in ("L", "R")}   # ankle / toe-tip height with the sole on the floor
# Unity's Humanoid gives the toes ONE muscle, "Toes Up-Down", hinged about the T-pose's WORLD
# sideways axis (measured with HumanPoseHandler: 50 deg about world (1,0,0) on the shared avatar;
# the toe bone itself yaws 10 deg outward, so its own X is not that axis). Any other toe rotation
# is dropped on import; with the boot resting on the toe cap that moved the sole 1 cm
# (Impaled_Rise crouch: Humanoid toes 6-13 deg off the Generic playback). Every authored toe
# keeps only the hinge component, so Humanoid and Blender agree.
TOE_REST_REL = {s: ((rig.matrix_world @ pbs["DEF-foot." + s].matrix).to_quaternion().inverted() @ (rig.matrix_world @ pbs["DEF-toe." + s].matrix).to_quaternion()) for s in ("L", "R")}
TOE_HINGE = {s: ((rig.matrix_world @ pbs["DEF-toe." + s].matrix).to_3x3().inverted() @ Vector((1, 0, 0))).normalized() for s in ("L", "R")}


WRIST_LIMIT = math.radians(float(arg("--wrist-limit", "60")))   # max twist of a hand about its forearm's axis; the excess becomes forearm pronation


def limit_wrist(side):
    """Keep the hand's twist about the forearm axis within WRIST_LIMIT, moving the excess into the
    forearm (pronation) while the hand keeps its WORLD rotation. A hand keyed in world space can sit
    180 deg twisted on its forearm and look fine in Blender; Unity's Humanoid splits that twist
    between hand and forearm and wraps at 180 deg, snapping the forearm 178 deg on those frames
    (Shoot_01/02 at the draw, 2026-09-22)."""
    fa = pbs["forearm_fk." + side]; hf = pbs["hand_fk." + side]
    if side not in WRIST_REST:
        return
    q_fa = world_rot(fa); q_h = world_rot(hf)
    rel = WRIST_REST[side].inverted() @ q_fa.inverted() @ q_h            # hand vs its rest relation, in the hand's frame
    s_ = rel.y                                                            # twist about the hand's own Y (along the forearm)
    tw = 2.0 * math.atan2(s_, rel.w)
    tw = (tw + math.pi) % (2 * math.pi) - math.pi
    if abs(tw) <= WRIST_LIMIT:
        return
    excess = tw - math.copysign(WRIST_LIMIT, tw)
    axis = (q_fa @ Vector((0, 1, 0))).normalized()
    set_world(fa, Quaternion(axis, excess) @ q_fa)                       # pronate the forearm by the excess
    update()
    set_world(hf, q_h)                                                    # the hand keeps its world rotation
    update()


def hinge_toes():
    for side in ("L", "R"):
        foot_q = (rig.matrix_world @ pbs["DEF-foot." + side].matrix).to_quaternion()
        toe_q = (rig.matrix_world @ pbs["DEF-toe." + side].matrix).to_quaternion()
        rel = TOE_REST_REL[side].inverted() @ foot_q.inverted() @ toe_q       # toe vs its rest, in the toe's own frame
        a = TOE_HINGE[side]
        v = Vector((rel.x, rel.y, rel.z)); p = v.dot(a) * a
        tw = Quaternion((rel.w, p.x, p.y, p.z)).normalized()                  # the hinge component only
        q = foot_q @ TOE_REST_REL[side] @ tw
        for ctrl in ("toe_fk." + side, "toe_ik." + side):
            set_world(pbs[ctrl], q)
        update()


HAND_FROM_SOCKET = {}
for side in ("L", "R"):
    hand_m = (rig.matrix_world @ pbs["hand_ik." + side].matrix).copy()
    sock_m = (rig.matrix_world @ pbs["DEF-weapon." + side].matrix).copy()
    HAND_FROM_SOCKET[side] = sock_m.inverted() @ hand_m            # socket_world @ this = hand_world


def socket_frame(pos, y, z):
    """4x4 world matrix of a socket: columns X, Y (hilt), Z (back of hand), origin pos."""
    y = Vector(y).normalized(); z = Vector(z)
    x = y.cross(z).normalized(); z = x.cross(y).normalized()
    m = Matrix.Identity(4)
    for i in range(3):
        m[i][0], m[i][1], m[i][2] = x[i], y[i], z[i]
    m.translation = Vector(pos)
    return m

# ------------------------------------------------------------- 1b. blend-from pose
BASE = None
if BLEND_FROM:
    bname, _, bframe = BLEND_FROM.partition(":")
    bact = bpy.data.actions[bname]
    rig.animation_data.action = bact
    if hasattr(rig.animation_data, "action_slot") and bact.slots:
        rig.animation_data.action_slot = bact.slots[0]
    scene.frame_set(int(bframe) if bframe else int(round(bact.frame_range[0]))); update()
    BASE = {"rot": {tgt: world_rot(pbs[tgt]) for tgt in TARGETS},
            "hips": (rig.matrix_world @ pbs["torso"].matrix).translation.copy(),
            "fist": {n: (pbs[n].rotation_euler.x if pbs[n].rotation_mode != 'QUATERNION' else FIST) for n in FINGERS}}
    # the base's hand socket frames in TORSO-REST space, so they follow the torso like the presets
    torso_base = (rig.matrix_world @ pbs["torso"].matrix).copy()
    to_rest = TORSO_REST @ torso_base.inverted()
    for side in ("L", "R"):
        sock = to_rest @ (rig.matrix_world @ pbs["DEF-weapon." + side].matrix)
        pos = sock.translation.copy(); y = (sock.to_3x3() @ Vector((0, 1, 0))).normalized(); z = (sock.to_3x3() @ Vector((0, 0, 1))).normalized()
        ARM_POSES.setdefault("base", {})[side] = (pos, y, z)
        ARM_POSES.setdefault("base_out", {})[side] = (pos - y * (0.36 + 0.02) if side == "R" else pos, y, z)   # right hand: the blade slid out along the hilt
    rig.animation_data.action = None
    zero_pose()
    log("blend-from %s: hips %s, right hilt axis %s, %d frames of crossfade" % (BLEND_FROM, tuple(round(v, 3) for v in BASE["hips"]), tuple(round(v, 2) for v in ARM_POSES["base"]["R"][1]), BLEND_IN))

END = None
if BLEND_TO:
    ename, _, eframe = BLEND_TO.partition(":")
    eact = bpy.data.actions[ename]
    rig.animation_data.action = eact
    if hasattr(rig.animation_data, "action_slot") and eact.slots:
        rig.animation_data.action_slot = eact.slots[0]
    scene.frame_set(int(eframe) if eframe else int(round(eact.frame_range[0]))); update()
    END = {"rot": {tgt: world_rot(pbs[tgt]) for tgt in TARGETS},
           "hips": (rig.matrix_world @ pbs["torso"].matrix).translation.copy(),
           "fist": {n: (pbs[n].rotation_euler.x if pbs[n].rotation_mode != 'QUATERNION' else FIST) for n in FINGERS}}
    rig.animation_data.action = None
    zero_pose()
    log("blend-to %s over the last %d frames" % (BLEND_TO, BLEND_OUT))

def _sample_ref(spec):
    name, _, frame = spec.partition(":")
    act_ = bpy.data.actions[name]; rig.animation_data.action = act_
    if hasattr(rig.animation_data, "action_slot") and act_.slots: rig.animation_data.action_slot = act_.slots[0]
    scene.frame_set(int(frame) if frame else int(round(act_.frame_range[0]))); update()
    out = ((rig.matrix_world @ pbs["torso"].matrix).copy(), (rig.matrix_world @ pbs["DEF-weapon.R"].matrix).translation.copy(), (rig.matrix_world @ pbs["DEF-weapon.L"].matrix).translation.copy())
    rig.animation_data.action = None; zero_pose()
    return out
if TORSO_REF:
    TORSO_REF_POSE = _sample_ref(TORSO_REF)[0]
    log("torso-ref %s: torso at %s, %s deg" % (TORSO_REF, tuple(round(v, 3) for v in TORSO_REF_POSE.translation), tuple(round(math.degrees(v)) for v in TORSO_REF_POSE.to_euler())))
if HAND_REF:
    r_ = _sample_ref(HAND_REF); HAND_REF_POS = {"R": r_[1], "L": r_[2]}
    log("hand-ref %s: sockets R %s L %s" % (HAND_REF, tuple(round(v, 3) for v in r_[1]), tuple(round(v, 3) for v in r_[2])))

# ------------------------------------------------------------- 2. source
before = set(bpy.data.objects)
acts_before = set(bpy.data.actions)
bpy.ops.import_scene.gltf(filepath=GLB)
new = [o for o in bpy.data.objects if o not in before]
SRC_ARM = next(o for o in new if o.type == 'ARMATURE')
src_act = SRC_ARM.animation_data.action if SRC_ARM.animation_data else None
assert src_act is not None, "GLB armature carries no action"
n_src = int(round(src_act.frame_range[1] - src_act.frame_range[0])) + 1
f_src0 = int(round(src_act.frame_range[0]))
log("source %s: %d joints, %d frames" % (os.path.basename(GLB), len(SRC_ARM.data.bones), n_src))
if RENAME:
    # two phases: the mixamo table chains names (Spine -> Spine1 -> Spine2), a direct rename would collide
    hit = [old_n for old_n in RENAME_TABLES[RENAME] if old_n in SRC_ARM.data.bones]
    for old_n in hit:
        SRC_ARM.data.bones[old_n].name = "__ren__" + RENAME_TABLES[RENAME][old_n]
    for old_n in hit:
        SRC_ARM.data.bones["__ren__" + RENAME_TABLES[RENAME][old_n]].name = RENAME_TABLES[RENAME][old_n]
    log("renamed %d source joints (%s)" % (len(RENAME_TABLES[RENAME]), RENAME))
S = {b.name: b for b in SRC_ARM.data.bones}
S_PARENT = {b.name: (b.parent.name if b.parent else None) for b in SRC_ARM.data.bones}
S_rest = {n: ((SRC_ARM.matrix_world @ b.matrix_local).to_quaternion(),
              (SRC_ARM.matrix_world @ b.head_local).copy()) for n, b in S.items()}


def _mirror_pose(p):
    """Reflect a {joint: (world quat, world pos)} dict across the source's YZ plane
    (sideways is X: walks travel along Y) and swap Left*/Right* joints. A rotation R
    reflected by M = diag(-1,1,1) is M R M: same x, negated y and z in the quaternion."""
    out = {}
    for n, (q, pos) in p.items():
        m = "Right" + n[4:] if n.startswith("Left") else "Left" + n[5:] if n.startswith("Right") else n
        out[m] = (Quaternion((q.w, q.x, -q.y, -q.z)), Vector((-pos.x, pos.y, pos.z)))
    return out


if MIRROR:
    S_rest = _mirror_pose(S_rest)
hip_z_s = S_rest["Hips"][1].z
scale = hip_z_t / hip_z_s
log("source hips rest z %.4f -> scale %.4f" % (hip_z_s, scale))

A = {}
for src, tgt, align, kid in MAP:
    if align:
        if kid not in S_rest and kid.endswith("MiddleEnd"):
            kid = kid.replace("MiddleEnd", "Middle1")            # knuckle instead of fingertip: same hand direction
        d_s = (S_rest[kid][1] - S_rest[src][1]).normalized()
        A[tgt] = T_rest[tgt][1].rotation_difference(d_s)
    else:
        A[tgt] = Quaternion((1, 0, 0, 0))

SRC = []
for i in range(n_src):
    scene.frame_set(f_src0 + i); update()
    SRC.append({n: ((SRC_ARM.matrix_world @ SRC_ARM.pose.bones[n].matrix).to_quaternion(),
                    (SRC_ARM.matrix_world @ SRC_ARM.pose.bones[n].head).copy()) for n in S})
for j in STILL:
    # freeze the joint's rotation relative to its parent to the medoid over the clip (the frame whose
    # relative rotation is closest to all others): a video tracker that loses a hanging hand flaps it
    # 70 deg in a frame while the forearm stays calm (the propped idle, 2026-09-21)
    par = S_PARENT[j]
    rel = [p[par][0].inverted() @ p[j][0] for p in SRC]
    idx = range(0, len(rel), max(1, len(rel) // 60))
    best = min(idx, key=lambda i: sum(min(rel[i].rotation_difference(rel[k]).angle, 2 * math.pi - rel[i].rotation_difference(rel[k]).angle) for k in idx))
    for p in SRC:
        p[j] = (p[par][0] @ rel[best], p[j][1])
    log("still joint %s: rotation vs %s frozen to frame %d's" % (j, par, best))
if MIRROR:
    SRC = [_mirror_pose(p) for p in SRC]
    log("mirrored the source left<->right")
if HEADING != "keep":
    # hips yaw relative to the bind pose, mean over the clip (Kimodo ~0; the recorded idle stood 49 deg off,
    # which the retarget copied onto the pelvis while the IK feet stayed at rest: both legs twisted 49 deg)
    if HEADING == "auto":
        sx = sy = 0.0
        for p in SRC:
            v = (p["Hips"][0] @ S_rest["Hips"][0].inverted()) @ Vector((0, 1, 0))
            sx += v.x; sy += v.y
        yaw = math.atan2(-sx, sy)                    # +yaw = counter-clockwise from above (Blender's Z rotation)
    else:
        yaw = math.radians(float(HEADING))
    if abs(yaw) > math.radians(0.5):
        Rz = Quaternion((0, 0, 1), -yaw)
        SRC = [{n: (Rz @ q, Rz @ pos) for n, (q, pos) in p.items()} for p in SRC]
        log("heading: removed %.1f deg of hips yaw from the source" % math.degrees(yaw))
for o in new:
    bpy.data.objects.remove(o, do_unlink=True)
for a in list(bpy.data.actions):
    if a not in acts_before:
        bpy.data.actions.remove(a)


def _lerp_pose(a, b, u):
    out = {}
    for n in a:
        qb = b[n][0].copy()
        if a[n][0].dot(qb) < 0:
            qb.negate()
        out[n] = (a[n][0].slerp(qb, u), a[n][1].lerp(b[n][1], u))
    return out


if SRC_END >= 0:
    SRC = SRC[:SRC_END + 1]
if TIME_WARP:
    wa, wb = (int(v) for v in TIME_WARP.split(":"))
    assert 0 < wb <= wa < len(SRC), "time-warp A:B needs 0 < B <= A < source frames"
    res = []
    for i in range(wb):
        t = i * wa / float(wb); k = min(len(SRC) - 2, int(math.floor(t)))
        res.append(_lerp_pose(SRC[k], SRC[k + 1], t - k))
    SRC = res + SRC[wa:]
    log("time-warp: source frames 0..%d played over %d frames -> %d source frames" % (wa, wb, len(SRC)))
if TIME_SCALE != 1.0:
    m = len(SRC) - 1
    res = []
    for i in range(int(math.floor(m * TIME_SCALE)) + 1):
        t = i / TIME_SCALE
        k = min(m - 1, int(math.floor(t))); u = min(1.0, t - k)
        res.append(_lerp_pose(SRC[k], SRC[k + 1], u))
    log("time-scale x%.2f: %d -> %d source frames" % (TIME_SCALE, len(SRC), len(res)))
    SRC = res
for _ in range(SMOOTH):
    SRC = [SRC[0]] + [_lerp_pose(_lerp_pose(SRC[i - 1], SRC[i + 1], 0.5), SRC[i], 0.5) for i in range(1, len(SRC) - 1)] + [SRC[-1]]
for _ in range(HEAD_SMOOTH):
    sm = [SRC[0]] + [_lerp_pose(_lerp_pose(SRC[i - 1], SRC[i + 1], 0.5), SRC[i], 0.5) for i in range(1, len(SRC) - 1)] + [SRC[-1]]
    for i in range(len(SRC)):
        for j in ("Neck", "Neck1", "Head"):
            if j in SRC[i]:
                SRC[i][j] = sm[i][j]
n_src = len(SRC)

# ------------------------------------------------------------- 3. segment / loop
if MODE == "loco":
    # gait period from the ankle-height difference (one full cycle = both steps)
    sig = [SRC[i]["LeftFoot"][1].z - SRC[i]["RightFoot"][1].z for i in range(n_src)]
    mean = sum(sig) / len(sig); sig = [s - mean for s in sig]
    corr = {}
    for p in range(12, n_src // 2):
        num = sum(sig[i] * sig[i + p] for i in range(n_src - p))
        den = math.sqrt(sum(s * s for s in sig[:n_src - p]) * sum(s * s for s in sig[p:])) or 1e-9
        corr[p] = num / den
    best = max(corr.values())
    # ONE gait cycle = the first local maximum of the autocorrelation that is clearly
    # positive; the global maximum of a shambling gait lands on 3-4 cycles (142 frames,
    # measured) because single cycles correlate only weakly with each other
    lags = sorted(corr)
    period = 0
    for i in range(1, len(lags) - 1):
        p = lags[i]
        if corr[p] >= corr[lags[i - 1]] and corr[p] >= corr[lags[i + 1]] and corr[p] >= max(0.2, 0.4 * best):
            period = p; break
    if period == 0:
        period = min(p for p, r in corr.items() if r >= 0.85 * best)
    best = corr[period]
    assert best > 0.15, "no periodic gait in the source (autocorrelation %.2f)" % best
    if LOOP <= 0:
        LOOP = period
    if SRC_START < 0:
        SRC_START = min(period, n_src - LOOP - 1)
    if BLEND <= 0:
        BLEND = max(4, min(10, LOOP // 4, SRC_START))
    log("gait period %d frames (r=%.2f) -> loop %d, src-start %d, blend %d" % (period, best, LOOP, SRC_START, BLEND))
elif MODE == "idle":
    if LOOP <= 0: LOOP = 120
    if BLEND <= 0: BLEND = 30
    if SRC_START < 0: SRC_START = BLEND
else:
    if SRC_START < 0: SRC_START = 0
    LOOP = n_src - SRC_START - 1
    BLEND = 0
need = SRC_START + LOOP + (1 if not LOOPING else 0)
assert need <= n_src, "need %d source frames (src-start %d + loop %d), have %d" % (need, SRC_START, LOOP, n_src)
if LOOPING:
    assert SRC_START >= BLEND, "src-start must be >= blend so the seam has frames to fade into"
N_OUT = LOOP + 1                     # frames written: 1..N_OUT (loop: last == first)


LOOP_SHIFT = Vector((0, 0, 0))    # loco: the hips' travel over one loop, see sample()


def sample(f):
    """Source pose for output frame f (0-based); loops crossfade over the last BLEND frames.

    The crossfade partner is the source frame one loop EARLIER. On a locomotion clip that
    frame is a whole cycle behind in world space, so blending its raw positions pulled the
    hips backwards over the last BLEND frames and the wrap snapped them forward again
    ("the drift back starts from frame 33 and continues to frame 42, on frame 43 it snaps");
    the partner's positions are shifted forward by the loop's travel first."""
    a = SRC[SRC_START + f]
    if not LOOPING or f < LOOP - BLEND:
        return a
    w = smooth01((f - (LOOP - BLEND)) / float(BLEND))
    b = SRC[SRC_START + f - LOOP]
    if LOOP_SHIFT.length > 0:
        b = {n: (q, p + LOOP_SHIFT) for n, (q, p) in b.items()}
    return _lerp_pose(a, b, w)


# travel / drift handling on the hips (source metres, then scaled)
hips0 = SRC[SRC_START]["Hips"][1].copy()
travel_v = Vector((0, 0, 0))
drift_v = Vector((0, 0, 0))
if MODE == "loco":
    d = SRC[SRC_START + LOOP]["Hips"][1] - hips0
    LOOP_SHIFT = d.copy()
    # root motion along the DOMINANT axis only (forward for walks/runs, sideways for
    # strafes); the source's drift on the other axis is removed linearly from the hips,
    # or a walk with 0.22 m of sideways drift per cycle becomes a diagonal walk
    if TRAVEL_AXIS == "y" or (TRAVEL_AXIS == "auto" and abs(d.y) >= abs(d.x)):
        travel_v = Vector((0, d.y, 0)) / float(LOOP); drift_v = Vector((d.x, 0, 0)) / float(LOOP)
    else:
        travel_v = Vector((d.x, 0, 0)) / float(LOOP); drift_v = Vector((0, d.y, 0)) / float(LOOP)
    log("travel per loop: (%.3f, %.3f) m source -> %.3f m/s on the rig; drift removed (%.3f, %.3f)"
        % (d.x, d.y, (travel_v * scale).length * 30, drift_v.x * LOOP, drift_v.y * LOOP))
if MODE in ("action", "upper"):
    d = SRC[SRC_START + LOOP]["Hips"][1] - hips0
    drift_v = Vector((d.x, d.y, 0)) / float(max(LOOP, 1))
if MODE == "idle":
    # a recorded idle drifts (video mocap: 8 cm over 5 s); the seam crossfade would slide the
    # hips back over BLEND frames, so the partner is shifted like a loco loop and the drift
    # is removed linearly (Kimodo idles drift ~0, so this changes nothing for them)
    d = SRC[SRC_START + LOOP]["Hips"][1] - hips0
    LOOP_SHIFT = Vector((d.x, d.y, 0))
    drift_v = Vector((d.x, d.y, 0)) / float(LOOP)
    if LOOP_SHIFT.length > 0.005:
        log("idle drift over the loop (%.3f, %.3f) m removed" % (d.x, d.y))


def hips_target(f, src):
    """World position for the torso control at output frame f, and the root travel.

    f is the UN-WRAPPED output frame: on a loop the last frame samples the source's
    first frame but its root has travelled the whole loop (the first build snapped the
    root back to 0 on the seam frame, so Unity measured zero travel)."""
    h = src["Hips"][1] - hips0
    if MODE == "loco":
        root = travel_v * f
        local = h - (travel_v + drift_v) * (f % LOOP)
    elif MODE == "action":
        root = Vector((0, 0, 0)); local = h - drift_v * f
    else:
        root = Vector((0, 0, 0)); local = h - drift_v * (f % LOOP if LOOPING else f)
    # the torso is set in ARMATURE space (set_world), so its world target must include the
    # root's travel or the hips stay in place while root slides underneath, and Unity's
    # Humanoid root motion (derived from the hips, not from the Root bone) measures zero
    world = Vector((local.x + root.x, local.y + root.y, local.z))
    return T_rest["torso"][2] + world * scale, Vector((root.x, root.y, 0)) * scale


# ------------------------------------------------------------- 4. the action
act = bpy.data.actions.get(NAME)
if act is not None:
    bpy.data.actions.remove(act)
act = bpy.data.actions.new(NAME)
act.use_fake_user = True
rig.animation_data_create()
rig.animation_data.action = act
if hasattr(rig.animation_data, "action_slot"):
    rig.animation_data.action_slot = act.slots.new('OBJECT', rig.name)

DRIVEN = sorted(TARGETS) + FINGERS + ["root"] + (["hand_ik.L", "hand_ik.R"] if (ARM_POSE or ARM_KEYS or LOCK_L > 0 or PROP or HAND_CLEAR) else []) + (["upper_arm_ik_target.L", "upper_arm_ik_target.R"] if ELBOW_POLE else []) + (["foot_ik.L", "foot_ik.R", "toe_ik.L", "toe_ik.R"] if (PLANT > 0 or AIM_FORWARD) else [])
STATIC = [c for c in controls() if c not in DRIVEN]
_rnd = __import__("random").Random(7)
FINGER_WAVE = {n: (_rnd.choice([1, 1, 2]), _rnd.uniform(0, 2 * math.pi), _rnd.uniform(0.6, 1.0)) for n in FINGERS}


def key_frame(f):
    for n in DRIVEN + ([c for c in POSE_DELTAS if c not in DRIVEN] if POSE_DELTAS else []):
        pb = pbs[n]
        pb.keyframe_insert("location", frame=f, group=n)
        pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=n)
    for b in IKFK_ARMS + IKFK_LEGS:
        pbs[b].keyframe_insert('["IK_FK"]', frame=f, group=b)
    if ELBOW_POLE:
        for b in IKFK_ARMS:
            pbs[b].keyframe_insert('["pole_vector"]', frame=f, group=b)
        if "IK_Stretch" in pbs[b]:
            pbs[b].keyframe_insert('["IK_Stretch"]', frame=f, group=b)


def key_static(f):
    for n in STATIC:
        pb = pbs[n]
        pb.keyframe_insert("location", frame=f, group=n)
        pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=n)


def pose(f, dz=0.0, f_travel=None):
    global NEED_DROP, ANCHOR_ROLL_SIGN
    zero_pose()
    for b in IKFK_ARMS:
        pbs[b]["IK_FK"] = 1.0
    for b in IKFK_LEGS:
        pbs[b]["IK_FK"] = 1.0 if FK_LEGS else 0.0
    for n in FINGERS:
        k, ph, amp = FINGER_WAVE[n]
        pb = pbs[n]; pb.rotation_mode = 'XYZ'
        life = FINGER_LIFE * amp * math.sin(2 * math.pi * k * f / float(max(LOOP, 1)) + ph) if MODE == "idle" else 0.0
        pb.rotation_euler = (max(0.0, FIST + life), 0, 0)
    aim_yaw_f = 0.0; aim_w_f = 0.0; aim_full_f = 0.0; aim_w_full = 0.0; step_hip_shift = Vector((0, 0, 0))
    if AIM_FORWARD and AIM_FIX is not None:
        w_aim = 1.0
        if BASE is not None and f < BLEND_IN:
            w_aim = min(w_aim, smooth01(f / float(BLEND_IN)))
        if END is not None and f > N_OUT - 1 - BLEND_OUT:
            w_aim = min(w_aim, 1.0 - smooth01((f - (N_OUT - 1 - BLEND_OUT)) / float(BLEND_OUT)))
        aim_full_f = AIM_FIX[f] * w_aim; aim_yaw_f = aim_full_f * AIM_BODY; aim_w_f = w_aim if AIM_BODY else 0.0; aim_w_full = w_aim
    if (STANCE or aim_yaw_f) and not FK_LEGS:
        update()
        stance_m = {}
        for side in ("L", "R"):
            m = rig.matrix_world @ pbs["foot_ik." + side].matrix
            stance_m[side] = Matrix.Translation((0, -STANCE.get(side, 0.0), 0)) @ m     # the split, along world forward
        if aim_yaw_f:
            # the body turns: the FRONT foot (the larger forward stance) pivots in place, the other
            # foot STEPS round it with a lift arc (user: "a slight step back instead of feet shifting")
            front = max(("L", "R"), key=lambda s_: STANCE.get(s_, 0.0))
            back = "R" if front == "L" else "L"
            pivot = stance_m[front].translation.copy()
            R = Matrix.Translation(pivot) @ Matrix.Rotation(aim_yaw_f, 4, 'Z') @ Matrix.Translation(-pivot)
            for side in ("L", "R"):
                stance_m[side] = R @ stance_m[side]
            lift = STEP_LIFT * math.sin(math.pi * aim_w_f)             # up on the way into the stance, down on the way out
            moved = stance_m[back].translation - (Matrix.Translation((0, -STANCE.get(back, 0.0), 0)) @ (rig.matrix_world @ pbs["foot_ik." + back].matrix)).translation
            step_hip_shift = Vector((moved.x, moved.y, 0.0)) * 0.5      # the body steps back with the foot (a pivot about the front foot alone left the rear foot beyond reach)
            stance_m[back] = Matrix.Translation((0, 0, lift)) @ stance_m[back]
        for side in ("L", "R"):
            pbs["foot_ik." + side].matrix = rig.matrix_world.inverted() @ stance_m[side]
        update()
    src = sample(f)
    targets = {}
    for sname, tgt, _, _ in MAP:
        delta = src[sname][0] @ S_rest[sname][0].inverted()
        if HEAD_DAMP < 1.0 and tgt in ("neck", "head"):
            delta = Quaternion((1, 0, 0, 0)).slerp(delta, HEAD_DAMP)
        targets[tgt] = delta @ A[tgt] @ T_rest[tgt][0]
    if HUNCH:
        targets["spine_fk.003"] = Quaternion((1, 0, 0), HUNCH) @ targets["spine_fk.003"]
    hips, root = hips_target(f if f_travel is None else f_travel, src)
    if BASE is not None and f < BLEND_IN:
        wb = smooth01(f / float(BLEND_IN))
        for tgt in targets:
            targets[tgt] = BASE["rot"][tgt].slerp(targets[tgt], wb)
        hips = BASE["hips"].lerp(hips, wb)
        for n in FINGERS:
            pbs[n].rotation_euler = (BASE["fist"][n] + (pbs[n].rotation_euler.x - BASE["fist"][n]) * wb, 0, 0)
    if END is not None and f > N_OUT - 1 - BLEND_OUT:
        we = smooth01((f - (N_OUT - 1 - BLEND_OUT)) / float(BLEND_OUT))
        for tgt in targets:
            targets[tgt] = targets[tgt].slerp(END["rot"][tgt], we)
        hips = hips.lerp(END["hips"], we)
        for n in FINGERS:
            pbs[n].rotation_euler = (pbs[n].rotation_euler.x + (END["fist"][n] - pbs[n].rotation_euler.x) * we, 0, 0)
    if aim_full_f:
        # the turn that puts the shot line (draw hand -> bow hand) forward: AIM_BODY of it on the whole
        # body (pelvis = torso + spine_fk, and the feet in the stance block), the rest as a spine twist
        # spread up the chain (the pelvis bone follows spine_fk, not the torso control). With AIM_BODY 0
        # the body faces forward and only the torso turns (user 2026-09-22: "body twists too much, so
        # he is not shooting forward"); with 1 it is the side-on archer. Fades with the idle crossfades.
        rest_turn = aim_full_f - aim_yaw_f
        share = {"torso": 0.0, "spine_fk": 0.0, "spine_fk.001": 1.0 / 3.0, "spine_fk.002": 2.0 / 3.0}
        pelvis_hold = PELVIS_FIX[f] * aim_w_full * (1.0 - AIM_BODY)    # the capture's own pelvis turn, undone on the pelvis group only
        for tgt in targets:
            sh_ = share.get(tgt, 1.0)
            targets[tgt] = Quaternion((0, 0, 1), aim_yaw_f + rest_turn * sh_ + pelvis_hold * (1.0 - sh_)) @ targets[tgt]
    if TORSO_REF_POSE is not None:
        if TORSO_FIX is None:
            TORSO_TRACE.append((targets["torso"].copy(), hips.copy()))          # pass 1: collect the clip's torso
        else:
            # the user rotated the torso CONTROL, which carries everything above it: apply the delta to
            # every world target (spine, neck, head, shoulders, FK arms), not to the pelvis alone
            for tgt in targets:
                targets[tgt] = TORSO_FIX[0] @ targets[tgt]
            hips = hips + TORSO_FIX[1]
    hips = hips + step_hip_shift
    if HIPS_DROP:
        w_drop = 1.0
        if BASE is not None and f < BLEND_IN:
            w_drop = min(w_drop, smooth01(f / float(BLEND_IN)))
        if END is not None and f > N_OUT - 1 - BLEND_OUT:
            w_drop = min(w_drop, 1.0 - smooth01((f - (N_OUT - 1 - BLEND_OUT)) / float(BLEND_OUT)))
        hips = hips - Vector((0, 0, HIPS_DROP * w_drop))              # user 2026-09-22: "lower the torso ~10 cm, standing too high makes the legs twitch"
    hips = hips + Vector((0, 0, dz - (HIP_DROP[f] if HIP_DROP is not None else 0.0)))
    pbs["root"].location = (root.x, root.y, root.z)      # root points +Y, its local frame = world at rest
    update()
    for level in LEVELS:
        for tgt in level:
            set_world(pbs[tgt], targets[tgt], hips if tgt == "torso" else None)
        update()
    if "spine_fk" in targets and "spine_fk.001" in targets:
        # Rigify's pelvis FK control (spine_fk) is a CHILD of the spine pivot (spine_fk.001): posed
        # before its parent it is dragged along afterwards, so it is re-applied once the chain is set
        # (found when the pelvis hold of aim-forward landed on nothing)
        set_world(pbs["spine_fk"], targets["spine_fk"])
        update()
    for side, (ca, cb) in HAND_CLEAR.items():
        # a captured hand that sinks into the torso (the bow idle, source frames 42-56): push the socket
        # out to the chest's outline in the horizontal plane and let the arm follow through IK, blended
        # in over the first 3 cm of push so an untouched frame stays pure FK
        sock = rig.matrix_world @ pbs["DEF-weapon." + side].matrix
        hips_w = (rig.matrix_world @ pbs["DEF-spine"].matrix).translation
        shoulder_z = (rig.matrix_world @ pbs["DEF-upper_arm." + side].matrix).translation.z
        dx = sock.translation.x - hips_w.x; dy = sock.translation.y - (hips_w.y + 0.02)
        r = math.sqrt((dx / ca) ** 2 + (dy / cb) ** 2)
        if r < 1.0 and r > 1e-6 and sock.translation.z < shoulder_z:      # above the shoulders the hand is at the face, not in the torso
            new_xy = Vector((hips_w.x + dx / r, hips_w.y + 0.02 + dy / r, sock.translation.z))
            push = (new_xy - sock.translation).length
            wgt = min(1.0, push / 0.03)
            # Rigify's IK_FK blends the FK and IK poses, so a partial weight lands the hand short of the
            # outline: overshoot the IK target by 1/weight so the BLENDED hand sits exactly on it
            frame_m = sock.copy(); frame_m.translation = sock.translation + (new_xy - sock.translation) / max(wgt, 1e-3)
            pbs["upper_arm_parent." + side]["IK_FK"] = 1.0 - wgt
            pbs["hand_ik." + side].matrix = rig.matrix_world.inverted() @ frame_m @ HAND_FROM_SOCKET[side]
            update()
            HAND_CLEAR_LOG[side] = max(HAND_CLEAR_LOG.get(side, 0.0), push)
    for side, ang in WRIST_TWIST.items():
        # pronate / supinate: rotate the FK forearm about its own axis (the hand and fingers follow)
        fa = pbs["forearm_fk." + side]
        axis = ((rig.matrix_world @ fa.matrix).to_3x3() @ Vector((0, 1, 0))).normalized()
        set_world(fa, Quaternion(axis, ang) @ world_rot(fa))
        update()
    if AIM_FORWARD and ANCHOR > 0 and ANCHOR_W is not None and ANCHOR_W[f] > 0.0:
        # the anchor: the captured draw hand sat 0.2 rig m beside the head (an arrow that passes 38 cm
        # right of the eye). While both hands are raised the whole draw arm is swung about the vertical
        # through its shoulder, in FK, until the hand lies on the vertical plane through the head and the
        # bow hand: the elbow angle and the hand height are kept, and there is no IK/FK blend to snap
        # (an IK version with a pole differed from the captured FK arm by ~180 deg of forearm roll and the
        # blend between them flipped the hand 174 deg in one frame, in Blender and in Unity)
        dside = AIM_HANDS[1][0]
        sock = (rig.matrix_world @ pbs["DEF-weapon." + dside].matrix).translation
        bh = (rig.matrix_world @ pbs["DEF-hand." + AIM_HANDS[0][0]].matrix).translation
        hd = (rig.matrix_world @ pbs["DEF-spine.006"].matrix).translation
        sh = (rig.matrix_world @ pbs["DEF-upper_arm." + dside].matrix).translation
        line = bh - hd; line.z = 0.0
        if line.length > 1e-4:
            n = Vector((-line.y, line.x, 0.0)).normalized()
            off0 = (sock - hd).dot(n)                                   # which side of the sight plane the hand comes from
            p = sock - sh; c = math.copysign(ANCHOR_GAP, off0 if off0 else 1.0) - (sh - hd).dot(n)
            ca_ = p.x * n.x + p.y * n.y; sa_ = p.x * n.y - p.y * n.x; ra_ = math.hypot(ca_, sa_)
            if ra_ > 1e-6:
                base = math.atan2(sa_, ca_); d = math.acos(max(-1.0, min(1.0, c / ra_)))
                cands = [(base + d + math.pi) % (2 * math.pi) - math.pi, (base - d + math.pi) % (2 * math.pi) - math.pi]
                if f == 0:
                    ANCHOR_PREV.clear()
                # the root closest to last frame's (the two roots swap places as the arm rises; picking the
                # smaller each frame jumped the whole arm)
                theta_full = min(cands, key=lambda t_: abs(t_ - ANCHOR_PREV["theta"]) if "theta" in ANCHOR_PREV else abs(t_))
                ANCHOR_PREV["theta"] = theta_full
                theta = theta_full * ANCHOR_W[f] * ANCHOR
                ua = pbs["upper_arm_fk." + dside]
                set_world(ua, Quaternion((0, 0, 1), theta) @ world_rot(ua))
                update()
                moved = ((rig.matrix_world @ pbs["DEF-weapon." + dside].matrix).translation - sock).length
                ANCHOR_LOG[0] = max(ANCHOR_LOG[0], moved); ANCHOR_LOG[1] += 1
                # the elbow: swivel the arm about its shoulder -> hand axis (the hand stays put) until the
                # elbow points BACK along the arrow, level with it (the capture's elbow hung 27 cm below the
                # hand; an archer's draw elbow is behind the hand at its height)
                sh2 = (rig.matrix_world @ pbs["DEF-upper_arm." + dside].matrix).translation
                hd2 = (rig.matrix_world @ pbs["DEF-hand." + dside].matrix).translation
                el2 = (rig.matrix_world @ pbs["DEF-forearm." + dside].matrix).translation
                axis = (hd2 - sh2).normalized()
                e_ = el2 - sh2; e_ = e_ - axis * e_.dot(axis)
                out_ = Vector((1, 0, 0)) if dside == "L" else Vector((-1, 0, 0))
                # LEVEL: the horizontal perpendicular to the shoulder -> hand axis, on the back/out side
                # ("back along the arrow" projected onto that plane pointed almost straight up, since the
                # hand at the cheek sits nearly along that line from the shoulder: the elbow rose 16 cm
                # above the shoulder and flipped down 180 deg at the release)
                d_ = axis.cross(Vector((0, 0, 1)))
                ref_ = ANCHOR_PREV.get("d", -line.normalized() + out_ * 0.5)   # first frame: the back/out side; then last frame's side (the rule alone flipped it twice)
                if d_.dot(ref_) < 0:
                    d_ = -d_
                ANCHOR_PREV["d"] = d_.copy()
                if e_.length > 0.03 and d_.length > 1e-4:                  # a nearly straight arm has no elbow direction to swivel
                    phi = e_.normalized().rotation_difference(d_.normalized())
                    ang = phi.angle if phi.axis.dot(axis) >= 0 else -phi.angle
                    if abs(ang) > math.radians(150) and ANCHOR_PREV.get("ang_sign", 0) and (ang > 0) != (ANCHOR_PREV["ang_sign"] > 0):
                        ang -= math.copysign(2 * math.pi, ang)           # near 180 deg the sign is arbitrary: keep last frame's way round (a partial weight otherwise jumps the arm)
                    ANCHOR_PREV["ang_sign"] = 1 if ang > 0 else -1
                    if os.environ.get("ANCHOR_DEBUG"):
                        print("anchor f%d w %.2f theta %.0f ang %.0f e %.3f aimhand %.2f" % (f + 1, ANCHOR_W[f], math.degrees(theta_full), math.degrees(ang), e_.length, AIM_HAND[f]))
                    set_world(ua, Quaternion(axis, ang * ANCHOR_W[f] * ANCHOR) @ world_rot(ua))
                    update()
    if AIM_FORWARD and AIM_HAND is not None and AIM_HAND[f] > 0.0:
        # the string hand: the wrist the tracker lost is re-aimed so the fingers (socket +X) run along
        # the shot line towards the bow and the back of the hand (+Z) faces away from the head; the
        # arrow prefab grips the shaft along the fingers, so it points at the bow at the draw and hangs
        # down the leg when the hand hangs (user: the default grip needed "an awkward hand twist")
        dside = AIM_HANDS[1][0]
        bh = (rig.matrix_world @ pbs["DEF-hand." + AIM_HANDS[0][0]].matrix).translation
        sockm = rig.matrix_world @ pbs["DEF-weapon." + dside].matrix
        chest_m = rig.matrix_world @ pbs["DEF-spine.003"].matrix
        chest_c = chest_m.translation + (chest_m.to_3x3() @ Vector((0, 1, 0))) * (pbs["DEF-spine.003"].length * 0.5)
        x_new = (bh - sockm.translation).normalized()
        # the back of the hand faces away from the CHEST centre; "away from the head" collapsed when the
        # hand reached the cheek and flipped the hand 167 deg in one frame
        away = sockm.translation - chest_c
        z_new = (away - x_new * away.dot(x_new)).normalized()
        y_new = z_new.cross(x_new)
        q_new = Matrix((x_new, y_new, z_new)).transposed().to_quaternion()
        q_cur = sockm.to_quaternion()
        if ANCHOR > 0 and ANCHOR_W is not None and ANCHOR_W[f] > 0.0:
            # anchored, the hand's roll is taken from the FOREARM, not from a world reference: the hand at
            # zero wrist twist (rest relation) is turned by the least rotation that lays its fingers along
            # the shot, then rolled about the fingers by ANCHOR_ROLL (sign chosen once so the back of the
            # hand faces out). A world reference (chest, or lateral) sat ~90-180 deg from the forearm's
            # roll with the elbow back, and the twist limiter flipped the hand 174 deg on the way through
            hf_ = pbs["hand_fk." + dside]
            S_ = world_rot(hf_).inverted() @ q_cur                   # socket vs hand (a rigid child)
            sq0 = world_rot(pbs["forearm_fk." + dside]) @ WRIST_REST[dside] @ S_
            x0 = sq0 @ Vector((1, 0, 0))
            sq1 = x0.rotation_difference(x_new) @ sq0
            if ANCHOR_ROLL_SIGN == 0.0 and ANCHOR_W[f] > 0.9:
                out_ = Vector((1, 0, 0)) if dside == "L" else Vector((-1, 0, 0))
                ANCHOR_ROLL_SIGN = max((1.0, -1.0), key=lambda sg: ((Quaternion(x_new, sg * ANCHOR_ROLL) @ sq1) @ Vector((0, 0, 1))).dot(out_))
                log("anchor: hand roll %+.0f deg about the fingers (back of the hand out)" % math.degrees(ANCHOR_ROLL_SIGN * ANCHOR_ROLL))
            sg_ = ANCHOR_ROLL_SIGN if ANCHOR_ROLL_SIGN else 1.0
            q_anch = Quaternion(x_new, sg_ * ANCHOR_ROLL) @ sq1
            if q_new.dot(q_anch) < 0:
                q_anch.negate()
            q_new = q_new.slerp(q_anch, ANCHOR_W[f])
        if q_cur.dot(q_new) < 0:
            q_new.negate()                                            # shortest path (a 167 deg one-frame hand jump came from the long way round)
        hf = pbs["hand_fk." + dside]
        set_world(hf, (q_cur.slerp(q_new, AIM_HAND[f]) @ q_cur.inverted()) @ world_rot(hf))
        update()
        limit_wrist(dside)
    if HEAD_AIM and BOW_UP is not None and BOW_UP[f] > 0.0:
        # the head looks at the target: its yaw is turned to the sight line (user: "less head jerk";
        # the capture's head swung 65 deg in 20 frames and ended 47 deg off the target at the draw)
        hd_ = pbs["head"]
        hm = rig.matrix_world @ pbs["DEF-spine.006"].matrix
        face = hm.to_3x3() @ HEAD_FACE_LOCAL
        bh_ = (rig.matrix_world @ pbs["DEF-hand." + AIM_HANDS[0][0]].matrix).translation
        sight = bh_ - hm.translation
        dyaw = math.atan2(sight.x, -sight.y) - math.atan2(face.x, -face.y)
        dyaw = (dyaw + math.pi) % (2 * math.pi) - math.pi
        set_world(hd_, Quaternion((0, 0, 1), dyaw * BOW_UP[f]) @ world_rot(hd_))
        update()
    if BOW_SQUARE and BOW_UP is not None and BOW_UP[f] > 0.0:
        # the bow hand: its hilt axis (socket +Y, the bow's limbs) is turned perpendicular to the SIGHT
        # line (head -> bow hand) by the least rotation, the cant kept (user, from a top view: "twist the
        # left hand so that bow is perpendicular to the arrow"), for as long as the bow arm is raised:
        # squaring only while both hands were raised left the bow along the arrow through the pull
        bside = AIM_HANDS[0][0]
        bsock = rig.matrix_world @ pbs["DEF-weapon." + bside].matrix
        hd_ = (rig.matrix_world @ pbs["DEF-spine.006"].matrix).translation
        aim_ = (bsock.translation - hd_).normalized()
        if AIM_HAND is not None and AIM_HAND[f] > 0.0:
            # drawn, the reference is the ARROW itself (draw socket -> bow socket): with the anchor gap the
            # arrow runs 12 deg off the sight line and squaring to the sight left the limbs at 77 deg
            dsock_ = (rig.matrix_world @ pbs["DEF-weapon." + AIM_HANDS[1][0]].matrix).translation
            aim_ = aim_.lerp((bsock.translation - dsock_).normalized(), AIM_HAND[f]).normalized()
        yb = (bsock.to_3x3() @ Vector((0, 1, 0))).normalized()
        yp = yb - aim_ * yb.dot(aim_)
        if yp.length > 1e-4:
            qd = yb.rotation_difference(yp.normalized())
            qd = Quaternion((1, 0, 0, 0)).slerp(qd, BOW_UP[f])
            hb = pbs["hand_fk." + bside]
            set_world(hb, qd @ world_rot(hb))
            update()
            limit_wrist(bside)
    if FK_LEGS:
        hinge_toes()          # before the plant measures the sole: the toe cap is what a pitched boot rests on
    if PROP_SIDE:
        # propping hand: the socket's +Y (the hilt axis: the weapon convention's "blade direction")
        # is aimed at the floor point so a weapon in that hand points down onto it, the fingers keep
        # their heading, and the hand is put on IK at its mean position plus PROP_DAMP of its own
        # motion (user: "reduce the movement on the right hand, so it feels like it rests on a
        # weapon"). The "Staff (propped)" prefab grips the staff at its top end along +Y.
        sock = rig.matrix_world @ pbs["DEF-weapon." + PROP_SIDE].matrix
        PROP_TRACE.append((sock.translation.copy(), (rig.matrix_world @ pbs["DEF-upper_arm." + PROP_SIDE].matrix).translation.copy()))
        if PROP_POINT is not None:
            pos = PROP_MEAN + (sock.translation - PROP_MEAN) * PROP_DAMP
            y_new = (PROP_POINT - pos).normalized()                 # aimed from where the hand is PUT, not where it was recorded
            x_old = (sock.to_3x3() @ Vector((1, 0, 0))).normalized()
            x_new = (x_old - y_new * x_old.dot(y_new)).normalized()
            z_new = x_new.cross(y_new)
            frame = Matrix.Translation(pos) @ Matrix((x_new, y_new, z_new)).transposed().to_4x4()
            pbs["upper_arm_parent." + PROP_SIDE]["IK_FK"] = 0.0
            pbs["hand_ik." + PROP_SIDE].matrix = rig.matrix_world.inverted() @ frame @ HAND_FROM_SOCKET[PROP_SIDE]
            update()
    if not FK_LEGS:
        # IK legs on resting feet: hips beyond PLANT_REACH of the leg leave the IK a straight leg whose
        # roll is undetermined (the recorded idle rolled both legs 49 deg; Idle's knee sat at 177 deg)
        NEED_DROP = 0.0
        for side in ("L", "R"):
            v = (rig.matrix_world @ pbs["DEF-thigh." + side].matrix).translation - (rig.matrix_world @ pbs["foot_ik." + side].matrix).translation
            NEED_DROP = max(NEED_DROP, v.z - math.sqrt(max(0.0, (PLANT_REACH * LEG_LEN[side]) ** 2 - v.x * v.x - v.y * v.y)))
    if ARM_POSE:
        # authored hands on IK, following the torso's current transform (sway, hunch)
        torso_now = (rig.matrix_world @ pbs["torso"].matrix).copy()
        follow = torso_now @ TORSO_REST.inverted()
        for side, (pos, y, z) in ARM_POSES[ARM_POSE].items():
            pbs["upper_arm_parent." + side]["IK_FK"] = 0.0
            target = follow @ socket_frame(pos, y, z) @ HAND_FROM_SOCKET[side]
            pbs["hand_ik." + side].matrix = rig.matrix_world.inverted() @ target
        update()
    if ARM_KEYS:
        # authored hands keyed over the clip: between two keys that both pose a side the
        # socket frame is interpolated (smoothstep); where only one key poses the side the
        # arm blends between the source (FK) and the authored pose through Rigify's IK_FK
        u = f / float(max(N_OUT - 1, 1))
        k1 = next((i for i, (t, _) in enumerate(ARM_KEYS) if t >= u), len(ARM_KEYS) - 1)
        k0 = max(0, k1 - 1)
        t0, n0 = ARM_KEYS[k0]; t1, n1 = ARM_KEYS[k1]
        w = smooth01((u - t0) / (t1 - t0)) if t1 > t0 else 1.0
        torso_now = (rig.matrix_world @ pbs["torso"].matrix).copy()
        follow = torso_now @ TORSO_REST.inverted()
        for side in ("L", "R"):
            a = ARM_POSES[n0].get(side); b = ARM_POSES[n1].get(side)
            if a is None and b is None:
                continue
            if a is not None and b is not None:
                pos = a[0].lerp(b[0], w); y = a[1].lerp(b[1], w); z = a[2].lerp(b[2], w); ikfk = 0.0
            elif a is not None:
                pos, y, z = a; ikfk = w
            else:
                pos, y, z = b; ikfk = 1.0 - w
            pbs["upper_arm_parent." + side]["IK_FK"] = ikfk
            target = follow @ socket_frame(pos, y, z) @ HAND_FROM_SOCKET[side]
            pbs["hand_ik." + side].matrix = rig.matrix_world.inverted() @ target
            if ELBOW_POLE:
                # pole vector held outward, back and down from the shoulder so the elbow never folds into the body
                pbs["upper_arm_parent." + side]["pole_vector"] = True
                sh = (rig.matrix_world @ pbs["DEF-upper_arm." + side].matrix).translation
                out = Vector((1, 0, 0)) if side == "L" else Vector((-1, 0, 0))
                pole = sh + out * 0.30 + Vector((0, 0.25, 0)) - Vector((0, 0, 0.15))
                m = pbs["upper_arm_ik_target." + side].matrix.copy(); m.translation = rig.matrix_world.inverted() @ pole
                pbs["upper_arm_ik_target." + side].matrix = m
        update()
    if PLANT > 0 and PLANT_ACTIVE and FK_LEGS:
        NEED_DROP = 0.0
        # blend-from: the first frame is the base pose verbatim, the planting fades in with the crossfade
        w_in = smooth01(f / float(BLEND_IN)) if (BASE is not None and f < BLEND_IN) else 1.0
        for side, sf, st in (("L", "LeftFoot", "LeftToeBase"), ("R", "RightFoot", "RightToeBase")):
            if sf not in src or st not in src:
                continue
            # human: ankle ~8 cm up when flat, toe joint ~0; the plant weight eases in over the
            # last 3 cm of the source foot's descent so the landing does not pop
            src_h = min(src[sf][1].z - 0.075, src[st][1].z)
            w = w_in * max(0.0, min(1.0, (0.05 - src_h) / 0.03))
            fm = rig.matrix_world @ pbs["DEF-foot." + side].matrix
            lowest = foot_min_z(side)                                  # the boots of all six characters, not a bare-foot estimate
            if lowest < -PLANT and f > 0:
                w = 1.0                                                # a boot under the floor is wrong whatever the source does (FK blends sweep through it)
            if w <= 0.0 or (abs(lowest) <= PLANT and w >= 1.0):
                continue
            toe_q = (rig.matrix_world @ pbs["DEF-toe." + side].matrix).to_quaternion()
            ankle_t = fm.translation - Vector((0, 0, lowest))
            hipj = (rig.matrix_world @ pbs["DEF-thigh." + side].matrix).translation
            v = hipj - ankle_t
            reach = PLANT_REACH * LEG_LEN[side]
            need = v.z - math.sqrt(max(0.0, reach * reach - v.x * v.x - v.y * v.y))
            NEED_DROP = max(NEED_DROP, need * w)
            pbs["thigh_parent." + side]["IK_FK"] = 1.0 - w
            target = Matrix.Translation((0, 0, -lowest)) @ fm @ FOOTIK_FROM_FOOT[side]
            pbs["foot_ik." + side].matrix = rig.matrix_world.inverted() @ target
            update()
            set_world(pbs["toe_ik." + side], toe_q)
            update()
    if LOCK_L > 0:
        # two-handed grip: the left hand's socket frame = the right hand's socket frame moved
        # LOCK_L down the handle (-Y), so both hands wrap the handle the same way and a weapon
        # attached to RightWeaponSocket passes through the left hand every frame
        sock_r = (rig.matrix_world @ pbs["DEF-weapon.R"].matrix).copy()
        target = sock_r @ Matrix.Translation((0, -LOCK_L, 0)) @ Matrix.Rotation(LOCK_L_ROLL, 4, 'Y') @ HAND_FROM_SOCKET["L"]
        pbs["upper_arm_parent.L"]["IK_FK"] = 0.0
        pbs["hand_ik.L"].matrix = rig.matrix_world.inverted() @ target
        update()
    if FK_LEGS:
        hinge_toes()
    if AIM_FORWARD and AIM_FIX is None:
        bh = (rig.matrix_world @ pbs["DEF-hand." + AIM_HANDS[0][0]].matrix).translation
        dh = (rig.matrix_world @ pbs["DEF-hand." + AIM_HANDS[1][0]].matrix).translation
        sh = (rig.matrix_world @ pbs["DEF-upper_arm." + AIM_HANDS[0][0]].matrix).translation
        v = bh - dh
        # the shot line is only one of three lines that read as "where he shoots": both hands sat 0.2 rig m
        # right of the head with the shot line dead ahead, and the bow arm crossed the body 50 deg to the
        # right (user: "still shoots diagonally, rotate the left arm to the left more")
        ref = {"shot": dh, "sight": (rig.matrix_world @ pbs["DEF-spine.006"].matrix).translation, "arm": sh}[AIM_LINE]
        va = bh - ref
        pf = (rig.matrix_world @ pbs["DEF-spine"].matrix).to_3x3() @ PELVIS_FWD_LOCAL
        AIM_TRACE.append((math.atan2(va.x, -va.y) - AIM_OFFSET, bh.z > sh.z - 0.08 and dh.z > sh.z - 0.08 and v.length > 0.2, math.atan2(pf.x, -pf.y), bh.z > sh.z - 0.08))
    if POSE_DELTAS:
        w_ = (ANCHOR_W[f] if ANCHOR_W is not None else 1.0)
        for c_, (dloc, drot, w_at) in POSE_DELTAS.items():
            k_ = min(1.0, w_ / w_at) if w_at > 1e-6 else 0.0
            if k_ <= 0.0:
                continue
            pb_ = pbs[c_]
            b_ = pb_.matrix_basis.copy()
            r_ = Quaternion((1, 0, 0, 0)).slerp(drot, k_).to_matrix().to_4x4()
            r_.translation = dloc * k_
            pb_.matrix_basis = r_ @ b_
        update()


# every skinned reference mesh of all six characters (boots, greaves, robes and armour
# included): a lying skeleton rests on its pauldrons and the Necromancer's robe reaches
# 15 cm below the Knight's body, so measuring the Knight body alone under-grounds the
# death clips. Unity's ground_clip.py measures the same set, so the two agree.
import numpy as np
# the Ref_<Character> collections are excluded from the view layer in the anim file (only the
# Knight is shown); excluded objects are not in the depsgraph and would report their rest
# shape, so include them for the measurement and restore the file's state before saving
_EXCLUDED = []
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name.startswith("Ref_") and lc.exclude:
        lc.exclude = False; _EXCLUDED.append(lc)
update()
REF_MESHES = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("Skeleton")
              and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)
              and not any(k in o.name for k in GROUND_IGNORE)]
assert REF_MESHES, "no skinned reference meshes in the anim file"
_co_buf = {}


def body_min_z():
    dg = bpy.context.evaluated_depsgraph_get()
    lowest = 1e9
    for o in REF_MESHES:
        me = o.evaluated_get(dg).data
        n = len(me.vertices)
        buf = _co_buf.get(o.name)
        if buf is None or len(buf) != n * 3:
            buf = _co_buf[o.name] = np.empty(n * 3, dtype=np.float32)
        me.vertices.foreach_get("co", buf)
        co = buf.reshape(-1, 3)
        M = np.array(o.matrix_world, dtype=np.float32)
        z = co @ M[2, :3] + M[2, 3]
        lowest = min(lowest, float(z.min()))
    return lowest


def foot_min_z(side):
    """Lowest vertex of every character's meshes around this ankle (nearer to it than to the
    other ankle, within 0.16 m): the boot sole under the posed foot, whatever its tilt."""
    dg = bpy.context.evaluated_depsgraph_get()
    a = np.array((rig.matrix_world @ pbs["DEF-foot." + side].matrix).translation, dtype=np.float32)
    o_ = np.array((rig.matrix_world @ pbs["DEF-foot." + ("R" if side == "L" else "L")].matrix).translation, dtype=np.float32)
    lowest = 1e9
    for o in REF_MESHES:
        me = o.evaluated_get(dg).data
        n = len(me.vertices)
        buf = _co_buf.get(o.name)
        if buf is None or len(buf) != n * 3:
            buf = _co_buf[o.name] = np.empty(n * 3, dtype=np.float32)
        me.vertices.foreach_get("co", buf)
        M = np.array(o.matrix_world, dtype=np.float32)
        w = buf.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        da = ((w - a) ** 2).sum(1); do = ((w - o_) ** 2).sum(1)
        m = (da < 0.16 * 0.16) & (da <= do)
        if m.any():
            lowest = min(lowest, float(w[m, 2].min()))
    return lowest if lowest < 1e8 else 0.0


# pass 1: raw pose, measure the floor (and, idle mode, the legs' reach)
raw_min = []; idle_need = []
for f in range(N_OUT):
    scene.frame_set(f + 1)
    pose(f % LOOP if LOOPING else f, 0.0, f)
    raw_min.append(body_min_z())
    idle_need.append(NEED_DROP)
if TORSO_REF_POSE is not None:
    qs = [q for q, _ in TORSO_TRACE]; q0 = qs[0]
    acc = Quaternion((0, 0, 0, 0))
    for q in qs:
        acc = acc + (q if q.dot(q0) >= 0 else -q)
    mean_q = acc.normalized(); mean_p = sum((p for _, p in TORSO_TRACE), Vector()) / len(TORSO_TRACE)
    TORSO_FIX = (TORSO_REF_POSE.to_quaternion() @ mean_q.inverted(), TORSO_REF_POSE.translation - mean_p)
    ang = TORSO_FIX[0].angle
    log("torso-ref: clip mean replaced by the reference: rotated %.0f deg, moved %s rig m; reach drop off (the reference sets the height)" % (math.degrees(ang if ang <= math.pi else 2 * math.pi - ang), tuple(round(v, 3) for v in TORSO_FIX[1])))
if PROP_SIDE:
    mean = sum((h for h, _ in PROP_TRACE), Vector()) / len(PROP_TRACE)
    shoulder = sum((sh for _, sh in PROP_TRACE), Vector()) / len(PROP_TRACE)
    ahead = math.sqrt(max(0.0, PROP_LEN * PROP_LEN - mean.z * mean.z))
    if HAND_REF_POS is not None:
        PROP_MEAN = HAND_REF_POS[PROP_SIDE] + HAND_OFFSET
        # keep the target within 90 % of the arm's reach from the mean shoulder (a lowered hand would
        # otherwise straighten the elbow): pulled towards the shoulder along the same line
        arm = ((rig.matrix_world @ pbs["DEF-upper_arm." + PROP_SIDE].matrix).translation - (rig.matrix_world @ pbs["DEF-forearm." + PROP_SIDE].matrix).translation).length \
            + ((rig.matrix_world @ pbs["DEF-forearm." + PROP_SIDE].matrix).translation - (rig.matrix_world @ pbs["DEF-hand." + PROP_SIDE].matrix).translation).length
        # keep the requested HEIGHT; if the target is beyond 97 % of the arm's reach from the mean
        # shoulder, bring it in horizontally towards the shoulder (the elbow keeps ~30 deg of bend)
        v = PROP_MEAN - shoulder
        limit = 0.97 * arm
        if v.length > limit:
            dz = PROP_MEAN.z - shoulder.z
            if abs(dz) >= limit:
                PROP_MEAN = Vector((shoulder.x, shoulder.y, shoulder.z + math.copysign(limit, dz)))
            else:
                h = Vector((v.x, v.y, 0.0)); h = h.normalized() if h.length > 1e-4 else Vector((0, -1, 0))
                r = math.sqrt(limit * limit - dz * dz)
                PROP_MEAN = Vector((shoulder.x + h.x * r, shoulder.y + h.y * r, PROP_MEAN.z))
            log("prop: hand target %.3f rig m from the shoulder, beyond 97%% of the arm (%.3f): brought in to (%.3f, %.3f, %.3f)" % (v.length, arm, PROP_MEAN.x, PROP_MEAN.y, PROP_MEAN.z))
        PROP_POINT = Vector((PROP_MEAN.x, PROP_MEAN.y, 0.0)) if PROP_VERTICAL else Vector((PROP_MEAN.x, PROP_MEAN.y - math.sqrt(max(0.0, PROP_LEN ** 2 - PROP_MEAN.z ** 2)), 0.0))
        log("prop: hand %s from the reference (offset %.3f, %.3f, %.3f) at (%.3f, %.3f, %.3f) rig m: %.2f m up in the engine; a %.2f m weapon below it reaches %+.2f m" % (PROP_SIDE, HAND_OFFSET.x, HAND_OFFSET.y, HAND_OFFSET.z, PROP_MEAN.x, PROP_MEAN.y, PROP_MEAN.z, PROP_MEAN.z * 1.8, PROP_LEN * 1.8, (PROP_MEAN.z - PROP_LEN) * 1.8))
    elif PROP_VERTICAL:
        # the hand rests on the staff's top at height PROP_LEN, placed where the arm holds it at 90 % of
        # its reach (pinning it at the recorded x/y left the elbow locked 3 cm short of the top)
        arm = (rig.matrix_world @ pbs["DEF-upper_arm." + PROP_SIDE].matrix).translation - (rig.matrix_world @ pbs["DEF-forearm." + PROP_SIDE].matrix).translation
        arm = arm.length + ((rig.matrix_world @ pbs["DEF-forearm." + PROP_SIDE].matrix).translation - (rig.matrix_world @ pbs["DEF-hand." + PROP_SIDE].matrix).translation).length
        dz = PROP_LEN - shoulder.z
        r = math.sqrt(max(0.0, (0.9 * arm) ** 2 - dz * dz))
        d = Vector((mean.x - shoulder.x, mean.y - shoulder.y, 0.0)); d = d.normalized() if d.length > 1e-4 else Vector((0, -1, 0))
        PROP_MEAN = Vector((shoulder.x + d.x * r, shoulder.y + d.y * r, PROP_LEN)); PROP_POINT = Vector((PROP_MEAN.x, PROP_MEAN.y, 0.0))
        log("prop: hand %s on the staff's top at %.3f rig m, %.2f from the shoulder (arm %.2f, 90%%), weapon straight down; recorded hand mean %.3f up" % (PROP_SIDE, PROP_LEN, r, arm, mean.z))
    else:
        PROP_POINT = Vector((mean.x, mean.y - ahead, 0.0)); PROP_MEAN = mean.copy()
        log("prop: hand %s mean height %.3f rig m, staff %.2f -> floor point %.2f ahead" % (PROP_SIDE, mean.z, PROP_LEN, ahead))
    PROP_TRACE = []
if MODE == "idle" and TORSO_REF_POSE is not None:
    # the reference sets the height, but the sway must still keep the knees off full extension:
    # re-measure the reach with the torso fix applied
    idle_need = []
    for f in range(N_OUT):
        scene.frame_set(f + 1)
        pose(f % LOOP if LOOPING else f, 0.0, f)
        idle_need.append(NEED_DROP)
if MODE == "upper" and max(idle_need) > 1e-4:
    # one-shot: the drop follows the need (running max over +-5 frames, smoothed) so the blend-from
    # frames, whose need is 0, stay on the idle's own height and the clip meets it exactly
    wide = [max(idle_need[max(0, i - 5):i + 6]) for i in range(N_OUT)]
    HIP_DROP = smooth_series(wide, 3)
    log("reach: hips lowered by up to %.4f rig m (%.0f mm) where the IK legs would straighten" % (max(HIP_DROP), max(HIP_DROP) * 1800))
elif MODE == "idle" and max(idle_need) > 1e-4:
    HIP_DROP = [max(idle_need)] * N_OUT                      # constant: the sway keeps its shape, the knees keep a bend
    log("reach: hips lowered by %.4f rig m (%.0f mm) so the IK legs never straighten" % (HIP_DROP[0], HIP_DROP[0] * 1800))

# ground correction per frame (rig metres)
if MODE in ("idle", "upper"):
    dz = [0.0] * N_OUT
elif MODE == "loco":
    dz = smooth_series([-m for m in raw_min], 3)                 # two-way: lowest point on the floor
elif MODE == "action" and GROUND == "twoway":
    dz = smooth_series([-m for m in raw_min], 3)
elif MODE == "action":
    med = sorted(raw_min)[len(raw_min) // 2]
    dz = smooth_series([max(0.0, -(m - med)) - med for m in raw_min], 3)  # stance to floor + lift-only
else:  # death
    base = -sorted(raw_min[:10])[5]                              # standing start on the floor
    dz = []
    prev = base
    for m in raw_min:
        want = -m                                                # two-way: rest the lowest point on the floor
        step = max(-0.016, min(0.016, want - prev))              # slope-limited (creatures: 0.016 m/frame)
        prev = prev + step; dz.append(prev)
    dz = smooth_series(dz, 2)
log("ground: raw body min z %.4f..%.4f -> correction %.4f..%.4f" % (min(raw_min), max(raw_min), min(dz), max(dz)))
if LOOPING:
    dz[-1] = dz[0]
if BASE is not None and dz[0] != 0.0:
    # the first frame must be the base pose verbatim (the idle it follows), so the correction fades in with the crossfade
    log("ground: first-frame correction %.4f faded in over %d frames (the base pose is kept as authored)" % (dz[0], BLEND_IN))
    dz = [d - dz[0] * (1.0 - smooth01(min(1.0, f / float(BLEND_IN)))) for f, d in enumerate(dz)]
if BASE is not None and BLEND_FROM_LIFT:
    dz = [d + BLEND_FROM_LIFT * (1.0 - smooth01(min(1.0, f / float(BLEND_IN)))) for f, d in enumerate(dz)]
    log("blend-from lift %.4f rig m on the first frame, faded out over %d frames" % (BLEND_FROM_LIFT, BLEND_IN))

if AIM_FORWARD:
    PELVIS_FIX = smooth_series([-yp for _, _, yp, _ in AIM_TRACE], 4)
    BOW_UP = smooth_series([1.0 if bu else 0.0 for _, _, _, bu in AIM_TRACE], 8)     # what puts the pelvis back on the idle's heading, per frame
    raw = [-y if up else None for y, up, _, _ in AIM_TRACE]
    ups = [i for i, r in enumerate(raw) if r is not None]
    assert ups, "aim-forward: the hands are never both raised"
    for i in range(N_OUT):                                    # frames without a raised pair take the nearest raised value
        if raw[i] is None:
            j = min(ups, key=lambda k: abs(k - i)); raw[i] = raw[j]
    AIM_FIX = smooth_series(raw, 6)
    AIM_PEAK = max(AIM_FIX, key=abs)
    AIM_HAND = smooth_series([1.0 if up else 0.0 for _, up, _, _ in AIM_TRACE], 8)
    ANCHOR_W = smooth_series([1.0 if up else 0.0 for _, up, _, _ in AIM_TRACE], 24)
    log("aim-forward: the capture's pelvis heading %.0f..%.0f deg is %s" % (-math.degrees(max(PELVIS_FIX)), -math.degrees(min(PELVIS_FIX)), "kept (aim-body 1)" if AIM_BODY >= 1.0 else "held on the idle's heading by %.0f%%" % ((1 - AIM_BODY) * 100)))
    log("aim-forward %s: %s line %.0f..%.0f deg off the aim while drawn (%d frames); whole body turned by %.0f..%.0f deg, feet with it" % (
        AIM_FORWARD, AIM_LINE, -math.degrees(max(raw[i] for i in ups)), -math.degrees(min(raw[i] for i in ups)), len(ups), math.degrees(min(AIM_FIX)), math.degrees(max(AIM_FIX))))
    AIM_TRACE = []
    if MODE == "upper":                                           # the turned feet change the legs' reach: re-measure
        idle_need = []
        for f in range(N_OUT):
            scene.frame_set(f + 1)
            pose(f % LOOP if LOOPING else f, 0.0, f)
            idle_need.append(NEED_DROP)

# pass 1b: with the feet planted, how far must the hips drop so no planted foot is beyond reach
PLANT_ACTIVE = True
if PLANT > 0 and FK_LEGS:
    need = []
    for f in range(N_OUT):
        scene.frame_set(f + 1)
        pose(f % LOOP if LOOPING else f, dz[f], f)
        need.append(max(0.0, NEED_DROP))
    # never less than the raw need on any frame (a running max over 5 frames), then smoothed
    wide = [max(need[max(0, i - 2):i + 3]) for i in range(N_OUT)]
    HIP_DROP = smooth_series(wide, 2)
    if BASE is not None:                                     # the first frame stays the base pose; the drop fades in with the crossfade
        HIP_DROP = [d * (smooth01(f / float(BLEND_IN)) if f < BLEND_IN else 1.0) for f, d in enumerate(HIP_DROP)]
    log("plant: reach drop of the hips %.4f..%.4f rig m (%d frames need it)" % (min(HIP_DROP), max(HIP_DROP), sum(1 for n in need if n > 1e-4)))

if POSE_REF:
    # the user's reference pose (tools/anim_pose_save.py) for output frame AT: generate that frame,
    # read every control's local transform, read the reference's, keep the deltas. Applied at the
    # end of pose() with the anchor mask as weight (scaled so frame AT is the reference exactly), so
    # the raise and the release keep the capture's motion and the drawn pose is the user's
    spec_, _, at_ = POSE_REF.partition("@"); at_ = int(at_)
    scene.frame_set(at_); pose((at_ - 1) % LOOP if LOOPING else at_ - 1, dz[at_ - 1], at_ - 1)
    ctrls_ = [b.name for b in pbs if not b.name.startswith(("DEF-", "MCH-", "ORG-", "VIS_"))]
    gen_ = {c: pbs[c].matrix_basis.copy() for c in ctrls_}
    rname_, _, rframe_ = spec_.partition(":")
    ract_ = bpy.data.actions[rname_]; rig.animation_data.action = ract_
    if hasattr(rig.animation_data, "action_slot") and ract_.slots: rig.animation_data.action_slot = ract_.slots[0]
    scene.frame_set(int(rframe_) if rframe_ else 1); update()
    ref_ = {c: pbs[c].matrix_basis.copy() for c in ctrls_}
    rig.animation_data.action = None; zero_pose()
    rig.animation_data.action = act
    if hasattr(rig.animation_data, "action_slot") and act.slots: rig.animation_data.action_slot = act.slots[0]
    w_at_ = ANCHOR_W[at_ - 1] if ANCHOR_W is not None else 1.0
    POSE_DELTAS = {}
    for c in ctrls_:
        d_ = ref_[c] @ gen_[c].inverted()
        if d_.to_quaternion().angle > math.radians(0.5) or d_.translation.length > 0.001:
            POSE_DELTAS[c] = (d_.translation.copy(), d_.to_quaternion(), w_at_)
    log("pose-ref %s: %d controls differ from the generated frame %d (weight there %.2f): %s" % (
        POSE_REF, len(POSE_DELTAS), at_, w_at_, ", ".join("%s %.0f deg/%.0f mm" % (c, math.degrees(v[1].angle), v[0].length * 1000) for c, v in sorted(POSE_DELTAS.items(), key=lambda kv: -kv[1][1].angle)[:12])))

# pass 2: final pose + keys
planted = 0
for f in range(N_OUT):
    frame = f + 1
    scene.frame_set(frame)
    pose(f % LOOP if LOOPING else f, dz[f], f)
    key_frame(frame)
    if f == 0:
        key_static(frame)
final_min = []
for f in range(N_OUT):
    scene.frame_set(f + 1); update(); final_min.append(body_min_z())
log("body min z after correction %.4f..%.4f" % (min(final_min), max(final_min)))
if ANCHOR_LOG[1]:
    log("anchor: the draw arm swung the string hand up to %.3f rig m towards the sight plane on %d frames" % (ANCHOR_LOG[0], ANCHOR_LOG[1]))
for side_, push_ in HAND_CLEAR_LOG.items():
    log("hand-clear %s: pushed out of the torso by up to %.3f rig m (%.0f mm in the engine)" % (side_, push_, push_ * 1800))

if LOOPING:
    def ang(a, b):
        d = math.degrees(a.rotation_difference(b).angle); return min(d, 360 - d)
    scene.frame_set(1); update(); q1 = {n: world_rot(pbs[n]) for n in TARGETS}
    scene.frame_set(N_OUT); update(); q2 = {n: world_rot(pbs[n]) for n in TARGETS}
    scene.frame_set(N_OUT - 1); update(); q3 = {n: world_rot(pbs[n]) for n in TARGETS}
    log("loop seam: frame 1 vs %d differ by %.4f deg (must be ~0); last step moves %.2f deg"
        % (N_OUT, max(ang(q1[n], q2[n]) for n in TARGETS), max(ang(q3[n], q2[n]) for n in TARGETS)))
    scene.frame_set(N_OUT); update()
    log("root travel over the loop: (%.4f, %.4f) m rig units" % (pbs["root"].location.x, pbs["root"].location.y))
    if MODE == "loco":
        # the hips must advance every frame by about the travel per frame: a negative step
        # along the travel axis is the loop-closing drift-back this fixed once
        hw = []
        for f in range(1, N_OUT + 1):
            scene.frame_set(f); update(); hw.append((rig.matrix_world @ pbs["torso"].matrix).translation.copy())
        axis = (travel_v * scale).normalized() if travel_v.length > 0 else Vector((0, 1, 0))
        steps = [(hw[i + 1] - hw[i]).dot(axis) for i in range(len(hw) - 1)]
        log("hips advance per frame along the travel axis: min %.4f max %.4f mean %.4f m (must never be negative); seam step %.4f"
            % (min(steps), max(steps), sum(steps) / len(steps), steps[-1]))
scene.frame_start, scene.frame_end = 1, N_OUT
scene.frame_set(1); zero_pose()
log("action %s: %d frames (%.2f s), %s" % (NAME, N_OUT, LOOP / 30.0, "loop" if LOOPING else "one-shot"))
for lc in _EXCLUDED:
    lc.exclude = True
if SAVE:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath, compress=True)
    log("saved")
