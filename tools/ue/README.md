# Unreal Engine development project — `skeletons_ue/` (UE 5.8)

The Unreal twin of the Unity development project `skeletons/`, built entirely by scripts from the same sources.
Ported from the creatures pack's proven pipeline (`smp-10-rgp-creatures/tools/ue/README.md`: units, the stripped
`Armature` node, Interchange pipeline assets, the MCP Blueprint DSL and its traps).

## Rebuild from scratch

    python tools/ue/export_ue.py                     # Blender -> Export_UE/ (models, 48 modules, weapons, 45 clips)
    # open skeletons_ue/skeletons_ue.uproject in UE 5.8 (MCP server auto-starts; Python remote execution is on)
    python tools/ue/ue_py.py tools/ue/ue_build.py models textures weapons materials clips montages
    python tools/ue/ue_weapons.py                    # hand-slot sockets on every body (MCP), then:
    python tools/ue/ue_py.py tools/ue/ue_build.py sockets weapon_blueprints materials
    python tools/ue/build_abp.py                     # ABP_UndeadSkeleton graphs
    python tools/ue/ue_py.py tools/ue/ue_build.py character
    python tools/ue/build_character.py               # BP_UndeadSkeleton graphs
    python tools/ue/ue_py.py tools/ue/ue_build.py character_children
    python tools/ue/build_demo_ui.py trees
    python tools/ue/ue_py.py tools/ue/ue_build.py demo_vars demo_data demo_actors
    python tools/ue/build_demo_logic.py button Setup SetSelected
    python tools/ue/build_demo_logic.py header pawn browser
    python tools/ue/build_demo_logic.py button EventGraph
    python tools/ue/build_demo_logic.py showcase
    python tools/ue/ue_py.py tools/ue/ue_demo_map.py overview demo

`materials` runs again after `sockets`: touching a skeletal mesh asset (the MCP socket tool) has reset its material
slots once; re-running is harmless. Asset edits and saves fail while a Play session runs — stop PIE first.

## Export target (`--unreal` on `export_fbx.py` / `export_weapons.py`)

* CENTIMETRES: SCALE 1.8 x 100 on the data, `scale_length 0.01` during the write (UnitScaleFactor 1). A metres
  file puts scale 100 on `Root` in Unreal and root motion runs 100x (creatures pack).
* `Armature` with one child `Root`: UE strips the node, the skeleton is rooted at `Root`, which keeps the travel.
* No Unity-only fixes: no leg de-twist, no `Body` decoy node, no baked space transform.
* Clip lifts: the manifest's `lift` (engine metres, x100); the per-frame `ground_fit` curves are NOT applied (they
  correct Unity Humanoid's leg reconstruction; Unreal plays the bones verbatim).

Measured (2026-09-29): 68 bones rooted at `Root`, Hips at 98.17 cm, every body 169.5 cm with feet at 0, all 53
meshes on the one skeleton `SKEL_UndeadLegion`; Walk_Fwd_01 72.43 cm per 1.40 s loop (Unity 0.724 m), strafes on
±X, character facing +Y (the mannequin convention; the BP yaws the mesh −90). Idle_01's raised right hand (1.34 m)
is the authored clip: the Unity export evaluates identically.

## Content layout (`/Game/UndeadLegion`)

| Unity | Unreal |
|---|---|
| `Models/<C>/SK_<C>.fbx`, `Models/Armor/<C>/SK_<C>_<M>.fbx` | `Characters/<C>/SK_<C>`, `Characters/<C>/Armor/SK_<C>_<M>`, one `Characters/SKEL_UndeadLegion` |
| `M_<C>_{Body,Armor}` (URP/Lit, MS map) | `Materials/M_UndeadLegion_Master` + `MI_<C>_{Body,Armor}` (armour two-sided), the same PNGs; normal green flipped |
| `Skeleton@<Clip>.fbx` | `Animations/A_<Clip>` (root motion on the locomotion loops; twitches additive vs own frame 0; `AN_BowAttach` / `AN_BowRelease` on Shoot_01 at frames 15 / 21), `Animations/Montages/AM_<Clip>` |
| hand slots on `PF_<C>` | sockets `RightHandSlot` / `LeftHandSlot` on every body: (−x, −y, z)·100 of the Unity slot, Rz(180)·rotation |
| `W_<Weapon>` + `Grip` | `Weapons/Blueprints/BP_Weapon_<Name>`: mesh component at `Grip⁻¹·C·S` (Unreal mesh axes → Unity mesh axes) |
| `AC_Skeleton` (8 layers) | `Blueprints/ABP_UndeadSkeleton` (below) |
| `PF_<C>`, `SkeletonModules`, `SkeletonWeapon` | `Characters/<C>/BP_<C>` children of `Blueprints/BP_UndeadSkeleton` |
| demo scene + `SkeletonShowcase` | `Demo/Maps/UndeadLegion_Demo` (startup map), `Demo/UI/WBP_AnimBrowser`, `Demo/Blueprints/BP_OrbitPawn` |

The grip frames were MEASURED: the skeleton's bone-local frame is Blender's mirrored in Y (`R_ue = S·R_b·S`,
S = diag(1,−1,1), 3 decimals on both weapon sockets), which with `anim_weapon_ref.py`'s Unity→Blender mapping gives
the formulas above. Re-tune in the editor (socket in the skeletal mesh editor, mesh component in the weapon BP);
`weapon_blueprints` never overwrites an existing weapon Blueprint and `sockets` keeps a moved socket.

## ABP_UndeadSkeleton — the layer stack (flat: the toolset cannot build state machines)

    BaseA/BaseB players (fallback) --BlendPosesByBool--> Slot Base --> Slot DefaultSlot -> cache Base
    Layered(Spine1): Base + Slot UpperBody -> cache Upper
    Layered(LeftShoulder): Upper + Slot LeftArm over TwoWayBlend(Upper, Block_L_Idle, BlockAlpha) -> cache Arms
    Layered(RightShoulder): Arms + Slot RightArm
    ApplyAdditive x3: Twitch_01..03 (alpha Twitch1..3) -> cache Body
    Layered(LeftHandPalm1-4), Layered(RightHandPalm1-4): TwoWayBlend(Hand_Idle_<side>, Grip frame 0, Grip<side>), weight Finger<side>

Loops are LOOPING montages in the `Base` slot (`PlayLoop`: StopSlotAnimation on Base, then Montage_Play with
`bStopAllMontages` false), one-shots montages in DefaultSlot / UpperBody / LeftArm / RightArm (`PlayAction` stops only those
four). Both are created with `CreateSlotAnimationAsDynamicMontage_WithBlendSettings` (its blend-settings pins are by-ref: wire a
`MakeMontageBlendSettings`). ⚠ **Root motion reaches CharacterMovement only from montages**: with the loops as graph sequence
players (`RootMotionFromEverything`) the root bone was locked to the capsule — extracted — and the capsule never moved
(2026-09-30); the same walk as a montage moves 51.8 cm/s (Unity 0.52 m/s). Playing with `bStopAllMontages` false is also what
keeps a loop and a one-shot alive together although every slot is in DefaultGroup. ⚠ **A spawned Character has no controller
by default and CharacterMovement does not run without one** (movement mode None): `AutoPossessAI = PlacedInWorldOrSpawned` on
`BP_UndeadSkeleton`. `SetRootMotion(false)` = `IgnoreRootMotion` (in place; the demo recenters).

## BP_UndeadSkeleton API

`WearModule / RemoveModule / IsModuleWorn / SetDefaultModulesWorn` (a leader-pose SkeletalMeshComponent per module:
any module on any skeleton), `EquipLoadout(i)` (spawns the loadout's weapon BPs on the hand sockets; 11 Unity
loadouts; the weapons are separate actors, so `EndPlay` destroys them with the character — they outlived it until
2026-09-30), `PlayLoop(clip)`, `PlayAction(clip, slot, blendIn, blendOut, rate) -> length`, `StopActions`,
`SetHeldBlock`, `SetTwitch(1..3, weight)`, `SetRootMotion`, `SetClipHold` (grip fist on a hand the clip holds: Unity's
`grip_hands`), `SetFingerIdle`, `SetFingersSuspended`, `PauseActions`. Each child sets `DefaultModules` (the armour
map: its own set), `StartLoadout`, `DisplayName`.

## The demo browser (Unity's `SkeletonShowcase`)

Characters are spawned on selection; armour: own set as toggles, All/None, every other character's set to borrow;
weapons: the 11 loadouts; animations in the Unity sections — a masked clip (upper/left/right) plays on its slot while a
locomotion loop runs and full body otherwise, a one-shot from an idle puts its section's idle underneath (it blends
out onto it), deaths hold 2 s with twitches and finger idles off, Block_L_Idle / twitches / hand idles are toggles;
footer Root motion / Turntable / Recenter. Drag (either mouse button) to orbit, wheel to zoom.

## Traps met (all reproducible, 2026-09-29)

* `BlueprintEditorLibrary.get_basic_type_by_name("float")` returns an **int** pin type; the float type is `"real"`.
  Retyping afterwards left stale int pins — remove and re-add the variable.
* Variable getter ids carry the variable's CATEGORY: `Variables|UndeadLegion|GetBaseA`, `Variables|Demo|...`.
* `get_editor_property("materials")` on a skeletal mesh returns struct COPIES: edit them, write a new list back.
* `remove_unused_variables` removes every variable no graph uses yet — including ones just added.
* `SkeletalMeshSocket.socket_name` is read-only in Python; the MCP `SkeletalMeshTools.add_socket` makes mesh sockets.
* Use-cached-pose nodes are not listed by `find_node_types`, but `Animation|CachedPoses|Usecachedpose'<Name>'` creates one.
* The Layered-blend node refuses `add_node_pin`: chain single-layer blends. `BlendListByBool`: `BlendPose_0` = TRUE.
* The DSL: a `switch` ends the flow (put later statements in a wrapper function); switch cases must be `0..n-1`;
  `IsValid` / casts are multi-exec and must be last; `UserConstructionScript` and a widget's bound
  `OnClicked(Btn)` cannot be written by the DSL — place and wire their nodes with `create_node` + `connect_pins`;
  widget events are `UserInterface|EventConstruct` / `UserInterface|EventTick` (add them with `add_event` first);
  `AddComponentbyClass` takes only `:Class`.
* The MCP server does not start by itself on a new project: `Config/DefaultEditorPerProjectUserSettings.ini` sets
  `bAutoStartServer`; the console command `ModelContextProtocol.StartServer` starts it in a running editor.

## Base-pack update of 2026-10-01 (pulled at `3a1e74d`)

What the Unity side added to the BASE edition, carried over (the Extended edition — ragdoll, cloth, NavMesh AI, armies — is a
separate Unity product and is not ported):
* **Reactions**: `Hit_01` / `Hit_02` are ADDITIVE (manifest `additive`: imported additive against their own frame 0) and play
  through `BP_UndeadSkeleton.PlayOverlay` as montages in the new `Hit` slot, an ApplyAdditive over the identity pose after the
  twitches (Unity: the additive `Hit` layer) — added over whatever plays, nothing underneath changes. `Stagger_01` / `_02`:
  full-body one-shots with root motion (66.2 cm back; Unity 0.662 m). The browser's Reactions section; 48 clips.
  `export_ue.py clips Hit_01 Hit_02 Stagger_01 Stagger_02 Run_Fwd_01` re-exported the five changed clips.
* **Root motion on every `drift root` clip** (staggers, 2H attacks, wand casts, taunts, Summon, Cutthroat, Rally), as Unity
  imports them; the Root motion toggle decides.
* **Grips**: `unity_grips.json` was re-dumped (both shields, the battle axe, the staff). `ue_build.py
  weapon_blueprints:H1HeaterShield,H1RoundShield,H2Axe,H2MagicStuff` re-applies a grip to an EXISTING weapon BP (only its mesh
  component's transform: the class and every loadout reference stay).
* **Eyes** (`ue_eyes.py`, step `eyes`): sockets `EyeL` / `EyeR` on the Head bone of every body, seated from each Unity prefab's
  measured `SkeletonEyes.offset` (Knight / Archer 7.1 cm forward, the others 8.6, ±3.0 cm, 2.3 cm up; read from the `.prefab`
  YAML so the engines cannot drift), `M_Eyes` (unlit, emissive `Color` = (5, 0.2, 0.1) HDR), sphere components `EyeL` / `EyeR` on
  `BP_UndeadSkeleton` (0.018 of the 1 m engine sphere) attached by the construction script (`ApplyEyes`); `ShowEyes(On)`,
  `TintEyes(Color)` (an army's team colour). Footer **Eyes** toggle. Both maps have an unbound PostProcessVolume with Bloom
  (intensity 2.5, threshold 1: Unity's `Demo_Volume`), so only the eyes bloom.
* ⚠ **A child Blueprint compiled before a parent variable existed stores the ZERO value as its own** (black eyes on all six:
  `EyeColor` 0 on every `BP_<Character>` while the parent held red). `character_children` resets `EyeColor` / `EyesVisible` on
  the child CDOs (`reset_editor_property`). Rule: after adding a parent variable with a non-zero default, reset it on the children.
* ⚠ **`LevelEditorSubsystem.new_level` refuses an existing map and leaves the CURRENT level open**, so the map builder used to
  rebuild whichever map was loaded; `ue_demo_map.open_map` loads an existing map and creates a missing one.
* ⚠ Blueprint `or` / `and` evaluate both sides: an array read guarded only by `(or (== i 0) ...)` still reads index −1
  (`BuildClips`, the twitch highlight); clamp the index itself. And a DSL `;` comment runs to the end of the line, closing
  parentheses included — a failed `write_graph_dsl` leaves the function EMPTY (the clip list had 0 buttons): never put a comment
  after code on a line.

## Base-pack update of 2026-10-04 (the user's attack set)

Synced at the base pack's `5295a16`+ (2026-10-04). What changed on the Unity side and how it was carried over:
* **The 16-clip attack set** replaces every earlier attack clip: `Attack_R/L_01_Stab`, `_02_Swing`, `_03_Swing` + a `_Heavy` variant of
  each, `Attack_2H_01/02_Swing` + `_Heavy` (CLAUDE.md §1). `export_ue.py clips <names>` wrote them (the six retired exports deleted from
  `Export_UE/`), `ue_build.py clips:<names>` imported them (all in place, `rm off`), `montages:<names>` built their `AM_`, and the
  retired `A_` / `AM_` assets were deleted (`EditorAssetLibrary.delete_asset`). ⚠ **A deleted montage's `.uasset` stayed on disk** (delete
  reported True, the registry re-found the file on its next scan and the asset came back): the six `AM_` files were removed from disk by
  hand after the registry delete. ⚠ `montages` used to crash on the first clip whose montage could not be deleted (`create_asset` returned
  None, nothing built): it now takes `montages:A,B` and keeps-and-logs an undeletable montage.
* **Re-exported clips**: `Idle_1H_Combat`, `Idle_TwoHanded` (verbatim, no fit), `Run_Fwd_02` (0.933 s, 175.1 cm per loop, 187.6 cm/s),
  `Strafe_Left/Right_02` (1.300 s, 84.3 cm, 64.8 cm/s — the user's shorter steps).
* **Grips**: `weapon_blueprints:H2Axe,H2Longsword` re-applied the re-tuned grips (axe yaw 40, longsword yaw 130 in Unity).
* **Browser**: `ue_demo_ui.SECTIONS` carries the new Right arm / Left arm / Two-handed members (the `_Heavy` variants included) and
  `GRIP_L` the four 2H clips; `demo_data` rebuilt (58 clips in 13 sections).
* **Showreel plan**: `showreel_plan.py` renamed to the new clips (the recorder's steps: Warrior 2H_01/02_Swing, Knight axe R_02_Swing,
  sword R_01_Stab + R_02_Swing, Assassin R/L_01_Stab + R/L_02_Swing at 1.6×); `Showreel/unreal/clip_lengths.json` re-dumped from the
  imported assets (a `ue_py` one-liner over every `A_` clip: `get_play_length`), `plan.json` regenerated. The stages were NOT re-rendered.
* Not ported: Unity's `AttackSpeed` Animator parameter (the per-weapon pace lives in the plan's `speed` and `PlayAction`'s rate here);
  the Extended edition; `Rise_01` (not exported anywhere yet).

## Showreel fixes of 2026-10-04 ("the models float slightly"; "the model / camera still gets into position")

Measured in PIE at 1/50 time dilation (a python poll every ~2 game frames, `ue_poll2`-style: actor Z, Root and Hips socket Z,
camera Z, the active montage) and with per-frame image diffs of the rendered shots (`ImageChops.difference` means, spikes listed):
* **The float** was CharacterMovement's floor distance: the capsule rests 2.28 cm above the floor (MIN/MAX_FLOOR_DIST) and the mesh
  sat at −90 under a 90 half-height capsule, so every sole hung 2.3 cm up (+ the idles' Unity lift, 0.4–1.1 cm here, kept: a sole
  1 cm under an opaque floor is invisible). **The mesh sits at −92.3 now** (`BP_UndeadSkeleton`, the six children compiled after it).
  A plane constraint (Z) on the movement component also cured it but BLOCKED horizontal root motion (the staggers stood still): not used.
* **The "getting into position"** was a VERTICAL ROOT-MOTION IMPULSE on the first frame of some root-motion montages: `Taunt_02`
  (and `Cutthroat`, `Summon`, the wand casts in the old render) launched the capsule 12–34 cm up for one frame, the floor logic
  pulled it back over 2–3 frames — a one-frame hop of the whole figure (frame-diff spikes of 6–8 at frame 25 of the Knight /
  Assassin / Necromancer shots). Isolated with test maps (`ue_showreel.py build` with the character, idle, loadout and clip swapped
  one at a time): the CLIP decides (Taunt_02 hops on every character / idle / loadout, Taunt_01 and Rally never, the staggers not),
  not the weapons (their mesh collision is off now anyway), not the montage blend-in (0 hops the same), not the root lock
  (ANIM_FIRST_FRAME the same), not the root-motion mode (`RootMotionFromMontagesOnly` halves it; it is the mode in `SetRootMotion`
  now, the loops are montages anyway); the asset's Root track is flat (0.4 cm lift, roll 90) on every frame and the raw-track
  accessors return nothing in 5.8, so the source of the Z delta is unknown. **The fix: those clips play IN PLACE in Unreal**
  (`ue_anims.ROOT_MOTION_ONESHOTS` = the staggers only; `enable_root_motion` off on the taunts, casts, Summon, Cutthroat, Rally —
  1–8 cm of travel that the pose carries instead, as Unity's in-place import would). An in-place clip's montage never hops.
* **The seamless recenter popped the picture** even for a few cm of drift: the teleport of camera + character re-slices the
  cascaded shadow map (camera-relative), and the first version re-spawned the character at Z 90 while it rests at 92.3 (a 3-frame
  dip). `Recenter` keeps the current Z now, and the plan issues a `recenter` only after the clips in `showreel_plan.RECENTER` (the
  staggers); the attack set is in place, so the weapons stage has no recenter at all and the camera never moves there.
* The weapons stage follows the recorder's 2026-10-04 steps (heavy variants, the Knight mace step, the per-weapon pace `SWORD` 1.3 /
  `DAGGER` 1.7 on the plan's steps instead of a 1.6 override). `BP_Weapon_*` mesh components are `NoCollision`.
⚠ A sub-range render (`render 8 135:143 <shot>`) restarts the shot from its BeginPlay: the director's timeline is not the sequence's
frame, so frames 135–143 show the shot's first frames again — render from 0 to test a later moment. ⚠ `ue_showreel.py build`'s
arguments are split on spaces by `ue_py.py`: loadout names with spaces cannot be passed (use `Mace`, `Sword`, `Dagger`). ⚠ `ue_showreel.py
shot` rebuilds the ONE showreel map: a `render` of another shot's sequence afterwards films the wrong actors (a tiny figure at the edge).

## Death patches (2026-10-05, "the deaths have twitching playing; re-record just the deaths with twitching disabled and edit them in")

The director had no twitch command, so the corpses kept the additive twitch loops and the finger idles (Unity's showcase turns both
off for a death). Now: **RunCommand kind 15 `twitch`** (CmdInt 1 on / 0 off: `SetTwitch` 1..3 and `SetFingersSuspended`), and the
plan emits `twitch 0` at a death step's start and `twitch 1` after its hold. Re-rendering only the deaths without the hours: a
**`patch` stage** built from the plan's own functions — per weapons shot with a death, one shot = [the idle held for P frames] + [the
death step], with **P = Fd mod L** (Fd = the death step's first frame in the full shot, L = the idle loop's frame count; the loop
runs from BeginPlay in both renders and no `loop` restart precedes the deaths, so frame Pf of the patch has the idle at the same phase
as frame Fd of the shot; the twitch loops' phases differ, which only shows if a jerk was mid-way on the cut frame). The four patch
shots are 270 / 267 / 345 / 186 frames (~45 min at 64 samples) against 3476 for the four full shots. `Showreel/unreal/patch_info.json`
records the mapping; `showreel_unreal_all.py --only patch_00,patch_01,patch_02,patch_03 --no-encode` renders them;
**`tools/ue/showreel_patch_deaths.py`** copies each patch's frames from Pf over the shot's frames from Fd (the same count by
construction) and re-encodes the weapons stage and the YouTube cut. The `patch` stage lives in `plan.json` only while needed:
`showreel_plan.py` regenerates the three stages without it.

## Showreel in Unreal (2026-10-01, a first test: the modular stage's opening beat)

`ue_showreel.py build Warrior Idle_03 3` → map `Demo/Maps/UndeadLegion_Showreel` (the stage on a 2 km floor, the class BP with no
weapon and the idle as `StartClip`, a CineCamera with Unity's framing: azimuth −30, elevation 12, 4.0 m, look 1.0 m, vertical FOV
32 = 35.31 mm on a 36 × 20.25 filmback) + `Demo/Showreel/LS_Modular_Test` (one camera cut); `ue_showreel.py render [samples]
[A:B]` queues Movie Render Queue (PIE executor, fixed 30 fps, 8 temporal samples, 60 warm-up frames) → `Showreel/unreal/
modular_test/frame_NNNNN.png`; `showreel_encode_ue.py` overlays the Unity recorder's caption panel and writes the MP4. Traps:
⚠ a map with no PlayerStart spawns the player pawn on the character and depenetration pushes it out of frame (the creatures
pack's trap again); ⚠ the editor's Python caches imported modules between runs — `ue_showreel` reloads `ue_demo_map`, or a fix to it
silently does not apply; ⚠ auto exposure brightened the dark floor and swallowed the eyes' glow: the stage volume uses MANUAL
exposure (`EXPOSURE` +1 EV) with Bloom 8 / threshold 0.5, picked against the Unity frame; ⚠ Unity's ground colour (0.19, 0.19,
0.21) is sRGB: 0.030 / 0.037 linear in the UE material.

### The full showreel (2026-10-02, "all 3 stages, intro and description, same content as the Unity video, best quality")

    python tools/ue/showreel_unreal_all.py [--samples 64] [--only weapons_03] [--no-encode]   (editor running; ~4 h at 64)

1. **`showreel_plan.py`** ports `ShowreelRecorder.BuildModular / BuildMovement / BuildAttacks` and its step loop into
   `Showreel/unreal/plan.json`: per stage a title card + SHOTS (a shot = one character's run of steps; a change of character is
   a hard cut, as in Unity), each with the director commands at output frames and the caption segments. Same frame accounting as
   the recorder: a step holds `seconds`, each attack `round((length / speed + 0.15) * 30) + 2` frames then the settle (0.9 s, a
   death's 1.6 s), root motion recentres after each attack; the return-to-idle rules of `SkeletonShowcase` decide the loop under a
   one-shot; Shoot_01 gets BowAttach 15 / BowRelease 21 + the arrow's 1.2 s hide. Clip lengths: `Showreel/unreal/clip_lengths.json`.
2. **`BP_ShowreelDirector`** (`ue_build.py showreel_director`, graphs by `build_showreel_director.py`) plays a shot's commands on
   the character (`RunCommand` kinds 0–14: loop, action at a rate, equip, wear / remove a module, held block, overlay, root motion,
   seamless recenter, follow the hips, clip hold, pause the corpse, bow string, fire, show arrow), moves the camera like Unity's
   `FollowCamera` (damped position, never rotation) and, while a bow is equipped, poses it (`UpdateBow`: Unity's `BowString` —
   the draw hand in the Brace bone's frame, whose DRAW axis is −Y in Unreal; the Nock on the hand inside the corridor, the limbs
   bent by local roll, upper −10/−14°, lower +10/+14° at 50 cm, return at 8 m/s). `T` starts at −(warm-up + 2) / 30 so a command
   at frame f fires on output frame f.
3. **`ue_build.py showreel_bow`**: `BP_Weapon_H2Recurvebow` gets a PoseableMeshComponent `BowPose` (the skinned bow, the Mesh
   hidden: a SkeletalMeshComponent's bones cannot be set from a Blueprint); `BP_ArrowProjectile` (SM_Arrow with its HEAD — the mesh
   origin, shaft along +Z — turned onto +X by pitch 90, ProjectileMovement 1500 cm/s, no gravity, 4 s life) is spawned at the held
   arrow's mesh origin facing the character's forward, the held arrow hidden 1.2 s. Demo-only for now (see below).
4. **`ue_showreel.py shot <stage> <i>`** builds the map for one shot (character with the shot's first loadout / idle, the
   director, the camera, `LS_<Stage>_<NN>`); **`render 64 all <stage>_<NN>`** renders it with the best settings this machine
   offers on the project's renderer (no Lumen / VSM, as Unity): 64 SPATIAL samples (no motion blur), cinematic scalability, LOD 0,
   no texture streaming, 4096 shadow maps, SSR / AO / tonemapper / bloom at max, anisotropy 16 (`CVARS`). Radeon 780M: ~2.2 s per
   frame. The orchestrator skips a shot whose folder holds every frame and a `.final` marker, and restarts the editor on a failure.
5. **`showreel_stage_ue.py`**: the recorder's 48-frame title card + every shot with the caption panel per segment →
   `Showreel/unreal/showreel_<stage>.mp4`; then **`tools/unity/showreel_youtube.py --src Showreel/unreal --engine "Rendered in
   Unreal Engine 5.8"`** builds `Showreel/unreal/undead_legion_showreel_unreal.mp4` with the same cards, fonts and music as the Unity
   video; `Showreel/unreal/youtube_description.txt` carries its chapter times.

⚠ Python's `subprocess` "bash" on this machine is WSL's (no /bin/bash): the orchestrator calls Git Bash by path. ⚠ A Claude Code
background task is capped at 2 h: the 4-hour render runs as a detached process (log `Showreel/unreal/final_run.log`).

## The Fab package (2026-10-05)

`python tools/make_documentation.py ue` prints the buyer manual (`tools/docs/UndeadLegion_UE_Documentation.html`, the Unity
manual's stylesheet, 10 A4 pages: the Blueprint API from `build_character.py`'s function table, the loadout table, the clip
list with `clip_lengths.json`'s lengths, the speed table in cm/s) to `skeletons_ue/Content/UndeadLegion/Documentation.pdf`
(tracked; the editor ignores a PDF under Content, and Fab wants the documentation inside the package). Then
**`python tools/ue/make_production_ue.py --verify`** writes `../undead-legion-production-ue/UndeadLegion/` (`Config/`,
`Content/UndeadLegion/`, `UndeadLegion.uproject`) and zips it as `UndeadLegion_UE58.zip` (top folder `UndeadLegion/`,
291 files, 95 MB): the showreel map, `Demo/Showreel/LS_*`, `BP_ShowreelDirector` and `Pipelines/IP_*` are left out,
`Developers` / `Collections` never copied, all seven plugins dropped from the `.uproject` (Blueprint-only, no dependency),
`DefaultEditorPerProjectUserSettings.ini` (the MCP auto-start) and the empty `DefaultEditor.ini` removed, the Python
remote-execution block cut from `DefaultEngine.ini`, `/Script/skeletons_ue` renamed, the project name without
"(development)". The audit (the creatures pack's Fab rules): root entries, one Content subfolder, no generated folders,
no empty directories, no redirectors, no `IP_` / `LS_` / showreel asset, no shipped asset importing a dropped plugin's
module (`/Script/PythonScriptPlugin`, `MovieRenderPipeline`, `SequencerScripting`, the MCP modules, `EditorScriptingUtilities`
— NOT `/Script/MovieScene`, an engine module every AnimSequence imports for its data model), no tooling or AI names in any
asset or text file, the manual source free of pipeline names. `--verify` runs `UnrealEditor-Cmd -run=CompileAllBlueprints
-NullRHI` on the COPY (~2 min; 29 pack Blueprints compiled, 0 errors, 0 warnings) and removes the generated folders again
before the zip. Measured in the editor first (`AssetRegistry.get_dependencies` on the shipped set): nothing shipped depends on
anything stripped, no redirectors; the 33 `AM_` montages are referenced by nothing (the character builds its montages at
runtime) and ship as buyer content; `BP_ArrowProjectile` was referenced only by the director and ships as a ready actor.
The description and the manual say what the demo does NOT do: drive the bow string or fire the arrow.

## The Epic-skeleton twin: `skeletons_ue_epic/` (2026-10-05)

User: "let's start with the full transition [to the Epic skeleton], as it makes it look like the asset was actually made for
Unreal Engine, plus less friction for users to test new animations; do it in a separate project sub-folder." `skeletons_ue/`
(Mixamo names) stays as it is; `skeletons_ue_epic/` is the same project rebuilt on the **UE5 mannequin's bone set**, so a
mannequin animation plays on the skeletons unchanged and Fab's "Rigged to Epic skeleton" is true.

**What "Epic skeleton" has to mean, measured.** Unreal stores an animation as absolute LOCAL rotations per bone, so on a skeleton
with the mannequin's hierarchy and the mannequin's bone-axis convention every animated WORLD rotation is the mannequin's whatever
the bind pose or the proportions; the bind pose's A-pose angle does not matter (the first analysis said it did: wrong), the local
axis convention does. The mannequin's reference skeleton was dumped from the editor (`tools/ue/dump_refpose.py` on
`SKM_Manny_Simple` → `Rig/ue5_mannequin_refpose.json`: 89 bones, the character facing +Y with its left at +X like ours, X down
each bone, Y forward, Z to the right on the spine; the RIGHT arm, the right fingers and the LEFT leg point toward the parent;
twist bones at 1/3 and 2/3 of their parent; `ik_hand_gun` / `ik_hand_l/r` / `ik_foot_l/r` equal to the hands' and feet's frames;
`interaction` / `center_of_mass` at the root). The pipeline's Blender→Unreal frame map was verified on all 68 bones of the Mixamo
export before anything was written: `x_ue = M(x_b)`, `y_ue = -M(y_b)`, `z_ue = M(z_b)`, `pos_ue = M(head)·180`, with
`M(x, y, z) = (x, −y, z)` (5e-7 worst error).

**The spec**: `python tools/epic_skeleton.py` → `Rig/epic_skeleton.json` (93 bones = the 89 + `jaw_01` / `jaw_02` under `head`
+ `pelvis_l` / `pelvis_r` under `pelvis`, which carry skirt and robe weights). Every bone's frame is the mannequin's re-aimed by
the least rotation onto OUR bone's direction (sign per bone: toward the child or toward the parent as the mannequin has it;
the foot's X continues the shin, the ball's X runs along the toe); the three Rigify spine bones become five at the mannequin's
stations along our spine polyline (pelvis 0, spine_01 0.064, spine_02 0.182, spine_03 0.308, spine_04 0.456, spine_05 0.793,
neck_01 1), each rigid with the DEF bone whose span holds its head (spine_01 ← Hips, spine_02/03 ← Spine, spine_04 ← Spine1,
spine_05 ← Spine2); twist bones rigid with their parent at the stations; ik bones copies of hands and feet; the thumb's parent
is the hand, the metacarpals are Rigify's palm bones.

**The exporter**: `tools/export_epic.py` (`python tools/ue/export_ue.py --epic [models|clips]` → `Export_UE_Epic/`; the weapons
stay in `Export_UE/Weapons`). A model: the spec's bones as Blender edit bones through the inverse frame map, the vertex groups
remapped — a DEF bone's weight goes to its target; the split spine by the vertex's station along the DEF bone (pelvis below 0.42
of Hips, else spine_01; spine_02 / spine_03 at 0.72 of Spine; spine_04; spine_05); the upper arm / forearm / thigh / shin weight
shared with the two twist bones by a hat function over the stations, so mannequin clips twist the limbs the way they do on the
mannequin while OUR clips (the twist on the bone itself, the twist bones identity) deform exactly as before — up to 8 influences.
A clip: per frame `W_target = W_DEF · W_DEF(rest)⁻¹ · W_target(rest)` for all 93 bones, the basis decomposed and keyed
(rotation everywhere, location on `root` and `pelvis` only), `root` = Rigify's root location + its yaw, the lift on root Z; 4 s
per clip. `Export_UE_Epic/frames.json` carries the hands' and head's new frames and the old weapon-socket frames.

**The build**: the same steps as above with `UL_EPIC=1` (`bash tools/ue/epic_build_all.sh [assets|sockets|abp|character|demo|map]`,
the editor open on `skeletons_ue_epic` through `editor_up.sh skeletons_ue_epic`). `ue_common.EPIC` is detected from the open
project's folder in the editor and from `UL_EPIC=1` / `--epic` in system Python (`import unreal` is optional there now);
`EXPORT` becomes `Export_UE_Epic`, `bn()` maps the bone names the steps touch (`Hips`→`pelvis`, `Spine1`→`spine_04`,
`Head`→`head`, `LeftShoulder`→`clavicle_l`, the weapon-socket bones → `hand_l` / `hand_r`), the finger layers blend from the four
metacarpals + `thumb_01` per hand. **Sockets**: there are no weapon-socket bones, so `RightHandSlot` / `LeftHandSlot` sit on the
hands with `T = hand_new⁻¹ · weaponbone_old` (from `frames.json`) folded into the Unity slot transform. Measured after the import:
all 93 bones, every frame within 0.06° and 0.000 cm of the spec; 53 modules + bow on the shared skeleton; 59 clips with the loops'
root travel on `root` (Walk_Fwd_01 72.4 cm per loop as before); 33 montages.

**Verified against the mannequin** (`tools/ue/epic_anim_test.py`, `tools/ue/epic_pose_shot.py`): the Knight body imported a
second time AGAINST the mannequin's own `SK_Mannequin` skeleton asset binds (the buyer's "Assign Skeleton" path; our extra bones
are merged into it), and with `MF_Unarmed_Walk_Fwd` parked at 0.45 s on SKM_Manny and on that Knight in a Simulate session every
one of the 89 shared bones' world rotations agrees to 0.00° (median 0.00°). ⚠ Three traps on the way: (1) the template's
mannequin content must live at `Content/Characters/Mannequins` — its assets reference each other at that path; copied to
`Content/Mannequins` the meshes and clips had no skeleton (a poseable mesh then asserted `AssetSkeletonObj` in FBoneContainer
and crashed the editor); (2) an edit-mode viewport never evaluates a SkeletalMeshActor's clip (every capture showed the
reference pose): pose in a Simulate session, and set the component's SAVED play data (`SingleAnimationPlayData`:
`anim_to_play`, `saved_position`, `saved_play_rate` 0) — `set_animation` only reaches the live instance and the simulation's copy
started with no clip; read the simulated actors through `UnrealEditorSubsystem.get_game_world()`; (3) Git Bash rewrites a
`/Game/...` argument into `C:/Program Files/Git/Game/...` — `MSYS_NO_PATHCONV=1` before every `ue_py.py` call that passes an asset path.
The mannequin content and `/Game/_EpicTest` are test-only: `make_production_ue.py --epic` leaves them out.

**In the shipped demo** (`tools/ue/epic_demo_probe.py`, a PIE probe: `play` / `where` / `weapons` / `action ANIM [rate]` /
`montage` / `turn YAW` / `stop`, captures through `capture_editor.py` — the MCP viewport capture renders the EDITOR world, which
PIE is not, Simulate is): the Knight spawns with sword and shield on `hand_r` / `hand_l` (the slots 5.8 / 6.1 cm from the hand
bones, the weapons attached to them), the eyes glow in the sockets, and `PlayAction` with a MANNEQUIN clip (`MM_Attack_01`,
`MF_Unarmed_Walk_Fwd`) plays it on the Knight once the two skeleton assets list each other as compatible (`epic_demo_probe.py compat`;
the shipped `SKEL_UndeadLegion` carries NO such reference — the buyer adds the compatibility in their project, one click, documented
in the manual's section 12 together with Assign Skeleton and the IK Retargeter). ⚠ `unreal.Rotator(a, b, c)` is (roll, pitch, yaw):
`Rotator(0, 90, 0)` pitched the character onto its face; use keywords. The `ABP_UndeadSkeleton` ASSET is now created by the step
`ue_build.py abp_asset` (the Mixamo project's was made by hand once), and `eyes` must run after `character` and before
`build_character.py` (its graphs read `EyesVisible` / `EyeColor`): `epic_build_all.sh` has that order. The manual
(`make_documentation.py ue`) prints into the Epic project since 2026-10-05 (11 pages: section 12 is the mannequin-animation
recipe); `make_production_ue.py --epic --verify` → `../undead-legion-production-ue-epic/UndeadLegion_UE58_Epic.zip`.
⚠ The MCP-built widgets and graphs stay UNSAVED in memory: after a complete build `WBP_DemoHeader` was missing on disk (the
package audit counted 2 widgets) while the editor showed it — `ue_build.py save_all` (`EAL.save_directory(PKG, only_if_is_dirty)`)
ends `epic_build_all.sh` now; run it before packaging or restarting the editor. `ue_build.py showreel_bow` builds the bow's
`BowPose` and `BP_ArrowProjectile` here too and skips its director part when `BP_ShowreelDirector` is absent.

**The UE-animation test map (2026-10-05, "since skeletons_ue_epic is a dev environment, add another map for testing UE animations on
our skeletons").** `/Game/Dev/Maps/UE_AnimTest`: the demo browser with the pack's 13 sections plus seven mannequin sections (unarmed
loops, attacks, jump / dash, hit reactions, deaths, rifle, pistol: 102 clips in 20 sections) on any of the six characters with their
armour and weapons. Built by `tools/ue/ue_uetest.py assets` (a child widget `/Game/Dev/UI/WBP_UETestBrowser` of `WBP_AnimBrowser`
and a child showcase `/Game/Dev/Blueprints/BP_UETestShowcase` of `BP_DemoShowcase`, plus a `Browser` variable on the child),
`build_demo_logic.py uetest` (the child showcase's BeginPlay = the parent's with the child widget class and `SetBrowser`; the child
WIDGET gets the parent's whole EventGraph as its own — UMG decides whether a widget class ticks from that class's graphs, and with an
empty one the parent's Tick never ran: no orbit-pawn target, the camera stayed on the player start), `ue_uetest.py data`
(`demo_data()` takes the widget, the sections, the clip asset paths, the return idles and the loco sections now; the UE one-shots
return to `MM_Idle`, the deaths hold; `RootMotionOn` false by default — the mannequin clips carry root motion and the first jog ran
the Mage out of frame), `ue_uetest.py map` (`ue_demo_map.demo(path, showcase, label)`). Everything sits under `/Game/Dev`, so
the package never carries it and the shipped Blueprints are untouched. Before it on a fresh clone: `python tools/ue/
epic_mannequin_content.py` (the template content into `Content/Characters/Mannequins`, git-ignored) and `ue_py.py tools/ue/
epic_demo_probe.py compat` (SK_Mannequin lists SKEL_UndeadLegion; one-sided is enough, measured). Driving it from Python in PIE:
`epic_demo_probe.py open /Game/Dev/Maps/UE_AnimTest`, `play`, `button KIND INDEX` / `clip NAME` (the browser's own `OnButton`
through the showcase's `Browser`), `stop`. ⚠ The editor caches `ue_demo_ui` / `ue_demo_map` between runs: `ue_uetest.py`
reloads them (`demo_data() got an unexpected keyword argument` was the stale module).

## Not done yet

The recurve bow's string pull and the fired arrow in the DEMO (the showreel director does both; the notifies exist on Shoot_01
but `AN_BowAttach` / `AN_BowRelease` have no Received_Notify graph yet); the in-place locomotion blend space;
the Unity "Specials return to the last idle" is implemented, the Cast_Staff_01 → Idle_Staff hand-off at frame 54 is a
plain return; Unreal-side grounding measurement per clip; a full cook of the Fab package and an interactive open of the zip on
a clean machine.
