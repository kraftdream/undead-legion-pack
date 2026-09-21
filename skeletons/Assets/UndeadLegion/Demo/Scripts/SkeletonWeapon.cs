using System.Collections.Generic;
using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// Hangs weapon prefabs on the skeleton's hand slots at runtime.
    ///
    /// Two editable transforms meet: a SLOT on the character (`RightHandSlot` under the
    /// `RightWeaponSocket` bone, `LeftHandSlot` under `LeftWeaponSocket`, `LeftForearmSlot`
    /// under `LeftForeArm`; saved in the character prefab, move/rotate them there) and a
    /// `Grip` child in every weapon prefab (Prefabs/Weapons/W_*.prefab; move/rotate it on
    /// the weapon). Equip() places the weapon so its Grip coincides with the slot in position
    /// AND rotation. Grip +Y is the hilt direction, +Z the back of the hand (CLAUDE.md 2).
    /// </summary>
    [DisallowMultipleComponent]
    public class SkeletonWeapon : MonoBehaviour
    {
        public enum Hand { Right, Left, LeftForearm }   // LeftForearm: kept for strapped items; shields now go on Left

        [System.Serializable]
        public class Item
        {
            [Tooltip("Weapon prefab (Prefabs/Weapons/W_<Name>) with a child named Grip")]
            public GameObject model;
            public Hand hand = Hand.Right;
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
        public const string RightSlotName = "RightHandSlot", LeftSlotName = "LeftHandSlot", ForearmSlotName = "LeftForearmSlot", GripName = "Grip";
        // defaults used only when a prefab has no slot yet (the prefab builder creates them
        // and keeps whatever you moved them to): measured 2026-09-20 as the centroid of the
        // curled fingers in socket space, and mid-forearm on the outside for the shield
        // the user tuned these on the Warrior in the editor (2026-09-21); they hold for all six
        public static readonly Vector3 DefaultRightSlotPos = new Vector3(-0.0079f, 0.008f, -0.0352f);
        public static readonly Vector3 DefaultLeftSlotPos = new Vector3(0.0086f, 0.010f, -0.0384f);
        public static readonly Vector3 DefaultForearmSlotPos = new Vector3(0.028f, 0.13f, -0.021f);
        public static readonly Vector3 DefaultForearmSlotEuler = new Vector3(0f, 126.1f, 180f);

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

        /// <summary>Find the three slots, creating any missing one at its default under the
        /// socket bone (also usable from editor tooling, where Awake does not run).</summary>
        public void EnsureSockets()
        {
            if (_right != null && _left != null && _forearm != null) return;
            Transform rightBone = null, leftBone = null, forearmBone = null;
            foreach (var t in GetComponentsInChildren<Transform>(true))
            {
                if (t.name == "RightWeaponSocket") rightBone = t;
                else if (t.name == "LeftWeaponSocket") leftBone = t;
                else if (t.name == "LeftForeArm") forearmBone = t;
            }
            _right = Slot(rightBone, RightSlotName, DefaultRightSlotPos, Vector3.zero);
            _left = Slot(leftBone, LeftSlotName, DefaultLeftSlotPos, Vector3.zero);
            _forearm = Slot(forearmBone, ForearmSlotName, DefaultForearmSlotPos, DefaultForearmSlotEuler);
        }

        public static Transform Slot(Transform bone, string name, Vector3 defaultPos, Vector3 defaultEuler)
        {
            if (bone == null) return null;
            var s = bone.Find(name);
            if (s == null)
            {
                s = new GameObject(name).transform;
                s.SetParent(bone, false);
                s.localPosition = defaultPos;
                s.localRotation = Quaternion.Euler(defaultEuler);
                s.localScale = Vector3.one;
            }
            return s;
        }

        /// <summary>Place `weapon` so that its Grip child coincides with `slot` (position and rotation).</summary>
        public static void AlignGrip(Transform weapon, Transform slot)
        {
            var grip = weapon.Find(GripName);
            if (grip == null) { weapon.SetPositionAndRotation(slot.position, slot.rotation); return; }
            // rotation first (the grip's rotation relative to the weapon root is fixed), then translate
            Quaternion gripRel = Quaternion.Inverse(weapon.rotation) * grip.rotation;
            weapon.rotation = slot.rotation * Quaternion.Inverse(gripRel);
            weapon.position += slot.position - grip.position;
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
                go.transform.localScale = Vector3.one;
                AlignGrip(go.transform, socket);
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
