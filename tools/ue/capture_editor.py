"""Save a picture of the whole editor window (PIE included) through the MCP EditorAppToolset.
    python tools/ue/capture_editor.py OUT.png"""
import base64, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp_call
mcp_call.init()
res = mcp_call.rpc("tools/call", {"name": "call_tool", "arguments": {"toolset_name": "EditorToolset.EditorAppToolset",
                   "tool_name": "CaptureEditorImage", "arguments": {}}}, id_=3)
for c in res["result"]["content"]:
    d = json.loads(c.get("text", "{}")).get("returnValue", {})
    d = d.get("image", d)
    if "data" in d:
        open(sys.argv[1], "wb").write(base64.b64decode(d["data"]))
        print("saved", sys.argv[1])
