using UnityEngine;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// A third-person camera behind a target: it follows the target's position and yaw (the mouse turns the character, the
    /// camera turns with it), the wheel zooms, and <see cref="Shake"/> adds a short kick when the target is hit.
    /// </summary>
    public class PlayerCamera : MonoBehaviour
    {
        public Transform target;
        public float distance = 3.6f;
        public float minDistance = 2f, maxDistance = 7f;
        [Tooltip("Height of the point the camera looks at, above the target's root.")]
        public float lookHeight = 1.45f;
        [Tooltip("Sideways offset of the look point (over the right shoulder).")]
        public float shoulder = 0.45f;
        [Range(0f, 60f)] public float pitch = 14f;
        [Tooltip("How fast the camera catches up with the target's position, per second.")]
        public float followDamping = 12f;
        [Tooltip("How fast the camera catches up with the target's yaw, per second.")]
        public float yawDamping = 14f;

        float _yaw, _shake;
        bool _snapped;

        /// <summary>A short camera kick (0..1).</summary>
        public void Shake(float amount) { _shake = Mathf.Max(_shake, Mathf.Clamp01(amount)); }

        /// <summary>Puts the camera behind the target at once (after the target changed).</summary>
        public void Snap() { _snapped = false; }

        void LateUpdate()
        {
            if (target == null) return;
            float dt = Time.unscaledDeltaTime;
            if (Time.timeScale > 0f)
            {
                float scroll = ExtendedInput.Scroll;
                if (Mathf.Abs(scroll) > 0.01f) distance = Mathf.Clamp(distance * (1f - scroll * 0.1f), minDistance, maxDistance);
            }
            float targetYaw = target.eulerAngles.y;
            _yaw = _snapped ? Mathf.LerpAngle(_yaw, targetYaw, 1f - Mathf.Exp(-yawDamping * dt)) : targetYaw;
            var rot = Quaternion.Euler(pitch, _yaw, 0f);
            Vector3 look = target.position + Vector3.up * lookHeight + rot * Vector3.right * shoulder;
            Vector3 want = look - rot * Vector3.forward * distance;
            transform.position = _snapped ? Vector3.Lerp(transform.position, want, 1f - Mathf.Exp(-followDamping * dt)) : want;
            transform.rotation = rot;
            if (_shake > 0f)
            {
                float s = _shake * _shake;
                transform.position += (Vector3)(Random.insideUnitCircle * 0.06f * s);
                transform.rotation *= Quaternion.Euler(Random.Range(-1f, 1f) * 2.5f * s, Random.Range(-1f, 1f) * 2.5f * s, 0f);
                _shake = Mathf.Max(0f, _shake - dt * 3f);
            }
            _snapped = true;
        }
    }
}
