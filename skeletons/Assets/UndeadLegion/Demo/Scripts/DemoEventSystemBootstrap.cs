using UnityEngine;
using UnityEngine.EventSystems;

namespace UndeadLegion.Demo
{
    /// <summary>
    /// Attaches the input module that matches whatever input backend the project is set to.
    ///
    /// A demo scene's EventSystem is normally saved with one specific module:
    /// StandaloneInputModule throws if the project is set to "Input System Package (New)"
    /// only, and InputSystemUIInputModule does not exist if the Input System package is
    /// absent. Either way the demo's buttons silently stop working for a share of buyers.
    /// Picking the module at runtime behind the compiler defines avoids both failures.
    /// </summary>
    [RequireComponent(typeof(EventSystem))]
    [DefaultExecutionOrder(-100)]
    public class DemoEventSystemBootstrap : MonoBehaviour
    {
        void Awake()
        {
#if ENABLE_INPUT_SYSTEM
            if (GetComponent<UnityEngine.InputSystem.UI.InputSystemUIInputModule>() == null)
            {
                var legacy = GetComponent<StandaloneInputModule>();
                if (legacy != null) Destroy(legacy);
                gameObject.AddComponent<UnityEngine.InputSystem.UI.InputSystemUIInputModule>();
            }
#else
            if (GetComponent<StandaloneInputModule>() == null)
                gameObject.AddComponent<StandaloneInputModule>();
#endif
        }
    }
}
