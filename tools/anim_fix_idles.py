"""Hand-fix the three idles in place (user review 2026-09-21), no Kimodo regeneration.

    blender -b Animations/skeleton_anim.blend -P tools/anim_fix_idles.py -- [--save] [--only Idle,Idle_02]

Per frame of each action (the retarget keyed every frame, so every frame is re-keyed):

  all three   wrists: the socket's hilt axis (+Y of DEF-weapon, the blade direction) is
              turned to face FORWARD by pronating forearm_fk about its own axis (the hand
              follows). Before: Idle 72-83 deg off forward, Idle_03 90-112, Idle_02 110-140
              (blades pointed into the model). Target: forward, 12 deg outward.
  Idle        torso dropped 10 mm: its hips sat 7 mm above the legs' reach and the IK chain
              lifted both feet 9 mm off the floor ("feet slightly floating").
  Idle_02     spine flex scaled to SPINE_KEEP (chest tilt 57-69 deg -> ~25), head re-aimed
              forward on top of the new spine (HEAD_KEEP of its own motion kept), both arms
              replaced by Idle's hanging arms (Idle's arm world rotations resampled over the
              loop): the source arms were bent up in front, "left arm bent strange".

Everything is written back into the same actions; export with export_fbx.py --clip.
"""
import bpy, math, sys, os
from mathutils import Vector, Quaternion, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAVE = "--save" in argv
ONLY = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else {"Idle", "Idle_02", "Idle_03"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FWD = Vector((0, -1, 0)); UP = Vector((0, 0, 1))
OUTWARD_DEG = 12.0          # blades point forward and a little out, not exactly parallel
SPINE_KEEP = 0.4            # Idle_02: fraction of the source spine flex kept
HEAD_KEEP = 0.25            # Idle_02: fraction of the source head motion kept (about the rest heading)
IDLE_TORSO_DROP = 0.010

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
pbs = rig.pose.bones
scene = bpy.context.scene


def log(m):
    print("[fix] " + m); sys.stdout.flush()


def update():
    bpy.context.view_layer.update()


def wmat(n):
    return rig.matrix_world @ pbs[n].matrix


def world_rot(n):
    return wmat(n).to_quaternion()


def set_world_rot(n, q):
    pb = pbs[n]
    m = pb.matrix.copy()
    Rm = (rig.matrix_world.inverted().to_3x3() @ q.to_matrix()).to_4x4()
    Rm.translation = m.translation
    pb.matrix = Rm


def key(n, f):
    pb = pbs[n]
    pb.keyframe_insert("location", frame=f, group=n)
    pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=n)


def rest_rots():
    """World rotation of every control at rest (action detached, pose cleared)."""
    prev = rig.animation_data.action
    rig.animation_data.action = None
    for pb in pbs:
        pb.matrix_basis.identity()
    update()
    r = {pb.name: world_rot(pb.name) for pb in pbs}
    rig.animation_data.action = prev
    return r


REST = rest_rots()
ARM = ["upper_arm_fk", "forearm_fk", "hand_fk"]
SPINE = ["spine_fk", "spine_fk.001", "spine_fk.002", "spine_fk.003"]
ARM_BONES = ["shoulder." + s for s in "LR"] + [b + "." + s for b in ARM for s in "LR"]


def sample_arms(action_name):
    """World rotations of the arm controls on every frame of an action (Idle: hanging arms)."""
    act = bpy.data.actions[action_name]
    rig.animation_data.action = act
    if hasattr(rig.animation_data, "action_slot") and act.slots:
        rig.animation_data.action_slot = act.slots[0]
    f0, f1 = (int(round(x)) for x in act.frame_range)
    out = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f); update()
        out.append({n: world_rot(n) for n in ARM_BONES})
    return out


IDLE_ARMS = sample_arms("Idle") if "Idle_02" in ONLY else None


def mirror_q(q):
    """Reflect a world rotation across the YZ plane (right <-> left)."""
    return Quaternion((q.w, q.x, -q.y, -q.z))


def wrist_forward(side):
    """Pronate forearm_fk.<side> so DEF-weapon.<side>'s +Y points forward (+OUTWARD_DEG out)."""
    fa = "forearm_fk." + side
    axis = (wmat(fa).to_3x3() @ Vector((0, 1, 0))).normalized()          # forearm axis
    hilt = (wmat("DEF-weapon." + side).to_3x3() @ Vector((0, 1, 0))).normalized()
    out = Vector((1 if side == "L" else -1, 0, 0))
    target = (FWD * math.cos(math.radians(OUTWARD_DEG)) + out * math.sin(math.radians(OUTWARD_DEG))).normalized()
    # project both onto the plane perpendicular to the forearm axis, signed angle about the axis
    h = (hilt - axis * hilt.dot(axis)); t = (target - axis * target.dot(axis))
    if h.length < 1e-4 or t.length < 1e-4:
        return 0.0
    h.normalize(); t.normalize()
    ang = math.atan2(h.cross(t).dot(axis), h.dot(t))
    set_world_rot(fa, Quaternion(axis, ang) @ world_rot(fa))
    update()
    return math.degrees(ang)


def process(name):
    act = bpy.data.actions[name]
    rig.animation_data.action = act
    if hasattr(rig.animation_data, "action_slot") and act.slots:
        rig.animation_data.action_slot = act.slots[0]
    f0, f1 = (int(round(x)) for x in act.frame_range)
    twist_stats = {"L": [], "R": []}
    tilt_before = tilt_after = 0.0
    for f in range(f0, f1 + 1):
        scene.frame_set(f); update()
        if name == "Idle":
            pbs["torso"].location.z -= IDLE_TORSO_DROP
            update()
        if name == "Idle_02":
            # spine: scale each control's own rotation towards identity, root to tip
            if f == f0:
                tilt_before = math.degrees((wmat("DEF-spine.003").to_3x3() @ Vector((0, 1, 0))).normalized().angle(UP))
            for n in ["torso"] + SPINE:
                pb = pbs[n]
                if pb.rotation_mode == 'QUATERNION':
                    pb.rotation_quaternion = Quaternion((1, 0, 0, 0)).slerp(pb.rotation_quaternion, SPINE_KEEP)
                else:
                    pb.rotation_euler = tuple(v * SPINE_KEEP for v in pb.rotation_euler)
            update()
            if f == f0:
                tilt_after = math.degrees((wmat("DEF-spine.003").to_3x3() @ Vector((0, 1, 0))).normalized().angle(UP))
            # head: look forward (rest heading) with a fraction of its own motion; neck neutral
            set_world_rot("neck", REST["neck"]); update()
            delta = world_rot("head") @ REST["head"].inverted()
            set_world_rot("head", Quaternion((1, 0, 0, 0)).slerp(delta, HEAD_KEEP) @ REST["head"]); update()
            # arms := Idle's hanging arms, resampled over this loop (both loops close, so the seam holds)
            src = IDLE_ARMS[int(round((f - f0) * (len(IDLE_ARMS) - 1) / float(f1 - f0)))]
            for n in ARM_BONES:
                set_world_rot(n, src[n]); update()
        for side in "LR":
            twist_stats[side].append(wrist_forward(side))
        for n in ["torso", "neck", "head"] + SPINE + ARM_BONES:
            key(n, f)
    log("%s: %d frames; wrist twist applied L %.0f..%.0f deg, R %.0f..%.0f deg%s" % (
        name, f1 - f0 + 1, min(twist_stats["L"]), max(twist_stats["L"]), min(twist_stats["R"]), max(twist_stats["R"]),
        ("; chest tilt at frame 1: %.0f -> %.0f deg" % (tilt_before, tilt_after)) if name == "Idle_02" else ""))
    # report the result on the first frame
    scene.frame_set(f0); update()
    for side in "LR":
        hilt = (wmat("DEF-weapon." + side).to_3x3() @ Vector((0, 1, 0))).normalized()
        log("   %s hilt now %.0f deg from forward" % (side, math.degrees(hilt.angle(FWD))))
    if name == "Idle":
        log("   hips z %.4f, ankle z L %.4f R %.4f (rest ankle 0.052)" % (wmat("DEF-spine").translation.z, wmat("DEF-foot.L").translation.z, wmat("DEF-foot.R").translation.z))


for n in ("Idle", "Idle_02", "Idle_03"):
    if n in ONLY:
        process(n)
scene.frame_set(1)
if SAVE:
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath, compress=True)
    log("saved " + os.path.relpath(bpy.data.filepath, ROOT))
