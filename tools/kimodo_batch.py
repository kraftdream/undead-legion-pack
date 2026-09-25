"""Generate every clip in Animations/clips.json that has no GLB yet, one after another.

    python tools/kimodo_batch.py [names...]

Runs tools/kimodo_gen.ps1 per entry (skeleton body profile prepended). ~2 min per
300 frames on the laptop. Skips entries whose External Anims/Kimodo/<glb>.glb exists,
so it can be re-run after a failure. Progress goes to Animations/kimodo_batch.log.
"""
import json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, "Animations", "clips.json")
GLB_DIR = os.path.join(ROOT, "External Anims", "Kimodo")
LOG = os.path.join(ROOT, "Animations", "kimodo_batch.log")


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    only = set(sys.argv[1:])
    clips = json.load(open(MAN, encoding="utf-8"))["clips"]
    todo = [c for c in clips if (not only or c["name"] in only) and not os.path.exists(os.path.join(GLB_DIR, c["glb"] + ".glb"))]
    log("batch: %d of %d clips to generate" % (len(todo), len(clips)))
    for c in todo:
        t0 = time.time()
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(ROOT, "tools", "kimodo_gen.ps1"),
               "-Prompt", c["prompt"], "-Name", c["glb"], "-Frames", str(c["frames"]), "-Seed", str(c["seed"])]
        if c.get("no_profile"):
            cmd.append("-NoProfile")          # a plain human prompt: no stiff-undead body description prepended (the "normal" walk/run, 2026-09-25)
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        ok = os.path.exists(os.path.join(GLB_DIR, c["glb"] + ".glb"))
        tail = (r.stdout + r.stderr).strip().splitlines()[-1:] if not ok else []
        log("%-16s %s  %3.0f s  %s" % (c["name"], "ok " if ok else "FAILED", time.time() - t0, " ".join(tail)))
    log("batch done")


if __name__ == "__main__":
    main()
