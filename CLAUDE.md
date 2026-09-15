# Undead Legion Pack — Modular Skeleton Army

Commercial asset pack for the **Unity Asset Store** and **Unreal Fab**: a skeleton
army in four class variants, each built from a **shared humanoid rig** with
**swappable armour modules**, shipped with a single retargetable animation set.

Working title: **Undead Legion — Modular Skeleton Army**

---

## 1. Current state

Verified 2026-09-15 by probing the FBX node tables directly, not from commit messages.

| Character | Concept | Mesh | Textures | Rig (in .blend) | Rigged FBX export | Anims | Unity |
|---|---|---|---|---|---|---|---|
| Skeleton Knight  | done | done | done | done | **no** | — | **demo scene** |
| Skeleton Archer  | done | done | done | done | **no** | — | — |
| Skeleton Mage    | done | done | partial | done | **no** | — | — |
| Skeleton Warrior | done | done | done | done | **no** | — | — |
| Weapons          | done | done | **none** | n/a | n/a | n/a | — |

### ⚠ EVERY COMMITTED FBX IS MESH-ONLY

All 13 tracked `.fbx` files contain `Geometry`, `Material` and `Texture` records and
**zero** `Deformer`, `LimbNode` or `AnimationStack` records. The rigs referenced by
commits `a7f40a5`, `46876c1` and `5bb83ef` exist **only inside the `prod.blend`
files**. Nothing skinned has ever left Blender.

Consequence: the Unity project has never seen a rig, so no avatar has been
configured and no import setting is load-bearing yet. **Everything about the
skeleton is still cheap to change.** That stops being true the moment the first
clip is authored against it.

### Known gaps

- `SkeletonMage/armor_metallic.png` is **missing**; the other three have one. Either
  the mage's armour is non-metallic by design (then the material must not sample a
  metallic map at all) or the bake was skipped.
- `Weapons/` has `mesh_quad.fbx` and a reference image but **no textures at all**.
- Export naming is inconsistent and must be normalised before import:
  `skeleton.fbx` (archer, mage, warrior) vs `body.fbx` (knight);
  `mesh_quad.fbx` (archer, mage, warrior, weapons) vs `mesh_uv.fbx` (knight).

---

## 2. The one constraint that governs this pack

**Modularity is a rig promise, not a mesh promise.** A buyer's expectation is that
any armour piece drops onto any of the four skeletons and animates correctly. That
holds only if:

1. **One armature, shared by all four characters and every armour module.** Same
   bone names, same rest pose, same bone rolls, same hierarchy. Not "similar" — the
   same armature datablock, linked or appended, never re-created per character.
2. **Every armour module is skinned to that armature**, not parented to a bone.
   Bone-parenting is fine for rigid props (a helmet, a pauldron that does not
   deform); anything crossing a joint must be weighted.
3. **Unity Humanoid avatar is configured once and reused.** In Unity, armour modules
   import as separate `SkinnedMeshRenderer`s and are bound at runtime by assigning
   `bones` + `rootBone` from the body's renderer. This requires *identical bone
   arrays*, which is another way of stating rule 1.

Get this wrong and the fix is not "adjust a weight" — it is re-authoring every clip.
Settle the shared rig before any animation work begins.

### Weapons are the exception

Weapons are rigid props attached to a hand bone, not skinned. They need a defined
grip convention (which bone, what local offset/rotation) fixed once and applied to
every weapon, so swapping a sword for an axe needs no per-weapon adjustment.

---

## 3. Repository layout

```
undead-legion-pack/
├── SkeletonKnight/      prod.blend + textures + reference + FBX exports
├── SkeletonArcher/      "
├── SkeletonMage/        "
├── SkeletonWarrior/     "
├── Weapons/             weapons.blend + FBX
└── skeletons/           Unity project (Unity 6000.4.0f1, URP 17.4.0)
    └── Assets/UndeadLegion/
        ├── Animations/          shared clips — retarget to all four
        ├── Demo/{Scenes,Scripts,Editor}
        ├── Materials/{URP,BuiltIn}
        ├── Models/<Character>/
        ├── Prefabs/{Characters,Modules}
        └── Textures/<Character>/
```

`Animations/` is **flat and shared**, not per-character. This is the structural
difference from a pack of unrelated creatures: four characters on one humanoid rig
means one clip set, retargeted — authoring per-character clips would quadruple the
work and break the pack's premise.

`Prefabs/Characters/` holds assembled ready-to-drop prefabs.
`Prefabs/Modules/` holds individual armour pieces for runtime swapping.

---

## 4. Conventions

**Animation export** — `<Character>@<Clip>.fbx`, e.g. `Skeleton@Idle.fbx`. The `@`
form is what Unity splits into a named clip automatically. Since the rig is shared,
prefer a neutral prefix (`Skeleton@Idle`) over a per-class one.

**Textures** — `<part>_<map>.png`: `body_color`, `body_normal`, `body_roughness`,
`armor_color`, `armor_normal`, `armor_roughness`, `armor_metallic`.
`*_orig.png` files are pre-edit backups and are **not shipped**; they are currently
tracked and should be moved out of the shipped texture set before packaging.

**Unity import** — normal maps must be marked `Texture Type: Normal map`; color maps
sRGB on; roughness/metallic sRGB **off**. Unity uses smoothness, not roughness, so
either invert the roughness bake or drive smoothness from the alpha of the metallic
map. Decide once and apply uniformly.

---

## 5. Git hygiene

- `*.blend1` are Blender autosaves. **Never commit them.** Six were tracked and were
  removed from the index on 2026-09-15 (files kept on disk).
- The Unity project's ignore rules live in `skeletons/.gitignore`, anchored with
  leading slashes so an asset folder named `Build/` or `Temp/` under `Assets/` is
  never swallowed. Tracked: `Assets/`, `Packages/`, `ProjectSettings/` only.
- `.meta` files are tracked and load-bearing — they carry import settings and the
  GUIDs every prefab and material reference resolves through.
- The repo is already ~137 MB of `.git` for 74 files. Texture `*_orig.png` backups
  and repeated `.blend` saves are the main drivers. If animation exports push this
  past comfort, Git LFS is the lever — but it changes clone workflow and carries a
  GitHub quota, so it is a deliberate decision, not a default.

---

## 6. Tooling

- **Unity MCP** — registered for this project on 2026-09-15 and verified working:
  `uvx --from mcpforunityserver==10.2.0 mcp-for-unity --default-instance skeletons`.
  Server version **10.2.0** matches the installed package — `#main` has moved past the
  10.1.2 used by the creatures pack, so check
  `Library/PackageCache/com.coplaydev.unity-mcp@*/package.json` before pinning a version.
  The Editor bridge listens on `127.0.0.1:6400`.
  `--default-instance` is deliberate: `~/.unity-mcp/unity-mcp-port.json` holds a **stale
  entry claiming port 6400 for a different project**, so instance selection is ambiguous
  without it.
- **Asset Store Tools** is embedded at `skeletons/Packages/com.unity.asset-store-tools`
  (760 files, not listed in `manifest.json`). It ships the same validator Unity runs at
  submission review — see §7.
- **Blender MCP** — `C:\Users\vadym\.local\bin\blender-mcp.exe`. Needed for any rig
  work, since the rigs live only in the `.blend` files.
- Blender 4.3 and 5.2 are both installed. Pick one and stay on it; a `.blend` saved
  in 5.2 will not open in 4.3.

---

## 7. Demo scene and submission validation

`Assets/UndeadLegion/Demo/Scenes/UndeadLegion_Demo.unity` — built 2026-09-15 as the
minimum shippable scene so store review can begin. Contents: `Ground` (30 × 30 m plane),
`SK_SkeletonKnight`, a warm key light with soft shadows, a cool directional fill,
trilight ambient, and a camera framed on the character at 40° FOV.

The character is the knight assembled from **two** meshes, which is the pack's premise
made visible: `Body` (4,173 v) + `Armor` (6,578 v). The armour mesh is named `Skirt`
inside the FBX but is actually the **complete armour set** — helmet, pauldrons, chest,
greaves and boots.

### Import decisions, applied uniformly

- **Scale**: source art is ~1.0 m tall. `ModelImporter.globalScale = 1.8` brings the
  knight to **1.795 m**. Any future character must use the same treatment or the pack
  will not be internally consistent.
- **Smoothness**: URP has no roughness input. The maps were packed once with Pillow —
  `R = metallic`, `A = 1 - roughness` — into `<part>_metallicsmoothness.png`,
  which is what `_MetallicGlossMap` expects. The raw `*_roughness.png` and
  `*_metallic.png` are therefore **not shipped**; they stay in the repo-root source
  folders. Materials set `_Metallic = 1` and `_Smoothness = 1` so the map alone drives
  both.
- **Colour space**: normal maps import as `NormalMap`; the packed map is
  `sRGB = false` with `alphaSource = FromInput`; albedo is sRGB.
- **Materials**: `materialImportMode = None` on the FBX — the pack's own materials in
  `Materials/URP/` are the single source of truth.

### Validator status — 31 pass, 0 fail, 1 warning

Run the Asset Store validator headlessly against `Assets/UndeadLegion` (category
`3D/Characters/Humanoids`). Its classes are `internal`, so drive
`AssetStoreTools.Validator.CurrentProjectValidator` by reflection; `Title` and `Result`
on `AutomatedTest` are **fields, not properties**.

**⚠ OUTSTANDING: `Check Model Orientation` (warning).** Every mesh node carries
`localRotation = (89.98, 0, 0)` — the Blender Z-up export baked onto the node. The
validator wants identity on any transform holding a `MeshFilter`/`SkinnedMeshRenderer`.
`ModelImporter.bakeAxisConversion = true` **does not fix this** (tried and reverted);
it addresses the FBX axis metadata, not an explicit node rotation. The real fix is in
Blender — apply the rotation before export — and it belongs in the same pass that
exports the rigs, since re-exporting later would invalidate any clip authored first.

`Check Prefab Transforms` was a hard **fail** and is fixed: the Asset Store requires a
prefab's root at exactly position 0 / rotation 0 / scale 1, compared at **12 decimal
places**. The grounding offset that seats the character on Y = 0 therefore lives on the
`Body` and `Armor` children, never on the root.

### Verifying a scene actually renders

`manage_camera screenshot` returns a **stale Game view frame** in edit mode — it showed
empty ground for a scene that was in fact correct. To see the truth, render explicitly:
assign a `RenderTexture` to the camera, call `cam.Render()`, `ReadPixels`, and write the
PNG. `GeometryUtility.TestPlanesAABB` is the cheap companion check for "is it even in
frustum".
