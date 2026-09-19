"""Add the weapon socket bones to Rig/skeleton_rig.blend (idempotent).

    blender -b Rig/skeleton_rig.blend -P tools/rig_lib_add_sockets.py

Adds `weapon.L/R` to the metarig (child of hand.L/R) and `DEF-weapon.L/R` to the
generated rig (child of DEF-hand.L/R, deform, no weights). The exporter turns them into
`LeftWeaponSocket` / `RightWeaponSocket`, so the grip convention ships inside every
model and clip FBX and is identical in Unity and Unreal.

Grip convention (bone axes, Blender terms; Unity/Unreal see the same bone frame):
  head  = centre of the palm (mean of the four palm-bone midpoints)
  +Y    = along the hilt, out of the fist on the THUMB/INDEX side  (blade direction)
  +Z    = out of the BACK of the hand (away from the palm)
  +X    = completes the right-handed frame (roughly along the fingers, sign per side)
A weapon mesh is authored with its grip point at the origin and its blade along +Y in
the engine, and attaches to the socket with an identity local transform.

If the Rigify rig is ever regenerated from the metarig, mark `weapon.L/R` as
`basic.raw_copy` (Rigify cannot be driven headlessly here) or re-run this script.
"""
import bpy, os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEN = 0.05


def palm_frame(bones, side):
    palms = [bones["DEF-palm.0%d.%s" % (i, side)] for i in (1, 2, 3, 4)]
    mids = [(b.head_local + b.tail_local) / 2 for b in palms]
    centre = sum(mids, Vector()) / 4
    hand = bones["DEF-hand." + side]
    fingers = (hand.tail_local - hand.head_local).normalized()          # wrist -> fingertips
    across = (mids[0] - mids[3]).normalized()                            # pinky -> index
    across = (across - across.dot(fingers) * fingers).normalized()       # keep it in the palm plane
    normal = fingers.cross(across).normalized()
    thumb_tip = bones["DEF-thumb.03." + side].tail_local
    if (thumb_tip - centre).dot(normal) > 0:   # the thumb opposes the palm: it sits on the palm side
        normal = -normal                       # so make `normal` point out of the BACK of the hand
    return centre, across, normal, fingers


def add(arm_obj, name, parent_name, head, blade, back):
    bpy.ops.object.select_all(action='DESELECT')
    arm_obj.select_set(True); bpy.context.view_layer.objects.active = arm_obj
    arm_obj.hide_viewport = False
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_obj.data.edit_bones
    if name in eb:
        eb.remove(eb[name])
    b = eb.new(name)
    b.head = head; b.tail = head + blade * LEN
    b.align_roll(back)
    b.parent = eb[parent_name]; b.use_connect = False
    b.use_deform = True
    bpy.ops.object.mode_set(mode='OBJECT')
    bone = arm_obj.data.bones[name]
    parent = arm_obj.data.bones[parent_name]
    for col in parent.collections:
        col.assign(bone)
    return bone


rig = bpy.data.objects["RIG-Meta-Rig"]
meta = bpy.data.objects["Meta-Rig"]
for side in ("L", "R"):
    centre, across, back, fingers = palm_frame(rig.data.bones, side)
    b = add(rig, "DEF-weapon." + side, "DEF-hand." + side, centre, across, back)
    add(meta, "weapon." + side, "hand." + side, centre, across, back)
    m = b.matrix_local
    print("[sockets] %s head=%s  +Y(blade)=%s  +Z(back of hand)=%s  +X=%s" % (
        b.name, tuple(round(v, 4) for v in b.head_local),
        tuple(round(v, 3) for v in m.col[1][:3]), tuple(round(v, 3) for v in m.col[2][:3]),
        tuple(round(v, 3) for v in m.col[0][:3])))

print("[sockets] deform bones now", sum(1 for x in rig.data.bones if x.use_deform))
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath, compress=True)
