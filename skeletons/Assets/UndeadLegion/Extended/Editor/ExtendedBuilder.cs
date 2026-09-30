using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.EventSystems;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using Unity.AI.Navigation;
using UndeadLegion.Demo;
using UndeadLegion.DemoEditor;

namespace UndeadLegion.ExtendedEditor
{
    /// <summary>
    /// Builds the extended edition from the base assets, so it follows every change to them:
    ///   1. AC_Skeleton_Extended: a copy of AC_Skeleton plus two locomotion blend trees (MoveX / MoveZ, clips at their
    ///      measured speeds) and the weapon idles on the UpperBody layer (held while walking).
    ///   2. PFX_&lt;Character&gt;: variants of the character prefabs with the ragdoll, hit reactions, health, cloth, dissolve,
    ///      eyes, a NavMeshAgent, the navigation controller and the combat AI.
    ///   3. The arena demo scene: a baked NavMesh, lights and bloom, the battle camera, two armies and the demo controller.
    ///   4. The browser demo with the extended characters and a PHYSICS panel (cloth, hits, ragdoll, revive, rise / dust).
    /// </summary>
    public static class ExtendedBuilder
    {
        const string Root = "Assets/UndeadLegion/Extended";
        const string BaseController = "Assets/UndeadLegion/Animations/AC_Skeleton.controller";
        const string Controller = Root + "/Animations/AC_Skeleton_Extended.controller";
        const string PrefabDir = Root + "/Prefabs";
        const string SceneDir = Root + "/Scenes";
        const string ScenePath = SceneDir + "/UndeadLegion_Extended_Demo.unity";
        const string ShowcasePath = SceneDir + "/UndeadLegion_Extended_Showcase.unity";
        static readonly string[] Characters = { "Knight", "Warrior", "Archer", "Assassin", "Mage", "Necromancer" };

        [MenuItem("Undead Legion/Extended/1. Build Extended Controller")]
        public static string BuildController()
        {
            Directory.CreateDirectory(Root + "/Animations");
            if (File.Exists(Controller)) AssetDatabase.DeleteAsset(Controller);
            AssetDatabase.CopyAsset(BaseController, Controller);
            var ac = AssetDatabase.LoadAssetAtPath<AnimatorController>(Controller);
            ac.AddParameter("MoveX", AnimatorControllerParameterType.Float);
            ac.AddParameter("MoveZ", AnimatorControllerParameterType.Float);
            // measured speeds (m/s): walk forward, run, walk back, strafe
            AddLocomotion(ac, "Locomotion_Heavy", "Idle_01", "Walk_Fwd_01", 0.52f, "Run_Fwd_01", 1.14f, "Walk_Back_01", 0.34f, "Strafe_Left_01", "Strafe_Right_01", 0.20f);
            AddLocomotion(ac, "Locomotion_Upright", "Idle_01", "Walk_Fwd_02", 1.28f, "Run_Fwd_02", 1.87f, "Walk_Back_02", 0.77f, "Strafe_Left_02", "Strafe_Right_02", 0.93f);
            // weapon idles on the upper body, so the weapon stays in its pose while the legs walk
            int upper = -1; for (int i = 0; i < ac.layers.Length; i++) if (ac.layers[i].name == "UpperBody") upper = i;
            int added = 0;
            if (upper >= 0)
            {
                var sm = ac.layers[upper].stateMachine;
                foreach (var idle in new[] { "Idle_1H_Combat", "Idle_TwoHanded", "Idle_Bow", "Idle_Staff" })
                {
                    bool exists = false; foreach (var s in sm.states) if (s.state.name == idle) exists = true;
                    if (exists) continue;
                    var clip = Clip(idle); if (clip == null) continue;
                    var st = sm.AddState(idle); st.motion = clip; added++;
                    var baseState = FindState(ac.layers[0].stateMachine, idle);
                    if (baseState != null) foreach (var b in baseState.behaviours)
                        if (b is SkeletonGripState) { var g = st.AddStateMachineBehaviour<SkeletonGripState>(); g.hand = ((SkeletonGripState)b).hand; }
                }
            }
            EditorUtility.SetDirty(ac); AssetDatabase.SaveAssets();
            return Controller + ": locomotion trees 2, upper-body idles " + added;
        }

        static AnimatorState FindState(AnimatorStateMachine sm, string name) { foreach (var s in sm.states) if (s.state.name == name) return s.state; return null; }

        static AnimationClip Clip(string name)
        {
            foreach (var o in AssetDatabase.LoadAllAssetsAtPath("Assets/UndeadLegion/Animations/Skeleton@" + name + ".fbx"))
                if (o is AnimationClip && !o.name.StartsWith("__preview")) return (AnimationClip)o;
            return null;
        }

        static void AddLocomotion(AnimatorController ac, string state, string idle, string walk, float walkSpeed, string run, float runSpeed, string back, float backSpeed, string left, string right, float strafeSpeed)
        {
            BlendTree tree;
            var st = ac.CreateBlendTreeInController(state, out tree, 0);
            tree.blendType = BlendTreeType.FreeformDirectional2D;
            tree.blendParameter = "MoveX"; tree.blendParameterY = "MoveZ";
            tree.useAutomaticThresholds = false;
            void Add(string clip, float x, float z) { var c = Clip(clip); if (c != null) tree.AddChild(c, new Vector2(x, z)); else Debug.LogWarning("[Extended] clip missing: " + clip); }
            Add(idle, 0f, 0f);
            Add(walk, 0f, walkSpeed);
            Add(run, 0f, runSpeed);
            Add(back, 0f, -backSpeed);
            Add(left, -strafeSpeed, 0f);
            Add(right, strafeSpeed, 0f);
            st.writeDefaultValues = true;
        }

        [MenuItem("Undead Legion/Extended/2. Build Extended Prefabs")]
        public static string BuildPrefabs()
        {
            Directory.CreateDirectory(PrefabDir);
            var controller = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(Controller);
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(Root + "/Shaders/UndeadLegionDissolve.shader");
            var sb = new System.Text.StringBuilder();
            foreach (var ch in Characters)
            {
                var basePrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/UndeadLegion/Prefabs/Characters/PF_Skeleton" + ch + ".prefab");
                if (basePrefab == null) { sb.AppendLine("missing base prefab " + ch); continue; }
                string path = PrefabDir + "/PFX_Skeleton" + ch + ".prefab";
                if (File.Exists(path)) AssetDatabase.DeleteAsset(path);
                var go = (GameObject)PrefabUtility.InstantiatePrefab(basePrefab);
                var an = go.GetComponent<Animator>(); if (controller != null) an.runtimeAnimatorController = controller;
                var ragdoll = go.AddComponent<UndeadLegion.Extended.SkeletonRagdoll>(); ragdoll.Build();
                go.AddComponent<UndeadLegion.Extended.SkeletonHitReaction>();
                go.AddComponent<UndeadLegion.Extended.SkeletonHealth>();
                go.AddComponent<UndeadLegion.Extended.SkeletonCloth>();
                var dis = go.AddComponent<UndeadLegion.Extended.SkeletonDissolve>(); dis.dissolveShader = shader;
                go.AddComponent<UndeadLegion.Extended.SkeletonEyes>();
                var agent = go.AddComponent<NavMeshAgent>();
                agent.radius = 0.32f; agent.height = 1.8f; agent.speed = 0.52f; agent.angularSpeed = 360f; agent.acceleration = 6f;
                agent.stoppingDistance = 0.1f; agent.obstacleAvoidanceType = ObstacleAvoidanceType.MedQualityObstacleAvoidance;
                go.AddComponent<UndeadLegion.Extended.SkeletonNavController>();
                go.AddComponent<UndeadLegion.Extended.SkeletonAI>();
                var twitch = go.GetComponent<SkeletonTwitch>(); if (twitch != null) twitch.enabled = true;
                PrefabUtility.SaveAsPrefabAsset(go, path);
                Object.DestroyImmediate(go);
                sb.AppendLine(path + ": ragdoll " + ragdoll.parts.Count + " bodies");
            }
            AssetDatabase.SaveAssets();
            return sb.ToString();
        }

        [MenuItem("Undead Legion/Extended/3. Build Extended Demo Scene")]
        public static string BuildScene()
        {
            Directory.CreateDirectory(SceneDir); Directory.CreateDirectory(Root + "/Materials");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // lights: the base demo's three-light rig, sky ambient
            var key = Light("Key Light", new Color(1f, 0.95f, 0.88f), 1.2f, LightShadows.Soft, new Vector3(50f, -35f, 0f));
            Light("Fill Light", new Color(0.45f, 0.55f, 0.75f), 0.4f, LightShadows.None, new Vector3(25f, 150f, 0f));
            RenderSettings.ambientMode = AmbientMode.Skybox; RenderSettings.ambientIntensity = 1.4f; RenderSettings.sun = key;
            RenderSettings.skybox = AssetDatabase.GetBuiltinExtraResource<Material>("Default-Skybox.mat");

            // arena
            var arena = new GameObject("Arena");
            var ground = GameObject.CreatePrimitive(PrimitiveType.Plane); ground.name = "Ground"; ground.transform.SetParent(arena.transform); ground.transform.localScale = new Vector3(10f, 1f, 10f);
            var groundMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/UndeadLegion/Materials/URP/M_Demo_Ground.mat"); if (groundMat != null) ground.GetComponent<Renderer>().sharedMaterial = groundMat;
            var stone = new Material(Shader.Find("Universal Render Pipeline/Lit")); stone.SetColor("_BaseColor", new Color(0.36f, 0.35f, 0.33f)); stone.SetFloat("_Smoothness", 0.15f);
            string stonePath = Root + "/Materials/M_Arena_Stone.mat";
            if (File.Exists(stonePath)) AssetDatabase.DeleteAsset(stonePath);
            AssetDatabase.CreateAsset(stone, stonePath);
            var rng = new System.Random(7);
            foreach (var p in new[] { new Vector3(-6f, 0f, 0f), new Vector3(6f, 0f, 1f), new Vector3(-2.5f, 0f, 3f), new Vector3(3f, 0f, -3f), new Vector3(-9f, 0f, 5f), new Vector3(9f, 0f, -5f) })
            {
                var pillar = GameObject.CreatePrimitive(PrimitiveType.Cylinder); pillar.name = "Pillar"; pillar.transform.SetParent(arena.transform);
                float h = 1.2f + (float)rng.NextDouble() * 2.2f;
                pillar.transform.position = p + Vector3.up * h * 0.5f; pillar.transform.localScale = new Vector3(0.8f, h * 0.5f, 0.8f);
                pillar.GetComponent<Renderer>().sharedMaterial = stone;
                NotWalkable(pillar);
            }
            foreach (var w in new[] { new Vector4(0f, 0f, 12f, 0f), new Vector4(-12f, 0f, -2f, 90f) })
            {
                var wall = GameObject.CreatePrimitive(PrimitiveType.Cube); wall.name = "Wall"; wall.transform.SetParent(arena.transform);
                wall.transform.position = new Vector3(w.x, 0.6f, w.z); wall.transform.rotation = Quaternion.Euler(0f, w.w, 0f); wall.transform.localScale = new Vector3(6f, 1.2f, 0.5f);
                wall.GetComponent<Renderer>().sharedMaterial = stone;
                NotWalkable(wall);
            }
            var surface = arena.AddComponent<NavMeshSurface>();
            surface.collectObjects = CollectObjects.Children; surface.useGeometry = NavMeshCollectGeometry.RenderMeshes;
            surface.buildHeightMesh = true;          // agents stand on the real ground, not on the coarse navmesh (8 cm above it)
            surface.BuildNavMesh();
            string navPath = SceneDir + "/UndeadLegion_Extended_Demo_NavMesh.asset";
            if (File.Exists(navPath)) AssetDatabase.DeleteAsset(navPath);
            AssetDatabase.CreateAsset(surface.navMeshData, navPath);

            // camera with bloom (the glowing eyes and spells)
            var camGo = new GameObject("Main Camera"); camGo.tag = "MainCamera";
            var cam = camGo.AddComponent<Camera>(); cam.fieldOfView = 40f; cam.nearClipPlane = 0.1f; cam.farClipPlane = 200f;
            var camData = camGo.AddComponent<UniversalAdditionalCameraData>(); camData.renderPostProcessing = true; camData.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
            var rts = camGo.AddComponent<UndeadLegion.Extended.RtsCamera>(); rts.distance = 18f; rts.pitch = 48f; rts.yaw = 35f;
            string profilePath = Root + "/Materials/ExtendedDemo_Volume.asset";
            if (File.Exists(profilePath)) AssetDatabase.DeleteAsset(profilePath);
            var profile = ScriptableObject.CreateInstance<VolumeProfile>();
            AssetDatabase.CreateAsset(profile, profilePath);
            var bloom = profile.Add<Bloom>(true); bloom.threshold.Override(1.0f); bloom.intensity.Override(0.9f); bloom.scatter.Override(0.6f);
            var tone = profile.Add<Tonemapping>(true); tone.mode.Override(TonemappingMode.ACES);
            var vig = profile.Add<Vignette>(true); vig.intensity.Override(0.25f);
            foreach (var c in profile.components) AssetDatabase.AddObjectToAsset(c, profile);
            var volGo = new GameObject("Global Volume"); var vol = volGo.AddComponent<Volume>(); vol.isGlobal = true; vol.sharedProfile = profile;

            // armies
            var pfx = new List<GameObject>();
            foreach (var ch in Characters) { var p = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabDir + "/PFX_Skeleton" + ch + ".prefab"); if (p != null) pfx.Add(p); }
            var catalogue = new List<GameObject>();
            foreach (var guid in AssetDatabase.FindAssets("t:Prefab A_Skeleton", new[] { "Assets/UndeadLegion/Prefabs/Armor" }))
                catalogue.Add(AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(guid)));
            var a = Spawner("Army A (teal)", new Vector3(0f, 0f, -6f), 0f, 0, new Color(0.3f, 2.4f, 1.6f), pfx, catalogue);
            var b = Spawner("Army B (red)", new Vector3(0f, 0f, 6f), 180f, 1, new Color(2.8f, 0.35f, 0.2f), pfx, catalogue);

            var es = new GameObject("EventSystem"); es.AddComponent<EventSystem>(); es.AddComponent<DemoEventSystemBootstrap>();
            var demo = new GameObject("Extended Demo").AddComponent<UndeadLegion.Extended.ExtendedDemo>();
            demo.teamA = a; demo.teamB = b; demo.rtsCamera = rts;

            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            return ScenePath + ": armies with " + pfx.Count + " characters, " + catalogue.Count + " armour modules, navmesh " + (surface.navMeshData != null);
        }

        [MenuItem("Undead Legion/Extended/4. Build Extended Browser Scene")]
        public static string BuildShowcaseScene()
        {
            Directory.CreateDirectory(SceneDir);
            DemoSceneBuilder.Build(ShowcasePath, c => PrefabDir + "/PFX_" + c + ".prefab",
                "UNDEAD LEGION   Extended     Animation Browser     |     drag to orbit, wheel to zoom, click the skeleton to hit it", false);
            // the extended prefabs carry a NavMeshAgent: a small baked NavMesh lets it spawn quietly (the browser removes it)
            var ground = GameObject.Find("Ground");
            int built = 0;
            if (ground != null)
            {
                var surface = ground.AddComponent<NavMeshSurface>();
                surface.collectObjects = CollectObjects.Children; surface.useGeometry = NavMeshCollectGeometry.RenderMeshes; surface.buildHeightMesh = true;
                surface.BuildNavMesh();
                string navPath = SceneDir + "/UndeadLegion_Extended_Showcase_NavMesh.asset";
                if (File.Exists(navPath)) AssetDatabase.DeleteAsset(navPath);
                AssetDatabase.CreateAsset(surface.navMeshData, navPath); built = 1;
            }
            var showcase = Object.FindFirstObjectByType<SkeletonShowcase>();
            var add = showcase.gameObject.AddComponent<UndeadLegion.Extended.ExtendedShowcase>(); add.showcase = showcase;
            var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene, ShowcasePath);
            AssetDatabase.SaveAssets();
            return ShowcasePath + ": " + showcase.characters.Count + " extended characters, navmesh " + built;
        }

        static UndeadLegion.Extended.ArmySpawner Spawner(string name, Vector3 pos, float yaw, int team, Color eyes, List<GameObject> pfx, List<GameObject> catalogue)
        {
            var go = new GameObject(name); go.transform.position = pos; go.transform.rotation = Quaternion.Euler(0f, yaw, 0f);
            var s = go.AddComponent<UndeadLegion.Extended.ArmySpawner>();
            s.characters = new List<GameObject>(pfx); s.armourCatalogue = new List<GameObject>(catalogue); s.team = team; s.eyeColor = eyes;
            s.count = 8; s.columns = 4; s.spacing = 1.5f; s.enableAI = false;
            return s;
        }

        // obstacles: their tops must not become walkable islands
        static void NotWalkable(GameObject go) { var m = go.AddComponent<NavMeshModifier>(); m.overrideArea = true; m.area = 1; }

        static Light Light(string name, Color color, float intensity, LightShadows shadows, Vector3 euler)
        {
            var go = new GameObject(name); go.transform.rotation = Quaternion.Euler(euler);
            var l = go.AddComponent<Light>(); l.type = LightType.Directional; l.color = color; l.intensity = intensity; l.shadows = shadows;
            return l;
        }

        [MenuItem("Undead Legion/Extended/Build All (1-4)")]
        public static string BuildAll()
        {
            Directory.CreateDirectory(Root + "/Materials");
            var r1 = BuildController(); var r2 = BuildPrefabs(); var r3 = BuildScene(); var r4 = BuildShowcaseScene();
            return r1 + "\n" + r2 + r3 + "\n" + r4;
        }
    }
}
