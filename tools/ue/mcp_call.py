"""Minimal MCP (streamable HTTP) client for the Unreal editor at 127.0.0.1:8000/mcp.
    python mcp_call.py list                       -> tool names
    python mcp_call.py <tool> '<json args>'       -> tools/call result text
"""
import sys, json, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

URL = "http://127.0.0.1:8000/mcp"
SESSION = {}

def rpc(method, params=None, id_=1):
    body = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        body["params"] = params
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    for k, v in SESSION.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=600) as r:
        sid = r.headers.get("Mcp-Session-Id")
        if sid:
            SESSION["Mcp-Session-Id"] = sid
        raw = r.read().decode("utf-8", "replace")
        ctype = r.headers.get("Content-Type", "")
    if "text/event-stream" in ctype:
        msgs = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
        raw = msgs[-1] if msgs else "{}"
    return json.loads(raw)

def init():
    rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "cc", "version": "0"}})
    try:
        req = urllib.request.Request(URL, data=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode(), method="POST")
        req.add_header("Content-Type", "application/json"); req.add_header("Accept", "application/json, text/event-stream")
        for k, v in SESSION.items(): req.add_header(k, v)
        urllib.request.urlopen(req, timeout=30).read()
    except Exception:
        pass

def call(tool, args):
    res = rpc("tools/call", {"name": tool, "arguments": args}, id_=2)
    if "error" in res:
        return "ERROR: " + json.dumps(res["error"])
    out = []
    for c in res.get("result", {}).get("content", []):
        out.append(c.get("text", json.dumps(c)))
    if res.get("result", {}).get("isError"):
        out.insert(0, "[isError]")
    return "\n".join(out)

if __name__ == "__main__":
    init()
    if sys.argv[1] == "list":
        res = rpc("tools/list", {}, id_=2)
        for t in res["result"]["tools"]:
            print(t["name"], "-", (t.get("description") or "")[:200].replace("\n", " "))
            print("   schema:", json.dumps(t.get("inputSchema", {}))[:600])
    else:
        args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        print(call(sys.argv[1], args))
