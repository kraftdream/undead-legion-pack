"""Play-mode check of layered playback in the demo: legs walk while the upper body attacks.

    python tools/unity/layer_smoke.py [out_dir]

Selects the Knight with a sword, plays Walk_Fwd, then clicks Attack_1H_01 (an on-the-move
clip: must land on the UpperBody layer while Base stays on Walk_Fwd), then Attack_2H_01
(a full-stop clip: must take the Base layer, and Walk_Fwd must resume after it). Prints
the state of every layer at each step and writes <out_dir>/layer_<step>.png. Same
play-mode driving rules as demo_smoke.py (kick the loop, wait for shaders, stop at the end).
"""
import sys, json, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_call import Client

PROBE = r'''
var sb = new System.Text.StringBuilder();
var sc = UnityEngine.Object.FindFirstObjectByType<UndeadLegion.Demo.SkeletonShowcase>();
if (sc == null) return "NO SHOWCASE (is the demo scene open?)";
%EXTRA%
var an = UnityEngine.Object.FindFirstObjectByType<Animator>();
if (an == null) return "no animator";
sb.Append("t=" + Time.time.ToString("F1"));
for (int l = 0; l < an.layerCount; l++) {
  var st = an.GetCurrentAnimatorStateInfo(l);
  string name = "?";
  foreach (var c in an.runtimeAnimatorController.animationClips) if (st.IsName(c.name)) { name = c.name; break; }
  if (name == "?" && st.IsName("Empty")) name = "Empty";
  if (name == "?" && st.IsName("Rest")) name = "Rest";
  sb.Append(" | " + an.GetLayerName(l) + "=" + name + " nt=" + st.normalizedTime.ToString("F2") + " w=" + an.GetLayerWeight(l).ToString("F1"));
}
sb.Append(" | label: " + sc.clipInfoLabel.text);
return sb.ToString();
'''

PLAY = 'var cl = System.Array.Find(an0.runtimeAnimatorController.animationClips, x => x.name == "%s"); sc.Play(cl);'


def run(out_dir):
    out_dir = os.path.abspath(out_dir).replace("\\", "/")
    os.makedirs(out_dir, exist_ok=True)
    c = Client()

    def code(src, t=300):
        r = c.call("execute_code", {"action": "execute", "code": src}, timeout=t)
        d = r.get("data", r) if isinstance(r, dict) else r
        return (d.get("result") if isinstance(d, dict) else None) or json.dumps(r)[:600]

    def probe(extra=""):
        return code(PROBE.replace("%EXTRA%", "var an0 = UnityEngine.Object.FindFirstObjectByType<Animator>(); " + extra))

    def shot(name):
        code('ScreenCapture.CaptureScreenshot("%s/layer_%s.png"); return "ok";' % (out_dir, name))
        time.sleep(1.5)

    try:
        print("play:", c.call("manage_editor", {"action": "play"}, timeout=120).get("message"))
        time.sleep(2)
        code('for (int i = 0; i < 10; i++) EditorApplication.Step(); EditorApplication.isPaused = false; Application.runInBackground = true; EditorApplication.QueuePlayerLoopUpdate(); return "kicked";')
        time.sleep(6)
        print("knight+sword:", probe('sc.SelectCharacter(0); var w = UnityEngine.Object.FindFirstObjectByType<UndeadLegion.Demo.SkeletonWeapon>(); if (w != null) w.Equip(1);'))
        time.sleep(1.5)
        print("walk:       ", probe(PLAY % "Walk_Fwd"))
        time.sleep(2.0)
        print("walking:    ", probe())
        print("1H on move: ", probe(PLAY % "Attack_1H_01"))
        time.sleep(1.2)
        print("mid attack: ", probe())
        shot("walk_attack")
        time.sleep(3.5)
        print("after:      ", probe())
        print("2H fullstop:", probe(PLAY % "Attack_2H_01"))
        time.sleep(1.5)
        print("mid 2H:     ", probe())
        shot("fullstop")
        time.sleep(4.0)
        print("resumed:    ", probe())
        r = c.call("read_console", {"action": "get", "types": ["error", "warning"], "count": 20, "format": "plain"}, timeout=120)
        print("console:", r.get("message"), json.dumps(r.get("data"))[:800])
    finally:
        try:
            print("stop:", c.call("manage_editor", {"action": "stop"}, timeout=120).get("message"))
        finally:
            c.close()


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "layer_shots")
