using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using UndeadLegion.Demo;

namespace UndeadLegion.DemoEditor
{
    /// <summary>
    /// Builds PF_<Character>.prefab for every character from its SK_<Character>.fbx:
    /// materials per renderer (Body -> M_<C>_Body, everything else -> M_<C>_Armor),
    /// Animator (own avatar, the shared AC_Skeleton, root motion on, always animate),
    /// CapsuleCollider, SkeletonModules and SkeletonTwitch. Root stays at exactly
    /// 0 / 0 / 1: the Asset Store validator compares it at 12 decimal places.
    /// </summary>
    public static class CharacterPrefabBuilder
    {
        const string Root = UndeadLegionImportSetup.Root;
        const string ControllerPath = Root + "/Animations/AC_Skeleton.controller";

        [MenuItem("Undead Legion/2. Rebuild Character Prefabs")]
        public static void Run()
        {
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath);
            if (controller == null) Debug.LogWarning("[UndeadLegion] no controller at " + ControllerPath);
            int n = 0;
            foreach (var c in UndeadLegionImportSetup.Characters)
                if (Build(c, controller)) n++;
            AssetDatabase.SaveAssets();
            Debug.Log("[UndeadLegion] built " + n + " character prefabs");
        }

        public static string PrefabPath(string c)
        {
            return string.Format("{0}/Prefabs/Characters/PF_{1}.prefab", Root, c);
        }

        /// <summary>Weapon loadouts every character offers in the demo (name, then
        /// (model, hand) pairs). Models are the SM_*.fbx from tools/export_weapons.py.</summary>
        static readonly object[][] LoadoutTable =
        {
            new object[] { "Sword + shield", "SM_H1Sword", SkeletonWeapon.Hand.Right, "SM_H1HeaterShield", SkeletonWeapon.Hand.Left },
            new object[] { "Sword", "SM_H1Sword", SkeletonWeapon.Hand.Right },
            new object[] { "Axe + round shield", "SM_H1Axe", SkeletonWeapon.Hand.Right, "SM_H1RoundShield", SkeletonWeapon.Hand.Left },
            new object[] { "Mace", "SM_H1Mace", SkeletonWeapon.Hand.Right },
            new object[] { "Dagger", "SM_H1Dagger", SkeletonWeapon.Hand.Right },
            new object[] { "Two daggers", "SM_H1Dagger", SkeletonWeapon.Hand.Right, "SM_H1Dagger", SkeletonWeapon.Hand.Left },
            new object[] { "Longsword (2H)", "SM_H2Longsword", SkeletonWeapon.Hand.Right },
            new object[] { "Battle axe (2H)", "SM_H2Axe", SkeletonWeapon.Hand.Right },
            new object[] { "Longbow", "SM_H2Longbow", SkeletonWeapon.Hand.Left, "SM_Arrow", SkeletonWeapon.Hand.Right },
            new object[] { "Staff", "SM_H2MagicStuff", SkeletonWeapon.Hand.Right },
            new object[] { "Spellbook", "SM_H1Spellbook", SkeletonWeapon.Hand.Left },
        };

        static readonly string[] FingerBones = { "Thumb1", "Thumb2", "Thumb3", "Index1", "Index2", "Index3", "Middle1", "Middle2", "Middle3", "Ring1", "Ring2", "Ring3", "Pinky1", "Pinky2", "Pinky3" };

        /// <summary>Sample Skeleton@Grip (the authored finger grip, tools/anim_grip_export.py) on this
        /// model through its own avatar and store the finger bones' local rotations on the component.</summary>
        static void SampleGrip(GameObject go, SkeletonWeapon weapon)
        {
            AnimationClip clip = null;
            foreach (var a in AssetDatabase.LoadAllAssetsAtPath(Root + "/Animations/Skeleton@Grip.fbx"))
                if (a is AnimationClip && !a.name.StartsWith("__preview")) clip = (AnimationClip)a;
            weapon.gripLeft.Clear(); weapon.gripRight.Clear();
            if (clip == null) { Debug.LogWarning("[UndeadLegion] no Skeleton@Grip clip: hands will not grip weapons"); return; }
            var an = go.GetComponent<Animator>();
            var all = go.GetComponentsInChildren<Transform>(true);
            AnimationMode.StartAnimationMode();
            try
            {
                AnimationMode.BeginSampling();
                AnimationMode.SampleAnimationClip(go, clip, 0.02f);
                AnimationMode.EndSampling();
                foreach (var side in new[] { "Left", "Right" })
                    foreach (var f in FingerBones)
                    {
                        var t = System.Array.Find(all, x => x.name == side + "Hand" + f);
                        if (t == null) continue;
                        var gb = new SkeletonWeapon.GripBone { bone = t.name, localRotation = t.localRotation };
                        if (side == "Left") weapon.gripLeft.Add(gb); else weapon.gripRight.Add(gb);
                    }
            }
            finally { AnimationMode.StopAnimationMode(); }
            Debug.Log("[UndeadLegion] grip sampled on " + go.name + ": " + weapon.gripLeft.Count + " left + " + weapon.gripRight.Count + " right finger bones");
        }

        static System.Collections.Generic.List<SkeletonWeapon.Loadout> Loadouts()
        {
            var list = new System.Collections.Generic.List<SkeletonWeapon.Loadout>();
            foreach (var row in LoadoutTable)
            {
                var lo = new SkeletonWeapon.Loadout { displayName = (string)row[0] };
                for (int i = 1; i + 1 < row.Length; i += 2)
                {
                    var model = EnsureWeaponPrefab((string)row[i]);
                    if (model == null) { Debug.LogWarning("[UndeadLegion] missing weapon model " + row[i]); continue; }
                    lo.items.Add(new SkeletonWeapon.Item { model = model, hand = (SkeletonWeapon.Hand)row[i + 1] });
                }
                if (lo.items.Count > 0) list.Add(lo);
            }
            return list;
        }

        /// <summary>Prefabs/Weapons/W_<Name>.prefab: the SM_<Name> mesh with its material and a
        /// child `Grip` (identity by default: the export already put the grip at the origin,
        /// blade along +Y). Created once; an existing prefab is left alone so an edited Grip
        /// survives every rebuild. Delete the prefab to regenerate it.</summary>
        static GameObject EnsureWeaponPrefab(string sm)
        {
            string name = sm.StartsWith("SM_") ? sm.Substring(3) : sm;
            string path = string.Format("{0}/Prefabs/Weapons/W_{1}.prefab", Root, name);
            var existing = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (existing != null) return existing;
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(string.Format("{0}/Models/Weapons/{1}.fbx", Root, sm));
            if (model == null) return null;
            var mat = AssetDatabase.LoadAssetAtPath<Material>(string.Format("{0}/Materials/URP/M_Weapon_{1}.mat", Root, name));
            if (mat == null) mat = AssetDatabase.LoadAssetAtPath<Material>(Root + "/Materials/URP/M_Weapon_Placeholder.mat");
            var root = new GameObject("W_" + name);
            var mesh = (GameObject)PrefabUtility.InstantiatePrefab(model);
            mesh.transform.SetParent(root.transform, false);
            mesh.name = "Mesh";
            foreach (var r in mesh.GetComponentsInChildren<Renderer>())
            {
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++) mats[i] = mat;
                r.sharedMaterials = mats;
            }
            var grip = new GameObject(SkeletonWeapon.GripName).transform;
            grip.SetParent(root.transform, false);
            if (name.Contains("Shield"))
            {
                // hand-held shield (2026-09-21): the fist closes on a handle 4.5 cm behind the
                // plate and the plate's top points towards the wrist (slot -X), so the Grip sits
                // behind the mesh origin (the boss) and is rolled -90 deg about the face normal
                grip.localPosition = new Vector3(0f, 0f, -0.045f);
                grip.localRotation = Quaternion.Euler(0f, 0f, -90f);
            }
            System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path));
            var saved = PrefabUtility.SaveAsPrefabAsset(root, path);
            Object.DestroyImmediate(root);
            Debug.Log("[UndeadLegion] created weapon prefab " + path);
            return saved;
        }

        /// <summary>Read a slot's local pose from the existing character prefab (null if absent).</summary>
        static Transform ExistingSlot(string c, string slotName)
        {
            var old = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(c));
            if (old == null) return null;
            foreach (var t in old.GetComponentsInChildren<Transform>(true)) if (t.name == slotName) return t;
            return null;
        }

        static bool Build(string c, AnimatorController controller)
        {
            // the hand slots are the user's to edit: carry their poses over from the current prefab
            var keep = new System.Collections.Generic.Dictionary<string, Transform>();
            foreach (var n in new[] { SkeletonWeapon.RightSlotName, SkeletonWeapon.LeftSlotName, SkeletonWeapon.ForearmSlotName })
            {
                var t = ExistingSlot(c, n);
                if (t != null) keep[n] = t;
            }
            string modelPath = UndeadLegionImportSetup.ModelPath(c);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (model == null) { Debug.LogWarning("[UndeadLegion] missing model " + modelPath); return false; }
            Avatar avatar = null;
            foreach (var a in AssetDatabase.LoadAllAssetsAtPath(modelPath))
                if (a is Avatar) avatar = (Avatar)a;

            var body = AssetDatabase.LoadAssetAtPath<Material>(UndeadLegionImportSetup.MaterialPath(c, "Body"));
            var armor = AssetDatabase.LoadAssetAtPath<Material>(UndeadLegionImportSetup.MaterialPath(c, "Armor"));

            var go = (GameObject)PrefabUtility.InstantiatePrefab(model);
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            go.name = "PF_" + c;
            go.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            go.transform.localScale = Vector3.one;

            foreach (var r in go.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                var m = r.name == "Body" ? body : armor;
                if (m == null) continue;
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++) mats[i] = m;
                r.sharedMaterials = mats;
                r.updateWhenOffscreen = true;
            }

            var an = go.GetComponent<Animator>();
            if (an == null) an = go.AddComponent<Animator>();
            an.avatar = avatar;
            an.runtimeAnimatorController = controller;
            an.applyRootMotion = true;
            an.cullingMode = AnimatorCullingMode.AlwaysAnimate;

            var col = go.GetComponent<CapsuleCollider>();
            if (col == null) col = go.AddComponent<CapsuleCollider>();
            col.center = new Vector3(0f, 0.9f, 0f);
            col.height = 1.8f;
            col.radius = 0.35f;

            // Ground the character on its LOWEST module, not on the bare foot: boot soles sit
            // 4-8 mm below the body's foot and read as sinking. The lift goes on the Armature
            // node, never on the prefab root (the validator wants the root at exactly 0/0/1).
            float minY = 9f;
            var bake = new Mesh();
            foreach (var r in go.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                r.BakeMesh(bake);
                var vs = bake.vertices;
                for (int i = 0; i < vs.Length; i++) minY = Mathf.Min(minY, r.transform.TransformPoint(vs[i]).y);
            }
            Object.DestroyImmediate(bake);
            var armature = go.transform.Find("Armature");
            // plus a clearance: Unity's humanoid retarget lets the feet dip ~5 mm below their
            // rest height through the idle (measured; Foot IK made it 9 mm), and a sole that
            // starts exactly on the floor then reads as sinking
            // A lift on the Armature node only works for the REST pose: while a Humanoid clip
            // plays, Unity places the hips from the avatar root and the child offset is all
            // but ignored (13.6 mm of lift moved the animated mesh 2 mm). Grounding therefore
            // lives in the clips (export_fbx.CLIP_LIFT). Reported here for the record.
            if (armature != null && minY < 9f)
            {
                armature.localPosition = Vector3.zero;
                Debug.Log(string.Format("[UndeadLegion] {0}: lowest rest vertex at {1:+0.0000;-0.0000} m (clips carry the clearance)", c, minY));
            }

            if (go.GetComponent<SkeletonModules>() == null) go.AddComponent<SkeletonModules>();
            if (go.GetComponent<SkeletonTwitch>() == null) go.AddComponent<SkeletonTwitch>();
            var weapon = go.GetComponent<SkeletonWeapon>();
            if (weapon == null) weapon = go.AddComponent<SkeletonWeapon>();
            weapon.loadouts = Loadouts();
            SampleGrip(go, weapon);
            weapon.EnsureSockets();            // creates the three slots at their defaults
            foreach (var kv in keep)
                foreach (var t in go.GetComponentsInChildren<Transform>(true))
                    if (t.name == kv.Key) { t.localPosition = kv.Value.localPosition; t.localRotation = kv.Value.localRotation; t.localScale = kv.Value.localScale; }
            Debug.Log("[UndeadLegion] " + c + ": hand slots " + (keep.Count > 0 ? "kept from the previous prefab (" + keep.Count + ")" : "created at defaults"));

            string path = PrefabPath(c);
            System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path));
            PrefabUtility.SaveAsPrefabAsset(go, path);
            Object.DestroyImmediate(go);
            return true;
        }
    }
}
