using UnityEngine;

namespace UndeadLegion.Demo
{
    /// <summary>Marks a worn piece on a character: which prefab it came from (so the demo can toggle it) and its
    /// identity. Placed by <see cref="ArmorModule.Attach"/>.</summary>
    public class ArmorPiece : MonoBehaviour
    {
        public string character;
        public string moduleName;
        public GameObject sourcePrefab;
    }
}
