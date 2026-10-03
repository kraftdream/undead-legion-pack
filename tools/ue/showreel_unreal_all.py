"""Render every shot of the Unreal showreel, then encode the stages and the YouTube video (system Python, editor running).

    python tools/ue/showreel_unreal_all.py [--samples 64] [--only weapons_03,...] [--no-encode]

For each shot of Showreel/unreal/plan.json (tools/ue/showreel_plan.py): skipped when its folder already holds all its frames,
else `ue_showreel.py shot` builds the map + sequence + director and `render` runs Movie Render Queue at the best quality this
machine offers (64 spatial samples, cinematic scalability, see ue_showreel.CVARS); waits until the job is done. A failed
editor call restarts the editor (tools/ue/editor_up.sh) and retries the shot. Then showreel_stage_ue.py and
tools/unity/showreel_youtube.py --src Showreel/unreal. ~2 s per frame at 64 samples on a Radeon 780M.
"""
import argparse, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UR = os.path.join(ROOT, "Showreel", "unreal")
PY = sys.executable


def ue(*args, timeout=900):
    r = subprocess.run([PY, os.path.join(ROOT, "tools", "ue", "ue_py.py"), os.path.join(ROOT, "tools", "ue", "ue_showreel.py")] + list(args),
                       capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    out = r.stdout + r.stderr
    if r.returncode or "Traceback" in out or "[Error]" in out:
        raise RuntimeError(out[-1500:])
    return out


def editor_up():
    # Git Bash: a plain "bash" from Python on Windows resolves to WSL's, which has no /bin/bash here
    bash = "C:/Program Files/Git/bin/bash.exe" if os.path.exists("C:/Program Files/Git/bin/bash.exe") else "bash"
    subprocess.run([bash, os.path.join(ROOT, "tools", "ue", "editor_up.sh")], cwd=ROOT, timeout=1800)


def frames_in(d):
    return len([f for f in os.listdir(d) if f.endswith(".png")]) if os.path.isdir(d) else 0


def render_shot(stage, i, sh, samples):
    name = "%s_%02d" % (stage, i)
    d = os.path.join(UR, name)
    for attempt in range(4):
        try:
            if os.path.isdir(d):
                for f in os.listdir(d):
                    os.remove(os.path.join(d, f))
            ue("shot", stage, str(i))
            ue("render", str(samples), "all", name)
            time.sleep(20)
            t0 = time.time()
            while True:
                time.sleep(15)
                if "BUSY False" in ue("busy", timeout=120):
                    break
                if time.time() - t0 > 4 * 3600:
                    raise RuntimeError("render timed out")
            n = frames_in(d)
            if n >= sh["frames"]:
                print("%s done: %d frames, %.0f s" % (name, n, time.time() - t0), flush=True)
                return
            raise RuntimeError("%s: only %d of %d frames" % (name, n, sh["frames"]))
        except Exception as e:
            print("!! %s attempt %d: %s" % (name, attempt + 1, str(e)[-600:]), flush=True)
            editor_up()
            time.sleep(30)
    sys.exit("giving up on " + name)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--only", default="")
    ap.add_argument("--no-encode", action="store_true")
    a = ap.parse_args()
    subprocess.run([PY, os.path.join(ROOT, "tools", "ue", "showreel_plan.py")], check=True)
    plan = json.load(open(os.path.join(UR, "plan.json")))
    only = [x for x in a.only.split(",") if x]
    editor_up()
    for st in plan:
        for i, sh in enumerate(st["shots"]):
            name = "%s_%02d" % (st["name"], i)
            if only and name not in only:
                continue
            if not only and frames_in(os.path.join(UR, name)) >= sh["frames"] and os.path.exists(os.path.join(UR, name, ".final")):
                print("%s already rendered" % name, flush=True)
                continue
            render_shot(st["name"], i, sh, a.samples)
            open(os.path.join(UR, name, ".final"), "w").write(str(a.samples))
    if not a.no_encode:
        subprocess.run([PY, os.path.join(ROOT, "tools", "ue", "showreel_stage_ue.py")], check=True)
        subprocess.run([PY, os.path.join(ROOT, "tools", "unity", "showreel_youtube.py"), "--src", UR,
                        "--out", os.path.join(UR, "undead_legion_showreel_unreal.mp4"), "--engine", "Rendered in Unreal Engine 5.8"], check=True)
