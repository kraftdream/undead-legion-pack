"""Create or refresh Animations/skeleton_anim.blend - the ONE file clips are authored in.

    create :  blender -b -P tools/anim_file_build.py
    refresh:  blender -b Animations/skeleton_anim.blend -P tools/anim_file_build.py

Contents:
  * the shared rig, LINKED from Rig/skeleton_rig.blend as a library override, so an
    edit to the library shows up here on the next open; posing and keying work as on a
    local rig
  * every character's Body + armour meshes, APPENDED as reference (local copies) into
    Ref_<Character> collections, skinned to the override rig; only Ref_SkeletonKnight is
    enabled in the view layer
  * the weapons, appended into a `Weapons` collection (disabled)
  * scene at 30 fps, frame 1..60

Refresh deletes and re-appends the reference meshes and weapons only. It NEVER touches
actions or the rig override, so authored clips survive a refresh. Actions are the
payload of this file; do not author clips in the character files (rig_sync.py replaces
their rig object and would drop the animation data with it).
"""
import bpy, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Animations", "skeleton_anim.blend")
LIB = os.path.join(ROOT, "Rig", "skeleton_rig.blend")
CHARS = ["SkeletonKnight", "SkeletonArcher", "SkeletonAssassin", "SkeletonMage",
         "SkeletonNecromancer", "SkeletonWarrior"]
FPS = 30


def log(*a):
    print("[anim_file]", *a); sys.stdout.flush()


def link_rig(scene):
    with bpy.data.libraries.load(LIB, link=True, relative=True) as (src, dst):
        dst.collections = ["Rig"]
    linked = next(c for c in bpy.data.collections if c.name == "Rig" and c.library is not None)
    scene.collection.children.link(linked)
    ov = linked.override_hierarchy_create(scene, bpy.context.view_layer, do_fully_editable=True)
    if linked.name in scene.collection.children:
        scene.collection.children.unlink(linked)
    if ov.name not in scene.collection.children:
        scene.collection.children.link(ov)
    rig = next(o for o in ov.all_objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
    assert rig.override_library is not None, "rig is not an override"
    log("rig override:", rig.name, "bones:", len(rig.data.bones))
    return rig


def clear_collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        return
    for o in list(col.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)


def ensure_collection(scene, name, exclude):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
    if name not in scene.collection.children:
        scene.collection.children.link(col)
    bpy.context.view_layer.layer_collection.children[name].exclude = exclude
    return col


def append_meshes(path, col, rig, rename=None):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if not n.startswith("WGT") and n not in ("RIG-Meta-Rig", "Meta-Rig")]
    got = []
    for o in dst.objects:
        if o is None or o.type != 'MESH':
            if o is not None:
                bpy.data.objects.remove(o, do_unlink=True)
            continue
        col.objects.link(o)
        o.hide_viewport = False; o.hide_render = False; o.hide_set(False)   # some sources were saved hidden
        if rename:
            o.name = rename(o.name)
        for m in list(o.modifiers):
            if m.type == 'ARMATURE':
                o.modifiers.remove(m)
        if rig is not None:
            o.modifiers.new("Armature", 'ARMATURE').object = rig
            o.parent = rig
        got.append(o.name)
    return got


def main():
    creating = not bpy.data.filepath
    if creating:
        bpy.ops.wm.read_homefile(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.0
    scene.frame_start, scene.frame_end = 1, 60

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    rig = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and o.override_library and o.name.startswith("RIG-")), None)
    if rig is not None and "--relink" in argv:
        # rebuild the override from the current library (after a library rebuild that
        # changed more than bone data, e.g. restored drivers). Actions are datablocks
        # with fake users and survive; they are re-bound by name when next assigned.
        log("relinking the rig override; actions kept:", [a.name for a in bpy.data.actions])
        for o in list(bpy.data.objects):
            if o.override_library is not None or o.library is not None:
                bpy.data.objects.remove(o, do_unlink=True)
        for c in list(bpy.data.collections):
            if c.override_library is not None or c.library is not None or c.name.startswith(("Rig", "WGTS")):
                bpy.data.collections.remove(c)
        for _ in range(3):
            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
        rig = None
    if rig is None:
        rig = link_rig(scene)
    else:
        log("rig override present:", rig.name, "actions kept:", [a.name for a in bpy.data.actions])

    for c in CHARS:
        clear_collection("Ref_" + c)
        col = ensure_collection(scene, "Ref_" + c, exclude=(c != "SkeletonKnight"))
        got = append_meshes(os.path.join(ROOT, c, "prod.blend"), col, rig, rename=lambda n, c=c: c + "_" + n)
        log("%-20s %d meshes" % (c, len(got)))
    clear_collection("Weapons")
    col = ensure_collection(scene, "Weapons", exclude=True)
    got = append_meshes(os.path.join(ROOT, "Weapons", "weapons.blend"), col, None)
    log("Weapons %d meshes" % len(got))

    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True, relative_remap=True)
    log("saved", os.path.relpath(OUT, ROOT), "| fps", scene.render.fps, "| actions", [a.name for a in bpy.data.actions])


main()
