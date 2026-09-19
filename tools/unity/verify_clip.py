"""Import a clip FBX as Humanoid (avatar copied from a model) and measure it on every model.

    python tools/unity/verify_clip.py Assets/UndeadLegion/Animations/Skeleton@Walk_Fwd.fbx \
        [--avatar Assets/UndeadLegion/Models/SkeletonKnight/SK_SkeletonKnight.fbx] [--loop 1]

Prints, per model: whether the clip has curves, its length, the GameObject's travel and
yaw after stepping the Animator through the whole clip with Apply Root Motion ON, the
same with it OFF (must be zero), and how much a body bone moved (proof the clip drives
the pose, not just the root). Leaves a temporary controller in Assets/_PipelineTest,
which the caller deletes on disk.
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_call import Client

MODELS = ["SkeletonKnight", "SkeletonArcher", "SkeletonAssassin", "SkeletonMage", "SkeletonNecromancer", "SkeletonWarrior"]

CODE = r'''
var sb = new System.Text.StringBuilder();
string clipPath = "%CLIP%"; string avatarPath = "%AVATAR%"; bool loop = %LOOP%; bool additive = %ADDITIVE%;
var avImp = AssetImporter.GetAtPath(avatarPath) as ModelImporter;
Avatar srcAvatar = null;
foreach (var a in AssetDatabase.LoadAllAssetsAtPath(avatarPath)) if (a is Avatar) srcAvatar = (Avatar)a;
if (srcAvatar == null) return "no avatar at " + avatarPath;
var imp = AssetImporter.GetAtPath(clipPath) as ModelImporter;
if (imp == null) return "no importer at " + clipPath;
imp.animationType = ModelImporterAnimationType.Human;
imp.avatarSetup = ModelImporterAvatarSetup.CopyFromOther;
imp.sourceAvatar = srcAvatar;
imp.globalScale = 1f; imp.useFileScale = true; imp.importAnimation = true;
imp.materialImportMode = ModelImporterMaterialImportMode.None; imp.bakeAxisConversion = false;
imp.importBlendShapes = false; imp.importCameras = false; imp.importLights = false;
var clips = imp.defaultClipAnimations;
foreach (var c in clips) { c.loopTime = loop; c.loopPose = false; c.hasAdditiveReferencePose = additive; c.additiveReferencePoseFrame = 0f; c.lockRootRotation = false; c.lockRootHeightY = false; c.lockRootPositionXZ = false; c.keepOriginalOrientation = true; c.keepOriginalPositionY = true; c.keepOriginalPositionXZ = true; }
imp.clipAnimations = clips;
imp.SaveAndReimport();
AnimationClip clip = null;
foreach (var a in AssetDatabase.LoadAllAssetsAtPath(clipPath)) if (a is AnimationClip && !a.name.StartsWith("__preview")) clip = (AnimationClip)a;
if (clip == null) return "NO CLIP imported from " + clipPath + " (node paths mismatch?)";
var bindings = AnimationUtility.GetCurveBindings(clip);
sb.AppendLine(string.Format("clip {0}: length={1:F3}s frameRate={2} curves={3} humanMotion={4} isHumanMotion={5} apparentSpeed={6:F3} averageSpeed={7}",
  clip.name, clip.length, clip.frameRate, bindings.Length, clip.hasMotionCurves, clip.isHumanMotion, clip.apparentSpeed, clip.averageSpeed.ToString("F3")));
if (!AssetDatabase.IsValidFolder("Assets/_PipelineTest")) AssetDatabase.CreateFolder("Assets", "_PipelineTest");
var ctrl = UnityEditor.Animations.AnimatorController.CreateAnimatorControllerAtPath("Assets/_PipelineTest/AC_Test.controller");
ctrl.AddMotion(clip);
var models = new string[]{ %MODELS% };
foreach (var m in models) {
  var path = "Assets/UndeadLegion/Models/" + m + "/SK_" + m + ".fbx";
  var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
  Avatar av = null; foreach (var a in AssetDatabase.LoadAllAssetsAtPath(path)) if (a is Avatar) av = (Avatar)a;
  var go = (GameObject)GameObject.Instantiate(prefab); go.name = "__test_" + m;
  var an = go.GetComponent<Animator>(); if (an == null) an = go.AddComponent<Animator>();
  an.avatar = av; an.runtimeAnimatorController = ctrl; an.cullingMode = AnimatorCullingMode.AlwaysAnimate;
  var watch = new System.Collections.Generic.List<Transform>();
  foreach (var t in go.GetComponentsInChildren<Transform>(true)) if (t.name == "Hips" || t.name == "Spine" || t.name == "Spine1" || t.name == "Head" || t.name == "RightArm" || t.name == "LeftUpLeg") watch.Add(t);
  int steps = Mathf.RoundToInt(clip.length * clip.frameRate);
  string line = m;
  foreach (var rm in new bool[]{true, false}) {
    go.transform.position = Vector3.zero; go.transform.rotation = Quaternion.identity;
    an.applyRootMotion = rm; an.Rebind(); an.Update(0f);
    var q0 = new System.Collections.Generic.List<Quaternion>(); foreach (var w in watch) q0.Add(w.localRotation);
    var moved = new float[watch.Count];
    for (int i = 0; i < steps; i++) { an.Update(1f / clip.frameRate); for (int k = 0; k < watch.Count; k++) moved[k] = Mathf.Max(moved[k], Quaternion.Angle(q0[k], watch[k].localRotation)); }
    string mv = ""; for (int k = 0; k < watch.Count; k++) mv += watch[k].name + "=" + moved[k].ToString("F1") + " ";
    line += string.Format(" | rootMotion={0}: travel={1} yaw={2:F2} | max local rot (deg): {3}", rm ? "ON " : "OFF", go.transform.position.ToString("F3"), go.transform.eulerAngles.y, mv);
  }
  sb.AppendLine(line);
  GameObject.DestroyImmediate(go);
}
return sb.ToString();
'''

if __name__ == "__main__":
    args = sys.argv[1:]
    clip = args[0]
    avatar = args[args.index("--avatar") + 1] if "--avatar" in args else "Assets/UndeadLegion/Models/SkeletonKnight/SK_SkeletonKnight.fbx"
    loop = "true" if ("--loop" in args and args[args.index("--loop") + 1] == "1") else "false"
    additive = "true" if ("--additive" in args and args[args.index("--additive") + 1] == "1") else "false"
    code = CODE.replace("%CLIP%", clip).replace("%AVATAR%", avatar).replace("%LOOP%", loop).replace("%ADDITIVE%", additive) \
               .replace("%MODELS%", ", ".join('"%s"' % m for m in MODELS))
    c = Client()
    try:
        c.call("refresh_unity", {"mode": "force", "scope": "assets", "wait_for_ready": True}, timeout=300)
        r = c.call("execute_code", {"action": "execute", "code": code}, timeout=900)
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
