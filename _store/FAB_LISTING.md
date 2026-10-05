# Fab listing copy — Undead Legion, Modular Skeleton Army (Unreal Engine 5.8)

Every figure below was measured on 2026-10-05 off `skeletons_ue` through the editor's asset registry
(`ue_py` inventory: classes, the `Triangles` / `Vertices` tags, LOD counts, texture sizes, the normal
maps' `flip_green_channel`). The description and the additional-information box are the two `.txt`
files beside this one; paste those, not this file. Edit the `.txt`, then re-check the figures here —
the creatures pack was rejected once for a description that did not match the pack.

⚠ **What the shipped package must NOT contain** (the figures below exclude it): the showreel map
`Demo/Maps/UndeadLegion_Showreel`, the 25 `Demo/Showreel/LS_*` level sequences, `Demo/Blueprints/
BP_ShowreelDirector`, the 5 `Pipelines/IP_*` Interchange pipelines (import settings, not content —
Fab's "no unused assets" rule, the creatures pack's rejection #2), `Developers`, `Collections`. The
production copy for Fab is not scripted yet (`tools/ue/README.md`, "Not done yet"); strip by hand or
port `production_branch.sh` from the creatures pack, and re-run the counts after.

---

## Description

`_store/FAB_DESCRIPTION.txt` — paste verbatim.

## Additional information

`_store/FAB_ADDITIONAL_INFO.txt` — paste verbatim.

## Tags (Fab allows up to 20)

skeleton, undead, modular, character, fantasy, rpg, medieval, knight, warrior, archer, assassin, mage,
necromancer, armor, weapons, animated, rigged, game ready, army, horde

## Category

Characters & Creatures → Humanoids (the six are human-shaped skeletons on a humanoid skeleton; the
creatures pack went under Creatures & Monsters)

## "Add Unreal Engine version" dialog

| Field | Value |
|---|---|
| Version title | Unreal 5.8 |
| Project file link | your upload of the production project zip (Google Drive / Dropbox / any direct link); Fab downloads it from there |
| Supported engine version | 5.8 (only: the project cannot be opened by an older editor; the Blueprint graphs and the skinned bow were built on 5.8) |
| Supported target platforms | Windows, Mac, Linux (desktop; Blueprint only, nothing platform-specific; untested on mobile and consoles, so do not claim them) |
| Version notes | the zip's password if you protect it; otherwise leave empty |

## Fab "details" form — every field

### Geometry — *Use range for multiple assets: on*

| Field | Value | |
|---|---|---|
| Total triangles | 16,728 – 18,870 | per class, body + its default armour (Knight → Assassin) |
| Quads | 0 – 0 | triangulated on export |
| Polygons | 191 – 7,588 | = triangles per mesh |
| Triangles | 191 – 7,588 | per mesh: `SK_SkeletonMage_Greave_L` → `SK_SkeletonAssassin` body |
| Vertices | 134 – 5,031 | the same two meshes |
| Pack of multiple assets | Yes | |
| Assets | ~ 290 | 55 skeletal meshes, 11 static meshes, 2 skeletons, 1 physics asset, 67 textures, 2 materials, 25 instances, 59 sequences, 33 montages, 1 Animation Blueprint, 2 notifies, 22 Blueprints, 3 widgets, 2 maps — recount on the stripped package |
| Unique meshes | 66 | 55 skeletal (6 bodies, 48 modules, 1 bow) + 11 static (weapons) |
| Includes LODs | No | every skeletal and static mesh has 1 LOD |
| Bounding box size | 170 | the dressed characters, cm |
| Bounding box X / Y / Z | 99 / 34 / 170 | the widest body (arms in the A-pose) / depth / skull top; helmets reach ~181 |
| Has collision | Yes | Collision type **Custom**: the capsule and `PA_UndeadLegion`; the weapon static meshes have NO collision primitives |
| Nanite-enabled | No | |

### Materials and textures — *Use range: on*

| Field | Value | |
|---|---|---|
| Texture resolution | 128 – 1,254 | 35 at 1024² (characters), 30 at 512² (weapons), 1 at 1254² (`T_SkeletonWarrior_Armor_C`), 1 at 128² (the arrow) |
| Materials | 27 | 2 `Material` (`M_UndeadLegion_Master`, `M_Eyes`) + 25 `MaterialInstanceConstant` (12 character, 12 weapon, 1 demo floor) |
| Substrate materials | 0 | |
| Custom shaders | No | |
| Textures | 67 | base colour, normal and packed metallic / smoothness per character body and armour and per weapon |
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
| Rigged to | Custom | one shared 68-bone skeleton, not the Epic skeleton |
| Animation tracks | 59 | 58 clips + the two-frame `A_Grip` finger-pose data |
| Solid animation | No | |
| Morph animation / blendshapes | No | |
| Scale animation | No | |
| Baked animation | Yes | |
| IK bones included | No | |
| Characters | 6 | |
| Animation type | Root Motion | the locomotion loops and the staggers; every other clip in place |

### Interactivity and logic

| Field | Value | |
|---|---|---|
| Contains scripted logic | Yes | the character Blueprint (armour, weapons, grips, eyes, the layer stack), the demo browser |
| Event triggers and interactions | Yes | |
| Blueprints | 22 (+ 1 Animation Blueprint, 3 widgets, 2 notifies) | `BP_UndeadSkeleton`, 6 `BP_<Class>`, 12 `BP_Weapon_*`, `BP_ArrowProjectile`, `BP_DemoGameMode`, `BP_DemoShowcase`, `BP_OrbitPawn` — `BP_ShowreelDirector` is dev-only and must be stripped |
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
| Supported engine version | 5.8 |
| Supported target platforms | Windows, macOS, Linux |
| Distribution method | Asset package |
| Documentation | `Content/UndeadLegion/Documentation.pdf` — copy the Unity manual's PDF into the package (the Unreal manual is not written yet; the clip list, speed table, sockets and grips sections apply as they are, the Unity-specific sections do not) |

---

## Checks still open before submitting

- The Fab production copy (stripped as above) and a cook on 5.8 with 0 errors / 0 warnings.
- The physics asset `PA_UndeadLegion` is the one the Knight's import generated, not a tuned ragdoll:
  the description does not claim a ragdoll. Tune it or leave the claim out.
- The Unity manual's weapon triangle counts (498 – 5,074) do not match the Unreal assets (344 –
  1,495, the bow 3,869); the character and module counts match exactly. Check the Unity figure
  before the next manual print (2026-10-05).
- The showreel videos were rendered from the dev project; the Fab page video is
  `Showreel/unreal/undead_legion_showreel_unreal.mp4` (4:17) with its `youtube_description.txt`.
