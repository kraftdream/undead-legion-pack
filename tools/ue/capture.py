"""Capture the level viewport (or PIE) through the MCP EditorAppToolset and save it as a PNG.

    python tools/ue/capture.py OUT.png [x y z pitch yaw]     (camera optional; roll 0)
"""
import base64, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp_call
from mcp import tool

APP = "EditorToolset.EditorAppToolset"


def capture(out, cam=None):
    args = {"annotations": {"gridSpacing": 0, "gridExtent": 0, "gridHeight": 0, "maxLabelDistance": 0, "classFilter": None, "maxLabels": 0}, "bShowUI": False}
    if cam:
        x, y, z, pitch, yaw = cam
        args["captureTransform"] = {"location": {"x": x, "y": y, "z": z},
                                    "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0.0}, "scale": {"x": 1, "y": 1, "z": 1}}
    mcp_call.init()
    res = mcp_call.rpc("tools/call", {"name": "call_tool", "arguments": {"toolset_name": APP, "tool_name": "CaptureViewport", "arguments": args}}, id_=3)
    for c in res.get("result", {}).get("content", []):
        data = c.get("data") if c.get("type") == "image" else None
        if data is None and c.get("type") == "text":
            try:
                data = json.loads(c["text"])["returnValue"]["image"]["data"]
            except Exception:
                data = None
        if data:
            open(out, "wb").write(base64.b64decode(data))
            print("saved", out)
            return out
    print(json.dumps(res)[:1500])


if __name__ == "__main__":
    cam = [float(v) for v in sys.argv[2:7]] if len(sys.argv) >= 7 else None
    capture(sys.argv[1], cam)
