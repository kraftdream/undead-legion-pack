"""SAM 3D Body on the frames of a video GVHMR already processed: per-frame 3D keypoints (body + hands) and joint
global rotations, for the hand-direction step (GVHMR sees 17 body keypoints and never observes the hand).

Runs in the SAM 3D Body environment (WSL, /mnt/d/Sam/.venv):

    wsl -d Ubuntu -- /mnt/d/Sam/.venv/bin/python tools/sam3d_hands.py VIDEO.mp4 GVHMR_RESULTS.pt OUT.npz [--step N] [--frames A:B] [--limit K]

The person box (GVHMR's bbx_xys: centre + square size per frame) and the camera intrinsics (K_fullimg) come from
the GVHMR run on the SAME video, so no detector is loaded. --step N processes every Nth frame (the hand's rotation
is smooth; the caller interpolates). Writes frame indices, the MHR70 3D keypoints (camera frame), the 2D keypoints,
the joint coords and the joint global rotations.
"""
import os, sys, time
import numpy as np, torch, cv2

argv = sys.argv[1:]
video, gv, dst = argv[0], argv[1], argv[2]
def arg(k, d):
    return argv[argv.index(k) + 1] if k in argv else d
STEP = int(arg("--step", "1"))
LIMIT = int(arg("--limit", "0"))
FR = arg("--frames", "")
SAM_ROOT = arg("--sam-root", "/mnt/d/Sam")

sys.path.insert(0, os.path.join(SAM_ROOT, "sam-3d-body"))
torch.set_num_threads(os.cpu_count() or 8)
from sam_3d_body import load_sam_3d_body, SAM3DBodyEstimator

d = torch.load(gv, map_location="cpu", weights_only=False)
bbx = d["bbx_xys"].numpy()            # (F, 3): centre x, centre y, size
K = d["K_fullimg"].numpy()            # (F, 3, 3)

cap = cv2.VideoCapture(video); frames = []
while True:
    ok, im = cap.read()
    if not ok: break
    frames.append(im)
cap.release()
F = min(len(frames), len(bbx))
idx = list(range(0, F, STEP))
if FR:
    a, b = (int(v) for v in FR.split(":")); idx = [i for i in idx if a <= i <= b]
if LIMIT: idx = idx[:LIMIT]
print("[sam3d] %d video frames, %d to process (step %d)" % (F, len(idx), STEP), flush=True)

t0 = time.time()
model, cfg = load_sam_3d_body(os.path.join(SAM_ROOT, "model.ckpt"), device="cpu", mhr_path=os.path.join(SAM_ROOT, "assets", "mhr_model.pt"))
est = SAM3DBodyEstimator(sam_3d_body_model=model, model_cfg=cfg, human_detector=None, human_segmentor=None, fov_estimator=None)
print("[sam3d] model loaded in %.0f s" % (time.time() - t0), flush=True)

out = {k: [] for k in ("frame", "kp3d", "kp2d", "joints", "grots", "cam_t", "focal")}
for n, i in enumerate(idx):
    t1 = time.time()
    cx, cy, s = bbx[i]
    box = np.array([[cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2]], dtype=np.float32)
    rgb = cv2.cvtColor(frames[i], cv2.COLOR_BGR2RGB)
    res = est.process_one_image(rgb, bboxes=box, cam_int=torch.from_numpy(K[i]).float()[None])
    if not res:
        print("[sam3d] frame %d: no result" % i, flush=True); continue
    r = res[0]
    out["frame"].append(i); out["kp3d"].append(r["pred_keypoints_3d"]); out["kp2d"].append(r["pred_keypoints_2d"])
    out["joints"].append(r["pred_joint_coords"]); out["grots"].append(r["pred_global_rots"])
    out["cam_t"].append(r["pred_cam_t"]); out["focal"].append(r["focal_length"])
    print("[sam3d] frame %d (%d/%d) %.1f s" % (i, n + 1, len(idx), time.time() - t1), flush=True)
    if (n + 1) % 10 == 0 or n + 1 == len(idx):
        np.savez(dst, **{k: np.array(v) for k, v in out.items()})
print("[sam3d] wrote %s (%d frames) in %.0f s" % (dst, len(out["frame"]), time.time() - t0))
