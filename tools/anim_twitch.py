"""Author the additive twitch clips (head + lower jaw) in Animations/skeleton_anim.blend.

    blender -b Animations/skeleton_anim.blend -P tools/anim_twitch.py [-- --save]

Writes Twitch_01, Twitch_02, Twitch_03: 2.5 / 3.5 / 4.5 s at 30 fps, different seeds.
Frame 1 is the REST pose and so is the last frame, so the clip is its own additive
reference (Unity: Additive Reference Pose = frame 0; Unreal: Additive Anim Type Local
Space, Base Pose = selected animation frame 0). Played on an additive layer over any
base clip, with a random pick and a random start per instance, so an army does not
twitch in unison (CLAUDE.md 8).

What a twitch is: a quick jerk (2-4 frames in), a short hold, a slower settle (6-14
frames out), sometimes with a small rebound. Head: random axis, 3-9 deg. Jaw: opens
1-6 deg, sometimes chatters (two or three quick opens). Gaps of 0.4-1.6 s between
events. Nothing else moves: additive deltas elsewhere are zero by construction.
"""
import bpy, sys, os, math, random
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAVE = "--save" in argv
CLIPS = [("Twitch_01", 75, 1), ("Twitch_02", 105, 2), ("Twitch_03", 135, 3)]

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
pbs = rig.pose.bones
scene = bpy.context.scene
HEAD, NECK, JAW = pbs["head"], pbs["neck"], pbs["lowerjaw"]


def log(*a):
    print("[twitch]", *a); sys.stdout.flush()


def zero():
    for pb in pbs:
        pb.matrix_basis.identity()
    bpy.context.view_layer.update()


# which way does the jaw control open? rotate +/- about local X and see where the chin goes
zero()
chin0 = (rig.matrix_world @ pbs["DEF-lowerjaw.001"].tail).copy()
JAW.rotation_mode = 'XYZ'
JAW.rotation_euler = (math.radians(10), 0, 0); bpy.context.view_layer.update()
chin_p = (rig.matrix_world @ pbs["DEF-lowerjaw.001"].tail).copy()
JAW.rotation_euler = (0, 0, 0); bpy.context.view_layer.update()
# opening = the chin moves DOWN (this rig's jaw chain pivots inside the skull and runs
# down to the chin, so 'forward' is the wrong test: +X here lifted the chin)
JAW_SIGN = 1.0 if (chin_p - chin0).z < 0 else -1.0
log("jaw: +10 deg about X moves the chin by %s -> open sign %+.0f" % (tuple(round(v, 4) for v in (chin_p - chin0)), JAW_SIGN))


def envelope(attack, hold, release, rebound=0.0):
    """0..1..0 over attack+hold+release frames, optional negative rebound after."""
    out = []
    for i in range(attack):
        u = (i + 1) / float(attack); out.append(u * u)                      # snap in
    out += [1.0] * hold
    for i in range(release):
        u = 1.0 - (i + 1) / float(release); out.append(u * u * (3 - 2 * u))  # settle
    if rebound:
        for i in range(6):
            u = math.sin(math.pi * (i + 1) / 7.0); out.append(-rebound * u)
    return out


def author(name, frames, seed):
    rnd = random.Random(seed)
    head = [Vector((0, 0, 0)) for _ in range(frames + 1)]
    jaw = [0.0 for _ in range(frames + 1)]
    f = 1 + rnd.randint(6, 20)
    events = 0
    while f < frames - 20:
        kind = rnd.choice(["head", "head", "jaw", "both", "chatter"])
        if kind in ("head", "both"):
            axis = Vector((rnd.uniform(-1, 1), rnd.uniform(-0.6, 0.6), rnd.uniform(-1, 1))).normalized()
            amp = math.radians(rnd.uniform(3, 9))
            env = envelope(rnd.randint(2, 4), rnd.randint(0, 3), rnd.randint(6, 14), rebound=rnd.choice([0, 0, 0.25]))
            for i, e in enumerate(env):
                if f + i <= frames:
                    head[f + i] = head[f + i] + axis * amp * e
        if kind in ("jaw", "both"):
            amp = math.radians(rnd.uniform(1, 6))
            env = envelope(rnd.randint(2, 3), rnd.randint(0, 4), rnd.randint(5, 12))
            for i, e in enumerate(env):
                if f + i <= frames:
                    jaw[f + i] += amp * e
        if kind == "chatter":
            amp = math.radians(rnd.uniform(2, 5))
            g = f
            for _ in range(rnd.randint(2, 3)):
                env = envelope(2, 0, 3)
                for i, e in enumerate(env):
                    if g + i <= frames:
                        jaw[g + i] += amp * e
                g += rnd.randint(5, 7)
        events += 1
        f += rnd.randint(12, 48)
    # the last frame must be rest again
    head[frames] = Vector((0, 0, 0)); jaw[frames] = 0.0
    head[1] = Vector((0, 0, 0)); jaw[1] = 0.0

    act = bpy.data.actions.get(name)
    if act is not None:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = act
    if hasattr(rig.animation_data, "action_slot"):
        rig.animation_data.action_slot = act.slots.new('OBJECT', rig.name)
    zero()
    HEAD.rotation_mode = 'XYZ'; NECK.rotation_mode = 'XYZ'; JAW.rotation_mode = 'XYZ'
    for fr in range(1, frames + 1):
        v = head[fr]
        HEAD.rotation_euler = Euler((v.x, v.y, v.z), 'XYZ')
        NECK.rotation_euler = Euler((v.x * 0.35, v.y * 0.35, v.z * 0.35), 'XYZ')   # the neck carries a third
        JAW.rotation_euler = (JAW_SIGN * jaw[fr], 0, 0)
        for pb in (HEAD, NECK, JAW):
            pb.keyframe_insert("rotation_euler", frame=fr, group=pb.name)
    peak_h = max(math.degrees(v.length) for v in head[1:])
    peak_j = max(math.degrees(x) for x in jaw[1:])
    log("%s: %d frames (%.1f s), %d events, head peak %.1f deg, jaw peak %.1f deg" % (name, frames, frames / 30.0, events, peak_h, peak_j))
    return act


for name, frames, seed in CLIPS:
    author(name, frames, seed)
zero()
rig.animation_data.action = None
if SAVE:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath, compress=True)
    log("saved")
