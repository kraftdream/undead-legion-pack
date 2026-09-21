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
        int _upperLayer = -1;
        AnimationClip _upperCurrent;
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
            if (_upperCurrent != null && Time.frameCount > _upperPlayFrame + 1 && !_animator.IsInTransition(_upperLayer))
            {
                var us = _animator.GetCurrentAnimatorStateInfo(_upperLayer);
                if (!us.IsName(_upperCurrent.name) || us.normalizedTime >= 1f)
                {
                    _upperCurrent = null;
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
            _upperCurrent = null;
            _lastLoco = null;
            _upperLayer = -1;
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
            if (_animator != null) _upperLayer = _animator.GetLayerIndex("UpperBody");
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
                members = new[] { "Idle_TwoHanded", "Idle_Propped", "Idle_Bow", "Idle_Staff", "Idle_Wand" } },
            // impaled: kneeling with the sword in the belly (loop), then pull it out and rise (one-shot,
            // ends on the neutral standing pose so the crossfade lands on whichever idle follows)
            new ClipSection { title = "Impaled", idlePreference = new[] { "Idle" },
                members = new[] { "Impaled_Idle", "Impaled_Rise" } },
            new ClipSection { title = "Locomotion", idlePreference = new[] { "Idle" },
                members = new[] { "Walk_Fwd", "Walk_Back", "Run_Fwd", "Strafe_Left", "Strafe_Right",
                                  "Turn_Left_90", "Turn_Right_90" } },
            new ClipSection { title = "One-handed", idlePreference = new[] { "Idle" },
                members = new[] { "Attack_1H_01", "Attack_1H_02", "Shield_Bash", "Block" } },
            new ClipSection { title = "Two-handed", idlePreference = new[] { "Idle_TwoHanded", "Idle" },
                members = new[] { "Attack_2H_01", "Attack_2H_02" } },
            new ClipSection { title = "Bow", idlePreference = new[] { "Idle_Bow", "Idle" },
                members = new[] { "Shoot_01", "Shoot_02" } },
            new ClipSection { title = "Magic", idlePreference = new[] { "Idle_Staff", "Idle_Wand", "Idle" },
                members = new[] { "Cast_Wand_01", "Cast_Wand_02", "Cast_Staff_01", "Cast_Staff_02" } },
            new ClipSection { title = "Specials", idlePreference = new[] { "Idle" },
                members = new[] { "Taunt", "Rally", "Cutthroat", "Summon", "AOE_Cast" } },
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

        /// <summary>True when the controller offers this clip on the masked upper-body layer.</summary>
        public bool CanPlayOnTheMove(AnimationClip clip)
        {
            return clip != null && _animator != null && _upperLayer >= 0
                   && _animator.HasState(_upperLayer, Animator.StringToHash(clip.name));
        }

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
            if (_current != null && _current.isLooping && IsLocomotion(_current) && CanPlayOnTheMove(clip))
            {
                PlayOnTheMove(clip);
                return;
            }
            if (_upperCurrent != null)
            {
                _animator.Play("Empty", _upperLayer, 0f);
                _upperCurrent = null;
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

        /// <summary>Play an upper-body-capable clip on the masked layer over the running locomotion loop.</summary>
        public void PlayOnTheMove(AnimationClip clip)
        {
            if (!CanPlayOnTheMove(clip)) { Play(clip); return; }
            _animator.Play(Animator.StringToHash(clip.name), _upperLayer, 0f);
            _upperCurrent = clip;
            _upperPlayFrame = Time.frameCount;
            if (clipInfoLabel != null)
                clipInfoLabel.text = string.Format("{0}   |   {1:0.00}s   |   upper body over {2}   (legs keep walking)",
                    clip.name, clip.length, _current != null ? _current.name : "-");
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
