"""Build the clean, shippable Unity project from the development project.

    python tools/make_production.py [--edition base|extended] [--dest DIR] [--verify]

Two editions, two listings: `base` (../undead-legion-production) is the pack without Assets/UndeadLegion/Extended;
`extended` (../undead-legion-extended-production) adds the Extended folder (ragdolls, hit reactions, cloth, dissolve
VFX, NavMesh control, combat AI, army spawner, the arena demo) and keeps the AI Navigation package it needs. The
Extended editor builder is left out like the base builders; both demo scenes are build scenes in the extended copy.

The development project (skeletons/) carries the pipeline: editor builders that read the repo's tools and manifests, a
showreel recorder, a scratch folder, the editor bridge package, and code comments that record how each piece was
made. The production project is a copy with only what a buyer gets, and nothing that describes the process:

  Assets/UndeadLegion      models, animations, materials, textures, prefabs, the demo scene and its runtime scripts
                           (Demo/Editor and ShowreelRecorder left out; every C# comment stripped and replaced by a
                           one-line summary per type; tooltips rewritten)
  Assets/Settings          the URP assets the project settings point at
  Packages                 the manifest without the editor bridge, collaboration and multiplayer packages;
                           the Asset Store publishing tools kept (needed to upload)
  ProjectSettings          copied, product name set, the cloud project link cleared, the demo scene as the build scene

Every FBX embeds the absolute path of the .blend it was exported from (Blender's DocumentUrl / SrcDocumentUrl /
ApplicationNativeFile); those strings are overwritten in place with a neutral name of the SAME byte length, so the
binary layout and every offset stay valid. The destination's Library/ is kept between runs (a full reimport is slow).
--verify opens the project in batch mode and fails on compile errors, missing scripts, or any leftover marker.
"""
import argparse, os, re, shutil, subprocess, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "skeletons")
UNITY = r"C:\Program Files\Unity\Hub\Editor\6000.4.0f1\Editor\Unity.exe"

EXCLUDE = ["Assets/UndeadLegion/Demo/Editor", "Assets/UndeadLegion/Demo/Editor.meta",
           "Assets/UndeadLegion/Demo/Scripts/ShowreelRecorder.cs", "Assets/UndeadLegion/Demo/Scripts/ShowreelRecorder.cs.meta"]
# Also exclude stale exports if a retired authoring action was exported earlier.
with open(os.path.join(ROOT, "Animations", "clips.json"), encoding="utf-8") as _manifest:
    EXCLUDE += ["Assets/UndeadLegion/Animations/Skeleton@" + c["name"] + suffix
                for c in json.load(_manifest)["clips"] if c.get("disabled") for suffix in (".fbx", ".fbx.meta")]
COPY = ["Assets/UndeadLegion", "Assets/UndeadLegion.meta", "Assets/Settings", "Assets/Settings.meta",
        "Assets/InputSystem_Actions.inputactions", "Assets/InputSystem_Actions.inputactions.meta", "ProjectSettings",
        "Packages/com.unity.asset-store-tools"]
EXCLUDE_BASE = ["Assets/UndeadLegion/Extended", "Assets/UndeadLegion/Extended.meta"]
EXCLUDE_EXTENDED = ["Assets/UndeadLegion/Extended/Editor", "Assets/UndeadLegion/Extended/Editor.meta"]
DROP_PACKAGES = ["com.coplaydev.unity-mcp", "com.unity.collab-proxy", "com.unity.multiplayer.center"]
NAVIGATION = "com.unity.ai.navigation"          # the extended edition's NavMesh; dropped from the base
SCENES = {"base": ["Assets/UndeadLegion/Demo/Scenes/UndeadLegion_Demo.unity"],
          "extended": ["Assets/UndeadLegion/Extended/Scenes/UndeadLegion_Extended_Demo.unity", "Assets/UndeadLegion/Extended/Scenes/UndeadLegion_Extended_Showcase.unity",
                       "Assets/UndeadLegion/Extended/Scenes/UndeadLegion_Extended_Player.unity",
                       "Assets/UndeadLegion/Demo/Scenes/UndeadLegion_Demo.unity"]}
PRODUCT = {"base": "Undead Legion", "extended": "Undead Legion Extended"}
# anything that points back at how the pack was made
MARKERS = re.compile(r"claude|anthropic|kimodo|\bmcp\b|coplay|scratchpad|\buser\b|\bthe user's\b|2026-|CLAUDE\.md|clips\.json|build_state|"
                     r"tools/|skeleton_anim|\.blend\b|creatures pack|bridge|vadym|OneDrive|session|prefab builder|blender|rig m\b|retarget|mocap|recording", re.I)
UNITY_OWN = re.compile(r"m_\w*[Uu]ser|userData|UserSettings|usedByComposite|pnSessions|VR Device User Alert|[Rr]etargeting|When Recording|For Recording|RecordingFeatures")

SUMMARIES = {
    "ArmorModule": "An armour piece that binds to any character built on the shared skeleton by matching bone names.",
    "ArmorPiece": "Marks an attached armour piece: the character and module it came from.",
    "ArrowProjectile": "A fired arrow: flies along its launch direction and removes itself after its lifetime or under the floor.",
    "BowString": "Pulls the bow's string to the draw hand between the attach and release events and bends the limbs with the draw.",
    "DemoEventSystemBootstrap": "Makes sure the demo scene has an EventSystem with an input module for the active input backend.",
    "DemoTurntable": "Demo camera: drag to orbit, scroll to zoom, optional slow turntable.",
    "DemoUI": "Small uGUI helpers used to build the demo's panels, buttons and toggles at runtime.",
    "SkeletonFootLock": "Holds both feet on their IK goals while a looping idle plays, so the feet stay planted under the sway.",
    "SkeletonGripState": "Animator state behaviour: tells SkeletonWeapon that the clip holds a weapon in the given hand, so that hand closes its grip.",
    "SkeletonModules": "Switches a character's armour modules on and off and wears pieces from any other character's set.",
    "SkeletonShowcase": "The demo browser: character selection, armour modules, animation sections, layered playback and root motion options.",
    "SkeletonTwitch": "Plays short additive head and jaw twitches at random intervals for crowds of skeletons.",
    "SkeletonWeapon": "Equips weapon loadouts into the hand slots, closes the fingers on held items and drives the empty-hand finger idles.",
    "SkeletonRagdoll": "A full-body ragdoll on the humanoid bones: kinematic hitboxes while animated, physics on death, and a blend back to animation.",
    "Part": "One ragdoll body: the bone, its rigidbody and its collider.",
    "SkeletonHitReaction": "Physical hit reactions layered over any animation: damped springs on the spine, head and arms kicked by each hit's torque.",
    "SkeletonHealth": "Health, team and death handling: ragdoll or death clip, then an optional dissolve; events for damage and death.",
    "DamageInfo": "One hit: the amount, the world point, the impulse and the attacker.",
    "SkeletonDissolve": "Rise-from-the-ground and turn-to-dust effects: a glowing cut height sweeps through every renderer of the skeleton.",
    "SkeletonCloth": "Adds cloth simulation to robes, skirts and pants, pinned at the waist and colliding with the legs; culled by distance.",
    "ModuleRule": "Which armour module gets cloth, and how far below the waist the cloth starts to move.",
    "SkeletonNavController": "Drives a skeleton with a NavMeshAgent: locomotion blend trees fed from the agent's velocity, weapon idles and one-shot actions.",
    "SkeletonAI": "Simple combat AI: finds the nearest enemy, closes in, and attacks with the moves that suit the equipped weapon.",
    "Move": "One attack: the clip, when the hit lands, its range, damage and impulse.",
    "MagicBolt": "A glowing homing projectile for wand and staff attacks; damages its target on arrival.",
    "SkeletonEyes": "Glowing eyes in the skull's sockets, in any HDR colour (bloom makes them glow).",
    "ArmySpawner": "Spawns a formation of varied skeletons: random class, mixed armour, a suitable loadout, a tint, team eyes and a rise from the ground.",
    "ExtendedInput": "Mouse and keyboard reads that work with either input backend.",
    "RtsCamera": "A top-down battle camera: pan, rotate and zoom.",
    "ExtendedDemo": "The arena demo: raise two armies, start the battle, select and command a skeleton, strike or kill any skeleton.",
    "Slot": "A renderer and its original materials for the duration of an effect.",
    "Spring": "One bone's reaction spring.",
    "ExtendedShowcase": "Adds the extended systems to the animation browser: cloth, hits, ragdoll death, revive, rise and dust, and hits by clicking the character.",
}


# tooltips and messages that describe the pipeline, rewritten for a buyer (matched on their start)
TEXT_REWRITES = {
    "Draw length (metres) at which the limbs reach their full bend": "Draw length (metres) at which the limbs reach their full bend.",
    "Degrees of bend at full draw on the first and second limb segments": "Degrees of bend at full draw on the first and second limb segments.",
    "This character's default armour set (module prefabs)": "This character's default armour set (module prefabs), worn from the prefab.",
    "Finger bone local rotations of the authored grip": "Finger bone local rotations of the grip pose, applied after the Animator to a hand that holds an item.",
    "Where the fired arrow flies": "Where the fired arrow flies: along the character's forward, or from the draw hand toward the bow.",
    "BowString: the bow model has no rig bones": "BowString: the bow model has no rig bones (Nock/Brace/Limb_*).",
}


def rewrite_texts(s):
    def repl(m):
        body = m.group(2)
        for start, new in TEXT_REWRITES.items():
            if body.startswith(start): return m.group(1) + '"' + new + '"'
        return m.group(0)
    return re.sub(r'(\[Tooltip\(|Debug\.LogWarning\()"((?:[^"\\]|\\.)*)"', repl, s)


def strip_comments(src):
    """Remove // and /* */ comments from C#, leaving string, verbatim-string, interpolated and char literals intact."""
    out = []; i = 0; n = len(src)
    while i < n:
        c = src[i]; c2 = src[i:i + 2]
        if c2 == "//":
            j = src.find("\n", i); i = n if j < 0 else j; continue
        if c2 == "/*":
            j = src.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        if c == '@' and i + 1 < n and src[i + 1] == '"':          # verbatim string: "" escapes a quote
            j = i + 2
            while j < n:
                if src[j] == '"' and src[j + 1:j + 2] == '"': j += 2; continue
                if src[j] == '"': break
                j += 1
            out.append(src[i:j + 1]); i = j + 1; continue
        if c == '"' or c == "'":
            q = c; j = i + 1
            while j < n and src[j] != q:
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1]); i = j + 1; continue
        out.append(c); i += 1
    s = "".join(out)
    s = "\n".join(l.rstrip() for l in s.split("\n"))
    s = re.sub(r"\n{3,}", "\n\n", s)                               # collapse the gaps comments left
    s = re.sub(r"\{\n\n+", "{\n", s); s = re.sub(r"\n\n+(\s*\})", r"\n\1", s)
    return s.strip() + "\n"


def add_summaries(s):
    def repl(m):
        indent, decl, name = m.group(1), m.group(2), m.group(3)
        text = SUMMARIES.get(name)
        return (indent + "/// <summary>" + text + "</summary>\n" if text else "") + indent + decl
    s = re.sub(r"(?m)^(\s*)((?:public |internal )?(?:static |sealed |abstract )*(?:class|struct|enum) (\w+))", repl, s)
    # a summary belongs above the type's attributes: move it over the [Attribute] lines directly before it
    return re.sub(r"(?m)((?:^[ \t]*\[[^\n]*\]\n)+)(^[ \t]*/// <summary>[^\n]*\n)", r"\2\1", s)


def clean_tooltips(s):
    """Tooltips are the only comment-like text left in strings; drop the ones that narrate history, trim the rest."""
    def repl(m):
        body = m.group(1)
        if MARKERS.search(body):
            body = re.sub(r"\s*\((?:[^()]|\([^()]*\))*\)", "", body)   # parenthetical history
            body = re.split(r"(?<=[.;:])\s", body)[0].rstrip(" ;:")
            if MARKERS.search(body): return ""
            if not body.endswith("."): body += "."
        return '[Tooltip("%s")]' % body
    s = re.sub(r'\[Tooltip\("((?:[^"\\]|\\.)*)"\)\]', repl, s)
    return re.sub(r"(?m)^\s*\n(?=\s*\[Tooltip)", "", s)


def scrub_fbx(path):
    """Blender writes the source .blend's absolute path into the FBX header; overwrite each occurrence in place with a
    neutral name padded with spaces to the same byte length (the binary FBX string length prefix and every node offset
    stay valid)."""
    b = bytearray(open(path, "rb").read()); n = 0
    for m in list(re.finditer(rb"[A-Za-z]:\\[^\x00\"]*?\.blend", b)):
        old = m.group(0); name = os.path.basename(old.decode("latin-1").replace("\\", "/")).encode()
        new = (b"Source/" + name)[:len(old)].ljust(len(old), b" ")
        b[m.start():m.end()] = new; n += 1
    if n: open(path, "wb").write(bytes(b))
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edition", choices=["base", "extended"], default="base")
    ap.add_argument("--dest", default=None)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    dest = os.path.abspath(a.dest or os.path.join(os.path.dirname(ROOT), "undead-legion-production" if a.edition == "base" else "undead-legion-extended-production"))
    if os.path.abspath(dest).startswith(os.path.abspath(ROOT) + os.sep): sys.exit("the production project must live outside this repository")
    os.makedirs(dest, exist_ok=True)
    lock = os.path.join(dest, "Temp", "UnityLockfile")
    if os.path.exists(lock):
        try: os.remove(lock)                                          # a stale lock from a closed editor can be removed; an open one cannot
        except OSError: sys.exit("the production project is open in Unity: close it first (this rebuild replaces Assets/)")
    for sub in ("Assets", "ProjectSettings", "Packages"):
        p = os.path.join(dest, sub)
        if os.path.exists(p): shutil.rmtree(p)
    excl = {os.path.normcase(os.path.join(SRC, e)) for e in EXCLUDE + (EXCLUDE_BASE if a.edition == "base" else EXCLUDE_EXTENDED)}
    ign = lambda d, names: [x for x in names if os.path.normcase(os.path.join(d, x)) in excl]
    for rel in COPY:
        s, d = os.path.join(SRC, rel), os.path.join(dest, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if os.path.isdir(s): shutil.copytree(s, d, ignore=ign)
        elif os.path.exists(s): shutil.copy2(s, d)
    # the manifest
    man = json.load(open(os.path.join(SRC, "Packages", "manifest.json")))
    for p in DROP_PACKAGES + ([NAVIGATION] if a.edition == "base" else []): man["dependencies"].pop(p, None)
    json.dump(man, open(os.path.join(dest, "Packages", "manifest.json"), "w"), indent=2)
    # project settings
    ps = os.path.join(dest, "ProjectSettings", "ProjectSettings.asset"); t = open(ps, encoding="utf-8").read()
    t = re.sub(r"(?m)^(  productName: ).*$", lambda m: m.group(1) + PRODUCT[a.edition], t); t = re.sub(r"(?m)^(  cloudProjectId: ).*$", r"\1", t)
    t = re.sub(r"(?m)^(  projectName: ).*$", r"\1", t)
    open(ps, "w", encoding="utf-8").write(t)
    entries = ""
    for scene in SCENES[a.edition]:
        guid = re.search(r"guid: (\w+)", open(os.path.join(SRC, scene + ".meta")).read()).group(1)
        entries += "  - enabled: 1\n    path: " + scene + "\n    guid: " + guid + "\n"
    open(os.path.join(dest, "ProjectSettings", "EditorBuildSettings.asset"), "w").write(
        "%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n--- !u!1045 &1\nEditorBuildSettings:\n  m_ObjectHideFlags: 0\n  serializedVersion: 2\n"
        "  m_Scenes:\n" + entries + "  m_configObjects: {}\n")
    for junk in ("VersionControlSettings.asset",):
        p = os.path.join(dest, "ProjectSettings", junk)
        if os.path.exists(p): os.remove(p)
    # scripts
    nscripts = 0
    for dp, dn, fn in os.walk(os.path.join(dest, "Assets")):
        for f in fn:
            if f.endswith(".cs"):
                p = os.path.join(dp, f); s = open(p, encoding="utf-8-sig").read()
                s = add_summaries(rewrite_texts(clean_tooltips(strip_comments(s))))
                open(p, "w", encoding="utf-8", newline="\n").write(s); nscripts += 1
    # fbx source paths
    nf = nfix = 0
    for dp, dn, fn in os.walk(os.path.join(dest, "Assets")):
        for f in fn:
            if f.lower().endswith(".fbx"):
                k = scrub_fbx(os.path.join(dp, f)); nf += 1; nfix += k
    gi = os.path.join(dest, ".gitignore")
    if not os.path.exists(gi):
        open(gi, "w").write("/Library/\n/Temp/\n/Obj/\n/Logs/\n/UserSettings/\n/Build/\n/Builds/\n*.csproj\n*.sln\n.vs/\n.vscode/\n.idea/\n")
    print("production project (%s): %s\n  %d scripts cleaned, %d FBX scanned, %d embedded source paths blanked" % (a.edition, dest, nscripts, nf, nfix), flush=True)
    # the leftover scan: every text file in the copy
    left = []
    for dp, dn, fn in os.walk(dest):
        if any(x in dp for x in (os.sep + "Library", os.sep + "Temp", os.sep + "Logs", os.sep + ".vscode", "asset-store-tools")): continue   # .vscode: written by Unity's VS Code package on the verify open, not shipped
        for f in fn:
            p = os.path.join(dp, f)
            if f.lower().endswith((".cs", ".meta", ".unity", ".prefab", ".asset", ".controller", ".mask", ".mat", ".json", ".txt", ".inputactions")):
                for i, line in enumerate(open(p, encoding="utf-8", errors="ignore")):
                    if MARKERS.search(line) and not UNITY_OWN.search(line):
                        left.append("%s:%d: %s" % (os.path.relpath(p, dest), i + 1, line.strip()[:120]))
            elif f.lower().endswith(".fbx"):
                if re.search(rb"[A-Za-z]:\\\\?[^\x00]{0,200}\.blend", open(p, "rb").read()): left.append(os.path.relpath(p, dest) + ": absolute .blend path")
    print("  leftover markers: %d" % len(left))
    for l in left[:40]: print("   ", l)
    if a.verify:
        log = os.path.join(dest, "Logs", "production_verify.log"); os.makedirs(os.path.dirname(log), exist_ok=True)
        print("  opening the project in batch mode (first import is slow) ...", flush=True)
        r = subprocess.run([UNITY, "-batchmode", "-quit", "-nographics", "-projectPath", dest, "-logFile", log], capture_output=True, text=True)
        text = open(log, encoding="utf-8", errors="ignore").read()
        errs = [l for l in text.splitlines() if re.search(r"error CS\d+|Missing Script|The referenced script .* is missing", l)]
        print("  unity exit %d, compile/missing-script errors: %d" % (r.returncode, len(errs)))
        for l in errs[:20]: print("   ", l[:160])
        if r.returncode != 0 or errs: sys.exit(1)
    if left: sys.exit(1)


if __name__ == "__main__":
    main()
