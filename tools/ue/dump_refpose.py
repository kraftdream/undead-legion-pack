"""Dump a skeletal mesh's reference skeleton from the live editor: every bone's name, parent, component-space
frame (position + rotation matrix, the bone's local axes in component space) and its local transform.

    python tools/ue/ue_py.py tools/ue/dump_refpose.py /Game/Path/SKM_Mesh out.json

A SkeletalMeshActor is spawned in the open level with the mesh, no animation (the reference pose), read through
get_socket_transform(bone, RTS_COMPONENT) and destroyed again (the level is not saved). Units: cm, Unreal axes.
"""
import json, sys
import unreal

mesh_path, out = sys.argv[1], sys.argv[2]
mesh = unreal.load_asset(mesh_path)
assert mesh, "no asset at " + mesh_path
actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0))
comp = actor.skeletal_mesh_component
comp.set_skeletal_mesh_asset(mesh)
comp.set_animation_mode(unreal.AnimationMode.ANIMATION_CUSTOM_MODE)   # nothing drives it: the reference pose
bones = []
n = comp.get_num_bones()
for i in range(n):
    name = str(comp.get_bone_name(i))
    parent = str(comp.get_parent_bone(name)) if i > 0 else ""
    t = comp.get_socket_transform(name, unreal.RelativeTransformSpace.RTS_COMPONENT)
    q = t.rotation
    m = q.rotator()
    # basis vectors of the bone frame in component space
    x = q.rotate_vector(unreal.Vector(1, 0, 0)); y = q.rotate_vector(unreal.Vector(0, 1, 0)); z = q.rotate_vector(unreal.Vector(0, 0, 1))
    lt = comp.get_socket_transform(name, unreal.RelativeTransformSpace.RTS_PARENT_BONE_SPACE)
    lq = lt.rotation
    bones.append({"name": name, "parent": parent if parent != "None" else "",
                  "pos": [t.translation.x, t.translation.y, t.translation.z],
                  "x": [x.x, x.y, x.z], "y": [y.x, y.y, y.z], "z": [z.x, z.y, z.z],
                  "quat": [q.x, q.y, q.z, q.w],
                  "local_pos": [lt.translation.x, lt.translation.y, lt.translation.z],
                  "local_quat": [lq.x, lq.y, lq.z, lq.w],
                  "local_rot": [lq.rotator().roll, lq.rotator().pitch, lq.rotator().yaw]})
actor.destroy_actor()
skel = mesh.skeleton
json.dump({"mesh": mesh_path, "skeleton": str(skel.get_path_name()) if skel else "", "bones": bones}, open(out, "w"), indent=1)
print("DUMP %d bones -> %s" % (n, out))
for b in bones[:12]:
    print("  %-22s <- %-18s pos (%.1f %.1f %.1f) x(%.2f %.2f %.2f) y(%.2f %.2f %.2f)" % (b["name"], b["parent"], *b["pos"], *b["x"], *b["y"]))
