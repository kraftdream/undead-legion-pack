using UnityEngine;
using UnityEngine.EventSystems;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace UndeadLegion.Demo
{
    /// <summary>
    /// Orbits the camera around the showcased character: auto-rotation, plus mouse-drag to
    /// look around by hand and wheel to zoom.
    ///
    /// The pivot follows the character's XZ so that clips played with root motion enabled
    /// stay framed instead of running out of shot.
    ///
    /// Input is read through BOTH backends: a project set to the new Input System only
    /// throws on UnityEngine.Input, and a project without the Input System package cannot
    /// compile against UnityEngine.InputSystem. Same reason DemoEventSystemBootstrap exists.
    /// </summary>
    [RequireComponent(typeof(Camera))]
    public class DemoTurntable : MonoBehaviour
    {
        public Transform target;

        [Header("Framing")]
        public float distance = 4.6f;
        public float height = 1.7f;
        public float lookAtHeight = 0.85f;

        [Header("Rotation")]
        public bool autoRotate = true;
        public float degreesPerSecond = 12f;
        public float startAngle = 145f;

        [Tooltip("How quickly the pivot catches up to a character moving under root motion.")]
        public float followLerp = 3f;

        [Header("Mouse drag")]
        public bool allowDrag = true;
        public float dragSensitivity = 0.28f;
        public float minPitch = -12f;
        public float maxPitch = 62f;
        [Tooltip("Scroll wheel zoom, as a FRACTION of the current distance per notch.")]
        public float zoomSensitivity = 0.18f;
        public float minDistance = 1.6f;
        public float maxDistance = 14f;

        /// <summary>Raised the first frame the viewer drags, so the demo can switch the
        /// Turntable toggle off: auto-rotation fighting a hand-placed camera reads as the
        /// drag not working.</summary>
        public System.Action onUserTookOver;

        float _angle;
        float _pitch;
        Vector3 _pivot;
        bool _dragging;

        void Start()
        {
            _angle = startAngle;
            _pitch = Mathf.Clamp(20f, minPitch, maxPitch);
            _pivot = target != null ? target.position : Vector3.zero;
            Apply();
        }

        void LateUpdate()
        {
            HandleInput();
            if (autoRotate && !_dragging) _angle += degreesPerSecond * Time.deltaTime;

            var wanted = target != null ? target.position : Vector3.zero;
            wanted.y = 0f;
            _pivot = Vector3.Lerp(_pivot, wanted, 1f - Mathf.Exp(-followLerp * Time.deltaTime));
            Apply();
        }

        void HandleInput()
        {
            if (!allowDrag) { _dragging = false; return; }

            bool held; Vector2 delta; float scroll;
            ReadMouse(out held, out delta, out scroll);

            // Don't orbit while the pointer is over the UI, or every click on a clip
            // button would also swing the camera.
            if (held && !_dragging && IsPointerOverUI()) held = false;

            if (held)
            {
                if (!_dragging)
                {
                    _dragging = true;
                    if (autoRotate && onUserTookOver != null) onUserTookOver();
                }
                // The mouse moves the CAMERA, not the subject.
                _angle += delta.x * dragSensitivity;
                _pitch = Mathf.Clamp(_pitch - delta.y * dragSensitivity, minPitch, maxPitch);
            }
            else
            {
                _dragging = false;
            }

            if (Mathf.Abs(scroll) > 0.01f && !IsPointerOverUI())
            {
                // One notch is a constant FRACTION of the distance: fine control close
                // in, fast travel far out.
                float step = scroll * zoomSensitivity * Mathf.Max(1f, distance);
                distance = Mathf.Clamp(distance - step, minDistance, maxDistance);
            }
        }

        static bool IsPointerOverUI()
        {
            return EventSystem.current != null && EventSystem.current.IsPointerOverGameObject();
        }

        static void ReadMouse(out bool held, out Vector2 delta, out float scroll)
        {
            held = false; delta = Vector2.zero; scroll = 0f;
#if ENABLE_INPUT_SYSTEM
            var m = Mouse.current;
            if (m != null)
            {
                held = m.leftButton.isPressed || m.rightButton.isPressed;
                delta = m.delta.ReadValue();
                // Backends disagree about the unit of one wheel notch (raw WHEEL_DELTA
                // 120 or a normalised 1.0). Normalise on magnitude so one notch is 1.
                float raw = m.scroll.ReadValue().y;
                scroll = Mathf.Abs(raw) >= 10f ? raw / 120f : raw;
            }
#else
            held = Input.GetMouseButton(0) || Input.GetMouseButton(1);
            delta = new Vector2(Input.GetAxis("Mouse X"), Input.GetAxis("Mouse Y")) * 10f;
            scroll = Input.mouseScrollDelta.y;
#endif
        }

        void Apply()
        {
            var rad = _angle * Mathf.Deg2Rad;
            var pitchRad = _pitch * Mathf.Deg2Rad;
            var flat = new Vector3(Mathf.Sin(rad), 0f, Mathf.Cos(rad));
            var offset = flat * (distance * Mathf.Cos(pitchRad));
            float y = height + distance * Mathf.Sin(pitchRad);
            transform.position = _pivot + offset + Vector3.up * y;
            transform.LookAt(_pivot + Vector3.up * lookAtHeight);
        }
    }
}
