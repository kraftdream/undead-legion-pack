using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// A fired arrow (2026-09-27): a copy of the arrow weapon prefab, launched by
    /// <see cref="SkeletonWeapon.BowRelease"/> along a fixed direction (the character's forward for now),
    /// flying straight at <see cref="speed"/> with an optional <see cref="gravity"/> drop, the shaft (the
    /// weapon prefab's +Y, head at +Y) kept along its velocity, destroyed after <see cref="lifetime"/> seconds
    /// or when it goes under the floor (y &lt; 0). Demo-side only: no collision, no damage.
    /// </summary>
    public class ArrowProjectile : MonoBehaviour
    {
        [Tooltip("Launch speed in metres per second.")]
        public float speed = 30f;
        [Tooltip("Downward acceleration (m/s^2); 0 = a dead-straight flight.")]
        public float gravity = 0f;
        [Tooltip("Seconds before the arrow is destroyed.")]
        public float lifetime = 4f;

        Vector3 _velocity;
        float _age;

        /// <summary>Start the flight along <paramref name="direction"/> (normalised inside).</summary>
        public void Launch(Vector3 direction)
        {
            _velocity = direction.normalized * speed;
            _age = 0f;
            Orient();
        }

        void Orient()
        {
            if (_velocity.sqrMagnitude < 1e-8f) return;
            // the prefab's shaft runs along its +Y: turn +Y onto the velocity (LookRotation gives +Z, then Y -> Z)
            transform.rotation = Quaternion.LookRotation(_velocity.normalized, Vector3.up) * Quaternion.Euler(90f, 0f, 0f);
        }

        void Update()
        {
            float dt = Time.deltaTime;
            _velocity += Vector3.down * gravity * dt;
            transform.position += _velocity * dt;
            if (gravity > 0f) Orient();
            _age += dt;
            if (_age >= lifetime || transform.position.y < 0f) Destroy(gameObject);
        }
    }
}
