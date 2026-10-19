# Fab listing copy — Undead Legion, Modular Skeleton Army (Unreal Engine 5.4 – 5.8)

Every figure below was measured on 2026-10-05 through the editor's asset registry (the meshes, textures and clips of
`skeletons_ue_epic` are the same exports as `skeletons_ue`'s, re-skinned to the Epic skeleton; the asset counts are the Epic package's)
(`ue_py` inventory: classes, the `Triangles` / `Vertices` tags, LOD counts, texture sizes, the normal
maps' `flip_green_channel`). The description and the additional-information box are the two `.txt`
files beside this one; paste those, not this file. Edit the `.txt`, then re-check the figures here —
the creatures pack was rejected once for a description that did not match the pack.

**The package to upload** is the EPIC-SKELETON project (`skeletons_ue_epic`, 2026-10-05), built by
`python tools/ue/make_production_ue.py --epic --verify` (after `python tools/make_documentation.py ue`, which prints the
manual into it): `../undead-legion-production-ue-epic/UndeadLegion_UE58_Epic.zip` (the Mixamo-skeleton package of
`skeletons_ue` is `make_production_ue.py --verify` → `../undead-legion-production-ue/UndeadLegion_UE58.zip`) (top folder `UndeadLegion/`: `Config/`, `Content/UndeadLegion/`,
`UndeadLegion.uproject`; 291 files, 95 MB). It strips the showreel map, the 25 `LS_*` level sequences,
`BP_ShowreelDirector`, the 5 `Pipelines/IP_*` Interchange pipelines (import settings, not content —
Fab's "no unused assets" rule, the creatures pack's rejection #2), `Developers`, `Collections`, all seven
editor plugins and the dev config lines, audits the result and compiles every Blueprint headlessly on 5.8
(29 compiled, 0 errors, 0 warnings on 2026-10-05). The figures below are the stripped package's.

**The second package, for UE 5.4** (2026-10-19): the same content rebuilt in UE 5.4 (`skeletons_ue54`), built by
`python tools/ue/make_production_ue.py --ue54 --verify` (after `python tools/make_documentation.py ue54`, the same manual with the
engine version changed): `../undead-legion-production-ue54/UndeadLegion_UE54.zip` (277 files, 94 MB; 31 Blueprints compiled
headlessly on 5.4, 0 errors, 0 warnings). A 5.4 project opens in 5.4 – 5.7 as it is (and in 5.8, which upgrades it), so it is
the package for every version below 5.8. Its inventory (2026-10-19): 272 assets — 50 sequences (49 animations + `A_Grip`),
26 montages, 23 Blueprints, 4 notifies, 3 widgets, 2 maps, 1 Animation Blueprint, 1 skeleton, 1 physics asset, 11 static meshes,
67 textures, 2 materials, 25 instances. ⚠ The clip set shrank after 2026-10-05 (the manifest disables `Idle_Bow`, `Idle_Staff`,
`Shoot_02`, `Cast_Wand_03`, the L_03 swing and most heavy variants), so the 5.8 package's 10-05 figures in the table below
(59 sequences, 33 montages) are stale: rebuild the 5.8 zip and re-count it before submitting; the description now says 49 / 26.

---

## Description

`_store/FAB_DESCRIPTION.txt` — paste verbatim.

## Additional information

`_store/FAB_ADDITIONAL_INFO.txt` — paste verbatim.

## Tags (Fab allows up to 20)

skeleton, undead, modular, character, fantasy, rpg, medieval, knight, warrior, archer, assassin, mage,
necromancer, armor, weapons, animated, rigged, game ready, army, horde

## Category

Characters & Creatures → Humanoids (the six are human-shaped skeletons on the Epic skeleton; the
creatures pack went under Creatures & Monsters)

## "Add Unreal Engine version" dialog

| Field | Value |
|---|---|
Add the dialog twice, once per package:

| Field | Unreal 5.8 | Unreal 5.4 |
|---|---|---|
| Version title | Unreal 5.8 | Unreal 5.4 |
| Project file link | your upload of `UndeadLegion_UE58_Epic.zip` | your upload of `UndeadLegion_UE54.zip` |
| Supported engine version | 5.8 (an older editor cannot open it) | 5.4, 5.5, 5.6, 5.7 (tested in 5.4 only; a 5.4 project opens in the later editors) |

Both, every other field:

| Field | Value |
|---|---|
| Project file link | your upload of the production project zip (Google Drive / Dropbox / any direct link); Fab downloads it from there |
| Supported target platforms | Windows, Mac, Linux (desktop; Blueprint only, nothing platform-specific; untested on mobile and consoles, so do not claim them) |
| Version notes | the zip's password if you protect it; otherwise leave empty |

## Fab "details" form — every field

### Geometry — *Use range for multiple assets: on*

| Field | Value | |
|---|---|---|
| Total triangles | 16,728 – 18,870 | per class, body + its default armor (Knight → Assassin) |
| Quads | 0 – 0 | triangulated on export |
| Polygons | 191 – 7,588 | = triangles per mesh |
| Triangles | 191 – 7,588 | per mesh: `SK_SkeletonMage_Greave_L` → `SK_SkeletonAssassin` body |
| Vertices | 134 – 5,031 | the same two meshes |
| Pack of multiple assets | Yes | |
| Assets | 286 | 55 skeletal meshes, 11 static meshes, 2 skeletons, 1 physics asset, 67 textures, 2 materials, 25 instances, 59 sequences, 33 montages, 1 Animation Blueprint, 2 notifies, 23 Blueprints, 3 widgets, 2 maps (counted in the stripped Epic-skeleton package, 2026-10-05) |
| Unique meshes | 66 | 55 skeletal (6 bodies, 48 modules, 1 bow) + 11 static (weapons) |
| Includes LODs | No | every skeletal and static mesh has 1 LOD |
| Bounding box size | 170 | the dressed characters, cm |
| Bounding box X / Y / Z | 99 / 34 / 170 | the widest body (arms in the A-pose) / depth / skull top; helmets reach ~181 |
| Has collision | Yes | Collision type **Custom**: the capsule and `PA_UndeadLegion`; the weapon static meshes have NO collision primitives |
| Nanite-enabled | No | |

### Materials and textures — *Use range: on*

| Field | Value | |
|---|---|---|
| Texture resolution | 128 – 1,024 | 36 at 1024² (characters), 30 at 512² (weapons), 1 at 128² (the arrow); every one a power of two (the Warrior's armor color was 1254², resized 2026-10-06) |
| Materials | 27 | 2 `Material` (`M_UndeadLegion_Master`, `M_Eyes`) + 25 `MaterialInstanceConstant` (12 character, 12 weapon, 1 demo floor) |
| Substrate materials | 0 | |
| Custom shaders | No | |
| Textures | 67 | base color, normal and packed metallic / smoothness per character body and armor and per weapon; every one a power of two (2026-10-06) |
| Normal map orientation | DirectX (Y-) | `flip_green_channel` on at import (the sources are OpenGL) |
| UV channels | 1 | |
| Clean UV | No | mirrored left / right pieces share UV space |
| Overlapping UV | Yes | |
| UDIM | No | |
| Vertex colors | No | |
| Scanned | No | |

### Rigging and animation

| Field | Value | |
|---|---|---|
| Animated | Yes | |
| Rigged animation | Yes | |
| Rigged to | Epic skeleton | the UE5 mannequin's 89 bones (hierarchy, names, bone frames, ik bones) + jaw_01/02 + pelvis_l/r = 93, our proportions (`skeletons_ue_epic`, 2026-10-05) |
| Animation tracks | 59 | 58 clips + the two-frame `A_Grip` finger-pose data |
| Solid animation | No | |
| Morph animation / blendshapes | No | |
| Scale animation | No | |
| Baked animation | Yes | |
| IK bones included | Yes | the mannequin's ik_hand_root / ik_hand_gun / ik_hand_l/r and ik_foot_root / ik_foot_l/r | |
| Characters | 6 | |
| Animation type | Root Motion | the locomotion loops and the staggers; every other clip in place |

### Interactivity and logic

| Field | Value | |
|---|---|---|
| Contains scripted logic | Yes | the character Blueprint (armor, weapons, grips, eyes, the layer stack), the demo browser |
| Event triggers and interactions | Yes | |
| Blueprints | 23 (+ 1 Animation Blueprint, 3 widgets, 2 notifies) | `BP_UndeadSkeleton`, 6 `BP_<Class>`, 12 `BP_Weapon_*`, `BP_ArrowProjectile`, `BP_DemoGameMode`, `BP_DemoShowcase`, `BP_OrbitPawn` (`BP_ShowreelDirector` is stripped by the packaging script) |
| Input methods | Keyboard, Mouse | the browser is clicked, the orbit camera dragged |
| Contains C++ source code | No | |
| Scripting language | Blueprint | |
| Logic system | Event-driven | |
| Network replicated | No | |

### Scenes, levels and prefabs

| Field | Value | |
|---|---|---|
| Levels / scenes | 2 | `UndeadLegion_Demo` (the animation browser, the startup map) and `UndeadLegion_Overview`; drop Overview to ship 1 |
| Playable | 2 | |
| Persistent level | Yes | |
| World Partition | No | |

### The rest of the form

| Field | Value |
|---|---|
| Supported engine version | 5.4 – 5.8 (two packages, see the version dialog) |
| Supported target platforms | Windows, macOS, Linux |
| Distribution method | Asset package |
| Documentation | `Content/UndeadLegion/Documentation.pdf` — the Unreal manual (11 A4 pages: setup, folders, characters, armor API, weapons and loadouts, sockets, the bow, the clip list with lengths, the Animation Blueprint layers, root motion and speeds in cm/s, the Blueprint API, the demo map, mannequin animations and own animations, technical details), printed from `tools/docs/UndeadLegion_UE_Documentation.html` by `python tools/make_documentation.py ue` (5.8) / `ue54` (5.4) |

---

## Checks still open before submitting

- Mobile: the shipped copy renders clean in Unreal's ES3.1 mobile preview (2026-10-06: every material, the eyes, the UI; the
  demo map got a sky dome for it, the one NPOT texture was resized). A real Android / iOS cook needs the SDK and was not run,
  so a mobile platform claim is backed by the preview only.

- The package compiles clean headlessly and the production copy was opened and tested interactively on 2026-10-06;
  a full cook on 5.8 has not been done (Fab's own validation cooks it).
- The 5.4 package: compiled headlessly on 5.4 and tested interactively on 2026-10-19 (the browser, the death holds, the feet on
  the floor); the mobile preview and a cook were not run on 5.4. Mannequin animations on 5.4 (`tools/ue/ue54_manny_check.py`, the
  manual's compatible-skeletons route): UE 5.4's own MM_Run_Fwd, MM_Walk_Fwd and Quinn's MF_Walk_Fwd played through the
  Knight's Animation Blueprint move every one of the 48 body bones exactly as on SKM_Manny (0.00 deg, measured as each bone's
  motion from its own rest pose; the fingers follow the pack's grip layers and the neck / head its twitches, by design). The
  "Rigged to Epic skeleton" claim holds for the 5.4 package.
- The demo browser does not drive the bow string or fire the arrow (the weapon Blueprint has the poseable
  bow and `BP_ArrowProjectile` ships; the manual and the description say so).
- The physics asset `PA_UndeadLegion` is the one the Knight's import generated, not a tuned ragdoll:
  the description does not claim a ragdoll. Tune it or leave the claim out.
- The Unity manual's weapon triangle counts (498 – 5,074) do not match the Unreal assets (344 –
  1,495, the bow 3,869); the character and module counts match exactly. Check the Unity figure
  before the next manual print (2026-10-05).
- The showreel videos were rendered from `skeletons_ue` (the Mixamo-named twin) and are NOT re-recorded for the Epic
  package (user decision 2026-10-06: the clips are the same actions bone for bone, nothing on screen differs); the Fab page
  video is `Showreel/unreal/undead_legion_showreel_unreal.mp4` (4:17) with its `youtube_description.txt`.
