using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UndeadLegion.Demo;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// The extended demo: two armies on a NavMesh arena. Raise them, start the battle, and take a skeleton over:
    /// left click selects (the selected skeleton follows orders instead of its AI), right click moves it or sends it at an
    /// enemy, Ctrl + click strikes any skeleton (hit reactions, ragdolls on corpses), Alt + click kills it outright.
    /// </summary>
    public class ExtendedDemo : MonoBehaviour
    {
        public ArmySpawner teamA;
        public ArmySpawner teamB;
        public RtsCamera rtsCamera;
        public float strikeDamage = 20f;
        public float strikeImpulse = 70f;
        public float killImpulse = 160f;

        SkeletonHealth _selected;
        GameObject _marker;
        bool _battle, _cloth = true, _dissolve = true;
        SkeletonHealth.DeathMode _deathMode = SkeletonHealth.DeathMode.Ragdoll;
        Text _status, _selInfo;
        Button _battleBtn, _clothBtn, _deathBtn, _dissolveBtn;
        Vector2 _rightDown;

        void Start()
        {
            BuildUI();
            _marker = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            _marker.name = "SelectionMarker"; Destroy(_marker.GetComponent<Collider>());
            _marker.transform.localScale = new Vector3(0.9f, 0.01f, 0.9f);
            var sh = Shader.Find("Universal Render Pipeline/Unlit");
            var mat = new Material(sh != null ? sh : Shader.Find("Unlit/Color")); mat.SetColor("_BaseColor", new Color(1f, 0.8f, 0.2f));
            _marker.GetComponent<Renderer>().sharedMaterial = mat;
            _marker.SetActive(false);
            Raise(8);
        }

        // ------------------------------------------------------------------ UI

        void BuildUI()
        {
            var canvasGo = new GameObject("ExtendedDemoCanvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            var canvas = canvasGo.GetComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = canvasGo.GetComponent<CanvasScaler>(); scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize; scaler.referenceResolution = new Vector2(1920, 1080); scaler.matchWidthOrHeight = 1f;
            var panel = Panel(canvasGo.transform, new Vector2(16, -16), new Vector2(280, 0));
            DemoUI.CreateSectionLabel(panel, "Armies");
            DemoUI.CreateListButton(panel, "Raise armies (8 v 8)", Dark()).onClick.AddListener(() => Raise(8));
            DemoUI.CreateListButton(panel, "Raise armies (16 v 16)", Dark()).onClick.AddListener(() => Raise(16));
            _battleBtn = DemoUI.CreateListButton(panel, "Start battle", new Color(0.45f, 0.16f, 0.14f)); _battleBtn.onClick.AddListener(ToggleBattle);
            DemoUI.CreateListButton(panel, "Clear", Dark()).onClick.AddListener(ClearAll);
            DemoUI.CreateSectionLabel(panel, "Options");
            _clothBtn = DemoUI.CreateListButton(panel, "", Dark()); _clothBtn.onClick.AddListener(ToggleCloth);
            _deathBtn = DemoUI.CreateListButton(panel, "", Dark()); _deathBtn.onClick.AddListener(CycleDeath);
            _dissolveBtn = DemoUI.CreateListButton(panel, "", Dark()); _dissolveBtn.onClick.AddListener(ToggleDissolve);
            DemoUI.CreateSectionLabel(panel, "Selected");
            _selInfo = DemoUI.CreateInfoRow(panel, "none");
            _status = DemoUI.CreateInfoRow(panel, "");
            var help = Panel(canvasGo.transform, new Vector2(16, 16), new Vector2(640, 0), true);
            var t = DemoUI.CreateInfoRow(help, "");
            t.text = "Left click select  |  Right click move / attack  |  Ctrl + click strike  |  Alt + click kill  |  WASD pan, right-drag rotate, wheel zoom";
            RefreshButtons();
        }

        static Color Dark() { return new Color(0.2f, 0.21f, 0.24f); }

        RectTransform Panel(Transform parent, Vector2 pos, Vector2 size, bool bottom = false)
        {
            var go = new GameObject("Panel", typeof(RectTransform), typeof(Image), typeof(VerticalLayoutGroup), typeof(ContentSizeFitter));
            var rt = (RectTransform)go.transform; rt.SetParent(parent, false);
            rt.anchorMin = rt.anchorMax = rt.pivot = bottom ? new Vector2(0, 0) : new Vector2(0, 1);
            rt.anchoredPosition = pos; rt.sizeDelta = size;
            go.GetComponent<Image>().color = new Color(0.08f, 0.09f, 0.11f, 0.85f);
            var v = go.GetComponent<VerticalLayoutGroup>(); v.padding = new RectOffset(8, 8, 8, 8); v.spacing = 4; v.childControlHeight = true; v.childControlWidth = true; v.childForceExpandHeight = false;
            go.GetComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            return rt;
        }

        void RefreshButtons()
        {
            Label(_battleBtn, _battle ? "Stop battle" : "Start battle");
            Label(_clothBtn, "Cloth: " + (_cloth ? "on" : "off"));
            Label(_deathBtn, "Deaths: " + (_deathMode == SkeletonHealth.DeathMode.Ragdoll ? "ragdoll" : _deathMode == SkeletonHealth.DeathMode.DeathClip ? "death clip" : "clip, then ragdoll"));
            Label(_dissolveBtn, "Dissolve corpses: " + (_dissolve ? "on" : "off"));
        }

        static void Label(Button b, string s) { if (b != null) b.GetComponentInChildren<Text>().text = s; }

        // ------------------------------------------------------------------ armies

        IEnumerable<SkeletonHealth> AllUnits()
        {
            foreach (var sp in new[] { teamA, teamB }) if (sp != null) foreach (var g in sp.spawned) if (g != null) { var h = g.GetComponent<SkeletonHealth>(); if (h != null) yield return h; }
        }

        void Raise(int perSide)
        {
            ClearAll();
            foreach (var sp in new[] { teamA, teamB })
            {
                if (sp == null) continue;
                sp.count = perSide; sp.columns = perSide > 8 ? 8 : 4; sp.enableAI = false;
                sp.Spawn();
            }
            ApplyOptions();
        }

        void ClearAll()
        {
            Select(null);
            _battle = false;
            if (teamA != null) teamA.Clear();
            if (teamB != null) teamB.Clear();
            RefreshButtons();
        }

        void ToggleBattle()
        {
            _battle = !_battle;
            foreach (var h in AllUnits())
            {
                if (h.IsDead) continue;
                var ai = h.GetComponent<SkeletonAI>(); if (ai == null) continue;
                bool possessed = h == _selected;
                ai.enabled = _battle && !possessed;
                if (!_battle) { ai.target = null; var nav = h.GetComponent<SkeletonNavController>(); if (nav != null) nav.Stop(); }
            }
            RefreshButtons();
        }

        void ToggleCloth() { _cloth = !_cloth; ApplyOptions(); RefreshButtons(); }
        void CycleDeath() { _deathMode = (SkeletonHealth.DeathMode)(((int)_deathMode + 1) % 3); ApplyOptions(); RefreshButtons(); }
        void ToggleDissolve() { _dissolve = !_dissolve; ApplyOptions(); RefreshButtons(); }

        void ApplyOptions()
        {
            foreach (var h in AllUnits())
            {
                h.deathMode = _deathMode; h.dissolveAfter = _dissolve ? 5f : 0f;
                var c = h.GetComponent<SkeletonCloth>(); if (c != null) c.SetSimulate(_cloth);
            }
        }

        // ------------------------------------------------------------------ input

        void Update()
        {
            if (_marker != null && _selected != null && !_selected.IsDead)
            {
                _marker.transform.position = _selected.transform.position + Vector3.up * 0.02f;
                _selInfo.text = _selected.name + "  |  team " + _selected.team + "  |  health " + Mathf.CeilToInt(_selected.health);
            }
            else if (_selected != null) Select(null);

            int alive0 = 0, alive1 = 0;
            foreach (var h in AllUnits()) if (!h.IsDead) { if (h.team == 0) alive0++; else alive1++; }
            if (_status != null) _status.text = "standing: " + alive0 + " v " + alive1;

            if (ExtendedInput.PointerOverUI) return;
            var cam = Camera.main; if (cam == null) return;
            if (ExtendedInput.ButtonDown(1)) _rightDown = ExtendedInput.MousePosition;
            bool rightClick = !ExtendedInput.Button(1) && _rightWasDown && (ExtendedInput.MousePosition - _rightDown).magnitude < 6f;
            _rightWasDown = ExtendedInput.Button(1);

            if (ExtendedInput.ButtonDown(0))
            {
                RaycastHit hit;
                if (!Physics.Raycast(cam.ScreenPointToRay(ExtendedInput.MousePosition), out hit, 200f, ~0, QueryTriggerInteraction.Ignore)) { Select(null); return; }
                var h = hit.collider.GetComponentInParent<SkeletonHealth>();
                Vector3 dir = cam.ScreenPointToRay(ExtendedInput.MousePosition).direction;
                if (ExtendedInput.Key(KeyCode.LeftControl)) { Strike(h, hit, dir, strikeDamage, strikeImpulse); return; }
                if (ExtendedInput.Key(KeyCode.LeftAlt)) { Strike(h, hit, dir, 10000f, killImpulse); return; }
                Select(h != null && !h.IsDead ? h : null);
            }
            if (rightClick && _selected != null)
            {
                RaycastHit hit;
                if (!Physics.Raycast(cam.ScreenPointToRay(ExtendedInput.MousePosition), out hit, 200f, ~0, QueryTriggerInteraction.Ignore)) return;
                var enemy = hit.collider.GetComponentInParent<SkeletonHealth>();
                var ai = _selected.GetComponent<SkeletonAI>();
                var nav = _selected.GetComponent<SkeletonNavController>();
                if (enemy != null && !enemy.IsDead && enemy.team != _selected.team && ai != null) { ai.target = enemy; ai.enabled = true; }
                else if (nav != null) { if (ai != null) { ai.enabled = false; ai.target = null; } nav.MoveTo(hit.point, ExtendedInput.Key(KeyCode.LeftShift)); }
            }
        }
        bool _rightWasDown;

        void Strike(SkeletonHealth h, RaycastHit hit, Vector3 dir, float damage, float impulse)
        {
            if (h == null)
            {
                if (hit.rigidbody != null && !hit.rigidbody.isKinematic) hit.rigidbody.AddForceAtPosition(dir * impulse, hit.point, ForceMode.Impulse);
                return;
            }
            if (h.IsDead)
            {
                var rd = h.GetComponent<SkeletonRagdoll>();
                if (rd != null && rd.IsRagdoll) { var rb = rd.Nearest(hit.point); if (rb != null) rb.AddForceAtPosition(dir * impulse, hit.point, ForceMode.Impulse); }
                return;
            }
            h.TakeDamage(damage, hit.point, dir * impulse, null);
        }

        void Select(SkeletonHealth h)
        {
            if (_selected != null && _selected != h)
            {
                var prevAi = _selected.GetComponent<SkeletonAI>(); if (prevAi != null && !_selected.IsDead) prevAi.enabled = _battle;
            }
            _selected = h;
            if (_marker != null) _marker.SetActive(h != null);
            if (h == null) { if (_selInfo != null) _selInfo.text = "none"; return; }
            var ai = h.GetComponent<SkeletonAI>(); if (ai != null) { ai.enabled = false; ai.target = null; }
            var nav = h.GetComponent<SkeletonNavController>(); if (nav != null) nav.Stop();
        }
    }
}
