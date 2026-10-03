"""Encode an Unreal showreel render (PNG frames from ue_showreel.py) to MP4 with the Unity recorder's caption panel.

    python tools/ue/showreel_encode_ue.py [--frames Showreel/unreal/modular_test] [--out Showreel/unreal/showreel_modular_test.mp4]
                                          [--title "Skeleton Warrior"] [--text "Six class presets on one shared humanoid rig"]
                                          [--line-at "0.8:<line>" ...]

The panel is ShowreelRecorder.BuildCanvas at 1920 x 1080: a box at (60, 60), 600 x 170, colour (0.06, 0.07, 0.09, 0.72);
the title bold (0.96, 0.95, 0.90) on ONE line centred on y 113, 40 px shrunk until it fits the 540 px text box (Unity's
ShowCaption); the line 24 px (0.80, 0.82, 0.86) wrapped at 540 px and centred on y 181 (Unity's 70 px box, Wrap); both at
x 90, in Arial (Unity's built-in UI font is an Arial), measured with the Windows font engine. `--line-at` switches the line
at a time (the recorder appends the running attack's name). ffmpeg from the imageio-ffmpeg package (pip install --user
imageio-ffmpeg); H.264 crf 16, yuv420p, faststart, as the Unity stages.
"""
import argparse, ctypes, os, subprocess, sys
from ctypes import wintypes

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT = "C\\:/Windows/Fonts/arial.ttf"
BOLD = "C\\:/Windows/Fonts/arialbd.ttf"
BOX_W = 540          # the panel's text width (600 px panel, text at x 30, 540 wide)
LEAD = 28            # line spacing of a wrapped caption line


def text_width(text, px, bold=False):
    """Pixel width of `text` in Arial at `px` (the em height), from GDI."""
    gdi, user = ctypes.windll.gdi32, ctypes.windll.user32
    # 64-bit handles: without explicit types ctypes truncates them to int and later calls overflow
    user.GetDC.restype = wintypes.HDC
    user.GetDC.argtypes = [wintypes.HWND]
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    gdi.CreateFontW.restype = wintypes.HFONT
    gdi.CreateFontW.argtypes = [ctypes.c_int] * 5 + [wintypes.DWORD] * 8 + [wintypes.LPCWSTR]
    gdi.SelectObject.restype = wintypes.HGDIOBJ
    gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi.GetTextExtentPoint32W.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.SIZE)]
    hdc = user.GetDC(0)
    f = gdi.CreateFontW(-px, 0, 0, 0, 700 if bold else 400, 0, 0, 0, 0, 0, 0, 4, 0, "Arial")
    old = gdi.SelectObject(hdc, f)
    size = wintypes.SIZE()
    gdi.GetTextExtentPoint32W(hdc, text, len(text), ctypes.byref(size))
    gdi.SelectObject(hdc, old)
    gdi.DeleteObject(f)
    user.ReleaseDC(0, hdc)
    return size.cx


def wrap(text, px, width=BOX_W):
    """Unity's Text with horizontalOverflow Wrap: break at spaces so no line exceeds the box."""
    rows, cur = [], ""
    for w in text.split(" "):
        t = (cur + " " + w) if cur else w
        if cur and text_width(t, px) > width:
            rows.append(cur)
            cur = w
        else:
            cur = t
    return rows + [cur]


def esc(t):
    # a ' cannot be escaped inside ffmpeg's quoted filter strings: the typographic apostrophe renders the same in Arial
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’")


def filters(title, text, line_at):
    tsize = 40
    while tsize > 12 and text_width(title, tsize, True) > BOX_W:
        tsize -= 1
    vf = ["drawbox=x=60:y=60:w=600:h=170:color=0x0F1217@0.72:t=fill",
          "drawtext=fontfile='%s':text='%s':fontsize=%d:fontcolor=0xF5F2E6:x=90:y=113-th/2" % (BOLD, esc(title), tsize)]
    lines = [(0.0, text)] + sorted((float(x.split(":", 1)[0]), x.split(":", 1)[1]) for x in line_at)
    for i, (t0, txt) in enumerate(lines):
        t1 = lines[i + 1][0] if i + 1 < len(lines) else 1e9
        rows = wrap(txt, 24)
        for k, row in enumerate(rows):
            yc = 181 + (k - (len(rows) - 1) / 2.0) * LEAD
            # enable on gte / lt: ffmpeg's between() is inclusive at both ends
            vf.append("drawtext=fontfile='%s':text='%s':fontsize=24:fontcolor=0xCCD1DB:x=90:y=%d-th/2:enable='gte(t\\,%.3f)*lt(t\\,%.3f)'"
                      % (FONT, esc(row), yc, t0, t1))
    return ",".join(vf), tsize


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=os.path.join(ROOT, "Showreel", "unreal", "modular_test"))
    ap.add_argument("--out", default=os.path.join(ROOT, "Showreel", "unreal", "showreel_modular_test.mp4"))
    ap.add_argument("--title", default="Skeleton Warrior")
    ap.add_argument("--text", default="Six class presets on one shared humanoid rig")
    ap.add_argument("--line-at", action="append", default=[], help="SECONDS:TEXT, repeatable")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=16)
    a = ap.parse_args()
    import imageio_ffmpeg
    vf, tsize = filters(a.title, a.text, a.line_at)
    n = len([f for f in os.listdir(a.frames) if f.endswith(".png")])
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-framerate", str(a.fps),
           "-i", os.path.join(a.frames, "frame_%05d.png"), "-vf", vf,
           "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-2000:])
    print("wrote %s (%d frames, %.1f s, %.1f MB; title %d px)" % (a.out, n, n / float(a.fps), os.path.getsize(a.out) / 1e6, tsize))
