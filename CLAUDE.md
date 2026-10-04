# Undead Legion Pack — Modular Skeleton Army

Commercial asset pack for the **Unity Asset Store** and **Unreal Fab**: a skeleton
army in **six** class variants, each built from **one shared humanoid rig** with
**swappable armour modules**, shipped with a single retargetable animation set.

Working title: **Undead Legion — Modular Skeleton Army**

---

## 1. Current state

Verified 2026-09-19 by probing the `.blend` files headlessly (`tools/rig_check.py`)
and importing the exports into Unity 6000.4 through the editor bridge.

| Character | Mesh | Textures | Shared rig | `SK_*.fbx` in Unity | Humanoid avatar | Materials + prefab | In demo |
|---|---|---|---|---|---|---|---|
| Skeleton Knight      | done | done | **yes** | **yes** | **valid, 53 bones mapped** | **yes** | **yes** |
| Skeleton Archer      | done | done | **yes** | **yes** | valid | **yes** | **yes** |
| Skeleton Assassin    | done | partial (no `armor_metallic`) | **yes** | **yes** | valid | **yes** | **yes** |
| Skeleton Mage        | done | partial (no `armor_metallic`) | **yes** | **yes** | valid | **yes** | **yes** |
| Skeleton Necromancer | done | partial (no `armor_metallic`) | **yes** | **yes** | valid | **yes** | **yes** |
| Skeleton Warrior     | done | done | **yes** | **yes** | valid | **yes** | **yes** |
| Armour modules (48)  | done | per character | **yes** | `Models/Armor/<Char>/SK_<Char>_<Module>.fbx` x48, Generic / No Avatar (2026-09-27) | n/a | `Prefabs/Armor/<Char>/A_<Char>_<Module>.prefab` x48, `M_<Char>_Armor` | **yes** (each character dressed from the armour map; any piece on any skeleton) |
| Weapons (12 meshes)  | done | all textured (8 full PBR; staff, recurve bow, wand colour + normal; arrow colour only) | n/a | `SM_*.fbx` ×12 (the recurve bow skinned to its own 8-bone rig, Generic / No Avatar, 2026-09-27) | n/a | `M_Weapon_<Name>` ×12 (+ unused placeholder) | **yes** (11 loadouts, `W_*` prefabs; the propped staff removed 2026-09-25) |

Shared clips so far: `Idle`, `Idle_02`, `Idle_03` (loops, 8 / 12 / 12 s) +
`Twitch_01..03` (additive), on `AC_Skeleton`. Armour materials render both faces
(torn cloth, open hoods); body materials stay single-sided.

All six characters share one armature (§2), every body and armour module is skinned to
it, and every exported model imports in Unity with the **same 68-bone hierarchy**
(66 + two weapon sockets), the same bone array on every renderer, Hips at 0.982 m and
mesh nodes at identity rotation.

**First clips exist (2026-09-19), so the skeleton is frozen.** As of 2026-09-22 there
are **37 clips** in `Assets/UndeadLegion/Animations/` (`Skeleton@<Name>.fbx`, 30 fps,
every one verified on all six models with `verify_clip.py` + `ground_clip.py`; plus
`Skeleton@Grip.fbx`, finger-pose data) and `AC_Skeleton.controller` (8 layers, §8
"Layered animation"):

| Group | Clips |
|---|---|
| Idles (loop) | `Idle_01` (`Idle` until 2026-09-28: "rename idle to idle_01"), `Idle_02` (hand-fixed 2026-09-21: blades forward, Idle grounded, Idle_02 upright with hanging arms, left foot 5 cm forward / right 5 cm back), `Idle_03` (the user's own video-mocap idle, 2026-09-21, slowed 3×, 10.8 s loop, fingers from the capture, right foot 10 cm forward / left 10 cm back); weapon idles `Idle_TwoHanded` (the user's mannequin recording, 2026-09-23: two-hander held ahead, both hands on the shaft), `Idle_Bow`, `Idle_Staff` (`Idle_Wand` removed 2026-09-24: "enough idle animations"; the H1Wand loadout stays, the Cast_Wand clips play over Idle_Staff / Idle; **`Idle_Propped` and the "Staff (propped)" loadout removed 2026-09-25** at the user's request: export, manifest entry, build state, fit curve, the `W_H2MagicStuff_Top` prefab, the builder's row and `ProppedHandHeight`, the grip dump entry, the demo list; the actions `Idle_Propped` / `Propped_Base` and the `prop` / `hunch` / `torso_ref` retarget passes stay as tools) |
| Impaled (hand-authored) | `Impaled_Idle` (loop: on its knees, hunched, sword through the belly), `Impaled_Rise` (one-shot: pulls it out, stands up, ends on the neutral standing pose) — **not exported since 2026-09-26** (user: "remove impale idle/rise from the export for now"): FBX + meta, build state and controller states removed, the actions and the tools stay; `Impaled_Rise`'s manifest entry carries `disabled true` (`anim_batch` skips such entries), `Impaled_Idle` never had one (`anim_author_impaled.py` writes both); drop the flag and re-export to bring them back |
| Twitch (additive) | `Twitch_01/02/03` head + jaw |
| Locomotion (loop, root motion) | `Walk_Fwd_01`, `Walk_Back_01`, `Run_Fwd_01` (renamed from `Run_Fwd` 2026-09-29; a Kimodo redo the same day was reverted), `Strafe_Left_01` (mirrored right), `Strafe_Right_01` (the `_01` index added 2026-09-26: the low-rank shambling set; a small-step redo of both strafes on 2026-09-29 was reverted); **`Walk_Fwd_02`, `Run_Fwd_02`** (2026-09-25: the "normal" pair, an upright human walk and jog for the higher ranks such as the necromancer and mage, Kimodo without the stiff-undead prompt profile), **`Walk_Back_02`** (2026-09-26, the same for the walk back), **`Strafe_Left_02` / `Strafe_Right_02`** (2026-09-26, the same for the side-steps) |
| **The user's attack set (2026-10-04, replaces every earlier attack clip)** | `Attack_R_01_Stab`, `Attack_R_02_Swing`, `Attack_R_03_Swing` + a `_Heavy` variant of each (the same arm, a bigger body lunge in the hips: 13–25 cm against 0–8), `Attack_L_*` = the X-flipped mirrors (`anim_nla_bake --mirror-to`, within 2.5–15 mm of the exact mirror), `Attack_2H_01_Swing`, `Attack_2H_02_Swing` + `_Heavy` — 16 clips, hand-animated by the user in the anim file (the old `Attack_R/L_Stab`, `Attack_R/L_Swing_01/02`, `Attack_R/L_Slice`, `Attack_2H_01/02/03/04`, `Attack_R_Swing_07` actions, exports, manifest entries, fit curves and build state are gone). Manifest entries carry only `layer` (right / left / full), `mode action`, `hand_edited`, **`lift 0`** and no `ground_fit` (user: 'all clips are fine-tuned to avoid this'): the FBX is the action verbatim, `anim_batch` accepts an entry with no `glb` when it is `hand_edited` and run with `--export-only`. All in place (root travel ≤ 3 cm, average speed 0.000 on all six); with no lift the Knight's lowest vertex sits −0.3..−8 mm, the other four −2..−12 mm, the Necromancer's hips-weighted robe hem 19–176 mm under on the lunges. The AI's `hitAt` = the hand-speed peak measured per clip (stab 0.30 / 0.27 heavy, swings 0.46–0.50, 2H 0.54 / 0.43); the `_Heavy` variants are extra moves with more damage and reach. Demo sections, `SkeletonAI`, the showreel script, the layering proof, `layer_smoke`, both manuals renamed; `AC_Skeleton` rebuilt (Idle + 50 Base states, 6 per arm layer, grip states on the four 2H clips), the demo scene and the Extended controller / prefabs / browser rebuilt (⚠ rebuilding the Extended controller alone leaves the `PFX_` prefabs without a controller — run Extended *Build All (1-4)*). Verified in play mode: a swing from standing full-body on Base and back to `Idle_1H_Combat`, a swing over `Walk_Fwd_01` on the RightArm layer, a heavy 2H as a full stop. The Unreal side is NOT synced to these names. |
| Per arm (2026-09-22/23, replaces the one-handed set) | `Attack_R_Stab`, `Attack_R_Slice` (redone 2026-09-26, experimental, from the user's `melee in place.glb`: frames 60–104 / 1–50, plain transfers at the take's own tempo, both feet frozen, in place; the `attack_ref5` builds are the `_base` actions), `Attack_L_Stab`, `Attack_L_Slice` (the same mirrored), `Block_L_Idle` (loop: shield held up on the left arm, a HELD action in the demo). Each lives on its arm's masked layer (`LeftArm` / `RightArm`) and as a full-body state on Base; the Animator carries the transitions |
| One-handed swings (2026-10-02, replace the slices) | `Attack_R_Swing_01`, `Attack_R_Swing_02` + the mirrored `Attack_L_Swing_01/02` (user: "replace the slice animation with swing: frames 0–57; swing_02 frames 64–122; `P: handed extras.glb`"). The mannequin app, 153 frames at 30 fps = the user's 122 × 1.25, so their numbers were 24 fps again (at face value swing_02 ends mid-air with the hand at 1.73 m): source 0–71 / 80–152, each rest to rest (`onehand_extras_mocap.glb` → `onehand_extras_arm.blend`). Plain transfers like the ref5 attacks (`mode action`, `plant_feet`, `drift root` — the performer lunges ~0.4 m and back, net root travel 2–6 cm —, `unwind_yaw` + `unwind_ref body`, `lift 0.004`, `ground_fit`): 72 / 73 frames (2.4 s), the hand's peak 5.8 / 5.4 m/s at t 0.41 / 0.42 (the AI's `hitAt`), worst hand step 35° / 25° per frame (the swing's speed), boots on the floor (the Necromancer robe 6 cm under on Swing_01). `Attack_R/L_Slice` removed (exports, metas, fit curves, manifest entries, controller states; the actions stay in the anim file); the browsers' arm sections, `SkeletonAI` (OneHanded: Swing_01, Stab, Swing_02; dual daggers and unarmed: Swing_01), the showreel script (Slice → Swing_01; the stages were NOT re-recorded) and the controller's layering proof use the swings. 50 clips now. **`Idle_1H_Combat` still carries the slice's first-frame arms** (its join to the swings is 21–27 cm of hand travel, the stab's 31–35): rebuild it with `--arms-from "Attack_R_Swing_01:1:R,Attack_L_Swing_01:1:L"` if the crossfade reads big. **Second round (same day: "the return to idle is too snappy; no feel of weight; swing_01: in the wind-up the weapon should face back, in the strike the attack direction — it strikes with the palm; after the attack the facing changes")**, measured first: the take stood 28° off the idle's facing at both ends (hips −26..−29°) and imported its root rotation as root motion; the hand kept the hilt ~85° off the forearm for the whole swing with the PALM leading the strike (palm vs motion 8–13° at impact) and the hilt pointing left in the wind-up. Now: manifest **`heading first`**, **`bake_rot`** (new batch key: `verify_clip --bake-rot 1` on a non-loco clip, the root rotation in the pose — Unity yaw 0.00), **`bake` as a LIST OF RUNS** (new: each a separate `anim_nla_bake` call, in order — a speed segment is one per run, applied from the clip's end so the earlier frame numbers hold), `--start-blend` / `--end-blend Idle_1H_Combat:1:6 / :16` (both ends ON the idle's frame 1: 0 cm at the join), speed segments for weight (Swing_01: the wind-up's top 0.7×, the strike 1.25×, the recovery 1.15× → 69 frames, the hand peaks at 10.4 m/s at t 0.46; Swing_02: wind-up 0.8×, the top 0.7× → 79 frames, 7.5 m/s at t 0.41; the AI's `hitAt` follows), and on Swing_01 the new bake pass **`--hilt-path`** (`R=1:rec,8:rec,20:-0.8/0/-0.6/0.7,25:-0.3/0/1/0.7,29:edge/0.9/45,34:edge/0.9/45,46:rec`: key specs `rec` / `arm` / a character-frame direction `f/l/u[/w]` / `edge[/w[/deg]]` — the full strike orientation, the knuckle side (socket +X) leading the motion, the hilt across the motion at `deg` off the forearm; the change split into forearm pronation on `forearm_fk` and the rest on `hand_fk`): hilt back-and-down behind the head through the top of the wind-up, still trailing up-back into the downswing, knuckles leading within 2–9° and the hilt 46–49° off the forearm at impact. ⚠ Two traps found on the way: a strike target recomputed from the hand's per-frame velocity flipped 180° when the hand reversed at the bottom of the swing (forearm +100° → −71° in one frame, Unity forearm 82° / hand 159° — an `edge` key's motion direction is now its KEY frame's, carried with the upper arm); and an `edge` hilt along the forearm (deg 0) needs an 80° wrist bend — 45 is the natural limit. Unity's worst per-frame steps now are the strikes themselves (forearm 24–39°, hand 29–57° in the whip), no flips; boots ≤ 11 mm under after the fit (the Necromancer robe 6 cm). **Third round ("fix the swing_02 weapon trailing")**: the rising forehand (hand low-right → high-left) carried the weapon LEADING the motion (hilt 37° off the path). Swing_02's `--hilt-path` is `1:rec,8:rec,21:trail/0.5/31,27:trail/0.6/31,32:edge/0.9/45,34:edge/0.9/45,46:rec` with a new key type **`trail[/w[/F]]`** (the weapon square to the forearm — the fist's own angle, so no wrist bend — pointing AGAINST frame F's motion, reached by forearm roll). The pass gained three things on the way, each found as a one-frame snap in Unity: (1) **a wrist limit `--hilt-wrist 40,140`** that pulls the change back toward the clip's own hand until the hilt is 40–140° off the forearm (pushing the hilt out radially flipped side near the forearm line: 68° hand steps); (2) **every key's target is computed ONCE at its own frame and carried with the upper arm** (a per-frame target from the forearm and the motion has no stable side where the forearm lines up with the motion: 95° steps); (3) a direction-only trail ("back and down") cannot be reached with the forearm pointing down — a wrist bends ~45°; the reachable trail is forearm ROLL. ⚠ Swing_02's full trail needs ~170° of added pronation (the recorded weapon points across to the left, the trail back-right) and Unity wraps a forearm twist that large (168° steps): the trail weight is 0.5–0.6, i.e. the weapon hangs down-back in the wind-up and lies across the motion into the whip, not fully behind — a full trail on this take needs the recorded hand rolled the other way first. Steps now: Swing_02 forearm ≤ 35°, hand ≤ 53°; Swing_01 unchanged (forearm 39°, hand 52°). |
| Two-handed | `Attack_2H_01` (downward chop with a step), `Attack_2H_02` (raise and horizontal sweep) — the user's mannequin recording (2026-09-23), legs planted, left hand on the handle through the two-handed GATE (slides 0.03..0.11 rig m below the right hand) |
| Bow | `Idle_Bow` hand-edited 2026-09-27 (knees 3 cm narrower than the retarget's build by the pole swivel, at the retarget's height; `Idle_Bow_base` is that build); `Shoot_01` (redone 2026-09-25 from the user's mannequin recording `aoe cast shoot.glb`: raise, draw at the cheek, release, lower, 1.9 s; the shot goes where the recorded feet point, `heading feet`; the video-mocap build of 2026-09-22 and `Shoot_02` retired; 2026-09-27: the user's `Shoot_01_Fix` baked, `hand_edited`, and animation events `BowAttach` 15 / `BowRelease` 21 on the clip — the recurve bow is a skinned model now and its string follows the draw hand between them, and a fired arrow flies along the character's forward on the release, §8 "The recurve bow bends"; imported in place; legs from `Idle_Bow`'s stance under the take's hips) |
| Magic | `Cast_Wand_01/02`, `Cast_Staff_01` (both hands on the staff; redone 2026-09-27 from the user's `cast staff.glb`, frames 88–155, in place, both feet frozen) — the user's mannequin recording `magic attacks.glb` (2026-09-25); `Cast_Staff_02` retired |
| Specials | `Summon` (necromancer, both hands overhead), `AOE_Cast` (mage; redone 2026-09-27 from the user's `aoe cast.glb`: a left-hand gesture, then the staff raised overhead and lowered, 4.8 s, on `Idle_Staff`'s legs, in place; a hold/release split was tried and reverted), `Taunt_01/02/03` (warrior), `Cutthroat` (assassin), `Rally` (knight, sword raised) — all from the user's recording `taunts.glb` (2026-09-25); the Kimodo `Taunt` retired |
| Reactions | `Hit_01` (head and shoulders snap back, recovers, feet planted; `hit_c3`, seed 33), `Stagger_01` (since 2026-09-30 late: Hit_01 added over one full cycle of Walk_Back_01 at 1.4×, 1.40 s, 66 cm of root motion back; the Kimodo one-step build is `Stagger_01_onestep` in the anim file, the first build `stagger_c1` folded over) — 2026-09-30, Kimodo with the skeleton profile, three candidates each (GLBs kept), picked on contact sheets + `reacteval`-style numbers (hips travel, chest pitch, knee range, feet travel); plain action-mode transfers, in place, ground fit (boots ≤ 9 mm under; the Necromancer robe 12.7 cm under in the stagger's fold, the hips-weighted hem). In the demo's Reactions section |
| Death | `Death_01` (drops straight down), `Death_02` (face-down), `Death_03` (flat on the back), `Death_04` (limp, like a puppet) — the four instant-fall Kimodo generations the user kept on 2026-09-27 from seven candidates, the full 100-frame generations on the rig with no floor pass and no lift (§8 "Death candidates"); the user gives each one's start frame; the old struck-on-the-back / kneel-and-crumple deaths are gone |

**Measured speed table** (Unity, Humanoid, root motion on, Knight; the other five are
identical because the avatar is shared). Ship these numbers with the pack:

| Clip | Length | Travel per loop | Speed |
|---|---|---|---|
| `Walk_Fwd_01` | 1.400 s | +0.724 m | 0.52 m/s |
| `Walk_Back_01` | 1.967 s | −0.662 m | 0.34 m/s (redone 2026-09-24; upper body from Idle_03) |
| `Run_Fwd_01` | 0.967 s | +1.107 m | 1.14 m/s (`Run_Fwd` until 2026-09-29) |
| `Walk_Fwd_02` | 1.133 s | +1.455 m | 1.28 m/s (the upright "normal" walk, 2026-09-25) |
| `Run_Fwd_02` | 0.933 s | +1.753 m | 1.88 m/s (the "normal" jog; the user's 29-frame edit, re-exported 2026-10-04) |
| `Walk_Back_02` | 1.467 s | −1.132 m | 0.77 m/s (the "normal" walk back, 2026-09-26) |
| `Strafe_Left_01` | 1.467 s | −0.293 m (X) | 0.20 m/s (steps 30 % shorter 2026-09-24 and 30 % again 2026-09-26) |
| `Strafe_Right_01` | 1.467 s | +0.293 m (X) | 0.20 m/s (the mirror of the finished Strafe_Left_01) |
| `Strafe_Left_02` | 1.300 s | −0.843 m (X) | 0.64 m/s (the "normal" side-step, 2026-09-26; the retarget's mirror of the right; the user's shorter-step edit pulled 2026-10-04, was 1.204 m / 0.93) |
| `Strafe_Right_02` | 1.300 s | +0.843 m (X) | 0.64 m/s (the same edit, 2026-10-04) |

Measured on all six models: Idle travel 0, Head 5.2° / Hips 2.5° of motion; Twitch_03
over Idle adds Head 5.7° / Jaw 4.7° peaks with Hips at 0.00°. Every clip's lowest baked
vertex is ≥ 0 on every model except `Death_02` (Necromancer robe −5.6 cm during the
kneel, §8 "Grounding"). Not yet authored: turns, knockdown/get-up
(the showcase already lists those sections and skips missing clips). The pipeline test
clip `Test_RootMotion` stays in the anim file, not in Unity.

### Unreal development project (2026-09-29)

`skeletons_ue/` (UE 5.8, Blueprint-only) is the Unreal twin of `skeletons/`, rebuilt by scripts from the same
sources: `tools/export_fbx.py` / `export_weapons.py --unreal` write `Export_UE/` in centimetres, `tools/ue/` imports and
builds everything (shared skeleton `SKEL_UndeadLegion`, 48 leader-pose armour modules, weapon Blueprints on hand-slot
sockets carried over from `unity_grips.json`, `ABP_UndeadSkeleton` with the Unity layer stack, `BP_UndeadSkeleton` +
six `BP_<Character>`, the UMG animation browser map `Demo/Maps/UndeadLegion_Demo`). Everything, including the traps,
is in `tools/ue/README.md`; read it before touching the Unreal side. Synced with the base pack at `3a1e74d` (2026-10-01): the reactions
(Hit_01/02 additive overlays, Stagger_01/02), the re-tuned grips and the red glowing eyes; the Extended edition is not ported.
**The full showreel rendered by Unreal (2026-10-02)**: `python tools/ue/showreel_unreal_all.py` (the Unity recorder's three stages
ported shot by shot, `BP_ShowreelDirector`, 64-sample Movie Render Queue, ~4 h on this machine) → `Showreel/unreal/
undead_legion_showreel_unreal.mp4` (3:59, the same cards and music as the Unity cut) + `youtube_description.txt`; details in
`tools/ue/README.md` "The full showreel".

### Known gaps

- `SkeletonMage`, `SkeletonNecromancer` and `SkeletonAssassin` have **no `armor_metallic.png`**;
  Knight, Archer and Warrior do. Either those armours are non-metallic by design (then
  the material must not sample a metallic map) or the bake was skipped.
- **Weapons** (2026-09-20, updated 2026-09-21 from the teammate's commit `4a70422`):
  `Weapons/prod.blend` is the only source; `weapons.blend` is history. Twelve of the
  thirteen meshes carry UVs and textures (`Weapons/<lower>_{color,normal[,roughness,metallic]}.png`,
  packed by `tools/pack_textures.py -- Weapons` into `Textures/Weapons/`, materials
  `M_Weapon_<Name>` made by the import setup; a weapon without a roughness map gets no
  packed map and plain `_Metallic 0 / _Smoothness 0.35` instead of the 1/1 that the packed
  map normally drives). `H2Recurvebow` replaced `H2Longbow` (the `SM_`/`W_` longbow assets
  were deleted); `H1Wand` is a textured 0.39 m short staff and has its own loadout now; the
  `Arrow` is a real 29 cm arrow modelled along +Y, so `export_weapons.PRE` rotates it onto
  the length axis first (the old 2 cm arrow and the `--only Arrow` export from
  `weapons.blend` are gone). Grips carried over by relative position along the length as
  before (`OLD_EXTENT`); new entries: recurve bow at the riser's middle (roll 90 like the
  longbow), wand 10 cm up the shaft. `H1Spellbook` (no UVs, never textured) was removed from
  the pack on 2026-09-21 at the user's request: not exported, no loadout, its `SM_`/`W_`
  assets deleted (the mesh stays in prod.blend). The prefab
  builder now swaps the placeholder for the weapon's own material on an EXISTING `W_*`
  prefab (the Grip is still never touched). `Weapons/prod.blend1` keeps arriving from the
  remote as a tracked file (autosaves are ignored by our `.gitignore`, §5).
- The **old mesh-only exports in the character folders are superseded but still
  tracked**: `skeleton.fbx`, `armor.fbx`, `mesh_quad.fbx`, `mesh_uv.fbx`. The Unity
  copies (`SkeletonKnight_{Body,Armor}.fbx`) were deleted on 2026-09-19 and every prefab
  now builds from `SK_<Character>.fbx`. Deleting the repo-root ones is safe.
- The Asset Store validator has not been re-run since the prefabs and demo were rebuilt.
- The **Archer's head** was skinned against a rig whose neck/head/jaw bones sat ~18 mm
  forward of the shared rig's; it now binds to the shared rig. Posed deviation is
  ≤ 6 mm on the skull and helm. Acceptable, but look at the Archer first if a neck
  clip reads wrong. **Its skull sat 11.2 mm rig (20 mm engine) FORWARD of the other
  five (2026-09-29, user: "the archer helm on warrior is a bit misaligned, too far forward")**:
  the Archer's skull is the Knight's skull mesh translated by (0, −0.0112, +0.0015) rig m
  (ICP, translation only, residual 0.1 mm), so its helm, made for that skull, sat forward on
  every other skeleton, and every other helm sat back on the Archer. Fixed in `SkeletonArcher/
  prod.blend` (session script `archer_head_shift.py`: every Body and Helm vertex moved by that
  vector times its head + jaw weight share, 407 body vertices, 24 of them partial through the
  neck, the whole helm; `rig_check` OK, the skull now equals the Knight's to 0.0 mm), `SK_
  SkeletonArcher.fbx` + `SK_SkeletonArcher_Helm.fbx` re-exported (the other modules unchanged,
  restored from git after the export). Verified in Unity with side renders: the Archer helm on
  the Warrior and the Knight covers the skull (the bare back of the skull stuck out before), the
  Archer's own fit unchanged, avatar valid, 68 bones. Rule: **a module fits every skeleton only
  if every skeleton's MESH sits on the shared rig the same way; when a borrowed piece is off on
  all but its owner, register the owner's body against the others, not the piece.** The
  modular showreel stage was re-rendered after this fix.
- Rest-pose `>4 influences` exist in the sources (Body 42 verts, Warrior skirt 290);
  `export_fbx.py` cuts to 4 and re-normalises at export, so Unity never truncates.

---

## 2. The one constraint that governs this pack

**Modularity is a rig promise, not a mesh promise.** A buyer expects any armour piece
to drop onto any skeleton and animate correctly. That holds only if:

1. **One armature, shared by all six characters and every armour module.** It lives in
   **`Rig/skeleton_rig.blend`** (Rigify metarig `Meta-Rig` + generated `RIG-Meta-Rig`,
   389 bones, 65 deform, no B-bone segments). Each `prod.blend` carries a *copy* put
   there by `tools/rig_sync.py`; `tools/rig_check.py` proves the copy is unchanged
   (every bone's name, parent, head, tail and roll against `Rig/skeleton_rig.json`).
   **Never edit the rig inside a character file.** Edit the library, re-run
   `rig_lib_dump.py`, then `rig_sync.py` on all six.
2. **Every armour module is skinned to that armature**, not parented to a bone. This is
   true today for all 54 meshes (`rig_check` fails on any dangling modifier, non-bone
   vertex group, unweighted vertex or non-identity object transform).
3. **Unity Humanoid avatar is configured once and reused.** Armour modules are their OWN
   assets since 2026-09-27 (`Models/Armor/<Char>/SK_<Char>_<Module>.fbx`: the shared skeleton +
   that one skinned mesh, imported Generic without an avatar; `Prefabs/Armor/<Char>/
   A_<Char>_<Module>.prefab` with the character's armour material and an `ArmorModule`) and
   bind to ANY character by BONE NAME (`ArmorModule.Attach`: the renderer's `bones` rebuilt
   against the character's transforms, `rootBone` likewise, the piece reparented, the
   module's own skeleton discarded) — which requires identical bone hierarchies, i.e. rule 1.
   The character models `SK_<Char>.fbx` are BODY-ONLY (the Humanoid avatar source); the
   prefab builder dresses each `PF_<Char>` from the **armour map** (`CharacterPrefabBuilder.
   ArmorMap`: character -> `Char:Module` entries, every character's own set by default) at build
   time, and `SkeletonModules` toggles the default set and wears any other character's piece at
   runtime (the demo's modules panel lists the other five sets to borrow from). A module prefab
   dropped in a scene is a prop in its rest pose on its own bones.

Get this wrong and the fix is re-authoring every clip.

### Weapons are the exception

Rigid props, attached to the **weapon socket bones** that are part of the shared
skeleton: `DEF-weapon.L/R` in Blender, `LeftWeaponSocket` / `RightWeaponSocket` in the
export, children of the hands, deform-flagged, no weights (`tools/rig_lib_add_sockets.py`).
Grip convention, in the socket's own bone frame, identical in Unity and Unreal:

- head = centre of the palm (mean of the four palm-bone midpoints)
- **+Y = along the hilt, out of the fist on the thumb/index side** (blade direction)
- **+Z = out of the back of the hand**
- +X completes the right-handed frame (roughly along the fingers)

**Slots and grips (2026-09-20, user request: "slots in skeleton hands that I can
configure, and slots on each weapon where it connects, respecting rotation").** Two
editable transforms meet at attach time:

- **Hand slots** on the character prefab: `RightHandSlot` (child of the
  `RightWeaponSocket` bone), `LeftHandSlot` (under `LeftWeaponSocket`), plus a
  `LeftForearmSlot` (under `LeftForeArm`) that nothing uses since shields moved to the
  hand. Move/rotate them in the prefab with the gizmo. The prefab builder creates missing
  ones at the defaults (`SkeletonWeapon.Default*`: right (−0.0079, 0.008, −0.0352), left
  (0.0086, 0.010, −0.0384) — the user's own tuning on the Warrior, 2026-09-21, copied to
  the other five) and **carries edited ones over on every rebuild** (proved: an edited
  Warrior slot survived Rebuild Character Prefabs). All six share one skeleton, so one
  set of slot values fits all; tune on any character and copy (the copy is a 20-line
  `execute_code`: read the poses from one prefab, `LoadPrefabContents` the others).
- **Weapon prefabs** `Prefabs/Weapons/W_<Name>.prefab`: `Mesh` (the `SM_*` model with its
  material) + a child `Grip`. Move/rotate `Grip` on the weapon. Created once by the prefab
  builder (Grip at identity, since the export already puts the grip at the mesh origin,
  blade +Y, back-of-hand +Z); an existing weapon prefab is never overwritten, delete it to
  regenerate. Loadouts reference these prefabs, not the FBX. **Shields are hand-held**
  (user decision 2026-09-21, `Hand.Left`): their Grip starts 4.5 cm behind the boss and
  rolled −90° about the face normal, so the fist closes on a handle behind the plate and
  the plate's top points towards the wrist; the grip finger pose applies to that hand.
- `SkeletonWeapon.AlignGrip(weapon, slot)` places the weapon so `Grip` coincides with the
  slot in position and rotation (verified to 0.00000 m / 0.000° after moving either).

The per-weapon table in `tools/export_weapons.py` still sets the mesh origin (the
starting point for `Grip`); `tools/unity/grip_sheet.py` renders every loadout close-up
for review.

**Fingers close on whatever a hand holds (2026-09-20).** The grip is hand-authored in
`Animations/skeleton_anim.blend` on the individual finger controls of both hands (the
user's `grip` action keys the body but no finger, so the pose lived only in the saved
pose state); `tools/anim_grip_export.py -- --save` keys it into the action `Grip` and
`export_fbx.py -- --clip Grip` ships it as `Skeleton@Grip.fbx`, a two-frame clip that is
finger-pose DATA, not a demo state (the controller builder skips it). The prefab builder
samples it on each model through its own avatar and stores the 15 finger bones' local
rotations per hand on `SkeletonWeapon` (`gripLeft` / `gripRight`); `ApplyGrip()` writes
them in LateUpdate, after the Animator, to every hand that holds an item (a forearm
shield counts for the left hand), so any clip keeps its own fingers on an empty hand and
the grip on a full one. The
weapon meshes in `Weapons/weapons.blend` are not yet re-origined to this convention.

---

## 3. Repository layout

```
undead-legion-pack/
├── Rig/
│   ├── skeleton_rig.blend     THE armature (Rigify metarig + generated rig + widgets)
│   └── skeleton_rig.json      bone table dumped from it; what rig_check compares against
├── Animations/
│   └── skeleton_anim.blend    THE file clips are authored in: rig LINKED from Rig/ as a
│                              library override, all six bodies + armour appended as
│                              reference (Ref_<Character>, only the Knight enabled),
│                              weapons appended, 30 fps. Actions live here, nowhere else.
├── Skeleton{Knight,Archer,Assassin,Mage,Necromancer,Warrior}/
│   └── prod.blend + textures + reference + (superseded) mesh-only FBX exports
├── Weapons/                   weapons.blend + mesh_quad.fbx
├── tools/                     headless Blender + Unity scripts, see tools/README.md
│   ├── rig_lib_build.py       (one-off) built Rig/skeleton_rig.blend from the Knight
│   ├── rig_lib_add_sockets.py adds/refreshes the weapon socket bones in the library
│   ├── rig_lib_dump.py        library -> skeleton_rig.json
│   ├── rig_sync.py            put the library rig into a character file, normalise it
│   ├── rig_check.py           assert a character file matches the library (exit 1 if not)
│   ├── anim_file_build.py     create / refresh Animations/skeleton_anim.blend (keeps actions)
│   ├── anim_test_clip.py      authors the Test_RootMotion pipeline clip
│   ├── export_fbx.py          model: character file -> SK_<Character>.fbx
│   │                          clip:  anim file + `--clip Name` -> Skeleton@Name.fbx
│   └── unity/                 mcp_call.py (stdio MCP client), probe_fbx.py (model
│                              import check), verify_clip.py (clip import + root-motion
│                              measurement on all six models)
└── skeletons/                 Unity project (Unity 6000.4.0f1, URP 17.4.0)
    └── Assets/UndeadLegion/
        ├── Animations/        shared clips — Skeleton@<Clip>.fbx, retarget to all six
        ├── Demo/{Scenes,Scripts,Editor}
        ├── Materials/{URP,BuiltIn}
        ├── Models/<Character>/SK_<Character>.fbx   rigged BODY only, Humanoid (2026-09-27)
        ├── Models/Armor/<Character>/SK_<Character>_<Module>.fbx   one skinned module + the skeleton, Generic
        ├── Prefabs/Armor/<Character>/A_<Character>_<Module>.prefab   module prefab (material + ArmorModule)
        ├── Prefabs/{Characters,Armor,Weapons}
        └── Textures/<Character>/
```

`Animations/` is **flat and shared**: six characters on one rig means one clip set.

**Clip adjustment (decided 2026-09-20).** The animations are the same for all six, so
they live on ONE model: `Animations/skeleton_anim.blend` is where a Kimodo clip is
hand-adjusted (the rig override animates like a local rig; enable another `Ref_*`
collection to check the clip on that body), then `export_fbx.py -- --clip <Name>` and
`verify_clip.py`. Per-character `prod_copy.blend` files with the actions were built and
verified that day and then dropped as redundant. Lesson kept from that: an Action does
not carry pose-bone state. If clips are ever appended onto another rig, set each bone's
rotation mode from the keys it receives (the finger masters are keyed in Euler; on a
quaternion-mode bone the keys are ignored, the thumb came out 53° off) and force IK
stretch off, as `glb_retarget.zero_pose` does; with that, an export from a copy matched
the shipped clip to 0.0000° on all 68 bones.

---

## 4. Conventions

**Model export** — `export_fbx.py` on a character file writes (since 2026-09-27) the body-only
`SK_<Character>.fbx` (the deform skeleton under `Armature/Root` + `Body` as a sibling of
`Armature`) and one `Models/Armor/<Character>/SK_<Character>_<Module>.fbx` per armour module
(the same skeleton + that mesh), all at **1.8× the Blender metres** (Hips 0.982 m, skull top
≈ 1.70 m, helmet ≈ 1.81 m); `--legacy` writes the old single file with every mesh. Unity
import: the body **Humanoid, Create From This Model, `globalScale = 1`, materials None, no
animation**; the modules **Generic, No Avatar**, otherwise the same.

**Bone names in the export** are Mixamo-style, produced by `export_fbx.game_name()`:
`Hips, Spine, Spine1, Spine2, Neck, Neck1, Head, Jaw, Jaw2, Left/Right{Shoulder, Arm,
ForeArm, Hand, HandPalm1-4, HandThumb1-3, HandIndex1-3, …, Pelvis, UpLeg, Leg, Foot,
ToeBase}`. Unity maps 53 of the 65 (fingers, jaw and UpperChest included); `Neck1`,
the palms, pelvis helpers and `Jaw2` are extra transforms — your own clips drive them,
third-party humanoid clips leave them at rest.

**Animation authoring and export** — author every clip as an Action on the override
rig in `Animations/skeleton_anim.blend` at **30 fps**, then
`blender -b Animations/skeleton_anim.blend -P tools/export_fbx.py -- --clip <Name>` →
`Assets/UndeadLegion/Animations/Skeleton@<Name>.fbx`: rig only, one take named after
the clip, plus an empty node called `Body` that reproduces the model files' node paths
(without it Unity's "Copy From Other Avatar" yields zero clips, silently). Unity import:
Humanoid, avatar copied from `SK_SkeletonKnight`, then
`python tools/unity/verify_clip.py Assets/UndeadLegion/Animations/Skeleton@<Name>.fbx`
to measure it on all six models. **Never author clips in a character file**:
`rig_sync.py` replaces the rig object there and the animation data goes with it.
`anim_file_build.py` may be re-run to refresh the reference meshes; it keeps actions.

**Textures** — `<part>_<map>.png`: `body_color`, `body_normal`, `body_roughness`,
`armor_color`, `armor_normal`, `armor_roughness`, `armor_metallic`. `*_orig.png` are
pre-edit backups, tracked but **not shipped**.

**Unity import** — normal maps `Texture Type: Normal map`; colour sRGB on; packed
metallic/smoothness sRGB off (see §7 for the packing).

---

## 5. Git hygiene

- `*.blend1` are Blender autosaves, gitignored. The headless tools save with
  `save_version = 0` so they never create one.
- **Every headless save of `skeleton_anim.blend` must be `compress=True`** (as `glb_retarget` and
  `anim_nla_bake` do): the file is 21 MB compressed and 290 MB raw, and GitHub rejects the push
  above 100 MB (2026-09-25: two `compress=False` saves did that; re-saved compressed, commits redone).
- `skeletons/.gitignore` is anchored; tracked: `Assets/`, `Packages/`, `ProjectSettings/`.
- `.meta` files are tracked and load-bearing (import settings, GUIDs).
- `.git` is already large. Git LFS is the lever if clip exports push it further, but it
  changes clone workflow and carries a quota — a deliberate decision, not a default.

---

## 6. Tooling

- **Blender 5.2 only.** Every `.blend` is saved by 5.2.44 and will not open in 4.3.
  Headless: `"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b <file> -P <script>`.
  The Rigify add-on is **not** loaded in background mode (`pose_bone.rigify_parameters`
  does not exist there) — the tools read the metarig's bones directly instead.
- **Unity MCP** — server `uvx --from mcpforunityserver==10.2.0 mcp-for-unity
  --default-instance skeletons`; the Editor bridge listens on `127.0.0.1:6400`.
  `--default-instance` is deliberate: `~/.unity-mcp/unity-mcp-port.json` holds a stale
  entry claiming port 6400 for a different project. The MCP tools are **not exposed as
  Claude Code tools in this project's sessions**; drive the server over stdio with
  `python tools/unity/mcp_call.py list | call <tool> '<json>'`. `execute_code` runs a C#
  method body (CodeDom, C# 6 — no `?.`, no string interpolation) and **blocks
  `AssetDatabase.DeleteAsset`** unless `safety_checks=false`; delete on disk and
  `refresh_unity` instead. ⚠ Never delete `Assets/_PipelineTest` while a `verify_clip.py` may still
  be saving into it: the editor then blocks on a MODAL "Moving file failed" dialog (its temp
  controller cannot be moved into the missing folder), the bridge logs "Command TCS timed out (N
  consecutive)" and every call hangs, with the editor's CPU flat. Diagnose with a window listing of
  the Unity process (a second visible window is the dialog; `PrintWindow` renders it), recreate the
  folder, click its "Try Again" button (`SendMessage BM_CLICK`), then delete the folder on disk and
  refresh (2026-09-25).
- **Asset Store Tools** is embedded at `skeletons/Packages/com.unity.asset-store-tools`.
- Blender MCP (`C:\Users\vadym\.local\bin\blender-mcp.exe`) exists but the rig work is
  all scripted headlessly now; prefer the scripts, they are reproducible.

---

## 7. Demo scene, prefabs and submission validation

`Assets/UndeadLegion/Demo/Scenes/UndeadLegion_Demo.unity` — the animation-browser
demo, rebuilt 2026-09-19 on the model of the creatures pack: characters (top-left),
armour MODULES with All/None (left), ANIMATIONS grouped in sections (right: "Right arm",
"Left arm (block = hold)" — Block_L_Idle's button toggles the held block —, Two-handed, Bow,
Magic…, plus a
"Twitch (additive, toggle)" section: each twitch is a toggle that, while on, loops on its
own additive layer over whatever the base and upper-body layers play, all three on by
default, remembered across character switches), footer with Root Motion / Turntable
toggles and Recenter. The random trigger firing (`SkeletonTwitch`, the game-side way to
twitch a crowd) is disabled in the demo so it does not stack on the loops.
Drag to orbit, wheel to zoom. Verified in play mode: six characters, Idle looping on
each, module toggles, twitch firing, no console errors.

**Everything is generated by menu items in `Demo/Editor/`, never hand-edited:**

| menu (`Undead Legion/…`) | script | does |
|---|---|---|
| 1. Import Setup | `UndeadLegionImportSetup.cs` | texture importers (colour sRGB, normal `NormalMap`, packed map linear + alpha from input), `SK_*` model importers (Humanoid, scale 1, materials None), `M_<Char>_{Body,Armor}` URP/Lit materials |
| 2a. Rebuild Armour Module Prefabs | `CharacterPrefabBuilder.cs` | `Prefabs/Armor/<Char>/A_<Char>_<Module>.prefab` from every `Models/Armor/<Char>/SK_*.fbx`: the character's armour material, `ArmorModule {character, moduleName}`; regenerated every time (nothing hand-tuned) |
| 2. Rebuild Character Prefabs | `CharacterPrefabBuilder.cs` | `PF_<Char>.prefab` from the body-only `SK_<Char>.fbx`: body material, Animator (own avatar, `AC_Skeleton`, root motion on, always animate), CapsuleCollider 1.8/0.35, dressed from `ArmorMap` (each module prefab attached by bone name, marked `ArmorPiece`), `SkeletonModules.defaultModules`, `SkeletonTwitch`, `SkeletonWeapon`; root at exactly 0/0/1 |
| 3. Rebuild Demo Scene | `DemoSceneBuilder.cs` | also fills `SkeletonShowcase.armorCatalogue` (every character's module prefabs from the map); lights (1.10 key / 0.45 fill / 0.30 rim, skybox ambient 2.0 — the creatures pack's measured turntable rig), ground, camera + `DemoTurntable`, EventSystem + `DemoEventSystemBootstrap`, the uGUI canvas, `SkeletonShowcase` wired to all six prefabs |
| Rebuild All (1-3) | | the three in order |

Textures reach the project through `tools/pack_textures.py` (Blender + numpy: copies
colour/normal, packs `R = metallic` / `A = 1 − roughness` into
`<part>_metallicsmoothness.png`; characters without a metallic map get R = 0). ⚠ It
copies by **content**, never by mtime: a git checkout stamps every file alike, and the
Knight's body texture in Unity was a stale pre-retexture copy that an mtime check kept
("skeleton textures seem to be wrong": 33 % of the body faces on black). The check
that catches this is to sample `<part>_color` through the imported mesh's UVs at
triangle centroids and count near-black hits, in Unity and in the source `.blend`;
they must agree. Reference (2026-09-19): bodies ≤ 0.7 %, armour Knight 7 %, Assassin
4 %, Mage 2 %, Necromancer 22 % (dark cloth, present in the source art), others < 1 %. Runtime
scripts live in `Demo/Scripts/` (`SkeletonShowcase`, `SkeletonModules`, `SkeletonTwitch`, `SkeletonWeapon`,
`BowString`, `ArrowProjectile`, `SkeletonFootLock`, `ShowreelRecorder`, `DemoTurntable`, `DemoUI`, `DemoEventSystemBootstrap`), namespace `UndeadLegion.Demo`.
Legacy uGUI Text on purpose (no TMP import prompt for buyers); input read through both
backends. `tools/unity/demo_smoke.py` plays the scene headlessly and screenshots it.

### Import decisions

- **Avatar Lower Arm Twist = 1.0 on all six `SK_` models (2026-10-04, "during Attack_2H_02_Swing the right forearm snaps between two
  frames; in Blender the forearm is alright; fix the cause").** Measured: the clip's forearm carries 150–180° of axial twist relative to its
  rest (the pronated two-handed grip) and crosses ±180° on frames 7 / 18 / 22 / 35; the hand's own twist is ≤ 4°. Unity stores that as the
  `Right Forearm Twist In-Out` muscle at ±1.97–1.99 and wraps its sign at the crossings — the same orientation for the chain, but the
  avatar's default Lower Arm Twist 0.5 puts HALF the value on the forearm BONE (+89° vs −89°): a 178° vambrace snap with the hand and the
  weapon in place (`HumanPoseHandler` per frame + per-frame local-rotation steps; the Warrior at 0.5 snapped 179° on the same clip after
  the Knight at 1.0 read 9°). At 1.0 the forearm bone takes the whole value, a wrap is invisible (180 ≡ −180) and the vambrace shows the
  authored twist. `UndeadLegionImportSetup.SetModel` sets `humanDescription.lowerArmTwist` (`LowerArmTwist` const; the dirty check
  includes it); the legs keep 0.5 (measured better than 1.0 / 0.0 on 2026-09-21). All 58 clips in `Animations/` scanned on the Knight afterwards: no arm
  bone step above 60° except the strikes' own motion. Rule: **a Unity-only forearm snap with a quiet wrist is the twist wrap; measure
  the forearm's rest-relative twist (a `HumanPoseHandler` muscle at |value| ≈ 2 is the signature), never re-author the clip.**
  Side effect: writing `humanDescription` makes each `SK_*.fbx.meta` carry the explicit 53-bone human map (it was `human: []`,
  auto-mapped at import), so the six metas grew by ~750 lines each; the avatars are valid humanoids with the same 53 bones and the
  `PF_` prefabs reference them unchanged (no prefab rebuild needed).

- **Scale**: `SK_*.fbx` bake the 1.8 at export and import at **`globalScale = 1`**.
  The old mesh-only Knight FBXs (globalScale 1.8) were deleted on 2026-09-19.
- **Smoothness**: URP has no roughness input; the packed `_metallicsmoothness` map
  drives `_MetallicGlossMap` with `_Metallic = 1`, `_Smoothness = 1`. Raw
  roughness/metallic PNGs are not shipped.
- **Colour space**: normal maps `NormalMap`; packed map `sRGB = false`,
  `alphaSource = FromInput`; albedo sRGB.
- **Materials**: `materialImportMode = None` on every FBX; `Materials/URP/` is the
  single source of truth (twelve character materials + `M_Demo_Ground`).

### Production project (2026-09-29)

`python tools/make_production.py --verify` writes `../undead-legion-production/` (a sibling of this repo, so the art is not
duplicated in git; its own `.gitignore`, `Library/` kept between runs): the Unity project a buyer's package is exported from, with
nothing that describes how the pack was made. It copies `Assets/UndeadLegion` (minus `Demo/Editor` and `ShowreelRecorder`),
`Assets/Settings`, the input actions, `ProjectSettings` (product name "Undead Legion", the cloud project link cleared, the demo scene
as the only build scene) and the Asset Store publishing tools; drops the editor-bridge, collaboration, multiplayer-center and
navigation packages from the manifest; strips EVERY comment from the 13 runtime scripts (a literal-aware C# tokenizer) and adds a
one-line summary per type; rewrites the tooltips that narrated the pipeline. **Every FBX embeds the absolute path of its source
.blend** (Blender's DocumentUrl): overwritten in place with `Source/<name>.blend` padded to the same byte length, so the binary
layout stays valid (111 files). A scan of every text file and FBX for process markers must come back empty, and the batch-mode open
must compile with no errors and no missing scripts (a project's FIRST open can log two errors from Unity's own Shader Graph package
while packages resolve; the second open is clean). Re-run it after any change in `skeletons/`; never edit the production copy. It refuses to run while the production project is open in Unity (it replaces `Assets/`).
**The buyer documentation** is `Assets/UndeadLegion/Documentation/UndeadLegion_Documentation.pdf` (9 A4 pages: overview, setup, folders,
characters with triangle counts, armour modules and the wear/remove API, weapons, loadouts, slots and grips, the bow events, the clip list,
the controller's layers, the speed table, the scripts, the demo scene, own animations, technical details), printed from
`tools/docs/UndeadLegion_Documentation.html` by `tools/make_documentation.py`; edit the HTML and re-run it when the content changes.

### Extended edition (2026-09-29)

User: "an extended project version that current users can upgrade to, or new buy directly: cloth physics for armour with cloth, full-body
ragdoll, simple NavMesh navigation / controls, other ideas"; extras chosen: army spawner, hit reactions, spawn & death VFX, simple combat AI;
packaging: a SEPARATE listing (the full base + extras, upgrade discount from the base; `_store/unity_listing_extended.md`). Everything lives
in `Assets/UndeadLegion/Extended/` (runtime namespace `UndeadLegion.Extended`, editor `UndeadLegion.ExtendedEditor`); the base assets are
used as they are, three small additions to `SkeletonWeapon` (`HeldItems`, `ForgetHeldItems`, `ReequipCurrent`, for dropping weapons into
the ragdoll). **Generated, never hand-edited**: menu *Undead Legion / Extended / Build All (1-3)* (`Extended/Editor/ExtendedBuilder.cs`):
(1) `AC_Skeleton_Extended` = a copy of `AC_Skeleton` + params `MoveX` / `MoveZ` + two 2D freeform-directional blend trees on Base,
`Locomotion_Heavy` (the `_01` clips at their measured speeds 0.52 / 1.14 / −0.34 / ±0.20) and `Locomotion_Upright` (`_02`: 1.28 / 1.87 /
−0.77 / ±0.93), + the weapon idles as UpperBody states (with `SkeletonGripState`); (2) `Extended/Prefabs/PFX_Skeleton<Char>` = prefab
VARIANTS of the base `PF_` with the extended controller and `SkeletonRagdoll` (built: 11 bodies, CharacterJoints), `SkeletonHitReaction`,
`SkeletonHealth`, `SkeletonCloth`, `SkeletonDissolve` (shader referenced), `SkeletonEyes`, `NavMeshAgent` (r 0.32, h 1.8) +
`SkeletonNavController`, `SkeletonAI`; (3) the arena scene `Extended/Scenes/UndeadLegion_Extended_Demo.unity`: ground (Plane ×10),
6 pillars + 2 walls marked **NotWalkable** by `NavMeshModifier` (their tops became walkable islands, a skeleton stood on one), a
`NavMeshSurface` with **`buildHeightMesh`** (without it every agent stood 8.3 cm above the floor, the navmesh's voxel height), baked and
saved as an asset, URP camera with post (Bloom, ACES, vignette) + `RtsCamera`, two `ArmySpawner`s (teams 0 / 1, teal / red eyes),
`ExtendedDemo` (runtime uGUI panel: raise 8v8 / 16v16, battle, clear, cloth / death mode / dissolve toggles; left click select = possess,
right click move / attack, Ctrl+click strike, Alt+click kill). The dissolve shader `Extended/Shaders/UndeadLegionDissolve.shader` wraps
URP Lit's passes (ForwardLit, DepthOnly, DepthNormals cut by height + noise with an HDR edge; the ShadowCaster is not cut, so the effect turns
the renderer's shadows off while it runs).

Measured and fixed in play-mode probes (a throwaway `ExtProbe` MonoBehaviour under `_PipelineTest/` that logs a timeline and renders frames
itself, the Python side only polls a `done.txt` — the bridge stalls on long play tests): 8v8 battle to 3–4 survivors in ~35 s, no errors;
**dropped weapons** were orphans that outlived the corpse (now in `SkeletonRagdoll.Dropped`, dissolved with it and destroyed in its
`OnDestroy`); **eyes** sat on the forehead — the socket centres measured by raycasting the baked body mesh (all six skulls: x ±0.036–0.043,
y +0.023, surface z 0.066–0.071 from the Head bone) → offset (0.036, 0.029, 0.062), size 0.017; the eye point light at 5 cm from the skull
saturated the whole face (inverse square), so `addLight` is off by default and sits 30 cm ahead when on; the **hit-reaction springs**
flipped sign on a 0.33 s frame (semi-implicit Euler at ω·dt ≈ 3) and are sub-stepped at 1/120 s; the **area-cast and bolt lights** flooded
nearby skeletons (now 0.5 / 0.8 intensity, colour normalised from the HDR value, the flash faded over 0.45 s). All three death modes, the
demo's raycast strike / kill path and `Revive` (back on the animation, root on the ground, weapons re-equipped) verified.

**Shipping**: `make_production.py --edition extended` → `../undead-legion-extended-production` (adds `Extended/` minus its Editor folder,
keeps `com.unity.ai.navigation`, both demo scenes as build scenes with the arena first, product name "Undead Legion Extended"); the base
edition excludes `Extended/` and drops the navigation package. Both verified: 0 markers, clean compile on the second open. Buyer doc
`Extended/Documentation/UndeadLegion_Extended_Documentation.pdf` (7 pages, from `tools/docs/UndeadLegion_Extended_Documentation.html`,
`make_documentation.py extended`). Not done: the Asset Store validator on either edition, an extended showreel.

**What the base edition includes (user decision, 2026-10-01: "the base version should also include eyes and hit/stagger
animations").** The split is: animation, art and the glowing eyes are BASE; physics, navigation, AI and armies are EXTENDED.
- **Hit / stagger clips: base, already in place.** `Hit_01`, `Hit_02` (additive, on `AC_Skeleton`'s `Hit` layer) and `Stagger_01`,
  `Stagger_02` (Base states) are base-pack clips in `Animations/`, listed in the base browser's Reactions section; the base production
  copy ships them. Only the GAMEPLAY use (`SkeletonHealth.hitClips` playing one per non-lethal hit) is extended.
- **Eyes: base since 2026-10-01** ("yes, move the eyes to base"). `SkeletonEyes` moved to `Demo/Scripts/` (namespace `UndeadLegion.Demo`,
  `git mv` with its `.meta`, so the GUID and every reference held), `SetVisible()` added; `MeasureEyes` moved from `ExtendedBuilder` to
  `CharacterPrefabBuilder`, which puts the eyes on every `PF_<Char>` (Knight / Archer z 0.071, the other four 0.086, as before); the `PFX_`
  variants inherit them (`ExtendedBuilder` no longer adds its own; `ArmySpawner` sets the team colour). The base browser's footer has an
  **Eyes** toggle (`SkeletonShowcase.eyesToggle`, applied on every spawn; the info label ends 850 px from the right to fit it), so the
  extended browser has it too. Verified in play mode in the base demo: 2 eyes on the spawned character, parented to the head, toggle off
  → 0, on → 2, no console messages. Base manual (scripts table, footer), extended manual, both listings updated; both productions rebuilt.
  **Red glowing eyes (2026-10-01, "make eyes color + glow red; re-record all showreel stages").** `SkeletonEyes.color` default
  (5, 0.2, 0.1) HDR (the base prefabs rebuilt with it; the arena's `ArmySpawner` still sets its team colours, teal / red), and every
  browser scene built by `DemoSceneBuilder` gets a global Volume with the shared `Demo/Scenes/Demo_Volume.asset` (Bloom only: threshold
  1, intensity 2.5, scatter 0.75; created once, reused) and post-processing on its camera — the lit scene stays under the threshold, only
  the eyes bloom. ⚠ **The showreel's eyes did not glow at first: the recorder rendered into an ARGB32 (8-bit) texture, and URP renders an
  LDR target in LDR, so the eyes were clamped to 1 before Bloom** (measured with an HDR red sphere on black: halo 0.012 at 30 px on
  ARGB32 against 0.21 on `DefaultHDR`); the recorder's render target is `DefaultHDR` now (the 2× box-filter blit and the PNG read stay
  8-bit). The live demo renders to the screen through URP's HDR buffer and was never affected. All three stages re-recorded headless
  (left side), the YouTube cut rebuilt. Rule: **anything rendered by hand for capture must target an HDR texture, or HDR effects vanish.**
  Same session: the user re-tuned `W_H1RoundShield`'s Grip; `Animations/unity_grips.json` re-dumped (it also picked up the grip changes
  of the past days: heater shield, longsword, battle axe, staff, and the removed `_Top` staff).

**Second round (2026-09-30, user: "briefly visible for one frame before it disappears and spawns; attacks with a step forward
(wand_cast, the two-handed attacks) play their step but the skeletons stay in one place; update the regular demo scene with cloth
on/off, rigidbody death, hit reactions, and the hit_01 / stagger_01 animations").** (1) The flash: the dissolve material's
`_DissolveHeight` defaults to 100 (all visible) and `SkeletonDissolve.Run` waited one frame for the bounds before setting it, so the
renderer showed whole on the frame the rise enabled it; the cut is now set (−1000 for a rise, +1000 for a death) in the same frame as the
swap. The eyes were created in `Start`, after the spawner had collected the renderers to hide, so they floated during the rise delay:
`SkeletonEyes` builds them in `Awake` and the spawner calls `SetColor`. Probed: 32 skeletons over two raises, every body hidden on its
first visible frame, 0 flashes. (2) The step: the agent drives the transform and the Animator's root motion was off, so a clip's step
played in place; `SkeletonNavController.OnAnimatorMove` moves the agent by the clip's `deltaPosition` (`NavMeshAgent.Move`, stays on the
mesh) and turns by `deltaRotation` while a one-shot is busy, and ignores root motion while the agent walks. Measured: Attack_2H_01/02
carry the skeleton 27 / 38 cm at the swing, the wand casts 8–15 cm. (3) The regular browser: the base `Demo` scene ships in the base
edition, which has no `Extended/` folder, so the extended features live in a SECOND browser scene,
`Extended/Scenes/UndeadLegion_Extended_Showcase.unity` (menu *Extended / 4*, built by `DemoSceneBuilder.Build(path, prefabPath,
title, save)` with the `PFX_` prefabs, a small baked NavMesh so the agents spawn quietly, and `ExtendedShowcase`): a PHYSICS panel (cloth
toggle, hit, ragdoll death, revive, rise, dust) beside the animation list, click the skeleton to hit it where clicked, Shift + click for a
ragdoll death; on spawn it removes the character's AI, nav controller and agent (DestroyImmediate in dependency order: a deferred destroy
of the agent fails while the controller requires it). Hooks added to `SkeletonShowcase`: `CharacterSpawned`, `ClipPlaying` (any clip
stands a ragdoll back up), `CurrentInstance`, `PlayByName`, and `Update` pauses while the Animator is disabled (a ragdoll must not be
revived by the one-shot fallback). `Hit_01` / `Stagger_01` are base-pack clips (46 clips then, 48 with Hit_02 / Stagger_02) in the Reactions section. Verified in play
mode: both clips play and return to the idle, cloth toggles, the ragdoll stays down until revived, all six characters switch, no console
messages; both production editions rebuilt (0 markers, clean compile). Not done: the arena AI does not play the new reaction clips (its
hits are the physical springs).
**"With the Necromancer, after Cast_Wand_01 it keeps switching Idle_Staff -> Cast_Wand -> repeat endlessly" (2026-09-30, the extended
browser).** The extended controller carries the weapon idles on UpperBody too (the pose held while the agent walks), and the browser's
`LayerFor` treats any LOOPING clip with a masked-layer state as a HELD action (the block rule): the return-to-idle after the cast toggled
Idle_Staff on UpperBody instead of playing it on Base, Base stayed on the finished cast, and the same fallback fired again next frame.
`LayerFor` now never routes an `Idle*` clip to a masked layer. Probed in both browsers on the Necromancer: Cast_Wand_01/02,
Cast_Staff_01, Attack_2H_01, Shoot_01, Attack_R_Slice, Taunt_01 each settle on ONE idle (3 Base states in 9 s). Rule: **a state added
to a masked layer for gameplay is not a browser action; the browser's layer routing must know which clips are loops of the body.**
**"Wand skeletons in the arena only slightly rotate instead of stepping forward, then snap back to their target" (2026-09-30).**
Measured on the clip (Knight, root motion on): Cast_Wand_01 steps the right foot 35 cm forward while the ROOT moves 18 cm forward and
turns −44° (Unity's root rotation follows the body, which goes side-on to cast) and comes back to 0° by the end. The AI's attack
coroutine turned the skeleton toward its target every frame of the wind-up (180°/s), cancelling most of the clip's turn (the "slight
rotate") and bending the step, and the between-attack re-aim at 540°/s then snapped away what it had added. Now nothing steers during an
attack (it starts only within 12° of the target; bolts home anyway) and the re-aim runs at 200°/s. Probed in an all-wand battle: steps
0.2–0.45 m forward (Cast_Wand_01) / 0.07–0.14 m (Cast_Wand_02), the body turns −45° and back to within a few degrees, re-aims after the
clip 0–19° over ~0.1 s. Rule: **a clip that carries root motion owns the transform while it plays; aim before it, never during.**
**"The Knight has no cloth armour, remove cloth from his pieces" (2026-09-30).** The cloth rules match by module NAME, so the Knight's
plate `Skirt` was simulated like the fabric ones. `SkeletonCloth.rigidSets` (default `SkeletonKnight`) lists armour SETS whose pieces never
get cloth, by the piece's source (`ArmorPiece.character`), so a borrowed Knight skirt stays rigid on any skeleton. Probed in the extended
browser: Knight 0 cloths; Archer / Warrior skirt, Assassin skirt + pants, Mage / Necromancer robe unchanged.
**"Eyes are too deep on every skeleton, only slightly visible on the Knight and Archer" (2026-09-30).** The one shared offset
(0.036, 0.029, 0.062) came from a centroid that mixed the socket with the skull's side. Fine depth maps (5 mm grid, z from the Head bone)
show two socket types: Knight / Archer with the floor at 64 mm, the other four with a flat floor at 77 mm, both centred at x 30 / y 23 mm;
the old eyes sat ON the first floor and BEHIND the second. The extended prefab builder now measures each character's socket floor
(`MeasureEyes`: the deepest body-mesh hit in a 5 mm disc round the centre, on the bind pose) and writes the offset into that
`PFX_` prefab with the sphere's back on the floor: Knight / Archer (0.030, 0.023, 0.071), the others (0.030, 0.023, 0.086); size 0.018.
Rendered from the front and from 40° above on all six: the eyes fill the sockets, under the brow from above.
**Hit_01 made ADDITIVE (2026-09-30, "hit_01 has too much movement; an animation blended into whatever the skeleton is doing
instead of overriding it, working with any idle").** Blender: `anim_nla_bake --action Hit_01 --result Hit_01 --legs-from Hit_01_base:1
--root-hold --end-blend Hit_01_base:1:20` (legs and root still, the last 20 frames back to frame 1, so the clip starts and ends on its own
reference pose), then the new **`--amplitude K`** (every control slerped toward the clip's first frame by K, after all other passes)
**`--amplitude-head K`** (the same for `neck` / `head` alone): 0.5 overall, the head at a quarter (at 0.5 the recoil read as a broken
neck). Manifest `layer: additive`, `additive: true` (`anim_batch` → `verify_clip --additive 1`: frame 0 is the additive reference),
`hand_edited`, no ground fit. Controller: layer 10 **`Hit`** (Additive, weight 1, `AM_UpperBody`, Empty + the additive clips, back to
Empty at exit time), additive clips are NOT Base states. `SkeletonShowcase` plays a clip that has a state on `Hit` there, over the running
clip (the Base clip and the button highlight stay; an overlay does not stand a ragdoll up); `SkeletonHealth.hitClip` plays it on every
non-lethal hit in the extended edition, with the physical flinch. Measured on two Knights stepped in lockstep (Idle_03 / Walk_Fwd_01 /
Idle_Bow alone vs + Hit_01): the base clip stays on Base, hips and feet 0.0° / 0.0 mm, added chest 8°, head 20°, arms 21–31°, 0.00° 2.3 s
after the hit. The full-body retarget is `Hit_01_base`.
Then (same day) "first 15 frames like 5, 15–45 50 % faster, 46–60 shortened by 10 frames": three `--speed-segment` passes, run from
the END so the user's frame numbers stay valid (46:60:3.5 → 5 frames, 15:45:1.5 → 21, 1:15:3.5 → 5): 60 → 30 frames (0.97 s), the ends
unchanged, the same added motion (chest 8°, head 20°, arms 22–31°) and 0.00° once it has played.
**Stagger_01 reworked (2026-09-30, "one step back during the stagger; too much body-parts movement").** Six new Kimodo candidates:
WITH the stiff-undead profile (`stagger_d1..d3`) every one folded forward deeply after the hit (the profile's hunch is what made the old
one double over too); WITHOUT it (`no_profile`, `stagger_e1..e3`) `e1` (seed 81) steps back once with the right foot and stands upright
again, chest 15 / head 34 / arms 42–72° against the old clip's 57 / 78 / 68–106 (scored with a `staggereval`-style script: lift-offs per
foot, each foot's net travel, the chest / head / arm rotation away from frame 1 relative to the hips). Retargeted with `drift root`, it
also DRAGGED the left foot 17 cm back with 1 cm of lift, so it was baked to one step: `anim_nla_bake --action Stagger_01_base --result
Stagger_01 --ik-legs --stride 0.55 --pin-foot L:1:1:75 --leg-reach 0.95`, then both knee pole targets held at their frame-1 values
(`--stride 0.65 --leg-reach 0.985` locked the held knee at 177° and flipped it; the per-frame re-aim from the dragged leg's FK knee turned
the left shin 69° at frame 46 and the right 28° at frame 4). Result: the left foot on its spot to 0.0 mm, the right steps ~23 cm back,
every leg bone ≤ 5.6° per frame, knees ≤ 20 mm per frame, root motion 15 cm back + 9 cm sideways (the step goes back-right), boots within
9 mm of the floor after the fit; `hand_edited`, `Stagger_01_base` is the retarget. Rule: **a leg held for a whole clip keeps ONE knee
direction; re-aiming its pole from a source leg that moved flips it.**
**Then (same evening) "change stagger to a mix of hit_01 plus one step (1 full animation cycle) back from walk_back_01, 40 % faster".**
Session script `stagger_compose.py` (kept as this description): every control of `Walk_Back_01`'s full cycle (60 frames incl. the closing
frame) resampled 1.4× faster at fractional frames → 43 frames (1.40 s), and `Hit_01`'s motion ADDED on top over frames 1..30 (per control,
in its local space: rotation `q_walk @ (q_hit1⁻¹ @ q_hit)`, location `loc_walk + (loc_hit − loc_hit1)`; both have IK legs and FK arms);
the one-step build kept as `Stagger_01_onestep`. Scan: no flips, the largest steps 16–17° on the right thigh / upper arms at frames 4–6
(the hit's fast recoil over the walk's first step; thigh and knee agree). Unity: root motion 0.662 m straight back, yaw 0; boots ≤ 6 mm
under after the fit, the Necromancer's robe 77 mm under (the hips-weighted hem). The clip starts and ends on walk poses; the Animator's
crossfade carries the joins to and from the idle.
Then "feet should freeze after frame 40": both feet held at their frame-40 spots over 40–43 (`--pin-foot L:40:40:43,R:40:40:43
--pin-ease 0:0 --keep-poles`; both were on the floor there, after it the left slid 3 cm and the right began the next lift), knees 125–134°,
the composed clip kept as `Stagger_01_composed`.
**Hit_02 + Stagger_02 (2026-09-30, "add hit 02 with stagger 02").** `Hit_02` = the `hit_c1` candidate (a gut blow: the chest folds
forward), retargeted like Hit_01 and given its exact recipe (legs from frame 1, root held, end blend 20, amplitude 0.5 then the head at a
quarter, the three speed segments → 30 frames); additive, on the `Hit` layer (the builder now has two overlay states). Added motion over
Idle_03: chest 14°, head 16°, arms 23–28°, legs 0; back to the base pose after it. `Stagger_02` = `stagger_compose.py --hit Hit_02 --out
Stagger_02` (the script takes `--hit / --walk / --out` now) + the frame-40 feet freeze: 43 frames, 67 cm back, no leg bone above 13° per
frame. `SkeletonHealth.hitClips` (was `hitClip`) picks one at random per non-lethal hit (12 hits: 6 / 6). Both in the browsers' Reactions
section; the pack has 48 clips.
**Arena locomotion on root motion (2026-09-30, "not sure root motion is used in the arena; when they run they sway instead of stepping,
the rotation plays separate from the transform").** It was not: the agent moved the transform at a set speed (`updatePosition` /
`updateRotation` on) and `OnAnimatorMove` applied root motion only during one-shots, so the loco clips' root motion — the travel AND the
body's turn with each step — was thrown away. Measured in a battle (world yaw per frame): the old transform's yaw stayed at 351.7° while
the hips swung 306–4° under it (the "sway"); now the hips stay within ~8° of the transform. `SkeletonNavController`: `updatePosition` and
`updateRotation` OFF; `Update` steers the transform toward `desiredVelocity` (`turnSpeed`) and feeds that velocity, in the character's
frame, to `MoveX` / `MoveZ`; `OnAnimatorMove` always applies the root motion (position through `agent.nextPosition`, so the body stays on
the NavMesh and the agent follows it; rotation `deltaRotation`); moving = path pending or remaining distance above the stopping distance.
Foot skate (the slowest horizontal speed per 20-frame window of a moving foot): battle 0.175 → 0.145 m/s, which is the clips' own floor
(alone with root motion: Walk_Fwd_01 0.008, Walk_Fwd_02 0.10, Run_Fwd_01 0.16, Run_Fwd_02 0.26 m/s — the Kimodo runs skid at push-off).
Battle unchanged otherwise (8v8 to 5–7 survivors in ~25 s, no errors). ⚠ Edit-mode `Animator.Update` does not apply root motion even with
`applyRootMotion` on: add `deltaPosition` / `deltaRotation` to the transform by hand when measuring a clip there.
**"Run_Fwd_01 drifts slightly to the left while running" (2026-09-30).** In Blender the loop closes exactly (hips, chest and both feet at
the same x on the first and last frame, the root travelling straight along its axis), and in Unity the humanoid `RootT` / `RootQ` curves
also start and end equal; but Unity measures the loop's travel against the body's MEAN facing, and this run's body faces 0.7° off its path,
so the straight travel read as `averageSpeed.x` −0.013 m/s (= 1.072 × sin 0.7°) — a slow drift to the character's left. The fix is the
clip's **Root Transform Rotation Offset**: manifest **`root_yaw_offset`** (degrees) → `anim_batch` → `verify_clip --rot-offset` →
`ModelImporterClipAnimation.rotationOffset`. −0.7 → `averageSpeed.x` +0.0006 m/s (+0.7 doubled the drift: the sign is found by reimporting).
Not changed (not asked): `Walk_Fwd_01` averages −0.069 m/s sideways (the body ~8° off its path), `Walk_Fwd_02` +0.076, `Strafe_Left_01` /
`Walk_Back_01` small; the same key fixes each. ⚠ In edit mode `Animator.Update` with `applyRootMotion` ON applies the root motion itself:
measure either by reading the transform after `Update` or by adding the deltas with it OFF (on a prefab without an `OnAnimatorMove` the
deltas are then zero) — never both.
**Then "still drifts while running": the offset was the wrong fix.** Measured in PLAY MODE in the browser (root motion on, leash off):
the run's transform turned ~3° within its first second (the clip's root ROTATION applied as root motion) and travelled 5.8 cm/s sideways,
0.35 m in 6 s; the walk's heading swung −4..+12°. The average the offset corrected was not the problem. **Every `loco` clip now imports
with its root rotation baked into the pose** (`verify_clip --bake-rot 1`, passed by `anim_batch` for mode `loco`; `lockRootRotation` on,
XZ still root motion), the rotation offset key removed from Run_Fwd_01 (the `root_yaw_offset` key stays available). Play mode: the run
2 cm sideways over 7 m, heading 0.0°; the walk ±4 cm about its line, no build-up. All ten loops reimported: travel per loop unchanged
(the speed table holds), yaw 0, Unity's sideways average ≤ 1 % of the forward speed. The body's turn per step stays in the pose, so the
arena's root-motion locomotion keeps it while the heading follows the steering alone. Rule: **a straight locomotion loop bakes its root
rotation; only turn clips should drive the heading.**
**"In the demo they start walking to their target too early" (2026-09-30).** Measured (battle started 0.3 s after a raise): 15 of 16
skeletons walked while still hidden or dissolving in, and 5 s later 0 of 16 had their AI on — `ArmySpawner.Rise` disabled the AI for the
rise and then restored the state it had at SPAWN (off, the demo raises with `enableAI` off), overriding the battle's switch-on. Now the
rise only sets `SkeletonAI.Suspended` (the AI waits: no targeting, no moving, no attacks, a running path stopped) and clears it when the
rise ends; whether the AI is enabled is left to its owner. Re-measured: 0 walked while rising, 16 of 16 AI on, 8 moving at 5 s.
Then the user clarified: "while reaching the target they start walking too early, they should run for longer (closer to the target)".
The AI ran only while more than 4 m away (a fixed number), so a melee skeleton walked its last ~2.3 m. Now it runs until **`walkWithin`**
(0.8 m) beyond its attack's reach, re-decided every think (0.25 s). Measured in a battle (distance to the target at the run → walk switch):
melee median 3.93 → 2.42 m, casters just outside their 9–12 m reach; they stop at ~1.5 m as before.
**"Make melee skeletons attack range 1.1 m instead of 1.5 m" (2026-10-01).** The stop distance came from the moves' own `range`
(1.4–2.2 m, the min of the style) through `dist > range·0.9` / goal at `range·0.7`. Now **`SkeletonAI.meleeRange`** (1.1 m, centre to
centre) is the engage distance of every style without a ranged move; the chase runs while `dist > range` toward a goal at 0.85 of it.
The moves' `range` still gates whether a swing connects (`range + 0.4`), so blows land. Measured in a battle: melee attacks start at
a median 1.10 m (0.76–1.11), 16 → 7 alive after 25 s, no errors.
**Armour classes and attack modules (2026-10-04, extended only).** User: "armours should be classified; melee skeletons no robes /
hoods, only the assassin can wear the mage hood; melee may miss more pieces, like the default archer; mage / necromancer always at least
a robe and a hood" and "the assassin uses regular, not heavy attacks, left-hand attacks with both weapons; no heavy attacks for the sword;
mace / axe mix heavy and regular; make it modules, attached by the equipped weapon". **`ArmourRules`** (`Extended/Scripts/`): a module's
kind (`Robe`; `Hood` = the Mage's and Necromancer's `Helm`; else `Armour`), `CanWear(wearer, source, module)` (casters: no chest / skirt /
pants, the head always a caster hood; melee classes — Knight, Warrior, Archer, Assassin — no robe, no hood, except the Assassin in the
Mage's hood), `Required` (casters: robe + hood; melee: chest). `ArmySpawner.DressRandom` picks each slot among the sources the rules
allow, `meleeBareChance` 0.3 (new) against `bareChance` 0.1 for casters. **`AttackModule`** (`Extended/Scripts/`, `[Serializable]`):
a name, the loadout names it attaches to (empty = unarmed), `heavy`, `AttackMove[]` (clip, hitAt, range, damage, impulse, ranged / area /
arrow); `SkeletonAI.attackModules` (defaults: Right hand on every one-handed loadout, Right hand heavy on axe + shield and mace, Left hand
on two daggers, Two-handed on both 2H, Two-handed heavy on the battle axe only — the longsword counts as a sword —, Bow, Wand, Staff,
Unarmed) and **`allowHeavy`** (off on `PFX_SkeletonAssassin` by `ExtendedBuilder` and by the spawner for the Assassin); the move is a
random pick that avoids the last clip (was a fixed rotation), the `Style` enum is gone (the bow is `AttackMove.arrow`). The heavy stab
(not in the old table): damage 26, reach 1.9, hitAt 0.27. Probed in play mode: 120 spawns, 0 rule violations, every caster robed and
hooded (Mage / Necromancer pieces mixed between the two), each class / loadout with the intended moves; an 8v8 battle with no console
messages, regular and heavy one-handed moves, 2H, casts and shots played. Extended manual §11 / §12 and the extended listing updated.

**Extended browser layout (2026-09-30, "move the new UI panel under the animations panel, make that one shorter; the physics hit is
weak, 2x"):** the PHYSICS panel is anchored bottom-right at the ANIMATIONS panel's right edge and width (−20 / 280 px, 78 px above the
bottom), and `ExtendedShowcase.FitUnderAnimations` shortens the browser's `AnimationPanel` at runtime to end 10 px above it (measured
from world corners after layout, so any aspect works; the list scrolls). `hitImpulse` 45 → 90 (the physical hit and the push on a
ragdoll); the browser scene rebuilt so its serialized value follows.

### Validator

Run the Asset Store validator headlessly against `Assets/UndeadLegion` (category
`3D/Characters/Humanoids`). Its classes are `internal`; drive
`AssetStoreTools.Validator.CurrentProjectValidator` by reflection; `Title` and `Result`
on `AutomatedTest` are fields. Last run (2026-09-15, old export): 31 pass, 0 fail,
1 warning (`Check Model Orientation`), which the `SK_*` exports fix
(`bake_space_transform=True`: mesh nodes at identity). **Not yet re-run on the new
assets.** `Check Prefab Transforms` requires a prefab root at exactly 0 / 0 / 1 at 12
decimal places; the prefab builder guarantees it.

### Driving play mode from the MCP bridge

`manage_editor play` enters play mode but the game then sits at **frame 1** until
something advances it: call `EditorApplication.Step()` a few times, clear
`EditorApplication.isPaused` and `QueuePlayerLoopUpdate()` (`demo_smoke.py` does this;
measured 280 frames in the next 3 s). `Destroy` is deferred, so a frozen game keeps
destroyed UI rows in `childCount`. `ScreenCapture.CaptureScreenshot` needs a following
frame to flush, and the first seconds show **solid cyan UI panels** (URP's async shader
compilation placeholder), so wait before shooting. Stop play mode when done: a stalled
MCP call leaves the editor playing. In edit mode `manage_camera screenshot` returns a
stale Game view; render explicitly (`RenderTexture` + `cam.Render()` + `ReadPixels`).

---

## 8. Rig pipeline and the animation plan

### Why the export rebuilds the skeleton (from the creatures pack, proven there)

- Blender's "Only Deform Bones" is wrong for Rigify: `DEF-thigh` hangs off `ORG-spine`,
  so the tickbox drops parents. `export_fbx.py` resolves anatomy from the **metarig**
  and builds a clean 66-bone skeleton with each bone's **whole rest matrix** copied.
- `Root` points **up** (+Z in Blender). Rigify's `root` lies flat; copying it gives a
  root node on its side and tipped root motion.
- Meshes are **siblings** of the armature. A model FBX and a clip FBX must produce the
  same node paths or Unity's "Copy From Other Avatar" silently yields zero clips.
- No B-bones: FBX cannot carry them, so the library rig has `bbone_segments = 1`
  everywhere and Blender shows the same deformation the engine will.

### Shared clips

One clip set, exported rig-only as `Skeleton@<Clip>.fbx`, retargeted through the
Humanoid avatar onto all six. Per-class clips only where the motion differs (sword,
two-hander, bow, cast). Unreal: one Skeleton asset, every `SK_*` imported against it,
no IK Retargeter needed; the `Armature` node with one child (`Root`) is stripped by
UE's importer, and the Unreal target must be written in **centimetres** (see the
creatures pack `tools/ue/README.md`).

### Layered ("modular") animation — authoring rules

Walking while attacking, running while shooting, and twitch overlays are done in the
engine with masks over the full skeleton (Unity: Animator layers + `AvatarMask` cut at
`Spine1`; Unreal: `Layered blend per bone` + `UpperBody` montage slot + `Apply
Additive` + Aim Offset).

**Implemented in Unity 2026-09-20, per-arm layers added 2026-09-22.** `AC_Skeleton.controller`
has eight layers: `Base` (every clip), `UpperBody` (Override, weight 1, mask
`AM_UpperBody.mask`: humanoid Body/Head/Arms/Fingers on, Root/legs/IK off, plus the 55
extra transforms under `Spine1`; states `Empty` + every clip tagged `layer: upper` in
`Animations/clips.json`), **`LeftArm` / `RightArm`** (Override, weight 1, masks
`AM_LeftArm` / `AM_RightArm`: that arm + its fingers only, 24 transform paths under that
`Shoulder`; states `Empty` + the clips tagged `left` / `right`), `Twitch` (Additive,
trigger-fired once), `TwitchLoop_01..03` (Additive, weight 0, one looping state each: the
demo's twitch toggles set the weight; the twitch clips import with Loop Time on, which the
trigger layer's exit-time transition still ends after one pass). The manifest tag is the
single source of truth: `upper` (Shoot_01, Cast_Wand_01/02, Cast_Staff_02, Rally), `right`
(Attack_R_Stab/Slice), `left` (Attack_L_Stab/Slice, Block_L_Idle) versus "full stop" (`full`:
Attack_2H_01/02, Cast_Staff_01, Summon, AOE_Cast, Taunt, Cutthroat). **A LOOPING clip on a
masked layer is a HELD action** (user, 2026-09-22: "models carry shields only in the left
arm, left arm stuck in block action until released"): the builder gives it no exit
transition, the showcase toggles it with its button (`ToggleHeld`, crossfade in, stays over
whatever Base plays, walks included, until the same button crossfades to `Empty`). Measured
by `build_twitch_controller.py`: Walk_Fwd on Base + Attack_R_Slice on RightArm gives the
walk's legs and SPINE (LeftUpLeg and Spine1 within 0.00° of the walk alone; the slice alone
swings Spine1 5.6°) and the attack's right arm (within 0.00°, 87° swing); Walk_Fwd +
Block_L_Idle held on LeftArm + Attack_R_Slice on RightArm keeps both (0.00°). The demo
routes automatically (`SkeletonShowcase.LayerFor`: the first masked layer with a state for
the clip): a masked clip clicked while a locomotion loop plays goes to its layer ("RightArm
layer over Walk_Fwd"); otherwise it plays full-body on `Base` (the arm clips carry the torso and,
since the recorded set, the legs and the step, so a stab from an idle reads whole); a full-stop
clip takes `Base` and the loop resumes after it. A HELD block does not route attacks to the arm
layer (it did until 2026-09-23, and the user saw "stab/slice attacks stop moving the legs" after
toggling the block): the `LeftArm` layer overrides the left arm over whatever Base plays, so a
standing attack goes full-body on Base with the shield still up. `layer_smoke.py` proves walk +
right slice, the 2H full stop and resume, the block held through a right stab and a walk,
and its release, in play mode. Humanoid masks cannot cut inside the spine (Body is one part),
so the upper layer owns the whole spine above the hips and the arm layers own none of it;
the walk keeps hips + legs, which is the cut the clips were authored for. ⚠ The builder's
C# runs through CodeDom: a lambda may not declare a local that any enclosing scope also uses
(`mp`, `nm`, `cl`, `st`, `i`…), and the bridge's `refresh_unity … compile: request` can
time out before the code runs — run the CODE through `execute_code` directly then.

**The per-arm attack set (2026-09-22, user: "instead of 1 handed actions, we do right or
left hand").** Attack_1H_01/02, Shield_Bash and Block are retired (assets, manifest and
build state deleted). `Attack_R_Stab` / `Attack_R_Slice` come from the user's recordings
(`P:ttacks sword_stab.glb`, `P:ttacks sword_swing.glb` → `External Anims/Kimodo/
attack_{stab,swing}_mocap.glb`, 52-joint `*_JNT` skeletons at 24 fps, so `time_scale 1.25`;
the first builds were Kimodo prompts, `atk_r_stab/slice.glb`, now unused). The app mirrored
both (the file attacks with the LEFT arm, the user attacked with the right), so the R clips
are `mirror`ed and the L clips are the raw files. The clips carry the WHOLE upper body from
the capture (chest 21–43°, head 17–24°, the other arm moves), legs on IK at rest (mode upper),
blend in 12 / out 15 frames from and to `Idle:1`. The user's rule, "each should only control
1 arm … only if a moving animation controls the lower half", is the LAYER's job, not the
clip's: the demo plays an arm clip on its arm-only layer while a locomotion loop (or a held
block) runs, and full-body on Base when the character stands. (`--only-arm R|L` exists in the
retarget from the first build — the source drives one arm's chain and everything else holds the
blend-from pose — but is not used: a one-arm clip stood frozen in the idle's pose when played
from standing.) Then "speed it up 2 times": `time_scale 0.625` (the 24 fps file at 2×), blends
8/10; stab 46 frames (1.5 s), swing 64 (2.1 s). And, from a top view, "both the arm and the
weapon (hand rotation) extend not forward for a stab attack": **`stab_aim R|L`**
(`--stab-aim`) weights by the hand's horizontal distance from the shoulder (0 at 0.15 rig m,
1 at 0.27, smoothed), swings the arm about the vertical through its shoulder by that share of
its yaw error and turns the hand about the vertical by that share of the hilt axis's yaw error,
so at full extension both point straight ahead (Unity: arm yaw ±1°, hilt yaw ±1°; before, 25–30°
off to the side). Then, from a side view, "tilt the hand so the sword points forward, and
don't make the arm extend that much (10 cm less)": **`stab_pitch 0`** and **`stab_shorten
0.056`** (rig m). The hand is no longer aimed in world space: it is built from the FOREARM's
zero-twist hand (rest relation), turned by the least rotation that lays the hilt axis forward
at `stab_pitch`, rolled `--stab-roll` (0) about the blade, and blended with the capture's hand
by the extension weight (a world-aimed hand clamped by `limit_wrist` flipped the forearm
96–165° on two frames, as the bow anchor once did). The shortening bends the elbow: the
forearm turns about the hinge normal `(elbow − shoulder) × (hand − elbow)` by the law-of-
cosines difference (a POSITIVE turn closes the elbow; the first build opened it past straight
and the elbow swapped sides every other frame). ⚠ The capture's arm is dead straight at the
peak (interior angle 173–180°), where that normal is noise: it is taken from the capture only
while the elbow is bent > ~8° and kept from the previous frame otherwise (a fallback
"out-and-down" axis blended in by straightness pointed the opposite way and swung the elbow
across). Then "it twists the hand in a bad angle to make a sword go straight, so it's ok to go
a bit diagonal; make the first part (attack part) 2 times faster": **`stab_yaw 20`**
(`--stab-yaw`, degrees inward of forward, mirrored for the left hand) is where the blade points
at the peak — a neutral fist's hilt axis sits ~20° inside the forearm line, so the wrist stays
natural — and `time_warp 27:13` + `blend_in 5` play the wind-up to the peak at 2× on top of the
clip's 2× (peak at frame 12 of 37, 1.2 s). Result at the peak in Unity: reach 0.48 m (0.58
before), arm yaw ±1°, blade 23° inward, pitch 1°; forearm/hand steps ≤ 22°; lowest vertex
+4..+8 mm. **The swing** (user, from a front view at the wind-up: "weapon should point in
arrow direction during 1 handed swing attack; make it 2.7 times faster"): **`blade_along_arm
R|L`** (`--blade-along-arm`, `--blade-roll`) rebuilds that hand every frame from the forearm's
zero-twist hand turned so the hilt axis continues the forearm line (elbow → wrist), blended in
and out with the idle crossfades; Unity: blade-vs-forearm 0° from frame 4 to 19 of 24, the
idle's own wrist at the ends. `time_scale 0.3676` (1.7× the 2× build = 3.4× the recording;
"2.7 times faster was wrong, should be 1.7"), blends 5/6: 38 frames (1.23 s); per-frame
forearm/hand steps up to ~26° at that speed (motion, not wraps); lowest vertex +3..+8 mm. **Redone 2026-09-22 evening** from the user's updated
recording delivered as a BVH (`P:ttacks sword_swing.bvh` → `External Anims/Kimodo/
attack_swing2_mocap.{bvh,glb}` through `tools/bvh_to_glb.py`: the app's BVH is Z-UP with a
T-pose rest; imported with axis_up Z — the default Y-up import lay the skeleton on its side,
hands at z −0.3..0.4 — and exported as a Y-up GLB, after which the retarget treats it like the
app's own GLBs). Same settings, no pose refs: 37 frames (1.2 s), blade along the forearm from
frame 5 to 32, steps ≤ 30°, lowest vertex +4..+9 mm. Then "make it faster starting from frame
11 to frame 26, like 35 %": **`speed_segment "11:26:1.35"`** (`--speed-segment A:B:F`, OUTPUT
frames after `time_scale`, 1-based: A..B resampled F× faster, the rest shifted earlier): the 15
frames became 11, the clip 33 frames (1.07 s); blade along the forearm frames 5–28, steps ≤ 35°,
lowest vertex +5..+10 mm.
**Redone a third time (later that evening)** from `P:\cXi2eAP19XwQ-mrPMxTWYfy7h.bvh` frames
80–133 → `External Anims/Kimodo/attack_swing3_mocap.{bvh,glb}`: a different capture tool — an
**Unreal-mannequin skeleton** (79 joints: `pelvis`, `spine_01..05`, `clavicle_l`, `upperarm_l`,
`lowerarm_l`, `hand_l`, metacarpals and fingers, twist bones, `thigh_l`, `calf_l`, `foot_l`,
`ball_l`, `neck_01/02`, `head`), in CENTIMETRES, 30 fps, Y-up (`bvh_to_glb.py --yup`; the first
Z-up conversion put the hands at z −0.3..0.4), and a rest pose that is NOT a T-pose: every bone
stacked straight up (pelvis on the floor, hands above the head). Manifest `rename ue5` (the new
table: spine_01/03/05 → Spine1/Spine2/Chest, `middle_03_*` as the hand's direction child) and
**`bind stacked`** (`--bind`): the shoulders are then aligned by bone direction like the arms
(`MAP` entries with a kid, `A[tgt]` = rig rest direction → source bind direction; with a T-pose
bind the clavicle needs none) and the hips height for the scale is read from the animation
(the rest's pelvis sits at −2.6 cm); nothing else in the delta logic cares, since spine, neck,
head and legs point up in a T-pose bind too. **`src_begin 80`** (`--src-begin`, RAW source
frames, applied with `src_end` before `time_scale`; `src_start` counts resampled frames and
put 80 past the 49 resampled ones: IndexError). The file swings with the left arm, so the R
clip is `mirror`ed; `speed_segment` dropped. At `time_scale 0.3676` the 54-frame swing is 20
frames (0.63 s) — the tempo the user set on the previous take, probably too fast for this one:
`time_scale` is the knob. Chest 54°, hips move; forearm/hand steps 50–61° per frame at that
speed; the Necromancer robe dips −17 mm in the bend (the others +6..+11 mm). Then (user):
"idle should blend into frame 93 (hand overhead), so it should be a first frame; this reference
is faster, so only speed it up by 30 % of original speed; reference itself is good, don't alter
to adjust sword direction, just try to follow it" → `src_begin 93`, `time_scale 0.7692`,
blends 6/8, `blade_along_arm` dropped (the wrist is the capture's): 31 frames (1.0 s); the
idle's hanging arm reaches the overhead pose in the 6-frame crossfade (forearm steps up to
54–64° there, the crossfade, not a wrap); Necromancer robe −23 mm / −9 mm (R / L) in the
bend, the others +3..+8 mm. Then "hand twists few times at the start of the animation, plus arm
detaches?" (a screenshot with the pauldron off the arm). Measured in Unity: the RightShoulder
bone was 108–120° from the idle's, and in the SOURCE the mannequin's `clavicle → upperarm`
vector swings from sideways to straight BACK (+Y) in the wind-up — a collarbone cannot do that,
this app's clavicles are junk. **`shoulders keep`** (`--shoulders keep`): the clavicles hold
the blend-from pose (the idle's), the upper arms still follow the capture; shoulder 33° max
now. The wrist: the mannequin's `lowerarm_twist` bones carried the pronation, so `hand` vs
`lowerarm` was 70–110° in the source and the rig's wrist got it all; **`wrist_fix R|L`**
(`--wrist-fix`) runs `limit_wrist` on that hand every frame (twist ≤ 60°, the excess into
forearm pronation). What remains is the 6-frame crossfade from the hanging idle arm to the
overhead pose, where the wrist twist reads −30..+22° frame to frame — the slerp path of the
hand differs from the forearm's. (`bind stacked`'s direction-only clavicle aim is still in the
code for a source whose clavicles are sane.) Then "don't get it, still look wrong. redo, start
frame 96, end 117, with 6 frames to transition to and 6 to transition from": `src_begin 96`,
`src_end 117`, blends 6/6 → 17 frames (0.53 s), of which 12 are the crossfades. That build
showed a 122° forearm / 148° hand step in the blend-in: the hands and forearms were crossfaded
SEPARATELY in world space, so the wrist twist swept through 180° and the limiter flipped it. **The
crossfades now blend each hand RELATIVE to its forearm** (the forearm-to-hand quaternion slerped,
the hand rebuilt on the blended forearm), in both the blend-from and the blend-to: wrist twist
0..−12° through the clip, forearm/hand steps ≤ 51° (the 150° raise in 6 frames). Muscle curves
of the raised arm sit outside Humanoid's range (`Right Arm Down-Up` −1.34: the overhead-behind
pose is reached "backwards"); Unity still plays the hand at 1.5 m, and the demo shows the
overhead wind-up and the cut. ⚠ A frame strip rendered from ONE instance with `Animator.Update
(0.0001f)` between frames showed the arm mesh at rest while the bones were up — use
`weapon_shots.py`'s sequence (Play, Update(0), Update(0.03), then equip) per frame or the
play-mode stepping (`EditorApplication.Step` while paused) for a truthful picture.
**Then the user asked the right question: "can't we have animator do the transition part?"**
Yes — the two swings no longer bake `blend_from` / `blend_to`: the clip starts on the recording's
frame 96 (arm overhead) and ends on its frame 117, and the ANIMATOR carries both transitions:
the showcase crossfades onto the arm layers with `CrossFadeInFixedTime` (it used `Play`, an
instant cut) at its `crossFade` (0.15 s), the arm layers' exit-to-`Empty` transitions are 0.25 s
(were 0.15), and on Base the showcase's usual crossfade applies. Rule kept: a masked-layer
clip may start and end mid-action; the transition durations live in the controller builder and
the showcase, not in the clip. (`shoulders keep` without a blend-from holds the REST shoulders.)
Forearm/hand steps ≤ 36° (was 51 with the 6-frame baked raise), lowest vertex +7..+11 mm.

**Fourth reference (2026-09-22, late): `P:\c7uJKSavZ5aC-mrPMxTWYfy7h.glb`, stab = frames 75–108,
slice = 152–190**, the same mannequin app but as a GLB: 162 nodes, NO skin, no mesh, an A-pose rest
in metres (pelvis 0.96, hands ±0.478 at 1.045), 386 frames at 30 fps, 56 nodes animated (rotation
+ translation), fingers included, even a `weapon_r` node. Blender imports a skinless GLB as
animated EMPTIES, and the retarget needs an armature: **`tools/glb_nodes_to_armature.py`**
builds one (a bone per node, rest = the node's rest world matrix, the empties' animation baked on
with Copy Location + Copy Rotation, visual keying) and saves it as **`attack_ref4_arm.blend`**,
which the retarget now appends (`--glb X.blend`, manifest `src_ext blend`). Four pitfalls, each
measured: (1) the rest must come from the JSON node TRS, converted as the importer converts,
`CONV · W · CONV⁻¹` (verified against the importer's frame-0 empties: K = CONV⁻¹); unlinking the
empties' actions and reading their transforms gives frame 0, not the rest (animated properties
keep their last evaluated values); (2) a fresh edit bone is zero-length and IGNORES `.matrix`:
every bone came out pointing +Z (set head/tail first); (3) Copy Transforms carries the root's 0.01
scale into the bones (location + rotation only); (4) the GLB round trip is unusable as the source:
the exporter writes an armature as a skin only with a skinned mesh, and the importer re-orients
the bones while keeping the pose, so rest and pose are no longer paired — the rig folded flat
(spine pitch 10° from an upright 83° source; deltas of 124–152° with `delta·up` sideways). With the
.blend: spine 69–74°, hips at the idle's height.
**THE CORRECTION (2026-09-23, user: "the animation looks very different from the reference;
maybe you have difficulties with bone mapping? let's move the reference to the model with no
modifications so we can be sure the mapping is correct").** He was right, and the measurement
tool built for it settles it: **`tools/retarget_compare.py`** poses the source and the built clip
frame by frame and compares (a) joint positions relative to the hips, scaled, yawed onto the
rig's shoulder line, in engine cm, and (b) BONE DIRECTIONS, proportion-free. With the plain
rotation transfer on the FIXED source (`src_ext blend`, no arm passes at all) the sword arm
matches the capture within 1–3° (upper arm and forearm, both sides), the spine 2°, the neck 10°
(the rig's proportions), elbow twists −23..−67°, and Unity shows no forearm/hand step above 10°
with every arm muscle inside ±0.7. So: **the bone mapping is right, the capture's rolls are
FINE, and every "junk roll" finding of the previous evening — the 138–156° forearm twist, the
inverted elbow, the 250 % arm twist, the one-frame flips — came from the BROKEN conversion**
(bones pointing +Z with 0.01 scale), not from the capture. The passes built against it are kept
in the code but unused on these clips: `arm_ik` (it reproduced the hand path but put the elbow
on its own pole: the weapon arm sat 75°/56° off the capture, which is what "very different from
the reference" was), `arm_roll_geometric`, `hand_from_forearm`, `align_roll`, `wrist_fix`,
`shoulders keep` (this capture's clavicles are 38–80° from rest in the source, but copying them
plainly reads fine). Position errors that remain (chest 16 cm, hands ~14 cm) are the rig's
proportions (a skeleton's torso and arms vs the performer's), not mapping. Rule kept: **when a
retarget "looks wrong", compare bone DIRECTIONS against the source first**; a roll or twist
symptom on a source whose stick figure moves right is a conversion or rest-pose bug until
proven otherwise. (What the previous paragraph describes below is that broken-conversion
history, kept for the record.)
The capture's bone ROLLS looked like junk on the broken source (forearm 138–156° on the upper arm, upper arm 145° on the
shoulder, the elbow inverted in the user's screenshot; Humanoid read the arm twist at 170–250 %
and flipped the forearm on one frame): **`arm_ik R|L`** (`--arm-ik`) solves the weapon arm with
the rig's own IK from the capture's hand position (relative to the hips, scaled, clamped to 97 %
of the arm), the elbow on a pole that swings with the arm (out, back, a little down), and the hand
built from the IK forearm's zero-twist hand: its palm axis turned onto the capture's wrist →
KNUCKLE direction (`middle_01`, rigid on the palm; the fingertip curls into the fist and pointed the
hand backwards), then rolled about it so the hilt axis lies along the forearm (a zero-twist roll
hung the blade straight down out of the thrust). Nothing of the capture's rolls reaches the rig:
arm muscles −0.8..1.5, forearm twist ≤ 0.2, no snaps (stab ≤ 9°, slice ≤ 30°). `shoulders keep`
(this app's clavicles swing 38–80°). The stab's earlier aim tweaks (`stab_aim`, pitch, yaw,
shorten) act on FK and are off; the blade continues the forearm by construction. Also tried and
kept in the code: `--arm-roll-geometric` (upper arm twist from the elbow plane, forearm twist-free
— sane in Blender, Unity still read 250 % arm twist), `--hand-from-forearm`, `--align-roll`
(direction + roll alignment of the binds via each body's forward), the wrist limiter's unwrap.

**Fifth reference (2026-09-23): `P:\c7uJKSavZ5aC-mUqvTCBRmSJH.glb`, stab = frames 26–62, slice =
111–149** (`attack_ref5_mocap.glb` → `attack_ref5_arm.blend`, same app and skeleton, 221 frames).
This take attacks with the RIGHT arm, so the R clips are the raw transfer and the L clips the
mirror (the compare tool's hand-travel numbers say which arm: right 1.07 / 1.36 m, left 0.34 /
0.54). Plain transfer: both arms within 1–4° of the capture, spine 2–5°, no Unity step above 13°,
arm muscles inside ±0.9, lowest vertex 0..+11 mm. Stab 28 frames (0.9 s), slice 30 (1.0 s). Then widened (user: "I need more frames for these animations, as the transitions from/to blend the start/final frames"): stab 18–80, slice 101–165 → 48 and 50 frames (1.6 / 1.6 s), so the Animator's crossfades eat the recording's own lead-in and settle instead of the action ("slice animation stops too early": the demo returns to the idle only after a one-shot has fully played and the arm layers exit at its end, so nothing cuts a clip — the recovery frames have to be IN the range).

**Steps in the attacks (2026-09-23, user: "these references also include steps, like a step
forward during the stab; is it possible for them to only apply if the bottom half is not busy
with other animation?").** Yes, and the layer masks are the gate: on the `LeftArm` / `RightArm`
layers everything below the shoulder is dropped, on `Base` the whole clip plays. So the four arm
clips now carry the capture's legs: `mode action` (FK legs) + `plant_feet 0.001` + **`drift root`**
(`--drift root`, action mode: the take's NET hips travel goes on `Root` as root motion instead of
being slid out linearly — the performer lunges 15 cm on the stab and steps 33 cm on the slice, and
sliding 33 cm out of planted feet would skate them; `anim_batch` then imports the clip with the
in-place flag OFF). Measured in Unity with root motion on: stab travel 17.5 cm, slice 35.5 cm, with
the take's own 25° of body turn (mirrored on the L clips); with Apply Root Motion off the engine
plays them in place. Legs within 4–15° of the capture (the plant adjusts them), arms unchanged
(1–5°), no step above 15°, lowest vertex +10..+16 mm.

**Stab fixes (2026-09-23): "tilt the hand so that sword is more forward pointing; make it 2 times
faster; at the end of the attack the model's forward direction changes, 5–10°".** `hand_tilt
"R:-45"` (`--hand-tilt SIDE:deg`, + = blade up: a constant turn of the hand about the world-
horizontal axis perpendicular to its hilt, every frame; the forearm itself thrusts 22° upward in
this take, −30 left the blade 16° above it, −45 lays it along the arm: hilt +23° at the peak,
forearm +22°), `time_scale 0.3846` (24 frames, 0.77 s), and **`unwind_yaw`** (`--unwind-yaw`:
the hips' net yaw over the used range, here ~25°, is removed linearly, each frame turned about
the vertical through its hips, so the clip ends facing where it started; Unity's root-motion
yaw went from 335° to 355°). Steps ≤ 17° forearm / 35° hand (the doubled speed), lowest vertex
+15..+18 mm. **Then, from a top view: "sword still points in wrong direction; slight right knee jerk
close to the end of the thrust".** The tilt had fixed the PITCH only: measured in Unity the hilt's
yaw at the peak was 75° LEFT of the hips while the forearm thrust 18° right (the capture's hand
roll), so `hand_tilt` is dropped and **`blade_along_arm R|L`** rebuilds the hand every frame so
the hilt continues the forearm line (hilt yaw = forearm yaw, pitch = forearm pitch on every
frame: 18° right / 22° up at the peak — "a bit diagonal", as the user accepted for the FK build).
The knee: the plant blends the leg between FK and IK, and Rigify's IK knee sat 5 cm INWARD of
the capture's, so the two weight switches (the foot found on the floor at frame 13, lifting off
at 19) swung the knee 5.5 / 4.4 cm in one frame — the knee ANGLE matched the source to 5°
throughout, which is why an angle check saw nothing. `plant_feet` now puts the leg's IK pole
(`thigh_ik_target`, `pole_vector` on) out through the FK knee on every planted frame; the IK
knee equals the FK knee to 1 mm and the blend only lifts the foot (steps ≤ 1.6 cm where they
were 5.5). Applies to every clip that plants (the slices were rebuilt with it; Impaled_Rise not yet).
**Then "both feet slightly detach from the ground during attack"** (a Knight screenshot, both
boots ~2 cm up). Measured per frame in Unity: 17–24 mm on every frame of the stab. Action mode
grounds every frame against ALL SIX characters' meshes in Blender (lowest vertex at 0), so the
standard 15 mm export lift is pure float on these clips, plus the Knight's boot sits 5 mm above
the Archer's. Manifest `lift 0.004` on the four arm attacks (`ground_clip` had been suggesting
`--lift 0` all along; note it samples every 6th frame, so check per frame when it matters):
stab boots 4–13 mm on all six models on every frame, slice 0–14 mm (Necromancer −1 mm on one
frame). Then "still slight lift is present" (the Knight's boots at 4–13 mm): the remaining gap is
the six characters' SOLE SPREAD (the Blender grounding puts the lowest of the six on the floor, the
Knight's boot sits 4–5 mm above the Archer's) plus Humanoid's per-frame few mm. No constant lift
can fix that, so the loop is now closed IN THE ENGINE: **`tools/unity/ground_fit.py <Clip>`**
measures every model's lowest vertex on every frame in Unity and writes a per-frame Root lift
(`Animations/ground_fit/<Clip>.json`, tracked) that puts the HIGHEST model's lowest point on the
floor (`--target 0`); `export_fbx.py --lift-curve` adds it to the Root Y keys on top of `--lift`;
manifest **`ground_fit true`** makes `anim_batch` run measure → re-export → re-measure after the
normal export (one pass converges: Root Y is baked into the pose, so the shift is 1:1). The four
arm attacks: Knight boots −4..+1 mm on every frame of the stab, the other five sink ≤ 8 mm at their
lowest frame (a sole under an opaque floor is invisible, a gap is not). Rule: **a shared clip can
only ever put ONE model's sole exactly on the floor; choose the highest and let the rest sink.**
The 15 mm default lift stays for the IK-legged idles measured on the Knight alone.
**Then, editing in Blender: "on some frames foot_ik.R controls the right leg (frame 13 of the right
stab), on frame 14 it detaches; also happened in some actions with hands".** The retarget keyed the
IK/FK switch per frame: the plant set the leg to IK only on the frames it touched (partial weights
while the foot lands or lifts, pure FK where the boot already sat on the floor), and every hand pass
(hand clearance, gate, arm keys, prop, arm IK) does the same to its arm. **`--ik-always`** (manifest
`ik_always`, default `auto`): a limb that any pass puts on IK now stays on IK for the whole clip;
on the frames no pass touched, `bake_ik_limbs()` runs last in `pose()` and puts the IK target and
pole on the DEF result (the FK pose, or the plant's blend), so the pose is unchanged and the IK
control is live on every frame. `auto` = legs whenever `plant_feet` is on. Measured on the rebuilt
right stab against the previous build: feet, hips, spine and arms 0.0 mm, knees within 6 mm (the
pole is now REFINED: `ik_pole()` corrects the residual swivel about the hip→ankle axis until the
knee lies in the FK knee's plane, 0.00° — Rigify's pole angle is a rest-pose fit and a pole placed
in the plane left a 3–7° swivel; the remaining knee offset on planted frames is the plant's own
lift of the ankle, 11 mm at frame 3), thigh roll within 1.6° (stripped at export anyway). Both
legs' `IK_FK` keys are 0.0 on all 24 frames. **Arms are opt-in** (`ik_always arms|both`): the
pole reproduces upper arm, elbow, wrist and hand exactly, but the IK forearm has no twist of its
own, so the capture's forearm pronation on FK frames (21° on this stab) is lost — decide per clip.
Two things learned on the way: Rigify's `thigh_ik` / `upper_arm_ik` control is NOT the chain's
start (aligning it to the FK bone moved the knee 15–38 mm, the elbow 45–70 mm), the pole is the
only handle on the swivel; and "IK knee vs FK knee" is the wrong check on a planted frame — the
plant lowers the ankle, so the knee legitimately differs; compare against the previous build.

**The user's first NLA edit (2026-09-23): "added a new action Attack_R_Stab_Fix with the feet fixed;
the regular Attack_R_Stab now looks different; can we use the fix to update the stab animations? and
get rid of the drift on the left foot".** Their setup: Attack_R_Stab pushed down as an NLA strip
(Replace), the fix as the ACTIVE action in Combine mode (20 fcurves: `foot_ik.L/R`, 1–2 keys each).
Two lessons: (1) selecting Attack_R_Stab as the active action over its own strip in Combine mode
applies it TWICE (that was "looks different"); (2) switching the active action away from the fix
left it with no user and the first save dropped it — an action must have a fake user (the shield)
to survive. **`tools/anim_nla_bake.py -- --result Attack_R_Stab --mirror-to Attack_L_Stab
--pin-foot L --save`** flattens the stack: the evaluated pose of all 123 controls (loc/rot/scale +
IK_FK / pole_vector / IK_Stretch) per frame into a fresh action, the old one kept as
`<name>_base` (fake user), every NLA track removed; proved flat = stack to 0.00 mm on every DEF
bone. `--pin-foot L[:frame]` then holds that foot's IK control (and toe) at one world transform for
the whole clip (frame 1's: where the idle crossfade lands it; the capture's rear foot drifted 6 cm
sideways and 7 cm fore-aft while planted): knee 136–153°, DEF foot on the pin to 0.0 mm on every
frame. `--mirror-to` writes the X-flip (Paste-X-Flipped rule; landmarks within 2.1 mm of the exact
mirror). Manifest **`hand_edited true`** on both stabs: the batch no longer regenerates them (a
rebuild from the recording would erase the fix); **`anim_batch.py <names> --export-only`** exports,
verifies and ground-fits what is in the anim file. Root motion unchanged (18 cm, yaw 355° / 5°);
after the fit the Archer sinks 10–13 mm at its lowest frame (the fix widened the sole spread).
⚠ A headless `--save` overwrites the file under the user's open session: reload before editing on.

**Slice round (2026-09-23): "speed it up 1.7 times; after the animation the model's forward direction
changes 20–30°; it stops too suddenly, use 5–6 more reference frames".** `time_scale 0.4525`
(0.7692 / 1.7), `unwind_yaw` and the range extended: the recording's hand speed (measured on the
source armature) is still 1.1 m/s at frame 171, settles to ~0.5 at 174 and the performer walks off
from 180, so `src_end 176` (34 frames, 1.10 s; the hand ends at 1.5 m/s in Unity, decelerating,
was 3.2). The turn: a hips-only unwind left Unity's root-motion yaw at −13° because **Unity derives
root rotation from the BODY orientation, which weights the chest about 2:1 over the hips** (measured:
hips net 0°, chest net −19°, root rotation −13°; the follow-through leaves the torso turned).
**`unwind_ref body`** (`--unwind-ref hips|body`) cancels (hips + 2·chest)/3 instead: root-motion
yaw 356.7° / 3.3° (R / L). Lowest vertex after the fit: the Archer sinks ≤ 9 mm.
Then the user's `Attack_R_Slice_Fix` (foot_ik.L/R + hand_fk.R, Combine over the strip): "reuse it
to remove the right foot drift, plus the left foot drift after the step forward, from frame 20; then
bake". Traced through the stack: the right (rear) foot wandered 8 cm sideways and 6 cm fore-aft
while planted, the left steps forward over frames 13–19 and then slid 2–3 cm. `--pin-foot` now takes
`SIDE[:ref[:from[:to]]]`: **`--pin-foot "R,L:20:20"`** holds the right foot at its frame 1 transform
for all 34 frames (knee 144–157°) and the left at its frame 20 transform from frame 20 (knee 127–139°),
DEF feet on their pins to 0.0 mm; then `--mirror-to Attack_L_Slice --save`, both flagged
`hand_edited`, exported with `--export-only`: root motion 32 cm, yaw 356.7° / 3.7°, the six boots
sink ≤ 9 mm after the fit. Then "speed up by 35 % from frame 21 to 34": the clip is a baked action
now, so the warp runs on it: **`anim_nla_bake.py -- --result Attack_R_Slice --speed-segment 21:34:1.35
--mirror-to Attack_L_Slice --save`** (with no NLA the "stack" is the action itself; the segment is
resampled at fractional frames through Blender's own curve evaluation, `frame_set(f, subframe)`,
ending exactly on 34): 34 → 31 frames (1.00 s), the segment 14 → 11. A re-bake keeps the FIRST
`_base` (the generated clip) and just replaces the current action. ⚠ `anim_batch --export-only`
skips a clip whose manifest entry has not changed since its last build (the signature check): add
`--force` after a bake that touched only the anim file.
**Block_L_Idle (2026-09-23):** the user asked for the heater shield in Blender "the same way I have it in
Unity" (`anim_weapon_ref.py -- --attach H1HeaterShield:L --check Block_L_Idle:1 --save`, after a
`dump_grips.py` re-dump; placement 0.00000 m, the plate's long axis along the fingers), posed the
held block as `Block_L_Idle_Fix` (`hand_ik.L`, ONE key at frame 1 in Combine with Hold extrapolation,
so the same offset rides every frame of the loop and the seam is untouched) and had it baked
(`anim_nla_bake.py -- --result Block_L_Idle --save`, flat = stack to 0.00 mm; `hand_edited`;
`--export-only --force`): 6.0 s loop, in place, lowest vertex +4..+9 mm. `Block_L_Idle_base` keeps
the Kimodo build. Then "I wanted to adjust it again but upper_arm_fk.L and its children won't change
the mesh": that arm was on IK for the whole clip (`arm_pose shield_block` pins the fist on IK), so
only `hand_ik.L` moved it. **`anim_nla_bake.py -- --result Block_L_Idle --fk-arm L --save`**
converts an arm to FK losslessly: per frame the FK controls are set to reproduce the DEF upper arm,
forearm and hand (rest relation FK control → DEF bone) and `IK_FK` keyed 1; reproduced within 0.00
mm / 0.00° on all 181 frames, so no re-export. FK is the lossless direction (an FK chain can take
any rotation); IK→FK is exact, FK→IK loses the forearm twist. `hand_ik.L` is inert on this clip now.

**Sixth reference (2026-09-23, evening): `P:\c7uJKSavZ5aC-mWAAEhPEcDP8.glb` → `attack_ref6_mocap.glb` →
`attack_ref6_arm.blend`, 427 frames**, four clips from one take: `Idle_Propped`, `Idle_TwoHanded`,
`Attack_2H_01`, `Attack_2H_02`, all plain transfers (`rename ue5`, `src_ext blend`). ⚠ **The user's
frame numbers count at 24 fps; the recording is 30 fps.** The first build of "236–281 = Attack_2H_01"
gave a clip whose right arm moved 4°: a per-frame hand-speed scan of the source (`ref6speed.py`-style:
hand_r world speed per frame) showed nothing moving there and the two attacks at 304–327 and 368–412,
exactly the user's ranges × 1.25 — as were the idles (the performer lowers the hands onto the staff
by 90 and raises the two-hander at 206). So: propped 96–188, two-handed 213–294, chop 295–351, second
attack 355–413. Rule: **scan the source for the motion before trusting a frame range**. Settings:
idles slowed 2× (`time_scale 2.0 smooth 2`, loops 160 / 140 with 20-frame seams, 0.0000°);
`Idle_TwoHanded` keeps the left hand on the shaft through the gate (slots 5–6 cm apart, 12 cm apart
in `Idle_Propped` where the left hand rests below the right on the staff); the attacks like the arm
set (`plant_feet`, `drift root`, `unwind_yaw` + `unwind_ref body`, `gate "0.03,0.11"`, `lift 0.004`,
`ground_fit`): 57 / 59 frames, root motion −5 / +2 cm, yaw 0° / −1°, right arm 53° / 69°, boots on
the floor (≤ 9 mm sink). **The propped staff**: the plain transfer left the hand's hilt axis 53° UP
(a hand resting on a staff top has no vertical hilt), so `prop "R:0.69"` + `prop_damp 1.0` aim it at
the floor point a 1.24 m staff reaches from the hand's height (the hand keeps its recorded position,
~22° of lean), and since the hand rests at 1.15–1.17 m, on the staff's TOP, `ProppedHandHeight` is
1.24 (the Grip of `W_H2MagicStuff_Top` at the mesh top, moved in the existing prefab by
`execute_code` — the builder never overwrites a weapon prefab — and re-dumped to `unity_grips.json`).
Measured with the staff attached: foot at −0.01 m, top 1.17 m, elbow 81°. Then "both hands closed,
currently only the right does": the engine's grip fist goes only on a hand that HOLDS an item, the
empty left hand played the clip's own fingers (the constant curl). **`hand_grip L`** (`--hand-grip
L|R|LR`): that hand's finger controls take the `Grip` action's fist on every frame (read from the
action at start; verified 0.00° on every frame, middle fingertip 5.6 cm from the wrist), so both
hands close the same way in the engine. Then "IK controls don't work on the left arm": measured
headlessly, `hand_ik.L` moves the hand 27 cm in Idle_TwoHanded (gated, IK) and 0 in Idle_Propped
(plain transfer: FK), so the clip in question is the propped idle; `ik_always both` on it puts the
left arm on IK for the whole clip (the right already was, for the prop). Cost, measured: upper arm
and hand 0.0 mm / 0.0°, the forearm's own twist 20.9° different (the IK forearm carries none), i.e.
the vambrace rolls; drop the key to get the FK forearm back. The Kimodo / JNT builds of
these four (`arm_pose two_handed_shoulder`, the prop/hunch/torso_ref passes) are history in the
manifest notes.

Then "reuse it to get rid of feet drift" (the pin tool on the 2H attacks; the two idles have none —
their feet sit at the rest stance on every frame): traced per frame, the rear LEFT foot wandered 5 cm
while planted and lifted its heel 5 cm mid-lunge (a real pivot, not drift), the RIGHT foot slid before
and after its lunge step. Two new pin modes in `anim_nla_bake.py`: **`SIDE:ref:from:to:xy`** holds only
the horizontal position and keeps each frame's own height and rotation (the heel lift survives), and
**`SIDE:auto`** finds a stepping foot's planted phases itself (ankle within 12 mm rig of the clip's
lowest, ≥ 3 frames) and holds each at its middle frame (2H_01: 1–11, 29–36, 54–57; 2H_02: 1–8,
26–34, 55–59). Also **`--action NAME`**: with no fix stack the tool used to flatten whatever action was
ACTIVE (a dry run on the 2H clips produced the idle's feet); a plain clip is now named explicitly. Both
attacks flagged `hand_edited`, exported with `--export-only --force`.

**A fix from an unsaved session (Idle_Propped, 2026-09-23 late).** The user had `Idle_Propped_Fix`
open but did not want to save over the anim file (my later saves would have been lost): **File > Save
Copy** to a side path (`GitHub/skeleton_anim.blend`, outside the repo), the bake run ON THE COPY
(`anim_nla_bake.py -- --result Idle_Propped --save`, flat = stack to 0.00 mm), then the flat clip and
the fix action appended into the anim file (`transfer_action.py`: the old clip becomes `_base`, the
NLA cleared, the appended action made active) and exported with `--export-only --force`. The fix:
one held key on torso, chest, head, both feet, both hands and both elbow poles. Rule: **never ask
the user to save their session over a file the tools have touched since; a Save Copy is the bridge.**
The fix lowered the propping hand to 0.97 m and hunched the chest to 37°, so the staff gripped at its
top went 27 cm through the floor: `ProppedHandHeight` 0.97 (prefab Grip moved in place, grips
re-dumped); measured with the staff attached: foot 0.00 m, top 1.24 m, nearly vertical, elbow 84°.

**Idles bob in Unity (2026-09-23, "in Blender the feet are static, in Unity they drift up/down slightly
in Idle_TwoHanded").** Measured per frame on the Knight: both boots together at +10..+16 mm, following
the hips sway (0.94–0.98 m) — Humanoid's leg reconstruction moves the whole body a few mm with the
hips on top of the constant 15 mm lift; Blender's IK feet never move. Both feet track together, so
`ground_fit true` on Idle_TwoHanded and Idle_Propped (the per-frame Root fit, now on idles too):
Knight boots within ±2 / ±4 mm of the floor on every frame, the highest model's sole at 0, the
others sinking ≤ 10 mm; the fit curve's first and last frames differ by under 1 mm, so the loop seam
holds. Rule: a looping idle can take the per-frame fit as long as its seam is checked in the curve.
Then "closed grip on the left hand" for Idle_TwoHanded: the left hand rides the shaft but holds no
item, so the engine gives it no grip pose; the clip is hand-edited (no retarget), so `anim_nla_bake.py
--hand-grip L` does what the retarget's `hand_grip` does, on the baked action (25 finger controls,
verified 0.00° against the Grip fist on every frame).

**Attack_2H_01's right arm (2026-09-24, "till frame 16 upper_arm_fk_r controls the elbow, from 17 the mesh
detaches; a sudden jerk from 16 to 17").** The gate's reach PULL had put the right arm on IK for frames
17–46 (the hand pulled in so the left could reach the shaft) and left it FK elsewhere, with the elbow on
the REST pole on the IK frames: an 82 mm elbow step at the switch (neighbours 15–19 mm). Two bake-tool
passes, both lossless: **`--arm-pole-fk R`** re-aims the pole at the FK chain's own elbow on every IK
frame (the FK controls carry the capture's arm even while the switch is at IK; refined to 0.00° of
swivel), then **`--fk-arm R`** converts the whole arm to FK (0.00 mm / 0.00°). Result: FK on all 57
frames, elbow step 16 mm at 16→17. And **`--action NAME` now keeps the user's NLA stack**: the strip is
re-pointed at the rewritten clip and the fix action stays active in Combine, so a base can be repaired
under an edit in progress. Two things that bit: (1) my pin-foot rewrite had sliced `fk_arms()` out of
the tool (the slice from `def pin_feet` to the next marker swallowed the function after it; committed
that way) — restored; (2) **the clip export applied the stack twice**: `export_fbx` assigned the action
while the user's strip of the same clip stayed live in Combine (hips 36°, head 67°, arm 123° — every
angle doubled). `export_clip` now mutes every NLA track and sets the action alone in Replace at full
influence. Rule: any tool that evaluates a named action must silence the NLA first.

Then "attack direction is a bit to the left; add torso rotation, 50–60°, so the attack ends more forward;
speed it up 20 %": traced, the whole upper body turns 73° LEFT through the swing (chest −17° → +56°,
hips −16° → +41°, frames 18–33) and that is where the cut lands. **`--torso-yaw 55`** (bake tool)
counter-rotates the upper body against its OWN excursion: at the frame of the largest chest deviation
from the first frame the correction is 55° the other way, scaled by the deviation elsewhere (0 at both
ends, so the transitions are untouched), spread over `spine_fk.001` / `.002` / `chest` with a residual
correction on `chest` (≤ 1°); an IK left hand and its pole ride along with the right hand's socket
transform so the two-handed grip holds. Chest peak +56° → 0° at the cut; hips still turn (+23°).
`--speed-segment 1:57:1.2` → 48 frames. Rule: a swing's "direction" is the chest's yaw excursion —
counter it proportionally, never with a fixed offset (a fixed turn moves the start/end poses).

Then "bring the left hand 10 cm higher on the weapon grip; it should follow the shaft perfectly, as the
left hand is not attached to the weapon slot": the left hand is on the shaft only by the retarget's
gate, and the counter-turn, the resample and the user's fixes had left it −0.042..+0.022 rig m along
the right hand's hilt axis (around the right hand) and off the axis. **`--shaft-hand L:0.056`** (bake
tool) re-seats that socket ON the other hand's hilt axis every frame (its hilt axis turned parallel to
the shaft with the least rotation, the hand's own roll kept, the IK control moved rigidly with the
socket) and slides it the given rig m up the shaft: now +0.014..+0.078 (above the right hand, toward
the blade), ≤ 6.8 mm off the shaft (one frame at the arm's reach), hilt axes parallel to 0.0°.
`+` = toward the blade; if the hand should go the other way the sign flips.

Then "starting the attack from Idle_TwoHanded the left hand changes its grip; at the end of the attack it
sits too close to the right hand; in the idle it drifts slightly, as if not gripping": all one thing, the
left socket's transform RELATIVE to the right socket. **`--grip-follow L:Idle_TwoHanded:1`** (bake tool)
reads that relation on the reference action/frame (the user's posed idle grip: +0.074 rig m along the
right hand's hilt axis, 40 mm off it — their pose, kept as is) and holds it rigidly on every frame of the
target (the hand's IK control moved with the socket). Idle: the relation had wandered 7.6 mm / 1.2° over
the loop (the visible drift), now 0.0 mm / 0.0°. Attack: it had wandered 72 mm / 146° from the idle's
(a different roll, from the gate and the fixes), now within 12.6 mm (one frame at the arm's reach) /
0.0°, so the crossfade from the idle keeps the grip and the end of the attack has the idle's spacing.
The earlier `--shaft-hand` step on the attack is superseded by this.

**Attack_2H_02 (2026-09-24):** the same right-arm switch (IK 13–41 from the gate pull, 37 mm elbow step)
fixed with `--arm-pole-fk R --fk-arm R` (elbow step 19 mm). Then the user's fix: "faster after frame 16 by
25 %; left hand always follows the handle, 10 cm above the right hand; remove the right foot snap at
frames 34–35; bake": `--speed-segment 16:59:1.25` (59 → 50 frames); **`--grip-follow L:@0.056`** (an
idealised relation: ON the right hand's hilt axis, 0.056 rig m toward the blade, hilt axes parallel, the
hand's own roll about the shaft from frame 1 kept) with **`--grip-pull`**: where the left arm cannot reach
its spot (the sweep's extension: 19 of 50 frames, up to 49 mm short) the RIGHT hand is pulled in toward
the left shoulder by the shortfall on IK with its elbow on the FK plane, then `--fk-arm R` lands it back
on FK — within 1.5 mm on every frame; **`--pin-ease 4`**: each held foot phase now eases in and out over
4 frames (position lerp, rotation slerp against the clip's own foot), so the landing's release at the old
34–35 (now 30–34) steps 0 → 2 → 10 → 16 mm instead of snapping. ⚠ **A whole-character key in a Combine
fix cancels the clip's root motion**: the user's fix keyed `root` location (2 keys, +0.02) against the
strip's −0.02 drift, the stack evaluated to zero travel and the bake reproduced it (root motion 0, the
clip 15 mm low with no Root keys to lift); restored by rewriting the flat clip's root keys from the base
(retimed through the speed segment) — the bake tool now WARNS when a Combine fix keys the root. Result:
root motion 3.5 / 2.9 cm, boots within 4 mm of the floor on every frame (the Knight's skirt dips 17 mm in
the lunge crouch, the robe class of dip).

Then "the left hand snaps mid-attack in Unity, not in Blender — the left arm overextending; fix it by having
the right hand higher on the handle and the left hand lower, so the left hand is closer to the body; same for
Attack_2H_01". Measured in Unity: Attack_2H_02's left arm stepped 42° on frame 14 with the elbow at 178° — the
straight-arm flip (Humanoid's elbow plane is undefined on a straight arm; Blender's IK shows nothing).
The longsword's handle is long (mesh y −0.28 pommel .. +0.11 guard, the grip sat at y −0.15, mid-handle):
`W_H2Longsword`'s Grip moved to y +0.02 (the right hand 9 cm under the guard, 17 cm higher; grips
re-dumped), and **`--grip-follow L:@-0.075`** on both attacks AND Idle_TwoHanded (the same grip in all
three: the left hand 13.5 cm BELOW the right, toward the pommel and the body) with `--grip-pull` and the
new **`--grip-reach 0.96`** (the pull also acts when the wanted spot would put the wrist beyond 96 % of
the arm's length, so the elbow never locks): sweep's worst left-arm step 42° → 24° (elbow 110°), chop
26° (elbow 178°, seen after the first pass without the reach limit) → 9°. Rule: **keep every IK arm
under ~96 % of its reach; a Unity-only snap on a straight arm is the flip, and the cure is a bent elbow.**

Then "the left hand is a bit off position" (a close-up: the fist beside the handle, ~3 cm out). The weapon
hangs from the hand SLOT (the user's tuned offset from the socket bone, `RightHandSlot` 3.5 cm from it),
not from the socket, so a socket-on-the-axis relation leaves the fist beside the shaft by that offset.
`--grip-follow SIDE:@D` now builds the relation SLOT-to-slot (the slots read from `unity_grips.json`, X
flipped into the socket frame): measured in Unity, the left slot sits 2.2–2.6 mm off the right slot's
axis at worst on all three clips, 13.4 cm below it, slot axes parallel within 0.8°. Rule: **anything
that must sit on the weapon sits on the SLOT's axis; the socket is only the bone the slot hangs from.**

**Idle (the base idle) hand-fixed (2026-09-24):** the user's `Idle_Fix` (torso, both feet, both knee
poles, right arm; one held key each in Combine over the pushed-down strip, so the 8 s loop's seam is
untouched) baked by `anim_nla_bake.py -- --result Idle --save`, the Kimodo/`anim_fix_idles` build kept as
`Idle_base`. The three base idles had NO manifest entry (built before the clip factory and reworked by
`anim_fix_idles.py`), so the batch could not export it: an `Idle` entry was added (`glb idle_s42`,
`hand_edited`, `ground_fit`; not reproducible from the entry alone) and `--export-only --force` exports it
with the per-frame fit: highest model's sole on the floor, the others sinking ≤ 7 mm. `Idle_02` /
`Idle_03` still have no entry; add one the same way before exporting them through the batch.

**Walk_Fwd hand-fixed (2026-09-24, "added walk_fwd_fix; remove the right foot drift after the step from
frame 11 to 30 and the left foot drift from 31 to 43").** Traced in world space (root travel included): the
right foot slid 1 cm through its stance, the left 3.4 cm sideways over 31–43 — that one is the LOOP-CLOSING
crossfade dragging the planted foot from where it landed (x 0.134) to frame 1's spot (x 0.100), since frame
43 must equal frame 1 + the loop's travel. So the left hold's reference is frame 43 (seam-exact, the foot
now lands on the seam spot in flight) and the right's is frame 30 (its most extended moment). The walk's
legs are FK from the retarget, so **`--ik-legs`** first puts both on IK losslessly (foot / toe on the DEF
result, the knee pole out through the FK knee, 0.0 mm) — a pin on an FK leg would switch modes and jump
the knee — and every held frame keeps the pole on the pre-hold knee plane. **`--pin-ease 6:1`**
(in:out): a 6-frame ease-out on the right foot's push-off held the lifting foot back and straightened the
knee to 177° on frames 32–33 (the original never passed 165°); one frame out keeps it at 144–165°.
Root motion unchanged (0.724 m per loop), boots +7..+13 mm. The arm fix (one held key each) rides along.

**Walk_Back hand-fixed (2026-09-24):** legs to IK first (`--ik-legs`, "foot_ik.L and R don't control the
feet"), then the user's `Walk_Back_Fix` (both feet, 3 keys each) with: **`--vsmooth 103`** ("a slight jerk at
frame 103, the body shifts down": hips and both feet dipped 6–8 mm on that one frame — the loop-closing
blend's last frame; each root-level control's height on that frame is replaced by the mean of its
neighbours), and the left foot held horizontally over 1–55 at frame 1's spot (`L:1:1:55:xy`, ease 0:1: a
full-transform hold kept the foot flat through the push-off and the base's 167° knee went to 177°; xy keeps
the heel lift). `ground_fit` added: the fix had put the boots 17 mm under the floor in Unity (highest sole
now at 0, the others ≤ 12 mm under). ⚠ Measured on the user's stack BEFORE any pass: the left knee sits at
177° on frames 54–62 — their foot placement locks the leg straight (a Humanoid flip risk, see the 2H
sweep); reported, not changed. The right foot drifts 10 cm sideways over 37–104 (the loop blend pulling it
to frame 1's x) — not asked for, left alone.

Then (Walk_Back, second fix): "make the steps travel 30 % less, the legs overextend and twitch; the right
foot drifts 93–104; 30 % faster". **`--stride 0.7`** (bake tool, locomotion): the root's advance AND every
root-level control's position along the travel axis are scaled about the root's first-frame spot (p' = p +
(k−1)·((p−r0)·axis)·axis), so a planted foot stays planted, the body travels 0.7× and the feet's fore-aft
excursion relative to the hips shrinks 0.7× — the knees bend more: max L 148° / R 141° (the locked 177°
of the previous fix is gone). Right foot held horizontally over 93–104 at frame 104's spot (seam-exact);
`--speed-segment 1:104:1.3` → 80 frames. Unity: 2.633 s, −0.782 m per loop, 0.30 m/s (was 3.433 s /
−1.119 m / 0.33 m/s: the speed table above is updated; the demo's in-place blend tree reads it).

Then "left leg jerk at frame 44; right foot drifts 68–72" (the 80-frame clip): the left jerk was MY pin's
release (frame 1's x held to 43, the clip's own x 2 cm away on 44: a 16 mm step), the right drift the
pin's 3-frame ease-in squeezing the 10 cm lateral loop-blend correction into 69–71 (29 / 36 mm steps).
Both feet re-held with **`SIDE:auto:xy`** (planted phases found by the tool, now SEAM-AWARE: a phase
touching the first/last frame keeps that frame as its reference, an inner phase its middle) and
`--pin-ease 6:5`: L 1–43 at frame 1's spot, R 39–80 at frame 80's, releases eased — steps 3 mm at 44,
0 at 69–72. That exposed a seam pop the user's fix had introduced (the left foot 10 mm higher on the last
frame than on the first: keys near the ends of a Combine fix are not loop-consistent): **`--loop-seam 6`**
crossfades every control over the last 6 frames to the first frame's pose (root-space positions advanced
by the travel) — last frame = first + travel within 0.0 mm on feet, hips, hands and head. Rule: **after
any hand edit of a loop, re-close it** (`--loop-seam`) and check `frame F1 − travel == frame F0`.

**"You're clearly incapable of fixing a simple issue like this" (Walk_Back, right foot and left leg, a GIF).**
Right: my checks measured the FEET (steps of 3 mm) while the defect was the LEFT KNEE — a per-bone
rotation scan (`legscan.py`: every leg bone's per-frame rotation step and its acceleration; use
min(a, 360−a), a quaternion's `.angle` can read 356° for a 4° step) showed the shin rotating 52° with the
knee jumping 73 mm sideways at frame 44: the IK pole flipped at the pin's release, because `hold()` took
its pole from the DEF knee of the previous pass and the frames outside the hold kept whatever pole an
earlier pass had keyed. And the right foot's 9 cm lateral loop-blend correction was crammed into the
6-frame ease-in before landing. Rewritten: (1) **the pole comes from the clip's own FK knee on every
frame** (`fk_knee`: the FK chain still carries the retarget's legs after `--ik-legs`, a continuous
reference) and `repole_legs()` runs after every leg pass (knee steps ≤ 14 mm); (2) **a pin's correction is
carried through the whole flight** between consecutive holds (position lerp + rotation slerp on a
smoothstep, wrapping across the seam with `--loop`), never switched on over a few frames; (3) the clip
rebuilt from `Walk_Back_base` + the user's fix stack in ONE run (`setup_stack.py -P` then the bake tool:
`--ik-legs --vsmooth 103 --stride 0.7 --pin-foot "L:auto:xy,R:auto:xy" --loop --loop-seam 6
--speed-segment 1:104:1.3`), so no artefact of the three earlier rounds is left in the data (each round's
"own" foot had the previous round's eases baked in). Result: no leg bone rotates more than 5.7° between
frames anywhere, knee steps ≤ 21 mm, seam 0.0 mm, root motion 0.783 m / loop. Rule: **when the user
reports a jerk, scan every bone's rotation acceleration before claiming it fixed; a foot-position check
cannot see a knee flip.**

**REVERTED (2026-09-24, user: "the right foot drift is caused by thigh_ik_target.R and the left leg jerk by
thigh_ik_target.L; revert walk_back before applying the fix, it's beyond saving").** Walk_Back is the
generated clip again (`Walk_Back_base` renamed back; verified identical to HEAD's on feet, knees, hips,
hand and root), the export, manifest entry (no `hand_edited` / `ground_fit`), build state and speed table
restored from HEAD, the fit curve deleted; `Walk_Back_Fix` stays in the anim file. The four walk-back
paragraphs above are history of what NOT to do: the per-frame keyed knee poles (`thigh_ik_target`) are
what the user saw. Lesson: on a locomotion loop, the poles must not be keyed per frame from a pass;
either leave the legs on FK (the retarget's output) and pin through the retarget's own plant, or keep
the pole targets smooth and few.

**Walk_Back redone from a fresh Kimodo generation (2026-09-24, user: "let's redo it completely with a new
Kimodo animation").** Three candidates generated on the laptop (seeds 21 / 33 / 47, prompts varying
"short careful steps" / the original / "backs away slowly with small steps") and scored with
`walkeval.py` (loop length, root travel, knee range, planted-foot skate per stance, largest leg-bone
rotation step): c1 locked a knee at 172°, c2 skated 134 mm on the left stance, **c3** (seed 47, small
steps) kept every knee bent (105–153°) with the least skate — it is the new `Walk_Back` at `time_scale
1.0` (1.3 gave 0.21 m/s): 72 frames, 0.662 m per loop, 0.28 m/s, seam 0.0000°, `lift -0.002` (a
CONSTANT lift: the per-frame `ground_fit` on this walk dipped 10 mm over frames 8–14 and 69–71 — where
the retarget's ground pass floats the body over a foot dip — and stepped 10 mm at the seam, a hop; the
constant puts the highest model's sole at 0 on its lowest frame, the others ≤ 5 mm under). Rule: **no
per-frame fit on a stepping loop unless its curve is checked for frame steps and the seam**. Skate of
36–62 mm per stance remains, as on every
Kimodo locomotion clip (a human's FK legs on the skeleton's proportions). The GLB import now links
into the scene root (`active_layer_collection` reset: a saved session had left the overridden `Rig`
collection active and every retarget failed with "Could not (un)link the object 'Icosphere'").

Then the user's `Walk_Back_Fix` on the new clip ("make it 70 % faster; fix the feet drift, right 11–69,
left 59–72"): `--ik-legs --pin-foot "R:40:11:69:xy,L:72:59:72:xy" --loop --loop-seam 4 --speed-segment
1:72:1.7` (43 frames, 0.47 m/s; speed table updated). The first build put the LEFT shin through a 74°
step with the knee locked at 177°: the left hold spans the seam, and the flight carry lerped its
correction across the whole loop — including the left foot's OTHER stance (1–41, not asked to be
pinned), pushing that foot 6 cm through its stance. **The carry now changes only while the foot is in
the AIR** (constant at the previous hold's value while still on the ground, smoothstep through the
flight, constant at the next hold's once landed). Scan: no leg bone above 13.3° per frame (at 1.7×),
knees 105–154 / 112–136, seam 0.0 mm; right-foot skate 54 → 17 mm, the pinned left part 12 mm (its
unpinned first stance still skates 34 mm). Rule kept from the day: **run the per-bone rotation scan
after every leg pass, before reporting.**

Then "make the walk 40 % slower; too much movement above the legs, use the above-torso animation from
idle_3": `--speed-segment 1:43:0.7143` (60 frames, 1.97 s, 0.34 m/s) and **`--upper-from Idle_03:1`**
(bake tool, after the retime): every control above the legs — the torso's ROTATION (its location stays
the walk's: it carries the hips over the IK legs), spine, chest, neck, head, jaw, shoulders, arms, hands,
fingers and the arm switches, 91 controls — is taken frame by frame from a 60-frame window of Idle_03
(a 10.8 s loop, so the window is a slow sway), the window's last 8 frames crossfaded to its first
(`--upper-seam`) so the walk loop still closes: chest 0.1° / head 0.3° across the seam, no upper-body
bone above 3.2° per frame, legs unchanged (≤ 9.4°). The user's arm fix is superseded by the idle's arms. Then (2026-09-25) the user's updated `Walk_Back_Fix` (both feet, one torso key) baked over the finished
clip with `--loop --loop-seam 4` (seam 0.0 mm, travel unchanged): the pelvis 5° more upright, both feet 3–4 mm
lower and the left foot 4–5° more toe-down, so `lift 0.004` (was −0.002) puts the highest sole back at 0.
Left as authored and reported: the swinging left boot's toe reaches 10 mm under the floor on frames 44–46
(Unity), and the Necromancer's robe hem between the legs, which the pelvis tilt lowers, dips 31 mm at frame 8
(the robe class of dip). ⚠ `ground_clip` samples every 6th frame and saw neither; `ground_fit`'s per-frame
measurement did (read its json, then delete it: no per-frame fit on a stepping loop). Then (2026-09-26, "freeze the left foot from frame 1 to 27 and the right from 14 to 56"): `--pin-foot
"L:1:1:27,R:35:14:56" --loop --loop-seam 4 --even-advance 15` on the finished clip — full-transform holds
(the left at frame 1's spot so the seam holds, the right at its mid-stance frame 35), DEF feet on their holds to
0.0 mm, the corrections carried through the swings, the loop re-closed and its seam retimed (hips advance
2.9–8.8 mm per frame, 5.2 at the wrap). Knees 111–140 / 118–159, no leg bone above 11° per frame, travel
unchanged; the highest sole at +1 mm, the others ≤ 3 mm under, the Necromancer's robe 23 mm.

**Strafes (2026-09-24, "added strafe_left_fix, bake it; steps 30 % less; the right foot drifts above the
ground from frame 1 to 19; same for strafe_right").** Traced: the right foot lands at the seam 4 cm up
and settles over 19 frames while sliding — `--ik-legs --stride 0.7 --pin-foot "R:25:1:33" --loop
--loop-seam 4` (the whole stance held flat at frame 25's spot; the flight 34–45 carries the correction so
it lands planted on frame 1) and **`--mirror-to Strafe_Right`**: Strafe_Right was the raw generation and
Strafe_Left its mirror, so the finished left (fix, stride, pin) X-flipped IS the right with the same
changes (landmarks within 2.7 mm of the exact mirror). The mirror is now built from the finished result
(it used to be read right after the pins, missing the later passes). Scan: no leg bone above 10.7° per
frame, knees 102–130 / 112–122. Speed table updated (0.419 m per loop, 0.29 m/s).

**Idle_Staff / Idle_Wand rebuilt on the user's own idle (2026-09-24, "too static; some light sway plus
hand movement; the right hand extends too far on idle_wand").** Measured: the Kimodo builds swayed 11–15 mm
at the hips with the head at 1–4°/s and the hands moving 12–14 mm; Idle_03 (the user's mocap) 39 mm,
15°/s, 80–107 mm. Both idles now use Idle_03's source (`idle_mocap`, `rename mixamo`, the same trims,
`time_scale 3.0`, 324-frame loop, `fingers`) with their `arm_pose` presets on top: the pinned hand follows
the torso's sway (39–48 mm of motion), the free hand and the fingers are the capture's (81 mm). The wand
hand: the preset sat at 0.318 of a 0.32 arm (elbow locked) — **`arm_pose_reach`** (`--arm-pose-reach`,
default 0.9) pulls an authored hand toward its shoulder to that share of the arm; 0.9 still left the arm
straight out in front, `0.7` on the wand gives an elbow of 89° with the hand 20 cm ahead and 10 cm below
the shoulder (the staff keeps 0.9). Seams 0.0000°, boots +5..+10 mm.

Then the user's `Idle_Wand_Fix` (hand_ik.R) plus "a right-hand sway that mimics the wand's weight, in sync
with the character swaying up and down": **`--hand-weight R:0.015:4:6`** (bake tool): the hips' height over
the loop, normalised, delayed 4 frames (wrapping) and inverted, moves the IK hand ±15 mm rig the other way
and pitches it ±6° about the socket's finger axis (the tip dips as the hand drops; the sign measured so a
positive turn lowers the hilt). Hips ±3.4 mm → hand ±20 mm in total, 3 mm per frame, elbow 105–119°, seam
0.9 mm.

**Impaled_Rise leg snaps (2026-09-24, "lots of snapping in the legs, most likely IK gaining / losing
control").** Scanned: knees jumping 179–186 mm with shin rotations of 56–99° at frames 2 and 16, the
legs' IK weight switching 12–14 times (the clip predated `ik_always` and the FK-knee pole). A rebuild
through the current retarget fixed the right leg and the switching (0 switches) but the LEFT knee still
jumped 105 mm at frame 40: the capture's left leg is dead straight (180°) over frames 40–46, its knee ON
the hip→ankle axis, so the pole plane was noise and flipped sides. **The pole now has memory** (retarget
`ik_pole` and the bake tool's `leg_pole`): while the reference knee lies within 15 mm of the axis, or its
side jumps more than 90° from the last frame, last frame's plane is kept. After: no leg bone above
11.3° per frame, knee steps ≤ 38 mm (the rise itself). Rule: **a knee plane is only trusted when the
reference leg is bent; straight legs inherit the plane.**

Then "cut the frames from 47 to 65; it's ok to lower the torso on the fully standing pose, use it to fix
the floating feet at the end": the rise's end sat at hips 0.546 rig m with the knees at 163° (near
straight: Humanoid floats the feet) while the hand-fixed Idle's frame 1 is at 0.509 with knees 135–139°
— the old `blend_to Idle` had been baked before the Idle fix. `anim_nla_bake --speed-segment 47:65:19`
(the 19 frames become 2: 69 → 52 frames, a 19° step at the junction, the asked-for cut) and
**`--end-blend Idle:1:8`**: the last 8 frames crossfade every control to Idle's frame 1 (the legs keep
their IK with the pole re-aimed on the FK plane through it), so the clip ENDS on the idle's pose exactly —
hips 0.509, knees 139 / 135°, feet at the idle's height — and the demo's crossfade lands with nothing to
do. Rule: **a one-shot that returns to an idle should end on that idle's current frame 1; after an idle
is hand-fixed, re-blend the one-shots that end on it.** Impaled_Rise is `hand_edited` now.

**A second, "normal" walk and run (2026-09-25, user: "another set of walk forward and run forward; the
current ones are fine for skeletons of lower ranks, but the necromancer and mage can have more normal-looking
movement").** `Walk_Fwd_02` / `Run_Fwd_02`, generated by Kimodo WITHOUT the stiff-undead body profile
(manifest `no_profile`, `kimodo_batch` passes `-NoProfile`; the profile is what makes the first set shamble)
from plain human prompts, three candidates each (`walk_fwd_n1..n3`, `run_fwd_n1..n3`, GLBs kept), scored
with an extended `walkeval` (gait-cycle autocorrelation, knee range, planted-foot skate, largest leg-bone
step, chest lean and head pitch from vertical, hip sway, hand swing per arm). Walk: n3 (seed 35) has the
cleanest cycle (r 0.97), both knees 109–171° (n1 locked at 175°, n2's cycle was r 0.51 with a 110 mm seam
skate), chest 6–9° with a level head — the first set leans 18–41° with the head bowed 23–39°; its arm swing
is asymmetric (89 / 168 mm), the one thing a hand fix might want. Run: n2 (seed 24), both knees bent
(90–164°, symmetric), the least skate (33 / 46 mm per stance; n1 skated 191 mm), chest 20–29° as a jog
leans (n3 barely bent the right knee and looked up). Plain loco retargets at `time_scale 1.0` (their
speeds are a human's: 1.28 / 1.87 m/s against the shambling 0.52 / 1.14; `time_scale` is the knob if the
higher ranks should read heavier), 35 / 26 frames, seams 0.0000°, boots +4..+12 mm (`lift 0.008` on the
walk: the default 15 mm left them +12..+19) / +7..+15 mm. Same shared clips as everything else: they sit
in the demo's Locomotion section (`SkeletonShowcase` members) and on `AC_Skeleton` as Base states, and
the buyer decides per class; no per-character default exists in the demo. The speed table above carries
both. Rule: **a prompt's body description is a style knob** — the same generator gives a shambling and
an upright gait from the profile alone, so generate style variants by toggling it, not by re-describing
the gait.
**`Walk_Back_02`** (2026-09-26, "another walk_back_02, a normal looking one; this one is good for a low-grade
skeleton, walk_back_02 for a higher rank"): the same recipe, three candidates (`walk_back_n1..n3`, kept); n3
(seed 37) for its level head (6–9°), symmetric natural arm swing (108 / 100 mm), chest 6–11° and moderate skate
(42–63 mm per stance; n1 had the cleanest cycle but a bowed head and a weak swing, n2 skated 17–22 cm). Plain
loco retarget at `time_scale 1.0`: 45 frames, 1.132 m per loop, 0.77 m/s (the shambling one does 0.34), seam
0.0000° and the hips' advance continuous across the wrap (17, 16 → 15, 14 mm per frame: no retime needed),
knees 121–173° (all three candidates straighten to ~173° at push-off), `lift 0` (the default floated the boots
9–16 mm; the highest model's sole at +1 mm now). In the demo's Locomotion section and on `AC_Skeleton`.
**Renames and narrower strafes (2026-09-26, "strafe left/right still steps too wide; add a higher-rank strafe
left/right; the existing walk fwd/back, strafe right/left should receive the _01 index").** `Walk_Fwd`,
`Walk_Back`, `Strafe_Left`, `Strafe_Right` → `*_01` everywhere: the anim file's actions and their `_base`
copies (the user's `*_Fix` actions keep their names), the manifest, the build state, the exports (old FBX +
meta deleted, the four re-exported under the new names so the take names match), the demo list, the
controller (rebuilt), the layering proofs in `build_twitch_controller.py` / `layer_smoke.py`. `Run_Fwd` was
not listed and keeps its name. The strafes: `--stride 0.7` again on the finished Strafe_Left_01 (0.49 of the
generation now: 0.293 m per loop, 0.20 m/s), `--foot-clear 0` (nothing to lift), the loop re-closed,
Strafe_Right_01 re-mirrored; steps ≤ 11°, boots as before. ⚠ An `--even-advance` retime was tried on it and
dropped: a strafe PAUSES between side-steps (hips advance 0 for five frames), the retime compressed that pause
and the legs stepped 18° on one frame (11° before). Rule: **the advance retime is for gaits whose hips never
stop; a side-step's pause is the motion.**
Then "torso higher, knees not that far apart, like 20 cm closer" (2026-09-26): measured, the knees sat WIDER
than the feet (276–414 mm apart against feet 132–299; the walk's knees sit inside its feet at 194–221) —
bow-legged knee planes from the Kimodo source on top of a deep crouch (hips 0.46–0.52 rig m against the
walks' 0.53–0.56, knees 99–130°). `--torso-drop -0.04` (a 7 cm raise: hips 0.50–0.56; a 9 cm raise put the
spread leg at full reach, knee 177° and a 71° pole flip) and the new **`--knees-in D`** (rig m: each IK knee's
pole aimed at its FK knee moved D/2 toward the body's midline along the hips' lateral axis, the knee taking the
nearest point on its swivel circle; runs after every other leg pass): 0.18 → knees 119–245 mm apart, right
knee ≤ 165°, steps ≤ 11°; Strafe_Right_01 re-mirrored, boots unchanged. Rule: **"knees apart" can be the
knee PLANE, not the stance: compare the knee separation with the feet's before moving any foot.**
Then the user's updated `Strafe_Left_Fix` (chest, head, neck, both feet, both knee poles, torso; Combine) with
"freeze the left foot from frame 32 to 45": baked with **`--keep-poles`** (new: `--pin-foot` neither re-aims
the pinned leg's pole nor runs the repole after the leg passes, so the fix's own pole offsets and the knees-in
swivel survive; with a world-space pole target the knee keeps aiming at it while the foot moves), the left foot
held over 32–45 at frame 45's spot (seam-exact), `--loop --loop-seam 4`, `--mirror-to Strafe_Right_01`. ⚠ The
first bake came out 51 frames: the fix's keys reach frame 51 (beyond the 45-frame strip) and the stack range
follows the widest action — `--frames 1:45` pins it (the pre-fix clips were restored from HEAD's anim file and
the stack rebuilt for the redo). The fix lowers the body 14 mm (hips 0.48–0.55), so `lift 0.008`: the highest
sole at +2 mm, the others ≤ 5 mm under. Knees 149–303 mm apart now (the fix's poles), 113–158°, steps ≤ 11°.
Rule: **a Combine fix keyed beyond the strip's end widens the flatten; give the bake `--frames`.**
Then "lower the arms, they stick out too much; move some frames from the start into the end, the feet snap at
the end" (2026-09-26): measured, the strafe's upper arms sat 10–25° out from vertical (Idle_02 17–23°, the
normal strafe −5..18°). **`--arms-down DEG`** (each FK upper arm turned toward the body about the body's
forward axis through its shoulder, the sign found on the elbow, the forearm and hand riding; IK arms left
alone): 12° → −1..13° / −2..6°, the hands 5 cm closer to the hips. **`--loop-shift K`** (the loop's phase
rotated: the clip starts K frames later, the first K frames go to the end advanced by the travel — the root's
location is armature-space and every other root-level control is its child, so only the root's keys move — the
duplicated closing frame rebuilt from the same rule): 10, so the seam sits inside the double stance where both
feet are planted (wrap steps 1–2° where the old seam had 9°). `--keep-poles`, Strafe_Right_01 re-mirrored,
boots within ±3 mm. Rule: **put a loop's seam where both feet are planted; a seam in a foot's flight or at a
hold's edge reads as a snap however exact its numbers.**
**The melee-in-place take (2026-09-26, experimental: "new recording `melee in place.glb`; replace the slice with
frames 1–40 and the stab with 48–83, feet frozen in place").** `melee_ref_arm.blend`, 104 frames (= 83 ×
1.25, the 24 fps numbers again): slice 1–50, stab 60–104; the right hand attacks (2.1 / 1.4 m/s, the left
calm), the pelvis stays put, so plain transfers with the legs planted and NO `drift root` (in place, root
motion 0.000 m / 0°), `unwind_yaw` + `unwind_ref body`, no `time_scale` (the take's own tempo; the ref5 builds
ran at 0.38–0.45) and no blade pass (the wrist as recorded). Then `anim_nla_bake --pin-foot L,R` on each right
clip (both feet at their frame-1 transforms for the whole clip, 0.0 mm on every frame, knees 128–155°) with
`--mirror-to` the left clip (landmarks within 3.1 mm); all four `hand_edited`, exported with the fit: the
highest sole at 0, the others ≤ 9 mm under. Slice 50 frames (1.63 s; the cut steps the hand 37° on frame 24,
the take's speed), stab 45 (1.47 s). The previous builds live on as `_base`; `time_scale` and
`blade_along_arm` are the knobs if the old tempo or blade line are wanted back.
Then (user: "for one-handed attacks only torso and above bones are used, we don't touch legs and feet poses"),
with the updated `Attack_R_Slice_Fix` (right arm, one torso key; Combine): **`anim_nla_bake --legs-from Idle:1`**
(every LEG control — feet, toes, knee poles, the FK leg chain, heel/spin/tweaks, the leg switches, 28 controls —
taken from Idle's frame 1 on every frame; root, torso, pelvis and everything above stay the clip's, so the IK
legs stand on the idle's stance under the take's hips) on both right clips, the left ones mirrored, all four
exported in place (root motion 0). Rule: **a one-handed attack owns the torso and above; its legs are the
idle's stance.** Reported, not changed: the take's hips sit higher than Idle's, so the left knee reaches
166° (slice) / 171° (stab) over the idle's feet (Idle itself has 135–139°) — a `--torso-drop` of ~0.02 rig m
would keep it bent; and the slice fix extends the right elbow to 178° at the cut with a 43° hand step (the
straight-arm flip risk in Humanoid).

**`Strafe_Right_02` / `Strafe_Left_02`**: three profile-less Kimodo side-steps to the right (`strafe_right_n1..n3`,
kept); n3 (seed 39) for the cleanest cycle (r 0.95; n1 r 0.62 with asymmetric arms, n2's trailing foot dragging
32 cm), knees 136–170°, chest 9–14°. Plain loco retargets along X, the left the retarget's `mirror` of the same
generation (as the original pair was): 40 frames, 1.204 m per loop, 0.93 m/s, `lift 0` (the default floated
the boots 10–16 mm). Skate 67–129 mm per stance — every Kimodo side-step skates; the `--ik-legs --pin-foot
auto` pass is the fix if it shows.

**The `_02` set's hands turned outward (2026-09-29, from the movement showreel: "walk_fwd_02, turn hands so weapons point
outward; run_fwd_02 the same but slightly less; walk_back_02 more than walk_fwd_02; strafe_left/right_02 as walk_fwd_02").**
Measured (`hiltdir.py`-style: the socket's +Y in the body frame, yaw from forward toward that hand's outside): the plain
retargets carried the human's hanging hands with the hilt axis pointing ACROSS the body, −50° on the walk and strafes, −55°
on the run, −80..−100° on the walk back (the Idle_02 fix put it at +15°). Manifest **`wrist_twist`** on the five entries (the
retarget's pass: the FK forearm turned about its own axis every frame, the hand riding), the angles solved by `twistscan.py`-style
search on the built clips (the same rotation simulated on the socket axis until the hilt's mean yaw meets a target; a circular
mean, since the run's swinging left hand wraps through the back): `Walk_Fwd_02 "L:-67,R:63"` (→ +15°), `Walk_Back_02 "L:-126,R:104"` (→ +25°),
`Strafe_Left_02 "L:-73,R:76"` / `Strafe_Right_02 "L:-76,R:73"` (→ +25° after "turn them a bit more"; +15° with ±63/67 first;
the left strafe is the mirror build, so its sides swap). Rebuilt with `anim_batch --force` (reproducible entries, no hand edit).
**`Run_Fwd_02` is `hand_edited`** (the user's fix on top of the even-advance retime), so the batch refused to regenerate it and
its manifest key did nothing: the bake tool got the same pass, **`anim_nla_bake --wrist-twist "L:-46,R:35"`** (the FK forearm
turned about its own axis on every frame, IK arms skipped), run on the baked action (→ ~+10°, the smaller turn), then
`--export-only --force`. Rule: **"weapons point outward" is the hilt axis's yaw in the body frame; measure it per clip and solve the twist
on the built clip instead of guessing a round number.**

**Strafe_Left_Fix re-baked (2026-09-29, "updated strafe_left_fix, bake it to both strafe_left_01 and right_01").** `anim_nla_bake
--result Strafe_Left_01 --frames 1:45 --keep-poles --loop --loop-seam 4 --mirror-to Strafe_Right_01` (flat = stack 0.00 mm, seam
0.0 mm, the mirror within 2.6 mm; the fix moved the landmarks ≤ 12 mm), both exported with `--export-only --force`. **The grounding
line then read the Necromancer 103 mm under the floor on both strafes** (the other five within 3 mm) where the previous export had it
at −0.3 mm — and it is NOT the fix. Traced: the hips path is the same in both engines (a 0.87 m dip mid-clip in the Blender clip and
in Unity), the rest poses agree, but the ROBE differs: in `SkeletonNecromancer/prod.blend` since commit `f5ff22f` (09-27, "update
skeleton necromancer hood and robe rig") **88 hem vertices between the floor and mid-thigh (0.02–0.50 rig m) are weighted 100 % to
`DEF-spine` (the hips)** — in the previous robe (and in the anim file's `Ref_SkeletonNecromancer` copy, which still IS the 09-20 robe)
they were spread over the thighs and shins. A hem point rigid on the hips 0.95 m below the pivot swings 0.4 m for a 27° hips pitch, so
every crouching or pitched pose puts that flap through the floor: 103 mm on the `_01` strafes, 29 mm on Run_Fwd_02, 37 mm on Idle_02,
71 mm on AOE_Cast (the "robe class of dip" of the last two days is this rig change, not the clips). Blender never showed it because
the anim file's reference robe is the OLD skin — which also means the retarget's floor pass measures the old robe; refreshing the
reference (`anim_file_build.py`) would make every grounding pass lift clips by that flap. Decision left to the user: keep the
hips-weighted flap and accept the clipping (their stated preference on the deaths), or restore leg weights on those 88 vertices in
`prod.blend` and re-export the robe module. Rule: **when one character's floor number jumps on a clip that did not change, diff that
character's WEIGHTS against the previous commit before touching the clip.**

**Run_Fwd redone and renamed `Run_Fwd_01`; the `_01` strafes redone — REVERTED the same hour (user: "that's awful, just revert the strafe animations and run_fwd, the rename we keep"): the committed clips are back under the new run name, the candidates stay as GLBs, the paragraph is the record of what the generator gave (2026-09-29, "redo run_fwd with kimodo, rename it to
run_fwd_01 after it's done; also redo the strafe_01, use a similar travel distance in the prompt").** Candidates with the skeleton
profile, retargeted as temporary actions and scored (`locoeval.py`-style: loop length, root travel, knee range, stance skate, largest
leg-bone step, chest and head pitch, hilt yaw): of five runs (`run_fwd_c1..c5`, GLBs kept) **only c2 (seed 52) ran** — 1.556 m per
loop, knees 93–162°, chest 18–28°, a hunched stiff jog; c1 and c4 shuffled at 0.4–0.6 m/s with the knees near straight and c3 and
c5 stood still (Kimodo with the stiff-undead profile drops the run in 4 of 5 seeds: generate several). Built as `Run_Fwd_01` at
`time_scale 1.3` (1.43 m/s; 1.80 as generated, a human jog; the knob), `lift 0.005`; the old `Run_Fwd` (seed 9, the even-advance
retime) removed from the anim file, manifest, build state and export, `Run_Fwd_Fix` kept; the showcase, the showreel's movement
set and the controller renamed / rebuilt, the demo scene rebuilt. Strafes: three small-step prompts (`strafe_right_c1..c3`); **c2
(seed 44, "tiny shuffling steps, barely moving")** travels 0.390 m per loop at `time_scale 1.3` (0.24 m/s, the finished old clip did
0.293 after two 30 % stride cuts of a 0.60 m generation), knees 119–149°, steps ≤ 8°; c1 travelled 0.94 m with a 670 mm stance skate,
c3 0.48 m on a weak cycle. Both `_01` strafes are FRESH plain retargets of it (the left the mirror), `lift 0.001`: none of the earlier
passes (stride, knees-in, torso raise, arms-down, loop-shift, the user's Strafe_Left_Fix) carry over; the head bows 34–47° and the
chest 33–42° as generated. The Necromancer's robe reads 77 / 102 mm under on these (the hips-weighted hem, above). ⚠ The first build
was killed by Claude Code for low system memory after the run's retarget had saved; the file was intact (a save writes a temp file
and renames) and the batch was re-run on request. Rule: **a Kimodo run with the undead profile needs several seeds; score the
travel and the knee range before looking at anything else.**

**Combat idles (2026-09-29, "we are missing idle_combat animations for each weapon type: two 1-handed/shield, 2-handed, staff, bow;
the transition from idle_01 to a right-hand attack is big and happens in a short time; body pose from idle_01, hands placement from
the first attack of that weapon type").** Four 8 s loops, each Idle_01's flattened clip (the sway, legs, head) with the ARM controls of
one source frame held on every frame — bake tool **`--arms-from ACTION:FRAME[:LR]`** (shoulders, the FK and IK arm chains, tweaks,
switches, hands, fingers; an arm on IK on the source frame is converted to its FK equivalent there first, as `fk_arms` does, so the
copied arm is a local pose that rides the swaying torso instead of a hand fixed in space): `Idle_1H_Combat` ← `Attack_R_Slice:1`
(the melee take's ready stance: right hand 0.97 m, elbow 96°, the left hand chest-high — the shield arm), `Idle_2H_Combat` ←
`Attack_2H_01:1` (the two-handed hold; the gated left hand was IK, converted; `grip_hands L`), `Idle_Staff_Combat` ← `Cast_Staff_01:1`
(both hands on the staff; `grip_hands L`), `Idle_Bow_Combat` ← `Shoot_01:12` (the raise complete, the arrow nocked, not drawn —
Shoot_01's frame 1 IS Idle_Bow's lowered pose, so the shot still starts lowered; a shot cut from frame 12 would pair with this idle).
Manifest entries `hand_edited` with Idle_01's lift, in the demo's Idle section. Measured (hand distance, idle frame 1 → the
attack's first frame, engine cm): 1H 54 / 41 (Idle_01) → 13 / 11 (the rest is Idle_01's 11° chest against the take's 23°: the arms are
local); staff 29 / 16 (Idle_Staff) → 8 / 6; bow 60 / 56 (Idle_Bow → Shoot_01 frame 12) → 28 / 26, but Shoot_01 still STARTS on
Idle_Bow's lowered pose, so from the bow combat idle the shot first drops the arms — it needs a shot cut from frame 12 to pair with;
**two-hander: `Idle_TwoHanded` → `Attack_2H_01` is already 1 cm (the same take), the new `Idle_2H_Combat` is 14 / 12 — the existing
two-handed idle is the better pre-attack idle there.** **Second round (same day, "we only keep idle_1h_combat, the only different animation when the skeleton enters the combat state;
other weapon types use their respective idles; in idle_1h_combat the left arm stance is not as ready for left-hand attacks as the
right"):** `Idle_2H_Combat`, `Idle_Staff_Combat`, `Idle_Bow_Combat` removed (actions, entries, exports, states, buttons);
`Idle_1H_Combat` rebuilt with **`--arms-from "Attack_R_Slice:1:R,Attack_L_Slice:1:L"`** (the pass takes one spec per arm): each arm in
its OWN attack's first-frame stance, both hands low and ready — 11 cm from the right slice's right hand, 10 cm from the left slice's
left hand (the other arm then sits ~30 cm from that take's raised non-attacking arm: the recorded stance is asymmetric, so a
symmetric ready idle cannot match both arms of one take). The showreel's attacks stage plays the Knight's and the Assassin's steps
on it, and the demo's "Right arm" / "Left arm" sections return to it after an attack (`idlePreference` `Idle_1H_Combat`, then
`Idle_01`; the user saw both characters drop to Idle_01 between attacks). The "Specials" and "Reactions" sections return to the LAST idle
loop that played on Base (`returnToLastIdle`; taunts, rally, cutthroat, summon and AOE cast had dropped to Idle_01 too). Rule: **a combat idle is the base idle's body with
the attack's own first-frame arms; then the engine's 0.15 s crossfade has only the attack's motion to cover.**

**The recorded magic and specials set (2026-09-25, user: two mannequin-app files, `P:\magic attacks.glb`
and `P:	aunts.glb`, split by frame ranges).** `External Anims/Kimodo/magic_ref_mocap.glb` →
`magic_ref_arm.blend` (200 frames) and `taunts_ref_mocap.glb` → `taunts_ref_arm.blend` (666 frames) through
`glb_nodes_to_armature.py` (which takes a `DST.glb` argument and writes `DST.glb.blend` + `DST.glb.glb`; rename
after). **The user's frame numbers are 24 fps again**: both files' lengths are the user's last frame × 1.25
exactly (160 → 200, 533 → 666), and a per-10-frame hand-speed scan of each source (`srcspeed.py`-style) put
every clip's motion inside its ×1.25 range with the pose holds where the user's boundaries fall. Ten clips,
all plain transfers like the arm attacks (`rename ue5`, `src_ext blend`, `mode action`, `plant_feet`,
`drift root`, `unwind_yaw` + `unwind_ref body`, `lift 0.004`, `ground_fit`): `Cast_Wand_01` (1–68),
`Cast_Wand_02` (69–123), `Cast_Staff_01` (124–200); `Taunt_01` (1–83), `Taunt_02` (86–159), `Taunt_03`
(160–241), `Rally` (253–344), `Cutthroat` (346–439), `Summon` (441–554), `AOE_Cast` (555–666; the user
wrote "cast_aoe", the name is kept because the demo and the controller reference it). `Cast_Staff_02` and
the Kimodo `Taunt` are retired (export, meta, manifest entry, build state, demo lists; the actions stay in
the anim file), the layer tags as before (wand casts and Rally `upper`, the rest `full`). Root motion within
a few cm with the yaw unwound to ±1°, the highest model's sole on the floor, the others sinking ≤ 13 mm
after the fit. Per-bone scan (`stepscan.py`: worst per-frame step of every arm, leg and spine bone, knee and
elbow ranges): the taunts, Rally and Cutthroat under 11° per frame, the wand casts' flicks 22–26° on the
hand (the motion), Summon 18°. Two things needed fixing: **AOE_Cast started on a tracker glitch** (the
source's right hand jumps 14 cm / 31° in ONE frame at source 555–557, the tail of the summon's arm drop;
the user's start frame sat exactly on it): `src_begin 559`, four frames later, once the hand has settled
(worst step 28° → 18°). Rule kept: **scan the source's per-frame steps at a requested cut before trusting
it.** And **the staff cast's gate was on the wrong side**: the gate range is written for a sword (the second
hand BELOW the grip, −Y, toward the pommel), but the staff's long end lies on the +Y side and the performer's
left hand rides there, 0.3–0.6 m from the right hand (the source's hand distance, measured); with
`gate "0.05,0.28"` the projection was negative on every frame, clamped to the 5 cm minimum, and the pull
dragged the right arm to the chest (12 cm from the left shoulder, 35–50 % of its reach) with the left elbow
locked at 145–180° — the built clip looked nothing like the capture while every number of the transfer was
"fine". The gate clamps a SIGNED projection, so **`gate "-0.35,-0.15"`** (negative = the +Y side) keeps the
left hand 0.15–0.35 rig m up the shaft from the right hand where the capture has it; then
`anim_nla_bake --arm-pole-fk R --fk-arm R` lands the gate pull's right arm back on FK with the elbow on the
capture's plane (the 40° forearm step at the pull's one FK frame is gone); the rig's shorter reach still
locked the left elbow at 180° with a 65° upper-arm flip on frames 39–49 (the capture's left arm is at 75 %
there), so a second pass `--arm-pole-fk L --grip-follow L:@0.15 --grip-pull --grip-reach 0.96 --fk-arm R`
holds the left slot 0.15 rig m up the shaft from the right slot (0.0 mm on every frame) and pulls the right
hand in wherever the left would pass 96 % of its reach: left elbow 51–147°, worst step 25° inside the raise,
`hand_edited`. Verified in play mode on the Mage: all ten buttons, the one-shots on Base, Cast_Wand_01
clicked during Walk_Fwd goes to the UpperBody layer with the legs walking. Rule: **a two-handed
prop's second hand goes where the PROP extends, which for a staff is the "blade" side; check the capture's hand
spacing before choosing the gate's sign.** Also bitten: the bake tool had LOST six functions (`_hand_from_sock`,
`arm_pole_fk`, `fk_arms`, `grip_follow`, `shaft_hand`, `torso_counter_yaw`, plus the `HAND_FROM_SOCK` init)
in the pin-foot rewrite of commit `b4824c5` — the option parsing and the call sites survived, so the tool
parsed and only failed at the call (`NameError`, before its `--save`); restored from `f4141e2`. Rule:
**after any splice edit of a tool, diff its `def` list against the previous commit.**

**Empty-hand finger idles (2026-09-25, user: "from Grip action frame 2, use the left hand pose for the left and
mirrored for the right, as the default hand pose when the model holds nothing; two actions, one per hand, with
slight finger movement so they don't look static").** `Grip` frame 1 is the fist both hands take on a held
item; its frame 2 carries the user's RELAXED left hand (fingertips 63–76 mm from the wrist against the fist's
51–59; the right hand is the fist on both frames). `tools/anim_hand_idle.py -- --save` writes `Hand_Idle_L` /
`Hand_Idle_R` (240 frames, 8 s loops): that hand's 26 finger controls keyed on every frame with the frame-2
pose plus a slow sine per finger master (integer cycles, phases spread: index and middle 1 cycle, ring and
pinky 2, thumb 1; `--amp` degrees of curl), every other control at rest. The right hand is the Paste-X-Flipped
mirror (location x, quaternion y/z, Euler y/z negated): right fingertips within 0.0 mm of the X-mirrored left
ones, seams 0.1 mm. Exported like any clip (`export_fbx --clip`), imported as looping Humanoid clips, NOT
Base states: `AC_Skeleton` has two more layers, **`LeftFingers` / `RightFingers`** (Override, weight 0, masks
`AM_LeftFingers` / `AM_RightFingers`: that hand's humanoid finger part + the transform paths under the hand
bone), one looping state each. **`SkeletonWeapon.ApplyFingerLayers()`** sets each layer's weight per hand
on Start, Equip and Clear: 1 while the hand holds nothing, 0 while it holds an item (the Grip fist then goes
on in LateUpdate as before). So on every clip an empty hand shows the relaxed sway and a full hand the fist;
a clip's own recorded fingers are only seen if a buyer turns the layers off. Rule: the two hand poses live
in the anim file's `Grip` action (frame 1 fist, frame 2 relaxed); re-run the tool and the prefab builder
after editing it. **The second hand of a two-hander (2026-09-27, user: "idle_twohanded, attack_2h_01 and 02:
the left hand doesn't use the grip pose, most likely due to the default hand pose change").** Right: the
left hand rides the shaft but holds no item, so the finger layer played the relaxed sway over the clip's
baked fist. Manifest **`grip_hands: "L"`** (Idle_TwoHanded, Attack_2H_01/02, Cast_Staff_01) → the controller
builder puts a **`SkeletonGripState`** (a `StateMachineBehaviour`, `Demo/Scripts/`) on those states, on every
layer they live on. It re-asserts the hold EVERY frame its state is evaluated (`OnStateEnter` + `OnStateUpdate`
→ `SkeletonWeapon.ClipHoldThisFrame(hand)`, forgotten in `LateUpdate`): the first version used
OnStateEnter / OnStateExit with a bool and Unity fired the outgoing Attack_2H_01's exit AFTER the incoming
Idle_TwoHanded's enter, which opened the hand on the return. A clip-held hand counts as holding for the finger
layer AND gets `ApplyGrip`, so it closes exactly like a hand holding an item (measured on the Knight: left
middle tip to wrist 113 mm with the shield in hand and 113 mm on Idle_TwoHanded's clip-hold, 132 relaxed;
the right fist reads 98: the user's Grip fist differs per hand, not a bug). The
finger layer weights are TARGETS faded in `LateUpdate` over `fingerFade` (0.15 s, the demo's crossfade) and
`ApplyGrip` slerps the fist in by 1 − the layer's weight, so equipping and a clip-hold's start and end close
or open the hand over the crossfade instead of snapping. Per-clip, not per-loadout, because the staff is held
one-handed in Idle_Staff and two-handed in Cast_Staff_01.

**"walk_back, run_fwd and run_fwd_02 have looping issues" (2026-09-25).** Every seam was POSITION-exact
(last frame = first + travel to 0.0 mm on feet and hips, no rotation step at the wrap), so the defect was
velocity: the hips' advance per frame along the travel collapsed at the seam — Run_Fwd_02 55 mm on the frame
before the wrap, then 17 (the retarget's loop-closing crossfade drags the hips toward the partner frame),
Run_Fwd 31 → 15, and Walk_Back lurched 14 mm then stalled to 0 over its last four frames (my `--loop-seam`
crossfade, which converges on a fixed pose and kills the velocity). Under root motion Unity moves the
character by the hips, so a speed dip at the seam is a hitch every cycle, and no position check sees it.
**`anim_nla_bake --even-advance K`**: the per-frame advance profile is smoothed circularly (K passes of
[1,2,1], the wrap a neighbour of the first frame), scaled to keep the travel, and the clip is RETIMED by
resampling at fractional frames so the hips follow the smoothed profile (same frame count, same travel; the
Root re-keyed linear so Unreal's root motion stays clean, its children kept in place). K 40 on the runs
(Run_Fwd_02 30–39 mm per frame, Run_Fwd 19–24: a run's root speed is near-constant anyway), K 15 on
Walk_Back (its own slow double-support phase kept, the seam 5 mm against 6–7 beside it); frames moved by
up to 0.8 frames in time on the runs and 2.9 on the walk (the stall). Lengths and travel unchanged, the speed
table holds. Rule: **check a loop's seam in VELOCITY (the advance profile across the wrap), not only in
position; and a pose crossfade at the seam needs the retime after it.** The strafes carry the same
`--loop-seam` crossfade (their last steps 7.6 / 6.4 / 2.2°) and were not reported; the same pass applies.

**"Both strafe animations float above the ground in Unity, in Blender they look correct" (2026-09-25).**
Measured per frame in Unity: every boot 20–27 mm up through the whole loop and under the floor only on frame
38. The constant `lift 0.025` of 2026-09-24 had been fitted to that one frame — the swinging right foot pitches
toe-down to 39° while its ankle lifts barely 2 cm, so the boot's TOE dragged 14 mm through the floor in
Blender too (a per-frame boot trace shows it; a stance-frame glance does not), and lifting the clip until the
toe cleared floated the stance by the same amount. **`anim_nla_bake --foot-clear Z`**: per frame and foot, the
lowest vertex of all six characters' `Boot_<side>` meshes is measured (the `Ref_*` collections un-excluded
for it and restored) and an IK foot with its toe is raised by the deficit below Z, the lift running-maxed over
±1 frame and smoothed (wrapping with `--loop`), the knee pole re-aimed on the FK plane: the right foot raised
by up to 17 mm through its swing, the left by 2 mm where the Archer's boot sat under. Strafe_Right re-mirrored
from the result (landmarks within 2.7 mm), `lift 0.002`: the highest model's sole at 0 on its lowest frame,
the loop within 4 mm of the floor for it, the others sinking ≤ 7 mm. Rule: **a constant lift is fitted to the
STANCE; a swing-foot dip is fixed in the pose, never by lifting the clip** — and check the boots per frame,
the sixth-frame sampler and a stance-frame glance both missed this.

**Summon fix (2026-09-25, "added Summon_Fix, bake it; also bring the torso down like 8 cm").** The fix is one
held key on each IK foot in REPLACE mode (an absolute foot placement over the strip; the bake evaluates the
stack as-is, so Replace and Combine fixes both work). **`anim_nla_bake --torso-drop D`** (rig m; 0.0444 =
8 cm engine) then lowers the torso control on every frame: the IK feet stay planted, the knees bend more
(115–152° → 105–129°), the FK arms ride with the torso, the poles re-aimed on the FK plane (knee steps ≤ 7 mm).
The drop is constant, ends included: the demo's crossfade from the idle dips the body 8 cm on the way in and
lifts it on the way out; an eased drop is a small change if that reads wrong. After the fit the Warrior's sole
is the highest (0), the Knight sinks 14 mm at its lowest frame and the Necromancer's robe 29 mm (the lower
hips hang the hem lower: the robe class of dip).

**Rally fix (2026-09-25, "added Rally_Fix, bake it").** One held key on every leg control AND the root, in
REPLACE mode: baked as posed (flat = stack to 0.00 mm, `Rally_base` kept). Two things reported, not changed:
the held root key replaces the take's 4 cm root travel with a constant (root motion 0.4 cm now: in Replace
mode a root key HOLDS the root, the Combine warning does not apply); and the right foot's placement locks
that knee at 174–177° on frames 78–84 (reach 1.000 of the leg, 165° on frame 1; before the fix 121–149°) —
the straight-leg flip risk in Humanoid; a torso drop or a foot a few cm closer to the hips fixes it.

**AOE_Cast fixes (2026-09-25, "added AOE_Cast_Fix_01 and 02, bake them (fix 1 first); from frame 60 the left
hand should hold the weapon handle 15 cm higher").** The stack was the strip, a 2-frame Replace strip of
Fix_01 (every leg control + the root, held) and Fix_02 active in Combine (hand_fk.R, torso, a knee pole): one
flatten evaluates them in that order (flat = stack to 0.00 mm, `AOE_Cast_base` kept). The left hand: measured
after the bake, the slam brings both hands down side by side on the staff (the left slot ~+0.03 rig m along
the right hand's hilt axis and 6–13 cm off it, the staff vertical with the hilt axis UP through frames 74–98),
so "15 cm higher" = the left slot ON the shaft 0.113 rig m (20 cm) above the right slot. **`--grip-follow`
now takes a frame range, `SIDE:@D:from[:to]`** (and `SIDE:ACTION:FRAME:from[:to]`), the relation eased in
from the clip's own over `--grip-ease` frames (6) so the hand slides up instead of jumping, and an arm that
was FK on those frames gets its IK elbow pole on the FK elbow's plane before the hand goes on IK (the frames
before the range stay FK). `L:@0.113:60:108 --grip-pull --grip-reach 0.96 --fk-arm R`: from frame 60 the left
slot is on the shaft to 0.0 mm, reach 0.61–0.82 (no pull needed), the ease frames step 22–25° on the left
forearm/hand (the slide, a longer `--grip-ease` softens it). Root: Fix_01's held root key in Replace holds
the Root, as on Rally.

**`aoe cast shoot.glb` (2026-09-25, "replace cast_aoe: frames 10–121, replace shoot_01: frames 130–177").** The
mannequin app again (224 frames, the user's numbers ×1.25: 13–151 and 163–221), `aoe_shoot_ref_arm.blend`.
`AOE_Cast` is a plain transfer as before (139 frames, 4.6 s: both hands up to 1.6 m, a slam with a deep crouch,
knees to 68°); the taunts.glb take with its two fixes and the left-hand grip-follow is superseded (`AOE_Cast_base`
holds the old baked clip). `Shoot_01` from the same take (59 frames, 1.9 s; the LEFT hand holds the bow, 0.54 m
out, the RIGHT draws to the cheek, 0.27 m from the head: no mirror) replaces the video-mocap build and its
anchor / bow-square / head-aim / pose-ref passes, but not the aim: this performer also shoots 65–70° LEFT of his
hips' facing, so `aim_forward L` + `aim_body 0.0` (the pelvis held on the heading, the turn a spine twist) with
`aim_line shot` and no offset — the draw hand anchors at the cheek here, so the ARROW line is what reads, and it
is aimed dead ahead (−1..−3° through the draw; arrow along the draw fingers to 2–3°). Two things the plain
one-shot needed, both new: **`aim_fade N`** (`--aim-fade`: the aim turn fades in over the first N output
frames and out over the last N without a blend_from/blend_to — the nearest raised value had held a 50° twist
through the standing ends; `blend_from Idle_Bow` faded it too but the idle's IK legs crossfading into the
take's planted legs snapped the shins 33° on frames 2–3 and locked the knees at 174°), and **`heading first`**
(`--heading first`: the used RANGE's first 5 frames' hips yaw is zeroed instead of the file's mean — the
performer starts facing 47° left of his shooting mean and returns there, so with `auto` the standing ends turned
47–61° away from the idle). ⚠ Found on the way: the heading block runs BEFORE the `src_begin` trim, so `auto` has
always been the WHOLE file's mean yaw, not the clip range's (every clip cut from a multi-clip recording carries
that file-wide offset; left as is, a rebuild would change them all). Result: hips 0° on every frame, chest 0° at
both ends and −56° at the draw, root motion in place (2 cm, 0.6°), knees 109–136°, boots on the floor (the
Knight sinks 13 mm at its lowest frame). Kept as captured: the bow limbs sit 116–117° from the arrow at the draw
(a 26° cant; `bow_square` would square it).
**WRONG, and corrected the same evening (user, with the bow and arrow attached in Blender: "in my Blender the
shoot direction is correct, in the same direction as the feet; you imported the animation incorrectly, the
model shoots diagonally compared to the feet").** Measured in the SOURCE: the feet stand at +38° all along and
the shot at full draw goes +51°, along the FRONT foot and 13° left of the feet's mean — the archer shoots
where his feet point, the hips 40–50° side-on to it. The aim build had held the hips on the heading and
twisted the spine until the arrow was at 0° in the WORLD while the feet pointed +12° (front foot +24°): 25°
off the front foot, the diagonal. The aim passes are for the video take whose stance was lost; on a good
capture they break the feet/shot relation. Now: NO aim passes, **`heading feet`** (`--heading feet`, new:
the mean yaw of both feet's ankle→toe direction over the used range, against the bind's, is zeroed — the
feet are the facing of an archer, as they are of Idle_02) and the take as recorded: feet mean −1..+11°, the
front foot +23° and the shot +19° at the draw, hips −34° side-on there, back to −8° at the ends; bone
directions within 2° of the source on every arm bone (`retarget_compare`). Rule: **when the capture is good,
the shot goes where the recorded feet point; aim only what a capture lost.** Also on the way: a batch build
of the SAME entry came out with every arm bone 60–74° off the source (feet +33°, shot −20°) right after
`anim_weapon_ref.py --check Shoot_01:26 --save` had left that action active and posed in the file; the
identical retarget run again afterwards (and on copies, including a replay of that exact sequence) matched
the source within 2° — not reproduced, cause unknown. Rule: **after a retarget "looks wrong", run
`retarget_compare` before touching the manifest; and rebuild once before diagnosing, a bad build can be a
transient file state.** (`anim_weapon_ref --check` leaves the checked action on an NLA track and active;
cleared by hand this time.)

**AOE_Cast fixes on the new take (2026-09-25, "updated AOE_Cast_Fix_01 and 02, this time bake 02 first, then
01").** The order matters when the fixes share controls: Fix_02 is a held ABSOLUTE foot placement (both feet +
the left knee pole, Replace) and Fix_01 a held OFFSET on nearly every control (chest, head, hips, jaw, both arms,
feet, fingers; Combine), so the feet must be placed before the offsets ride on them. The user's NLA had them the
other way round (02 active over a 01 strip: the Replace would have overridden 01's foot offsets), so two stacks
were built headlessly (`setup_stack2.py --base --fix --mode`: the clip as a Replace strip + one fix active in
its mode, saved) and flattened in turn; flat = stack to 0.00 mm both times, `AOE_Cast_base` untouched. Rule:
**when a Replace fix and a Combine fix touch the same controls, bake the Replace one first.**

**AOE_Cast facing and left hand (2026-09-25, "the animation direction the same as the feet direction in
idle_02; the left hand follows the handle after frame 100 to 125").** Measured: Idle_02's feet splay ±12° about
0 with the hips at 0; the AOE take's feet pointed −17° (right; L +5°, R −38°) with the hips −28..−41° and the
chest to −60°. **`anim_nla_bake --yaw-clip DEG`** turns the whole clip about the vertical through the root's
first-frame spot — every root-level control (torso, feet, toes, knee poles, IK hands, elbow poles) and the
root's path, the Root's ORIENTATION left at identity so the export's Root stays as in every other clip: +17°
puts the feet's mean yaw at 0 (L +22°, R −21°); the performer's own turn relative to his feet stays (hips
−6..−24°, chest to −43°). **`--shaft-hand` takes a frame range**, `SIDE:OFF:from:to`, eased in and out over
`--grip-ease` frames, and puts an FK arm on IK there with its elbow pole on the FK elbow's plane (as
`--grip-follow` does): `L:0:100:125` seats the left socket on the staff's axis at its own height along the
shaft (0.13 → 0.26 rig m as the staff tilts) to 0.0 mm through the middle of the range, 3–9 cm off at the
eased edges, the arm FK again outside it. Left reach peaks at 0.94 (frame 116), the slam's left forearm step
28°. Rule: **"direction" of a clip = the feet's mean yaw against the idle it plays over; turn the root-level
controls, never the Root.**

**Multi-frame pose references** (built for the swing, kept): `pose_ref` takes several
`ACTION:frame@at`; the first ramps in over `pose_ref_in` frames, the deltas interpolate between
refs, and `pose_ref_tail return` goes from the last ref's pose straight to the blend-to pose by
the last frame ("continue to end frame from it"); `pose_ref_mirror` swaps .L/.R and X-flips the
refs for a mirrored clip (Paste-X-Flipped rule: location x and quaternion y, z negated; verified
to 0.5 mm on the hands). ⚠ Reference poses only exist for the tools once the user has SAVED the
.blend: two refs copied from an unsaved session came out identical to the generated frames
(0 controls differed), and every headless `--save` overwrites the file under an open session, so
reload before posing. ⚠ A Unity check that re-equips a weapon per frame in edit mode must
`DestroyImmediate` the old one: `Clear()` defers, the stale instances pile up and a render shows a
"floating" sword (the socket was 38 mm from the hand on every frame, as at rest). `Block_L_Idle` is a
Kimodo "shield raised" loop (idle mode, 6 s) whose left arm came back hanging — Kimodo has
no props — so `arm_pose shield_block` pins the left fist chest-high on IK, knuckles forward,
hilt axis DOWN (the hand-held shield's plate top points to the wrist, so down = upright, face
forward); verified with the round shield on the Knight. All five: in place on all six models,
lowest vertex +4..+17 mm. Attack_2H_01/02 were rebuilt with the gate (§"Two-handed grips"):
the left hand rides the handle 0.03..0.10 rig m below the right, 0..10 mm off the shaft on
every frame (it was up to 100–217 mm off with a fixed distance once the reach was checked:
the capture's right hand holds the weapon 0.42 rig m from the left shoulder, the arm is 0.32,
so the gate takes the gated point nearest the shoulder and, if that is still short, pulls the
RIGHT hand in by the shortfall on IK — both hands stay on the shaft and the arc shortens a
little).

What it changes on the authoring side:

1. **Attack and cast clips are in place** — the root never moves. Locomotion carries
   the travel; lunges come from the base layer or gameplay.
2. **Author upper-body clips over `Walk_Fwd` / `Run_Fwd`** in the NLA, not over idle,
   or the torso lean fights the legs.
3. **Additive clips (twitches, aim offset) are deltas from their own frame 0**; set the
   additive reference pose to that frame in both engines. Three or four twitch loops
   of different lengths, random start offset and weight per instance.
4. The seven-bone spine chain gives the mask a clean cut; `Hips` + `Spine` stay with
   locomotion, `Spine1` upward goes to the upper body.
5. The additive layer can drive `Jaw` even under third-party humanoid clips that leave
   it at rest.

### Motion source — Kimodo text-to-motion, retargeted (first used 2026-09-19)

Clips start as a text prompt to NVIDIA's Kimodo (SOMA-RP-v1.1) running as the
`kimodo.cpp` port on the LAN laptop `DESKTOP-PQNPNNB` (details in the creatures pack
memory note `kimodo-machine`): `tools/kimodo_gen.ps1 -Prompt "..." -Name idle_s42
[-Frames 180 -Seed 42]` → `External Anims/Kimodo/<Name>.glb` (30-joint SOMA human,
Mixamo-style names, T-pose bind, 30 fps; ~2 min per 90 frames). The driver ships the
job as a `.ps1` over scp and runs it with `-File`: the remote login shell is cmd.exe
and an inline command loses its quotes (the prompt arrived as a comma-split array).
A skeleton body description is prepended to steer weight and stiffness; the output
skeleton is always human.

`tools/glb_retarget.py -- --glb ... --name Idle --loop 120 --blend 30 --src-start 30
--save` puts it on the rig in the anim file: world-rotation deltas from the GLB's
bind pose onto the FK controls, a per-bone rest correction on the arms only, hips
translation scaled by the hip-height ratio onto `torso`, arms on FK (`IK_FK` keyed 1),
**legs NOT copied** — they stay on IK with the feet at rest, because copying a human's
FK legs onto other proportions is what skated the creatures' feet. The loop is closed
by crossfading the last `blend` frames into the source frames before `src-start`;
frame `loop+1` equals frame 1 (0.0000° seam). Kimodo's idle is subtle (hips ±2 cm,
arms a few degrees); that reads right for undead standing still, and the twitches
carry the life.

⚠ `scene.frame_set` re-applies the action being written: set the frame BEFORE posing,
or every key repeats the previous frame (the first build produced a 121-frame still).

**Idle set (2026-09-19, by request: "too fast for a skeleton, not just speed").**
`Idle` = `idle_s42` at `--time-scale 2.0 --smooth 2` (8 s loop); `Idle_02` = `idle_slow_c`
(exhausted heavy sway) and `Idle_03` = `idle_slow_b` (slouched slow look-around), both
at `--time-scale 3.0 --smooth 3` (12 s loops). The stretch is slerp resampling, the
smoothing is N passes of a [1,2,1] temporal low-pass that removes the human's quick
corrections, which is what makes it read heavier rather than merely slower. A prompt
saying "completely still" (`idle_slow_a`) came back frozen (3 mm of hip travel in
10 s) and is not used. Measured mean angular speed of the head, deg/s: old Idle 5.8,
new Idle 3.8, Idle_02 7.7, Idle_03 8.1 (these two carry real motion at a slow pace).
**Fingers**: Kimodo's skeleton has none, so `glb_retarget.py` gives every finger master
a constant curl plus its own slow sine (1-2 cycles per loop, `--finger-life`).

⚠ **IK STRETCH MUST BE OFF** (`tools/rig_lib_no_stretch.py`, now the library state, and
re-asserted at export). Rigify leaves `ik_stretch = 0.1` on the IK chain bones: a pinned
foot under a lowered pelvis was reached by SHRINKING the leg 3 % instead of bending the
knee (the upright idle stretched it 2 %). Blender showed the feet on the floor; Unity's
Humanoid keeps rigid bone lengths and put the same rotations 2-3 cm under it, while the
same clip played as Generic was exact — that comparison is the diagnostic. A pose-bone
`ik_stretch` set on the anim file's library override is NOT saved with the override;
it has to be in the library.

⚠ **Rig-only clip files carry the CURRENT POSE as the skeleton.** Blender's FBX
exporter writes bone nodes from the pose, and a bind pose only exists with a skinned
mesh. Re-imported, Idle's thigh read 0.3816 m and Idle_02's 0.3673 m from one rig
(model: 0.3740). `export_clip` now strips every baked bone translation/scale except
Root and Hips (Humanoid ignores them anyway) and parks the scene on a rest-keyed frame
before the take (`park_on_rest`), so the file's skeleton is the model's.

**Grounding**: every clip's `Root` is lifted by `CLIP_LIFT = 0.015` m at export. Boot
soles sit 4-8 mm below the bare foot and Humanoid playback dips the feet a few mm; a
lift on the prefab's Armature node is ignored while a Humanoid clip plays (13.6 mm
moved the mesh 2 mm). Measured with `tools/unity/ground_clip.py` (lowest baked vertex
per model per clip, forced reimport): all six models, three idles, +4.1 .. +10.8 mm.
Foot IK on the states made things WORSE (goals ~13 mm below the FK feet) and root Y
"based on feet" dropped the character a metre; neither is used. Root Y is always baked
into the pose; idles/attacks/twitches bake XZ and rotation too (`verify_clip.py
--in-place 1`), locomotion will not.

Twitches are not Kimodo: `tools/anim_twitch.py` authors them procedurally (random
quick jerks on `head`, a third on `neck`, opens on `lowerjaw` whose open direction is
measured — on this rig +X about the jaw control LIFTS the chin, so open is −X). Frame
1 and the last frame are rest, so each clip is its own additive reference (Unity:
`hasAdditiveReferencePose`, frame 0). `tools/anim_preview.py` renders a Workbench
contact sheet of any action for review.

Reference meshes in the anim file must be bound to `RIG-Meta-Rig`, not `Meta-Rig`:
both are overrides, and a refresh once picked the metarig and froze every mesh.

⚠ **THE RIG'S 109 DRIVERS ARE PART OF THE RIG.** The first library build called
`animation_data_clear()` to drop a stray action and removed every Rigify driver with
it: the IK/FK switches, so each ORG bone followed the IK copy at full influence no
matter what `IK_FK` said, and every FK control posed nothing. The retargeted Idle
therefore showed the untouched IK arms (32–35° from vertical) instead of the source's
18–25°, reported as "arms pose is too wide". Rebuilt 2026-09-19 from the Knight as
committed in `f9eacf8` with only the action cleared (`rig_lib_build.py` now asserts
the driver count), sockets re-added, all six files re-synced, the anim file's override
relinked (`anim_file_build.py -- --relink`), clips rebuilt: FK and DEF now agree at
23.0°. Bind pose was never the cause: the retarget corrects for the source's T-pose.

**Face winding vs single-layer cloth** (settled 2026-09-19, the user asked whether
normals were the cause of the one-sided look). Measured by rendering every character
with and without back-face culling from five views and counting changed pixels
(`tools/mesh_normals_fix.py --render`, EEVEE with `use_backface_culling` on the
materials; Workbench's culling flag is viewport-only and renders identically):

- **Assassin: yes, winding.** 697 body faces are wound inward — the lower jaw and part
  of the skull vanish under culling. `recalc_face_normals` fixes it; changed pixels
  8009 → 6057. Fixed copy saved as `SkeletonAssassin/prod_copy.blend` (the only copy
  kept). `export_fbx.fix_normals` applies the same recalc on every export copy.
- **Mage: no.** The 1208 robe faces recalc re-winds are a TWO-LAYER cloth island, so
  flipping them changes nothing visible (22958 vs 22954 pixels). What disappears under
  culling — hood side, sleeve flaps, skirt side panels seen from below — is
  single-layer cloth viewed from its back. No winding fix can help; the armour
  materials render both faces for exactly this. Same for the Necromancer (identical
  counts) and the Knight (3 pixels).
- **Archer: the automatic island vote makes it slightly worse** (6085 → 6204), so the
  vote is not applied anywhere shipped; the export uses the consistency recalc only.
- Rule: a face is a hole in Unity only if it is wound against its neighbours or is a
  single-layer surface seen from behind. Blender's default viewport shows neither;
  check with the Face Orientation overlay or a culled render, not with normals.

### Video mocap through GVHMR (2026-10-02)

**Superseded (2026-10-04):** the video-built attack clips (`Attack_R_Swing_01/07`, `Attack_2H_03/04`) were replaced by the user's own hand-animated set (§1); the tools stay.


`python tools/video_mocap.py VIDEO NAME [--fast]`: GVHMR (the `westnt/gvhmr-pr` fork, CPU, in WSL Ubuntu at `D:/GVHMR`,
SMPL-X body models from the user's MPI downloads; ~1.4 min per second of video) → `tools/gvhmr_export.py` (GVHMR venv:
`hmr4d_results.pt` → SMPL `.npz` in Blender's frame, floor at 0, 30 fps) → `tools/smpl_to_armature.py` (identity-rest
bones; the FK reproduces the body model to 0.00 mm) → `External Anims/Video/NAME_arm.blend` (untracked), retargeted with
`--rename smpl`. First test (the user's `slowmo 1 attack.mp4`, black side bars cropped first, 3x `time_scale` from the
hand speed): arm bones within 1–3 deg of the capture, no per-clip passes; the clip was discarded at the user's request.
SMPL-X is MPI's non-commercial licence: check it before shipping clips made this way.
**Second round (2026-10-03): the user's two one-handed swing videos.** Three findings, all in the tools now:
(1) **the retarget bent every FK leg** (`glb_retarget.pose`): the FK leg controls hang under `spine_fk` (thigh_fk <
MCH-thigh_parent < ORG-spine < tweak_spine < spine_fk), so the final re-apply of `spine_fk` after the chain swung both legs,
already set, as one rigid piece — 20–44 deg on `swing_1` with the knee angles exact (the plant then folded the stance; feet
0.57 apart against the source's 0.32), and likely the 4–15 deg leg errors of the earlier captures. The legs are set again after
that re-apply: 0–3 deg. Every clip with FK legs from a capture (action / loco / death) was built with the bug; none rebuilt.
(2) **GVHMR drifts a planted foot** (1.1 m on swing_1, 0.29 m on swing_2): `gvhmr_export.py --anchor-foot L|R[:frame]` shifts
the whole body per frame so that foot (ankle + ball mean) stays at its reference spot, and takes the floor from it.
(3) **the idle's knees point 11–14 deg further out than a capture's**, so the start/end blends swung them:
`anim_nla_bake --knee-swivel-to ACTION:FRAME` turns the IK knees about the hip→ankle axis so the knee direction equals the
reference's on the first AND last frame, the offset lerped between; run it before the blends, then blend with `--keep-poles`.
Recipe used (in place, `drift remove`): retarget (`--mode action --time-scale 0.3333 --plant-feet 0.001 --heading first
--unwind-yaw --unwind-ref body`) → [blends] → `--ik-legs --pin-foot ... --leg-reach 0.95 --knee-swivel-to Idle_1H_Combat:1`
→ [blends `--keep-poles`]. `Attack_R_Swing_01` is the swing_1 video build (right foot static, left held 45–63 at 63); the
swing_2 build is **`Attack_R_Swing_07`** (99 frames; right ball held, the foot keeps its 33 deg tilt; left held 1–10, 44–70
@52, 85–99); `Attack_R_Swing_02` is the committed mannequin clip again (user: "save the new one as 07"), the old mannequin
clips kept as `Attack_R_Swing_01/02_mannequin`. Not exported, manifest not updated, the L mirrors not rebuilt.
**Hands: GVHMR never observes them** (17 COCO keypoints; its wrist moves ~14 deg over a whole swing). **SAM 3D Body** is
installed for that: weights in `D:/Sam` (gated `facebook/sam-3d-body-dinov3`: `model.ckpt`, `model_config.yaml`,
`assets/mhr_model.pt`), code `D:/Sam/sam-3d-body` (GitHub, with a local CPU patch: 7 hard-coded `.cuda()` calls), venv
`D:/Sam/.venv` (`D:/Sam/setup_local.sh`), no Detectron2: `tools/sam3d_hands.py` feeds it GVHMR's per-frame box and camera.
11.6 s per frame on this CPU; hand and finger keypoints land on the hands. **The hand step (2026-10-03 evening, `tools/sam3d_wrists.py`)**: SAM's hand orientation RELATIVE TO THE FOREARM, from joint
positions only (forearm frame = elbow->wrist + the upper arm projected off it, blended to the shoulder line near a straight
elbow; the hand = wrist->middle knuckle and the palm normal from the index/pinky knuckles), rebuilt on GVHMR's forearm of the
same frame; the twist about the forearm axis goes on the ELBOW as pronation, the swing stays on the wrist (clamped 80 deg),
slerped between SAM's frames (every 2nd) and low-passed. `video_mocap.py --hands [--step N] --anchor-foot L|R` runs the whole
chain. On the one-handed swing video GVHMR's right wrist moved 6-23 deg over the swing, SAM's 6-74 deg + 0-79 deg of pronation.
Measured on the same frames, SAM's per-frame body agrees with GVHMR's within 3-12 deg (joint angles) with ~2x the jitter and a
1 cm/frame depth wander: a SAM-only path (MHR is Apache-2.0, SMPL-X is non-commercial) is feasible but not built - the user
kept the hybrid ("already good as is"). Clips built this way: **`Attack_R_Swing_07`** (video 2 of the one-handed set, rebuilt
with the hands; `Attack_R_Swing_01` still has GVHMR's hands), **`Attack_2H_03` / `Attack_2H_04`** (the user's `2 handed 1/2.MOV`,
normal-speed recordings built at `time_scale 0.5`: 106 / 86 frames; `--start-blend / --end-blend Idle_TwoHanded:1:6 / :16`, both
balls of the feet held on the idle's stance for the whole clip (`--pin-foot "L:1:1:N:toe,R:1:1:N:toe"`: the heels lift as recorded),
`--leg-reach 0.95 --knee-swivel-to Idle_TwoHanded:1` (the recording's right knee pointed ~50 deg out, the idle's 13), then
`--grip-follow L:@-0.075 --grip-pull --grip-reach 0.96 --fk-arm R` as on Attack_2H_01/02: the left hand within 51 mm of the shaft
spot on the widest frame (the performer's hands were up to 0.56 m apart); the start/end crossfades turn the right forearm up to
33-36 deg per frame at frames 4-7 and ~99). In the anim file only: no manifest entries, not exported, no controller states.
⚠ A background SAM run was killed by Claude Code for low system memory (SAM takes ~9 GB); run it in foreground halves
(`--frames A:B`, ≤ 10 min each) and merge the npz files by frame. **Feet fixes pulled from the user's side file** (same evening):
`Run_Fwd_01/02`, `Walk_Back_01/02`, `Walk_Fwd_02` appended from `Animations/skeleton_anim_run_feet_fix.blend` over the anim file's
(feet only differ; the `_base` / `_Fix` actions untouched); not re-exported, the speed table not re-measured.
**Second pull (2026-10-04, "pull Run_Fwd_02 and Strafe_02 left/right from skeleton_anim_skeletal_locomotion into the main file, re-export
these 3 into Unity")**: the three actions appended from `Animations/skeleton_anim_skeletal_locomotion.blend` (the user's side file, untracked)
over the anim file's (the old ones removed after `user_remap`; `bpy.data.libraries.load` append, saved compressed, 29 MB), all three
`hand_edited` in the manifest (the strafes were reproducible entries before: a `--force` rebuild would have erased the edit), exported with
`--export-only --force`. Measured: Run_Fwd_02 unchanged (0.833 s, 1.562 m, 1.87 m/s); **the `_02` strafes now step shorter: 0.843 m per
1.300 s loop, 0.64 m/s (were 1.204 m / 0.93)** — the speed table, `ExtendedBuilder`'s `Locomotion_Upright` tree (±0.64), `SkeletonNavController.
UprightSpeeds`, the showreel captions (Unity recorder + `tools/ue/showreel_plan.py`) and the buyer manual follow; Extended *Build All (1-4)* re-run
(the tree reads ±0.64, the `PFX_` prefabs keep their controller). Boots after the export: the Knight within 1 mm on the strafes, the others
≤ 6 mm under; the run +4..+13 mm (its default lift, as before); the Necromancer's hips-weighted robe 9–14 cm under as on every `_02` loop.

### The clip factory (2026-09-19/20)

`Animations/clips.json` is the manifest: one entry per clip with the Kimodo prompt,
frames, seed, retarget **mode** and arguments. Two detached batches consume it:
`tools/kimodo_batch.py` (generates every GLB that is missing, ~2–4 min each on the
laptop) and `tools/anim_batch.py --wait` (retargets, previews to
`Animations/preview/`, exports, runs `verify_clip.py` with the mode's import flags and
`ground_clip.py`; state in `Animations/build_state.json`, log in
`Animations/anim_batch.log`). Re-run `anim_batch.py <Name> --force` after changing an
entry or the retarget.

`glb_retarget.py --mode`:
- **idle** — legs on IK at rest, loop, finger life. Weapon idles are just prompts
  ("axe resting on the right shoulder", "leaning on a staff"); the hands hold nothing
  in Blender, the socket carries the weapon in the engine.
- **loco** — FK legs from the source; the hips' straight-line travel over the loop goes
  on `root` (→ `Root` = root motion), the rest on `torso`; loop = one gait cycle found
  by autocorrelating the ankle-height difference (first local maximum, not the global
  one: the global max is several cycles); root travel along the **dominant axis only**
  (`--travel-axis x` forces sideways for strafes), the other axis's drift is removed
  linearly from the hips. ⚠ The torso is set in armature space, so its world target
  must **include** the root's travel: the first build put travel on `root` while the
  hips stayed in place, and Unity measured zero root motion — Humanoid derives root
  motion from the hips, never from the `Root` bone. `--mirror` swaps left/right in the
  source (Strafe_Left is the mirrored right strafe: the left generation barely moved).
  `--head-damp 0.45` on Walk_Fwd/Run_Fwd: Kimodo's "shambling" walks bow the head 30–60°.
  ⚠ The loop-closing crossfade blends each of the last BLEND frames with the source frame
  one cycle EARLIER; on a walk that frame is a whole cycle behind in world space, so the
  raw blend pulled the hips backwards over frames 33–42 and the wrap snapped them forward
  (the user saw it in the anim file). The partner frame's positions are shifted forward
  by the loop's travel before blending; the retarget now logs the hips' advance per frame
  along the travel axis, which must never be negative (Walk_Fwd: 5.8–19 mm, seam 5.9 mm).
- **action** — FK legs, root fixed, net hips drift removed (end = start), one-shot;
  ground = median stance on the floor + smoothed lift-only.
- **death** — FK legs, hips as authored (the corpse lands where the fall put it), root
  fixed, two-way slope-limited ground correction so the lying body rests on the floor.
Unity import per mode: idle/loco loop; loco keeps root XZ as root motion; everything
else bakes XZ + rotation into the pose; root Y is always baked.

**Grounding measures every skinned mesh of all six characters** (boots, greaves, robes,
armour), un-excluding the `Ref_*` collections for the measurement and restoring them
before the save. The Knight body alone under-grounded the deaths by 6–15 cm: a corpse
rests on its pauldrons and the Necromancer's robe hangs lowest. What remains is a Unity-
side difference on deep knee bends (Death_02 kneel: Necromancer robe −5.6 cm for ~1 s)
because the export merges Rigify's two-segment limbs into one bone; `ground_clip.py`
is the truth, the Blender number is the estimate.

**Authored arm keys**: Kimodo has no props, so archery, summoning and taunting came back
as hanging or half-raised arms. `--arm-keys "t:preset,..."` (manifest `arm_keys`, t in
0..1 of the clip) interpolates socket-frame hand poses over the clip and blends each arm
between the source and the authored pose through Rigify's `IK_FK` where only one key
poses it (`free` = hand the arm back). `Shoot_01/02` = bow_side → bow_aim → bow_draw →
bow_release → bow_side; `Summon` = summon_high; `Taunt` = arms_wide after the chest beats.
The hand IK controls are keyed only while an authored mode is active — the first lock
build keyed them once at frame 1 and the left hand stayed pinned in space.

**Two-handed grips**: `--lock-left-hand D` (manifest `lock_left_hand`) pins the left
hand on IK D m down the right hand's weapon handle every frame (left socket frame =
right socket frame moved −Y), so a weapon on `RightWeaponSocket` passes through both
hands: 0.22 for Cast_Staff_*. Verified with `weapon_shots.py` on the battle axe.
**The gate (2026-09-22, user: "a gate for attack animations that controls how far the two
weapon slots on hands can travel from one another, so the second hand feels like it's on the
shaft")**: `--gate MIN,MAX` (manifest `gate "0.03,0.11"` on Attack_2H_01/02, replacing the
fixed 0.085) pins the left hand the same way but at the distance where the CAPTURE's left hand
projects onto the right hand's hilt axis, clamped to MIN..MAX and smoothed (`--gate-smooth`),
so the hand slides along the handle through the swing instead of being welded to one point.
The range is the handle below the socket: battle axe 0.13 rig m, longsword 0.108. The arc is
still the right hand's (the capture's); the left follows on the shaft.

Weapon idles: Kimodo has no props, so "axe resting on the shoulder" comes back as
hanging arms. `--arm-pose <preset>` (manifest key `arm_pose`) puts the hands on IK at
an authored position/orientation written in the socket's own frame and following the
torso's sway; presets in `glb_retarget.ARM_POSES`. ⚠ The detached batch loads its code
at start: after editing `anim_batch.py` restart the process, and clear the affected
entries from `build_state.json` (the signature already contained the new manifest key,
so the old process had marked them built without the argument). Never run a manual
retarget with `--save` while the batch is mid-clip: two Blender processes writing
`skeleton_anim.blend` is a corrupt file.

### The bone atlas (2026-09-22) — measure a control before trusting its axis name

`tools/bone_atlas.py` (ported from the creatures pack) probes every rotation and
translation axis of every animator-facing control on `RIG-Meta-Rig` from its identity
rest pose and records what moved, on the **bare Knight body** (`SkeletonKnight_Body`,
never an armour module), in the character's frame (forward / left / up). Output in
`Rig/atlas/`: `atlas.json` (708 channels, tracked), `ATLAS.txt` (readable, tracked),
`sheets/<control>.png` + `index.html` (one row per channel, −delta | rest | +delta with
red / grey / green borders; 53 MB, gitignored, regenerate with `--sheets-from`).
`tools/atlas_query.py Rig/atlas/atlas.json <probe>` answers "which channel moves X" by
sorting the recorded response. The harness validates itself first (root translation moves
every landmark exactly, restore is drift-free, and the known jaw sign is reproduced). FK
controls are probed with `IK_FK = 1`, the IK controls with `IK_FK = 0`; each record says
which. Why: this week's defects were each one unmeasured fact about one channel (the toe
hinge, the jaw sign, a wrist's "counterclockwise", the arrow along the fingers).

    blender -b Animations/skeleton_anim.blend -P tools/bone_atlas.py -- --out Rig/atlas [--render] [--only torso,head]
    python tools/atlas_query.py Rig/atlas/atlas.json jaw_dz hilt_R fingers_R foot_L_fwd footL_min_z index_R_tip
    python tools/atlas_query.py Rig/atlas/atlas.json --bone hand_fk.R --shape swivel --inert

**Measured facts to cite** (delta +0.35 rad; "L/R" = the same channel on each side):

| Want | Channel (+0.35 rad does…) | Note |
|---|---|---|
| open the mouth | `lowerjaw` rotX **negative** (+X closes: jaw_dz −0.028) | matches `anim_twitch.py`; `lowerjaw.001` rotX is the second jaw segment (half the effect) |
| look down / look left | `head` rotX → aim down; `head` rotY → aim **left** (rotZ is the head roll, 0.07) | `neck` rotX moves the head 2.4 cm forward, rotY is inert |
| chest pitch / yaw | `chest` or `spine_fk.003` rotX → chest faces down, rotZ → left | `hips` rotX tilts the PELVIS only (chest facing unchanged) |
| turn the hilt (weapon roll) | `hand_fk` rotY (or `hand_ik` rotY, or `forearm_fk` rotY: pronation) | **per-side sign**: R +Y turns the hilt forward/up, L +Y turns it back/down |
| point the fingers | `hand_fk` rotX → fingers forward+up; rotZ → fingers left (both sides) | the socket's +X IS the finger direction |
| spread the arm | `shoulder` rotZ: R +Z swings the hand forward, **L +Z swings it back** | `shoulder` rotX lifts the arm up and outward on both sides |
| raise the arm (FK) | `upper_arm_fk` rotX → hand forward+up (same sign both sides); rotZ → hand left on BOTH sides (not mirrored) | |
| elbow direction | `forearm_tweak` locX/locZ and `shin_tweak` locX/locZ are true **swivels** (tip and root fixed, extension unchanged); `thigh_ik` rotX swivels the knee | the arm pole targets are live in the file's rest state (`pole_vector` on), the leg pole targets are **inert** |
| lower the sole / lift the toes | `foot_ik` rotX −0.35 lifts the sole 4 cm (rotX pitches about the ankle); `toe_ik` rotX +0.35 lifts the toe tip 2.4 cm; `foot_ik` rotZ yaws the foot left | `foot_fk` rotX identical with `IK_FK = 1` |
| curl a finger | `f_*.01_master` rotX; `thumb.01_master` rotX | `f_*.01.L.001`, `thumb.01.L.001` and every finger's rotY are inert; `f_*.02/.03` move only their own tip (the hand centroid cannot see them: probe the fingertips, `index_R_tip` etc.) |
| reach limit | `hand_ik` locZ: linearity 0.58, asymmetry 1.20 | the arm saturates 3 cm above the rest hand: a placed hand target beyond it straightens the elbow (the 97 % reach rule in the retarget) |

Rule kept from the creatures pack: **a channel's sign is per side** (Rigify computes bone
rolls against a world target, so left and right local axes are not mirror images). Anything
authored as a socket-frame offset must be verified from the side on ONE hand before it is
copied to the other, and the atlas is where to look it up. The engine-side facts that the
atlas cannot see stay documented where they were found: Unity's slot **+X is Blender's −X**
(the FBX import flips that axis, §"Recorded bow shots"), and Humanoid **toes have one muscle**
about the T-pose's world sideways axis (§"Feet").

### Recorded idle (2026-09-21)

`Idle_03` is no longer the Kimodo `idle_slow_b` build: the user recorded an idle with a
video-mocap app (`P:\VID20260921200208_default.glb`, copied to `External Anims/Kimodo/
idle_mocap.glb`: a 53-joint Mixamo-named skeleton WITH finger joints, T-pose bind, 163
frames at 30 fps) and asked for "all bones except legs/feet". That is idle mode as it
already was (legs on IK at rest) plus two additions to `glb_retarget.py`, both in the
manifest entry: `rename mixamo` (Spine/Spine1/Spine2/Neck/UpLeg/Leg → the SOMA names the
MAP expects; the rename is two-phase because the names chain, and the hand's direction
child falls back from `*HandMiddleEnd` to `*HandMiddle1` when a capture has real fingers)
and `fingers` (`--fingers`: the first two phalanges of every finger are copied as world-
rotation deltas onto Rigify's `thumb/f_*.01/.02` chain controls, the third follows its
parent, and the finger masters stay at 0 instead of the constant curl + sine). Idle mode
now also removes the hips' net XY drift over the loop linearly and shifts the seam's
crossfade partner by it (the recording drifted 3 cm in 4 s; Kimodo idles drift ~0, so
their rebuilds are unchanged). `src_end 128`, then `time_scale 3.0` (user: "slow it
down like 3 times"; slerp resampling, `smooth 3`), `loop 324 blend 60 src_start 60` in
resampled frames (10.8 s): the app lost the right hand at source frames 130–132 (a 50°
jump in one frame, jitter to the end), so the loop stops before it; `--smooth` alone did
not hide it, and the raw-source per-joint step trace is how to find such dropouts.

**Heading (user: "knees twist slightly in some spots").** The performer stood 48° off the
app's bind facing. The retarget copied that yaw onto the pelvis while idle mode keeps
the feet at rest, so both legs were rolled 49° about their own axes on every frame
(the greave sat 4 cm inward in Blender too, easy to miss on a straight leg; the export's
de-twist then stripped it and Unity's Humanoid re-derived ±40° of thigh twist from the
swing, which is what showed as twisting knees). `--heading auto` (now the default, manifest
`heading`; `keep` disables) rotates every source frame about Z so the hips' mean yaw
against the bind is 0: thigh/shin twist 0–6° in Blender, de-twist ≤ 11°. The user then
named the deeper cause ("the torso is a bit too high, making the legs twist to compensate"):
Idle_03's hips reached 102 % of the leg length and Idle's 100 % (knee 177°), and a straight
IK leg has no defined roll. **Idle mode now lowers the hips by a constant** so no frame
exceeds `PLANT_REACH` (0.985 of the leg, knee ≥ ~20° of bend): 32 mm on Idle_03 (the sway
keeps its shape). `Idle` got the same through `anim_fix_idles.py --only Idle --torso-drop
0.0071` (a further 13 mm on top of its first 10 mm; knee 177° → 160°). Idle_02 sits at
93 % and needed nothing. After that, Unity's Humanoid is within ±8° of the Generic playback
on every leg bone (it was ±14° with straight legs, and 1.0 / 0.0 avatar twist settings are
worse than the default 0.5). Verified: seam 0.0000°, in place on all six, lowest vertex
Idle +2.7..+7.4 mm, Idle_03 +5.2..+10.1 mm with the default lift, faces forward in play
mode.

**Split stances (user request, same evening).** Idle_02: left foot forward, right back
"a bit" (`tools/anim_stance.py -- --action Idle_02 --left 0.03 --right -0.03`, rig m along
forward = 5.4 cm each in the engine); Idle_03: the other way round and wider (manifest
`stance "L:-0.055,R:0.055"`, 10 cm each). The retarget's `--stance` moves the resting
`foot_ik` targets before the pose every frame; the standalone tool does the same on a
finished action and lowers the torso by the reach constant if the wider stance needs it
(Idle_02 needed 0: its knees sit at 129–139°). ⚠ The tool's first version shifted the foot
per frame after keying it, on controls keyed only on frame 1: every frame re-evaluated the
previous frame's shifted key and the feet ran 10 m away (the anim file was saved so; Idle_02
was restored from `HEAD` by appending the action from `git show HEAD:…blend`). Any tool that
keys a control per frame must read every frame's original value first. The wrists are the capture's, except that the LEFT forearm is turned 60° about its own
axis (manifest `wrist_twist "L:-60"`, 2026-09-22, "rotate the left hand counterclockwise 60
degree"; the user's counterclockwise is NEGATIVE about the forearm's bone axis, i.e. seen
from the elbow looking down the arm; +60 went the wrong way), and the
motion is brisker than the other idles (head ~40°/s in the source): `time_scale` +
`smooth` in the manifest are the knobs if it should read heavier.

### Recorded propped idle (2026-09-21, later)

`Idle_Propped` is the user's capture `P: handed propped up 2_default.glb` (copied to
`External Anims/Kimodo/idle_propped_mocap.glb`, the 52-joint `*_JNT` skeleton, 168 frames).
Three things the file needed, all manifest keys now: **`mirror`** (the app mirrored the
capture: the user propped with the right arm, the file shows the left; `--mirror` swaps it
back and the retarget's heading removal runs after the mirror), **`still_joints RightHand`**
(pre-mirror name = the file's hanging hand: the tracker lost it at source frames 75–91, 73°
steps while the forearm stayed calm; the joint's rotation vs its parent is frozen to the
clip's medoid frame) and **`prop R:0.69`** + **`prop_damp 0.2`** (user: "twist the right
hand 90 degree, so the weapon points down. also, reduce the movement on the right hand, so
it feels like it rests on a weapon"): the hand's socket +Y, the hilt axis that every weapon's
blade direction follows, is aimed at a floor point straight ahead at the distance a 0.69 rig
m (1.24 m) staff reaches from the hand's mean height (0.27 rig m ahead here), the fingers
keep their heading, and the hand goes on IK at its mean position plus a fifth of its own
motion (5 mm of travel over the loop). Then (user, from a Knight screenshot with the sword
angled ahead: "twist the torso forward, so that model is hunched forward more; twist the arm
so that the weapon points down") **`hunch 25`** and **`prop_vertical`**: the hand is put ON
the staff's top at the staff's height (0.69 rig m = 1.24 m, the recording had it at 1.08),
horizontally where the arm holds it at 90 % of its reach (pinning it at the recorded x/y
left the elbow locked 3 cm short), and the hilt axis is aimed straight down from that
pinned position (aiming from the recorded position left an 11° lean). Result in Unity: chest
38° forward, elbow ~100°, staff foot on the floor 0.5 m ahead, hilt within 2° of vertical.
Then the user posed a **reference** on frame 0 of the generated Idle_Propped ("use the
reference pose in blender for torso position/rotation and right hand position"): torso 19°
further forward and 4 cm back, right hand at 0.95 m. `tools/anim_pose_save.py -- --from
Idle_Propped:0 --to Propped_Base` copied it into a one-frame action of its own (a rebuild
recreates Idle_Propped, frame 0 included), and the manifest's **`torso_ref` / `hand_ref`
`Propped_Base:1`** make the retarget use it: the torso control's world rotation/position
replace the clip's MEAN (the recorded sway stays) and the delta is applied to every world
target above the torso (the user rotated the control, which carries the spine, head and
arms with it; rotating the pelvis alone left the chest where it was); the propping hand's
socket position comes from the reference and the reach drop is re-measured after the fix
(the reference's height alone locked a knee at 177° mid-loop). Then "lower the right hand like 20 cm": manifest `hand_offset 0,0,-0.111` (rig m, on top of
the reference; if the target is beyond 97 % of the arm's reach from the mean shoulder it is
brought in HORIZONTALLY at the requested height, so the elbow keeps ~30° and the height
holds; pulling it straight towards the shoulder had given most of the drop back). The staff's grip for the propped loadout is `ProppedHandHeight =
0.80` m up from its foot (0.95 before the lowering; 0.80 is the socket height Unity measures,
the hand at 0.75 plus the export lift and the socket's offset above the wrist), so the foot
meets the floor and the head rises above the hand. The staff is held by its TOP for this: loadout row
`"SM_H2MagicStuff@Top"` makes a second prefab `W_H2MagicStuff_Top` of the same model whose
Grip sits at the mesh's max Y turned 180° about Z, so the shaft runs down the slot's +Y to
the floor (the first try aimed the palm normal and gripped along Z; a sign slip hung the
staff off the back of the hand, the bounds check caught it); the demo lists it as "Staff
(propped)" (the plain "Staff" keeps the shaft grip for Idle_Staff). Legs on IK with the
reach drop (28 mm), 12.0 s loop (`time_scale 3.0`, slowed 3× on request), seam 0.0000°, lowest vertex +2.8..+7.5 mm, hands 20–24°/s after the freeze.

### Recorded bow idle (2026-09-22)

`Idle_Bow` is the user's capture `P:\bow idle_default.glb` (`External Anims/Kimodo/
idle_bow_mocap.glb`, `*_JNT` skeleton with finger joints, 280 frames), bow in the left
hand (the extended one in the file, no mirror needed), arrow in the right; `time_scale 2.5 smooth 3 loop 596 blend 100 src_start 100` (19.9 s;
built at real time first, then "make it 2.5 times slower"). The user's two notes from Blender, and how they are
met: "right hand slightly overlaps with body from frame 42 to 52" → **`hand_clear R`**: on
any frame where the right socket lies inside an ellipse round the torso (0.22 rig m
sideways, 0.18 front-back, centred on the hips; the Knight's chest is ±0.18 / −0.08..+0.12)
it is pushed out to the outline in the horizontal plane and the arm follows on IK, the
IK/FK weight ramping over the first 3 cm of push so untouched frames stay pure FK; "right
feet detached from ground from frame 220" → nothing to do: idle mode keeps both legs on IK
at rest (the source foot rises 4–5 cm from frame 200 on and is never copied). Plus
`still_joints RightHand`: the tracker jittered the arrow hand (93°/s, a 43° step at source
frame 83). Fingers are in the file but not copied (both hands hold items, so the engine's
grip pose replaces them anyway).

### Recorded bow shots (2026-09-22)

`Shoot_01` (slow draw, `P:\bow attacks_default.glb`, 117 frames) and `Shoot_02` (quick,
`P:\bow attacks_default (1).glb`, 75 frames) replace the Kimodo builds; copies in
`External Anims/Kimodo/shoot_mocap_1.glb` / `_2.glb`. Both files hold the bow in the RIGHT
hand and draw with the left, so they are `mirror`ed (bow left, arrow right, as Idle_Bow);
`still_joints LeftHand` (the file's drawing hand, lost by the tracker near the face:
346°/s, 80° steps; the wrist is frozen, the arm's draw stays). The user: "both start with
bow hand in already raised position, so maybe add some transition" → `blend_from Idle_Bow:1`
over 20 frames (15 on the quick shot) raises the bow arm from the idle, `blend_to Idle_Bow:1`
over the last 20 (15) lowers it, so the clip starts and ends on the idle's frame. New
retarget **mode `upper`**: a one-shot with the legs on IK at rest exactly like the idle (an
upper-body clip that the demo plays over Idle_Bow or a walk; the file's feet lift up to
5 cm and are never copied), hips drift removed, no grounding, and the reach drop following
the need per frame (running max ±5 frames, smoothed) so the blend-from frames keep the
idle's height and the transition does not pop. `hand_clear` now applies only below the
shoulders (a drawing hand at the cheek is not inside the torso).

**The user's review ("shoots diagonally, should shoot in front of itself; left leg forward,
right back; the arrow points wrong in the hand").** The capture is a real archer: the shot
line sits ~80° from the hips (side-on stance), and after the heading removal (mean hips
yaw) the shot went diagonally. A squarely facing pelvis with the shot ahead would need an
80–100° spine twist (tried: grotesque), so **`aim_forward L`** turns the WHOLE body per
frame until the shot line (draw hand → bow hand, both raised) points forward, the feet
turning with it about the rig origin (the legs never twist), fading with the idle crossfades:
the transition from Idle_Bow is a pivot into the archer's stance (the IK feet slide round
over the 20-frame blend). Measured in pass 1 on the posed rig, applied in pass 2 (the
targets are world rotations, so a per-frame yaw on all of them turns the body as a unit);
the foot controls are keyed per frame when it is on. **Stance** `L:0.06,R:-0.06` on the
shots AND on Idle_Bow (the archer's front foot toward the target; ±0.08 cost the idle a
6 cm crouch to keep the knees bent). **The string hand**: the tracker had lost that wrist,
the medoid freeze happened to present the thumb side to the bow, and the arrow (gripped
along the hilt axis) stuck out of the fist; now, while both hands are raised, the hand is
re-aimed so its fingers (socket +X) run along the shot line and the back of the hand faces
away from the head, and the Arrow prefab's Grip holds the shaft along the fingers
(`Euler(0,0,-90)`: the fingers are the slot's **−X** in Unity, the FBX import flips the
handedness of that axis; +90 pointed the arrow straight up, measured, not guessed). The
arrow therefore points at the bow at full draw and hangs down the leg in the idle. The
performer aims ~25° downward at full draw (the bow hand below the draw hand): kept.
**Second review (user: "a slight step back instead of feet shifting; the right forearm
snaps in Unity but not in Blender").** The step: the FRONT foot (the larger forward stance)
now pivots in place and the rear foot steps round it with a 4 cm lift arc (`--step-lift`,
profile on the crossfade weight, so up on the way in, down on the way out), and the hips
move back by half the rear foot's displacement so the body steps rather than the foot
alone (pivoting about the front foot with the hips fixed swung the rear foot beyond the leg
and it hung 8 cm in the air). The snap: at full draw the right hand sat **150–176° twisted
on its forearm** — Blender keys the hand in world space and shows nothing, Unity's Humanoid
splits that twist between hand and forearm and wraps at ±180°, snapping the forearm 178°
on six frames. Two causes, both in the string-hand aim: the palm reference "away from the
head" collapsed when the hand reached the cheek (a 167° hand flip in ONE Blender frame,
which the twist limiter then chased); it is now "away from the chest centre". And
`limit_wrist()` (default `--wrist-limit 60`) keeps every aimed hand's twist about the
forearm axis within 60°, moving the excess into forearm pronation while the hand keeps its
world rotation; the hand aim also takes the shortest quaternion path. Result: Unity's
largest forearm step 23° / 27° (was 179° / 177°), the same as Blender's; wrist twist ≤ 71°;
lowest vertex +2..+7 mm on all six (the robe dip went with the wide foot swing). Rule: a
hand's twist relative to its forearm is what Humanoid distributes; keep it human. Then
"lower the torso a bit (like 10 cm), since standing too high makes leg twitch": manifest
`hips_drop 0.056` (rig m), a deliberate crouch on top of the reach drop, faded with the
idle crossfades so the join stays exact; knees 123–151° through the clip (the per-frame
reach drop then has nothing left to do), Necromancer robe −4 mm in the crouch (accepted).

**"Body twists too much, so he is not shooting forward, are you adding extra twist?"**
(user, from a Unity screenshot). Yes: `--aim-forward` turned the WHOLE body (pelvis, feet
and all) by the shot-line error, so the character faced 41–57° away and shot forward only
across its own chest. Manifest `aim_body 0.0` (`--aim-body S`, S = the share of the turn the
pelvis and feet take; 1 = the old behaviour): the pelvis is HELD on the idle's heading
(pass 1 records the capture's pelvis yaw, −20..8°, smoothed; the hold cancels it) and the
turn is spread up the spine (`spine_fk.001` a third, `.002` two thirds, chest and above the
full turn), so the feet stay put and the shot line still ends up forward. ⚠ The hold did
nothing at first: Rigify's pelvis FK control `spine_fk` is a CHILD of the spine pivot
`spine_fk.001`, so posing it in the pelvis-first level order and then setting its parent
dragged it along. `pose()` now re-applies `spine_fk` after the whole chain. Measured at the
draw: Blender pelvis 0°, chest −64°, feet 0°, shot line 0°; Unity hips 2–4°, chest 62–65°,
shot yaw 0°; forearm step 16°, seam and in-place unchanged, lowest vertex +6..+11 mm.

**"Still shoots diagonally, rotate the left arm to the left more."** The hand-to-hand line was
dead ahead, but BOTH hands sat 0.2 rig m to the right of the head (the capture's draw hand was
never at the cheek), so the bow arm crossed the body 43–54° to the right and that is what reads
as the aim. Three lines can read as "where he shoots" and they cannot all be forward: the head
sits 16 cm right of the bow shoulder. Manifest `aim_line sight` (`--aim-line shot|sight|arm`:
which line the turn aims, hand→hand, head→bow hand or bow shoulder→bow hand) with
`aim_offset 10` (`--aim-offset DEG`, + = left): the sight line 10° left, the bow arm 7–9° right
of forward, the arrow 11–15° left (with `arm` the bow arm was 0 but the arrow 18–24° left).
And `anchor 1` (`--anchor 0..1`), the archer's anchor: while both hands are raised the draw arm
is swung in FK about the vertical through its shoulder until the string hand lies on the
vertical plane through the head and the bow hand (the arrow passes under the eye; 22 cm of
swing), then swivelled about the shoulder→hand axis until the elbow is LEVEL on the back/out
side, and the hand is rebuilt from the forearm's zero-twist hand: fingers along the shot, then
`--anchor-roll 45` about the fingers with the sign chosen once so the back of the hand faces out.
Four things failed on the way, all of them 170–180° one-frame flips that Blender shows as much as
Unity: an IK anchor with an elbow pole (the captured FK arm and the IK arm differed by ~180° of
forearm roll and the IK/FK crossfade flipped the hand); a world palm reference (chest or
lateral) for the anchored hand (it sat 90–180° from the forearm's roll, and `limit_wrist` clamped
to ±60° from the wrong side); "elbow back along the arrow" as the swivel target (projected
onto the plane normal to the shoulder→hand axis it pointed straight UP, the elbow rose 16 cm above
the shoulder and dropped 180° at the release); and per-frame sign choices (the swing's two roots,
the swivel's ±180°, the level target's side) — every one now takes last frame's side
(`ANCHOR_PREV`, reset on frame 0), and the anchor's own weight is the raised mask smoothed 24×
(a 120° swivel needs ~16 frames). Measured at the draw in Unity: draw hand 13 cm from the head,
elbow 50°, level with the hand and behind it; wrist twist +45° constant; largest forearm step
20°; sight −10°, bow arm +7..9°, hips 2–4°; lowest vertex +5..+11 mm.
Then, from the user's top view: "twist the left hand so that bow is perpendicular to the arrow;
right hand should not come so close to the head, slightly less (5 cm)". Manifest `bow_square`
(`--bow-square`): while drawn, the bow hand takes the least rotation that puts its hilt axis
(socket +Y = the bow's limbs) perpendicular to the arrow (draw socket → bow socket), the cant
kept; the limbs were 36° from the arrow (nearly along it), now 90° in 3D and 95° from above.
`anchor_gap 0.028` (`--anchor-gap`, rig m) keeps the anchored hand that far out of the sight
plane on the side it came from: 5 cm lateral gap, 15 cm from the head centre in a straight line.
Forearm step 19°, lowest vertex unchanged.
Next round (top view again): "straighten the bow a bit more; don't bring the arrow too close to
the head (10 cm less); faster wind-up before the model starts to pull the string (50 %); less head
jerk". The bow had been squared only while BOTH hands were raised, so through the pull it still
lay along the arrow (1–30° at the frames the user looked at); `bow_square` now runs for the whole
raised phase (`BOW_UP`, the bow arm up, smoothed 8×) against the sight line, blending to the
arrow itself (draw socket → bow socket) while drawn — with the gap the arrow runs 12° off the
sight line and squaring to the sight left the limbs at 77°; now 86–88°. `anchor_gap 0.083` (15 cm
lateral; hand centre 21 cm from the head centre). **`time_warp 22:11`** (`--time-warp A:B`,
before `time_scale`: source frames 0..A played over B frames, the rest unchanged; the pull begins
at source frame ~22) with `blend_in 10`, so the clip is 69 frames (2.3 s). **`head_aim`**
(`--head-aim`): while the bow arm is raised the head's yaw is turned onto the sight line; the
capture's head swung 65° in 20 frames and ended 47° off the target, which was the jerk. Plus
`head_smooth 3` (`--head-smooth N`: extra low-pass passes on the neck + head source rotations
only). Head yaw now +27 → +10 over the raise and steady at +10 (= the sight) through the draw;
forearm step 20°, lowest vertex +5..+11 mm.

**The user's "fire" pose (saved on frame 37 of the generated Shoot_01, with the reference bow
and arrow attached).** `tools/anim_pose_save.py -- --from Shoot_01:37 --to Fire_Base` keeps it
(a rebuild recreates Shoot_01, frame 37 included), and manifest **`pose_ref "Fire_Base:1@37"`**
(`--pose-ref ACTION:frame@at`) makes the retarget use it: just before the final pass it
generates output frame `at`, reads every control's local transform, reads the reference's, and
keeps the deltas (here 4 controls: forearm_fk.R 40°, hand_fk.L 29°, upper_arm_fk.R 26°,
hand_fk.R 11° — the draw arm and the bow hand); `pose()` then applies them last, after every
other pass, weighted by the anchor mask scaled so frame `at` is the reference exactly. Controls
with a delta are keyed every frame. Frame 37 no longer differs from its neighbours (the deltas
ride on the capture's motion), the raise and the release are untouched. It is a LOCAL delta,
so the user may pose anything (torso, head, fingers) and it will be carried through the drawn
phase; a control they did not touch gets no delta.

### Weapons in the anim file, placed as Unity places them (2026-09-22)

The user asked for the bow and arrow in Blender "the same way it is in Unity" to pose a
reference. `tools/anim_weapon_ref.py -- --attach H2Recurvebow:L,Arrow:R --save` appends the
meshes from `Weapons/prod.blend`, puts each in the export-local frame (`export_weapons.
export_local_mesh`: grip at the origin, length +Z, roll; the 1.8× is left out, the anim file is
in Blender metres) and parents it to `DEF-weapon.L/R` with a Child Of constraint whose local
matrix is Unity's `AlignGrip`: `M · Slot · Grip⁻¹ · C`, the slot and Grip poses read from
`Animations/unity_grips.json` (`tools/unity/dump_grips.py` writes it from `PF_SkeletonArcher`
and every `W_*` prefab; re-dump after editing either in Unity). `M = diag(−1,1,1)` is the
X flip between Unity's slot frame and the Blender socket bone, `C: (x,y,z) → (−x, z, −y)` maps
Blender export-local mesh axes to Unity's mesh-local axes (Z-up → Y-up plus the flip); the
product is a proper rotation. Verified on Shoot_01 frame 36: the constraint reproduces the
bone-frame placement to 0.00000 m, the bow's limbs are 88° to the arrow (Unity: 86–88°), and
the arrow's mesh +Y runs 175° from the draw-hand → bow-hand line, exactly as Unity measures it
(`unity_arrow_check`: −0.93; the user set the arrow's Grip at (0, 0.464, 0) / Euler(0,0,90) so
the model reads right there). Objects `Ref_H2Recurvebow` / `Ref_Arrow` in collection
`Ref_Weapons`; reference only (clip exports are rig-only; grounding takes only skinned
`Skeleton*` meshes); `--remove --save` deletes them.

### The recurve bow bends (2026-09-27, "update the recurve bow .blend so it can bend when the string is pulled")

`Weapons/prod.blend` now carries **`H2Recurvebow_Rig`**, an armature the bow mesh is parented and skinned to
(built by the session script `bowrig.py`, kept as the description here): `Riser` (the grip, rigid), `Limb_U1` /
`Limb_U2` and `Limb_L1` / `Limb_L2` (two segments per limb on the limb's measured centreline), `Nock` (the
string's centre, pointing along the draw axis = the bow's local +Y, the string side), plus two non-deforming
helpers at the string's rest point, `Brace` and `Pull`. Weights by height along the bow: riser → limb 1 → limb 2
with smoothstep blends, the tip pieces on limb 2, and the STRING linearly between `Nock` (its middle) and the
limb-2 tips (its ends), so a pulled string is a clean V. ⚠ The string mesh was a 5-sided tube with vertices only
at its two ends (the loose part of 38 vertices is the two nock loops), so it could not bend: its five long
edges are subdivided into 17 segments (1875 → 1955 vertices; the static `SM_H2Recurvebow.fbx` re-exported, no
visible change). **Drivers** on the limb bones' local X rotation read the Nock's local Y (the draw): limb 1 bends
10° and limb 2 14° at a 0.28 m draw (0.5 m in the engine), the sign per limb found on the tip (U −, L +),
clamped at 1.5× the draw. Measured with the Nock pulled 0.28 m: the string's middle moves 0.26 m, its ends
stay on the limb tips, the tips flex 36–40 mm toward the archer. The export is unchanged in kind
(`export_local_mesh` copies the rest mesh, the armature parent is at identity).

**In the anim file** (`anim_weapon_ref.py --attach H2Recurvebow:L`): a weapon with a `<Name>_Rig` armature in
prod.blend is appended WITH it — the armature's rest pose transformed into the export-local frame by the new
`export_weapons.export_local_matrix` (the same transform the mesh gets), the mesh bound to it as its child, the
ARMATURE carrying the Child Of constraint on the socket (`Ref_H2Recurvebow_Rig` + `Ref_H2Recurvebow`). **The
string pull**: `Pull` copies the OTHER hand's socket (`DEF-weapon.R` for a left-hand bow); its local location
is then the hand in the string's frame (y = behind the string plane, x/z = off the midpoint), and simple-
expression drivers put the `Nock` at that hand while the hand is behind the string and within 0.28 rig m of the
midpoint (`gate = clamp((0.28 − lateral)·20) · clamp(py·40)`; Nock y = clamp(py, 0, 0.45)·gate, x/z =
px/pz·gate so the apex follows the fingers along the bow). Measured on Shoot_01 in the string's frame: drawing
0.10–0.41 behind and 0.12–0.21 off, at rest 0.10 IN FRONT, after the release 0.33 off — so the string sits at
brace with the hands down (frames 1–14, 50–59), follows the fingers through the draw (its middle 30–40 mm from
the hand socket, the limbs at 12–13° at full draw) and falls back as the hand swings away (frame 40 half).
A plain distance gate could not do this (full draw is 0.44 rig m from the brace point while the hanging hand
is 0.19). The bow limbs sit 72° to the arrow at the draw on the current shot.

**The engine side (2026-09-27, "let's export to unity; the arrow/string should attach at frame 15 and be
released at frame 21").** `export_weapons.py` exports a weapon whose mesh has an ARMATURE parent skinned: the
armature data copied and transformed by `export_local_matrix` + the 1.8× (the same frame the mesh gets), the
mesh its child with an Armature modifier, `object_types {ARMATURE, MESH}`, `bake_space_transform` OFF (the
exporter refuses it with an armature; the rig node therefore imports at (270, 0, 0) with the mesh under it,
which changes nothing: bounds and the Grip are as before), `add_leaf_bones` off, and the source object + data
renamed `_src` for the run so the export rig keeps the clean name `H2Recurvebow_Rig` (the file is not saved).
`SM_H2Recurvebow.fbx` now carries 8 bones and 2138 skinned vertices; the import setup's `RiggedWeapons` list
makes such a model **Generic, No Avatar** (`animationType None` imports the skin as a plain MeshRenderer and
drops the bones — measured; the other weapons stay None). The existing `W_H2Recurvebow` prefab is an instance
of the model, so it picked the skinned renderer up by itself; its material override was lost because the
renderer moved from the root to a child node (set back to `M_Weapon_H2Recurvebow` by `execute_code`; the Grip,
the user's (−0.010, −0.126, 0) / yaw 165°, untouched) and it now carries **`BowString`**
(`Demo/Scripts/BowString.cs`): it finds `Nock` / `Brace` / `Limb_*` by name, and in LateUpdate, while
`attached`, reads the draw hand's slot in the `Brace` bone's frame (its +Y is the draw axis, as in Blender:
measured on Shoot_01, the hand at y −0.27 m in front of the string on frame 2, −0.03 on frame 15, +0.003 on 16,
+0.57 at full draw on 26–30), gates it by the same corridor rule as the Blender drivers (behind the string, within
`corridor` 0.5 m of the midpoint), puts the Nock at the hand (0 mm on every attached frame) and bends the limbs
`bendLimb1/2` 10° / 14° at `fullDraw` 0.5 m (the drivers' values); on release the string returns at
`returnSpeed` 8 m/s (two frames). `SkeletonWeapon.Equip` hands every spawned `BowString` the OTHER hand's slot
as `drawHand`. **The events**: manifest `events {"BowAttach": 15, "BowRelease": 21}` → `anim_batch` passes
`--events` to `verify_clip.py`, which writes `ModelImporterClipAnimation.events` (normalised time
(frame − 1) / (last − first); verified on the imported clip: 0.467 s = frame 15.0, 0.667 s = 21.0) and prints
them; the Animator fires them on the character, `SkeletonWeapon.BowAttach()` / `BowRelease()` set `attached` on
the spawned bows, and for the demo `BowRelease` hides the `W_Arrow` renderers for `arrowHideSeconds` (1.2 s) so
the shot reads. Verified in play mode on the Archer, stepped at 30 fps: attached from 15.4, the Nock on the slot
from 16.6 (draw 0.035 → 0.267 m by 20.8, limb 1 at 5.4°), released at 21.4 (string back at brace by 22.0, arrow
hidden, back after 1.2 s), the string never moves while the hands are down. **Note for the user: frame 21 is
mid-draw** — the hand keeps drawing to 0.57 m at frames 26–30 with the string already at rest (renders
`f20_drawn` / `f24_released` in the session scratchpad); the numbers are two manifest fields. **The user's
answer: "the arrow is too short, and the tip of it is not on the bow at frame 30; frame 21 is already the latest
we can do with this arrow/bow meshes"** — 21 stays; a longer arrow mesh is what would move it. **The fired arrow
(same request: "an actual arrow projectile released when the arrow shoots, in a static direction from the
skeleton for now")**: `Demo/Scripts/ArrowProjectile.cs` + `SkeletonWeapon.FireArrow()` on `BowRelease`: a fresh
instance of the loadout's `W_Arrow` prefab at the held arrow's transform, renderers on, launched along the
CHARACTER's forward (`arrowDirection CharacterForward`; `BowAim` = draw slot → bow slot is there but off) at
`arrowSpeed` 15 m/s (30 until 2026-09-29, "decrease projectile speed by half": the script default and the six prefabs' serialized values), the prefab's shaft axis turned onto the velocity (`LookRotation · Euler(−90,0,0)` since 2026-09-29: the mesh has its HEAD at the origin and the nock at +Y, the grip near the nock — the first version turned +Y onto the flight and the user saw "the launched arrow flies backward", fletching first; measured in play mode: shaft +Y · forward −1.00 now, +1.00 before),
`gravity` 0 (dead straight), destroyed after `lifetime` 4 s or under the floor; no collision, no damage
(`fireProjectile` off disables it). Measured in play mode: the projectile appears on the release frame at the
hand's height (1.34 m) and covers 30 m/s along the forward the character had at that moment. **Then (user:
"the direction depends on the animation frame; make it GO transform direction based").** It WAS the
GameObject's forward — the GameObject itself was turning: Shoot_01 carried `drift root`, so it imported with
root rotation as root motion (`loopBlendOrientation 0`), and with Root Motion on the Animator turned the
character's root with the archer's side-on body (hips −34° at the draw; the first probe read the shaft 0.87 of
the root's LATER forward, which I misread as the turntable). `drift root` dropped: the clip imports IN PLACE
(rotation and XZ baked into the pose; the take's own root travel was 2 cm / 0.6°), re-exported with the events
and the fit. Measured with root motion on: the root's yaw stays 0.0° through the whole clip and the projectile
flies exactly along the root's +Z. Rule: **a one-shot whose body turns must bake its root rotation into the
pose, or every GO-transform direction read during it turns with the body.** Then "change the legs animation for
shoot_01 with the legs animation from idle_bow": `anim_nla_bake --action Shoot_01 --result Shoot_01 --legs-from
Idle_Bow:1` — the bow idle's 28 leg controls are CONSTANT over its 597-frame loop (IK feet at rest in the
archer's stance, L 5 cm forward / R 5 cm back; only the torso sways), so its frame 1 is its whole leg animation
and the take's stepping feet (4 cm of shuffle) are replaced by the idle's stance under the take's own hips
(0.485 rig m, 3 cm lower than the idle's 0.518: knees 115–140°, more bent than the idle's 138–158°, no lock).
Exported with the events and the fit (the Knight's sole the highest, the others ≤ 6 mm under). The events now
carry `SendMessageOptions.DontRequireReceiver` (`verify_clip.py`): the verify's bare test models, and any
buyer's character without `SkeletonWeapon`, logged "AnimationEvent has no receiver" on every play.
**Then "a noticeable snap between idle and shoot, both start and end".** Measured against Idle_Bow's frame 1
(`seamdiff`-style: landmark DEF bones' world position and rotation), the clip's two ends sat 33 mm rig LOWER at
the hips (6 cm in the engine), the chest 27–37° off, the bow hand 16–17 cm and 73° off, the shins 12° — the
take's standing pose is not the idle's, and the demo's 0.15 s crossfade cannot hide 6 cm of hips. The bake
tool's new **`--start-blend ACTION:FRAME:N`** (the mirror of `--end-blend`: the first N frames crossfade FROM
the reference pose into the clip, frame 1 = the reference exactly) with `--end-blend Idle_Bow:1:12` and
`--legs-from Idle_Bow:1`, all in ONE run on the clip restored from HEAD (`Shoot_01_blendtry`-style: the
committed action appended back over the tried one, so no pass rides on an earlier round's output): frame 1 and
frame 59 now equal Idle_Bow's frame 1 to 0.0 mm / 0.0° on every landmark, the attach at 15 untouched (the
start blend is over by frame 10), knees 120–151°, worst steps 20° on the release hand and 16° on the bow arm
inside the 10-frame raise. ⚠ The first try flipped the LEFT shin 200°: the blends re-aim each IK leg's pole at
the FK knee, and this clip's FK leg chain is the idle's REST chain (straight, no knee plane). `--keep-poles`
now also applies to the blends: the pole CONTROLS are lerped like every other control and never re-aimed.
And the lift: `lift 0.015` (the idle's default) with `ground_fit` dropped (the feet are the idle's constant
controls on every frame, so nothing needs a per-frame fit) puts the clip in Unity exactly where Idle_Bow sits:
boots +2..+7 mm on all six through the clip. Rule: **a one-shot played from an idle starts AND ends on that
idle's pose with that idle's lift; blend both ends in the bake, never rely on the engine crossfade for more
than a few cm.**
**Then "for shoot_01 the distance between knees is ~15 cm bigger than for idle_bow; increase it ~10 cm for
idle_bow, bring the torso down if there is not enough space".** Measured (`kneesep`-style: DEF-shin heads):
Idle_Bow's knees 41–48 cm apart in the engine, Shoot_01's 45–54 (the take's 3 cm lower hips bend the idle's
legs more and push the knees out), feet 40 cm apart in both. Idle_Bow is now hand-edited: `anim_nla_bake
--action Idle_Bow_base --result Idle_Bow --torso-drop 0.012 --knees-in -0.056` (a NEGATIVE knees-in widens):
knees 53–60 cm (+12), hips 2 cm lower, knees 123–146° (were 130–158°), the loop's worst step 4° on a hand.
Three things the tool needed, all for a clip whose legs are on IK with the FK chain at REST (every idle-mode
retarget): (1) `knees_in` aimed at `fk_knee`, the rest chain's straight knee — no plane; it now checks
**`fk_leg_straight`** (the FK chain's own knee angle > 168°, measured on the chain itself: measuring the FK
knee against the IK ankle hid it, the stance offset tilts that axis) and then moves the clip's OWN IK knee on
its swivel circle directly: the perpendicular from the hip→ankle axis keeps its radius, the lateral share grows
by d/2 outward, the forward share shrinks to match, the pole is put in that plane and its swivel error corrected
(a 12-step scan of the pole round the axis, then two signed-angle refinements; the knee must end in FRONT of
the leg, "front" = the BODY's forward, never the knee's own share, or the frame keeps its pole). A knee whose
radius cannot give the lateral offset is reported short (`--torso-drop` bends the knees and widens the circle:
alone the swivel reached +5..+8 cm with 17 mm short and the knees pointing nearly sideways; drop 0.025 gave
+16; 0.012 the +12 kept). (2) `repole_legs` (which `--torso-drop` runs) re-aimed the poles at that same
straight FK knee and flipped the LEFT knee BEHIND the leg (perp y +71..+114 mm, hyperextension) — it now
skips a straight FK chain. (3) The first flip guard compared against the knee's own forward share and let a
flipped knee stay flipped. Then Shoot_01 rebuilt on the widened idle (restored from the pre-legs commit
`c571ad9`, the same one run: legs-from, keep-poles, both blends): seams 0.0 mm / 0.0° again, knees 57–69 cm
against the idle's 53–60 (the take's lower hips; 15 → 7–9 cm of difference). Rule: **on an idle-mode clip
the FK legs are a rest chain; every pole pass must test `fk_leg_straight` and fall back to the IK knee (or
leave the pole alone), and "in front" is the body's forward.**
**Then "the knees are too far apart for both, make it 15 cm less, and maybe bring the torso 8 cm up".** The
raise first, probed on `Idle_Bow_base` (`raiseprobe`-style: the torso control lifted on sampled frames, knees
and separation read): +1 cm above the retarget's height already puts the right (rear) knee at 170°, +2 cm at
177°, +8 cm both knees at 177° with the legs fully extended — the retarget had lowered the hips to the reach
limit (`PLANT_REACH`), so **the 8 cm is not available**; the idle went back UP to that height (2 cm above the
previous round) and no further. Knees: `--knees-in 0.017` at that height → 39–45 cm apart (−14 / −15 from
53–60; the original build had 41–47). Shoot_01 rebuilt the same way on the final idle with `--torso-drop
-0.02` (a 3.6 cm RAISE of the take's hips, 0.500–0.533 rig m, level with the idle's so the mid-shot crouch is
gone; knees 129–159°): 39–46 cm apart (−18 / −23 from 57–69, 1 cm from the idle's), seams 0.0 mm / 0.0°,
boots on the floor on all six. Rule: **a torso raise is bounded by the rear foot's reach on the sway's peak
frame; probe the knee angle across the loop before promising a height.** (Tried the same evening and
REVERTED at the user's request: Cast_Staff_01 on Idle_Staff's legs with the take's step removed — `anim_nla_bake
--root-hold --legs-from Idle_Staff:1 --keep-poles`, then `--torso-drop 0.015` because the take's hips sit
1.3 cm above the staff idle's and locked the left knee over the idle's feet; "nope, let's revert this one".
The clip, its export, manifest entry and fit curve are HEAD's again; **`--root-hold`** stays in the bake tool:
the `root` control held at its frame-1 transform on every frame, for a take whose step should go.)
**Cast_Staff_01 redone from a new recording (2026-09-27, "P:\cast staff.glb, use frames 70 to 124, freeze both
feet").** The mannequin app (157 frames at 30 fps = the user's 124 × 1.25; `cast_staff_ref_mocap.glb` →
`cast_staff_ref_arm.blend`), frames 88–155: a raise of both hands to 1.4–1.5 m (source 91–120), a swing
(121–130), a settle; the source's hands 0.32–0.67 m apart. Same manifest as the previous take minus `drift root`
(in place), 68 frames (2.27 s). **The first build reused the staff GATE and was wrong** (user: "it looks
different from the original animation I see in Blender; the left hand should be below the right during the
cast"). Measured on a plain transfer (no gate, no arm passes; arms within 0–1° of the recording): the left
hand sits BELOW the right on every frame (0.45–0.76 vs 0.54–0.83 rig m) and 0.17–0.38 rig m OFF the right
hand's hilt axis with a projection near 0 — this performer's captured right-hand orientation puts the socket's
+Y ~90° off the hand-to-hand line, so the gate (project the left hand onto that axis, clamp, pin on IK)
dragged the left arm 76–109° off the recording, locked its elbow, and the previous take's `grip-follow
L:@0.15` then put the left hand ABOVE the right. **`staff_line "R,L"`** (`--staff-line`, `--staff-roll`, new
in the retarget) replaces the gate for this take: both hands stay where the capture has them and each is
rebuilt from its forearm's zero-twist hand (the `blade_along_arm` construction) turned so its hilt axis lies
on the line from the LEFT socket to the RIGHT (the top of the staff beyond the right hand, the left hand below
it on the shaft), two rounds because turning a hand moves its palm. Result: arms within 1° of the recording,
the left socket on the right hand's axis to 0.002 rig m, 0.17–0.38 rig m below it, left elbow 66–112°, worst
steps 28° (the swing's wrists), then `anim_nla_bake --pin-foot L,R` (both feet at their frame-1 transforms,
knees 117–147°), `hand_edited`, `grip_hands L`. Boots: the highest sole on the floor, the others ≤ 9 mm under.
**Reported, not changed: the staff is 0.52 m long below its grip point and the performer's left hand sits
0.30–0.69 m below the right, so on 30 of 68 frames (1–11, 36–49, 64–68: the start, the swing and the end) the
left fist is past the staff's foot, up to 17 cm.** Two ways out, the user's call: move `W_H2MagicStuff`'s Grip
15–20 cm up the shaft (every staff clip then holds it higher; AOE_Cast's left hand is 20 cm ABOVE the right and
keeps 0.5 m of shaft), or clamp the left hand's distance along the line (an IK pull that leaves the recording).
Rule: **a two-handed prop's second hand needs the LINE between the hands, not the first hand's hilt axis, when
the capture's hand roll is unreliable; measure the projection and the off-axis distance on a plain transfer
before choosing the gate.**
**Then the user's `Cast_Staff_01_Fix` (right arm, Combine) + "the left hand doesn't follow the staff handle from
14 to 43; use idle_staff after the cast, transitioning from frame 54".** The fix flattened (0.00 mm), then
`--shaft-hand L:0:14:43 --shaft-clamp -0.27,-0.08 --grip-pull --grip-reach 0.96 --fk-arm R`. Three things in
the seat tool: (1) **`shaft_hand` is SLOT-based now** (the hand slot from `unity_grips.json` on the other SLOT's
axis, as `grip_follow` already was) — the socket seat left the fist beside the shaft by the slot offset in
Unity; (2) **`--shaft-clamp MIN,MAX`** (rig m along the shaft, − = below the other hand) keeps the seated
hand on the prop: the staff's 0.52 m below the grip is 0.288 rig m, the performer's hand went to 0.38, so
frames 36–43 slide up the shaft (eased over `--grip-ease` 6 at both ends of the range, so 38–43 return to the
recording); (3) the seat is reach-aware: a spot beyond `--grip-reach` of the arm slides along the shaft
(inside the clamp) toward the shoulder's projection, and `--grip-pull` pulls the other hand in for what is
still short (none needed here). ⚠ The first run folded the left elbow to 12° with 88° right-arm steps: the
old socket seat ADDED the position after the rotation (`Matrix.Translation(pos_new) @ m_new`) and the slot
version already carried it, so the fully seated frames got a doubled position (z 1.45 rig m, above the head)
while the eased frames looked sane (their translation is lerped separately) — found by printing the wanted
socket per frame; a pass that "works at the edges and breaks in the middle" is a code path difference, not
geometry. Result: left elbow 66–112°, steps ≤ 28°, the left slot on the shaft to 0.0 mm over 20–37. **The
follow-up loop**: manifest **`next: "Idle_Staff"`, `next_at: 54`** → the controller builder adds an exit-time
transition on the Base state (exitTime (54 − 1)/68, fixed duration the remaining 14 frames) and
`SkeletonShowcase` adopts the loop the controller lands in (when the Base state is no longer the one-shot's
and is a looping clip, `_current` becomes that clip, its button highlighted) instead of crossfading back to
the loop it came from. The clip's own last 14 frames are the user's (their fix moves the staff away from the
left hand from 58 on, the lowering into the idle); no end blend was baked.
**AOE_Cast redone from a new recording (2026-09-27, "replace the existing aoe_cast with P:\aoe cast.glb").** The
mannequin app, 144 frames at 30 fps (4.8 s), the whole file (`aoe_cast_ref_mocap.glb` → `aoe_cast_ref_arm.blend`;
no frame range given): a slow left-hand gesture at chest height (frames 1–80, the right hand still at 1.0 m),
the right hand raised to 1.9 m (81–110), lowered (111–143). Plain transfer with the previous entry's settings
(`mode action`, `plant_feet`, `drift root`, `unwind_yaw` + `unwind_ref body`, `lift 0.004`, `ground_fit`, `fist
0.3`), the `aoe cast shoot.glb` build with its yaw-clip / shaft-hand bakes retired (`AOE_Cast_base` holds it).
Arms within 1–2° of the recording, spine 3–7°, steps ≤ 15° (the raise), knees 112–146°, root motion −9 cm
(the performer steps back; in place with the toggle off), boots: the highest sole on the floor, the others
≤ 10 mm under. The left hand never touches the staff in this take (0.19–0.71 rig m off the right hand's axis),
so no seat, no `grip_hands`.
**A split into a sequence, tried and REVERTED (2026-09-27).** The user asked for `AOE_Cast_Hold` (a loopable
31–61) and `AOE_Cast_Release` (75–144) played in the demo as hold → delay → release, like the creatures pack's
knockback / get-up. Built as three clips (Start 1–30, Hold 31–53 after a loop-point search, Release 75–144),
the hold's loop closed by a manifest-driven bake, its torso re-centred over the feet, the joins blended, a
boxed UI group with a delay row — and rejected: "the hold animation is bad, only half of what I expected is in
it, the body position shifts from start to hold". Lesson: **a hold cut from a one-shot take is not a hold** —
the performer never held still or cycled, so any loop point is a compromise and the re-centring that makes it
stand is what pops at the join; a hold needs to be RECORDED as a loop (the performer channelling in place for a
few seconds), then the pieces cut from it share its heading (per-piece `unwind_yaw` broke the joins: pieces of
one take must keep the take's yaw). AOE_Cast is the single 144-frame clip again (its action was never removed,
re-exported with the fit; the three clips, exports, fit curves, build-state entries and the sequence entry
removed). What stays, for a recorded hold: the batch's manifest keys **`bake`** (a list of `anim_nla_bake` args
run on the fresh retarget before the export) and **`loops`** (import a non-idle/loco clip looping); the bake
tool's **`--torso-shift X,Y`** (the torso moved horizontally over the IK feet) and `end_blend` skipping the
`root` control (travel, not pose); `SkeletonShowcase.Sequences` (a step list with `holdSeconds`: one button per
step boxed with a delay row, each button playing from its step, the running step highlighted, a looping step
held through the pending follow-up, one-shot steps advancing on their end — the table is empty now) and
`DemoUI.CreateGroup` (ported from the creatures pack). ⚠ A play-mode test right after a script compile ran in
the STALE play session (Time.time 281 s): the domain reload keeps the showcase instance but empties its
non-serialized clip lists — stop play mode before a test that follows a compile.
**AOE_Cast on Idle_Staff's legs (2026-09-27, "fix the legs pose for aoe_cast, use the pose from idle_staff").**
After the user's `AOE_Cast_Fix_01` bake: `anim_nla_bake --root-hold --legs-from Idle_Staff:1 --keep-poles`
(the staff idle's constant leg controls on every frame; the take's 5.5 cm root step held at frame 1, `drift
root` dropped, the clip imports in place), then `--torso-drop 0.012`: over the idle's feet the take's hips
reached 0.541 rig m and the left knee 169° (the straight-leg risk), 2 cm down gives hips 0.484–0.529 and knees
118–152°. Feet identical to Idle_Staff's on every frame, hips within 14 mm of the idle's on frame 1 and 6 mm on
the last frame; boots on the floor on all six after the fit. ⚠ Two bridge
lessons: `execute_code` REQUIRES `"action": "execute"` (a call without it fails validation, and a JSON with C#
`
` literals written through a shell heredoc arrives with real newlines — run C# from a file, `runcs.py`-style);
and `ScreenCapture.CaptureScreenshot` followed by `EditorApplication.Step()` while PAUSED stalls the bridge (the
capture never flushes and every later call times out; the editor itself stays responsive and leaves play mode
on the next stop) — render a temporary camera into a RenderTexture + `ReadPixels` instead, which is synchronous.

### Armour modules as their own assets (2026-09-27, "have them separate as weapons in a project")

The user chose the hard route ("since we have everything saved in git"): the character models are
BODY-ONLY and every armour piece is an asset of its own, with a MAP of what each skeleton wears by
default. `export_fbx.py` writes `SK_<Character>.fbx` (skeleton + `Body`) and one
`Models/Armor/<Character>/SK_<Character>_<Module>.fbx` per module (the same 68-bone skeleton + that
skinned mesh; 48 files: Knight 9, Archer 7, Assassin 8 incl. `Pants`, Mage 8 incl. `Robe`, Necromancer
8, Warrior 8, no Helm); the import setup makes the modules **Generic / No Avatar** (as the rigged
bow: `animationType None` would drop the skin). **`ArmorModule`** (`Demo/Scripts/`, on each
`A_<Character>_<Module>` prefab): `Attach(characterRoot)` rebuilds the renderer's `bones` by NAME
against the character's Armature transforms, sets `rootBone` the same way, copies the body's
`localBounds`, reparents the piece next to the body, marks it with an **`ArmorPiece`** (character,
module, source prefab) and destroys the module's own skeleton; `Wear(prefab, character)` instantiates
and attaches in one go, in the editor (DestroyImmediate) or at runtime. ⚠ `ArmorPiece` must live in
its own file: a MonoBehaviour declared beside another class cannot be added by `AddComponent` (the
first build dressed every character with zero markers and no error). **The armour map**
(`CharacterPrefabBuilder.ArmorMap`, character -> `Char:Module` entries) is what each `PF_<Char>` is
dressed with at build time; a set may borrow across characters. **`SkeletonModules`** (rewritten)
holds `defaultModules` (the map's prefabs, set by the builder), finds their worn pieces on Awake by
the markers, toggles them (`Set` re-wears a piece whose instance is gone), and `Wear` / `Remove` /
`ToggleWear` take any module prefab (a borrowed piece is destroyed on removal, a default one only
switched off). The demo's modules panel: the current character's set as toggles, then one section
per other character ("Knight armour" ...) whose buttons wear or remove that piece; All / None act on
the defaults; `SkeletonShowcase.armorCatalogue` is filled by the scene builder from the map. Verified
2026-09-27: all six prefabs dressed (every piece's 68-bone array equals the body's, the root bone the
body's), 48 module prefabs, and in play mode the Mage wearing the Knight's helm and chest through
`Walk_Fwd_01` on its own bones. The verify / grounding tools instantiate `PF_<Char>` now (the models
have no boots to measure). Not done: the Asset Store validator on the new layout; Unreal notes (one
skeletal mesh per module against the shared Skeleton is the standard there).

### Death candidates (2026-09-27, "redo the deaths: too long a wind-up, the models end up floating; a prompt that falls immediately; five, pick later")

Five Kimodo generations with the skeleton profile, 100 frames each (`death_instant_{drop,face,back,knees,puppet}`,
seeds 3 / 5 / 13 / 17 / 23), mode `death`, as `Death_03`–`Death_07` next to the old `Death_01` / `02`; all
seven in the demo's Death section (the hold, then the return to the idle). **Kimodo starts standing whatever the
prompt says**: measured (`deatheval`-style: the frame where the hips have dropped 5 cm rig), the plain builds
stand 0.6–1.2 s before dropping (the old two 1.43 / 0.87 s). A round that trimmed each clip with `src_begin`
from that measurement was REJECTED ("your estimates for a fall start are off; use the full clips, I will tell you
the start frame for each"), so the seven are the plain FULL builds again and the user's frame numbers go into
`src_begin` (the clip's frame N = the source's frame N, 30 fps, no time_scale). Also tried and withdrawn at the
user's request ("no grounding fix here, many body parts still end up floating; the grounding is a separate
task"): a per-frame `ground_fit` (wrong for a corpse: the highest model's lowest point on the floor sank the
others 3–10 cm, a lying body's spread across the six being far larger than the soles') and `ground_ignore
Robe,Skirt` + `lift 0.003`. What that round measured, for the grounding task: rendering the LAST frame on the
Knight with the camera on the corpse (`deathrender`-style, the corpse's bounds baked) showed the corpse's lowest
vertex 7–12 cm up on every death, old and new, while the whole-clip minimum read ~0 only because a hand touched
the floor mid-fall — the retarget's grounding takes the lowest of all six characters' meshes and a lying
Necromancer's robe hangs far below the body, so the other five were lifted by the robe's overhang; with the
robes and skirts out of the measure the Knight's corpse rested within 2–21 mm on all seven, but the cloth then
hangs through (the Mage's robe 3–22 cm, the Necromancer's up to 50 cm prone, the skirts up to 9 cm) and the
user reports parts still floating. **The decision (user, same evening: "don't use any clothes when calculating
the thickness, just a body-part average; meshes overlapping the ground are fine, I care about a natural-looking
animation over clipping").** Two things stacked: the robe overhang (the bug) and the armour's own thickness (a
lying Knight rests on pauldrons and backplate, so his hips centre sits ~15 cm up where the recorded human's sits at
5; and the six bodies differ, so one shared Root height cannot ground them all). So every death entry now grounds
on the six bare BODY meshes only — `ground_ignore "Robe,Skirt,Pants,Chest,Helm,Glove,Boot,Greave"` (the retarget's
floor measure keeps only meshes whose names contain none of these, i.e. `Skeleton*_Body`) — with `lift 0`:
Death_05's last frame has the hips at 0.06 m engine against the human's 0.05, the Archer's body on the floor, the
Knight's chest plate 7 cm into it, the Mage's robe 15 cm and the Necromancer's 18 cm, all accepted. The engine-side
per-character curve stays an option if clipping ever matters. Rules kept: **check a corpse on the LAST frame's
lowest vertex, the whole-clip minimum hides it; Kimodo's standing start is trimmed from the user's frame, not
from a heuristic; and a lying body is grounded on the BONES, its armour and cloth clip into the floor.**
**Then "still off; what I want is the original Kimodo animation, just raised 6–7 cm: during the animation some
nodes fall under the ground and you apply the raise based on that node to ALL the bones, so they float."** Two
things, both in the retarget and both new manifest keys on the seven deaths: **`ground "none"`** (`--ground
none`: no per-frame floor correction at all, the export lift the only offset) with a plain **`lift 0.065`**, and
**`hips_map "floor"`** (`--hips-map delta|floor`): the torso target used to be the rig's REST torso plus the
hips' offset from the clip's FIRST frame, scaled (`delta`) — right for a clip that starts standing at the rest
height, but a corpse then ends at rest minus the drop: Death_05's source pelvis goes 0.896 → 0.050 m and the
rig's ended at 0.093 rig m (0.17 m engine) where the proportional height is 0.028. `floor` maps the source's
hips HEIGHT proportionally from the floor (DEF hips z = source z × the hip-height ratio; the bind's hips land
on the rest, so a standing clip is unchanged within the source's own crouch): Death_05 now ends at 0.042 rig m
(the pelvis pivot's offset from the torso control on a rotated pelvis is the rest), 0.14 m in Unity with the
lift. Measured on the Knight's LAST frame (`deathrender`-style corpse bounds): lowest vertex −4..+2 cm on six of
the seven, −13 cm on Death_07 (the puppet's limb through the floor), against +7..+12 cm before. Rule: **a death's
hips height is proportional from the floor, never a delta from the standing start; and grounding is a constant
lift chosen by eye, not a per-frame fit to the lowest node.**
Then "still off: they start off the ground now, which makes sense for a 6.5 cm lift; no changes to the Kimodo
animations this time": **`lift 0`** on all seven, so the clip IS the generation on the rig (no floor pass, the
hips proportional from the floor, no lift). Knight, Unity: the standing first frame's lowest vertex within
±2 cm of the floor on every clip; the corpse's lowest vertex on the last frame −5..−13 cm (Death_07 −20 cm),
i.e. the lying body clips into the floor by its own thickness, as the user accepts.
**The pick (2026-09-27, "we keep 03, 04, 05, 07")**: renumbered to `Death_01` (drop, `death_instant_drop`),
`Death_02` (face-down, `death_instant_face`), `Death_03` (on the back, `death_instant_back`), `Death_04` (puppet,
`death_instant_puppet`) — manifest entries, actions (the seven dropped from the anim file and the four rebuilt
under the new names), exports, build state, the showcase's Death members, the controller and the demo scene; the
old `Death_01` / `Death_02` (`death_back`, `death_crumple`) and the knees candidate are removed from the pack (their
GLBs stay in `External Anims/Kimodo/`). **The user's ranges (2026-09-28, Blender clip frames of the full
builds, 1-based, both ends inclusive): Death_01 18–93, Death_02 1–87, Death_03 8–77, Death_04 1–88** → manifest
`src_begin` = start − 1 (0-based source frames; omitted for a start at 1) and `src_end` = end − 1 (inclusive),
so clip frame N of the full build is source frame N − 1: 76 / 87 / 70 / 88 frames (2.5 / 2.9 / 2.3 / 2.9 s).
The controller's states reference the clip assets, so a length change needs no controller rebuild.
**Death_01's feet (2026-09-28, "can't control the legs with foot_ik; freeze the feet from frame 1 to 27, they leave
the ground from frame 1 because of the torso's height").** Measured: frame 1 has both boots on the floor (+6 / −5 mm
rig), then the generation raises the hips 2.8 cm rig by frame 13 and both feet lift 3–4 cm and slide 9 cm back before
the fall (the wind-up). Death mode's legs are FK from the source, hence no foot_ik control. `anim_nla_bake --action
Death_01 --result Death_01 --ik-legs --pin-foot "L:1:1:27,R:1:1:27" --pin-ease 0:8 --leg-reach 0.985`: legs to IK
losslessly, both feet held at their frame-1 transforms over 1–27 (eased out over 8 frames into the fall), and the new
**`--leg-reach K`** (bake tool): after the pins, per frame, the torso is lowered by the least amount that keeps every
IK foot target within K of its leg (hip → knee → ankle), the need running-maxed over ±2 frames and low-passed twice,
0 where nothing is needed — here up to 7 mm rig on frames 1–23 (knees peak at 160°, no lock; a constant `--torso-drop`
would have moved the whole fall). Feet on their holds to 0.0 mm, no leg bone above 15° per frame, the largest
acceleration at the release on 27. `hand_edited`, `Death_01_base` is the retarget. Rule: **a held foot under a rising
source needs a per-frame reach drop, not a constant one.**
Then the user's `Death_01_Fix` (Combine over the strip: both feet with two keys each over frames 37–70, the right thigh
FK and the torso with one key) baked by `anim_nla_bake -- --result Death_01 --save` (flat = stack to 0.00 mm; the
first `_base`, the retarget, kept), re-exported with `--export-only --force`.
**Deaths and the finger idles (2026-09-28, three "small issues").** (1) "hand_idle_l/r are not highlighted when
active": the two clips sat in the demo's "Other" section as plain buttons (no Base state, nothing to highlight).
They are a section of their own now, **"Hand idle (empty hand, toggle)"** (`SkeletonShowcase.handIdlePrefix`):
each button is lit while its finger layer's TARGET weight is 1 (`SkeletonWeapon.IsFingerIdleActive`: the hand
empty, the toggle on, no death playing), refreshed every 8 frames, and clicking it toggles
`SkeletonWeapon.fingerIdleLeft / Right` (`SetFingerIdle`; off = the clip's own fingers). (2) "when a death plays,
twitch and hand idle should stop": `Play` calls `SetDeathSuspend(IsDeath(clip))` — every `TwitchLoop_NN` layer to
weight 0 and `SkeletonWeapon.SetFingerIdleSuspended(true)` (both finger layers fade to 0 over `fingerFade`) for
the death and its hold, restored by the next `Play` (the twitch toggles and the hand-idle toggles keep their
state; `SetTwitchLoop` respects the suspension). (3) "bake the hand idle into the deaths so the fingers don't
look bad": bake tool **`--fingers-from "L:Hand_Idle_L:1,R:Hand_Idle_R:1"`** — every finger control the source
action keys for that side (thumb / f_* / palm chains) taken frame by frame from `Hand_Idle_L/R` starting at
frame 1 (wrapping), so with the finger layers off the death shows the relaxed sway instead of the retarget's
constant curl. On Death_01 run by hand (hand-edited), on Death_02–04 as the manifest **`bake`** list (run on the
fresh retarget before the export). Rule: **a clip that turns the finger layers off must carry the relaxed hand
itself.**
Then "adjust death_02/3/4 so that foot_ik.L/R controls the feet": `--ik-legs` first in their `bake` lists (the
retarget's FK legs converted to IK losslessly on every frame, the foot/toe controls on the DEF result, the knee
pole out through the FK knee), so all four deaths are editable through the foot IK controls like Death_01.
**"Death 2/3/4 now have their origin shifted" (2026-09-28).** Measured: the rebuilt clips' torso control sat at a
CONSTANT offset (−0.75, −0.30, −0.47 rig m on every frame, Death_03 included) equal to Death_02's held last pose;
the `_base` copies and two dry bakes on them were clean, so the bake tool was not it. The cause is the RETARGET
reading the rig's REST transforms (`T_rest`: the torso's rest position among them) from a rig that was still
POSED: the file had a `Death_02` strip (Replace) on the rig's NLA under `Death_02_Fix` active in Combine, and
`glb_retarget` only cleared the active action before `zero_pose()` — an unmuted strip keeps posing the rig
(holding its last frame beyond its range), so every torso target was built on the corpse's torso. A first fix
that muted the tracks only for the WRITE changed nothing (the rest read comes first); the retarget now creates
the animation data, mutes every NLA track and sets the active blend to Replace BEFORE the rest read and keeps
them so for the run (mutes restored before the save; the bake tool that follows in the batch restores the
user's fix and re-points the strip). This is also the "not reproduced, cause unknown" build of 2026-09-25
(every arm bone 60–74° off after `anim_weapon_ref --check` had left a posed action live). Side effect noted: the
user's first `Death_02_Fix` (empty, 0 f-curves, no fake user) was dropped by that rebuild's save. Rule kept and
widened: **any tool that reads or writes a named action must silence the NLA first, and "the rest pose" is only
the rest pose with no action AND no strip live.**
**Death_02_Fix (2026-09-28, "added Death_02_Fix, bake it").** Both feet and the torso, two keys each over 38–87, in
Combine over the strip: flattened (0.00 mm), `hand_edited`, `Death_02_base` the retarget. The leg scan after the
bake showed the RIGHT SHIN turning 87° in one frame at 52 with the knee jumping 17 cm — and a dry `--ik-legs` on the
`_base` reproduced it, so it was the IK conversion, not the fix (the tool's own "knee within 9.5 mm" check missed
it). Cause: **the pole memory rule** (`leg_pole` / `ik_pole`: "a side flip vs last frame keeps the old plane")
fired on a knee 7–16 cm OFF the axis that genuinely swung across it as the leg folded in the fall, held the old
plane for 30 frames and snapped when the memory let go. The clause now applies only while the knee is within 4 cm
of the axis (both tools); a bent knee's FK plane is the truth. Then a 39.5° step at 68: from frame 67 the user's
right foot placement puts that leg at its FULL length (knee 177°, hip→ankle 0.472 rig m = the leg), where the
swivel is undefined and the refinement loop chased noise (the pole moved 20 cm between two locked frames) — a
near-straight reference knee now takes the memory's plane without refinement. Death_02 re-aimed (`--action
Death_02 --result Death_02 --ik-legs`: the feet are the fix's, the poles from the retarget's FK knees),
re-exported. **Reported, not changed: the right knee is locked straight on frames 67–87 by the fix's foot spot
(the straight-leg flip risk in Humanoid); a foot ~3 cm closer to the hips would keep it bent.** Rule: **a pole
memory is for a knee ON the axis; a bent knee that changes side has really changed side.**
**Death_03_Fix (2026-09-28):** both feet (two keys each) and `hand_fk.R` (three) over 34–70, Combine; flattened
(0.00 mm), no leg bone above 14° per frame, `hand_edited`, `Death_03_base` the retarget, re-exported.
**Death_04_Fix (2026-09-28):** chest, head, neck, torso, both feet and both forearms (one or two keys each over
1–88, Combine); flattened (0.00 mm), no leg bone above 13° per frame, `hand_edited`, `Death_04_base` the retarget,
re-exported. All four deaths are hand-edited now; their `bake` lists record what built the bases.
**Death_04's feet on their toes (2026-09-28, "freeze the feet from frame 1 to 45 at the toes' position, even when they
bend").** Measured: over 1–45 the balls of the feet drifted up to 4 cm sideways and rose up to 4 cm while the heels
lifted 6–9 cm (the body falling forward over the toes). New pin mode **`SIDE:ref:from:to:toe`** (bake tool): the
BALL of the foot (the `DEF-toe` joint) is held at the reference frame's spot in all three axes while the foot keeps
each frame's own rotation and its ankle height relative to the ball, so the heel lifts and the foot pitches on its
toes; the toe control is the clip's own (a full hold would freeze it). `anim_nla_bake --action Death_04 --result
Death_04 --pin-foot "L:1:1:45:toe,R:1:1:45:toe" --pin-ease 0:8 --leg-reach 0.985`: balls on their spots to 0.0 mm
on every held frame, the release eased over 8 frames, the torso lowered up to 7 mm rig on frames 1–19 where the held
feet would have locked a knee, no leg bone above 13° per frame (the toes 19° at the release), re-exported.
**Death_03 the same (2026-09-28, "freeze the feet from frame 1 to 31"):** the balls had slid 3–7 cm back and sideways
over 1–31 with the heels flat (this fall goes backwards). `--pin-foot "L:1:1:31:toe,R:1:1:31:toe" --pin-ease 0:8
--leg-reach 0.985` (no frame needed the drop): balls on their spots to 0.0 mm, knees 84–134°, no leg bone above 14°
per frame, re-exported.

### The Asset Store showreel (2026-09-28, "a 45 degree static view on a model; each skeleton cycles through its weapons, playing its attack once")

`Demo/Scripts/ShowreelRecorder.cs` + the menu **Undead Legion / Record Showreel (play mode)** (`Demo/Editor/ShowreelMenu.cs`,
which enters play mode and starts the recorder; a `ShowreelRecorder` placed in the scene is used as configured, else a
temporary one with the defaults). It records a PNG frame sequence OFFLINE: `Time.captureDeltaTime = 1 / fps` fixes the
simulation step, so the frames are the same whatever the machine renders at (the user's "not sure this PC can render
at high enough settings": it just takes longer), a dedicated camera at `azimuth` 45° / `elevation` 12° / `distance` 4.3 m
looking at 0.95 m (FOV 32) is rendered by hand into a 1920×1080 RenderTexture with 4× MSAA and read back per frame, the
UI canvases hidden, root motion off (every attack in place), the turntable off. The sequence is a table (`plans`: one
row per character with its loadouts in order; `attacks` / `idles`: the clip per loadout name), defaults in the script:
Knight sword + shield → Attack_R_Slice, longsword → Attack_2H_01; Warrior axe + shield → Attack_R_Slice, battle axe →
Attack_2H_02, mace → Attack_R_Stab; Archer bow → Shoot_01, dagger → Attack_R_Stab; Assassin two daggers →
Attack_L_Slice, dagger → Attack_R_Stab; Mage / Necromancer staff → Cast_Staff_01, wand → Cast_Wand_01; the weapon's
idle first (Idle_TwoHanded / Idle_Bow / Idle_Staff, else Idle), `holdBefore` 0.8 s, the attack once, `holdAfter` 0.9 s,
`characterGap` 0.4 s. Frames go to `<repo>/Showreel/frames` (gitignored), then **`python tools/unity/showreel_encode.py`**
encodes them with the ffmpeg bundled in the `imageio-ffmpeg` pip package (installed user-scope; no system ffmpeg):
H.264 crf 18, yuv420p, faststart → `Showreel/showreel.mp4`. From the bridge the run is `ShowreelMenu.Start()` in play
mode and a poll of `Done` / `FramesWritten` / `Status` (session script `showreel_run.py`-style).
**"The video quality is low; do a small test of the highest this machine can do."** The first run was the demo's
own quality (the PC level: MSAA off in the URP asset, a 2048 shadow map split over 4 cascades to 50 m, no AA) at 1080p
with the figure small in frame: aliased edges, coarse texture pixels. Offline, the machine's speed caps nothing, so
the recorder's **`maxQuality`** (default on) pushes everything the runtime API allows, on the LIVE URP asset, and
restores it at the end: the highest quality level, forced anisotropic filtering, mipmap limit 0, LOD bias 4; the URP
asset at 8× MSAA, HDR, render scale 1, ONE shadow cascade of 4096 over `shadowDistance` 10 m (the whole map on the
character: sharp contact shadows); the recording camera with post-processing on for SMAA (high); the texture at 8×
MSAA. `maxLoadouts N` limits a test run. The 4K test (3840×2160, the Knight's sword-and-shield slice, distance 3.4 /
look 0.9 / FOV 30, ~1 frame/s to write) is crisp at 100 % (helmet dents, rust, clean edges); `showreel_encode.py
--scale 1920:-2` (lanczos) makes a supersampled 1080p from the same frames. ⚠ Poll a long recording from the
frames folder (`done.txt` is written at the end), not through the bridge: a 4K PNG per frame keeps the main thread
busy and the bridge's calls time out (the first run's runner stalled that way and left play mode on).
Then "no need for 4K, just quality maxed; also the 45° of the other side": the full showreel twice at 1080p native
with `maxQuality`, framed as the test (distance 3.4, look 0.9, FOV 30), `azimuth` +45 (the character's right side
nearest the camera) → `Showreel/showreel_right.mp4` and −45 → `showreel_left.mp4`, crf 16 (session script
`showreel_both.py`-style: play, configure + `Begin()` through the bridge, poll the frames folder, stop, encode).
**"Even higher quality, still 1080p; headless, easier on RAM" (2026-09-29; the user chose the left angle).** Two
additions. (1) **`supersample`** on the recorder (default 2): the camera renders into a texture of 2× the output
(3840×2160 at 4× MSAA), a bilinear `Graphics.Blit` box-filters it down to the output size (exactly 2×2 texels per
pixel), the PNG is read from the small texture — 4 samples per pixel on top of MSAA + SMAA, and the soft-shadow
quality of every light forced to High (`UniversalAdditionalLightData.softShadowQuality`). (2) **Headless**:
`tools/unity/showreel_headless.py [--side left|right] [--supersample 2] [--max-loadouts N]` launches
`Unity.exe -batchmode -projectPath skeletons -executeMethod UndeadLegion.Demo.ShowreelMenu.RecordHeadless` (no
`-nographics`: the GPU still renders offscreen, only the editor UI is skipped — the interactive editor must be CLOSED,
one editor per project) with the settings as `SHOWREEL_*` environment variables; `RecordHeadless` stores them in
`SessionState`, opens the demo scene and enters play mode, an `[InitializeOnLoadMethod]` hook re-arms after the
domain reload, starts the recorder once the showcase exists and `EditorApplication.Exit(0)`s when it is done; the
launcher polls the frames folder, then encodes (`Showreel/headless_<side>/frames`, `showreel_<side>.mp4`, the Unity
log in `Showreel/headless_<side>.log`). ⚠ Batch mode never reaches an end-of-frame, so the capture yields `null` there
(`Application.isBatchMode`) instead of `WaitForEndOfFrame`, which would hang forever. Test: one loadout at 2×,
compile + scene + 107 frames + exit in ~75 s.
**Stages (2026-09-29, "split it into chapters with a clear transition, render each separately, we stitch later";
"the video quality is fine"; then "change chapter to stage, modularity to modular, the angle to 30 from 45, no fade
in/out inside a stage, we do the fades when stitching").** The recorder is a STAGE player: a stage is a list of `Step`s
(character, armour pieces to wear / take off as `Char:Module`, weapon loadout, idle, an optional attack, caption title +
line, seconds), it opens on a static TITLE CARD on black (`titleCardSeconds` 1.6) and hard-cuts to the first character;
a change of character is a hard cut too (two uncaptured frames settle the new character first). The fades of the first
build (in from the card, through black between characters, out at the end) are gone: the stitch does them. A CAPTION
PANEL (title + one line, the demo's built-in font; 600 px wide since the second round, the 900 px box overlapped the head at 30°; the title is sized to the box from its `preferredWidth` in `ShowCaption`, one line always — uGUI's best-fit never shrank it under Wrap + Overflow, nor under Wrap + Truncate) sits top-left over the sky — a bottom panel covered the figure's feet —
on a world-space canvas parented to the recording camera and sized to its frustum at 1 m (a screen-space canvas is not
part of a hand-rendered camera). The camera's `azimuth` default is **−30** (the character's left side nearest; 45 for
the first two rounds). `stage` picks the step list: **`modular`** (the user's script, title card "MODULAR": Warrior,
Assassin, Archer, Mage, Necromancer, Knight on `Idle_03` 3 s each; then the Knight wearing the Warrior's chest, the
Archer's helm, the Warrior's greaves and the Assassin's gloves one at a time — the character's own piece of that module
off, the borrowed one on through `SkeletonModules` and the showcase's armour catalogue; then on that mixed Knight sword +
shield and axe + shield on `Idle_03`, sword / dagger / two daggers on `Idle_02`, mace on `Idle_01`, longsword and battle axe
on `Idle_TwoHanded`; then the Archer's bow on `Idle_Bow`, the Necromancer's staff on `Idle_Staff`, the Mage's wand on
`Idle_03`) and **`weapons`** ("weapons & utils" since 2026-09-29, the old id `attacks` still accepted; title card "WEAPONS & UTILS"; each
class's utility one-shots before its attacks and a death after, the corpse held `deathHoldSeconds` 1.6: Warrior `Taunt_01` … `Death_01`,
Knight `Taunt_02` + `Rally` … `Death_02`, Assassin `Cutthroat` … `Death_03` (both at normal speed, only the attacks at 1.6×),
Necromancer `Summon` … `AOE_Cast` + `Death_04`; output `showreel_weapons.mp4`; a death keeps its root fixed and falls in the
hips, so during a death step the camera follows the HIPS horizontally and sinks `deathCameraDrop` 0.5 m (damped, rotation unchanged) —
following the root left the corpses at the frame's edge, the Necromancer's half out of it; rewritten 2026-09-29 to the user's script, replacing the per-loadout plan tables: Warrior on `Idle_TwoHanded`
with the longsword then the battle axe, `Attack_2H_01` + `02` each; Knight on `Idle_1H_Combat` (third script, 2026-09-29): `Block_L_Idle`
HELD from the start (a step's `holdOn`: the showcase's `ToggleHeld` on its layer, so the shield stays up while the right attacks
play full-body on Base), axe + round shield `Attack_R_Slice`, sword + heater shield with both right attacks under the block, then
the sword alone with the block released (`holdOff`) and both attacks (the mace step and the stab on the axe are gone); Assassin on
`Idle_1H_Combat`: one dagger with both right attacks, two daggers with both left attacks, all at
**`attackSpeed` 1.6** (the Animator's speed during the attack, the capture shortened to match); Archer on `Idle_Bow` with `Shoot_01`;
Mage on `Idle_03` with both wand casts; Necromancer on `Idle_Staff` with both wand casts and `Cast_Staff_01`; then "skip
attack_r_stab for the axe + round shield and the mace": the axe plays the slice, the mace only the slice. **Root motion is ON for
this stage** (`attacksRootMotion`; the user: "this requires camera follow and a recenter after each attack, seamless, no camera
lerp during it"): `FollowCamera` runs before every captured frame — the camera's POSITION closes on the character's root + its
original offset at `followDamping` 4/s (the lag is what shows the travel), its rotation never changes; `RecenterSeamless` after each
attack's settle puts the character back on the spawn point facing forward and applies the SAME rigid transform (the translation
and the yaw, since the recorded attacks leave the body a few degrees turned) to the camera and the follow offset in the same
frame, so the rendered picture is identical across the recenter; a new character resets the camera to its home transform (a hard
cut anyway), so the yaw corrections never accumulate across characters. The showcase's `resetFacing` is a no-op, so the recorder
owns the recenter A step carries a LIST
of attacks (`holdAfter` between them, the caption line naming the running clip), and a loadout change on the same character keeps
the running idle instead of restarting it; captions "Skeleton X | weapon") and **`movement`** (2026-09-29, "the chapter with movement animations; _01 for the warrior and archer
skeletons, _02 for the others", then "only use warrior for the low-rank animations and mage for the high-rank": title card
"MOVEMENT", then the Warrior with the shambling `_01` set and the Mage with the upright `_02` set (the six-character first cut ran
92 s; two characters, 10 clips, ~33 s) — walk forward, run, walk back, strafe left, strafe right, `movementSeconds` 3 each,
looping IN PLACE with the character's usual weapon (axe + round shield, bow, two daggers, staff, staff, sword + shield); the
caption carries the clip name and the speed-table figure, since root motion at 0.2–1.9 m/s would carry the figure out of the
static frame within the 3 s; since 2026-10-01 it ends on the Warrior's reactions, "include hit/staggers at the end of movement stage": `Hit_01` + `Hit_02` additive over `Idle_1H_Combat`, then `Stagger_01` + `Stagger_02` with root motion ON for that step only — a step's `rootMotion` flag switches the browser toggle and re-bases the follow offset, the camera follows the step back and `RecenterSeamless` puts the character back after each; 1274 frames, 42.5 s; the YouTube cut rebuilt from it, 3:59). `SHOWREEL_STAGE` / `showreel_headless.py --stage` select it headlessly (outputs
`Showreel/headless_<stage>_<side>/`, `showreel_<stage>_<side>.mp4`, `--side left` = −30); in the editor a session script
sets `rec.stage` before `Begin()` (`stage_test.py`-style: play, configure, poll the frames folder for `done.txt`, stop,
encode to `Showreel/showreel_<stage>.mp4`). ⚠ After the Archer head fix the user reported "the recorded video has the
Archer helm issue that was fixed in the editor": measured in the recorder's own run (a `probe_stage.py`-style run stopped after
the helm step, the helm's baked centroid in the head bone's frame) the offset equals the editor's, and in the video the Knight's
borrowed helm sits exactly as the Archer's own (`Showreel/helm_check_archer_vs_knight.png`); the pre-fix `showreel_modularity.mp4`
had stayed in the same folder and was deleted. Rule: **a stale render beside a fresh one is a report waiting to happen; remove
superseded outputs when re-rendering.**

**The YouTube video (2026-09-29, "a full video for youtube, both unity and unreal; royalty-free music; a fantasy/RPG font").**
`tools/unity/showreel_youtube.py` builds `Showreel/undead_legion_showreel.mp4` (3:49, 1080p30, ~80 MB) from the three stage videos: an
intro card ("UNDEAD LEGION / Modular Skeleton Army / for Unity & Unreal Engine"), a "What's inside" card (6 classes, 48 armour modules,
12 weapons, 40+ animations, one rig: Unity Humanoid | Unreal skeleton), a card per stage, the stages with their plain recorder title
cards cut (the first 48 frames), an outro, every join an `xfade fadeblack` of 0.8 s. Cards are PIL renders over a blurred, darkened stage
frame with a slow push-in: **Cinzel Decorative / Cinzel / EB Garamond** (Google Fonts, SIL OFL 1.1). Music: Kevin MacLeod's **"Five
Armies" crossfaded into "Heroic Age"** (incompetech.com, **CC BY 4.0 — the credit must go in the video description**; FreePD, the CC0
source first tried, has closed), faded and normalised to −14 LUFS (measured −13.4). Fonts and music are fetched into `Showreel/assets/`
(ignored). The in-scene captions stay in the demo's built-in font; putting Cinzel in them means importing the font into the project and
re-recording the stages.

**Shoot_01's feet frozen (2026-09-28, "update shoot_01, freeze the feet position").** The legs are the bow idle's
constant controls, yet both feet drifted 1 cm over the clip, identically: the ROOT control moved (the take's own
travel, up to 11 mm rig, left on `root` when the clip went in place; the feet are its children). `anim_nla_bake
--action Shoot_01 --result Shoot_01 --root-hold`: the root at its frame-1 transform on every frame, both balls of
the feet at 0.000 on every frame, the start and end still equal to Idle_Bow's frame 1 to 0.0 mm / 0.0° on every
landmark, the BowAttach 15 / BowRelease 21 events intact on the re-imported clip. Rule: **two feet that drift by
the same vector are the root, not the legs; hold the root.**
**`Idle` → `Idle_01`, and the idles' feet frozen in the engine (2026-09-28, "rename idle to idle_01; there is a subtle
feet drift for idle, idle_02, idle_03 - freeze them").** The rename: the anim file's `Idle` / `Idle_base` →
`Idle_01` / `Idle_01_base` (`Idle_Fix` keeps its name), the manifest entry and every `Idle:1` / `blend_to Idle`
reference in other entries (`Idle_01:1`), the export (old FBX + meta deleted, re-exported under the new name),
`SkeletonShowcase.idleClipName` and every section's idle preference, `ShowreelRecorder`'s fallback, the tool defaults
(`build_twitch_controller`, `demo_smoke`, `grip_sheet`, `ground_clip`, `anim_author_impaled`, `anim_fix_idles`), the
controller and the demo scene rebuilt. `Idle_02` got a manifest entry (`hand_edited`, not reproducible from it) and
`Idle_03` the `hand_edited` flag, so all three export through `--export-only`. **The drift**: measured in Blender the
three idles' feet, foot controls and root are static to 0.0 mm over the whole loop; in Unity the feet wander
1.5–2.6 mm horizontally and 1–4 mm vertically while the hips sway 40–70 mm — Humanoid's leg reconstruction (the muscle
round trip; the export's leg de-twist keeps it small but not zero), and the imported foot IK goals carry the SAME error
because Unity generates them from the retargeted pose (goal height varying 5–9 mm on Idle_01 / Idle_03, 0.7 on Idle_02),
so `iKOnFeet` on the states cannot remove it. Two changes: Idle_01's per-frame `ground_fit` is replaced by a constant
`lift 0.0036` (the fit curve's mean on top of the old default: a vertical curve baked into the Root only rides into the
goals); and **`SkeletonFootLock`** (`Demo/Scripts/`, on every `PF_<Char>` from the prefab builder; the controller's Base
layer has `iKPass` on): once the Base layer has settled on a looping clip whose name starts with `Idle` (no transition
running) it captures both feet's IK goals ONCE, in the character's space, and holds them at full weight (position +
rotation) until the next state begins, fading in over 0.15 s and out over 0.12 s; the hips keep swaying and the knees
follow through the IK. Measured in play mode (a per-frame probe on the Knight, 360–540 frames per clip): feet and toes
at 0.00 mm horizontally and vertically on all three idles with the lock, hips 40–70 mm as before. Rule: **a few mm of
foot wander under a Humanoid sway is the retarget's floor, not the clip's; hold the feet in the engine, on idles only.**
⚠ Two bridge lessons from the measuring: `EditorApplication.Step()` while paused does not advance the game through the
bridge (identical samples) and a call every 0.25 s stalls it — sample INSIDE Unity (a throwaway MonoBehaviour under the
gitignored `Assets/_PipelineTest/`, deleted after) and read one summary.
**AOE_Cast_Fix_02 updated (2026-09-28, "bake it"):** a torso offset with two keys over frames 1–34 in Combine over
the strip, flattened (0.00 mm) over the previous bakes (the staff idle's legs, root held); the IK feet stay put
(0.0 mm / 0.0° steps), the knees close from 135° to 118° through the range, no leg bone above 3° per frame.
Re-exported with the fit: the highest sole on the floor, the Necromancer's robe 71 mm under at its lowest frame
(the lowered torso hangs the hem lower: the robe class of dip).
**AOE_Cast_Fix_01 updated (2026-09-28, "bake it"):** one held key on both knee poles (`thigh_ik_target.L/R`) in Combine
over the strip, so the same swivel offset rides every frame: flattened (0.00 mm), feet untouched (0.0 mm / 0.0°),
knees 118–135°, no leg bone above 3° per frame; re-exported with the fit (unchanged: the Necromancer's robe 71 mm).
**Idle_02_Fix (2026-09-29, "bake it"):** one held key on both knee poles in Combine over the strip (the same swivel
offset on every frame of the 360-frame loop, so the seam holds: frame 361 = frame 1): flattened (0.00 mm),
`Idle_02_base` kept, the feet and root static to 0.0 mm, knees 133–139°, no leg bone above 0.3° per frame;
re-exported (the Knight's sole +10 mm, the Necromancer's robe 37 mm under, as before).

### Hand-authored clips and idle fixes (2026-09-21)

The user's review of the idles: blades pointed into the model, Idle's feet floated, Idle_02
was hunched with a bent left arm and looked sideways. `tools/anim_fix_idles.py` rewrites
the three actions in place, no Kimodo: every frame, the forearm is pronated about its
own axis until the socket's hilt axis points forward (12° out); Idle's torso is dropped
10 mm (its hips sat above the IK legs' reach, which lifted both feet 9 mm; a further
13 mm on 2026-09-21 evening, `--torso-drop`, so the knees keep 20° of bend); Idle_02's
spine flex is scaled down (61° → 14° chest tilt after two passes: the fixer is NOT
idempotent on Idle_02, run it once), the head re-aimed forward on the new spine, and
both arms replaced by Idle's hanging arms resampled over its loop.

`Idle_OneHanded` is retired (deleted from the project and the manifest). In its place,
`tools/anim_author_impaled.py` builds two clips from a **hand-posed base**: the user
posed a genuflect (left foot planted forward, right knee on the floor with that foot on
its bent toes behind, hips low and forward, chest 42° down, head down) and it lives in the
one-frame action `Impaled_Base` in the anim file (frame 1; keys must be INSERTED there,
a pose without keys is lost on the next frame change). Edit that action and re-run the
tool; everything in it is kept, arms included (the user posed the right fist on the hilt
at the belly with the hilt axis pointing into the body; `--tool-arms` makes the tool pose
them instead). `Impaled_Idle` (30 frames) is that base held still: skeletons do not
breathe. `Impaled_Rise` (69 frames, 2.3 s) is a **video-mocap clip spliced onto the base**:
the user recorded a stand-up (`P:\standing up.glb`, copied to `External Anims/Kimodo/
standing_up.glb`, a 52-joint `*_JNT` skeleton at 24 fps; `--rename jnt` maps it to the
names the retarget expects) and asked for its frame 34 as the start (= 30 fps frame 42,
where the hips begin to rise). Before that a Kimodo candidate (`rise_a`) had been chosen
among five; the mocap replaced it. The capture's own right arm does the pull (an authored
slide along the hilt axis over-reached and locked the elbow at 180°; the performer keeps
it at ~100°, measured 72° → 104° in play mode). Manifest: `blend_from Impaled_Idle:1`
(`blend_in 14`, so the rise starts on the idle's own frame, not the base: the idle's
analytic legs differ from the base by 2 cm), `blend_from_lift 0.0061` (rig m = the idle's
15 mm export lift minus this clip's 4 mm, faded out with the crossfade, so frame 1 lands
where the idle sits in Unity to 3 mm), `arm_keys 0:base,0.08:base,0.3:free`, `elbow_pole`,
`ground twoway` + `ground_ignore Robe,Skirt`, `plant_feet 0.001`, `blend_to Idle` over the
last 20 frames, `lift 0.004`.

**Feet (2026-09-21, "feet are floating on this one, while in mine they not").** The
`--plant-feet` pass in `glb_retarget.py` is what keeps FK-copied legs on the floor, and it
took four fixes to make Unity agree with Blender:
1. **Sole from the meshes, not an estimate.** The first pass lowered a foot by the bare
   foot's flat-sole offset; on a toe-down foot that sank the boot 18 mm. `foot_min_z(side)`
   now measures the lowest vertex of all six characters' meshes around that ankle.
2. **Reach.** The hips (scaled human) sat too high for the skeleton's stepped-forward leg:
   the IK locked the knee straight and the foot hung 34 mm up in Unity from t=0.5 on. A
   pass 1b measures, per frame, how far the hips must drop for every planted foot to stay
   within `PLANT_REACH = 0.985` of the leg length (knee keeps ~20°), running-max ±2 frames
   then smoothed, applied to the torso before planting (up to 3.4 cm rig on this clip).
3. **Toes have ONE muscle in Humanoid.** Measured with `HumanPoseHandler`: "Toes Up-Down"
   hinges about the T-pose's **world sideways axis** (the toe bone itself yaws 10° out, so
   its own X is not it); every other toe component is dropped on import, and with the boot
   resting on the toe cap in the crouch that moved the sole 1 cm (Humanoid toes 6–13° off
   the Generic playback of the same file). `hinge_toes()` keeps only that component on
   both toe controls, before the plant measures the sole; Humanoid now matches Generic and
   Blender within 1° on every foot and toe bone.
4. **Under-floor clamp and first frame.** A boot under the floor is lifted at full weight
   whatever the source does (FK blends sweep through the floor); a floating foot is planted
   with a weight that eases in over the source foot's last 3 cm of descent and with the
   blend-from crossfade, and the ground correction and hip drop both start at zero on
   frame 1, so the first frame is the idle verbatim.
Diagnostic chain that found it: `ground_clip`-style per-boot trace on all six models
(Unity) vs the same measure in Blender **including the export lift**; then bone heights
Humanoid vs Generic vs Blender (agreed to 1–4 mm → not the pose); then per-bone rotation
Humanoid vs Generic (toes 6–13° → the muscle model); then boot bounds per engine
(1 mm → the plant itself). Result: the lowest of the six boots is on the floor on every
frame from t=0.18 to the end in Blender; Unity reads 0..+14 mm across the models with
`lift 0.004` (Archer 0..+7), the two-frame landing of the stepping foot peaks at +3 cm. Kimodo cannot take a start pose (the
port has no constraint input) and every prompt that mentioned the sword in the stomach
skipped the kneel or collapsed instead; stand-up-only prompts knelt but as a head-down
crouch. The old procedural rise (pull, gather, blend to Idle frame 1) was: brings the right
foot forward to its stance, steps the left foot back to its stance while the hips rise
(a gather in place, since the clip must end where Idle stands and in-place import would
otherwise leave the character 0.6 m from its root), and from frame 100 blends every
control to Idle's frame 1 (arms IK→FK, legs FK→IK). **Dynamic final pose**: the rise
ends on the neutral standing pose and the showcase's return-to-idle crossfade lands on
whichever idle follows, so one rise serves every idle (verified in play mode: kneel →
rise → Idle, hips 0.56 → 0.99 m).

Lessons: the user's IK-posed legs are reproduced by the analytic two-bone solve from
the DEF bones (hip joint → ankle, knee towards the user's knee) plus explicit foot and
TOE frames (the base's right foot rests on bent toes; leaving the toe at rest put it
4.4 cm through the floor). No grounding pass on these two clips: the user grounded the
base on the Knight, and a pass that lifted the rise's first frame 4 cm above the idle
made the two clips not meet. Unity floor contact with the standard 15 mm lift: Knight
+7 mm, Archer/Assassin +6, Warrior −6; the Mage and Necromancer robes hang 7 cm through
the floor while kneeling (hems weighted to the shins, no cloth: accepted). Earlier
lessons from the first, fully procedural version still hold: grounding must ignore robes
and skirts, and a per-frame shift must move the hips and only a still-kneeling foot.

### Root motion — decided 2026-09-19

**Locomotion, turns, dodges and knockdowns are authored WITH root motion, carried on
`Root`.** Everything else (idles, attacks, casts, hits, staggers, deaths) keeps `Root`
still — except the four recorded arm attacks (2026-09-23), whose take includes a step: their net
travel rides on `Root` (`drift root`) and the demo's Root Motion toggle decides. **No `Motion` node.**

- Root motion is the superset: with Apply Root Motion off, Unity discards the travel
  and the clip plays in place, which is what a NavMesh-driven army does; Unreal gets the
  same from the per-sequence root motion flag or Force Root Lock. An in-place clip can
  never be turned back into root motion.
- One export serves both engines: Unity Humanoid rebuilds root motion from the hips and
  ignores `Root`; Unreal extracts it from the root bone only. Travel on `Root`, body
  relative to it, satisfies both (Orc: 2.04 m per Walk cycle with no Motion node;
  Unreal target: `Root` keeps the travel).
- **Reaction displacement lives in the pose (hips), not the root**, so a hit or stagger
  still recoils when root motion is discarded. Only clips whose point is displacement
  (dodge, knockdown) put it on `Root`.
- **Turns** put the yaw on `Root`; the engines' root-rotation settings decide whether it
  drives the actor or stays visual.
- **Ship the measured speed table**: exact travel per cycle and per second for every
  locomotion clip, so in-place blend trees and agent speeds can be matched without foot
  slide. Measure it in Unity, not from the authored curve (creatures pack §5.2).
- **Demo both**: one Animator controller with an in-place directional blend tree driven
  by a speed parameter, one with root motion on.
