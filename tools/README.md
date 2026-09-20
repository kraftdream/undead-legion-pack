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
| `rig_lib_add_sockets.py` | `Rig/skeleton_rig.blend` | Adds/refreshes `DEF-weapon.L/R` (+ `weapon.L/R` on the metarig): the weapon socket bones and the grip convention (see its docstring / CLAUDE.md §2) | **overwrites the library** |
| `anim_file_build.py` | none (create) or `Animations/skeleton_anim.blend` (refresh) | Links the library rig as an override, appends every character's meshes as reference and the weapons, sets 30 fps. Refresh replaces the reference meshes only; actions and the rig override are untouched | writes/overwrites the anim file |
| `anim_test_clip.py` | `Animations/skeleton_anim.blend` | Authors `Test_RootMotion` (1 m forward, 30° yaw, 25° head nod, 1 s) for pipeline verification | overwrites the anim file |
| `export_fbx.py` | a character file | Builds a clean Mixamo-named game skeleton + skinned copies, scales ×1.8, writes `skeletons/Assets/UndeadLegion/Models/<Character>/SK_<Character>.fbx`. `-- --out DIR`, `-- --bst 0` | no (never saves the .blend) |
| `export_fbx.py -- --clip Name` | the anim file | Builds the game skeleton constrained to the source rig, bakes the action, scales rest + location keys ×1.8, writes `skeletons/Assets/UndeadLegion/Animations/Skeleton@Name.fbx` (rig + `Body` empty, one take) | no |
| `kimodo_gen.ps1` (PowerShell) | a text prompt | Generates a clip on the Kimodo laptop over SSH, fetches `External Anims/Kimodo/<Name>.glb/.bvh/.txt` | writes External Anims |
| `rig_lib_no_stretch.py` | `Rig/skeleton_rig.blend` | Sets `ik_stretch = 0` on every pose bone and `IK_Stretch = 0` on the limb switches (CLAUDE.md §8: rigid IK chains or Unity sinks the feet) | **overwrites the library** |
| `glb_retarget.py -- --glb F --name N --mode idle\|loco\|action\|death [--loop 120 --blend 30 --src-start 30 --time-scale 1.0 --smooth 0 --fist 0.3 --finger-life 0.12 --hunch 0 --head-damp 1 --arm-pose P --lock-left-hand 0 --travel-axis auto --mirror] [--save]` | the anim file | Kimodo GLB → Action on the rig (world-rotation deltas, IK-pinned legs for idles, FK legs otherwise). `--time-scale` slerp-stretches the source, `--smooth` low-passes it, `--head-damp 0.45` takes the bow out of a shambling head, `--arm-pose` swaps the arms for an authored socket-frame hand pose (weapon idles), `--lock-left-hand D` pins the left hand D m down the right hand's weapon handle (two-handed attacks, staff casts), `--travel-axis x` forces sideways root travel (strafes), `--mirror` swaps left/right in the source (Strafe_Left is the mirrored right strafe). `--arm-keys "0:bow_side,0.4:bow_draw,..."` keys arm presets over the clip (archery, summon, taunt; `free` releases the arm to the source). Ground correction per mode from the lowest vertex of **all six characters' meshes** (the Ref_ collections are un-excluded for the measurement). Reports gait period, travel, floor and seam | with `--save` |
| `anim_grip_export.py [-- --save]` | the anim file | Keys the hand-authored finger grip (unkeyed pose on the finger controls of both hands) into the action `Grip`; export it with `export_fbx.py -- --clip Grip` and rebuild the prefabs, which sample it into `SkeletonWeapon.gripLeft/Right` | with `--save` |
| `anim_twitch.py [-- --save]` | the anim file | Authors `Twitch_01..03`, the additive head + jaw clips (rest at frame 1 and the last frame) | with `--save` |
| `anim_preview.py -- --action N [--frames 1,31,..] [--out DIR] [--ref SkeletonKnight]` | the anim file | Workbench contact sheet, front + side, one column per frame (default: six frames spread over the action; the camera follows the root's travel) | writes PNGs |

Clip authoring loop as it ran for `Idle` (2026-09-19):

    powershell -NoProfile -ExecutionPolicy Bypass -File tools/kimodo_gen.ps1 -Prompt "A person stands still ..." -Name idle_s42 -Frames 180 -Seed 42
    "$B" -b Animations/skeleton_anim.blend -P tools/glb_retarget.py -- --glb "External Anims/Kimodo/idle_s42.glb" --name Idle --loop 120 --blend 30 --src-start 30 --save
    "$B" -b Animations/skeleton_anim.blend -P tools/anim_preview.py -- --action Idle --out /tmp/preview     # look at it
    "$B" -b Animations/skeleton_anim.blend -P tools/export_fbx.py -- --clip Idle
    python tools/unity/verify_clip.py "Assets/UndeadLegion/Animations/Skeleton@Idle.fbx" --loop 1

Typical loop after editing the rig in `Rig/skeleton_rig.blend`:

    "$B" -b Rig/skeleton_rig.blend -P tools/rig_lib_dump.py
    for c in SkeletonArcher SkeletonAssassin SkeletonKnight SkeletonMage SkeletonNecromancer SkeletonWarrior; do
      "$B" -b $c/prod.blend -P tools/rig_sync.py
      "$B" -b $c/prod.blend -P tools/rig_check.py
      "$B" -b $c/prod.blend -P tools/export_fbx.py
    done
    # the anim file links the library, so it picks the change up on next open; refresh the
    # reference meshes only if a body/armour mesh changed:
    "$B" -b Animations/skeleton_anim.blend -P tools/anim_file_build.py

Clip loop:

    "$B" -b Animations/skeleton_anim.blend -P tools/export_fbx.py -- --clip Walk_Fwd
    python tools/unity/verify_clip.py "Assets/UndeadLegion/Animations/Skeleton@Walk_Fwd.fbx" --loop 1
    rm -rf skeletons/Assets/_PipelineTest*     # verify_clip leaves its test controller there

| `mesh_normals_fix.py [-- --save] [--render DIR]` | a character file | Makes each island's winding consistent, votes open cloth islands against the body surface, reports per mesh; `--render` writes EEVEE back-face-culled renders before/after (what Unity shows); `--save` writes `<Character>/prod_copy.blend`, never prod.blend. The vote can be wrong on hanging cloth (Archer): compare the culled renders before trusting a copy | with `--save`, to prod_copy |
| `pack_textures.py [-- Char ...]` | none | Copies `<part>_color/_normal.png` into `skeletons/Assets/UndeadLegion/Textures/<Char>/` and packs `<part>_metallicsmoothness.png` (R = metallic or 0, A = 1 − roughness) with Blender's image API + numpy | writes into the Unity project |

## The clip factory

`Animations/clips.json` lists every clip (prompt, frames, seed, retarget mode + args).

    python tools/kimodo_batch.py            # generate every missing GLB on the laptop (detach it: an hour+)
    python tools/anim_batch.py --wait       # retarget -> preview -> export -> Unity verify, as GLBs arrive
    python tools/anim_batch.py Walk_Fwd --force   # rebuild one after editing its entry or the retarget

Both log to `Animations/*.log`; `Animations/build_state.json` remembers what was built
from which GLB and which manifest entry. Previews land in `Animations/preview/` (look at them).
To rebuild a clip after a retarget change, delete its entry from `build_state.json`; the
waiting batch picks it up on its next two-minute poll. **`anim_batch.py` itself is loaded
once**: after editing it (new manifest keys) kill the detached process and start it again,
between builds (it saves the anim file; never run a manual `--save` retarget while it runs).
Grounding in Unity (`ground_clip.py`) can still differ from Blender's by a few cm on deep
knee bends: the export merges Rigify's two-segment limbs into one bone and a robe hem
weighted to the shin lands elsewhere (Death_02 Necromancer: -5.6 cm during the kneel).

Weapons: `blender -b Weapons/prod.blend -P tools/export_weapons.py` (then
`... Weapons/weapons.blend ... -- --only Arrow`) writes `Models/Weapons/SM_*.fbx` with the
grip at the origin and the length along the socket's +Y (grip table inside the script,
carried over to rescaled meshes); `blender -b -P tools/pack_textures.py -- Weapons` packs the
textured weapons' maps into `Textures/Weapons/`; `python tools/unity/weapon_shots.py <out> <Clip>
<loadout> [Character]` renders a character playing a clip with a loadout equipped on
the socket bones, in edit mode.

## Unity menu items (Demo/Editor)

`Undead Legion/1. Import Setup` → texture + model importers, materials.
`Undead Legion/2. Rebuild Character Prefabs` → `PF_<Char>.prefab` ×6.
`Undead Legion/3. Rebuild Demo Scene` → `Demo/Scenes/UndeadLegion_Demo.unity`.
`Undead Legion/Rebuild All (1-3)`. From here:
`python tools/unity/mcp_call.py call execute_code '{"action":"execute","code":"return EditorApplication.ExecuteMenuItem(\"Undead Legion/Rebuild All (1-3)\");"}'`

## unity/

- `demo_smoke.py [out_dir]` — enters play mode, kicks the player loop (see CLAUDE.md §7:
  play mode sits at frame 1 until stepped), selects characters, fires a twitch, toggles a
  module, screenshots, reads the console, stops play mode.

- `mcp_call.py` — minimal stdio MCP client for the Unity MCP server. The Unity editor
  must be open on `skeletons/`. `python tools/unity/mcp_call.py list`, or
  `call <tool> '<json>'`. Importable: `from mcp_call import Client`.
- `probe_fbx.py` — imports the given FBX paths as Humanoid (scale 1, no materials) and
  prints avatar validity, the human-bone mapping, node transforms and per-renderer bone
  counts. `python tools/unity/probe_fbx.py Assets/UndeadLegion/Models/SkeletonKnight/SK_SkeletonKnight.fbx`
- `build_twitch_controller.py` — (re)builds `Animations/AC_Skeleton.controller` in place
  (Base: every clip as a state; UpperBody: Override layer masked by `AM_UpperBody.mask`
  at Spine1 with `Empty` + every manifest clip tagged `layer: upper`; Twitch: additive
  layer with Rest + Twitch_01..03, trigger `Twitch` + int `TwitchIndex`; TwitchLoop_01..03:
  additive loop layers at weight 0 for the demo's twitch toggles) and measures the
  additive head/jaw contribution over the idle (fired once, and toggled on across two
  passes) and the walk+attack layering on the Knight. Run it after every new clip. `Demo/Scripts/SkeletonTwitch.cs` fires the
  twitch layer at random; `SkeletonShowcase.PlayOnTheMove` uses the upper layer.
- `layer_smoke.py [out_dir]` — play-mode proof of layered playback in the demo: walk,
  then an on-the-move attack (must land on UpperBody while Base keeps walking), then a
  full-stop attack (takes Base, walk resumes). Prints every layer's state per step.
- `ground_clip.py Idle Idle_02 ...` — force-reimports each clip, plays it on all six raw
  models and reports the lowest baked vertex; the grounding check for every new clip
  (CLAUDE.md §8, "Grounding"). Must be ≥ 0 on every model.
- `verify_clip.py` — imports a clip FBX as Humanoid with the avatar copied from a model,
  then steps an Animator through it on all six models in edit mode and prints travel and
  yaw with root motion on and off, plus how far key bones rotated. This is how the
  shipped speed table gets measured (CLAUDE.md §8).

## Lessons baked into these scripts (do not re-learn)

- Compare bone axes by chord length, not `acos(dot)`: acos turns float32 rounding of a
  unit vector into 0.03° of phantom roll and fails every finger bone.
- A datablock loaded with `link=True` carries the matrices it was saved with, not
  evaluated ones; compare against the JSON dump, not a linked armature.
- Deleting an armature *object* leaves its *data* behind under the same name; purge it
  before appending or the library copy lands as `RIG-Meta-Rig.001`.
- `is` on `bpy` RNA wrappers is never a valid identity test; use `==`.
- `bake_space_transform=True` is what puts skinned mesh nodes at identity in Unity.
