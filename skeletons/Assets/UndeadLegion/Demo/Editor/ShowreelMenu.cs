using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// Undead Legion / Record Showreel: enters play mode on the demo scene and starts a ShowreelRecorder (one already in
    /// the scene is used as configured; otherwise a temporary one with the defaults). The frames land in
    /// <repo>/Showreel/frames; encode them with tools/unity/showreel_encode.py.
    ///
    /// HEADLESS (2026-09-29): with the interactive editor closed,
    ///   Unity.exe -batchmode -projectPath skeletons -executeMethod UndeadLegion.Demo.ShowreelMenu.RecordHeadless -logFile ...
    /// reads the settings from environment variables (SHOWREEL_STAGE, SHOWREEL_AZIMUTH, _WIDTH, _HEIGHT, _SUPERSAMPLE, _MAXLOADOUTS,
    /// _OUT, _DISTANCE, _LOOKHEIGHT, _FOV, _SCENE), opens the demo scene, enters play mode and, after the domain reload,
    /// starts the recorder and exits the process when it is done (tools/unity/showreel_headless.py drives this). Batch
    /// mode keeps the GPU (no -nographics), so the offscreen render is the same; the editor UI is not loaded.
    /// </summary>
    public static class ShowreelMenu
    {
        const string KeyPending = "UndeadLegion.Showreel.Pending";
        const string KeyConfig = "UndeadLegion.Showreel.Config";
        const string DefaultScene = "Assets/UndeadLegion/Demo/Scenes/UndeadLegion_Demo.unity";

        [System.Serializable]
        public class Config
        {
            public float azimuth = -30f, elevation = 12f, distance = 4.0f, lookHeight = 1.0f, fieldOfView = 32f;
            public int width = 1920, height = 1080, supersample = 2, maxLoadouts = 0, fps = 30, msaa = 8;
            public string outputDir = "";
            public string stage = "weapons";
        }

        static bool _pending;

        [MenuItem("Undead Legion/Record Showreel (play mode)")]
        public static void Record()
        {
            if (EditorApplication.isPlaying) { Start(); return; }
            _pending = true;
            EditorApplication.playModeStateChanged -= OnPlayModeChanged;
            EditorApplication.playModeStateChanged += OnPlayModeChanged;
            EditorApplication.isPlaying = true;
        }

        static void OnPlayModeChanged(PlayModeStateChange state)
        {
            if (state != PlayModeStateChange.EnteredPlayMode || !_pending) return;
            _pending = false;
            EditorApplication.playModeStateChanged -= OnPlayModeChanged;
            Start();
        }

        public static ShowreelRecorder Start()
        {
            var rec = Object.FindFirstObjectByType<ShowreelRecorder>();
            if (rec == null) rec = new GameObject("ShowreelRecorder").AddComponent<ShowreelRecorder>();
            rec.Begin();
            return rec;
        }

        // ------------------------------------------------------------------ headless

        static string Env(string name, string fallback)
        {
            var v = System.Environment.GetEnvironmentVariable(name);
            return string.IsNullOrEmpty(v) ? fallback : v;
        }

        public static void RecordHeadless()
        {
            var cfg = new Config();
            cfg.azimuth = float.Parse(Env("SHOWREEL_AZIMUTH", "-30"), System.Globalization.CultureInfo.InvariantCulture);
            cfg.elevation = float.Parse(Env("SHOWREEL_ELEVATION", "12"), System.Globalization.CultureInfo.InvariantCulture);
            cfg.distance = float.Parse(Env("SHOWREEL_DISTANCE", "4.0"), System.Globalization.CultureInfo.InvariantCulture);
            cfg.lookHeight = float.Parse(Env("SHOWREEL_LOOKHEIGHT", "1.0"), System.Globalization.CultureInfo.InvariantCulture);
            cfg.fieldOfView = float.Parse(Env("SHOWREEL_FOV", "32"), System.Globalization.CultureInfo.InvariantCulture);
            cfg.width = int.Parse(Env("SHOWREEL_WIDTH", "1920")); cfg.height = int.Parse(Env("SHOWREEL_HEIGHT", "1080"));
            cfg.supersample = int.Parse(Env("SHOWREEL_SUPERSAMPLE", "2")); cfg.maxLoadouts = int.Parse(Env("SHOWREEL_MAXLOADOUTS", "0"));
            cfg.fps = int.Parse(Env("SHOWREEL_FPS", "30")); cfg.msaa = int.Parse(Env("SHOWREEL_MSAA", "8"));
            cfg.outputDir = Env("SHOWREEL_OUT", "");
            cfg.stage = Env("SHOWREEL_STAGE", "weapons");
            SessionState.SetString(KeyConfig, JsonUtility.ToJson(cfg));
            SessionState.SetBool(KeyPending, true);
            var scene = Env("SHOWREEL_SCENE", DefaultScene);
            Debug.Log("Showreel headless: opening " + scene + " with " + JsonUtility.ToJson(cfg));
            EditorSceneManager.OpenScene(scene);
            EditorApplication.isPlaying = true;                 // the domain reloads; Resume() picks the job up after it
        }

        static ShowreelRecorder _rec;

        [InitializeOnLoadMethod]
        static void Resume()
        {
            if (!SessionState.GetBool(KeyPending, false)) return;
            EditorApplication.update -= Tick;
            EditorApplication.update += Tick;
        }

        static void Tick()
        {
            if (!EditorApplication.isPlaying) return;
            if (_rec == null)
            {
                var sc = Object.FindFirstObjectByType<SkeletonShowcase>();
                if (sc == null) return;                          // the scene is still loading
                var cfg = JsonUtility.FromJson<Config>(SessionState.GetString(KeyConfig, "{}"));
                _rec = new GameObject("ShowreelRecorder").AddComponent<ShowreelRecorder>();
                _rec.azimuth = cfg.azimuth; _rec.elevation = cfg.elevation; _rec.distance = cfg.distance; _rec.lookHeight = cfg.lookHeight; _rec.fieldOfView = cfg.fieldOfView;
                _rec.width = cfg.width; _rec.height = cfg.height; _rec.supersample = cfg.supersample; _rec.targetMsaa = cfg.msaa; _rec.maxLoadouts = cfg.maxLoadouts; _rec.fps = cfg.fps;
                _rec.outputDir = cfg.outputDir; _rec.maxQuality = true; _rec.stage = cfg.stage;
                _rec.Begin();
                Debug.Log("Showreel headless: recorder started");
                return;
            }
            if (!_rec.Done) return;
            Debug.Log("Showreel headless: " + _rec.Status);
            SessionState.SetBool(KeyPending, false);
            EditorApplication.update -= Tick;
            if (Application.isBatchMode) EditorApplication.Exit(0);
            else EditorApplication.isPlaying = false;
        }
    }
}
