using UnityEngine;
using UnityEngine.UI;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// Builds the demo's list rows in code. The list contents are dynamic (one row per
    /// character, one per clip, one per armour module), so there is nothing useful to
    /// author by hand in the scene: the panels, scroll views and labels are real scene
    /// objects you can restyle, only the rows are generated.
    ///
    /// Legacy uGUI Text on purpose: TextMeshPro needs its "Essential Resources" imported
    /// before it renders, and prompting a buyer to import extra packages on first open of
    /// a demo scene is a bad first impression.
    /// </summary>
    public static class DemoUI
    {
        static Font _font;

        /// <summary>Unity's built-in font. Avoids shipping a font asset or needing TMP.</summary>
        public static Font Font
        {
            get
            {
                if (_font == null) _font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
                return _font;
            }
        }

        public static Button CreateListButton(RectTransform parent, string label, Color color)
        {
            var go = new GameObject(label, typeof(RectTransform), typeof(Image), typeof(Button));
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);

            var img = go.GetComponent<Image>();
            img.color = color;

            var le = go.AddComponent<LayoutElement>();
            le.minHeight = 30f;
            le.preferredHeight = 30f;

            var textGo = new GameObject("Label", typeof(RectTransform), typeof(Text));
            var trt = (RectTransform)textGo.transform;
            trt.SetParent(rt, false);
            trt.anchorMin = Vector2.zero;
            trt.anchorMax = Vector2.one;
            trt.offsetMin = new Vector2(10f, 0f);
            trt.offsetMax = new Vector2(-10f, 0f);

            var text = textGo.GetComponent<Text>();
            text.text = label;
            text.font = Font;
            text.fontSize = 14;
            text.color = Color.white;
            text.alignment = TextAnchor.MiddleLeft;
            text.raycastTarget = false;

            var btn = go.GetComponent<Button>();
            btn.targetGraphic = img;
            return btn;
        }

        /// <summary>Non-interactive section header row for a list.</summary>
        public static void CreateSectionLabel(RectTransform parent, string title)
        {
            var go = new GameObject("Section_" + title, typeof(RectTransform), typeof(Text));
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);

            var le = go.AddComponent<LayoutElement>();
            le.minHeight = 22f;
            le.preferredHeight = 22f;

            var text = go.GetComponent<Text>();
            text.text = title.ToUpperInvariant();
            text.font = Font;
            text.fontSize = 11;
            text.fontStyle = FontStyle.Bold;
            text.color = new Color(0.62f, 0.64f, 0.68f, 1f);
            text.alignment = TextAnchor.LowerLeft;
            text.raycastTarget = false;
        }

        /// <summary>Non-interactive informational row. Slimmer and darker than a button.</summary>
        public static Text CreateInfoRow(RectTransform parent, string label)
        {
            var go = new GameObject("Info_" + label, typeof(RectTransform), typeof(Image));
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            go.GetComponent<Image>().color = new Color(0.14f, 0.14f, 0.16f, 1f);

            var le = go.AddComponent<LayoutElement>();
            le.minHeight = 20f;
            le.preferredHeight = 20f;

            var textGo = new GameObject("Label", typeof(RectTransform), typeof(Text));
            var trt = (RectTransform)textGo.transform;
            trt.SetParent(rt, false);
            trt.anchorMin = Vector2.zero;
            trt.anchorMax = Vector2.one;
            trt.offsetMin = new Vector2(24f, 0f);
            trt.offsetMax = new Vector2(-10f, 0f);

            var text = textGo.GetComponent<Text>();
            text.text = label;
            text.font = Font;
            text.fontSize = 12;
            text.fontStyle = FontStyle.Italic;
            text.color = new Color(0.62f, 0.64f, 0.68f, 1f);
            text.alignment = TextAnchor.MiddleLeft;
            text.raycastTarget = false;
            return text;
        }
    }
}
