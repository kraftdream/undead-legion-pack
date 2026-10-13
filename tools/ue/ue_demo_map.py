"""The overview map: all six skeletons in a row, lit, with a PlayerStart (runs inside the editor).

    python tools/ue/ue_py.py tools/ue/ue_demo_map.py [overview]

Lighting mirrors the Unity demo scene's rig (key 1.10 / fill 0.45 / rim 0.30, skybox ambient 2.0) in the ratios the
creatures pack measured for Unreal (key 4.0 lux, fill 1.64, rim 1.09, sky light 2.0). Every light is Movable: a Static
light needs a lighting build, and an unbuilt map ships "Lighting needs to be rebuilt" across the viewport.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unreal
from ue_common import PKG, CHARACTERS, EAL, log

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
MAPS = PKG + "/Demo/Maps"
SPACING = 160.0
HALF = 90.0                # capsule half height: a Character stands on its capsule's bottom
EXPOSURE = 1.0             # manual exposure compensation, EV (picked on renders against the Unity frame)
BLOOM = (8.0, 0.5)         # intensity, threshold (Unity 2.5 / 1; UE needs more for the same halo, compared on renders)


def ground_material():
    path = PKG + "/Demo/Materials/MI_Demo_Ground"
    MEL = unreal.MaterialEditingLibrary
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
    if mi is None:
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset("MI_Demo_Ground", PKG + "/Demo/Materials",
                                                                     unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, unreal.load_asset(PKG + "/Materials/M_UndeadLegion_Master"))
    MEL.set_material_instance_texture_parameter_value(mi, "BaseColor", unreal.load_asset("/Engine/EngineResources/WhiteSquareTexture"))
    MEL.set_material_instance_texture_parameter_value(mi, "Normal", unreal.load_asset("/Engine/EngineMaterials/FlatNormal"))
    MEL.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(0.030, 0.030, 0.037, 1))
    MEL.set_material_instance_static_switch_parameter_value(mi, "UseMSMap", False)
    MEL.set_material_instance_scalar_parameter_value(mi, "Roughness", 0.85)
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi, False)
    return mi


def open_map(path):
    """new_level refuses an existing asset and leaves the CURRENT level open, so the builder would rebuild whatever
    map happened to be loaded (2026-10-01): load an existing map, create a missing one."""
    if EAL.does_asset_exist(path):
        if not LES.load_level(path):
            raise RuntimeError("could not load " + path)
    elif not LES.new_level(path):
        raise RuntimeError("could not create " + path)


def sky_dome():
    """The engine's sky dome (SM_SkySphere x 400 with M_SimpleSkyDome, as the default template level has it): on desktop
    the SkyAtmosphere draws the sky by itself, but the MOBILE renderer (ES3.1 / Vulkan mobile) only shows the atmosphere
    through a sky mesh whose material is tagged IsSky and reads the SkyAtmosphere nodes - without one the sky is black and a
    development build prints "SkyAtmosphere component needs a mesh ..." (seen in the ES3.1 mobile preview, 2026-10-06)."""
    dome = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/EngineSky/SM_SkySphere"), unreal.Vector(0, 0, 0))
    dome.set_actor_label("SkyDome")
    dome.set_actor_scale3d(unreal.Vector(400, 400, 400))
    c = dome.static_mesh_component
    c.set_material(0, unreal.load_asset("/Engine/EngineSky/M_SimpleSkyDome"))
    c.set_editor_property("cast_shadow", False)
    return dome


def stage(size=60):
    """Floor + key / fill / rim + sky light + atmosphere, on an emptied level."""
    for a in EAS.get_all_level_actors():
        EAS.destroy_actor(a)
    floor = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Plane"), unreal.Vector(0, 0, 0))
    floor.set_actor_scale3d(unreal.Vector(size, size, 1))
    floor.set_actor_label("Floor")
    floor.get_component_by_class(unreal.StaticMeshComponent).set_material(0, ground_material())
    lights = (("KeyLight", 4.0, -42.0, -135.0, True), ("FillLight", 1.64, -20.0, 135.0, False), ("RimLight", 1.09, -30.0, 20.0, False))
    for name, lux, pitch, yaw, shadows in lights:
        a = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500), unreal.Rotator(roll=0, pitch=pitch, yaw=yaw))
        a.set_actor_label(name)
        c = a.get_component_by_class(unreal.DirectionalLightComponent)
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_intensity(lux)
        c.set_cast_shadows(shadows)
        c.set_editor_property("atmosphere_sun_light", name == "KeyLight")
        c.set_editor_property("forward_shading_priority", 1 if name == "KeyLight" else 0)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 400))
    sky.set_actor_label("SkyLight")
    k = sky.get_component_by_class(unreal.SkyLightComponent)
    k.set_mobility(unreal.ComponentMobility.MOVABLE)
    k.set_intensity(2.0)
    k.set_editor_property("real_time_capture", True)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0)).set_actor_label("SkyAtmosphere")
    sky_dome()
    # Unity's Demo_Volume (2026-10-01, the glowing eyes): Bloom only, threshold 1, so the lit scene stays under it and
    # only the HDR eyes bloom
    pp = EAS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
    pp.set_actor_label("BloomVolume")
    pp.set_editor_property("unbound", True)
    st = pp.get_editor_property("settings")
    # FIXED exposure like Unity's camera (auto exposure brightened the dark floor and dimmed the eyes' glow relative to
    # the scene); EXPOSURE is the compensation in EV with the physical-camera exposure off
    for k, v in (("bloom_method", unreal.BloomMethod.BM_SOG), ("bloom_intensity", BLOOM[0]), ("bloom_threshold", BLOOM[1]),
                 ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL), ("auto_exposure_bias", EXPOSURE),
                 ("auto_exposure_apply_physical_camera_exposure", False)):
        st.set_editor_property("override_" + k, True)
        st.set_editor_property(k, v)
    pp.set_editor_property("settings", st)


def overview():
    path = MAPS + "/UndeadLegion_Overview"
    open_map(path)
    stage()
    x0 = -SPACING * (len(CHARACTERS) - 1) / 2.0
    for i, c in enumerate(CHARACTERS):
        bp = unreal.load_asset("%s/Characters/%s/BP_%s" % (PKG, c, c))
        a = EAS.spawn_actor_from_class(unreal.BlueprintEditorLibrary.generated_class(bp), unreal.Vector(0, x0 + SPACING * i, HALF),
                                       unreal.Rotator(roll=0, pitch=0, yaw=180))
        a.set_actor_label(c)
    ps = EAS.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(-650, 0, 100), unreal.Rotator(roll=0, pitch=0, yaw=0))
    ps.set_actor_label("PlayerStart")
    LES.save_current_level()
    log("overview map %s: %d skeletons" % (path, len(CHARACTERS)))




def demo(path=None, showcase=None, label="DemoShowcase"):
    """The animation browser map: one skeleton at a time on the spawn point, the orbit camera, the UMG browser
    (BP_DemoShowcase puts WBP_AnimBrowser on screen; BP_DemoGameMode spawns BP_OrbitPawn). The dev test map
    (ue_uetest.py) is the same with its child showcase at another path."""
    path = path or MAPS + "/UndeadLegion_Demo"
    open_map(path)
    stage()
    show = unreal.load_asset(showcase or PKG + "/Demo/Blueprints/BP_DemoShowcase")
    a = EAS.spawn_actor_from_class(unreal.BlueprintEditorLibrary.generated_class(show), unreal.Vector(0, 0, 0))
    a.set_actor_label(label)
    ps = EAS.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(-600, 0, 100), unreal.Rotator(roll=0, pitch=0, yaw=0))
    ps.set_actor_label("PlayerStart")
    gm = unreal.BlueprintEditorLibrary.generated_class(unreal.load_asset(PKG + "/Demo/Blueprints/BP_DemoGameMode"))
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property("default_game_mode", gm)
    LES.save_current_level()
    log("demo map %s" % path)


if __name__ == "__main__":
    for step in (sys.argv[1:] or ["overview"]):
        globals()[step]()
