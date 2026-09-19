"""Play-mode smoke test of the demo scene: enter play, drive the browser, screenshot, stop.

    python tools/unity/demo_smoke.py [out_dir]

Requires the demo scene to be the open scene in the editor. Writes
<out_dir>/demo_<Character>.png per selected character (default: two characters).

The editor does NOT tick play mode on its own while it is driven from here: after
`play` the game sits at frame 1 until something advances it. `EditorApplication.Step()`
a few times and clearing `isPaused` starts the loop; measured 280 frames in the next
three seconds. Screenshots taken before the UI shaders have compiled show solid cyan
panels (the async shader compilation placeholder), so wait a few seconds first.
"""
import sys, json, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_call import Client

INSPECT = r'''
var sb = new System.Text.StringBuilder();
var sc = UnityEngine.Object.FindFirstObjectByType<UndeadLegion.Demo.SkeletonShowcase>();
if (sc == null) return "NO SHOWCASE (is the demo scene open?)";
%EXTRA%
var an = UnityEngine.Object.FindFirstObjectByType<Animator>();
var st = an != null ? an.GetCurrentAnimatorStateInfo(0) : new AnimatorStateInfo();
var tw = an != null ? an.GetComponent<UndeadLegion.Demo.SkeletonTwitch>() : null;
int visible = 0, total = 0; if (an != null) foreach (var r in an.GetComponentsInChildren<SkinnedMeshRenderer>(true)) { total++; if (r.enabled) visible++; }
sb.Append("frame=" + Time.frameCount + " t=" + Time.time.ToString("F1") + " | " + sc.characterNameLabel.text + " | chars=" + sc.characterListContent.childCount
  + " clipRows=" + sc.clipListContent.childCount + " modules=" + sc.moduleListContent.childCount + " | " + sc.clipInfoLabel.text
  + " | state=" + (an != null ? (st.IsName("Idle") ? "Idle" : "other") : "none") + " nt=" + st.normalizedTime.ToString("F2")
  + " rootMotion=" + (an != null && an.applyRootMotion) + " twitch=" + (tw != null && tw.enabled) + " renderers " + visible + "/" + total
  + " pos=" + (an != null ? an.transform.position.ToString("F2") : "-") + " cam=" + Camera.main.transform.position.ToString("F1"));
return sb.ToString();
'''


def run(out_dir, picks=(0, 3)):
    out_dir = os.path.abspath(out_dir).replace("\\", "/")
    os.makedirs(out_dir, exist_ok=True)
    c = Client()

    def code(src, t=300):
        r = c.call("execute_code", {"action": "execute", "code": src}, timeout=t)
        d = r.get("data", r) if isinstance(r, dict) else r
        return (d.get("result") if isinstance(d, dict) else None) or json.dumps(r)[:600]

    try:
        print("play:", c.call("manage_editor", {"action": "play"}, timeout=120).get("message"))
        time.sleep(2)
        print("kick:", code('for (int i = 0; i < 10; i++) EditorApplication.Step(); EditorApplication.isPaused = false; Application.runInBackground = true; EditorApplication.QueuePlayerLoopUpdate(); return "frame=" + Time.frameCount;'))
        time.sleep(6)   # shaders compile, idle plays
        for i in picks:
            name = code(INSPECT.replace("%EXTRA%", "sc.SelectCharacter(%d);" % i))
            time.sleep(2.5)
            print(code(INSPECT.replace("%EXTRA%", "")))
            shot = "%s/demo_%d.png" % (out_dir, i)
            code('ScreenCapture.CaptureScreenshot("%s"); return "ok";' % shot)
            time.sleep(2)
        print("twitch:", code(INSPECT.replace("%EXTRA%", "sc.FireTwitch(2); sc.ToggleModule(0);")))
        time.sleep(2)
        code('ScreenCapture.CaptureScreenshot("%s/demo_twitch.png"); return "ok";' % out_dir)
        time.sleep(2)
        r = c.call("read_console", {"action": "get", "types": ["error", "warning"], "count": 20, "format": "plain"}, timeout=120)
        print("console:", r.get("message"), json.dumps(r.get("data"))[:1500])
        print("stop:", c.call("manage_editor", {"action": "stop"}, timeout=120).get("message"))
    finally:
        c.close()


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "demo_shots")
