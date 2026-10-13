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

        [MenuItem("Undead Legion/2a. Rebuild Armour Module Prefabs")]
        public static void RebuildModulePrefabs()
        {
            int n = BuildModulePrefabs();
            AssetDatabase.SaveAssets();
            Debug.Log("[UndeadLegion] " + n + " armour module prefabs rebuilt");
        }

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
            new object[] { "Recurve bow", "SM_H2Recurvebow", SkeletonWeapon.Hand.Left, "SM_Arrow", SkeletonWeapon.Hand.Right },
            new object[] { "Staff", "SM_H2MagicStuff", SkeletonWeapon.Hand.Right },
            // ("Staff (propped)" / SM_H2MagicStuff@Top, the top-gripped staff for Idle_Propped, removed 2026-09-25 with that clip;
            // the "@Variant" suffix still makes a second prefab of a model with its own Grip if one is needed again)
            new object[] { "Wand", "SM_H1Wand", SkeletonWeapon.Hand.Right },
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

        // The eye sockets differ per skull (the Knight / Archer socket floor sits 13 mm deeper than the other four), so each
        // character's eyes are seated on its own socket: the floor is the deepest body-mesh point in a 5 mm disc round the socket
        // centre (x 30 mm, y 23 mm from the Head bone), measured on the bind pose; the sphere's back rests on it.
        static Vector3 MeasureEyes(GameObject go, Vector3 fallback, float size)
        {
            var an = go.GetComponent<Animator>(); var head = an != null ? an.GetBoneTransform(HumanBodyBones.Head) : null;
            SkinnedMeshRenderer body = null; foreach (var r in go.GetComponentsInChildren<SkinnedMeshRenderer>()) if (r.name.EndsWith("Body")) body = r;
            if (head == null || body == null) return fallback;
            var mesh = new Mesh(); body.BakeMesh(mesh, true);
            var cgo = new GameObject("eye_probe"); cgo.transform.SetPositionAndRotation(body.transform.position, body.transform.rotation);
            var mc = cgo.AddComponent<MeshCollider>(); mc.sharedMesh = mesh;
            Vector3 fwd = go.transform.forward, right = go.transform.right, up = go.transform.up;
            float floor = float.MaxValue;
            for (int i = -2; i <= 2; i++) for (int j = -2; j <= 2; j++)
            {
                if (i * i + j * j > 5) continue;
                Vector3 o = head.position + right * (0.030f + i * 0.0025f) + up * (0.023f + j * 0.0025f) + fwd * 0.4f; RaycastHit h;
                if (mc.Raycast(new Ray(o, -fwd), out h, 1f)) floor = Mathf.Min(floor, Vector3.Dot(h.point - head.position, fwd));
            }
            Object.DestroyImmediate(cgo); Object.DestroyImmediate(mesh);
            if (floor == float.MaxValue) return fallback;
            return new Vector3(0.030f, 0.023f, floor + size * 0.5f);
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
            string variant = null;
            int at = sm.IndexOf('@');
            if (at >= 0) { variant = sm.Substring(at + 1); sm = sm.Substring(0, at); }
            string name = (sm.StartsWith("SM_") ? sm.Substring(3) : sm) + (variant != null ? "_" + variant : "");
            string path = string.Format("{0}/Prefabs/Weapons/W_{1}.prefab", Root, name);
            var existing = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(string.Format("{0}/Materials/URP/M_Weapon_{1}.mat", Root, sm.StartsWith("SM_") ? sm.Substring(3) : sm));
            var placeholder = AssetDatabase.LoadAssetAtPath<Material>(Root + "/Materials/URP/M_Weapon_Placeholder.mat");
            if (existing != null)
            {
                // kept as is (an edited Grip survives), except that a weapon which has gained its
                // textures since the prefab was made swaps the placeholder for its own material
                if (mat != null)
                {
                    bool changed = false;
                    var contents = PrefabUtility.LoadPrefabContents(path);
                    foreach (var r in contents.GetComponentsInChildren<Renderer>())
                    {
                        var mats = r.sharedMaterials;
                        for (int i = 0; i < mats.Length; i++) if (mats[i] == null || mats[i] == placeholder) { mats[i] = mat; changed = true; }
                        r.sharedMaterials = mats;
                    }
                    if (changed) { PrefabUtility.SaveAsPrefabAsset(contents, path); Debug.Log("[UndeadLegion] weapon prefab " + path + ": placeholder -> " + mat.name); }
                    PrefabUtility.UnloadPrefabContents(contents);
                }
                return AssetDatabase.LoadAssetAtPath<GameObject>(path);
            }
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(string.Format("{0}/Models/Weapons/{1}.fbx", Root, sm));
            if (model == null) return null;
            if (mat == null) mat = placeholder;
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
            if (name == "Arrow")
            {
                // held between the fingers of the string hand: the shaft (weapon +Y, head at +Y) runs
                // along the fingers, which is the slot's -X in Unity (Blender's socket +X; the FBX
                // import flips the handedness of that axis), so it points at the bow at full draw and
                // hangs down the leg when the hand hangs (Shoot_01/02 aim the string hand's fingers at
                // the bow; measured: the shot line reads (-1, 0, 0) in the slot frame at full draw)
                grip.localRotation = Quaternion.Euler(0f, 0f, 90f);
                grip.localPosition = new Vector3(0f, 0.8352f, 0f);
                mesh.transform.localScale = Vector3.one; // Arrow shaft extension is authored in the mesh; head and feathers keep their size.
            }
            else if (name.Contains("Shield"))
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

        /// <summary>The armour MAP (2026-09-27, the modular route): which module prefabs each skeleton wears by
        /// default. Each character's own set, in the order the demo lists them; any character's piece fits any
        /// skeleton (one shared rig), so a set may borrow across characters here.</summary>
        public static readonly System.Collections.Generic.Dictionary<string, string[]> ArmorMap =
            new System.Collections.Generic.Dictionary<string, string[]>
            {
                { "SkeletonKnight",      new[] { "SkeletonKnight:Helm", "SkeletonKnight:Chest", "SkeletonKnight:Skirt", "SkeletonKnight:Glove_L", "SkeletonKnight:Glove_R", "SkeletonKnight:Greave_L", "SkeletonKnight:Greave_R", "SkeletonKnight:Boot_L", "SkeletonKnight:Boot_R" } },
                { "SkeletonArcher",      new[] { "SkeletonArcher:Helm", "SkeletonArcher:Chest", "SkeletonArcher:Skirt", "SkeletonArcher:Glove_L", "SkeletonArcher:Glove_R", "SkeletonArcher:Boot_L", "SkeletonArcher:Boot_R" } },
                { "SkeletonAssassin",    new[] { "SkeletonAssassin:Helm", "SkeletonAssassin:Chest", "SkeletonAssassin:Skirt", "SkeletonAssassin:Pants", "SkeletonAssassin:Glove_L", "SkeletonAssassin:Glove_R", "SkeletonAssassin:Boot_L", "SkeletonAssassin:Boot_R" } },
                { "SkeletonMage",        new[] { "SkeletonMage:Helm", "SkeletonMage:Robe", "SkeletonMage:Glove_L", "SkeletonMage:Glove_R", "SkeletonMage:Greave_L", "SkeletonMage:Greave_R", "SkeletonMage:Boot_L", "SkeletonMage:Boot_R" } },
                { "SkeletonNecromancer", new[] { "SkeletonNecromancer:Helm", "SkeletonNecromancer:Robe", "SkeletonNecromancer:Glove_L", "SkeletonNecromancer:Glove_R", "SkeletonNecromancer:Greave_L", "SkeletonNecromancer:Greave_R", "SkeletonNecromancer:Boot_L", "SkeletonNecromancer:Boot_R" } },
                { "SkeletonWarrior",     new[] { "SkeletonWarrior:Chest", "SkeletonWarrior:Skirt", "SkeletonWarrior:Glove_L", "SkeletonWarrior:Glove_R", "SkeletonWarrior:Greave_L", "SkeletonWarrior:Greave_R", "SkeletonWarrior:Boot_L", "SkeletonWarrior:Boot_R" } },
            };

        public static string ModulePrefabPath(string c, string module)
        {
            return string.Format("{0}/Prefabs/Armor/{1}/A_{1}_{2}.prefab", Root, c, module);
        }

        /// <summary>`Prefabs/Armor/&lt;Character&gt;/A_&lt;Character&gt;_&lt;Module&gt;.prefab`: the module model with the
        /// character's armour material and an ArmorModule. Regenerated on every build (nothing hand-tuned lives
        /// here; the hand slots and weapon Grips are the tuned things, and they live elsewhere).</summary>
        static GameObject BuildModulePrefab(string c, string modelPath)
        {
            string module = UndeadLegionImportSetup.ModuleName(modelPath, c);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (model == null) { Debug.LogWarning("[UndeadLegion] missing module model " + modelPath); return null; }
            var armor = AssetDatabase.LoadAssetAtPath<Material>(UndeadLegionImportSetup.MaterialPath(c, "Armor"));
            var go = (GameObject)PrefabUtility.InstantiatePrefab(model);
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            go.name = "A_" + c + "_" + module;
            go.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            go.transform.localScale = Vector3.one;
            foreach (var r in go.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (armor != null) { var mats = r.sharedMaterials; for (int i = 0; i < mats.Length; i++) mats[i] = armor; r.sharedMaterials = mats; }
                r.updateWhenOffscreen = true;
            }
            foreach (var a in go.GetComponentsInChildren<Animator>(true)) Object.DestroyImmediate(a);
            var mod = go.AddComponent<ArmorModule>();
            mod.character = c; mod.moduleName = module;
            string path = ModulePrefabPath(c, module);
            System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path));
            var saved = PrefabUtility.SaveAsPrefabAsset(go, path);
            Object.DestroyImmediate(go);
            return saved;
        }

        /// <summary>Every character's module prefabs, rebuilt from the module models.</summary>
        public static int BuildModulePrefabs()
        {
            int n = 0;
            foreach (var c in UndeadLegionImportSetup.Characters)
                foreach (var mp in UndeadLegionImportSetup.ModulePaths(c))
                    if (BuildModulePrefab(c, mp) != null) n++;
            return n;
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

            // dress the body with its default set from the armour map: each module prefab attached by bone name
            // (ArmorModule.Wear), the pieces plain children of the Armature's parent, marked with their source prefab
            var modules = go.GetComponent<SkeletonModules>();
            if (modules == null) modules = go.AddComponent<SkeletonModules>();
            modules.defaultModules = new System.Collections.Generic.List<GameObject>();
            string[] set;
            if (ArmorMap.TryGetValue(c, out set))
                foreach (var entry in set)
                {
                    var parts = entry.Split(':');
                    var mp = AssetDatabase.LoadAssetAtPath<GameObject>(ModulePrefabPath(parts[0], parts[1]));
                    if (mp == null) { Debug.LogWarning("[UndeadLegion] " + c + ": missing module prefab " + entry); continue; }
                    var piece = ArmorModule.Wear(mp, go, null);
                    if (piece == null) { Debug.LogWarning("[UndeadLegion] " + c + ": could not attach " + entry); continue; }
                    modules.defaultModules.Add(mp);
                }
            Debug.Log("[UndeadLegion] " + c + ": dressed with " + modules.defaultModules.Count + " modules from the armour map");

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

            if (go.GetComponent<SkeletonTwitch>() == null) go.AddComponent<SkeletonTwitch>();
            if (go.GetComponent<SkeletonFootLock>() == null) go.AddComponent<SkeletonFootLock>();   // the feet held on looping idles (2026-09-28)
            var eyes = go.GetComponent<SkeletonEyes>(); if (eyes == null) eyes = go.AddComponent<SkeletonEyes>();
            eyes.offset = MeasureEyes(go, eyes.offset, eyes.size);   // seated on this skull's own socket floor
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
