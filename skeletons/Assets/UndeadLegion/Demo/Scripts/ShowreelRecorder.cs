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
    /// character's locomotion set looping in place) and "attacks" "weapons" (weapons & utils: each class's utility one-shots, its weapons' attacks and a death; "attacks" is the old id). Configure a ShowreelRecorder in the scene or use the menu / headless
    /// launcher.
    /// </summary>
    public class ShowreelRecorder : MonoBehaviour
    {
        [System.Serializable]
        public class Step
        {
            public string character;                    // prefab name substring; a change of character is a hard cut
            public string loadout;                      // weapon loadout display name; "" = hands empty
            public string idle = "Idle_01";             // the looping clip on Base
            public string attack;                       // optional one-shot played after `seconds` of the idle
            public List<string> attacks = new List<string>();  // several one-shots in a row (holdAfter between them); wins over `attack`
            public float attackSpeed = 1f;
            public float afterSeconds = -1f;            // the settle after each attack; < 0 = holdAfter (a death holds longer)
            public bool followHips;                     // the camera follows the hips, not the root (a death's fall lives in the pose: the root stays)              // Animator.speed while the attacks play (user, Assassin: "60 % faster")
            public string holdOn;                       // a looping masked-layer clip to hold before the attacks (Block_L_Idle: the shield stays up)
            public string holdOff;                      // ... and one to release
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
        [Tooltip("modular | movement | weapons (\"attacks\" is accepted)")]
        public string stage = "weapons";
        public float titleCardSeconds = 1.6f;
        [Tooltip("Movement stage: seconds per locomotion clip.")]
        public float movementSeconds = 3f;
        [Tooltip("Weapons & utils stage: how long a death's corpse is held before the cut.")]
        public float deathHoldSeconds = 1.6f;
        [Tooltip("Death steps: how far the following camera sinks so the corpse sits mid-frame, not on the bottom edge (m).")]
        public float deathCameraDrop = 0.5f;
        [Header("Root motion (attacks stage)")]
        [Tooltip("Attacks stage: root motion ON, the camera follows the character with damping and the character is recentred after every attack - the camera moved by the same offset in the same frame, so the recenter is invisible (user, 2026-09-29).")]
        public bool attacksRootMotion = true;
        [Tooltip("Follow damping, 1/s: the camera's position closes on (character + its original offset) at this rate; the lag is what shows the travel.")]
        public float followDamping = 4f;
        public bool captions = true;

        [Header("Timing of the attacks stage (seconds)")]
        public float holdBefore = 0.8f;
        public float holdAfter = 0.9f;
        public float characterGap = 0.4f;

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
        string _currentCharacter, _currentIdle;
        bool _rootMotion, _followHips; Vector3 _camHomePos, _camOffset; Quaternion _camHomeRot;
        readonly List<Canvas> _hidden = new List<Canvas>();
        string _dir;
        // the caption canvas
        GameObject _canvasGo; Image _fade; Image _panel; Text _title; Text _text; Text _card;

        public void Begin()
        {
            StartCoroutine(Record());
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
        /// The user's split (2026-09-29): the `_01` shambling set on the Warrior, the `_02` upright set on the Mage (one character
        /// per set; the first cut showed all six). The caption carries the clip name and the shipped speed-table figure.</summary>
        public List<Step> BuildMovement()
        {
            var steps = new List<Step>();
            steps.Add(new Step { titleCard = true, title = "MOVEMENT", text = "two locomotion sets  |  root motion on every clip  |  measured speed table shipped", seconds = titleCardSeconds });
            string[][] set01 = { new[] { "Walk_Fwd_01", "0.52" }, new[] { "Run_Fwd_01", "1.14" }, new[] { "Walk_Back_01", "0.34" }, new[] { "Strafe_Left_01", "0.20" }, new[] { "Strafe_Right_01", "0.20" } };
            string[][] set02 = { new[] { "Walk_Fwd_02", "1.28" }, new[] { "Run_Fwd_02", "1.87" }, new[] { "Walk_Back_02", "0.77" }, new[] { "Strafe_Left_02", "0.93" }, new[] { "Strafe_Right_02", "0.93" } };
            // 2026-09-29, second cut: one character per set (the six-character version ran 92 s) - the Warrior for the low-rank _01 set, the Mage for the high-rank _02 set
            string[][] chars = { new[] { "Warrior", "Axe + round shield", "01" }, new[] { "Mage", "Staff", "02" } };
            foreach (var ch in chars)
            {
                var set = ch[2] == "01" ? set01 : set02;
                string line = ch[2] == "01" ? "Shambling set (_01) for the lower ranks" : "Upright set (_02) for the higher ranks";
                foreach (var clip in set)
                    steps.Add(S(ch[0], ch[1], clip[0], movementSeconds, "Skeleton " + ch[0] + "  |  " + clip[0], line + "  |  root motion " + clip[1] + " m/s, played in place here"));
            }
            return steps;
        }

        static Step A(string character, string loadout, string idle, string title, string text, params string[] attacks)
        {
            var st = new Step { character = character, loadout = loadout, idle = idle, seconds = 0.8f, title = title, text = text };
            st.attacks.AddRange(attacks);
            return st;
        }

        /// <summary>"Combat", the user's script (2026-09-29): Warrior on Idle_TwoHanded - longsword then battle axe, both two-handed
        /// attacks each; Knight on Idle_03 - axe + round shield (right stab), sword + heater shield (right slice), then the left block
        /// HELD with both right attacks, then the mace with the block released and both right attacks; Assassin on Idle_02 - one dagger
        /// (both right attacks), two daggers (both left attacks), all at 1.6x; Archer on Idle_Bow - the shot; Mage on Idle_03 - the two
        /// wand casts; Necromancer on Idle_Staff - the two wand casts and the staff cast.</summary>
        public List<Step> BuildAttacks()
        {
            // "Weapons & utils" (2026-09-29): the attacks script, plus each class's utility one-shots before its attacks and a death after
            var steps = new List<Step>();
            steps.Add(new Step { titleCard = true, title = "WEAPONS & UTILS", text = "every weapon with its idle and attacks  |  taunts, specials, deaths", seconds = titleCardSeconds });
            steps.Add(A("Warrior", "Longsword (2H)", "Idle_TwoHanded", "Skeleton Warrior  |  Longsword", "Taunt", "Taunt_01"));
            steps.Add(A("Warrior", "Longsword (2H)", "Idle_TwoHanded", "Skeleton Warrior  |  Longsword", "Two-handed idle; the second hand rides the handle", "Attack_2H_01", "Attack_2H_02"));
            steps.Add(A("Warrior", "Battle axe (2H)", "Idle_TwoHanded", "Skeleton Warrior  |  Battle axe", "The same two-handed grip and attacks on every long weapon", "Attack_2H_01", "Attack_2H_02"));
            steps.Add(Death(A("Warrior", "Battle axe (2H)", "Idle_TwoHanded", "Skeleton Warrior  |  Battle axe", "Death", "Death_01")));
            // Knight: taunt and rally, then the combat idle with the left block HELD; axe + round shield slice; sword + heater shield
            // with both right attacks under the block; the sword alone with the block released and both attacks; then the death
            steps.Add(A("Knight", "Axe + round shield", "Idle_1H_Combat", "Skeleton Knight  |  Axe + round shield", "Taunt and rally", "Taunt_02", "Rally"));
            var axe = A("Knight", "Axe + round shield", "Idle_1H_Combat", "Skeleton Knight  |  Axe + round shield", "Left-arm block HELD on its own layer; the right arm attacks under it", "Attack_R_Slice");
            axe.holdOn = "Block_L_Idle"; steps.Add(axe);
            steps.Add(A("Knight", "Sword + shield", "Idle_1H_Combat", "Skeleton Knight  |  Sword + heater shield", "Any one-handed weapon, any shield; the block still held", "Attack_R_Stab", "Attack_R_Slice"));
            var sw = A("Knight", "Sword", "Idle_1H_Combat", "Skeleton Knight  |  Sword", "Block released; the same attacks with the free hand", "Attack_R_Stab", "Attack_R_Slice");
            sw.holdOff = "Block_L_Idle"; steps.Add(sw);
            steps.Add(Death(A("Knight", "Sword", "Idle_1H_Combat", "Skeleton Knight  |  Sword", "Death", "Death_02")));
            // Assassin: the cutthroat at normal speed, the attacks at 1.6x, the death at normal speed
            steps.Add(A("Assassin", "Dagger", "Idle_1H_Combat", "Skeleton Assassin  |  Dagger", "Cutthroat", "Cutthroat"));
            var d1 = A("Assassin", "Dagger", "Idle_1H_Combat", "Skeleton Assassin  |  Dagger", "Right-arm attacks at 1.6x speed", "Attack_R_Stab", "Attack_R_Slice"); d1.attackSpeed = 1.6f; steps.Add(d1);
            var d2 = A("Assassin", "Two daggers", "Idle_1H_Combat", "Skeleton Assassin  |  Two daggers", "Left-arm attacks at 1.6x speed", "Attack_L_Stab", "Attack_L_Slice"); d2.attackSpeed = 1.6f; steps.Add(d2);
            steps.Add(Death(A("Assassin", "Two daggers", "Idle_1H_Combat", "Skeleton Assassin  |  Two daggers", "Death", "Death_03")));
            steps.Add(A("Archer", "Recurve bow", "Idle_Bow", "Skeleton Archer  |  Recurve bow", "The string follows the draw hand; an arrow is fired on release", "Shoot_01"));
            steps.Add(A("Mage", "Wand", "Idle_03", "Skeleton Mage  |  Wand", "Two wand casts", "Cast_Wand_01", "Cast_Wand_02"));
            // Necromancer: summon, the casts, the area cast, the death
            steps.Add(A("Necromancer", "Staff", "Idle_Staff", "Skeleton Necromancer  |  Staff", "Summon", "Summon"));
            steps.Add(A("Necromancer", "Staff", "Idle_Staff", "Skeleton Necromancer  |  Staff", "The wand casts on the staff, then the two-handed staff cast", "Cast_Wand_01", "Cast_Wand_02", "Cast_Staff_01"));
            steps.Add(A("Necromancer", "Staff", "Idle_Staff", "Skeleton Necromancer  |  Staff", "Area cast", "AOE_Cast"));
            steps.Add(Death(A("Necromancer", "Staff", "Idle_Staff", "Skeleton Necromancer  |  Staff", "Death", "Death_04")));
            return steps;
        }

        /// <summary>A death step: the corpse held `deathHoldSeconds` before the cut (holdAfter is too short to read the landing).</summary>
        Step Death(Step st) { st.afterSeconds = deathHoldSeconds; st.followHips = true; st.seconds = 0.3f; return st; }

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
            bool weaponsStage = stage == "weapons" || stage == "attacks";
            _rootMotion = weaponsStage && attacksRootMotion;
            if (_showcase.rootMotionToggle != null) _showcase.rootMotionToggle.isOn = _rootMotion;
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
                    _cam.transform.position = _camHomePos; _cam.transform.rotation = _camHomeRot; _camOffset = _camHomePos - Spawn();
                }
                SetStatus(step.character + " / " + (string.IsNullOrEmpty(step.loadout) ? "-" : step.loadout) + " / " + step.idle);
                // armour
                foreach (var r in step.remove) TakeOff(r);
                foreach (var w in step.wear) PutOn(w);
                // the idle, then the weapon (the grip closes on the crossfade)
                var idle = FindClip(_animator, step.idle) ?? FindClip(_animator, "Idle_01");
                if (idle != null && (newCharacter || idle.name != _currentIdle)) { _showcase.Play(idle); _currentIdle = idle.name; }   // a loadout change keeps the running idle
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
                if (!string.IsNullOrEmpty(step.holdOff)) { var h = FindClip(_animator, step.holdOff); if (h != null && _showcase.IsHolding) _showcase.ToggleHeld(h, _showcase.LayerFor(h)); }
                if (!string.IsNullOrEmpty(step.holdOn)) { var h = FindClip(_animator, step.holdOn); if (h != null && !_showcase.IsHolding) _showcase.ToggleHeld(h, _showcase.LayerFor(h)); }
                _followHips = step.followHips;
                HideCard(); ShowCaption(step.title, step.text);
                if (newCharacter) { yield return null; yield return null; SetFade(0f); }   // two uncaptured frames to settle the new character, then the hard cut
                yield return Capture(Mathf.RoundToInt(step.seconds * fps));
                var attackNames = step.attacks.Count > 0 ? step.attacks : (string.IsNullOrEmpty(step.attack) ? new List<string>() : new List<string> { step.attack });
                foreach (var an_ in attackNames)
                {
                    var attack = FindClip(_animator, an_);
                    if (attack == null) { Debug.LogWarning("Showreel: no attack clip '" + an_ + "'"); continue; }
                    float sp = step.attackSpeed > 0f ? step.attackSpeed : 1f;
                    ShowCaption(step.title, step.text + "  |  " + attack.name + (sp != 1f ? string.Format("  ({0:0.0}x)", sp) : ""));
                    _animator.speed = sp;
                    _showcase.Play(attack);
                    if (Application.isBatchMode) Debug.Log("Showreel: attack " + attack.name + " playing at " + sp + "x");
                    yield return Capture(Mathf.RoundToInt((attack.length / sp + _showcase.crossFade) * fps) + 2);
                    _animator.speed = 1f;
                    yield return Capture(Mathf.RoundToInt((step.afterSeconds >= 0f ? step.afterSeconds : holdAfter) * fps));
                    if (_rootMotion) RecenterSeamless();
                }
                if (attackNames.Count > 0) ShowCaption(step.title, step.text);
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
            _camHomePos = camGo.transform.position; _camHomeRot = camGo.transform.rotation; _camOffset = _camHomePos - pivot;
            int ss = Mathf.Max(1, supersample);
            _rt = new RenderTexture(width * ss, height * ss, 24, RenderTextureFormat.ARGB32); _rt.antiAliasing = maxQuality ? (ss > 1 ? 4 : 8) : 4;
            _out = ss > 1 ? new RenderTexture(width, height, 0, RenderTextureFormat.ARGB32) : _rt;   // a bilinear blit from 2x averages exactly 2x2 texels (a box filter)
            if (ss > 1) _out.filterMode = FilterMode.Bilinear;
            _tex = new Texture2D(width, height, TextureFormat.RGB24, false);
            _cam.targetTexture = _rt;
        }

        Vector3 Spawn() { return _showcase.spawnPoint != null ? _showcase.spawnPoint.position : Vector3.zero; }

        /// <summary>Root motion: the camera's position closes on the character's root + its original offset (damped, so the
        /// travel of an attack shows as the character moving in frame and the camera catching up); its rotation never changes.</summary>
        void FollowCamera()
        {
            if (!_rootMotion || _animator == null) return;
            var anchor = _animator.transform.position;
            if (_followHips)
            {
                var hips = _animator.GetBoneTransform(HumanBodyBones.Hips);
                if (hips != null) { anchor.x = hips.position.x; anchor.z = hips.position.z; }
                anchor.y -= deathCameraDrop;                                                      // the camera sinks with the fall (damped), its rotation unchanged
            }
            var target = anchor + _camOffset;
            float k = 1f - Mathf.Exp(-followDamping / fps);
            _cam.transform.position = Vector3.Lerp(_cam.transform.position, target, k);
        }

        /// <summary>After an attack: the character back at the spawn point facing forward, and the camera (and its follow
        /// offset) moved by the same rigid transform in the same frame - the rendered picture does not change, so no lerp
        /// is visible. The yaw is included because the recorded attacks leave the body a few degrees turned.</summary>
        void RecenterSeamless()
        {
            if (_animator == null) return;
            var root = _animator.transform; var spawn = Spawn();
            var oldPos = root.position; float yaw = root.eulerAngles.y;
            var fix = Quaternion.AngleAxis(-yaw, Vector3.up);
            root.position = spawn; root.rotation = Quaternion.identity;
            _cam.transform.position = spawn + fix * (_cam.transform.position - oldPos);
            _cam.transform.rotation = fix * _cam.transform.rotation;
            _camOffset = fix * _camOffset;
        }

        IEnumerator Capture(int frames)
        {
            for (int i = 0; i < frames; i++)
            {
                if (Application.isBatchMode) yield return null;   // batch mode never reaches an end-of-frame; the camera is rendered by hand anyway
                else yield return new WaitForEndOfFrame();
                FollowCamera();
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
