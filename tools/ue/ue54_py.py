"""Run a script in the live UE 5.4 editor (skeletons_ue54) and print what it logged.

    python tools/ue/ue54_py.py SCRIPT [ARGS...]      (or -c CODE)

ue_py.py echoes a script's output only when it succeeds; this also shows a traceback, by printing the editor log's
new LogPython lines (and any other new Error lines) after the run.
"""
import os, sys, subprocess, time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG = os.path.join(REPO, "skeletons_ue54", "Saved", "Logs", "skeletons_ue54.log")


def run(args, timeout=600):
    start = os.path.getsize(LOG) if os.path.exists(LOG) else 0
    if args and args[0] != "-c":
        args = [os.path.abspath(args[0])] + args[1:]
    p = subprocess.run([sys.executable, os.path.join(REPO, "tools", "ue", "ue_py.py")] + args + ["--timeout", "30"],
                       capture_output=True, text=True, timeout=timeout)
    time.sleep(0.3)
    with open(LOG, "rb") as f:
        f.seek(start)
        new = f.read().decode("utf-8", "replace").splitlines()
    for line in new:
        if "LogPython" in line or ": Error:" in line:
            print(line.split("]", 2)[-1] if line.startswith("[") else line)
    if p.returncode and p.stderr.strip():
        print(p.stderr.strip()[-2000:])
    return p.returncode


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
