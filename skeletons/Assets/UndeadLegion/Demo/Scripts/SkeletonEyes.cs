using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>Two small glowing lights in the eye sockets, following the head. The colour is HDR, so bloom makes them glow.</summary>
    [DisallowMultipleComponent]
    public class SkeletonEyes : MonoBehaviour
    {
        [ColorUsage(false, true)] public Color color = new Color(5f, 0.2f, 0.1f);   // red, HDR: glows under Bloom
        [Tooltip("Eye position from the head bone, in the character's frame (x right, y up, z forward), metres.")]
        public Vector3 offset = new Vector3(0.030f, 0.023f, 0.075f);
        public float size = 0.018f;
        [Tooltip("Adds a faint point light in front of the face (costs a light per skeleton; off for crowds).")]
        public bool addLight = false;

        Transform _left, _right;
        MaterialPropertyBlock _mpb;
        static Material _mat;

        void Awake()          // created with the character, so a spawner that hides its renderers hides the eyes too
        {
            var an = GetComponent<Animator>();
            var head = an != null && an.isHuman ? an.GetBoneTransform(HumanBodyBones.Head) : null;
            if (head == null) return;
            if (_mat == null)
            {
                var sh = Shader.Find("Universal Render Pipeline/Unlit");
                _mat = new Material(sh != null ? sh : Shader.Find("Unlit/Color"));
            }
            _left = Make(head, new Vector3(-offset.x, offset.y, offset.z), "EyeL");
            _right = Make(head, new Vector3(offset.x, offset.y, offset.z), "EyeR");
            if (addLight)
            {
                var lg = new GameObject("EyeLight"); lg.transform.SetParent(head, false);
                lg.transform.position = head.position + transform.rotation * new Vector3(0f, offset.y, offset.z + 0.3f);
                var l = lg.AddComponent<Light>(); l.type = LightType.Point; l.range = 0.6f; l.intensity = 0.15f; l.shadows = LightShadows.None;
                l.color = color.linear.maxColorComponent > 0 ? (color / color.maxColorComponent) : Color.white;
            }
            SetColor(color);
        }

        Transform Make(Transform head, Vector3 characterOffset, string n)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            go.name = n; Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(head, false);
            go.transform.position = head.position + transform.rotation * characterOffset;
            go.transform.localScale = Vector3.one * size / Mathf.Max(0.0001f, head.lossyScale.x);
            var r = go.GetComponent<MeshRenderer>(); r.sharedMaterial = _mat; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return go.transform;
        }

        public bool Visible { get { return _left == null || _left.gameObject.activeSelf; } }

        /// <summary>Shows or hides the eyes (and their light).</summary>
        public void SetVisible(bool on)
        {
            foreach (var t in new[] { _left, _right }) if (t != null) t.gameObject.SetActive(on);
            var l = GetComponentInChildren<Light>(true); if (l != null && l.name == "EyeLight") l.gameObject.SetActive(on);
        }

        public void SetColor(Color hdr)
        {
            color = hdr;
            if (_mpb == null) _mpb = new MaterialPropertyBlock();
            _mpb.SetColor("_BaseColor", hdr);
            foreach (var t in new[] { _left, _right }) if (t != null) t.GetComponent<Renderer>().SetPropertyBlock(_mpb);
            var l = GetComponentInChildren<Light>(); if (l != null && l.name == "EyeLight") l.color = hdr.maxColorComponent > 0 ? hdr / hdr.maxColorComponent : Color.white;
        }
    }
}
