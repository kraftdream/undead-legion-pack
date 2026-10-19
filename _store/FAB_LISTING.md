# Fab listing copy — Undead Legion, Modular Skeleton Army (Unreal Engine 5.4 – 5.8)

Every figure below was measured on 2026-10-05 through the editor's asset registry (the meshes, textures and clips of
`skeletons_ue_epic` are the same exports as `skeletons_ue`'s, re-skinned to the Epic skeleton; the asset counts are the Epic package's)
(`ue_py` inventory: classes, the `Triangles` / `Vertices` tags, LOD counts, texture sizes, the normal
maps' `flip_green_channel`). The description and the additional-information box are the two `.txt`
files beside this one; paste those, not this file. Edit the `.txt`, then re-check the figures here —
the creatures pack was rejected once for a description that did not match the pack.

**The package to upload is the UE 5.4 one, and it is the ONLY Unreal package (user decision 2026-10-19: "easier to maintain only
one version").** `skeletons_ue54`, built by `python tools/make_documentation.py ue54` (prints the manual into it) then
`python tools/ue/make_production_ue.py --ue54 --verify` → `../undead-legion-production-ue54/UndeadLegion_UE54.zip` (top folder
`UndeadLegion/`; 277 files, 94 MB; the showreel, level sequences, import pipelines, plugins, dev config and the mannequin test content
stripped; 31 Blueprints compiled headlessly on 5.4, 0 errors, 0 warnings). A 5.4 project opens in 5.5 – 5.8 too (the newer editor
converts it on first open), so one zip covers 5.4 – 5.8. Its inventory (2026-10-19, after the clip sync): 278 assets — 53 sequences (52 animations +
`A_Grip`), 29 montages, 23 Blueprints, 4 notifies, 3 widgets, 2 maps, 1 Animation Blueprint, 2 skeletons, 1 physics asset,
55 skeletal meshes, 11 static meshes, 67 textures, 2 materials, 25 instances. The per-asset figures further down (triangles, LODs, texture sizes) were
measured on the 5.8 Epic package on 2026-10-05; meshes and textures are the same exports in both, the clip and montage counts are not
(the 5.8 figures were 59 / 33 before the manifest disabled `Idle_Bow`, `Idle_Staff`, `Shoot_02`, `Cast_Wand_03`, the L_03 swing and
most heavy variants).

**The 5.8 project stays the SOURCE, not a product.** `skeletons_ue_epic` (UE 5.8) is rebuilt headlessly by `tools/ue/` and its DSL
is what `tools/ue/ue54_compile.py` turns into the 5.4 paste text; every Blueprint change goes there first and is then pasted into
5.4 (`tools/ue/README.md`, "The UE 5.4 twin"). `make_production_ue.py --epic` still works but its zip is not uploaded.

**One-time check on the 5.8 machine before submitting** (5.8 has never opened the 5.4 build; the source project's own update of
2026-10-19 is in `tools/ue/README.md`, "Base-pack update of 2026-10-19"):
1. Unzip `UndeadLegion_UE54.zip` to a fresh folder, open `UndeadLegion.uproject` in UE 5.8, accept the conversion ("Open a copy").
2. Output Log after the load: no errors; compile every Blueprint (`BP_*`, `ABP_UndeadSkeleton`, `WBP_AnimBrowser`): 0 errors.
3. Play `UndeadLegion_Demo`: switch all six characters, toggle armour, play a walk, a swing over a walk (arm layer), a 2H attack,
   `Shoot_01` (string and arrow), a hit, a stagger, a death clicked during another death (it must reset), the held block.
4. Mannequin route: copy the 5.8 template's `Characters/Content/Mannequins` into the copy's `Content/Characters/Mannequins`, add
   `SKEL_UndeadLegion` to `SK_Mannequin`'s Compatible Skeletons, play `MM_Run_Fwd` on the Knight. Do not save the copy.
If anything fails there, the fallback is to ship the 5.8 zip as a second version entry (rebuilt with today's DSL first).

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

One version entry:

| Field | Value |
|---|---|
| Version title | UE 5.4 – 5.8 |
| Project file link | your upload of `UndeadLegion_UE54.zip` (Google Drive / Dropbox: sharing set to "Anyone with the link"); Fab downloads it from there |
| Supported engine version | 5.4, 5.5, 5.6, 5.7, 5.8 (tested in 5.4; 5.8 after the one-time check above; 5.5 – 5.7 not opened, a 5.4 project upgrades) |
| Supported target platforms | Windows, Mac, Linux, iOS, Android, Oculus, SteamVR / HTC Vive; optionally PS4, Xbox One, Nintendo Switch (supported by 5.4 – 5.8 and nothing in the pack is platform-specific, but untested without devkits). Never HTML5 (removed in 4.24), Win32 (UE5 is 64-bit only), Gear VR (removed in UE4), HoloLens 2 (deprecated). Mobile is backed by the ES3.1 preview only (run on the 5.8 copy, the same materials), no device cook |
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
| Assets | 278 | 55 skeletal meshes, 11 static meshes, 2 skeletons (the characters' + the bow's), 1 physics asset, 67 textures, 2 materials, 25 instances, 53 sequences, 29 montages, 1 Animation Blueprint, 4 notifies, 23 Blueprints, 3 widgets, 2 maps (counted in the 5.4 zip, 2026-10-19) |
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
| Animation tracks | 52 | the 52 animations the description lists; the 53rd sequence, `A_Grip`, is two-frame finger-pose data, not a clip (5.4 zip, 2026-10-19) |
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
| Supported engine version | 5.4 – 5.8 (one 5.4 package, see the version dialog) |
| Supported target platforms | as in the version dialog |
| Distribution method | Asset package |
| Documentation | `Content/UndeadLegion/Documentation.pdf` — the Unreal manual (11 A4 pages: setup, folders, characters, armor API, weapons and loadouts, sockets, the bow, the clip list with lengths, the Animation Blueprint layers, root motion and speeds in cm/s, the Blueprint API, the demo map, mannequin animations and own animations, technical details), printed from `tools/docs/UndeadLegion_UE_Documentation.html` by `python tools/make_documentation.py ue54` |

---

## Checks still open before submitting

- Mobile: the shipped copy renders clean in Unreal's ES3.1 mobile preview (2026-10-06: every material, the eyes, the UI; the
  demo map got a sky dome for it, the one NPOT texture was resized). A real Android / iOS cook needs the SDK and was not run,
  so a mobile platform claim is backed by the preview only.

- The 5.4 package opened in 5.8: the one-time check above.
- A full cook has not been done on either version (Fab's own validation cooks it).
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
