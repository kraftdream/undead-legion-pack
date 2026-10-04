"""Animation sequences, notifies and montages (imported by tools/ue/ue_build.py).

Clip settings mirror the Unity import (tools/unity/verify_clip.py per retarget mode, Animations/clips.json):
  * locomotion loops (mode `loco`): root motion ON - the travel is on `Root` (CLAUDE.md 8, root motion decision);
    Unreal extracts it from the root bone, the character BP turns it into movement or discards it.
  * everything else: root motion off - an in-place clip's Root barely moves, and what it does move stays visual.
  * clips whose net travel rides on Root (manifest `drift root`: the staggers, the 2H attacks, the wand casts, taunts...):
    root motion ON too, as Unity imports them; the demo's Root motion toggle decides whether it moves the character.
  * Twitch_* and the manifest's `additive` clips (Hit_01 / Hit_02): additive, local space, against the clip's own frame 0
    (each starts and ends on its reference pose).
  * Grip: a two-frame finger-pose DATA clip (frame 0 the fist, frame 1 the relaxed hand), not a playable clip.
  * events (manifest `events`, 1-based frames at 30 fps) become notifies AN_<Name> at (frame - 1) / 30 s.
"""
import os, glob
import unreal
from ue_common import (PKG, EXPORT, SKEL, EAL, log, pipeline, interchange, clips_manifest)

ANIMS = PKG + "/Animations"
FPS = 30.0
LOOP_MODES = ("idle", "loco")
# One-shots that keep root motion in Unreal: the ones whose travel matters (the staggers, 66 cm). Every other `drift root`
# clip (taunts, casts, Summon, Cutthroat, Rally: 1-8 cm of travel) plays IN PLACE here - a root-motion montage of those
# launched the capsule 12-34 cm up on its first frame (2026-10-04, tools/ue/README.md "Showreel fixes"), which Unity does not do.
ROOT_MOTION_ONESHOTS = {"Stagger_01", "Stagger_02"}


def clip_names():
    return sorted(os.path.basename(p)[len("Skeleton@"):-4] for p in glob.glob(os.path.join(EXPORT, "Animations", "Skeleton@*.fbx")))


def is_loop(name, man):
    c = man.get(name, {})
    return (c.get("mode") in LOOP_MODES or c.get("loops") or name.startswith("Idle") or name.startswith("Hand_Idle")
            or name.startswith("Twitch_") or name == "Block_L_Idle")


def is_additive(name, man):
    return name.startswith("Twitch_") or bool(man.get(name, {}).get("additive"))


def is_loco(name, man):
    return man.get(name, {}).get("mode") == "loco" or name.split("_")[0] in ("Walk", "Run", "Strafe")


def clips(only=None):
    skel = unreal.load_asset(SKEL)
    pipe = pipeline("IP_Anim", skel, meshes=False, anims=True)
    man = clips_manifest()
    for n in clip_names():
        if only and n not in only:
            continue
        a = interchange(os.path.join(EXPORT, "Animations", "Skeleton@%s.fbx" % n), ANIMS, "A_" + n, pipe)
        if a is None:
            continue
        a.set_editor_property("enable_root_motion", is_loco(n, man) or n in ROOT_MOTION_ONESHOTS)
        a.set_editor_property("root_motion_root_lock", unreal.RootMotionRootLock.REF_POSE)
        if is_additive(n, man):
            a.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE)
            a.set_editor_property("ref_pose_type", unreal.AdditiveBasePoseType.ABPT_LOCAL_ANIM_FRAME)
            a.set_editor_property("ref_frame_index", 0)
        EAL.save_loaded_asset(a, False)
    notifies()
    measure_clips(only)


def _notify_class(name):
    """A Blueprint AnimNotify class AN_<name> (its Received_Notify is authored with the character Blueprint)."""
    path = PKG + "/Blueprints/Notifies/AN_" + name
    if not EAL.does_asset_exist(path):
        f = unreal.BlueprintFactory()
        f.set_editor_property("parent_class", unreal.AnimNotify)
        unreal.AssetToolsHelpers.get_asset_tools().create_asset("AN_" + name, PKG + "/Blueprints/Notifies", unreal.Blueprint, f)
        EAL.save_asset(path, only_if_is_dirty=False)
    return unreal.load_object(None, path + ".AN_%s_C" % name)


def notifies():
    AL = unreal.AnimationLibrary
    for n, c in clips_manifest().items():
        ev = c.get("events")
        a = unreal.load_asset(ANIMS + "/A_" + n) if ev and EAL.does_asset_exist(ANIMS + "/A_" + n) else None
        if a is None:
            continue
        track = "Events"
        if track not in [str(x) for x in AL.get_animation_notify_track_names(a)]:
            AL.add_animation_notify_track(a, track)
        AL.remove_animation_notify_events_by_track(a, track)
        for evn, fr in sorted(ev.items(), key=lambda kv: kv[1]):
            AL.add_animation_notify_event(a, track, (fr - 1) / FPS, _notify_class(evn))
            log("%s: notify AN_%s at frame %d (%.4f s)" % (n, evn, fr, (fr - 1) / FPS))
        EAL.save_loaded_asset(a, False)


def measure_clips(only=None):
    X = unreal.AnimPoseExtensions
    man = clips_manifest()
    opts = unreal.AnimPoseEvaluationOptions()
    for n in clip_names():
        if only and n not in only:
            continue
        a = unreal.load_asset(ANIMS + "/A_" + n)
        if a is None:
            log("!! missing A_" + n)
            continue
        nf = a.get_editor_property("number_of_sampled_frames")
        p0, pN = X.get_anim_pose_at_frame(a, 0, opts), X.get_anim_pose_at_frame(a, nf, opts)
        r0 = X.get_bone_pose(p0, "Root", unreal.AnimPoseSpaces.WORLD).translation
        rN = X.get_bone_pose(pN, "Root", unreal.AnimPoseSpaces.WORLD).translation
        L = a.get_play_length()
        tr = rN - r0
        d = (tr.x ** 2 + tr.y ** 2) ** 0.5
        log("%-18s %4d f %7.3f s  root travel (%7.2f, %7.2f) cm  %6.1f cm/s  rm %s%s" % (
            n, nf, L, tr.x, tr.y, d / L if L else 0, "on " if a.get_editor_property("enable_root_motion") else "off",
            "  loop" if is_loop(n, man) else ""))


def montages(only=None):
    """AM_<Clip> in DefaultSlot for every one-shot (the buyer's usual route; the demo plays sequences through
    slots directly with PlaySlotAnimationAsDynamicMontage). `montages:A,B` limits it to those clips. A montage
    that cannot be deleted (still referenced by something loaded in the editor) is kept and logged instead of
    crashing the step (2026-10-04: create_asset returned None on the first clip and nothing was built)."""
    man = clips_manifest()
    for n in clip_names():
        if only and n not in only:
            continue
        if is_loop(n, man) or n == "Grip" or is_additive(n, man):
            continue
        a = unreal.load_asset(ANIMS + "/A_" + n)
        path = PKG + "/Animations/Montages/AM_" + n
        if EAL.does_asset_exist(path):
            EAL.delete_asset(path)
            if EAL.does_asset_exist(path):
                log("montage AM_%s: could not be deleted (still referenced), kept" % n)
                continue
        f = unreal.AnimMontageFactory()
        f.set_editor_property("target_skeleton", a.get_editor_property("skeleton"))
        f.set_editor_property("source_animation", a)
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset("AM_" + n, PKG + "/Animations/Montages", unreal.AnimMontage, f)
        EAL.save_loaded_asset(m, False)
        log("montage AM_%s (%.3f s)" % (n, m.get_play_length()))
