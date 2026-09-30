using UnityEngine;

namespace UndeadLegion.Extended
{
    /// <summary>A top-down battle camera: WASD / arrows or middle-drag to pan, right-drag or Q / E to rotate, wheel to zoom.</summary>
    public class RtsCamera : MonoBehaviour
    {
        public Vector3 focus = Vector3.zero;
        public float distance = 16f;
        public float minDistance = 4f, maxDistance = 40f;
        [Range(15f, 85f)] public float pitch = 50f;
        public float yaw = 0f;
        public float panSpeed = 10f;
        public float rotateSpeed = 0.25f;
        public float zoomStep = 0.12f;
        public Vector2 bounds = new Vector2(30f, 30f);

        void LateUpdate()
        {
            float dt = Time.unscaledDeltaTime;
            Vector3 fwd = Quaternion.Euler(0f, yaw, 0f) * Vector3.forward, right = Quaternion.Euler(0f, yaw, 0f) * Vector3.right;
            Vector3 move = Vector3.zero;
            if (ExtendedInput.Key(KeyCode.W) || ExtendedInput.Key(KeyCode.UpArrow)) move += fwd;
            if (ExtendedInput.Key(KeyCode.S) || ExtendedInput.Key(KeyCode.DownArrow)) move -= fwd;
            if (ExtendedInput.Key(KeyCode.D) || ExtendedInput.Key(KeyCode.RightArrow)) move += right;
            if (ExtendedInput.Key(KeyCode.A) || ExtendedInput.Key(KeyCode.LeftArrow)) move -= right;
            focus += move * panSpeed * dt * (distance / 16f);
            if (ExtendedInput.Button(2)) { var d = ExtendedInput.MouseDelta; focus -= (right * d.x + fwd * d.y) * 0.02f * (distance / 16f); }
            if (ExtendedInput.Button(1)) yaw += ExtendedInput.MouseDelta.x * rotateSpeed;
            if (ExtendedInput.Key(KeyCode.Q)) yaw -= 90f * dt;
            if (ExtendedInput.Key(KeyCode.E)) yaw += 90f * dt;
            if (!ExtendedInput.PointerOverUI)
            {
                float s = ExtendedInput.Scroll;
                if (Mathf.Abs(s) > 0.01f) distance = Mathf.Clamp(distance * (1f - s * zoomStep), minDistance, maxDistance);
            }
            focus.x = Mathf.Clamp(focus.x, -bounds.x, bounds.x); focus.z = Mathf.Clamp(focus.z, -bounds.y, bounds.y);
            var rot = Quaternion.Euler(pitch, yaw, 0f);
            transform.position = focus - rot * Vector3.forward * distance;
            transform.rotation = rot;
        }
    }
}
