"""Encode the showreel's PNG frames (ShowreelRecorder, <repo>/Showreel/frames) into an MP4.

    python tools/unity/showreel_encode.py [--frames Showreel/frames] [--out Showreel/showreel.mp4] [--fps 30] [--crf 18]

Uses the ffmpeg binary bundled with the `imageio-ffmpeg` package (pip install --user imageio-ffmpeg), so no
system ffmpeg is needed. H.264, yuv420p, faststart: what the Asset Store's video upload takes.
"""
import argparse, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap = argparse.ArgumentParser()
ap.add_argument("--frames", default=os.path.join(ROOT, "Showreel", "frames"))
ap.add_argument("--out", default=os.path.join(ROOT, "Showreel", "showreel.mp4"))
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--crf", type=int, default=18)
ap.add_argument("--scale", default="", help="ffmpeg scale, e.g. 1920:-2 (lanczos): a supersampled downscale of larger frames")
a = ap.parse_args()

try:
    import imageio_ffmpeg
except ImportError:
    sys.exit("pip install --user imageio-ffmpeg first (it bundles the ffmpeg binary)")
exe = imageio_ffmpeg.get_ffmpeg_exe()
n = len([f for f in os.listdir(a.frames) if f.startswith("frame_") and f.endswith(".png")])
if n == 0:
    sys.exit("no frames in " + a.frames)
cmd = [exe, "-y", "-framerate", str(a.fps), "-i", os.path.join(a.frames, "frame_%05d.png"),
       ] + (["-vf", "scale=%s:flags=lanczos" % a.scale] if a.scale else []) + [
       "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
print("encoding %d frames at %d fps -> %s" % (n, a.fps, a.out))
r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
if r.returncode != 0:
    sys.exit(r.stdout[-2000:])
print("wrote %s (%.1f MB, %.1f s)" % (a.out, os.path.getsize(a.out) / 1e6, n / float(a.fps)))
