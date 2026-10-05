"""Splice re-rendered death segments into the weapons shots and re-encode (system Python).

    python tools/ue/showreel_patch_deaths.py plan       # append the `patch` stage (one phase-matched shot per death) to plan.json
    python tools/ue/showreel_patch_deaths.py render     # build + render the patch shots (editor running; ~45 min at 64 samples)
    python tools/ue/showreel_patch_deaths.py splice     # frames into the weapons shots, re-encode the stage and the YouTube cut

showreel_unreal_all.py regenerates plan.json (showreel_plan.py) at start and so DROPS the patch stage: render through this script.

Showreel/unreal/patch_info.json (written when the `patch` stage was built, 2026-10-05) maps each patch shot to its weapons shot:
the death step starts at frame Fd of the full shot and at frame Pf of the patch shot, Pf chosen so the idle loop's phase is the
same (Pf == Fd mod the loop's frame count; the loop runs from BeginPlay in both). The frames from Fd on are replaced by the
patch's frames from Pf on (the same count by construction), then the weapons stage and the YouTube cut are re-encoded.
"""
import json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UR = os.path.join(ROOT, "Showreel", "unreal")
PY = sys.executable


def plan():
    import importlib.util
    spec = importlib.util.spec_from_file_location("sp", os.path.join(ROOT, "tools", "ue", "showreel_plan.py")); sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)
    full = [st for st in json.load(open(os.path.join(UR, "plan.json"))) if st["name"] != "patch"]
    stages = {st["name"]: st for st in full}
    L = json.load(open(os.path.join(UR, "clip_lengths.json")))
    steps, info = [], []
    for i, sh in enumerate(stages["weapons"]["shots"]):
        tw = [c["f"] for c in sh["cmds"] if c["name"] == "twitch" and c["n"] == 0]
        if not tw:
            continue
        Fd = tw[0]; idle = sh["idle"]; Lf = round(L[idle] * 30); P = Fd % Lf
        death = [c["clip"] for c in sh["cmds"] if c["name"] == "action" and c["clip"].startswith("Death_")][0]
        lo = sh["loadout"]
        for c in sh["cmds"]:
            if c["name"] == "equip" and c["f"] <= Fd:
                lo = sp.LOADOUTS[c["n"]]
        cap = [c for c in sh["captions"] if c["f0"] == Fd][0]
        info.append(dict(shot=i, character=sh["character"], death=death, Fd=Fd, idle=idle, L=Lf, P=P, frames=sh["frames"], loadout=lo, title=cap["title"]))
        steps.append(sp.S(sh["character"], lo, idle, P / 30.0, cap["title"], "hold"))
        steps.append(sp.death(sp.A(sh["character"], lo, idle, cap["title"], "Death", death)))
    stage = dict(name="patch", title="PATCH", text="death segments", root_motion=True, steps=steps)
    shots = sp.shots(stage); stage["shots"] = shots; del stage["steps"]
    for sh, inf in zip(shots, info):
        inf["patch_frames"] = sh["frames"]; inf["Pf"] = [c["f"] for c in sh["cmds"] if c["name"] == "twitch" and c["n"] == 0][0]
        assert inf["patch_frames"] - inf["Pf"] == inf["frames"] - inf["Fd"]
        print("patch_%02d <- weapons_%02d %s %s: Fd %d, Pf %d (idle %s, %d f loop), %d frames" % (len(info) and info.index(inf), inf["shot"], inf["character"], inf["death"], inf["Fd"], inf["Pf"], inf["idle"], inf["L"], inf["patch_frames"]))
    json.dump(full + [stage], open(os.path.join(UR, "plan.json"), "w"), indent=1)
    json.dump(info, open(os.path.join(UR, "patch_info.json"), "w"), indent=1)


def render(samples="64"):
    import time
    plan_ = {st["name"]: st for st in json.load(open(os.path.join(UR, "plan.json")))}
    uepy = os.path.join(ROOT, "tools", "ue", "ue_py.py"); show = os.path.join(ROOT, "tools", "ue", "ue_showreel.py")
    for i, sh in enumerate(plan_["patch"]["shots"]):
        name = "patch_%02d" % i; out = os.path.join(UR, name)
        if os.path.isdir(out) and len([f for f in os.listdir(out) if f.startswith("frame_")]) >= sh["frames"]:
            print(name, "already rendered"); continue
        subprocess.run([PY, uepy, show, "shot", "patch", str(i)], check=True)
        subprocess.run([PY, uepy, show, "render", str(samples), "all", name], check=True)
        t0 = time.time()
        while len([f for f in os.listdir(out) if f.startswith("frame_")]) < sh["frames"] if os.path.isdir(out) else True:
            time.sleep(20)
            if time.time() - t0 > 3600:
                raise SystemExit(name + ": render timed out")
        time.sleep(5)
        print("%s done: %d frames, %.0f s" % (name, sh["frames"], time.time() - t0), flush=True)


def splice(encode=True):
  info = json.load(open(os.path.join(UR, "patch_info.json")))
  for j, inf in enumerate(info):
    src = os.path.join(UR, "patch_%02d" % j); dst = os.path.join(UR, "weapons_%02d" % inf["shot"])
    n_src = len([f for f in os.listdir(src) if f.startswith("frame_")]); n_dst = len([f for f in os.listdir(dst) if f.startswith("frame_")])
    assert n_src >= inf["patch_frames"], "patch_%02d has %d of %d frames" % (j, n_src, inf["patch_frames"])
    assert n_dst == inf["frames"], "weapons_%02d has %d frames, plan says %d" % (inf["shot"], n_dst, inf["frames"])
    copied = 0
    for k in range(inf["Fd"], inf["frames"]):
        shutil.copyfile(os.path.join(src, "frame_%05d.png" % (inf["Pf"] + k - inf["Fd"])), os.path.join(dst, "frame_%05d.png" % k)); copied += 1
    print("weapons_%02d (%s, %s): frames %d..%d replaced from patch_%02d frames %d.. (%d frames)" % (inf["shot"], inf["character"], inf["death"], inf["Fd"], inf["frames"] - 1, j, inf["Pf"], copied))
  if encode:
    subprocess.run([PY, os.path.join(ROOT, "tools", "ue", "showreel_stage_ue.py"), "weapons"], check=True)
    subprocess.run([PY, os.path.join(ROOT, "tools", "unity", "showreel_youtube.py"), "--src", UR,
                    "--out", os.path.join(UR, "undead_legion_showreel_unreal.mp4"), "--engine", "Rendered in Unreal Engine 5.8"], check=True)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "splice"
    if what == "plan":
        plan()
    elif what == "render":
        render(*sys.argv[2:3])
    else:
        splice("--no-encode" not in sys.argv)
