using UnityEngine;
using UnityEngine.AI;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// Moves a skeleton with a NavMeshAgent and animates it to match. The agent's velocity, in the character's frame, drives
    /// a 2D locomotion blend tree whose clips sit at their measured speeds, so the feet keep pace with the ground. Two gaits:
    /// Heavy (the shambling _01 set) and Upright (the _02 set). While moving, the weapon's idle pose holds the upper body;
    /// when the agent stops, the full weapon idle takes over. Also the entry point for one-shot actions (attacks, casts).
    /// </summary>
    [RequireComponent(typeof(NavMeshAgent))]
    [DisallowMultipleComponent]
    public class SkeletonNavController : MonoBehaviour
    {
        public enum Gait { Heavy, Upright }

        public Gait gait = Gait.Heavy;
        [Tooltip("Run instead of walk when moving to a destination.")]
        public bool run = false;
        [Tooltip("Idle state played when standing (per weapon; set automatically from the loadout when empty).")]
        public string idleState = "";
        [Tooltip("Seconds of smoothing on the blend-tree parameters.")]
        public float parameterDamping = 0.12f;
        [Tooltip("Degrees per second the agent turns.")]
        public float turnSpeed = 360f;

        // measured on the shipped clips (Unity, Humanoid, root motion): walk / run / back / strafe, m/s
        static readonly float[] HeavySpeeds = { 0.52f, 1.14f, 0.34f, 0.20f };
        static readonly float[] UprightSpeeds = { 1.28f, 1.87f, 0.77f, 0.93f };

        static readonly int MoveX = Animator.StringToHash("MoveX");
        static readonly int MoveZ = Animator.StringToHash("MoveZ");

        NavMeshAgent _agent;
        Animator _animator;
        UndeadLegion.Demo.SkeletonWeapon _weapon;
        UndeadLegion.Demo.SkeletonFootLock _footLock;
        int _upperLayer = -1;
        bool _moving, _busy;
        float _busyUntil;
        string _upperPlaying = "";
        string _basePlaying = "";

        public NavMeshAgent Agent { get { return _agent; } }
        public bool IsBusy { get { return _busy; } }
        public bool IsMoving { get { return _moving; } }

        void Awake()
        {
            _agent = GetComponent<NavMeshAgent>();
            _animator = GetComponent<Animator>();
            _weapon = GetComponent<UndeadLegion.Demo.SkeletonWeapon>();
            _footLock = GetComponent<UndeadLegion.Demo.SkeletonFootLock>();
            _agent.updateRotation = true;
            _agent.angularSpeed = turnSpeed;
            _agent.acceleration = 6f;
            _agent.stoppingDistance = 0.1f;
            if (_animator != null)
            {
                _animator.applyRootMotion = false;
                _upperLayer = _animator.GetLayerIndex("UpperBody");
            }
        }

        void Start() { ApplyGait(); PlayIdle(true); }

        public float WalkSpeed { get { return (gait == Gait.Heavy ? HeavySpeeds : UprightSpeeds)[0]; } }
        public float RunSpeed { get { return (gait == Gait.Heavy ? HeavySpeeds : UprightSpeeds)[1]; } }
        string LocomotionState { get { return gait == Gait.Heavy ? "Locomotion_Heavy" : "Locomotion_Upright"; } }

        public void ApplyGait() { if (_agent != null) _agent.speed = run ? RunSpeed : WalkSpeed; }

        /// <summary>Walks (or runs) to a point on the NavMesh.</summary>
        public bool MoveTo(Vector3 destination, bool? running = null)
        {
            if (_agent == null || !_agent.isActiveAndEnabled || !_agent.isOnNavMesh) return false;
            if (running.HasValue) run = running.Value;
            ApplyGait();
            _agent.isStopped = false;
            return _agent.SetDestination(destination);
        }

        public void Stop()
        {
            if (_agent != null && _agent.isActiveAndEnabled && _agent.isOnNavMesh) { _agent.isStopped = true; _agent.ResetPath(); }
        }

        /// <summary>The idle this loadout stands in: the weapon's own idle, or the one-handed combat idle.</summary>
        public string WeaponIdle()
        {
            if (!string.IsNullOrEmpty(idleState)) return idleState;
            string lo = _weapon != null && _weapon.Current >= 0 ? _weapon.NameAt(_weapon.Current) : "";
            if (lo.Contains("(2H)")) return "Idle_TwoHanded";
            if (lo.Contains("bow")) return "Idle_Bow";
            if (lo == "Staff") return "Idle_Staff";
            if (lo.Length > 0) return "Idle_1H_Combat";
            return "Idle_01";
        }

        void PlayIdle(bool force)
        {
            var idle = WeaponIdle();
            if (!force && _basePlaying == idle) return;
            _animator.CrossFadeInFixedTime(idle, 0.25f, 0); _basePlaying = idle;
        }

        /// <summary>Faces a point on the ground (turns the agent in place).</summary>
        public void FaceTowards(Vector3 point, float maxDegrees = 720f)
        {
            Vector3 d = point - transform.position; d.y = 0f;
            if (d.sqrMagnitude < 1e-4f) return;
            transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(d), maxDegrees);
        }

        /// <summary>Plays a one-shot (an attack or a cast) on the Base layer; the skeleton stops and returns to its idle after it.</summary>
        public float PlayAction(string state, float speed = 1f)
        {
            if (_animator == null) return 0f;
            Stop();
            float len = ClipLength(state);
            _animator.speed = speed;
            _animator.CrossFadeInFixedTime(state, 0.12f, 0); _basePlaying = state;
            if (_upperLayer >= 0 && _upperPlaying != "Empty") { _animator.CrossFadeInFixedTime("Empty", 0.12f, _upperLayer); _upperPlaying = "Empty"; }
            _busy = true; _busyUntil = Time.time + len / Mathf.Max(0.01f, speed);
            return len / Mathf.Max(0.01f, speed);
        }

        // The agent moves the skeleton while it walks; during a one-shot the clip's own root motion (a lunge, a step into a
        // cast) moves it instead, through the agent so it stays on the NavMesh.
        void OnAnimatorMove()
        {
            if (_animator == null || !_busy) return;
            Vector3 d = _animator.deltaPosition; d.y = 0f;
            if (_agent != null && _agent.enabled && _agent.isOnNavMesh) _agent.Move(d);
            else transform.position += d;
            transform.rotation = _animator.deltaRotation * transform.rotation;
        }

        public float ClipLength(string clipName)
        {
            if (_animator == null || _animator.runtimeAnimatorController == null) return 1f;
            foreach (var c in _animator.runtimeAnimatorController.animationClips) if (c != null && c.name == clipName) return c.length;
            return 1f;
        }

        void Update()
        {
            if (_animator == null || _agent == null || !_animator.enabled) return;
            if (_busy && Time.time >= _busyUntil) { _busy = false; _animator.speed = 1f; _basePlaying = ""; }
            if (_busy) { _animator.SetFloat(MoveX, 0f); _animator.SetFloat(MoveZ, 0f); return; }

            Vector3 v = _agent.enabled ? _agent.velocity : Vector3.zero;
            Vector3 local = transform.InverseTransformDirection(v);
            bool moving = v.sqrMagnitude > 0.0025f || (_agent.enabled && _agent.hasPath && _agent.remainingDistance > _agent.stoppingDistance + 0.05f);
            _animator.SetFloat(MoveX, local.x, parameterDamping, Time.deltaTime);
            _animator.SetFloat(MoveZ, local.z, parameterDamping, Time.deltaTime);

            if (moving && !_moving)
            {
                _animator.CrossFadeInFixedTime(LocomotionState, 0.2f, 0); _basePlaying = LocomotionState;
                var idle = WeaponIdle();
                if (_upperLayer >= 0 && idle != "Idle_01" && _animator.HasState(_upperLayer, Animator.StringToHash(idle)))
                { _animator.CrossFadeInFixedTime(idle, 0.2f, _upperLayer); _upperPlaying = idle; }
            }
            else if (!moving && _moving)
            {
                PlayIdle(true);
                if (_upperLayer >= 0 && _upperPlaying != "Empty") { _animator.CrossFadeInFixedTime("Empty", 0.25f, _upperLayer); _upperPlaying = "Empty"; }
            }
            else if (!moving && string.IsNullOrEmpty(_basePlaying)) PlayIdle(true);
            _moving = moving;
            if (_footLock != null) _footLock.enabledLock = !moving;
        }

        /// <summary>Re-reads the loadout (call after equipping another weapon) so the idle and the upper-body pose follow it.</summary>
        public void OnLoadoutChanged() { if (!_moving && !_busy) PlayIdle(true); }
    }
}
