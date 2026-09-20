"""Measure how far below the floor a clip puts the mesh, per model, without any prefab lift.

    python tools/unity/ground_clip.py Idle Idle_02 Idle_03

Instantiates the raw SK_*.fbx (no Armature lift), plays the clip through a throwaway
controller (no Foot IK), bakes every SkinnedMeshRenderer every 6 frames and reports the
lowest vertex. The worst model's number, negated, is the `--lift` to re-export the clip
with (CLAUDE.md 8). Prints one line per clip with the suggested lift.
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_call import Client

MODELS = ["SkeletonKnight", "SkeletonArcher", "SkeletonAssassin", "SkeletonMage", "SkeletonNecromancer", "SkeletonWarrior"]
CODE = r'''
var sb = new System.Text.StringBuilder();
foreach (var clipName in new string[]{ %CLIPS% }) {
  // FORCE the reimport: a lazy refresh from the bridge left the previous import in place
  // and three successive export changes measured identically to 4 decimals
  AssetDatabase.ImportAsset("Assets/UndeadLegion/Animations/Skeleton@" + clipName + ".fbx", ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
  AnimationClip clip = null;
  foreach (var a in AssetDatabase.LoadAllAssetsAtPath("Assets/UndeadLegion/Animations/Skeleton@" + clipName + ".fbx")) if (a is AnimationClip && !a.name.StartsWith("__preview")) clip = (AnimationClip)a;
  if (clip == null) { sb.AppendLine(clipName + ": no clip"); continue; }
  float worst = 9f; string worstModel = ""; var per = new System.Text.StringBuilder();
  foreach (var ch in new string[]{ %MODELS% }) {
    string model = "Assets/UndeadLegion/Models/" + ch + "/SK_" + ch + ".fbx";
    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(model);
    Avatar av = null; foreach (var a in AssetDatabase.LoadAllAssetsAtPath(model)) if (a is Avatar) av = (Avatar)a;
    var ctrl = new UnityEditor.Animations.AnimatorController(); ctrl.AddLayer("Base");
    var st = ctrl.layers[0].stateMachine.AddState("X"); st.motion = clip;
    var go = (GameObject)GameObject.Instantiate(prefab);
    var an = go.GetComponent<Animator>(); if (an == null) an = go.AddComponent<Animator>();
    an.avatar = av; an.runtimeAnimatorController = ctrl; an.applyRootMotion = false; an.cullingMode = AnimatorCullingMode.AlwaysAnimate;
    an.Rebind(); an.Update(0f);
    int frames = Mathf.RoundToInt(clip.length * clip.frameRate); float minAll = 9f; var bake = new Mesh();
    for (int f = 0; f < frames; f += 6) {
      an.Update(6f / clip.frameRate); float m = 9f;
      foreach (var r in go.GetComponentsInChildren<SkinnedMeshRenderer>()) { r.BakeMesh(bake); var vs = bake.vertices; for (int i = 0; i < vs.Length; i++) m = Mathf.Min(m, r.transform.TransformPoint(vs[i]).y); }
      minAll = Mathf.Min(minAll, m);
    }
    UnityEngine.Object.DestroyImmediate(bake); GameObject.DestroyImmediate(go);
    per.Append(ch.Replace("Skeleton", "") + " " + minAll.ToString("+0.0000;-0.0000") + "  ");
    if (minAll < worst) { worst = minAll; worstModel = ch; }
  }
  sb.AppendLine(string.Format("{0}: lowest vertex {1:+0.0000;-0.0000} m ({2}) -> suggested --lift {3:0.0000}   [{4}]", clipName, worst, worstModel, Mathf.Max(0f, -worst), per.ToString().Trim()));
}
return sb.ToString();
'''

if __name__ == "__main__":
    clips = sys.argv[1:] or ["Idle"]
    code = CODE.replace("%CLIPS%", ", ".join('"%s"' % c for c in clips)).replace("%MODELS%", ", ".join('"%s"' % m for m in MODELS))
    c = Client()
    try:
        c.call("refresh_unity", {"mode": "if_dirty", "scope": "assets", "wait_for_ready": True}, timeout=300)
        r = c.call("execute_code", {"action": "execute", "code": code}, timeout=1800)
        d = r.get("data", r)
        print(d.get("result") if isinstance(d, dict) else d)
    finally:
        c.close()
