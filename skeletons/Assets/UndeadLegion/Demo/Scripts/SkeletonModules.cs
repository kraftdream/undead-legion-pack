using System.Collections.Generic;
using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// The armour modules a skeleton wears, each an independent on/off at runtime.
    ///
    /// Every character is one skeleton with several SkinnedMeshRenderers: `Body` plus one
    /// per armour piece (Helm, Chest, Glove_L, Boot_R, ...). They are SEPARATE RENDERERS
    /// on the same bone array, deliberately not submeshes: a submesh cannot be toggled
    /// and every instance would skin the hidden vertices anyway. `enabled = false` on a
    /// renderer is a true toggle at zero skinning cost, and it lets pieces be mixed.
    ///
    /// `Body` is never in the list. It is always on: the modules are worn over it.
    /// Modules are discovered at Awake, so a prefab needs no configuration; set
    /// <see cref="bodyRendererName"/> if a character's body renderer is named differently.
    /// </summary>
    [DisallowMultipleComponent]
    public class SkeletonModules : MonoBehaviour
    {
        [Tooltip("Renderer that is the bare skeleton and never toggles.")]
        public string bodyRendererName = "Body";

        [Tooltip("Renderer names that start off when the prefab is instantiated (optional).")]
        public List<string> offByDefault = new List<string>();

        readonly List<SkinnedMeshRenderer> _modules = new List<SkinnedMeshRenderer>();
        readonly List<bool> _worn = new List<bool>();

        void Awake()
        {
            _modules.Clear();
            _worn.Clear();
            var all = GetComponentsInChildren<SkinnedMeshRenderer>(true);
            System.Array.Sort(all, (a, b) => string.CompareOrdinal(a.name, b.name));
            foreach (var r in all)
            {
                if (r.name == bodyRendererName) { r.enabled = true; continue; }
                _modules.Add(r);
                _worn.Add(!offByDefault.Contains(r.name));
            }
            ApplyAll();
        }

        public int Count { get { return _modules.Count; } }

        public string NameAt(int i)
        {
            return (i >= 0 && i < _modules.Count) ? _modules[i].name : "?";
        }

        public bool IsWorn(int i)
        {
            return i >= 0 && i < _worn.Count && _worn[i];
        }

        public void Toggle(int i)
        {
            if (i < 0 || i >= _worn.Count) return;
            _worn[i] = !_worn[i];
            ApplyAll();
        }

        public void Set(int i, bool on)
        {
            if (i < 0 || i >= _worn.Count) return;
            _worn[i] = on;
            ApplyAll();
        }

        public void SetAll(bool on)
        {
            for (int i = 0; i < _worn.Count; i++) _worn[i] = on;
            ApplyAll();
        }

        void ApplyAll()
        {
            for (int i = 0; i < _modules.Count; i++)
                if (_modules[i] != null) _modules[i].enabled = _worn[i];
        }
    }
}
