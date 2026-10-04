namespace UndeadLegion.Extended
{
    /// <summary>What an armour module is, for the dressing rules.</summary>
    public enum ArmourKind { Armour, Robe, Hood }

    /// <summary>
    /// Armour classification for the army spawner. Robes and the casters' hoods are caster attire: the Mage and the
    /// Necromancer always wear a robe and a hood; melee classes wear no robe and no hood, except that the Assassin may wear
    /// the Mage's hood. Classes are the character names without the "Skeleton" prefix (Knight, Archer, Assassin, Mage,
    /// Necromancer, Warrior).
    /// </summary>
    public static class ArmourRules
    {
        public static bool IsCaster(string cls) { return cls == "Mage" || cls == "Necromancer"; }

        /// <summary>The kind of a module from its source set and slot.</summary>
        public static ArmourKind KindOf(string sourceClass, string module)
        {
            if (module == "Robe") return ArmourKind.Robe;
            if (module == "Helm" && IsCaster(sourceClass)) return ArmourKind.Hood;
            return ArmourKind.Armour;
        }

        /// <summary>The slots a robe covers; a caster never wears them, a melee skeleton may.</summary>
        public static bool UnderRobe(string module) { return module == "Chest" || module == "Skirt" || module == "Pants"; }

        /// <summary>Whether a skeleton of class <paramref name="wearer"/> may wear <paramref name="module"/> from the
        /// <paramref name="sourceClass"/> set.</summary>
        public static bool CanWear(string wearer, string sourceClass, string module)
        {
            var kind = KindOf(sourceClass, module);
            if (IsCaster(wearer))
            {
                if (UnderRobe(module)) return false;              // the robe covers chest, skirt and pants
                if (module == "Helm") return kind == ArmourKind.Hood;   // the head is always a hood
                return true;
            }
            if (kind == ArmourKind.Robe) return false;
            if (kind == ArmourKind.Hood) return wearer == "Assassin" && sourceClass == "Mage";
            return true;
        }

        /// <summary>Slots a skeleton of this class always wears (never left bare).</summary>
        public static bool Required(string wearer, string module)
        {
            return IsCaster(wearer) ? module == "Robe" || module == "Helm" : module == "Chest";
        }
    }
}
