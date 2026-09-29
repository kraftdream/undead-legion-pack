using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.UI;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// Records the Asset Store showreel as a PNG frame sequence, one STAGE per run (2026-09-29: "split it into
    /// chapters, render each separately, we stitch them later"; then "change chapter to stage, no fade in/out inside a
    /// stage, we do the fades when stitching").
    ///
    /// Runs in play mode over the demo scene: the UI is hidden, root motion is off, a dedicated camera sits at a fixed
    /// azimuth / elevation around the spawn point, every frame is rendered by hand into a RenderTexture (optionally
    /// supersampled) and written as PNG. `Time.captureDeltaTime` fixes the simulation step to 1 / fps, so the recording
    /// is deterministic whatever the machine renders at. Encode the folder with `tools/unity/showreel_encode.py`.
    ///
    /// A stage is a list of <see cref="Step"/>s (character, armour pieces to wear / take off, weapon loadout, idle,
    /// an optional attack, caption, duration). Each stage opens on a static title card on black, then hard-cuts to the
    /// first character; a change of character is a hard cut too (no fades: they belong to the stitch). A caption panel
    /// (title + one line) sits in the frame, drawn on a canvas parented to the recording camera. Stages: "modular" (the
    /// six presets, then the Knight dressed in other classes' pieces, then every weapon with its idle), "movement" (each
    /// character's locomotion set looping in place) and "attacks" (each preset's weapons, one attack each). Configure a ShowreelRecorder in the scene or use the menu / headless
    /// launcher.
    /// </summary>
    public class ShowreelRecorder : MonoBehaviour
    {
        [System.Serializable]
        public class Plan
        {
            [Tooltip("Substring of the character prefab's name (Knight, Archer, ...).")]
            public string character;
            [Tooltip("Loadout display names, in order (see SkeletonWeapon.loadouts).")]
            public List<string> loadouts = new List<string>();
        }

        [System.Serializable]
        public class ClipFor
        {
            public string loadout;
            public string clip;
        }

        /// <summary>One beat of a stage.</summary>
        [System.Serializable]
        public class Step
        {
            public string character;                    // prefab name substring; a change of character is a hard cut
            public string loadout;                      // weapon loadout display name; "" = hands empty
            public string idle = "Idle_01";             // the looping clip on Base
            public string attack;                       // optional one-shot played after `seconds` of the idle
            public float seconds = 3f;                  // hold on the idle before the attack / the next step
            public string title;                        // caption title
            public string text;                         // caption line
            public List<string> wear = new List<string>();     // "Warrior:Chest" - borrow that character's piece (its own piece of the same module goes off)
            public List<string> remove = new List<string>();   // "Chest" - take the current character's own piece off
            public bool titleCard;                      // a stage title on black instead of a scene beat
        }

        [Header("Output")]
        [Tooltip("Frames folder; empty = <project parent>/Showreel/<stage>/frames. Cleared before recording.")]
        public string outputDir = "";
        public int width = 1920;
        public int height = 1080;
        public int fps = 30;

        [Header("Camera (static, around the spawn point)")]
        [Tooltip("Degrees around the vertical from the character's front; 30 since 2026-09-29 (45 before), negative = the character's left side nearest.")]
        public float azimuth = -30f;
        public float elevation = 12f;
        public float distance = 4.0f;
        public float lookHeight = 1.0f;
        public float fieldOfView = 32f;

        [Header("Stage")]
        [Tooltip("modular | movement | attacks")]
        public string stage = "attacks";
        public float titleCardSeconds = 1.6f;
        [Tooltip("Movement stage: seconds per locomotion clip.")]
        public float movementSeconds = 3f;
        public bool captions = true;

        [Header("Timing of the attacks stage (seconds)")]
        public float holdBefore = 0.8f;
        public float holdAfter = 0.9f;
        public float characterGap = 0.4f;

        [Header("Attacks stage sequence")]
        public List<Plan> plans = new List<Plan>();
        [Tooltip("Attack clip per loadout name.")]
        public List<ClipFor> attacks = new List<ClipFor>();
        [Tooltip("Idle clip per loadout name (others use Idle_01).")]
        public List<ClipFor> idles = new List<ClipFor>();

        [Header("Quality")]
        [Tooltip("Offline, so everything can be maxed: the highest quality level, forced anisotropic filtering, full-resolution textures, the URP asset at 8x MSAA with a single 4096 shadow cascade over `shadowDistance`, HDR, soft shadows high, and SMAA (high) on the recording camera. Restored when the recording ends.")]
        public bool maxQuality = true;
        public float shadowDistance = 10f;
        [Tooltip("Render each frame at this multiple of the output size and box-filter it down (2 = 4 samples per pixel on top of MSAA + SMAA). Offline, so only memory limits it.")]
        [Range(1, 3)] public int supersample = 2;
        [Tooltip("Test runs: stop after this many steps (0 = the whole stage).")]
        public int maxLoadouts = 0;

        public bool autoStart = false;

        public bool Done { get; private set; }
        public int FramesWritten { get; private set; }
        public string Status { get; private set; }
        void SetStatus(string s) { Status = s; if (Application.isBatchMode) Debug.Log("Showreel: " + s + " (frame " + FramesWritten + ")"); }

        Camera _cam;
        RenderTexture _rt, _out;
        Texture2D _tex;
        SkeletonShowcase _showcase;
        Animator _animator; SkeletonWeapon _weapon; SkeletonModules _modules;
        string _currentCharacter;
        readonly List<Canvas> _hidden = new List<Canvas>();
        string _dir;
        // the caption canvas
        GameObject _canvasGo; Image _fade; Image _panel; Text _title; Text _text; Text _card;

        public static readonly object[][] DefaultPlans =
        {
            new object[] { "Knight", "Sword + shield", "Longsword (2H)" },
            new object[] { "Warrior", "Axe + round shield", "Battle axe (2H)", "Mace" },
            new object[] { "Archer", "Recurve bow", "Dagger" },
            new object[] { "Assassin", "Two daggers", "Dagger" },
            new object[] { "Mage", "Staff", "Wand" },
            new object[] { "Necromancer", "Staff", "Wand" },
        };
        public static readonly string[][] DefaultAttacks =
        {
            new[] { "Sword + shield", "Attack_R_Slice" }, new[] { "Sword", "Attack_R_Stab" },
            new[] { "Axe + round shield", "Attack_R_Slice" }, new[] { "Mace", "Attack_R_Stab" },
            new[] { "Dagger", "Attack_R_Stab" }, new[] { "Two daggers", "Attack_L_Slice" },
            new[] { "Longsword (2H)", "Attack_2H_01" }, new[] { "Battle axe (2H)", "Attack_2H_02" },
            new[] { "Recurve bow", "Shoot_01" }, new[] { "Staff", "Cast_Staff_01" }, new[] { "Wand", "Cast_Wand_01" },
        };
        public static readonly string[][] DefaultIdles =
        {
            new[] { "Longsword (2H)", "Idle_TwoHanded" }, new[] { "Battle axe (2H)", "Idle_TwoHanded" },
            new[] { "Recurve bow", "Idle_Bow" }, new[] { "Staff", "Idle_Staff" },
        };

        public void FillDefaults()
        {
            plans.Clear(); attacks.Clear(); idles.Clear();
            foreach (var row in DefaultPlans)
            {
                var p = new Plan { character = (string)row[0] };
                for (int i = 1; i < row.Length; i++) p.loadouts.Add((string)row[i]);
                plans.Add(p);
            }
            foreach (var a in DefaultAttacks) attacks.Add(new ClipFor { loadout = a[0], clip = a[1] });
            foreach (var a in DefaultIdles) idles.Add(new ClipFor { loadout = a[0], clip = a[1] });
        }

        void Start()
        {
            if (autoStart) Begin();
        }

        public void Begin()
        {
            if (plans.Count == 0) FillDefaults();
            StartCoroutine(Record());
        }

        string Lookup(List<ClipFor> table, string loadout, string fallback)
        {
            foreach (var c in table) if (c.loadout == loadout) return c.clip;
            return fallback;
        }

        static AnimationClip FindClip(Animator an, string name)
        {
            if (an == null || an.runtimeAnimatorController == null || string.IsNullOrEmpty(name)) return null;
            foreach (var c in an.runtimeAnimatorController.animationClips) if (c != null && c.name == name) return c;
            return null;
        }

        // ------------------------------------------------------------------ the stages

        static Step S(string character, string loadout, string idle, float seconds, string title, string text)
        {
            return new Step { character = character, loadout = loadout, idle = idle, seconds = seconds, title = title, text = text };
        }

        /// <summary>"Modular": the six presets in turn on Idle_03, then the Knight dressed in the Warrior's chest, the
        /// Archer's helm, the Warrior's greaves and the Assassin's gloves, then every weapon on that mixed Knight with the
        /// idle the user chose per weapon, then the bow / staff / wand on the presets that own them.</summary>
        public List<Step> BuildModular()
        {
            var steps = new List<Step>();
            steps.Add(new Step { titleCard = true, title = "MODULAR", text = "six class presets  |  one shared rig  |  every armour piece and weapon on any skeleton", seconds = titleCardSeconds });
            string six = "Six class presets on one shared humanoid rig";
            steps.Add(S("Warrior", "", "Idle_03", 3f, "Skeleton Warrior", six));
            steps.Add(S("Assassin", "", "Idle_03", 3f, "Skeleton Assassin", six));
            steps.Add(S("Archer", "", "Idle_03", 3f, "Skeleton Archer", six));
            steps.Add(S("Mage", "", "Idle_03", 3f, "Skeleton Mage", six));
            steps.Add(S("Necromancer", "", "Idle_03", 3f, "Skeleton Necromancer", six));
            steps.Add(S("Knight", "", "Idle_03", 3f, "Skeleton Knight", six));
            // the Knight as the base: other classes' pieces, one at a time
            var chest = S("Knight", "", "Idle_03", 3f, "Warrior chest plate on the Knight", "Armour modules are separate assets: any piece binds to any skeleton by bone name"); chest.wear.Add("Warrior:Chest"); steps.Add(chest);
            var helm = S("Knight", "", "Idle_03", 3f, "+ Archer helm", "Mix and match across the six sets"); helm.wear.Add("Archer:Helm"); steps.Add(helm);
            var greaves = S("Knight", "", "Idle_03", 3f, "+ Warrior greaves", "Each piece is its own renderer on the character's bones: on / off at zero cost"); greaves.wear.Add("Warrior:Greave_L"); greaves.wear.Add("Warrior:Greave_R"); steps.Add(greaves);
            var gloves = S("Knight", "", "Idle_03", 3f, "+ Assassin gloves", "The mixed skeleton animates like any other"); gloves.wear.Add("Assassin:Glove_L"); gloves.wear.Add("Assassin:Glove_R"); steps.Add(gloves);
            // weapons on the mixed Knight, the idle per weapon
            string slots = "Weapons attach to hand slots; the fingers close on the grip";
            steps.Add(S("Knight", "Sword + shield", "Idle_03", 3f, "Sword + heater shield", slots));
            steps.Add(S("Knight", "Axe + round shield", "Idle_03", 3f, "Axe + round shield", slots));
            steps.Add(S("Knight", "Sword", "Idle_02", 3f, "Sword", "Three base idles to pick from per class"));
            steps.Add(S("Knight", "Dagger", "Idle_02", 3f, "Dagger", slots));
            steps.Add(S("Knight", "Two daggers", "Idle_02", 3f, "Two daggers", "One-handed items in either hand"));
            steps.Add(S("Knight", "Mace", "Idle_01", 3f, "Mace", slots));
            steps.Add(S("Knight", "Longsword (2H)", "Idle_TwoHanded", 3f, "Longsword", "Two-handed idle: the second hand rides the handle"));
            steps.Add(S("Knight", "Battle axe (2H)", "Idle_TwoHanded", 3f, "Battle axe", "The same two-handed grip on every long weapon"));
            // the class weapons on their presets
            steps.Add(S("Archer", "Recurve bow", "Idle_Bow", 3.5f, "Recurve bow", "Bow idle; the bow is a skinned model whose string follows the draw hand"));
            steps.Add(S("Necromancer", "Staff", "Idle_Staff", 3.5f, "Staff", "Staff idle"));
            steps.Add(S("Mage", "Wand", "Idle_03", 3.5f, "Wand", "Short staff, one-handed"));
            return steps;
        }

        /// <summary>"Attacks": each preset's weapons in turn, the weapon's idle, one attack.</summary>
        /// <summary>"Movement": every character with its locomotion set, each clip looping in place for `movementSeconds`.
        /// The user's split (2026-09-29): the `_01` shambling set for the Warrior and the Archer, the `_02` upright set for the
        /// other four. The caption carries the clip name and the shipped speed-table figure.</summary>
        public List<Step> BuildMovement()
        {
            var steps = new List<Step>();
            steps.Add(new Step { titleCard = true, title = "MOVEMENT", text = "two locomotion sets  |  root motion on every clip  |  measured speed table shipped", seconds = titleCardSeconds });
            string[][] set01 = { new[] { "Walk_Fwd_01", "0.52" }, new[] { "Run_Fwd", "1.14" }, new[] { "Walk_Back_01", "0.34" }, new[] { "Strafe_Left_01", "0.20" }, new[] { "Strafe_Right_01", "0.20" } };
            string[][] set02 = { new[] { "Walk_Fwd_02", "1.28" }, new[] { "Run_Fwd_02", "1.87" }, new[] { "Walk_Back_02", "0.77" }, new[] { "Strafe_Left_02", "0.93" }, new[] { "Strafe_Right_02", "0.93" } };
            string[][] chars = { new[] { "Warrior", "Axe + round shield", "01" }, new[] { "Archer", "Recurve bow", "01" }, new[] { "Assassin", "Two daggers", "02" },
                                 new[] { "Mage", "Staff", "02" }, new[] { "Necromancer", "Staff", "02" }, new[] { "Knight", "Sword + shield", "02" } };
            foreach (var ch in chars)
            {
                var set = ch[2] == "01" ? set01 : set02;
                string line = ch[2] == "01" ? "Shambling set (_01) for the lower ranks" : "Upright set (_02) for the higher ranks";
                foreach (var clip in set)
                    steps.Add(S(ch[0], ch[1], clip[0], movementSeconds, "Skeleton " + ch[0] + "  |  " + clip[0], line + "  |  root motion " + clip[1] + " m/s, played in place here"));
            }
            return steps;
        }

        public List<Step> BuildAttacks()
        {
            var steps = new List<Step>();
            steps.Add(new Step { titleCard = true, title = "COMBAT", text = "every weapon with its idle and attack  |  in place, root motion optional", seconds = titleCardSeconds });
            foreach (var plan in plans)
                foreach (var lo in plan.loadouts)
                {
                    var st = S(plan.character, lo, Lookup(idles, lo, "Idle_01"), holdBefore, "Skeleton " + plan.character + "  |  " + lo, Lookup(attacks, lo, ""));
                    st.attack = Lookup(attacks, lo, "");
                    steps.Add(st);
                }
            return steps;
        }

        // ------------------------------------------------------------------ the run

        IEnumerator Record()
        {
            Done = false; FramesWritten = 0; SetStatus("starting");
            _showcase = FindFirstObjectByType<SkeletonShowcase>();
            if (_showcase == null) { SetStatus("no SkeletonShowcase in the scene"); Done = true; yield break; }

            _dir = string.IsNullOrEmpty(outputDir) ? Path.Combine(Path.GetDirectoryName(Application.dataPath), "..", "Showreel", stage, "frames") : outputDir;
            _dir = Path.GetFullPath(_dir);
            if (Directory.Exists(_dir)) Directory.Delete(_dir, true);
            Directory.CreateDirectory(_dir);

            foreach (var cv in FindObjectsByType<Canvas>(FindObjectsSortMode.None)) if (cv.enabled) { cv.enabled = false; _hidden.Add(cv); }
            if (_showcase.rootMotionToggle != null) _showcase.rootMotionToggle.isOn = false;
            if (_showcase.turntableToggle != null) _showcase.turntableToggle.isOn = false;

            SetupCamera();
            if (maxQuality) ApplyMaxQuality();
            BuildCanvas();
            Time.captureDeltaTime = 1f / fps;
            yield return null;

            var steps = stage == "modular" ? BuildModular() : stage == "movement" ? BuildMovement() : BuildAttacks();
            int doneSteps = 0;
            foreach (var step in steps)
            {
                if (step.titleCard)
                {
                    SetStatus("title card " + step.title);
                    ShowCard(step.title, step.text); SetFade(1f);
                    yield return Capture(Mathf.RoundToInt(step.seconds * fps));
                    continue;
                }
                bool newCharacter = step.character != _currentCharacter;
                if (newCharacter)
                {
                    int ci = -1;
                    for (int i = 0; i < _showcase.characters.Count; i++)
                        if (_showcase.characters[i].prefab != null && _showcase.characters[i].prefab.name.Contains(step.character)) { ci = i; break; }
                    if (ci < 0) { Debug.LogWarning("Showreel: no character matching '" + step.character + "'"); continue; }
                    _showcase.SelectCharacter(ci);
                    yield return null;
                    _animator = FindFirstObjectByType<Animator>(); _weapon = FindFirstObjectByType<SkeletonWeapon>(); _modules = FindFirstObjectByType<SkeletonModules>();
                    _currentCharacter = step.character;
                }
                SetStatus(step.character + " / " + (string.IsNullOrEmpty(step.loadout) ? "-" : step.loadout) + " / " + step.idle);
                // armour
                foreach (var r in step.remove) TakeOff(r);
                foreach (var w in step.wear) PutOn(w);
                // the idle, then the weapon (the grip closes on the crossfade)
                var idle = FindClip(_animator, step.idle) ?? FindClip(_animator, "Idle_01");
                if (idle != null) _showcase.Play(idle);
                if (_weapon != null)
                {
                    if (string.IsNullOrEmpty(step.loadout)) _weapon.Clear();
                    else
                    {
                        int li = -1;
                        for (int i = 0; i < _weapon.Count; i++) if (_weapon.NameAt(i) == step.loadout) { li = i; break; }
                        if (li >= 0) _weapon.Equip(li); else Debug.LogWarning("Showreel: no loadout '" + step.loadout + "'");
                    }
                }
                HideCard(); ShowCaption(step.title, step.text);
                if (newCharacter) { yield return null; yield return null; SetFade(0f); }   // two uncaptured frames to settle the new character, then the hard cut
                yield return Capture(Mathf.RoundToInt(step.seconds * fps));
                if (!string.IsNullOrEmpty(step.attack))
                {
                    var attack = FindClip(_animator, step.attack);
                    if (attack != null)
                    {
                        _showcase.Play(attack);
                        if (Application.isBatchMode) Debug.Log("Showreel: attack " + attack.name + " playing");
                        yield return Capture(Mathf.RoundToInt((attack.length + _showcase.crossFade) * fps) + 2);
                        yield return Capture(Mathf.RoundToInt(holdAfter * fps));
                    }
                    else Debug.LogWarning("Showreel: no attack clip '" + step.attack + "'");
                }
                doneSteps++;
                if (maxLoadouts > 0 && doneSteps >= maxLoadouts) break;
            }
            Time.captureDeltaTime = 0f;
            foreach (var cv in _hidden) if (cv != null) cv.enabled = true;
            RestoreQuality();
            if (_canvasGo != null) Destroy(_canvasGo);
            _cam.targetTexture = null; Destroy(_cam.gameObject); if (_out != _rt) Destroy(_out); Destroy(_rt); Destroy(_tex);
            SetStatus("done: " + FramesWritten + " frames in " + _dir);
            File.WriteAllText(Path.Combine(_dir, "done.txt"), Status);      // a marker a shell can poll without the bridge
            Debug.Log("Showreel " + Status);
            Done = true;
        }

        // ---- armour swaps through the showcase's catalogue + the character's SkeletonModules
        GameObject ModulePrefab(string character, string module)
        {
            foreach (var set in _showcase.armorCatalogue)
            {
                if (set.character == null || !set.character.Contains(character)) continue;
                foreach (var m in set.modules) if (m != null && m.name.EndsWith("_" + module)) return m;
            }
            return null;
        }

        void PutOn(string spec)
        {
            if (_modules == null) return;
            var parts = spec.Split(':'); if (parts.Length != 2) return;
            var own = ModulePrefab(_currentCharacter, parts[1]);
            if (own != null) _modules.Remove(own);                          // the character's own piece of that module off
            var borrowed = ModulePrefab(parts[0], parts[1]);
            if (borrowed != null) _modules.Wear(borrowed); else Debug.LogWarning("Showreel: no module " + spec);
        }

        void TakeOff(string module)
        {
            if (_modules == null) return;
            var own = ModulePrefab(_currentCharacter, module);
            if (own != null) _modules.Remove(own);
        }

        // ---- the camera and the capture
        void SetupCamera()
        {
            var main = Camera.main;
            var camGo = new GameObject("ShowreelCamera");
            _cam = camGo.AddComponent<Camera>();
            if (main != null) _cam.CopyFrom(main);
            _cam.fieldOfView = fieldOfView;
            _cam.enabled = false;                                    // rendered by hand into the texture
            var pivot = _showcase.spawnPoint != null ? _showcase.spawnPoint.position : Vector3.zero;
            var fwd = _showcase.spawnPoint != null ? _showcase.spawnPoint.forward : Vector3.forward;
            var look = pivot + Vector3.up * lookHeight;
            var dirFromFront = Quaternion.AngleAxis(azimuth, Vector3.up) * fwd;
            var offset = Quaternion.AngleAxis(-elevation, Vector3.Cross(Vector3.up, dirFromFront)) * dirFromFront;
            camGo.transform.position = look + offset.normalized * distance;
            camGo.transform.LookAt(look);
            int ss = Mathf.Max(1, supersample);
            _rt = new RenderTexture(width * ss, height * ss, 24, RenderTextureFormat.ARGB32); _rt.antiAliasing = maxQuality ? (ss > 1 ? 4 : 8) : 4;
            _out = ss > 1 ? new RenderTexture(width, height, 0, RenderTextureFormat.ARGB32) : _rt;   // a bilinear blit from 2x averages exactly 2x2 texels (a box filter)
            if (ss > 1) _out.filterMode = FilterMode.Bilinear;
            _tex = new Texture2D(width, height, TextureFormat.RGB24, false);
            _cam.targetTexture = _rt;
        }

        IEnumerator Capture(int frames)
        {
            for (int i = 0; i < frames; i++)
            {
                if (Application.isBatchMode) yield return null;   // batch mode never reaches an end-of-frame; the camera is rendered by hand anyway
                else yield return new WaitForEndOfFrame();
                _cam.Render();
                if (_out != _rt) Graphics.Blit(_rt, _out);
                var prev = RenderTexture.active; RenderTexture.active = _out;
                _tex.ReadPixels(new Rect(0, 0, width, height), 0, 0); _tex.Apply();
                RenderTexture.active = prev;
                File.WriteAllBytes(Path.Combine(_dir, string.Format("frame_{0:D5}.png", FramesWritten)), _tex.EncodeToPNG());
                FramesWritten++;
            }
        }

        // ---- the caption canvas: world space, parented to the recording camera, sized to fill its frustum at 1 m
        void BuildCanvas()
        {
            _canvasGo = new GameObject("ShowreelCanvas");
            var canvas = _canvasGo.AddComponent<Canvas>(); canvas.renderMode = RenderMode.WorldSpace; canvas.worldCamera = _cam;
            var rt = _canvasGo.GetComponent<RectTransform>(); rt.sizeDelta = new Vector2(width, height);
            float dist = 1f; float h = 2f * dist * Mathf.Tan(fieldOfView * 0.5f * Mathf.Deg2Rad);
            _canvasGo.transform.SetParent(_cam.transform, false);
            _canvasGo.transform.localPosition = new Vector3(0f, 0f, dist); _canvasGo.transform.localRotation = Quaternion.identity;
            _canvasGo.transform.localScale = Vector3.one * (h / height);
            // the caption panel, top-left over the sky (the figure stands centre-bottom: a bottom panel covered its feet)
            _panel = NewImage("Panel", rt, new Color(0.06f, 0.07f, 0.09f, 0.72f));
            _panel.rectTransform.anchorMin = _panel.rectTransform.anchorMax = new Vector2(0f, 1f); _panel.rectTransform.pivot = new Vector2(0f, 1f);
            _panel.rectTransform.anchoredPosition = new Vector2(60f, -60f); _panel.rectTransform.sizeDelta = new Vector2(600f, 170f);   // 900 wide until 2026-09-29: it overlapped the head
            _title = NewText("Title", _panel.rectTransform, new Vector2(30f, 92f), new Vector2(540f, 50f), 40, FontStyle.Bold, new Color(0.96f, 0.95f, 0.90f, 1f));
            _text = NewText("Text", _panel.rectTransform, new Vector2(30f, 14f), new Vector2(540f, 70f), 24, FontStyle.Normal, new Color(0.80f, 0.82f, 0.86f, 1f));
            _title.horizontalOverflow = HorizontalWrapMode.Overflow;   // one line always; ShowCaption sizes the font to the panel (uGUI best-fit did not shrink it)
            // full-frame black for the title card, above the panel
            _fade = NewImage("Fade", rt, new Color(0f, 0f, 0f, 0f));
            _fade.rectTransform.anchorMin = Vector2.zero; _fade.rectTransform.anchorMax = Vector2.one; _fade.rectTransform.offsetMin = Vector2.zero; _fade.rectTransform.offsetMax = Vector2.zero;
            // the stage title card, centred, above the black
            _card = NewText("Card", rt, Vector2.zero, new Vector2(1700f, 320f), 96, FontStyle.Bold, new Color(0.96f, 0.95f, 0.90f, 1f));
            _card.rectTransform.anchorMin = _card.rectTransform.anchorMax = new Vector2(0.5f, 0.5f); _card.rectTransform.pivot = new Vector2(0.5f, 0.5f);
            _card.rectTransform.anchoredPosition = Vector2.zero; _card.alignment = TextAnchor.MiddleCenter; _card.supportRichText = true;
            HideCard(); if (!captions) _panel.gameObject.SetActive(false);
        }

        Image NewImage(string name, RectTransform parent, Color color)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false);
            var img = go.AddComponent<Image>(); img.color = color; img.raycastTarget = false;
            return img;
        }

        Text NewText(string name, RectTransform parent, Vector2 pos, Vector2 size, int fontSize, FontStyle style, Color color)
        {
            var go = new GameObject(name); go.transform.SetParent(parent, false);
            var t = go.AddComponent<Text>(); t.font = DemoUI.Font; t.fontSize = fontSize; t.fontStyle = style; t.color = color; t.raycastTarget = false;
            t.alignment = TextAnchor.MiddleLeft; t.horizontalOverflow = HorizontalWrapMode.Wrap; t.verticalOverflow = VerticalWrapMode.Overflow;
            var r = t.rectTransform; r.anchorMin = r.anchorMax = Vector2.zero; r.pivot = Vector2.zero; r.anchoredPosition = pos; r.sizeDelta = size;
            return t;
        }

        void SetFade(float a) { if (_fade != null) _fade.color = new Color(0f, 0f, 0f, Mathf.Clamp01(a)); }
        void ShowCaption(string title, string text)
        {
            if (_panel == null || !captions) return;
            _panel.gameObject.SetActive(!string.IsNullOrEmpty(title) || !string.IsNullOrEmpty(text));
            _title.text = title ?? ""; _text.text = text ?? "";
            _title.fontSize = titleFontSize;
            float w = _title.preferredWidth, maxW = _title.rectTransform.rect.width;   // the unwrapped width in canvas units
            if (w > maxW) _title.fontSize = Mathf.Max(20, Mathf.FloorToInt(titleFontSize * maxW / w));
        }
        const int titleFontSize = 40;
        void ShowCard(string title, string text)
        {
            if (_card == null) return;
            _card.gameObject.SetActive(true); _card.text = title + (string.IsNullOrEmpty(text) ? "" : "\n<size=30>" + text + "</size>");
            if (_panel != null) _panel.gameObject.SetActive(false);
        }
        void HideCard() { if (_card != null) _card.gameObject.SetActive(false); }

        // ---- quality: pushed as far as the runtime API allows, on the live URP asset, and put back afterwards
        int _qLevel; AnisotropicFiltering _qAniso; int _qMip; float _qLod;
        UniversalRenderPipelineAsset _urp; int _uMsaa; float _uShadowDist; int _uCascades; int _uShadowRes; bool _uHdr; float _uScale;

        void ApplyMaxQuality()
        {
            _qLevel = QualitySettings.GetQualityLevel(); _qAniso = QualitySettings.anisotropicFiltering; _qMip = QualitySettings.globalTextureMipmapLimit; _qLod = QualitySettings.lodBias;
            QualitySettings.SetQualityLevel(QualitySettings.names.Length - 1, true);
            QualitySettings.anisotropicFiltering = AnisotropicFiltering.ForceEnable;
            QualitySettings.globalTextureMipmapLimit = 0;
            QualitySettings.lodBias = 4f;
            _urp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
            if (_urp != null)
            {
                _uMsaa = _urp.msaaSampleCount; _uShadowDist = _urp.shadowDistance; _uCascades = _urp.shadowCascadeCount; _uShadowRes = _urp.mainLightShadowmapResolution; _uHdr = _urp.supportsHDR; _uScale = _urp.renderScale;
                _urp.msaaSampleCount = 8;
                _urp.shadowDistance = shadowDistance;               // a short range: the whole shadow map on the character
                _urp.shadowCascadeCount = 1;
                _urp.mainLightShadowmapResolution = 4096;
                _urp.supportsHDR = true;
                _urp.renderScale = 1f;
            }
            foreach (var l in FindObjectsByType<Light>(FindObjectsSortMode.None))
            {
                var ld = l.GetUniversalAdditionalLightData();
                if (ld != null) ld.softShadowQuality = SoftShadowQuality.High;
            }
            if (_cam != null)
            {
                _cam.allowHDR = true; _cam.allowMSAA = true;
                var data = _cam.GetUniversalAdditionalCameraData();
                if (data != null) { data.renderPostProcessing = true; data.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing; data.antialiasingQuality = AntialiasingQuality.High; data.renderShadows = true; }
            }
            Debug.Log(string.Format("Showreel quality: level {0}, MSAA {1}, shadow map {2} x1 cascade over {3} m, soft shadows high, SMAA high, HDR, supersample {4}x", QualitySettings.names[QualitySettings.GetQualityLevel()], _urp != null ? _urp.msaaSampleCount : 0, _urp != null ? _urp.mainLightShadowmapResolution : 0, shadowDistance, Mathf.Max(1, supersample)));
        }

        void RestoreQuality()
        {
            if (!maxQuality) return;
            QualitySettings.SetQualityLevel(_qLevel, true);
            QualitySettings.anisotropicFiltering = _qAniso; QualitySettings.globalTextureMipmapLimit = _qMip; QualitySettings.lodBias = _qLod;
            if (_urp != null)
            {
                _urp.msaaSampleCount = _uMsaa; _urp.shadowDistance = _uShadowDist; _urp.shadowCascadeCount = _uCascades; _urp.mainLightShadowmapResolution = _uShadowRes; _urp.supportsHDR = _uHdr; _urp.renderScale = _uScale;
            }
        }
    }
}
