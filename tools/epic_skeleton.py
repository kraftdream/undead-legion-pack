"""The Epic-skeleton target: the UE5 mannequin's bone set with OUR bone directions (2026-10-05).

    python tools/epic_skeleton.py          -> Rig/epic_skeleton.json (+ a report)

Reads Rig/skeleton_rig.json (the library rig's deform bones, Blender metres, Blender axes) and
Rig/ue5_mannequin_refpose.json (SKM_Manny's reference skeleton dumped from the editor with
tools/ue/dump_refpose.py: every bone's component-space frame) and writes, for every bone of the
mannequin hierarchy plus our extras (two jaw bones, two pelvis helpers), its parent, the DEF bone
that drives it, its position and its frame in Unreal component space.

The frame rule: the mannequin's frame for that bone, re-aimed by the least rotation that takes the
mannequin's bone axis (its local X, pointing toward the child on most bones and toward the PARENT on
the right arms and left legs: `sign`) onto our bone's direction. So the local-axis convention is the
mannequin's (what makes mannequin animations play unchanged: Unreal stores absolute local rotations,
and with the same hierarchy and the same bone frames the animated world frames are the mannequin's),
while the positions and proportions are ours. The three spine bones become five at the mannequin's
stations along our spine, each rigid with the DEF bone whose span contains its head; the twist bones
sit at the mannequin's stations along their parent, rigid with it; the ik bones copy the hands and
feet. Nothing here changes how our own clips deform: every target bone moves rigidly with one DEF bone.

Space: Unreal component space, cm, the character facing +Y with its left at +X (the mannequin's
layout and the one our current import already has). Blender armature space maps into it by
(x, y, z) -> (x, -y, z) x 180 (SCALE 1.8 x 100), verified on all 68 bones of the current export.
"""
import json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = 180.0                     # Blender rig metres -> engine cm


def M(v):
    return [v[0], -v[1], v[2]]


def sub(a, b): return [a[i] - b[i] for i in range(3)]
def add(a, b): return [a[i] + b[i] for i in range(3)]
def mul(a, s): return [a[i] * s for i in range(3)]
def dot(a, b): return sum(a[i] * b[i] for i in range(3))
def cross(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
def norm(v):
    l = math.sqrt(dot(v, v)) or 1.0
    return [c / l for c in v]
def lerp(a, b, t): return [a[i] + (b[i] - a[i]) * t for i in range(3)]


def rot_between(a, b):
    """3x3 matrix of the least rotation taking unit vector a onto unit vector b (Rodrigues)."""
    v = cross(a, b); c = dot(a, b); s = math.sqrt(dot(v, v))
    if s < 1e-9:
        if c > 0:
            return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        # antiparallel: 180 deg about any axis perpendicular to a
        p = norm(cross(a, [1, 0, 0] if abs(a[0]) < 0.9 else [0, 1, 0]))
        return [[2 * p[i] * p[j] - (1 if i == j else 0) for j in range(3)] for i in range(3)]
    k = norm(v); ang = math.atan2(s, c)
    K = [[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]]
    I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    KK = [[sum(K[i][m] * K[m][j] for m in range(3)) for j in range(3)] for i in range(3)]
    return [[I[i][j] + math.sin(ang) * K[i][j] + (1 - math.cos(ang)) * KK[i][j] for j in range(3)] for i in range(3)]


def apply(R, v):
    return [sum(R[i][j] * v[j] for j in range(3)) for i in range(3)]


def main():
    rig = json.load(open(os.path.join(ROOT, "Rig", "skeleton_rig.json")))
    man = {b["name"]: b for b in json.load(open(os.path.join(ROOT, "Rig", "ue5_mannequin_refpose.json")))["bones"]}
    D = {}                                             # DEF bone -> (head, tail, dir) in UE cm
    for n, b in rig.items():
        if b.get("deform") or n == "root":
            h = mul(M(b["head"]), SCALE); t = mul(M(b["tail"]), SCALE)
            D[n] = (h, t, norm(sub(t, h)))

    def seg(a, b):                                     # direction from DEF a's head to DEF b's head
        return norm(sub(D[b][0], D[a][0]))

    # our spine polyline (Hips head .. Neck head) and the mannequin's stations along its own
    chain = ["DEF-spine", "DEF-spine.001", "DEF-spine.002", "DEF-spine.003", "DEF-spine.004"]
    pts = [D[n][0] for n in chain]
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + math.sqrt(dot(sub(pts[i], pts[i - 1]), sub(pts[i], pts[i - 1]))))
    ours = [c / cum[-1] for c in cum]                  # Hips 0, Spine, Spine1, Spine2, Neck 1
    mchain = ["pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01"]
    mp = [man[n]["pos"] for n in mchain]
    mcum = [0.0]
    for i in range(1, len(mp)):
        mcum.append(mcum[-1] + math.sqrt(dot(sub(mp[i], mp[i - 1]), sub(mp[i], mp[i - 1]))))
    mfrac = {n: c / mcum[-1] for n, c in zip(mchain, mcum)}

    def spine_point(f):
        for i in range(len(ours) - 1):
            if f <= ours[i + 1] or i == len(ours) - 2:
                t = (f - ours[i]) / (ours[i + 1] - ours[i])
                return lerp(pts[i], pts[i + 1], t), chain[i], t
        raise AssertionError

    bones = []

    def put(name, parent, source, pos, frame, kind, station=None, note=""):
        bones.append({"name": name, "parent": parent, "source": source, "pos": [round(c, 4) for c in pos],
                      "x": [round(c, 6) for c in frame[0]], "y": [round(c, 6) for c in frame[1]], "z": [round(c, 6) for c in frame[2]],
                      "kind": kind, "station": station, "note": note})

    def reaim(mname, tX):
        m = man[mname]
        R = rot_between(norm(m["x"]), norm(tX))
        return (apply(R, m["x"]), apply(R, m["y"]), apply(R, m["z"]))

    IDENT = ([1, 0, 0], [0, 1, 0], [0, 0, 1])
    put("root", "", "root", [0, 0, 0], IDENT, "root")
    # pelvis + the five spine bones
    put("pelvis", "root", "DEF-spine", D["DEF-spine"][0], reaim("pelvis", seg("DEF-spine", "DEF-spine.001")), "bone")
    for k in ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05"):
        p, src, t = spine_point(mfrac[k])
        i = chain.index(src)
        put(k, bones[-1]["name"], src, p, reaim(k, seg(src, chain[i + 1])), "split", station=round(t, 4),
            note="at %.3f of our spine (%s span, %.2f of it)" % (mfrac[k], src, t))
    put("neck_01", "spine_05", "DEF-spine.004", D["DEF-spine.004"][0], reaim("neck_01", D["DEF-spine.004"][2]), "bone")
    put("neck_02", "neck_01", "DEF-spine.005", D["DEF-spine.005"][0], reaim("neck_02", D["DEF-spine.005"][2]), "bone")
    put("head", "neck_02", "DEF-spine.006", D["DEF-spine.006"][0], reaim("head", D["DEF-spine.006"][2]), "bone")
    # extras: the jaw under the head (the head's convention re-aimed on the jaw bones)
    hx = man["head"]
    put("jaw_01", "head", "DEF-lowerjaw", D["DEF-lowerjaw"][0], reaim("head", D["DEF-lowerjaw"][2]), "extra")
    put("jaw_02", "jaw_01", "DEF-lowerjaw.001", D["DEF-lowerjaw.001"][0], reaim("head", D["DEF-lowerjaw.001"][2]), "extra")

    for S, s in (("L", "l"), ("R", "r")):
        sign = 1.0 if S == "L" else -1.0             # the mannequin's right arm and fingers point toward the parent
        def arm(name, src, dir_, mref=None):
            put(name % s, None, src, D[src][0], reaim((mref or name) % s, mul(dir_, sign)), "bone")
        put("clavicle_" + s, "spine_05", "DEF-shoulder." + S, D["DEF-shoulder." + S][0],
            reaim("clavicle_" + s, mul(seg("DEF-shoulder." + S, "DEF-upper_arm." + S), sign)), "bone")
        put("upperarm_" + s, "clavicle_" + s, "DEF-upper_arm." + S, D["DEF-upper_arm." + S][0],
            reaim("upperarm_" + s, mul(D["DEF-upper_arm." + S][2], sign)), "bone")
        ua = D["DEF-upper_arm." + S]
        for tw, st in (("upperarm_twist_01_" + s, 1 / 3.0), ("upperarm_twist_02_" + s, 2 / 3.0)):
            put(tw, "upperarm_" + s, "DEF-upper_arm." + S, lerp(ua[0], ua[1], st), reaim("upperarm_" + s, mul(ua[2], sign)), "twist", station=st)
        put("lowerarm_" + s, "upperarm_" + s, "DEF-forearm." + S, D["DEF-forearm." + S][0],
            reaim("lowerarm_" + s, mul(D["DEF-forearm." + S][2], sign)), "bone")
        fa = D["DEF-forearm." + S]
        for tw, st in (("lowerarm_twist_02_" + s, 1 / 3.0), ("lowerarm_twist_01_" + s, 2 / 3.0)):
            put(tw, "lowerarm_" + s, "DEF-forearm." + S, lerp(fa[0], fa[1], st), reaim("lowerarm_" + s, mul(fa[2], sign)), "twist", station=st)
        put("hand_" + s, "lowerarm_" + s, "DEF-hand." + S, D["DEF-hand." + S][0],
            reaim("hand_" + s, mul(D["DEF-hand." + S][2], sign)), "bone")
        for fname, palm in (("index", "01"), ("middle", "02"), ("ring", "03"), ("pinky", "04")):
            mc = "DEF-palm.%s.%s" % (palm, S)
            put("%s_metacarpal_%s" % (fname, s), "hand_" + s, mc, D[mc][0],
                reaim("%s_metacarpal_%s" % (fname, s), mul(seg(mc, "DEF-f_%s.01.%s" % (fname, S)), sign)), "bone")
            prev = "%s_metacarpal_%s" % (fname, s)
            for k in ("01", "02", "03"):
                src = "DEF-f_%s.%s.%s" % (fname, k, S)
                nm = "%s_%s_%s" % (fname, k, s)
                put(nm, prev, src, D[src][0], reaim(nm, mul(D[src][2], sign)), "bone"); prev = nm
        prev = "hand_" + s
        for k in ("01", "02", "03"):
            src = "DEF-thumb.%s.%s" % (k, S); nm = "thumb_%s_%s" % (k, s)
            put(nm, prev, src, D[src][0], reaim(nm, mul(D[src][2], sign)), "bone"); prev = nm
        # legs: the mannequin's LEFT leg points toward the parent, the right toward the child
        lsign = -1.0 if S == "L" else 1.0
        th, sh, ft, toe = D["DEF-thigh." + S], D["DEF-shin." + S], D["DEF-foot." + S], D["DEF-toe." + S]
        put("thigh_" + s, "pelvis", "DEF-thigh." + S, th[0], reaim("thigh_" + s, mul(th[2], lsign)), "bone")
        for tw, st in (("thigh_twist_01_" + s, 1 / 3.0), ("thigh_twist_02_" + s, 2 / 3.0)):
            put(tw, "thigh_" + s, "DEF-thigh." + S, lerp(th[0], th[1], st), reaim("thigh_" + s, mul(th[2], lsign)), "twist", station=st)
        put("calf_" + s, "thigh_" + s, "DEF-shin." + S, sh[0], reaim("calf_" + s, mul(sh[2], lsign)), "bone")
        for tw, st in (("calf_twist_02_" + s, 1 / 3.0), ("calf_twist_01_" + s, 2 / 3.0)):
            put(tw, "calf_" + s, "DEF-shin." + S, lerp(sh[0], sh[1], st), reaim("calf_" + s, mul(sh[2], lsign)), "twist", station=st)
        # the foot's X continues the shin line (the mannequin's foot points up/down the leg, not along the sole)
        put("foot_" + s, "calf_" + s, "DEF-foot." + S, ft[0], reaim("foot_" + s, mul(sh[2], lsign)), "bone")
        put("ball_" + s, "foot_" + s, "DEF-toe." + S, toe[0], reaim("ball_" + s, mul(toe[2], sign)), "bone")
        # pelvis helpers (Rigify's DEF-pelvis.L/R carry skirt and robe weights)
        pv = D["DEF-pelvis." + S]
        put("pelvis_" + s, "pelvis", "DEF-pelvis." + S, pv[0], reaim("pelvis", pv[2]), "extra")

    # ik bones: rigid copies of the hands and feet (the mannequin's ik frames equal those bones' frames)
    B = {b["name"]: b for b in bones}
    put("ik_foot_root", "root", "root", [0, 0, 0], IDENT, "copy")
    for s in ("l", "r"):
        f = B["foot_" + s]
        put("ik_foot_" + s, "ik_foot_root", f["source"], f["pos"], (f["x"], f["y"], f["z"]), "copy")
    put("ik_hand_root", "root", "root", [0, 0, 0], IDENT, "copy")
    hr, hl = B["hand_r"], B["hand_l"]
    put("ik_hand_gun", "ik_hand_root", hr["source"], hr["pos"], (hr["x"], hr["y"], hr["z"]), "copy")
    put("ik_hand_l", "ik_hand_gun", hl["source"], hl["pos"], (hl["x"], hl["y"], hl["z"]), "copy")
    put("ik_hand_r", "ik_hand_gun", hr["source"], hr["pos"], (hr["x"], hr["y"], hr["z"]), "copy")
    put("interaction", "root", "root", [0, 0, 0], IDENT, "copy")
    put("center_of_mass", "root", "root", [0, 0, 0], IDENT, "copy")

    # fix the spine parents (put() wrote bones[-1] for the first spine bone)
    for i, b in enumerate(bones):
        if b["name"] == "spine_01":
            b["parent"] = "pelvis"
    names = [b["name"] for b in bones]
    missing = [n for n in man if n not in names]
    extra = [n for n in names if n not in man]
    assert not missing, "mannequin bones not covered: %s" % missing
    for b in bones:
        assert b["parent"] == "" or b["parent"] in names, b
        if b["name"] in man and b["name"] != "root":
            assert man[b["name"]]["parent"] == b["parent"], (b["name"], b["parent"], man[b["name"]]["parent"])
    # the weight rules: which target bone a DEF bone's weight goes to, by station along the DEF bone
    spine_rules = {}
    for b in bones:
        if b["kind"] == "split":
            spine_rules.setdefault(b["source"], []).append((b["station"], b["name"]))
    weights = {"split": {src: sorted(v) for src, v in spine_rules.items()},
               "twist": {b["source"]: sorted([(c["station"], c["name"]) for c in bones if c["kind"] == "twist" and c["source"] == b["source"]])
                         for b in bones if b["kind"] == "twist"}}
    out = {"scale": SCALE, "facing": "+Y, left at +X (Unreal component space, cm)", "bones": bones, "weights": weights,
           "spine_fractions": {"ours": dict(zip(chain, ours)), "mannequin": mfrac}}
    path = os.path.join(ROOT, "Rig", "epic_skeleton.json")
    json.dump(out, open(path, "w"), indent=1)
    print("wrote %s: %d bones (%d mannequin + %d extra: %s)" % (os.path.relpath(path, ROOT), len(bones), len(man), len(extra), extra))
    print("spine stations ours", {k: round(v, 3) for k, v in zip(chain, ours)})
    print("spine stations mannequin", {k: round(v, 3) for k, v in mfrac.items()})
    # report: how far each re-aimed frame turned from the mannequin's (the A-pose difference per bone)
    for b in bones:
        if b["name"] in man:
            m = man[b["name"]]
            ang = math.degrees(math.acos(max(-1, min(1, dot(norm(m["x"]), norm(b["x"]))))))
            if ang > 5:
                print("  %-22s re-aimed %5.1f deg from the mannequin's bone axis" % (b["name"], ang))
    print("weight rules:", json.dumps(weights))


if __name__ == "__main__":
    main()
