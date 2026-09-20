"""Build Rig/skeleton_rig.blend - the ONE armature every character links to.

    blender -b <original knight prod.blend> -P tools/rig_lib_build.py

Takes the Rigify metarig + generated rig out of a character file (the Knight as
committed in f9eacf8, before any tooling touched it: its deform skeleton is the one
five of six files already agreed on to 0.1 mm), drops
everything else, normalises the datablock names, sets bbone_segments=1 on every
deform bone (FBX has no B-bones, so what Blender shows must be what the engine
shows) and saves the library. Never edit the rig in a character file afterwards:
edit it here and run tools/rig_sync.py. Then run tools/rig_lib_add_sockets.py and
tools/rig_lib_dump.py.

⚠ KEEP THE DRIVERS. The first build called `animation_data_clear()` to drop any
action and silently removed Rigify's 109 drivers with it - the IK/FK switches,
among others. Every FK control then posed nothing (the ORG chain followed the IK
copy at full influence) and the retargeted Idle's arms were the untouched IK
controls' pose, ~12 deg wider than the source. Only the ACTION is cleared here.
"""
import bpy, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Rig", "skeleton_rig.blend")
RIG_OBJ, META_OBJ = "RIG-Meta-Rig", "Meta-Rig"

rig = bpy.data.objects[RIG_OBJ]
meta = bpy.data.objects[META_OBJ]
assert rig.type == 'ARMATURE' and meta.type == 'ARMATURE'
assert all(abs(v) < 1e-6 for v in rig.location) and all(abs(v) < 1e-6 for v in rig.rotation_euler)
assert all(abs(s - 1) < 1e-6 for s in rig.scale), "rig object must be at identity"

# widgets: every object referenced as a custom shape by a pose bone
wgts = {pb.custom_shape for pb in rig.pose.bones if pb.custom_shape}
keep = {rig, meta} | wgts
for o in list(bpy.data.objects):
    if o not in keep:
        bpy.data.objects.remove(o, do_unlink=True)

# collections: one for the rig, one (excluded) for the widgets
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
scene = bpy.context.scene
col_rig = bpy.data.collections.new("Rig"); scene.collection.children.link(col_rig)
col_w = bpy.data.collections.new("WGTS_Rig"); scene.collection.children.link(col_w)
for o in (rig, meta):
    for c in list(o.users_collection): c.objects.unlink(o)
    col_rig.objects.link(o)
for o in wgts:
    for c in list(o.users_collection): c.objects.unlink(o)
    col_w.objects.link(o)
bpy.context.view_layer.layer_collection.children["WGTS_Rig"].exclude = True

# datablock names: no .001 suffixes
rig.data.name = "RIG-Meta-Rig"
meta.data.name = "metarig"

# no B-bones on anything that deforms
n = 0
for b in rig.data.bones:
    if b.bbone_segments != 1:
        b.bbone_segments = 1; n += 1
for b in meta.data.bones:
    if b.bbone_segments != 1:
        b.bbone_segments = 1
print("bbone_segments reset on", n, "bones")

# rest pose, no leftover action - but the DRIVERS stay (see the docstring)
for ob in (rig, meta):
    if ob.animation_data is not None:
        ob.animation_data.action = None
for pb in rig.pose.bones:
    pb.matrix_basis.identity()
n_drv = len(rig.animation_data.drivers) if rig.animation_data else 0
assert n_drv > 50, "rig has only %d drivers - wrong source file?" % n_drv
print("drivers kept:", n_drv)

# orphan purge
for _ in range(3):
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

bpy.context.preferences.filepaths.save_version = 0
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print("saved", OUT, "objects:", len(bpy.data.objects), "armatures:", [a.name for a in bpy.data.armatures],
      "texts:", [t.name for t in bpy.data.texts], "deform:", sum(1 for b in rig.data.bones if b.use_deform))
