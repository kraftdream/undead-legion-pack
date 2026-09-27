using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// A bow whose string follows the archer's draw hand and whose limbs bend with the draw (2026-09-27).
    /// The bow model is exported skinned to a small rig (Weapons/prod.blend, `H2Recurvebow_Rig`): `Riser`,
    /// `Limb_U1/U2`, `Limb_L1/L2`, the string's centre `Nock` and two rest-point helpers `Brace` / `Pull`.
    /// While <see cref="attached"/> (an animation event `BowAttach` on the clip, received by
    /// <see cref="SkeletonWeapon.BowAttach"/>) the Nock is placed at the draw hand's slot, gated to the draw
    /// corridor exactly as the Blender reference does: only while the hand is behind the string plane and
    /// within <see cref="corridor"/> of the string's midpoint (the apex follows the fingers along the bow).
    /// The limbs bend <see cref="bendLimb1"/> / <see cref="bendLimb2"/> degrees at <see cref="fullDraw"/>.
    /// `BowRelease` lets the string go. Sits on the W_H2Recurvebow prefab; SkeletonWeapon hands it the slot.
    /// </summary>
    [DisallowMultipleComponent]
    public class BowString : MonoBehaviour
    {
        [Tooltip("The draw hand's slot (set by SkeletonWeapon on equip: the hand that does not hold the bow).")]
        public Transform drawHand;
        [Tooltip("The string follows the draw hand while this is on (BowAttach / BowRelease animation events).")]
        public bool attached;
        [Tooltip("Draw length (metres) at which the limbs reach their full bend: 0.28 rig m in Blender = 0.5 m here.")]
        public float fullDraw = 0.5f;
        [Tooltip("The draw hand counts as on the string only within this distance (metres) of the string's midpoint, measured across the draw axis.")]
        public float corridor = 0.5f;
        [Tooltip("Degrees of bend at full draw on the first and second limb segments (the Blender drivers' values).")]
        public float bendLimb1 = 10f, bendLimb2 = 14f;
        [Tooltip("How fast the string settles back after a release (metres per second); 0 = instant.")]
        public float returnSpeed = 8f;

        Transform _nock, _brace, _u1, _u2, _l1, _l2;
        Quaternion _rU1, _rU2, _rL1, _rL2;
        Vector3 _nockRestLocal;
        float _draw;                                   // the current draw (metres), smoothed on release
        Vector3 _apexLocal;                            // the apex's lateral offset in the brace's frame
        bool _ready;

        void Awake() { Resolve(); }

        /// <summary>Find the rig's bones by name (the FBX keeps Blender's bone names).</summary>
        public void Resolve()
        {
            foreach (var t in GetComponentsInChildren<Transform>(true))
            {
                switch (t.name)
                {
                    case "Nock": _nock = t; break;
                    case "Brace": _brace = t; break;
                    case "Limb_U1": _u1 = t; break;
                    case "Limb_U2": _u2 = t; break;
                    case "Limb_L1": _l1 = t; break;
                    case "Limb_L2": _l2 = t; break;
                }
            }
            _ready = _nock != null && _brace != null && _u1 != null && _u2 != null && _l1 != null && _l2 != null;
            if (!_ready) { Debug.LogWarning("BowString: the bow model has no rig bones (Nock/Brace/Limb_*): export it skinned", this); return; }
            _rU1 = _u1.localRotation; _rU2 = _u2.localRotation; _rL1 = _l1.localRotation; _rL2 = _l2.localRotation;
            _nockRestLocal = _nock.localPosition;
        }

        /// <summary>The string's draw right now, metres (0 at rest).</summary>
        public float Draw { get { return _draw; } }

        void LateUpdate()
        {
            if (!_ready) return;
            float target = 0f; Vector3 apex = Vector3.zero;
            if (attached && drawHand != null)
            {
                // the hand in the string's frame: the Brace bone's +Y is the draw axis (Blender's bone Y, kept by the FBX)
                Vector3 local = _brace.InverseTransformPoint(drawHand.position);
                float along = local.y;
                float lateral = Mathf.Sqrt(local.x * local.x + local.z * local.z);
                float gate = Mathf.Clamp01((corridor - lateral) / 0.05f) * Mathf.Clamp01(along / 0.025f);
                target = Mathf.Clamp(along, 0f, fullDraw * 1.6f) * gate;
                apex = new Vector3(local.x, 0f, local.z) * gate;
            }
            if (target >= _draw || returnSpeed <= 0f) { _draw = target; _apexLocal = apex; }
            else
            {
                _draw = Mathf.MoveTowards(_draw, target, returnSpeed * Time.deltaTime);
                _apexLocal = Vector3.MoveTowards(_apexLocal, apex, returnSpeed * Time.deltaTime);
            }
            // limbs first (the string's ends ride on the tips through the skinning), then the nock
            float k = Mathf.Clamp01(_draw / fullDraw);
            _u1.localRotation = _rU1 * Quaternion.AngleAxis(-bendLimb1 * k, Vector3.right);
            _u2.localRotation = _rU2 * Quaternion.AngleAxis(-bendLimb2 * k, Vector3.right);
            _l1.localRotation = _rL1 * Quaternion.AngleAxis(bendLimb1 * k, Vector3.right);
            _l2.localRotation = _rL2 * Quaternion.AngleAxis(bendLimb2 * k, Vector3.right);
            _nock.position = _brace.TransformPoint(new Vector3(_apexLocal.x, _draw, _apexLocal.z));
        }
    }
}
