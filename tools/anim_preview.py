"""Render a contact sheet of an action for review (Workbench, no scene setup needed).

    blender -b Animations/skeleton_anim.blend -P tools/anim_preview.py -- --action Idle \
        [--frames 1,31,61,91,121] [--out DIR] [--px 420] [--ref SkeletonKnight]

Writes <out>/<action>_front.png and <action>_side.png: one column per frame, camera
framed on the reference character. Meant to be looked at, not measured.
"""
import bpy, sys, os, math
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(k, d=None):
    return argv[argv.index(k) + 1] if k in argv else d


ACTION = arg("--action", "Idle")
FRAMES = [int(x) for x in arg("--frames", "1,31,61,91,121").split(",")]
OUT = arg("--out", os.path.join(ROOT, "Animations", "preview"))
PX = int(arg("--px", "420"))
REF = arg("--ref", "SkeletonKnight")

rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith("RIG-"))
scene = bpy.context.scene
act = bpy.data.actions[ACTION]
rig.animation_data_create(); rig.animation_data.action = act
if hasattr(rig.animation_data, "action_slot") and act.slots:
    rig.animation_data.action_slot = act.slots[0]

# only the reference character visible
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name.startswith("Ref_"):
        lc.exclude = (lc.name != "Ref_" + REF)
    if lc.name == "Weapons":
        lc.exclude = True
rig.hide_render = True                                   # no bone widgets
for o in bpy.data.objects:
    if o.type == 'ARMATURE' or o.name.startswith("WGT"):
        o.hide_render = True

scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (0.75, 0.72, 0.65)
sh.show_cavity = True; sh.show_shadows = True; sh.show_object_outline = True
scene.render.resolution_x = PX; scene.render.resolution_y = int(PX * 1.6)
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.world = scene.world or bpy.data.worlds.new("W")
scene.world.color = (0.18, 0.18, 0.2)

cam_data = bpy.data.cameras.new("_preview_cam"); cam_data.type = 'ORTHO'; cam_data.ortho_scale = 1.25
cam = bpy.data.objects.new("_preview_cam", cam_data); scene.collection.objects.link(cam); scene.camera = cam
centre = Vector((0, 0, 0.5))
VIEWS = {"front": (Vector((0, -6, 0.5)), (math.radians(90), 0, 0)),
         "side": (Vector((6, 0, 0.5)), (math.radians(90), 0, math.radians(90)))}
os.makedirs(OUT, exist_ok=True)
tiles = {}
for view, (loc, rot) in VIEWS.items():
    cam.location = loc; cam.rotation_euler = rot
    paths = []
    for f in FRAMES:
        scene.frame_set(f)
        p = os.path.join(OUT, "_%s_%s_%03d.png" % (ACTION, view, f))
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        paths.append(p)
    tiles[view] = paths

# stitch with Blender's own image API (no PIL dependency)
for view, paths in tiles.items():
    imgs = [bpy.data.images.load(p) for p in paths]
    w, h = imgs[0].size
    sheet = bpy.data.images.new("_sheet", w * len(imgs), h)
    px = [0.0] * (w * len(imgs) * h * 4)
    for i, im in enumerate(imgs):
        src = list(im.pixels)
        for y in range(h):
            row = src[y * w * 4:(y + 1) * w * 4]
            off = (y * w * len(imgs) + i * w) * 4
            px[off:off + w * 4] = row
    sheet.pixels = px
    out = os.path.join(OUT, "%s_%s.png" % (ACTION, view))
    sheet.filepath_raw = out; sheet.file_format = 'PNG'; sheet.save()
    for p in paths:
        os.remove(p)
    print("[preview] wrote", out, "frames", FRAMES)
