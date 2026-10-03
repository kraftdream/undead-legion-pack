"""Build the full YouTube showreel from the three stage videos: an intro, a feature card, a title card per stage, the stages
(their own plain title cards cut), an outro, fades between every segment, and music.

    python tools/unity/showreel_youtube.py [--out Showreel/undead_legion_showreel.mp4] [--crf 16]
    python tools/unity/showreel_youtube.py --src Showreel/unreal --out Showreel/unreal/undead_legion_showreel_unreal.mp4                                            --engine "Rendered in Unreal Engine 5.8"      (the Unreal renders, tools/ue/showreel_unreal_all.py)

Inputs: Showreel/showreel_{modular,movement,weapons}.mp4 (ShowreelRecorder stages, each opening on a 48-frame title card).
Assets are fetched into Showreel/assets/ on first run (ignored by git):
  fonts  Cinzel Decorative Bold, Cinzel, EB Garamond - Google Fonts, SIL Open Font License 1.1 (OFL texts saved beside them)
  music  Kevin MacLeod (incompetech.com) "Five Armies" crossfaded into "Heroic Age" - CC BY 4.0: credit in the video description:
         Music: "Five Armies", "Heroic Age" by Kevin MacLeod (incompetech.com), Licensed under Creative Commons: By Attribution 4.0
         License http://creativecommons.org/licenses/by/4.0/
Cards are drawn with PIL over a blurred, darkened frame of the stages; ffmpeg (imageio-ffmpeg's binary) does the joins
(xfade fadeblack), the music crossfade, the fade-out and EBU R128 loudness normalisation to -14 LUFS (YouTube's target).
"""
import argparse, json, os, subprocess, sys, urllib.request
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SR = os.path.join(ROOT, "Showreel"); AS = os.path.join(SR, "assets"); WK = os.path.join(AS, "work")
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1920, 1080, 30
FADE = 0.8
STAGE_TITLE = 48 / 30.0            # the recorder's own title card, cut

FONTS = {"CinzelDecorative-Bold.ttf": "ofl/cinzeldecorative/CinzelDecorative-Bold.ttf", "OFL_cinzeldecorative.txt": "ofl/cinzeldecorative/OFL.txt",
         "Cinzel.ttf": "ofl/cinzel/Cinzel%5Bwght%5D.ttf", "OFL_cinzel.txt": "ofl/cinzel/OFL.txt",
         "EBGaramond.ttf": "ofl/ebgaramond/EBGaramond%5Bwght%5D.ttf", "OFL_ebgaramond.txt": "ofl/ebgaramond/OFL.txt"}
MUSIC = {"Five_Armies.mp3": "Five%20Armies.mp3", "Heroic_Age.mp3": "Heroic%20Age.mp3"}
GOLD = (222, 184, 110); GOLD_HI = (250, 226, 170); BONE = (228, 222, 208); DIM = (170, 164, 150)


def fetch():
    os.makedirs(AS, exist_ok=True); os.makedirs(WK, exist_ok=True)
    for name, path in FONTS.items():
        dst = os.path.join(AS, name)
        if not os.path.exists(dst): urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/" + path, dst)
    for name, path in MUSIC.items():
        dst = os.path.join(AS, name)
        if not os.path.exists(dst): urllib.request.urlretrieve("https://incompetech.com/music/royalty-free/mp3-royaltyfree/" + path, dst)


def run(args):
    r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y"] + args, capture_output=True, text=True)
    if r.returncode != 0: sys.exit("ffmpeg failed: " + r.stderr[-2000:])


def duration(path):
    r = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True)
    h, m, s = r.stderr.split("Duration: ")[1].split(",")[0].split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(AS, name), size)
    if weight:
        try: f.set_variation_by_name(weight)
        except Exception: pass
    return f


def still(video, t):
    out = os.path.join(WK, "still_%s_%d.png" % (os.path.basename(video)[:-4], int(t * 10)))
    run(["-ss", "%.2f" % t, "-i", video, "-frames:v", "1", out])
    return Image.open(out).convert("RGB")


def background(img, blur=14, dark=0.32):
    bg = img.filter(ImageFilter.GaussianBlur(blur)); bg = ImageEnhance.Brightness(bg).enhance(dark)
    # vignette
    v = Image.new("L", (W, H), 0); d = ImageDraw.Draw(v)
    for i in range(60):
        a = int(255 * (i / 60.0) ** 1.6); m = i * 9
        d.rectangle([m * 1.6, m * 0.9, W - m * 1.6, H - m * 0.9], outline=a, width=12)
    v = v.filter(ImageFilter.GaussianBlur(80))
    black = Image.new("RGB", (W, H), (6, 6, 8))
    return Image.composite(bg, black, v)


def text(d, xy, s, f, fill, anchor="mm", shadow=True, spacing=0):
    if shadow:
        for o in ((3, 3), (2, 2)):
            d.text((xy[0] + o[0], xy[1] + o[1]), s, font=f, fill=(0, 0, 0), anchor=anchor)
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def rule(d, cx, y, half, color=GOLD):
    d.line([cx - half, y, cx - 18, y], fill=color, width=2); d.line([cx + 18, y, cx + half, y], fill=color, width=2)
    d.polygon([(cx, y - 7), (cx + 7, y), (cx, y + 7), (cx - 7, y)], outline=color, fill=None)


ENGINE = ""                        # --engine: a small line under the intro (e.g. "Rendered in Unreal Engine 5.8")


def card_intro(bg):
    im = background(bg, 5, 0.55); d = ImageDraw.Draw(im); cx = W // 2
    text(d, (cx, 400), "UNDEAD LEGION", font("CinzelDecorative-Bold.ttf", 150), GOLD_HI)
    rule(d, cx, 500, 420)
    text(d, (cx, 575), "Modular Skeleton Army", font("Cinzel.ttf", 64, b"Regular"), BONE)
    text(d, (cx, 700), "for  Unity  &  Unreal Engine", font("Cinzel.ttf", 46, b"Bold"), GOLD)
    if ENGINE:
        text(d, (cx, 790), ENGINE, font("EBGaramond.ttf", 38, b"Regular"), DIM)
    return im


def card_features(bg):
    im = background(bg, 16, 0.32); d = ImageDraw.Draw(im); cx = W // 2
    text(d, (cx, 190), "WHAT'S INSIDE", font("Cinzel.ttf", 70, b"Bold"), GOLD_HI)
    rule(d, cx, 262, 300)
    items = [("6 skeleton classes", "Knight, Warrior, Archer, Assassin, Mage, Necromancer"),
             ("48 armour modules", "every piece fits every skeleton"),
             ("12 weapons", "swords, axes, shields, bow, staff, wand, daggers"),
             ("40+ animations", "idles, locomotion, attacks, casts, taunts, deaths"),
             ("One shared humanoid rig", "Unity Humanoid avatar  |  Unreal Engine skeleton")]
    fh = font("Cinzel.ttf", 46, b"Bold"); fb = font("EBGaramond.ttf", 38, b"Regular")
    y = 350
    for head, body in items:
        text(d, (cx, y), head, fh, BONE); text(d, (cx, y + 52), body, fb, DIM); y += 138
    return im


def card_stage(bg, title, sub):
    im = background(bg, 12, 0.42); d = ImageDraw.Draw(im); cx = W // 2
    text(d, (cx, 490), title, font("CinzelDecorative-Bold.ttf", 120), GOLD_HI)
    rule(d, cx, 580, 320)
    text(d, (cx, 650), sub, font("EBGaramond.ttf", 48, b"Medium"), BONE)
    return im


def card_outro(bg):
    im = background(bg, 5, 0.5); d = ImageDraw.Draw(im); cx = W // 2
    text(d, (cx, 380), "UNDEAD LEGION", font("CinzelDecorative-Bold.ttf", 136), GOLD_HI)
    rule(d, cx, 470, 400)
    text(d, (cx, 540), "Modular Skeleton Army", font("Cinzel.ttf", 58, b"Regular"), BONE)
    text(d, (cx, 680), "Unity   |   Unreal Engine", font("Cinzel.ttf", 52, b"Bold"), GOLD)
    text(d, (cx, 770), "one rig  ·  modular armour  ·  shared animation set", font("EBGaramond.ttf", 40, b"Regular"), DIM)
    return im


def card_clip(img, seconds, name, zoom=0.035):
    """A slow push-in, rendered here frame by frame: a BICUBIC affine transform from a 2x source keeps the scale and the centre
    sub-pixel exact (ffmpeg's zoompan rounds the crop to whole pixels per frame, which made the text shake), piped raw to x264."""
    png = os.path.join(WK, name + ".png"); img.save(png)
    out = os.path.join(WK, name + ".mp4"); n = int(round(seconds * FPS))
    src = img.resize((W * 2, H * 2), Image.LANCZOS); sw, sh = src.size
    p = subprocess.Popen([FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / float(max(1, n - 1)); t = t * t * (3 - 2 * t)          # smoothstep: eases in and out
        z = 1.0 + zoom * t
        a = sw / (W * z)                                               # source pixels per output pixel
        cx, cy = sw / 2.0, sh / 2.0
        frame = src.transform((W, H), Image.AFFINE, (a, 0, cx - a * W / 2.0, 0, a, cy - a * H / 2.0), resample=Image.BICUBIC)
        p.stdin.write(frame.tobytes())
    p.stdin.close(); p.wait()
    if p.returncode != 0: sys.exit("ffmpeg failed on " + name)
    return out


def stage_clip(video, name):
    out = os.path.join(WK, name + ".mp4")
    run(["-ss", "%.4f" % STAGE_TITLE, "-i", video, "-an", "-vf", "fps=%d,format=yuv420p" % FPS, "-c:v", "libx264", "-crf", "12", "-preset", "slow", out])
    return out


def main():
    global WK, ENGINE
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(SR, "undead_legion_showreel.mp4")); ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--src", default=SR, help="folder with showreel_{modular,movement,weapons}.mp4 (Showreel/unreal for the Unreal renders)")
    ap.add_argument("--engine", default="", help="a line under the intro title")
    a = ap.parse_args()
    ENGINE = a.engine
    if os.path.abspath(a.src) != os.path.abspath(SR):
        WK = os.path.join(AS, "work_" + os.path.basename(os.path.normpath(a.src)))
    fetch()
    mod, mov, wpn = (os.path.join(a.src, "showreel_%s.mp4" % s) for s in ("modular", "movement", "weapons"))
    for v in (mod, mov, wpn):
        if not os.path.exists(v): sys.exit("missing " + v)
    print("stills ...", flush=True)
    s_knight = still(wpn, 32.0); s_mod = still(mod, 25.0); s_mov = still(mov, 20.0); s_wpn = still(wpn, 12.0); s_nec = still(wpn, 95.0)
    print("cards ...", flush=True)
    segs = [card_clip(card_intro(s_knight), 6.0, "c_intro"),
            card_clip(card_features(s_mod), 8.5, "c_features", 0.02),
            card_clip(card_stage(s_mod, "MODULAR", "Any armour piece and any weapon on any skeleton"), 3.2, "c_modular"),
            stage_clip(mod, "s_modular"),
            card_clip(card_stage(s_mov, "MOVEMENT", "Two locomotion sets with root motion"), 3.2, "c_movement"),
            stage_clip(mov, "s_movement"),
            card_clip(card_stage(s_wpn, "WEAPONS & UTILS", "Attacks, blocks, casts, taunts and deaths"), 3.2, "c_weapons"),
            stage_clip(wpn, "s_weapons"),
            card_clip(card_outro(s_nec), 7.0, "c_outro")]
    durs = [duration(s) for s in segs]
    print("segments:", ", ".join("%s %.1fs" % (os.path.basename(s)[:-4], d) for s, d in zip(segs, durs)), flush=True)
    # the joins: xfade fadeblack between every pair
    inputs = []
    for s in segs: inputs += ["-i", s]
    fc = []; prev = "[0:v]"; t = durs[0]
    for i in range(1, len(segs)):
        off = t - FADE; lab = "[v%d]" % i
        fc.append("%s[%d:v]xfade=transition=fadeblack:duration=%.2f:offset=%.3f%s" % (prev, i, FADE, off, lab))
        prev = lab; t = off + durs[i]
    total = t
    # fade in from black and out to black at the very ends
    fc.append("%sfade=t=in:st=0:d=0.8,fade=t=out:st=%.3f:d=1.2,format=yuv420p[vout]" % (prev, total - 1.2))
    # music: Five Armies crossfaded into Heroic Age, trimmed to the video, faded, normalised
    m1, m2 = os.path.join(AS, "Five_Armies.mp3"), os.path.join(AS, "Heroic_Age.mp3")
    ai = len(segs)
    fc.append("[%d:a][%d:a]acrossfade=d=4:c1=tri:c2=tri,atrim=0:%.3f,afade=t=in:st=0:d=1.5,afade=t=out:st=%.3f:d=4,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]" % (ai, ai + 1, total, total - 4))
    run(inputs + ["-i", m1, "-i", m2, "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
                  "-c:v", "libx264", "-crf", str(a.crf), "-preset", "slow", "-pix_fmt", "yuv420p", "-r", str(FPS),
                  "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", a.out])
    print("wrote %s (%.1f MB, %.1f s)" % (os.path.relpath(a.out, ROOT), os.path.getsize(a.out) / 1048576.0, duration(a.out)), flush=True)
    json.dump({"segments": [os.path.basename(s) for s in segs], "durations": durs, "total": total}, open(os.path.join(WK, "layout.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
