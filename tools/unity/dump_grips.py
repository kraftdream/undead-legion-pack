"""Dump the hand slots and every weapon prefab's Grip from the Unity project to JSON.

    python tools/unity/dump_grips.py [out.json]      (default Animations/unity_grips.json)

Reads PF_SkeletonArcher's LeftHandSlot / RightHandSlot (all six prefabs share one set of
values, CLAUDE.md 2) and the Grip child of every Prefabs/Weapons/W_*.prefab, as Unity
LOCAL position (metres) + rotation (quaternion x, y, z, w). tools/anim_weapon_ref.py
converts them into the Blender socket frame to attach a weapon in the anim file exactly
as Unity does.
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_call import Client

CODE = r'''
var sb = new System.Text.StringBuilder(); sb.Append("{\"slots\":{");
var pf = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/UndeadLegion/Prefabs/Characters/PF_SkeletonArcher.prefab");
bool first = true;
foreach (var t in pf.GetComponentsInChildren<Transform>(true)) if (t.name == "RightHandSlot" || t.name == "LeftHandSlot") {
  if (!first) sb.Append(","); first = false;
  sb.Append(string.Format(System.Globalization.CultureInfo.InvariantCulture, "\"{0}\":{{\"pos\":[{1},{2},{3}],\"rot\":[{4},{5},{6},{7}]}}", t.name.StartsWith("Left") ? "L" : "R", t.localPosition.x, t.localPosition.y, t.localPosition.z, t.localRotation.x, t.localRotation.y, t.localRotation.z, t.localRotation.w));
}
sb.Append("},\"grips\":{"); first = true;
foreach (var guid in AssetDatabase.FindAssets("t:Prefab", new string[]{"Assets/UndeadLegion/Prefabs/Weapons"})) {
  var path = AssetDatabase.GUIDToAssetPath(guid); var wp = AssetDatabase.LoadAssetAtPath<GameObject>(path);
  if (wp == null || !wp.name.StartsWith("W_")) continue;
  Transform g = null; foreach (var t in wp.GetComponentsInChildren<Transform>(true)) if (t.name == "Grip") g = t;
  if (g == null) continue;
  if (!first) sb.Append(","); first = false;
  sb.Append(string.Format(System.Globalization.CultureInfo.InvariantCulture, "\"{0}\":{{\"pos\":[{1},{2},{3}],\"rot\":[{4},{5},{6},{7}]}}", wp.name.Substring(2), g.localPosition.x, g.localPosition.y, g.localPosition.z, g.localRotation.x, g.localRotation.y, g.localRotation.z, g.localRotation.w));
}
sb.Append("}}"); return sb.ToString();
'''

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Animations", "unity_grips.json")
    c = Client()
    try:
        r = c.call("execute_code", {"action": "execute", "code": CODE}, timeout=300); d = r.get("data", r)
        text = d.get("result") if isinstance(d, dict) else None
        assert text and text.startswith("{"), json.dumps(r)[:400]
        data = json.loads(text)
        json.dump(data, open(out, "w", encoding="utf-8"), indent=1)
        print("wrote %s: slots %s, grips %s" % (out, sorted(data["slots"]), sorted(data["grips"])))
    finally:
        c.close()
