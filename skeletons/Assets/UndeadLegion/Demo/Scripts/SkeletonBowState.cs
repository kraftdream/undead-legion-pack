using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>Resets bow visibility and string attachment when a shot starts or is interrupted.</summary>
    public sealed class SkeletonBowState : StateMachineBehaviour
    {
        static bool IsShot(AnimatorStateInfo state) { return state.IsName("Shoot_01") || state.IsName("Shoot_02"); }
        public override void OnStateEnter(Animator animator, AnimatorStateInfo stateInfo, int layerIndex)
        {
            var weapon = animator.GetComponent<SkeletonWeapon>();
            if (weapon != null) weapon.BowReset();
        }

        public override void OnStateExit(Animator animator, AnimatorStateInfo stateInfo, int layerIndex)
        {
            // A restarted shot owns its new draw event; the outgoing shot must not hide it.
            if (animator.IsInTransition(layerIndex) && IsShot(animator.GetNextAnimatorStateInfo(layerIndex))) return;
            var current = animator.GetCurrentAnimatorStateInfo(layerIndex);
            if (IsShot(current) && current.normalizedTime < stateInfo.normalizedTime) return;
            var weapon = animator.GetComponent<SkeletonWeapon>();
            if (weapon != null) weapon.BowReset();
        }
    }
}
