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
    STACK_KEEP = {"active": ad.action, "blend": ad.action_blend_type, "influence": ad.action_influence,
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


def pin_feet(act):
    """Hold each --pin-foot foot's IK control on the floor spot for the whole clip or a frame range (the legs
    are on IK on every frame since ik_always). Spec SIDE[:ref[:from[:to]]][:xy]: `ref` = the frame whose world
    transform is held (default the first), `xy` = hold only the horizontal position and keep each frame's own
    height and rotation (a planted rear foot that lifts its heel in a lunge). SIDE:auto[:xy] finds the foot's
    planted phases itself (frames whose ankle sits within 12 mm rig of the clip's lowest, 3+ frames long) and
    holds each at its middle frame (a stepping foot: before the step, the landing, the return). Reports the
    knee angle so a locked leg shows, and the DEF foot's distance from the target so an unreachable pin shows."""
    ad.action = act

    def hold(side, fr_, p0, p1, xy):
        scene.frame_set(fr_)
        foot_m = (rig.matrix_world @ pbs["foot_ik." + side].matrix).copy()
        toe_m = (rig.matrix_world @ pbs["toe_ik." + side].matrix).copy()
        worst_gap = 0.0; knee_min = 180.0; knee_max = 0.0
        for f in range(p0, p1 + 1):
            scene.frame_set(f)
            tgt = foot_m
            if xy:
                tgt = (rig.matrix_world @ pbs["foot_ik." + side].matrix).copy()
                tgt.translation = Vector((foot_m.translation.x, foot_m.translation.y, tgt.translation.z))
            pb = pbs["foot_ik." + side]; pb.matrix = rig.matrix_world.inverted() @ tgt
            pbs["thigh_parent." + side]["IK_FK"] = 0.0
            bpy.context.view_layer.update()
            if not xy:
                pt = pbs["toe_ik." + side]; pt.matrix = rig.matrix_world.inverted() @ toe_m
                bpy.context.view_layer.update()
            for n in ("foot_ik." + side, "toe_ik." + side):
                pbs[n].keyframe_insert("location", frame=f, group=n)
                pbs[n].keyframe_insert("rotation_quaternion" if pbs[n].rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=n)
            pbs["thigh_parent." + side].keyframe_insert('["IK_FK"]', frame=f, group="thigh_parent." + side)
            hip = (rig.matrix_world @ pbs["DEF-thigh." + side].matrix).translation; knee = (rig.matrix_world @ pbs["DEF-shin." + side].matrix).translation
            ank = (rig.matrix_world @ pbs["DEF-foot." + side].matrix).translation
            a_ = math.degrees((hip - knee).angle(ank - knee)); knee_min = min(knee_min, a_); knee_max = max(knee_max, a_)
            worst_gap = max(worst_gap, (ank - tgt.translation).length * 1000)
        log("pinned foot %s on frames %d..%d at frame %d's %s (%.3f, %.3f, %.3f): knee %.0f..%.0f deg, DEF foot within %.1f mm of the pin on every pinned frame" % (
            side, p0, p1, fr_, "horizontal position (height and rotation kept)" if xy else "world transform", foot_m.translation.x, foot_m.translation.y, foot_m.translation.z, knee_min, knee_max, worst_gap))

    for spec in PIN_FOOT.split(","):
        if not spec:
            continue
        parts = spec.split(":"); side = parts[0]
        xy = parts[-1] == "xy"
        if xy:
            parts = parts[:-1]
        if len(parts) > 1 and parts[1] == "auto":
            zs = {}
            for f in range(F0, F1 + 1):
                scene.frame_set(f); zs[f] = (rig.matrix_world @ pbs["DEF-foot." + side].matrix).translation.z
            zmin = min(zs.values()); planted = [f for f in range(F0, F1 + 1) if zs[f] <= zmin + 0.012]
            phases = []
            for f in planted:
                if phases and f == phases[-1][1] + 1:
                    phases[-1][1] = f
                else:
                    phases.append([f, f])
            phases = [ph for ph in phases if ph[1] - ph[0] + 1 >= 3]
            log("foot %s auto: lowest ankle %.3f, planted phases %s" % (side, zmin, ", ".join("%d..%d" % tuple(ph) for ph in phases)))
            for p0, p1 in phases:
                hold(side, (p0 + p1) // 2, p0, p1, xy)
            continue
        fr_ = int(parts[1]) if len(parts) > 1 and parts[1] else F0
        p0 = int(parts[2]) if len(parts) > 2 and parts[2] else F0
        p1 = min(F1, int(parts[3])) if len(parts) > 3 and parts[3] else F1
        hold(side, fr_, max(F0, p0), p1, xy)


def torso_counter_yaw(act, deg):
    ad.action = act
    def yaw_ctrl(b):
        v = (rig.matrix_world @ pbs[b].matrix).to_3x3() @ Vector((0, 0, 1)); return math.atan2(v.x, -v.y)
    def wrap(a): return (a + math.pi) % (2 * math.pi) - math.pi
    yaws = {}
    for f in range(F0, F1 + 1):
        scene.frame_set(f); yaws[f] = yaw_ctrl("DEF-spine.003")
    y0 = yaws[F0]; dev = {f: wrap(yaws[f] - y0) for f in yaws}
    fmax = max(dev, key=lambda f: abs(dev[f])); dmax = dev[fmax]
    if abs(dmax) < 1e-4:
        log("torso-yaw: the chest does not turn in this clip; nothing to counter"); return
    chain = ["spine_fk.001", "spine_fk.002", "chest"]
    left_ik = pbs["upper_arm_parent.L"]["IK_FK"] < 0.5 if True else False
    worst_res = 0.0; peak_after = None
    for f in range(F0, F1 + 1):
        scene.frame_set(f)
        share = dev[f] / dmax if (dev[f] * dmax) > 0 else 0.0
        target = -math.radians(deg) * share * (1 if dmax > 0 else -1)
        left_ik = pbs["upper_arm_parent.L"]["IK_FK"] < 0.5
        Mr0 = (rig.matrix_world @ pbs["DEF-weapon.R"].matrix).copy()
        Ml0 = (rig.matrix_world @ pbs["hand_ik.L"].matrix).copy(); Mp0 = (rig.matrix_world @ pbs["upper_arm_ik_target.L"].matrix).copy()
        def turn(b, ang):
            pb = pbs[b]; m = (rig.matrix_world @ pb.matrix).copy()
            r = Matrix.Rotation(ang, 4, 'Z'); m2 = r @ m; m2.translation = m.translation
            pb.matrix = rig.matrix_world.inverted() @ m2; bpy.context.view_layer.update()
        if abs(target) > 1e-6:
            for b in chain:
                turn(b, target / 3.0)
            res = wrap((yaws[f] + target) - yaw_ctrl("DEF-spine.003"))
            turn("chest", res)
            res2 = wrap((yaws[f] + target) - yaw_ctrl("DEF-spine.003")); worst_res = max(worst_res, abs(math.degrees(res2)))
            Mr1 = (rig.matrix_world @ pbs["DEF-weapon.R"].matrix).copy(); T = Mr1 @ Mr0.inverted()
            if left_ik:
                pbs["hand_ik.L"].matrix = rig.matrix_world.inverted() @ (T @ Ml0); bpy.context.view_layer.update()
                pbs["upper_arm_ik_target.L"].matrix = rig.matrix_world.inverted() @ (T @ Mp0); bpy.context.view_layer.update()
        if f == fmax:
            peak_after = math.degrees(wrap(yaw_ctrl("DEF-spine.003") - y0))
        for b in chain + (["hand_ik.L", "upper_arm_ik_target.L"] if left_ik else []):
            pb = pbs[b]
            pb.keyframe_insert("location", frame=f, group=b)
            pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=b)
    log("torso-yaw %.0f: chest excursion peaked at %+.0f deg on frame %d -> %+.0f deg after the counter-turn (start and end unchanged, residual <= %.2f deg); left hand %s" % (
        deg, math.degrees(dmax), fmax, peak_after if peak_after is not None else 0.0, worst_res, "carried with the right hand (IK)" if pbs["upper_arm_parent.L"]["IK_FK"] < 0.5 else "on FK, follows the chest"))


def arm_pole_fk(act):
    """On every frame where the arm is on IK, put its pole out through the FK chain's elbow (forearm_fk head),
    refined until the DEF elbow lies in that plane. The FK frames are untouched."""
    ad.action = act
    for side in ARM_POLE_FK:
        if side not in ("L", "R"):
            continue
        n_ik = 0; worst = 0.0
        for f in range(F0, F1 + 1):
            scene.frame_set(f)
            sw = pbs["upper_arm_parent." + side]
            if sw["IK_FK"] > 0.5:
                continue
            n_ik += 1
            sh = (rig.matrix_world @ pbs["DEF-upper_arm." + side].matrix).translation.copy()
            wrist = (rig.matrix_world @ pbs["DEF-hand." + side].matrix).translation.copy()
            elbow_fk = (rig.matrix_world @ pbs["forearm_fk." + side].matrix).translation.copy()
            ax = (wrist - sh).normalized(); d_ = elbow_fk - sh; perp = d_ - ax * d_.dot(ax)
            if perp.length < 0.005:
                continue
            sw["pole_vector"] = True
            pole = pbs["upper_arm_ik_target." + side]; pt = elbow_fk + perp.normalized() * 0.4
            for _ in range(3):
                pm = pole.matrix.copy(); pm.translation = rig.matrix_world.inverted() @ pt; pole.matrix = pm; bpy.context.view_layer.update()
                k_ = (rig.matrix_world @ pbs["DEF-forearm." + side].matrix).translation
                dk = k_ - sh; pk = dk - ax * dk.dot(ax)
                if pk.length < 1e-4:
                    break
                ang = pk.normalized().angle(perp.normalized())
                if pk.normalized().cross(perp.normalized()).dot(ax) < 0:
                    ang = -ang
                if abs(ang) < 1e-4:
                    break
                pt = sh + Matrix.Rotation(ang, 3, ax) @ (pt - sh)
            k_ = (rig.matrix_world @ pbs["DEF-forearm." + side].matrix).translation; dk = k_ - sh; pk = dk - ax * dk.dot(ax)
            worst = max(worst, math.degrees(pk.normalized().angle(perp.normalized())) if pk.length > 1e-4 else 0.0)
            pole.keyframe_insert("location", frame=f, group="upper_arm_ik_target." + side)
            pole.keyframe_insert("rotation_quaternion" if pole.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group="upper_arm_ik_target." + side)
            sw.keyframe_insert('["pole_vector"]', frame=f, group="upper_arm_parent." + side)
        log("arm %s pole on the FK elbow plane on %d IK frames (residual swivel <= %.2f deg)" % (side, n_ik, worst))


def fk_arms(act):
    """Convert an arm from IK to FK for the whole clip without changing the pose: per frame, read the DEF
    upper arm / forearm / hand world rotations, set the FK controls to reproduce them (rest relation
    FK control -> DEF bone, measured on the zero pose) and switch IK_FK to 1."""
    ad.action = act
    chain = [("upper_arm_fk", "DEF-upper_arm"), ("forearm_fk", "DEF-forearm"), ("hand_fk", "DEF-hand")]
    for side in FK_ARM:
        if side not in ("L", "R"):
            continue
        ad.action = None
        for pb in pbs: pb.matrix_basis.identity()
        bpy.context.view_layer.update()
        rel = {c: (rig.matrix_world @ pbs[d + "." + side].matrix).to_quaternion().inverted() @ (rig.matrix_world @ pbs[c + "." + side].matrix).to_quaternion() for c, d in chain}
        ad.action = act
        worst = 0.0
        for f in range(F0, F1 + 1):
            scene.frame_set(f)
            target = {c: (rig.matrix_world @ pbs[d + "." + side].matrix).copy() for c, d in chain}
            pbs["upper_arm_parent." + side]["IK_FK"] = 1.0
            bpy.context.view_layer.update()
            for c, d in chain:
                pb = pbs[c + "." + side]
                q = target[c].to_quaternion() @ rel[c]
                m = pb.matrix.copy(); r = (rig.matrix_world.to_3x3().inverted() @ q.to_matrix()).to_4x4(); r.translation = m.translation
                pb.matrix = r
                bpy.context.view_layer.update()
            for c, d in chain:
                pb = pbs[c + "." + side]
                pb.keyframe_insert("location", frame=f, group=c + "." + side)
                pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=c + "." + side)
            pbs["upper_arm_parent." + side].keyframe_insert('["IK_FK"]', frame=f, group="upper_arm_parent." + side)
            for c, d in chain:
                m = rig.matrix_world @ pbs[d + "." + side].matrix
                worst = max(worst, (m.translation - target[c].translation).length * 1000, math.degrees(m.to_quaternion().rotation_difference(target[c].to_quaternion()).angle))
        log("arm %s on FK for frames %d..%d: DEF upper arm / forearm / hand reproduced within %.2f (mm or deg) on every frame" % (side, F0, F1, worst))


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
if PIN_FOOT:
    pin_feet(baked)
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

if FK_ARM:
    fk_arms(baked)

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

if MIRROR_TO:
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
    act_ = STACK_KEEP["active"]
    if act_ is not None and act_.name != RESULT and bpy.data.actions.get(act_.name) is not None:
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
