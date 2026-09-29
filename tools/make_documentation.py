"""Print the buyer documentation to PDF into the Unity project.

    python tools/make_documentation.py

Source: tools/docs/UndeadLegion_Documentation.html (fonts: Cinzel, Cinzel Decorative, EB Garamond - SIL OFL, fetched with the
showreel assets). Output: skeletons/Assets/UndeadLegion/Documentation/UndeadLegion_Documentation.pdf, printed by Microsoft Edge
headless (A4, no header or footer). tools/make_production.py copies it with the rest of Assets/UndeadLegion.
"""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "unity"))
import showreel_youtube as sy
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SRC = os.path.join(ROOT, "tools", "docs", "UndeadLegion_Documentation.html")
OUT = os.path.join(ROOT, "skeletons", "Assets", "UndeadLegion", "Documentation", "UndeadLegion_Documentation.pdf")

sy.fetch()
work = tempfile.mkdtemp(prefix="ul_doc_"); os.makedirs(os.path.join(work, "fonts"))
for f in ("CinzelDecorative-Bold.ttf", "Cinzel.ttf", "EBGaramond.ttf"): shutil.copy2(os.path.join(sy.AS, f), os.path.join(work, "fonts", f))
html = os.path.join(work, "doc.html"); shutil.copy2(SRC, html)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
tmp_pdf = os.path.join(work, "doc.pdf")
subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=5000", "--print-to-pdf=" + tmp_pdf, "file:///" + html.replace("\\", "/")], capture_output=True, timeout=180)
if not os.path.exists(tmp_pdf): sys.exit("Edge did not write the PDF")
shutil.copy2(tmp_pdf, OUT); shutil.rmtree(work, ignore_errors=True)
print("wrote %s (%.0f KB)" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1024.0))
