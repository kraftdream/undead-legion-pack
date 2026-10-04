using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// A simple combat brain: pick the nearest living enemy (another team) in sight, chase it on the NavMesh, stop in range,
    /// face it and attack with the moves of the equipped weapon. Melee deals damage at the swing's hit moment; the bow, wand
    /// and staff fire projectiles; casters occasionally use the area cast. Idle skeletons can wander around their start.
    /// </summary>
    [RequireComponent(typeof(SkeletonNavController))]
    [RequireComponent(typeof(SkeletonHealth))]
    [DisallowMultipleComponent]
    public class SkeletonAI : MonoBehaviour
    {
        public enum Style { Auto, OneHanded, DualDaggers, TwoHanded, Bow, Wand, Staff, Unarmed }

        [Tooltip("Attack style; Auto reads it from the equipped loadout.")]
        public Style style = Style.Auto;
        public float sightRange = 18f;
        [Tooltip("Seconds between attacks (after the attack clip ends).")]
        public float attackCooldown = 0.6f;
        [Tooltip("Scales every attack's damage.")]
        public float damageScale = 1f;
        [Tooltip("Attack clip speed (1 = as authored).")]
        public float attackSpeed = 1f;
        [Tooltip("Metres to wander around the start point while no enemy is in sight (0 = stand).")]
        public float wanderRadius = 0f;
        [Tooltip("Metres beyond the attack's reach at which a running skeleton slows to a walk for the last steps.")]
        public float walkWithin = 0.8f;
        [Tooltip("Distance (metres, centre to centre) at which a melee skeleton stops and attacks.")]
        public float meleeRange = 1.1f;
        [Tooltip("An explicit target; otherwise the nearest enemy is chosen.")]
        public SkeletonHealth target;
        [ColorUsage(false, true)] public Color magicColor = new Color(0.4f, 2.2f, 1.1f);

        struct Move { public string clip; public float hitAt; public float range; public float damage; public float impulse; public bool ranged; public bool area; }

        static readonly Dictionary<Style, Move[]> Moves = new Dictionary<Style, Move[]>
        {
            { Style.OneHanded,   new[] { M("Attack_R_02_Swing", 0.46f, 1.7f, 20, 70), M("Attack_R_01_Stab", 0.30f, 1.8f, 18, 55), M("Attack_R_03_Swing", 0.50f, 1.7f, 20, 70),
                                         M("Attack_R_02_Swing_Heavy", 0.46f, 1.8f, 26, 90), M("Attack_R_03_Swing_Heavy", 0.48f, 1.8f, 26, 90) } },
            { Style.DualDaggers, new[] { M("Attack_R_01_Stab", 0.30f, 1.6f, 14, 45), M("Attack_L_02_Swing", 0.46f, 1.5f, 14, 55), M("Attack_L_01_Stab", 0.30f, 1.6f, 14, 45), M("Attack_R_02_Swing", 0.46f, 1.5f, 14, 55),
                                         M("Attack_L_03_Swing", 0.50f, 1.5f, 14, 55), M("Attack_R_03_Swing", 0.50f, 1.5f, 14, 55) } },
            { Style.TwoHanded,   new[] { M("Attack_2H_01_Swing", 0.54f, 2.1f, 35, 120), M("Attack_2H_02_Swing", 0.43f, 2.2f, 30, 110),
                                         M("Attack_2H_01_Swing_Heavy", 0.54f, 2.2f, 45, 150), M("Attack_2H_02_Swing_Heavy", 0.41f, 2.3f, 40, 140) } },   // hitAt = the hand-speed peak measured on each clip (2026-10-04)
            { Style.Bow,         new[] { R("Shoot_01", 21f / 59f, 16f, 28, 50) } },
            { Style.Wand,        new[] { R("Cast_Wand_01", 0.45f, 11f, 16, 35), R("Cast_Wand_02", 0.45f, 11f, 16, 35) } },
            { Style.Staff,       new[] { R("Cast_Staff_01", 0.55f, 12f, 24, 45), A("AOE_Cast", 0.62f, 9f, 30, 90) } },
            { Style.Unarmed,     new[] { M("Attack_R_02_Swing", 0.46f, 1.4f, 8, 40), M("Attack_L_02_Swing", 0.46f, 1.4f, 8, 40) } },
        };
        static Move M(string c, float at, float r, float d, float i) { return new Move { clip = c, hitAt = at, range = r, damage = d, impulse = i }; }
        static Move R(string c, float at, float r, float d, float i) { return new Move { clip = c, hitAt = at, range = r, damage = d, impulse = i, ranged = true }; }
        static Move A(string c, float at, float r, float d, float i) { return new Move { clip = c, hitAt = at, range = r, damage = d, impulse = i, ranged = true, area = true }; }

        SkeletonNavController _nav;
        SkeletonHealth _health;
        Animator _animator;
        UndeadLegion.Demo.SkeletonWeapon _weapon;
        Vector3 _home;
        float _nextAttack, _nextThink, _nextWander, _nextArea;
        int _moveIndex;
        Coroutine _attack;

        public bool InCombat { get { return target != null; } }

        /// <summary>While true (e.g. rising from the ground) the AI waits: no targeting, no moving, no attacks.</summary>
        public bool Suspended { get; set; }

        void Awake()
        {
            _nav = GetComponent<SkeletonNavController>();
            _health = GetComponent<SkeletonHealth>();
            _animator = GetComponent<Animator>();
            _weapon = GetComponent<UndeadLegion.Demo.SkeletonWeapon>();
            _health.onDied.AddListener(OnDied);
        }

        void Start() { _home = transform.position; }

        void OnDied() { if (_attack != null) StopCoroutine(_attack); _attack = null; target = null; enabled = false; }

        public Style CurrentStyle()
        {
            if (style != Style.Auto) return style;
            string lo = _weapon != null && _weapon.Current >= 0 ? _weapon.NameAt(_weapon.Current) : "";
            if (lo.Contains("(2H)")) return Style.TwoHanded;
            if (lo.Contains("bow")) return Style.Bow;
            if (lo == "Staff") return Style.Staff;
            if (lo == "Wand") return Style.Wand;
            if (lo == "Two daggers") return Style.DualDaggers;
            if (lo.Length > 0) return Style.OneHanded;
            return Style.Unarmed;
        }

        Move[] CurrentMoves() { Move[] m; return Moves.TryGetValue(CurrentStyle(), out m) ? m : Moves[Style.Unarmed]; }

        float PreferredRange()
        {
            var moves = CurrentMoves(); float r = float.MaxValue; bool melee = true;
            foreach (var m in moves) if (!m.area) { r = Mathf.Min(r, m.range); if (m.ranged) melee = false; }
            return melee ? meleeRange : r;
        }

        SkeletonHealth FindTarget()
        {
            SkeletonHealth best = null; float bd = sightRange * sightRange;
            foreach (var h in SkeletonHealth.All)
            {
                if (h == null || h == _health || h.IsDead || h.team == _health.team) continue;
                float d = (h.transform.position - transform.position).sqrMagnitude;
                if (d < bd) { bd = d; best = h; }
            }
            return best;
        }

        void Update()
        {
            if (_health.IsDead || _attack != null || _nav.IsBusy) return;
            if (Suspended) { if (_nav.IsMoving) _nav.Stop(); return; }
            if (Time.time >= _nextThink)
            {
                _nextThink = Time.time + 0.25f + Random.value * 0.1f;
                if (target == null || target.IsDead || (target.transform.position - transform.position).sqrMagnitude > sightRange * sightRange * 1.5f) target = FindTarget();
            }
            if (target == null) { Wander(); return; }

            Vector3 to = target.transform.position - transform.position; to.y = 0f;
            float dist = to.magnitude, range = PreferredRange();
            if (dist > range)
            {
                Vector3 goal = target.transform.position - to.normalized * range * 0.85f;
                _nav.MoveTo(goal, dist > range + walkWithin && CurrentStyle() != Style.Bow);   // run until just outside the reach
                return;
            }
            _nav.Stop();
            _nav.FaceTowards(target.transform.position, 200f * Time.deltaTime);   // a smooth re-aim between attacks (a target that moved)
            if (Time.time >= _nextAttack && Vector3.Angle(transform.forward, to) < 12f) _attack = StartCoroutine(Attack());
        }

        void Wander()
        {
            if (wanderRadius <= 0f || Time.time < _nextWander || _nav.IsMoving) return;
            _nextWander = Time.time + 3f + Random.value * 4f;
            var p = _home + Random.insideUnitSphere * wanderRadius; p.y = _home.y;
            _nav.MoveTo(p, false);
        }

        IEnumerator Attack()
        {
            var moves = CurrentMoves();
            Move m = moves[_moveIndex % moves.Length]; _moveIndex++;
            if (m.area)
            {
                if (Time.time < _nextArea) { m = moves[0]; }
                else _nextArea = Time.time + 8f;
            }
            float len = _nav.PlayAction(m.clip, attackSpeed);
            float hitTime = len * m.hitAt;
            float t = 0f;
            // no steering while the clip plays: its root motion carries the step and the body's turn (a cast turns side-on and
            // back); the attack only starts when facing the target within 12 degrees
            while (t < hitTime) { if (_health.IsDead) { _attack = null; yield break; } t += Time.deltaTime; yield return null; }
            Strike(m);
            while (t < len) { if (_health.IsDead) { _attack = null; yield break; } t += Time.deltaTime; yield return null; }
            _nextAttack = Time.time + attackCooldown * (0.7f + Random.value * 0.6f);
            _attack = null;
        }

        void Strike(Move m)
        {
            if (target == null || target.IsDead) return;
            float dmg = m.damage * damageScale;
            Vector3 aim = MagicBolt.AimPoint(target);
            if (m.area)
            {
                Vector3 centre = target.transform.position;
                foreach (var h in SkeletonHealth.All)
                {
                    if (h == null || h.IsDead || h.team == _health.team) continue;
                    Vector3 d = h.transform.position - centre; if (d.magnitude > 3f) continue;
                    Vector3 push = (d.normalized + Vector3.up * 0.8f).normalized * m.impulse;
                    h.TakeDamage(dmg, MagicBolt.AimPoint(h), push, gameObject);
                }
                AreaFlash(centre);
                return;
            }
            if (m.ranged)
            {
                var from = HandPoint();
                if (CurrentStyle() == Style.Bow)
                {
                    // the visible arrow is the weapon's own (SkeletonWeapon fires it on BowRelease); the hit lands after its flight time
                    float fly = Vector3.Distance(from, aim) / 15f;
                    StartCoroutine(Delayed(fly, () => { if (target != null && !target.IsDead) target.TakeDamage(dmg, MagicBolt.AimPoint(target), transform.forward * m.impulse, gameObject); }));
                }
                else MagicBolt.Launch(from, target, aim, magicColor, dmg, gameObject);
                return;
            }
            Vector3 toT = target.transform.position - transform.position; toT.y = 0f;
            if (toT.magnitude <= m.range + 0.4f && Vector3.Angle(transform.forward, toT) < 70f)
                target.TakeDamage(dmg, aim, (transform.forward + Vector3.up * 0.15f).normalized * m.impulse, gameObject);
        }

        Vector3 HandPoint()
        {
            var hand = _animator != null && _animator.isHuman ? _animator.GetBoneTransform(HumanBodyBones.RightHand) : null;
            return hand != null ? hand.position : transform.position + Vector3.up * 1.3f;
        }

        IEnumerator Delayed(float seconds, System.Action action) { yield return new WaitForSeconds(seconds); action(); }

        void AreaFlash(Vector3 at)
        {
            var go = new GameObject("AreaFlash"); go.transform.position = at + Vector3.up * 1.5f;
            var l = go.AddComponent<Light>(); l.type = LightType.Point; l.range = 4f; l.intensity = 0.5f; l.shadows = LightShadows.None;
            l.color = magicColor.maxColorComponent > 0f ? magicColor / magicColor.maxColorComponent : Color.white;
            StartCoroutine(FadeLight(l, 0.45f)); Destroy(go, 0.6f);
        }

        static IEnumerator FadeLight(Light l, float seconds)
        {
            float i0 = l.intensity, t = 0f;
            while (l != null && t < seconds) { t += Time.deltaTime; l.intensity = i0 * (1f - t / seconds); yield return null; }
            if (l != null) Destroy(l.gameObject);
        }
    }
}
