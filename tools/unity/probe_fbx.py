"""Import FBX files as Humanoid and report avatar validity, mapping and node transforms.

    python tools/unity/probe_fbx.py Assets/_RigTest/SK_Knight_bst0.fbx [more paths...]
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_call import Client

CODE = r'''
var sb = new System.Text.StringBuilder();
var paths = new string[]{ %PATHS% };
foreach (var path in paths) {
  var imp = AssetImporter.GetAtPath(path) as ModelImporter;
  if (imp == null) { sb.AppendLine(path + ": NO IMPORTER"); continue; }
  imp.animationType = ModelImporterAnimationType.Human;
  imp.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
  imp.globalScale = 1f; imp.useFileScale = true; imp.importAnimation = false;
  imp.materialImportMode = ModelImporterMaterialImportMode.None;
  imp.bakeAxisConversion = false;
  imp.SaveAndReimport();
  var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
  Avatar avatar = null;
  foreach (var a in AssetDatabase.LoadAllAssetsAtPath(path)) if (a is Avatar) avatar = (Avatar)a;
  sb.AppendLine("== " + path + " avatar=" + (avatar != null) + " valid=" + (avatar != null && avatar.isValid) + " human=" + (avatar != null && avatar.isHuman));
  if (avatar != null) {
    var hd = avatar.humanDescription;
    sb.AppendLine("  human bones mapped=" + hd.human.Length + " skeleton nodes=" + hd.skeleton.Length);
    var map = new System.Collections.Generic.List<string>();
    foreach (var hb in hd.human) map.Add(hb.humanName + "<-" + hb.boneName);
    sb.AppendLine("  " + string.Join(", ", map.ToArray()));
  }
  var arm = go.transform.Find("Armature");
  sb.AppendLine("  Armature rot=" + (arm ? arm.localRotation.eulerAngles.ToString("F2") : "MISSING") + " scale=" + (arm ? arm.localScale.ToString("F3") : "") + " children=" + (arm ? arm.childCount : 0));
  Transform hips = null, head = null, root = null;
  foreach (var t in go.GetComponentsInChildren<Transform>(true)) { if (t.name == "Hips") hips = t; if (t.name == "Head") head = t; if (t.name == "Root") root = t; }
  if (root) sb.AppendLine("  Root local rot=" + root.localRotation.eulerAngles.ToString("F2") + " pos=" + root.localPosition.ToString("F3"));
  if (hips) sb.AppendLine("  Hips world=" + hips.position.ToString("F3") + "  Head world=" + (head ? head.position.ToString("F3") : "?"));
  var smrs = go.GetComponentsInChildren<SkinnedMeshRenderer>(true);
  string[] first = null; bool same = true;
  foreach (var smr in smrs) {
    var t = smr.transform;
    var names = new string[smr.bones.Length]; for (int i = 0; i < names.Length; i++) names[i] = smr.bones[i].name;
    if (first == null) first = names; else if (!System.Linq.Enumerable.SequenceEqual(first, names)) same = false;
    sb.AppendLine(string.Format("  node {0,-9} rot={1} pos={2} scale={3} bones={4} bindposes={5} verts={6} max.y={7:F3} root={8}",
      t.name, t.localRotation.eulerAngles.ToString("F2"), t.localPosition.ToString("F3"), t.localScale.ToString("F2"),
      smr.bones.Length, smr.sharedMesh.bindposes.Length, smr.sharedMesh.vertexCount, smr.bounds.max.y, smr.rootBone ? smr.rootBone.name : "null"));
  }
  sb.AppendLine("  renderers=" + smrs.Length + " identical bone arrays=" + same);
}
return sb.ToString();
'''

if __name__ == "__main__":
    paths = ", ".join('"%s"' % p for p in sys.argv[1:])
    c = Client()
    try:
        c.call("refresh_unity", {"mode": "force", "scope": "assets", "wait_for_ready": True}, timeout=300)
        r = c.call("execute_code", {"action": "execute", "code": CODE.replace("%PATHS%", paths)}, timeout=600)
        if isinstance(r, dict):
            res = r.get("result", r.get("data", r))
            if isinstance(res, dict):
                for k in ("result", "output", "logs", "error", "message"):
                    if k in res and res[k]:
                        print(k + ":", res[k] if isinstance(res[k], str) else json.dumps(res[k], indent=1))
            else:
                print(res)
            if not r.get("success", True):
                print(json.dumps(r, indent=1)[:4000])
        else:
            print(r)
    finally:
        c.close()
