using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// Raise-from-the-ground and turn-to-dust effects. For the duration of an effect every renderer of the skeleton (body,
    /// armour, weapons) uses a "UndeadLegion/Lit Dissolve" copy of its own material, and a cut height sweeps up (spawn) or
    /// down (death) through the body with a glowing edge. The original materials come back when a spawn finishes.
    /// </summary>
    [DisallowMultipleComponent]
    public class SkeletonDissolve : MonoBehaviour
    {
        [Tooltip("Seconds a spawn or a dissolve takes.")]
        public float duration = 1.6f;
        [ColorUsage(false, true)] public Color edgeColor = new Color(0.35f, 1.6f, 0.9f);
        [Tooltip("Width of the glowing band, metres.")]
        public float edgeWidth = 0.12f;
        public float noiseScale = 9f;
        [Tooltip("Play the spawn effect when the skeleton is enabled.")]
        public bool dissolveInOnEnable = false;
        [Tooltip("The dissolve shader (referenced so it is included in builds).")]
        public Shader dissolveShader;

        static readonly int HeightId = Shader.PropertyToID("_DissolveHeight");
        static readonly int WidthId = Shader.PropertyToID("_DissolveWidth");
        static readonly int NoiseId = Shader.PropertyToID("_NoiseScale");
        static readonly int EdgeId = Shader.PropertyToID("_EdgeColor");
        static readonly Dictionary<Material, Material> Cache = new Dictionary<Material, Material>();
        static Shader _shader;

        class Slot { public Renderer renderer; public Material[] original; public ShadowCastingMode shadows; public MaterialPropertyBlock block; }
        readonly List<Slot> _slots = new List<Slot>();
        MaterialPropertyBlock _mpb;
        Coroutine _running;

        public bool IsPlaying { get { return _running != null; } }

        void OnEnable() { if (dissolveInOnEnable) DissolveIn(); }

        Material DissolveCopy(Material src)
        {
            if (src == null) return null;
            Material m;
            if (Cache.TryGetValue(src, out m) && m != null) return m;
            if (_shader == null) _shader = dissolveShader != null ? dissolveShader : Shader.Find("UndeadLegion/Lit Dissolve");
            if (_shader == null) return src;
            m = new Material(_shader) { name = src.name + " (Dissolve)" };
            m.CopyMatchingPropertiesFromMaterial(src);
            foreach (var k in src.shaderKeywords) m.EnableKeyword(k);
            Cache[src] = m;
            return m;
        }

        void Swap()
        {
            _slots.Clear();
            var renderers = new List<Renderer>(GetComponentsInChildren<Renderer>());
            var ragdoll = GetComponent<SkeletonRagdoll>();
            if (ragdoll != null) foreach (var d in ragdoll.Dropped) if (d != null) renderers.AddRange(d.GetComponentsInChildren<Renderer>());
            foreach (var r in renderers)
            {
                if (!(r is SkinnedMeshRenderer) && !(r is MeshRenderer)) continue;
                var slot = new Slot { renderer = r, original = r.sharedMaterials, shadows = r.shadowCastingMode, block = new MaterialPropertyBlock() };
                r.GetPropertyBlock(slot.block);          // a tint or other per-renderer values survive the effect
                var mats = new Material[slot.original.Length];
                for (int i = 0; i < mats.Length; i++) mats[i] = DissolveCopy(slot.original[i]);
                r.sharedMaterials = mats;
                r.shadowCastingMode = ShadowCastingMode.Off;      // the shadow pass has no cut
                _slots.Add(slot);
            }
        }

        void Restore()
        {
            foreach (var s in _slots)
            {
                if (s.renderer == null) continue;
                s.renderer.sharedMaterials = s.original; s.renderer.shadowCastingMode = s.shadows; s.renderer.SetPropertyBlock(s.block.isEmpty ? null : s.block);
            }
            _slots.Clear();
        }

        void Apply(float height)
        {
            if (_mpb == null) _mpb = new MaterialPropertyBlock();
            foreach (var s in _slots)
            {
                if (s.renderer == null) continue;
                s.renderer.GetPropertyBlock(_mpb);
                _mpb.SetFloat(HeightId, height); _mpb.SetFloat(WidthId, edgeWidth); _mpb.SetFloat(NoiseId, noiseScale); _mpb.SetColor(EdgeId, edgeColor);
                s.renderer.SetPropertyBlock(_mpb);
            }
        }

        Bounds WorldBounds()
        {
            var b = new Bounds(transform.position, Vector3.zero); bool any = false;
            foreach (var s in _slots) if (s.renderer != null) { if (!any) { b = s.renderer.bounds; any = true; } else b.Encapsulate(s.renderer.bounds); }
            return b;
        }

        /// <summary>The skeleton rises out of the ground: the cut sweeps from below the feet to above the head.</summary>
        public void DissolveIn()
        {
            if (_running != null) { StopCoroutine(_running); Restore(); }
            _running = StartCoroutine(Run(true, false));
        }

        /// <summary>The body turns to dust from the top down; optionally the GameObject is destroyed at the end.</summary>
        public void DissolveOut(bool destroyAfter = false)
        {
            if (_running != null) { StopCoroutine(_running); Restore(); }
            _running = StartCoroutine(Run(false, destroyAfter));
        }

        IEnumerator Run(bool spawn, bool destroyAfter)
        {
            Swap();
            Apply(spawn ? -1000f : 1000f);                      // the dissolve material's default shows everything: hide (or keep) the body at once
            yield return null;                                  // one frame so the bounds follow the posed body
            var b = WorldBounds();
            float low = b.min.y - edgeWidth * 2f, high = b.max.y + edgeWidth * 2f;
            float t = 0f;
            while (t < 1f)
            {
                t += Time.deltaTime / Mathf.Max(0.01f, duration);
                float w = Mathf.Clamp01(t); w = w * w * (3f - 2f * w);
                Apply(spawn ? Mathf.Lerp(low, high, w) : Mathf.Lerp(high, low, w));
                yield return null;
            }
            _running = null;
            if (spawn) Restore();
            else if (destroyAfter) Destroy(gameObject);
            else foreach (var s in _slots) if (s.renderer != null) s.renderer.enabled = false;
        }

        /// <summary>Stops any effect and shows the skeleton with its own materials.</summary>
        public void ResetVisuals()
        {
            if (_running != null) { StopCoroutine(_running); _running = null; }
            foreach (var s in _slots) if (s.renderer != null) s.renderer.enabled = true;
            Restore();
        }
    }
}
