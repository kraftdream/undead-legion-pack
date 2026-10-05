"""Does a mannequin animation play on our skeleton as it plays on the mannequin? (Epic-skeleton check, 2026-10-05)

    python tools/ue/ue_py.py tools/ue/epic_anim_test.py /Game/Characters/Mannequins/Anims/Unarmed/MM_Walk_Fwd [more anims...]

1. Imports the Knight body FBX a second time, bound to the MANNEQUIN's own skeleton asset (/Game/Characters/Mannequins/Meshes/
   SK_Mannequin), into /Game/_EpicTest/SK_Knight_OnManny: that is what a buyer does with "Assign Skeleton", and it only
   works if the hierarchy is the mannequin's (our extra bones are merged into the skeleton).
2. Spawns two SkeletalMeshActors, SKM_Manny_Simple and that mesh, plays the clip on both at the same times and compares
   every shared bone's WORLD X axis (the bone direction) and the full rotation: with the mannequin's bone frames the
   world rotations must agree bone for bone whatever the proportions. Reports the worst bones per sample.
"""
import math, os, sys
import unreal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ue_common import EXPORT, EAL, log, pipeline, interchange

MANNY_SKEL = "/Game/Characters/Mannequins/Meshes/SK_Mannequin"
MANNY_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
TEST = "/Game/_EpicTest"
OURS = TEST + "/SK_Knight_OnManny"


def ensure_mesh():
    if EAL.does_asset_exist(OURS):
        return unreal.load_asset(OURS)
    skel = unreal.load_asset(MANNY_SKEL)
    pipe = pipeline("IP_EpicTest", skel)
    m = interchange(os.path.join(EXPORT, "Characters", "SkeletonKnight", "SK_SkeletonKnight.fbx"), TEST, "SK_Knight_OnManny", pipe)
    assert m is not None, "import against the mannequin skeleton failed"
    log("SK_Knight_OnManny skeleton: %s" % m.skeleton.get_path_name())
    return m


def frames(comp, names):
    out = {}
    for n in names:
        t = comp.get_socket_transform(n, unreal.RelativeTransformSpace.RTS_WORLD)
        q = t.rotation
        out[n] = (q, q.rotate_vector(unreal.Vector(1, 0, 0)))
    return out


def main(anims):
    ours = ensure_mesh()
    manny = unreal.load_asset(MANNY_MESH)
    a = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0))
    b = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 300, 0))
    ca, cb = a.skeletal_mesh_component, b.skeletal_mesh_component
    ca.set_skeletal_mesh_asset(manny); cb.set_skeletal_mesh_asset(ours)
    names = [str(ca.get_bone_name(i)) for i in range(ca.get_num_bones())]
    names = [n for n in names if cb.get_bone_index(n) >= 0]
    for path in anims:
        anim = unreal.load_asset(path)
        if anim is None:
            log("no animation at " + path); continue
        length = anim.get_play_length()
        for comp in (ca, cb):
            comp.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            comp.set_animation(anim)
            comp.set_play_rate(0.0)
        worst = []
        for k in range(5):
            t = length * k / 4.0
            for comp in (ca, cb):
                comp.set_position(t, False)
                comp.tick_animation(0.0, False)
                comp.refresh_bone_transforms()
            fa, fb = frames(ca, names), frames(cb, names)
            bad = []
            for n in names:
                qa, xa = fa[n]; qb, xb = fb[n]
                d = max(-1.0, min(1.0, xa.x * xb.x + xa.y * xb.y + xa.z * xb.z))
                ang = math.degrees(math.acos(d))
                qd = qa.inverse() * qb
                full = math.degrees(2 * math.acos(min(1.0, abs(qd.w))))
                bad.append((ang, full, n))
            bad.sort(reverse=True)
            worst.append((t, bad[:4]))
        log("%s (%.2f s): worst bone-direction / rotation differences per sample" % (os.path.basename(path), length))
        for t, bad in worst:
            log("  t %.2f: " % t + ", ".join("%s %.1f/%.1f" % (n, ang, full) for ang, full, n in bad))
    a.destroy_actor(); b.destroy_actor()


if __name__ == "__main__":
    main(sys.argv[1:] or ["/Game/Characters/Mannequins/Anims/Death/MM_Death_Front_01"])
