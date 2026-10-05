"""Print the buyer documentation to PDF into the Unity project.

    python tools/make_documentation.py [base|extended|ue]   (base + extended when no argument; `ue` prints the Unreal manual
                                                            to skeletons_ue/Content/UndeadLegion/Documentation.pdf)

Sources: tools/docs/UndeadLegion_Documentation.html and tools/docs/UndeadLegion_Extended_Documentation.html (fonts: Cinzel,
Cinzel Decorative, EB Garamond - SIL OFL, fetched with the showreel assets). Outputs:
  skeletons/Assets/UndeadLegion/Documentation/UndeadLegion_Documentation.pdf
  skeletons/Assets/UndeadLegion/Extended/Documentation/UndeadLegion_Extended_Documentation.pdf
printed by Microsoft Edge headless (A4, no header or footer). tools/make_production.py copies them with the rest of
Assets/UndeadLegion (the extended one only into the extended edition). A new PDF gets a .meta written here, so its GUID is
stable from the first run.
"""
import os, shutil, subprocess, sys, tempfile, uuid
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "unity"))
import showreel_youtube as sy
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ASSETS = os.path.join(ROOT, "skeletons", "Assets", "UndeadLegion")
DOCS = {
    "base": ("UndeadLegion_Documentation.html", os.path.join(ASSETS, "Documentation", "UndeadLegion_Documentation.pdf")),
    "extended": ("UndeadLegion_Extended_Documentation.html", os.path.join(ASSETS, "Extended", "Documentation", "UndeadLegion_Extended_Documentation.pdf")),
    # the Unreal manual lives INSIDE the Unreal project's content folder (Fab wants the documentation in the package; the
    # editor ignores a PDF under Content) and gets no .meta: tools/ue/make_production_ue.py ships it as it is
    # since 2026-10-05 the Unreal manual describes the EPIC-skeleton project and prints into it; the Mixamo project's PDF in
    # skeletons_ue/Content stays as printed on 2026-10-05 (its HTML is in git history before that date)
    "ue": ("UndeadLegion_UE_Documentation.html", os.path.join(ROOT, "skeletons_ue_epic", "Content", "UndeadLegion", "Documentation.pdf")),
}
DEFAULT = ("base", "extended")   # `ue` only on request: it is printed into the other project
FOLDER_META = "fileFormatVersion: 2\nguid: %s\nfolderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n"
FILE_META = "fileFormatVersion: 2\nguid: %s\nDefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n"


def ensure_meta(path, folder):
    meta = path + ".meta"
    if not os.path.exists(meta): open(meta, "w", newline="\n").write((FOLDER_META if folder else FILE_META) % uuid.uuid4().hex)


def build(src_name, out):
    work = tempfile.mkdtemp(prefix="ul_doc_"); os.makedirs(os.path.join(work, "fonts"))
    for f in ("CinzelDecorative-Bold.ttf", "Cinzel.ttf", "EBGaramond.ttf"): shutil.copy2(os.path.join(sy.AS, f), os.path.join(work, "fonts", f))
    html = os.path.join(work, "doc.html"); shutil.copy2(os.path.join(ROOT, "tools", "docs", src_name), html)
    unity = out.startswith(ASSETS)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if unity: ensure_meta(os.path.dirname(out), True)
    tmp_pdf = os.path.join(work, "doc.pdf")
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=5000", "--print-to-pdf=" + tmp_pdf, "file:///" + html.replace("\\", "/")], capture_output=True, timeout=180)
    if not os.path.exists(tmp_pdf): sys.exit("Edge did not write the PDF for " + src_name)
    shutil.copy2(tmp_pdf, out)
    if unity: ensure_meta(out, False)
    shutil.rmtree(work, ignore_errors=True)
    print("wrote %s (%.0f KB)" % (os.path.relpath(out, ROOT), os.path.getsize(out) / 1024.0))


sy.fetch()
for key in (sys.argv[1:] or DEFAULT):
    build(*DOCS[key])
