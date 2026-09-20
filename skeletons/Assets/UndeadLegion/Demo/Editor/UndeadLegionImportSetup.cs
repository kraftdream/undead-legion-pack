using UnityEditor;
using UnityEngine;

namespace UndeadLegion.DemoEditor
{
    /// <summary>
    /// Applies the pack's import decisions (CLAUDE.md 4 and 7) to every character's
    /// textures and model, and creates the URP materials. Idempotent; re-run after adding
    /// a character or re-exporting textures.
    ///
    /// Textures per character: body/armor _color (sRGB), _normal (NormalMap),
    /// _metallicsmoothness (linear, R = metallic, A = smoothness; packed by
    /// tools/pack_textures.py). Materials: URP/Lit, _Metallic = _Smoothness = 1 so the
    /// packed map alone drives both.
    /// </summary>
    public static class UndeadLegionImportSetup
    {
        public const string Root = "Assets/UndeadLegion";
        public static readonly string[] Characters =
        {
            "SkeletonKnight", "SkeletonArcher", "SkeletonAssassin",
            "SkeletonMage", "SkeletonNecromancer", "SkeletonWarrior",
        };

        [MenuItem("Undead Legion/1. Import Setup (textures, models, materials)")]
        public static void Run()
        {
            foreach (var c in Characters)
            {
                foreach (var part in new[] { "body", "armor" })
                {
                    SetTexture(TexPath(c, part, "color"), TextureImporterType.Default, true, TextureImporterAlphaSource.None);
                    SetTexture(TexPath(c, part, "normal"), TextureImporterType.NormalMap, false, TextureImporterAlphaSource.None);
                    SetTexture(TexPath(c, part, "metallicsmoothness"), TextureImporterType.Default, false, TextureImporterAlphaSource.FromInput);
                }
                SetModel(ModelPath(c));
                foreach (var part in new[] { "Body", "Armor" })
                    EnsureMaterial(c, part);
            }
            // weapons: plain meshes at the pack scale, no rig, no materials of their own
            foreach (var guid in AssetDatabase.FindAssets("SM_ t:Model", new[] { Root + "/Models/Weapons" }))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var imp = AssetImporter.GetAtPath(path) as ModelImporter;
                if (imp == null) continue;
                if (imp.animationType != ModelImporterAnimationType.None || imp.materialImportMode != ModelImporterMaterialImportMode.None
                    || Mathf.Abs(imp.globalScale - 1f) > 1e-4f || imp.importAnimation)
                {
                    imp.animationType = ModelImporterAnimationType.None;
                    imp.importAnimation = false;
                    imp.materialImportMode = ModelImporterMaterialImportMode.None;
                    imp.globalScale = 1f;
                    imp.useFileScale = true;
                    imp.SaveAndReimport();
                }
            }
            string wp = Root + "/Materials/URP/M_Weapon_Placeholder.mat";
            if (AssetDatabase.LoadAssetAtPath<Material>(wp) == null)
            {
                var m = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                m.SetColor("_BaseColor", new Color(0.42f, 0.40f, 0.38f));
                m.SetFloat("_Metallic", 0.6f);
                m.SetFloat("_Smoothness", 0.45f);
                AssetDatabase.CreateAsset(m, wp);
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("[UndeadLegion] import setup done for " + Characters.Length + " characters");
        }

        public static string TexPath(string c, string part, string map)
        {
            return string.Format("{0}/Textures/{1}/{2}_{3}.png", Root, c, part, map);
        }

        public static string ModelPath(string c)
        {
            return string.Format("{0}/Models/{1}/SK_{1}.fbx", Root, c);
        }

        public static string MaterialPath(string c, string part)
        {
            return string.Format("{0}/Materials/URP/M_{1}_{2}.mat", Root, c, part);
        }

        static void SetTexture(string path, TextureImporterType type, bool srgb, TextureImporterAlphaSource alpha)
        {
            var imp = AssetImporter.GetAtPath(path) as TextureImporter;
            if (imp == null) { Debug.LogWarning("[UndeadLegion] missing texture " + path); return; }
            bool dirty = imp.textureType != type || imp.sRGBTexture != srgb || imp.alphaSource != alpha
                         || imp.alphaIsTransparency || imp.maxTextureSize != 2048;
            if (!dirty) return;
            imp.textureType = type;
            imp.sRGBTexture = srgb;
            imp.alphaSource = alpha;
            imp.alphaIsTransparency = false;
            imp.maxTextureSize = 2048;
            imp.SaveAndReimport();
        }

        static void SetModel(string path)
        {
            var imp = AssetImporter.GetAtPath(path) as ModelImporter;
            if (imp == null) { Debug.LogWarning("[UndeadLegion] missing model " + path); return; }
            bool dirty = imp.animationType != ModelImporterAnimationType.Human
                         || imp.materialImportMode != ModelImporterMaterialImportMode.None
                         || Mathf.Abs(imp.globalScale - 1f) > 1e-4f || imp.importAnimation;
            if (!dirty) return;
            imp.animationType = ModelImporterAnimationType.Human;
            imp.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            imp.globalScale = 1f;
            imp.useFileScale = true;
            imp.importAnimation = false;
            imp.materialImportMode = ModelImporterMaterialImportMode.None;
            imp.bakeAxisConversion = false;
            imp.SaveAndReimport();
        }

        static void EnsureMaterial(string c, string part)
        {
            string path = MaterialPath(c, part);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            bool created = false;
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                created = true;
            }
            string p = part.ToLowerInvariant();
            var color = AssetDatabase.LoadAssetAtPath<Texture2D>(TexPath(c, p, "color"));
            var normal = AssetDatabase.LoadAssetAtPath<Texture2D>(TexPath(c, p, "normal"));
            var ms = AssetDatabase.LoadAssetAtPath<Texture2D>(TexPath(c, p, "metallicsmoothness"));
            mat.SetTexture("_BaseMap", color);
            mat.SetTexture("_BumpMap", normal);
            mat.SetTexture("_MetallicGlossMap", ms);
            mat.SetFloat("_Metallic", 1f);
            mat.SetFloat("_Smoothness", 1f);
            mat.SetFloat("_BumpScale", 1f);
            // Armour is torn cloth, open hoods and hollow greaves: render both faces, or the
            // inside of a hood is a hole. Bones are closed volumes and stay single-sided.
            mat.SetFloat("_Cull", part == "Armor" ? 0f : 2f);
            mat.doubleSidedGI = part == "Armor";
            if (normal != null) mat.EnableKeyword("_NORMALMAP"); else mat.DisableKeyword("_NORMALMAP");
            if (ms != null) mat.EnableKeyword("_METALLICSPECGLOSSMAP"); else mat.DisableKeyword("_METALLICSPECGLOSSMAP");
            if (created)
            {
                System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path));
                AssetDatabase.CreateAsset(mat, path);
            }
            else EditorUtility.SetDirty(mat);
        }
    }
}
