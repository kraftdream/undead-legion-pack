"""Author Impaled_Idle and Impaled_Rise on the rig in the anim file from a hand-posed base (no Kimodo).

    blender -b Animations/skeleton_anim.blend -P tools/anim_author_impaled.py -- [--save] [--only Impaled_Idle]

BASE POSE (user, 2026-09-21): a genuflect posed by hand — left foot planted forward, right knee
on the floor with that foot on its toes behind, hips low and forward, chest ~42° down, head
down, arms left hanging on FK. It lives in the one-frame action `Impaled_Base` (created from
frame 0 of the user's Impaled_Idle the first time this runs; edit that action and re-run to
regenerate both clips). EVERYTHING in the base is kept, arms included (the user poses the
right fist on the hilt at the belly with the hilt axis pointing INTO the body; key the arm
controls on the base's frame, or the pose is lost when the frame changes). With --tool-arms
the script poses the arms itself instead (IK: fist on the hilt, left palm on the belly).

Impaled_Idle (loop, 30 frames): the base, held still (skeletons do not breathe).
Impaled_Rise (one-shot, 120 frames): pulls the blade out along the base's hilt axis, drops the arms,
brings the right foot forward to its stance, steps the left foot back to its stance while the
hips rise (a gather in place: the clip must end where Idle stands, so no net travel), and from
frame 100 blends every control to Idle's frame 1 ("dynamic final pose": the engine crossfades
from that neutral stance into whichever idle follows).

Legs are FK placed by an analytic two-bone solve (hip joint -> ankle, knee towards a bend
direction) with an explicit foot frame; the start reproduces the user's IK-posed legs from
their DEF bones. The torso chain, neck and head interpolate between the base's own control
values and Idle's. Grounding per frame from the lowest vertex of all six characters' meshes
minus robes/skirts, shifting the hips and only a foot that is still kneeling.
"""
import bpy, math, sys, os
import numpy as np
from mathutils import Vector, Quaternion, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAVE = "--save" in argv
ONLY = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else {"Impaled_Idle", "Impaled_Rise"}
TOOL_ARMS = "--tool-arms" in argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FWD, UP, RIGHT, LEFT = Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((-1, 0, 0)), Vector((1, 0, 0))
FPS = 30
IDLE_FRAMES = 30
RISE_FRAMES = 120
BLADE = 0.36                   # H1Sword blade length in rig units (0.68 m at pack scale / 1.8 = 0.377 total)

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
pbs = rig.pose.bones
scene = bpy.context.scene
scene.render.fps = FPS


def log(m):
    print("[impaled] " + m); sys.stdout.flush()


def update():
    bpy.context.view_layer.update()


def wmat(n):
    return rig.matrix_world @ pbs[n].matrix


def bone_dir(n):
    return (wmat(n).to_3x3() @ Vector((0, 1, 0))).normalized()


def set_world(n, q, translation=None):
    pb = pbs[n]
    m = pb.matrix.copy()
    Rm = (rig.matrix_world.inverted().to_3x3() @ q.to_matrix()).to_4x4()
    Rm.translation = m.translation if translation is None else rig.matrix_world.inverted() @ translation
    pb.matrix = Rm


def aim(n, direction):
    set_world(n, REST_DIR[n].rotation_difference(direction.normalized()) @ REST_ROT[n])
    update()


def frame_from(y, z):
    y = Vector(y).normalized(); z = Vector(z)
    x = y.cross(z).normalized(); z = x.cross(y).normalized()
    m = Matrix.Identity(3)
    for i in range(3):
        m[i][0], m[i][1], m[i][2] = x[i], y[i], z[i]
    return m


def socket_frame(pos, y, z):
    m = frame_from(y, z).to_4x4(); m.translation = Vector(pos); return m


def smooth01(u):
    u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


IKFK_ARMS = ["upper_arm_parent.L", "upper_arm_parent.R"]
IKFK_LEGS = ["thigh_parent.L", "thigh_parent.R"]
FINGER_MASTERS = ["thumb.01_master", "f_index.01_master", "f_middle.01_master", "f_ring.01_master", "f_pinky.01_master"]
FINGERS = [m + "." + s for s in ("L", "R") for m in FINGER_MASTERS]
TORSO_CHAIN = ["torso", "spine_fk", "spine_fk.001", "spine_fk.002", "spine_fk.003", "neck", "head"]
ARM_CTRL = [b + "." + s for s in "LR" for b in ("shoulder", "upper_arm_fk", "forearm_fk", "hand_fk", "hand_ik", "upper_arm_ik_target")]
LEG_CTRL = [b + "." + s for s in "LR" for b in ("thigh_fk", "shin_fk", "foot_fk", "toe_fk", "foot_ik", "foot_heel_ik", "foot_spin_ik", "toe_ik", "thigh_ik_target")]


def controls():
    return [b.name for b in pbs if not b.name.startswith(("DEF-", "MCH-", "ORG-", "VIS_"))]


def zero_pose():
    for pb in pbs:
        pb.matrix_basis.identity()
        pb.ik_stretch = 0.0
    for b in IKFK_ARMS:
        pbs[b]["IK_FK"] = 0.0
    for b in IKFK_LEGS:
        pbs[b]["IK_FK"] = 1.0           # FK legs, placed analytically
    for b in IKFK_ARMS + IKFK_LEGS:
        if "IK_Stretch" in pbs[b]:
            pbs[b]["IK_Stretch"] = 0.0
    for n in FINGERS:
        pbs[n].rotation_mode = 'XYZ'
    update()


def snapshot(names):
    out = {}
    for n in names:
        pb = pbs[n]
        out[n] = (pb.location.copy(), pb.rotation_mode, pb.rotation_quaternion.copy(), pb.rotation_euler.copy(),
                  {k: pb[k] for k in ("IK_FK", "IK_Stretch") if k in pb.keys()})
    return out


def apply_values(vals, names=None):
    for n, (loc, mode, q, e, props) in vals.items():
        if names is not None and n not in names:
            continue
        pb = pbs[n]; pb.location = loc; pb.rotation_mode = mode; pb.rotation_quaternion = q; pb.rotation_euler = e
        for k, v in props.items():
            pb[k] = v


def lerp_values(A, B, u, names):
    """Interpolate control values (location lerp, rotation slerp) from A to B."""
    for n in names:
        la, ma, qa, ea, _ = A[n]; lb, mb, qb, eb, _ = B[n]
        pb = pbs[n]; pb.location = la.lerp(lb, u)
        if ma == 'QUATERNION':
            pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = qa.slerp(qb, u)
        else:
            pb.rotation_mode = ma
            qa2 = ea.to_quaternion(); qb2 = eb.to_quaternion()
            pb.rotation_euler = qa2.slerp(qb2, u).to_euler(ma)


def set_action(act):
    rig.animation_data.action = act
    if act is not None and hasattr(rig.animation_data, "action_slot") and act.slots:
        rig.animation_data.action_slot = act.slots[0]


# ------------------------------------------------------------------ rest anatomy
prev_action = rig.animation_data.action if rig.animation_data else None
rig.animation_data_create(); set_action(None)
zero_pose()
CTRLS = controls()
REST_ROT = {n: wmat(n).to_quaternion() for n in CTRLS}
REST_DIR = {n: bone_dir(n) for n in CTRLS}
REST_VALUES = snapshot(CTRLS)
HIPJ = {s: wmat("DEF-thigh." + s).translation.copy() for s in "LR"}
KNEE0 = {s: wmat("DEF-shin." + s).translation.copy() for s in "LR"}
ANKLE0 = {s: wmat("DEF-foot." + s).translation.copy() for s in "LR"}
THIGH = {s: (KNEE0[s] - HIPJ[s]).length for s in "LR"}
SHIN = {s: (ANKLE0[s] - KNEE0[s]).length for s in "LR"}
HAND_FROM_SOCKET = {s: wmat("DEF-weapon." + s).inverted() @ wmat("hand_ik." + s) for s in "LR"}
HANDIK_FROM_HAND = {s: wmat("DEF-hand." + s).inverted() @ wmat("hand_ik." + s) for s in "LR"}
FOOT_REST = {s: (bone_dir("foot_fk." + s), (REST_ROT["foot_fk." + s].to_matrix() @ Vector((0, 0, 1))).normalized()) for s in "LR"}
SPINE2_INV = wmat("DEF-spine.002").inverted()
body = bpy.data.objects["SkeletonKnight_Body"]
dg = bpy.context.evaluated_depsgraph_get(); me = body.evaluated_get(dg).data
slab = [body.matrix_world @ v.co for v in me.vertices if 0.56 < (body.matrix_world @ v.co).z < 0.66 and abs((body.matrix_world @ v.co).x) < 0.04]
BELLY_LOCAL = SPINE2_INV @ Vector((0.0, min(c.y for c in slab), 0.61))
FWD_LOCAL = SPINE2_INV.to_3x3() @ FWD

_EXCLUDED = []
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name.startswith("Ref_") and lc.exclude:
        lc.exclude = False; _EXCLUDED.append(lc)
update()
REF_MESHES = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("Skeleton")
              and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)
              and not any(k in o.name for k in ("Robe", "Skirt"))]
_buf = {}


def body_min_z():
    dg = bpy.context.evaluated_depsgraph_get(); lowest = 1e9
    for o in REF_MESHES:
        me = o.evaluated_get(dg).data; n = len(me.vertices)
        buf = _buf.get(o.name)
        if buf is None or len(buf) != n * 3:
            buf = _buf[o.name] = np.empty(n * 3, dtype=np.float32)
        me.vertices.foreach_get("co", buf)
        M = np.array(o.matrix_world, dtype=np.float32)
        lowest = min(lowest, float((buf.reshape(-1, 3) @ M[2, :3] + M[2, 3]).min()))
    return lowest


# ------------------------------------------------------------------ the user's base pose
BASE_NAME = "Impaled_Base"
base_act = bpy.data.actions.get(BASE_NAME)
if base_act is None:
    src = bpy.data.actions["Impaled_Idle"]
    set_action(src); scene.frame_set(0); update()
    base_vals = snapshot(CTRLS)
    set_action(None)
    base_act = bpy.data.actions.new(BASE_NAME); base_act.use_fake_user = True
    set_action(base_act)
    if hasattr(rig.animation_data, "action_slot") and not base_act.slots:
        rig.animation_data.action_slot = base_act.slots.new(id_type='OBJECT', name=rig.name)
    scene.frame_set(1); apply_values(base_vals); update()
    for n in CTRLS:
        pb = pbs[n]
        pb.keyframe_insert("location", frame=1, group=n)
        pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=1, group=n)
    for b in IKFK_ARMS + IKFK_LEGS:
        pbs[b].keyframe_insert('["IK_FK"]', frame=1, group=b)
    log("created %s from frame 0 of the user's Impaled_Idle" % BASE_NAME)
set_action(base_act); scene.frame_set(int(round(base_act.frame_range[0]))); update()
BASE = snapshot(CTRLS)
# the user's leg configuration, read from the DEF bones (their legs are on IK)
BASE_LEG = {}
for s in "LR":
    hip = wmat("DEF-thigh." + s).translation.copy(); knee = wmat("DEF-shin." + s).translation.copy(); ankle = wmat("DEF-foot." + s).translation.copy()
    mid = (hip + ankle) * 0.5
    bend = (knee - mid); bend = bend.normalized() if bend.length > 1e-3 else Vector((0, -1, 0))
    fm = wmat("DEF-foot." + s).to_3x3()
    BASE_LEG[s] = {"ankle": ankle, "bend": bend, "foot_dir": (fm @ Vector((0, 1, 0))).normalized(), "sole": (fm @ Vector((0, 0, 1))).normalized(), "knee": knee,
                   "toe_q": wmat("DEF-toe." + s).to_quaternion()}
BASE_HIPS = wmat("DEF-spine").translation.copy()
BASE_HAND = {s: wmat("DEF-hand." + s) @ HANDIK_FROM_HAND[s] for s in "LR"}      # IK targets reproducing the base's hands
BASE_HILT_OUT = -(wmat("DEF-weapon.R").to_3x3() @ Vector((0, 1, 0))).normalized()   # the blade points +Y into the body; pull out along -Y
ARM_NAMES = [n for n in CTRLS if any(n.startswith(k) for k in ("shoulder", "upper_arm", "forearm", "hand_", "upper_arm_parent"))]
log("base arms: hand R %s hand L %s, hilt out-direction %s, arms on %s" % (tuple(round(v, 3) for v in wmat("DEF-hand.R").translation), tuple(round(v, 3) for v in wmat("DEF-hand.L").translation),
    tuple(round(v, 2) for v in BASE_HILT_OUT), "IK" if BASE["upper_arm_parent.R"][4].get("IK_FK", 1.0) < 0.5 else "FK"))
log("base: hips %s, chest tilt %.0f deg, L ankle %s (knee z %.3f), R ankle %s (knee z %.3f)" % (
    tuple(round(v, 3) for v in BASE_HIPS), math.degrees((wmat("DEF-spine.003").to_3x3() @ Vector((0, 1, 0))).normalized().angle(UP)),
    tuple(round(v, 3) for v in BASE_LEG["L"]["ankle"]), BASE_LEG["L"]["knee"].z, tuple(round(v, 3) for v in BASE_LEG["R"]["ankle"]), BASE_LEG["R"]["knee"].z))

# Idle's frame-1 pose: the rise ends on it (arms FK, legs IK at rest)
IDLE = bpy.data.actions["Idle"]
set_action(IDLE); scene.frame_set(int(round(IDLE.frame_range[0]))); update()
IDLE_VALS = snapshot(CTRLS)
IDLE_HAND = {s: wmat("DEF-hand." + s) @ HANDIK_FROM_HAND[s] for s in "LR"}
IDLE_HIPS = wmat("DEF-spine").translation.copy()
IDLE_LEG = {s: {"ankle": wmat("DEF-foot." + s).translation.copy(), "bend": Vector((0, -1, 0)), "foot_dir": FOOT_REST[s][0], "sole": FOOT_REST[s][1],
                "toe_q": wmat("DEF-toe." + s).to_quaternion()} for s in "LR"}
set_action(None); zero_pose()


# ------------------------------------------------------------------ posing
def place_leg(s, ankle, bend, foot_dir, sole, toe_q=None):
    H = wmat("DEF-thigh." + s).translation
    a, b = THIGH[s], SHIN[s]
    d_vec = ankle - H; d = min(d_vec.length, a + b - 1e-4)
    along = d_vec.normalized()
    x = (a * a - b * b + d * d) / (2 * d); h = math.sqrt(max(a * a - x * x, 0.0))
    perp = bend - along * bend.dot(along)
    perp = perp.normalized() if perp.length > 1e-4 else Vector((0, -1, 0))
    K = H + along * x + perp * h
    aim("thigh_fk." + s, K - H)
    aim("shin_fk." + s, ankle - K)
    set_world("foot_fk." + s, frame_from(foot_dir, sole).to_quaternion()); update()
    if toe_q is not None:                                   # the base's right foot rests on bent toes
        set_world("toe_fk." + s, toe_q); update()
    return K


def hand_target(s, mode, P, belly, fb):
    if mode == "base":                     # the user's hand, pulled out along the base's hilt axis
        return Matrix.Translation(BASE_HILT_OUT * P["pull"]) @ BASE_HAND[s]
    if mode == "hilt":                     # right fist on the hilt, blade INTO the belly, 17 deg up
        fbh = Vector((fb.x, fb.y, 0)).normalized()
        return socket_frame(belly + fb * (0.035 + P["pull"]), (-fbh + UP * 0.3).normalized(), (RIGHT + UP * 0.35 + fb * 0.2)) @ HAND_FROM_SOCKET[s]
    if mode == "belly":                    # left palm on the belly beside the wound
        return socket_frame(belly + LEFT * 0.10 + fb * 0.015 + UP * 0.02, (-UP * 0.8 + fb * 0.2 + LEFT * 0.3).normalized(), fb) @ HAND_FROM_SOCKET[s]
    return IDLE_HAND[s]


def pose(P):
    zero_pose()
    for n in FINGERS:
        pbs[n].rotation_euler = (P["fist_R"] if n.endswith(".R") else P["fist_L"], 0, 0)
    # torso chain: the base's own values -> Idle's, plus a breathing offset on the hips and spine
    lerp_values(BASE, IDLE_VALS, P["u_torso"], ["torso", "spine_fk", "spine_fk.001", "spine_fk.002", "spine_fk.003"])
    lerp_values(BASE, IDLE_VALS, P["u_head"], ["neck", "head"])
    pbs["torso"].location += Vector((0, 0, P.get("breath_z", 0.0))) + P.get("hips_shift", Vector((0, 0, 0)))
    if P.get("breath_flex", 0.0):
        pbs["spine_fk.002"].rotation_quaternion = Quaternion((1, 0, 0), math.radians(P["breath_flex"])) @ pbs["spine_fk.002"].rotation_quaternion
    update()
    knees = {}
    for s in "LR":
        L = P["leg_" + s]
        knees[s] = place_leg(s, L["ankle"], L["bend"], L["foot_dir"], L["sole"], L.get("toe_q"))
    S2 = wmat("DEF-spine.002")
    belly = S2 @ BELLY_LOCAL
    fb = (S2.to_3x3() @ FWD_LOCAL).normalized()
    if P.get("arms_verbatim"):             # the base's arm controls exactly as the user keyed them
        apply_values(BASE, ARM_NAMES); update()
        return {s: wmat("DEF-shin." + s).translation.copy() for s in "LR"}, belly, fb
    for s in "LR":
        mode = P["hand_" + s]
        if isinstance(mode, tuple):
            ma = hand_target(s, mode[0], P, belly, fb); mb = hand_target(s, mode[1], P, belly, fb); u = P["hand_blend"]
            target = Matrix.Translation(ma.translation.lerp(mb.translation, u)) @ ma.to_quaternion().slerp(mb.to_quaternion(), u).to_matrix().to_4x4()
        else:
            target = hand_target(s, mode, P, belly, fb)
        pbs["hand_ik." + s].matrix = rig.matrix_world.inverted() @ target
    update()
    return knees, belly, fb


def leg_lerp(A, B, u, lift=0.0, rot_u=None):
    r = u if rot_u is None else rot_u
    return {"ankle": A["ankle"].lerp(B["ankle"], u) + UP * lift, "bend": A["bend"].lerp(B["bend"], u),
            "foot_dir": A["foot_dir"].lerp(B["foot_dir"], r), "sole": A["sole"].lerp(B["sole"], r), "toe_q": A["toe_q"].slerp(B["toe_q"], r)}


def base_params():
    P = {"u_torso": 0.0, "u_head": 0.0, "fist_R": 0.9, "fist_L": 0.15, "hand_R": "hilt", "hand_L": "belly", "pull": 0.0, "hand_blend": 0.0,
         "leg_L": dict(BASE_LEG["L"]), "leg_R": dict(BASE_LEG["R"]), "shift_L": 0.0, "shift_R": 1.0}
    if not TOOL_ARMS:
        P["hand_R"] = "base"; P["hand_L"] = "base"; P["arms_verbatim"] = True
        P["fist_R"] = BASE["f_index.01_master.R"][3].x; P["fist_L"] = BASE["f_index.01_master.L"][3].x
    return P


def key_all(f):
    for n in CTRLS:
        pb = pbs[n]
        pb.keyframe_insert("location", frame=f, group=n)
        pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=n)
    for b in IKFK_ARMS + IKFK_LEGS:
        pbs[b].keyframe_insert('["IK_FK"]', frame=f, group=b)


def new_action(name):
    old = bpy.data.actions.get(name)
    if old is not None:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    set_action(act)
    if hasattr(rig.animation_data, "action_slot") and not act.slots:
        rig.animation_data.action_slot = act.slots.new(id_type='OBJECT', name=rig.name)
    return act


def build(name, n_frames, params_at, looping, ground=True, ground_off_from=None):
    act = new_action(name)

    def shifted(P, dz):
        Q = dict(P); Q["hips_shift"] = UP * dz
        Q["leg_L"] = dict(P["leg_L"]); Q["leg_R"] = dict(P["leg_R"])
        Q["leg_L"]["ankle"] = P["leg_L"]["ankle"] + UP * (dz * P.get("shift_L", 0.0)); Q["leg_R"]["ankle"] = P["leg_R"]["ankle"] + UP * (dz * P.get("shift_R", 0.0))
        return Q
    raw = []
    for f in range(n_frames):
        scene.frame_set(f + 1); pose(params_at(f)); raw.append(body_min_z())
    dz = [-m for m in raw] if ground else [0.0] * n_frames
    for _ in range(3):
        dz = [dz[0]] + [(dz[i - 1] + 2 * dz[i] + dz[i + 1]) / 4.0 for i in range(1, len(dz) - 1)] + [dz[-1]]
    if looping:
        dz[-1] = dz[0]
    if ground_off_from is not None:
        a, b = ground_off_from
        for f in range(n_frames):
            if f >= b: dz[f] = 0.0
            elif f > a: dz[f] *= 1.0 - (f - a) / float(b - a)
    final = []
    for f in range(n_frames):
        scene.frame_set(f + 1)
        knees, belly, fb = pose(shifted(params_at(f), dz[f])); key_all(f + 1); final.append(body_min_z())
        if f in (0, n_frames // 2, n_frames - 1):
            log("  %s f%3d: hips z %.3f knees z L %.3f R %.3f ankles z L %.3f R %.3f hilt->body %s floor %.4f" % (
                name, f + 1, wmat("DEF-spine").translation.z, knees["L"].z, knees["R"].z, wmat("DEF-foot.L").translation.z, wmat("DEF-foot.R").translation.z, tuple(round(v, 2) for v in (-fb)), final[-1]))
    log("%s: %d frames, floor %.4f..%.4f (raw %.4f..%.4f)" % (name, n_frames, min(final), max(final), min(raw), max(raw)))
    return act


# ------------------------------------------------------------------ Impaled_Idle
if "Impaled_Idle" in ONLY:
    def idle_at(f):
        return base_params()                                  # held still: a skeleton does not breathe
    build("Impaled_Idle", IDLE_FRAMES, idle_at, True, ground=False)
    # check the reproduction of the user's legs on frame 1
    scene.frame_set(1); update()
    for s in "LR":
        log("  base check %s: knee %s vs user %s, ankle %s vs user %s" % (s, tuple(round(v, 3) for v in wmat("DEF-shin." + s).translation), tuple(round(v, 3) for v in BASE_LEG[s]["knee"]),
            tuple(round(v, 3) for v in wmat("DEF-foot." + s).translation), tuple(round(v, 3) for v in BASE_LEG[s]["ankle"])))

# ------------------------------------------------------------------ Impaled_Rise
if "Impaled_Rise" in ONLY:
    PULL_A, PULL_B = 8, 32            # blade slides out
    ARMS_A, ARMS_B = 30, 50           # arms fall to Idle's hand positions
    RSTEP_A, RSTEP_B = 44, 70         # right foot forward to its stance
    LSTEP_A, LSTEP_B = 66, 92         # left foot back to its stance
    END = 100                         # standing neutral; 100..120 blends to Idle frame 1

    def rise_at(f):
        fr = f + 1
        P = base_params()
        pull = smooth01((fr - PULL_A) / float(PULL_B - PULL_A))
        P["pull"] = (BLADE + 0.02) * pull
        ua = smooth01((fr - ARMS_A) / float(ARMS_B - ARMS_A))
        if TOOL_ARMS:
            P["hand_R"] = ("hilt", "idle"); P["hand_L"] = ("belly", "idle")
        else:
            # frames before the pull keep the user's arm controls verbatim; from the pull on, the
            # hands are IK targets that START on the user's hands (same world pose) and slide out
            P["arms_verbatim"] = fr < PULL_A
            P["hand_R"] = ("base", "idle"); P["hand_L"] = ("base", "idle")
        P["hand_blend"] = ua
        P["fist_L"] = 0.15 + (0.3 - 0.15) * ua
        ur = smooth01((fr - RSTEP_A) / float(RSTEP_B - RSTEP_A))
        ul = smooth01((fr - LSTEP_A) / float(LSTEP_B - LSTEP_A))
        P["leg_R"] = leg_lerp(BASE_LEG["R"], IDLE_LEG["R"], ur, lift=0.08 * math.sin(math.pi * ur), rot_u=smooth01(ur / 0.45))
        P["leg_L"] = leg_lerp(BASE_LEG["L"], IDLE_LEG["L"], ul, lift=0.05 * math.sin(math.pi * ul), rot_u=smooth01(ul / 0.45))
        P["shift_R"] = 1.0 - ur; P["shift_L"] = 0.0
        # torso: a little straighter while pulling, then up with the steps; hips follow the feet
        P["u_torso"] = 0.25 * pull + 0.75 * smooth01((fr - RSTEP_A) / float(END - RSTEP_A))
        P["u_head"] = 0.35 * pull + 0.65 * smooth01((fr - RSTEP_A) / float(END - RSTEP_A))
        return P

    # no grounding pass: the base is grounded by the user (on the Knight) and the standing end
    # puts the feet on their rest spots; a pass here lifted the first frame 4 cm above the idle
    build("Impaled_Rise", END, rise_at, False, ground=False)
    scene.frame_set(RISE_FRAMES); apply_values(IDLE_VALS); update(); key_all(RISE_FRAMES)
    log("Impaled_Rise: frames %d..%d blend to Idle frame 1 (hands, legs IK<->FK); end hips z %.3f" % (END, RISE_FRAMES, wmat("DEF-spine").translation.z))

for lc in _EXCLUDED:
    lc.exclude = True
scene.frame_set(1); zero_pose()
set_action(base_act)
if SAVE:
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath, compress=True)
    log("saved " + os.path.relpath(bpy.data.filepath, ROOT))
