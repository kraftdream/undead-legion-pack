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

## Not done yet

The recurve bow's string pull (Unity `BowString`) and the fired arrow (`ArrowProjectile`) — the notifies exist on
Shoot_01 but `AN_BowAttach` / `AN_BowRelease` have no Received_Notify graph yet; the in-place locomotion blend space;
the Unity "Specials return to the last idle" is implemented, the Cast_Staff_01 → Idle_Staff hand-off at frame 54 is a
plain return; Unreal-side grounding measurement per clip; a Fab production copy.
