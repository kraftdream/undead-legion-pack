"""Minimal stdio MCP client for the Unity MCP server (mcpforunityserver).

    python tools/unity/mcp_call.py list
    python tools/unity/mcp_call.py call <tool> '<json args>'
    python tools/unity/mcp_call.py call <tool> @args.json

Spawns `uvx --from mcpforunityserver==10.2.0 mcp-for-unity --default-instance skeletons`
(see CLAUDE.md §6 for why --default-instance is required) and speaks JSON-RPC over
stdio. The Unity Editor must be open on the skeletons project (bridge on 127.0.0.1:6400).
"""
import json, subprocess, sys, os, threading, queue

SERVER = ["uvx", "--from", "mcpforunityserver==10.2.0", "mcp-for-unity",
          "--default-instance", "skeletons"]


class Client:
    def __init__(self):
        self.p = subprocess.Popen(SERVER, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1)
        self.q = queue.Queue()
        threading.Thread(target=self._reader, daemon=True).start()
        self._id = 0
        self.req("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                "clientInfo": {"name": "mcp_call", "version": "0"}})
        self.notify("notifications/initialized", {})

    def _reader(self):
        for line in self.p.stdout:
            line = line.strip()
            if line:
                try:
                    self.q.put(json.loads(line))
                except json.JSONDecodeError:
                    pass

    def _send(self, msg):
        self.p.stdin.write(json.dumps(msg) + "\n"); self.p.stdin.flush()

    def notify(self, method, params):
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def req(self, method, params, timeout=180):
        self._id += 1
        self._send({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        while True:
            msg = self.q.get(timeout=timeout)
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg["result"]

    def call(self, tool, args=None, timeout=180):
        r = self.req("tools/call", {"name": tool, "arguments": args or {}}, timeout)
        out = []
        for c in r.get("content", []):
            if c.get("type") == "text":
                t = c["text"]
                try:
                    out.append(json.loads(t))
                except json.JSONDecodeError:
                    out.append(t)
        return out[0] if len(out) == 1 else out

    def close(self):
        try:
            self.p.stdin.close(); self.p.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    c = Client()
    try:
        if sys.argv[1] == "list":
            for t in c.req("tools/list", {})["tools"]:
                print(t["name"], "-", (t.get("description") or "").split("\n")[0][:110])
        elif sys.argv[1] == "call":
            a = sys.argv[3] if len(sys.argv) > 3 else "{}"
            if a.startswith("@"):
                a = open(a[1:], encoding="utf-8").read()
            print(json.dumps(c.call(sys.argv[2], json.loads(a)), indent=1)[:20000])
    finally:
        c.close()
