"""Flatten the rig's animation stack (NLA strips + the active action, e.g. a generated clip pushed down
as a strip with a hand-made fix action on top) into ONE plain action, and optionally mirror it into the
other side's clip.

    blender -b Animations/skeleton_anim.blend -P tools/anim_nla_bake.py -- --result Attack_R_Stab \
        [--frames 1:24] [--mirror-to Attack_L_Stab] [--keep-old Attack_R_Stab_base] [--save]

The evaluated pose of every animator-facing control (location, rotation, scale and the Rigify switch
properties IK_FK / pole_vector / IK_Stretch) is read frame by frame from the stack exactly as the
viewport shows it and keyed into a fresh action named --result; the old action of that name is renamed
--keep-old (default <name>_base, fake user) and every NLA track on the rig is removed, so the file is
back to "one action per clip" and export_fbx / verify_clip see what the user saw. --mirror-to writes the
same clip X-flipped (Blender's Paste X-Flipped rule: .L <-> .R, location x negated, quaternion y and z
negated, Euler controls converted through a quaternion; centre bones flipped onto themselves), the
rule verified on this rig to 0.5 mm.

Why (2026-09-23): the user edited Attack_R_Stab in the NLA (strip + a fix action) and the pipeline
exports a single action by name; also, an action that loses its last user (switching the active action
away from the fix) is dropped by Blender on save unless it has a fake user.
"""
import bpy, sys, math
from mathutils import Vector, Quaternion, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(k, d=None): return argv[argv.index(k) + 1] if k in argv else d
RESULT = arg("--result"); MIRROR_TO = arg("--mirror-to", ""); SAVE = "--save" in argv
KEEP_OLD = arg("--keep-old", RESULT + "_base")
FRAMES = arg("--frames", "")
SOURCE = arg("--action", "")
HAND_GRIP = arg("--hand-grip", "")                # "L" / "R" / "LR": after the bake, that hand's finger controls take the `Grip` action's fist on every frame (the pose the engine puts on a hand that holds an item; an empty hand on a two-hander's shaft gets none)                      # flatten THIS action instead of the rig's current stack (a plain clip with no fix on top: the tool otherwise reads whatever action happens to be active)
SPEED_SEGMENT = arg("--speed-segment", "")
ARM_POLE_FK = arg("--arm-pole-fk", "")           # "L" / "R" / "LR": on the frames where that arm is on IK, re-aim the elbow pole at the FK chain's elbow (the FK controls carry the capture's arm on every frame even while the switch is at IK), so an IK stretch inside an FK clip keeps the capture's elbow plane (a gate pull put the elbow on the rest pole: 82 mm jump at the switch)
TORSO_YAW = float(arg("--torso-yaw", "0"))       # degrees: counter-rotate the upper body against its OWN yaw excursion - at the frame where the chest has turned furthest from its first-frame heading the correction is this many degrees the other way, scaled by the excursion on every other frame (0 at the ends), spread over spine_fk.001 / .002 / chest; an IK left hand (the gate) and its pole ride along with the right hand so the two-handed grip holds (user: "attack direction is a bit to the left, add torso rotation like 50-60 degrees so the attack ends more forward")
SHAFT_HAND = arg("--shaft-hand", "")              # "L:0.056": re-seat that hand's socket ON the other hand's hilt axis every frame (0 mm off the shaft, its hilt axis parallel to the shaft, the hand's own roll about the shaft kept) and slide it this many rig m UP the shaft (toward the blade; negative = down) from where it sits now (user: "bring the left hand 10 cm higher on the weapon grip; it should follow the shaft perfectly")
_pe = arg("--pin-ease", "0").split(":")
PIN_EASE = int(_pe[0]); PIN_EASE_OUT = int(_pe[1]) if len(_pe) > 1 else PIN_EASE   # "6" or "6:2": frames to ease INTO a hold and OUT of it (a long ease-out on a walk's push-off held the lifting foot back and straightened the knee to 177 deg)           # frames: a pinned foot eases into and out of each hold over this many frames instead of switching (user: "remove the right foot snap at frames 34-35" = the release of a held landing)
GRIP_REACH = float(arg("--grip-reach", "0.96"))    # with --grip-pull: the following hand's spot is kept within this share of its arm's length from the shoulder (a straight arm flips in Humanoid: the chop's left elbow hit 178 deg with a 26 deg step)
GRIP_PULL = "--grip-pull" in argv                  # with --grip-follow: where the following hand cannot reach its place on the shaft, the OTHER hand is pulled in toward the following hand's shoulder by the shortfall (on IK, its elbow kept on the FK elbow plane), as the retarget's gate does; pair with --fk-arm on that side to land it back on FK
GRIP_FOLLOW = arg("--grip-follow", "")            # also "L:@0.056": an idealised relation - ON the other hand's hilt axis, that many rig m toward the blade, hilt axes parallel, the hand's own roll about the shaft (first frame) kept (user: "left hand always follows the handle, 10 cm above the right hand")            # "L:Idle_TwoHanded:1": that hand's socket takes, on every frame, the transform it has RELATIVE to the other hand's socket on the given action and frame (position along / off the shaft and roll about it), so a two-handed grip is identical across clips and rigid through a loop (user: "the left hand changes the grip between idle and attack; at the end it sits too close to the right; in the idle it drifts")
VSMOOTH = [int(v) for v in arg("--vsmooth", "").split(",") if v]   # frames: on each, every root-level control's world HEIGHT is replaced by the mean of its own height on the neighbouring frames (a one-frame dip of the whole body: Walk_Back frame 103, hips and both feet 6-8 mm down)
STRIDE = float(arg("--stride", "1"))             # locomotion: scale the travel along the clip's travel axis - the root's advance AND every root-level control's position along that axis about the root's first-frame spot - by this factor (0.7 = steps 30 % shorter; a planted foot stays planted, the knees bend more). Run before pins and the speed segment
LOOP_SEAM = int(arg("--loop-seam", "0"))         # frames: re-close a loop after edits - over the last N frames every control is crossfaded to its FIRST-frame pose (root-space locations shifted by the root's travel), so the last frame equals the first + travel exactly (a fix keyed near the ends had left the left foot 10 mm higher on the last frame than on the first)
LOOP = "--loop" in argv                           # the clip is a cycle: a pin's flight-phase correction wraps across the seam (last frame -> first)
UPPER_FROM = arg("--upper-from", "")              # "Idle_03:1": after the retime, every control ABOVE the legs (the torso's rotation - its location stays the clip's - spine, chest, neck, head, jaw, shoulders, arms, hands, fingers and the arm IK/FK switches) is taken frame by frame from that action starting at that frame (wrapping over its length), the clip keeping its root, hips, legs and feet (user, Walk_Back: "too much movement above the legs, use the above-torso animation from idle_3")
UPPER_SEAM = int(arg("--upper-seam", "8"))         # frames: the copied window's end crossfaded to its start so the loop closes
HAND_WEIGHT = arg("--hand-weight", "")            # "R:0.015:4:6": that IK hand bobs against the body's vertical sway as if the held item had weight - the hips' height over the clip, normalised to -1..1, delayed DELAY frames (wrapping over a loop), moves the hand AMP rig m the OTHER way and pitches it PITCH degrees about the socket's finger axis (the tip dips as the hand drops) (user, Idle_Wand: "right hand sway that mimics the wand's weight, in sync with the character swaying up and down")
IK_LEGS = "--ik-legs" in argv                     # after the bake, both legs on IK on every frame, the foot/toe controls on the DEF result and the knee pole out through the FK knee (refined): lossless (the walks' legs are FK from the retarget; a foot pin on an FK leg would switch modes and jump the knee)
FK_ARM = arg("--fk-arm", "")                      # "L" / "R" / "LR": after the bake, that arm is put on FK on every frame, the FK chain set to the arm's current (IK) result: lossless, and upper_arm_fk / forearm_fk / hand_fk then control it (user, on Block_L_Idle whose left arm was IK throughout: "upper_arm_fk_l and its children won't change the mesh")        # "A:B:F": after the bake (and pin), frames A..B of the result are resampled F times faster (Blender's own curve evaluation at fractional frames), the frames after B shift earlier (user: "speed up by 35% from frame 21 to 34")
PIN_FOOT = arg("--pin-foot", "")                  # "L" / "L:1" / "L,R" / "L:20:20:34": SIDE[:ref[:from[:to]]] - after the bake, that foot's IK control (and toe) is held from frame `from` to `to` (default: the whole clip) at the WORLD transform it has on frame `ref` (default: the first frame): a planted foot that the capture let drift (user: "get rid of the drift on the left feet"; "left foot drift after the step forward, from frame 20")
assert RESULT, "--result NAME is required"

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
scene = bpy.context.scene; pbs = rig.pose.bones; ad = rig.animation_data
CONTROLS = [b.name for b in pbs if not b.name.startswith(("DEF-", "MCH-", "ORG-", "VIS_"))]
PROPS = ("IK_FK", "pole_vector", "IK_Stretch")


def log(*a): print("[nla_bake]", *a)


def stack_range():
    lo, hi = None, None
    for t in ad.nla_tracks:
        if t.mute:
            continue
        for s in t.strips:
            if s.mute or s.influence == 0.0:
                continue
            lo = s.frame_start if lo is None else min(lo, s.frame_start); hi = s.frame_end if hi is None else max(hi, s.frame_end)
    if ad.action is not None:
        a0, a1 = ad.action.frame_range
        lo = a0 if lo is None else min(lo, a0); hi = a1 if hi is None else max(hi, a1)
    return int(round(lo)), int(round(hi))


STACK_KEEP = None
if SOURCE:
    src_act = bpy.data.actions[SOURCE]
    STACK_KEEP = {"active": ad.action.name if ad.action else None, "blend": ad.action_blend_type, "influence": ad.action_influence,
                  "tracks": [(t, t.mute, [(st, st.action.name if st.action else None) for st in t.strips]) for t in ad.nla_tracks]}
    for t in ad.nla_tracks:
        t.mute = True
    ad.action = src_act; ad.action_blend_type = 'REPLACE'; ad.action_influence = 1.0
    if hasattr(ad, "action_slot") and src_act.slots:
        ad.action_slot = src_act.slots[0]
    log("source: action %s (NLA tracks muted)" % SOURCE)
if FRAMES:
    F0, F1 = (int(v) for v in FRAMES.split(":"))
else:
    F0, F1 = stack_range()
if ad.action is not None and ad.nla_tracks and ad.action_blend_type == 'COMBINE':
    _root_keys = [fc for fc in (fc_ for l_ in ad.action.layers for st_ in l_.strips for cb_ in st_.channelbags for fc_ in cb_.fcurves) if fc.data_path == 'pose.bones["root"].location' and any(abs(k.co.y) > 1e-6 for k in fc.keyframe_points)]
    if _root_keys:
        log("WARNING: the fix action %s keys the root's location (%d channels, non-zero): in Combine that adds to the strip's root travel (a whole-character key at the last frame cancels a clip's root motion). Drop those channels from the fix unless the root offset is intended" % (ad.action.name, len(_root_keys)))
log("stack: active action %s (%s, influence %.2f), %d NLA tracks; baking frames %d..%d" % (
    ad.action.name if ad.action else None, ad.action_blend_type, ad.action_influence, len(ad.nla_tracks), F0, F1))
for t in ad.nla_tracks:
    for s in t.strips:
        log("  track %s strip %s -> action %s, %s, influence %.2f, frames %.0f..%.0f%s" % (
            t.name, s.name, s.action.name if s.action else None, s.blend_type, s.influence, s.frame_start, s.frame_end, " (muted)" if (t.mute or s.mute) else ""))

def read_pose():
    fr = {}
    for n in CONTROLS:
        pb = pbs[n]
        rec = {"loc": pb.location.copy(), "scale": pb.scale.copy(), "mode": pb.rotation_mode}
        if pb.rotation_mode == 'QUATERNION':
            rec["rot"] = pb.rotation_quaternion.copy()
        elif pb.rotation_mode == 'AXIS_ANGLE':
            rec["rot"] = Quaternion(pb.rotation_axis_angle[1:], pb.rotation_axis_angle[0])
        else:
            rec["rot"] = pb.rotation_euler.to_quaternion()
        for p in PROPS:
            if p in pb:
                rec[p] = pb[p]                              # keep the type: pole_vector is a Boolean IDProperty
        fr[n] = rec
    return fr


# 1. read the evaluated pose of every control per frame
poses = {}
for f in range(F0, F1 + 1):
    scene.frame_set(f)
    poses[f] = read_pose()
log("read %d frames x %d controls" % (len(poses), len(CONTROLS)))


def other(n):
    if n.endswith(".L"): return n[:-2] + ".R"
    if n.endswith(".R"): return n[:-2] + ".L"
    return n


def flip(rec):
    q = rec["rot"]
    return dict(rec, loc=Vector((-rec["loc"].x, rec["loc"].y, rec["loc"].z)), rot=Quaternion((q.w, q.x, -q.y, -q.z)))


def write_action(name, frames_, mirror):
    old = bpy.data.actions.get(name)
    if old is not None:
        keep = KEEP_OLD if name == RESULT else name + "_base"
        if bpy.data.actions.get(keep) is None:
            old.name = keep; old.use_fake_user = True
            log("old %s kept as %s (fake user)" % (name, keep))
        else:
            ad.action = None
            bpy.data.actions.remove(old)                     # the generated base is already kept; this was an earlier bake
            log("old %s replaced (%s already holds the generated clip)" % (name, keep))
    act = bpy.data.actions.new(name); act.use_fake_user = True
    # a clean stack for keying: no NLA, the new action active (a named --action keeps the user's stack:
    # its strips are re-pointed at the new action and the active fix restored at the end)
    if STACK_KEEP is None:
        for t in list(ad.nla_tracks):
            ad.nla_tracks.remove(t)
    ad.action = act; ad.action_blend_type = 'REPLACE'; ad.action_influence = 1.0
    if hasattr(ad, "action_slot") and act.slots:
        ad.action_slot = act.slots[0]
    for f in sorted(frames_):
        fr = frames_[f]
        scene.frame_set(f)                                   # BEFORE posing (frame_set re-applies the action being written)
        for n in CONTROLS:
            src = fr[other(n)] if mirror else fr[n]
            rec = flip(src) if mirror else src
            pb = pbs[n]
            pb.location = rec["loc"]; pb.scale = rec["scale"]
            if pb.rotation_mode == 'QUATERNION':
                pb.rotation_quaternion = rec["rot"]
            elif pb.rotation_mode == 'AXIS_ANGLE':
                ax, an = rec["rot"].to_axis_angle(); pb.rotation_axis_angle = (an, ax.x, ax.y, ax.z)
            else:
                pb.rotation_euler = rec["rot"].to_euler(pb.rotation_mode)
            for p in PROPS:
                if p in rec and p in pb:
                    pb[p] = bool(rec[p]) if isinstance(pb[p], bool) else float(rec[p])
        for n in CONTROLS:
            pb = pbs[n]
            pb.keyframe_insert("location", frame=f, group=n)
            pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_axis_angle" if pb.rotation_mode == 'AXIS_ANGLE' else "rotation_euler", frame=f, group=n)
            pb.keyframe_insert("scale", frame=f, group=n)
            for p in PROPS:
                if p in pb and any(p in fr[m] for m in (n,)):
                    pb.keyframe_insert('["%s"]' % p, frame=f, group=n)
    act.frame_range = (F0, F1)
    log("wrote %s: frames %d..%d, %d controls%s" % (name, F0, F1, len(CONTROLS), ", X-flipped" if mirror else ""))
    return act


FOOTIK_REL = {}
def _footik_rel():
    prev = ad.action; ad.action = None
    for pb in pbs: pb.matrix_basis.identity()
    bpy.context.view_layer.update()
    for s_ in ("L", "R"):
        FOOTIK_REL[s_] = (rig.matrix_world @ pbs["DEF-foot." + s_].matrix).inverted() @ (rig.matrix_world @ pbs["foot_ik." + s_].matrix)
    ad.action = prev; bpy.context.view_layer.update()


def leg_pole(side, knee_target, hip_, ankle_):
    """Aim the leg's IK pole so the DEF knee lands on knee_target's side of the hip->ankle axis (three refinements)."""
    sw = pbs["thigh_parent." + side]; pole = pbs["thigh_ik_target." + side]
    ax = ankle_ - hip_
    if ax.length < 1e-6:
        return
    ax.normalize(); d_ = knee_target - hip_; perp = d_ - ax * d_.dot(ax)
    if perp.length < 0.005:
        return
    sw["pole_vector"] = True
    pt = knee_target + perp.normalized() * 0.4
    for _ in range(3):
        pm = pole.matrix.copy(); pm.translation = rig.matrix_world.inverted() @ pt; pole.matrix = pm; bpy.context.view_layer.update()
        k_ = (rig.matrix_world @ pbs["DEF-shin." + side].matrix).translation
        dk = k_ - hip_; pk = dk - ax * dk.dot(ax)
        if pk.length < 1e-4 or (k_ - knee_target).length < 0.0005:
            break
        ang = pk.normalized().angle(perp.normalized())
        if pk.normalized().cross(perp.normalized()).dot(ax) < 0:
            ang = -ang
        pt = hip_ + Matrix.Rotation(ang, 3, ax) @ (pt - hip_)


def loop_seam(act, n):
    ad.action = act
    scene.frame_set(F0); first = read_pose(); r0 = (rig.matrix_world @ pbs["root"].matrix).translation.copy()
    scene.frame_set(F1); r1 = (rig.matrix_world @ pbs["root"].matrix).translation.copy()
    travel = r1 - r0
    rootspace = {"root", "torso", "foot_ik.L", "foot_ik.R", "thigh_ik_target.L", "thigh_ik_target.R", "hand_ik.L", "hand_ik.R", "upper_arm_ik_target.L", "upper_arm_ik_target.R"}
    # the target pose for the LAST frame: the first frame, root-space controls advanced by the travel (world space)
    scene.frame_set(F0); tgt_world = {c: (rig.matrix_world @ pbs[c].matrix).copy() for c in rootspace}
    for c in tgt_world:
        tgt_world[c].translation = tgt_world[c].translation + travel
    for i, f in enumerate(range(F1 - n + 1, F1 + 1)):
        w = (i + 1) / float(n); w = w * w * (3 - 2 * w)
        scene.frame_set(f)
        cur = read_pose()
        for c in CONTROLS:
            pb = pbs[c]; a = cur[c]; b = first[c]
            qa = a["rot"]; qb = b["rot"]
            if qa.dot(qb) < 0: qb = -qb
            q = qa.slerp(qb, w)
            if pb.rotation_mode == 'QUATERNION': pb.rotation_quaternion = q
            elif pb.rotation_mode == 'AXIS_ANGLE':
                ax_, an_ = q.to_axis_angle(); pb.rotation_axis_angle = (an_, ax_.x, ax_.y, ax_.z)
            else: pb.rotation_euler = q.to_euler(pb.rotation_mode)
            pb.scale = a["scale"].lerp(b["scale"], w)
            if c not in rootspace:
                pb.location = a["loc"].lerp(b["loc"], w)
        bpy.context.view_layer.update()
        for c in ["root"] + sorted(rootspace - {"root"}):        # root first (children ride), then absolute world placement
            pb = pbs[c]; m = (rig.matrix_world @ pb.matrix).copy()
            m.translation = m.translation.lerp(tgt_world[c].translation, w)
            pb.matrix = rig.matrix_world.inverted() @ m; bpy.context.view_layer.update()
        for c in CONTROLS:
            pb = pbs[c]
            pb.keyframe_insert("location", frame=f, group=c)
            pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_axis_angle" if pb.rotation_mode == 'AXIS_ANGLE' else "rotation_euler", frame=f, group=c)
            pb.keyframe_insert("scale", frame=f, group=c)
    scene.frame_set(F1)
    worst = 0.0
    for c in ("DEF-foot.L", "DEF-foot.R", "DEF-spine", "DEF-hand.L", "DEF-hand.R", "DEF-spine.006"):
        p1 = (rig.matrix_world @ pbs[c].matrix).translation.copy(); scene.frame_set(F0); p0 = (rig.matrix_world @ pbs[c].matrix).translation.copy(); scene.frame_set(F1)
        worst = max(worst, ((p1 - travel) - p0).length * 1000)
    log("loop-seam over the last %d frames: last frame = first + travel (%.3f, %.3f, %.3f) within %.1f mm on feet, hips, hands and head" % (n, travel.x, travel.y, travel.z, worst))


UPPER_CTRLS = None
def upper_controls():
    global UPPER_CTRLS
    if UPPER_CTRLS is None:
        keep = {"root", "torso", "hips", "foot_ik.L", "foot_ik.R", "toe_ik.L", "toe_ik.R", "foot_fk.L", "foot_fk.R", "toe_fk.L", "toe_fk.R",
                "thigh_fk.L", "thigh_fk.R", "shin_fk.L", "shin_fk.R", "thigh_ik.L", "thigh_ik.R", "thigh_ik_target.L", "thigh_ik_target.R",
                "thigh_parent.L", "thigh_parent.R", "foot_heel_ik.L", "foot_heel_ik.R", "foot_spin_ik.L", "foot_spin_ik.R",
                "thigh_tweak.L", "thigh_tweak.R", "shin_tweak.L", "shin_tweak.R", "foot_tweak.L", "foot_tweak.R", "spine_fk"}
        UPPER_CTRLS = [c for c in CONTROLS if c not in keep and not c.startswith("VIS_")]
    return UPPER_CTRLS


def upper_from(act, spec, seam):
    src_name, start = spec.split(":"); start = int(start); src = bpy.data.actions[src_name]
    s0, s1 = (int(round(x)) for x in src.frame_range); n_src = s1 - s0 + 1
    ctrls = upper_controls()
    # read the source window
    ad.action = src; win = {}
    for i in range(F1 - F0 + 1):
        sf = s0 + ((start - s0) + i) % n_src
        scene.frame_set(sf); win[F0 + i] = read_pose()
    # the window's last `seam` frames crossfaded to its first frame so the copy loops
    first = win[F0]
    for j, f in enumerate(range(F1 - seam + 1, F1 + 1)):
        w = (j + 1) / float(seam + 1); w = w * w * (3 - 2 * w)
        for c in ctrls:
            a = win[f][c]; b = first[c]; qa = a["rot"]; qb = b["rot"]
            if qa.dot(qb) < 0: qb = -qb
            win[f][c] = dict(a, loc=a["loc"].lerp(b["loc"], w), rot=qa.slerp(qb, w), scale=a["scale"].lerp(b["scale"], w))
    # write onto the clip: torso rotation only (its location is the walk's), everything else whole
    ad.action = act
    for f in range(F0, F1 + 1):
        scene.frame_set(f)
        for c in ctrls:
            rec = win[f][c]; pb = pbs[c]
            if c != "torso":
                pb.location = rec["loc"]; pb.scale = rec["scale"]
            if pb.rotation_mode == 'QUATERNION': pb.rotation_quaternion = rec["rot"]
            elif pb.rotation_mode == 'AXIS_ANGLE':
                ax_, an_ = rec["rot"].to_axis_angle(); pb.rotation_axis_angle = (an_, ax_.x, ax_.y, ax_.z)
            else: pb.rotation_euler = rec["rot"].to_euler(pb.rotation_mode)
            for p_ in PROPS:
                if p_ in rec and p_ in pb:
                    pb[p_] = bool(rec[p_]) if isinstance(pb[p_], bool) else float(rec[p_])
        bpy.context.view_layer.update()
        for c in ctrls:
            pb = pbs[c]
            pb.keyframe_insert("location", frame=f, group=c)
            pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_axis_angle" if pb.rotation_mode == 'AXIS_ANGLE' else "rotation_euler", frame=f, group=c)
            pb.keyframe_insert("scale", frame=f, group=c)
            for p_ in PROPS:
                if p_ in pb and p_ in win[f][c]:
                    pb.keyframe_insert('["%s"]' % p_, frame=f, group=c)
    log("upper body from %s frames %d..%d (of %d) onto %d controls, the last %d frames crossfaded to the first (torso: rotation only)" % (src_name, start, start + (F1 - F0), n_src, len(ctrls), seam))


def hand_weight(act, spec):
    parts = spec.split(":"); side = parts[0]; amp = float(parts[1]); delay = int(parts[2]) if len(parts) > 2 else 0; pitch = math.radians(float(parts[3])) if len(parts) > 3 else 0.0
    ad.action = act; n = F1 - F0 + 1
    zs = []
    for f in range(F0, F1 + 1):
        scene.frame_set(f); zs.append((rig.matrix_world @ pbs["DEF-spine"].matrix).translation.z)
    zmid = 0.5 * (max(zs) + min(zs)); half = 0.5 * (max(zs) - min(zs)) or 1e-6
    norm = [(z - zmid) / half for z in zs]
    # sign of the pitch: the rotation about the socket's X that lowers the hilt axis (+Y) when applied positively
    scene.frame_set(F0); sock = (rig.matrix_world @ pbs["DEF-weapon." + side].matrix).copy()
    x_ = (sock.to_3x3() @ Vector((1, 0, 0))).normalized(); y_ = (sock.to_3x3() @ Vector((0, 1, 0))).normalized()
    sgn = 1.0 if (Matrix.Rotation(0.1, 3, x_) @ y_).z < y_.z else -1.0
    pbs["upper_arm_parent." + side]["IK_FK"] = 0.0
    lo = hi = 0.0
    for i, f in enumerate(range(F0, F1 + 1)):
        scene.frame_set(f)
        u = -norm[(i - delay) % n]                                # against the body: the body up, the weight lags down
        dz = amp * u; lo = min(lo, dz); hi = max(hi, dz)
        h = pbs["hand_ik." + side]; hm = (rig.matrix_world @ h.matrix).copy()
        sock = (rig.matrix_world @ pbs["DEF-weapon." + side].matrix).copy()
        x_ = (sock.to_3x3() @ Vector((1, 0, 0))).normalized()
        R = Matrix.Rotation(sgn * pitch * u, 4, x_)
        T = Matrix.Translation(Vector((0, 0, dz))) @ Matrix.Translation(sock.translation) @ R @ Matrix.Translation(-sock.translation)
        h.matrix = rig.matrix_world.inverted() @ (T @ hm); pbs["upper_arm_parent." + side]["IK_FK"] = 0.0
        bpy.context.view_layer.update()
        h.keyframe_insert("location", frame=f, group="hand_ik." + side)
        h.keyframe_insert("rotation_quaternion" if h.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group="hand_ik." + side)
        pbs["upper_arm_parent." + side].keyframe_insert('["IK_FK"]', frame=f, group="upper_arm_parent." + side)
    log("hand-weight %s: hips sway +-%.1f mm -> hand %+.1f..%+.1f mm the other way, delayed %d frames, pitch +-%.0f deg" % (side, half * 1000, lo * 1000, hi * 1000, delay, math.degrees(pitch)))


def stride(act, k):
    """Shorter (or longer) steps: p' = p + (k-1)((p - r0).axis) axis for the root, torso, feet, toes, knee poles,
    IK hands and elbow poles, axis = the root's net travel direction, r0 = the root on the first frame. A
    planted foot (constant p) stays planted; the body travels k times as far; the feet's fore-aft excursion
    relative to the hips scales by k."""
    ad.action = act
    scene.frame_set(F0); r0 = (rig.matrix_world @ pbs["root"].matrix).translation.copy()
    scene.frame_set(F1); r1 = (rig.matrix_world @ pbs["root"].matrix).translation.copy()
    axis = r1 - r0
    if axis.length < 1e-4:
        log("stride: the root does not travel in this clip; nothing to scale"); return
    axis.normalize()
    ctrls = ["root", "torso", "foot_ik.L", "foot_ik.R", "thigh_ik_target.L", "thigh_ik_target.R", "hand_ik.L", "hand_ik.R", "upper_arm_ik_target.L", "upper_arm_ik_target.R"]
    for f in range(F0, F1 + 1):
        scene.frame_set(f)
        want = {}
        for c in ctrls:
            p_ = (rig.matrix_world @ pbs[c].matrix).translation.copy()
            want[c] = p_ + axis * ((k - 1.0) * (p_ - r0).dot(axis))
        for c in ctrls:                                     # root first: its children ride, then each is placed absolutely
            pb = pbs[c]; m = (rig.matrix_world @ pb.matrix).copy(); m.translation = want[c]
            pb.matrix = rig.matrix_world.inverted() @ m; bpy.context.view_layer.update()
            pb.keyframe_insert("location", frame=f, group=c)
    scene.frame_set(F1); r1n = (rig.matrix_world @ pbs["root"].matrix).translation
    log("stride x%.2f along (%.2f, %.2f, %.2f): root travel %.3f -> %.3f rig m per clip" % (k, axis.x, axis.y, axis.z, (r1 - r0).length, (r1n - r0).length))


def vsmooth(act, frames):
    """Remove a one-frame vertical hiccup: for each listed frame, each root-level control (root, torso, feet,
    toes, knee poles, IK hands and elbow poles) takes the mean of its own world height on the frames before
    and after, x/y and rotation untouched. root first (its children ride), then the rest re-read."""
    ad.action = act
    ctrls = ["root", "torso", "foot_ik.L", "foot_ik.R", "toe_ik.L", "toe_ik.R", "thigh_ik_target.L", "thigh_ik_target.R",
             "hand_ik.L", "hand_ik.R", "upper_arm_ik_target.L", "upper_arm_ik_target.R"]
    for f in frames:
        if f <= F0 or f >= F1:
            continue
        zs = {}
        for g in (f - 1, f + 1):
            scene.frame_set(g)
            zs[g] = {c: (rig.matrix_world @ pbs[c].matrix).translation.z for c in ctrls}
        scene.frame_set(f); moved = []
        for c in ctrls:
            pb = pbs[c]; m = (rig.matrix_world @ pb.matrix).copy()
            want = 0.5 * (zs[f - 1][c] + zs[f + 1][c]); d = want - m.translation.z
            if abs(d) < 1e-5:
                continue
            m.translation = Vector((m.translation.x, m.translation.y, want))
            pb.matrix = rig.matrix_world.inverted() @ m; bpy.context.view_layer.update()
            pb.keyframe_insert("location", frame=f, group=c); moved.append("%s %+.1f" % (c, d * 1000))
        hz = (rig.matrix_world @ pbs["DEF-spine"].matrix).translation.z
        log("vsmooth frame %d: %s; hips now %.4f (neighbours %.4f / %.4f)" % (f, ", ".join(moved) if moved else "nothing to do", hz, 0, 0))


def ik_legs(act):
    if not FOOTIK_REL:
        _footik_rel()
    ad.action = act
    for side in ("L", "R"):
        worst = 0.0; wk = 0.0
        for f in range(F0, F1 + 1):
            scene.frame_set(f)
            fm = (rig.matrix_world @ pbs["DEF-foot." + side].matrix).copy()
            toe_q = (rig.matrix_world @ pbs["DEF-toe." + side].matrix).to_quaternion()
            knee = (rig.matrix_world @ pbs["DEF-shin." + side].matrix).translation.copy()
            hip_ = (rig.matrix_world @ pbs["DEF-thigh." + side].matrix).translation.copy()
            pbs["thigh_parent." + side]["IK_FK"] = 0.0
            pbs["foot_ik." + side].matrix = rig.matrix_world.inverted() @ fm @ FOOTIK_REL[side]; bpy.context.view_layer.update()
            leg_pole(side, knee, hip_, fm.translation)
            t = pbs["toe_ik." + side]; tm = t.matrix.copy(); r = (rig.matrix_world.to_3x3().inverted() @ toe_q.to_matrix()).to_4x4(); r.translation = tm.translation; t.matrix = r; bpy.context.view_layer.update()
            for n in ("foot_ik." + side, "toe_ik." + side, "thigh_ik_target." + side):
                pbs[n].keyframe_insert("location", frame=f, group=n)
                pbs[n].keyframe_insert("rotation_quaternion" if pbs[n].rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=n)
            pbs["thigh_parent." + side].keyframe_insert('["IK_FK"]', frame=f, group="thigh_parent." + side)
            pbs["thigh_parent." + side].keyframe_insert('["pole_vector"]', frame=f, group="thigh_parent." + side)
            worst = max(worst, ((rig.matrix_world @ pbs["DEF-foot." + side].matrix).translation - fm.translation).length * 1000)
            wk = max(wk, ((rig.matrix_world @ pbs["DEF-shin." + side].matrix).translation - knee).length * 1000)
        log("legs on IK: %s foot reproduced within %.1f mm, knee within %.1f mm on every frame" % (side, worst, wk))


def fk_knee(side):
    """The clip's own FK knee (the FK chain still carries the retarget's legs after --ik-legs): a continuous
    reference for the IK pole plane on every frame - the DEF knee of a previous pass is not (a pole flip
    swung the left knee 73 mm on one frame)."""
    return (rig.matrix_world @ pbs["shin_fk." + side].matrix).translation.copy()


def repole_legs(act):
    """Aim both legs' IK poles at the FK knee plane on every frame and key them."""
    ad.action = act
    for side in ("L", "R"):
        worst = 0.0; prev = None
        for f in range(F0, F1 + 1):
            scene.frame_set(f)
            if pbs["thigh_parent." + side]["IK_FK"] > 0.5:
                continue
            hip_ = (rig.matrix_world @ pbs["DEF-thigh." + side].matrix).translation.copy()
            ank_ = (rig.matrix_world @ pbs["DEF-foot." + side].matrix).translation.copy()
            leg_pole(side, fk_knee(side), hip_, ank_)
            pole = pbs["thigh_ik_target." + side]
            pole.keyframe_insert("location", frame=f, group="thigh_ik_target." + side)
            pole.keyframe_insert("rotation_quaternion" if pole.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group="thigh_ik_target." + side)
            pbs["thigh_parent." + side].keyframe_insert('["pole_vector"]', frame=f, group="thigh_parent." + side)
            k_ = (rig.matrix_world @ pbs["DEF-shin." + side].matrix).translation.copy()
            if prev is not None:
                worst = max(worst, (k_ - prev).length * 1000)
            prev = k_
        log("legs re-poled on the FK knee plane: %s knee's largest step %.0f mm per frame" % (side, worst))


def pin_feet(act):
    """Hold a planted foot in world space. Spec SIDE[:ref[:from[:to]]][:xy] or SIDE:auto[:xy] (planted phases
    found from the ankle height, a phase touching the first/last frame referencing that frame so a loop's
    seam holds, an inner phase its middle frame). `xy` holds the horizontal position only (height and
    rotation kept: a heel lift survives). The correction a hold applies (pin minus the clip's own foot) is
    carried SMOOTHLY through the flight between two holds - from the end of one to the start of the next,
    wrapping across the seam with --loop - instead of switching on over a few frames before landing (the
    walk-back's right foot took its 9 cm lateral correction in the last 6 frames of its swing). The IK pole
    follows the FK knee plane on every frame."""
    ad.action = act
    specs = {}
    for spec in PIN_FOOT.split(","):
        if not spec:
            continue
        parts = spec.split(":"); side = parts[0]; xy = parts[-1] == "xy"
        if xy:
            parts = parts[:-1]
        specs.setdefault(side, []).append((parts[1:], xy))
    for side, lst in specs.items():
        # the clip's own foot, per frame
        own = {}; zs = {}
        for f in range(F0, F1 + 1):
            scene.frame_set(f); own[f] = (rig.matrix_world @ pbs["foot_ik." + side].matrix).copy(); zs[f] = (rig.matrix_world @ pbs["DEF-foot." + side].matrix).translation.z
        phases = []
        for parts, xy in lst:
            if parts and parts[0] == "auto":
                zmin = min(zs.values()); planted = [f for f in range(F0, F1 + 1) if zs[f] <= zmin + 0.012]
                ph = []
                for f in planted:
                    if ph and f == ph[-1][1] + 1: ph[-1][1] = f
                    else: ph.append([f, f])
                ph = [x for x in ph if x[1] - x[0] + 1 >= 3]
                log("foot %s auto: lowest ankle %.3f, planted phases %s" % (side, zmin, ", ".join("%d..%d" % tuple(x) for x in ph)))
                for p0, p1 in ph:
                    ref_ = F0 if p0 == F0 else (F1 if p1 == F1 else (p0 + p1) // 2)
                    phases.append((ref_, p0, p1, xy))
            else:
                ref_ = int(parts[0]) if parts and parts[0] else F0
                p0 = int(parts[1]) if len(parts) > 1 and parts[1] else F0
                p1 = min(F1, int(parts[2])) if len(parts) > 2 and parts[2] else F1
                phases.append((ref_, max(F0, p0), p1, xy))
        phases.sort(key=lambda x: x[1])
        # target per held frame, and the correction (target - own) at each phase's ends
        target = {}
        for ref_, p0, p1, xy in phases:
            foot_m = own[ref_]
            for f in range(p0, p1 + 1):
                if xy:
                    t = own[f].copy(); t.translation = Vector((foot_m.translation.x, foot_m.translation.y, own[f].translation.z))
                else:
                    t = foot_m.copy()
                target[f] = t
        # flight phases: carry the correction from the previous hold's end to the next hold's start
        def corr(f):
            d = target[f].translation - own[f].translation
            q = own[f].to_quaternion().rotation_difference(target[f].to_quaternion()); return d, q
        held = sorted(target)
        gaps = []
        for i, (ref_, p0, p1, xy) in enumerate(phases):
            nxt = phases[(i + 1) % len(phases)] if phases else None
            if nxt is None:
                break
            if i + 1 < len(phases):
                gaps.append((p1, nxt[1], False))
            elif LOOP and len(phases) >= 1:
                gaps.append((p1, nxt[1], True))            # wraps: p1..F1 then F0..next p0
        zmin_ = min(zs.values())
        for a_, b_, wrap in gaps:
            da, qa = corr(a_); db, qb = corr(b_)
            if qa.dot(qb) < 0: qb = -qb
            frames_ = list(range(a_ + 1, F1 + 1)) + list(range(F0, b_)) if wrap else list(range(a_ + 1, b_))
            # the correction changes only while the foot is IN THE AIR: constant (the previous hold's) while it is
            # still on the ground after the hold, a smoothstep through the flight, constant (the next hold's) once
            # it has landed - a carry across an unpinned stance pushed that foot 6 cm and locked the knee at 177
            air = [i for i, f in enumerate(frames_) if zs[f] > zmin_ + 0.012]
            i0, i1 = (air[0], air[-1]) if air else (0, len(frames_) - 1)
            for j, f in enumerate(frames_):
                if j < i0: w = 0.0
                elif j > i1: w = 1.0
                else:
                    w = (j - i0 + 1) / float(i1 - i0 + 2); w = w * w * (3 - 2 * w)
                d = da.lerp(db, w); q = qa.slerp(qb, w)
                t = own[f].copy(); r = q.to_matrix().to_4x4() @ Matrix.Translation(-own[f].translation) @ own[f]; r = Matrix.Translation(own[f].translation + d) @ r
                target[f] = r
        # the clip edges of a one-shot: ease the first/last correction out over PIN_EASE / PIN_EASE_OUT frames
        if not LOOP and phases:
            f0p = phases[0][1]; f1p = phases[-1][2]
            for k_, f in enumerate(range(f0p - 1, max(F0, f0p - PIN_EASE) - 1, -1)):
                w = 1.0 - (k_ + 1) / float(PIN_EASE + 1); d, q = corr(f0p); q = Quaternion((1, 0, 0, 0)).slerp(q, w)
                t = q.to_matrix().to_4x4() @ Matrix.Translation(-own[f].translation) @ own[f]; target[f] = Matrix.Translation(own[f].translation + d * w) @ t
            for k_, f in enumerate(range(f1p + 1, min(F1, f1p + PIN_EASE_OUT) + 1)):
                w = 1.0 - (k_ + 1) / float(PIN_EASE_OUT + 1); d, q = corr(f1p); q = Quaternion((1, 0, 0, 0)).slerp(q, w)
                t = q.to_matrix().to_4x4() @ Matrix.Translation(-own[f].translation) @ own[f]; target[f] = Matrix.Translation(own[f].translation + d * w) @ t
        # apply
        worst_gap = 0.0; kmin = 180.0; kmax = 0.0; toe_hold = {}
        for ref_, p0, p1, xy in phases:
            if not xy:
                scene.frame_set(ref_); toe_hold[(p0, p1)] = (rig.matrix_world @ pbs["toe_ik." + side].matrix).copy()
        for f in range(F0, F1 + 1):
            if f not in target:
                continue
            scene.frame_set(f)
            pb = pbs["foot_ik." + side]; pb.matrix = rig.matrix_world.inverted() @ target[f]
            pbs["thigh_parent." + side]["IK_FK"] = 0.0; bpy.context.view_layer.update()
            hip_ = (rig.matrix_world @ pbs["DEF-thigh." + side].matrix).translation.copy()
            leg_pole(side, fk_knee(side), hip_, target[f].translation)
            for (p0, p1), tm in toe_hold.items():
                if p0 <= f <= p1:
                    pt = pbs["toe_ik." + side]; pt.matrix = rig.matrix_world.inverted() @ tm; bpy.context.view_layer.update()
            for n in ("foot_ik." + side, "toe_ik." + side, "thigh_ik_target." + side):
                pbs[n].keyframe_insert("location", frame=f, group=n)
                pbs[n].keyframe_insert("rotation_quaternion" if pbs[n].rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=n)
            pbs["thigh_parent." + side].keyframe_insert('["IK_FK"]', frame=f, group="thigh_parent." + side)
            pbs["thigh_parent." + side].keyframe_insert('["pole_vector"]', frame=f, group="thigh_parent." + side)
            knee = (rig.matrix_world @ pbs["DEF-shin." + side].matrix).translation; ank = (rig.matrix_world @ pbs["DEF-foot." + side].matrix).translation
            a_ = math.degrees((hip_ - knee).angle(ank - knee)); kmin = min(kmin, a_); kmax = max(kmax, a_)
            if any(p0 <= f <= p1 for _, p0, p1, _ in phases):
                worst_gap = max(worst_gap, (ank - target[f].translation).length * 1000)
        log("foot %s: %s; corrections carried through %d flight phase(s)%s; knee %.0f..%.0f deg, DEF foot within %.1f mm of its hold on every held frame" % (
            side, ", ".join("%d..%d @f%d%s" % (p0, p1, r_, " xy" if xy else "") for r_, p0, p1, xy in phases), len(gaps), " (loop)" if LOOP else "", kmin, kmax, worst_gap))


# 2. check that the flat action reproduces the stack: DEF bones before vs after
DEF = [b.name for b in pbs if b.name.startswith("DEF-")]
ref = {}
for f in range(F0, F1 + 1):
    scene.frame_set(f); ref[f] = {b: (rig.matrix_world @ pbs[b].matrix).copy() for b in DEF}
baked = write_action(RESULT, poses, False)
worst = (0.0, "", 0); worst_r = (0.0, "", 0)
for f in range(F0, F1 + 1):
    scene.frame_set(f)
    for b in DEF:
        m = rig.matrix_world @ pbs[b].matrix
        dp = (m.translation - ref[f][b].translation).length * 1000
        dr = math.degrees(m.to_quaternion().rotation_difference(ref[f][b].to_quaternion()).angle)
        if dp > worst[0]: worst = (dp, b, f)
        if dr > worst_r[0]: worst_r = (dr, b, f)
log("flat %s vs the stack: worst DEF position %.2f mm (%s f%d), worst rotation %.2f deg (%s f%d)" % (RESULT, worst[0], worst[1], worst[2], worst_r[0], worst_r[1], worst_r[2]))
if IK_LEGS:
    ik_legs(baked)                                   # first: the height smoothing and the stride move foot_ik, which is inert on FK legs

if VSMOOTH:
    vsmooth(baked, VSMOOTH)

if STRIDE != 1.0:
    stride(baked, STRIDE)

if PIN_FOOT:
    pin_feet(baked)
if PIN_FOOT or IK_LEGS or STRIDE != 1.0 or VSMOOTH:
    repole_legs(baked)
    # the mirror is built from the pinned result
    poses = {}
    for f in range(F0, F1 + 1):
        scene.frame_set(f)
        fr = {}
        for n in CONTROLS:
            pb = pbs[n]
            rec = {"loc": pb.location.copy(), "scale": pb.scale.copy(), "mode": pb.rotation_mode}
            rec["rot"] = pb.rotation_quaternion.copy() if pb.rotation_mode == 'QUATERNION' else Quaternion(pb.rotation_axis_angle[1:], pb.rotation_axis_angle[0]) if pb.rotation_mode == 'AXIS_ANGLE' else pb.rotation_euler.to_quaternion()
            for p_ in PROPS:
                if p_ in pb:
                    rec[p_] = pb[p_]
            fr[n] = rec
        poses[f] = fr

if HAND_GRIP:
    g_ = bpy.data.actions.get("Grip"); assert g_ is not None, "--hand-grip needs the Grip action"
    ad.action = g_; scene.frame_set(1); bpy.context.view_layer.update()
    grip_pose = {}
    for pb in pbs:
        n_ = pb.name
        if n_.startswith(("thumb.", "f_index", "f_middle", "f_ring", "f_pinky")) and any(n_.endswith("." + s_) or ("." + s_ + ".") in n_ for s_ in HAND_GRIP if s_ in "LR"):
            grip_pose[n_] = pb.matrix_basis.copy()
    ad.action = baked
    for f in range(F0, F1 + 1):
        scene.frame_set(f)
        for n_, m_ in grip_pose.items():
            pbs[n_].matrix_basis = m_
        for n_ in grip_pose:
            pb = pbs[n_]
            pb.keyframe_insert("location", frame=f, group=n_)
            pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=n_)
    log("hand-grip %s: %d finger controls set to the Grip fist on frames %d..%d" % (HAND_GRIP, len(grip_pose), F0, F1))

if ARM_POLE_FK:
    arm_pole_fk(baked)

if TORSO_YAW:
    torso_counter_yaw(baked, TORSO_YAW)

if SHAFT_HAND:
    shaft_hand(baked, SHAFT_HAND)

if HAND_WEIGHT:
    hand_weight(baked, HAND_WEIGHT)

if GRIP_FOLLOW:
    grip_follow(baked, GRIP_FOLLOW)

if FK_ARM:
    fk_arms(baked)

if LOOP_SEAM:
    loop_seam(baked, LOOP_SEAM)

if SPEED_SEGMENT:
    A_, B_, FX = SPEED_SEGMENT.split(":"); A_ = int(A_); B_ = int(B_); FX = float(FX)
    ad.action = baked
    new = {}; k = F0
    for f in range(F0, A_):
        scene.frame_set(f); new[k] = read_pose(); k += 1
    t = float(A_); ts = []
    while t < B_ - 0.5 * FX + 1e-6:
        ts.append(t); t += FX
    ts.append(float(B_))                                    # the segment ends exactly on B
    for t in ts:
        scene.frame_set(int(math.floor(t)), subframe=t - math.floor(t)); new[k] = read_pose(); k += 1
    for f in range(B_ + 1, F1 + 1):
        scene.frame_set(f); new[k] = read_pose(); k += 1
    n_old = F1 - F0 + 1; F1 = k - 1
    log("speed-segment %d..%d x%.2f: %d frames -> %d (the segment %d -> %d frames)" % (A_, B_, FX, n_old, F1 - F0 + 1, B_ - A_ + 1, len(ts)))
    poses = new
    baked = write_action(RESULT, poses, False)

if UPPER_FROM:
    upper_from(baked, UPPER_FROM, UPPER_SEAM)
    ad.action = baked

if MIRROR_TO:
    # the mirror is built from the FINISHED result (every pass above), re-read here
    ad.action = baked; poses = {}
    for f in range(F0, F1 + 1):
        scene.frame_set(f); poses[f] = read_pose()
    mir = write_action(MIRROR_TO, poses, True)
    # proof: hand and foot positions of the mirror are the X-mirror of the original's, per frame
    ad.action = baked; scene.frame_set(F0); orig = {}
    for f in range(F0, F1 + 1):
        scene.frame_set(f); orig[f] = {b: (rig.matrix_world @ pbs[b].matrix).translation.copy() for b in ("DEF-hand.L", "DEF-hand.R", "DEF-foot.L", "DEF-foot.R", "DEF-spine", "DEF-spine.006")}
    ad.action = mir; wm = (0.0, "", 0)
    for f in range(F0, F1 + 1):
        scene.frame_set(f)
        for b, p in orig[f].items():
            q = (rig.matrix_world @ pbs[other(b)].matrix).translation
            d = (Vector((-p.x, p.y, p.z)) - q).length * 1000
            if d > wm[0]: wm = (d, b, f)
    log("mirror %s vs %s X-flipped: worst landmark %.2f mm (%s f%d)" % (MIRROR_TO, RESULT, wm[0], wm[1], wm[2]))
    ad.action = baked

if STACK_KEEP is not None:
    for t, was_mute, strips in STACK_KEEP["tracks"]:
        t.mute = was_mute
        for st, old_name in strips:
            if old_name in (SOURCE, RESULT, RESULT + "_base") or old_name is None or bpy.data.actions.get(old_name) is None:
                st.action = bpy.data.actions[RESULT]
    act_ = bpy.data.actions.get(STACK_KEEP["active"]) if STACK_KEEP["active"] else None
    if act_ is not None and act_.name != RESULT:
        ad.action = act_; ad.action_blend_type = STACK_KEEP["blend"]; ad.action_influence = STACK_KEEP["influence"]
        if hasattr(ad, "action_slot") and ad.action.slots:
            ad.action_slot = ad.action.slots[0]
    log("stack kept: active %s (%s), strips -> %s" % (ad.action.name if ad.action else None, ad.action_blend_type if ad.action else "-", [(st.name, st.action.name if st.action else None) for t in ad.nla_tracks for st in t.strips]))
scene.frame_set(F0)
if SAVE:
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
    log("saved", bpy.data.filepath)
else:
    log("dry run (no --save)")
