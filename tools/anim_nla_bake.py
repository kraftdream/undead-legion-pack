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
GRIP_EASE = int(arg("--grip-ease", "6"))           # frames: with a --grip-follow range ("L:@D:60"), the relation eases in from the clip's own over this many frames from the range's first frame
GRIP_PULL = "--grip-pull" in argv                  # with --grip-follow: where the following hand cannot reach its place on the shaft, the OTHER hand is pulled in toward the following hand's shoulder by the shortfall (on IK, its elbow kept on the FK elbow plane), as the retarget's gate does; pair with --fk-arm on that side to land it back on FK
GRIP_FOLLOW = arg("--grip-follow", "")            # also "L:@0.056": an idealised relation - ON the other hand's hilt axis, that many rig m toward the blade, hilt axes parallel, the hand's own roll about the shaft (first frame) kept (user: "left hand always follows the handle, 10 cm above the right hand")            # "L:Idle_TwoHanded:1": that hand's socket takes, on every frame, the transform it has RELATIVE to the other hand's socket on the given action and frame (position along / off the shaft and roll about it), so a two-handed grip is identical across clips and rigid through a loop (user: "the left hand changes the grip between idle and attack; at the end it sits too close to the right; in the idle it drifts")
VSMOOTH = [int(v) for v in arg("--vsmooth", "").split(",") if v]   # frames: on each, every root-level control's world HEIGHT is replaced by the mean of its own height on the neighbouring frames (a one-frame dip of the whole body: Walk_Back frame 103, hips and both feet 6-8 mm down)
STRIDE = float(arg("--stride", "1"))             # locomotion: scale the travel along the clip's travel axis - the root's advance AND every root-level control's position along that axis about the root's first-frame spot - by this factor (0.7 = steps 30 % shorter; a planted foot stays planted, the knees bend more). Run before pins and the speed segment
LOOP_SEAM = int(arg("--loop-seam", "0"))         # frames: re-close a loop after edits - over the last N frames every control is crossfaded to its FIRST-frame pose (root-space locations shifted by the root's travel), so the last frame equals the first + travel exactly (a fix keyed near the ends had left the left foot 10 mm higher on the last frame than on the first)
LOOP = "--loop" in argv                           # the clip is a cycle: a pin's flight-phase correction wraps across the seam (last frame -> first)
UPPER_FROM = arg("--upper-from", "")              # "Idle_03:1": after the retime, every control ABOVE the legs (the torso's rotation - its location stays the clip's - spine, chest, neck, head, jaw, shoulders, arms, hands, fingers and the arm IK/FK switches) is taken frame by frame from that action starting at that frame (wrapping over its length), the clip keeping its root, hips, legs and feet (user, Walk_Back: "too much movement above the legs, use the above-torso animation from idle_3")
UPPER_SEAM = int(arg("--upper-seam", "8"))         # frames: the copied window's end crossfaded to its start so the loop closes
HAND_WEIGHT = arg("--hand-weight", "")            # "R:0.015:4:6": that IK hand bobs against the body's vertical sway as if the held item had weight - the hips' height over the clip, normalised to -1..1, delayed DELAY frames (wrapping over a loop), moves the hand AMP rig m the OTHER way and pitches it PITCH degrees about the socket's finger axis (the tip dips as the hand drops) (user, Idle_Wand: "right hand sway that mimics the wand's weight, in sync with the character swaying up and down")
END_BLEND = arg("--end-blend", "")               # "Idle:1:8": after the retime, the last N frames crossfade every control to that action's frame (locations, rotations, scales, the switches on the last frame), so a one-shot ends EXACTLY on the pose the demo crossfades to next; the IK legs keep their knee poles on the FK plane through it (user, Impaled_Rise: "lower the torso on the fully standing pose, use it to fix the floating feet at the end")
EVEN_ADVANCE = int(arg("--even-advance", "0"))      # K: a locomotion loop is RETIMED so the hips' advance per frame along the travel follows a circularly smoothed (K passes of [1,2,1], wrapping at the seam) version of its own profile; same frame count, same travel, the Root kept linear. Removes the speed dip that a loop-closing crossfade leaves at the seam (the hips advanced 55 mm per frame and then 17 at Run_Fwd_02's wrap; Walk_Back lurched 14 mm and stalled to 0 on its last frames), which plays as a hitch every cycle under root motion (user: "walk_back, run_fwd and run_fwd_02 have looping issues")
FOOT_CLEAR = arg("--foot-clear", "")              # Z rig m: no model's BOOT goes below Z on any frame - per frame and foot, the lowest vertex of all six characters' Boot_<side> meshes is measured and an IK foot (and its toe) is raised by the deficit, the lift running-maxed over +-1 frame and smoothed (wrapping with --loop), the knee pole kept on the FK plane. For a swinging foot that pitches toe-down while barely lifting (the strafes: the boot's toe dragged 14 mm through the floor, and a constant export lift fitted to that dip floated the whole stance 25 mm; user: "both strafe animations in unity have model float above ground")
TORSO_DROP = float(arg("--torso-drop", "0"))       # rig m: the torso control (the hips, and with it the spine, head and FK arms) lowered by this on every frame; IK feet stay planted so the knees bend more, the poles re-aimed on the FK plane (user, Summon: "bring the torso down like 8 cm" = 0.044 rig m)
YAW_CLIP = float(arg("--yaw-clip", "0"))          # degrees, + = left: the whole clip turned about the vertical through the root's first-frame spot - every root-level control (torso, feet, toes, knee poles, IK hands, elbow poles) and the root's path, the Root's own orientation left at identity so the export's Root stays as in every other clip (user, AOE_Cast: "animation direction the same as the feet direction in idle_02": the take faced 17 deg right)
KNEES_IN = float(arg("--knees-in", "0"))         # rig m: the IK knees swivelled toward the body's midline so their separation shrinks by this much (each knee's pole aimed at the FK knee moved half of it inward along the hips' lateral axis; the knee can only move on its swivel circle, so the pole takes the nearest point). Runs after every other leg pass. (user, Strafe_01: "knees not that far apart, like 20 cm closer": the knees sat 276-414 mm apart with the feet 132-299)
KEEP_POLES = "--keep-poles" in argv               # with --pin-foot: the knee poles are left as they are (no re-aim onto the FK knee plane, no repole after the leg passes) - for a clip whose poles were set by hand or by --knees-in (user, Strafe_01: the fix keys the poles)
ARMS_DOWN = float(arg("--arms-down", "0"))         # degrees: each FK upper arm turned toward the body about the body's forward axis through its shoulder (pure adduction; the forearm and hand ride), on every frame (user, Strafe_01: "lower the arms, they stick out too much")
LOOP_SHIFT = int(arg("--loop-shift", "0"))          # frames: the loop's phase rotated - the clip starts K frames later and the first K frames go to the end, advanced by the travel (the Root keeps its linear path); the seam moves to where the old frame K meets K+1 (user, Strafe_01: "move some frames from the start into the end, the feet snap at the end")
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


LEG_POLE_PREV = {}
def leg_pole(side, knee_target, hip_, ankle_):
    """Aim the leg's IK pole so the DEF knee lands on knee_target's side of the hip->ankle axis (three refinements)."""
    sw = pbs["thigh_parent." + side]; pole = pbs["thigh_ik_target." + side]
    ax = ankle_ - hip_
    if ax.length < 1e-6:
        return
    ax.normalize(); d_ = knee_target - hip_; perp = d_ - ax * d_.dot(ax)
    prev_ = LEG_POLE_PREV.get(side)                            # memory: a near-straight leg or a side flip keeps last frame's plane
    if perp.length < 0.015 or (prev_ is not None and perp.normalized().dot(prev_) < 0.0):
        if prev_ is None:
            return
        perp = prev_ * 0.05
    LEG_POLE_PREV[side] = perp.normalized()
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


def end_blend(act, spec):
    tgt_name, tgt_frame, n = spec.split(":"); tgt_frame = int(tgt_frame); n = int(n)
    ad.action = bpy.data.actions[tgt_name]; scene.frame_set(tgt_frame); bpy.context.view_layer.update(); tgt = read_pose()
    ad.action = act
    legs_ik = [sd for sd in ("L", "R") if pbs["thigh_parent." + sd]["IK_FK"] < 0.5]
    for i, f in enumerate(range(F1 - n + 1, F1 + 1)):
        w = (i + 1) / float(n); w = w * w * (3 - 2 * w)
        scene.frame_set(f); cur = read_pose()
        for c in CONTROLS:
            pb = pbs[c]; a = cur[c]; b = tgt[c]
            if c.startswith("thigh_ik_target") or c.startswith("thigh_parent"):
                continue                                        # the legs' IK stays as it is; the pole is re-aimed below
            qa = a["rot"]; qb = b["rot"]
            if qa.dot(qb) < 0: qb = -qb
            q = qa.slerp(qb, w)
            if pb.rotation_mode == 'QUATERNION': pb.rotation_quaternion = q
            elif pb.rotation_mode == 'AXIS_ANGLE':
                ax_, an_ = q.to_axis_angle(); pb.rotation_axis_angle = (an_, ax_.x, ax_.y, ax_.z)
            else: pb.rotation_euler = q.to_euler(pb.rotation_mode)
            pb.location = a["loc"].lerp(b["loc"], w); pb.scale = a["scale"].lerp(b["scale"], w)
            if w >= 1.0 - 1e-6:
                for p_ in PROPS:
                    if p_ in b and p_ in pb and not c.startswith("thigh_parent"):
                        pb[p_] = bool(b[p_]) if isinstance(pb[p_], bool) else float(b[p_])
        bpy.context.view_layer.update()
        for sd in legs_ik:
            pbs["thigh_parent." + sd]["IK_FK"] = 0.0
            hip_ = (rig.matrix_world @ pbs["DEF-thigh." + sd].matrix).translation.copy(); ank_ = (rig.matrix_world @ pbs["DEF-foot." + sd].matrix).translation.copy()
            leg_pole(sd, fk_knee(sd), hip_, ank_)
        for c in CONTROLS:
            pb = pbs[c]
            pb.keyframe_insert("location", frame=f, group=c)
            pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_axis_angle" if pb.rotation_mode == 'AXIS_ANGLE' else "rotation_euler", frame=f, group=c)
            pb.keyframe_insert("scale", frame=f, group=c)
            for p_ in PROPS:
                if p_ in pb:
                    pb.keyframe_insert('["%s"]' % p_, frame=f, group=c)
    scene.frame_set(F1); hz = (rig.matrix_world @ pbs["DEF-spine"].matrix).translation.z
    ad.action = bpy.data.actions[tgt_name]; scene.frame_set(tgt_frame); hz_t = (rig.matrix_world @ pbs["DEF-spine"].matrix).translation.z; ad.action = act
    log("end-blend: the last %d frames crossfaded to %s frame %d; last-frame hips %.3f vs the target's %.3f" % (n, tgt_name, tgt_frame, hz, hz_t))


HAND_FROM_SOCK = {}


def _hand_from_sock():
    prev = ad.action; ad.action = None
    for pb in pbs: pb.matrix_basis.identity()
    bpy.context.view_layer.update()
    for s_ in ("L", "R"):
        HAND_FROM_SOCK[s_] = (rig.matrix_world @ pbs["DEF-weapon." + s_].matrix).inverted() @ (rig.matrix_world @ pbs["hand_ik." + s_].matrix)
    ad.action = prev; bpy.context.view_layer.update()


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


def grip_follow(act, spec):
    if not HAND_FROM_SOCK:
        _hand_from_sock()
    parts = spec.split(":"); side = parts[0]; other_ = "R" if side == "L" else "L"
    if parts[1].startswith("@"):
        # idealised: on the axis at D, parallel, with the first frame's roll about the shaft
        D = float(parts[1][1:])
        FROM_ = int(parts[2]) if len(parts) > 2 and parts[2] else F0     # "L:@D:60": the relation held from that frame on (eased in over GRIP_EASE frames, the arm FK before)
        TO_ = int(parts[3]) if len(parts) > 3 and parts[3] else F1
        ad.action = act; scene.frame_set(F0); bpy.context.view_layer.update()
        so = (rig.matrix_world @ pbs["DEF-weapon." + other_].matrix).copy(); ss = (rig.matrix_world @ pbs["DEF-weapon." + side].matrix).copy()
        cur = so.inverted() @ ss
        q = cur.to_quaternion(); sw_, tw_ = q.to_swing_twist('Y')            # twist about the shaft = the hand's roll
        # the weapon hangs from the hand SLOT, not the socket: the slot is the user's tuned offset from the socket
        # bone (Animations/unity_grips.json, Unity metres, X flipped into the Blender socket frame), so the shaft
        # runs through the slot's origin along the socket's +Y. The relation is built slot-to-slot (2026-09-24:
        # socket-to-socket left the fist 3.5 cm beside the handle)
        import json as _json, os as _os
        _g = _json.load(open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "Animations", "unity_grips.json"), encoding="utf-8"))
        def _slot(sd):
            px, py, pz = _g["slots"][sd]["pos"]; return Matrix.Translation(Vector((-px, py, pz)) / 1.8)
        REL = _slot(other_) @ Matrix.Translation((0.0, D, 0.0)) @ Matrix.Rotation(tw_, 4, 'Y') @ _slot(side).inverted()
        log("grip-follow %s: idealised relation - the %s SLOT on the %s hand's shaft (through its slot, along the socket's +Y) %+.3f rig m toward the blade, parallel, roll %.0f deg kept from frame %d" % (side, side, other_, D, math.degrees(tw_), F0))
    else:
        ref_name, ref_frame = parts[1], int(parts[2])
        FROM_ = int(parts[3]) if len(parts) > 3 and parts[3] else F0
        TO_ = int(parts[4]) if len(parts) > 4 and parts[4] else F1
        ref_act = bpy.data.actions[ref_name]
        ad.action = ref_act; scene.frame_set(ref_frame); bpy.context.view_layer.update()
        so = (rig.matrix_world @ pbs["DEF-weapon." + other_].matrix).copy(); ss = (rig.matrix_world @ pbs["DEF-weapon." + side].matrix).copy()
        REL = so.inverted() @ ss                                               # side socket in the other socket's frame
        d_ = REL.translation; al_ref = d_.y; off_ref = math.sqrt(d_.x * d_.x + d_.z * d_.z)
        log("grip-follow %s: reference %s frame %d - the %s socket sits %+.3f rig m along the %s hand's hilt axis, %.1f mm off it" % (side, ref_name, ref_frame, side, al_ref, other_, off_ref * 1000))
    ad.action = act
    before = []; worst = 0.0; worst_ang = 0.0
    for f in range(F0, F1 + 1):
        scene.frame_set(f)
        so = (rig.matrix_world @ pbs["DEF-weapon." + other_].matrix).copy(); ss = (rig.matrix_world @ pbs["DEF-weapon." + side].matrix).copy()
        cur = so.inverted() @ ss
        if f < FROM_ or f > TO_:
            continue
        before.append(((cur.translation - REL.translation).length * 1000, math.degrees(cur.to_quaternion().rotation_difference(REL.to_quaternion()).angle)))
        w_ = 1.0 if FROM_ == F0 else min(1.0, (f - FROM_ + 1) / float(GRIP_EASE + 1)); w_ = w_ * w_ * (3 - 2 * w_)
        qc_ = cur.to_quaternion(); qr_ = REL.to_quaternion()
        if qc_.dot(qr_) < 0: qr_ = -qr_
        RELf = qc_.slerp(qr_, w_).to_matrix().to_4x4(); RELf.translation = cur.translation.lerp(REL.translation, w_)
        if pbs["upper_arm_parent." + side]["IK_FK"] > 0.5:
            # the arm was FK on this frame: its IK elbow pole on the FK elbow's plane before the hand goes on IK
            sh_ = (rig.matrix_world @ pbs["DEF-upper_arm." + side].matrix).translation.copy(); wr_ = (rig.matrix_world @ pbs["DEF-hand." + side].matrix).translation.copy()
            el_ = (rig.matrix_world @ pbs["forearm_fk." + side].matrix).translation.copy()
            ax_ = (wr_ - sh_).normalized(); d_ = el_ - sh_; perp_ = d_ - ax_ * d_.dot(ax_)
            hm0 = (rig.matrix_world @ pbs["hand_ik." + side].matrix).copy()
            pbs["hand_ik." + side].matrix = rig.matrix_world.inverted() @ (ss @ HAND_FROM_SOCK[side]); pbs["upper_arm_parent." + side]["IK_FK"] = 0.0; bpy.context.view_layer.update()
            if perp_.length > 0.005:
                pbs["upper_arm_parent." + side]["pole_vector"] = True
                pl_ = pbs["upper_arm_ik_target." + side]; pm_ = pl_.matrix.copy(); pm_.translation = rig.matrix_world.inverted() @ (el_ + perp_.normalized() * 0.4); pl_.matrix = pm_
                bpy.context.view_layer.update()
        target = so @ RELf
        T = target @ ss.inverted()
        h = pbs["hand_ik." + side]; hm = (rig.matrix_world @ h.matrix).copy()
        h.matrix = rig.matrix_world.inverted() @ (T @ hm); pbs["upper_arm_parent." + side]["IK_FK"] = 0.0
        bpy.context.view_layer.update()
        if GRIP_PULL:
            # out of reach? pull the other hand in along the line from the wanted spot to this shoulder
            arm_len = (rig.data.bones["DEF-forearm." + side].head_local - rig.data.bones["DEF-upper_arm." + side].head_local).length + (rig.data.bones["DEF-hand." + side].head_local - rig.data.bones["DEF-forearm." + side].head_local).length
            for _it in range(3):
                so = (rig.matrix_world @ pbs["DEF-weapon." + other_].matrix).copy(); ss = (rig.matrix_world @ pbs["DEF-weapon." + side].matrix).copy()
                want = (so @ RELf).translation; gap_v = want - ss.translation
                sh_s = (rig.matrix_world @ pbs["DEF-upper_arm." + side].matrix).translation.copy()
                wr_want = want + (rig.matrix_world @ pbs["DEF-hand." + side].matrix).translation - ss.translation   # the wrist that goes with the wanted socket
                over = (wr_want - sh_s).length - GRIP_REACH * arm_len
                if gap_v.length < 0.003 and over <= 0.0:
                    break
                pull = (sh_s - want).normalized() * max(gap_v.length, over)
                sw_o = pbs["upper_arm_parent." + other_]
                if sw_o["IK_FK"] > 0.5:
                    # the other arm on IK, elbow on its FK plane, hand where it is now
                    sh_o = (rig.matrix_world @ pbs["DEF-upper_arm." + other_].matrix).translation.copy()
                    wr_o = (rig.matrix_world @ pbs["DEF-hand." + other_].matrix).translation.copy()
                    el_fk = (rig.matrix_world @ pbs["forearm_fk." + other_].matrix).translation.copy()
                    ho = pbs["hand_ik." + other_]; ho.matrix = rig.matrix_world.inverted() @ (so @ HAND_FROM_SOCK[other_])
                    sw_o["IK_FK"] = 0.0; bpy.context.view_layer.update()
                    ax = (wr_o - sh_o).normalized(); d_ = el_fk - sh_o; perp = d_ - ax * d_.dot(ax)
                    if perp.length > 0.005:
                        sw_o["pole_vector"] = True
                        pole = pbs["upper_arm_ik_target." + other_]; pm = pole.matrix.copy(); pm.translation = rig.matrix_world.inverted() @ (el_fk + perp.normalized() * 0.4); pole.matrix = pm
                        bpy.context.view_layer.update()
                ho = pbs["hand_ik." + other_]; hom = (rig.matrix_world @ ho.matrix).copy()
                ho.matrix = rig.matrix_world.inverted() @ (Matrix.Translation(pull) @ hom); bpy.context.view_layer.update()
                so = (rig.matrix_world @ pbs["DEF-weapon." + other_].matrix).copy(); ss = (rig.matrix_world @ pbs["DEF-weapon." + side].matrix).copy()
                T = (so @ RELf) @ ss.inverted(); hm = (rig.matrix_world @ h.matrix).copy()
                h.matrix = rig.matrix_world.inverted() @ (T @ hm); bpy.context.view_layer.update()
            for b in ("hand_ik." + other_, "upper_arm_ik_target." + other_):
                pbs[b].keyframe_insert("location", frame=f, group=b)
                pbs[b].keyframe_insert("rotation_quaternion" if pbs[b].rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=b)
            pbs["upper_arm_parent." + other_].keyframe_insert('["IK_FK"]', frame=f, group="upper_arm_parent." + other_)
            pbs["upper_arm_parent." + other_].keyframe_insert('["pole_vector"]', frame=f, group="upper_arm_parent." + other_)
        for b in ("upper_arm_ik_target." + side,):
            pbs[b].keyframe_insert("location", frame=f, group=b)
            pbs[b].keyframe_insert("rotation_quaternion" if pbs[b].rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=b)
        pbs["upper_arm_parent." + side].keyframe_insert('["pole_vector"]', frame=f, group="upper_arm_parent." + side)
        h.keyframe_insert("location", frame=f, group="hand_ik." + side)
        h.keyframe_insert("rotation_quaternion" if h.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group="hand_ik." + side)
        pbs["upper_arm_parent." + side].keyframe_insert('["IK_FK"]', frame=f, group="upper_arm_parent." + side)
        so = (rig.matrix_world @ pbs["DEF-weapon." + other_].matrix).copy(); ss = (rig.matrix_world @ pbs["DEF-weapon." + side].matrix).copy()
        now = so.inverted() @ ss
        worst = max(worst, (now.translation - RELf.translation).length * 1000); worst_ang = max(worst_ang, math.degrees(now.to_quaternion().rotation_difference(RELf.to_quaternion()).angle))
    log("grip-follow %s on %s: before, the relation wandered up to %.1f mm / %.1f deg from the reference; after, within %.1f mm / %.1f deg on every frame" % (
        side, act.name, max(b[0] for b in before), max(b[1] for b in before), worst, worst_ang))


def shaft_hand(act, spec):
    """Put SIDE's weapon socket on the other hand's hilt axis (socket +Y) every frame, moved `off` rig m along
    it, with the socket's own Y turned parallel to the shaft and its roll about the shaft kept; the hand's IK
    control moves with the socket (rigid), so the arm follows on IK."""
    ad.action = act
    parts = spec.split(":"); side = parts[0]; off = float(parts[1]); other_ = "R" if side == "L" else "L"
    FROM_ = int(parts[2]) if len(parts) > 2 and parts[2] else F0       # "L:0:100:125": only over that range, eased in and out over GRIP_EASE frames (the arm FK outside it)
    TO_ = int(parts[3]) if len(parts) > 3 and parts[3] else F1
    n = 0; d_min = 9; d_max = -9; worst_off = 0.0; worst_ang = 0.0
    for f in range(F0, F1 + 1):
        if f < FROM_ or f > TO_:
            continue
        scene.frame_set(f)
        w_ = 1.0
        if FROM_ > F0: w_ = min(w_, (f - FROM_ + 1) / float(GRIP_EASE + 1))
        if TO_ < F1: w_ = min(w_, (TO_ - f + 1) / float(GRIP_EASE + 1))
        w_ = w_ * w_ * (3 - 2 * w_)
        sock_o = (rig.matrix_world @ pbs["DEF-weapon." + other_].matrix).copy()
        sock_s = (rig.matrix_world @ pbs["DEF-weapon." + side].matrix).copy()
        if pbs["upper_arm_parent." + side]["IK_FK"] > 0.5:
            # the arm was FK: put it on IK where it is, the elbow pole on the FK elbow's plane
            sh_ = (rig.matrix_world @ pbs["DEF-upper_arm." + side].matrix).translation.copy(); wr_ = (rig.matrix_world @ pbs["DEF-hand." + side].matrix).translation.copy()
            el_ = (rig.matrix_world @ pbs["forearm_fk." + side].matrix).translation.copy()
            ax_ = (wr_ - sh_).normalized(); dv_ = el_ - sh_; perp_ = dv_ - ax_ * dv_.dot(ax_)
            if not HAND_FROM_SOCK: _hand_from_sock()
            pbs["hand_ik." + side].matrix = rig.matrix_world.inverted() @ (sock_s @ HAND_FROM_SOCK[side]); pbs["upper_arm_parent." + side]["IK_FK"] = 0.0; bpy.context.view_layer.update()
            if perp_.length > 0.005:
                pbs["upper_arm_parent." + side]["pole_vector"] = True
                pl_ = pbs["upper_arm_ik_target." + side]; pm_ = pl_.matrix.copy(); pm_.translation = rig.matrix_world.inverted() @ (el_ + perp_.normalized() * 0.4); pl_.matrix = pm_
                bpy.context.view_layer.update()
            sock_s = (rig.matrix_world @ pbs["DEF-weapon." + side].matrix).copy()
        y_ = (sock_o.to_3x3() @ Vector((0, 1, 0))).normalized()
        along = (sock_s.translation - sock_o.translation).dot(y_)              # + = toward the blade
        along_new = along + off
        pos_new = sock_o.translation + y_ * along_new
        ys = (sock_s.to_3x3() @ Vector((0, 1, 0))).normalized()
        q_align = ys.rotation_difference(y_)                                    # least rotation: the socket's hilt axis onto the shaft
        m_new = q_align.to_matrix().to_4x4() @ Matrix.Translation(-sock_s.translation) @ sock_s
        m_new = Matrix.Translation(pos_new) @ m_new
        if w_ < 1.0:                                                            # the ease: blend the wanted socket with the clip's own
            qa_ = sock_s.to_quaternion(); qb_ = m_new.to_quaternion()
            if qa_.dot(qb_) < 0: qb_ = -qb_
            m_new = qa_.slerp(qb_, w_).to_matrix().to_4x4(); m_new.translation = sock_s.translation.lerp(pos_new, w_)
        T = m_new @ sock_s.inverted()
        h = pbs["hand_ik." + side]; hm = (rig.matrix_world @ h.matrix).copy()
        h.matrix = rig.matrix_world.inverted() @ (T @ hm); pbs["upper_arm_parent." + side]["IK_FK"] = 0.0
        bpy.context.view_layer.update()
        for b in ("upper_arm_ik_target." + side,):
            pbs[b].keyframe_insert("location", frame=f, group=b)
            pbs[b].keyframe_insert("rotation_quaternion" if pbs[b].rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=b)
        pbs["upper_arm_parent." + side].keyframe_insert('["pole_vector"]', frame=f, group="upper_arm_parent." + side)
        h.keyframe_insert("location", frame=f, group="hand_ik." + side)
        h.keyframe_insert("rotation_quaternion" if h.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group="hand_ik." + side)
        pbs["upper_arm_parent." + side].keyframe_insert('["IK_FK"]', frame=f, group="upper_arm_parent." + side)
        # verify on the DEF result
        sock_o = (rig.matrix_world @ pbs["DEF-weapon." + other_].matrix).copy(); sock_s = (rig.matrix_world @ pbs["DEF-weapon." + side].matrix).copy()
        y_ = (sock_o.to_3x3() @ Vector((0, 1, 0))).normalized(); d = sock_s.translation - sock_o.translation
        al = d.dot(y_); off_axis = (d - y_ * al).length * 1000
        ang = math.degrees((sock_s.to_3x3() @ Vector((0, 1, 0))).normalized().angle(y_))
        worst_off = max(worst_off, off_axis); worst_ang = max(worst_ang, ang); d_min = min(d_min, al); d_max = max(d_max, al); n += 1
    log("shaft-hand %s %+.3f rig m: on %d frames the %s socket sits %.3f..%.3f rig m along the %s hand's hilt axis (- = below the hand), %.1f mm off the shaft at worst, hilt axes within %.1f deg" % (
        side, off, n, side, d_min, d_max, other_, worst_off, worst_ang))


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




def even_advance(K):
    """Retime the loop so the hips advance smoothly across the wrap (see EVEN_ADVANCE)."""
    global poses, baked, F1
    from bisect import bisect_right
    ad.action = baked
    n = F1 - F0 + 1
    hips = []; roots = []
    for f in range(F0, F1 + 1):
        scene.frame_set(f); hips.append((rig.matrix_world @ pbs["DEF-spine"].matrix).translation.copy()); roots.append((rig.matrix_world @ pbs["root"].matrix).translation.copy())
    travel = roots[-1] - roots[0]
    if travel.length < 1e-4:
        log("even-advance: the root does not travel in this clip; nothing to do"); return
    axis = travel.normalized()
    a = [max((hips[i + 1] - hips[i]).dot(axis), 1e-4) for i in range(n - 1)]      # per-frame advance, kept monotone
    total = sum(a); sm = a[:]
    for _ in range(K):
        sm = [(sm[(i - 1) % (n - 1)] + 2 * sm[i] + sm[(i + 1) % (n - 1)]) / 4.0 for i in range(n - 1)]   # circular: the seam is a neighbour
    k_ = total / sum(sm); sm = [v * k_ for v in sm]
    A = [0.0]
    for v in a: A.append(A[-1] + v)
    S = [0.0]
    for v in sm: S.append(S[-1] + v)
    ts = []
    for j in range(n):
        i = min(max(bisect_right(A, S[j]) - 1, 0), n - 2)
        frac = (S[j] - A[i]) / max(A[i + 1] - A[i], 1e-9)
        ts.append(F0 + i + min(max(frac, 0.0), 1.0))
    ts[0] = float(F0); ts[-1] = float(F1)
    new = {}
    for j, t in enumerate(ts):
        scene.frame_set(int(math.floor(t)), subframe=t - math.floor(t)); new[F0 + j] = read_pose()
    poses = new; baked = write_action(RESULT, poses, False); ad.action = baked
    # the Root stays linear (Unreal extracts root motion from it); its children keep their world placement
    rootspace = ["torso", "foot_ik.L", "foot_ik.R", "thigh_ik_target.L", "thigh_ik_target.R", "hand_ik.L", "hand_ik.R", "upper_arm_ik_target.L", "upper_arm_ik_target.R"]
    scene.frame_set(F0); rq = (rig.matrix_world @ pbs["root"].matrix).to_quaternion()
    if math.degrees(rq.angle) < 1.0:
        for j in range(n):
            f = F0 + j; scene.frame_set(f)
            world = {c: (rig.matrix_world @ pbs[c].matrix).copy() for c in rootspace}
            pb = pbs["root"]; m = (rig.matrix_world @ pb.matrix).copy(); m.translation = roots[0] + travel * (j / float(n - 1))
            pb.matrix = rig.matrix_world.inverted() @ m; bpy.context.view_layer.update()
            pb.keyframe_insert("location", frame=f, group="root")
            for c in rootspace:
                pbs[c].matrix = rig.matrix_world.inverted() @ world[c]; bpy.context.view_layer.update()
                pbs[c].keyframe_insert("location", frame=f, group=c)
    else:
        log("even-advance: the root is rotated (%.0f deg); left as resampled" % math.degrees(rq.angle))
    after = []
    for f in range(F0, F1 + 1):
        scene.frame_set(f); after.append((rig.matrix_world @ pbs["DEF-spine"].matrix).translation.dot(axis))
    adv2 = [after[i + 1] - after[i] for i in range(n - 1)]
    warp = max(abs(ts[j] - (F0 + j)) for j in range(n))
    log("even-advance x%d: hips advance per frame %.1f..%.1f mm -> %.1f..%.1f (mean %.1f), at the wrap %.1f -> %.1f mm; frames moved by up to %.2f in time; travel %.3f rig m unchanged" % (
        K, min(a) * 1000, max(a) * 1000, min(adv2) * 1000, max(adv2) * 1000, sum(adv2) / len(adv2) * 1000, a[-1] * 1000, adv2[-1] * 1000, warp, travel.length))
    log("even-advance profile before: " + " ".join("%.0f" % (v * 1000) for v in a))
    log("even-advance profile after:  " + " ".join("%.0f" % (v * 1000) for v in adv2))


def foot_clear(act, zmin):
    ad.action = act
    vl = bpy.context.view_layer; saved = {}
    def walk(lc):
        if lc.name.startswith("Ref_Skeleton"):
            saved[lc.name] = lc.exclude; lc.exclude = False
        for c in lc.children: walk(c)
    walk(vl.layer_collection)
    boots = {sd: [o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith("_Boot_" + sd)] for sd in ("L", "R")}
    n = F1 - F0 + 1; need = {"L": [], "R": []}; lowest = {"L": (9.0, F0), "R": (9.0, F0)}
    for f in range(F0, F1 + 1):
        scene.frame_set(f); vl.update(); dg = bpy.context.evaluated_depsgraph_get()
        for sd in ("L", "R"):
            lo = 9.0
            for o in boots[sd]:
                ev = o.evaluated_get(dg); mw = ev.matrix_world
                lo = min(lo, min((mw @ v.co).z for v in ev.data.vertices))
            need[sd].append(max(0.0, zmin - lo))
            if lo < lowest[sd][0]: lowest[sd] = (lo, f)
    for sd in ("L", "R"):
        raw = need[sd]
        d = [max(raw[max(i - 1, 0)], raw[i], raw[min(i + 1, n - 1)]) for i in range(n)]
        for _ in range(2):
            d = [(d[(i - 1) % n] + 2 * d[i] + d[(i + 1) % n]) / 4.0 if LOOP else (d[max(i - 1, 0)] + 2 * d[i] + d[min(i + 1, n - 1)]) / 4.0 for i in range(n)]
        d = [max(a_, b_) for a_, b_ in zip(d, raw)]        # smoothing must not drop below the raw need
        if max(d) < 1e-4:
            log("foot-clear %s: the boots never go below %.3f (lowest %.1f mm at frame %d); nothing to lift" % (sd, zmin, lowest[sd][0] * 1000, lowest[sd][1])); continue
        lifted = 0
        for i, f in enumerate(range(F0, F1 + 1)):
            if d[i] < 1e-5: continue
            scene.frame_set(f)
            if pbs["thigh_parent." + sd]["IK_FK"] > 0.5:
                log("foot-clear %s: frame %d needs %.0f mm but the leg is on FK (run --ik-legs first)" % (sd, f, d[i] * 1000)); continue
            foot = pbs["foot_ik." + sd]; toe = pbs["toe_ik." + sd]
            fm = (rig.matrix_world @ foot.matrix).copy(); tm = (rig.matrix_world @ toe.matrix).copy()
            fm.translation.z += d[i]; tm.translation.z += d[i]
            foot.matrix = rig.matrix_world.inverted() @ fm; bpy.context.view_layer.update()
            toe.matrix = rig.matrix_world.inverted() @ tm; bpy.context.view_layer.update()
            hip_ = (rig.matrix_world @ pbs["DEF-thigh." + sd].matrix).translation.copy()
            leg_pole(sd, fk_knee(sd), hip_, fm.translation)
            for b in ("foot_ik." + sd, "toe_ik." + sd, "thigh_ik_target." + sd):
                pbs[b].keyframe_insert("location", frame=f, group=b)
                pbs[b].keyframe_insert("rotation_quaternion" if pbs[b].rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=b)
            pbs["thigh_parent." + sd].keyframe_insert('["pole_vector"]', frame=f, group="thigh_parent." + sd)
            lifted += 1
        log("foot-clear %s: raised on %d frames by up to %.0f mm (the boots' lowest point was %.0f mm at frame %d, floor %.3f)" % (sd, lifted, max(d) * 1000, lowest[sd][0] * 1000, lowest[sd][1], zmin))
    def restore(lc):
        if lc.name in saved: lc.exclude = saved[lc.name]
        for c in lc.children: restore(c)
    restore(vl.layer_collection)


def torso_drop(act, d):
    ad.action = act
    for f in range(F0, F1 + 1):
        scene.frame_set(f)
        pb = pbs["torso"]; m = (rig.matrix_world @ pb.matrix).copy(); m.translation.z -= d
        pb.matrix = rig.matrix_world.inverted() @ m; bpy.context.view_layer.update()
        pb.keyframe_insert("location", frame=f, group="torso")
    scene.frame_set(F0); hz = (rig.matrix_world @ pbs["DEF-spine"].matrix).translation.z
    log("torso lowered by %.3f rig m (%.0f mm engine) on every frame: hips at %.3f on frame %d" % (d, d * 1800, hz, F0))


def yaw_clip(act, deg):
    ad.action = act
    scene.frame_set(F0); pivot = (rig.matrix_world @ pbs["root"].matrix).translation.copy()
    R = Matrix.Rotation(math.radians(deg), 4, 'Z')
    ctrls = ["torso", "foot_ik.L", "foot_ik.R", "toe_ik.L", "toe_ik.R", "thigh_ik_target.L", "thigh_ik_target.R", "hand_ik.L", "hand_ik.R", "upper_arm_ik_target.L", "upper_arm_ik_target.R"]
    for f in range(F0, F1 + 1):
        scene.frame_set(f)
        world = {c: (rig.matrix_world @ pbs[c].matrix).copy() for c in ctrls}
        pb = pbs["root"]; m = (rig.matrix_world @ pb.matrix).copy(); m.translation = pivot + R.to_3x3() @ (m.translation - pivot)
        pb.matrix = rig.matrix_world.inverted() @ m; bpy.context.view_layer.update()
        pb.keyframe_insert("location", frame=f, group="root")
        for c in ctrls:
            m = Matrix.Translation(pivot) @ R @ Matrix.Translation(-pivot) @ world[c]
            pbs[c].matrix = rig.matrix_world.inverted() @ m; bpy.context.view_layer.update()
            pbs[c].keyframe_insert("location", frame=f, group=c)
            pbs[c].keyframe_insert("rotation_quaternion" if pbs[c].rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=c)
    log("yaw-clip %+.1f deg: the whole clip turned about the vertical through the root's first-frame spot (Root orientation untouched)" % deg)


def knees_in(act, d):
    ad.action = act
    sep0 = []; sep1 = []
    for f in range(F0, F1 + 1):
        scene.frame_set(f)
        lat = ((rig.matrix_world @ pbs["DEF-spine"].matrix).to_3x3() @ Vector((1, 0, 0))); lat.z = 0
        if lat.length < 1e-6: lat = Vector((1, 0, 0))
        lat.normalize()
        kl = (rig.matrix_world @ pbs["DEF-shin.L"].matrix).translation.copy(); kr = (rig.matrix_world @ pbs["DEF-shin.R"].matrix).translation.copy()
        sep0.append((kl - kr).length)
        mid = 0.5 * (kl + kr)
        for sd in ("L", "R"):
            if pbs["thigh_parent." + sd]["IK_FK"] > 0.5:
                continue
            fk = fk_knee(sd); side_sign = 1.0 if (fk - mid).dot(lat) > 0 else -1.0
            tgt = fk - lat * (side_sign * 0.5 * d)
            hip_ = (rig.matrix_world @ pbs["DEF-thigh." + sd].matrix).translation.copy(); ank_ = (rig.matrix_world @ pbs["DEF-foot." + sd].matrix).translation.copy()
            leg_pole(sd, tgt, hip_, ank_)
            pole = pbs["thigh_ik_target." + sd]
            pole.keyframe_insert("location", frame=f, group="thigh_ik_target." + sd)
            pole.keyframe_insert("rotation_quaternion" if pole.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group="thigh_ik_target." + sd)
            pbs["thigh_parent." + sd].keyframe_insert('["pole_vector"]', frame=f, group="thigh_parent." + sd)
        bpy.context.view_layer.update()
        kl = (rig.matrix_world @ pbs["DEF-shin.L"].matrix).translation; kr = (rig.matrix_world @ pbs["DEF-shin.R"].matrix).translation
        sep1.append((kl - kr).length)
    log("knees-in %.3f rig m: knees apart %.0f..%.0f mm -> %.0f..%.0f (the swivel circle limits the move)" % (d, min(sep0) * 1000, max(sep0) * 1000, min(sep1) * 1000, max(sep1) * 1000))


def arms_down(act, deg):
    ad.action = act
    n_ = 0
    for f in range(F0, F1 + 1):
        scene.frame_set(f)
        fwd = ((rig.matrix_world @ pbs["DEF-spine"].matrix).to_3x3() @ Vector((0, 0, 1))); fwd.z = 0
        if fwd.length < 1e-6: fwd = Vector((0, -1, 0))
        fwd.normalize()
        for sd in ("L", "R"):
            if pbs["upper_arm_parent." + sd]["IK_FK"] < 0.5:
                continue                                        # an IK arm is placed by its hand; leave it
            pb = pbs["upper_arm_fk." + sd]; m = (rig.matrix_world @ pb.matrix).copy(); sh = m.translation.copy()
            lat = ((rig.matrix_world @ pbs["DEF-spine"].matrix).to_3x3() @ Vector((1, 0, 0))); lat.z = 0; lat.normalize()
            el = (rig.matrix_world @ pbs["DEF-forearm." + sd].matrix).translation
            side_sign = 1.0 if (el - sh).dot(lat) > 0 else -1.0     # which way is "out" for this arm
            # a rotation about the forward axis that moves the elbow inward: sign found by trial on the elbow
            R1 = Matrix.Rotation(math.radians(deg), 4, fwd); R2 = Matrix.Rotation(-math.radians(deg), 4, fwd)
            def moved(R):
                e = Matrix.Translation(sh) @ R @ Matrix.Translation(-sh) @ Matrix.Translation(el)
                return (e.translation - sh).dot(lat) * side_sign
            R = R1 if moved(R1) < moved(R2) else R2
            pb.matrix = rig.matrix_world.inverted() @ (Matrix.Translation(sh) @ R @ Matrix.Translation(-sh) @ m); bpy.context.view_layer.update()
            pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group="upper_arm_fk." + sd)
            n_ += 1
    log("arms-down %.0f deg: %d arm-frames adducted about the body's forward axis" % (deg, n_))


def loop_shift(K):
    global poses, baked
    ad.action = baked
    n = F1 - F0 + 1; m = n - 1                                   # the cycle: the last frame repeats the first + travel
    scene.frame_set(F0); r0 = (rig.matrix_world @ pbs["root"].matrix).translation.copy()
    scene.frame_set(F1); r1 = (rig.matrix_world @ pbs["root"].matrix).translation.copy()
    travel = r1 - r0
    old = {}
    for f in range(F0, F1 + 1):
        scene.frame_set(f); old[f] = read_pose()
    new = {}
    for j in range(n):
        i = K + j; wraps = i // m; src = F0 + i % m
        rec = {c: dict(v) for c, v in old[src].items()}
        rec["root"] = dict(rec["root"], loc=rec["root"]["loc"] + travel * wraps)   # root: no parent, its local location is armature space
        new[F0 + j] = rec
    poses = new; baked = write_action(RESULT, poses, False); ad.action = baked
    scene.frame_set(F0); a_ = (rig.matrix_world @ pbs["DEF-spine"].matrix).translation.copy(); scene.frame_set(F1); b_ = (rig.matrix_world @ pbs["DEF-spine"].matrix).translation.copy()
    log("loop-shift %d: the clip now starts on the old frame %d, the old frames %d..%d follow at the end advanced by the travel; last frame vs first + travel on the hips %.1f mm" % (K, F0 + K, F0, F0 + K - 1, ((a_ + travel) - b_).length * 1000))


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
            if not KEEP_POLES:
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
if (PIN_FOOT or IK_LEGS or STRIDE != 1.0 or VSMOOTH) and not KEEP_POLES:
    repole_legs(baked)
if FOOT_CLEAR:
    foot_clear(baked, float(FOOT_CLEAR))
if TORSO_DROP:
    torso_drop(baked, TORSO_DROP)
    repole_legs(baked)
if YAW_CLIP:
    yaw_clip(baked, YAW_CLIP)
if KNEES_IN:
    knees_in(baked, KNEES_IN)
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

if ARMS_DOWN:
    arms_down(baked, ARMS_DOWN)

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

if EVEN_ADVANCE:
    even_advance(EVEN_ADVANCE)

if LOOP_SHIFT:
    loop_shift(LOOP_SHIFT)

if END_BLEND:
    end_blend(baked, END_BLEND)

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
