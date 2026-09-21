"""One contact sheet of every weapon loadout, close-up on the holding hand(s), in edit mode.

    python tools/unity/grip_sheet.py <out.png> [clip] [character] [normalized time]

One row per loadout (CharacterPrefabBuilder.LoadoutTable order): close-ups of the right
hand socket, the left hand socket and the forearm socket, each from the palm side and from
above the thumb, only for the sockets that hold something in that loadout. The quick way to
review the grip table in tools/export_weapons.py and the per-hand offsets on SkeletonWeapon.
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_call import Client

CODE = r'''
var sb = new System.Text.StringBuilder();
var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/UndeadLegion/Prefabs/Characters/PF_%CHAR%.prefab");
var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab); go.name = "__sheet";
var an = go.GetComponent<Animator>(); an.applyRootMotion = false; an.cullingMode = AnimatorCullingMode.AlwaysAnimate; an.Rebind(); an.Update(0f);
if (an.HasState(0, Animator.StringToHash("%CLIP%"))) { an.Play("%CLIP%", 0, %T%f); an.Update(0f); an.Update(0.03f); }
var w = go.GetComponent<UndeadLegion.Demo.SkeletonWeapon>();
var all = go.GetComponentsInChildren<Transform>(true);
System.Func<string, Transform> T = (n) => System.Array.Find(all, x => x.name == n);
int W = 360, H = 360; int rows = w.loadouts.Count; int cols = 6;
var sheet = new Texture2D(W * cols, H * rows, TextureFormat.RGB24, false);
var camGo = new GameObject("__cam"); var cam = camGo.AddComponent<Camera>(); cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(0.25f, 0.26f, 0.3f); cam.fieldOfView = 30f; cam.nearClipPlane = 0.05f;
var rt = new RenderTexture(W, H, 24); cam.targetTexture = rt; var tile = new Texture2D(W, H, TextureFormat.RGB24, false);
var black = new Color[W * H]; for (int i = 0; i < black.Length; i++) black[i] = new Color(0.12f, 0.12f, 0.14f);
for (int li = 0; li < rows; li++) {
  w.Equip(li); w.ApplyGrip();
  bool r = false, l = false, f = false;
  foreach (var it in w.loadouts[li].items) { if (it.hand == UndeadLegion.Demo.SkeletonWeapon.Hand.Right) r = true; else if (it.hand == UndeadLegion.Demo.SkeletonWeapon.Hand.Left) l = true; else f = true; }
  string[] socks = { "RightWeaponSocket", "LeftWeaponSocket", "LeftForeArm" }; bool[] use = { r, l, f };
  for (int si = 0; si < 3; si++) {
    for (int vi = 0; vi < 2; vi++) {
      int col = si * 2 + vi; int y0 = (rows - 1 - li) * H;
      if (!use[si]) { sheet.SetPixels(col * W, y0, W, H, black); continue; }
      var s = T(socks[si]); Vector3 c = s.position; if (si == 2) c = (T("LeftForeArm").position + T("LeftHand").position) * 0.5f;
      // view 0: from the back-of-hand side (+Z of the socket) so the fingers wrap towards the camera; view 1: from along -X (thumb side)
      float mirror = si == 1 ? -1f : 1f;   // the left socket's frame is mirrored: its thumb side is +X
      Vector3 dir = si == 2 ? (vi == 0 ? -go.transform.right : go.transform.forward) : (vi == 0 ? s.forward + s.up * 0.4f : -s.right * mirror + s.up * 0.3f);
      cam.transform.position = c + dir.normalized * 0.7f; cam.transform.LookAt(c);
      cam.Render(); var prev = RenderTexture.active; RenderTexture.active = rt; tile.ReadPixels(new Rect(0, 0, W, H), 0, 0); tile.Apply(); RenderTexture.active = prev;
      sheet.SetPixels(col * W, y0, W, H, tile.GetPixels());
    }
  }
  sb.AppendLine(li + " " + w.loadouts[li].displayName);
}
sheet.Apply(); System.IO.File.WriteAllBytes("%OUT%", sheet.EncodeToPNG());
w.Clear(); UnityEngine.Object.DestroyImmediate(tile); UnityEngine.Object.DestroyImmediate(sheet); UnityEngine.Object.DestroyImmediate(camGo); UnityEngine.Object.DestroyImmediate(rt); GameObject.DestroyImmediate(go);
return "rows (top to bottom):\n" + sb.ToString();
'''

if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1]).replace("\\", "/"); os.makedirs(os.path.dirname(out), exist_ok=True)
    clip = sys.argv[2] if len(sys.argv) > 2 else "Idle"
    char = sys.argv[3] if len(sys.argv) > 3 else "SkeletonKnight"
    t = sys.argv[4] if len(sys.argv) > 4 else "0.3"
    c = Client()
    try:
        c.call("refresh_unity", {"mode": "if_dirty", "scope": "assets", "wait_for_ready": True}, timeout=300)
        r = c.call("execute_code", {"action": "execute", "code": CODE.replace("%OUT%", out).replace("%CLIP%", clip).replace("%CHAR%", char).replace("%T%", t)}, timeout=900)
        d = r.get("data", r); print(d.get("result") if isinstance(d, dict) else json.dumps(r)[:600])
    finally:
        c.close()
