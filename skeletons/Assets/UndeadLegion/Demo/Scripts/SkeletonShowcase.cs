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
        public Text characterNameLabel;
        public Text clipInfoLabel;
        public Toggle rootMotionToggle;
        public Toggle turntableToggle;
        public Toggle twitchToggle;
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
        [Tooltip("Prefix of the clips that live on the additive twitch layer.")]
        public string twitchPrefix = "Twitch_";

        static readonly Color NormalColor = new Color(0.22f, 0.23f, 0.26f, 1f);
        static readonly Color SelectedColor = new Color(0.55f, 0.72f, 0.30f, 1f);

        GameObject _instance;
        Animator _animator;
        SkeletonModules _modules;
        SkeletonTwitch _twitch;
        readonly List<Button> _characterButtons = new List<Button>();
        readonly List<Button> _clipButtons = new List<Button>();
        readonly List<Button> _moduleButtons = new List<Button>();
        readonly List<AnimationClip> _clips = new List<AnimationClip>();      // base-layer clips, display order
        readonly List<AnimationClip> _twitches = new List<AnimationClip>();   // additive-layer clips
        AnimationClip _current;
        AnimationClip _pendingFollow;
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
            if (twitchToggle != null)
            {
                twitchToggle.onValueChanged.AddListener(OnTwitchChanged);
                OnTwitchChanged(twitchToggle.isOn);
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
            if (_current == null) return;
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
            _modules = _instance.GetComponentInChildren<SkeletonModules>();
            _twitch = _instance.GetComponentInChildren<SkeletonTwitch>();
            if (_twitch != null && twitchToggle != null) _twitch.enabled = twitchToggle.isOn;
            BuildModuleList();
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
            new ClipSection { title = "Locomotion", idlePreference = new[] { "Idle" },
                members = new[] { "Idle", "Walk_Fwd", "Walk_Back", "Run_Fwd", "Strafe_Left", "Strafe_Right",
                                  "Turn_Left_90", "Turn_Right_90" } },
            new ClipSection { title = "Combat", idlePreference = new[] { "Idle_Combat", "Idle" },
                members = new[] { "Idle_Combat", "Attack_Light_01", "Attack_Light_02", "Attack_Heavy",
                                  "Attack_Special", "Shoot", "Cast", "Idle_Block", "Block_Impact", "Dodge_Back" } },
            new ClipSection { title = "Reactions", idlePreference = new[] { "Idle_Combat", "Idle" },
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

            if (_twitches.Count > 0)
            {
                DemoUI.CreateSectionLabel(clipListContent, "Twitch  (additive layer)");
                for (int i = 0; i < _twitches.Count; i++)
                {
                    int index = i;
                    var b = DemoUI.CreateListButton(clipListContent, _twitches[i].name, NormalColor);
                    b.onClick.AddListener(() => FireTwitch(index));
                }
                DemoUI.CreateInfoRow(clipListContent, "plays over the current clip");
            }
        }

        AnimationClip ReturnClipFor(AnimationClip clip)
        {
            ClipSection s;
            if (_sectionOf.TryGetValue(clip.name, out s))
                foreach (var name in s.idlePreference)
                {
                    var c = _clips.Find(x => x.name == name);
                    if (c != null) return c;
                }
            return _clips.Find(x => x.name == idleClipName);
        }

        /// <param name="resetFacing">True when the viewer picked the clip: put the character
        /// back on the spawn point facing forward. False when falling back to idle after a
        /// one-shot, where a turn's rotation must survive.</param>
        public void Play(AnimationClip clip, bool resetFacing = true)
        {
            if (_animator == null || clip == null) return;
            _pendingFollow = null;
            if (resetFacing && _instance != null)
            {
                var home = spawnPoint != null ? spawnPoint : transform;
                _instance.transform.SetPositionAndRotation(home.position, home.rotation);
            }
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
            if (clipInfoLabel != null)
            {
                int frames = Mathf.RoundToInt(clip.length * clip.frameRate);
                clipInfoLabel.text = string.Format("{0}   |   {1:0.00}s   |   {2} frames @ {3:0}fps   |   {4}",
                    clip.name, clip.length, frames, clip.frameRate, clip.isLooping ? "looping" : "one-shot");
            }
            if (rootMotionToggle != null && rootMotionToggle.isOn) Recenter();
        }

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

        void OnTwitchChanged(bool on)
        {
            if (_twitch != null) _twitch.enabled = on;
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
