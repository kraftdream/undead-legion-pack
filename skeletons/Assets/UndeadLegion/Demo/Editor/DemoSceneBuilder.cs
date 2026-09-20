using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using UndeadLegion.Demo;

namespace UndeadLegion.DemoEditor
{
    /// <summary>
    /// Rebuilds the demo scene from scratch. Kept in an Editor folder so it never ships in
    /// a player build. Re-run it after adding a character: the browser reads the character
    /// list from <see cref="UndeadLegionImportSetup.Characters"/> and the clip list from
    /// the controller at runtime, so nothing else needs touching.
    ///
    /// Lighting is the rig the creatures pack measured for a turntable demo: a 1.10 key,
    /// a 0.45 cool fill, a 0.30 rim and skybox ambient at 2.0. Two lights alone left the
    /// deep creases near black when the creature turned away; the rim kills the black
    /// and the ambient lift stops the key having to carry the whole image.
    /// </summary>
    public static class DemoSceneBuilder
    {
        const string Root = UndeadLegionImportSetup.Root;
        const string ScenePath = Root + "/Demo/Scenes/UndeadLegion_Demo.unity";
        const string GroundMatPath = Root + "/Materials/URP/M_Demo_Ground.mat";

        static readonly Color PanelBg = new Color(0.10f, 0.11f, 0.13f, 0.92f);
        static readonly Color BarBg = new Color(0.07f, 0.08f, 0.09f, 0.96f);
        static readonly Color HeaderText = new Color(0.85f, 0.86f, 0.90f);
        static readonly Color Accent = new Color(0.55f, 0.72f, 0.30f);

        [MenuItem("Undead Legion/3. Rebuild Demo Scene")]
        public static string Build()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // ---------------------------------------------------------- environment
            var key = MakeLight("Key Light", new Color(1f, 0.96f, 0.90f), 1.10f, LightShadows.Soft, new Vector3(45f, -35f, 0f));
            MakeLight("Fill Light", new Color(0.45f, 0.55f, 0.75f), 0.45f, LightShadows.None, new Vector3(20f, 150f, 0f));
            MakeLight("Rim Light", new Color(0.80f, 0.82f, 0.88f), 0.30f, LightShadows.None, new Vector3(30f, 60f, 0f));
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Skybox;
            RenderSettings.ambientIntensity = 2.0f;
            RenderSettings.sun = key;

            var groundMat = AssetDatabase.LoadAssetAtPath<Material>(GroundMatPath);
            if (groundMat == null)
            {
                groundMat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                groundMat.SetColor("_BaseColor", new Color(0.17f, 0.17f, 0.19f));
                groundMat.SetFloat("_Smoothness", 0.12f);
                AssetDatabase.CreateAsset(groundMat, GroundMatPath);
            }
            var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
            ground.name = "Ground";
            ground.transform.localScale = new Vector3(6f, 1f, 6f);   // 60 m
            ground.GetComponent<Renderer>().sharedMaterial = groundMat;

            var spawn = new GameObject("SpawnPoint");
            spawn.transform.position = Vector3.zero;

            // ---------------------------------------------------------------- camera
            var camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            var cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.Skybox;
            cam.fieldOfView = 45f;
            cam.nearClipPlane = 0.1f;
            cam.farClipPlane = 300f;
            camGo.AddComponent<AudioListener>();
            var turntable = camGo.AddComponent<DemoTurntable>();
            turntable.target = spawn.transform;

            // ------------------------------------------------------------ event system
            var esGo = new GameObject("EventSystem");
            esGo.AddComponent<EventSystem>();
            esGo.AddComponent<DemoEventSystemBootstrap>();

            // ------------------------------------------------------------------ canvas
            var canvasGo = new GameObject("DemoCanvas");
            var canvas = canvasGo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = canvasGo.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            scaler.matchWidthOrHeight = 0.5f;
            canvasGo.AddComponent<GraphicRaycaster>();
            var canvasRt = (RectTransform)canvasGo.transform;

            // header bar (top pivot: anchoredPosition y is the TOP edge)
            var header = Panel(canvasRt, "HeaderBar", BarBg);
            Stretch(header, new Vector2(0f, 1f), new Vector2(1f, 1f));
            header.sizeDelta = new Vector2(0f, 58f);
            header.anchoredPosition = Vector2.zero;
            var title = Label(header, "Title", "UNDEAD LEGION   Modular Skeleton Army     Animation Browser     |     drag to orbit, wheel to zoom", 18, HeaderText, TextAnchor.MiddleLeft);
            Stretch(title, Vector2.zero, Vector2.one);
            title.offsetMin = new Vector2(24f, 0f);
            title.offsetMax = new Vector2(-24f, 0f);
            var selectedName = Label(header, "SelectedName", "", 16, Accent, TextAnchor.MiddleRight);
            Stretch(selectedName, Vector2.zero, Vector2.one);
            selectedName.offsetMin = new Vector2(24f, 0f);
            selectedName.offsetMax = new Vector2(-24f, 0f);

            // character panel (top-left)
            var charPanel = Panel(canvasRt, "CharacterPanel", PanelBg);
            TopLeft(charPanel, new Vector2(20f, -74f), new Vector2(240f, 260f));
            SectionHeader(charPanel, "CHARACTERS");
            var charContent = ScrollList(charPanel);

            // module panel (left, under the characters)
            var modPanel = Panel(canvasRt, "ModulePanel", PanelBg);
            TopLeft(modPanel, new Vector2(20f, -346f), new Vector2(240f, 300f));
            var modHeader = SectionHeader(modPanel, "MODULES");
            var allBtn = TextButton(modPanel, "AllOn", "All", Accent);
            TopLeft((RectTransform)allBtn.transform, new Vector2(128f, -3f), new Vector2(48f, 22f));
            var noneBtn = TextButton(modPanel, "AllOff", "None", new Color(0.30f, 0.31f, 0.35f));
            TopLeft((RectTransform)noneBtn.transform, new Vector2(182f, -3f), new Vector2(48f, 22f));
            var modContent = ScrollList(modPanel);

            // weapon panel (left, under the modules): loadouts on the socket bones
            var wpnPanel = Panel(canvasRt, "WeaponPanel", PanelBg);
            TopLeft(wpnPanel, new Vector2(20f, -662f), new Vector2(240f, 330f));
            var wpnHeader = SectionHeader(wpnPanel, "WEAPONS");
            var wpnContent = ScrollList(wpnPanel);

            // clip panel (top-right)
            var clipPanel = Panel(canvasRt, "AnimationPanel", PanelBg);
            clipPanel.anchorMin = clipPanel.anchorMax = new Vector2(1f, 1f);
            clipPanel.pivot = new Vector2(1f, 1f);
            clipPanel.anchoredPosition = new Vector2(-20f, -74f);
            clipPanel.sizeDelta = new Vector2(280f, 672f);
            SectionHeader(clipPanel, "ANIMATIONS");
            var clipContent = ScrollList(clipPanel);

            // footer bar
            var footer = Panel(canvasRt, "FooterBar", BarBg);
            Stretch(footer, new Vector2(0f, 0f), new Vector2(1f, 0f));
            footer.sizeDelta = new Vector2(0f, 62f);
            footer.anchoredPosition = Vector2.zero;
            var info = Label(footer, "ClipInfo", "", 15, HeaderText, TextAnchor.MiddleLeft);
            Stretch(info, Vector2.zero, Vector2.one);
            info.offsetMin = new Vector2(24f, 0f);
            info.offsetMax = new Vector2(-700f, 0f);

            var rootToggle = Toggle(footer, "RootMotionToggle", "Root Motion", true);
            RightMid(rootToggle.Item1, -540f);
            var turnToggle = Toggle(footer, "TurntableToggle", "Turntable", true);
            RightMid(turnToggle.Item1, -390f);
            var recenter = TextButton(footer, "RecenterButton", "Recenter", Accent);
            RightMid((RectTransform)recenter.transform, -24f);
            ((RectTransform)recenter.transform).sizeDelta = new Vector2(120f, 34f);

            // -------------------------------------------------------------- showcase
            var showcaseGo = new GameObject("SkeletonShowcase");
            var showcase = showcaseGo.AddComponent<SkeletonShowcase>();
            showcase.spawnPoint = spawn.transform;
            showcase.characterListContent = charContent;
            showcase.clipListContent = clipContent;
            showcase.moduleListContent = modContent;
            showcase.moduleHeaderLabel = modHeader;
            showcase.weaponListContent = wpnContent;
            showcase.weaponHeaderLabel = wpnHeader;
            showcase.characterNameLabel = selectedName.GetComponent<Text>();
            showcase.clipInfoLabel = info.GetComponent<Text>();
            showcase.rootMotionToggle = rootToggle.Item2;
            showcase.turntableToggle = turnToggle.Item2;
            showcase.recenterButton = recenter;
            showcase.allModulesButton = allBtn;
            showcase.noModulesButton = noneBtn;
            showcase.turntable = turntable;
            showcase.characters = new List<SkeletonShowcase.Entry>();
            foreach (var c in UndeadLegionImportSetup.Characters)
            {
                var pf = AssetDatabase.LoadAssetAtPath<GameObject>(CharacterPrefabBuilder.PrefabPath(c));
                if (pf == null) continue;
                var e = new SkeletonShowcase.Entry();
                e.prefab = pf;
                e.displayName = c.Replace("Skeleton", "Skeleton ");
                showcase.characters.Add(e);
            }

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            Debug.Log("[UndeadLegion] demo scene rebuilt: " + ScenePath + " with " + showcase.characters.Count + " characters");
            return ScenePath;
        }

        [MenuItem("Undead Legion/Rebuild All (1-3)")]
        public static void RebuildAll()
        {
            UndeadLegionImportSetup.Run();
            CharacterPrefabBuilder.Run();
            Build();
        }

        // ------------------------------------------------------------------ helpers

        static Light MakeLight(string name, Color color, float intensity, LightShadows shadows, Vector3 euler)
        {
            var go = new GameObject(name);
            var l = go.AddComponent<Light>();
            l.type = LightType.Directional;
            l.color = color;
            l.intensity = intensity;
            l.shadows = shadows;
            go.transform.rotation = Quaternion.Euler(euler);
            return l;
        }

        static RectTransform Panel(RectTransform parent, string name, Color color)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image));
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            go.GetComponent<Image>().color = color;
            return rt;
        }

        static void Stretch(RectTransform rt, Vector2 anchorMin, Vector2 anchorMax)
        {
            rt.anchorMin = anchorMin;
            rt.anchorMax = anchorMax;
            rt.pivot = new Vector2(0.5f, (anchorMin.y + anchorMax.y) * 0.5f);
        }

        static void TopLeft(RectTransform rt, Vector2 pos, Vector2 size)
        {
            rt.anchorMin = rt.anchorMax = new Vector2(0f, 1f);
            rt.pivot = new Vector2(0f, 1f);
            rt.anchoredPosition = pos;
            rt.sizeDelta = size;
        }

        static void RightMid(RectTransform rt, float x)
        {
            rt.anchorMin = rt.anchorMax = new Vector2(1f, 0.5f);
            rt.pivot = new Vector2(1f, 0.5f);
            rt.anchoredPosition = new Vector2(x, 0f);
        }

        static RectTransform Label(RectTransform parent, string name, string text, int size, Color color, TextAnchor anchor)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Text));
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            var t = go.GetComponent<Text>();
            t.text = text;
            t.font = DemoUI.Font;
            t.fontSize = size;
            t.color = color;
            t.alignment = anchor;
            t.raycastTarget = false;
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            return rt;
        }

        static Text SectionHeader(RectTransform panel, string text)
        {
            var rt = Label(panel, "SectionHeader", text, 13, Accent, TextAnchor.MiddleLeft);
            rt.anchorMin = new Vector2(0f, 1f);
            rt.anchorMax = new Vector2(1f, 1f);
            rt.pivot = new Vector2(0.5f, 1f);
            rt.sizeDelta = new Vector2(0f, 28f);
            rt.anchoredPosition = Vector2.zero;
            rt.offsetMin = new Vector2(12f, rt.offsetMin.y);
            rt.offsetMax = new Vector2(-12f, rt.offsetMax.y);
            return rt.GetComponent<Text>();
        }

        static RectTransform ScrollList(RectTransform panel)
        {
            var scrollGo = new GameObject("ScrollView", typeof(RectTransform), typeof(ScrollRect));
            var scrollRt = (RectTransform)scrollGo.transform;
            scrollRt.SetParent(panel, false);
            scrollRt.anchorMin = Vector2.zero;
            scrollRt.anchorMax = Vector2.one;
            scrollRt.offsetMin = new Vector2(8f, 8f);
            scrollRt.offsetMax = new Vector2(-8f, -30f);

            var viewportGo = new GameObject("Viewport", typeof(RectTransform), typeof(Image), typeof(RectMask2D));
            var viewportRt = (RectTransform)viewportGo.transform;
            viewportRt.SetParent(scrollRt, false);
            viewportRt.anchorMin = Vector2.zero;
            viewportRt.anchorMax = Vector2.one;
            viewportRt.offsetMin = Vector2.zero;
            viewportRt.offsetMax = Vector2.zero;
            viewportRt.pivot = new Vector2(0f, 1f);
            viewportGo.GetComponent<Image>().color = new Color(0f, 0f, 0f, 0.15f);

            var contentGo = new GameObject("Content", typeof(RectTransform));
            var contentRt = (RectTransform)contentGo.transform;
            contentRt.SetParent(viewportRt, false);
            contentRt.anchorMin = new Vector2(0f, 1f);
            contentRt.anchorMax = new Vector2(1f, 1f);
            contentRt.pivot = new Vector2(0.5f, 1f);
            contentRt.sizeDelta = Vector2.zero;

            var vlg = contentGo.AddComponent<VerticalLayoutGroup>();
            vlg.spacing = 4f;
            vlg.padding = new RectOffset(4, 4, 4, 4);
            vlg.childForceExpandHeight = false;
            vlg.childForceExpandWidth = true;
            vlg.childControlHeight = true;
            vlg.childControlWidth = true;
            var fitter = contentGo.AddComponent<ContentSizeFitter>();
            fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

            var sr = scrollGo.GetComponent<ScrollRect>();
            sr.content = contentRt;
            sr.viewport = viewportRt;
            sr.horizontal = false;
            sr.vertical = true;
            sr.movementType = ScrollRect.MovementType.Clamped;
            sr.scrollSensitivity = 20f;
            return contentRt;
        }

        static Button TextButton(RectTransform parent, string name, string label, Color color)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image), typeof(Button));
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            var img = go.GetComponent<Image>();
            img.color = color;
            var t = Label(rt, "Label", label, 14, Color.white, TextAnchor.MiddleCenter);
            t.anchorMin = Vector2.zero;
            t.anchorMax = Vector2.one;
            t.offsetMin = Vector2.zero;
            t.offsetMax = Vector2.zero;
            var b = go.GetComponent<Button>();
            b.targetGraphic = img;
            return b;
        }

        static System.Tuple<RectTransform, UnityEngine.UI.Toggle> Toggle(RectTransform parent, string name, string label, bool on)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(UnityEngine.UI.Toggle));
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.sizeDelta = new Vector2(150f, 30f);

            var bg = new GameObject("Background", typeof(RectTransform), typeof(Image));
            var bgRt = (RectTransform)bg.transform;
            bgRt.SetParent(rt, false);
            bgRt.anchorMin = bgRt.anchorMax = new Vector2(0f, 0.5f);
            bgRt.pivot = new Vector2(0f, 0.5f);
            bgRt.sizeDelta = new Vector2(20f, 20f);
            bgRt.anchoredPosition = Vector2.zero;
            bg.GetComponent<Image>().color = new Color(0.22f, 0.23f, 0.26f);

            var check = new GameObject("Checkmark", typeof(RectTransform), typeof(Image));
            var checkRt = (RectTransform)check.transform;
            checkRt.SetParent(bgRt, false);
            checkRt.anchorMin = Vector2.zero;
            checkRt.anchorMax = Vector2.one;
            checkRt.offsetMin = new Vector2(4f, 4f);
            checkRt.offsetMax = new Vector2(-4f, -4f);
            check.GetComponent<Image>().color = Accent;

            var lbl = Label(rt, "Label", label, 14, HeaderText, TextAnchor.MiddleLeft);
            lbl.anchorMin = Vector2.zero;
            lbl.anchorMax = Vector2.one;
            lbl.offsetMin = new Vector2(28f, 0f);
            lbl.offsetMax = Vector2.zero;

            var tg = go.GetComponent<UnityEngine.UI.Toggle>();
            tg.targetGraphic = bg.GetComponent<Image>();
            tg.graphic = check.GetComponent<Image>();
            tg.isOn = on;
            return new System.Tuple<RectTransform, UnityEngine.UI.Toggle>(rt, tg);
        }
    }
}
