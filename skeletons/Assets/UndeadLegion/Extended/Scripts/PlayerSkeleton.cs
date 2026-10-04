using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// Puts a skeleton under player control: WASD walks (Shift + W runs) on the locomotion blend tree with root motion, the
    /// mouse turns the body, the left button attacks with the moves of the attack modules attached to the equipped weapon
    /// (each click the next one; a click during an attack queues the next), the right button held raises the shield (a
    /// loadout with a shield). The skeleton keeps its hit reactions; with <c>invulnerable</c> it never loses health.
    /// </summary>
    [RequireComponent(typeof(SkeletonNavController))]
    [DisallowMultipleComponent]
    public class PlayerSkeleton : MonoBehaviour
    {
        [Tooltip("Degrees of turn per pixel of mouse movement.")]
        public float mouseSensitivity = 0.15f;
        [Tooltip("The character cannot die (its health never drops); it still flinches and plays hit clips.")]
        public bool invulnerable = true;
        [Tooltip("Scales the damage of the player's attacks.")]
        public float damageScale = 1.5f;
        [Tooltip("Attack clip speed (1 = as authored).")]
        public float attackSpeed = 1.1f;
        [Tooltip("Read input (off while a menu is open).")]
        public bool inputEnabled = true;
        [ColorUsage(false, true)] public Color magicColor = new Color(0.4f, 2.2f, 1.1f);

        SkeletonNavController _nav;
        SkeletonHealth _health;
        SkeletonAI _ai;
        Animator _animator;
        UndeadLegion.Demo.SkeletonWeapon _weapon;
        int _leftArmLayer = -1;
        bool _blocking;
        int _attackIndex, _attackLoadout = int.MinValue;
        bool _queued;
        Coroutine _attack;
        float _attackEnds, _attackLength;

        /// <summary>Raised when the player's skeleton is hit (blocked or not).</summary>
        public event System.Action<DamageInfo, bool> Hit;

        public bool IsBlocking { get { return _blocking; } }
        public bool IsAttacking { get { return _attack != null; } }
        /// <summary>The move the next click plays.</summary>
        public string NextAttack { get { var m = Moves(); return m.Count > 0 ? m[_attackIndex % m.Count].clip : ""; } }

        void Awake()
        {
            _nav = GetComponent<SkeletonNavController>();
            _health = GetComponent<SkeletonHealth>();
            _ai = GetComponent<SkeletonAI>();
            _animator = GetComponent<Animator>();
            _weapon = GetComponent<UndeadLegion.Demo.SkeletonWeapon>();
            if (_animator != null) _leftArmLayer = _animator.GetLayerIndex("LeftArm");
        }

        void OnEnable()
        {
            if (_ai != null) { _ai.enabled = false; _ai.target = null; }   // the AI's attack modules stay the source of the moves
            _nav.manual = true;
            if (_health != null) { _health.invulnerable = invulnerable; _health.onDamaged.AddListener(OnDamaged); }
        }

        void OnDisable()
        {
            _nav.manual = false; _nav.ManualVelocity = Vector3.zero;
            if (_health != null) { _health.onDamaged.RemoveListener(OnDamaged); _health.blocking = false; }
            SetBlock(false);
        }

        void OnDamaged(DamageInfo info) { if (Hit != null) Hit(info, _health != null && _health.LastHitBlocked); }

        List<AttackMove> Moves()
        {
            return _ai != null ? _ai.CurrentMoves() : new List<AttackMove>();
        }

        bool HasShield()
        {
            string lo = _weapon != null && _weapon.Current >= 0 ? _weapon.NameAt(_weapon.Current) : "";
            return lo.ToLowerInvariant().Contains("shield");
        }

        void Update()
        {
            if (_health != null && _health.IsDead) return;
            if (!inputEnabled || Time.timeScale <= 0f) { _nav.ManualVelocity = Vector3.zero; return; }

            // turn: the mouse yaws the body (also during an attack, so a swing can be aimed)
            transform.Rotate(0f, ExtendedInput.MouseDelta.x * mouseSensitivity, 0f, Space.World);

            // move: forward / back / sideways at the clips' measured speeds; Shift + forward runs
            float f = (ExtendedInput.Key(KeyCode.W) ? 1f : 0f) - (ExtendedInput.Key(KeyCode.S) ? 1f : 0f);
            float s = (ExtendedInput.Key(KeyCode.D) ? 1f : 0f) - (ExtendedInput.Key(KeyCode.A) ? 1f : 0f);
            bool run = f > 0f && ExtendedInput.Key(KeyCode.LeftShift);
            float z = f > 0f ? (run ? _nav.RunSpeed : _nav.WalkSpeed) : f < 0f ? -_nav.BackSpeed : 0f;
            _nav.ManualVelocity = new Vector3(s * _nav.StrafeSpeed, 0f, z);

            // block: hold the right button with a shield
            SetBlock(ExtendedInput.Button(1) && HasShield());

            // attack: each click the next move; a click late in an attack queues the next one
            if (ExtendedInput.ButtonDown(0) && !ExtendedInput.PointerOverUI)
            {
                if (_attack == null) _attack = StartCoroutine(Attack());
                else if (Time.time > _attackEnds - _attackLength * 0.5f) _queued = true;
            }
        }

        void SetBlock(bool on)
        {
            if (on == _blocking) return;
            _blocking = on;
            if (_health != null) _health.blocking = on;
            if (_animator == null || _leftArmLayer < 0) return;
            if (on && _animator.HasState(_leftArmLayer, Animator.StringToHash("Block_L_Idle"))) _animator.CrossFadeInFixedTime("Block_L_Idle", 0.15f, _leftArmLayer);
            else if (!on) _animator.CrossFadeInFixedTime("Empty", 0.2f, _leftArmLayer);
        }

        IEnumerator Attack()
        {
            do
            {
                _queued = false;
                var moves = Moves();
                int cur = _weapon != null ? _weapon.Current : -1;
                if (cur != _attackLoadout) { _attackLoadout = cur; _attackIndex = 0; }
                if (moves.Count == 0) break;
                var m = moves[_attackIndex % moves.Count]; _attackIndex++;
                float len = _nav.PlayAction(m.clip, attackSpeed);
                _attackLength = len; _attackEnds = Time.time + len;
                float t = 0f, hit = len * m.hitAt;
                while (t < hit) { t += Time.deltaTime; yield return null; }
                Strike(m);
                while (t < len) { t += Time.deltaTime; yield return null; }
            } while (_queued && inputEnabled);
            _attack = null;
        }

        /// <summary>The nearest living enemy within range and a cone ahead (null if none).</summary>
        public SkeletonHealth EnemyAhead(float range, float halfAngle)
        {
            SkeletonHealth best = null; float bd = float.MaxValue;
            int team = _health != null ? _health.team : 0;
            foreach (var h in SkeletonHealth.All)
            {
                if (h == null || h == _health || h.IsDead || h.team == team) continue;
                Vector3 d = h.transform.position - transform.position; d.y = 0f;
                float dist = d.magnitude;
                if (dist > range || Vector3.Angle(transform.forward, d) > halfAngle) continue;
                if (dist < bd) { bd = dist; best = h; }
            }
            return best;
        }

        void Strike(AttackMove m)
        {
            float dmg = m.damage * damageScale;
            int team = _health != null ? _health.team : 0;
            if (m.area)
            {
                var t = EnemyAhead(m.range, 30f);
                Vector3 centre = t != null ? t.transform.position : transform.position + transform.forward * Mathf.Min(6f, m.range);
                foreach (var h in new List<SkeletonHealth>(SkeletonHealth.All))
                {
                    if (h == null || h.IsDead || h.team == team) continue;
                    Vector3 d = h.transform.position - centre; if (d.magnitude > 3f) continue;
                    h.TakeDamage(dmg, MagicBolt.AimPoint(h), (d.normalized + Vector3.up * 0.8f).normalized * m.impulse, gameObject);
                }
                return;
            }
            if (m.ranged)
            {
                var t = EnemyAhead(m.range, m.arrow ? 12f : 30f);
                if (m.arrow)
                {
                    // the visible arrow is the bow's own (SkeletonWeapon fires it along the forward on BowRelease)
                    if (t != null) StartCoroutine(ArrowHit(t, Vector3.Distance(transform.position, t.transform.position) / 15f, dmg, m.impulse));
                    return;
                }
                Vector3 from = HandPoint();
                Vector3 aim = t != null ? MagicBolt.AimPoint(t) : from + transform.forward * m.range;
                MagicBolt.Launch(from, t, aim, magicColor, dmg, gameObject);
                return;
            }
            foreach (var h in new List<SkeletonHealth>(SkeletonHealth.All))   // a melee blow hits everyone in front, within reach
            {
                if (h == null || h.IsDead || h.team == team) continue;
                Vector3 d = h.transform.position - transform.position; d.y = 0f;
                if (d.magnitude > m.range + 0.4f || Vector3.Angle(transform.forward, d) > 70f) continue;
                h.TakeDamage(dmg, MagicBolt.AimPoint(h), (transform.forward + Vector3.up * 0.15f).normalized * m.impulse, gameObject);
            }
        }

        IEnumerator ArrowHit(SkeletonHealth t, float delay, float dmg, float impulse)
        {
            yield return new WaitForSeconds(delay);
            if (t != null && !t.IsDead) t.TakeDamage(dmg, MagicBolt.AimPoint(t), transform.forward * impulse, gameObject);
        }

        Vector3 HandPoint()
        {
            var hand = _animator != null && _animator.isHuman ? _animator.GetBoneTransform(HumanBodyBones.RightHand) : null;
            return hand != null ? hand.position : transform.position + Vector3.up * 1.3f;
        }
    }
}
