"""Encode an Unreal showreel render (PNG frames from ue_showreel.py) to MP4 with the Unity recorder's caption panel.

    python tools/ue/showreel_encode_ue.py [--frames Showreel/unreal/modular_test] [--out Showreel/unreal/showreel_modular_test.mp4]
                                          [--title "Skeleton Warrior"] [--text "Six class presets on one shared humanoid rig"]

The panel is ShowreelRecorder.BuildCanvas at 1920 x 1080: a box at (60, 60), 600 x 170, colour (0.06, 0.07, 0.09, 0.72);
the title 40 px bold (0.96, 0.95, 0.90) centred on y 113, the line 24 px (0.80, 0.82, 0.86) centred on y 181, both at x 90,
in Arial (Unity's built-in UI font is an Arial). ffmpeg from the imageio-ffmpeg package (pip install --user imageio-ffmpeg);
H.264 crf 16, yuv420p, faststart, as the Unity stages.
"""
import argparse, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap = argparse.ArgumentParser()
ap.add_argument("--frames", default=os.path.join(ROOT, "Showreel", "unreal", "modular_test"))
ap.add_argument("--out", default=os.path.join(ROOT, "Showreel", "unreal", "showreel_modular_test.mp4"))
ap.add_argument("--title", default="Skeleton Warrior")
ap.add_argument("--text", default="Six class presets on one shared humanoid rig")
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--crf", type=int, default=16)
a = ap.parse_args()

import imageio_ffmpeg
exe = imageio_ffmpeg.get_ffmpeg_exe()


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


font = "C\\:/Windows/Fonts/arial.ttf"
bold = "C\\:/Windows/Fonts/arialbd.ttf"
vf = ",".join([
    "drawbox=x=60:y=60:w=600:h=170:color=0x0F1217@0.72:t=fill",
    "drawtext=fontfile='%s':text='%s':fontsize=40:fontcolor=0xF5F2E6:x=90:y=113-th/2" % (bold, esc(a.title)),
    "drawtext=fontfile='%s':text='%s':fontsize=24:fontcolor=0xCCD1DB:x=90:y=181-th/2" % (font, esc(a.text)),
])
n = len([f for f in os.listdir(a.frames) if f.endswith(".png")])
cmd = [exe, "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", os.path.join(a.frames, "frame_%05d.png"), "-vf", vf,
       "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode:
    sys.exit(r.stderr[-2000:])
print("wrote %s (%d frames, %.1f s, %.1f MB)" % (a.out, n, n / float(a.fps), os.path.getsize(a.out) / 1e6))
