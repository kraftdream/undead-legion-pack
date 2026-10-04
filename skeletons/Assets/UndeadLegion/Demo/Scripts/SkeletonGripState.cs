using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// On a clip whose hand rides the weapon WITHOUT holding an item of its own (the left hand on a two-hander's
    /// shaft: Idle_TwoHanded, Attack_2H_01_Swing/02, Cast_Staff_01), the empty-hand finger layer would play the relaxed
    /// sway over the clip's baked fist. This behaviour sits on those states (manifest `grip_hands`, put there by
    /// the controller builder) and tells <see cref="SkeletonWeapon"/> to treat that hand as holding while the
    /// state is active: its finger layer fades to 0 and the clip's own fingers (the Grip fist) show.
    /// </summary>
    public class SkeletonGripState : StateMachineBehaviour
    {
        public SkeletonWeapon.Hand hand = SkeletonWeapon.Hand.Left;

        // The hold is re-asserted EVERY frame the state is evaluated (OnStateUpdate runs for both states of a
        // transition), and SkeletonWeapon forgets it in LateUpdate: no enter/exit bookkeeping, so the order
        // in which Unity fires the outgoing state's exit and the incoming state's enter cannot drop a hold
        // (Attack_2H_01_Swing -> Idle_TwoHanded fired the attack's exit AFTER the idle's enter and opened the hand).
        public override void OnStateEnter(Animator animator, AnimatorStateInfo stateInfo, int layerIndex) { Mark(animator); }
        public override void OnStateUpdate(Animator animator, AnimatorStateInfo stateInfo, int layerIndex) { Mark(animator); }

        void Mark(Animator animator)
        {
            var w = animator.GetComponent<SkeletonWeapon>();
            if (w != null) w.ClipHoldThisFrame(hand);
        }
    }
}
