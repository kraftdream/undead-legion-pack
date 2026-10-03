"""Video -> retarget source in one command: GVHMR (WSL, CPU) -> SMPL .npz -> armature .blend.

    python tools/video_mocap.py VIDEO.mp4 NAME [--anchor-foot L|R[:frame]] [--hands [--step N]] [--moving-cam] [--fast] [--render]

1. `gvhmr demo` in the WSL install at D:/GVHMR (static camera by default; --moving-cam uses its
   rotation-only odometry); results in D:/GVHMR/outputs/demo/<video stem>/
2. tools/gvhmr_export.py (in the GVHMR venv): hmr4d_results.pt -> External Anims/Video/NAME.npz
   --anchor-foot L|R: that foot stood still in the recording; its drift in the solve is removed from the whole body
3. with --hands: tools/sam3d_hands.py (SAM 3D Body, /mnt/d/Sam/.venv, ~12 s per frame on CPU, every --step N frames,
   default 2) -> External Anims/Video/NAME_sam.npz, then tools/sam3d_wrists.py puts its hand orientation onto the
   SMPL wrists (GVHMR never observes the hand) -> NAME_hands.npz
4. tools/smpl_to_armature.py (Blender): -> External Anims/Video/NAME_arm.blend (from the hands npz when --hands)
Then retarget it like any converted capture (`--rename smpl`, manifest `glb "Video/NAME_arm"` is not
the batch's folder: run glb_retarget directly or give the batch the path):

    blender -b Animations/skeleton_anim.blend -P tools/glb_retarget.py -- \
        --glb "External Anims/Video/NAME_arm.blend" --rename smpl --name Clip --mode action ...

Time on this machine (Ryzen 7 8845HS, CPU): ~1.4 min per second of video, about 2x faster with --fast
(no ViTPose flip test, a small accuracy cost). --render also writes GVHMR's overlay preview video.
SMPL-X is under MPI's non-commercial licence: check it before shipping clips made this way.
"""
import os, subprocess, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
GVHMR = "/mnt/d/GVHMR"
SAM = "/mnt/d/Sam"


def wsl_path(p):
    p = os.path.abspath(p).replace("\\", "/")
    return "/mnt/%s%s" % (p[0].lower(), p[2:]) if p[1] == ":" else p


def run(cmd, **kw):
    print("$", cmd if isinstance(cmd, str) else " ".join(cmd), flush=True)
    t = time.time(); r = subprocess.run(cmd, **kw)
    if r.returncode:
        sys.exit("failed (exit %d)" % r.returncode)
    print("  (%.0f s)" % (time.time() - t), flush=True)


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    video, name = a[0], a[1]
    flags = ["-s"] if "--moving-cam" not in a else []
    if "--fast" in a: flags.append("--fast")
    if "--render" not in a: flags.append("--no-render")
    anchor = a[a.index("--anchor-foot") + 1] if "--anchor-foot" in a else ""
    hands = "--hands" in a
    step = a[a.index("--step") + 1] if "--step" in a else "2"
    stem = os.path.splitext(os.path.basename(video))[0]
    out_dir = os.path.join(REPO, "External Anims", "Video"); os.makedirs(out_dir, exist_ok=True)
    npz = os.path.join(out_dir, name + ".npz"); blend = os.path.join(out_dir, name + "_arm.blend")
    res = "%s/outputs/demo/%s/hmr4d_results.pt" % (GVHMR, stem)
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    run(["wsl", "-d", "Ubuntu", "--", "bash", "-c",
         "cd %s && bin/gvhmr demo '%s' %s" % (GVHMR, wsl_path(video), " ".join(flags))], env=env)
    run(["wsl", "-d", "Ubuntu", "--", "bash", "-c",
         "cd %s && .venv/bin/python '%s' '%s' '%s' --video '%s'%s" % (GVHMR, wsl_path(os.path.join(REPO, "tools", "gvhmr_export.py")),
                                                                 res, wsl_path(npz), wsl_path(video), " --anchor-foot " + anchor if anchor else "")], env=env)
    src_npz = npz
    if hands:
        sam_npz = os.path.join(out_dir, name + "_sam.npz"); hands_npz = os.path.join(out_dir, name + "_hands.npz")
        run(["wsl", "-d", "Ubuntu", "--", "bash", "-c",
             "cd %s && .venv/bin/python '%s' '%s' '%s' '%s' --step %s" % (SAM, wsl_path(os.path.join(REPO, "tools", "sam3d_hands.py")),
                                                                        wsl_path(video), res, wsl_path(sam_npz), step)], env=env)
        run(["wsl", "-d", "Ubuntu", "--", "bash", "-c",
             "cd %s && .venv/bin/python '%s' '%s' '%s' '%s'" % (GVHMR, wsl_path(os.path.join(REPO, "tools", "sam3d_wrists.py")),
                                                              wsl_path(npz), wsl_path(sam_npz), wsl_path(hands_npz))], env=env)
        src_npz = hands_npz
    run([BLENDER, "-b", "-P", os.path.join(REPO, "tools", "smpl_to_armature.py"), "--", src_npz, blend])
    print("\nretarget source:", os.path.relpath(blend, REPO))
    print('next: blender -b Animations/skeleton_anim.blend -P tools/glb_retarget.py -- --glb "%s" --rename smpl --name <Clip> --mode action'
          % os.path.relpath(blend, REPO).replace("\\", "/"))


if __name__ == "__main__":
    main()
