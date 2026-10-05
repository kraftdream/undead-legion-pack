"""Hand-slot sockets and the weapon Blueprints, carried over from the Unity setup (imported by ue_build.py).

Unity: a weapon W_<Name> is placed so its `Grip` child coincides with the character's hand slot
(`SkeletonWeapon.AlignGrip`): weapon = Slot x Grip^-1. The slot values and every Grip are in
Animations/unity_grips.json (tools/unity/dump_grips.py).

Unreal, measured 2026-09-29: the skeleton's bone-local frame is Blender's mirrored in Y (R_ue = S R_b S,
S = diag(1,-1,1), to 3 decimals on both weapon sockets), and tools/anim_weapon_ref.py already maps Unity to Blender
(M = diag(-1,1,1) on the slot side, C on the mesh side). Put together:
  * socket   RightHandSlot / LeftHandSlot on Right/LeftWeaponSocket:  location (-x, -y, z) x 100 of the Unity slot,
             rotation Rz(180) x the Unity slot rotation  (Unity's slot axes ARE the socket axes: both engines are
             left-handed)
  * weapon   BP_Weapon_<Name>: a scene root (= the slot) and the mesh component at Grip^-1 x C x S
             (C x S = [[-1,0,0],[0,0,1],[0,1,0]]: Unreal static-mesh axes -> Unity mesh axes), Unity metres x 100.
Move the socket in the skeleton editor (Unity: the hand slot) or the mesh component in BP_Weapon_<Name> (Unity: the
Grip) to re-tune; the builder creates missing ones and never overwrites an existing weapon Blueprint.
"""
import json, math, os, sys
try:
    import unreal
    from ue_common import PKG, REPO, SKEL, WEAPONS, RIGGED_WEAPONS, CHARACTERS, EAL, log, EPIC, bn
except ImportError:          # system Python (sockets_create only)
    PKG, CHARACTERS = "/Game/UndeadLegion", ["SkeletonKnight", "SkeletonArcher", "SkeletonAssassin", "SkeletonMage", "SkeletonNecromancer", "SkeletonWarrior"]
    REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    EPIC = os.environ.get("UL_EPIC") == "1" or "--epic" in sys.argv      # `import unreal` fails here, so ue_common is not used
    bn = lambda n: {"LeftWeaponSocket": "hand_l", "RightWeaponSocket": "hand_r", "Head": "head"}.get(n, n) if EPIC else n

GRIPS = os.path.join(REPO, "Animations", "unity_grips.json")
# the Epic skeleton has no weapon-socket bones: the slots sit on the hands, the socket bone's rest offset folded in
BONE = {"R": bn("RightWeaponSocket"), "L": bn("LeftWeaponSocket")}
SOCKET = {"R": "RightHandSlot", "L": "LeftHandSlot"}
EPIC_FRAMES = os.path.join(REPO, "Export_UE_Epic", "frames.json")


def _qmat(x, y, z, w):
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _matquat(m):
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        return ((m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s)
    i = max(range(3), key=lambda k: m[k][k])
    j, k = (i + 1) % 3, (i + 2) % 3
    s = math.sqrt(1.0 + m[i][i] - m[j][j] - m[k][k]) * 2
    q = [0, 0, 0, 0]
    q[i] = 0.25 * s
    q[j] = (m[j][i] + m[i][j]) / s
    q[k] = (m[k][i] + m[i][k]) / s
    q[3] = (m[k][j] - m[j][k]) / s
    return tuple(q)


def _rot(q):
    return unreal.Quat(q[0], q[1], q[2], q[3]).rotator()


def socket_transform(side, grips):
    s = grips["slots"][side]
    x, y, z = s["pos"]
    R = _mul([[-1, 0, 0], [0, -1, 0], [0, 0, 1]], _qmat(*s["rot"]))
    loc = [-x * 100, -y * 100, z * 100]
    if EPIC:
        # the slot is written in the Mixamo export's weapon-socket bone frame; on the Epic skeleton the socket hangs
        # from the hand, so compose with T = hand_new^-1 . weaponbone_old (both frames in component space, from the
        # exporter's frames.json)
        fr = json.load(open(EPIC_FRAMES, encoding="utf-8"))
        w = fr["DEF-weapon.%s" % side]["old"]; h = fr["hand_%s" % side.lower()]["new"]
        Rw = [[w["x"][i], w["y"][i], w["z"][i]] for i in range(3)]          # columns = axes
        Rh = [[h["x"][i], h["y"][i], h["z"][i]] for i in range(3)]
        RhT = [list(r) for r in zip(*Rh)]
        Tr = _mul(RhT, Rw)
        d = [w["pos"][i] - h["pos"][i] for i in range(3)]
        Tp = [sum(RhT[i][k] * d[k] for k in range(3)) for i in range(3)]
        loc = [sum(Tr[i][k] * loc[k] for k in range(3)) + Tp[i] for i in range(3)]
        R = _mul(Tr, R)
    return unreal.Vector(*loc), _rot(_matquat(R))


def grip_transform(name, grips):
    g = grips["grips"][name]
    Rg = _qmat(*g["rot"])
    RgT = [list(r) for r in zip(*Rg)]
    R = _mul(RgT, [[-1, 0, 0], [0, 0, 1], [0, 1, 0]])
    t = [-sum(RgT[i][k] * g["pos"][k] for k in range(3)) * 100 for i in range(3)]
    return unreal.Vector(*t), _rot(_matquat(R))


def sockets_create():
    """System-Python half: the MCP SkeletalMeshTools.add_socket creates the socket objects (their names are
    read-only to Python). Mesh sockets, on every body (Unity keeps the slots per prefab too, copied from one)."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mcp import tool, ref
    SM = "editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools"
    for c in CHARACTERS:
        m = ref("%s/Characters/%s/SK_%s" % (PKG, c, c))
        have = tool(SM, "get_socket_names", mesh=m) or []
        for side in ("R", "L"):
            if SOCKET[side] not in have:
                tool(SM, "add_socket", mesh=m, socket_name=SOCKET[side], bone_name=BONE[side])
                print("added", c, SOCKET[side])
        for eye in ("EyeL", "EyeR"):            # the glowing eyes (ue_eyes.py seats them per skull)
            if eye not in have:
                tool(SM, "add_socket", mesh=m, socket_name=eye, bone_name=bn("Head"))
                print("added", c, eye)


def sockets(force=None):
    """In-editor half: put each body's hand-slot sockets at the Unity slot transform. A socket that already has a
    non-identity transform is kept (tuned in the editor) unless run as `sockets:force`."""
    grips = json.load(open(GRIPS, encoding="utf-8"))
    for c in CHARACTERS:
        mesh = unreal.load_asset("%s/Characters/%s/SK_%s" % (PKG, c, c))
        for side in ("R", "L"):
            sk = mesh.find_socket(SOCKET[side])
            if sk is None:
                log("!! %s has no %s: run `python tools/ue/ue_weapons.py` first" % (c, SOCKET[side]))
                continue
            loc, rot = socket_transform(side, grips)
            cur = sk.get_editor_property("relative_location")
            if cur.length() > 1e-4 and not force:
                log("%s %s kept (tuned)" % (c, SOCKET[side]))
                continue
            sk.set_socket_local_transform(unreal.Transform(loc, rot, unreal.Vector(1, 1, 1)))
            log("%s %s on %s at (%.2f, %.2f, %.2f) cm, rot %s" % (c, SOCKET[side], BONE[side], loc.x, loc.y, loc.z, rot))
        EAL.save_loaded_asset(mesh, False)


def _component_object(bp, name):
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in _subsys().k2_gather_subobject_data_for_blueprint(bp):
        d = lib.get_data(h)
        if str(lib.get_variable_name(d)) == name:
            return lib.get_object_for_blueprint(d, bp)
    raise KeyError(name)


def _subsys():
    return unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)


def _add_component(bp, cls, name, parent_handle=None):
    ss = _subsys()
    handles = ss.k2_gather_subobject_data_for_blueprint(bp)
    parent = parent_handle or handles[0]
    params = unreal.AddNewSubobjectParams(parent_handle=parent, new_class=cls, blueprint_context=bp)
    h, fail = ss.add_new_subobject(params)
    if not fail.is_empty():
        raise RuntimeError("add %s: %s" % (name, fail))
    ss.rename_subobject(h, unreal.Text(name))
    data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
    return h, unreal.SubobjectDataBlueprintFunctionLibrary.get_object_for_blueprint(data, bp)


def weapon_blueprints(update=None):
    """Create missing BP_Weapon_<Name>. `weapon_blueprints:H1Axe,H2Axe` re-applies the Unity grip to EXISTING ones (the mesh
    component's transform only; the class, and every loadout that references it, stays), for after a Unity grip re-tune."""
    grips = json.load(open(GRIPS, encoding="utf-8"))
    folder = PKG + "/Weapons/Blueprints"
    for w in WEAPONS:
        path = "%s/BP_Weapon_%s" % (folder, w)
        if EAL.does_asset_exist(path):
            if update and w in update:
                bp = unreal.load_asset(path)
                comp = _component_object(bp, "Mesh")
                loc, rot = grip_transform(w, grips)
                comp.set_editor_property("relative_location", loc)
                comp.set_editor_property("relative_rotation", rot)
                unreal.BlueprintEditorLibrary.compile_blueprint(bp)
                EAL.save_loaded_asset(bp, False)
                log("BP_Weapon_%-15s grip updated: (%.2f, %.2f, %.2f) %s" % (w, loc.x, loc.y, loc.z, rot))
            else:
                log("BP_Weapon_%s exists, kept (its grip may be tuned)" % w)
            continue
        f = unreal.BlueprintFactory()
        f.set_editor_property("parent_class", unreal.Actor)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("BP_Weapon_" + w, folder, unreal.Blueprint, f)
        root_h, root = _add_component(bp, unreal.SceneComponent, "Slot")
        rigged = w in RIGGED_WEAPONS
        cls = unreal.SkeletalMeshComponent if rigged else unreal.StaticMeshComponent
        _, comp = _add_component(bp, cls, "Mesh", root_h)
        loc, rot = grip_transform(w, grips)
        if rigged:
            comp.set_editor_property("skeletal_mesh_asset", unreal.load_asset(PKG + "/Weapons/SK_" + w))
        else:
            comp.set_editor_property("static_mesh", unreal.load_asset(PKG + "/Weapons/SM_" + w))
        comp.set_editor_property("relative_location", loc)
        comp.set_editor_property("relative_rotation", rot)
        comp.set_collision_profile_name("NoCollision")
        comp.set_editor_property("cast_shadow", True)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        EAL.save_loaded_asset(bp, False)
        log("BP_Weapon_%-15s mesh at %s %s" % (w, loc, rot))


if __name__ == "__main__":
    sockets_create()
