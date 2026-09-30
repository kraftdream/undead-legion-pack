using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UndeadLegion.Demo;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// Adds the extended systems to the animation browser: a PHYSICS panel (cloth on/off, a physical hit, a ragdoll death,
    /// revive, rise and turn-to-dust) and clicking the character (click: a hit where you click; Shift + click: a ragdoll
    /// death pushed from there). The browser shows one character at a time, so its navigation and AI are removed on spawn
    /// and the browser drives the Animator as usual.
    /// </summary>
    public class ExtendedShowcase : MonoBehaviour
    {
        public SkeletonShowcase showcase;
        public float hitImpulse = 45f;
        public float deathImpulse = 120f;

        GameObject _char;
        SkeletonRagdoll _ragdoll;
        SkeletonHitReaction _hit;
        SkeletonCloth _cloth;
        SkeletonDissolve _dissolve;
        bool _clothOn = true;
        int _pieceCount = -1;
        Button _clothBtn;
        Text _status;
        Vector2 _down;
        bool _pressed;

        void Awake()
        {
            if (showcase == null) showcase = FindFirstObjectByType<SkeletonShowcase>();
            if (showcase != null) { showcase.CharacterSpawned += OnSpawned; showcase.ClipPlaying += OnClip; }
        }

        void OnDestroy()
        {
            if (showcase != null) { showcase.CharacterSpawned -= OnSpawned; showcase.ClipPlaying -= OnClip; }
        }

        void Start() { BuildUI(); }

        void OnSpawned(GameObject go)
        {
            _char = go;
            // one character on a browser stage: no NavMesh movement or combat AI (removed in dependency order)
            var ai = go.GetComponent<SkeletonAI>(); if (ai != null) DestroyImmediate(ai);
            var nav = go.GetComponent<SkeletonNavController>(); if (nav != null) DestroyImmediate(nav);
            var agent = go.GetComponent<UnityEngine.AI.NavMeshAgent>(); if (agent != null) DestroyImmediate(agent);
            _ragdoll = go.GetComponent<SkeletonRagdoll>();
            _hit = go.GetComponent<SkeletonHitReaction>();
            _cloth = go.GetComponent<SkeletonCloth>();
            _dissolve = go.GetComponent<SkeletonDissolve>();
            var health = go.GetComponent<SkeletonHealth>(); if (health != null) health.dissolveAfter = 0f;
            if (_cloth != null) _cloth.simulate = _clothOn;
            _pieceCount = -1;
            SetStatus("");
        }

        // any clip picked from the browser stands a fallen skeleton back up first
        void OnClip(AnimationClip clip) { if (_ragdoll != null && _ragdoll.IsRagdoll) _ragdoll.BlendToAnimation(); }

        // ------------------------------------------------------------------ actions

        Vector3 Chest()
        {
            var an = _char != null ? _char.GetComponent<Animator>() : null;
            var t = an != null && an.isHuman ? an.GetBoneTransform(HumanBodyBones.Chest) : null;
            return t != null ? t.position : _char.transform.position + Vector3.up * 1.3f;
        }

        Vector3 FromCamera(Vector3 at)
        {
            var cam = Camera.main; if (cam == null) return -_char.transform.forward;
            Vector3 d = at - cam.transform.position; d.y *= 0.3f; return d.normalized;
        }

        public void Hit(Vector3 point, Vector3 dir)
        {
            if (_char == null) return;
            if (_ragdoll != null && _ragdoll.IsRagdoll) { var rb = _ragdoll.Nearest(point); if (rb != null) rb.AddForceAtPosition(dir * hitImpulse, point, ForceMode.Impulse); return; }
            if (_hit != null) _hit.Hit(point, dir * hitImpulse);
            SetStatus("hit reaction over the clip");
        }

        public void RagdollDeath(Vector3 point, Vector3 dir)
        {
            if (_char == null || _ragdoll == null) return;
            if (_ragdoll.IsRagdoll) { Hit(point, dir); return; }
            _ragdoll.Activate(dir * deathImpulse, point);
            SetStatus("ragdoll: click pushes it, Revive stands it up");
        }

        public void Revive()
        {
            if (_ragdoll != null && _ragdoll.IsRagdoll) _ragdoll.BlendToAnimation();
            if (_dissolve != null) _dissolve.ResetVisuals();
            if (showcase != null) showcase.PlayByName("");
            SetStatus("");
        }

        void ToggleCloth()
        {
            _clothOn = !_clothOn;
            if (_cloth != null) { _cloth.SetSimulate(_clothOn); if (!_clothOn) _cloth.Refresh(); }
            Label(_clothBtn, "Cloth: " + (_clothOn ? "on" : "off"));
        }

        void Rise() { if (_dissolve == null) return; _dissolve.ResetVisuals(); _dissolve.DissolveIn(); }
        void Dust() { if (_dissolve != null) _dissolve.DissolveOut(false); SetStatus("dust: Rise brings it back"); }

        // ------------------------------------------------------------------ input

        void Update()
        {
            if (_char == null) return;
            // armour worn or removed in the modules panel: put cloth on the new pieces
            if (_cloth != null && _clothOn)
            {
                int n = _char.GetComponentsInChildren<ArmorPiece>(false).Length;
                if (n != _pieceCount) { _pieceCount = n; _cloth.Refresh(); }
            }
            if (ExtendedInput.ButtonDown(0)) { _pressed = !ExtendedInput.PointerOverUI; _down = ExtendedInput.MousePosition; }
            if (_pressed && !ExtendedInput.Button(0))
            {
                _pressed = false;
                if ((ExtendedInput.MousePosition - _down).magnitude < 6f) Click();
            }
        }

        void Click()
        {
            var cam = Camera.main; if (cam == null) return;
            var ray = cam.ScreenPointToRay(ExtendedInput.MousePosition);
            RaycastHit best = default(RaycastHit); bool found = false; float bd = float.MaxValue;
            foreach (var h in Physics.RaycastAll(ray, 100f, ~0, QueryTriggerInteraction.Ignore))
            {
                if (!h.collider.transform.IsChildOf(_char.transform)) continue;
                bool root = h.collider.gameObject == _char;                      // the root capsule: only when no body part is hit
                float d = h.distance + (root ? 50f : 0f);
                if (d < bd) { bd = d; best = h; found = true; }
            }
            if (!found) return;
            if (ExtendedInput.Key(KeyCode.LeftShift)) RagdollDeath(best.point, ray.direction);
            else Hit(best.point, ray.direction);
        }

        // ------------------------------------------------------------------ UI

        void BuildUI()
        {
            var canvasGo = new GameObject("PhysicsCanvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            var canvas = canvasGo.GetComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceOverlay; canvas.sortingOrder = 5;
            var scaler = canvasGo.GetComponent<CanvasScaler>(); scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f); scaler.matchWidthOrHeight = 0.5f;
            var go = new GameObject("PhysicsPanel", typeof(RectTransform), typeof(Image), typeof(VerticalLayoutGroup), typeof(ContentSizeFitter));
            var rt = (RectTransform)go.transform; rt.SetParent(canvasGo.transform, false);
            rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(1f, 0f);
            rt.anchoredPosition = new Vector2(-312f, 78f); rt.sizeDelta = new Vector2(240f, 0f);   // beside the animation list, above the footer
            go.GetComponent<Image>().color = new Color(0.10f, 0.11f, 0.13f, 0.92f);
            var v = go.GetComponent<VerticalLayoutGroup>(); v.padding = new RectOffset(8, 8, 8, 8); v.spacing = 4;
            v.childControlHeight = true; v.childControlWidth = true; v.childForceExpandHeight = false;
            go.GetComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            DemoUI.CreateSectionLabel(rt, "PHYSICS");
            _clothBtn = DemoUI.CreateListButton(rt, "Cloth: on", Dark()); _clothBtn.onClick.AddListener(ToggleCloth);
            DemoUI.CreateListButton(rt, "Hit (physics)", Dark()).onClick.AddListener(() => { if (_char != null) Hit(Chest(), FromCamera(Chest())); });
            DemoUI.CreateListButton(rt, "Ragdoll death", new Color(0.45f, 0.16f, 0.14f)).onClick.AddListener(() => { if (_char != null) RagdollDeath(Chest(), FromCamera(Chest())); });
            DemoUI.CreateListButton(rt, "Revive", Dark()).onClick.AddListener(Revive);
            DemoUI.CreateListButton(rt, "Rise from the ground", Dark()).onClick.AddListener(Rise);
            DemoUI.CreateListButton(rt, "Turn to dust", Dark()).onClick.AddListener(Dust);
            var help = DemoUI.CreateInfoRow(rt, "");
            help.text = "click: hit  |  shift + click: ragdoll";
            _status = DemoUI.CreateInfoRow(rt, "");
        }

        static Color Dark() { return new Color(0.2f, 0.21f, 0.24f); }
        static void Label(Button b, string s) { if (b != null) b.GetComponentInChildren<Text>().text = s; }
        void SetStatus(string s) { if (_status != null) _status.text = s; }
    }
}
