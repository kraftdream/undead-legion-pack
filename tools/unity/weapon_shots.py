"""Render a character playing a clip with a weapon loadout equipped, in edit mode.

    python tools/unity/weapon_shots.py <out_dir> <clip> <loadout index> [character] [normalized time]

e.g.  python tools/unity/weapon_shots.py shots Idle_TwoHanded 7 SkeletonKnight 0.3
Loadout indices follow CharacterPrefabBuilder.LoadoutTable (0 sword+shield, 1 sword,
2 axe+round shield, 3 mace, 4 dagger, 5 two daggers, 6 longsword 2H, 7 battle axe 2H,
8 longbow, 9 staff, 10 spellbook). Writes <out>/<clip>_<loadout>_{front,right,left}.png
through a camera render (no play mode, no UI), so it is safe while the factories run.
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_call import Client

CODE = r'''
var sb = new System.Text.StringBuilder();
var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/UndeadLegion/Prefabs/Characters/PF_%CHAR%.prefab");
var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab); go.name = "__wpn";
var an = go.GetComponent<Animator>(); an.applyRootMotion = false; an.cullingMode = AnimatorCullingMode.AlwaysAnimate;
an.Rebind(); an.Update(0f);
if (an.HasState(0, Animator.StringToHash("%CLIP%"))) { an.Play("%CLIP%", 0, %T%f); an.Update(0f); an.Update(0.03f); sb.AppendLine("playing %CLIP%"); } else sb.AppendLine("NO STATE %CLIP% - rest pose");
var w = go.GetComponent<UndeadLegion.Demo.SkeletonWeapon>();
w.Equip(%LOADOUT%);
var camGo = new GameObject("__cam"); var cam = camGo.AddComponent<Camera>(); cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(0.25f, 0.26f, 0.3f); cam.fieldOfView = 32f;
var rt = new RenderTexture(800, 1000, 24); cam.targetTexture = rt;
var views = new object[][]{ new object[]{"front", new Vector3(0, 1.0f, 3.4f)}, new object[]{"right", new Vector3(3.4f, 1.0f, 0)}, new object[]{"left", new Vector3(-3.4f, 1.0f, 0)} };
foreach (var v in views) {
  cam.transform.position = (Vector3)v[1]; cam.transform.LookAt(new Vector3(0, 0.95f, 0));
  cam.Render(); var prev = RenderTexture.active; RenderTexture.active = rt;
  var tex = new Texture2D(800, 1000, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, 800, 1000), 0, 0); tex.Apply(); RenderTexture.active = prev;
  System.IO.File.WriteAllBytes("%OUT%/%CLIP%_%LOADOUT%_" + (string)v[0] + ".png", tex.EncodeToPNG());
  UnityEngine.Object.DestroyImmediate(tex);
}
Transform rs = null; foreach (var t in go.GetComponentsInChildren<Transform>(true)) if (t.name == "RightWeaponSocket") rs = t;
if (rs != null) sb.AppendLine("RightWeaponSocket at " + rs.position.ToString("F2") + " hilt dir " + rs.up.ToString("F2") + " back-of-hand " + rs.forward.ToString("F2"));
w.Clear(); UnityEngine.Object.DestroyImmediate(camGo); UnityEngine.Object.DestroyImmediate(rt); GameObject.DestroyImmediate(go);
return sb.ToString();
'''

if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1]).replace("\\", "/"); os.makedirs(out, exist_ok=True)
    clip = sys.argv[2]; loadout = sys.argv[3]
    char = sys.argv[4] if len(sys.argv) > 4 else "SkeletonKnight"
    t = sys.argv[5] if len(sys.argv) > 5 else "0.3"
    code = CODE.replace("%OUT%", out).replace("%CLIP%", clip).replace("%LOADOUT%", loadout).replace("%CHAR%", char).replace("%T%", t)
    c = Client()
    try:
        c.call("refresh_unity", {"mode": "if_dirty", "scope": "assets", "wait_for_ready": True}, timeout=300)
        r = c.call("execute_code", {"action": "execute", "code": code}, timeout=600)
        d = r.get("data", r)
        print(d.get("result") if isinstance(d, dict) else d)
    finally:
        c.close()
