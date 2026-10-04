using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;

namespace UndeadLegion.Extended
{
    /// <summary>What a hit carries: the damage, where it landed, the push and who dealt it.</summary>
    public struct DamageInfo
    {
        public float amount;
        public Vector3 point;
        public Vector3 impulse;
        public GameObject source;
    }

    /// <summary>
    /// Health, teams and death. Damage drives <see cref="SkeletonHitReaction"/>; at zero health the skeleton dies by ragdoll,
    /// by one of the death clips, or by a death clip that hands over to the ragdoll, and can dissolve and remove itself after.
    /// </summary>
    [DisallowMultipleComponent]
    public class SkeletonHealth : MonoBehaviour
    {
        public enum DeathMode { Ragdoll, DeathClip, DeathClipThenRagdoll }

        public float maxHealth = 100f;
        public float health = 100f;
        [Tooltip("Skeletons of the same team never target each other.")]
        public int team = 0;
        public DeathMode deathMode = DeathMode.Ragdoll;
        [Tooltip("Death clips picked at random for the DeathClip modes (Base-layer state names).")]
        public string[] deathClips = { "Death_01", "Death_02", "Death_03", "Death_04" };
        [Tooltip("Seconds into a death clip before the ragdoll takes over (DeathClipThenRagdoll).")]
        public float ragdollAfter = 0.6f;
        [Tooltip("Seconds after death before the body dissolves (0 = never).")]
        public float dissolveAfter = 4f;
        [Tooltip("Additive reaction clips played on the Animator's Hit layer on every hit that does not kill, one picked at random (empty = none).")]
        public string[] hitClips = { "Hit_01", "Hit_02" };
        [Tooltip("Remove the GameObject once dissolved.")]
        public bool destroyWhenDissolved = true;
        [Tooltip("Takes the hits (reactions, hit clips, the damage event) but never loses health: a player character that cannot die.")]
        public bool invulnerable = false;
        [Tooltip("While true, hits from the front (within blockArc) are blocked: a small flinch, no hit clip, no damage.")]
        public bool blocking = false;
        [Tooltip("Half-angle, degrees, of the arc in front of the skeleton that a block covers.")]
        public float blockArc = 70f;
        [Range(0f, 1f)] [Tooltip("Share of the push a blocked hit still gives the hit reaction.")]
        public float blockedReaction = 0.3f;

        public UnityEvent<DamageInfo> onDamaged = new UnityEvent<DamageInfo>();
        public UnityEvent onDied = new UnityEvent();

        public bool IsDead { get; private set; }
        public float Normalized { get { return maxHealth > 0f ? Mathf.Clamp01(health / maxHealth) : 0f; } }

        SkeletonHitReaction _hit;
        SkeletonRagdoll _ragdoll;
        Animator _animator;
        DamageInfo _lastHit;

        /// <summary>Every enabled SkeletonHealth (for target searches).</summary>
        public static readonly List<SkeletonHealth> All = new List<SkeletonHealth>();
        void OnEnable() { if (!All.Contains(this)) All.Add(this); }
        void OnDisable() { All.Remove(this); }

        void Awake()
        {
            _hit = GetComponent<SkeletonHitReaction>();
            _ragdoll = GetComponent<SkeletonRagdoll>();
            _animator = GetComponent<Animator>();
            health = Mathf.Clamp(health, 0f, maxHealth);
        }

        public void TakeDamage(DamageInfo info)
        {
            if (IsDead) return;
            if (IsBlocked(info))
            {
                if (_hit != null) _hit.Hit(info.point, info.impulse * blockedReaction);
                info.amount = 0f; LastHitBlocked = true;
                onDamaged.Invoke(info);
                return;
            }
            LastHitBlocked = false;
            if (!invulnerable) health = Mathf.Max(0f, health - info.amount);
            _lastHit = info;
            if (_hit != null) _hit.Hit(info.point, info.impulse);
            if (health > 0f) PlayHitClip();
            onDamaged.Invoke(info);
            if (health <= 0f) Die();
        }

        public void TakeDamage(float amount, Vector3 point, Vector3 impulse, GameObject source = null)
        {
            TakeDamage(new DamageInfo { amount = amount, point = point, impulse = impulse, source = source });
        }

        /// <summary>True when the last hit taken was blocked.</summary>
        public bool LastHitBlocked { get; private set; }

        bool IsBlocked(DamageInfo info)
        {
            if (!blocking) return false;
            Vector3 from = info.source != null ? info.source.transform.position : info.point;
            Vector3 d = from - transform.position; d.y = 0f;
            return d.sqrMagnitude > 1e-4f && Vector3.Angle(transform.forward, d) <= blockArc;
        }

        /// <summary>Kills the skeleton with the configured death mode.</summary>
        public void Die()
        {
            if (IsDead) return;
            IsDead = true; health = 0f;
            var agent = GetComponent<UnityEngine.AI.NavMeshAgent>(); if (agent != null && agent.enabled) { if (agent.isOnNavMesh) agent.isStopped = true; agent.enabled = false; }
            bool clip = deathMode != DeathMode.Ragdoll && _animator != null && deathClips != null && deathClips.Length > 0;
            if (clip)
            {
                _animator.CrossFadeInFixedTime(deathClips[Random.Range(0, deathClips.Length)], 0.12f, 0);
                if (deathMode == DeathMode.DeathClipThenRagdoll && _ragdoll != null) Invoke("RagdollNow", ragdollAfter);
            }
            else if (_ragdoll != null) _ragdoll.Activate(_lastHit.impulse * 1.5f, _lastHit.point);
            onDied.Invoke();
            if (dissolveAfter > 0f) Invoke("DissolveNow", dissolveAfter);
        }

        void PlayHitClip()
        {
            if (hitClips == null || hitClips.Length == 0 || _animator == null || !_animator.isActiveAndEnabled) return;
            string clip = hitClips[Random.Range(0, hitClips.Length)]; if (string.IsNullOrEmpty(clip)) return;
            int layer = _animator.GetLayerIndex("Hit"); int hash = Animator.StringToHash(clip);
            if (layer >= 0 && _animator.HasState(layer, hash)) _animator.CrossFadeInFixedTime(hash, 0.05f, layer, 0f);
        }

        void RagdollNow() { if (_ragdoll != null) _ragdoll.Activate(_lastHit.impulse, _lastHit.point); }

        void DissolveNow()
        {
            var d = GetComponent<SkeletonDissolve>();
            if (d != null) d.DissolveOut(destroyWhenDissolved);
            else if (destroyWhenDissolved) Destroy(gameObject);
        }

        /// <summary>Back to full health, out of the ragdoll and on the animation again.</summary>
        public void Revive()
        {
            CancelInvoke();
            IsDead = false; health = maxHealth;
            if (_ragdoll != null && _ragdoll.IsRagdoll) _ragdoll.BlendToAnimation();
            var agent = GetComponent<UnityEngine.AI.NavMeshAgent>(); if (agent != null) agent.enabled = true;
        }
    }
}
