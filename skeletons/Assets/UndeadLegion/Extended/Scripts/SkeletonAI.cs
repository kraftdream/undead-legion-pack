using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// A simple combat brain: pick the nearest living enemy (another team) in sight, chase it on the NavMesh, stop in range,
    /// face it and attack with the moves of the ATTACK MODULES that attach to the equipped weapon (see AttackModule: swords
    /// and daggers regular one-handed attacks, axes and maces regular + heavy, a second dagger the left-hand attacks...).
    /// Melee deals damage at the swing's hit moment; the bow, wand and staff fire projectiles; casters occasionally use the
    /// area cast. Idle skeletons can wander around their start.
    /// </summary>
    [RequireComponent(typeof(SkeletonNavController))]
    [RequireComponent(typeof(SkeletonHealth))]
    [DisallowMultipleComponent]
    public class SkeletonAI : MonoBehaviour
    {
        [Tooltip("Attack modules; every module whose weapon list holds the equipped loadout adds its moves.")]
        public List<AttackModule> attackModules = AttackModule.Defaults();
        [Tooltip("Off: heavy modules are skipped (the assassin fights with regular attacks only).")]
        public bool allowHeavy = true;
        [Tooltip("Off: area moves (the staff's AOE cast) are skipped.")]
        public bool allowArea = true;
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
        [Tooltip("Distance (metres, centre to centre) at which a melee skeleton stops and attacks, for a weapon whose modules set no engageRange.")]
        public float meleeRange = 1.1f;
        [Tooltip("Once engaged, a melee skeleton keeps attacking until the target is this far (metres) beyond its engage distance.")]
        public float engageSlack = 0.3f;
        [Tooltip("Seconds a chasing skeleton may be blocked (others in the way) within its weapon's reach before it attacks from there.")]
        public float blockedAttackAfter = 0.4f;
        [Tooltip("An explicit target; otherwise the nearest enemy is chosen.")]
        public SkeletonHealth target;
        [ColorUsage(false, true)] public Color magicColor = new Color(0.4f, 2.2f, 1.1f);

        SkeletonNavController _nav;
        SkeletonHealth _health;
        Animator _animator;
        UndeadLegion.Demo.SkeletonWeapon _weapon;
        Vector3 _home;
        float _nextAttack, _nextThink, _nextWander, _nextArea;
        string _lastClip;
        int _movesFor = int.MinValue; bool _movesHeavy, _movesArea;
        float _engage, _blockedFor;
        bool _engaged;
        Vector3 _lastPos;
        readonly List<AttackMove> _moves = new List<AttackMove>();
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

        void OnValidate() { _movesFor = int.MinValue; }   // modules edited in the inspector: rebuild the move list

        void OnDied() { if (_attack != null) StopCoroutine(_attack); _attack = null; target = null; enabled = false; }

        /// <summary>The equipped loadout's name ("" when the skeleton holds nothing).</summary>
        public string CurrentLoadout()
        {
            return _weapon != null && _weapon.Current >= 0 ? _weapon.NameAt(_weapon.Current) : "";
        }

        /// <summary>The moves of every module attached to the equipped loadout (heavy ones only when allowed, area ones only when allowed).</summary>
        public List<AttackMove> CurrentMoves()
        {
            int cur = _weapon != null ? _weapon.Current : -1;
            if (cur == _movesFor && allowHeavy == _movesHeavy && allowArea == _movesArea && _moves.Count > 0) return _moves;
            _movesFor = cur; _movesHeavy = allowHeavy; _movesArea = allowArea; _moves.Clear(); _engage = 0f;
            if (!Collect(CurrentLoadout())) Collect("");   // a loadout no module knows: fight unarmed
            return _moves;
        }

        bool Collect(string loadout)
        {
            foreach (var mod in attackModules)
            {
                if (mod == null || !mod.AttachesTo(loadout) || (!allowHeavy && mod.heavy)) continue;
                foreach (var mv in mod.moves) if (mv != null && (allowArea || !mv.area)) _moves.Add(mv);
                if (mod.engageRange > 0f) _engage = _engage > 0f ? Mathf.Min(_engage, mod.engageRange) : mod.engageRange;
            }
            return _moves.Count > 0;
        }

        /// <summary>The shortest reach of the equipped weapon's melee moves (0 for a ranged weapon).</summary>
        float MeleeReach()
        {
            float r = float.MaxValue;
            foreach (var m in CurrentMoves()) { if (m.ranged) return 0f; r = Mathf.Min(r, m.range); }
            return r == float.MaxValue ? 0f : r;
        }

        /// <summary>Where this skeleton stops to attack with the equipped weapon: the nearest ranged move's range for a bow,
        /// wand or staff, else the weapon modules' engageRange (the shortest of the attached ones), else meleeRange.</summary>
        public float EngageRange()
        {
            var moves = CurrentMoves(); float r = float.MaxValue;
            foreach (var m in moves) if (m.ranged && !m.area) r = Mathf.Min(r, m.range);
            if (r < float.MaxValue) return r;
            return _engage > 0f ? _engage : meleeRange;
        }

        bool UsesBow() { foreach (var m in CurrentMoves()) if (m.arrow) return true; return false; }

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
                if (target == null || target.IsDead || (target.transform.position - transform.position).sqrMagnitude > sightRange * sightRange * 1.5f) { var t = FindTarget(); if (t != target) _engaged = false; target = t; }
            }
            if (target == null) { Wander(); return; }

            Vector3 to = target.transform.position - transform.position; to.y = 0f;
            float dist = to.magnitude, range = EngageRange();
            // blocked: chasing but hardly moving (other skeletons hold the spot); within the weapon's reach that is close enough
            Vector3 step = transform.position - _lastPos; step.y = 0f; _lastPos = transform.position;
            _blockedFor = _nav.IsMoving && step.magnitude < 0.1f * Time.deltaTime ? _blockedFor + Time.deltaTime : 0f;
            bool inRange = dist <= range || (_engaged && dist <= range + engageSlack) || (dist <= MeleeReach() && _blockedFor >= blockedAttackAfter);
            _engaged = inRange;
            if (!inRange)
            {
                Vector3 goal = target.transform.position - to.normalized * range * 0.85f;
                _nav.MoveTo(goal, dist > range + walkWithin && !UsesBow());   // run until just outside the reach
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
            var m = PickMove();
            if (m == null) { _nextAttack = Time.time + attackCooldown; _attack = null; yield break; }
            if (m.area) _nextArea = Time.time + 8f;
            float len = _nav.PlayAction(m.clip, attackSpeed * m.Speed);
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

        /// <summary>A random move of the attached modules, not the one just used (when there is a choice) and no area cast on cooldown.</summary>
        AttackMove PickMove()
        {
            var pool = new List<AttackMove>();
            foreach (var mv in CurrentMoves()) if (!(mv.area && Time.time < _nextArea)) pool.Add(mv);
            if (pool.Count == 0) return null;
            if (pool.Count > 1) pool.RemoveAll(mv => mv.clip == _lastClip);
            var pick = pool[Random.Range(0, pool.Count)];
            _lastClip = pick.clip;
            return pick;
        }

        void Strike(AttackMove m)
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
                if (m.arrow)
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
