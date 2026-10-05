"""Put the UE5 template's mannequin content into the Epic dev project for testing (system Python, 2026-10-05).

    python tools/ue/epic_mannequin_content.py

Copies <UE 5.8>/Templates/TemplateResources/High/Characters/Content/Mannequins into
skeletons_ue_epic/Content/Characters/Mannequins (git-ignored, never shipped) when it is missing. The folder MUST sit at
Content/Characters/Mannequins: the template's assets reference each other at /Game/Characters/Mannequins/..., and copied anywhere
else the meshes and clips import with no skeleton (a poseable mesh then asserts and crashes the editor). Run it on a fresh clone
before tools/ue/ue_uetest.py; then `ue_py.py tools/ue/epic_demo_probe.py compat` makes SK_Mannequin list SKEL_UndeadLegion.
"""
import os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = r"C:\Program Files\Epic Games\UE_5.8\Templates\TemplateResources\High\Characters\Content\Mannequins"
DST = os.path.join(ROOT, "skeletons_ue_epic", "Content", "Characters", "Mannequins")

if os.path.isdir(DST):
    print("already there:", DST)
    sys.exit(0)
if not os.path.isdir(SRC):
    sys.exit("template content not found: " + SRC)
shutil.copytree(SRC, DST)
n = sum(len(f) for _, _, f in os.walk(DST))
print("copied %d files -> %s" % (n, DST))
