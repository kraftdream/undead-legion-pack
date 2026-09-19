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

        static bool Build(string c, AnimatorController controller)
        {
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

            if (go.GetComponent<SkeletonModules>() == null) go.AddComponent<SkeletonModules>();
            if (go.GetComponent<SkeletonTwitch>() == null) go.AddComponent<SkeletonTwitch>();

            string path = PrefabPath(c);
            System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path));
            PrefabUtility.SaveAsPrefabAsset(go, path);
            Object.DestroyImmediate(go);
            return true;
        }
    }
}
