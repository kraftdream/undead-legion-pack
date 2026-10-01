"""The showreel in Unreal: a stage beat rendered offline with Movie Render Queue (runs inside the editor).

    python tools/ue/ue_py.py tools/ue/ue_showreel.py build  [Warrior] [Idle_03] [seconds]
    python tools/ue/ue_py.py tools/ue/ue_showreel.py render
    python tools/ue/ue_py.py tools/ue/ue_showreel.py status
    python tools/ue/showreel_encode_ue.py                       (system Python: PNGs + caption -> MP4)

The framing is the Unity recorder's (Demo/Scripts/ShowreelRecorder.cs, as the stages were recorded headless): azimuth
-30 (the character's LEFT side nearest), elevation 12, distance 4.0 m, look height 1.0 m, vertical FOV 32 (Unity's
fieldOfView is vertical: on a 16:9 filmback of 36 x 20.25 mm that is a 35.31 mm lens), 1920 x 1080, 30 fps. The character
is the class Blueprint with no weapon (StartLoadout -1) and the stage idle as its StartClip, so the AnimBP plays it exactly
as in the demo (twitches, finger idles, glowing eyes). Movie Render Queue renders in PIE at a fixed 1/30 s step, so the
frames do not depend on the machine's speed (Unity: captureDeltaTime).
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
import unreal
import ue_common, ue_demo_map
importlib.reload(ue_common); importlib.reload(ue_demo_map)   # the editor's Python caches modules between runs
from ue_common import PKG, EAL, log

MAP = PKG + "/Demo/Maps/UndeadLegion_Showreel"
SEQ_DIR = PKG + "/Demo/Showreel"
SEQ = "LS_Modular_Test"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Showreel", "unreal", "modular_test")
FPS = 30
CAM = dict(azimuth=-30.0, elevation=12.0, distance=400.0, look=100.0, vfov=32.0)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def camera_transform():
    """Unity: dir = AngleAxis(azimuth, up) * forward, tilted up by elevation; camera = look + dir * distance.
    The character stands at the origin facing -X (yaw 180), so its forward is -X and its left +Y."""
    a, e = math.radians(CAM["azimuth"]), math.radians(CAM["elevation"])
    fwd, left = (-1.0, 0.0), (0.0, 1.0)
    # Unity's positive angle turns forward toward the RIGHT (seen from above); -30 turns it toward the left
    dx = math.cos(a) * fwd[0] - math.sin(a) * left[0]
    dy = math.cos(a) * fwd[1] - math.sin(a) * left[1]
    d = unreal.Vector(dx * math.cos(e), dy * math.cos(e), math.sin(e))
    loc = unreal.Vector(0, 0, CAM["look"]) + d * CAM["distance"]
    yaw = math.degrees(math.atan2(-d.y, -d.x))
    return loc, unreal.Rotator(roll=0.0, pitch=-CAM["elevation"], yaw=yaw)


def build(character="Warrior", idle="Idle_03", seconds="3"):
    seconds = float(seconds)
    ue_demo_map.open_map(MAP)
    ue_demo_map.stage(size=2000)       # 2 km: the floor reaches the horizon (a 60 m one ended in a black band)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property("default_game_mode", unreal.BlueprintEditorLibrary.generated_class(
        unreal.load_asset(PKG + "/Demo/Blueprints/BP_DemoGameMode")))   # the orbit pawn: no body, no collision
    # the player pawn must not spawn on the character (no PlayerStart = the origin: depenetration shoves the character)
    EAS.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(-1500, -1500, 100)).set_actor_label("PlayerStart")
    c = "Skeleton" + character
    bp = unreal.load_asset("%s/Characters/%s/BP_%s" % (PKG, c, c))
    ch = EAS.spawn_actor_from_class(unreal.BlueprintEditorLibrary.generated_class(bp), unreal.Vector(0, 0, ue_demo_map.HALF),
                                    unreal.Rotator(roll=0, pitch=0, yaw=180))
    ch.set_actor_label(c)
    ch.set_editor_property("StartLoadout", -1)
    ch.set_editor_property("StartClip", unreal.load_asset("%s/Animations/A_%s" % (PKG, idle)))
    loc, rot = camera_transform()
    cam = EAS.spawn_actor_from_class(unreal.CineCameraActor, loc, rot)
    cam.set_actor_label("ShowreelCamera")
    cc = cam.get_cine_camera_component()
    fb = cc.get_editor_property("filmback")
    fb.set_editor_property("sensor_width", 36.0)
    fb.set_editor_property("sensor_height", 20.25)
    cc.set_editor_property("filmback", fb)
    cc.set_editor_property("current_focal_length", 20.25 / 2.0 / math.tan(math.radians(CAM["vfov"] / 2.0)))
    fs = cc.get_editor_property("focus_settings")
    fs.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)    # everything sharp, as Unity's camera
    cc.set_editor_property("focus_settings", fs)
    # the sequence: one camera cut on that camera, `seconds` long at 30 fps
    path = SEQ_DIR + "/" + SEQ
    if EAL.does_asset_exist(path):          # a loaded sequence cannot be deleted: empty it and reuse it
        seq = unreal.load_asset(path)
        for t in seq.get_tracks():
            seq.remove_track(t)
        for b in seq.get_bindings():
            b.remove()
    else:
        seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset(SEQ, SEQ_DIR, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(FPS, 1))
    n = int(round(seconds * FPS))
    seq.set_playback_start(0)
    seq.set_playback_end(n)
    binding = seq.add_possessable(cam)
    track = seq.add_track(unreal.MovieSceneCameraCutTrack)
    sec = track.add_section()
    sec.set_range(0, n)
    sec.set_camera_binding_id(seq.get_binding_id(binding))
    EAL.save_loaded_asset(seq, False)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("showreel map: %s on %s, %d frames; camera at (%.0f, %.0f, %.0f) yaw %.1f pitch %.1f, focal %.2f mm" % (
        c, idle, n, loc.x, loc.y, loc.z, rot.yaw, rot.pitch, cc.get_editor_property("current_focal_length")))


def render(samples="8", frames=""):
    """frames "A:B": render only that range (quick look tests)."""
    samples = int(samples)
    sub = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    q = sub.get_queue()
    q.delete_all_jobs()
    job = q.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.job_name = "Showreel_" + SEQ
    job.map = unreal.SoftObjectPath(MAP)
    job.sequence = unreal.SoftObjectPath("%s/%s.%s" % (SEQ_DIR, SEQ, SEQ))
    cfg = job.get_configuration()
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    o = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    o.output_directory = unreal.DirectoryPath(OUT)
    o.file_name_format = "frame_{frame_number}"
    o.output_resolution = unreal.IntPoint(1920, 1080)
    o.use_custom_frame_rate = True
    o.output_frame_rate = unreal.FrameRate(FPS, 1)
    o.override_existing_output = True
    o.zero_pad_frame_numbers = 5
    if frames:
        o.use_custom_playback_range = True
        o.custom_start_frame, o.custom_end_frame = (int(v) for v in frames.split(":"))
    aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    aa.temporal_sample_count = samples          # accumulated samples per frame (Unity: 2x supersample + MSAA)
    aa.spatial_sample_count = 1
    aa.override_anti_aliasing = True
    aa.anti_aliasing_method = unreal.AntiAliasingMethod.AAM_NONE if samples > 1 else unreal.AntiAliasingMethod.AAM_TSR
    aa.engine_warm_up_count = 60                 # the idle, the twitches and auto exposure settle before frame 0
    aa.render_warm_up_count = 32
    aa.render_warm_up_frames = True
    sub.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
    log("rendering %s -> %s (%d temporal samples)" % (SEQ, OUT, samples))


def exposure(ev):
    """Set the showreel map's manual exposure compensation (EV) in place, for look tests."""
    ue_demo_map.open_map(MAP)
    for a in EAS.get_all_level_actors():
        if a.get_actor_label() == "BloomVolume":
            st = a.get_editor_property("settings")
            st.set_editor_property("override_auto_exposure_bias", True)
            st.set_editor_property("auto_exposure_bias", float(ev))
            a.set_editor_property("settings", st)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("exposure %s EV" % ev)


def status():
    sub = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    jobs = sub.get_queue().get_jobs()
    log("rendering %s | %s" % (sub.is_rendering(), [(j.job_name, round(j.get_status_progress(), 3)) for j in jobs]))


if __name__ == "__main__":
    args = sys.argv[1:] or ["status"]
    globals()[args[0]](*args[1:])
