using UnityEngine;

namespace UndeadLegion.Extended
{
    /// <summary>A glowing projectile that homes on a target point and deals damage on arrival (the casters' attack).</summary>
    public class MagicBolt : MonoBehaviour
    {
        public float speed = 12f;
        public float damage = 20f;
        public float impulse = 30f;
        public float lifetime = 4f;
        public GameObject source;
        public SkeletonHealth target;
        Vector3 _aim;
        float _age;

        static Material _mat;

        /// <summary>Spawns a bolt of the given HDR colour from a point toward a target.</summary>
        public static MagicBolt Launch(Vector3 from, SkeletonHealth target, Vector3 aimPoint, Color hdr, float damage, GameObject source)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            go.name = "MagicBolt";
            Object.Destroy(go.GetComponent<Collider>());
            go.transform.position = from; go.transform.localScale = Vector3.one * 0.09f;
            var r = go.GetComponent<MeshRenderer>();
            if (_mat == null)
            {
                var sh = Shader.Find("Universal Render Pipeline/Unlit");
                _mat = new Material(sh != null ? sh : Shader.Find("Sprites/Default"));
            }
            r.sharedMaterial = _mat;
            var mpb = new MaterialPropertyBlock(); mpb.SetColor("_BaseColor", hdr); r.SetPropertyBlock(mpb);
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            var trail = go.AddComponent<TrailRenderer>();
            trail.time = 0.25f; trail.startWidth = 0.08f; trail.endWidth = 0f; trail.sharedMaterial = _mat;
            trail.startColor = hdr; trail.endColor = new Color(hdr.r, hdr.g, hdr.b, 0f);
            var light = go.AddComponent<Light>(); light.type = LightType.Point; light.range = 2.5f; light.intensity = 0.8f; light.shadows = LightShadows.None; light.color = hdr.maxColorComponent > 0f ? hdr / hdr.maxColorComponent : Color.white;
            var b = go.AddComponent<MagicBolt>();
            b.target = target; b._aim = aimPoint; b.damage = damage; b.source = source;
            return b;
        }

        void Update()
        {
            _age += Time.deltaTime;
            if (target != null && !target.IsDead) _aim = AimPoint(target);
            Vector3 to = _aim - transform.position;
            float step = speed * Time.deltaTime;
            if (to.magnitude <= step || _age > lifetime)
            {
                transform.position = _aim;
                if (target != null && !target.IsDead && (target.transform.position - transform.position).sqrMagnitude < 4f)
                    target.TakeDamage(damage, _aim, to.normalized * impulse, source);
                Destroy(gameObject);
                return;
            }
            transform.position += to.normalized * step;
        }

        public static Vector3 AimPoint(SkeletonHealth h)
        {
            var an = h.GetComponent<Animator>();
            var chest = an != null && an.isHuman ? an.GetBoneTransform(HumanBodyBones.Chest) : null;
            return chest != null ? chest.position : h.transform.position + Vector3.up * 1.2f;
        }
    }
}
