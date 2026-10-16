"""Drive the UE 5.4 Blueprint editor to paste a Blueprint's generated graphs (tools/ue/ue54_compile.py output).

    python tools/ue/ue54_paste.py PLAN_DIR BP_NAME [--what var,fn,events] [--only NAME,...]
        [--mybp X,Y] [--graph-tab X,Y] [--canvas X,Y]

The editor must show the Blueprint (open it first: ue54_py.py ... open_editor_for_assets) maximised on the primary screen.
  var     one paste per variable into the My Blueprint panel (click at --mybp, Ctrl+V)
  fn      one paste per function into My Blueprint; the editor opens the new graph and asks for a name: Enter keeps it
  events  the event graph's nodes: click the Event Graph tab (--graph-tab), click the canvas (--canvas), Ctrl+V
"""
import argparse, json, os, subprocess, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GUI = ["powershell", "-STA", "-NoProfile", "-File", os.path.join(REPO, "tools", "ue", "gui.ps1")]


def gui(*a):
    return subprocess.run(GUI + [str(x) for x in a], capture_output=True, text=True).stdout.strip()


def xy(s):
    x, y = s.split(","); return int(x), int(y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_dir"); ap.add_argument("bp")
    ap.add_argument("--what", default="var,fn,events")
    ap.add_argument("--only", default="")
    ap.add_argument("--mybp", default="240,975")
    ap.add_argument("--graph-tab", default="547,113")
    ap.add_argument("--canvas", default="1000,800")
    ap.add_argument("--focus", default="skeletons_ue54")
    ap.add_argument("--click-once", action="store_true",
                    help="click My Blueprint only before the first paste: after a function paste + Enter the tree keeps the focus")
    a = ap.parse_args()
    plan = json.load(open(os.path.join(a.plan_dir, "plan.json")))
    what = a.what.split(",")
    only = set(a.only.split(",")) if a.only else None
    items = [p for p in plan if p[0].split("/")[-1] == a.bp and p[1] in what and (not only or p[2] in only)]
    gui("focus", a.focus)
    time.sleep(0.5)
    mx, my = xy(a.mybp)
    clicked = False
    for bp, kind, name, f in sorted(items, key=lambda p: ["var", "fn", "events"].index(p[1])):
        gui("clip", f)
        if kind in ("var", "fn"):
            if not (a.click_once and clicked):
                gui("click", mx, my); time.sleep(0.4)
                clicked = True
            gui("paste"); time.sleep(1.2 if kind == "fn" else 0.6)
            if kind == "fn":
                gui("keys", "{ENTER}"); time.sleep(0.6)
        else:
            gx, gy = xy(a.graph_tab); cx, cy = xy(a.canvas)
            gui("click", gx, gy); time.sleep(0.8)
            gui("click", cx, cy); time.sleep(0.4)
            gui("paste"); time.sleep(2.0)
        print("pasted", kind, name, flush=True)


if __name__ == "__main__":
    main()
