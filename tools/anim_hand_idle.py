"""Author the empty-hand finger idles: Hand_Idle_L / Hand_Idle_R (2026-09-25).

    blender -b Animations/skeleton_anim.blend -P tools/anim_hand_idle.py -- [--frames 240] [--amp 3] [--save]

User: "from Grip action frame 2, use left hand pose for left, and mirrored right poses, as default
hand pose when model don't hold anything in it's hand. make 2 actions for it, for left and right
hand, with slight fingers movement, so they don't look static".

The Grip action's frame 2 carries the user's RELAXED left hand (frame 1 is the fist both hands take
on a held item; the right hand is that fist on both frames). Each action keys that hand's 26 finger
controls (thumb / f_* chains, their masters, the palm) on every frame of a loop: the frame-2 pose
plus a slow sine per finger master (integer cycles over the loop, so frame N+1 == frame 1) of a few
degrees of curl, phases spread so the fingers do not move in step. Every other control is keyed at
rest on the first and last frame (the clip plays on a finger-only masked layer; the rest of the body
is never seen from it). Hand_Idle_R is the Paste-X-Flipped mirror of the left pose (location x,
quaternion y and z, Euler y and z negated), verified below by fingertip positions.

In the engine the two clips loop on the finger-only layers LeftFingers / RightFingers of
AC_Skeleton, whose weights SkeletonWeapon sets per hand: 1 while the hand holds nothing, 0 while it
holds an item (the Grip fist then goes on in LateUpdate as before).
"""
import bpy, math, sys
from mathutils import Vector, Quaternion, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(k, d=None):
    return argv[argv.index(k) + 1] if k in argv else d


FRAMES = int(arg("--frames", "240"))
AMP = math.radians(float(arg("--amp", "6.0")))
SAVE = "--save" in argv

rig = bpy.data.objects["RIG-Meta-Rig"]; pbs = rig.pose.bones; scene = bpy.context.scene; ad = rig.animation_data
scene.render.fps = 30
for t in ad.nla_tracks:
    t.mute = True
CONTROLS = [b.name for b in pbs if not b.name.startswith(("DEF-", "MCH-", "ORG-", "VIS_"))]


def log(s):
    print("[hand_idle] " + s, flush=True)


def finger_controls(side):
    return sorted(n for n in pbs.keys() if (n.startswith(("thumb", "f_", "palm"))) and (n.endswith("." + side) or n.endswith("." + side + ".001")))


def mirror_name(n):
    return n[:-6] + ".R.001" if n.endswith(".L.001") else n[:-2] + ".R"


# --- the relaxed pose: Grip frame 2, left hand -------------------------------------------------------
grip = bpy.data.actions["Grip"]
ad.action = grip
if hasattr(ad, "action_slot") and grip.slots:
    ad.action_slot = grip.slots[0]
ad.action_blend_type = 'REPLACE'
scene.frame_set(2); bpy.context.view_layer.update()
LEFT = finger_controls("L")
assert len(LEFT) == 26, LEFT
pose = {}
for n in LEFT:
    pb = pbs[n]
    rot = pb.rotation_quaternion.copy() if pb.rotation_mode == 'QUATERNION' else pb.rotation_euler.copy()
    pose[n] = (pb.location.copy(), rot, pb.scale.copy(), pb.rotation_mode)
log("Grip frame 2, left hand: %d finger controls read" % len(pose))

# the slow sway: per finger master, amplitude x AMP, cycles per loop, phase (turns)
SWAY = {"f_index.01_master": (1.0, 1, 0.00), "f_middle.01_master": (1.0, 1, 0.20), "f_ring.01_master": (1.0, 2, 0.50),
        "f_pinky.01_master": (1.3, 2, 0.70), "thumb.01_master": (0.7, 1, 0.40)}


def build(side):
    name = "Hand_Idle_" + side
    old = bpy.data.actions.get(name)
    if old is not None:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    ad.action = act
    if hasattr(ad, "action_slot"):
        ad.action_slot = act.slots.new('OBJECT', rig.name)
    for pb in pbs:
        pb.matrix_basis.identity()
    # rest on the first and last frame for everything (a finger-only layer never shows the rest)
    for f in (1, FRAMES):
        for n in CONTROLS:
            pb = pbs[n]
            pb.keyframe_insert("location", frame=f, group=n)
            pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_axis_angle" if pb.rotation_mode == 'AXIS_ANGLE' else "rotation_euler", frame=f, group=n)
            pb.keyframe_insert("scale", frame=f, group=n)
    mirror = side == "R"
    for f in range(1, FRAMES + 1):
        t = (f - 1) / float(FRAMES)
        for ln, (loc, rot, scl, mode) in pose.items():
            n = mirror_name(ln) if mirror else ln
            pb = pbs[n]
            loc_ = loc.copy(); scl_ = scl.copy()
            if mode == 'QUATERNION':
                rot_ = Quaternion((rot.w, rot.x, -rot.y, -rot.z)) if mirror else rot.copy()
            else:
                rot_ = Euler((rot.x, -rot.y, -rot.z), rot.order) if mirror else rot.copy()
            if mirror:
                loc_.x = -loc_.x
            key = ln[:-2] if ln.endswith(".L") else None
            if key in SWAY and mode != 'QUATERNION':
                a, cyc, ph = SWAY[key]
                rot_.x += a * AMP * math.sin(2 * math.pi * (cyc * t + ph))
            pb.location = loc_; pb.scale = scl_
            if mode == 'QUATERNION':
                pb.rotation_quaternion = rot_
            else:
                pb.rotation_euler = rot_
            pb.keyframe_insert("location", frame=f, group=n)
            pb.keyframe_insert("rotation_quaternion" if mode == 'QUATERNION' else "rotation_euler", frame=f, group=n)
            pb.keyframe_insert("scale", frame=f, group=n)
    act.frame_range = (1, FRAMES)
    log("%s: %d frames (%.1f s), %d finger controls swaying up to %.1f deg" % (name, FRAMES, FRAMES / 30.0, len(pose), math.degrees(AMP) * max(a for a, _, _ in SWAY.values())))
    return act


acts = {s: build(s) for s in ("L", "R")}


def tips(side):
    return {n: (rig.matrix_world @ pbs["DEF-%s.03.%s" % (n, side)].matrix).translation.copy() for n in ("thumb", "f_index", "f_middle", "f_ring", "f_pinky")}


def wrist(side):
    return (rig.matrix_world @ pbs["DEF-hand." + side].matrix).translation.copy()


# --- checks: the mirror, the seam, the motion ---------------------------------------------------------
for pb in pbs:
    pb.matrix_basis.identity()
ad.action = acts["L"]; ad.action_slot = acts["L"].slots[0]; scene.frame_set(1); bpy.context.view_layer.update()
tl = tips("L"); wl = wrist("L")
ad.action = acts["R"]; ad.action_slot = acts["R"].slots[0]; scene.frame_set(1); bpy.context.view_layer.update()
tr = tips("R"); wr = wrist("R")
worst = max((Vector((-tl[n].x, tl[n].y, tl[n].z)) - tr[n]).length for n in tl) * 1000
log("mirror check on frame 1: right fingertips within %.1f mm of the X-mirrored left ones (wrists %.1f mm apart in X-mirror)" % (worst, (Vector((-wl.x, wl.y, wl.z)) - wr).length * 1000))
log("tips from the wrist, left (mm): " + ", ".join("%s %.0f" % (n, (tl[n] - wl).length * 1000) for n in tl))
for side in ("L", "R"):
    ad.action = acts[side]; ad.action_slot = acts[side].slots[0]
    scene.frame_set(1); a = tips(side); scene.frame_set(FRAMES); b = tips(side)
    seam = max((a[n] - b[n]).length for n in a) * 1000
    travel = {n: 0.0 for n in a}; prev = None
    for f in range(1, FRAMES + 1, 4):
        scene.frame_set(f); cur = tips(side)
        if prev:
            for n in cur:
                travel[n] = max(travel[n], (cur[n] - a[n]).length)
        prev = cur
    log("%s: seam (frame %d vs 1) %.1f mm; fingertip excursion over the loop: %s" % ("Hand_Idle_" + side, FRAMES, seam, ", ".join("%s %.0f mm" % (n, v * 1000) for n, v in travel.items())))

ad.action = None
if SAVE:
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath, compress=True)   # compressed like every other tool: an uncompressed save is 290 MB, over GitHub's 100 MB limit
    log("saved " + bpy.data.filepath)
else:
    log("dry run (no --save)")
