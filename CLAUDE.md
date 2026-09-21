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
| Weapons (13 meshes)  | done | 6 textured (sword, dagger, axe, mace, both shields), 7 untextured | n/a | `SM_*.fbx` ×13 | n/a | `M_Weapon_<Name>` ×6 + placeholder | **yes** (11 loadouts, `W_*` prefabs) |

Shared clips so far: `Idle`, `Idle_02`, `Idle_03` (loops, 8 / 12 / 12 s) +
`Twitch_01..03` (additive), on `AC_Skeleton`. Armour materials render both faces
(torn cloth, open hoods); body materials stay single-sided.

All six characters share one armature (§2), every body and armour module is skinned to
it, and every exported model imports in Unity with the **same 68-bone hierarchy**
(66 + two weapon sockets), the same bone array on every renderer, Hips at 0.982 m and
mesh nodes at identity rotation.

**First clips exist (2026-09-19), so the skeleton is frozen.** As of 2026-09-20 there
are **35 clips** in `Assets/UndeadLegion/Animations/` (`Skeleton@<Name>.fbx`, 30 fps,
every one verified on all six models with `verify_clip.py` + `ground_clip.py`) plus
`AC_Skeleton.controller` (Base: every clip as a state; Twitch: additive layer):

| Group | Clips |
|---|---|
| Idles (loop) | `Idle`, `Idle_02`, `Idle_03` (hand-fixed 2026-09-21: blades forward, Idle grounded, Idle_02 upright with hanging arms); weapon idles `Idle_TwoHanded` (axe on the shoulder), `Idle_Propped` (leaning on the staff), `Idle_Bow`, `Idle_Staff`, `Idle_Wand` |
| Impaled (hand-authored) | `Impaled_Idle` (loop: on its knees, hunched, sword through the belly), `Impaled_Rise` (one-shot: pulls it out, stands up, ends on the neutral standing pose) |
| Twitch (additive) | `Twitch_01/02/03` head + jaw |
| Locomotion (loop, root motion) | `Walk_Fwd`, `Walk_Back`, `Run_Fwd`, `Strafe_Left` (mirrored right), `Strafe_Right` |
| One-handed | `Attack_1H_01` (slash), `Attack_1H_02` (thrust), `Shield_Bash`, `Block` |
| Two-handed | `Attack_2H_01` (overhead chop), `Attack_2H_02` (horizontal sweep) — left hand locked on the handle |
| Bow | `Shoot_01` (slow draw), `Shoot_02` (quick) — authored arm keys over the generated body |
| Magic | `Cast_Wand_01/02`, `Cast_Staff_01/02` (both hands on the staff) |
| Specials | `Summon` (necromancer, arms overhead), `AOE_Cast` (mage slam), `Taunt` (warrior, chest beat + arms wide), `Cutthroat` (assassin), `Rally` (knight, sword raised) |
| Death | `Death_01` (struck, falls on the back), `Death_02` (kneels, crumples sideways) |

**Measured speed table** (Unity, Humanoid, root motion on, Knight; the other five are
identical because the avatar is shared). Ship these numbers with the pack:

| Clip | Length | Travel per loop | Speed |
|---|---|---|---|
| `Walk_Fwd` | 1.400 s | +0.724 m | 0.52 m/s |
| `Walk_Back` | 3.433 s | −1.119 m | 0.33 m/s |
| `Run_Fwd` | 0.967 s | +1.107 m | 1.14 m/s |
| `Strafe_Left` | 1.467 s | −0.599 m (X) | 0.41 m/s |
| `Strafe_Right` | 1.467 s | +0.599 m (X) | 0.41 m/s |

Measured on all six models: Idle travel 0, Head 5.2° / Hips 2.5° of motion; Twitch_03
over Idle adds Head 5.7° / Jaw 4.7° peaks with Hips at 0.00°. Every clip's lowest baked
vertex is ≥ 0 on every model except `Death_02` (Necromancer robe −5.6 cm during the
kneel, §8 "Grounding"). Not yet authored: turns, hits/staggers, knockdown/get-up
(the showcase already lists those sections and skips missing clips). The pipeline test
clip `Test_RootMotion` stays in the anim file, not in Unity.

### Known gaps

- `SkeletonMage`, `SkeletonNecromancer` and `SkeletonAssassin` have **no `armor_metallic.png`**;
  Knight, Archer and Warrior do. Either those armours are non-metallic by design (then
  the material must not sample a metallic map) or the bake was skipped.
- **Weapons** (2026-09-20): `Weapons/prod.blend` replaced `weapons.blend` as the source.
  `H1Sword`, `H1Dagger`, `H1Axe`, `H1Mace`, `H1HeaterShield` have UVs and 512² PBR maps
  (`Weapons/<lower>_{color,normal,roughness[,metallic]}.png`, packed by
  `tools/pack_textures.py -- Weapons` into `Textures/Weapons/`, materials
  `M_Weapon_<Name>` made by the import setup, assigned inside the `W_*` weapon prefab).
  The round shield got its maps on 2026-09-21 (commit `10740f3`). Still untextured on
  the placeholder: longsword, battle axe, longbow, staff, spellbook, arrow. Several meshes were rescaled in prod.blend (longsword 1.15 m, staff
  1.24 m, heater shield 0.70 m at pack scale); the grips carried over at the same
  relative position along the length. The **Arrow** in prod.blend is 2 cm long, so it is
  still exported from `weapons.blend` (`--only Arrow`). **`H1Wand`** in prod.blend is the
  staff mesh squashed to 0.39 m in length only and renders as a block: not exported, no
  Wand loadout until a real mesh exists. `Weapons/prod.blend1` came in tracked from a
  remote commit and is removed from the index (autosaves are ignored, §5).
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
        ├── Models/<Character>/SK_<Character>.fbx   rigged body + modules, Humanoid
        ├── Prefabs/{Characters,Modules}
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
Additive` + Aim Offset).

**Implemented in Unity 2026-09-20.** `AC_Skeleton.controller` has three layers: `Base`
(every clip), `UpperBody` (Override, weight 1, mask `AM_UpperBody.mask`: humanoid
Body/Head/Arms/Fingers on, Root/legs/IK off, plus the 55 extra transforms under
`Spine1`; states `Empty` + every clip tagged `layer: upper` in `Animations/clips.json`),
`Twitch` (Additive, trigger-fired once), `TwitchLoop_01..03` (Additive, weight 0, one
looping state each: the demo's twitch toggles set the weight; the twitch clips import
with Loop Time on, which the trigger layer's exit-time transition still ends after one
pass). The manifest tag is the single source of truth for "can be
performed on the move" (`upper`: Attack_1H_01/02, Shield_Bash, Block, Shoot_01/02,
Cast_Wand_01/02, Cast_Staff_02, Rally) versus "full stop" (`full`: Attack_2H_01/02,
Cast_Staff_01, Summon, AOE_Cast, Taunt, Cutthroat). Measured by
`build_twitch_controller.py`: Walk_Fwd on Base + Attack_1H_01 on UpperBody gives the
walk's legs (LeftUpLeg within 0.00° of the walk alone, 31° swing) and the attack's arms
and spine (RightArm within 0.00° of the attack alone, 74° swing). The demo routes
automatically: an upper clip clicked while a locomotion loop plays goes to `UpperBody`
("upper body over Walk_Fwd"); a full-stop clip takes `Base` and the loop resumes after
it (`layer_smoke.py` proves both in play mode). Humanoid masks cannot cut inside the
spine (Body is one part), so the upper layer owns the whole spine above the hips; the
walk keeps hips + legs, which is the cut the clips were authored for.

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
hands: 0.085 for Attack_2H_*, 0.22 for Cast_Staff_*. Verified with `weapon_shots.py`
on the battle axe.

Weapon idles: Kimodo has no props, so "axe resting on the shoulder" comes back as
hanging arms. `--arm-pose <preset>` (manifest key `arm_pose`) puts the hands on IK at
an authored position/orientation written in the socket's own frame and following the
torso's sway; presets in `glb_retarget.ARM_POSES`. ⚠ The detached batch loads its code
at start: after editing `anim_batch.py` restart the process, and clear the affected
entries from `build_state.json` (the signature already contained the new manifest key,
so the old process had marked them built without the argument). Never run a manual
retarget with `--save` while the batch is mid-clip: two Blender processes writing
`skeleton_anim.blend` is a corrupt file.

### Hand-authored clips and idle fixes (2026-09-21)

The user's review of the idles: blades pointed into the model, Idle's feet floated, Idle_02
was hunched with a bent left arm and looked sideways. `tools/anim_fix_idles.py` rewrites
the three actions in place, no Kimodo: every frame, the forearm is pronated about its
own axis until the socket's hilt axis points forward (12° out); Idle's torso is dropped
10 mm (its hips sat above the IK legs' reach, which lifted both feet 9 mm); Idle_02's
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
breathe. `Impaled_Rise` (150 frames, 5 s) is a **Kimodo clip spliced onto the base**
(user's choice among five candidates, `External Anims/Kimodo/rise_a.glb`, manifest
entry with `blend_from: Impaled_Base`): `glb_retarget.py --blend-from` starts the clip on
the base pose and crossfades every target and the hips into the generated motion over
18 frames; `--arm-keys "0:base,0.1:base,0.3:base_out,0.45:free"` keeps the base's hands,
slides the right hand out along the POSED hilt axis by a blade length, then hands the
arms to the source; `--elbow-pole` drives the arm IK with a pole held outward (the first
procedural pull folded the elbow into the body). Trimmed to 91 frames (`src_end 90`) with
`--blend-to Idle --blend-out 20`: frames 70..90 crossfade every target and the hips into
Idle's frame 1 so the clip ends upright and still (the source swayed on for 2.5 s more).
Grounded `twoway` (the stance changes) and exported with `lift 0.009`: Unity's Humanoid
floats this clip ~1 cm more than the idles at the default 15 mm. Kimodo cannot take a start pose (the
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
