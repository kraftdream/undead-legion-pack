using UnityEngine;
using UnityEngine.EventSystems;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace UndeadLegion.Extended
{
    /// <summary>Mouse and keyboard reads that work with either input backend (Input System or the legacy Input Manager).</summary>
    public static class ExtendedInput
    {
        public static Vector2 MousePosition
        {
            get
            {
#if ENABLE_INPUT_SYSTEM
                return Mouse.current != null ? Mouse.current.position.ReadValue() : Vector2.zero;
#else
                return Input.mousePosition;
#endif
            }
        }

        public static Vector2 MouseDelta
        {
            get
            {
#if ENABLE_INPUT_SYSTEM
                return Mouse.current != null ? Mouse.current.delta.ReadValue() : Vector2.zero;
#else
                return new Vector2(Input.GetAxis("Mouse X"), Input.GetAxis("Mouse Y")) * 10f;
#endif
            }
        }

        public static float Scroll
        {
            get
            {
#if ENABLE_INPUT_SYSTEM
                if (Mouse.current == null) return 0f;
                float raw = Mouse.current.scroll.ReadValue().y;
                return Mathf.Abs(raw) >= 10f ? raw / 120f : raw;
#else
                return Input.mouseScrollDelta.y;
#endif
            }
        }

        /// <summary>0 left, 1 right, 2 middle.</summary>
        public static bool ButtonDown(int b)
        {
#if ENABLE_INPUT_SYSTEM
            var m = Mouse.current; if (m == null) return false;
            return b == 0 ? m.leftButton.wasPressedThisFrame : b == 1 ? m.rightButton.wasPressedThisFrame : m.middleButton.wasPressedThisFrame;
#else
            return Input.GetMouseButtonDown(b);
#endif
        }

        public static bool Button(int b)
        {
#if ENABLE_INPUT_SYSTEM
            var m = Mouse.current; if (m == null) return false;
            return b == 0 ? m.leftButton.isPressed : b == 1 ? m.rightButton.isPressed : m.middleButton.isPressed;
#else
            return Input.GetMouseButton(b);
#endif
        }

        public static bool Key(KeyCode k)
        {
#if ENABLE_INPUT_SYSTEM
            var kb = Keyboard.current; if (kb == null) return false;
            switch (k)
            {
                case KeyCode.W: return kb.wKey.isPressed; case KeyCode.A: return kb.aKey.isPressed;
                case KeyCode.S: return kb.sKey.isPressed; case KeyCode.D: return kb.dKey.isPressed;
                case KeyCode.Q: return kb.qKey.isPressed; case KeyCode.E: return kb.eKey.isPressed;
                case KeyCode.UpArrow: return kb.upArrowKey.isPressed; case KeyCode.DownArrow: return kb.downArrowKey.isPressed;
                case KeyCode.LeftArrow: return kb.leftArrowKey.isPressed; case KeyCode.RightArrow: return kb.rightArrowKey.isPressed;
                case KeyCode.LeftShift: return kb.leftShiftKey.isPressed || kb.rightShiftKey.isPressed;
                case KeyCode.LeftControl: return kb.leftCtrlKey.isPressed || kb.rightCtrlKey.isPressed;
                case KeyCode.LeftAlt: return kb.leftAltKey.isPressed || kb.rightAltKey.isPressed;
            }
            return false;
#else
            if (k == KeyCode.LeftShift) return Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift);
            if (k == KeyCode.LeftControl) return Input.GetKey(KeyCode.LeftControl) || Input.GetKey(KeyCode.RightControl);
            if (k == KeyCode.LeftAlt) return Input.GetKey(KeyCode.LeftAlt) || Input.GetKey(KeyCode.RightAlt);
            return Input.GetKey(k);
#endif
        }

        /// <summary>A key pressed this frame (Escape, Space, Tab, the letters and digits; Shift / Ctrl / Alt as held keys).</summary>
        public static bool KeyDown(KeyCode k)
        {
#if ENABLE_INPUT_SYSTEM
            var kb = Keyboard.current; if (kb == null) return false;
            var key = ToKey(k);
            return key != UnityEngine.InputSystem.Key.None && kb[key].wasPressedThisFrame;
#else
            return Input.GetKeyDown(k);
#endif
        }

#if ENABLE_INPUT_SYSTEM
        static UnityEngine.InputSystem.Key ToKey(KeyCode k)
        {
            if (k == KeyCode.Escape) return UnityEngine.InputSystem.Key.Escape;
            if (k == KeyCode.Space) return UnityEngine.InputSystem.Key.Space;
            if (k == KeyCode.Tab) return UnityEngine.InputSystem.Key.Tab;
            if (k == KeyCode.Return) return UnityEngine.InputSystem.Key.Enter;
            if (k >= KeyCode.A && k <= KeyCode.Z) return UnityEngine.InputSystem.Key.A + (k - KeyCode.A);
            if (k >= KeyCode.Alpha1 && k <= KeyCode.Alpha9) return UnityEngine.InputSystem.Key.Digit1 + (k - KeyCode.Alpha1);
            if (k == KeyCode.Alpha0) return UnityEngine.InputSystem.Key.Digit0;
            return UnityEngine.InputSystem.Key.None;
        }
#endif

        public static bool PointerOverUI { get { return EventSystem.current != null && EventSystem.current.IsPointerOverGameObject(); } }
    }
}
