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
| Weapons (12 meshes)  | done | **none** — no UVs, no materials | n/a | — | n/a | — | — |

Shared clips so far: `Idle` (loop) + `Twitch_01..03` (additive), on `AC_Skeleton`.

All six characters share one armature (§2), every body and armour module is skinned to
it, and every exported model imports in Unity with the **same 68-bone hierarchy**
(66 + two weapon sockets), the same bone array on every renderer, Hips at 0.982 m and
mesh nodes at identity rotation.

**First clips exist (2026-09-19), so the skeleton is frozen.** In Unity
`Assets/UndeadLegion/Animations/`: `Skeleton@Idle` (4.0 s loop, Kimodo text-to-motion
retargeted, §8), `Skeleton@Twitch_01/02/03` (2.5 / 3.5 / 4.5 s additive head + jaw
twitches), and `AC_Skeleton.controller` (Base: Idle; Twitch: additive layer, random
pick via `Demo/Scripts/SkeletonTwitch.cs`). Measured on all six models: Idle travel
0, Head 5.2° / Hips 2.5° of motion; Twitch_03 over Idle adds Head 5.7° / Jaw 4.7°
peaks with Hips at 0.00°. The pipeline test clip `Test_RootMotion` (1 m forward, 30°
yaw, 25° nod) measured 1.805 m / 30.08° / 25.0° with Apply Root Motion on and 0 / 0
with it off; it stays in the anim file, not in Unity.

### Known gaps

- `SkeletonMage`, `SkeletonNecromancer` and `SkeletonAssassin` have **no `armor_metallic.png`**;
  Knight, Archer and Warrior do. Either those armours are non-metallic by design (then
  the material must not sample a metallic map) or the bake was skipped.
- `Weapons/weapons.blend` holds 12 rigid meshes (`H1Sword`, `H2Longbow`, `H1Spellbook`…)
  with **no UVs, no textures and placeholder Tripo materials**. No grip convention yet.
- The **old mesh-only exports in the character folders are superseded but still
  tracked**: `skeleton.fbx`, `armor.fbx`, `mesh_quad.fbx`, `mesh_uv.fbx`. The Unity
  copies (`SkeletonKnight_{Body,Armor}.fbx`) were deleted on 2026-09-19 and every prefab
  now builds from `SK_<Character>.fbx`. Deleting the repo-root ones is safe.
- The Asset Store validator has not been re-run since the prefabs and demo were rebuilt.
- The **Archer's head** was skinned against a rig whose neck/head/jaw bones sat ~18 mm
  forward of the shared rig's; it now binds to the shared rig. Posed deviation is
  ≤ 6 mm on the skull and helm. Acceptable, but look at the Archer first if a neck
  clip reads wrong.
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
3. **Unity Humanoid avatar is configured once and reused.** Armour modules import as
   separate `SkinnedMeshRenderer`s and bind at runtime by copying `bones` + `rootBone`
   from the body's renderer — which requires identical bone arrays, i.e. rule 1.

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

A weapon mesh is authored with its grip point at the origin and its blade along +Y in
the engine, and attaches to the socket with an **identity** local transform. The
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
        ├── Models/<Character>/SK_<Character>.fbx   rigged body + modules, Humanoid
        ├── Prefabs/{Characters,Modules}
        └── Textures/<Character>/
```

`Animations/` is **flat and shared**: six characters on one rig means one clip set.

---

## 4. Conventions

**Model export** — `SK_<Character>.fbx`, one file per character containing the deform
skeleton under `Armature/Root` and every skinned mesh (`Body`, `Helm`, `Chest`,
`Glove_L`…) as **siblings** of `Armature`, at **1.8× the Blender metres** (Hips 0.982 m,
skull top ≈ 1.70 m, helmet ≈ 1.81 m). Unity import: **Humanoid, Create From This
Model, `globalScale = 1`, materials None, no animation.**

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
  `refresh_unity` instead.
- **Asset Store Tools** is embedded at `skeletons/Packages/com.unity.asset-store-tools`.
- Blender MCP (`C:\Users\vadym\.local\bin\blender-mcp.exe`) exists but the rig work is
  all scripted headlessly now; prefer the scripts, they are reproducible.

---

## 7. Demo scene, prefabs and submission validation

`Assets/UndeadLegion/Demo/Scenes/UndeadLegion_Demo.unity` — the animation-browser
demo, rebuilt 2026-09-19 on the model of the creatures pack: characters (top-left),
armour MODULES with All/None (left), ANIMATIONS grouped in sections (right, plus a
"Twitch (additive layer)" section whose buttons fire the additive layer over the
current clip), footer with Root Motion / Turntable / Random twitch toggles and Recenter.
Drag to orbit, wheel to zoom. Verified in play mode: six characters, Idle looping on
each, module toggles, twitch firing, no console errors.

**Everything is generated by menu items in `Demo/Editor/`, never hand-edited:**

| menu (`Undead Legion/…`) | script | does |
|---|---|---|
| 1. Import Setup | `UndeadLegionImportSetup.cs` | texture importers (colour sRGB, normal `NormalMap`, packed map linear + alpha from input), `SK_*` model importers (Humanoid, scale 1, materials None), `M_<Char>_{Body,Armor}` URP/Lit materials |
| 2. Rebuild Character Prefabs | `CharacterPrefabBuilder.cs` | `PF_<Char>.prefab` from `SK_<Char>.fbx`: materials per renderer, Animator (own avatar, `AC_Skeleton`, root motion on, always animate), CapsuleCollider 1.8/0.35, `SkeletonModules`, `SkeletonTwitch`; root at exactly 0/0/1 |
| 3. Rebuild Demo Scene | `DemoSceneBuilder.cs` | lights (1.10 key / 0.45 fill / 0.30 rim, skybox ambient 2.0 — the creatures pack's measured turntable rig), ground, camera + `DemoTurntable`, EventSystem + `DemoEventSystemBootstrap`, the uGUI canvas, `SkeletonShowcase` wired to all six prefabs |
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
scripts live in `Demo/Scripts/` (`SkeletonShowcase`, `SkeletonModules`, `SkeletonTwitch`,
`DemoTurntable`, `DemoUI`, `DemoEventSystemBootstrap`), namespace `UndeadLegion.Demo`.
Legacy uGUI Text on purpose (no TMP import prompt for buyers); input read through both
backends. `tools/unity/demo_smoke.py` plays the scene headlessly and screenshots it.

### Import decisions

- **Scale**: `SK_*.fbx` bake the 1.8 at export and import at **`globalScale = 1`**.
  The old mesh-only Knight FBXs (globalScale 1.8) were deleted on 2026-09-19.
- **Smoothness**: URP has no roughness input; the packed `_metallicsmoothness` map
  drives `_MetallicGlossMap` with `_Metallic = 1`, `_Smoothness = 1`. Raw
  roughness/metallic PNGs are not shipped.
- **Colour space**: normal maps `NormalMap`; packed map `sRGB = false`,
  `alphaSource = FromInput`; albedo sRGB.
- **Materials**: `materialImportMode = None` on every FBX; `Materials/URP/` is the
  single source of truth (twelve character materials + `M_Demo_Ground`).

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
Additive` + Aim Offset). What it changes on the authoring side:

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

Twitches are not Kimodo: `tools/anim_twitch.py` authors them procedurally (random
quick jerks on `head`, a third on `neck`, opens on `lowerjaw` whose open direction is
measured — on this rig +X about the jaw control LIFTS the chin, so open is −X). Frame
1 and the last frame are rest, so each clip is its own additive reference (Unity:
`hasAdditiveReferencePose`, frame 0). `tools/anim_preview.py` renders a Workbench
contact sheet of any action for review.

Reference meshes in the anim file must be bound to `RIG-Meta-Rig`, not `Meta-Rig`:
both are overrides, and a refresh once picked the metarig and froze every mesh.

### Root motion — decided 2026-09-19

**Locomotion, turns, dodges and knockdowns are authored WITH root motion, carried on
`Root`.** Everything else (idles, attacks, casts, hits, staggers, deaths) keeps `Root`
still. **No `Motion` node.**

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
