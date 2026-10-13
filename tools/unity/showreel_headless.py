"""Record the showreel HEADLESSLY (the interactive editor must be closed: one editor per project) and encode it.

    python tools/unity/showreel_headless.py [--stage modular|movement|weapons|physics|army] [--side left|right | --azimuth DEG] [--supersample 2] [--max-loadouts 0]
                                            [--width 1920 --height 1080] [--out Showreel/showreel_<stage>.mp4] [--crf 12]
                                            [--unity "C:/Program Files/Unity/Hub/Editor/6000.4.0f1/Editor/Unity.exe"]

Stages and scenes: modular / movement / weapons run in the base demo scene; "physics" (cloth, hit reactions, ragdolls, dissolve)
in the Extended browser scene and "army" (the 12 v 12 arena battle, scripted camera) in the arena scene (2026-10-09, the
Extended edition's showreel). The output is Showreel/showreel_<stage>.mp4 for the default left side, showreel_<stage>_<side>.mp4
otherwise; the frames stay in Showreel/headless_<tag>/frames.

Runs Unity in -batchmode (no -nographics: the GPU renders offscreen, only the editor UI is skipped) with
-executeMethod UndeadLegion.Demo.ShowreelMenu.RecordHeadless, the settings passed as SHOWREEL_* environment
variables; the recorder writes <frames dir>/done.txt and the editor exits when the sequence is done. Then
showreel_encode.py makes the mp4. The Unity log goes to Showreel/headless_<side>.log.
"""
import argparse, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT = os.path.join(ROOT, "skeletons")
ap = argparse.ArgumentParser()
ap.add_argument("--stage", choices=["modular", "movement", "weapons", "attacks", "physics", "army"], default="modular", help="which stage to render (one per run; stitched later)")
ap.add_argument("--side", choices=["left", "right"], default="left", help="left = the camera at -30 deg (the character's left side nearest), right = +30")
ap.add_argument("--azimuth", type=float, default=None, help="overrides --side")
ap.add_argument("--supersample", type=int, default=2, help="1, 2 or 4 (3 rounds up to 4)")
ap.add_argument("--msaa", type=int, default=8, help="MSAA samples on the render target")
ap.add_argument("--max-loadouts", type=int, default=0, help="test runs: stop after N loadouts (0 = the whole plan)")
ap.add_argument("--arena-seconds", type=float, default=0, help="army stage test runs: cap the arena at N seconds (0 = the recorder's default, ~62 s or until one side falls)")
ap.add_argument("--width", type=int, default=1920)
ap.add_argument("--height", type=int, default=1080)
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--out", default="")
ap.add_argument("--crf", type=int, default=12, help="x264 quality of the stage video (the YouTube cut re-encodes it; 12 since 2026-10-04)")
ap.add_argument("--unity", default=r"C:\Program Files\Unity\Hub\Editor\6000.4.0f1\Editor\Unity.exe")
ap.add_argument("--no-encode", action="store_true")
a = ap.parse_args()

SCENES = {"physics": "Assets/UndeadLegion/Extended/Scenes/UndeadLegion_Extended_Showcase.unity",
          "army": "Assets/UndeadLegion/Extended/Scenes/UndeadLegion_Extended_Demo.unity"}
az = a.azimuth if a.azimuth is not None else (-30.0 if a.side == "left" else 30.0)
tag = a.stage if a.stage == "army" else a.stage + "_" + (a.side if a.azimuth is None else ("az%+.0f" % a.azimuth))
frames = os.path.join(ROOT, "Showreel", "headless_" + tag, "frames")
default_side = a.azimuth is None and a.side == "left"
out = a.out or os.path.join(ROOT, "Showreel", "showreel_%s.mp4" % (a.stage if default_side else tag))
log = os.path.join(ROOT, "Showreel", "headless_%s.log" % tag)
os.makedirs(os.path.dirname(log), exist_ok=True)
if not os.path.exists(a.unity):
    sys.exit("Unity not found at " + a.unity)
if os.path.exists(os.path.join(PROJECT, "Temp", "UnityLockfile")):
    print("WARNING: skeletons/Temp/UnityLockfile exists - if the interactive editor is open on this project the batch run will refuse to start")

env = dict(os.environ)
env.update({"SHOWREEL_AZIMUTH": str(az), "SHOWREEL_WIDTH": str(a.width), "SHOWREEL_HEIGHT": str(a.height), "SHOWREEL_SUPERSAMPLE": str(a.supersample),
            "SHOWREEL_MAXLOADOUTS": str(a.max_loadouts), "SHOWREEL_FPS": str(a.fps), "SHOWREEL_MSAA": str(a.msaa), "SHOWREEL_OUT": frames, "SHOWREEL_STAGE": a.stage})
if a.stage in SCENES: env["SHOWREEL_SCENE"] = SCENES[a.stage]
if a.arena_seconds > 0: env["SHOWREEL_ARENA_SECONDS"] = str(a.arena_seconds)
cmd = [a.unity, "-batchmode", "-projectPath", PROJECT, "-executeMethod", "UndeadLegion.Demo.ShowreelMenu.RecordHeadless", "-logFile", log]
print("launching headless Unity: stage %s, azimuth %+.0f, %dx%d, supersample %dx, steps %s -> %s" % (a.stage, az, a.width, a.height, a.supersample, a.max_loadouts or "all", frames), flush=True)
t0 = time.time()
p = subprocess.Popen(cmd, env=env)
last = -1
while p.poll() is None:
    time.sleep(15)
    n = len(os.listdir(frames)) if os.path.isdir(frames) else 0
    if n != last:
        print("%5.0fs  %d frames" % (time.time() - t0, n), flush=True); last = n
print("unity exited with %d after %.0f s" % (p.returncode, time.time() - t0), flush=True)
done = os.path.join(frames, "done.txt")
print("recorder:", open(done).read() if os.path.exists(done) else "NO done marker (see " + log + ")", flush=True)
if a.no_encode or not os.path.exists(done):
    sys.exit(0 if os.path.exists(done) else 1)
r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "unity", "showreel_encode.py"), "--frames", frames, "--out", out, "--fps", str(a.fps), "--crf", str(a.crf)],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
print(r.stdout[-600:], flush=True)
