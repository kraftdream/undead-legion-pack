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

        /// <summary>One character's armour module prefabs (the catalogue the demo offers on EVERY character:
        /// any piece fits any skeleton). Filled by the scene builder from Prefabs/Armor.</summary>
        [System.Serializable]
        public class ArmorSet
        {
            public string character;
            public List<GameObject> modules = new List<GameObject>();
        }

        [Tooltip("Every character's armour module prefabs; the modules panel lists the current character's default set first, then the other sets to borrow from.")]
        public List<ArmorSet> armorCatalogue = new List<ArmorSet>();

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
        public string idleClipName = "Idle_01";
        [Tooltip("Seconds a finished death clip holds its last pose before the idle returns.")]
        public float deathHold = 2f;
        [Tooltip("With root motion on, bring the character back to the spawn point once it is this far away (metres). 0 = never: the position is only reset by the Recenter button or by turning root motion off.")]
        public float rootMotionLeash = 0f;
        [Tooltip("Prefix of the clips that live on the additive twitch layer.")]
        public string twitchPrefix = "Twitch_";
        [Tooltip("Prefix of the empty-hand finger idle clips (LeftFingers / RightFingers layers): listed as toggles, highlighted while their layer drives the hand.")]
        public string handIdlePrefix = "Hand_Idle_";

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
        readonly List<AnimationClip> _handIdles = new List<AnimationClip>();   // Hand_Idle_L / _R (finger-layer clips, 2026-09-28)
        readonly List<Button> _handIdleButtons = new List<Button>();
        bool _deathSuspend;   // a death plays: the twitch loops and the finger idles are off until the next clip
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
            if (_handIdleButtons.Count > 0 && (Time.frameCount & 7) == 0) RefreshHandIdleButtons();

            if (_pendingFollow != null)
            {
                if (Time.time >= _pendingAt)
                {
                    var follow = _pendingFollow;
                    _pendingFollow = null;
                    if (_pendingIsSequence && _seq != null) { _pendingIsSequence = false; AdvanceSequence(); }
                    else Play(follow, false);
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
                if (!st.IsName(_current.name))
                {
                    // the controller carried the one-shot into a follow-up loop of its own (manifest `next`, e.g.
                    // Cast_Staff_01 -> Idle_Staff from frame 54): adopt that loop instead of crossfading back
                    var landed = _clips.Find(x => x.isLooping && st.IsName(x.name));
                    if (landed != null) { _current = landed; ShowClipInfo(landed); HighlightClip(landed); return; }
                }
                if (st.normalizedTime < 1f) return;
                if (_seq != null && _seqIndex + 1 < _seq.steps.Length) { AdvanceSequence(); return; }
                _seq = null;
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
            _handIdles.Clear();
            _deathSuspend = false;

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
                else if (c.name.StartsWith(handIdlePrefix)) _handIdles.Add(c);
                else _clips.Add(c);
            }
            _clips.Sort((a, b) => string.CompareOrdinal(a.name, b.name));
            _twitches.Sort((a, b) => string.CompareOrdinal(a.name, b.name));
            _handIdles.Sort((a, b) => string.CompareOrdinal(a.name, b.name));
        }

        class ClipSection
        {
            public string title;
            public string[] idlePreference;
            public string[] members;
        }

        static readonly ClipSection[] Sections =
        {
            new ClipSection { title = "Idle", idlePreference = new[] { "Idle_01" },
                members = new[] { "Idle_01", "Idle_02", "Idle_03" } },
            new ClipSection { title = "Weapon idles", idlePreference = new[] { "Idle_01" },
                members = new[] { "Idle_TwoHanded", "Idle_Bow", "Idle_Staff" } },   // Idle_Propped removed 2026-09-25 with the "Staff (propped)" loadout
            // impaled: kneeling with the sword in the belly (loop), then pull it out and rise (one-shot,
            // ends on the neutral standing pose so the crossfade lands on whichever idle follows)
            new ClipSection { title = "Impaled", idlePreference = new[] { "Idle_01" },
                members = new[] { "Impaled_Idle", "Impaled_Rise" } },   // not exported since 2026-09-26 ("for now"); the section hides itself while the clips are missing
            new ClipSection { title = "Locomotion", idlePreference = new[] { "Idle_01" },
                // _01 = the low-rank (shambling) set, renamed 2026-09-26; _02 = the normal-looking set for the higher ranks
                members = new[] { "Walk_Fwd_01", "Walk_Back_01", "Run_Fwd_01", "Strafe_Left_01", "Strafe_Right_01",
                                  // the "normal" pair (2026-09-25): an upright human walk and jog, generated without the
                                  // stiff-undead prompt profile, for the higher ranks (necromancer, mage); the same
                                  // shared clips, the buyer picks per class
                                  "Walk_Fwd_02", "Walk_Back_02", "Run_Fwd_02", "Strafe_Left_02", "Strafe_Right_02",
                                  "Turn_Left_90", "Turn_Right_90" } },
            // per-arm set (2026-09-22): each clip lives on its arm's masked layer; Block_L_Idle is a held toggle
            new ClipSection { title = "Right arm", idlePreference = new[] { "Idle_01" },
                members = new[] { "Attack_R_Stab", "Attack_R_Slice" } },
            new ClipSection { title = "Left arm (block = hold)", idlePreference = new[] { "Idle_01" },
                members = new[] { "Attack_L_Stab", "Attack_L_Slice", "Block_L_Idle" } },
            new ClipSection { title = "Two-handed", idlePreference = new[] { "Idle_TwoHanded", "Idle_01" },
                members = new[] { "Attack_2H_01", "Attack_2H_02" } },
            new ClipSection { title = "Bow", idlePreference = new[] { "Idle_Bow", "Idle_01" },
                members = new[] { "Shoot_01" } },
            new ClipSection { title = "Magic", idlePreference = new[] { "Idle_Staff", "Idle_01" },
                members = new[] { "Cast_Wand_01", "Cast_Wand_02", "Cast_Staff_01" } },   // Cast_Staff_02 retired 2026-09-25 (the recorded set)
            new ClipSection { title = "Specials", idlePreference = new[] { "Idle_01" },
                members = new[] { "Taunt_01", "Taunt_02", "Taunt_03", "Rally", "Cutthroat", "Summon", "AOE_Cast" } },   // the user's recordings, 2026-09-25 (Taunt -> Taunt_01..03)
            new ClipSection { title = "Reactions", idlePreference = new[] { "Idle_01" },
                members = new[] { "Hit_Front", "Hit_Back", "Stagger", "Knockdown", "Get_Up", "Rise" } },
            new ClipSection { title = "Death", idlePreference = new string[0],
                members = new[] { "Death_01", "Death_02", "Death_03", "Death_04" } },   // the four instant-fall generations the user kept (2026-09-27): drop, face-down, on the back, puppet
            new ClipSection { title = "Other", idlePreference = new string[0], members = new string[0] },
        };

        readonly Dictionary<string, ClipSection> _sectionOf = new Dictionary<string, ClipSection>();

        /// <summary>A clip SEQUENCE listed as one button (2026-09-27, user: "aoe_cast as hold (loopable) + release,
        /// played as a sequence: the hold looping with a delay, then the release"; the creatures pack's
        /// knockdown / get-up idea): the steps play in order; a looping step holds for holdSeconds before the next
        /// step, a one-shot step advances when it ends; after the last step the usual return to the section's idle.</summary>
        public class ClipSequence
        {
            public string name;
            public string[] steps;
            public float holdSeconds;
        }

        static readonly ClipSequence[] Sequences =
        {
            // (the AOE_Cast Start / Hold / Release sequence was reverted 2026-09-27: a hold cut from a one-shot take
            // did not read as a hold; add an entry here once a hold is recorded as a loop)
        };

        ClipSequence _seq;
        int _seqIndex;
        bool _seqPlaying;
        bool _pendingIsSequence;
        readonly List<Button> _seqButtons = new List<Button>();
        readonly List<AnimationClip> _seqClips = new List<AnimationClip>();   // the steps: not in the list (no button), reachable by name

        AnimationClip FindClip(string name)
        {
            var c = _clips.Find(x => x.name == name);
            return c != null ? c : _seqClips.Find(x => x.name == name);
        }

        void BuildClipList()
        {
            if (clipListContent == null) return;
            Clear(clipListContent, _clipButtons);
            _sectionOf.Clear();

            var claimed = new HashSet<string>();
            foreach (var s in Sections)
                foreach (var m in s.members)
                    claimed.Add(m);
            _seqClips.Clear();
            foreach (var q in Sequences)
                foreach (var step in q.steps)
                {
                    claimed.Add(step);                          // the steps are reached through the sequence button
                    var sc_ = _clips.Find(x => x.name == step);
                    if (sc_ != null && !_seqClips.Contains(sc_)) _seqClips.Add(sc_);
                }
            _seqButtons.Clear();

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
                var seqs = new List<ClipSequence>();
                foreach (var m in s.members)
                    foreach (var q in Sequences)
                        if (q.name == m && SequenceAvailable(q)) seqs.Add(q);
                if (present.Count == 0 && seqs.Count == 0) continue;
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
                foreach (var q in seqs)
                {
                    // the sequence's steps boxed together like the creatures pack's knockback / get-up pair:
                    // one button per step (each plays the sequence FROM that step) and a delay row after the
                    // looping step (rows 30 each, info rows 20, spacing 2, padding 4+4)
                    float h = 8f;
                    foreach (var step in q.steps) { var sc_ = FindClip(step); h += 30f + 2f; if (sc_ != null && sc_.isLooping && step != q.steps[q.steps.Length - 1]) h += 20f + 2f; }
                    var group = DemoUI.CreateGroup(clipListContent, h);
                    for (int si = 0; si < q.steps.Length; si++)
                    {
                        var stepClip = FindClip(q.steps[si]);
                        if (stepClip == null) continue;
                        _sectionOf[stepClip.name] = s;
                        var bq = DemoUI.CreateListButton(group, stepClip.name, NormalColor);
                        var capturedQ = q; int capturedI = si;
                        bq.onClick.AddListener(() => PlaySequence(capturedQ, capturedI));
                        _seqButtons.Add(bq);
                        if (stepClip.isLooping && si + 1 < q.steps.Length)
                            DemoUI.CreateInfoRow(group, string.Format("delay  {0:0.0} s", q.holdSeconds));
                    }
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

            // the empty-hand finger idles (2026-09-28, user: "hand_idle_l/r are not highlighted when they are
            // active"): one toggle per hand, lit while its finger layer drives the hand (empty, toggle on, no
            // death playing); the weight itself is SkeletonWeapon's (0 on a hand that holds an item)
            _handIdleButtons.Clear();
            if (_handIdles.Count > 0)
            {
                DemoUI.CreateSectionLabel(clipListContent, "Hand idle  (empty hand, toggle)");
                for (int i = 0; i < _handIdles.Count; i++)
                {
                    var hc = _handIdles[i];
                    var hb = DemoUI.CreateListButton(clipListContent, hc.name, NormalColor);
                    var hand = HandOf(hc);
                    hb.onClick.AddListener(() => ToggleHandIdle(hand));
                    _handIdleButtons.Add(hb);
                }
                DemoUI.CreateInfoRow(clipListContent, "lit = driving that hand's fingers");
                RefreshHandIdleButtons();
            }
        }

        SkeletonWeapon.Hand HandOf(AnimationClip clip)
        {
            return clip != null && clip.name.EndsWith("_L") ? SkeletonWeapon.Hand.Left : SkeletonWeapon.Hand.Right;
        }

        public void ToggleHandIdle(SkeletonWeapon.Hand hand)
        {
            if (_weapon == null) return;
            bool on = hand == SkeletonWeapon.Hand.Left ? _weapon.fingerIdleLeft : _weapon.fingerIdleRight;
            _weapon.SetFingerIdle(hand, !on);
            RefreshHandIdleButtons();
            if (clipInfoLabel != null)
                clipInfoLabel.text = string.Format("Hand idle {0}   |   {1}   |   over {2}", hand == SkeletonWeapon.Hand.Left ? "L" : "R", !on ? "ON while the hand is empty" : "off", _current != null ? _current.name : "-");
        }

        void RefreshHandIdleButtons()
        {
            for (int i = 0; i < _handIdleButtons.Count && i < _handIdles.Count; i++)
            {
                bool active = _weapon != null && _weapon.IsFingerIdleActive(HandOf(_handIdles[i]));
                var img = _handIdleButtons[i].GetComponent<Image>();
                if (img != null) img.color = active ? SelectedColor : NormalColor;
            }
        }

        /// <summary>A death plays (2026-09-28, user: "when death plays, twitch and hand idle animations should stop"):
        /// every twitch loop layer and both finger idles go to 0 until the next clip; the toggles keep their state.</summary>
        void SetDeathSuspend(bool on)
        {
            if (_deathSuspend == on) return;
            _deathSuspend = on;
            if (_animator != null)
                for (int i = 0; i < _twitches.Count; i++)
                {
                    int layer = _animator.GetLayerIndex("TwitchLoop_" + _twitches[i].name.Substring(_twitches[i].name.Length - 2));
                    if (layer >= 0) _animator.SetLayerWeight(layer, (!on && i < _twitchLoopOn.Count && _twitchLoopOn[i]) ? 1f : 0f);
                }
            if (_weapon != null) _weapon.SetFingerIdleSuspended(on);
            RefreshHandIdleButtons();
        }

        bool IsDeath(AnimationClip clip)
        {
            ClipSection s;
            return clip != null && _sectionOf.TryGetValue(clip.name, out s) && s.title == "Death";
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
        void HighlightSequenceStep(AnimationClip clip)
        {
            int k = 0;
            foreach (var q in Sequences)
                foreach (var step in q.steps)
                {
                    if (FindClip(step) == null) continue;
                    if (k < _seqButtons.Count) _seqButtons[k].image.color = step == clip.name ? SelectedColor : NormalColor;
                    k++;
                }
        }

        bool SequenceAvailable(ClipSequence q)
        {
            foreach (var step in q.steps) if (FindClip(step) == null) return false;
            return true;
        }

        public void PlaySequence(ClipSequence q) { PlaySequence(q, 0); }

        /// <summary>Play the sequence from its step `from` (a step's own button starts there).</summary>
        public void PlaySequence(ClipSequence q, int from)
        {
            if (_animator == null || q == null || !SequenceAvailable(q)) return;
            _seq = q; _seqIndex = from - 1;
            AdvanceSequence();
        }

        /// <summary>The next step of the running sequence: a looping step is held for holdSeconds (the pending
        /// follow-up mechanism), a one-shot step runs to its end (the one-shot fallback in Update advances it).</summary>
        void AdvanceSequence()
        {
            if (_seq == null) return;
            _seqIndex++;
            if (_seqIndex >= _seq.steps.Length) { _seq = null; return; }
            var clip = FindClip(_seq.steps[_seqIndex]);
            if (clip == null) { _seq = null; return; }
            _seqPlaying = true;
            Play(clip, false);
            _seqPlaying = false;
            HighlightSequenceStep(clip);
            string tail = clip.isLooping ? "looping" : "one-shot";
            if (clip.isLooping && _seqIndex + 1 < _seq.steps.Length)
            {
                var next = FindClip(_seq.steps[_seqIndex + 1]);
                if (next != null)
                {
                    _pendingFollow = next;
                    _pendingAt = Time.time + _seq.holdSeconds;
                    _pendingIsSequence = true;
                    tail = string.Format("holds {0:0.0} s, then {1}", _seq.holdSeconds, next.name);
                }
            }
            if (clipInfoLabel != null)
                clipInfoLabel.text = string.Format("{0}   |   step {1}/{2}: {3}   |   {4}", _seq.name, _seqIndex + 1, _seq.steps.Length, clip.name, tail);
        }

        public void Play(AnimationClip clip, bool resetFacing = true)
        {
            if (_animator == null || clip == null) return;
            if (!_seqPlaying) { _seq = null; _pendingIsSequence = false; }
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
            SetDeathSuspend(IsDeath(clip));
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

        void HighlightClip(AnimationClip clip)

        {

            int i = _clips.IndexOf(clip);

            if (i >= 0 && i < _clipButtons.Count) Highlight(_clipButtons, i);

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
                if (layer >= 0) _animator.SetLayerWeight(layer, (on && !_deathSuspend) ? 1f : 0f);
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

        readonly List<Button> _catalogueButtons = new List<Button>();
        readonly List<GameObject> _cataloguePrefabs = new List<GameObject>();

        void BuildModuleList()
        {
            Clear(moduleListContent, _moduleButtons);
            Clear(moduleListContent, _catalogueButtons);
            _catalogueButtons.Clear(); _cataloguePrefabs.Clear();
            if (moduleListContent == null) return;
            bool any = _modules != null && _modules.Count > 0;
            if (moduleHeaderLabel != null) moduleHeaderLabel.text = any ? "MODULES" : "MODULES  (none)";
            if (!any) return;
            // the character's own set (the armour map's defaults), toggles
            for (int i = 0; i < _modules.Count; i++)
            {
                int index = i;
                var b = DemoUI.CreateListButton(moduleListContent, _modules.NameAt(i), NormalColor);
                b.onClick.AddListener(() => ToggleModule(index));
                _moduleButtons.Add(b);
            }
            // the other characters' pieces: any of them fits this skeleton (one shared rig); a click wears or
            // removes it (2026-09-27, the modular route)
            string current = _instance != null ? _instance.name.Replace("PF_", "") : "";
            foreach (var set in armorCatalogue)
            {
                if (set == null || set.character == current || set.modules.Count == 0) continue;
                DemoUI.CreateSectionLabel(moduleListContent, set.character.Replace("Skeleton", "") + " armour");
                foreach (var mp in set.modules)
                {
                    if (mp == null) continue;
                    var am = mp.GetComponent<ArmorModule>();
                    var b = DemoUI.CreateListButton(moduleListContent, am != null ? am.moduleName : mp.name, NormalColor);
                    var captured = mp;
                    b.onClick.AddListener(() => { if (_modules != null) { _modules.ToggleWear(captured); RefreshModuleButtons(); } });
                    _catalogueButtons.Add(b);
                    _cataloguePrefabs.Add(mp);
                }
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
            for (int i = 0; i < _catalogueButtons.Count; i++)
            {
                var img = _catalogueButtons[i].GetComponent<Image>();
                if (img != null) img.color = _modules.IsWearing(_cataloguePrefabs[i]) ? SelectedColor : NormalColor;
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
