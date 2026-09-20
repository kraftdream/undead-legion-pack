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
            [Tooltip("The weapon's own material (M_Weapon_<Name>); empty = the placeholder")]
            public Material material;
        }

        [System.Serializable]
        public class Loadout
        {
            public string displayName;
            public List<Item> items = new List<Item>();
        }

        [System.Serializable]
        public class GripBone
        {
            public string bone;
            public Quaternion localRotation;
        }

        public List<Loadout> loadouts = new List<Loadout>();
        [Tooltip("Finger bone local rotations of the authored grip (sampled from Skeleton@Grip by the prefab builder); applied after the Animator to a hand that holds an item.")]
        public List<GripBone> gripLeft = new List<GripBone>();
        public List<GripBone> gripRight = new List<GripBone>();
        [Tooltip("Applied to a weapon renderer whose item has no material of its own (untextured meshes).")]
        public Material placeholderMaterial;
        // Shield socket on LeftForeArm: mid-forearm (+Y is the bone axis towards the hand) and
        // 3.5 cm out on the side away from the spine; the rotation maps the shield mesh's face
        // normal (+Z) to that outward direction and its top (+Y) towards the elbow. Measured on
        // the Knight 2026-09-20 (outward = (0.81, 0, -0.59) in forearm space).
        [Tooltip("Shield socket: offset from the LeftForeArm bone (bone-local metres, +Y along the bone towards the hand) and rotation.")]
        public Vector3 forearmSocketOffset = new Vector3(0.028f, 0.13f, -0.021f);
        public Vector3 forearmSocketEuler = new Vector3(0f, 126.1f, 180f);
        // Hand sockets sit at the palm centre (rig convention); with the grip pose the ring of
        // curled fingers is ~3 cm along the fingers and ~4 cm towards the palm side from there
        // (measured: finger-ring centroid in socket space), so the hilt moves into the fist.
        [Tooltip("Hand-held items: extra offset (socket-local metres) and rotation (degrees) applied on top of the socket bone, so the hilt sits inside the curled fingers rather than at the palm centre.")]
        public Vector3 rightHandOffset = new Vector3(-0.028f, 0.008f, -0.038f);
        public Vector3 rightHandEuler = Vector3.zero;
        public Vector3 leftHandOffset = new Vector3(0.038f, 0.010f, -0.037f);
        public Vector3 leftHandEuler = Vector3.zero;

        readonly List<GameObject> _spawned = new List<GameObject>();
        Transform _right, _left, _forearm;
        int _current = -1;
        readonly List<Transform> _gripLeftBones = new List<Transform>();
        readonly List<Transform> _gripRightBones = new List<Transform>();
        bool _holdLeft, _holdRight;

        /// <summary>Whether a hand currently holds an item (a forearm shield counts for the left hand).</summary>
        public bool HoldsLeft { get { return _holdLeft; } }
        public bool HoldsRight { get { return _holdRight; } }

        void ResolveGripBones()
        {
            _gripLeftBones.Clear(); _gripRightBones.Clear();
            var all = GetComponentsInChildren<Transform>(true);
            foreach (var g in gripLeft) _gripLeftBones.Add(System.Array.Find(all, t => t.name == g.bone));
            foreach (var g in gripRight) _gripRightBones.Add(System.Array.Find(all, t => t.name == g.bone));
        }

        /// <summary>Overrides the finger rotations of the holding hands with the authored grip.
        /// Runs in LateUpdate (after the Animator); edit-mode renders call it by hand.</summary>
        public void ApplyGrip()
        {
            if (_holdLeft && _gripLeftBones.Count == gripLeft.Count)
                for (int i = 0; i < gripLeft.Count; i++) if (_gripLeftBones[i] != null) _gripLeftBones[i].localRotation = gripLeft[i].localRotation;
            if (_holdRight && _gripRightBones.Count == gripRight.Count)
                for (int i = 0; i < gripRight.Count; i++) if (_gripRightBones[i] != null) _gripRightBones[i].localRotation = gripRight[i].localRotation;
        }

        void LateUpdate()
        {
            if (_holdLeft || _holdRight) ApplyGrip();
        }

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
            _holdLeft = _holdRight = false;
            if (index < 0 || index >= loadouts.Count) return;
            if (_gripLeftBones.Count != gripLeft.Count || _gripRightBones.Count != gripRight.Count) ResolveGripBones();
            foreach (var it in loadouts[index].items)
            {
                if (it.model == null) continue;
                if (it.hand == Hand.Right) _holdRight = true; else _holdLeft = true;
                var socket = it.hand == Hand.Right ? _right : it.hand == Hand.Left ? _left : _forearm;
                if (socket == null) { Debug.LogWarning("SkeletonWeapon: no socket for " + it.hand + " on " + name, this); continue; }
                var go = Instantiate(it.model, socket, false);
                go.name = it.model.name;
                go.transform.localPosition = it.hand == Hand.Right ? rightHandOffset : it.hand == Hand.Left ? leftHandOffset : Vector3.zero;
                go.transform.localRotation = it.hand == Hand.Right ? Quaternion.Euler(rightHandEuler) : it.hand == Hand.Left ? Quaternion.Euler(leftHandEuler) : Quaternion.identity;
                go.transform.localScale = Vector3.one;
                var use = it.material != null ? it.material : placeholderMaterial;
                if (use != null)
                    foreach (var r in go.GetComponentsInChildren<Renderer>())
                    {
                        var mats = r.sharedMaterials;
                        for (int i = 0; i < mats.Length; i++) mats[i] = use;
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
