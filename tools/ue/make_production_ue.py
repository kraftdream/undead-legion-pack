"""Build the Fab production package of the Unreal project.

    python tools/ue/make_production_ue.py [--verify] [--no-zip]

Writes ../undead-legion-production-ue/UndeadLegion/ (a sibling of this repo, like the Unity production project) with
Config/, Content/UndeadLegion/ and UndeadLegion.uproject only, and zips it as ../undead-legion-production-ue/
UndeadLegion_UE58.zip (top folder UndeadLegion/). Nothing that describes how the pack was made ships:

  * the showreel: Demo/Maps/UndeadLegion_Showreel, Demo/Showreel/ (the 25 level sequences), Demo/Blueprints/BP_ShowreelDirector
  * the Interchange import pipelines Pipelines/IP_* (import settings, not content)
  * Content/Developers, Content/Collections, every engine-generated folder
  * the seven editor plugins the build went through (MCP toolsets, Python, editor scripting, Movie Render Queue, Sequencer
    scripting): the package is Blueprint-only with no plugin dependency
  * the project name "(development)", the MCP auto-start setting, the Python remote-execution setting

The buyer manual must already be printed: `python tools/make_documentation.py ue` -> skeletons_ue/Content/UndeadLegion/
Documentation.pdf (it is copied with the content). Then the audit (every rule Fab rejected the creatures pack on, plus a scan
of every asset for the dropped plugins' modules), and with --verify a headless CompileAllBlueprints run of the COPY on 5.8
(the editor-generated folders are removed again before the zip). Exit 2 on an audit failure.
"""
import argparse, json, os, re, shutil, subprocess, sys, time, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "skeletons_ue")
OUT_ROOT = os.path.join(os.path.dirname(ROOT), "undead-legion-production-ue")
SHIP = "UndeadLegion"
OUT = os.path.join(OUT_ROOT, SHIP)
ZIP = os.path.join(OUT_ROOT, SHIP + "_UE58.zip")
ENGINE = "5.8"
UE_CMD = r"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"

PRODUCT = "Content/UndeadLegion"
EXCLUDE = [                                   # relative to the project, files or directories
    PRODUCT + "/Demo/Maps/UndeadLegion_Showreel.umap",
    PRODUCT + "/Demo/Showreel",
    PRODUCT + "/Demo/Blueprints/BP_ShowreelDirector.uasset",
    PRODUCT + "/Pipelines",
]
CONFIG_DROP = ["DefaultEditorPerProjectUserSettings.ini", "DefaultEditor.ini"]   # the MCP auto-start; an empty file
# a shipped asset must not import a module of a plugin the package does not enable
DROPPED_MODULES = [b"/Script/PythonScriptPlugin", b"/Script/ModelContextProtocol", b"/Script/MCPClientToolset", b"/Script/AllToolsets",
                   b"/Script/EditorScriptingUtilities", b"/Script/MovieRenderPipeline", b"/Script/SequencerScripting"]
# (not /Script/MovieScene or /Script/LevelSequence: engine runtime modules; every AnimSequence imports MovieScene for its data model)
TOOLING = re.compile(rb"modelcontextprotocol|mcpclienttoolset|alltoolsets|unrealmcp|claude|anthropic|scratchpad", re.I)
FORBIDDEN = re.compile(r"Claude|Anthropic|Fable|Opus|Sonnet|CLAUDE\.md|scratchpad|MCP|execute_code|Co-Authored|claude\.ai|session_[0-9A-Za-z]{6,}")
DOC_FORBIDDEN = re.compile(r"tools/ue|ue_build|ue_py|ue_import|showreel|Showreel|ModelContextProtocol|MCP|Kimodo|retarget\.py|anim_batch")
TEXT_EXT = (".ini", ".uproject", ".md", ".txt", ".json", ".html")
CRUFT = ("Saved", "Intermediate", "DerivedDataCache", "Binaries", "Build", ".vs")

fails = []


def fail(msg):
    fails.append(msg); print("  FAIL", msg)


def say(msg):
    print("[prod]", msg)


def excluded(rel):
    rel = rel.replace("\\", "/")
    return any(rel == e or rel.startswith(e + "/") for e in EXCLUDE)


def copy_tree(src_rel):
    src = os.path.join(SRC, src_rel)
    n = 0
    for d, dirs, files in os.walk(src):
        rel_d = os.path.relpath(d, SRC).replace("\\", "/")
        dirs[:] = [x for x in dirs if not excluded(rel_d + "/" + x)]
        for f in files:
            rel = rel_d + "/" + f
            if excluded(rel):
                continue
            dst = os.path.join(OUT, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(d, f), dst); n += 1
    return n


def src_uproject():
    return [f for f in os.listdir(SRC) if f.endswith(".uproject")][0]


def write_uproject():
    d = json.load(open(os.path.join(SRC, src_uproject()), encoding="utf-8"))
    d["EngineAssociation"] = ENGINE
    d["Description"] = "Undead Legion - Modular Skeleton Army: six skeleton classes on one shared skeleton, 48 armour modules, 12 weapons, 58 animations."
    dropped = [p["Name"] for p in d.get("Plugins", [])]
    d["Plugins"] = []
    p = os.path.join(OUT, SHIP + ".uproject")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(d, fh, indent="\t"); fh.write("\n")
    say("%s.uproject: engine %s, plugins dropped: %s" % (SHIP, ENGINE, ", ".join(dropped)))


def fix_config():
    cfg = os.path.join(OUT, "Config")
    for f in CONFIG_DROP:
        p = os.path.join(cfg, f)
        if os.path.exists(p):
            os.remove(p)
    p = os.path.join(cfg, "DefaultGame.ini")
    s = open(p, encoding="utf-8").read()
    s = re.sub(r"(?m)^ProjectName=.*$", "ProjectName=Undead Legion - Modular Skeleton Army", s)
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    p = os.path.join(cfg, "DefaultEngine.ini")
    s = open(p, encoding="utf-8").read()
    s = re.sub(r"\[/Script/PythonScriptPlugin\.PythonScriptPluginSettings\]\s*\n(?:[^\[\n][^\n]*\n|\n)*", "", s)
    s = s.replace("/Script/" + os.path.splitext(src_uproject())[0], "/Script/" + SHIP)
    s = re.sub(r"\n{3,}", "\n\n", s).lstrip("\n")
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    say("Config: %s removed, project renamed, Python remote execution dropped" % ", ".join(CONFIG_DROP))


def audit():
    say("audit: root entries")
    root = sorted(os.listdir(OUT))
    if root != ["Config", "Content", SHIP + ".uproject"]:
        fail("root must be Config, Content, %s.uproject: %s" % (SHIP, root))
    sub = os.listdir(os.path.join(OUT, "Content"))
    if sub != [SHIP]:
        fail("Content must hold exactly one folder: %s" % sub)
    say("audit: no generated folders, no stray assets, no empty directories")
    for c in CRUFT:
        if os.path.exists(os.path.join(OUT, c)):
            fail("generated folder shipped: " + c)
    assets = []
    for d, dirs, files in os.walk(OUT):
        rel_d = os.path.relpath(d, OUT).replace("\\", "/")
        if not dirs and not files:
            fail("empty directory: " + rel_d)
        for f in files:
            rel = (rel_d + "/" + f).replace("./", "")
            if f.endswith((".uasset", ".umap")):
                assets.append(rel)
                if not rel.startswith("Content/"):
                    fail("asset outside Content: " + rel)
            elif not (rel.startswith("Config/") or rel.endswith(".uproject") or rel.endswith(".pdf")):
                fail("unexpected file: " + rel)
    say("audit: %d assets; redirectors, pipelines, showreel leftovers, dropped plugins' modules, tooling names" % len(assets))
    for rel in assets:
        b = open(os.path.join(OUT, rel), "rb").read()
        if b"ObjectRedirector" in b:
            fail("redirector: " + rel)
        base = os.path.basename(rel)
        if base.startswith(("IP_", "LS_")) or "Showreel" in rel:
            fail("dev asset shipped: " + rel)
        for m in DROPPED_MODULES:
            if m in b:
                fail("%s imports %s (plugin not shipped)" % (rel, m.decode()))
        hit = TOOLING.search(b)
        if hit:
            fail("tooling name %r in %s" % (hit.group(0), rel))
    say("audit: text files")
    for d, _, files in os.walk(OUT):
        for f in files:
            if f.endswith(TEXT_EXT):
                p = os.path.join(d, f)
                s = open(p, encoding="utf-8", errors="replace").read()
                for m in FORBIDDEN.finditer(s):
                    fail("forbidden %r in %s" % (m.group(0), os.path.relpath(p, OUT)))
                if TOOLING.search(s.encode()):
                    fail("tooling name in " + os.path.relpath(p, OUT))
    up = json.load(open(os.path.join(OUT, SHIP + ".uproject"), encoding="utf-8"))
    if up.get("Plugins") or up.get("EngineAssociation") != ENGINE:
        fail("uproject: plugins %s, engine %s" % (up.get("Plugins"), up.get("EngineAssociation")))
    say("audit: the manual")
    pdf = os.path.join(OUT, PRODUCT, "Documentation.pdf")
    if not os.path.exists(pdf):
        fail("missing %s/Documentation.pdf (run: python tools/make_documentation.py ue)" % PRODUCT)
    src_html = os.path.join(ROOT, "tools", "docs", "UndeadLegion_UE_Documentation.html")
    for m in DOC_FORBIDDEN.finditer(open(src_html, encoding="utf-8").read()):
        fail("manual source mentions %r" % m.group(0))
    return assets


def inventory(assets):
    """Count what ships by the asset name prefix (the Fab form's figures; the registry is not available offline)."""
    kinds = {"SK_": "skeletal meshes", "SM_": "static meshes", "T_": "textures", "MI_": "material instances", "M_": "materials",
             "AM_": "montages", "A_": "animation sequences", "ABP_": "animation blueprints", "BP_": "blueprints", "WBP_": "widgets",
             "AN_": "notifies", "PA_": "physics assets", "SKEL_": "skeletons"}
    counts = {}
    for rel in assets:
        base = os.path.basename(rel)
        if rel.endswith(".umap"):
            k = "maps"
        else:
            k = next((v for p, v in sorted(kinds.items(), key=lambda kv: -len(kv[0])) if base.startswith(p)), "other")
        counts[k] = counts.get(k, 0) + 1
    say("inventory: %d assets: %s" % (len(assets), ", ".join("%d %s" % (v, k) for k, v in sorted(counts.items()))))
    return counts


def verify():
    log = os.path.join(OUT_ROOT, "verify_compile.log")
    say("verify: CompileAllBlueprints on the copy (headless, NullRHI); log " + log)
    t0 = time.time()
    r = subprocess.run([UE_CMD, os.path.join(OUT, SHIP + ".uproject"), "-run=CompileAllBlueprints", "-unattended", "-nopause", "-nosplash",
                        "-NullRHI", "-stdout", "-FullStdOutLogOutput", "-abslog=" + log], capture_output=True, text=True, timeout=3600)
    s = open(log, encoding="utf-8", errors="replace").read() if os.path.exists(log) else r.stdout
    lines = s.splitlines()
    errs = [l for l in lines if re.search(r"(?i)(^|\W)error(\W|$)", l) and "ErrorLevel" not in l and " 0 error(s)" not in l]
    compiled = [l for l in lines if "Compile of" in l and "successful" in l and "/Game/" + SHIP + "/" in l]
    failed = [l for l in lines if "Compile of" in l and "successful" not in l and "/Game/" in l]
    say("verify: %d pack Blueprints compiled, %d failed" % (len(compiled), len(failed)))
    if not compiled or failed:
        fail("verify: pack Blueprints not compiled cleanly")
    warns = [l for l in lines if "LogBlueprint: Warning" in l or "LogLinker: Warning" in l or "LogLoad: Warning" in l]
    summ = [l for l in lines if "CompileAllBlueprints" in l and ("compiled" in l.lower() or "Total" in l or "Blueprint" in l)][-4:]
    say("verify: exit %d in %.0f s, %d error lines, %d load / blueprint warnings" % (r.returncode, time.time() - t0, len(errs), len(warns)))
    for l in errs[:15] + warns[:10] + summ:
        print("   ", l.strip()[:220])
    if r.returncode != 0 or errs:
        fail("verify: CompileAllBlueprints reported errors (see the log)")
    for c in CRUFT:
        shutil.rmtree(os.path.join(OUT, c), ignore_errors=True)


def make_zip():
    if os.path.exists(ZIP):
        os.remove(ZIP)
    n = 0
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for d, _, files in os.walk(OUT):
            for f in files:
                p = os.path.join(d, f)
                z.write(p, SHIP + "/" + os.path.relpath(p, OUT).replace("\\", "/")); n += 1
    say("zip: %s, %d files, %.1f MB" % (ZIP, n, os.path.getsize(ZIP) / 1e6))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="run CompileAllBlueprints on the copy with UnrealEditor-Cmd 5.8")
    ap.add_argument("--no-zip", action="store_true")
    a = ap.parse_args()
    shutil.rmtree(OUT, ignore_errors=True)
    if os.path.exists(OUT):
        sys.exit("cannot clear %s (is the production project open in Unreal?)" % OUT)
    os.makedirs(OUT)
    n = copy_tree("Config") + copy_tree(PRODUCT)
    say("copied %d files from %s" % (n, os.path.relpath(SRC, ROOT)))
    write_uproject()
    fix_config()
    assets = audit()
    inventory(assets)
    if a.verify and not fails:
        verify()
    if fails:
        print("[prod] AUDIT FAILED: %d problem(s)" % len(fails)); sys.exit(2)
    if not a.no_zip:
        make_zip()
    say("done: " + OUT)


if __name__ == "__main__":
    main()
