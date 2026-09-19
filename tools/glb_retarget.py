"""Retarget a Kimodo GLB (30-joint SOMA human, Mixamo-style names) onto the shared Rigify
rig in Animations/skeleton_anim.blend as a new looping Action.

    blender -b Animations/skeleton_anim.blend -P tools/glb_retarget.py -- \
        --glb "External Anims/Kimodo/idle_s42.glb" --name Idle [--loop 120] [--blend 30] \
        [--src-start 30] [--fist 0.3] [--hunch 0] [--save]

Lean descendant of smp-10-rgp-creatures/tools/glb_retarget.py, for STANDING clips:
  * every mapped joint's WORLD rotation delta from its own bind pose (the GLB's T-pose)
    is applied on top of the target control's rest: target = delta * A * target_rest.
    A is a per-bone rest correction for the ARMS only (the minimal rotation taking the
    target bone's rest direction onto the source's), so a T-pose source lands on an
    A-pose rig. Torso, neck, head and shoulders keep the rig's own rest.
  * the hips translation is scaled by the hip-height ratio and put on `torso`.
  * LEGS ARE NOT COPIED. They stay on Rigify's IK with the feet at their rest positions:
    an idle is a planted pose, and copying a human's FK legs onto different proportions
    is exactly what skated the creatures' feet (creatures CLAUDE.md 12). Weight shift
    comes through the hips; the IK legs follow.
  * arms run FK (`IK_FK` = 1, keyed on every frame so no other clip's slider leaks in).
  * loop: output frame f takes source frame src_start + f; over the last `blend` frames
    it crossfades (slerp / lerp) into the source frames that precede the start, so the
    frame after the last equals the first. Frames are written 1..loop+1, frame loop+1
    being the seam duplicate Unity expects.
  * fingers: a constant slight curl on the finger master controls (`--fist`), so the
    hands do not hang flat.
Nothing is grounded per frame: with the feet pinned the mesh minimum is the rest's.
The script reports the Body mesh minimum per frame anyway.
"""
import bpy, sys, os, math
from mathutils import Vector, Matrix, Quaternion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(k, d=None):
    return argv[argv.index(k) + 1] if k in argv else d


GLB = os.path.abspath(os.path.join(ROOT, arg("--glb")))
NAME = arg("--name", "Idle")
LOOP = int(arg("--loop", "120"))
BLEND = int(arg("--blend", "30"))
SRC_START = int(arg("--src-start", "30"))
FIST = float(arg("--fist", "0.3"))
HUNCH = math.radians(float(arg("--hunch", "0")))   # extra forward pitch on the chest, deg
SAVE = "--save" in argv
REF_BODY = "SkeletonKnight_Body"

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
LEVELS = [["torso"], ["spine_fk"], ["spine_fk.001"], ["spine_fk.002"], ["spine_fk.003"],
          ["neck", "shoulder.L", "shoulder.R"], ["head", "upper_arm_fk.L", "upper_arm_fk.R"],
          ["forearm_fk.L", "forearm_fk.R"], ["hand_fk.L", "hand_fk.R"]]
IKFK_ARMS = ["upper_arm_parent.L", "upper_arm_parent.R"]
IKFK_LEGS = ["thigh_parent.L", "thigh_parent.R"]
FINGER_MASTERS = ["thumb.01_master", "f_index.01_master", "f_middle.01_master", "f_ring.01_master", "f_pinky.01_master"]


def log(*a):
    print("[retarget]", *a); sys.stdout.flush()


def update():
    bpy.context.view_layer.update()


def smooth(u):
    u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
scene = bpy.context.scene
assert abs(scene.render.fps - 30) < 1e-6
pbs = rig.pose.bones


def controls():
    return [b.name for b in pbs if not b.name.startswith(("DEF-", "MCH-", "ORG-", "VIS_"))]


def zero_pose():
    for pb in pbs:
        pb.matrix_basis.identity()
    for b in IKFK_ARMS + IKFK_LEGS:
        pbs[b]["IK_FK"] = 0.0
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
log("target hip pivot z %.4f, torso control at %s" % (hip_z_t, tuple(round(v, 4) for v in T_rest["torso"][2])))

# ------------------------------------------------------------- 2. source
before = set(bpy.data.objects) | set()
acts_before = set(bpy.data.actions)
bpy.ops.import_scene.gltf(filepath=GLB)
new = [o for o in bpy.data.objects if o not in before]
SRC_ARM = next(o for o in new if o.type == 'ARMATURE')
src_act = SRC_ARM.animation_data.action if SRC_ARM.animation_data else None
assert src_act is not None, "GLB armature carries no action"
n_src = int(round(src_act.frame_range[1] - src_act.frame_range[0])) + 1
f_src0 = int(round(src_act.frame_range[0]))
log("source %s: %d joints, %d frames (%d..%d)" % (os.path.basename(GLB), len(SRC_ARM.data.bones), n_src,
                                                  f_src0, f_src0 + n_src - 1))
S = {b.name: b for b in SRC_ARM.data.bones}
S_rest = {n: ((SRC_ARM.matrix_world @ b.matrix_local).to_quaternion(),
              (SRC_ARM.matrix_world @ b.head_local).copy()) for n, b in S.items()}
hip_z_s = S_rest["Hips"][1].z
scale = hip_z_t / hip_z_s
log("source hips rest z %.4f -> scale %.4f" % (hip_z_s, scale))

A = {}
for src, tgt, align, kid in MAP:
    if align:
        d_s = (S_rest[kid][1] - S_rest[src][1]).normalized()
        A[tgt] = T_rest[tgt][1].rotation_difference(d_s)
        log("  rest correction %-16s %.1f deg" % (tgt, math.degrees(A[tgt].angle)))
    else:
        A[tgt] = Quaternion((1, 0, 0, 0))

SRC = []
for i in range(n_src):
    scene.frame_set(f_src0 + i); update()
    SRC.append({n: ((SRC_ARM.matrix_world @ SRC_ARM.pose.bones[n].matrix).to_quaternion(),
                    (SRC_ARM.matrix_world @ SRC_ARM.pose.bones[n].head).copy()) for n in S})
need = SRC_START + LOOP
assert need <= n_src, "need %d source frames (src-start %d + loop %d), have %d" % (need, SRC_START, LOOP, n_src)
assert SRC_START >= BLEND, "src-start must be >= blend so the seam has frames to fade into"
for o in new:
    bpy.data.objects.remove(o, do_unlink=True)
for a in list(bpy.data.actions):
    if a not in acts_before:
        bpy.data.actions.remove(a)


def sample(f):
    """Source pose for output frame f (0-based), loop-blended over the last BLEND frames."""
    a = SRC[SRC_START + f]
    if f < LOOP - BLEND:
        return a
    w = smooth((f - (LOOP - BLEND)) / float(BLEND))
    b = SRC[SRC_START + f - LOOP]
    out = {}
    for n in a:
        qb = b[n][0].copy()
        if a[n][0].dot(qb) < 0:
            qb.negate()
        out[n] = (a[n][0].slerp(qb, w), a[n][1].lerp(b[n][1], w))
    return out


# ------------------------------------------------------------- 3. the action
act = bpy.data.actions.get(NAME)
if act is not None:
    bpy.data.actions.remove(act)
act = bpy.data.actions.new(NAME)
act.use_fake_user = True
rig.animation_data_create()
rig.animation_data.action = act
if hasattr(rig.animation_data, "action_slot"):
    slot = act.slots.new('OBJECT', rig.name)
    rig.animation_data.action_slot = slot

DRIVEN = sorted({t for _, t, _, _ in MAP})
STATIC = [c for c in controls() if c not in DRIVEN]


def key_frame(f):
    for n in DRIVEN:
        pb = pbs[n]
        pb.keyframe_insert("location", frame=f, group=n)
        pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=n)
    for b in IKFK_ARMS + IKFK_LEGS:
        pbs[b].keyframe_insert('["IK_FK"]', frame=f, group=b)


def key_static(f):
    for n in STATIC:
        pb = pbs[n]
        pb.keyframe_insert("location", frame=f, group=n)
        pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=n)


def pose(f):
    zero_pose()
    for b in IKFK_ARMS:
        pbs[b]["IK_FK"] = 1.0
    for b in IKFK_LEGS:
        pbs[b]["IK_FK"] = 0.0
    for side in ("L", "R"):
        for m in FINGER_MASTERS:
            pb = pbs[m + "." + side]
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (FIST, 0, 0)
    src = sample(f)
    targets = {}
    for sname, tgt, _, _ in MAP:
        delta = src[sname][0] @ S_rest[sname][0].inverted()
        targets[tgt] = delta @ A[tgt] @ T_rest[tgt][0]
    if HUNCH:
        targets["spine_fk.003"] = Quaternion((1, 0, 0), HUNCH) @ targets["spine_fk.003"]
    hips = T_rest["torso"][2] + (src["Hips"][1] - S_rest["Hips"][1]) * scale
    for level in LEVELS:
        for tgt in level:
            set_world(pbs[tgt], targets[tgt], hips if tgt == "torso" else None)
        update()


body = bpy.data.objects.get(REF_BODY)


def body_min_z():
    if body is None:
        return float("nan")
    dg = bpy.context.evaluated_depsgraph_get()
    me = body.evaluated_get(dg).data
    return min((body.matrix_world @ v.co).z for v in me.vertices)


worst = (0.0, 0)
for f in range(LOOP + 1):
    frame = f + 1
    # frame_set FIRST: it re-applies the action being written, and after pose() it
    # would overwrite the fresh pose with the previous key's value before keying
    scene.frame_set(frame)
    pose(f % LOOP)
    key_frame(frame)
    if f == 0:
        key_static(frame)
    if f % 30 == 0 or f == LOOP:
        z = body_min_z()
        h = (rig.matrix_world @ pbs["torso"].matrix).translation.z
        log("  frame %3d  body min z %+.4f  torso z %.4f" % (frame, z, h))
        if abs(z) > abs(worst[0]):
            worst = (z, frame)

# seam: frame LOOP+1 was posed from source frame 0 -> identical to frame 1 by construction
scene.frame_set(1); update(); q1 = {n: world_rot(pbs[n]) for n in DRIVEN}
scene.frame_set(LOOP + 1); update(); q2 = {n: world_rot(pbs[n]) for n in DRIVEN}
seam = max(math.degrees(q1[n].rotation_difference(q2[n]).angle) for n in DRIVEN)
scene.frame_set(LOOP); update(); q3 = {n: world_rot(pbs[n]) for n in DRIVEN}
step = max(math.degrees(q3[n].rotation_difference(q2[n]).angle) for n in DRIVEN)
log("loop seam: frame 1 vs %d differ by %.4f deg (must be ~0); last step %d->%d moves %.2f deg"
    % (LOOP + 1, seam, LOOP, LOOP + 1, step))
log("worst body min z %+.4f at frame %d" % worst)
scene.frame_start, scene.frame_end = 1, LOOP + 1
scene.frame_set(1); zero_pose()
log("action %s: %d frames (%.2f s)" % (NAME, LOOP + 1, LOOP / 30.0))
if SAVE:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath, compress=True)
    log("saved")
