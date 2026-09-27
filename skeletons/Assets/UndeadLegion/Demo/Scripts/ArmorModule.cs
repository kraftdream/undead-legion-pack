using System.Collections.Generic;
using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// An armour module shipped as its own asset (2026-09-27, the modular route): `Models/Armor/&lt;Character&gt;/
    /// SK_&lt;Character&gt;_&lt;Module&gt;.fbx` is that one skinned mesh with the shared skeleton, and the prefab
    /// `Prefabs/Armor/&lt;Character&gt;/A_&lt;Character&gt;_&lt;Module&gt;.prefab` carries it with its material and this component.
    /// Dropped in a scene it shows the piece in its rest pose on its own bones (a prop).
    /// <see cref="Attach"/> puts it on ANY of the six characters: every module is skinned to the one shared rig
    /// and every character exports the same 68-bone hierarchy, so the renderer's bone array is rebuilt by bone
    /// NAME against the character's bones, the root bone likewise, the mesh reparented under the character and
    /// the module's own skeleton discarded. The piece then follows whatever the character plays, in the editor
    /// (the prefab builder dresses each character with its default set) and at runtime (the demo swaps pieces).
    /// </summary>
    [DisallowMultipleComponent]
    public class ArmorModule : MonoBehaviour
    {
        [Tooltip("The character this piece was modelled for (its armour material and default set).")]
        public string character;
        [Tooltip("The piece: Helm, Chest, Glove_L, Boot_R, Skirt, Robe, ...")]
        public string moduleName;

        /// <summary>Attach this module instance to a character: returns the piece's renderer GameObject, now a
        /// child of `modulesParent` (or the character root) and skinned to the character's bones; the module's
        /// own root (this GameObject, with its skeleton) is destroyed. Null if the character has no body renderer
        /// or a bone is missing.</summary>
        public GameObject Attach(GameObject characterRoot, Transform modulesParent = null)
        {
            var body = FindBody(characterRoot);
            if (body == null) { Debug.LogWarning("ArmorModule: no Body renderer on " + characterRoot.name, this); return null; }
            var mine = GetComponentInChildren<SkinnedMeshRenderer>(true);
            if (mine == null) { Debug.LogWarning("ArmorModule: no skinned mesh on " + name, this); return null; }

            // the character's bones by name (its whole Armature hierarchy: the sockets and helpers included)
            var byName = new Dictionary<string, Transform>();
            Transform armature = null;
            foreach (var t in characterRoot.GetComponentsInChildren<Transform>(true))
                if (t.name == "Armature" && armature == null) armature = t;
            var scan = armature != null ? armature : body.rootBone != null ? body.rootBone.root : characterRoot.transform;
            foreach (var t in scan.GetComponentsInChildren<Transform>(true)) if (!byName.ContainsKey(t.name)) byName[t.name] = t;
            foreach (var t in body.bones) if (t != null) byName[t.name] = t;

            var bones = mine.bones; var mapped = new Transform[bones.Length];
            for (int i = 0; i < bones.Length; i++)
            {
                Transform t; string bn = bones[i] != null ? bones[i].name : null;
                if (bn == null || !byName.TryGetValue(bn, out t)) { Debug.LogWarning("ArmorModule: bone '" + bn + "' of " + name + " not found on " + characterRoot.name, this); return null; }
                mapped[i] = t;
            }
            Transform root;
            if (mine.rootBone == null || !byName.TryGetValue(mine.rootBone.name, out root)) root = body.rootBone;

            var piece = mine.gameObject;
            piece.transform.SetParent(modulesParent != null ? modulesParent : (body.transform.parent != null ? body.transform.parent : characterRoot.transform), false);
            piece.transform.localPosition = Vector3.zero; piece.transform.localRotation = Quaternion.identity; piece.transform.localScale = Vector3.one;
            piece.name = moduleName;
            mine.bones = mapped;
            mine.rootBone = root;
            mine.localBounds = body.localBounds;
            mine.updateWhenOffscreen = true;

            var marker = piece.GetComponent<ArmorPiece>();
            if (marker == null) marker = piece.AddComponent<ArmorPiece>();
            marker.character = character; marker.moduleName = moduleName;

            if (Application.isPlaying) Destroy(gameObject); else DestroyImmediate(gameObject);
            return piece;
        }

        /// <summary>Instantiate a module prefab and attach it in one go (editor or play mode).</summary>
        public static GameObject Wear(GameObject modulePrefab, GameObject characterRoot, Transform modulesParent = null)
        {
            if (modulePrefab == null || characterRoot == null) return null;
            var inst = Instantiate(modulePrefab);
            inst.name = modulePrefab.name;
            var mod = inst.GetComponent<ArmorModule>();
            if (mod == null) { Debug.LogWarning("ArmorModule.Wear: " + modulePrefab.name + " has no ArmorModule", modulePrefab); if (Application.isPlaying) Destroy(inst); else DestroyImmediate(inst); return null; }
            var piece = mod.Attach(characterRoot, modulesParent);
            if (piece != null) { var m = piece.GetComponent<ArmorPiece>(); if (m != null) m.sourcePrefab = modulePrefab; }
            return piece;
        }

        public static SkinnedMeshRenderer FindBody(GameObject characterRoot, string bodyName = "Body")
        {
            foreach (var r in characterRoot.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                if (r.name == bodyName) return r;
            return null;
        }
    }
}
