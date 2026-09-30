using System.Collections.Generic;
using UnityEngine;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// Cloth simulation on the soft armour modules a skeleton wears (skirts, robes, pants). Each piece gets Unity's Cloth
    /// with its vertices pinned by height: fixed at the waist, free to swing toward the hem. The legs' capsule colliders
    /// (the ragdoll's) keep the cloth out of the legs. Works on any piece worn by any skeleton; call
    /// <see cref="Refresh"/> after changing armour.
    /// </summary>
    [DisallowMultipleComponent]
    public class SkeletonCloth : MonoBehaviour
    {
        [System.Serializable]
        public class ModuleRule
        {
            [Tooltip("Armour module name (Skirt, Robe, Pants, ...).")]
            public string module;
            [Tooltip("How far the hem may move from its skinned position, metres.")]
            public float maxDistance = 0.12f;
            [Tooltip("Metres below the waist that stay pinned.")]
            public float pinnedBand = 0.06f;
            [Range(0f, 1f)] public float stiffness = 0.8f;
        }

        public bool simulate = true;
        public List<ModuleRule> rules = new List<ModuleRule>
        {
            new ModuleRule { module = "Skirt", maxDistance = 0.10f, pinnedBand = 0.05f, stiffness = 0.85f },
            new ModuleRule { module = "Robe", maxDistance = 0.16f, pinnedBand = 0.10f, stiffness = 0.75f },
            new ModuleRule { module = "Pants", maxDistance = 0.03f, pinnedBand = 0.10f, stiffness = 0.95f },
        };
        [Tooltip("Armour sets whose pieces are rigid (plate, not fabric): never simulated, also when another skeleton wears them.")]
        public List<string> rigidSets = new List<string> { "SkeletonKnight" };
        [Range(0f, 1f)] public float damping = 0.15f;
        [Tooltip("How much the character's own movement drags the cloth (0..1).")]
        [Range(0f, 1f)] public float worldVelocityScale = 0.4f;
        [Range(0f, 1f)] public float worldAccelerationScale = 0.9f;
        [Tooltip("Turn the cloth off beyond this distance from the main camera (0 = always on).")]
        public float cullDistance = 25f;

        readonly List<Cloth> _cloths = new List<Cloth>();
        Animator _animator;

        void Start() { _animator = GetComponent<Animator>(); Refresh(); }

        ModuleRule RuleFor(string moduleName)
        {
            foreach (var r in rules) if (!string.IsNullOrEmpty(r.module) && moduleName.StartsWith(r.module)) return r;
            return null;
        }

        /// <summary>Adds or updates the Cloth on every worn soft module and removes it from pieces that no longer qualify.</summary>
        public void Refresh()
        {
            _cloths.Clear();
            if (_animator == null) _animator = GetComponent<Animator>();
            var hips = _animator != null ? _animator.GetBoneTransform(HumanBodyBones.Hips) : null;
            float waist = hips != null ? hips.position.y : transform.position.y + 0.95f;
            var colliders = LegColliders();
            foreach (var piece in GetComponentsInChildren<UndeadLegion.Demo.ArmorPiece>(true))
            {
                var smr = piece.GetComponent<SkinnedMeshRenderer>(); if (smr == null) continue;
                var rule = RuleFor(piece.moduleName);
                var cloth = piece.GetComponent<Cloth>();
                if (rule == null || !simulate || rigidSets.Contains(piece.character)) { if (cloth != null) Destroy(cloth); continue; }
                if (cloth == null) cloth = piece.gameObject.AddComponent<Cloth>();
                Setup(cloth, rule, waist, colliders);
                _cloths.Add(cloth);
            }
        }

        CapsuleCollider[] LegColliders()
        {
            var list = new List<CapsuleCollider>();
            if (_animator == null) return list.ToArray();
            foreach (var b in new[] { HumanBodyBones.LeftUpperLeg, HumanBodyBones.LeftLowerLeg, HumanBodyBones.RightUpperLeg, HumanBodyBones.RightLowerLeg })
            {
                var t = _animator.GetBoneTransform(b); if (t == null) continue;
                var c = t.GetComponent<CapsuleCollider>(); if (c != null) list.Add(c);
            }
            return list.ToArray();
        }

        void Setup(Cloth cloth, ModuleRule rule, float waist, CapsuleCollider[] colliders)
        {
            var verts = cloth.vertices;
            var coeff = new ClothSkinningCoefficient[verts.Length];
            float hem = float.MaxValue;
            var world = new Vector3[verts.Length];
            for (int i = 0; i < verts.Length; i++) { world[i] = cloth.transform.TransformPoint(verts[i]); hem = Mathf.Min(hem, world[i].y); }
            float top = waist - rule.pinnedBand, span = Mathf.Max(0.05f, top - hem);
            for (int i = 0; i < verts.Length; i++)
            {
                float f = Mathf.Clamp01((top - world[i].y) / span);
                f = f * f * (3f - 2f * f);
                coeff[i].maxDistance = rule.maxDistance * f;
                coeff[i].collisionSphereDistance = 0f;
            }
            cloth.coefficients = coeff;
            cloth.stretchingStiffness = rule.stiffness;
            cloth.bendingStiffness = rule.stiffness * 0.6f;
            cloth.damping = damping;
            cloth.useGravity = true;
            cloth.worldVelocityScale = worldVelocityScale;
            cloth.worldAccelerationScale = worldAccelerationScale;
            cloth.friction = 0.4f;
            cloth.capsuleColliders = colliders;
            cloth.enabled = true;
        }

        void Update()
        {
            if (cullDistance <= 0f || Camera.main == null || _cloths.Count == 0) return;
            bool on = simulate && (Camera.main.transform.position - transform.position).sqrMagnitude < cullDistance * cullDistance;
            foreach (var c in _cloths) if (c != null && c.enabled != on) c.enabled = on;
        }

        /// <summary>Switches the simulation on or off for this skeleton.</summary>
        public void SetSimulate(bool on) { simulate = on; foreach (var c in _cloths) if (c != null) c.enabled = on; if (on && _cloths.Count == 0) Refresh(); }
    }
}
