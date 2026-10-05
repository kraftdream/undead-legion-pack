using System.Collections.Generic;
using UnityEngine;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// Physical hit reactions layered over any animation. A hit's torque (lever arm × force) kicks a damped angular spring on
    /// the struck bone and, with falloff, on its parents up to the hips; the springs are applied after the Animator every
    /// frame, so a skeleton flinches, twists and recovers while it keeps walking, idling or attacking.
    /// </summary>
    [DisallowMultipleComponent]
    public class SkeletonHitReaction : MonoBehaviour
    {
        [Tooltip("Spring stiffness: how fast a bone returns to the animated pose.")]
        public float stiffness = 90f;
        [Tooltip("Damping ratio (1 = no overshoot, lower wobbles).")]
        [Range(0.1f, 2f)] public float damping = 0.45f;
        [Tooltip("Degrees of offset per unit of angular impulse.")]
        public float strength = 12f;
        [Tooltip("Share of the impulse passed to each parent bone.")]
        [Range(0f, 1f)] public float falloff = 0.55f;
        [Tooltip("Largest offset any bone can take, degrees.")]
        public float maxAngle = 55f;

        class Spring { public Transform bone; public Vector3 angle; public Vector3 velocity; }

        Animator _animator;
        readonly Dictionary<Transform, Spring> _springs = new Dictionary<Transform, Spring>();
        readonly List<Transform> _candidates = new List<Transform>();
        Transform _hips;

        static readonly HumanBodyBones[] Reacting =
        {
            HumanBodyBones.Hips, HumanBodyBones.Spine, HumanBodyBones.Chest, HumanBodyBones.UpperChest, HumanBodyBones.Neck, HumanBodyBones.Head,
            HumanBodyBones.LeftShoulder, HumanBodyBones.LeftUpperArm, HumanBodyBones.LeftLowerArm,
            HumanBodyBones.RightShoulder, HumanBodyBones.RightUpperArm, HumanBodyBones.RightLowerArm,
        };

        void Awake()
        {
            _animator = GetComponent<Animator>();
            if (_animator == null || !_animator.isHuman) { enabled = false; return; }
            foreach (var b in Reacting) { var t = _animator.GetBoneTransform(b); if (t != null) _candidates.Add(t); }
            _hips = _animator.GetBoneTransform(HumanBodyBones.Hips);
        }

        /// <summary>A hit at a world point with a force (N·s, an impulse). The nearest reacting bone and its parents respond.</summary>
        public void Hit(Vector3 point, Vector3 impulse)
        {
            if (!enabled || _candidates.Count == 0 || !_animator.enabled) return;   // a ragdoll (Animator off) takes the hit physically
            Transform nearest = null; float bd = float.MaxValue;
            foreach (var t in _candidates) { float d = (t.position - point).sqrMagnitude; if (d < bd) { bd = d; nearest = t; } }
            float share = 1f;
            for (var t = nearest; t != null && share > 0.02f; t = t.parent)
            {
                if (!_candidates.Contains(t)) { if (t == transform) break; continue; }
                Spring s;
                if (!_springs.TryGetValue(t, out s)) { s = new Spring { bone = t }; _springs[t] = s; }
                Vector3 torque = Vector3.Cross(point - t.position, impulse);           // world-space angular impulse
                s.velocity += transform.InverseTransformDirection(torque) * strength * share;   // stored in the character's frame
                share *= falloff;
                if (t == _hips) break;
            }
        }

        void LateUpdate()
        {
            if (_springs.Count == 0) return;
            // the Animator is off under a ragdoll: nothing restores the pose each frame, so an offset would pile up on the bones
            if (!_animator.enabled) { _springs.Clear(); return; }
            float dt = Time.deltaTime; if (dt <= 0f) return;
            float c = 2f * damping * Mathf.Sqrt(stiffness);
            List<Transform> done = null;
            foreach (var s in _springs.Values)
            {
                // semi-implicit Euler on a unit-mass damped spring, in degrees; sub-stepped so a long frame stays stable
                int steps = Mathf.Clamp(Mathf.CeilToInt(dt / (1f / 120f)), 1, 32); float h = Mathf.Min(dt, 0.25f) / steps;
                for (int k = 0; k < steps; k++)
                {
                    s.velocity += (-stiffness * s.angle - c * s.velocity) * h;
                    s.angle += s.velocity * h;
                }
                if (s.angle.magnitude > maxAngle) { s.angle = s.angle.normalized * maxAngle; s.velocity *= 0.5f; }
                if (s.angle.sqrMagnitude < 1e-4f && s.velocity.sqrMagnitude < 1e-3f) { (done = done ?? new List<Transform>()).Add(s.bone); continue; }
                Vector3 axisW = transform.TransformDirection(s.angle);
                s.bone.rotation = Quaternion.AngleAxis(axisW.magnitude, axisW.normalized) * s.bone.rotation;
            }
            if (done != null) foreach (var t in done) _springs.Remove(t);
        }

        /// <summary>Clears every running reaction.</summary>
        public void ResetReactions() { _springs.Clear(); }
    }
}
