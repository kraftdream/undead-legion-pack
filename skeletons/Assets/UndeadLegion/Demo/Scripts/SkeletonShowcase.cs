using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// Demo-only animation browser: pick a character on the left, toggle its armour
    /// modules under it, play any clip on the right. The clip list is read from the
    /// character's AnimatorController at runtime, so a new clip in the controller makes a
    /// button appear with no code change. Twitch_* clips live on the additive layer and
    /// their buttons fire that layer over whatever the base layer is playing.
    /// </summary>
    public class SkeletonShowcase : MonoBehaviour
    {
        [System.Serializable]
        public class Entry
        {
            public string displayName;
            public GameObject prefab;
        }

        [Header("Content")]
        public List<Entry> characters = new List<Entry>();
        public Transform spawnPoint;

        [Header("UI wiring")]
        public RectTransform characterListContent;
        public RectTransform clipListContent;
        public RectTransform moduleListContent;
        public Text moduleHeaderLabel;
        public RectTransform weaponListContent;
        public Text weaponHeaderLabel;
        public Text characterNameLabel;
        public Text clipInfoLabel;
        public Toggle rootMotionToggle;
        public Toggle turntableToggle;
        public Button recenterButton;
        public Button allModulesButton;
        public Button noModulesButton;
        public DemoTurntable turntable;

        [Header("Playback")]
        [Tooltip("Blend time between clips, in seconds.")]
        [Range(0f, 0.5f)] public float crossFade = 0.15f;
        [Tooltip("Clip returned to when a one-shot finishes and its section declares no idle.")]
        public string idleClipName = "Idle";
        [Tooltip("Seconds a finished death clip holds its last pose before the idle returns.")]
        public float deathHold = 2f;
        [Tooltip("With root motion on, bring the character back to the spawn point once it is this far away (metres). 0 = never: the position is only reset by the Recenter button or by turning root motion off.")]
        public float rootMotionLeash = 0f;
        [Tooltip("Prefix of the clips that live on the additive twitch layer.")]
        public string twitchPrefix = "Twitch_";

        static readonly Color NormalColor = new Color(0.22f, 0.23f, 0.26f, 1f);
        static readonly Color SelectedColor = new Color(0.55f, 0.72f, 0.30f, 1f);

        GameObject _instance;
        Animator _animator;
        SkeletonModules _modules;
        SkeletonTwitch _twitch;
        SkeletonWeapon _weapon;
        readonly List<Button> _characterButtons = new List<Button>();
        readonly List<Button> _clipButtons = new List<Button>();
        readonly List<Button> _moduleButtons = new List<Button>();
        readonly List<Button> _weaponButtons = new List<Button>();
        readonly List<AnimationClip> _clips = new List<AnimationClip>();      // base-layer clips, display order
        readonly List<AnimationClip> _twitches = new List<AnimationClip>();   // additive-layer clips
        readonly List<Button> _twitchButtons = new List<Button>();
        // a twitch toggled on loops on its own additive layer (TwitchLoop_NN) over whatever plays;
        // all on when the demo starts, remembered across character switches
        readonly List<bool> _twitchLoopOn = new List<bool>();
        AnimationClip _current;
        AnimationClip _pendingFollow;
        // layered playback: clips with a state on the "UpperBody" layer (attacks that can be
        // performed on the move) play there while a locomotion loop keeps the legs; a clip
        // without one is a full stop: it takes the base layer and the loop resumes after it
        // masked layers, by name: UpperBody (both arms + torso), LeftArm, RightArm (arm-only, 2026-09-22:
        // the per-arm attack set). A clip plays on the first of them that has a state for it. A LOOPING
        // clip on a masked layer is a HELD action (Block_L_Idle): its button toggles it, it stays until released
        static readonly string[] MaskedLayerNames = { "UpperBody", "LeftArm", "RightArm" };
        readonly List<int> _maskedLayers = new List<int>();
        readonly Dictionary<int, AnimationClip> _layerCurrent = new Dictionary<int, AnimationClip>();   // one-shots running on masked layers
        readonly Dictionary<int, AnimationClip> _held = new Dictionary<int, AnimationClip>();           // loops held on masked layers
        int _upperPlayFrame = -10;
        AnimationClip _lastLoco;
        float _pendingAt;
        int _playFrame = -10;

        void Start()
        {
            BuildCharacterList();
            if (characters.Count > 0) SelectCharacter(0);

            if (rootMotionToggle != null)
            {
                rootMotionToggle.onValueChanged.AddListener(OnRootMotionChanged);
                OnRootMotionChanged(rootMotionToggle.isOn);
            }
            if (turntableToggle != null && turntable != null)
            {
                turntableToggle.onValueChanged.AddListener(v => turntable.autoRotate = v);
                turntable.autoRotate = turntableToggle.isOn;
                turntable.onUserTookOver = () => { if (turntableToggle.isOn) turntableToggle.isOn = false; };
            }
            if (recenterButton != null) recenterButton.onClick.AddListener(Recenter);
            if (allModulesButton != null) allModulesButton.onClick.AddListener(() => SetAllModules(true));
            if (noModulesButton != null) noModulesButton.onClick.AddListener(() => SetAllModules(false));
        }

        void Update()
        {
            if (_animator == null) return;

            if (_pendingFollow != null)
            {
                if (Time.time >= _pendingAt)
                {
                    var follow = _pendingFollow;
                    _pendingFollow = null;
                    Play(follow, false);
                }
                return;
            }
            if (_layerCurrent.Count > 0 && Time.frameCount > _upperPlayFrame + 1)
            {
                List<int> done = null;
                foreach (var kv in _layerCurrent)
                {
                    if (_animator.IsInTransition(kv.Key)) continue;
                    var us = _animator.GetCurrentAnimatorStateInfo(kv.Key);
                    if (!us.IsName(kv.Value.name) || us.normalizedTime >= 1f) { if (done == null) done = new List<int>(); done.Add(kv.Key); }
                }
                if (done != null)
                {
                    foreach (var k in done) _layerCurrent.Remove(k);
                    if (_current != null) ShowClipInfo(_current);
                }
            }
            if (_current == null) return;
            if (rootMotionLeash > 0f && _instance != null && rootMotionToggle != null && rootMotionToggle.isOn)
            {
                var where = spawnPoint != null ? spawnPoint.position : transform.position;
                if ((_instance.transform.position - where).sqrMagnitude > rootMotionLeash * rootMotionLeash) Recenter();
            }
            // The frame after Play() the animator still reports the previous state.
            if (Time.frameCount <= _playFrame + 1) return;

            // A one-shot that ran to its end would freeze on the last frame. Fall back.
            if (!_current.isLooping && !_animator.IsInTransition(0))
            {
                var st = _animator.GetCurrentAnimatorStateInfo(0);
                if (st.normalizedTime < 1f) return;
                var idle = ReturnClipFor(_current);
                if (_current.name.StartsWith("Death") && deathHold > 0f && idle != null && idle != _current)
                {
                    if (clipInfoLabel != null)
                        clipInfoLabel.text = string.Format("{0}   |   holds {1:0.0} s   |   then {2}", _current.name, deathHold, idle.name);
                    _pendingFollow = idle;
                    _pendingAt = Time.time + deathHold;
                    _current = null;
                    return;
                }
                if (idle != null && idle != _current) Play(idle, false);
            }
        }

        // ------------------------------------------------------------- characters

        void BuildCharacterList()
        {
            if (characterListContent == null) return;
            Clear(characterListContent, _characterButtons);
            for (int i = 0; i < characters.Count; i++)
            {
                int index = i;
                var label = string.IsNullOrEmpty(characters[i].displayName)
                    ? (characters[i].prefab != null ? characters[i].prefab.name : "Character " + i)
                    : characters[i].displayName;
                var b = DemoUI.CreateListButton(characterListContent, label, NormalColor);
                b.onClick.AddListener(() => SelectCharacter(index));
                _characterButtons.Add(b);
            }
        }

        public void SelectCharacter(int index)
        {
            if (index < 0 || index >= characters.Count) return;
            Highlight(_characterButtons, index);

            if (_instance != null) Destroy(_instance);
            _current = null;
            _pendingFollow = null;
            _layerCurrent.Clear();
            _held.Clear();
            _lastLoco = null;
            _maskedLayers.Clear();
            _clips.Clear();
            _twitches.Clear();

            var entry = characters[index];
            if (entry.prefab == null)
            {
                if (clipInfoLabel != null) clipInfoLabel.text = "No prefab assigned.";
                Clear(clipListContent, _clipButtons);
                return;
            }

            var where = spawnPoint != null ? spawnPoint : transform;
            _instance = Instantiate(entry.prefab, where.position, where.rotation);
            _instance.name = entry.prefab.name;
            _animator = _instance.GetComponentInChildren<Animator>();
            if (_animator != null)
                foreach (var ln in MaskedLayerNames) { int li = _animator.GetLayerIndex(ln); if (li >= 0) _maskedLayers.Add(li); }
            _modules = _instance.GetComponentInChildren<SkeletonModules>();
            _twitch = _instance.GetComponentInChildren<SkeletonTwitch>();
            // the demo shows the twitches through the per-clip loop toggles; the random trigger
            // firing (SkeletonTwitch, for games) stays off here so the two do not stack
            if (_twitch != null) _twitch.enabled = false;
            _weapon = _instance.GetComponentInChildren<SkeletonWeapon>();
            BuildModuleList();
            BuildWeaponList();
            FrameCamera();

            if (characterNameLabel != null)
                characterNameLabel.text = string.IsNullOrEmpty(entry.displayName) ? entry.prefab.name : entry.displayName;
            if (turntable != null) turntable.target = _instance.transform;

            CollectClips();
            BuildClipList();
            if (rootMotionToggle != null) OnRootMotionChanged(rootMotionToggle.isOn);

            var first = _clips.Find(c => c.name == idleClipName);
            if (first == null && _clips.Count > 0) first = _clips[0];
            if (first != null) Play(first);
        }

        // ------------------------------------------------------------------ clips

        void CollectClips()
        {
            _clips.Clear();
            _twitches.Clear();
            if (_animator == null || _animator.runtimeAnimatorController == null) return;
            var seen = new HashSet<string>();
            foreach (var c in _animator.runtimeAnimatorController.animationClips)
            {
                if (c == null || !seen.Add(c.name)) continue;
                if (c.name.StartsWith(twitchPrefix)) _twitches.Add(c);
                else _clips.Add(c);
            }
            _clips.Sort((a, b) => string.CompareOrdinal(a.name, b.name));
            _twitches.Sort((a, b) => string.CompareOrdinal(a.name, b.name));
        }

        class ClipSection
        {
            public string title;
            public string[] idlePreference;
            public string[] members;
        }

        static readonly ClipSection[] Sections =
        {
            new ClipSection { title = "Idle", idlePreference = new[] { "Idle" },
                members = new[] { "Idle", "Idle_02", "Idle_03" } },
            new ClipSection { title = "Weapon idles", idlePreference = new[] { "Idle" },
                members = new[] { "Idle_TwoHanded", "Idle_Propped", "Idle_Bow", "Idle_Staff" } },
            // impaled: kneeling with the sword in the belly (loop), then pull it out and rise (one-shot,
            // ends on the neutral standing pose so the crossfade lands on whichever idle follows)
            new ClipSection { title = "Impaled", idlePreference = new[] { "Idle" },
                members = new[] { "Impaled_Idle", "Impaled_Rise" } },
            new ClipSection { title = "Locomotion", idlePreference = new[] { "Idle" },
                members = new[] { "Walk_Fwd", "Walk_Back", "Run_Fwd", "Strafe_Left", "Strafe_Right",
                                  // the "normal" pair (2026-09-25): an upright human walk and jog, generated without the
                                  // stiff-undead prompt profile, for the higher ranks (necromancer, mage); the same
                                  // shared clips, the buyer picks per class
                                  "Walk_Fwd_02", "Run_Fwd_02",
                                  "Turn_Left_90", "Turn_Right_90" } },
            // per-arm set (2026-09-22): each clip lives on its arm's masked layer; Block_L_Idle is a held toggle
            new ClipSection { title = "Right arm", idlePreference = new[] { "Idle" },
                members = new[] { "Attack_R_Stab", "Attack_R_Slice" } },
            new ClipSection { title = "Left arm (block = hold)", idlePreference = new[] { "Idle" },
                members = new[] { "Attack_L_Stab", "Attack_L_Slice", "Block_L_Idle" } },
            new ClipSection { title = "Two-handed", idlePreference = new[] { "Idle_TwoHanded", "Idle" },
                members = new[] { "Attack_2H_01", "Attack_2H_02" } },
            new ClipSection { title = "Bow", idlePreference = new[] { "Idle_Bow", "Idle" },
                members = new[] { "Shoot_01" } },
            new ClipSection { title = "Magic", idlePreference = new[] { "Idle_Staff", "Idle" },
                members = new[] { "Cast_Wand_01", "Cast_Wand_02", "Cast_Staff_01" } },   // Cast_Staff_02 retired 2026-09-25 (the recorded set)
            new ClipSection { title = "Specials", idlePreference = new[] { "Idle" },
                members = new[] { "Taunt_01", "Taunt_02", "Taunt_03", "Rally", "Cutthroat", "Summon", "AOE_Cast" } },   // the user's recordings, 2026-09-25 (Taunt -> Taunt_01..03)
            new ClipSection { title = "Reactions", idlePreference = new[] { "Idle" },
                members = new[] { "Hit_Front", "Hit_Back", "Stagger", "Knockdown", "Get_Up", "Rise" } },
            new ClipSection { title = "Death", idlePreference = new string[0],
                members = new[] { "Death_01", "Death_02" } },
            new ClipSection { title = "Other", idlePreference = new string[0], members = new string[0] },
        };

        readonly Dictionary<string, ClipSection> _sectionOf = new Dictionary<string, ClipSection>();

        void BuildClipList()
        {
            if (clipListContent == null) return;
            Clear(clipListContent, _clipButtons);
            _sectionOf.Clear();

            var claimed = new HashSet<string>();
            foreach (var s in Sections)
                foreach (var m in s.members)
                    claimed.Add(m);

            var ordered = new List<AnimationClip>();
            foreach (var s in Sections)
            {
                var present = new List<AnimationClip>();
                if (s.members.Length == 0)
                {
                    foreach (var c in _clips)
                        if (!claimed.Contains(c.name)) present.Add(c);
                }
                else
                {
                    foreach (var m in s.members)
                    {
                        var c = _clips.Find(x => x.name == m);
                        if (c != null) present.Add(c);
                    }
                }
                if (present.Count == 0) continue;
                DemoUI.CreateSectionLabel(clipListContent, s.title);
                foreach (var clip in present)
                {
                    _sectionOf[clip.name] = s;
                    var b = DemoUI.CreateListButton(clipListContent, clip.name, NormalColor);
                    var captured = clip;
                    b.onClick.AddListener(() => Play(captured));
                    _clipButtons.Add(b);
                    ordered.Add(clip);
                }
            }
            _clips.Clear();
            _clips.AddRange(ordered);

            _twitchButtons.Clear();
            if (_twitches.Count > 0)
            {
                DemoUI.CreateSectionLabel(clipListContent, "Twitch  (additive, toggle)");
                while (_twitchLoopOn.Count < _twitches.Count) _twitchLoopOn.Add(true);   // all on by default
                for (int i = 0; i < _twitches.Count; i++)
                {
                    int index = i;
                    var b = DemoUI.CreateListButton(clipListContent, _twitches[i].name, NormalColor);
                    b.onClick.AddListener(() => SetTwitchLoop(index, !_twitchLoopOn[index]));
                    _twitchButtons.Add(b);
                }
                DemoUI.CreateInfoRow(clipListContent, "on = keeps adding to the current clip");
                for (int i = 0; i < _twitches.Count; i++) SetTwitchLoop(i, _twitchLoopOn[i]);
            }
        }

        bool IsLocomotion(AnimationClip clip)
        {
            ClipSection s;
            return clip != null && _sectionOf.TryGetValue(clip.name, out s) && s.title == "Locomotion";
        }

        /// <summary>The masked layer (UpperBody, LeftArm or RightArm) that has a state for this clip, or -1.</summary>
        public int LayerFor(AnimationClip clip)
        {
            if (clip == null || _animator == null) return -1;
            int hash = Animator.StringToHash(clip.name);
            foreach (var li in _maskedLayers) if (_animator.HasState(li, hash)) return li;
            return -1;
        }

        /// <summary>True when the controller offers this clip on a masked layer.</summary>
        public bool CanPlayOnTheMove(AnimationClip clip) { return LayerFor(clip) >= 0; }

        /// <summary>True while a looping clip (a block) is held on a masked layer.</summary>
        public bool IsHolding { get { return _held.Count > 0; } }

        AnimationClip ReturnClipFor(AnimationClip clip)
        {
            if (_lastLoco != null && !clip.name.StartsWith("Death")) return _lastLoco;
            ClipSection s;
            if (_sectionOf.TryGetValue(clip.name, out s))
                foreach (var name in s.idlePreference)
                {
                    var c = _clips.Find(x => x.name == name);
                    if (c != null) return c;
                }
            return _clips.Find(x => x.name == idleClipName);
        }

        /// <param name="resetFacing">Kept for callers; the position is no longer reset when a
        /// clip starts or ends (the character stays where root motion left it, the turntable
        /// follows it). Only the Recenter button and turning root motion off recenter.</param>
        public void Play(AnimationClip clip, bool resetFacing = true)
        {
            if (_animator == null || clip == null) return;
            int masked = LayerFor(clip);
            if (masked >= 0 && clip.isLooping)          // a held action (Block_L_Idle): toggle it on its layer
            {
                ToggleHeld(clip, masked);
                return;
            }
            // an arm/upper clip goes to its masked layer only while a locomotion loop runs (the legs keep
            // walking); standing, it plays full-body on Base, steps included. A held block does not change
            // that: its layer overrides the left arm over whatever Base plays, so the shield stays up
            // through a full-body attack (2026-09-23: routing every attack to the arm layer while a block
            // was held left the legs still on the idle - "stab/slice attacks stop moving the legs")
            if (masked >= 0 && _current != null && _current.isLooping && IsLocomotion(_current))
            {
                PlayOnTheMove(clip);
                return;
            }
            if (_layerCurrent.Count > 0)
            {
                foreach (var kv in _layerCurrent) _animator.Play("Empty", kv.Key, 0f);
                _layerCurrent.Clear();
            }
            if (IsLocomotion(clip)) _lastLoco = clip;
            else if (clip.isLooping) _lastLoco = null;          // an idle picked by hand ends the walk
            _pendingFollow = null;
            int hash = Animator.StringToHash(clip.name);
            bool hasEvents = clip.events != null && clip.events.Length > 0;
            bool restart = !clip.isLooping && !_animator.IsInTransition(0)
                           && _animator.GetCurrentAnimatorStateInfo(0).IsName(clip.name);
            if (!_animator.HasState(0, hash)) _animator.Play(clip.name, 0, 0f);
            else if (hasEvents || restart) _animator.Play(hash, 0, 0f);
            else _animator.CrossFadeInFixedTime(hash, crossFade, 0);

            _current = clip;
            _playFrame = Time.frameCount;
            Highlight(_clipButtons, _clips.IndexOf(clip));
            ShowClipInfo(clip);
        }

        void ShowClipInfo(AnimationClip clip)
        {
            if (clipInfoLabel == null) return;
            int frames = Mathf.RoundToInt(clip.length * clip.frameRate);
            string tail = clip.isLooping ? "looping" : "one-shot";
            if (!clip.isLooping && _lastLoco != null && !clip.name.StartsWith("Death")) tail = "full stop, then " + _lastLoco.name;
            else if (clip.isLooping && IsLocomotion(clip)) tail = "looping   |   pick an attack: on-the-move ones play over it";
            clipInfoLabel.text = string.Format("{0}   |   {1:0.00}s   |   {2} frames @ {3:0}fps   |   {4}",
                clip.name, clip.length, frames, clip.frameRate, tail);
        }

        /// <summary>Play a masked-layer clip (upper body or one arm) over whatever the base layer runs.</summary>
        public void PlayOnTheMove(AnimationClip clip)
        {
            int layer = LayerFor(clip);
            if (layer < 0) { Play(clip); return; }
            // crossfade onto the masked layer: the arm clips start mid-action (a swing begins with the
            // arm overhead) and rely on the Animator for the transition, not on baked blend frames
            _animator.CrossFadeInFixedTime(Animator.StringToHash(clip.name), crossFade, layer, 0f);
            _layerCurrent[layer] = clip;
            _upperPlayFrame = Time.frameCount;
            if (clipInfoLabel != null)
                clipInfoLabel.text = string.Format("{0}   |   {1:0.00}s   |   {2} layer over {3}{4}",
                    clip.name, clip.length, _animator.GetLayerName(layer), _current != null ? _current.name : "-",
                    _held.Count > 0 ? "   (block held)" : "   (legs keep walking)");
        }

        /// <summary>A looping masked-layer clip is a held action: on = it stays on its layer over
        /// everything until the same button releases it ("left arm stuck in block until released").</summary>
        public void ToggleHeld(AnimationClip clip, int layer)
        {
            AnimationClip cur;
            if (_held.TryGetValue(layer, out cur) && cur == clip)
            {
                _animator.CrossFadeInFixedTime("Empty", crossFade, layer);
                _held.Remove(layer);
                if (_current != null) ShowClipInfo(_current);
                return;
            }
            _animator.CrossFadeInFixedTime(Animator.StringToHash(clip.name), crossFade, layer);
            _held[layer] = clip;
            _layerCurrent.Remove(layer);
            if (clipInfoLabel != null)
                clipInfoLabel.text = string.Format("{0}   |   held on the {1} layer over {2}   (click again to release)",
                    clip.name, _animator.GetLayerName(layer), _current != null ? _current.name : "-");
        }

        /// <summary>Toggle a twitch clip: on = it loops on its own additive layer over whatever
        /// the base and upper-body layers play, until toggled off. Several can be on at once.</summary>
        public void SetTwitchLoop(int index, bool on)
        {
            if (index < 0 || index >= _twitches.Count) return;
            while (_twitchLoopOn.Count <= index) _twitchLoopOn.Add(false);
            _twitchLoopOn[index] = on;
            if (_animator != null)
            {
                int layer = _animator.GetLayerIndex("TwitchLoop_" + _twitches[index].name.Substring(_twitches[index].name.Length - 2));
                if (layer >= 0) _animator.SetLayerWeight(layer, on ? 1f : 0f);
                else Debug.LogWarning("SkeletonShowcase: no TwitchLoop layer for " + _twitches[index].name + " (rebuild the controller)", this);
            }
            if (index < _twitchButtons.Count)
            {
                var img = _twitchButtons[index].GetComponent<Image>();
                if (img != null) img.color = on ? SelectedColor : NormalColor;
            }
            if (clipInfoLabel != null)
                clipInfoLabel.text = string.Format("{0}   |   {1}   |   additive over {2}", _twitches[index].name, on ? "ON, looping" : "off", _current != null ? _current.name : "-");
        }

        public bool IsTwitchLoopOn(int index) { return index >= 0 && index < _twitchLoopOn.Count && _twitchLoopOn[index]; }

        public void FireTwitch(int index)
        {
            if (_twitch == null) return;
            _twitch.Fire(index, 1f);
            if (clipInfoLabel != null && index < _twitches.Count)
                clipInfoLabel.text = string.Format("{0}   |   additive over {1}   |   {2:0.00}s",
                    _twitches[index].name, _current != null ? _current.name : "-", _twitches[index].length);
        }

        // ---------------------------------------------------------------- options

        void OnRootMotionChanged(bool on)
        {
            if (_animator != null) _animator.applyRootMotion = on;
            if (recenterButton != null) recenterButton.gameObject.SetActive(on);
            if (!on) Recenter();
        }


        /// <summary>Bring the character back to the spawn point, keeping its facing.</summary>
        public void Recenter()
        {
            if (_instance == null) return;
            var where = spawnPoint != null ? spawnPoint : transform;
            _instance.transform.position = where.position;
        }

        // ---------------------------------------------------------------- modules

        void BuildModuleList()
        {
            Clear(moduleListContent, _moduleButtons);
            if (moduleListContent == null) return;
            bool any = _modules != null && _modules.Count > 0;
            if (moduleHeaderLabel != null) moduleHeaderLabel.text = any ? "MODULES" : "MODULES  (none)";
            if (!any) return;
            for (int i = 0; i < _modules.Count; i++)
            {
                int index = i;
                var b = DemoUI.CreateListButton(moduleListContent, _modules.NameAt(i), NormalColor);
                b.onClick.AddListener(() => ToggleModule(index));
                _moduleButtons.Add(b);
            }
            RefreshModuleButtons();
        }

        public void ToggleModule(int index)
        {
            if (_modules == null) return;
            _modules.Toggle(index);
            RefreshModuleButtons();
        }

        public void SetAllModules(bool on)
        {
            if (_modules == null) return;
            _modules.SetAll(on);
            RefreshModuleButtons();
        }

        void RefreshModuleButtons()
        {
            if (_modules == null) return;
            for (int i = 0; i < _moduleButtons.Count; i++)
            {
                var img = _moduleButtons[i].GetComponent<Image>();
                if (img != null) img.color = _modules.IsWorn(i) ? SelectedColor : NormalColor;
            }
        }

        // ---------------------------------------------------------------- weapons

        void BuildWeaponList()
        {
            Clear(weaponListContent, _weaponButtons);
            if (weaponListContent == null) return;
            bool any = _weapon != null && _weapon.Count > 0;
            if (weaponHeaderLabel != null) weaponHeaderLabel.text = any ? "WEAPONS" : "WEAPONS  (none)";
            if (!any) return;
            var none = DemoUI.CreateListButton(weaponListContent, "None", NormalColor);
            none.onClick.AddListener(() => SelectWeapon(-1));
            _weaponButtons.Add(none);
            for (int i = 0; i < _weapon.Count; i++)
            {
                int index = i;
                var b = DemoUI.CreateListButton(weaponListContent, _weapon.NameAt(i), NormalColor);
                b.onClick.AddListener(() => SelectWeapon(index));
                _weaponButtons.Add(b);
            }
            SelectWeapon(-1);
        }

        public void SelectWeapon(int index)
        {
            if (_weapon == null) return;
            _weapon.Equip(index);
            Highlight(_weaponButtons, index + 1);   // button 0 is "None"
        }

        // ---------------------------------------------------------------- framing

        void FrameCamera()
        {
            if (turntable == null || _instance == null) return;
            var rends = _instance.GetComponentsInChildren<Renderer>();
            if (rends.Length == 0) return;
            var b = rends[0].bounds;
            foreach (var r in rends) b.Encapsulate(r.bounds);
            float size = Mathf.Max(b.size.x, Mathf.Max(b.size.y, b.size.z));
            turntable.distance = Mathf.Clamp(size * 2.1f, 2.0f, 16f);
            turntable.height = b.size.y * 0.85f;
            turntable.lookAtHeight = b.size.y * 0.5f;
            turntable.maxDistance = turntable.distance * 3f;
            turntable.minDistance = size * 0.5f;
        }

        // ---------------------------------------------------------------- helpers

        static void Highlight(List<Button> buttons, int index)
        {
            for (int i = 0; i < buttons.Count; i++)
            {
                var img = buttons[i].GetComponent<Image>();
                if (img != null) img.color = (i == index) ? SelectedColor : NormalColor;
            }
        }

        static void Clear(RectTransform content, List<Button> tracked)
        {
            tracked.Clear();
            if (content == null) return;
            for (int i = content.childCount - 1; i >= 0; i--)
                Destroy(content.GetChild(i).gameObject);
        }
    }
}
