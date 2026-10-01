"""Thin Python client for the Unreal MCP toolsets (import from other tools/ue scripts, system Python).

    from mcp import bp, obj, tool
    bp("list_graphs", blueprint=ref("/Game/X/BP_Y"))
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp_call

_init = False
BPT = "editor_toolset.toolsets.blueprint.BlueprintTools"
OBJ = "editor_toolset.toolsets.object.ObjectTools"
UMG = "UMGToolSet.UMGToolSet"


def tool(toolset, _tool, **args):
    global _init
    if not _init:
        mcp_call.init(); _init = True
    txt = mcp_call.call("call_tool", {"toolset_name": toolset, "tool_name": _tool, "arguments": args})
    if txt.startswith("[isError]") or txt.startswith("ERROR"):
        raise RuntimeError("%s.%s failed: %s" % (toolset.split(".")[-1], _tool, txt[:1500]))
    try:
        return json.loads(txt).get("returnValue")
    except Exception:
        return txt


def bp(_tool, **args):
    return tool(BPT, _tool, **args)


def obj(_tool, **args):
    return tool(OBJ, _tool, **args)


def umg(_tool, **args):
    return tool(UMG, _tool, **args)


def ref(path):
    """'/Game/A/B' -> {'refPath': '/Game/A/B.B'}; a path with '.' or ':' is taken as is."""
    if "." not in path.split("/")[-1]:
        path = path + "." + path.split("/")[-1]
    return {"refPath": path}
