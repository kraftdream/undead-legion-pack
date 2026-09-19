"""Character file -> game-ready FBX: shared Rigify rig -> clean Mixamo-named skeleton.

    blender -b SkeletonKnight/prod.blend -P tools/export_fbx.py -- [--out DIR] [--bst 0|1]

Writes skeletons/Assets/UndeadLegion/Models/<Character>/SK_<Character>.fbx (or --out
DIR): the deform skeleton
under a `Root` node plus every skinned mesh in the file (Body + armour modules) as
SIBLING nodes of the armature, at SCALE x the Blender metres. No animation.
Nothing is saved back to the .blend.

Why a rebuilt skeleton (inherited from the creatures pack, see smp-10-rgp-creatures
tools/goblin_export.py):
  * "Only Deform Bones" is wrong for Rigify: DEF-thigh hangs off ORG-spine, so the
    tickbox drops parents and you get a flat skeleton. Anatomy comes from the METARIG.
  * Mixamo names: Unity's Humanoid auto-mapper takes them cleanly and buyers can drop
    any Mixamo/humanoid clip on the rig.
  * Copy each bone's WHOLE rest matrix (roll included) or every posed frame skins wrong.
  * `Root` points UP (+Z here = +Y in the engine); Rigify's `root` lies flat.
  * Meshes are siblings of the armature, not children: a model FBX and a clip FBX must
    produce the same node paths or Unity's "Copy From Other Avatar" yields zero clips.
  * bake_space_transform=True (default, --bst 0 to disable): measured in Unity 6000.4 on
    2026-09-19, both settings give the same valid Humanoid avatar and identical bounds,
    but only True leaves every SkinnedMeshRenderer node at identity rotation, which is
    what the Asset Store validator's "Check Model Orientation" wants. The Armature node
    keeps its -90 deg X either way; the validator does not look at it.
"""
import bpy, os, sys
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_RIG, METARIG = "RIG-Meta-Rig", "Meta-Rig"
RIG_NODE = "Armature"       # one child (Root) -> Unreal strips it, Unity keeps it; same in every file
SCALE = 1.8                 # source art is ~0.94 m; the Unity demo established 1.8x (CLAUDE.md 7)
MAX_INFLUENCES = 4

_SPINE = {"spine": "Hips", "spine.001": "Spine", "spine.002": "Spine1", "spine.003": "Spine2",
          "spine.004": "Neck", "spine.005": "Neck1", "spine.006": "Head"}
_LIMB = {"shoulder": "Shoulder", "upper_arm": "Arm", "forearm": "ForeArm", "hand": "Hand",
         "thigh": "UpLeg", "shin": "Leg", "foot": "Foot", "toe": "ToeBase", "pelvis": "Pelvis"}
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
        req += [s + x for x in ("Shoulder", "Arm", "ForeArm", "Hand", "UpLeg", "Leg", "Foot", "ToeBase")]
    miss = [r for r in req if r not in seen]
    if miss:
        raise RuntimeError("humanoid mapping incomplete: %s" % miss)
    log("%d deform bones -> %d names; all %d humanoid-required bones present" % (len(seen), len(seen), len(req)))
    return seen


def build_game_rig(src, meta):
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
    log("game rig: %d bones; children of Root: %s" % (len(arm.bones), roots))
    assert roots == ["Hips"], roots
    return rig


def limit_influences(ob):
    """Unity keeps 4 weights per vertex; do the cut and re-normalise here, deterministically."""
    me = ob.data
    n = 0
    for v in me.vertices:
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


def build_game_mesh(src_ob, rig, name):
    ob = bpy.data.objects.new(name, src_ob.data.copy())
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = src_ob.matrix_world.copy()
    for g in ob.vertex_groups:
        if g.name.startswith("DEF-") or g.name == "root":
            g.name = game_name(g.name)
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    ob.modifiers.new("Armature", 'ARMATURE').object = rig
    cut = limit_influences(ob)
    log("  mesh %-10s %6d v  %s" % (name, len(ob.data.vertices),
                                    ("%d verts cut to %d influences" % (cut, MAX_INFLUENCES)) if cut else ""))
    return ob


def apply_scale(rig, meshes):
    """Scale the temporary export set by SCALE, baked into bones and vertices."""
    M = Matrix.Scale(SCALE, 4)
    for ob in meshes:
        ob.data.transform(M)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); bpy.context.view_layer.objects.active = rig
    rig.scale = (SCALE, SCALE, SCALE)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def export(path, rig, meshes, bake_space_transform):
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    for ob in meshes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = rig
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'},
        apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z', axis_up='Y', bake_space_transform=bake_space_transform,
        use_mesh_modifiers=True, mesh_smooth_type='OFF', use_tspace=False,
        add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
        use_armature_deform_only=False, armature_nodetype='NULL',
        bake_anim=False, path_mode='AUTO', embed_textures=False, use_custom_props=False)
    log("wrote", os.path.relpath(path, ROOT), "%d KB" % (os.path.getsize(path) // 1024))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_dir = argv[argv.index("--out") + 1] if "--out" in argv else None
    bst = bool(int(argv[argv.index("--bst") + 1])) if "--bst" in argv else True
    character = os.path.basename(os.path.dirname(bpy.data.filepath))
    out_dir = out_dir or os.path.join(ROOT, "skeletons", "Assets", "UndeadLegion", "Models", character)
    src, meta = bpy.data.objects[SRC_RIG], bpy.data.objects[METARIG]
    assert bpy.context.mode == 'OBJECT'
    assert src.matrix_world == Matrix.Identity(4)
    for pb in src.pose.bones:
        pb.matrix_basis.identity()
    src.data.pose_position = 'REST'

    sources = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("WGT")
               and any(m.type == 'ARMATURE' and m.object == src for m in o.modifiers)]
    sources.sort(key=lambda o: (o.name != "Body", o.name))
    log(character, "-", len(sources), "skinned meshes:", [o.name for o in sources])
    name_report(src)

    # park the sources' names so the export copies can take them (file is never saved)
    names = [o.name for o in sources]
    for o in sources:
        o.hide_viewport = False; o.hide_set(False)
        o.name = "__src_" + o.name
    rig = build_game_rig(src, meta)
    meshes = [build_game_mesh(o, rig, n) for o, n in zip(sources, names)]
    apply_scale(rig, meshes)
    hips = rig.data.bones["Hips"].head_local
    top = max((v.co.z for v in meshes[0].data.vertices), default=0)
    log("scale x%.2f -> Hips at %.3f m, Body top at %.3f m" % (SCALE, hips.z, top))
    export(os.path.join(out_dir, "SK_%s.fbx" % character), rig, meshes, bst)


main()
