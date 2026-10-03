"""Put SAM 3D Body's hand orientation onto the GVHMR / SMPL motion (tools/gvhmr_export.py's .npz).

Runs in the GVHMR environment (scipy):

    wsl -d Ubuntu -- /mnt/d/GVHMR/.venv/bin/python tools/sam3d_wrists.py SMPL.npz SAM.npz OUT.npz [--hands LR] [--smooth 1] [--max-swing 80]

GVHMR estimates the body from 17 keypoints and never sees the hand: its wrist barely moves (~14 deg over a sword
swing). SAM 3D Body (tools/sam3d_hands.py, every Nth frame) sees the hand: the wrist, the three knuckles, the elbow
and the shoulder, in 3D. What is transferred is the hand's orientation RELATIVE TO THE FOREARM, built from joint
positions only (no joint-frame conventions of either body model):

  forearm frame B = [f, r, f x r]   f = elbow -> wrist, r = the upper arm (elbow -> shoulder) projected off f, blended
                                     toward the shoulder line when the elbow is near straight (no bend plane there)
  hand directions  h = wrist -> middle knuckle (the hand's forward), n = (index knuckle - wrist) x (pinky knuckle - wrist)
                                     (the palm normal; the same formula per side in both models, so its sign transfers)

h and n are read in SAM's forearm frame and rebuilt in the SMPL forearm frame of the same video frame, then the SMPL
wrist's global rotation is the one that maps the rest hand's (h, n) onto them. Its rotation relative to the elbow is
split into the TWIST about the forearm axis, which goes on the elbow joint as forearm pronation (a human wrist has
none), and the SWING, which stays on the wrist (clamped to --max-swing degrees). Between SAM's frames the two
rotations are slerped; `--smooth N` low-passes them ([1,2,1], N passes) against SAM's per-frame jitter.
"""
import sys, numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

argv = sys.argv[1:]
smpl_path, sam_path, dst = argv[0], argv[1], argv[2]
def arg(k, d):
    return argv[argv.index(k) + 1] if k in argv else d
HANDS = arg("--hands", "LR").upper()
SMOOTH = int(arg("--smooth", "1"))
MAX_SWING = float(arg("--max-swing", "80"))

S = np.load(smpl_path); names = [str(n) for n in S["names"]]; parents = [int(p) for p in S["parents"]]
rest, quat, transl = S["rest"].astype(np.float64), S["quat"].astype(np.float64), S["transl"].astype(np.float64)
rest_hands = S["rest_hands"].astype(np.float64)          # [L, R] x [index1, middle1, pinky1]
F = quat.shape[0]
Z = np.load(sam_path); sf = Z["frame"].astype(int); kp = Z["kp3d"].astype(np.float64)   # (n, 70, 3), camera frame
J = {n: i for i, n in enumerate(names)}
# SAM MHR70 keypoint indices
K = {"L": dict(sh=5, el=7, wr=62, idx=49, mid=53, pky=61, osh=6), "R": dict(sh=6, el=8, wr=41, idx=28, mid=32, pky=40, osh=5)}
SM = {"L": dict(sh=J["left_shoulder"], el=J["left_elbow"], wr=J["left_wrist"], osh=J["right_shoulder"], rh=0),
      "R": dict(sh=J["right_shoulder"], el=J["right_elbow"], wr=J["right_wrist"], osh=J["left_shoulder"], rh=1)}


def fk(q):
    """Global rotations (F, J, 3, 3) and positions (F, J, 3) of the identity-rest chain."""
    Rl = R.from_quat(q[..., [1, 2, 3, 0]].reshape(-1, 4)).as_matrix().reshape(F, len(names), 3, 3)
    Rg = np.zeros_like(Rl); P = np.zeros((F, len(names), 3))
    for j, p in enumerate(parents):
        if p < 0:
            Rg[:, j] = Rl[:, j]; P[:, j] = transl
        else:
            Rg[:, j] = Rg[:, p] @ Rl[:, j]; P[:, j] = P[:, p] + np.einsum("fij,j->fi", Rg[:, p], rest[j] - rest[p])
    return Rl, Rg, P


def unit(v):
    n = np.linalg.norm(v); return v / n if n > 1e-9 else v


def forearm_frame(sh, el, wr, osh):
    f = unit(wr - el); u = unit(sh - el); l = unit(sh - osh)
    bend = np.degrees(np.arccos(np.clip(np.dot(-f, u), -1, 1)))         # interior elbow angle: 180 = straight
    w = np.clip((180.0 - bend - 10.0) / 15.0, 0.0, 1.0)                 # 1 when bent > 25 deg, 0 when straighter than 10
    def perp(v):
        v = v - f * np.dot(v, f); return unit(v)
    r = perp(w * perp(u) + (1.0 - w) * perp(l))
    if np.linalg.norm(r) < 1e-6:
        r = perp(np.array([0.0, 0.0, 1.0]))
    return np.stack([f, r, np.cross(f, r)], 1)                           # columns


def triad(h, n):
    h = unit(h); n = unit(n - h * np.dot(n, h)); return np.stack([h, n, np.cross(h, n)], 1)


Rl, Rg, P = fk(quat)
if "joints_check" in S.files:
    err = np.abs(P[:, :22] - S["joints_check"]).max()
    assert err < 1e-3, "FK mismatch %.4f" % err

out_q = quat.copy()
report = {}
for side in HANDS:
    k, s = K[side], SM[side]
    rh = rest_hands[s["rh"]]; wr_rest = rest[s["wr"]]
    M_rest = triad(rh[1] - wr_rest, np.cross(rh[0] - wr_rest, rh[2] - wr_rest))
    a = unit(rest[s["wr"]] - rest[s["el"]])                               # the forearm axis in the elbow's (identity) rest frame
    twists, swings, keep = [], [], []
    for n_, f in enumerate(sf):
        if f >= F:
            continue
        p = kp[n_]
        if not np.all(np.isfinite(p[[k["wr"], k["idx"], k["mid"], k["pky"]]])):
            continue
        B_s = forearm_frame(p[k["sh"]], p[k["el"]], p[k["wr"]], p[k["osh"]])
        h_s = p[k["mid"]] - p[k["wr"]]; n_s = np.cross(p[k["idx"]] - p[k["wr"]], p[k["pky"]] - p[k["wr"]])
        if np.linalg.norm(h_s) < 1e-4 or np.linalg.norm(n_s) < 1e-8:
            continue
        B_g = forearm_frame(P[f, s["sh"]], P[f, s["el"]], P[f, s["wr"]], P[f, s["osh"]])
        h_t = B_g @ (B_s.T @ unit(h_s)); n_t = B_g @ (B_s.T @ unit(n_s))
        Rw = triad(h_t, n_t) @ M_rest.T                                 # the wrist's global rotation that gives the hand (h_t, n_t)
        Rloc = Rg[f, s["el"]].T @ Rw                                     # relative to the elbow's global frame
        q = R.from_matrix(Rloc).as_quat()                                # x y z w
        w, v = q[3], q[:3]
        tw = np.r_[np.dot(v, a) * a, w]; tw /= np.linalg.norm(tw)        # twist about the forearm axis (left factor)
        sw = (R.from_quat(tw).inv() * R.from_quat(q))                    # the swing: q = twist * swing
        ang = np.degrees(sw.magnitude())
        if ang > MAX_SWING:
            sw = R.from_rotvec(sw.as_rotvec() * (MAX_SWING / ang))
        twists.append(R.from_quat(tw)); swings.append(sw); keep.append(f)
    if len(keep) < 2:
        print("[sam3d_wrists] %s: too few frames" % side); continue
    keep = np.array(keep)
    def smooth(rots):
        for _ in range(SMOOTH):
            rots = [rots[0]] + [R.from_quat(unit(0.25 * q_(rots[i - 1], rots[i]) + 0.5 * rots[i].as_quat() + 0.25 * q_(rots[i + 1], rots[i]))) for i in range(1, len(rots) - 1)] + [rots[-1]]
        return rots
    def q_(r_, ref):
        q = r_.as_quat(); return q if np.dot(q, ref.as_quat()) >= 0 else -q
    twists, swings = smooth(twists), smooth(swings)
    t_all = np.clip(np.arange(F), keep[0], keep[-1])
    tw_i = Slerp(keep, R.concatenate(twists))(t_all); sw_i = Slerp(keep, R.concatenate(swings))(t_all)
    # write: elbow local' = elbow local * twist ; wrist local' = swing (the knuckle kids ride along)
    el, wr = s["el"], s["wr"]
    el_new = R.from_quat(quat[:, el][:, [1, 2, 3, 0]]) * tw_i
    out_q[:, el] = el_new.as_quat()[:, [3, 0, 1, 2]]
    out_q[:, wr] = sw_i.as_quat()[:, [3, 0, 1, 2]]
    sw_deg = np.degrees(np.array([r_.magnitude() for r_ in swings])); tw_deg = np.degrees(np.array([r_.magnitude() for r_ in twists]))
    old = np.degrees(R.from_quat(quat[keep, wr][:, [1, 2, 3, 0]]).magnitude())
    steps = np.degrees(np.array([(swings[i].inv() * swings[i + 1]).magnitude() for i in range(len(swings) - 1)]))
    report[side] = "%s hand: %d SAM frames %d..%d; wrist swing %.0f..%.0f deg (GVHMR's wrist was %.0f..%.0f), forearm twist %.0f..%.0f deg, worst step between SAM frames %.0f deg" % (
        side, len(keep), keep[0], keep[-1], sw_deg.min(), sw_deg.max(), old.min(), old.max(), tw_deg.min(), tw_deg.max(), steps.max())
    print("[sam3d_wrists]", report[side])

# keep the quaternion sign continuous (Blender interpolates component-wise)
for j in range(len(names)):
    for f in range(1, F):
        if np.dot(out_q[f, j], out_q[f - 1, j]) < 0:
            out_q[f, j] *= -1
data = {k: S[k] for k in S.files}; data["quat"] = out_q.astype(np.float32)
np.savez(dst, **data)
print("[sam3d_wrists] wrote", dst)
