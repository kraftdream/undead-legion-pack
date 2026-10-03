"""Encode the Unreal showreel stages from the rendered shots (system Python, after showreel_unreal_all.py rendered them).

    python tools/ue/showreel_stage_ue.py [modular movement weapons]

For each stage of Showreel/unreal/plan.json: the recorder's title card (ShowreelRecorder.ShowCard: 1.6 s on black, the title
96 px bold and the line 30 px under it, centred), then every shot's PNG frames (Showreel/unreal/<stage>_<NN>/) with the
caption panel of showreel_encode_ue.py switched per caption segment of the plan, hard cuts between shots (a change of character
is a hard cut in Unity too) -> Showreel/unreal/showreel_<stage>.mp4, H.264 crf 16 like the Unity stages. The YouTube
assembly (tools/unity/showreel_youtube.py --src Showreel/unreal) cuts the 48-frame card and adds its own.
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imageio_ffmpeg
from showreel_encode_ue import BOLD, FONT, BOX_W, LEAD, esc, text_width, wrap

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UR = os.path.join(ROOT, "Showreel", "unreal")
WK = os.path.join(UR, "work")
FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30


def run(args):
    r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y"] + args, capture_output=True, text=True)
    if r.returncode:
        sys.exit("ffmpeg failed: " + r.stderr[-2000:])


def caption_filters(segments):
    vf = ["drawbox=x=60:y=60:w=600:h=170:color=0x0F1217@0.72:t=fill"]
    for s in segments:
        t0, t1 = s["f0"] / float(FPS), s["f1"] / float(FPS)
        en = ":enable='gte(t\\,%.4f)*lt(t\\,%.4f)'" % (t0 - 0.5 / FPS, t1 - 0.5 / FPS)
        tsize = 40
        while tsize > 20 and text_width(s["title"], tsize, True) > BOX_W:
            tsize -= 1
        vf.append("drawtext=fontfile='%s':text='%s':fontsize=%d:fontcolor=0xF5F2E6:x=90:y=113-th/2%s" % (BOLD, esc(s["title"]), tsize, en))
        rows = wrap(s["text"], 24)
        for k, row in enumerate(rows):
            yc = 181 + (k - (len(rows) - 1) / 2.0) * LEAD
            vf.append("drawtext=fontfile='%s':text='%s':fontsize=24:fontcolor=0xCCD1DB:x=90:y=%d-th/2%s" % (FONT, esc(row), yc, en))
    return ",".join(vf)


def card(stage, out):
    vf = ("drawtext=fontfile='%s':text='%s':fontsize=96:fontcolor=0xF5F2E6:x=(w-tw)/2:y=h/2-th-6,"
          "drawtext=fontfile='%s':text='%s':fontsize=30:fontcolor=0xF5F2E6:x=(w-tw)/2:y=h/2+18"
          % (BOLD, esc(stage["title"]), BOLD, esc(stage["text"])))
    run(["-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=%d" % FPS, "-frames:v", str(stage["card_frames"]), "-vf", vf,
         "-c:v", "libx264", "-crf", "10", "-preset", "slow", "-pix_fmt", "yuv420p", out])


def shot(stage, i, sh, out):
    d = os.path.join(UR, "%s_%02d" % (stage, i))
    n = len([f for f in os.listdir(d) if f.endswith(".png")]) if os.path.isdir(d) else 0
    if n < sh["frames"]:
        sys.exit("%s: %d of %d frames rendered" % (d, n, sh["frames"]))
    run(["-framerate", str(FPS), "-i", os.path.join(d, "frame_%05d.png"), "-frames:v", str(sh["frames"]),
         "-vf", caption_filters(sh["captions"]), "-c:v", "libx264", "-crf", "10", "-preset", "slow", "-pix_fmt", "yuv420p", out])


def stage_video(st):
    os.makedirs(WK, exist_ok=True)
    parts = [os.path.join(WK, "%s_card.mp4" % st["name"])]
    card(st, parts[0])
    for i, sh in enumerate(st["shots"]):
        p = os.path.join(WK, "%s_%02d.mp4" % (st["name"], i))
        shot(st["name"], i, sh, p)
        parts.append(p)
    lst = os.path.join(WK, "%s_list.txt" % st["name"])
    open(lst, "w").write("".join("file '%s'\n" % p.replace("\\", "/") for p in parts))
    out = os.path.join(UR, "showreel_%s.mp4" % st["name"])
    run(["-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p",
         "-r", str(FPS), "-movflags", "+faststart", out])
    frames = st["card_frames"] + sum(s["frames"] for s in st["shots"])
    print("wrote %s (%d frames, %.1f s, %.1f MB)" % (os.path.relpath(out, ROOT), frames, frames / float(FPS), os.path.getsize(out) / 1e6))


if __name__ == "__main__":
    plan = json.load(open(os.path.join(UR, "plan.json")))
    only = sys.argv[1:]
    for st in plan:
        if not only or st["name"] in only:
            stage_video(st)
