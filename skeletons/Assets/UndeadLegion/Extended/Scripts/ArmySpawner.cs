using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using UndeadLegion.Demo;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// Spawns a formation of skeletons with varied looks: random class, an armour mix that borrows slots from other classes
    /// (a robe replaces chest, skirt and pants), a loadout that suits the class, a subtle tint, team-coloured eyes, and a
    /// rise-from-the-ground entrance. Everything is optional, so it also works as a plain crowd spawner.
    /// </summary>
    public class ArmySpawner : MonoBehaviour
    {
        [Tooltip("Character prefabs to pick from (the extended variants carry physics, navigation and AI).")]
        public List<GameObject> characters = new List<GameObject>();
        [Tooltip("Every armour module prefab (ArmorModule) the mix may borrow from.")]
        public List<GameObject> armourCatalogue = new List<GameObject>();
        public int count = 10;
        public int columns = 5;
        public float spacing = 1.4f;
        public int team = 0;
        [ColorUsage(false, true)] public Color eyeColor = new Color(0.3f, 2.4f, 1.6f);

        [Header("Variety")]
        [Range(0f, 1f)] [Tooltip("Chance that a slot borrows a piece from another class instead of the character's own.")]
        public float mixChance = 0.45f;
        [Range(0f, 1f)] [Tooltip("Chance that a slot is left empty.")]
        public float bareChance = 0.1f;
        public bool randomLoadout = true;
        [Range(0f, 0.6f)] public float tintStrength = 0.22f;
        [Tooltip("Casters (Mage, Necromancer) walk upright; the rest use the heavy gait.")]
        public bool gaitByClass = true;

        [Header("Behaviour")]
        public bool enableAI = true;
        public bool riseFromGround = true;
        [Tooltip("Random delay per skeleton for the rise, seconds.")]
        public float riseStagger = 1.2f;
        public float wanderRadius = 0f;

        public readonly List<GameObject> spawned = new List<GameObject>();

        static readonly string[][] Slots =
        {
            new[] { "Helm" }, new[] { "Chest" }, new[] { "Robe" }, new[] { "Skirt" }, new[] { "Pants" },
            new[] { "Glove_L", "Glove_R" }, new[] { "Greave_L", "Greave_R" }, new[] { "Boot_L", "Boot_R" },
        };

        void Start() { }

        [ContextMenu("Spawn")]
        public void Spawn()
        {
            if (characters.Count == 0) return;
            int rows = Mathf.CeilToInt(count / (float)Mathf.Max(1, columns));
            for (int i = 0; i < count; i++)
            {
                int c = i % columns, r = i / columns;
                Vector3 local = new Vector3((c - (columns - 1) * 0.5f) * spacing, 0f, -(r - (rows - 1) * 0.5f) * spacing);
                local += new Vector3(Random.Range(-0.2f, 0.2f), 0f, Random.Range(-0.2f, 0.2f));
                Vector3 pos = transform.TransformPoint(local);
                NavMeshHit hit; if (NavMesh.SamplePosition(pos, out hit, 2f, NavMesh.AllAreas)) pos = hit.position;
                var go = SpawnOne(characters[Random.Range(0, characters.Count)], pos, transform.rotation);
                if (go != null) spawned.Add(go);
            }
        }

        [ContextMenu("Clear")]
        public void Clear()
        {
            foreach (var g in spawned) if (g != null) Destroy(g);
            spawned.Clear();
        }

        public GameObject SpawnOne(GameObject prefab, Vector3 position, Quaternion rotation)
        {
            var go = Instantiate(prefab, position, rotation);
            string cls = ClassOf(prefab.name);
            go.name = prefab.name + "_" + spawned.Count;
            var modules = go.GetComponent<SkeletonModules>();
            if (modules != null && armourCatalogue.Count > 0) DressRandom(modules, cls);
            var weapon = go.GetComponent<SkeletonWeapon>();
            if (weapon != null && randomLoadout) EquipFor(weapon, cls);
            if (tintStrength > 0f) Tint(go);
            var health = go.GetComponent<SkeletonHealth>(); if (health != null) health.team = team;
            var eyes = go.GetComponent<UndeadLegion.Demo.SkeletonEyes>(); if (eyes == null) eyes = go.AddComponent<UndeadLegion.Demo.SkeletonEyes>(); eyes.SetColor(eyeColor);
            var nav = go.GetComponent<SkeletonNavController>();
            if (nav != null)
            {
                if (gaitByClass) nav.gait = cls == "Mage" || cls == "Necromancer" ? SkeletonNavController.Gait.Upright : SkeletonNavController.Gait.Heavy;
                if (nav.Agent != null) nav.Agent.Warp(position);
            }
            var ai = go.GetComponent<SkeletonAI>(); if (ai != null) { ai.enabled = enableAI; ai.wanderRadius = wanderRadius; ai.magicColor = eyeColor * 0.9f; }
            var twitch = go.GetComponent<SkeletonTwitch>(); if (twitch != null) twitch.enabled = true;
            if (riseFromGround) StartCoroutine(Rise(go, Random.value * riseStagger));
            return go;
        }

        static string ClassOf(string prefabName)
        {
            foreach (var n in new[] { "Necromancer", "Mage", "Knight", "Warrior", "Archer", "Assassin" }) if (prefabName.Contains(n)) return n;
            return "";
        }

        IEnumerator Rise(GameObject go, float delay)
        {
            var d = go.GetComponent<SkeletonDissolve>();
            // the AI waits until the skeleton has risen; whether it is enabled at all (a battle started meanwhile) is left alone
            var ai = go.GetComponent<SkeletonAI>(); if (ai != null) ai.Suspended = true;
            var rends = go.GetComponentsInChildren<Renderer>();
            foreach (var r in rends) r.enabled = false;
            yield return new WaitForSeconds(delay);
            if (go == null) yield break;
            foreach (var r in rends) if (r != null) r.enabled = true;
            if (d != null) { d.DissolveIn(); yield return new WaitForSeconds(d.duration); }
            if (ai != null && go != null) ai.Suspended = false;
        }

        void DressRandom(SkeletonModules modules, string cls)
        {
            var bySource = new Dictionary<string, Dictionary<string, GameObject>>();
            foreach (var p in armourCatalogue)
            {
                if (p == null) continue; var m = p.GetComponent<ArmorModule>(); if (m == null) continue;
                string src = ClassOf(m.character);
                Dictionary<string, GameObject> set; if (!bySource.TryGetValue(src, out set)) bySource[src] = set = new Dictionary<string, GameObject>();
                set[m.moduleName] = p;
            }
            var chosen = new Dictionary<string, GameObject>();
            var sources = new List<string>(bySource.Keys);
            foreach (var slot in Slots)
            {
                if (Random.value < bareChance && slot[0] != "Chest" && slot[0] != "Robe") continue;
                string src = cls;
                if (Random.value < mixChance)
                {
                    var withSlot = sources.FindAll(s => bySource[s].ContainsKey(slot[0]));
                    if (withSlot.Count > 0) src = withSlot[Random.Range(0, withSlot.Count)];
                }
                Dictionary<string, GameObject> set;
                if (!bySource.TryGetValue(src, out set)) continue;
                foreach (var piece in slot) { GameObject pf; if (set.TryGetValue(piece, out pf)) chosen[piece] = pf; }
            }
            if (chosen.ContainsKey("Robe")) { chosen.Remove("Chest"); chosen.Remove("Skirt"); chosen.Remove("Pants"); }
            else if (chosen.ContainsKey("Pants") && chosen.ContainsKey("Skirt") && Random.value < 0.5f) chosen.Remove("Skirt");
            modules.SetAll(false);
            foreach (var pf in chosen.Values) modules.Wear(pf);
        }

        static readonly string[] Melee = { "Sword + shield", "Sword", "Axe + round shield", "Mace", "Longsword (2H)", "Battle axe (2H)" };
        static readonly string[] Rogue = { "Two daggers", "Dagger", "Sword" };
        static readonly string[] Caster = { "Staff", "Wand" };

        void EquipFor(SkeletonWeapon weapon, string cls)
        {
            string[] pool = cls == "Archer" ? new[] { "Recurve bow", "Recurve bow", "Dagger" }
                          : cls == "Assassin" ? Rogue
                          : cls == "Mage" || cls == "Necromancer" ? Caster : Melee;
            string want = pool[Random.Range(0, pool.Length)];
            for (int i = 0; i < weapon.Count; i++) if (weapon.NameAt(i) == want) { weapon.Equip(i); return; }
        }

        void Tint(GameObject go)
        {
            var hue = Color.HSVToRGB(Random.value, 0.5f, 1f);
            var tint = Color.Lerp(Color.white, hue, tintStrength * Random.Range(0.5f, 1f)) * Random.Range(0.85f, 1.05f); tint.a = 1f;
            var mpb = new MaterialPropertyBlock();
            foreach (var piece in go.GetComponentsInChildren<ArmorPiece>(true))
            {
                var r = piece.GetComponent<Renderer>(); if (r == null) continue;
                r.GetPropertyBlock(mpb); mpb.SetColor("_BaseColor", tint); r.SetPropertyBlock(mpb);
            }
        }
    }
}
