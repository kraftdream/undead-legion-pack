"""Build Assets/UndeadLegion/Animations/AC_Skeleton.controller and prove the additive twitch layer.

    python tools/unity/build_twitch_controller.py

Layer 0 "Base": Idle (looping). Layer 1 "Twitch": Additive, weight 1, states Rest (empty)
and Twitch_01..03; Rest -> Twitch_NN on trigger `Twitch` with `TwitchIndex` == NN-1,
back to Rest on exit time. Demo/Scripts/SkeletonTwitch.cs drives it at random.

Then measures on the Knight, in edit mode: Head and Jaw local rotation per frame with
the twitch layer at weight 0 versus weight 1 with Twitch_03 fired at frame 0. The
difference is the additive contribution; Hips must stay at 0.
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_call import Client

CODE = r'''
var sb = new System.Text.StringBuilder();
string dir = "Assets/UndeadLegion/Animations/";
System.Func<string, AnimationClip> load = (name) => {
  foreach (var a in AssetDatabase.LoadAllAssetsAtPath(dir + "Skeleton@" + name + ".fbx"))
    if (a is AnimationClip && !a.name.StartsWith("__preview")) return (AnimationClip)a;
  return null;
};
var idle = load("Idle"); if (idle == null) return "no Idle clip";
string path = dir + "AC_Skeleton.controller";
var ctrl = UnityEditor.Animations.AnimatorController.CreateAnimatorControllerAtPath(path);
ctrl.AddParameter("Twitch", AnimatorControllerParameterType.Trigger);
ctrl.AddParameter("TwitchIndex", AnimatorControllerParameterType.Int);
var layers = ctrl.layers; layers[0].name = "Base"; ctrl.layers = layers;
var baseSm = ctrl.layers[0].stateMachine;
var idleState = baseSm.AddState("Idle"); idleState.motion = idle; baseSm.defaultState = idleState;
ctrl.AddLayer("Twitch");
layers = ctrl.layers;
layers[1].blendingMode = UnityEditor.Animations.AnimatorLayerBlendingMode.Additive;
layers[1].defaultWeight = 1f;
ctrl.layers = layers;
var sm = ctrl.layers[1].stateMachine;
var rest = sm.AddState("Rest"); sm.defaultState = rest;
int n = 0;
for (int i = 0; i < 3; i++) {
  var clip = load("Twitch_0" + (i + 1)); if (clip == null) { sb.AppendLine("missing Twitch_0" + (i + 1)); continue; }
  var st = sm.AddState("Twitch_0" + (i + 1)); st.motion = clip;
  var t = rest.AddTransition(st); t.hasExitTime = false; t.duration = 0.05f;
  t.AddCondition(UnityEditor.Animations.AnimatorConditionMode.If, 0, "Twitch");
  t.AddCondition(UnityEditor.Animations.AnimatorConditionMode.Equals, i, "TwitchIndex");
  var back = st.AddTransition(rest); back.hasExitTime = true; back.exitTime = 1f; back.duration = 0.1f;
  n++;
}
EditorUtility.SetDirty(ctrl); AssetDatabase.SaveAssets();
sb.AppendLine("controller " + path + ": layers=" + ctrl.layers.Length + " twitch states=" + n + " layer1 mode=" + ctrl.layers[1].blendingMode);

// measure
string model = "Assets/UndeadLegion/Models/SkeletonKnight/SK_SkeletonKnight.fbx";
var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(model);
Avatar av = null; foreach (var a in AssetDatabase.LoadAllAssetsAtPath(model)) if (a is Avatar) av = (Avatar)a;
var go = (GameObject)GameObject.Instantiate(prefab); go.name = "__twitch_test";
var an = go.GetComponent<Animator>(); if (an == null) an = go.AddComponent<Animator>();
an.avatar = av; an.runtimeAnimatorController = ctrl; an.applyRootMotion = false; an.cullingMode = AnimatorCullingMode.AlwaysAnimate;
Transform head = null, jaw = null, hips = null;
foreach (var t in go.GetComponentsInChildren<Transform>(true)) { if (t.name == "Head") head = t; if (t.name == "Jaw") jaw = t; if (t.name == "Hips") hips = t; }
int frames = 140;
var headA = new Quaternion[frames]; var jawA = new Quaternion[frames]; var hipsA = new Quaternion[frames];
var headB = new Quaternion[frames]; var jawB = new Quaternion[frames]; var hipsB = new Quaternion[frames];
for (int run = 0; run < 2; run++) {
  an.Rebind(); an.Update(0f);
  an.SetLayerWeight(1, run == 0 ? 0f : 1f);
  if (run == 1) { an.SetInteger("TwitchIndex", 2); an.SetTrigger("Twitch"); }
  for (int f = 0; f < frames; f++) {
    an.Update(1f / 30f);
    if (run == 0) { headA[f] = head.localRotation; jawA[f] = jaw.localRotation; hipsA[f] = hips.localRotation; }
    else { headB[f] = head.localRotation; jawB[f] = jaw.localRotation; hipsB[f] = hips.localRotation; }
  }
}
float mh = 0, mj = 0, mp = 0; int fh = 0, fj = 0; int active = 0;
for (int f = 0; f < frames; f++) {
  float dh = Quaternion.Angle(headA[f], headB[f]), dj = Quaternion.Angle(jawA[f], jawB[f]), dp = Quaternion.Angle(hipsA[f], hipsB[f]);
  if (dh > mh) { mh = dh; fh = f; } if (dj > mj) { mj = dj; fj = f; } if (dp > mp) mp = dp;
  if (dh > 0.2f || dj > 0.2f) active++;
}
sb.AppendLine(string.Format("Twitch_03 over Idle on the Knight: Head additive peak {0:F1} deg at frame {1}, Jaw peak {2:F1} deg at frame {3}, Hips diff {4:F2} deg, frames with visible twitch {5}/{6}", mh, fh, mj, fj, mp, active, frames));
sb.AppendLine("base Idle alone: Head moved " + Quaternion.Angle(headA[0], headA[frames-1]).ToString("F1") + " deg between first and last frame (idle motion, not twitch)");
GameObject.DestroyImmediate(go);
return sb.ToString();
'''

if __name__ == "__main__":
    ctrl_path = os.path.join(os.path.dirname(__file__), "..", "..", "skeletons", "Assets", "UndeadLegion", "Animations", "AC_Skeleton.controller")
    for p in (ctrl_path, ctrl_path + ".meta"):   # rebuild from scratch; deleting is blocked inside execute_code
        if os.path.exists(p):
            os.remove(p)
    c = Client()
    try:
        c.call("refresh_unity", {"mode": "force", "scope": "all", "compile": "request", "wait_for_ready": True}, timeout=600)
        r = c.call("execute_code", {"action": "execute", "code": CODE}, timeout=900)
        res = r.get("data", r) if isinstance(r, dict) else r
        if isinstance(res, dict):
            print(res.get("result") or json.dumps(res, indent=1)[:4000])
            if res.get("logs"): print("logs:", res["logs"])
        else:
            print(res)
        if isinstance(r, dict) and not r.get("success", True):
            print(json.dumps(r, indent=1)[:4000])
    finally:
        c.close()
