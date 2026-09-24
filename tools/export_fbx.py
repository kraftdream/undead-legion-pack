"""Shared Rigify rig -> clean Mixamo-named skeleton -> FBX, for models and clips.

Model (run in a character file):
    blender -b SkeletonKnight/prod.blend -P tools/export_fbx.py -- [--out DIR] [--bst 0|1]
  -> skeletons/Assets/UndeadLegion/Models/<Character>/SK_<Character>.fbx : the deform
     skeleton under Armature/Root plus every skinned mesh (Body + armour modules) as
     SIBLING nodes of the armature, at SCALE x the Blender metres, no animation.

Clip (run in Animations/skeleton_anim.blend):
    blender -b Animations/skeleton_anim.blend -P tools/export_fbx.py -- --clip Walk_Fwd [--out DIR] [--lift 0.018]
  -> skeletons/Assets/UndeadLegion/Animations/Skeleton@Walk_Fwd.fbx : the same skeleton,
     no mesh, one baked take named after the clip, plus an EMPTY node called `Body` so
     the node paths match the model files (see below).

Nothing is ever saved back to the .blend.

Why a rebuilt skeleton (inherited from the creatures pack, see smp-10-rgp-creatures
tools/goblin_export.py):
  * "Only Deform Bones" is wrong for Rigify: DEF-thigh hangs off ORG-spine, so the
    tickbox drops parents and you get a flat skeleton. Anatomy comes from the METARIG.
  * Mixamo names: Unity's Humanoid auto-mapper takes them cleanly and buyers can drop
    any Mixamo/humanoid clip on the rig.
  * Copy each bone's WHOLE rest matrix (roll included) or every posed frame skins wrong.
  * `Root` points UP (+Z here = +Y in the engine); Rigify's `root` lies flat. Root takes
    the source root's location and Z-only rotation, so travel and yaw land on `Root`
    (CLAUDE.md 8: root motion decision) and Unreal extracts them from the root bone.
  * Meshes are siblings of the armature, not children. Unity renames an FBX's SINGLE
    root node after the file but keeps names when there are two or more roots. A model
    file has Armature + meshes (many roots); a rig-only clip file would have ONE root
    and be renamed, the bone paths would disagree, and "Copy From Other Avatar" yields
    ZERO clips silently. Clip files therefore carry an empty node named `Body`.
  * Scale: bones are built at Blender scale, the clip is baked there, then edit bones
    and every location key are multiplied by SCALE. Rotations are scale-invariant.
  * bake_space_transform=True (default): measured in Unity 6000.4, both settings give
    the same valid Humanoid avatar, but only True leaves every SkinnedMeshRenderer
    node at identity rotation, which the Asset Store validator's "Check Model
    Orientation" wants. The Armature node keeps its -90 deg X either way.
"""
import bpy, json, os, sys, math
from mathutils import Matrix, Vector, Quaternion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_RIG, METARIG = "RIG-Meta-Rig", "Meta-Rig"
RIG_NODE = "Armature"       # one child (Root) -> Unreal strips it, Unity keeps it; same in every file
CLIP_PREFIX = "Skeleton"    # Skeleton@<Clip>.fbx
SCALE = 1.8                 # source art is ~0.94 m; the Unity demo established 1.8x (CLAUDE.md 7)
FPS = 30
MAX_INFLUENCES = 4
# Ground clearance baked into every clip's Root (engine metres). The boots' soles sit
# 4-8 mm below the bare foot and Unity's humanoid playback lets the feet dip a few mm,
# so an exact-floor clip reads as sinking. A lift on the prefab's Armature node does
# NOT work for a Humanoid: Unity positions the hips from the avatar root and ignores
# the child offset while a clip plays (measured: 13.6 mm of lift moved the mesh 2 mm).
# Measured raw penetration 2026-09-19, all six models, three idles: worst -10.9 mm.
CLIP_LIFT = 0.015
UNITY = os.path.join(ROOT, "skeletons", "Assets", "UndeadLegion")

_SPINE = {"spine": "Hips", "spine.001": "Spine", "spine.002": "Spine1", "spine.003": "Spine2",
          "spine.004": "Neck", "spine.005": "Neck1", "spine.006": "Head"}
_LIMB = {"shoulder": "Shoulder", "upper_arm": "Arm", "forearm": "ForeArm", "hand": "Hand",
         "thigh": "UpLeg", "shin": "Leg", "foot": "Foot", "toe": "ToeBase", "pelvis": "Pelvis",
         "weapon": "WeaponSocket"}
_HAND = {"thumb": "HandThumb", "f_index": "HandIndex", "f_middle": "HandMiddle",
         "f_ring": "HandRing", "f_pinky": "HandPinky", "palm": "HandPalm"}
_HEAD = {"lowerjaw": "Jaw"}


def log(*a):
    print("[export]", *a); sys.stdout.flush()


def game_name(def_name):
    """DEF-f_index.02.L -> LeftHandIndex2, DEF-spine.004 -> Neck, root -> Root."""
    if def_name == "root":
        return "Root"
    n = def_name[4:] if def_name.startswith("DEF-") else def_name
    if n in _SPINE:
        return _SPINE[n]
    side = "Left" if n.endswith(".L") else "Right" if n.endswith(".R") else ""
    core = n[:-2] if side else n
    parts = core.split(".")
    stem, idx = parts[0], ""
    for p in parts[1:]:
        if p.isdigit():
            idx = str(int(p) + (0 if stem in _HAND else 1))  # thumb.01 -> 1 ; lowerjaw.001 -> 2
    if stem in _LIMB:
        return side + _LIMB[stem]
    if stem in _HAND:
        return side + _HAND[stem] + (idx or "1")
    if stem in _HEAD:
        return side + _HEAD[stem] + (idx if idx and idx != "1" else "")
    raise RuntimeError("no game name for bone " + def_name)


def deform_parent_map(src, meta):
    """Deform bone -> parent deform bone, resolved through the metarig's anatomy."""
    defs = [b.name for b in src.data.bones if b.use_deform]
    defset = set(defs)
    out = {}
    for n in defs:
        mb = meta.data.bones.get(n[4:])
        assert mb is not None, "metarig has no bone for " + n
        p = mb.parent
        while p is not None and ("DEF-" + p.name) not in defset:
            p = p.parent
        out[n] = ("DEF-" + p.name) if p else "root"
    return out


def name_report(src):
    seen = {}
    for b in src.data.bones:
        if b.use_deform:
            seen.setdefault(game_name(b.name), []).append(b.name)
    dup = {k: v for k, v in seen.items() if len(v) > 1}
    if dup:
        raise RuntimeError("name collision: %s" % dup)
    req = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head"]
    for s in ("Left", "Right"):
        req += [s + x for x in ("Shoulder", "Arm", "ForeArm", "Hand", "UpLeg", "Leg", "Foot",
                                "ToeBase", "WeaponSocket")]
    miss = [r for r in req if r not in seen]
    if miss:
        raise RuntimeError("required bones missing: %s" % miss)
    log("%d deform bones -> %d names; all %d required bones present" % (len(seen), len(seen), len(req)))
    return seen


def fcurves(action):
    """Blender 5 slotted actions have no action.fcurves; walk the channelbags."""
    if getattr(action, "layers", None):
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    yield from cb.fcurves
    elif hasattr(action, "fcurves"):
        yield from action.fcurves


# ------------------------------------------------------------------- the rig

def build_game_rig(src, meta, constrain):
    """Root + the deform bones, Mixamo-named, at Blender scale.

    constrain=True adds the constraints that make the game rig follow the source
    (for baking a clip): every bone COPY_TRANSFORMS in WORLD space from its DEF bone,
    Root COPY_LOCATION + Z-only COPY_ROTATION from `root`.
    """
    pmap = deform_parent_map(src, meta)
    arm = bpy.data.armatures.new(RIG_NODE)
    rig = bpy.data.objects.new(RIG_NODE, arm)
    bpy.context.scene.collection.objects.link(rig)
    rig.matrix_world = Matrix.Identity(4)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones.new("Root")
    eb.head, eb.tail, eb.roll = (0, 0, 0), (0, 0, 0.2), 0.0
    order = [b.name for b in src.data.bones if b.use_deform]
    for n in order:
        sb = src.data.bones[n]
        e = arm.edit_bones.new(game_name(n))
        e.head = sb.head_local.copy(); e.tail = sb.tail_local.copy()
        e.matrix = sb.matrix_local.copy()          # roll included
    for n in order:
        p = pmap[n]
        arm.edit_bones[game_name(n)].parent = arm.edit_bones["Root" if p == "root" else game_name(p)]
    bpy.ops.object.mode_set(mode='OBJECT')
    roots = sorted(game_name(n) for n, p in pmap.items() if p == "root")
    assert roots == ["Hips"], roots
    if constrain:
        pb = rig.pose.bones["Root"]
        c = pb.constraints.new('COPY_LOCATION'); c.target, c.subtarget = src, "root"
        c = pb.constraints.new('COPY_ROTATION'); c.target, c.subtarget = src, "root"
        c.use_x = c.use_y = False
        for n in order:
            c = rig.pose.bones[game_name(n)].constraints.new('COPY_TRANSFORMS')
            c.target, c.subtarget = src, n
            c.target_space = c.owner_space = 'WORLD'
    log("game rig: %d bones%s" % (len(arm.bones), ", constrained to source" if constrain else ""))
    return rig


LEG_BONES = ("LeftUpLeg", "LeftLeg", "RightUpLeg", "RightLeg")
FOOT_BONES = ("LeftFoot", "LeftToeBase", "RightFoot", "RightToeBase")


def detwist_legs(rig, f0, f1):
    """Strip the axial twist Rigify's IK bakes into the thigh and shin, per frame.

    Unity's Humanoid muscle space does not carry that twist: the SAME clip played as
    Generic kept the feet within 3 mm of the floor, played as Humanoid it put the ankle
    2.5 cm lower with identical hips (Idle_02, 2026-09-19). Swing-twist decomposition
    about each bone's rest axis; dropping the twist keeps the bone DIRECTION, so knee
    and ankle positions do not move, and the foot is put back on its baked world pose.
    Ported from smp-10-rgp-creatures tools/export_fbx.py (_detwist_legs), whose note
    still applies: snapshot every world matrix BEFORE editing any of them.
    """
    scene = bpy.context.scene
    rest = {b: rig.data.bones[b].matrix_local.to_3x3() for b in LEG_BONES}
    axes = {b: (Vector(rig.data.bones[b].tail_local) - Vector(rig.data.bones[b].head_local)).normalized() for b in LEG_BONES}
    for b in LEG_BONES + FOOT_BONES:
        rig.pose.bones[b].rotation_mode = 'QUATERNION'
    worst = 0.0
    for f in range(f0, f1 + 1):
        scene.frame_set(f); bpy.context.view_layer.update()
        snap = {b: rig.pose.bones[b].matrix.copy() for b in LEG_BONES + FOOT_BONES}
        targets = {}
        for bn in LEG_BONES:
            q = (snap[bn].to_3x3() @ rest[bn].inverted()).to_quaternion()
            ax = axes[bn]
            v = Vector((q.x, q.y, q.z)); p = v.dot(ax) * ax
            tw = Quaternion((q.w, p.x, p.y, p.z)); tw.normalize()
            worst = max(worst, abs(tw.angle if tw.angle <= math.pi else 2 * math.pi - tw.angle))
            M = ((q @ tw.inverted()).to_matrix() @ rest[bn]).to_4x4()
            M.translation = snap[bn].translation
            targets[bn] = M
        for bn in LEG_BONES:
            rig.pose.bones[bn].matrix = targets[bn]; bpy.context.view_layer.update()
        for b in FOOT_BONES:
            rig.pose.bones[b].matrix = snap[b]; bpy.context.view_layer.update()
        for b in LEG_BONES + FOOT_BONES:
            rig.pose.bones[b].keyframe_insert("rotation_quaternion", frame=f)
            rig.pose.bones[b].keyframe_insert("location", frame=f)
    log("legs de-twisted over %d frames (largest twist removed %.1f deg)" % (f1 - f0 + 1, math.degrees(worst)))


def park_on_rest(rig, frame):
    """Key the REST pose on `frame` (outside the exported range) and park the scene there.

    Blender's FBX exporter writes a bone node's transform from the CURRENT POSE, not
    from the armature's rest (the bind pose is only written for skinned meshes). In a
    rig-only clip file that posed frame becomes the skeleton Unity reads: re-imported,
    Idle's thigh measured 0.3816 m, the hunched Idle_02's 0.3673 m, the model's 0.3740 m.
    Unity's Humanoid conversion then works against a skeleton that is not the avatar's
    and the ankle lands up to 2.5 cm low (Generic playback was exact). With every
    channel keyed at rest on a frame before the take and the scene parked there, the
    file's skeleton is the model's.
    """
    for pb in rig.pose.bones:
        pb.matrix_basis.identity()
        pb.keyframe_insert("location", frame=frame)
        pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler", frame=frame)
        pb.keyframe_insert("scale", frame=frame)
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


KEEP_TRANSLATION = ("Root", "Hips")


def strip_bone_translation(action):
    """Drop location (and scale) curves on every bone except Root and Hips.

    The baked COPY_TRANSFORMS carry Rigify's DEF-bone stretch as per-frame bone
    translations and scales. A rig-only clip file has no bind pose, so those baked
    offsets become the SKELETON Unity reads from the file: re-imported, Idle's thigh
    read 0.3816 m at rest and the hunched Idle_02's 0.3620 m, from the same rig. Unity's
    Humanoid retarget then reconstructs the legs against a skeleton that is not the
    model's and the ankle lands 2.5 cm low (Generic playback, which copies transforms
    verbatim, was exact). Humanoid ignores bone translation anyway; only Root (travel)
    and Hips (body position) carry meaning.
    """
    removed = 0
    for fc in list(fcurves(action)):
        if not (fc.data_path.endswith(".location") or fc.data_path.endswith(".scale")):
            continue
        bone = fc.data_path.split('"')[1] if '"' in fc.data_path else ""
        if bone in KEEP_TRANSLATION:
            continue
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    try:
                        cb.fcurves.remove(fc); removed += 1
                    except (RuntimeError, ReferenceError):
                        pass
    log("stripped %d bone translation/scale curves (kept Root, Hips)" % removed)


def scale_rig(rig, action=None):
    """Multiply the rest pose and (if given) every location key by SCALE."""
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for e in rig.data.edit_bones:
        e.head = e.head * SCALE; e.tail = e.tail * SCALE   # roll is an angle: unchanged
    bpy.ops.object.mode_set(mode='OBJECT')
    n = 0
    if action is not None:
        for fc in fcurves(action):
            if fc.data_path.endswith("location"):
                for kp in fc.keyframe_points:
                    kp.co.y *= SCALE; kp.handle_left.y *= SCALE; kp.handle_right.y *= SCALE
                n += 1
    return n


# ----------------------------------------------------------------- the meshes

def limit_influences(ob):
    """Unity keeps 4 weights per vertex; do the cut and re-normalise here, deterministically."""
    n = 0
    for v in ob.data.vertices:
        gs = sorted(((g.weight, g.group) for g in v.groups if g.weight > 0), reverse=True)
        if len(gs) > MAX_INFLUENCES:
            for w, gi in gs[MAX_INFLUENCES:]:
                ob.vertex_groups[gi].remove([v.index])
            gs = gs[:MAX_INFLUENCES]; n += 1
        tot = sum(w for w, _ in gs)
        if gs and abs(tot - 1.0) > 1e-4:
            for w, gi in gs:
                ob.vertex_groups[gi].add([v.index], w / tot, 'REPLACE')
    return n


def fix_normals(ob):
    """Make every face's winding consistent with its neighbours (bmesh recalc).

    Unity culls back faces, so a face wound the wrong way is a hole. Measured in the
    sources (2026-09-19): Assassin Body 15 % of faces inconsistent, Mage Robe 31 %,
    small patches on several helms/gloves/boots. Applied to the export copy only; the
    artist files are untouched. Returns the number of faces flipped.
    """
    import bmesh
    bm = bmesh.new(); bm.from_mesh(ob.data)
    before = [f.normal.copy() for f in bm.faces]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    n = sum(1 for f, v in zip(bm.faces, before) if f.normal.dot(v) < 0)
    if n:
        bm.to_mesh(ob.data)
    bm.free()
    return n


def build_game_mesh(src_ob, rig, name):
    ob = bpy.data.objects.new(name, src_ob.data.copy())
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = Matrix.Identity(4)
    ob.data.transform(src_ob.matrix_world)          # identity after rig_sync, but be exact
    for g in ob.vertex_groups:
        if g.name.startswith("DEF-") or g.name == "root":
            g.name = game_name(g.name)
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    ob.modifiers.new("Armature", 'ARMATURE').object = rig
    flipped = fix_normals(ob)
    cut = limit_influences(ob)
    ob.data.transform(Matrix.Scale(SCALE, 4))
    log("  mesh %-10s %6d v  %s%s" % (name, len(ob.data.vertices),
                                      ("%d verts cut to %d influences  " % (cut, MAX_INFLUENCES)) if cut else "",
                                      ("%d faces re-wound" % flipped) if flipped else ""))
    return ob


# --------------------------------------------------------------------- export

def park_names(names):
    """Free the given object names so the export copies can take them (file is never saved)."""
    for o in bpy.data.objects:
        if o.name in names:
            o.hide_viewport = False; o.hide_set(False)
            o.name = "__src_" + o.name


def fbx(path, objs, bake_anim, bake_space_transform, frame_range=None):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kw = dict(
        filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH', 'EMPTY'},
        apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z', axis_up='Y', bake_space_transform=bake_space_transform,
        use_mesh_modifiers=True, mesh_smooth_type='OFF', use_tspace=False,
        add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
        use_armature_deform_only=False, armature_nodetype='NULL',
        bake_anim=bake_anim, path_mode='AUTO', embed_textures=False, use_custom_props=False)
    if bake_anim:
        kw.update(bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                  bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
                  bake_anim_step=1.0, bake_anim_simplify_factor=0.0)
    bpy.ops.export_scene.fbx(**kw)
    log("wrote", os.path.relpath(path, ROOT), "%d KB" % (os.path.getsize(path) // 1024))


def source_rig():
    src, meta = bpy.data.objects[SRC_RIG], bpy.data.objects[METARIG]
    if bpy.context.mode != 'OBJECT':          # the anim file may be saved in pose mode
        bpy.ops.object.mode_set(mode='OBJECT')
    assert src.matrix_world == Matrix.Identity(4), "source rig must be at identity"
    return src, meta


def export_model(out_dir, bst):
    character = os.path.basename(os.path.dirname(bpy.data.filepath))
    out_dir = out_dir or os.path.join(UNITY, "Models", character)
    src, meta = source_rig()
    for pb in src.pose.bones:
        pb.matrix_basis.identity()
    src.data.pose_position = 'REST'
    sources = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("WGT")
               and any(m.type == 'ARMATURE' and m.object == src for m in o.modifiers)]
    sources.sort(key=lambda o: (o.name != "Body", o.name))
    assert sources and sources[0].name == "Body", [o.name for o in sources]
    log(character, "-", len(sources), "skinned meshes:", [o.name for o in sources])
    name_report(src)
    names = [o.name for o in sources]
    park_names(names)
    rig = build_game_rig(src, meta, constrain=False)
    meshes = [build_game_mesh(o, rig, n) for o, n in zip(sources, names)]
    scale_rig(rig)
    top = max(v.co.z for v in meshes[0].data.vertices)
    log("scale x%.2f -> Hips at %.3f m, Body top at %.3f m" % (SCALE, rig.data.bones["Hips"].head_local.z, top))
    fbx(os.path.join(out_dir, "SK_%s.fbx" % character), [rig] + meshes, False, bst)


def export_clip(clip, out_dir, bst, lift=0.0, lift_curve=None):
    out_dir = out_dir or os.path.join(UNITY, "Animations")
    scene = bpy.context.scene
    assert abs(scene.render.fps / scene.render.fps_base - FPS) < 1e-6, \
        "scene fps is %s, clips must be authored at %d" % (scene.render.fps, FPS)
    src, meta = source_rig()
    act = bpy.data.actions.get(clip)
    assert act is not None, "no action named %r (have %s)" % (clip, [a.name for a in bpy.data.actions])
    name_report(src)
    for pb in src.pose.bones:          # rigid IK chains (see tools/rig_lib_no_stretch.py)
        pb.ik_stretch = 0.0
    src.animation_data_create()
    ad_ = src.animation_data
    # the action ALONE: the anim file may hold the user's editing stack (the clip pushed down as an NLA
    # strip with a fix action in Combine on top); assigning the clip over its own strip in Combine applied
    # it twice (2026-09-24: every angle doubled in the export). Mute the tracks, plain Replace, full influence
    for t_ in ad_.nla_tracks:
        t_.mute = True
    ad_.action = act
    ad_.action_blend_type = 'REPLACE'; ad_.action_influence = 1.0; ad_.action_extrapolation = 'HOLD'
    if hasattr(ad_, "action_slot") and act.slots:
        ad_.action_slot = act.slots[0]
    if ad_.nla_tracks:
        log("export: %d NLA track(s) muted, action %s alone in Replace" % (len(ad_.nla_tracks), act.name))
    f0, f1 = (int(round(x)) for x in act.frame_range)
    scene.frame_start, scene.frame_end = f0, f1
    log("clip %s: frames %d..%d (%.2f s at %d fps)" % (clip, f0, f1, (f1 - f0) / FPS, FPS))

    park_names(["Body"])
    rig = build_game_rig(src, meta, constrain=True)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    kw = dict(frame_start=f0, frame_end=f1, step=1, only_selected=True, visual_keying=True,
              clear_constraints=True, clear_parents=False, use_current_action=False,
              clean_curves=False, bake_types={'POSE'})
    try:
        bpy.ops.nla.bake(channel_types={'LOCATION', 'ROTATION', 'SCALE'}, **kw)
    except TypeError:
        bpy.ops.nla.bake(**kw)
    bpy.ops.object.mode_set(mode='OBJECT')
    baked = rig.animation_data.action
    assert baked is not None and not any(pb.constraints for pb in rig.pose.bones)
    baked.name = clip
    detwist_legs(rig, f0, f1)
    n = scale_rig(rig, baked)
    strip_bone_translation(baked)
    root_fc = [fc for fc in fcurves(baked) if fc.data_path == 'pose.bones["Root"].location']
    if lift:
        # whole-character lift, in ENGINE metres: Unity's humanoid retarget reconstructs the
        # legs approximately and a pinned foot lands a few mm to 2 cm under the floor,
        # by an amount that depends on the pose (Idle -5 mm, hunched Idle_03 -18 mm).
        # Measured per clip in Unity by tools/unity/ground_clip.py; Root points up, so
        # its bone-local Y is world Z.
        for fc in root_fc:
            if fc.array_index == 1:
                for kp in fc.keyframe_points:
                    kp.co.y += lift; kp.handle_left.y += lift; kp.handle_right.y += lift
        log("lifted Root by %.4f m" % lift)
    if lift_curve:
        # per-frame lift on top, ENGINE metres, from tools/unity/ground_fit.py (the six models measured
        # in Unity: the highest model's lowest vertex is put on the floor frame by frame)
        curve = json.load(open(lift_curve))["lift"]
        for fc in root_fc:
            if fc.array_index == 1:
                for kp in fc.keyframe_points:
                    i = max(0, min(len(curve) - 1, int(round(kp.co.x - f0))))
                    kp.co.y += curve[i]; kp.handle_left.y += curve[i]; kp.handle_right.y += curve[i]
        log("lift curve %s: %d frames, %+.4f..%+.4f m" % (os.path.basename(lift_curve), len(curve), min(curve), max(curve)))
    travel = [fc.evaluate(f1) - fc.evaluate(f0) for fc in sorted(root_fc, key=lambda f: f.array_index)]
    log("baked %d location curves scaled x%.1f; Root travel over the clip (Blender XYZ, m): %s"
        % (n, SCALE, [round(t, 4) for t in travel]))

    body = bpy.data.objects.new("Body", None)          # node-path decoy, see module docstring
    bpy.context.scene.collection.objects.link(body)
    scene.name = clip                                   # the FBX take name comes from the scene
    park_on_rest(rig, f0 - 1)
    fbx(os.path.join(out_dir, "%s@%s.fbx" % (CLIP_PREFIX, clip)), [rig, body], True, bst)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_dir = argv[argv.index("--out") + 1] if "--out" in argv else None
    bst = bool(int(argv[argv.index("--bst") + 1])) if "--bst" in argv else True
    if "--clip" in argv:
        lift = float(argv[argv.index("--lift") + 1]) if "--lift" in argv else CLIP_LIFT
        lift_curve = argv[argv.index("--lift-curve") + 1] if "--lift-curve" in argv else None
        export_clip(argv[argv.index("--clip") + 1], out_dir, bst, lift, lift_curve)
    else:
        export_model(out_dir, bst)


main()
