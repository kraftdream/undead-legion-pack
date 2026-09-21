"""Split the stance of an IK-legged idle: move each resting foot forward/back, keep the knees bent.

    blender -b Animations/skeleton_anim.blend -P tools/anim_stance.py -- --action Idle_02 --left 0.03 --right -0.03 [--save]

Distances in rig metres along the character's forward axis (+ = forward; x1.8 in the engine).
Every frame: the foot_ik controls are translated in world space (the toe follows as a
child), then the torso is lowered by ONE constant so the hip-to-foot distance never exceeds
PLANT_REACH of the leg (a straight IK leg has no defined roll: "knees twist", 2026-09-21).
Written back into the same action; export with export_fbx.py --clip. Not idempotent: each
run adds its shift and its drop.
"""
import bpy, math, sys, os
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(k, d=None):
    return argv[argv.index(k) + 1] if k in argv else d
ACTION = arg("--action", "Idle_02")
SHIFT = {"L": float(arg("--left", "0")), "R": float(arg("--right", "0"))}
SAVE = "--save" in argv
PLANT_REACH = 0.985
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
pbs = rig.pose.bones; scene = bpy.context.scene
def log(m): print("[stance] " + m); sys.stdout.flush()
def update(): bpy.context.view_layer.update()
def wpos(n): return (rig.matrix_world @ pbs[n].matrix).translation
def key(n, f):
    pb = pbs[n]; pb.keyframe_insert("location", frame=f, group=n)
    pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=f, group=n)

rig.animation_data.action = None
for pb in pbs: pb.matrix_basis.identity()
update()
LEG = {s: (wpos("DEF-thigh." + s) - wpos("DEF-shin." + s)).length + (wpos("DEF-shin." + s) - wpos("DEF-foot." + s)).length for s in "LR"}
act = bpy.data.actions[ACTION]; rig.animation_data.action = act
if hasattr(rig.animation_data, "action_slot") and act.slots: rig.animation_data.action_slot = act.slots[0]
f0, f1 = (int(round(x)) for x in act.frame_range)
assert all(pbs["thigh_parent." + s]["IK_FK"] < 0.5 for s in "LR"), "legs are not on IK"

# pass 0: read every frame's foot controls BEFORE writing anything (the controls are keyed
# on frame 1 only; keying a shifted frame changes what the next frame evaluates to, and
# shifting per frame compounded 361 times the first time this ran)
orig = {}
for f in range(f0, f1 + 1):
    scene.frame_set(f); update()
    orig[f] = {s: (rig.matrix_world @ pbs["foot_ik." + s].matrix).copy() for s in "LR"}
# pass 1: shift the feet, measure the reach
need = 0.0
for f in range(f0, f1 + 1):
    scene.frame_set(f); update()
    for s, d in SHIFT.items():
        pbs["foot_ik." + s].matrix = rig.matrix_world.inverted() @ Matrix.Translation((0, -d, 0)) @ orig[f][s]
        update(); key("foot_ik." + s, f)
    for s in "LR":
        v = wpos("DEF-thigh." + s) - wpos("foot_ik." + s)
        need = max(need, v.z - math.sqrt(max(0.0, (PLANT_REACH * LEG[s]) ** 2 - v.x ** 2 - v.y ** 2)))
log("%s: feet moved L %+.3f R %+.3f rig m; hips must drop %.4f rig m (%.0f mm) to keep the knees bent" % (ACTION, SHIFT["L"], SHIFT["R"], need, need * 1800))
# pass 2: constant torso drop
if need > 1e-4:
    for f in range(f0, f1 + 1):
        scene.frame_set(f); update()
        pbs["torso"].location.z -= need; update(); key("torso", f)
scene.frame_set(f0); update()
for s in "LR":
    th = (wpos("DEF-shin." + s) - wpos("DEF-thigh." + s)).normalized(); sh = (wpos("DEF-foot." + s) - wpos("DEF-shin." + s)).normalized()
    log("   %s foot y %+.3f (rig), knee %.0f deg at frame %d" % (s, wpos("DEF-foot." + s).y, 180 - math.degrees(th.angle(sh)), f0))
if SAVE:
    bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath, compress=True); log("saved")
