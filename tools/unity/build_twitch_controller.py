"""Build Assets/UndeadLegion/Animations/AC_Skeleton.controller (+ AM_UpperBody.mask) and prove
the additive twitch layer and the upper-body layer.

    python tools/unity/build_twitch_controller.py

Layer 0 "Base": every Skeleton@*.fbx clip as a state (Idle default). Layer 1 "UpperBody":
Override, weight 1, AvatarMask AM_UpperBody (humanoid Body/Head/Arms/Fingers, no Root, no
legs; extra transforms under Spine1), states Empty (default) + every clip whose manifest
entry (Animations/clips.json) says `layer: upper` -> an attack that can be played on the
move over a locomotion loop. Layer 2 "Twitch": Additive, weight 1, states Rest (empty) and
Twitch_01..03; Rest -> Twitch_NN on trigger `Twitch` with `TwitchIndex` == NN-1, back to
Rest on exit time. Demo/Scripts/SkeletonTwitch.cs drives it at random, SkeletonShowcase
routes upper clips to layer 1 while a locomotion clip plays on layer 0. Layers 3..5
"TwitchLoop_01..03": Additive, weight 0, one looping state each, so a twitch can be
toggled ON and stay added to whatever plays (SkeletonShowcase.SetTwitchLoop sets the
weight); several can be on at once. The twitch importers are set to loop for that; the
trigger layer still plays them once because its exit transition fires at exit time 1.

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
// every Skeleton@*.fbx except the twitches becomes a base-layer state named after its clip
// (Idle is the default; the browser plays states by clip name)
var idleClips = new System.Collections.Generic.List<AnimationClip>();
foreach (var guid in AssetDatabase.FindAssets("Skeleton@ t:Model", new string[]{ dir.TrimEnd('/') })) {
  var p = AssetDatabase.GUIDToAssetPath(guid); var fn = System.IO.Path.GetFileNameWithoutExtension(p);
  if (!fn.StartsWith("Skeleton@")) continue;
  var nm = fn.Substring("Skeleton@".Length);
  if (nm == "Idle" || nm.StartsWith("Twitch_") || nm == "Grip" || nm.StartsWith("Hand_Idle_")) continue;   // Grip: finger pose data, not a state; Hand_Idle_L/R: the finger layers' loops
  var cl = load(nm); if (cl != null) idleClips.Add(cl);
}
idleClips.Sort((x, y) => string.CompareOrdinal(x.name, y.name));
string path = dir + "AC_Skeleton.controller";
// rebuild IN PLACE: deleting the asset gives it a new GUID and every prefab's Animator
// then points at a missing controller (measured: empty clip list, nothing plays)
var ctrl = AssetDatabase.LoadAssetAtPath<UnityEditor.Animations.AnimatorController>(path);
if (ctrl == null) ctrl = UnityEditor.Animations.AnimatorController.CreateAnimatorControllerAtPath(path);
while (ctrl.layers.Length > 0) ctrl.RemoveLayer(0);
while (ctrl.parameters.Length > 0) ctrl.RemoveParameter(0);
ctrl.AddLayer("Base");
ctrl.AddParameter("Twitch", AnimatorControllerParameterType.Trigger);
ctrl.AddParameter("TwitchIndex", AnimatorControllerParameterType.Int);
var baseSm = ctrl.layers[0].stateMachine;
// NO Foot IK: measured 2026-09-19, Foot IK put the goals ~13 mm BELOW the FK feet (Idle raw
// penetration -5 mm -> -18 mm). Grounding is a per-clip lift measured in Unity instead
// (tools/unity/ground_clip.py -> export_fbx --lift) plus the prefab's clearance.
var idleState = baseSm.AddState("Idle"); idleState.motion = idle; baseSm.defaultState = idleState;
foreach (var cl in idleClips) { var vs = baseSm.AddState(cl.name); vs.motion = cl; }
sb.AppendLine("base layer: Idle + " + idleClips.Count + " more states");

// ---- masks: humanoid parts on/off + the extra (non-humanoid) transforms under a bone. UpperBody:
// Body/Head/Arms/Fingers, transforms under Spine1. LeftArm / RightArm (2026-09-22, the per-arm attack
// set): that arm + its fingers only, transforms under that Shoulder, so a left block and a right
// stab compose over whatever the base and upper-body layers play (the torso stays with them)
string modelPath = "Assets/UndeadLegion/Models/SkeletonKnight/SK_SkeletonKnight.fbx";
var modelPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
System.Func<string, AvatarMaskBodyPart[], string, AvatarMask> makeMask = (mname, parts, pathKey) => {
  string mpath_ = dir + mname + ".mask";
  var mk_ = AssetDatabase.LoadAssetAtPath<AvatarMask>(mpath_); bool fresh_ = mk_ == null; if (fresh_) mk_ = new AvatarMask();
  foreach (AvatarMaskBodyPart part_ in System.Enum.GetValues(typeof(AvatarMaskBodyPart))) {
    if (part_ == AvatarMaskBodyPart.LastBodyPart) continue;
    mk_.SetHumanoidBodyPartActive(part_, System.Array.IndexOf(parts, part_) >= 0);
  }
  if (mk_.transformCount == 0) mk_.AddTransformPath(modelPrefab.transform, true);   // adding again duplicates every path
  else if (mk_.transformCount > 80) { while (mk_.transformCount > 0) mk_.RemoveTransformPath(modelPrefab.transform, true); mk_.AddTransformPath(modelPrefab.transform, true); }
  int onPaths_ = 0;
  for (int ii_ = 0; ii_ < mk_.transformCount; ii_++) {
    string tp_ = mk_.GetTransformPath(ii_);
    bool on_ = tp_.Contains("/" + pathKey + "/") || tp_.EndsWith("/" + pathKey);
    mk_.SetTransformActive(ii_, on_); if (on_) onPaths_++;
  }
  if (fresh_) AssetDatabase.CreateAsset(mk_, mpath_); else EditorUtility.SetDirty(mk_);
  sb.AppendLine("mask " + mpath_ + ": " + onPaths_ + "/" + mk_.transformCount + " transform paths on");
  return mk_;
};
var mask = makeMask("AM_UpperBody", new AvatarMaskBodyPart[]{ AvatarMaskBodyPart.Body, AvatarMaskBodyPart.Head, AvatarMaskBodyPart.LeftArm, AvatarMaskBodyPart.RightArm, AvatarMaskBodyPart.LeftFingers, AvatarMaskBodyPart.RightFingers }, "Spine1");
var maskL = makeMask("AM_LeftArm", new AvatarMaskBodyPart[]{ AvatarMaskBodyPart.LeftArm, AvatarMaskBodyPart.LeftFingers }, "LeftShoulder");
var maskR = makeMask("AM_RightArm", new AvatarMaskBodyPart[]{ AvatarMaskBodyPart.RightArm, AvatarMaskBodyPart.RightFingers }, "RightShoulder");
// finger-only masks (2026-09-25): the empty-hand finger idles Hand_Idle_L/R loop on these; transform paths under the
// hand bone cover the palms and the socket (constant in every clip), the humanoid part covers the 15 finger bones
var maskFL = makeMask("AM_LeftFingers", new AvatarMaskBodyPart[]{ AvatarMaskBodyPart.LeftFingers }, "LeftHand");
var maskFR = makeMask("AM_RightFingers", new AvatarMaskBodyPart[]{ AvatarMaskBodyPart.RightFingers }, "RightHand");

// twitch clips loop (for the loop layers); the trigger layer's exit-time transition still ends them after one pass
foreach (var tn in new string[]{ "Twitch_01", "Twitch_02", "Twitch_03" }) {
  var timp = AssetImporter.GetAtPath(dir + "Skeleton@" + tn + ".fbx") as ModelImporter;
  if (timp == null) continue;
  var tclips = timp.clipAnimations; bool dirty = false;
  for (int i = 0; i < tclips.Length; i++) if (!tclips[i].loopTime) { tclips[i].loopTime = true; dirty = true; }
  if (dirty) { timp.clipAnimations = tclips; timp.SaveAndReimport(); sb.AppendLine("set loopTime on " + tn); }
}
ctrl.AddLayer("UpperBody"); ctrl.AddLayer("LeftArm"); ctrl.AddLayer("RightArm");
ctrl.AddLayer("Twitch");
ctrl.AddLayer("TwitchLoop_01"); ctrl.AddLayer("TwitchLoop_02"); ctrl.AddLayer("TwitchLoop_03");
ctrl.AddLayer("LeftFingers"); ctrl.AddLayer("RightFingers");   // 8, 9: Override, weight 0; SkeletonWeapon sets 1 on an EMPTY hand
var layers = ctrl.layers;
for (int i = 8; i < 10; i++) { layers[i].blendingMode = UnityEditor.Animations.AnimatorLayerBlendingMode.Override; layers[i].defaultWeight = 0f; }
layers[8].avatarMask = maskFL; layers[9].avatarMask = maskFR;
for (int i = 5; i < 8; i++) { layers[i].blendingMode = UnityEditor.Animations.AnimatorLayerBlendingMode.Additive; layers[i].defaultWeight = 0f; }
for (int i = 1; i < 4; i++) { layers[i].blendingMode = UnityEditor.Animations.AnimatorLayerBlendingMode.Override; layers[i].defaultWeight = 1f; }
layers[1].avatarMask = mask; layers[2].avatarMask = maskL; layers[3].avatarMask = maskR;
layers[4].blendingMode = UnityEditor.Animations.AnimatorLayerBlendingMode.Additive;
layers[4].defaultWeight = 1f;
ctrl.layers = layers;
// masked layers: Empty (default) + the clips the manifest tags for them. A one-shot returns to Empty
// at exit time; a LOOPING clip (Block_L_Idle) has no exit: it holds until the demo plays Empty
// ("left arm stuck in block action until released")
System.Action<int, string, string[]> fillLayer = (li, label, names) => {
  var lsm_ = ctrl.layers[li].stateMachine;
  var empty_ = lsm_.AddState("Empty"); lsm_.defaultState = empty_;
  int n_ = 0, held_ = 0;
  foreach (var nm_ in names) {
    var cl_ = load(nm_); if (cl_ == null) { sb.AppendLine("missing " + label + " clip " + nm_); continue; }
    var st_ = lsm_.AddState(nm_); st_.motion = cl_;
    if (cl_.isLooping) held_++;
    else { var back_ = st_.AddTransition(empty_); back_.hasExitTime = true; back_.exitTime = 1f; back_.duration = 0.25f; back_.hasFixedDuration = true; }   // 0.25 s: the arm clips end mid-action and the Animator carries the return
    n_++;
  }
  sb.AppendLine(label + " layer: Empty + " + n_ + " states (" + held_ + " held loops)");
};
fillLayer(1, "upper-body", new string[]{ %UPPER% });
fillLayer(2, "left-arm", new string[]{ %LEFT% });
fillLayer(3, "right-arm", new string[]{ %RIGHT% });
var sm = ctrl.layers[4].stateMachine;
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
int nLoop = 0;
for (int i = 0; i < 3; i++) {
  var clip = load("Twitch_0" + (i + 1)); if (clip == null) continue;
  var lsm = ctrl.layers[5 + i].stateMachine; var ls = lsm.AddState("Twitch_0" + (i + 1)); ls.motion = clip; lsm.defaultState = ls; nLoop++;
}
sb.AppendLine("twitch loop layers: " + nLoop + " (additive, weight 0 until toggled)");
int nHand = 0;
foreach (var hs in new string[]{ "L", "R" }) {
  var hclip = load("Hand_Idle_" + hs); if (hclip == null) { sb.AppendLine("missing Hand_Idle_" + hs); continue; }
  var hsm = ctrl.layers[hs == "L" ? 8 : 9].stateMachine; var hst = hsm.AddState("Hand_Idle_" + hs); hst.motion = hclip; hsm.defaultState = hst; nHand++;
}
sb.AppendLine("finger layers: " + nHand + " (override, weight 0 until a hand is empty)");
EditorUtility.SetDirty(ctrl); AssetDatabase.SaveAssets();
sb.AppendLine("controller " + path + ": layers=" + ctrl.layers.Length + " twitch states=" + n + " twitch layer mode=" + ctrl.layers[4].blendingMode);

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
  an.SetLayerWeight(an.GetLayerIndex("Twitch"), run == 0 ? 0f : 1f);
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
// loop layers: Twitch_01 (75 frames) toggled on must still twitch in frames 90..200 (second pass) and Hips must stay put
{
  int lf = 200; var hOff = new Quaternion[lf]; var jOff = new Quaternion[lf]; var hOn = new Quaternion[lf]; var jOn = new Quaternion[lf]; var pOn = new Quaternion[lf]; var pOff = new Quaternion[lf];
  for (int run = 0; run < 2; run++) {
    an.Rebind(); an.Update(0f); an.SetLayerWeight(an.GetLayerIndex("Twitch"), 0f);
    an.SetLayerWeight(an.GetLayerIndex("TwitchLoop_01"), run == 0 ? 0f : 1f);
    for (int f = 0; f < lf; f++) { an.Update(1f / 30f); if (run == 0) { hOff[f] = head.localRotation; jOff[f] = jaw.localRotation; pOff[f] = hips.localRotation; } else { hOn[f] = head.localRotation; jOn[f] = jaw.localRotation; pOn[f] = hips.localRotation; } }
  }
  float p1 = 0, p2 = 0, ph = 0; int act2 = 0;
  for (int f = 0; f < lf; f++) { float d = Mathf.Max(Quaternion.Angle(hOff[f], hOn[f]), Quaternion.Angle(jOff[f], jOn[f])); ph = Mathf.Max(ph, Quaternion.Angle(pOff[f], pOn[f])); if (f < 75) p1 = Mathf.Max(p1, d); else { p2 = Mathf.Max(p2, d); if (d > 0.2f) act2++; } }
  sb.AppendLine(string.Format("TwitchLoop_01 toggled on over Idle: head/jaw peak {0:F1} deg in the first pass, {1:F1} deg in the second pass (frames 75..200, {2} frames visibly twitching), Hips diff {3:F2} deg", p1, p2, act2, ph));
}

// ---- layering proof: Walk_Fwd on Base + Attack_R_Slice on RightArm must give the walk's legs and
// spine and the attack's right arm; compared per frame against each clip played alone on the base
// layer. Then Block_L_Idle held on LeftArm under the same mix must keep the block's left arm
Transform lLeg = null, rArm = null, spine1 = null, lFoot = null;
foreach (var t in go.GetComponentsInChildren<Transform>(true)) { if (t.name == "LeftUpLeg") lLeg = t; if (t.name == "RightArm") rArm = t; if (t.name == "Spine1") spine1 = t; if (t.name == "LeftFoot") lFoot = t; }
var sliceClip = load("Attack_R_Slice"); int nf = Mathf.Min(60, sliceClip != null ? Mathf.RoundToInt(sliceClip.length * sliceClip.frameRate) - 1 : 60);   // within the clip: after it the arm layer exits to Empty by design
var legWalk = new Quaternion[nf]; var armAtk = new Quaternion[nf]; var sp1Atk = new Quaternion[nf]; var footWalk = new Vector3[nf];
var legMix = new Quaternion[nf]; var armMix = new Quaternion[nf]; var sp1Mix = new Quaternion[nf]; var footMix = new Vector3[nf]; var armWalk = new Quaternion[nf];
int lArmL = an.GetLayerIndex("LeftArm"), rArmL = an.GetLayerIndex("RightArm");
Transform lArm = null; foreach (var t in go.GetComponentsInChildren<Transform>(true)) if (t.name == "LeftArm") lArm = t;
var sp1Walk = new Quaternion[nf]; var lArmBlock = new Quaternion[nf]; var lArmMix = new Quaternion[nf]; var armMix2 = new Quaternion[nf];
for (int run = 0; run < 5; run++) {
  an.Rebind(); an.Update(0f);
  an.SetLayerWeight(an.GetLayerIndex("Twitch"), 0f);
  if (run == 0) { an.Play("Walk_Fwd", 0, 0f); }
  if (run == 1) { an.Play("Attack_R_Slice", 0, 0f); }
  if (run == 2) { an.Play("Walk_Fwd", 0, 0f); an.Play("Attack_R_Slice", rArmL, 0f); }
  if (run == 3) { an.Play("Block_L_Idle", 0, 0f); }
  if (run == 4) { an.Play("Walk_Fwd", 0, 0f); an.Play("Block_L_Idle", lArmL, 0f); an.Play("Attack_R_Slice", rArmL, 0f); }
  an.Update(0f);
  for (int f = 0; f < nf; f++) {
    an.Update(1f / 30f);
    if (run == 0) { legWalk[f] = lLeg.localRotation; footWalk[f] = lFoot.position - hips.position; armWalk[f] = rArm.localRotation; sp1Walk[f] = spine1.localRotation; }
    if (run == 1) { armAtk[f] = rArm.localRotation; sp1Atk[f] = spine1.localRotation; }
    if (run == 2) { legMix[f] = lLeg.localRotation; armMix[f] = rArm.localRotation; sp1Mix[f] = spine1.localRotation; footMix[f] = lFoot.position - hips.position; }
    if (run == 3) { lArmBlock[f] = lArm.localRotation; }
    if (run == 4) { lArmMix[f] = lArm.localRotation; armMix2[f] = rArm.localRotation; }
  }
}
float legDev = 0, armDev = 0, sp1Dev = 0, footDev = 0, armVsWalk = 0, legRange = 0, armRange = 0, blockDev = 0, armDev2 = 0, sp1Range = 0;
for (int f = 0; f < nf; f++) {
  legDev = Mathf.Max(legDev, Quaternion.Angle(legWalk[f], legMix[f]));
  armDev = Mathf.Max(armDev, Quaternion.Angle(armAtk[f], armMix[f]));
  sp1Dev = Mathf.Max(sp1Dev, Quaternion.Angle(sp1Walk[f], sp1Mix[f]));
  sp1Range = Mathf.Max(sp1Range, Quaternion.Angle(sp1Atk[0], sp1Atk[f]));
  footDev = Mathf.Max(footDev, (footWalk[f] - footMix[f]).magnitude);
  armVsWalk = Mathf.Max(armVsWalk, Quaternion.Angle(armWalk[f], armMix[f]));
  legRange = Mathf.Max(legRange, Quaternion.Angle(legWalk[0], legWalk[f]));
  armRange = Mathf.Max(armRange, Quaternion.Angle(armAtk[0], armAtk[f]));
  blockDev = Mathf.Max(blockDev, Quaternion.Angle(lArmBlock[f], lArmMix[f]));
  armDev2 = Mathf.Max(armDev2, Quaternion.Angle(armAtk[f], armMix2[f]));
}
sb.AppendLine(string.Format("layering (Walk_Fwd base + Attack_R_Slice right arm, {0} frames): LeftUpLeg follows the walk within {1:F2} deg (walk swings {2:F1} deg), LeftFoot within {3:F1} mm; RightArm follows the attack within {4:F2} deg (attack swings {5:F1} deg; it differs from the walk's arm by up to {6:F1} deg); Spine1 follows the WALK within {7:F2} deg (the attack alone swings it {8:F1} deg: arm layers are arm-only)", nf, legDev, legRange, footDev * 1000f, armDev, armRange, armVsWalk, sp1Dev, sp1Range));
sb.AppendLine(string.Format("held block: Walk_Fwd + Block_L_Idle on LeftArm + Attack_R_Slice on RightArm: LeftArm follows the block within {0:F2} deg, RightArm follows the attack within {1:F2} deg", blockDev, armDev2));
GameObject.DestroyImmediate(go);
return sb.ToString();
'''

if __name__ == "__main__":
    manifest = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Animations", "clips.json")
    clips = json.load(open(manifest))["clips"]
    tagged = lambda tag: [c["name"] for c in clips if c.get("layer") == tag]
    print("from the manifest: upper", ", ".join(tagged("upper")), "| left", ", ".join(tagged("left")), "| right", ", ".join(tagged("right")))
    code = CODE.replace("%UPPER%", ", ".join('"%s"' % u for u in tagged("upper"))).replace("%LEFT%", ", ".join('"%s"' % u for u in tagged("left"))).replace("%RIGHT%", ", ".join('"%s"' % u for u in tagged("right")))
    c = Client()
    try:
        c.call("refresh_unity", {"mode": "force", "scope": "all", "compile": "request", "wait_for_ready": True}, timeout=600)
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
