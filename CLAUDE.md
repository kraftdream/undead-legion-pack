# Undead Legion Pack — Modular Skeleton Army

Commercial asset pack for the **Unity Asset Store** and **Unreal Fab**: a skeleton
army in **six** class variants, each built from **one shared humanoid rig** with
**swappable armour modules**, shipped with a single retargetable animation set.

Working title: **Undead Legion — Modular Skeleton Army**

---

## 1. Current state

Verified 2026-09-19 by probing the `.blend` files headlessly (`tools/rig_check.py`)
and importing the exports into Unity 6000.4 through the editor bridge.

| Character | Mesh | Textures | Shared rig | `SK_*.fbx` in Unity | Humanoid avatar | Anims | Prefab / demo |
|---|---|---|---|---|---|---|---|
| Skeleton Knight      | done | done | **yes** | **yes** | **valid, 53 bones mapped** | — | demo scene, on the OLD mesh-only FBX |
| Skeleton Archer      | done | done | **yes** | **yes** | valid | — | — |
| Skeleton Assassin    | done | partial (no `armor_metallic`) | **yes** | **yes** | valid | — | — |
| Skeleton Mage        | done | partial (no `armor_metallic`) | **yes** | **yes** | valid | — | — |
| Skeleton Necromancer | done | partial (no `armor_metallic`) | **yes** | **yes** | valid | — | — |
| Skeleton Warrior     | done | done | **yes** | **yes** | valid | — | — |
| Weapons (12 meshes)  | done | **none** — no UVs, no materials | n/a | — | n/a | n/a | — |

All six characters share one armature (§2), every body and armour module is skinned to
it, and every exported model imports in Unity with the **same 66-bone hierarchy**, the
same bone array on every renderer, Hips at 0.982 m and mesh nodes at identity rotation.
**No clip exists yet.** Until the first one does, the skeleton is still cheap to change.

### Known gaps

- `SkeletonMage`, `SkeletonNecromancer` and `SkeletonAssassin` have **no `armor_metallic.png`**;
  Knight, Archer and Warrior do. Either those armours are non-metallic by design (then
  the material must not sample a metallic map) or the bake was skipped.
- `Weapons/weapons.blend` holds 12 rigid meshes (`H1Sword`, `H2Longbow`, `H1Spellbook`…)
  with **no UVs, no textures and placeholder Tripo materials**. No grip convention yet.
- The **old mesh-only exports are superseded but still tracked**: `skeleton.fbx`,
  `armor.fbx`, `mesh_quad.fbx`, `mesh_uv.fbx` in every character folder, and
  `Models/SkeletonKnight/SkeletonKnight_{Body,Armor}.fbx` in Unity. The demo prefab
  `PF_SkeletonKnight` still references the latter two, at `globalScale = 1.8`. Rebuild
  it on `SK_SkeletonKnight.fbx` (scale 1, §7) before deleting anything.
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

Rigid props attached to a hand bone (`RightHand` / `LeftHand` in the export). Fix one
grip convention (bone, local offset, rotation) and apply it to every weapon.

---

## 3. Repository layout

```
undead-legion-pack/
├── Rig/
│   ├── skeleton_rig.blend     THE armature (Rigify metarig + generated rig + widgets)
│   └── skeleton_rig.json      bone table dumped from it; what rig_check compares against
├── Skeleton{Knight,Archer,Assassin,Mage,Necromancer,Warrior}/
│   └── prod.blend + textures + reference + (superseded) mesh-only FBX exports
├── Weapons/                   weapons.blend + mesh_quad.fbx
├── tools/                     headless Blender + Unity scripts, see tools/README.md
│   ├── rig_lib_build.py       (one-off) built Rig/skeleton_rig.blend from the Knight
│   ├── rig_lib_dump.py        library -> skeleton_rig.json
│   ├── rig_sync.py            put the library rig into a character file, normalise it
│   ├── rig_check.py           assert a character file matches the library (exit 1 if not)
│   ├── export_fbx.py          character file -> SK_<Character>.fbx into the Unity project
│   └── unity/mcp_call.py      stdio MCP client for the running Unity editor
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

**Animation export** — `Skeleton@<Clip>.fbx`, rig only, no mesh, avatar copied from
`SK_SkeletonKnight`. The `@` form is what Unity splits into a named clip.

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

## 7. Demo scene and submission validation

`Assets/UndeadLegion/Demo/Scenes/UndeadLegion_Demo.unity` — minimum shippable scene
built 2026-09-15: `Ground`, `SK_SkeletonKnight` (from the old two-mesh export), warm key
light, cool fill, trilight ambient, camera at 40° FOV.

### Import decisions

- **Scale**: the old mesh-only FBXs use `ModelImporter.globalScale = 1.8`. The new
  `SK_*.fbx` bake the 1.8 at export and import at **`globalScale = 1`**. Do not mix.
- **Smoothness**: URP has no roughness input. Maps were packed once with Pillow —
  `R = metallic`, `A = 1 - roughness` — into `<part>_metallicsmoothness.png`
  (`_MetallicGlossMap`). Raw roughness/metallic PNGs are not shipped. Materials set
  `_Metallic = 1`, `_Smoothness = 1` so the map alone drives both.
- **Colour space**: normal maps `NormalMap`; packed map `sRGB = false`,
  `alphaSource = FromInput`; albedo sRGB.
- **Materials**: `materialImportMode = None` on every FBX; `Materials/URP/` is the
  single source of truth.

### Validator status — 31 pass, 0 fail, 1 warning (on the OLD export)

Run the Asset Store validator headlessly against `Assets/UndeadLegion` (category
`3D/Characters/Humanoids`). Its classes are `internal`; drive
`AssetStoreTools.Validator.CurrentProjectValidator` by reflection; `Title` and `Result`
on `AutomatedTest` are fields.

`Check Model Orientation` warned because the old exports carried `localRotation =
(89.98, 0, 0)` on every mesh node. **Fixed in the `SK_*.fbx` exports** with
`bake_space_transform=True` (measured: mesh nodes at identity, `Armature` keeps its −90°
X, which the validator ignores). The warning goes away once the demo prefab is rebuilt
on `SK_SkeletonKnight.fbx`.

`Check Prefab Transforms` requires a prefab's root at exactly 0 / 0 / 1 at 12 decimal
places. Any grounding offset lives on children, never the root.

### Verifying a scene actually renders

`manage_camera screenshot` returns a stale Game view in edit mode. Render explicitly:
`RenderTexture` on the camera, `cam.Render()`, `ReadPixels`, write the PNG.
`GeometryUtility.TestPlanesAABB` is the cheap "is it in frustum" check.

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
