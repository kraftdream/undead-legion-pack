# Undead Legion Extended - Skeleton Army with Ragdolls, AI and NavMesh

## Summary

The full Undead Legion skeleton pack plus ragdolls, hit reactions, cloth, rise and dissolve effects, NavMesh movement, combat AI and an army spawner. URP.

## Description

Raise an undead army, then send it to battle.

Undead Legion Extended contains everything in Undead Legion - Modular Skeleton Army (six skeleton classes on one shared rig, 48 swappable armour pieces, 12 weapons and 58 Humanoid animations) and adds the systems that make the skeletons playable: physics, movement, combat and whole armies. Owners of Undead Legion can upgrade at a discount.

**Full-body ragdolls**
Every skeleton carries an 11-body ragdoll. While it animates, the bodies are hitboxes that tell you which part was struck. On death it falls with the impact of the killing blow and drops its weapons, and it can blend back to the animation for revives and get-ups.

**Hit reactions**
Physical flinches layered over any animation: a struck skeleton recoils through the spine, head and arms and recovers, while it keeps walking, idling or attacking.

**Cloth**
Robes, skirts and pants simulate as cloth, pinned at the waist and colliding with the legs, with distance culling for crowds.

**Rise and dissolve effects**
Skeletons rise out of the ground and turn to dust with a glowing edge, on a URP Lit dissolve shader that keeps each material's look. The glowing eyes bloom in the arena.

**NavMesh movement**
A NavMeshAgent drives directional locomotion blend trees built from the pack's measured walk, run, back and strafe clips, so the feet match the ground at any speed. A heavy, shambling gait for the rank and file and an upright gait for casters. Weapon idles keep a two-hander, a bow or a staff properly held while moving.

**Combat AI**
Skeletons find the nearest enemy, close in and attack with the moves that suit their weapon, from attack modules attached by the weapon held: regular one-handed attacks for swords and daggers, regular and heavy attacks for axes and maces, left-hand attacks with a second dagger, regular and heavy two-handed swings, bow shots, homing wand and staff bolts, and an area cast. Damage lands when the blow connects. Assassins fight with quick regular attacks only. Add your own modules or change the moves per weapon in the inspector. Teams, health, damage and death events are ready to connect to your game.

**Army spawner**
Spawn formations of varied skeletons: random classes, mixed armour borrowed across classes under dressing rules (casters always robed and hooded, the melee ranks in plate and leather with pieces missing), loadouts that suit each class, subtle colour variation and team-coloured eyes, rising from the ground one by one.

**Arena demo**
Two armies on a NavMesh arena. Raise them, start the battle, take control of any skeleton, strike or kill with the mouse, and switch cloth, death modes and corpse dissolving on the fly.

**Player demo**
Take a skeleton yourself: WASD to walk, Shift to run, the mouse to turn, click to attack through the weapon's moves, hold the right button to block with a shield, and fight waves of AI skeletons. Esc pauses and lets you switch class and weapon.

**Extended animation browser**
The character browser with the extended skeletons and a physics panel: switch cloth on and off, hit a skeleton by clicking it, kill it into a ragdoll, revive it, raise it from the ground or turn it to dust, alongside every animation, armour piece and weapon.

Everything from the base pack is included unchanged: the character browser demo, the layered Animator controller, the root-motion speed table and the documentation. Full documentation for the extended systems (PDF) is included.

## Technical Details

**Everything in Undead Legion - Modular Skeleton Army**
- 6 characters on one 68-bone Humanoid rig, 16,728 - 18,870 triangles fully dressed
- 48 armour modules, 12 weapons (a rigged recurve bow), 58 animations at 30 fps
- URP/Lit materials, 1024x1024 character maps
- See that listing for the full breakdown

**Extended systems**
- 6 extended character prefabs (prefab variants of the base characters)
- Ragdoll: 11 rigidbodies with character joints per skeleton, kinematic hitboxes while animated
- Cloth: Unity Cloth on robes, skirts and pants, leg capsule colliders, distance culling
- Dissolve: URP Lit-based shader with height cut, noise and HDR edge; forward, depth and depth-normals passes
- Navigation: AI Navigation package (NavMeshAgent), two 2D directional locomotion blend trees at measured clip speeds
- Animator controller extended with locomotion blend trees and upper-body weapon idles
- 18 runtime scripts (C#, source included): ragdoll, hit reactions, health, cloth, dissolve, navigation, combat AI, projectiles, army spawner, battle camera, player controller and camera, and the demos
- Arena demo scene with a baked NavMesh and URP post-processing (bloom)
- Extended animation browser scene with a physics panel
- Player demo scene: control a skeleton against AI waves

**Requirements**
- Unity 6 (6000.4 or newer)
- Universal Render Pipeline (URP)
- AI Navigation package (com.unity.ai.navigation 2.x, listed in the project)

**Included**
- Everything in the base pack
- Extended prefabs, controller, shader and scripts
- Arena demo scene, the player demo and the extended animation browser
- PDF documentation for both the base pack and the extended systems

## Keywords

skeleton, undead, ragdoll, AI, navmesh, army, spawner, cloth, dissolve, hit reaction, combat, modular, character, fantasy, RPG, humanoid, animated, rigged, game ready, strategy

## Upgrade

Set up Undead Legion - Modular Skeleton Army as the upgrade source for this package, so owners pay the price difference.
