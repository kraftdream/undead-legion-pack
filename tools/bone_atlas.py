"""A measured map of what every control on the shared rig actually DOES.

    blender -b Animations/skeleton_anim.blend -P tools/bone_atlas.py -- --out Rig/atlas [--render] [--only torso,head]
    blender -b Animations/skeleton_anim.blend -P tools/bone_atlas.py -- --out Rig/atlas --sheets-from
    python tools/atlas_query.py Rig/atlas/atlas.json jaw_dz hilt_R foot_L_min_z
    python tools/atlas_query.py Rig/atlas/atlas.json --bone hand_fk.R --inert --shape swivel

Ported from the creatures pack (`smp-10-rgp-creatures/tools/bone_atlas.py`), where a
dozen wrong-control defects across six creatures were each ONE unmeasured fact about ONE
channel (a jaw driven through a skull, a hand that was a world orientation, an inert pole
target, a per-side shoulder sign). This pack collected its own set in one week: the toe's
hinge axis, the jaw's open sign, which way "counterclockwise" turns a wrist, which slot
axis the fingers are. So measure all of them once, on the BARE Knight body, and cite the
atlas instead of re-probing.

WHAT IT MEASURES
----------------
For every control channel (each rotation axis of every animator-facing bone, plus the
translation axes where the bone is free to translate) it applies a delta from the rig's
REST state and records what moved, in the CHARACTER's frame (forward / left / up):

  landmarks  head, chest, pelvis, hands, feet, elbows, knees: positions
  axes       the weapon sockets' hilt axis (+Y), back-of-hand (+Z) and fingers (+X),
             the head's aim, the chest's and pelvis' facing, each foot's direction
  regions    the lowest point and centroid of the jaw, head, hands, feet and torso
             (vertex groups of the bare body, resolved once at rest)
  jaw_dz     the gap between the skull's front and the jaw's front, SIGNED (+ = open)
  shape      inert / move / swivel / bend / root_shift, as in the creatures pack
  linearity  probed at half delta: a channel that saturates is visible

THE REST STATE HERE IS THE GENERATED RIG'S IDENTITY POSE. The anim file opens with a clip
assigned, so the tool detaches it and zeroes every control first; the IK/FK switches are
set per pass: the FK controls are probed with `IK_FK = 1` (they do nothing at 0) and the
IK controls with `IK_FK = 0`. Every record says which.

Nothing here gates anything and nothing here saves the .blend. It measures and prints.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector, Quaternion, Matrix

SKIP_PREFIX = ("VIS_", "ORG-", "MCH-", "DEF-", "WGT-")
ROT_DELTA = 0.35          # ~20 deg
LOC_FRACTION = 0.03       # of the body height
INERT = 0.001
SWIVEL_TIP = 0.002
SWIVEL_MID = 0.010
IKFK_SWITCHES = ("upper_arm_parent.L", "upper_arm_parent.R", "thigh_parent.L", "thigh_parent.R")


def _log(*a):
    print("[atlas]", *a)
    sys.stdout.flush()


# ------------------------------------------------------------------- discovery

def rig():
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    if not arms:
        raise RuntimeError("no armature in %s" % bpy.data.filepath)
    return max(arms, key=lambda o: len(o.data.bones))


def _excluded_names():
    out = set()

    def walk(lc):
        if lc.exclude:
            out.add(lc.name)
        for c in lc.children:
            walk(c)
    walk(bpy.context.view_layer.layer_collection)
    return out


def body(r=None, name=None):
    """The BARE body: a mesh named *_Body that is in the view layer, never an armour module."""
    r = r or rig()
    if name:
        return bpy.data.objects[name]
    excl = _excluded_names()
    cands = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith("_Body")
             and any(m.type == 'ARMATURE' and m.object is r for m in o.modifiers)
             and not any(c.name in excl for c in o.users_collection)]
    if not cands:
        raise RuntimeError("no *_Body mesh skinned to %s in the view layer" % r.name)
    if len(cands) > 1:
        _log("note: %d bodies in the view layer (%s); using %r" % (len(cands), ", ".join(o.name for o in cands), cands[0].name))
    return cands[0]


def controls(r=None):
    r = r or rig()
    return sorted(b.name for b in r.data.bones if not b.name.startswith(SKIP_PREFIX))


def ik_controls(r=None):
    r = r or rig()
    names = set()
    for c in r.data.collections_all:
        if "(IK)" in c.name:
            names.update(b.name for b in c.bones)
    return names


def deform(r=None):
    r = r or rig()
    return [b.name for b in r.data.bones if b.name.startswith("DEF-")]


# ------------------------------------------------------------------- the pose

def zero_pose(r, ikfk):
    if r.animation_data:
        r.animation_data.action = None
    for pb in r.pose.bones:
        pb.matrix_basis.identity()
        if "ik_stretch" in dir(pb):
            pb.ik_stretch = 0.0
    for n in IKFK_SWITCHES:
        if n in r.pose.bones and "IK_FK" in r.pose.bones[n]:
            r.pose.bones[n]["IK_FK"] = float(ikfk)
    bpy.context.view_layer.update()


class Rest(object):
    """The rest state as prepared by zero_pose(), restorable."""

    def __init__(self, r):
        self.rig = r
        self.state = {}
        self.props = {}
        for pb in r.pose.bones:
            self.state[pb.name] = (pb.location.copy(), pb.rotation_quaternion.copy(), pb.rotation_euler.copy(), pb.scale.copy())
            self.props[pb.name] = {k: pb[k] for k in pb.keys() if not k.startswith("_") and isinstance(pb[k], (int, float))}

    def restore(self):
        for name, (loc, q, e, sc) in self.state.items():
            pb = self.rig.pose.bones[name]
            pb.location = loc
            pb.rotation_quaternion = q
            pb.rotation_euler = e
            pb.scale = sc
            for k, v in self.props[name].items():
                try:
                    pb[k] = v
                except Exception:
                    pass
        bpy.context.view_layer.update()


def set_rot(pb, axis, angle):
    q = Quaternion((1, 0, 0) if axis == 0 else (0, 1, 0) if axis == 1 else (0, 0, 1), angle)
    if pb.rotation_mode == 'QUATERNION':
        pb.rotation_quaternion = pb.rotation_quaternion @ q
    else:
        m = pb.rotation_euler.to_matrix() @ q.to_matrix()
        pb.rotation_euler = m.to_euler(pb.rotation_mode)


def set_loc(pb, axis, d):
    v = pb.location.copy()
    v[axis] += d
    pb.location = v


# ---------------------------------------------------------------- measurement

class Frame(object):
    """The character's axes: forward -Y, left +X, up +Z at the root."""

    def __init__(self, r):
        M = (r.matrix_world @ r.pose.bones["root"].matrix) if "root" in r.pose.bones else r.matrix_world
        R = M.to_3x3()
        self.left = (R @ Vector((1, 0, 0))).normalized()
        self.fwd = (R @ Vector((0, -1, 0))).normalized()
        self.up = (R @ Vector((0, 0, 1))).normalized()
        if self.up.z < 0.9:
            # Rigify's root lies flat, so its +Z is not up: fall back to world axes
            self.left, self.fwd, self.up = Vector((1, 0, 0)), Vector((0, -1, 0)), Vector((0, 0, 1))

    def to(self, v):
        return Vector((v.dot(self.left), v.dot(self.fwd), v.dot(self.up)))

    @staticmethod
    def describe(v, tol=0.25):
        names = (("right", "left"), ("back", "forward"), ("down", "up"))
        out = []
        for i in sorted(range(3), key=lambda i: -abs(v[i])):
            if abs(v[i]) < tol * max(1e-9, max(abs(c) for c in v)):
                continue
            out.append("%s %.3f" % (names[i][v[i] > 0], abs(v[i])))
        return ", ".join(out) or "nothing"


def bone_points(r):
    out = {}
    for n in deform(r):
        b = r.pose.bones[n]
        out[n] = (r.matrix_world @ b.head, r.matrix_world @ b.tail)
    return out


def _hand_groups(side):
    names = ["hand." + side] + ["palm.0%d.%s" % (i, side) for i in range(1, 5)]
    for f in ("thumb", "f_index", "f_middle", "f_ring", "f_pinky"):
        names += ["%s.0%d.%s" % (f, i, side) for i in range(1, 4)]
    return tuple(names)


class Probes(object):
    """Named character-level quantities: what a clip actually wants to control."""

    REGIONS = {
        "lowerjaw": ("lowerjaw", "lowerjaw.001"),
        "head": ("spine.006",),
        "neck": ("spine.004", "spine.005"),
        "chest": ("spine.003",),
        "pelvis": ("spine", "pelvis.L", "pelvis.R"),
        "footL": ("foot.L", "toe.L"),
        "footR": ("foot.R", "toe.R"),
        "handL": _hand_groups("L"),
        "handR": _hand_groups("R"),
    }
    POS = {"DEF-spine.006": "head_pos", "DEF-spine.004": "neck_pos", "DEF-spine.003": "chest_pos", "DEF-spine": "pelvis_pos"}
    #: bones whose FACING is a probe: (bone, probe name, world direction at rest that the axis should read)
    AXES = (("DEF-spine.006", "head_aim", Vector((0, -1, 0))), ("DEF-spine.006", "head_up", Vector((0, 0, 1))),
            ("DEF-spine.003", "chest_fwd", Vector((0, -1, 0))), ("DEF-spine", "pelvis_fwd", Vector((0, -1, 0))),
            ("DEF-foot.L", "foot_L_fwd", Vector((0, -1, 0))), ("DEF-foot.R", "foot_R_fwd", Vector((0, -1, 0))))

    def __init__(self, r, mesh):
        self.rig = r
        self.mesh = mesh
        self.groups = {}
        for reg, names in self.REGIONS.items():
            idx = {g.index for g in mesh.vertex_groups if g.name.replace("DEF-", "") in names}
            if not idx:
                continue
            verts = [v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if g.group in idx) > 0.5]
            if verts:
                self.groups[reg] = verts
        _log("probe regions: %s" % ", ".join("%s=%d" % (k, len(v)) for k, v in sorted(self.groups.items())))
        co = self._co()
        self.marks = {}
        for reg, key in (("lowerjaw", "jaw_lo"), ("head", "jaw_up")):
            if reg in self.groups:
                self.marks[key] = min(self.groups[reg], key=lambda i: co[i].y)      # frontmost vertex (faces -Y)
        _log("fixed landmarks: %s" % ", ".join("%s=v%d" % (k, v) for k, v in sorted(self.marks.items())))
        # the local axis of each facing bone that points the given way AT REST
        self.axis_local = {}
        for bone_n, key, world_dir in self.AXES:
            if bone_n in r.pose.bones:
                R = (r.matrix_world @ r.pose.bones[bone_n].matrix).to_3x3()
                self.axis_local[key] = (bone_n, (R.inverted() @ world_dir).normalized())

    def _co(self):
        dg = bpy.context.evaluated_depsgraph_get()
        ev = self.mesh.evaluated_get(dg)
        me = ev.to_mesh()
        M = self.mesh.matrix_world
        co = [M @ v.co for v in me.vertices]
        ev.to_mesh_clear()
        return co

    def read(self):
        r = self.rig
        co = self._co()
        bp = bone_points(r)
        out = {}
        for reg, idx in self.groups.items():
            pts = [co[i] for i in idx]
            n = len(pts)
            out["%s_centroid" % reg] = Vector((sum(p.x for p in pts) / n, sum(p.y for p in pts) / n, sum(p.z for p in pts) / n))
            out["%s_min_z" % reg] = min(p.z for p in pts)
        out["mesh_min_z"] = min(p.z for p in co)
        out["mesh_max_z"] = max(p.z for p in co)
        if "jaw_lo" in self.marks and "jaw_up" in self.marks:
            lo = co[self.marks["jaw_lo"]]
            up = co[self.marks["jaw_up"]]
            out["jaw_gap"] = (up - lo).length
            out["jaw_dz"] = up.z - lo.z
            out["jaw_tip"] = lo
        for side in ("L", "R"):
            self._limb(out, bp, side, "arm", ("DEF-upper_arm.%s", "DEF-forearm.%s", "DEF-hand.%s"))
            self._limb(out, bp, side, "leg", ("DEF-thigh.%s", "DEF-shin.%s", "DEF-foot.%s"))
            sock = "DEF-weapon." + side
            if sock in r.pose.bones:
                M = r.matrix_world @ r.pose.bones[sock].matrix
                R = M.to_3x3()
                out["socket_%s_pos" % side] = M.translation.copy()
                out["hilt_%s" % side] = (R @ Vector((0, 1, 0))).normalized()
                out["back_of_hand_%s" % side] = (R @ Vector((0, 0, 1))).normalized()
                out["fingers_%s" % side] = (R @ Vector((1, 0, 0))).normalized()
            toe = "DEF-toe." + side
            if toe in bp:
                out["toe_%s_tip" % side] = bp[toe][1]
            # fingertips: a phalanx rotation moves a few vertices, which the 287-vertex hand
            # centroid rounds to nothing (the first run called every finger chain INERT)
            for fn in ("thumb", "f_index", "f_middle", "f_ring", "f_pinky"):
                b3 = "DEF-%s.03.%s" % (fn, side)
                if b3 in bp:
                    out["%s_%s_tip" % (fn.replace("f_", ""), side)] = bp[b3][1]
        for n, key in self.POS.items():
            if n in bp:
                out[key] = bp[n][0]
        for key, (bone_n, local) in self.axis_local.items():
            R = (r.matrix_world @ r.pose.bones[bone_n].matrix).to_3x3()
            out[key] = (R @ local).normalized()
        return out

    def _limb(self, out, bp, side, kind, chain):
        names = [c % side for c in chain]
        if not all(n in bp for n in names):
            return
        rootp, midp, tipp = bp[names[0]][0], bp[names[1]][0], bp[names[2]][0]
        out["%s_%s_tip" % (kind, side)] = tipp
        out["%s_%s_mid" % (kind, side)] = midp
        out["%s_%s_root" % (kind, side)] = rootp
        d = tipp - rootp
        if d.length > 1e-9:
            u = d.normalized()
            out["%s_%s_mid_off" % (kind, side)] = (midp - rootp) - u * (midp - rootp).dot(u)
        out["%s_%s_extension" % (kind, side)] = d.length


def _delta(a, b):
    return {k: b[k] - a[k] for k in set(a) & set(b)}


def _mag(v):
    return v.length if isinstance(v, Vector) else abs(v)


# ------------------------------------------------------------------- the probe

def channels(r, name):
    pb = r.pose.bones[name]
    out = [("rot", i) for i in range(3)]
    if not all(pb.lock_location):
        out += [("loc", i) for i in range(3)]
    return out


def probe_channel(r, rest, probes, name, kind, axis, delta, base, ikfk):
    pb = r.pose.bones[name]
    res = {}
    for tag, amount in (("half", delta * 0.5), ("full", delta), ("neg", -delta)):
        rest.restore()
        pb = r.pose.bones[name]
        (set_rot if kind == "rot" else set_loc)(pb, axis, amount)
        bpy.context.view_layer.update()
        res[tag] = _delta(base, probes.read())
    rest.restore()
    full, half, neg = res["full"], res["half"], res["neg"]
    fr = Frame(r)
    moved = sorted(((k, _mag(v)) for k, v in full.items() if k.endswith(("_pos", "_tip", "_mid", "_centroid"))), key=lambda kv: -kv[1])
    peak = moved[0][1] if moved else 0.0
    # an axis probe (a direction) counts too: a pure roll moves no landmark but turns the hilt
    turned = sorted(((k, _mag(v)) for k, v in full.items() if k in ("hilt_L", "hilt_R", "back_of_hand_L", "back_of_hand_R", "fingers_L", "fingers_R",
                                                                       "head_aim", "head_up", "chest_fwd", "pelvis_fwd", "foot_L_fwd", "foot_R_fwd")), key=lambda kv: -kv[1])
    tpeak = turned[0][1] if turned else 0.0
    rec = {"bone": name, "channel": "%s%s" % (kind, "XYZ"[axis]), "ikfk": ikfk, "delta": round(delta, 5), "rotation_mode": pb.rotation_mode,
           "peak": round(peak, 6), "turn_peak": round(tpeak, 5),
           "moved": [(k, round(v, 5)) for k, v in moved[:6] if v > INERT],
           "turned": [(k, round(v, 4)) for k, v in turned[:4] if v > 0.01],
           "shape": "inert" if (peak < INERT and tpeak < 0.01) else ("twist" if peak < INERT else "move"),
           "linearity": None, "asymmetry": None, "probes": {}}
    if peak >= INERT:
        h = _mag(half.get(moved[0][0], 0.0))
        rec["linearity"] = round(h / peak, 3)
        n = _mag(neg.get(moved[0][0], 0.0))
        rec["asymmetry"] = round(n / peak, 3)
        for side in ("L", "R"):
            for kind2 in ("arm", "leg"):
                tip = full.get("%s_%s_tip" % (kind2, side)); off = full.get("%s_%s_mid_off" % (kind2, side))
                rt = full.get("%s_%s_root" % (kind2, side)); ext = full.get("%s_%s_extension" % (kind2, side))
                if tip is None or off is None or rt is None:
                    continue
                if not (tip.length < SWIVEL_TIP and off.length > SWIVEL_MID):
                    continue
                rec["limb"] = "%s_%s" % (kind2, side)
                rec["root_moved"] = round(rt.length, 6)
                rec["extension_change"] = round(ext, 6)
                if rt.length > SWIVEL_TIP:
                    rec["shape"] = "root_shift:%s_%s" % (kind2, side)
                elif abs(ext) > SWIVEL_TIP:
                    rec["shape"] = "bend:%s_%s" % (kind2, side)
                else:
                    rec["shape"] = "swivel:%s_%s" % (kind2, side)
    if rec["shape"] != "inert":
        for k, v in sorted(full.items(), key=lambda kv: -_mag(kv[1])):
            m = _mag(v)
            if m < (0.01 if k in dict(turned) or k.endswith("_fwd") else INERT):
                continue
            if isinstance(v, Vector):
                rec["probes"][k] = {"mag": round(m, 5), "dir": [round(c, 4) for c in fr.to(v)], "says": Frame.describe(fr.to(v))}
            else:
                rec["probes"][k] = {"delta": round(v, 5)}
            if len(rec["probes"]) >= 12:
                break
    return rec


def validate(r, rest, probes, loc_delta):
    rest.restore()
    base = probes.read()
    fr = Frame(r)
    _log("frame: forward %s left %s up %s" % (tuple(round(v, 2) for v in fr.fwd), tuple(round(v, 2) for v in fr.left), tuple(round(v, 2) for v in fr.up)))
    ok = True
    pb = r.pose.bones["root"]
    set_loc(pb, 0, loc_delta)
    bpy.context.view_layer.update()
    got = _delta(base, probes.read())
    rest.restore()
    pts = [v for k, v in got.items() if isinstance(v, Vector) and k.endswith(("_pos", "_tip", "_centroid"))]
    worst = max(abs(v.length - loc_delta) for v in pts) if pts else 1.0
    _log("validate: root +%.4f moved %d landmarks, worst error %.6f" % (loc_delta, len(pts), worst))
    ok &= worst < 1e-4
    after = probes.read()
    drift = max((_mag(v) for v in _delta(base, after).values()), default=0.0)
    _log("validate: restore() drift %.8f" % drift)
    ok &= drift < 1e-6
    # the jaw: known from tools/anim_twitch.py, +X on `lowerjaw` LIFTS the chin (closes)
    if "jaw_dz" in base and "lowerjaw" in r.pose.bones:
        set_rot(r.pose.bones["lowerjaw"], 0, -ROT_DELTA)
        bpy.context.view_layer.update()
        dz = probes.read()["jaw_dz"] - base["jaw_dz"]
        rest.restore()
        _log("validate: lowerjaw rotX -0.35 changes jaw_dz by %+.4f (expected +: the mouth opens)" % dz)
        ok &= dz > 0
    if not ok:
        raise RuntimeError("bone_atlas: the harness failed its own known answers")


def build(out_dir, only=None, body_name=None):
    out_dir = os.path.abspath(out_dir)
    r = rig()
    mesh = body(r, body_name)
    _log("rig %s, body %s (%d verts)" % (r.name, mesh.name, len(mesh.data.vertices)))
    zero_pose(r, 1.0)
    size = max(mesh.dimensions)
    loc_delta = size * LOC_FRACTION
    _log("body size %.4f (rig m); rot delta %.3f rad (%.1f deg), loc delta %.4f" % (size, ROT_DELTA, math.degrees(ROT_DELTA), loc_delta))
    probes = Probes(r, mesh)
    iks = ik_controls(r)
    names = only or controls(r)
    records = []
    for ikfk, group in ((1.0, [n for n in names if n not in iks]), (0.0, [n for n in names if n in iks])):
        if not group:
            continue
        zero_pose(r, ikfk)
        rest = Rest(r)
        if ikfk == 1.0:
            validate(r, rest, probes, loc_delta)
        rest.restore()
        base = probes.read()
        _log("probing %d controls with IK_FK = %.0f" % (len(group), ikfk))
        for i, name in enumerate(group):
            if name not in r.pose.bones:
                continue
            for kind, axis in channels(r, name):
                d = ROT_DELTA if kind == "rot" else loc_delta
                records.append(probe_channel(r, rest, probes, name, kind, axis, d, base, ikfk))
            if (i + 1) % 20 == 0:
                _log("  %d/%d bones" % (i + 1, len(group)))
        rest.restore()
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    path = os.path.join(out_dir, "atlas.json")
    with open(path, "w") as f:
        json.dump({"file": bpy.data.filepath, "rig": r.name, "body": mesh.name, "size": round(size, 5), "rot_delta": ROT_DELTA,
                   "loc_delta": round(loc_delta, 5), "records": records}, f, indent=1)
    _log("wrote %s (%d channels)" % (path, len(records)))
    _log("  inert: %d, twist-only: %d, swivels: %d" % (sum(1 for x in records if x["shape"] == "inert"), sum(1 for x in records if x["shape"] == "twist"),
                                                       sum(1 for x in records if x["shape"].startswith("swivel"))))
    return records


# --------------------------------------------------------------- the pictures

KEY_CONTROLS = ("root", "torso", "hips", "chest", "spine_fk", "neck", "head", "lowerjaw", "tweak_lowerjaw",
                "shoulder.", "upper_arm_fk", "upper_arm_ik", "forearm_fk", "hand_fk", "hand_ik", "_master.",
                "thigh_fk", "thigh_ik", "shin_fk", "foot_fk", "foot_ik", "foot_heel_ik", "foot_spin_ik", "toe_fk", "toe_ik")
MIN_FRAME = 0.30
VIEWS = {"front": (0.0, -1.0), "side": (-1.0, 0.0), "quarter": (-0.75, -0.75)}


def _is_key(name):
    return any(name == k or name.startswith(k) for k in KEY_CONTROLS)


class _RenderState(object):
    """Workbench, the bare body alone, restored afterwards (nothing is saved anyway)."""

    def __init__(self, mesh):
        self.mesh = mesh

    def __enter__(self):
        self.sc = bpy.context.scene
        self.hidden = []
        for o in bpy.data.objects:
            if o is not self.mesh and o.type in ('MESH', 'CURVE', 'FONT', 'SURFACE') and not o.hide_render:
                o.hide_render = True
                self.hidden.append(o)
        self.saved = (self.sc.render.engine, self.sc.render.resolution_x, self.sc.render.resolution_y, self.sc.render.film_transparent)
        self.sc.render.engine = 'BLENDER_WORKBENCH'
        self.sc.display.shading.light = 'STUDIO'
        self.sc.display.shading.color_type = 'SINGLE'
        self.sc.display.shading.single_color = (0.75, 0.72, 0.66)
        self.sc.render.film_transparent = False
        self.sc.render.image_settings.file_format = 'PNG'
        self.sc.render.image_settings.color_mode = 'RGBA'
        return self

    def __exit__(self, *a):
        for o in self.hidden:
            o.hide_render = False
        self.sc.render.engine, self.sc.render.resolution_x, self.sc.render.resolution_y, self.sc.render.film_transparent = self.saved


def _read_png(path, np):
    img = bpy.data.images.load(path)
    try:
        w, h = img.size
        buf = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        return buf.reshape(h, w, 4)[::-1].copy()
    finally:
        bpy.data.images.remove(img)


def sheets(out_dir, records, cell=420, only=None, body_name=None):
    """Render every non-inert key channel as a  -delta | rest | +delta  strip: red / grey / green borders."""
    out_dir = os.path.abspath(out_dir)
    import numpy as np
    r = rig()
    mesh = body(r, body_name)
    iks = ik_controls(r)
    size = max(mesh.dimensions)
    by_bone = {}
    for rec in records:
        if rec["shape"] == "inert" or not _is_key(rec["bone"]):
            continue
        if only and rec["bone"] not in only:
            continue
        by_bone.setdefault(rec["bone"], []).append(rec)
    _log("rendering %d bones, %d channels" % (len(by_bone), sum(len(v) for v in by_bone.values())))
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    tmp = os.path.join(out_dir, "_cell.png")
    cam_data = bpy.data.cameras.new("BA_Cam")
    cam_data.type = 'ORTHO'
    cam_data.sensor_fit = 'VERTICAL'
    cam = bpy.data.objects.new("BA_Cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    written = []

    def co():
        dg = bpy.context.evaluated_depsgraph_get()
        ev = mesh.evaluated_get(dg)
        me = ev.to_mesh()
        M = mesh.matrix_world
        out = [M @ v.co for v in me.vertices]
        ev.to_mesh_clear()
        return out

    try:
        with _RenderState(mesh) as st:
            sc = st.sc
            sc.camera = cam
            sc.render.resolution_x = sc.render.resolution_y = cell
            sc.render.resolution_percentage = 100
            for bone_name, recs in sorted(by_bone.items()):
                ikfk = 0.0 if bone_name in iks else 1.0
                zero_pose(r, ikfk)
                rest = Rest(r)
                rest.restore()
                base_co = co()
                pts, disp_of = [], {}
                for rec in recs:
                    kind, ax = rec["channel"][:3], "XYZ".index(rec["channel"][3])
                    ends = []
                    for amount in (-rec["delta"], rec["delta"]):
                        rest.restore()
                        (set_rot if kind == "rot" else set_loc)(r.pose.bones[bone_name], ax, amount)
                        bpy.context.view_layer.update()
                        ends.append(co())
                    thr = 0.15 * max(rec["peak"], 0.01)
                    moved = [i for i in range(len(base_co)) if max((ends[0][i] - base_co[i]).length, (ends[1][i] - base_co[i]).length) > thr]
                    disp_of[rec["channel"]] = (ends[1][moved[0]] - ends[0][moved[0]]) if moved else Vector((0, 1, 0))
                    pts += [p for i in moved for p in (ends[0][i], ends[1][i], base_co[i])]
                pts = pts or base_co
                lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
                hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
                centre = (lo + hi) * 0.5
                cam_data.ortho_scale = max(max(hi - lo), size * MIN_FRAME) * 1.35
                big = max(recs, key=lambda x: max(x["peak"], x["turn_peak"] * 0.05))["channel"]
                dxy = Vector((disp_of[big].x, disp_of[big].y))
                vname = "front"
                if dxy.length > 1e-6:
                    dxy.normalize()
                    vname = min(VIEWS, key=lambda v: abs(Vector(VIEWS[v]).normalized().dot(dxy)))
                d = Vector(VIEWS[vname] + (0.0,)).normalized()
                cam.rotation_euler = (math.pi / 2.0, 0.0, math.atan2(d.y, d.x) + math.pi / 2.0)
                cam.location = centre + d * (size * 6.0)
                cam.location.z = centre.z
                rows = []
                for rec in recs:
                    kind, ax = rec["channel"][:3], "XYZ".index(rec["channel"][3])
                    states = []
                    for k, amount in enumerate((-rec["delta"], 0.0, rec["delta"])):
                        rest.restore()
                        if amount:
                            (set_rot if kind == "rot" else set_loc)(r.pose.bones[bone_name], ax, amount)
                        bpy.context.view_layer.update()
                        sc.render.filepath = tmp
                        bpy.ops.render.render(write_still=True)
                        px = _read_png(tmp, np)
                        col = ((0.85, 0.25, 0.2), (0.45, 0.45, 0.5), (0.25, 0.8, 0.35))[k]
                        for w in range(4):
                            px[w, :, :3] = col; px[-1 - w, :, :3] = col; px[:, w, :3] = col; px[:, -1 - w, :3] = col
                        states.append(px)
                    rows.append(np.concatenate(states, axis=1))
                grid = np.concatenate(rows, axis=0)
                p = os.path.join(out_dir, "%s.png" % bone_name.replace(".", "_"))
                img = bpy.data.images.new("BA_G", grid.shape[1], grid.shape[0], alpha=True, float_buffer=False)
                try:
                    img.pixels.foreach_set(grid[::-1].ravel())
                    img.filepath_raw = p
                    img.file_format = 'PNG'
                    img.save()
                finally:
                    bpy.data.images.remove(img)
                written.append((bone_name, [x["channel"] for x in recs], p))
                _log("  %-24s %s (%s view)" % (bone_name, " ".join(x["channel"] for x in recs), vname))
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cam_data)
    _index(out_dir, written, records)
    return written


def _index(out_dir, written, records):
    byk = {(rec["bone"], rec["channel"]): rec for rec in records}
    p = os.path.join(out_dir, "index.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write("<meta charset=utf-8><style>body{background:#16161a;color:#ddd;font:13px/1.5 system-ui,sans-serif;margin:24px}"
                "h2{margin:32px 0 4px;color:#fff}img{max-width:100%;border:1px solid #333}td{padding:2px 10px;vertical-align:top}"
                ".r{color:#e04030}.g{color:#40cc55}</style>\n")
        f.write("<h1>Bone atlas: the shared skeleton rig</h1><p>Each row is one channel: <span class=r>-delta</span> | rest | <span class=g>+delta</span>. "
                "Directions are in the character's frame (forward / left / up).</p>\n")
        for bone_name, chans, path in written:
            f.write("<h2>%s</h2><table>\n" % bone_name)
            for c in chans:
                rec = byk[(bone_name, c)]
                first = next(iter(rec["probes"].items()), None)
                f.write("<tr><td><b>%s</b></td><td>peak %.4f</td><td>%s</td><td>%s: %s</td></tr>\n"
                        % (c, rec["peak"], rec["shape"], first[0] if first else "", (first[1].get("says") or "%+.4f" % first[1].get("delta", 0.0)) if first else ""))
            f.write("</table><img src='%s'>\n" % os.path.basename(path))
    _log("wrote %s" % p)


def summary(records, out_dir):
    path = os.path.join(out_dir, "ATLAS.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("Bone atlas of RIG-Meta-Rig, measured from the identity rest pose on the bare Knight body.\n"
                "Directions: forward / left / up in the character's frame. rot delta 0.35 rad, IK_FK per record.\n")
        cur = None
        for rec in records:
            if rec["bone"] != cur:
                cur = rec["bone"]
                f.write("\n%s   [%s, IK_FK %.0f]\n" % (cur, rec["rotation_mode"], rec["ikfk"]))
            head = rec["probes"].get(next(iter(rec["probes"])), {}) if rec["probes"] else {}
            f.write("  %-6s peak %7.4f turn %6.3f lin %-6s asym %-6s  %-16s %s\n"
                    % (rec["channel"], rec["peak"], rec["turn_peak"], rec["linearity"], rec["asymmetry"], rec["shape"], head.get("says", "")))
            for k, p in list(rec["probes"].items())[:5]:
                f.write("        %-22s %s\n" % (k, p.get("says", "%+.5f" % p.get("delta", 0.0))))
    _log("wrote %s" % path)


def query(records, probe, top=10):
    hits = []
    for rec in records:
        p = rec["probes"].get(probe)
        if p:
            hits.append((p.get("mag", abs(p.get("delta", 0.0))), rec, p))
    hits.sort(key=lambda h: -h[0])
    print("\n=== channels that move %r ===" % probe)
    for mag, rec, p in hits[:top]:
        print("  %-24s %-5s ikfk %.0f %8.4f   %s%s" % (rec["bone"], rec["channel"], rec["ikfk"], mag, p.get("says", "%+.4f" % p.get("delta", 0.0)),
                                                       "" if rec["shape"] == "move" else "   [%s]" % rec["shape"]))
    return hits[:top]


def _cli():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = "Rig/atlas"
    only = None
    body_name = None
    render = "--render" in argv
    for i, a in enumerate(argv):
        if a == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
        if a == "--only" and i + 1 < len(argv):
            only = argv[i + 1].split(",")
        if a == "--body" and i + 1 < len(argv):
            body_name = argv[i + 1]
    if "--sheets-from" in argv:
        with open(os.path.join(out, "atlas.json")) as f:
            recs = json.load(f)["records"]
        sheets(os.path.join(out, "sheets"), recs, only=only, body_name=body_name)
        return
    recs = build(out, only=only, body_name=body_name)
    summary(recs, out)
    if render:
        sheets(os.path.join(out, "sheets"), recs, only=only, body_name=body_name)
    for p in ("jaw_dz", "head_aim", "hilt_R", "back_of_hand_R", "footL_min_z", "arm_R_mid_off", "toe_L_tip"):
        query(recs, p)


if __name__ == "__main__":
    _cli()
