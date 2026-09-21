"""Pack roughness (+ metallic) into <part>_metallicsmoothness.png and copy the shipped
textures into the Unity project, for every character.

    blender -b -P tools/pack_textures.py [-- SkeletonMage ...]

Per CLAUDE.md 7: URP has no roughness input, so R = metallic (0 when the character has
no metallic map), A = 1 - roughness, into `<part>_metallicsmoothness.png`, which is what
`_MetallicGlossMap` expects with _Metallic = 1 and _Smoothness = 1 on the material.
Colour and normal maps are copied as they are. `*_orig.png`, raw roughness/metallic and
the Knight's `armor_color2` variant are NOT shipped. Uses Blender's image API + numpy so
no Pillow install is needed. Copies are decided by CONTENT, never by mtime: a git
checkout stamps every file with the same time, and the Knight's stale body texture in
Unity (from the first import, before the body was re-textured) survived an mtime check
and showed up as 33 % of the body on black.
"""
import bpy, os, sys, shutil, hashlib
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITY_TEX = os.path.join(ROOT, "skeletons", "Assets", "UndeadLegion", "Textures")
CHARS = ["SkeletonKnight", "SkeletonArcher", "SkeletonAssassin", "SkeletonMage", "SkeletonNecromancer", "SkeletonWarrior"]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if argv:
    CHARS = argv


def log(*a):
    print("[pack]", *a); sys.stdout.flush()


def load_gray(path):
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = 'Non-Color'          # raw bytes, no sRGB linearisation
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    g = px.reshape(h, w, 4)[:, :, 0].copy()
    bpy.data.images.remove(img)
    return g, w, h


def pack(char, part):
    src_dir = os.path.join(ROOT, char)
    rough_p = os.path.join(src_dir, part + "_roughness.png")
    met_p = os.path.join(src_dir, part + "_metallic.png")
    out_dir = os.path.join(UNITY_TEX, char)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, part + "_metallicsmoothness.png")
    if not os.path.exists(rough_p):
        log(char, part, "no roughness map, skipped"); return
    rough, w, h = load_gray(rough_p)
    if os.path.exists(met_p):
        met, mw, mh = load_gray(met_p)
        if (mw, mh) != (w, h):
            raise RuntimeError("%s %s: metallic %dx%d != roughness %dx%d" % (char, part, mw, mh, w, h))
    else:
        met = np.zeros_like(rough)
    rgba = np.zeros((h, w, 4), dtype=np.float32)
    rgba[:, :, 0] = met
    rgba[:, :, 3] = 1.0 - rough
    img = bpy.data.images.new("_pack", w, h, alpha=True, is_data=True)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = out; img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    log("%s %-5s -> %s  (%dx%d, metallic %s, smoothness mean %.2f)" % (
        char, part, os.path.relpath(out, ROOT), w, h, "map" if os.path.exists(met_p) else "0", float((1 - rough).mean())))


def digest(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def copy_maps(char):
    out_dir = os.path.join(UNITY_TEX, char)
    os.makedirs(out_dir, exist_ok=True)
    for part in ("body", "armor"):
        for m in ("color", "normal"):
            src = os.path.join(ROOT, char, "%s_%s.png" % (part, m))
            dst = os.path.join(out_dir, "%s_%s.png" % (part, m))
            if not os.path.exists(src):
                log(char, part, m, "MISSING"); continue
            if not os.path.exists(dst) or digest(dst) != digest(src):
                shutil.copyfile(src, dst); log("copied", os.path.relpath(dst, ROOT))


# Weapons (2026-09-20): Weapons/<lower>_{color,normal,roughness[,metallic]}.png per textured
# weapon -> Textures/Weapons/<Name>_{color,normal,metallicsmoothness}.png, named after the
# SM_<Name> mesh so the import setup can pair them.
WEAPON_MAPS = {"H1Sword": "h1sword", "H1Dagger": "h1dagger", "H1Axe": "h1axe", "H1Mace": "h1mace", "H1HeaterShield": "h1heatershield", "H1RoundShield": "h1roundshield",
               "H2Axe": "h2axe", "H2Longsword": "h2longsword", "H2MagicStuff": "h2magicstuff", "H2Recurvebow": "h2recurvebow", "H1Wand": "h1wand", "Arrow": "arrow"}   # 4a70422: the last four have no roughness/metallic maps (colour + normal only, the Arrow colour only)


def pack_weapons():
    out_dir = os.path.join(UNITY_TEX, "Weapons"); os.makedirs(out_dir, exist_ok=True)
    for name, low in WEAPON_MAPS.items():
        src_dir = os.path.join(ROOT, "Weapons")
        for m in ("color", "normal"):
            src = os.path.join(src_dir, "%s_%s.png" % (low, m)); dst = os.path.join(out_dir, "%s_%s.png" % (name, m))
            if not os.path.exists(src):
                log("Weapons", name, m, "MISSING"); continue
            if not os.path.exists(dst) or digest(dst) != digest(src):
                shutil.copyfile(src, dst); log("copied", os.path.relpath(dst, ROOT))
        rough_p = os.path.join(src_dir, low + "_roughness.png"); met_p = os.path.join(src_dir, low + "_metallic.png")
        if not os.path.exists(rough_p):
            log("Weapons", name, "no roughness map, skipped"); continue
        rough, w, h = load_gray(rough_p)
        met = load_gray(met_p)[0] if os.path.exists(met_p) else np.zeros_like(rough)
        rgba = np.zeros((h, w, 4), dtype=np.float32); rgba[:, :, 0] = met; rgba[:, :, 3] = 1.0 - rough
        img = bpy.data.images.new("_pack", w, h, alpha=True, is_data=True); img.pixels.foreach_set(rgba.ravel())
        out = os.path.join(out_dir, name + "_metallicsmoothness.png"); img.filepath_raw = out; img.file_format = 'PNG'; img.save(); bpy.data.images.remove(img)
        log("Weapons %-15s -> %s  (%dx%d, metallic %s, smoothness mean %.2f)" % (name, os.path.relpath(out, ROOT), w, h, "map" if os.path.exists(met_p) else "0", float((1 - rough).mean())))


if argv == ["Weapons"]:
    pack_weapons()
else:
    for c in CHARS:
        copy_maps(c)
        for part in ("body", "armor"):
            pack(c, part)
    if not argv:
        pack_weapons()
