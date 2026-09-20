using System.Collections.Generic;
using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// Hangs weapon meshes on the skeleton's socket bones at runtime.
    ///
    /// The sockets are bones of the shared skeleton (`RightWeaponSocket`,
    /// `LeftWeaponSocket`, children of the hands; CLAUDE.md 2): a weapon exported by
    /// tools/export_weapons.py has its grip at the origin and its length along +Y, so it
    /// attaches with an IDENTITY local transform. Shields go on the left forearm instead,
    /// on a socket this component creates under `LeftForeArm`.
    /// </summary>
    [DisallowMultipleComponent]
    public class SkeletonWeapon : MonoBehaviour
    {
        public enum Hand { Right, Left, LeftForearm }

        [System.Serializable]
        public class Item
        {
            public GameObject model;
            public Hand hand = Hand.Right;
        }

        [System.Serializable]
        public class Loadout
        {
            public string displayName;
            public List<Item> items = new List<Item>();
        }

        public List<Loadout> loadouts = new List<Loadout>();
        [Tooltip("Applied to every weapon renderer (the weapon meshes ship untextured).")]
        public Material placeholderMaterial;
        [Tooltip("Shield socket: offset from the LeftForeArm bone along the bone (metres) and rotation.")]
        public Vector3 forearmSocketOffset = new Vector3(0f, 0.13f, 0.03f);
        public Vector3 forearmSocketEuler = new Vector3(0f, 90f, 90f);

        readonly List<GameObject> _spawned = new List<GameObject>();
        Transform _right, _left, _forearm;
        int _current = -1;

        public int Count { get { return loadouts.Count; } }
        public int Current { get { return _current; } }
        public string NameAt(int i) { return (i >= 0 && i < loadouts.Count) ? loadouts[i].displayName : "?"; }

        void Awake()
        {
            EnsureSockets();
        }

        /// <summary>Resolve the socket transforms (also usable from editor tooling, where Awake does not run).</summary>
        public void EnsureSockets()
        {
            if (_right != null && _left != null) return;
            foreach (var t in GetComponentsInChildren<Transform>(true))
            {
                if (t.name == "RightWeaponSocket") _right = t;
                else if (t.name == "LeftWeaponSocket") _left = t;
                else if (t.name == "LeftForeArm") _forearm = t;
            }
            if (_forearm != null)
            {
                var s = new GameObject("LeftForeArmSocket").transform;
                s.SetParent(_forearm, false);
                s.localPosition = forearmSocketOffset;
                s.localRotation = Quaternion.Euler(forearmSocketEuler);
                _forearm = s;
            }
        }

        public void Equip(int index)
        {
            EnsureSockets();
            Clear();
            _current = index;
            if (index < 0 || index >= loadouts.Count) return;
            foreach (var it in loadouts[index].items)
            {
                if (it.model == null) continue;
                var socket = it.hand == Hand.Right ? _right : it.hand == Hand.Left ? _left : _forearm;
                if (socket == null) { Debug.LogWarning("SkeletonWeapon: no socket for " + it.hand + " on " + name, this); continue; }
                var go = Instantiate(it.model, socket, false);
                go.name = it.model.name;
                go.transform.localPosition = Vector3.zero;
                go.transform.localRotation = Quaternion.identity;
                go.transform.localScale = Vector3.one;
                if (placeholderMaterial != null)
                    foreach (var r in go.GetComponentsInChildren<Renderer>())
                    {
                        var mats = r.sharedMaterials;
                        for (int i = 0; i < mats.Length; i++) mats[i] = placeholderMaterial;
                        r.sharedMaterials = mats;
                    }
                _spawned.Add(go);
            }
        }

        public void Clear()
        {
            foreach (var go in _spawned)
                if (go != null) { if (Application.isPlaying) Destroy(go); else DestroyImmediate(go); }
            _spawned.Clear();
            _current = -1;
        }
    }
}
