"""Mannequin animations on the UE 5.4 twin, the manual's "compatible skeletons" route (2026-10-19).

    python tools/epic_mannequin_content.py --ue54                                    (once: the template mannequin, never shipped)
    python tools/ue/ue54_py.py tools/ue/ue54_manny_check.py setup                    (editor: compat lists + a Manny actor in the level)
    (Play in the level editor, Alt+P)
    MSYS_NO_PATHCONV=1 python tools/ue/ue54_py.py tools/ue/ue54_manny_check.py run /Game/Characters/Mannequins/Animations/Manny/MM_Run_Fwd 0.6
    python tools/ue/ue54_py.py tools/ue/ue54_manny_check.py read
    (stop Play; ONE run per Play session: a paused loop is never stopped by the next PlayLoop - StopSlotAnimation skips paused
     montages - so a second run in the same session blends the old frozen loop in)
    python tools/ue/ue54_py.py tools/ue/ue54_manny_check.py clean                    (then quit WITHOUT saving: the level and both
                                                                                       skeletons were changed for the test only)

`run` plays the clip on the demo's Character through its own PlayLoop (the Animation Blueprint, as a buyer would), puts the Manny
actor beside it with the mesh's orientation, plays the same clip on Manny (single node), freezes both at time T. `read` compares
each shared bone's motion away from ITS OWN rest pose in mesh space (rotation * rest rotation^-1): compatible-skeleton playback
re-applies the clip's per-bone motion relative to the target's rest pose (Engine/Private/Animation/SkeletonRemapping.cpp), so raw
rotations differ by the two rest poses (13 - 30 deg median here) while the motion must agree. Measured 2026-10-19 on MM_Run_Fwd,
MM_Walk_Fwd and MF_Walk_Fwd at 0.6 s: 0.00 deg on all 48 body bones; the fingers (the pack's grip / finger-idle layers) and the
neck / head (the additive twitches) differ by design. 5.4's Python has no tick_animation, a lone SkeletalMeshActor of
SK_SkeletonKnight did not animate a mannequin clip in Simulate, AnimationLibrary.get_bone_pose_for_time logged "Provided Pose is
not valid", actor tags set from Python did not stick, and Quat has no inverse() (inversed()): hence this route.
"""
import math, sys
import unreal

MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
SKIP = ("thumb", "index", "middle", "ring", "pinky", "neck", "head")
CS = unreal.RelativeTransformSpace.RTS_COMPONENT
ES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)


def manny_actors(world):
    return [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SkeletalMeshActor)
            if a.skeletal_mesh_component.get_skeletal_mesh_asset() and a.skeletal_mesh_component.get_skeletal_mesh_asset().get_name() == "SKM_Manny_Simple"]


def setup():
    ours = unreal.load_asset("/Game/UndeadLegion/Characters/SKEL_UndeadLegion")
    manny = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SK_Mannequin")
    for skel, other in ((manny, ours), (ours, manny)):
        lst = list(skel.get_editor_property("compatible_skeletons"))
        if other not in lst:
            skel.set_editor_property("compatible_skeletons", lst + [other])
    if not manny_actors(ES.get_editor_world()):
        a = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 300, 0))
        a.skeletal_mesh_component.set_skeletal_mesh_asset(unreal.load_asset(MANNY))
    print("SETUP: SK_Mannequin compatible with", [s.get_name() for s in manny.get_editor_property("compatible_skeletons")])


def character(w):
    c = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Character)[0]
    return c, c.get_editor_property("mesh")


def run(path, t):
    w = ES.get_game_world(); assert w, "start Play first"
    anim = unreal.load_asset(path); c, m = character(w)
    c.call_method("PlayLoop", args=(anim,))
    a = manny_actors(w)[0]; mt = m.get_world_transform()
    a.set_actor_location_and_rotation(mt.translation + c.get_actor_right_vector() * 110.0, mt.rotation.rotator(), False, True)
    mc = a.skeletal_mesh_component
    mc.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE); mc.set_animation(anim); mc.set_play_rate(0.0); mc.set_position(t, False)
    ai = m.get_anim_instance(); lm = c.get_editor_property("LoopMontage")
    ai.montage_set_position(lm, t); ai.montage_pause(lm)
    print("RUN", anim.get_name(), "frozen at", t)


def read():
    w = ES.get_game_world(); assert w, "start Play first"
    c, m = character(w); mc = manny_actors(w)[0].skeletal_mesh_component
    ang = lambda a, b: math.degrees(2 * math.acos(min(1.0, abs(a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w))))

    def rest(comp, n, memo):        # a bone's component-space rest rotation: its local ref pose composed up the chain
        if n not in memo:
            q = comp.get_ref_pose_transform(comp.get_bone_index(n)).rotation
            par = str(comp.get_parent_bone(n))
            memo[n] = rest(comp, par, memo).multiply(q) if par and par != "None" else q
        return memo[n]

    names = [str(mc.get_bone_name(i)) for i in range(mc.get_num_bones())]
    names = [n for n in names if m.get_bone_index(n) >= 0]
    rm, rk = {}, {}
    d = sorted(((ang(mc.get_socket_transform(n, CS).rotation.multiply(rest(mc, n, rm).inversed()),
                     m.get_socket_transform(n, CS).rotation.multiply(rest(m, n, rk).inversed())), n) for n in names), reverse=True)
    body = [x for x in d if not any(s in x[1] for s in SKIP)]
    lm = c.get_editor_property("LoopMontage")
    print("READ t %.3f / %.3f: %d shared bones; motion difference on the %d body bones: worst %s, median %.3f deg; fingers / neck / head worst %s" % (
        m.get_anim_instance().montage_get_position(lm), mc.get_position(), len(d), len(body),
        ", ".join("%s %.2f" % (n, x) for x, n in body[:3]), body[len(body) // 2][0], ", ".join("%s %.1f" % (n, x) for x, n in d[:2])))


def clean():
    for a in manny_actors(ES.get_editor_world()):
        a.destroy_actor()
    print("CLEAN (quit without saving the level and the two skeletons)")


what = sys.argv[1] if len(sys.argv) > 1 else "read"
{"setup": setup, "clean": clean, "read": read}.get(what, lambda: run(sys.argv[2], float(sys.argv[3])))()
