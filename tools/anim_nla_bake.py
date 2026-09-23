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
SPEED_SEGMENT = arg("--speed-segment", "")
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
    # a clean stack for keying: no NLA, the new action active
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
    """Hold each --pin-foot foot's IK control at one world transform for the whole clip (the legs are on IK on
    every frame since ik_always). Reports the knee angle so a locked leg shows, and the DEF foot's distance
    from the target so an unreachable pin shows."""
    ad.action = act
    for spec in PIN_FOOT.split(","):
        if not spec:
            continue
        parts = spec.split(":"); side = parts[0]
        fr_ = int(parts[1]) if len(parts) > 1 and parts[1] else F0
        p0 = int(parts[2]) if len(parts) > 2 and parts[2] else F0
        p1 = int(parts[3]) if len(parts) > 3 and parts[3] else F1
        scene.frame_set(fr_)
        foot_m = (rig.matrix_world @ pbs["foot_ik." + side].matrix).copy()
        toe_m = (rig.matrix_world @ pbs["toe_ik." + side].matrix).copy()
        worst_gap = 0.0; knee_min = 180.0; knee_max = 0.0
        for f in range(p0, p1 + 1):
            scene.frame_set(f)
            pb = pbs["foot_ik." + side]; pb.matrix = rig.matrix_world.inverted() @ foot_m
            pbs["thigh_parent." + side]["IK_FK"] = 0.0
            bpy.context.view_layer.update()
            pt = pbs["toe_ik." + side]; pt.matrix = rig.matrix_world.inverted() @ toe_m
            bpy.context.view_layer.update()
            for n in ("foot_ik." + side, "toe_ik." + side):
                pbs[n].keyframe_insert("location", frame=f, group=n)
                pbs[n].keyframe_insert("rotation_quaternion" if pbs[n].rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=n)
            pbs["thigh_parent." + side].keyframe_insert('["IK_FK"]', frame=f, group="thigh_parent." + side)
            hip = (rig.matrix_world @ pbs["DEF-thigh." + side].matrix).translation; knee = (rig.matrix_world @ pbs["DEF-shin." + side].matrix).translation
            ank = (rig.matrix_world @ pbs["DEF-foot." + side].matrix).translation
            a_ = math.degrees((hip - knee).angle(ank - knee)); knee_min = min(knee_min, a_); knee_max = max(knee_max, a_)
            worst_gap = max(worst_gap, (ank - foot_m.translation).length * 1000)
        log("pinned foot %s on frames %d..%d at frame %d's world transform (%.3f, %.3f, %.3f): knee %.0f..%.0f deg, DEF foot within %.1f mm of the pin on every pinned frame" % (
            side, p0, p1, fr_, foot_m.translation.x, foot_m.translation.y, foot_m.translation.z, knee_min, knee_max, worst_gap))


def fk_arms(act):
    """Convert an arm from IK to FK for the whole clip without changing the pose: per frame, read the DEF
    upper arm / forearm / hand world rotations, set the FK controls to reproduce them (rest relation
    FK control -> DEF bone, measured on the zero pose) and switch IK_FK to 1."""
    ad.action = act
    chain = [("upper_arm_fk", "DEF-upper_arm"), ("forearm_fk", "DEF-forearm"), ("hand_fk", "DEF-hand")]
    for side in FK_ARM:
        if side not in ("L", "R"):
            continue
        # rest relation, on the zero pose
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

scene.frame_set(F0)
if SAVE:
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
    log("saved", bpy.data.filepath)
else:
    log("dry run (no --save)")
