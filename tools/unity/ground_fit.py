"""Close the grounding loop in the engine: measure, per frame, the lowest vertex of EACH of the six
models under a clip in Unity, and write a per-frame Root lift that puts the HIGHEST model's lowest
point on the floor (the others sink by the boot-sole spread, <= ~6 mm, which an opaque floor hides;
a gap shows). export_fbx.py --lift-curve applies it; anim_batch runs it for manifest `ground_fit`.

    python tools/unity/ground_fit.py <Clip> [--target 0.0] [--out Animations/ground_fit/<Clip>.json]

Why: the Blender-side grounding puts the LOWEST of the six characters' meshes on the floor and the
export adds a constant lift, so on the Knight the boots hovered 4-13 mm through the stab (user:
"still slight lift is present"); Humanoid playback also differs from Blender by a few mm per frame.
The measurement here is the truth the user sees. Root Y is baked into the pose, so a per-frame Root
shift moves the whole character 1:1 and one pass converges.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_call import Client

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS = ["SkeletonKnight", "SkeletonArcher", "SkeletonAssassin", "SkeletonMage", "SkeletonNecromancer", "SkeletonWarrior"]
CODE = r'''
var sb = new System.Text.StringBuilder();
string clipName = "%CLIP%";
AssetDatabase.ImportAsset("Assets/UndeadLegion/Animations/Skeleton@" + clipName + ".fbx", ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
AnimationClip clip = null;
foreach (var a in AssetDatabase.LoadAllAssetsAtPath("Assets/UndeadLegion/Animations/Skeleton@" + clipName + ".fbx")) if (a is AnimationClip && !a.name.StartsWith("__preview")) clip = (AnimationClip)a;
if (clip == null) return "no clip";
int frames = Mathf.RoundToInt(clip.length * clip.frameRate); var bake = new Mesh();
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
  sb.Append(ch + ":");
  for (int f = 0; f <= frames; f++) {
    an.Play("X", 0, f / (float)frames); an.Update(0f); an.Update(0.0001f);
    float m = 9f;
    foreach (var r in go.GetComponentsInChildren<SkinnedMeshRenderer>()) { r.BakeMesh(bake); var vs = bake.vertices; for (int i = 0; i < vs.Length; i++) m = Mathf.Min(m, r.transform.TransformPoint(vs[i]).y); }
    sb.Append(" " + m.ToString("0.00000", System.Globalization.CultureInfo.InvariantCulture));
  }
  sb.Append("\n");
  GameObject.DestroyImmediate(go);
}
UnityEngine.Object.DestroyImmediate(bake);
return sb.ToString();
'''


def measure(clip):
    code = CODE.replace("%CLIP%", clip).replace("%MODELS%", ", ".join('"%s"' % m for m in MODELS))
    c = Client()
    try:
        r = c.call("execute_code", {"action": "execute", "code": code}, timeout=900); d = r.get("data", r)
        res = d.get("result") if isinstance(d, dict) else None
    finally:
        c.close()
    if not res or ":" not in res:
        raise SystemExit("ground_fit: no measurement (%s)" % (res or json.dumps(r)[:300]))
    per = {}
    for line in res.strip().splitlines():
        name, vals = line.split(":", 1)
        per[name.strip()] = [float(v) for v in vals.split()]
    return per


def main():
    argv = sys.argv[1:]
    clip = argv[0]
    target = float(argv[argv.index("--target") + 1]) if "--target" in argv else 0.0
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(ROOT, "Animations", "ground_fit", clip + ".json")
    per = measure(clip)
    n = min(len(v) for v in per.values())
    maxmin = [max(per[m][f] for m in per) for f in range(n)]          # the model whose lowest point is highest
    minmin = [min(per[m][f] for m in per) for f in range(n)]
    lift = [target - v for v in maxmin]
    # one [1,2,1] pass: the measurement is per frame and a 1 mm ripple would become a hips jitter
    sm = [lift[0]] + [(lift[i - 1] + 2 * lift[i] + lift[i + 1]) / 4.0 for i in range(1, n - 1)] + [lift[-1]]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump({"clip": clip, "target": target, "frames": n, "lift": [round(v, 5) for v in sm],
               "measured_max_over_models": [round(v, 5) for v in maxmin], "measured_min_over_models": [round(v, 5) for v in minmin],
               "per_model": {m: [round(v, 5) for v in per[m][:n]] for m in per}}, open(out, "w"), indent=1)
    print("ground_fit %s: %d frames; highest model's lowest point %+.4f..%+.4f m, lowest model's %+.4f..%+.4f; lift curve %+.4f..%+.4f -> %s"
          % (clip, n, min(maxmin), max(maxmin), min(minmin), max(minmin), min(sm), max(sm), os.path.relpath(out, ROOT)))


if __name__ == "__main__":
    main()
