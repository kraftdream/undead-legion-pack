"""GVHMR result (hmr4d_results.pt) -> a plain .npz the Blender side can read (smpl_to_armature.py).

Runs in the GVHMR environment (WSL, D:/GVHMR/.venv), not in Blender:

    wsl -d Ubuntu -- /mnt/d/GVHMR/.venv/bin/python tools/gvhmr_export.py RESULTS.pt OUT.npz [--fps 30] [--video IN.mp4]

What it writes, already in Blender's frame (Z up, the body's forward -Y, metres):
  names (22,)      SMPL-X body joint names (+ two static hand-direction joints, see below)
  parents (24,)    parent index, -1 for the pelvis
  rest (24, 3)     the performer's rest joints (their own betas, flat T-pose), FEET ON THE FLOOR (z = 0)
  quat (F, 24, 4)  each joint's LOCAL rotation (w, x, y, z) relative to its parent, identity = rest
  transl (F, 3)    the pelvis' world position per frame, floor at z = 0
  fps              the output frame rate (the video's, resampled to --fps when they differ)

The global solution (`smpl_params_global`: gravity-aligned, Y up) is used, not the camera-frame one.
SMPL rotates every joint about its own joint with world-aligned rest frames, so a bone whose rest
orientation is the identity reproduces it exactly: world(j) = world(parent) . local(j).
GVHMR does not recover hands; the wrist rotation is real, the fingers are flat. The two
`*_middle1` joints are static children of the wrists (the knuckle), only there so the retarget
can read the hand's direction.
"""
import sys, os, numpy as np, torch
from scipy.spatial.transform import Rotation as R, Slerp

argv = sys.argv[1:]
src, dst = argv[0], argv[1]
def arg(k, d):
    return argv[argv.index(k) + 1] if k in argv else d
FPS_OUT = float(arg("--fps", "30"))
VIDEO = arg("--video", "")
BODY_MODELS = arg("--body-models", "/mnt/d/GVHMR/inputs/checkpoints/body_models")

NAMES = ["pelvis", "left_hip", "right_hip", "spine1", "left_knee", "right_knee", "spine2", "left_ankle", "right_ankle",
         "spine3", "left_foot", "right_foot", "neck", "left_collar", "right_collar", "head", "left_shoulder",
         "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"]
PARENTS = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19]
HAND_KIDS = [("left_middle1", 20, 28), ("right_middle1", 21, 43)]   # SMPL-X joint 28 / 43 = the middle finger's knuckle

d = torch.load(src, map_location="cpu", weights_only=False)
g = d["smpl_params_global"]
body_pose = g["body_pose"].reshape(-1, 21, 3).numpy().astype(np.float64)
orient = g["global_orient"].numpy().astype(np.float64)
transl = g["transl"].numpy().astype(np.float64)
betas = g["betas"].float().mean(0, keepdim=True)
F = orient.shape[0]

fps_in = 30.0
if not VIDEO:
    cand = os.path.join(os.path.dirname(src), "0_input_video.mp4")
    VIDEO = cand if os.path.exists(cand) else ""
if VIDEO:
    import cv2
    cap = cv2.VideoCapture(VIDEO); v = cap.get(cv2.CAP_PROP_FPS); cap.release()
    if v and v > 1:
        fps_in = float(v)
print("[gvhmr_export] %d frames at %.3f fps (%s)" % (F, fps_in, os.path.basename(VIDEO) if VIDEO else "assumed"))

import smplx
bm = smplx.SMPLX(model_path=os.path.join(BODY_MODELS, "smplx", "SMPLX_NEUTRAL.npz"), use_pca=False, flat_hand_mean=True,
                 num_betas=betas.shape[1], batch_size=1)
with torch.no_grad():
    rest_out = bm(betas=betas)                                   # zero pose: the flat T-pose of this performer
    J_rest = rest_out.joints[0].numpy().astype(np.float64)      # (127, 3) SMPL-X joints, Y up
    v_rest = rest_out.vertices[0].numpy()
    # posed vertices per frame for the floor: chunks, CPU
    mins, J0s, Jall = [], [], []
    for a in range(0, F, 64):
        b = min(F, a + 64); n = b - a
        bm_n = smplx.SMPLX(model_path=os.path.join(BODY_MODELS, "smplx", "SMPLX_NEUTRAL.npz"), use_pca=False,
                           flat_hand_mean=True, num_betas=betas.shape[1], batch_size=n)
        o = bm_n(betas=betas.expand(n, -1), global_orient=torch.from_numpy(orient[a:b]).float(),
                 body_pose=torch.from_numpy(body_pose[a:b].reshape(n, -1)).float(), transl=torch.from_numpy(transl[a:b]).float())
        mins.append(o.vertices[:, :, 1].min(1).values.numpy()); J0s.append(o.joints[:, 0].numpy()); Jall.append(o.joints[:, :22].numpy())
    vmin = np.concatenate(mins); J0_posed = np.concatenate(J0s); J_posed = np.concatenate(Jall).astype(np.float64)

# --anchor-foot L|R[:frame]: that foot stood still in the recording, so any travel of it is the solver's drift.
# The whole body is shifted every frame so that foot (the mean of its ankle and ball joints) stays where it is
# on the reference frame (1-based, default 1), in all three axes (user, swing_1: "left foot is static, use it
# to fix the drift"). The rotations are untouched; the floor is measured after the shift.
ANCHOR = arg("--anchor-foot", "")
if ANCHOR:
    side, _, ref = ANCHOR.partition(":")
    ref = int(ref or 1) - 1
    ja, jb = (7, 10) if side.upper() == "L" else (8, 11)
    foot = 0.5 * (J_posed[:, ja] + J_posed[:, jb])
    off = foot - foot[ref]
    print("[gvhmr_export] anchor %s foot on frame %d: it travelled up to %.3f m horizontally, %.3f m vertically; removed"
          % (side.upper(), ref + 1, np.linalg.norm(off[:, [0, 2]], axis=1).max(), np.abs(off[:, 1]).max()))
    J_posed -= off[:, None, :]
    J0_posed = J0_posed - off
    vmin = vmin - off[:, 1]

# the floor: the clip's low percentile of per-frame lowest vertices (a jump does not lift it, one bad frame does not sink it)
floor = float(np.percentile(vmin, 5))
rest_floor = float(v_rest[:, 1].min())
if ANCHOR:
    # the anchored foot is the one on the ground: its ankle sits at the rest ankle's height above the rest floor
    # (the percentile follows the other foot, which the solver's depth error sinks ~10 cm during a lunge)
    floor = float(0.5 * (J_posed[ref, ja, 1] + J_posed[ref, jb, 1]) - 0.5 * (J_rest[ja, 1] + J_rest[jb, 1]) + rest_floor)
print("[gvhmr_export] floor %.3f (per-frame lowest %.3f..%.3f), rest feet %.3f" % (floor, vmin.min(), vmin.max(), rest_floor))

# rest joints (22 body + 2 knuckles), feet on the floor
rest = np.concatenate([J_rest[:22], J_rest[[k for _, _, k in HAND_KIDS]]], 0)
rest[:, 1] -= rest_floor
names = NAMES + [n for n, _, _ in HAND_KIDS]
parents = PARENTS + [p for _, p, _ in HAND_KIDS]

# pelvis world position per frame: SMPL puts the pelvis joint at J0 + transl (rotation about J0)
pelvis = J0_posed.astype(np.float64).copy()
pelvis[:, 1] -= floor

# local rotations: pelvis = global_orient, the rest = body_pose, the knuckles = identity
rots = np.zeros((F, len(names), 3))
rots[:, 0] = orient
rots[:, 1:22] = body_pose
quat_xyzw = R.from_rotvec(rots.reshape(-1, 3)).as_quat().reshape(F, len(names), 4)

# resample to the output rate (slerp per joint, linear for the pelvis)
if abs(fps_in - FPS_OUT) > 1e-3:
    t_in = np.arange(F) / fps_in
    n_out = int(np.floor(t_in[-1] * FPS_OUT + 1e-6)) + 1
    t_out = np.arange(n_out) / FPS_OUT
    qn = np.zeros((n_out, len(names), 4))
    for j in range(len(names)):
        qn[:, j] = Slerp(t_in, R.from_quat(quat_xyzw[:, j]))(t_out).as_quat()
    pelvis = np.stack([np.interp(t_out, t_in, pelvis[:, k]) for k in range(3)], 1)
    quat_xyzw = qn
    print("[gvhmr_export] resampled %d frames @ %.3f -> %d @ %.1f" % (F, fps_in, n_out, FPS_OUT))
    F = n_out
    fps = FPS_OUT
else:
    fps = fps_in

# Y up -> Z up: p_b = C p_s, R_b = C R_s C^-1 with C: (x, y, z) -> (x, -z, y). The SMPL rest faces +Z_s = -Y_b, the rig's forward.
C = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)
rest_b = rest @ C.T
pelvis_b = pelvis @ C.T
Rm = R.from_quat(quat_xyzw.reshape(-1, 4)).as_matrix()
Rb = np.einsum("ij,njk,lk->nil", C, Rm, C)                     # C R C^T
qb = R.from_matrix(Rb).as_quat().reshape(F, len(names), 4)      # x y z w
quat_wxyz = np.concatenate([qb[..., 3:4], qb[..., :3]], -1)
# keep the quaternion sign continuous per joint (Blender interpolates keys component-wise)
for j in range(len(names)):
    for f in range(1, F):
        if np.dot(quat_wxyz[f, j], quat_wxyz[f - 1, j]) < 0:
            quat_wxyz[f, j] *= -1

extra = {}
if fps == fps_in:
    # the body model's own posed joints (Blender frame, floored): what smpl_to_armature must reproduce
    jp = J_posed.copy(); jp[..., 1] -= floor
    extra["joints_check"] = (jp @ C.T).astype(np.float32)
np.savez(dst, **extra, names=np.array(names), parents=np.array(parents), rest=rest_b.astype(np.float32),
         quat=quat_wxyz.astype(np.float32), transl=pelvis_b.astype(np.float32), fps=np.float32(fps))
print("[gvhmr_export] wrote %s: %d joints, %d frames @ %.1f fps, pelvis rest z %.3f, hand knuckles %s"
      % (dst, len(names), F, fps, rest_b[0, 2], np.round(rest_b[-2:], 3).tolist()))
