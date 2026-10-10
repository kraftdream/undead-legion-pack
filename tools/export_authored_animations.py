"""Export approved Unity clips directly from the main animation file.

    blender -b -P tools/export_authored_animations.py -- --clip Shoot_01,Shoot_02 [--out DIR]

Uses each clip's unity_export_fps and lift from clips.json. Higher sampling rates
preserve contacts without changing playback duration or saving the source .blend.
Unreal continues to use export_epic.py; this is the Unity sampling wrapper.
"""
import argparse
import json
from pathlib import Path
import runpy
import sys

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Animations/skeleton_anim.blend"


def resample_timeline(action, fps):
    """Stretch key times in memory; the matching scene FPS keeps real time fixed."""
    scene = bpy.context.scene
    source_fps = scene.render.fps / scene.render.fps_base
    factor = fps / source_fps
    if factor < 1 or abs(factor - round(factor)) > 1e-6:
        raise ValueError(f"Export FPS {fps} must be an integer multiple of {source_fps}")
    start, end = action.frame_range
    if factor != 1:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        snapshot = [(tuple(k.co), tuple(k.handle_left), tuple(k.handle_right))
                                    for k in curve.keyframe_points]
                        for key, (co, left, right) in zip(curve.keyframe_points, snapshot):
                            key.co = (start + (co[0] - start) * factor, co[1])
                            key.handle_left = (start + (left[0] - start) * factor, left[1])
                            key.handle_right = (start + (right[0] - start) * factor, right[1])
                        curve.update()
        action.frame_start = start
        action.frame_end = start + (end - start) * factor
    scene.render.fps = fps
    scene.render.fps_base = 1.0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clip", required=True, help="Comma-separated action names")
    parser.add_argument("--out", type=Path, help="Output directory; defaults to Unity animations")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    manifest = json.loads((ROOT / "Animations/clips.json").read_text(encoding="utf-8"))
    entries = {entry["name"]: entry for entry in manifest["clips"]}
    names = list(dict.fromkeys(name.strip() for name in args.clip.split(",") if name.strip()))
    if not names:
        parser.error("--clip requires at least one action")
    for name in names:
        if name not in entries:
            parser.error(f"Unknown manifest clip: {name}")
        if entries[name].get("disabled"):
            parser.error(f"Clip is authoring-only and disabled for export: {name}")
        if "unity_export_fps" not in entries[name]:
            parser.error(f"{name} has no authored sampling configuration; use its existing exporter")
    out = str(args.out.resolve()) if args.out else None
    for name in names:
        # The core exporter replaces scene data; reopen for every action.
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
        action = bpy.data.actions.get(name)
        if action is None:
            raise RuntimeError(f"Main animation file is missing {name}")
        entry = entries[name]
        fps = int(entry["unity_export_fps"])
        resample_timeline(action, fps)
        exporter = runpy.run_path(str(ROOT / "tools/export_fbx.py"), run_name="export_helper")
        export_clip = exporter["export_clip"]
        export_clip.__globals__["FPS"] = fps
        export_clip(name, out, True, lift=entry.get("lift", exporter["CLIP_LIFT"]))
        print(f"EXPORTED {name} at {fps} fps; source file unchanged", flush=True)


if __name__ == "__main__":
    main()
