using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// Fires the additive twitch clips at random intervals, with a random clip and a random
    /// layer weight per event, so a crowd of skeletons never twitches in unison.
    /// Expects an Animator layer named <see cref="layerName"/> (blending: Additive) whose
    /// state machine has a "Twitch" trigger and a "TwitchIndex" int parameter, as built by
    /// tools/unity/build_twitch_controller.py (AC_Skeleton.controller).
    /// Disable the component to stop the random twitching; <see cref="Fire(int,float)"/>
    /// still works while disabled (the demo's Twitch buttons use it).
    /// </summary>
    [RequireComponent(typeof(Animator))]
    public class SkeletonTwitch : MonoBehaviour
    {
        [Tooltip("Animator layer holding the additive twitch states")]
        public string layerName = "Twitch";
        [Tooltip("Number of Twitch_NN states the layer offers (TwitchIndex picks 0..clipCount-1)")]
        public int clipCount = 3;
        [Tooltip("Seconds between twitch events, random in this range")]
        public float minInterval = 1.5f;
        public float maxInterval = 5f;
        [Tooltip("Layer weight for each event, random in this range")]
        [Range(0f, 1f)] public float minWeight = 0.5f;
        [Range(0f, 1f)] public float maxWeight = 1f;
        [Tooltip("0 = seed from the instance id, so every skeleton differs")]
        public int seed = 0;

        static readonly int TwitchHash = Animator.StringToHash("Twitch");
        static readonly int IndexHash = Animator.StringToHash("TwitchIndex");

        Animator animator;
        int layer = -1;
        float nextTime;
        System.Random random;

        void Awake()
        {
            animator = GetComponent<Animator>();
            layer = animator.GetLayerIndex(layerName);
            random = new System.Random(seed != 0 ? seed : GetInstanceID());
            nextTime = Time.time + Range(0f, maxInterval);
            if (layer < 0)
                Debug.LogWarning("SkeletonTwitch: no animator layer named '" + layerName + "' on " + name, this);
        }

        float Range(float a, float b)
        {
            return a + (float)random.NextDouble() * (b - a);
        }

        void Update()
        {
            if (layer < 0 || Time.time < nextTime)
                return;
            Fire();
            nextTime = Time.time + Range(minInterval, maxInterval);
        }

        /// <summary>Trigger one twitch now: random clip, random weight.</summary>
        public void Fire()
        {
            Fire(random.Next(clipCount), Range(minWeight, maxWeight));
        }

        /// <summary>Trigger a specific twitch clip at a given layer weight.</summary>
        public void Fire(int index, float weight)
        {
            if (animator == null) animator = GetComponent<Animator>();
            if (layer < 0) layer = animator.GetLayerIndex(layerName);
            if (layer < 0) return;
            animator.SetLayerWeight(layer, Mathf.Clamp01(weight));
            animator.SetInteger(IndexHash, Mathf.Clamp(index, 0, Mathf.Max(0, clipCount - 1)));
            animator.SetTrigger(TwitchHash);
        }
    }
}
