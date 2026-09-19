# tools/ — headless Blender and Unity scripts

All Blender scripts run with Blender 5.2 in background mode and never open a UI:

    B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
    "$B" -b <file.blend> -P tools/<script>.py [-- args]

| Script | Input | What it does | Saves? |
|---|---|---|---|
| `rig_lib_build.py` | a character file | One-off: extracted the Rigify rig into `Rig/skeleton_rig.blend`, reset `bbone_segments` to 1 | writes `Rig/skeleton_rig.blend` |
| `rig_lib_dump.py` | `Rig/skeleton_rig.blend` | Dumps every bone (parent, head, tail, axes, deform) to `Rig/skeleton_rig.json` | writes the JSON |
| `rig_sync.py` | a character file | Replaces the file's rig with the library copy, re-points modifiers/parents, applies object transforms (flips normals on mirrored parts), drops dangling modifiers and non-bone vertex groups, fixes collection names. Verifies world-space geometry is unchanged at rest and reports posed deviation | **overwrites the .blend** |
| `rig_check.py` | a character file | Asserts the rig equals the library and the file is export-clean. Exit 1 on failure | no |
| `export_fbx.py` | a character file | Builds a clean Mixamo-named game skeleton + skinned copies, scales ×1.8, writes `skeletons/Assets/UndeadLegion/Models/<Character>/SK_<Character>.fbx`. `-- --out DIR`, `-- --bst 0` | no (never saves the .blend) |

Typical loop after editing the rig in `Rig/skeleton_rig.blend`:

    "$B" -b Rig/skeleton_rig.blend -P tools/rig_lib_dump.py
    for c in SkeletonArcher SkeletonAssassin SkeletonKnight SkeletonMage SkeletonNecromancer SkeletonWarrior; do
      "$B" -b $c/prod.blend -P tools/rig_sync.py
      "$B" -b $c/prod.blend -P tools/rig_check.py
      "$B" -b $c/prod.blend -P tools/export_fbx.py
    done

## unity/

- `mcp_call.py` — minimal stdio MCP client for the Unity MCP server. The Unity editor
  must be open on `skeletons/`. `python tools/unity/mcp_call.py list`, or
  `call <tool> '<json>'`. Importable: `from mcp_call import Client`.
- `probe_fbx.py` — imports the given FBX paths as Humanoid (scale 1, no materials) and
  prints avatar validity, the human-bone mapping, node transforms and per-renderer bone
  counts. `python tools/unity/probe_fbx.py Assets/UndeadLegion/Models/SkeletonKnight/SK_SkeletonKnight.fbx`

## Lessons baked into these scripts (do not re-learn)

- Compare bone axes by chord length, not `acos(dot)`: acos turns float32 rounding of a
  unit vector into 0.03° of phantom roll and fails every finger bone.
- A datablock loaded with `link=True` carries the matrices it was saved with, not
  evaluated ones; compare against the JSON dump, not a linked armature.
- Deleting an armature *object* leaves its *data* behind under the same name; purge it
  before appending or the library copy lands as `RIG-Meta-Rig.001`.
- `is` on `bpy` RNA wrappers is never a valid identity test; use `==`.
- `bake_space_transform=True` is what puts skinned mesh nodes at identity in Unity.
