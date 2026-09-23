"""Compare a built clip against its source capture joint by joint: is the bone mapping right?

    blender -b Animations/skeleton_anim.blend -P tools/retarget_compare.py -- --src "External Anims/Kimodo/attack_ref4_arm.blend" \
        --clip Attack_L_Slice --src-begin 152 --src-end 190 --time-scale 0.7692 [--mirror] [--rename ue5] [--render DIR]

For every output frame the matching source frame is posed, the source's joint positions are taken
RELATIVE TO ITS PELVIS, scaled by the hip-height ratio (as the retarget scales) and yawed so its
shoulder line matches the rig's (the retarget's heading removal), then compared with the rig's
DEF joints relative to its hips. Prints per joint the mean and max distance in ENGINE centimetres
(rig m x 1.8), and the joint's travel so a small error on a joint that moves a lot reads as a
match. With --render, the Knight is rendered from the front and the side at a few frames with
RED spheres at the source's joint positions: where a sphere sits off its bone, the mapping (or a
retarget pass) moved that joint away from the capture.
"""
import bpy, sys, os, math
from mathutils import Vector, Matrix, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(k, d=None): return argv[argv.index(k) + 1] if k in argv else d
SRC = os.path.abspath(arg("--src")); CLIP = arg("--clip"); SB = int(arg("--src-begin", "0")); SE = int(arg("--src-end", "-1"))
TS = float(arg("--time-scale", "1.0")); MIRROR = "--mirror" in argv; RENDER = arg("--render", ""); RENAME = arg("--rename", "ue5")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
TABLES = {
    "ue5": {"pelvis": "Hips", "spine_05": "Chest", "head": "Head", "upperarm_l": "LeftArm", "lowerarm_l": "LeftForeArm", "hand_l": "LeftHand",
            "upperarm_r": "RightArm", "lowerarm_r": "RightForeArm", "hand_r": "RightHand", "thigh_l": "LeftLeg", "calf_l": "LeftShin", "foot_l": "LeftFoot",
            "thigh_r": "RightLeg", "calf_r": "RightShin", "foot_r": "RightFoot"},
    "jnt": {"hips_JNT": "Hips", "spine2_JNT": "Chest", "head_JNT": "Head", "l_arm_JNT": "LeftArm", "l_forearm_JNT": "LeftForeArm", "l_hand_JNT": "LeftHand",
            "r_arm_JNT": "RightArm", "r_forearm_JNT": "RightForeArm", "r_hand_JNT": "RightHand", "l_upleg_JNT": "LeftLeg", "l_leg_JNT": "LeftShin", "l_foot_JNT": "LeftFoot",
            "r_upleg_JNT": "RightLeg", "r_leg_JNT": "RightShin", "r_foot_JNT": "RightFoot"},
}
RIG = {"Hips": "DEF-spine", "Chest": "DEF-spine.003", "Head": "DEF-spine.006", "LeftArm": "DEF-upper_arm.L", "LeftForeArm": "DEF-forearm.L", "LeftHand": "DEF-hand.L",
       "RightArm": "DEF-upper_arm.R", "RightForeArm": "DEF-forearm.R", "RightHand": "DEF-hand.R", "LeftLeg": "DEF-thigh.L", "LeftShin": "DEF-shin.L", "LeftFoot": "DEF-foot.L",
       "RightLeg": "DEF-thigh.R", "RightShin": "DEF-shin.R", "RightFoot": "DEF-foot.R"}
table = {v: k for k, v in TABLES[RENAME].items()}     # generic -> source joint name

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
scene = bpy.context.scene; pbs = rig.pose.bones
# the source armature
if SRC.lower().endswith(".blend"):
    with bpy.data.libraries.load(SRC, link=False) as (a, b): b.objects = list(a.objects)
    src = next(o for o in b.objects if o and o.type == 'ARMATURE'); scene.collection.objects.link(src)
else:
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=SRC)
    src = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o not in before)
bpy.context.view_layer.update()
spb = src.pose.bones
def S(name, fr):
    scene.frame_set(fr); return (src.matrix_world @ spb[table[name]].matrix).translation.copy()
def R(name, fr):
    scene.frame_set(fr); return (rig.matrix_world @ pbs[RIG[name]].matrix).translation.copy()
def mirror_name(n):
    return "Right" + n[4:] if n.startswith("Left") else "Left" + n[5:] if n.startswith("Right") else n

# scale: rest hips height ratio (what the retarget uses)
hip_t = (rig.matrix_world @ rig.data.bones["DEF-spine"].matrix_local).translation.z
hip_s = (src.matrix_world @ src.data.bones[table["Hips"]].matrix_local).translation.z
scale = hip_t / hip_s
act = bpy.data.actions[CLIP]; n_out = int(act.frame_range[1])
joints = [j for j in RIG if j != "Hips"]
errs = {j: [] for j in joints}; travel = {j: 0.0 for j in joints}; prev_r = {}
frames = []
for f in range(1, n_out + 1):
    fs = SB + (f - 1) / TS
    if SE >= 0 and fs > SE + 0.5: break
    fs_i = int(round(fs)); frames.append((f, fs_i))
    # source joints relative to the pelvis, scaled, mirrored
    rig.animation_data.action = act
    sp = {}
    for j in RIG:
        p = (S(mirror_name(j) if MIRROR else j, fs_i) - S("Hips", fs_i)) * scale
        if MIRROR: p = Vector((-p.x, p.y, p.z))
        sp[j] = p
    rp = {j: R(j, f) - R("Hips", f) for j in RIG}
    # yaw the source so its shoulder line matches the rig's
    ds = sp["LeftArm"] - sp["RightArm"]; dr = rp["LeftArm"] - rp["RightArm"]
    yaw = math.atan2(dr.y, dr.x) - math.atan2(ds.y, ds.x)
    Rz = Matrix.Rotation(yaw, 3, 'Z')
    for j in joints:
        e = (Rz @ sp[j] - rp[j]).length * 1.8 * 100.0
        errs[j].append(e)
        if j in prev_r: travel[j] += (rp[j] - prev_r[j]).length * 1.8 * 100.0
        prev_r[j] = rp[j]
    if RENDER and f in (1, max(1, n_out // 4), n_out // 2, 3 * n_out // 4, n_out):
        pass
print("[compare] %s vs %s frames %d..%d (%d output frames), scale %.3f, %s" % (CLIP, os.path.basename(SRC), SB, SE, len(frames), scale, "mirrored" if MIRROR else "as is"))
print("[compare] %-14s %8s %8s %10s" % ("joint", "mean cm", "max cm", "travel cm"))
for j in joints:
    print("[compare] %-14s %8.1f %8.1f %10.0f" % (j, sum(errs[j]) / len(errs[j]), max(errs[j]), travel[j]))
worst = max(joints, key=lambda j: sum(errs[j]) / len(errs[j]))
print("[compare] worst joint: %s" % worst)
# bone DIRECTIONS (proportion-free): the angle between the source's bone direction (yawed) and the rig's
BONES = [("Spine", "Hips", "Chest"), ("Neck", "Chest", "Head"), ("L upper arm", "LeftArm", "LeftForeArm"), ("L forearm", "LeftForeArm", "LeftHand"),
         ("R upper arm", "RightArm", "RightForeArm"), ("R forearm", "RightForeArm", "RightHand"), ("L thigh", "LeftLeg", "LeftShin"), ("L shin", "LeftShin", "LeftFoot"),
         ("R thigh", "RightLeg", "RightShin"), ("R shin", "RightShin", "RightFoot")]
dang = {b[0]: [] for b in BONES}
for f, fs_i in frames:
    sp = {}
    for j in RIG:
        p = S(mirror_name(j) if MIRROR else j, fs_i)
        if MIRROR: p = Vector((-p.x, p.y, p.z))
        sp[j] = p
    rig.animation_data.action = act
    rp = {j: R(j, f) for j in RIG}
    ds = sp["LeftArm"] - sp["RightArm"]; dr = rp["LeftArm"] - rp["RightArm"]
    Rz = Matrix.Rotation(math.atan2(dr.y, dr.x) - math.atan2(ds.y, ds.x), 3, 'Z')
    for name, a, b in BONES:
        vs = Rz @ (sp[b] - sp[a]); vr = rp[b] - rp[a]
        if vs.length > 1e-6 and vr.length > 1e-6: dang[name].append(math.degrees(vs.angle(vr)))
print("[compare] bone directions, source vs rig (deg): " + "; ".join("%s mean %.0f max %.0f" % (n, sum(v) / len(v), max(v)) for n, v in dang.items() if v))

if RENDER:
    os.makedirs(RENDER, exist_ok=True)
    # red spheres at the source positions (in the rig's frame), the Knight rendered around them
    mat = bpy.data.materials.new("SrcJoint"); mat.diffuse_color = (1, 0.05, 0.05, 1)
    spheres = {}
    for j in joints:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.012); ob = bpy.context.active_object; ob.name = "Src_" + j; ob.data.materials.append(mat); spheres[j] = ob
    scene.render.engine = 'BLENDER_WORKBENCH'; scene.display.shading.light = 'STUDIO'; scene.display.shading.color_type = 'MATERIAL'
    scene.render.resolution_x = 500; scene.render.resolution_y = 700; scene.render.film_transparent = False
    cam = bpy.data.objects.new("CmpCam", bpy.data.cameras.new("CmpCam")); scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 50
    picks = sorted(set([1, max(1, n_out // 4), max(1, n_out // 2), max(1, 3 * n_out // 4), n_out]))
    for f in picks:
        fs_i = SB + int(round((f - 1) / TS))
        sp = {}
        for j in RIG:
            p = (S(mirror_name(j) if MIRROR else j, fs_i) - S("Hips", fs_i)) * scale
            if MIRROR: p = Vector((-p.x, p.y, p.z))
            sp[j] = p
        rig.animation_data.action = act; scene.frame_set(f); bpy.context.view_layer.update()
        hips_r = R("Hips", f); rp = {j: R(j, f) - hips_r for j in RIG}
        ds = sp["LeftArm"] - sp["RightArm"]; dr = rp["LeftArm"] - rp["RightArm"]
        Rz = Matrix.Rotation(math.atan2(dr.y, dr.x) - math.atan2(ds.y, ds.x), 3, 'Z')
        for j in joints: spheres[j].location = hips_r + Rz @ sp[j]
        for view, pos in (("front", Vector((0, -2.6, 0.55))), ("side", Vector((2.6, 0, 0.55)))):
            cam.location = pos; cam.rotation_euler = (Vector((0, 0, 0.55)) - pos).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = os.path.join(RENDER, "%s_f%02d_%s.png" % (CLIP, f, view)); bpy.ops.render.render(write_still=True)
    print("[compare] rendered %d frames x 2 views to %s" % (len(picks), RENDER))
