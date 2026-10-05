"""Probe the Epic project's demo in a Play-in-Editor session (2026-10-05).

    python tools/ue/ue_py.py tools/ue/epic_demo_probe.py compat        # SKEL_UndeadLegion <-> SK_Mannequin compatible skeletons (editor, before PIE)
    python tools/ue/ue_py.py tools/ue/epic_demo_probe.py play          # begin PIE on the open demo map
    python tools/ue/ue_py.py tools/ue/epic_demo_probe.py where         # the spawned character's location / yaw, its held weapons
    python tools/ue/ue_py.py tools/ue/epic_demo_probe.py action /Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_01 [rate]
    python tools/ue/ue_py.py tools/ue/epic_demo_probe.py stop

`action` calls the character's PlayAction with ANY animation sequence - a mannequin clip included once the skeletons are
compatible - in DefaultSlot: the "drop a mannequin animation on the skeleton" test inside the shipped demo.
"""
import sys
import unreal

MANNY_SKEL = "/Game/Characters/Mannequins/Meshes/SK_Mannequin"
OUR_SKEL = "/Game/UndeadLegion/Characters/SKEL_UndeadLegion"


def character():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert world, "no PIE world"
    chars = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Character)
    assert chars, "no Character in the PIE world"
    return chars[0]


def main(a):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    what = a[0] if a else "where"
    if what == "compat":
        ours = unreal.load_asset(OUR_SKEL); manny = unreal.load_asset(MANNY_SKEL)
        for skel, other in ((ours, manny), (manny, ours)):
            lst = list(skel.get_editor_property("compatible_skeletons"))
            if other not in lst:
                lst.append(other)
                skel.set_editor_property("compatible_skeletons", lst)
                unreal.EditorAssetLibrary.save_loaded_asset(skel, False)
        print("COMPAT", [s.get_name() for s in ours.get_editor_property("compatible_skeletons")], [s.get_name() for s in manny.get_editor_property("compatible_skeletons")])
    elif what == "play":
        les.editor_request_begin_play(); print("PLAY requested")
    elif what == "stop":
        les.editor_request_end_play(); print("STOP requested")
    elif what == "where":
        c = character()
        loc = c.get_actor_location(); rot = c.get_actor_rotation()
        held = [x.get_name() for x in unreal.GameplayStatics.get_all_actors_of_class(c.get_world(), unreal.Actor) if "BP_Weapon" in x.get_name()]
        mesh = c.get_component_by_class(unreal.SkeletalMeshComponent)
        print("WHERE %s at (%.0f, %.0f, %.0f) yaw %.0f mesh yaw %.0f weapons %s" % (c.get_name(), loc.x, loc.y, loc.z, rot.yaw, mesh.get_editor_property("relative_rotation").yaw, held))
    elif what == "weapons":
        c = character(); mesh = c.get_component_by_class(unreal.SkeletalMeshComponent)
        W = unreal.RelativeTransformSpace.RTS_WORLD
        for side, bone, sock in (("R", "hand_r", "RightHandSlot"), ("L", "hand_l", "LeftHandSlot")):
            hb = mesh.get_socket_transform(bone, W).translation; sl = mesh.get_socket_transform(sock, W).translation
            print("SLOT %s %s at (%.1f %.1f %.1f)  %s at (%.1f %.1f %.1f)  slot-bone %.1f cm" % (side, bone, hb.x, hb.y, hb.z, sock, sl.x, sl.y, sl.z, (sl - hb).length()))
        for x in unreal.GameplayStatics.get_all_actors_of_class(c.get_world(), unreal.Actor):
            if "BP_Weapon" in x.get_name():
                l = x.get_actor_location(); r = x.get_actor_rotation()
                sm = x.get_component_by_class(unreal.StaticMeshComponent) or x.get_component_by_class(unreal.SkeletalMeshComponent)
                b = sm.get_local_bounds() if sm else None
                root = x.get_editor_property("root_component"); par = root.get_attach_parent(); ps = root.get_attach_socket_name()
                print("WEAPON %-28s at (%.1f %.1f %.1f) rot (%.0f %.0f %.0f) attached to %s / %s  mesh-bounds %s" % (
                    x.get_name(), l.x, l.y, l.z, r.pitch, r.yaw, r.roll, par.get_name() if par else None, ps,
                    ("(%.0f..%.0f, %.0f..%.0f, %.0f..%.0f)" % (b[0].x, b[1].x, b[0].y, b[1].y, b[0].z, b[1].z)) if b else None))
    elif what == "montage":
        c = character(); mesh = c.get_component_by_class(unreal.SkeletalMeshComponent); ai = mesh.get_anim_instance()
        m = ai.get_current_active_montage() if ai else None
        print("MONTAGE active %s pos %s slot %s" % (m.get_name() if m else None, ai.montage_get_position(m) if m else None,
              str(m.get_editor_property("slot_anim_tracks")[0].get_editor_property("slot_name")) if m else None))
    elif what == "select":
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        sc = [x for x in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if "BP_DemoShowcase" in x.get_name()][0]
        sc.call_method("SelectCharacter", args=(int(a[1]),)); print("SELECTED", a[1])
    elif what == "loadout":
        c = character(); c.call_method("EquipLoadout", args=(int(a[1]),)); print("LOADOUT", a[1])
    elif what == "loop":
        c = character(); c.call_method("PlayLoop", args=(unreal.load_asset(a[1]),)); print("LOOP", a[1])
    elif what in ("button", "clip"):
        # press a browser button: `button KIND INDEX` (0 character, 1 clip, 2 module, 5 loadout, 6..9 footer) or `clip NAME`
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        sc = [x for x in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if "UETestShowcase" in x.get_class().get_name()]
        assert sc, "no BP_UETestShowcase in the PIE world (the test map only)"
        w = sc[0].get_editor_property("Browser")
        assert w, "the showcase has no Browser yet"
        if what == "clip":
            names = [str(n) for n in w.get_editor_property("ClipNames")]
            kind, index = 1, names.index(a[1])
        else:
            kind, index = int(a[1]), int(a[2])
        w.call_method("OnButton", args=(kind, index)); print("BUTTON %s kind %d index %d" % (w.get_class().get_name(), kind, index))
    elif what == "open":
        unreal.EditorLevelLibrary.load_level(a[1]); print("OPENED", a[1])
    elif what == "turn":
        c = character(); c.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=float(a[1])), False); print("TURNED", a[1])
    elif what == "action":
        anim = unreal.load_asset(a[1]); rate = float(a[2]) if len(a) > 2 else 1.0
        c = character()
        length = c.call_method("PlayAction", args=(anim, "DefaultSlot", 0.2, 0.2, rate))
        print("ACTION %s -> length %s" % (anim.get_name(), length))
    else:
        print("unknown", what)


if __name__ == "__main__":
    main(sys.argv[1:])
