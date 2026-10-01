"""Run Python inside the LIVE Unreal editor over the Python plugin's remote execution.

The Unreal-side analogue of the Blender MCP bridge: the editor must have
Project Settings > Plugins > Python > "Enable Remote Execution" on (the
settings object re-arms the listener on change, no restart needed).

    python tools/ue/ue_py.py script.py            # run a file in the editor
    python tools/ue/ue_py.py -c "import unreal; print(unreal.SystemLibrary.get_engine_version())"

Output printed by the script is echoed here. Exit code 1 on a remote exception.
Pure stdlib; imports Epic's remote_execution.py from the installed engine.
"""
import os, sys, glob, argparse, time

ENGINE_ROOTS = [r"C:\Program Files\Epic Games\UE_5.8"]
REL = r"Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python"


def _import_remote_execution():
    for root in ENGINE_ROOTS + glob.glob(r"C:\Program Files\Epic Games\UE_*"):
        p = os.path.join(root, REL)
        if os.path.isfile(os.path.join(p, "remote_execution.py")):
            sys.path.insert(0, p)
            import remote_execution  # noqa
            return remote_execution
    raise SystemExit("remote_execution.py not found under any UE_* install")


def run(code, exec_mode=None, timeout=10.0):
    re_ = _import_remote_execution()
    exec_mode = exec_mode or re_.MODE_EXEC_FILE
    rx = re_.RemoteExecution()
    rx.start()
    try:
        t0 = time.time()
        while not rx.remote_nodes and time.time() - t0 < timeout:
            time.sleep(0.1)
        if not rx.remote_nodes:
            raise SystemExit("no Unreal editor answered the multicast within %.0fs "
                             "(is Remote Execution enabled in Project Settings > Python?)" % timeout)
        node = rx.remote_nodes[0]
        rx.open_command_connection(node["node_id"])
        res = rx.run_command(code, unattended=True, exec_mode=exec_mode)
    finally:
        rx.stop()
    for line in res.get("output", []):
        typ = line.get("type", "")
        txt = line.get("output", "")
        stream = sys.stderr if typ in ("Error", "Warning") else sys.stdout
        stream.write(("[%s] " % typ if typ not in ("Info", "") else "") + txt + "\n")
    return res.get("success", False), res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("script", nargs="?", help="python file to run inside the editor")
    ap.add_argument("args", nargs="*", help="arguments passed to the script (sys.argv[1:] inside the editor)")
    ap.add_argument("-c", "--code", help="inline code to run")
    ap.add_argument("--timeout", type=float, default=10.0)
    a = ap.parse_args()
    if a.code:
        code = a.code
    elif a.script:
        code = os.path.abspath(a.script)   # ExecuteFile accepts a path, plus arguments
        if a.args:
            code += " " + " ".join(a.args)
    else:
        ap.error("give a script path or -c CODE")
    ok, _ = run(code, timeout=a.timeout)
    sys.exit(0 if ok else 1)
