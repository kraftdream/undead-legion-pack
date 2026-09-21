"""Build every clip in Animations/clips.json whose GLB exists: retarget, preview, export, Unity.

    python tools/anim_batch.py [names...] [--force] [--no-unity] [--wait]

--wait keeps polling the manifest every two minutes and builds clips as their GLBs
arrive (the Kimodo batch runs for an hour or more), exiting once every entry is built.

Per clip (skipped when Animations/build_state.json says the GLB has not changed since,
unless --force):
  1. tools/glb_retarget.py  (mode + args from the manifest) -> Action in the anim file
  2. tools/anim_preview.py  -> Animations/preview/<Name>_{front,side}.png
  3. tools/export_fbx.py --clip <Name> -> skeletons/Assets/UndeadLegion/Animations/Skeleton@<Name>.fbx
  4. tools/unity/verify_clip.py with the mode's import flags (loop / in-place / root motion),
     then tools/unity/ground_clip.py (lowest vertex on all six models)
Everything is logged to Animations/anim_batch.log. Unity steps need the editor open;
--no-unity skips them.
"""
import json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, "Animations", "clips.json")
STATE = os.path.join(ROOT, "Animations", "build_state.json")
LOG = os.path.join(ROOT, "Animations", "anim_batch.log")
GLB_DIR = os.path.join(ROOT, "External Anims", "Kimodo")
ANIM = os.path.join(ROOT, "Animations", "skeleton_anim.blend")
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
PREVIEW = os.path.join(ROOT, "Animations", "preview")


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd, cwd=ROOT, timeout=1800):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def blender(script, args, blend=ANIM):
    code, out = run([BLENDER, "-b", blend, "-P", os.path.join(ROOT, "tools", script), "--"] + [str(a) for a in args])
    lines = [l for l in out.splitlines() if l.startswith(("[retarget]", "[export]", "[preview]")) or "Traceback" in l or "Error" in l or "assert" in l.lower()]
    return code, lines


def retarget_args(c):
    a = ["--glb", "External Anims/Kimodo/%s.glb" % c["glb"], "--name", c["name"], "--mode", c["mode"], "--save"]
    for k, flag in (("loop", "--loop"), ("blend", "--blend"), ("src_start", "--src-start"), ("src_end", "--src-end"),
                    ("time_scale", "--time-scale"), ("smooth", "--smooth"), ("fist", "--fist"), ("hunch", "--hunch"),
                    ("arm_pose", "--arm-pose"), ("head_damp", "--head-damp"), ("travel_axis", "--travel-axis"),
                    ("lock_left_hand", "--lock-left-hand"), ("lock_left_roll", "--lock-left-roll"),
                    ("blend_from", "--blend-from"), ("blend_in", "--blend-in"), ("ground", "--ground"),
                    ("ground_ignore", "--ground-ignore"), ("blend_to", "--blend-to"), ("blend_out", "--blend-out")):
        if k in c:
            a += [flag, str(c[k])]
    if c.get("mirror"):
        a.append("--mirror")
    if c.get("elbow_pole"):
        a.append("--elbow-pole")
    if c.get("arm_keys"):
        a += ["--arm-keys", ",".join("%g:%s" % (t, n) for t, n in c["arm_keys"])]
    return a


def unity_flags(c):
    mode = c["mode"]
    loop = "1" if mode in ("idle", "loco") else "0"
    inplace = "0" if mode == "loco" else "1"
    return ["--loop", loop, "--in-place", inplace]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    unity = "--no-unity" not in sys.argv
    wait = "--wait" in sys.argv
    while True:
        pending = build_pass(args, force, unity)
        force = False
        if not wait or pending == 0:
            break
        time.sleep(120)
    log("anim batch done")


def build_pass(args, force, unity):
    """Build what is buildable now; return how many manifest entries still lack a GLB."""
    clips = json.load(open(MAN, encoding="utf-8"))["clips"]
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    pending = sum(1 for c in clips if (not args or c["name"] in args) and not os.path.exists(os.path.join(GLB_DIR, c["glb"] + ".glb")))
    todo = []
    for c in clips:
        if args and c["name"] not in args:
            continue
        glb = os.path.join(GLB_DIR, c["glb"] + ".glb")
        if not os.path.exists(glb):
            continue
        sig = "%s|%d|%s" % (c["glb"], int(os.path.getmtime(glb)), json.dumps({k: v for k, v in c.items() if k != "prompt"}, sort_keys=True))
        if not force and state.get(c["name"], {}).get("sig") == sig and state[c["name"]].get("ok"):
            continue
        todo.append((c, sig))
    if todo:
        log("anim batch: %d clips to build (%d still waiting for Kimodo)" % (len(todo), pending))
    for c, sig in todo:
        t0 = time.time(); ok = True; notes = []
        code, lines = blender("glb_retarget.py", retarget_args(c))
        key = [l for l in lines if any(k in l for k in ("gait", "travel", "ground:", "body min", "seam", "action ", "Traceback", "Error", "assert"))]
        notes += key
        if code != 0 or not any("saved" in l for l in lines):
            ok = False
        if ok:
            os.makedirs(PREVIEW, exist_ok=True)
            blender("anim_preview.py", ["--action", c["name"], "--out", PREVIEW])
            code, lines = blender("export_fbx.py", ["--clip", c["name"]] + (["--lift", str(c["lift"])] if "lift" in c else []))
            notes += [l for l in lines if "wrote" in l or "Traceback" in l or "Error" in l]
            if code != 0 or not any("wrote" in l for l in lines):
                ok = False
        if ok and unity:
            code, out = run([sys.executable, os.path.join(ROOT, "tools", "unity", "verify_clip.py"),
                             "Assets/UndeadLegion/Animations/Skeleton@%s.fbx" % c["name"]] + unity_flags(c), timeout=900)
            notes += [l for l in out.splitlines() if l.startswith(("clip ", "SkeletonKnight"))][:2]
            code, out = run([sys.executable, os.path.join(ROOT, "tools", "unity", "ground_clip.py"), c["name"]], timeout=900)
            notes += [l for l in out.splitlines() if l.startswith(c["name"] + ":")]
        # merge into the file as it is NOW: entries cleared by hand while a pass runs must
        # not be resurrected from this pass's in-memory copy (that bit me twice)
        state = json.load(open(STATE)) if os.path.exists(STATE) else {}
        state[c["name"]] = {"sig": sig, "ok": ok, "when": time.strftime("%Y-%m-%d %H:%M"), "mode": c["mode"]}
        json.dump(state, open(STATE, "w"), indent=1)
        log("%-16s %s  %4.0f s" % (c["name"], "ok " if ok else "FAILED", time.time() - t0))
        for n in notes:
            log("    " + n[:220])
    return pending


if __name__ == "__main__":
    main()
