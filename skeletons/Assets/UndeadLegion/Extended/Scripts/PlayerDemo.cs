using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.UI;
using UndeadLegion.Demo;

namespace UndeadLegion.Extended
{
    /// <summary>
    /// The player demo: control one skeleton (PlayerSkeleton + PlayerCamera) against waves of AI skeletons from an
    /// ArmySpawner. Esc pauses and opens a menu to switch class (the controlled skeleton is replaced where it stands), change
    /// the weapon, or set how many enemies fight at once. The player's skeleton cannot die; it shows every hit.
    /// </summary>
    public class PlayerDemo : MonoBehaviour
    {
        [Tooltip("The playable characters (extended prefabs), in menu order.")]
        public List<GameObject> characters = new List<GameObject>();
        [Tooltip("Spawns the enemies (its team is the enemy team).")]
        public ArmySpawner enemies;
        public PlayerCamera playerCamera;
        public int startCharacter = 0;
        [Tooltip("Enemies alive at once.")]
        public int enemyCount = 4;
        public float spawnMinDistance = 9f, spawnMaxDistance = 14f;
        [Tooltip("Seconds before a fallen enemy is replaced.")]
        public float respawnDelay = 2.5f;
        public int playerTeam = 0;
        [ColorUsage(false, true)] public Color playerEyes = new Color(0.3f, 2.4f, 1.6f);

        static readonly string[] DefaultLoadouts = { "Sword + shield", "Axe + round shield", "Recurve bow", "Two daggers", "Wand", "Staff" };
        static readonly int[] EnemyCounts = { 1, 2, 4, 6, 8 };

        GameObject _player;
        PlayerSkeleton _control;
        int _character = -1;
        readonly List<SkeletonHealth> _enemies = new List<SkeletonHealth>();
        float _nextSpawn, _flash;
        int _kills;
        bool _paused;
        GameObject _menu;
        Text _hud, _enemiesLabel;
        Image _flashImage;
        readonly List<Button> _classButtons = new List<Button>();

        void Start()
        {
            BuildUI();
            SpawnPlayer(Mathf.Clamp(startCharacter, 0, characters.Count - 1), null);
            SetPaused(false);
        }

        // ------------------------------------------------------------------ player

        static string ClassOf(GameObject prefab)
        {
            foreach (var n in new[] { "Necromancer", "Mage", "Knight", "Warrior", "Archer", "Assassin" }) if (prefab.name.Contains(n)) return n;
            return prefab.name;
        }

        /// <summary>Replaces the controlled skeleton with one of the given character, where the current one stands.</summary>
        public void SpawnPlayer(int index, string loadout)
        {
            if (index < 0 || index >= characters.Count || characters[index] == null) return;
            Vector3 pos = transform.position; Quaternion rot = transform.rotation;
            if (_player != null)
            {
                pos = _player.transform.position; rot = _player.transform.rotation;
                _player.SetActive(false);            // out of SkeletonHealth.All at once (Destroy is deferred)
                Destroy(_player);
            }
            NavMeshHit hit; if (NavMesh.SamplePosition(pos, out hit, 2f, NavMesh.AllAreas)) pos = hit.position;
            var prefab = characters[index];
            string cls = ClassOf(prefab);
            _player = Instantiate(prefab, pos, rot);
            _player.name = "Player_" + cls;
            _character = index;

            var health = _player.GetComponent<SkeletonHealth>(); if (health != null) { health.team = playerTeam; health.invulnerable = true; }
            var eyes = _player.GetComponent<SkeletonEyes>(); if (eyes != null) eyes.SetColor(playerEyes);
            var nav = _player.GetComponent<SkeletonNavController>();
            if (nav != null)
            {
                nav.gait = ArmourRules.IsCaster(cls) ? SkeletonNavController.Gait.Upright : SkeletonNavController.Gait.Heavy;
                if (nav.Agent != null) nav.Agent.Warp(pos);
            }
            var weapon = _player.GetComponent<SkeletonWeapon>();
            if (weapon != null)
            {
                string want = !string.IsNullOrEmpty(loadout) ? loadout : DefaultLoadouts[Mathf.Clamp(index, 0, DefaultLoadouts.Length - 1)];
                for (int i = 0; i < weapon.Count; i++) if (weapon.NameAt(i) == want) { weapon.Equip(i); break; }
            }
            var playerAi = _player.GetComponent<SkeletonAI>();   // the move source: a player necromancer casts no AOE
            if (playerAi != null) playerAi.allowArea = cls != "Necromancer";
            _control = _player.AddComponent<PlayerSkeleton>();
            _control.magicColor = playerEyes * 0.9f;
            _control.inputEnabled = !_paused;
            _control.Hit += OnPlayerHit;
            if (playerCamera != null) { playerCamera.target = _player.transform; playerCamera.Snap(); }
            foreach (var e in _enemies) if (e != null) { var ai = e.GetComponent<SkeletonAI>(); if (ai != null) ai.target = null; }
            RefreshMenu();
        }

        void OnPlayerHit(DamageInfo info, bool blocked)
        {
            if (playerCamera != null) playerCamera.Shake(blocked ? 0.35f : 0.8f);
            if (!blocked) _flash = 0.35f;
        }

        void Equip(string loadout)
        {
            if (_player == null) return;
            var weapon = _player.GetComponent<SkeletonWeapon>(); if (weapon == null) return;
            for (int i = 0; i < weapon.Count; i++) if (weapon.NameAt(i) == loadout) { weapon.Equip(i); break; }
            var nav = _player.GetComponent<SkeletonNavController>(); if (nav != null) nav.OnLoadoutChanged();
            RefreshMenu();
        }

        // ------------------------------------------------------------------ enemies

        void UpdateEnemies()
        {
            _enemies.RemoveAll(e => e == null || e.IsDead);
            if (_enemies.Count >= enemyCount || enemies == null || _player == null || enemies.characters.Count == 0) return;
            if (Time.time < _nextSpawn) return;
            _nextSpawn = Time.time + respawnDelay * 0.4f;
            Vector3 centre = _player.transform.position;
            for (int tries = 0; tries < 12; tries++)
            {
                Vector2 dir = Random.insideUnitCircle.normalized;
                Vector3 p = centre + new Vector3(dir.x, 0f, dir.y) * Random.Range(spawnMinDistance, spawnMaxDistance);
                NavMeshHit hit; if (!NavMesh.SamplePosition(p, out hit, 1.5f, NavMesh.AllAreas)) continue;
                Vector3 face = centre - hit.position; face.y = 0f;
                var go = enemies.SpawnOne(enemies.characters[Random.Range(0, enemies.characters.Count)], hit.position, Quaternion.LookRotation(face));
                if (go == null) return;
                var h = go.GetComponent<SkeletonHealth>();
                if (h != null)
                {
                    h.team = enemies.team;
                    h.onDied.AddListener(() => { _kills++; _nextSpawn = Mathf.Max(_nextSpawn, Time.time + respawnDelay); });
                    _enemies.Add(h);
                }
                return;
            }
        }

        // ------------------------------------------------------------------ loop

        void Update()
        {
            if (ExtendedInput.KeyDown(KeyCode.Escape)) SetPaused(!_paused);
            if (!_paused) UpdateEnemies();
            if (_flashImage != null)
            {
                _flash = Mathf.Max(0f, _flash - Time.unscaledDeltaTime);
                _flashImage.color = new Color(0.6f, 0f, 0f, _flash * 0.6f);
            }
            if (_hud != null && _control != null && _player != null)
            {
                var weapon = _player.GetComponent<SkeletonWeapon>();
                string lo = weapon != null && weapon.Current >= 0 ? weapon.NameAt(weapon.Current) : "unarmed";
                _hud.text = ClassOf(characters[_character]) + "  |  " + lo + "  |  next: " + _control.NextAttack.Replace("Attack_", "") +
                            (_control.IsBlocking ? "  |  BLOCKING" : "") + "  |  enemies " + _enemies.Count + "  |  kills " + _kills +
                            "\nWASD move  ·  Shift + W run  ·  mouse turn  ·  left click attack (repeat for the next)  ·  hold right button block (shield)  ·  wheel zoom  ·  Esc menu";
            }
        }

        void SetPaused(bool paused)
        {
            _paused = paused;
            Time.timeScale = paused ? 0f : 1f;
            if (_menu != null) _menu.SetActive(paused);
            if (_control != null) _control.inputEnabled = !paused;
            Cursor.lockState = paused ? CursorLockMode.None : CursorLockMode.Locked;
            Cursor.visible = paused;
            RefreshMenu();
        }

        void OnDisable() { Time.timeScale = 1f; Cursor.lockState = CursorLockMode.None; Cursor.visible = true; }

        // ------------------------------------------------------------------ UI

        void BuildUI()
        {
            var canvasGo = new GameObject("PlayerDemoCanvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            var canvas = canvasGo.GetComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = canvasGo.GetComponent<CanvasScaler>(); scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080); scaler.matchWidthOrHeight = 1f;

            var flash = new GameObject("HitFlash", typeof(RectTransform), typeof(Image));
            var frt = (RectTransform)flash.transform; frt.SetParent(canvasGo.transform, false);
            frt.anchorMin = Vector2.zero; frt.anchorMax = Vector2.one; frt.offsetMin = frt.offsetMax = Vector2.zero;
            _flashImage = flash.GetComponent<Image>(); _flashImage.raycastTarget = false; _flashImage.color = new Color(0.6f, 0f, 0f, 0f);

            var hud = Panel(canvasGo.transform, new Vector2(0f, 0f), new Vector2(0f, 16f), new Vector2(1100, 0));
            _hud = DemoUI.CreateInfoRow(hud, ""); _hud.alignment = TextAnchor.MiddleCenter;

            // the pause menu: dim the screen, a centred panel
            _menu = new GameObject("PauseMenu", typeof(RectTransform), typeof(Image));
            var mrt = (RectTransform)_menu.transform; mrt.SetParent(canvasGo.transform, false);
            mrt.anchorMin = Vector2.zero; mrt.anchorMax = Vector2.one; mrt.offsetMin = mrt.offsetMax = Vector2.zero;
            _menu.GetComponent<Image>().color = new Color(0f, 0f, 0f, 0.55f);
            var panel = Panel(mrt, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(620, 0));
            DemoUI.CreateSectionLabel(panel, "PAUSED   ·   choose a skeleton to control");
            for (int i = 0; i < characters.Count; i++)
            {
                int idx = i;
                var b = DemoUI.CreateListButton(panel, "Skeleton " + ClassOf(characters[i]), Dark());
                b.onClick.AddListener(() => { SpawnPlayer(idx, null); });
                _classButtons.Add(b);
            }
            DemoUI.CreateSectionLabel(panel, "Weapon");
            for (int i = 0; i < AllLoadouts.Length; i++)
            {
                string lo = AllLoadouts[i];
                var b = DemoUI.CreateListButton(panel, lo, Dark()); b.onClick.AddListener(() => Equip(lo));
                _weaponButtons.Add(b);
            }
            DemoUI.CreateSectionLabel(panel, "Enemies");
            var eb = DemoUI.CreateListButton(panel, "", Dark()); _enemiesLabel = eb.GetComponentInChildren<Text>();
            eb.onClick.AddListener(CycleEnemies);
            DemoUI.CreateListButton(panel, "Resume (Esc)", new Color(0.16f, 0.36f, 0.3f)).onClick.AddListener(() => SetPaused(false));
        }

        static readonly string[] AllLoadouts = { "Sword + shield", "Sword", "Axe + round shield", "Mace", "Dagger", "Two daggers", "Longsword (2H)", "Battle axe (2H)", "Recurve bow", "Staff", "Wand" };
        readonly List<Button> _weaponButtons = new List<Button>();

        void CycleEnemies()
        {
            int i = System.Array.IndexOf(EnemyCounts, enemyCount);
            enemyCount = EnemyCounts[(i + 1) % EnemyCounts.Length];
            // fewer enemies: the extra ones crumble
            while (_enemies.Count > enemyCount) { var e = _enemies[_enemies.Count - 1]; _enemies.RemoveAt(_enemies.Count - 1); if (e != null && !e.IsDead) e.Die(); }
            RefreshMenu();
        }

        void RefreshMenu()
        {
            for (int i = 0; i < _classButtons.Count; i++) Tint(_classButtons[i], i == _character);
            string lo = "";
            if (_player != null) { var w = _player.GetComponent<SkeletonWeapon>(); if (w != null && w.Current >= 0) lo = w.NameAt(w.Current); }
            for (int i = 0; i < _weaponButtons.Count; i++) Tint(_weaponButtons[i], AllLoadouts[i] == lo);
            if (_enemiesLabel != null) _enemiesLabel.text = "Enemies at once: " + enemyCount + "   (click to change)";
        }

        static void Tint(Button b, bool on)
        {
            var img = b.GetComponent<Image>(); if (img != null) img.color = on ? new Color(0.55f, 0.42f, 0.16f) : Dark();
        }

        static Color Dark() { return new Color(0.2f, 0.21f, 0.24f); }

        static RectTransform Panel(Transform parent, Vector2 anchor, Vector2 pos, Vector2 size)
        {
            var go = new GameObject("Panel", typeof(RectTransform), typeof(Image), typeof(VerticalLayoutGroup), typeof(ContentSizeFitter));
            var rt = (RectTransform)go.transform; rt.SetParent(parent, false);
            rt.anchorMin = rt.anchorMax = rt.pivot = anchor;
            if (anchor == Vector2.zero) { rt.anchorMin = new Vector2(0.5f, 0f); rt.anchorMax = new Vector2(0.5f, 0f); rt.pivot = new Vector2(0.5f, 0f); }
            rt.anchoredPosition = pos; rt.sizeDelta = size;
            go.GetComponent<Image>().color = new Color(0.08f, 0.09f, 0.11f, 0.85f);
            var v = go.GetComponent<VerticalLayoutGroup>(); v.padding = new RectOffset(10, 10, 10, 10); v.spacing = 4;
            v.childControlHeight = true; v.childControlWidth = true; v.childForceExpandHeight = false;
            go.GetComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            return rt;
        }
    }
}
