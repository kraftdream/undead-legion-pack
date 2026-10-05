"""Pose the mannequin and our Knight (bound to the mannequin skeleton) with the same mannequin animation at one time
and leave them in the level for a viewport capture (Epic-skeleton check, 2026-10-05).

    python tools/ue/ue_py.py tools/ue/epic_pose_shot.py /Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd 0.5 [clear]

Two SkeletalMeshActors (EpicTest_Manny / EpicTest_Ours), each with the clip as its single-node animation, play rate 0,
parked at the given time. The edit-mode viewport never evaluates the pose (the captures showed the reference pose), so
`simulate` also starts a Simulate-in-Editor session after posing: the components tick there and the MCP viewport capture
shows the frame; stop it with `stop`. `clear` only deletes the actors.
(A PoseableMeshComponent fed from an AnimPose was tried first and asserted in FBoneContainer on set_skinned_asset.)
The mesh SK_Knight_OnManny comes from epic_anim_test.py (the import against SK_Mannequin).
"""
import math, os, sys
import unreal

OURS = "/Game/_EpicTest/SK_Knight_OnManny"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
ELL = unreal.EditorLevelLibrary


def clear():
    for a in ELL.get_all_level_actors():
        if a.get_actor_label().startswith("EpicTest_"):
            a.destroy_actor()


def actor(label, mesh, pos, anim, t):
    a = ELL.spawn_actor_from_class(unreal.SkeletalMeshActor, pos)
    a.set_actor_label(label)
    c = a.skeletal_mesh_component
    c.set_skeletal_mesh_asset(mesh)
    c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    # the SAVED play data is what the simulation's copy starts from (set_animation only reaches the live instance)
    data = unreal.SingleAnimationPlayData()
    data.set_editor_property("anim_to_play", anim)
    data.set_editor_property("saved_position", t)
    data.set_editor_property("saved_play_rate", 0.0)
    data.set_editor_property("saved_playing", True)
    data.set_editor_property("saved_looping", True)
    c.set_editor_property("animation_data", data)
    c.set_animation(anim)
    c.set_play_rate(0.0)
    c.set_position(t, False)
    return a, c


def sim_actors():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert world, "no game world: simulate is not running"
    A = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SkeletalMeshActor)}
    return A["EpicTest_Manny"].skeletal_mesh_component, A["EpicTest_Ours"].skeletal_mesh_component


def check_pose(t, shot):
    """In the running simulation: park both at t, aim the viewport, request a screenshot (Saved/Screenshots)."""
    cm, co = sim_actors()
    for c in (cm, co):
        c.set_play_rate(0.0); c.set_position(t, False)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(0, 420, 110), unreal.Rotator(-4, -90, 0))
    unreal.AutomationLibrary.take_high_res_screenshot(1600, 900, shot)
    print("CHECK positions set, screenshot requested:", shot)


def inspect():
    cm, co = sim_actors()
    for name, c in (("manny", cm), ("ours", co)):
        ai = c.get_anim_instance(); ad = c.get_editor_property("animation_data")
        print("SIM %s mode %s instance %s anim %s pos %.2f playing %s tick %s visible %s" % (
            name, c.get_editor_property("animation_mode"), type(ai).__name__ if ai else None, ad.get_editor_property("anim_to_play"),
            c.get_position(), c.is_playing(), c.get_editor_property("visibility_based_anim_tick_option"), c.is_visible()))


def compare():
    """In the running simulation: every shared bone's world rotation, ours against the mannequin's."""
    cm, co = sim_actors()
    names = [str(cm.get_bone_name(i)) for i in range(cm.get_num_bones())]
    names = [n for n in names if co.get_bone_index(n) >= 0]
    rows = []
    for n in names:
        qa = cm.get_socket_transform(n, unreal.RelativeTransformSpace.RTS_WORLD).rotation
        qb = co.get_socket_transform(n, unreal.RelativeTransformSpace.RTS_WORLD).rotation
        rows.append((math.degrees(qa.angular_distance(qb)), n))
    rows.sort(reverse=True)
    ref = cm.get_socket_transform("thigh_l", unreal.RelativeTransformSpace.RTS_COMPONENT).rotation.rotator()
    print("COMPARE %d bones: worst %s; median %.2f deg; manny thigh_l component rot %s; manny pos %.2f ours pos %.2f" % (
        len(rows), ", ".join("%s %.1f" % (n, d) for d, n in rows[:8]), rows[len(rows) // 2][0], ref, cm.get_position(), co.get_position()))


def main(anim_path, t, only_clear=False, simulate=False, stop=False, check=False, cmp_=False):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if stop:
        les.editor_request_end_play(); return
    if check:
        check_pose(t, anim_path.split("/")[-1] + "_%.2f.png" % t); return
    if cmp_:
        compare(); return
    if anim_path == "inspect":
        inspect(); return
    clear()
    if only_clear:
        return
    anim = unreal.load_asset(anim_path)
    assert anim, "no animation at " + anim_path
    manny = unreal.load_asset(MANNY); ours = unreal.load_asset(OURS)
    assert ours, "run epic_anim_test.py first (SK_Knight_OnManny)"
    # the sub-project opens on an empty level: a key light and a sky light so the capture shows something
    sun = ELL.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 300), unreal.Rotator(-45, 60, 0))
    sun.set_actor_label("EpicTest_Sun"); sun.light_component.set_intensity(12.0)
    sky = ELL.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 300))
    sky.set_actor_label("EpicTest_Sky"); sky.light_component.set_intensity(6.0)
    actor("EpicTest_Manny", manny, unreal.Vector(-80, 0, 0), anim, t)
    actor("EpicTest_Ours", ours, unreal.Vector(80, 0, 0), anim, t)
    print("POSED %s at %.2f s (ours on %s)" % (os.path.basename(anim_path), t, ours.skeleton.get_name()))
    if simulate:
        les.editor_play_simulate()


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0] if a and a[0] not in ("clear", "stop", "compare") else "", float(a[1]) if len(a) > 1 and a[1] not in ("clear", "stop", "simulate", "check") else 0.0,
         "clear" in a, "simulate" in a, "stop" in a, "check" in a, "compare" in a)
