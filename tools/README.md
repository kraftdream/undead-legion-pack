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
| `anim_weapon_ref.py -- --attach H2Recurvebow:L,Arrow:R [--check Shoot_01:36] [--save]` / `--remove --save` | the anim file | appends the named weapons from `Weapons/prod.blend`, puts each in the export-local frame (`export_weapons.export_local_mesh`) and parents it to `DEF-weapon.<side>` with a Child Of constraint whose local matrix reproduces Unity's `AlignGrip` (slot × Grip⁻¹, read from `Animations/unity_grips.json`), so a reference pose can be authored on the bow and arrow exactly where Unity shows them; collection `Ref_Weapons`, objects `Ref_<Name>`, never exported. `--check` prints the arrow's shaft against the draw-hand → bow-hand line and the bow's limbs against the arrow (Shoot_01:36: 175° / 88°, the same as Unity) | with `--save` |
| `bvh_to_glb.py -- SRC.bvh DST.glb [--yup]` | (no file) | converts a video-mocap BVH to the Y-up GLB the retarget reads (the `*_JNT` app's BVH is Z-up with a T-pose rest; an Unreal-mannequin BVH is Y-up in cm with a stacked rest: `--yup`, then `--rename ue5 --bind stacked`); prints the rest hand/head/hips positions so a wrong up axis shows | writes DST |
| `glb_nodes_to_armature.py -- SRC.glb DST.glb` | (no file) | a skinless node-hierarchy GLB (the mannequin app) → an armature: rest from the JSON node TRS in the importer's convention, the empties' animation baked on; writes `DST.blend` (the retarget source: manifest `src_ext blend`) and a viewer GLB | writes both |
| `retarget_compare.py -- --src SRC --clip NAME --src-begin A --src-end B --time-scale S [--mirror] [--render DIR]` | the anim file | poses the source capture and the built clip frame by frame: per-joint position error (engine cm, hips-relative, scaled, yaw-aligned on the shoulders) and per-bone DIRECTION error in degrees (proportion-free); `--render` puts red spheres at the capture's joints on the Knight. The first thing to run when a retarget "looks different from the reference" | |
| `unity/layer_smoke.py [out_dir]` | Unity (bridge, play mode) | walk + Attack_R_Slice on the RightArm layer, Attack_2H_01 as a full stop with the walk resuming, Block_L_Idle held on LeftArm through a right stab and a walk, then released; prints every layer's state per step and screenshots | |
| `unity/dump_grips.py [out.json]` | Unity (bridge) | writes `Animations/unity_grips.json`: the hand slots' local poses (from `PF_SkeletonArcher`) and every `W_*` prefab's `Grip` local pose, the inputs of `anim_weapon_ref.py`; re-run after moving a slot or a Grip in Unity | |
| `anim_nla_bake.py -- --result NAME [--action NAME] [--mirror-to NAME2] [--pin-foot SIDE[:ref[:from[:to]]]] [--speed-segment A:B:F] [--torso-yaw DEG] [--arm-pole-fk L|R|LR] [--fk-arm L|R|LR] [--hand-grip L|R|LR] [--frames A:B] [--save]` | anim file | flatten the rig's NLA stack + active action (a generated clip pushed down as a strip with a hand-made fix on top) into one plain action NAME (the old one kept as NAME_base, NLA tracks removed; proved flat = stack to 0.00 mm); `--pin-foot SIDE[:ref[:from[:to]]][:xy]` holds a planted foot's IK control at one world transform for the whole clip or a range (`xy` = horizontal position only, height and rotation kept; `SIDE:auto` detects a stepping foot's planted phases and holds each); `--action NAME` names the clip to flatten (with a fix stack on top, the strip is re-pointed at the rewritten clip and the fix stays active, so a base can be repaired under an edit in progress); `--speed-segment A:B:F` resamples frames A..B of the result F times faster (fractional-frame evaluation, ends exactly on B); `--hand-grip L|R|LR` sets that hand's fingers to the `Grip` fist on every frame of the result (an empty hand on a two-hander's shaft); `--torso-yaw DEG` counter-rotates the upper body against its own yaw excursion (DEG at the peak, proportional elsewhere, 0 at both ends; an IK left hand rides with the right hand); `--arm-pole-fk` re-aims an arm's elbow pole at the FK chain's elbow on the frames where it is on IK (an IK stretch inside an FK clip, e.g. the gate's reach pull, otherwise sits on the rest pole and jumps at the switch); `--fk-arm` converts an IK arm to FK for the whole clip without changing the pose (so upper_arm_fk / forearm_fk / hand_fk control it); `--mirror-to` writes the X-flipped copy for the other side. Then mark the clip `hand_edited true` in the manifest and export with `anim_batch.py NAME --export-only --force` (the batch skips an unchanged manifest entry otherwise) |
| `glb_retarget.py -- --glb F --name N --mode idle\|loco\|action\|death [--loop 120 --blend 30 --src-start 30 --time-scale 1.0 --smooth 0 --fist 0.3 --finger-life 0.12 --hunch 0 --head-damp 1 --arm-pose P --lock-left-hand 0 --travel-axis auto --mirror] [--save]` | the anim file | Kimodo GLB → Action on the rig (world-rotation deltas, IK-pinned legs for idles, FK legs otherwise). `--time-scale` slerp-stretches the source, `--smooth` low-passes it, `--head-damp 0.45` takes the bow out of a shambling head, `--arm-pose` swaps the arms for an authored socket-frame hand pose (weapon idles), `--lock-left-hand D` pins the left hand D m down the right hand's weapon handle (staff casts); `--stab-aim R|L` swings that arm about the vertical through its shoulder and turns its hand as it extends, so the arm and the hilt axis point straight ahead at full reach (a stab), with `--stab-pitch DEG` / `--stab-yaw DEG` (inward) for the blade's pitch and yaw there, `--stab-roll DEG` for the hand's roll about it (from the forearm's zero-twist hand) and `--stab-shorten D` rig m bending the elbow so the hand comes D closer to the shoulder; `--blade-along-arm R|L` rebuilds that hand every frame so the hilt axis continues the forearm line (a swing), `--blade-roll DEG` about it; `--only-arm R|L` copies only that arm's chain from the source, every other control holding the `--blend-from` pose (the per-arm attack clips); `--gate MIN,MAX` (two-handed attacks) lets it SLIDE where the capture's left hand projects onto the hilt axis, clamped to MIN..MAX rig m below the right hand and smoothed (`--gate-smooth 0.35`), so the second hand rides the shaft through the swing; `--travel-axis x` forces sideways root travel (strafes), `--mirror` swaps left/right in the source (Strafe_Left is the mirrored right strafe). `--arm-keys "0:bow_side,0.4:bow_draw,..."` keys arm presets over the clip (archery, summon, taunt; `free` releases the arm to the source). `--blend-from ACTION[:frame] --blend-in N` starts the clip on that pose and crossfades into the source over N frames (Impaled_Base -> a Kimodo stand-up), adding the presets `base` (the pose's own hand socket frames, following the torso) and `base_out` (right hand slid out along its hilt axis by a blade length); `--elbow-pole` drives the arm IK with a pole vector held outward so an authored hand never folds the elbow into the body; `--ground twoway` (action mode) grounds every frame on its lowest point for clips whose stance changes. `--ground-ignore Robe,Skirt` leaves hems out of the floor measure; `--plant-feet 0.001` (rig m tolerance) keeps FK-copied legs on the floor: the sole is measured on all six characters' boot meshes, a foot the source has on the floor is planted through the leg IK, a boot under the floor is lifted whatever the source does, the hips drop where a planted foot would be beyond `PLANT_REACH` of the leg (no locked knees), the leg's IK pole is put out through the FK knee on every planted frame (the IK knee sat 5 cm inward of the capture's, and the plant weight switching swung the knee in one frame), and every toe keeps only Humanoid's up-down hinge (world sideways axis of the T-pose) so Unity matches Blender; `--blend-from-lift D` adds D rig m on the first frame and fades it out over the crossfade (the blend-from clip's export lift minus this clip's); `--rename jnt|mixamo|ue5` maps a video-mocap skeleton (`*_JNT`, Mixamo names with fingers, or an Unreal mannequin) to the expected joint names; `--bind stacked` for a source whose rest pose is every bone stacked upward instead of a T-pose (mannequin BVHs: shoulders aligned by direction, hips height from the animation); `--src-begin N` drops the first N RAW source frames (with `--src-end`, before `--time-scale`); `--shoulders keep` holds the clavicles on the blend-from pose (a capture with junk clavicles); `--arm-ik R|L` solves that arm with the rig's IK from the capture's hand position (pole swinging with the arm, hand aimed by the knuckle with the hilt along the forearm: nothing of the capture's bone rolls); `--arm-roll-geometric R|L` / `--hand-from-forearm R|L` / `--align-roll` are the FK-side roll repairs that were not enough for that app; `--wrist-fix R|L|LR` runs the wrist twist limiter on that hand every frame; `--fingers` copies the capture's finger joints (two phalanges each) onto the finger chain controls instead of the constant curl; `--heading auto|keep|<deg>` (default auto) rotates the source so the hips' mean yaw against the bind is 0 (a performer standing off-axis otherwise rolls the pinned legs); idle mode lowers the hips by a constant so the IK legs never exceed `PLANT_REACH` (a straight IK leg has no defined roll); `--stance "L:d,R:d"` moves each resting foot forward by d rig m (negative = back); `--still-joints J,...` freezes a source joint's rotation vs its parent to the clip's medoid (a hand the tracker lost; pre-mirror names); `--mode upper` = a one-shot with the legs on IK at rest (an upper-body action that plays over an idle or a walk; the reach drop follows the need per frame so blend-from frames keep the idle's height); `--aim-forward L` (bow hand side) turns the whole body per frame until the shot line (draw hand → bow hand, both raised) points forward: the front foot pivots in place, the rear foot steps round it with a `--step-lift 0.04` arc and the hips follow half-way, and the string hand's fingers are aimed along the shot (Arrow prefab grip along the fingers); `--aim-line shot|sight|arm` picks the line the turn aims (draw hand→bow hand, head→bow hand, bow shoulder→bow hand) and `--aim-offset DEG` (+ = left) where it is aimed; `--anchor 0..1` swings the draw arm in FK until the string hand lies on the plane through the head and the bow hand, levels the elbow on the back/out side and rolls the hand `--anchor-roll 45` deg from the forearm's zero twist (back of the hand out), every per-frame sign choice continuous with the last frame, `--anchor-gap D` rig m keeps that hand D out of the plane; `--bow-square` turns the bow hand, for as long as the bow arm is raised, until its hilt axis (the bow's limbs) is perpendicular to the sight line (to the arrow itself while drawn); `--head-aim` turns the head's yaw onto the sight line while the bow arm is raised; `--head-smooth N` low-passes the neck + head source rotations only; `--time-warp A:B` plays source frames 0..A over B frames (a faster wind-up), before `--time-scale`; `--hand-tilt SIDE:deg` turns that hand every frame about the horizontal axis perpendicular to its hilt (+ = blade up; pitch only — for a blade that continues the arm use `--blade-along-arm`, which fixes yaw and pitch); `--unwind-yaw` removes the hips' net yaw over the used range linearly (the clip ends facing where it started); `--ik-always auto|legs|arms|both|none` (manifest `ik_always`; default auto): a limb that any pass puts on IK stays on IK for the whole clip, the IK target and pole placed on the FK result on the frames no pass touched, so `foot_ik` / `hand_ik` control the limb on every frame (they used to go dead wherever the plant or a hand pass was inactive); auto = legs whenever `--plant-feet` is on, which is exact (feet 0 mm, knees < 1 mm; only the thigh roll differs, and the export strips leg twist); arms only on request, because the IK forearm carries no twist of its own and the capture's forearm pronation on FK frames is lost; `ground_fit true` (manifest; batch only): after the export, `tools/unity/ground_fit.py` measures every model's lowest vertex per frame in Unity and the clip is re-exported with `export_fbx.py --lift-curve Animations/ground_fit/<Clip>.json`, a per-frame Root lift that puts the highest model's lowest point on the floor (the others sink by the sole spread; a constant lift cannot do this); `--hand-grip L|R|LR` gives that hand the `Grip` action's fist on every frame (an empty hand that should close like the holding one); `--drift root` (action mode) puts the take's net hips travel on Root as root motion instead of sliding it out (a step in the take; the batch then imports without in-place); `--speed-segment A:B:F` plays output frames A..B (after `--time-scale`) F times faster, the rest shifting earlier; `--pose-ref ACTION:frame@at` applies the user's reference pose (a one-frame action from `anim_pose_save.py`) as per-control local deltas against generated frame `at`, weighted by the anchor mask so that frame is the reference exactly; `--aim-body S` gives the pelvis and feet that share of the turn (0 = they hold the idle's heading and the spine carries it all, the pelvis re-applied after the chain because Rigify's `spine_fk` is a child of the spine pivot); `--wrist-limit 60` caps an aimed hand's twist about its forearm, the excess becoming forearm pronation (Unity's Humanoid wraps a 180 deg wrist twist into a forearm snap); `--hips-drop D` (rig m) adds a deliberate crouch, faded with the blend-from/to crossfades; `--hand-clear R[:a,b]` keeps that hand's socket (below the shoulders) outside an ellipse round the torso (rig m half-widths, default 0.22 sideways / 0.18 front-back, centred on the hips) by pushing it out through IK on the frames it dips inside; `--prop R:0.69 [--prop-damp 0.2]` aims that hand's hilt axis at a floor point straight ahead at a 0.69 rig m staff's reach and pins the hand on IK at its mean position with that fraction of its motion; `--prop-vertical` puts the hand on the staff's top at its full height, at 90 % of the arm's reach, weapon straight down (the propped idle; pairs with the demo's top-gripped staff prefab); `--hunch DEG` bends the chest forward; `--wrist-twist L:60,R:-20` turns a forearm about its own axis every frame (+ = counterclockwise seen from the hand looking up the arm; the hand and fingers follow); `--torso-ref ACTION[:frame]` replaces the clip's mean torso rotation/position by that pose's (the delta applied to the whole upper body); `--hand-ref ACTION[:frame]` takes the propping hand's position from it; `--hand-offset x,y,z` (rig m) shifts that hand; a target beyond 97 % of the arm's reach is brought in horizontally at its height; `--src-end N` trims the source. Ground correction per mode from the lowest vertex of **all six characters' meshes** (the Ref_ collections are un-excluded for the measurement). Reports gait period, travel, floor and seam | with `--save` |
| `anim_grip_export.py [-- --save]` | the anim file | Keys the hand-authored finger grip (unkeyed pose on the finger controls of both hands) into the action `Grip`; export it with `export_fbx.py -- --clip Grip` and rebuild the prefabs, which sample it into `SkeletonWeapon.gripLeft/Right` | with `--save` |
| `anim_fix_idles.py [-- --save --only Idle,Idle_02 --torso-drop 0.010]` | the anim file | In-place fixes of Idle/Idle_02/Idle_03 (wrists forward, Idle grounded, Idle_02 straightened with Idle's arms); run once per action, it is not idempotent on Idle_02 | with `--save` |
| `anim_stance.py -- --action Idle_02 --left 0.03 --right -0.03 [--save]` | the anim file | Splits the stance of an IK-legged idle: moves each resting foot forward (+) or back (rig m), keeps the knees bent by lowering the torso by one constant if the reach demands it. Not idempotent. The retarget has the same as `--stance "L:-0.055,R:0.055"` (manifest `stance`) | with `--save` |
| `bone_atlas.py -- --out Rig/atlas [--render] [--only a,b] [--body Name]` / `-- --sheets-from` | the anim file | The measured map of every control channel (708) on the bare Knight body, from the identity rest pose, FK controls at `IK_FK 1` and IK controls at `0`: landmarks, socket axes (hilt / back of hand / fingers), head aim, foot direction, jaw gap, fingertips; self-validating; `--render` writes one contact sheet per key control (gitignored). Ported from the creatures pack | writes `Rig/atlas/` |
| `atlas_query.py Rig/atlas/atlas.json <probe>... [--bone B] [--shape swivel] [--inert] [--probes]` | none | "Which channel moves X": sorts the atlas's recorded response (e.g. `jaw_dz`, `hilt_R`, `fingers_R`, `foot_L_fwd`, `footL_min_z`, `index_R_tip`, `head_aim`) | prints |
| `anim_pose_save.py -- --from Idle_Propped:0 --to Propped_Base [--save]` | the anim file | Copies one frame's pose of any action into a one-frame action (a reference the user posed on a generated clip, which a rebuild would erase); the retarget reads it via `--torso-ref` / `--hand-ref` / `--blend-from` | with `--save` |
| `anim_author_impaled.py [-- --save --only Impaled_Idle]` | the anim file | Builds `Impaled_Idle` (genuflect loop, sword through the belly) and `Impaled_Rise` (pull out, gather stand-up, blend to Idle frame 1) from the user's one-frame action `Impaled_Base` (created from Impaled_Idle frame 0 on first run; edit it and re-run). Legs analytic from the base's DEF bones incl. bent toes, arms on IK socket frames, no grounding pass. Export with the default lift | with `--save` |
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

Weapons: `blender -b Weapons/prod.blend -P tools/export_weapons.py` writes every
`Models/Weapons/SM_*.fbx` (12, the Arrow included since 4a70422, the untextured spellbook dropped) with the grip at the origin
and the length along the socket's +Y (grip table inside the script, carried over to rescaled
meshes; `PRE` rotates a mesh modelled along another axis first); `blender -b -P
tools/pack_textures.py -- Weapons` copies colour/normal and packs a metallic-smoothness map
for every weapon in `WEAPON_MAPS` that has a roughness map into `Textures/Weapons/`; then
Unity menu 1 (materials, plain 0/0.35 metallic/smoothness when there is no packed map) and
2 (new `W_*` prefabs, an existing one only swaps the placeholder for its material);
`python tools/unity/grip_sheet.py <out.png>` to review every loadout's grip; `python tools/unity/weapon_shots.py <out> <Clip>
<loadout> [Character]` renders a character playing a clip with a loadout equipped on
the socket bones, in edit mode.

`python tools/unity/grip_sheet.py <out.png> [clip] [character] [t]` renders every weapon
loadout close-up on the holding hands (one row per loadout) to review the hand slots
(`RightHandSlot`/`LeftHandSlot`/`LeftForearmSlot` in the character prefab) and each weapon
prefab's `Grip` (`Prefabs/Weapons/W_*.prefab`).

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
  (Base: every clip as a state; UpperBody / LeftArm / RightArm: Override layers masked by `AM_UpperBody` / `AM_LeftArm` / `AM_RightArm` with the clips the manifest tags `upper` / `left` / `right` (a looping one = a held action, no exit);
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
