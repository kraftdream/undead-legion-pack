"""Export to the Epic-skeleton Unreal project (skeletons_ue_epic): models and clips on the UE5 mannequin's bone set.

Model (run in a character file):
    blender -b SkeletonKnight/prod.blend -P tools/export_epic.py --
  -> Export_UE_Epic/Characters/<Character>/SK_<Character>.fbx (the skeleton + Body) and
     Export_UE_Epic/Armor/<Character>/SK_<Character>_<Module>.fbx per armour module, in centimetres,
     plus Export_UE_Epic/frames.json (the hand / head / weapon-socket frames the editor-side socket and eye
     placement needs).
Clip (run in Animations/skeleton_anim.blend):
    blender -b Animations/skeleton_anim.blend -P tools/export_epic.py -- --clip Walk_Fwd_01 [--lift 0.015]
  -> Export_UE_Epic/Animations/Skeleton@Walk_Fwd_01.fbx (rig only, one take).

The target skeleton is Rig/epic_skeleton.json (tools/epic_skeleton.py): the mannequin's 89 bones with our
directions and proportions, plus jaw_01/02 and pelvis_l/r. Every target bone is RIGID with one DEF bone of
the Rigify rig (`source`), so a clip is written frame by frame as
    W_target(f) = W_source(f) . W_source(rest)^-1 . W_target(rest)
and nothing deforms differently from the Unity export on our own clips; the split spine, the twist bones
and the ik bones ride their source bones. Only `root` (travel + yaw, from Rigify's `root`) and `pelvis`
keep location keys; the lift goes on root Z.

Weights: a DEF bone's vertex group becomes its target's; the three spine bones' weights are split among
the five spine bones by the vertex's station along the bone, and a share of each upper arm / forearm /
thigh / shin weight goes to that bone's two twist bones by station (a hat function between the bone's
head, the two twist stations and its tail), so mannequin animations twist the limbs the way they do on
the mannequin while our own clips, which carry the twist on the bone itself, deform exactly as before.

Blender frames come from the Unreal ones through the pipeline map verified on the current export:
x_b = M(x_ue), y_b = -M(y_ue), z_b = M(z_ue), head_b = M(pos_ue) / 180, with M = (x, y, z) -> (x, -y, z).
Blender's FBX exporter (primary Y, secondary X, -Z forward / Y up) then lands them in Unreal as given.
"""
import bpy, json, os, sys, math
from mathutils import Matrix, Vector, Quaternion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import export_fbx as X

OUT = os.path.join(ROOT, "Export_UE_Epic")
SCALE = 180.0                 # Blender rig metres -> cm (1.8 x 100)
MAX_INFLUENCES = 8
SPEC = json.load(open(os.path.join(ROOT, "Rig", "epic_skeleton.json")))
BONES = SPEC["bones"]
BY = {b["name"]: b for b in BONES}
X.UNREAL = True               # cm units in the FBX writer
X.SCALE = SCALE
X.LIFT_UNIT = 100.0
log = X.log


def Mv(v):
    return Vector((v[0], -v[1], v[2]))


def blender_rest(b):
    """The target bone's rest matrix in Blender armature space (metres)."""
    x = Mv(b["x"]); y = -Mv(b["y"]); z = Mv(b["z"]); p = Mv(b["pos"]) / SCALE
    return Matrix(((x.x, y.x, z.x, p.x), (x.y, y.y, z.y, p.y), (x.z, y.z, z.z, p.z), (0, 0, 0, 1)))


def ue_old_frame(bone):
    """A DEF bone's frame in Unreal space as the CURRENT (Mixamo) export has it: for the socket / eye carry-over."""
    m = bone.matrix_local
    x, y, z, p = (Vector(m.col[i][:3]) for i in range(4))
    ux, uy, uz = Mv(x), -Mv(y), Mv(z)
    return {"x": list(ux), "y": list(uy), "z": list(uz), "pos": list(Mv(p) * SCALE)}


def build_rig():
    """The target armature from the spec (no constraints)."""
    arm = bpy.data.armatures.new(X.RIG_NODE)
    rig = bpy.data.objects.new(X.RIG_NODE, arm)
    bpy.context.scene.collection.objects.link(rig)
    rig.matrix_world = Matrix.Identity(4)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    src = bpy.data.objects[X.SRC_RIG]
    for b in BONES:
        m = blender_rest(b)
        y = Vector(m.col[1][:3]); p = Vector(m.col[3][:3])
        ln = 0.05
        if b["kind"] in ("bone", "extra") and b["source"] in src.data.bones:
            sb = src.data.bones[b["source"]]
            ln = max(0.02, (sb.tail_local - sb.head_local).length)
        e = arm.edit_bones.new(b["name"])
        e.head = p; e.tail = p + y * ln
        e.matrix = m
    for b in BONES:
        if b["parent"]:
            arm.edit_bones[b["name"]].parent = arm.edit_bones[b["parent"]]
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    # verify the rest frames survived the edit-bone round trip
    worst = 0.0
    for b in BONES:
        m = rig.data.bones[b["name"]].matrix_local
        want = blender_rest(b)
        worst = max(worst, max(abs(m[i][j] - want[i][j]) for i in range(3) for j in range(4)))
    assert worst < 1e-4, "rest frame drift %.2e" % worst
    log("epic rig: %d bones (rest frames exact to %.1e)" % (len(arm.bones), worst))
    return rig


# ------------------------------------------------------------------ weights

def station(v, head, dirn, length):
    return max(0.0, min(1.0, (v - head).dot(dirn) / length))


def remap_weights(ob, src):
    """Rewrite the vertex groups from DEF names to the target bones (spine split, twist shares)."""
    one = {}                                  # DEF -> target (1:1)
    for b in BONES:
        if b["kind"] in ("bone", "extra") and b["source"] not in one:
            one[b["source"]] = b["name"]
    split = {s: sorted((st, n) for st, n in v) for s, v in SPEC["weights"]["split"].items()}
    twist = {s: sorted((st, n) for st, n in v) for s, v in SPEC["weights"]["twist"].items()}
    geo = {}
    for s in list(split) + list(twist):
        sb = src.data.bones[s]
        h = Vector(sb.head_local); t = Vector(sb.tail_local)
        geo[s] = (h, (t - h).normalized(), (t - h).length)
    old = {g.index: g.name for g in ob.vertex_groups}
    new_w = []                                # per vertex: {target: w}
    unknown = set()
    for v in ob.data.vertices:
        w = {}
        for g in v.groups:
            name = old[g.group]; wt = g.weight
            if wt <= 0 or not name.startswith("DEF-"):
                continue
            if name in split:
                h, d, L = geo[name]; s = station(v.co, h, d, L)
                target = one.get(name)         # pelvis below the first split station, else the split bone
                for st, n in split[name]:
                    if s >= st or target is None:
                        target = n
                w[target] = w.get(target, 0.0) + wt
            elif name in twist:
                h, d, L = geo[name]; s = station(v.co, h, d, L)
                (sa, na), (sb_, nb) = twist[name]
                base = one[name]
                if s <= sa:
                    shares = {base: 1 - s / sa, na: s / sa}
                elif s <= sb_:
                    shares = {na: (sb_ - s) / (sb_ - sa), nb: (s - sa) / (sb_ - sa)}
                else:
                    shares = {nb: 1.0}
                for n, sh in shares.items():
                    if sh > 1e-4:
                        w[n] = w.get(n, 0.0) + wt * sh
            elif name in one:
                w[one[name]] = w.get(one[name], 0.0) + wt
            else:
                unknown.add(name)
        new_w.append(w)
    assert not unknown, "no target for vertex groups %s" % sorted(unknown)
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    groups = {}
    for b in BONES:
        groups[b["name"]] = ob.vertex_groups.new(name=b["name"])
    used = set()
    for v, w in zip(ob.data.vertices, new_w):
        for n, wt in w.items():
            groups[n].add([v.index], wt, 'REPLACE'); used.add(n)
    for n, g in list(groups.items()):
        if n not in used:
            ob.vertex_groups.remove(g)
    return len(used)


def build_mesh(src_ob, rig, src, name):
    ob = bpy.data.objects.new(name, src_ob.data.copy())
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = Matrix.Identity(4)
    ob.data.transform(src_ob.matrix_world)
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    n = remap_weights(ob, src)
    ob.modifiers.new("Armature", 'ARMATURE').object = rig
    flipped = X.fix_normals(ob)
    X.MAX_INFLUENCES = MAX_INFLUENCES
    cut = X.limit_influences(ob)
    ob.data.transform(Matrix.Scale(SCALE, 4))
    log("  mesh %-10s %6d v  %d bones%s%s" % (name, len(ob.data.vertices), n,
        ("  %d verts cut to %d influences" % (cut, MAX_INFLUENCES)) if cut else "", ("  %d faces re-wound" % flipped) if flipped else ""))
    return ob


def write_frames(src):
    """hand / head / weapon-socket frames, old (Mixamo export) and new (Epic), for the editor-side steps."""
    out = {}
    for name in ("DEF-hand.L", "DEF-hand.R", "DEF-spine.006", "DEF-weapon.L", "DEF-weapon.R"):
        out[name] = {"old": ue_old_frame(src.data.bones[name])}
    for t in ("hand_l", "hand_r", "head"):
        b = BY[t]; out[t] = {"new": {"x": b["x"], "y": b["y"], "z": b["z"], "pos": b["pos"]}}
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, "frames.json"), "w"), indent=1)


def export_model():
    character = os.path.basename(os.path.dirname(bpy.data.filepath))
    out_dir = os.path.join(OUT, "Characters", character); armor_dir = os.path.join(OUT, "Armor", character)
    src, meta = X.source_rig()
    for pb in src.pose.bones:
        pb.matrix_basis.identity()
    src.data.pose_position = 'REST'
    sources = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("WGT")
               and any(m.type == 'ARMATURE' and m.object == src for m in o.modifiers)]
    sources.sort(key=lambda o: (o.name != "Body", o.name))
    assert sources and sources[0].name == "Body", [o.name for o in sources]
    log(character, "-", len(sources), "skinned meshes:", [o.name for o in sources])
    names = [o.name for o in sources]
    X.park_names(names)
    rig = build_rig()
    meshes = [build_mesh(o, rig, src, n) for o, n in zip(sources, names)]
    X.scale_rig(rig)
    top = max(v.co.z for v in meshes[0].data.vertices)
    log("scale x%.0f -> pelvis at %.1f cm, Body top at %.1f cm" % (SCALE, rig.data.bones["pelvis"].head_local.z, top))
    X.fbx(os.path.join(out_dir, "SK_%s.fbx" % character), [rig, meshes[0]], False, False)
    for mesh, n in zip(meshes[1:], names[1:]):
        X.fbx(os.path.join(armor_dir, "SK_%s_%s.fbx" % (character, n)), [rig, mesh], False, False)
    write_frames(src)
    log(character, "- body-only model + %d armour modules in %s" % (len(meshes) - 1, os.path.relpath(armor_dir, ROOT)))


# -------------------------------------------------------------------- clips

def yaw_matrix(m):
    """Translation + Z-only rotation of an armature-space matrix (Rigify's root lies flat along +Y)."""
    y = Vector(m.col[1][:3]); y.z = 0
    if y.length < 1e-6:
        y = Vector((0, 1, 0))
    ang = math.atan2(y.x, y.y)               # rotation about Z that turns +Y onto the root's Y
    r = Matrix.Rotation(-ang, 4, 'Z')
    r.translation = m.translation
    return r


def export_clip(clip, lift):
    if not X.clip_enabled(clip):
        log("skipped %s: disabled in Animations/clips.json" % clip)
        return
    scene = bpy.context.scene
    assert abs(scene.render.fps / scene.render.fps_base - X.FPS) < 1e-6
    src, meta = X.source_rig()
    act = bpy.data.actions.get(clip)
    assert act is not None, "no action named %r" % clip
    for pb in src.pose.bones:
        pb.ik_stretch = 0.0
    src.animation_data_create()
    ad_ = src.animation_data
    for t_ in ad_.nla_tracks:
        t_.mute = True
    ad_.action = act
    ad_.action_blend_type = 'REPLACE'; ad_.action_influence = 1.0; ad_.action_extrapolation = 'HOLD'
    if hasattr(ad_, "action_slot") and act.slots:
        ad_.action_slot = act.slots[0]
    f0, f1 = (int(round(x)) for x in act.frame_range)
    scene.frame_start, scene.frame_end = f0, f1
    log("clip %s: frames %d..%d (%.2f s)" % (clip, f0, f1, (f1 - f0) / X.FPS))
    X.park_names(["Body"])
    rig = build_rig()
    rest = {b["name"]: rig.data.bones[b["name"]].matrix_local.copy() for b in BONES}
    rest_inv = {n: m.inverted() for n, m in rest.items()}
    src_rest_inv = {}
    for b in BONES:
        s = b["source"]
        if s != "root" and s not in src_rest_inv:
            src_rest_inv[s] = src.data.bones[s].matrix_local.inverted()
    offset = {b["name"]: (src_rest_inv[b["source"]] @ rest[b["name"]]) if b["source"] != "root" else rest[b["name"]] for b in BONES}
    rig.animation_data_create()
    baked = bpy.data.actions.new(clip)
    rig.animation_data.action = baked
    keep_loc = ("root", "pelvis")
    pbs = {b["name"]: rig.pose.bones[b["name"]] for b in BONES}
    for f in range(f0, f1 + 1):
        scene.frame_set(f); bpy.context.view_layer.update()
        W = {}
        root_w = yaw_matrix(src.pose.bones["root"].matrix)
        for b in BONES:
            if b["source"] == "root":
                W[b["name"]] = root_w @ offset[b["name"]]
            else:
                W[b["name"]] = src.pose.bones[b["source"]].matrix @ offset[b["name"]]
        for b in BONES:
            n = b["name"]
            if b["parent"]:
                basis = rest_inv[n] @ rest[b["parent"]] @ W[b["parent"]].inverted() @ W[n]
            else:
                basis = rest_inv[n] @ W[n]
            loc, rot, sca = basis.decompose()
            pb = pbs[n]
            pb.rotation_quaternion = rot
            pb.keyframe_insert("rotation_quaternion", frame=f)
            if n in keep_loc:
                pb.location = loc
                pb.keyframe_insert("location", frame=f)
    scene.frame_set(f0)
    n = X.scale_rig(rig, baked)
    root_fc = [fc for fc in X.fcurves(baked) if fc.data_path == 'pose.bones["root"].location']
    lift *= X.LIFT_UNIT
    if lift:
        for fc in root_fc:
            if fc.array_index == 2:            # the root's local Z is world up (identity frame)
                for kp in fc.keyframe_points:
                    kp.co.y += lift; kp.handle_left.y += lift; kp.handle_right.y += lift
        log("lifted root by %.2f cm" % lift)
    travel = [fc.evaluate(f1) - fc.evaluate(f0) for fc in sorted(root_fc, key=lambda f: f.array_index)]
    log("keyed %d bones over %d frames; root travel (Blender XYZ, cm): %s" % (len(BONES), f1 - f0 + 1, [round(t, 2) for t in travel]))
    scene.name = clip
    X.park_on_rest(rig, f0 - 1)
    X.fbx(os.path.join(OUT, "Animations", "%s@%s.fbx" % (X.CLIP_PREFIX, clip)), [rig], True, False)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--clip" in argv:
        lift = float(argv[argv.index("--lift") + 1]) if "--lift" in argv else X.CLIP_LIFT
        export_clip(argv[argv.index("--clip") + 1], lift)
    else:
        export_model()


if __name__ == "__main__":
    main()
