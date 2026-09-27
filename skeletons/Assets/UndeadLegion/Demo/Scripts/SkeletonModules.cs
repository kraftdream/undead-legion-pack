using System.Collections.Generic;
using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// The armour a skeleton wears, piece by piece, from module PREFABS (2026-09-27, the modular route).
    ///
    /// A character prefab is the bare body (`SK_&lt;Character&gt;.fbx`, Body only) dressed at build time with its
    /// default set (<see cref="defaultModules"/>: the `A_&lt;Character&gt;_&lt;Module&gt;` prefabs the prefab builder's
    /// armour map lists for it), each piece attached by <see cref="ArmorModule.Attach"/> and marked with an
    /// <see cref="ArmorPiece"/>. At runtime any module prefab of any character can be worn on top
    /// (<see cref="Wear"/>): the six characters share one rig and one bone hierarchy, so a piece binds to any of
    /// them by bone name. The pieces are SEPARATE RENDERERS on the character's bone array, deliberately not
    /// submeshes: a piece is a true on/off at zero skinning cost and pieces mix freely.
    ///
    /// `Body` is never in the list. It is always on: the modules are worn over it.
    /// </summary>
    [DisallowMultipleComponent]
    public class SkeletonModules : MonoBehaviour
    {
        [Tooltip("Renderer that is the bare skeleton and never toggles.")]
        public string bodyRendererName = "Body";

        [Tooltip("This character's default armour set (module prefabs), worn from the prefab; set by the prefab builder from its armour map.")]
        public List<GameObject> defaultModules = new List<GameObject>();

        [Tooltip("Default pieces that start off when the prefab is instantiated (optional).")]
        public List<string> offByDefault = new List<string>();

        class Entry
        {
            public GameObject prefab;
            public string name;
            public GameObject instance;
        }

        readonly List<Entry> _entries = new List<Entry>();
        Transform _parent;

        void Awake()
        {
            _entries.Clear();
            // the pieces already on the prefab (dressed at build time), by their source prefab / name
            var worn = new List<ArmorPiece>(GetComponentsInChildren<ArmorPiece>(true));
            foreach (var p in defaultModules)
            {
                if (p == null) continue;
                var e = new Entry { prefab = p, name = ModuleLabel(p) };
                foreach (var w in worn)
                    if (w.sourcePrefab == p || (w.sourcePrefab == null && w.moduleName == e.name)) { e.instance = w.gameObject; break; }
                _entries.Add(e);
            }
            foreach (var w in worn)                             // pieces on the prefab that are not in the default list
            {
                bool listed = false;
                foreach (var e in _entries) if (e.instance == w.gameObject) listed = true;
                if (!listed) _entries.Add(new Entry { prefab = w.sourcePrefab, name = w.moduleName, instance = w.gameObject });
            }
            foreach (var e in _entries)
                if (e.instance != null && offByDefault.Contains(e.name)) e.instance.SetActive(false);
        }

        Transform ModulesParent()
        {
            if (_parent == null)
            {
                var body = ArmorModule.FindBody(gameObject, bodyRendererName);
                _parent = body != null && body.transform.parent != null ? body.transform.parent : transform;
            }
            return _parent;
        }

        static string ModuleLabel(GameObject prefab)
        {
            var m = prefab.GetComponent<ArmorModule>();
            return m != null && !string.IsNullOrEmpty(m.moduleName) ? m.moduleName : prefab.name;
        }

        // ---- the default set: index-based, as the demo's toggles use it

        public int Count { get { return _entries.Count; } }

        public string NameAt(int i)
        {
            return (i >= 0 && i < _entries.Count) ? _entries[i].name : "?";
        }

        public bool IsWorn(int i)
        {
            return i >= 0 && i < _entries.Count && _entries[i].instance != null && _entries[i].instance.activeSelf;
        }

        public void Toggle(int i) { Set(i, !IsWorn(i)); }

        public void Set(int i, bool on)
        {
            if (i < 0 || i >= _entries.Count) return;
            var e = _entries[i];
            if (on)
            {
                if (e.instance == null && e.prefab != null) e.instance = ArmorModule.Wear(e.prefab, gameObject, ModulesParent());
                if (e.instance != null) e.instance.SetActive(true);
            }
            else if (e.instance != null) e.instance.SetActive(false);
        }

        public void SetAll(bool on)
        {
            for (int i = 0; i < _entries.Count; i++) Set(i, on);
        }

        // ---- any module prefab (another character's armour)

        /// <summary>Is this module prefab worn right now?</summary>
        public bool IsWearing(GameObject prefab)
        {
            foreach (var e in _entries) if (e.prefab == prefab) return e.instance != null && e.instance.activeSelf;
            return false;
        }

        /// <summary>Wear a module prefab (attached by bone name); a prefab already listed is switched on.</summary>
        public GameObject Wear(GameObject prefab)
        {
            if (prefab == null) return null;
            for (int i = 0; i < _entries.Count; i++)
                if (_entries[i].prefab == prefab) { Set(i, true); return _entries[i].instance; }
            var piece = ArmorModule.Wear(prefab, gameObject, ModulesParent());
            if (piece != null) _entries.Add(new Entry { prefab = prefab, name = ModuleLabel(prefab), instance = piece });
            return piece;
        }

        /// <summary>Take a module prefab off: a default piece is switched off (kept), a borrowed one destroyed.</summary>
        public void Remove(GameObject prefab)
        {
            for (int i = 0; i < _entries.Count; i++)
            {
                var e = _entries[i];
                if (e.prefab != prefab) continue;
                if (defaultModules.Contains(prefab)) { Set(i, false); return; }
                if (e.instance != null) { if (Application.isPlaying) Destroy(e.instance); else DestroyImmediate(e.instance); }
                _entries.RemoveAt(i);
                return;
            }
        }

        public void ToggleWear(GameObject prefab)
        {
            if (IsWearing(prefab)) Remove(prefab); else Wear(prefab);
        }
    }
}
