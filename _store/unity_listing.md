# Undead Legion - Modular Skeleton Army

## Summary

Six skeleton warriors on one shared humanoid rig. 48 swappable armour pieces fit any skeleton, plus 12 weapons and 58 Humanoid animations with root motion. URP-ready.

## Description

Raise an undead army from a single rig.

Undead Legion is a modular skeleton character pack: six class presets, a full set of swappable armour and weapons, and one animation set that plays on every character. All six skeletons share the same humanoid rig, so every armour piece fits every skeleton and every animation works on every character.

**Six ready-made classes**
Knight, Warrior, Archer, Assassin, Mage and Necromancer, each a dressed, animated prefab you can drop straight into a scene.

**Modular armour**
48 armour pieces are separate prefabs: helms, chest plates, gloves, greaves, boots, skirts, robes and pants. Any piece binds to any skeleton at runtime by bone name, so you can put the Knight's helm on the Mage, give the Warrior the Necromancer's robe, or build your own mixes. A simple component switches pieces on and off and wears pieces borrowed from other sets.

**Weapons**
12 weapons: sword, axe, mace, dagger, wand, heater shield, round shield, longsword, battle axe, staff, recurve bow and arrow. They attach to adjustable hand slots and come in 11 ready loadouts, from sword and shield to two daggers. The fingers close around a held weapon and relax on an empty hand. The recurve bow is rigged: its string follows the draw hand and the limbs bend with the pull, and the shot fires an arrow on release.

**58 animations**
- Idles: three general idles, a one-handed combat stance, and two-handed, bow and staff idles
- Locomotion: two complete sets with root motion. A heavy, shambling set for rank-and-file skeletons and an upright set for captains and casters, each with walk forward, walk back, run and strafes
- Combat: a stab and two swings for each arm, each with a heavy variant that throws the body into the blow; two two-handed swings, also with heavy variants; a held shield block; a bow shot; wand and staff casts
- Each weapon keeps its own attack pace: sword strikes play faster than authored, dagger strikes faster still, heavier weapons at full weight
- Specials: three taunts, rally, cutthroat, summon and an area cast
- Hit and stagger reactions
- Four deaths
- Additive head and jaw twitches and relaxed finger idles, so a crowd never stands perfectly still

**Built for gameplay**
- Humanoid avatars: the clips retarget to other humanoid characters, and your own Humanoid animations play on the skeletons
- A layered Animator controller: attack or cast with the arms while the legs keep walking, hold a shield block over any motion
- Root motion on locomotion, with a measured speed table in the documentation for matching in-place movement
- Clean, tested loops
- Glowing red eyes (any colour), seated in each skull's sockets, with bloom in the demo

**Demo scene**
Browse every character, armour piece, weapon and animation in an interactive demo, with eyes, root motion and turntable options.

Full documentation (PDF) is included.

## Technical Details

**Characters**
- 6 characters, fully dressed 16,728 - 18,870 triangles each
- Bare skeleton body 6,364 - 7,588 triangles
- 48 armour modules, 191 - 6,582 triangles each
- Scale: real-world, 1 unit = 1 m, characters about 1.7 m tall

**Weapons**
- 12 weapon prefabs, 498 - 5,074 triangles each
- Recurve bow rigged with 8 bones for the string and limbs

**Rigging**
- Rigged: Yes
- One shared 68-bone skeleton for all characters and armour
- Unity Humanoid avatar (53 mapped bones including fingers and jaw)
- Two weapon socket bones with adjustable hand slots
- Up to 4 bone influences per vertex

**Animation**
- Animated: Yes
- 58 animations, 30 fps, Humanoid
- Animation types: root motion (locomotion) and in-place (idles, attacks, casts, specials, reactions, deaths)
- 16 attack clips: 6 per arm (stab and two swings, regular and heavy) and 4 two-handed
- Per-weapon attack speed through one Animator parameter
- Additive twitch clips and finger-only idle clips
- Animation events on the bow shot

**Materials and textures**
- 24 materials (URP/Lit), plus a demo floor material
- 67 textures: colour, normal and packed metallic/smoothness maps
- Characters: 1024x1024 maps; weapons: mostly 512x512
- UV mapping: Yes
- LODs: No

**Requirements**
- Unity 6 (6000.4 or newer)
- Universal Render Pipeline (URP)

**Included**
- Character, armour and weapon prefabs
- Animator controller with avatar masks for upper body, arms and fingers
- Demo scene with runtime scripts (C#, source included)
- PDF documentation

## Keywords

skeleton, undead, modular, character, fantasy, RPG, knight, warrior, archer, mage, necromancer, assassin, armor, weapons, humanoid, animated, rigged, game ready, medieval, army
