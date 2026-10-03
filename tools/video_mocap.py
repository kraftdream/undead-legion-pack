"""Video -> retarget source in one command: GVHMR (WSL, CPU) -> SMPL .npz -> armature .blend.

    python tools/video_mocap.py VIDEO.mp4 NAME [--moving-cam] [--fast] [--render]

1. `gvhmr demo` in the WSL install at D:/GVHMR (static camera by default; --moving-cam uses its
   rotation-only odometry); results in D:/GVHMR/outputs/demo/<video stem>/
2. tools/gvhmr_export.py (in the GVHMR venv): hmr4d_results.pt -> External Anims/Video/NAME.npz
3. tools/smpl_to_armature.py (Blender): -> External Anims/Video/NAME_arm.blend
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
    stem = os.path.splitext(os.path.basename(video))[0]
    out_dir = os.path.join(REPO, "External Anims", "Video"); os.makedirs(out_dir, exist_ok=True)
    npz = os.path.join(out_dir, name + ".npz"); blend = os.path.join(out_dir, name + "_arm.blend")
    res = "%s/outputs/demo/%s/hmr4d_results.pt" % (GVHMR, stem)
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    run(["wsl", "-d", "Ubuntu", "--", "bash", "-c",
         "cd %s && bin/gvhmr demo '%s' %s" % (GVHMR, wsl_path(video), " ".join(flags))], env=env)
    run(["wsl", "-d", "Ubuntu", "--", "bash", "-c",
         "cd %s && .venv/bin/python '%s' '%s' '%s' --video '%s'" % (GVHMR, wsl_path(os.path.join(REPO, "tools", "gvhmr_export.py")),
                                                               res, wsl_path(npz), wsl_path(video))], env=env)
    run([BLENDER, "-b", "-P", os.path.join(REPO, "tools", "smpl_to_armature.py"), "--", npz, blend])
    print("\nretarget source:", os.path.relpath(blend, REPO))
    print('next: blender -b Animations/skeleton_anim.blend -P tools/glb_retarget.py -- --glb "%s" --rename smpl --name <Clip> --mode action'
          % os.path.relpath(blend, REPO).replace("\\", "/"))


if __name__ == "__main__":
    main()
