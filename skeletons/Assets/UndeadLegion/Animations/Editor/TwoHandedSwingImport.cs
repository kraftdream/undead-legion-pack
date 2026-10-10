using UnityEditor;
using UnityEngine;

namespace UndeadLegion.AnimationEditor
{
    /// <summary>Keeps the two-handed swing's forearm rotation compatible with its idle during blends.</summary>
    public sealed class TwoHandedSwingImport : AssetPostprocessor
    {
        public override uint GetVersion() { return 1; }

        void OnPostprocessAnimation(GameObject root, AnimationClip clip)
        {
            if (!assetPath.EndsWith("/Skeleton@Attack_2H_01_Swing.fbx", System.StringComparison.Ordinal)
                || !clip.humanMotion)
                return;

            foreach (var binding in AnimationUtility.GetCurveBindings(clip))
            {
                if (binding.type != typeof(Animator) || binding.propertyName != "Right Forearm Twist In-Out")
                    continue;

                var curve = AnimationUtility.GetEditorCurve(clip, binding);
                if (curve == null || curve.length == 0) return;

                // Default forearm limits are +/-90 degrees: four muscle units are one turn.
                // This clip and Idle_TwoHanded have identical endpoint poses, but the FBX
                // importer chooses -270 degrees for this clip and +90 for the idle. Blending
                // the numeric muscle values would spin the wrist through a complete turn.
                // Shift the WHOLE curve to the idle's equivalent branch; retain every
                // relative rotation, tangent, key time and the continuous attack motion.
                const float fullTurn = 4f;
                float offset = -fullTurn * Mathf.Round(curve.Evaluate(0f) / fullTurn);
                if (Mathf.Abs(offset) < 0.001f) return;
                var keys = curve.keys;
                for (int i = 0; i < keys.Length; i++) keys[i].value += offset;
                curve.keys = keys;
                AnimationUtility.SetEditorCurve(clip, binding, curve);
                return;
            }
        }
    }
}
