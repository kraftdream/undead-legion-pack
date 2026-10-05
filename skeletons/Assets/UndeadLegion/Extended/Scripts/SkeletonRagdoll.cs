using System.Collections.Generic;
using UnityEngine;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// A physics body on the Humanoid bones: 11 rigidbodies with colliders and character joints. While the character is
    /// animated the bodies are kinematic and their colliders serve as hitboxes; <see cref="Activate"/> hands the body to
    /// physics, carrying each bone's current velocity so a fall continues the motion it interrupts, and
    /// <see cref="BlendToAnimation"/> returns it to the Animator over a short pose blend.
    /// </summary>
    [DisallowMultipleComponent]
    public class SkeletonRagdoll : MonoBehaviour
    {
        [System.Serializable]
        public class Part
        {
            public HumanBodyBones bone;
            public Rigidbody body;
            public Collider collider;
        }

        [Tooltip("Total mass of the body, kg (a skeleton is lighter than a person).")]
        public float totalMass = 35f;
        [Tooltip("Detach held weapons and give them physics when the ragdoll activates.")]
        public bool dropWeapons = true;
        [Tooltip("Seconds the pose blends from the ragdoll back to the animation.")]
        public float blendTime = 0.6f;
        [Tooltip("Angular damping of the bodies while ragdolled (higher settles a limp body sooner).")]
        public float angularDamping = 0.6f;
        [Tooltip("Angular damping of the head: an unsupported head otherwise swings on its joint like a pendulum for many seconds.")]
        public float headAngularDamping = 5f;
        public List<Part> parts = new List<Part>();

        public bool IsRagdoll { get; private set; }
        public event System.Action<bool> RagdollChanged;

        Animator _animator;
        readonly Dictionary<Rigidbody, Vector3> _prevPos = new Dictionary<Rigidbody, Vector3>();
        readonly Dictionary<Rigidbody, Quaternion> _prevRot = new Dictionary<Rigidbody, Quaternion>();
        readonly List<Transform> _bones = new List<Transform>();
        readonly List<Quaternion> _blendFrom = new List<Quaternion>();
        float _blendT = -1f;
        Vector3 _hipsBlendFrom;
        readonly List<GameObject> _dropped = new List<GameObject>();

        public Rigidbody Hips { get { foreach (var p in parts) if (p.bone == HumanBodyBones.Hips) return p.body; return null; } }

        void Awake()
        {
            _animator = GetComponent<Animator>();
            if (parts.Count == 0) Build();
            IgnoreSelfCollisions();   // not serialised: a prefab built in the editor loses it, so it is set again at runtime
            SetKinematic(true);
            foreach (var t in GetComponentsInChildren<Transform>()) _bones.Add(t);
        }

        // ------------------------------------------------------------------ build

        static readonly HumanBodyBones[] Order =
        {
            HumanBodyBones.Hips, HumanBodyBones.LeftUpperLeg, HumanBodyBones.LeftLowerLeg, HumanBodyBones.RightUpperLeg, HumanBodyBones.RightLowerLeg,
            HumanBodyBones.Chest, HumanBodyBones.Head, HumanBodyBones.LeftUpperArm, HumanBodyBones.LeftLowerArm, HumanBodyBones.RightUpperArm, HumanBodyBones.RightLowerArm,
        };
        static readonly float[] MassShare = { 0.20f, 0.09f, 0.05f, 0.09f, 0.05f, 0.22f, 0.08f, 0.055f, 0.045f, 0.055f, 0.045f };

        /// <summary>Creates the bodies, colliders and joints from the Animator's Humanoid bones (replaces any previous build).</summary>
        public void Build()
        {
            var an = GetComponent<Animator>();
            if (an == null || !an.isHuman) { Debug.LogWarning("SkeletonRagdoll: needs a Humanoid Animator", this); return; }
            Clear();
            Transform B(HumanBodyBones b) { var t = an.GetBoneTransform(b); return t; }
            var root = transform;
            Vector3 right = root.right, fwd = root.forward, up = root.up;
            float mass(int i) { return totalMass * MassShare[i]; }
            var map = new Dictionary<HumanBodyBones, Rigidbody>();
            for (int i = 0; i < Order.Length; i++)
            {
                var hb = Order[i]; var t = B(hb);
                if (hb == HumanBodyBones.Chest && t == null) t = B(HumanBodyBones.Spine);
                if (t == null) continue;
                var rb = t.gameObject.AddComponent<Rigidbody>(); rb.mass = mass(i); rb.interpolation = RigidbodyInterpolation.Interpolate;
                rb.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative; rb.linearDamping = 0.05f; rb.angularDamping = 0.1f;
                Collider col;
                switch (hb)
                {
                    case HumanBodyBones.Hips:
                    {
                        var spine = B(HumanBodyBones.Spine);
                        var box = t.gameObject.AddComponent<BoxCollider>();
                        float h = spine != null ? Vector3.Distance(t.position, spine.position) * 1.6f : 0.18f;
                        box.size = Local(t, new Vector3(0.30f, h, 0.20f), right, up, fwd);
                        box.center = t.InverseTransformPoint(t.position + up * h * 0.25f);
                        col = box; break;
                    }
                    case HumanBodyBones.Chest:
                    case HumanBodyBones.Spine:
                    {
                        var neck = B(HumanBodyBones.Neck) ?? B(HumanBodyBones.Head);
                        var box = t.gameObject.AddComponent<BoxCollider>();
                        float h = neck != null ? Vector3.Dot(neck.position - t.position, up) : 0.3f;
                        box.size = Local(t, new Vector3(0.32f, h, 0.22f), right, up, fwd);
                        box.center = t.InverseTransformPoint(t.position + up * h * 0.5f + fwd * 0.01f);
                        col = box; break;
                    }
                    case HumanBodyBones.Head:
                    {
                        var s = t.gameObject.AddComponent<SphereCollider>(); s.radius = 0.11f / Mathf.Max(0.0001f, t.lossyScale.x);
                        s.center = t.InverseTransformPoint(t.position + up * 0.09f + fwd * 0.02f); col = s; break;
                    }
                    default:
                    {
                        var child = ChildOf(an, hb);
                        var c = t.gameObject.AddComponent<CapsuleCollider>();
                        Vector3 end = child != null ? child.position : t.position + (t.position - t.parent.position) * 0.9f;
                        Vector3 lp = t.InverseTransformPoint(end);
                        int axis = Mathf.Abs(lp.x) > Mathf.Abs(lp.y) ? (Mathf.Abs(lp.x) > Mathf.Abs(lp.z) ? 0 : 2) : (Mathf.Abs(lp.y) > Mathf.Abs(lp.z) ? 1 : 2);
                        bool leg = hb == HumanBodyBones.LeftUpperLeg || hb == HumanBodyBones.RightUpperLeg || hb == HumanBodyBones.LeftLowerLeg || hb == HumanBodyBones.RightLowerLeg;
                        c.direction = axis; c.center = lp * 0.5f; c.height = lp.magnitude * 1.05f;
                        c.radius = (leg ? 0.075f : 0.055f) / Mathf.Max(0.0001f, t.lossyScale.x);
                        col = c; break;
                    }
                }
                map[hb] = rb;
                parts.Add(new Part { bone = hb, body = rb, collider = col });
            }
            // joints (limits after Unity's ragdoll conventions: twist about the character's right axis, swing about forward)
            Joint(an, map, HumanBodyBones.LeftUpperLeg, HumanBodyBones.Hips, right, fwd, -20, 70, 30);
            Joint(an, map, HumanBodyBones.RightUpperLeg, HumanBodyBones.Hips, right, fwd, -20, 70, 30);
            Joint(an, map, HumanBodyBones.LeftLowerLeg, HumanBodyBones.LeftUpperLeg, right, fwd, -90, 0, 0);
            Joint(an, map, HumanBodyBones.RightLowerLeg, HumanBodyBones.RightUpperLeg, right, fwd, -90, 0, 0);
            var chestKey = map.ContainsKey(HumanBodyBones.Chest) ? HumanBodyBones.Chest : HumanBodyBones.Spine;
            Joint(an, map, chestKey, HumanBodyBones.Hips, right, fwd, -20, 20, 10);
            Joint(an, map, HumanBodyBones.Head, chestKey, right, fwd, -40, 25, 25);
            Joint(an, map, HumanBodyBones.LeftUpperArm, chestKey, up, fwd, -70, 10, 50);
            Joint(an, map, HumanBodyBones.RightUpperArm, chestKey, -up, fwd, -70, 10, 50);
            Joint(an, map, HumanBodyBones.LeftLowerArm, HumanBodyBones.LeftUpperArm, fwd, up, -90, 0, 0);
            Joint(an, map, HumanBodyBones.RightLowerArm, HumanBodyBones.RightUpperArm, -fwd, up, -90, 0, 0);
            IgnoreSelfCollisions();
        }

        /// <summary>A body's parts never collide with each other (Physics.IgnoreCollision is runtime state, never saved).</summary>
        void IgnoreSelfCollisions()
        {
            for (int i = 0; i < parts.Count; i++) for (int j = i + 1; j < parts.Count; j++)
                if (parts[i].collider != null && parts[j].collider != null) Physics.IgnoreCollision(parts[i].collider, parts[j].collider, true);
        }

        static Vector3 Local(Transform t, Vector3 worldSize, Vector3 right, Vector3 up, Vector3 fwd)
        {
            // a world-axis-aligned box size expressed on the bone's local axes
            Vector3 s = Vector3.zero;
            Vector3[] axes = { t.right, t.up, t.forward };
            for (int i = 0; i < 3; i++)
            {
                var a = axes[i];
                s[i] = Mathf.Abs(Vector3.Dot(a, right)) * worldSize.x + Mathf.Abs(Vector3.Dot(a, up)) * worldSize.y + Mathf.Abs(Vector3.Dot(a, fwd)) * worldSize.z;
                s[i] /= Mathf.Max(0.0001f, t.lossyScale[i]);
            }
            return s;
        }

        static Transform ChildOf(Animator an, HumanBodyBones b)
        {
            switch (b)
            {
                case HumanBodyBones.LeftUpperLeg: return an.GetBoneTransform(HumanBodyBones.LeftLowerLeg);
                case HumanBodyBones.RightUpperLeg: return an.GetBoneTransform(HumanBodyBones.RightLowerLeg);
                case HumanBodyBones.LeftLowerLeg: return an.GetBoneTransform(HumanBodyBones.LeftFoot);
                case HumanBodyBones.RightLowerLeg: return an.GetBoneTransform(HumanBodyBones.RightFoot);
                case HumanBodyBones.LeftUpperArm: return an.GetBoneTransform(HumanBodyBones.LeftLowerArm);
                case HumanBodyBones.RightUpperArm: return an.GetBoneTransform(HumanBodyBones.RightLowerArm);
                case HumanBodyBones.LeftLowerArm: return an.GetBoneTransform(HumanBodyBones.LeftHand);
                case HumanBodyBones.RightLowerArm: return an.GetBoneTransform(HumanBodyBones.RightHand);
            }
            return null;
        }

        void Joint(Animator an, Dictionary<HumanBodyBones, Rigidbody> map, HumanBodyBones b, HumanBodyBones parent, Vector3 twistAxis, Vector3 swingAxis, float lowTwist, float highTwist, float swing)
        {
            Rigidbody rb, prb;
            if (!map.TryGetValue(b, out rb) || !map.TryGetValue(parent, out prb)) return;
            var j = rb.gameObject.AddComponent<CharacterJoint>();
            j.connectedBody = prb;
            j.axis = rb.transform.InverseTransformDirection(twistAxis).normalized;
            j.swingAxis = rb.transform.InverseTransformDirection(swingAxis).normalized;
            j.lowTwistLimit = new SoftJointLimit { limit = lowTwist };
            j.highTwistLimit = new SoftJointLimit { limit = highTwist };
            j.swing1Limit = new SoftJointLimit { limit = swing };
            j.swing2Limit = new SoftJointLimit { limit = swing };
            j.enableProjection = true;
            j.enablePreprocessing = false;
        }

        /// <summary>Removes every body, collider and joint this component built.</summary>
        public void Clear()
        {
            foreach (var p in parts)
            {
                if (p == null || p.body == null) continue;
                var j = p.body.GetComponent<CharacterJoint>(); if (j != null) DestroyNow(j);
                if (p.collider != null) DestroyNow(p.collider);
                DestroyNow(p.body);
            }
            parts.Clear();
        }

        static void DestroyNow(Object o) { if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }

        // ------------------------------------------------------------------ runtime

        void SetKinematic(bool kinematic)
        {
            foreach (var p in parts)
            {
                if (p.body == null) continue;
                p.body.isKinematic = kinematic;
                p.body.interpolation = kinematic ? RigidbodyInterpolation.None : RigidbodyInterpolation.Interpolate;
            }
        }

        void FixedUpdate()
        {
            if (IsRagdoll) return;
            foreach (var p in parts)
            {
                if (p.body == null) continue;
                _prevPos[p.body] = p.body.transform.position; _prevRot[p.body] = p.body.transform.rotation;
            }
        }

        /// <summary>Hands the body to physics. An optional impulse is applied at a world point (the body nearest the point takes it).</summary>
        public void Activate(Vector3 impulse = default(Vector3), Vector3 point = default(Vector3))
        {
            if (IsRagdoll) return;
            IsRagdoll = true; _blendT = -1f;
            float dt = Mathf.Max(0.0001f, Time.fixedDeltaTime);
            if (_animator != null) _animator.enabled = false;
            var capsule = GetComponent<CapsuleCollider>(); if (capsule != null) capsule.enabled = false;
            SetKinematic(false);
            foreach (var p in parts)
            {
                if (p.body == null) continue;
                p.body.angularDamping = p.bone == HumanBodyBones.Head ? headAngularDamping : angularDamping;
                Vector3 pp; Quaternion pr;
                if (_prevPos.TryGetValue(p.body, out pp)) p.body.linearVelocity = (p.body.transform.position - pp) / dt;
                if (_prevRot.TryGetValue(p.body, out pr))
                {
                    var dq = p.body.transform.rotation * Quaternion.Inverse(pr); float ang; Vector3 ax; dq.ToAngleAxis(out ang, out ax);
                    if (ang > 180f) ang -= 360f;
                    if (!float.IsNaN(ax.x)) p.body.angularVelocity = ax * (ang * Mathf.Deg2Rad / dt);
                }
            }
            if (impulse != Vector3.zero)
            {
                var hit = Nearest(point);
                if (hit != null) hit.AddForceAtPosition(impulse, point, ForceMode.Impulse);
            }
            if (dropWeapons) DropWeapons();
            if (RagdollChanged != null) RagdollChanged(true);
        }

        /// <summary>The ragdoll body nearest a world point.</summary>
        public Rigidbody Nearest(Vector3 point)
        {
            Rigidbody best = null; float bd = float.MaxValue;
            foreach (var p in parts)
            {
                if (p.collider == null) continue;
                float d = (p.collider.ClosestPoint(point) - point).sqrMagnitude;
                if (d < bd) { bd = d; best = p.body; }
            }
            return best;
        }

        void DropWeapons()
        {
            var weapon = GetComponent<UndeadLegion.Demo.SkeletonWeapon>();
            if (weapon == null) return;
            foreach (var item in weapon.HeldItems())
            {
                if (item == null) continue;
                item.transform.SetParent(null, true);
                var rb = item.GetComponent<Rigidbody>(); if (rb == null) rb = item.AddComponent<Rigidbody>();
                rb.mass = 2f; rb.interpolation = RigidbodyInterpolation.Interpolate;
                if (item.GetComponentInChildren<Collider>() == null)
                {
                    var b = new Bounds(item.transform.position, Vector3.zero); bool any = false;
                    foreach (var r in item.GetComponentsInChildren<Renderer>()) { if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds); }
                    var box = item.AddComponent<BoxCollider>();
                    box.center = item.transform.InverseTransformPoint(b.center);
                    var ls = item.transform.lossyScale; box.size = new Vector3(b.size.x / ls.x, b.size.y / ls.y, b.size.z / ls.z);
                }
                foreach (var p in parts) if (p.collider != null) foreach (var c in item.GetComponentsInChildren<Collider>()) Physics.IgnoreCollision(c, p.collider, true);
                _dropped.Add(item);
            }
            weapon.ForgetHeldItems();
        }

        /// <summary>Returns the body to the Animator: the character is placed under the fallen hips and the pose blends back over <see cref="blendTime"/>.</summary>
        public void BlendToAnimation()
        {
            if (!IsRagdoll) return;
            var hips = Hips;
            Vector3 hipsPos = hips != null ? hips.position : transform.position;
            _blendFrom.Clear();
            foreach (var t in _bones) _blendFrom.Add(t != null ? t.rotation : Quaternion.identity);
            _hipsBlendFrom = hipsPos;
            SetKinematic(true);
            // the root moves under the hips on the ground; the bones hold their world pose while it moves
            var worldPos = new List<Vector3>(); foreach (var t in _bones) worldPos.Add(t != null ? t.position : Vector3.zero);
            Vector3 ground = new Vector3(hipsPos.x, transform.position.y, hipsPos.z);
            RaycastHit rh; if (Physics.Raycast(hipsPos + Vector3.up * 0.5f, Vector3.down, out rh, 5f, ~0, QueryTriggerInteraction.Ignore) && !IsOwn(rh.collider)) ground.y = rh.point.y;
            transform.position = ground;
            for (int i = 0; i < _bones.Count; i++) if (_bones[i] != null && _bones[i] != transform) { _bones[i].position = worldPos[i]; _bones[i].rotation = _blendFrom[i]; }
            var capsule = GetComponent<CapsuleCollider>(); if (capsule != null) capsule.enabled = true;
            if (_animator != null) { _animator.enabled = true; _animator.Rebind(); _animator.Update(0f); }
            IsRagdoll = false; _blendT = 0f;
            foreach (var d in _dropped) if (d != null) Destroy(d);
            _dropped.Clear();
            var weapon = GetComponent<UndeadLegion.Demo.SkeletonWeapon>(); if (weapon != null) weapon.ReequipCurrent();
            if (RagdollChanged != null) RagdollChanged(false);
        }

        /// <summary>Weapons this skeleton dropped when it went limp; they dissolve and are destroyed with it.</summary>
        public IList<GameObject> Dropped { get { return _dropped; } }

        void OnDestroy() { foreach (var d in _dropped) if (d != null) Destroy(d); }

        bool IsOwn(Collider c) { foreach (var p in parts) if (p.collider == c) return true; return false; }

        void LateUpdate()
        {
            if (_blendT < 0f || IsRagdoll) return;
            _blendT += Time.deltaTime / Mathf.Max(0.01f, blendTime);
            float w = Mathf.Clamp01(_blendT); w = w * w * (3f - 2f * w);
            for (int i = 0; i < _bones.Count && i < _blendFrom.Count; i++)
            {
                var t = _bones[i]; if (t == null || t == transform) continue;
                t.rotation = Quaternion.Slerp(_blendFrom[i], t.rotation, w);
            }
            var hipsT = _animator != null ? _animator.GetBoneTransform(HumanBodyBones.Hips) : null;
            if (hipsT != null) hipsT.position = Vector3.Lerp(_hipsBlendFrom, hipsT.position, w);
            if (_blendT >= 1f) _blendT = -1f;
        }
    }
}
