using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// Freezes the feet while a looping idle plays on the Base layer (2026-09-28, user: "a subtle feet drift for
    /// idle, idle_02, idle_03 - freeze them").
    ///
    /// The clips' feet are static to 0.0 mm in Blender; the 1-4 mm they wander in Unity over a 40-70 mm hips sway is
    /// Humanoid's leg reconstruction (the muscle round trip), and the imported foot IK goals carry the same error
    /// because they are generated from the retargeted pose, so the state's own foot IK cannot remove it. This
    /// component does: once the Base layer has settled on a looping idle (clip name starting with <see cref="idlePrefix"/>,
    /// no transition running) it captures both feet's IK goals ONCE, in the character's own space, and holds them
    /// with full weight until the next state begins, fading in over <see cref="fadeIn"/> and out over
    /// <see cref="fadeOut"/>. Needs the Base layer's IK Pass (the controller builder sets it). Nothing else is touched:
    /// the hips keep swaying, the knees follow through the IK.
    /// </summary>
    [RequireComponent(typeof(Animator))]
    public class SkeletonFootLock : MonoBehaviour
    {
        [Tooltip("Base-layer clips whose name starts with this, and loop, get their feet locked.")]
        public string idlePrefix = "Idle";
        public bool lockRotation = true;
        public float fadeIn = 0.15f;
        public float fadeOut = 0.12f;
        public bool enabledLock = true;

        Animator _an;
        bool _captured;
        float _w;
        Vector3 _pl, _pr;          // goals in the character's local space
        Quaternion _rl, _rr;

        /// <summary>Current lock weight (0..1), for diagnostics.</summary>
        public float Weight { get { return _w; } }

        void Awake() { _an = GetComponent<Animator>(); }

        bool IdleSettled()
        {
            if (_an == null || !_an.isHuman || _an.IsInTransition(0)) return false;
            var infos = _an.GetCurrentAnimatorClipInfo(0);
            if (infos == null || infos.Length == 0 || infos[0].clip == null) return false;
            var clip = infos[0].clip;
            return clip.isLooping && clip.name.StartsWith(idlePrefix);
        }

        void OnAnimatorIK(int layerIndex)
        {
            if (layerIndex != 0 || _an == null) return;
            bool idle = enabledLock && IdleSettled();
            if (idle && !_captured)
            {
                _pl = transform.InverseTransformPoint(_an.GetIKPosition(AvatarIKGoal.LeftFoot));
                _pr = transform.InverseTransformPoint(_an.GetIKPosition(AvatarIKGoal.RightFoot));
                _rl = Quaternion.Inverse(transform.rotation) * _an.GetIKRotation(AvatarIKGoal.LeftFoot);
                _rr = Quaternion.Inverse(transform.rotation) * _an.GetIKRotation(AvatarIKGoal.RightFoot);
                _captured = true; _w = 0f;
            }
            float dt = Time.deltaTime;
            if (idle) _w = fadeIn > 0f ? Mathf.MoveTowards(_w, 1f, dt / fadeIn) : 1f;
            else _w = fadeOut > 0f ? Mathf.MoveTowards(_w, 0f, dt / fadeOut) : 0f;
            if (!idle && _w <= 0f) { _captured = false; return; }
            if (!_captured) return;
            _an.SetIKPositionWeight(AvatarIKGoal.LeftFoot, _w); _an.SetIKPositionWeight(AvatarIKGoal.RightFoot, _w);
            _an.SetIKPosition(AvatarIKGoal.LeftFoot, transform.TransformPoint(_pl)); _an.SetIKPosition(AvatarIKGoal.RightFoot, transform.TransformPoint(_pr));
            if (lockRotation)
            {
                _an.SetIKRotationWeight(AvatarIKGoal.LeftFoot, _w); _an.SetIKRotationWeight(AvatarIKGoal.RightFoot, _w);
                _an.SetIKRotation(AvatarIKGoal.LeftFoot, transform.rotation * _rl); _an.SetIKRotation(AvatarIKGoal.RightFoot, transform.rotation * _rr);
            }
        }
    }
}
