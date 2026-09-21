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
            // textured weapons (Weapons/prod.blend, 2026-09-20): Textures/Weapons/<Name>_{color,normal,metallicsmoothness}.png
            // packed by tools/pack_textures.py -> M_Weapon_<Name>.mat; SkeletonWeapon uses it when the loadout names it
            foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { Root + "/Textures/Weapons" }))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var file = System.IO.Path.GetFileNameWithoutExtension(path);
                if (file.EndsWith("_color")) SetTexture(path, TextureImporterType.Default, true, TextureImporterAlphaSource.None);
                else if (file.EndsWith("_normal")) SetTexture(path, TextureImporterType.NormalMap, false, TextureImporterAlphaSource.None);
                else if (file.EndsWith("_metallicsmoothness")) SetTexture(path, TextureImporterType.Default, false, TextureImporterAlphaSource.FromInput);
            }
            foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { Root + "/Textures/Weapons" }))
            {
                var file = System.IO.Path.GetFileNameWithoutExtension(AssetDatabase.GUIDToAssetPath(guid));
                if (!file.EndsWith("_color")) continue;
                string wname = file.Substring(0, file.Length - "_color".Length);
                EnsureLitMaterial(Root + "/Materials/URP/M_Weapon_" + wname + ".mat",
                    Root + "/Textures/Weapons/" + wname + "_color.png", Root + "/Textures/Weapons/" + wname + "_normal.png",
                    Root + "/Textures/Weapons/" + wname + "_metallicsmoothness.png", false);
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
            string p = part.ToLowerInvariant();
            // Armour is torn cloth, open hoods and hollow greaves: render both faces, or the
            // inside of a hood is a hole. Bones are closed volumes and stay single-sided.
            EnsureLitMaterial(MaterialPath(c, part), TexPath(c, p, "color"), TexPath(c, p, "normal"), TexPath(c, p, "metallicsmoothness"), part == "Armor");
        }

        /// <summary>URP/Lit material driven by the pack's colour, normal and packed metallic/smoothness maps.</summary>
        static void EnsureLitMaterial(string path, string colorPath, string normalPath, string msPath, bool doubleSided)
        {
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            bool created = false;
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                created = true;
            }
            var color = AssetDatabase.LoadAssetAtPath<Texture2D>(colorPath);
            var normal = AssetDatabase.LoadAssetAtPath<Texture2D>(normalPath);
            var ms = AssetDatabase.LoadAssetAtPath<Texture2D>(msPath);
            mat.SetTexture("_BaseMap", color);
            mat.SetTexture("_BumpMap", normal);
            mat.SetTexture("_MetallicGlossMap", ms);
            // with a packed map the map drives both; without one (staff, bow, wand, arrow: colour + normal
            // only) 1/1 would be a mirror-smooth metal, so plain wood/cloth values instead
            mat.SetFloat("_Metallic", ms != null ? 1f : 0f);
            mat.SetFloat("_Smoothness", ms != null ? 1f : 0.35f);
            mat.SetFloat("_BumpScale", 1f);
            mat.SetFloat("_Cull", doubleSided ? 0f : 2f);
            mat.doubleSidedGI = doubleSided;
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
