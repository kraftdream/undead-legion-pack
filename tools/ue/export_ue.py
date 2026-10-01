"""Write every Unreal-target FBX into Export_UE/ (system Python; runs Blender headless, one process per file).

    python tools/ue/export_ue.py                 # characters + armour, weapons, every clip
    python tools/ue/export_ue.py clips [Name...] # only clips (all, or the named ones)
    python tools/ue/export_ue.py models|weapons

The clip list is the Unity export folder (skeletons/Assets/UndeadLegion/Animations/Skeleton@*.fbx), so the two
engines ship the same set. Each clip gets its manifest `lift` (Animations/clips.json; the exporter's default
otherwise). The per-frame `ground_fit` curves are NOT applied: they correct Unity Humanoid's leg reconstruction,
and Unreal plays the bones verbatim (the Blender pose).
"""
import glob, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
CHARACTERS = ["SkeletonKnight", "SkeletonArcher", "SkeletonAssassin", "SkeletonMage", "SkeletonNecromancer", "SkeletonWarrior"]


def blender(blend, script, args):
    cmd = [BLENDER, "-b", os.path.join(ROOT, blend), "-P", os.path.join(ROOT, "tools", script), "--"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = [l for l in r.stdout.splitlines() if l.startswith("[export]") or l.startswith("[weapons]") or "Error" in l or "Traceback" in l]
    ok = r.returncode == 0 and not any("Traceback" in l for l in r.stdout.splitlines() + r.stderr.splitlines())
    for l in lines:
        if "wrote" in l or "Travel" in l or "travel" in l or "Error" in l or "Traceback" in l or "->" in l:
            print("   ", l)
    if not ok:
        print(r.stderr[-2000:])
    return ok


def clips(names=None):
    manifest = {c["name"]: c for c in json.load(open(os.path.join(ROOT, "Animations", "clips.json")))["clips"]}
    have = sorted(os.path.basename(p)[len("Skeleton@"):-4] for p in
                  glob.glob(os.path.join(ROOT, "skeletons", "Assets", "UndeadLegion", "Animations", "Skeleton@*.fbx")))
    bad = []
    for n in (names or have):
        args = ["--unreal", "--clip", n]
        if "lift" in manifest.get(n, {}):
            args += ["--lift", str(manifest[n]["lift"])]
        print("clip", n, args[3:])
        if not blender("Animations/skeleton_anim.blend", "export_fbx.py", args):
            bad.append(n)
    return bad


def models():
    bad = []
    for c in CHARACTERS:
        print("model", c)
        if not blender(c + "/prod.blend", "export_fbx.py", ["--unreal"]):
            bad.append(c)
    return bad


def weapons():
    print("weapons")
    return [] if blender("Weapons/prod.blend", "export_weapons.py", ["--unreal"]) else ["weapons"]


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    bad = []
    if what in ("all", "models"):
        bad += models()
    if what in ("all", "weapons"):
        bad += weapons()
    if what in ("all", "clips"):
        bad += clips(sys.argv[2:] or None)
    print("FAILED:", bad if bad else "none")
    sys.exit(1 if bad else 0)
