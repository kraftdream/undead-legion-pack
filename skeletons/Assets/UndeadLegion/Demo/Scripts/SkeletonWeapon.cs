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
        Animator _animator; int _fingersLeft = -2, _fingersRight = -2;   // -2 = not looked up yet, -1 = the controller has no such layer

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
            // the fist blends in by 1 - the hand's finger-layer weight (that layer fades over `fingerFade`), so a hand
            // closes on the item or the shaft over the crossfade; on an item held from the start the weight is 1
            float wl = GripWeight(_fingersLeft), wr = GripWeight(_fingersRight);
            if ((_holdLeft || _clipHoldLeft) && _gripLeftBones.Count == gripLeft.Count && wl > 0f)
                for (int i = 0; i < gripLeft.Count; i++) if (_gripLeftBones[i] != null) _gripLeftBones[i].localRotation = Quaternion.Slerp(_gripLeftBones[i].localRotation, gripLeft[i].localRotation, wl);
            if ((_holdRight || _clipHoldRight) && _gripRightBones.Count == gripRight.Count && wr > 0f)
                for (int i = 0; i < gripRight.Count; i++) if (_gripRightBones[i] != null) _gripRightBones[i].localRotation = Quaternion.Slerp(_gripRightBones[i].localRotation, gripRight[i].localRotation, wr);
        }

        void LateUpdate()
        {
            bool changed = _clipHoldLeft != _clipHoldLeftFrame || _clipHoldRight != _clipHoldRightFrame;
            _clipHoldLeft = _clipHoldLeftFrame; _clipHoldRight = _clipHoldRightFrame;
            _clipHoldLeftFrame = _clipHoldRightFrame = false;
            if (changed) ApplyFingerLayers();
            FadeFingers();
            if (_holdLeft || _holdRight || _clipHoldLeft || _clipHoldRight) ApplyGrip();
        }

        /// <summary>The empty-hand finger idles (2026-09-25): AC_Skeleton's LeftFingers / RightFingers layers loop
        /// Hand_Idle_L / Hand_Idle_R over that hand's 15 finger bones. Weight 1 while the hand holds nothing, 0 while
        /// it holds an item (the Grip fist then takes over in LateUpdate), so every clip's own fingers are replaced
        /// by the relaxed pose on an empty hand and by the fist on a full one.</summary>
        void ApplyFingerLayers()
        {
            if (_animator == null) _animator = GetComponent<Animator>();
            if (_animator == null || _animator.runtimeAnimatorController == null) return;
            if (_fingersLeft == -2) { _fingersLeft = _animator.GetLayerIndex("LeftFingers"); _fingersRight = _animator.GetLayerIndex("RightFingers"); }
            // the weight is a target: Update fades the layer over `fingerFade` seconds (a clip-hold from a state's
            // SkeletonGripState begins with the crossfade into it, so the fingers close as the hand reaches the shaft)
            _fingerTargetLeft = (_holdLeft || _clipHoldLeft || _fingerSuspend || !fingerIdleLeft) ? 0f : 1f;
            _fingerTargetRight = (_holdRight || _clipHoldRight || _fingerSuspend || !fingerIdleRight) ? 0f : 1f;
            if (!Application.isPlaying)
            {
                if (_fingersLeft >= 0) _animator.SetLayerWeight(_fingersLeft, _fingerTargetLeft);
                if (_fingersRight >= 0) _animator.SetLayerWeight(_fingersRight, _fingerTargetRight);
            }
        }

        void Start()
        {
            ApplyFingerLayers();
        }

        /// <summary>Animation event on a bow clip (manifest `events`, e.g. Shoot_01 frame 15): the string
        /// takes the draw hand from here on.</summary>
        public void BowAttach()
        {
            foreach (var go in _spawned) if (go != null) foreach (var b in go.GetComponentsInChildren<BowString>(true)) b.attached = true;
            SetArrowVisible(true);
        }

        /// <summary>Animation event (e.g. Shoot_01 frame 21): the string is let go, and for the demo the arrow in
        /// the draw hand is hidden for a moment so the shot reads (it comes back after `arrowHideSeconds`).</summary>
        public void BowRelease()
        {
            bool any = false;
            foreach (var go in _spawned) if (go != null) foreach (var b in go.GetComponentsInChildren<BowString>(true)) { b.attached = false; any = true; }
            if (any && arrowHideSeconds > 0f) { SetArrowVisible(false); _arrowShowAt = Time.time + arrowHideSeconds; }
            if (any && fireProjectile) FireArrow();
        }

        [Tooltip("On BowRelease, launch a copy of the held arrow as an ArrowProjectile (demo only, no collision).")]
        public bool fireProjectile = true;
        [Tooltip("Launch speed of the fired arrow, m/s.")]
        public float arrowSpeed = 30f;
        [Tooltip("Where the fired arrow flies: the character's forward for now (a static direction, not the bow's aim).")]
        public ArrowDirection arrowDirection = ArrowDirection.CharacterForward;
        public enum ArrowDirection { CharacterForward, BowAim }

        /// <summary>Spawn a free copy of the held arrow at the held arrow's transform and launch it.</summary>
        void FireArrow()
        {
            if (_current < 0 || _current >= loadouts.Count) return;
            GameObject held = null;
            foreach (var go in _spawned) if (go != null && go.name.StartsWith("W_Arrow")) held = go;
            if (held == null) return;
            GameObject model = null;
            foreach (var it in loadouts[_current].items) if (it.model != null && it.model.name.StartsWith("W_Arrow")) model = it.model;
            if (model == null) return;
            Vector3 dir = transform.forward;
            if (arrowDirection == ArrowDirection.BowAim)
            {
                // the bow hand to the draw hand's slot, reversed: the shot line as the pose has it
                var bow = _left != null && _holdLeft ? _left : _right;
                var draw = bow == _left ? _right : _left;
                if (bow != null && draw != null && (bow.position - draw.position).sqrMagnitude > 1e-6f) dir = (bow.position - draw.position).normalized;
            }
            var arrow = Instantiate(model, held.transform.position, held.transform.rotation);
            arrow.name = model.name + "_Projectile";
            arrow.transform.localScale = Vector3.one;
            foreach (var r in arrow.GetComponentsInChildren<Renderer>(true)) r.enabled = true;
            var p = arrow.GetComponent<ArrowProjectile>();
            if (p == null) p = arrow.AddComponent<ArrowProjectile>();
            p.speed = arrowSpeed;
            p.Launch(dir);
        }

        [Tooltip("After BowRelease the arrow in the draw hand is hidden this long (seconds) so the shot reads in the demo; 0 = never hidden.")]
        public float arrowHideSeconds = 1.2f;
        float _arrowShowAt = -1f;

        void SetArrowVisible(bool on)
        {
            foreach (var go in _spawned)
                if (go != null && go.name.StartsWith("W_Arrow"))
                    foreach (var r in go.GetComponentsInChildren<Renderer>(true)) r.enabled = on;
        }

        void Update()
        {
            if (_arrowShowAt > 0f && Time.time >= _arrowShowAt) { _arrowShowAt = -1f; SetArrowVisible(true); }
        }

        [Tooltip("Seconds the empty-hand finger layers take to fade in or out (matches the demo's crossfade).")]
        public float fingerFade = 0.15f;
        [Tooltip("The empty-hand finger idle on the left / right hand (the demo's Hand idle toggles); off = the clip's own fingers.")]
        public bool fingerIdleLeft = true, fingerIdleRight = true;
        bool _fingerSuspend;   // a death plays: both finger idles off whatever the toggles say (SetFingerIdleSuspended)

        /// <summary>Is the finger idle currently driving this hand (its layer's target weight is 1: the hand is empty,
        /// the toggle on, no suspension)?</summary>
        public bool IsFingerIdleActive(Hand hand)
        {
            return hand == Hand.Left ? _fingerTargetLeft > 0.5f : hand == Hand.Right ? _fingerTargetRight > 0.5f : false;
        }

        public void SetFingerIdle(Hand hand, bool on)
        {
            if (hand == Hand.Left) fingerIdleLeft = on; else if (hand == Hand.Right) fingerIdleRight = on;
            ApplyFingerLayers();
        }

        /// <summary>A death (or any clip whose own fingers must show): both finger idles fade out until released.</summary>
        public void SetFingerIdleSuspended(bool on)
        {
            _fingerSuspend = on;
            ApplyFingerLayers();
        }
        float _fingerTargetLeft = 1f, _fingerTargetRight = 1f;
        bool _clipHoldLeft, _clipHoldRight, _clipHoldLeftFrame, _clipHoldRightFrame;

        /// <summary>Called by a SkeletonGripState every frame its state is evaluated: this hand rides the weapon (a
        /// two-hander's second hand) and counts as holding for the finger layers and the grip fist. Forgotten
        /// in LateUpdate, so a hold lasts exactly as long as some grip state is active.</summary>
        public void ClipHoldThisFrame(Hand hand)
        {
            if (hand == Hand.Left) _clipHoldLeftFrame = true; else if (hand == Hand.Right) _clipHoldRightFrame = true;
        }

        /// <summary>The empty-hand finger layers fade toward their targets; the grip fist fades in with them
        /// (weight = 1 - the layer's weight), so equipping, a clip-hold's start and its end close or open the
        /// hand over `fingerFade` instead of snapping.</summary>
        void FadeFingers()
        {
            if (_animator == null) return;
            float step = fingerFade > 0f ? Time.deltaTime / fingerFade : 1f;
            if (_fingersLeft >= 0) _animator.SetLayerWeight(_fingersLeft, Mathf.MoveTowards(_animator.GetLayerWeight(_fingersLeft), _fingerTargetLeft, step));
            if (_fingersRight >= 0) _animator.SetLayerWeight(_fingersRight, Mathf.MoveTowards(_animator.GetLayerWeight(_fingersRight), _fingerTargetRight, step));
        }

        float GripWeight(int layer) { return layer >= 0 && _animator != null && Application.isPlaying ? 1f - _animator.GetLayerWeight(layer) : 1f; }

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
                // a bending bow (BowString on the weapon prefab): the string follows the OTHER hand's slot
                var bow = go.GetComponentInChildren<BowString>(true);
                if (bow != null) { bow.drawHand = it.hand == Hand.Left ? _right : _left; bow.attached = false; bow.Resolve(); }
            }
            ApplyFingerLayers();
        }

        public void Clear()
        {
            foreach (var go in _spawned)
                if (go != null) { if (Application.isPlaying) Destroy(go); else DestroyImmediate(go); }
            _spawned.Clear();
            _current = -1;
            _holdLeft = _holdRight = false;
            ApplyFingerLayers();
        }
    }
}
