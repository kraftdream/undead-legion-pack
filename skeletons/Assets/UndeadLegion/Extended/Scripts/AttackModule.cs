using System.Collections.Generic;
using UnityEngine;

namespace UndeadLegion.Extended
{
    /// <summary>One attack: the clip, when it lands, how far it reaches and how hard it hits.</summary>
    [System.Serializable]
    public class AttackMove
    {
        public string clip;
        [Range(0f, 1f)] [Tooltip("Normalised time of the hit (the hand-speed peak of the clip).")]
        public float hitAt = 0.45f;
        [Tooltip("Reach in metres (projectiles: the distance the caster keeps).")]
        public float range = 1.7f;
        public float damage = 15f;
        public float impulse = 50f;
        [Tooltip("Fires a projectile instead of a melee hit.")]
        public bool ranged;
        [Tooltip("Hits every enemy within 3 m of the target (on a cooldown).")]
        public bool area;
        [Tooltip("The projectile is the bow's own arrow (fired by the clip's BowRelease event).")]
        public bool arrow;
        [Tooltip("Extra clip speed for this move (1 = none). Multiplies the skeleton's attackSpeed and the weapon's pace (SkeletonWeapon.AttackSpeedFor).")]
        public float speed = 1f;

        /// <summary>The speed, 1 when unset.</summary>
        public float Speed { get { return speed > 0f ? speed : 1f; } }

        /// <summary>A copy at another clip speed.</summary>
        public AttackMove Faster(float s) { var m = (AttackMove)MemberwiseClone(); m.speed = s; return m; }

        public static AttackMove Melee(string c, float at, float r, float d, float i) { return new AttackMove { clip = c, hitAt = at, range = r, damage = d, impulse = i }; }
        public static AttackMove Bolt(string c, float at, float r, float d, float i) { return new AttackMove { clip = c, hitAt = at, range = r, damage = d, impulse = i, ranged = true }; }
        public static AttackMove Arrow(string c, float at, float r, float d, float i) { return new AttackMove { clip = c, hitAt = at, range = r, damage = d, impulse = i, ranged = true, arrow = true }; }
        public static AttackMove Area(string c, float at, float r, float d, float i) { return new AttackMove { clip = c, hitAt = at, range = r, damage = d, impulse = i, ranged = true, area = true }; }
    }

    /// <summary>
    /// A set of attacks that attaches to a skeleton while it holds one of the listed weapon loadouts. A skeleton attacks with
    /// the moves of every module that matches its loadout; a heavy module is skipped when the skeleton may not use heavy attacks.
    /// </summary>
    [System.Serializable]
    public class AttackModule
    {
        public string name;
        [Tooltip("Loadout names (SkeletonWeapon) this module attaches to. Empty = the skeleton holds nothing.")]
        public string[] weapons = new string[0];
        [Tooltip("Heavy attacks (bigger lunge, more damage); skipped by skeletons with Allow Heavy off.")]
        public bool heavy;
        public AttackMove[] moves = new AttackMove[0];

        public bool AttachesTo(string loadout)
        {
            if (string.IsNullOrEmpty(loadout)) return weapons == null || weapons.Length == 0;
            if (weapons == null) return false;
            foreach (var w in weapons) if (w == loadout) return true;
            return false;
        }

        static AttackModule Make(string n, bool heavy, string[] weapons, params AttackMove[] moves)
        {
            return new AttackModule { name = n, heavy = heavy, weapons = weapons, moves = moves };
        }

        static readonly string[] Swords = { "Sword + shield", "Sword" };
        static readonly string[] Daggers = { "Dagger", "Two daggers" };

        static AttackMove Stab() { return AttackMove.Melee("Attack_R_01_Stab", 0.30f, 1.8f, 18, 55); }
        static AttackMove Swing2() { return AttackMove.Melee("Attack_R_02_Swing", 0.46f, 1.7f, 20, 70); }
        static AttackMove Swing3() { return AttackMove.Melee("Attack_R_03_Swing", 0.50f, 1.7f, 20, 70); }

        /// <summary>
        /// The default modules, one set per weapon: the sword stabs and swings, regular attacks only; the dagger the same, and a
        /// second dagger adds the left-hand attacks; the axe mixes
        /// regular and heavy attacks; the mace too, without the stabs; the battle axe mixes regular and heavy two-handed swings,
        /// the longsword swings regular only. hitAt = the hand-speed peak measured on each clip (2026-10-04). The weapon's own
        /// pace (sword 1.3x, dagger 1.7x) is not here: SkeletonWeapon.AttackSpeedFor drives the controller's AttackSpeed
        /// parameter, so the same pace shows in every scene; a move's speed multiplies on top.
        /// </summary>
        public static List<AttackModule> Defaults()
        {
            return new List<AttackModule>
            {
                Make("Sword", false, Swords, Stab(), Swing2(), Swing3()),
                Make("Dagger", false, Daggers, Stab(), Swing2(), Swing3()),
                Make("Dagger, left hand (second dagger)", false, new[] { "Two daggers" },
                     AttackMove.Melee("Attack_L_01_Stab", 0.30f, 1.6f, 14, 45), AttackMove.Melee("Attack_L_02_Swing", 0.46f, 1.5f, 14, 55),
                     AttackMove.Melee("Attack_L_03_Swing", 0.50f, 1.5f, 14, 55)),
                Make("Axe", false, new[] { "Axe + round shield" }, Stab(), Swing2(), Swing3()),
                Make("Axe, heavy", true, new[] { "Axe + round shield" },
                     AttackMove.Melee("Attack_R_01_Stab_Heavy", 0.27f, 1.9f, 26, 85), AttackMove.Melee("Attack_R_02_Swing_Heavy", 0.46f, 1.8f, 26, 90),
                     AttackMove.Melee("Attack_R_03_Swing_Heavy", 0.48f, 1.8f, 26, 90)),
                Make("Mace", false, new[] { "Mace" }, Swing2(), Swing3()),
                Make("Mace, heavy", true, new[] { "Mace" },
                     AttackMove.Melee("Attack_R_02_Swing_Heavy", 0.46f, 1.8f, 26, 90), AttackMove.Melee("Attack_R_03_Swing_Heavy", 0.48f, 1.8f, 26, 90)),
                Make("Two-handed", false, new[] { "Longsword (2H)", "Battle axe (2H)" },
                     AttackMove.Melee("Attack_2H_01_Swing", 0.54f, 2.1f, 35, 120), AttackMove.Melee("Attack_2H_02_Swing", 0.43f, 2.2f, 30, 110)),
                Make("Two-handed, heavy", true, new[] { "Battle axe (2H)" },
                     AttackMove.Melee("Attack_2H_01_Swing_Heavy", 0.54f, 2.2f, 45, 150), AttackMove.Melee("Attack_2H_02_Swing_Heavy", 0.41f, 2.3f, 40, 140)),
                Make("Bow", false, new[] { "Recurve bow" }, AttackMove.Arrow("Shoot_01", 21f / 59f, 16f, 28, 50)),
                Make("Wand", false, new[] { "Wand" }, AttackMove.Bolt("Cast_Wand_01", 0.45f, 11f, 16, 35), AttackMove.Bolt("Cast_Wand_02", 0.45f, 11f, 16, 35)),
                Make("Staff", false, new[] { "Staff" }, AttackMove.Bolt("Cast_Staff_01", 0.55f, 12f, 24, 45), AttackMove.Area("AOE_Cast", 0.62f, 9f, 30, 90)),
                Make("Unarmed", false, new string[0], AttackMove.Melee("Attack_R_02_Swing", 0.46f, 1.4f, 8, 40), AttackMove.Melee("Attack_L_02_Swing", 0.46f, 1.4f, 8, 40)),
            };
        }
    }
}
