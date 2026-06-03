from typing import Optional, Dict, Any, Callable, List
import ctypes
import threading
import time
import json
import os
import sys

try:
    from pynput.keyboard import Controller as KController, Key
    from pynput.mouse import Button, Controller as MController
    PYNPUT_AVAILABLE = True
    print("[Controller] pynput available for input simulation")
except Exception as e:
    PYNPUT_AVAILABLE = False
    KController = None
    Button = None
    MController = None
    Key = None
    print(f"[Controller] pynput not available: {e}")

try:
    from modules import controller
except Exception:
    controller = None

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".zt2_manager")
MAPPING_FILE = os.path.join(CONFIG_DIR, "controller_mapping.json")
MAPPING_VERSION = 7

DEFAULT_BUTTON_MAPPING: Dict[int, str] = {
    0: "space",
    1: "esc",
    2: "space",
    3: "delete",
    4: "zoom_out",
    5: "zoom_in",
    6: "tab",
    7: "f1",
    8: "none",
    9: "none",
}

DEFAULT_BUTTON_COMBO_MAPPING: Dict[str, str] = {
    "8+0": "ctrl_k",
    "8+1": "ctrl_m",
    "8+2": "ctrl_t",
    "8+3": "ctrl_h",
    "8+4": "ctrl_q",
    "8+5": "ctrl_f",
    "8+6": "ctrl_c",
    "8+7": "ctrl_p",
    "9+0": "f5",
    "9+1": "f6",
    "9+2": "f4",
    "9+3": "f3",
    "9+4": "rotate_view_ccw",
    "9+5": "rotate_view_cw",
    "9+6": "overhead_toggle",
    "9+7": "view_toggle",
    "8+9+2": "ctrl_z",
}

DEFAULT_AXIS_MAPPING: Dict[int, Dict[str, str]] = {
    0: {"negative": "left", "positive": "right"},
    1: {"negative": "up", "positive": "down"},
    2: {"negative": "none", "positive": "none"},
    3: {"negative": "none", "positive": "none"},
}

_button_mapping: Dict[int, str] = {}
_button_combo_mapping: Dict[str, str] = {}
_axis_mapping: Dict[int, Dict[str, str]] = {}

_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_active = False
_game_mode = False
_debug_mode = False

_action_callbacks: Dict[str, Callable] = {}
_ui_poll_callback: Optional[Callable] = None

AXIS_THRESHOLD = 0.5
AXIS_REPEAT_DELAY = 0.3
AXIS_REPEAT_RATE = 0.15
POLL_INTERVAL = 0.016
MOUSE_SENSITIVITY = 18.0
MOUSE_DEADZONE = 0.2

GAME_MODE_USE_ARROWS = True

_WININPUT_AVAILABLE = sys.platform == "win32"
_VK_MAP = {
    "enter": 0x0D,
    "esc": 0x1B,
    "delete": 0x2E,
    "space": 0x20,
    "tab": 0x09,
    "f1": 0x70,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "zoom_in": 0xBB,   # = / +
    "zoom_out": 0xBD,  # - / _
    "rotate_view_ccw": 0xDB,  # [
    "rotate_view_cw": 0xDD,   # ]
    "object_rotate_ccw": 0xBC,  # <
    "object_rotate_cw": 0xBE,   # >
    "overhead_toggle": 0x47,  # G
    "view_toggle": 0x43,      # C
    "ctrl_z": 0x5A,
    "ctrl_p": 0x50,
    "ctrl_f": 0x46,
    "ctrl_c": 0x43,
    "ctrl_k": 0x4B,
    "ctrl_m": 0x4D,
    "ctrl_t": 0x54,
    "ctrl_h": 0x48,
    "ctrl_q": 0x51,
}
_VK_CTRL = 0x11
_HELD_ACTIONS = {"left", "right", "up", "down", "zoom_in", "zoom_out"}
_MOUSEEVENTF_MOVE = 0x0001
_MOUSEEVENTF_LEFTDOWN = 0x0002
_MOUSEEVENTF_LEFTUP = 0x0004
_MOUSEEVENTF_RIGHTDOWN = 0x0008
_MOUSEEVENTF_RIGHTUP = 0x0010
_KEYEVENTF_KEYUP = 0x0002


def load_mapping() -> None:
    global _button_mapping, _button_combo_mapping, _axis_mapping
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.isfile(MAPPING_FILE):
            with open(MAPPING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") != MAPPING_VERSION:
                raise ValueError("old controller mapping version")
            _button_mapping = {int(k): v for k, v in data.get("buttons", {}).items()}
            _button_combo_mapping = {
                str(k): v for k, v in data.get("button_combos", {}).items()
            }
            _axis_mapping = {int(k): v for k, v in data.get("axes", {}).items()}
            for button, action in DEFAULT_BUTTON_MAPPING.items():
                _button_mapping.setdefault(button, action)
            for combo, action in DEFAULT_BUTTON_COMBO_MAPPING.items():
                _button_combo_mapping.setdefault(combo, action)
            for axis, axis_map in DEFAULT_AXIS_MAPPING.items():
                _axis_mapping.setdefault(axis, axis_map.copy())
            return
    except Exception:
        pass

    _button_mapping = DEFAULT_BUTTON_MAPPING.copy()
    _button_combo_mapping = DEFAULT_BUTTON_COMBO_MAPPING.copy()
    _axis_mapping = {k: v.copy() for k, v in DEFAULT_AXIS_MAPPING.items()}
    save_mapping()


def save_mapping() -> bool:
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        data = {
            "version": MAPPING_VERSION,
            "buttons": {str(k): v for k, v in _button_mapping.items()},
            "button_combos": _button_combo_mapping.copy(),
            "axes": {str(k): v for k, v in _axis_mapping.items()},
        }
        with open(MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def get_mapping() -> Dict[str, Any]:
    return {
        "buttons": _button_mapping.copy(),
        "button_combos": _button_combo_mapping.copy(),
        "axes": {k: v.copy() for k, v in _axis_mapping.items()},
    }


def set_mapping(buttons: Dict[int, str], axes: Dict[int, Dict[str, str]], button_combos: Optional[Dict[str, str]] = None) -> None:
    global _button_mapping, _button_combo_mapping, _axis_mapping
    _button_mapping = {int(k): v for k, v in buttons.items()}
    _button_combo_mapping = {
        str(k): v for k, v in (button_combos or DEFAULT_BUTTON_COMBO_MAPPING).items()
    }
    _axis_mapping = {int(k): v.copy() for k, v in axes.items()}


def reset_to_defaults() -> None:
    global _button_mapping, _button_combo_mapping, _axis_mapping
    _button_mapping = DEFAULT_BUTTON_MAPPING.copy()
    _button_combo_mapping = DEFAULT_BUTTON_COMBO_MAPPING.copy()
    _axis_mapping = {k: v.copy() for k, v in DEFAULT_AXIS_MAPPING.items()}


load_mapping()


def register_action_callback(action: str, callback: Callable) -> None:
    _action_callbacks[action] = callback


def unregister_action_callback(action: str) -> None:
    _action_callbacks.pop(action, None)


def clear_action_callbacks() -> None:
    _action_callbacks.clear()


def set_ui_poll_callback(callback: Optional[Callable[[Dict[str, Any]], None]]) -> None:
    global _ui_poll_callback
    _ui_poll_callback = callback


def get_pending_actions() -> List[str]:
    global _pending_actions
    if not hasattr(get_pending_actions, '_lock'):
        get_pending_actions._lock = threading.Lock()
        get_pending_actions._actions = []
    
    with get_pending_actions._lock:
        actions = get_pending_actions._actions[:]
        get_pending_actions._actions.clear()
        return actions


def _queue_action(action: str) -> None:
    if not hasattr(get_pending_actions, '_lock'):
        get_pending_actions._lock = threading.Lock()
        get_pending_actions._actions = []
    
    with get_pending_actions._lock:
        get_pending_actions._actions.append(action)


def _press_key_once(kb, action: str) -> None:
    if _send_key_once(action):
        return
    if not PYNPUT_AVAILABLE or kb is None or Key is None:
        if _debug_mode:
            print(f"[Controller] Cannot press key '{action}' - pynput unavailable")
        return
    try:
        if _debug_mode:
            print(f"[Controller] Pressing key: {action}")
        if action == "enter":
            kb.press(Key.enter); kb.release(Key.enter)
        elif action == "esc":
            kb.press(Key.esc); kb.release(Key.esc)
        elif action == "undo":
            kb.press(Key.ctrl); kb.press('z'); kb.release('z'); kb.release(Key.ctrl)
        elif action == "delete":
            kb.press(Key.delete); kb.release(Key.delete)
        elif action == "space":
            kb.press(Key.space); kb.release(Key.space)
        elif action == "tab":
            kb.press(Key.tab); kb.release(Key.tab)
        elif action == "f1":
            kb.press(Key.f1); kb.release(Key.f1)
        elif action == "zoom_in":
            kb.press('='); kb.release('=')
        elif action == "zoom_out":
            kb.press('-'); kb.release('-')
        elif action == "left":
            kb.press(Key.left); kb.release(Key.left)
        elif action == "right":
            kb.press(Key.right); kb.release(Key.right)
        elif action == "up":
            kb.press(Key.up); kb.release(Key.up)
        elif action == "down":
            kb.press(Key.down); kb.release(Key.down)
        elif action in ("f3", "f4", "f5", "f6"):
            key_attr = getattr(Key, action, None)
            if key_attr:
                kb.press(key_attr); kb.release(key_attr)
        elif action == "rotate_view_ccw":
            kb.press('['); kb.release('[')
        elif action == "rotate_view_cw":
            kb.press(']'); kb.release(']')
        elif action == "object_rotate_ccw":
            kb.press(','); kb.release(',')
        elif action == "object_rotate_cw":
            kb.press('.'); kb.release('.')
        elif action == "overhead_toggle":
            kb.press('g'); kb.release('g')
        elif action == "view_toggle":
            kb.press('c'); kb.release('c')
        elif action.startswith("ctrl_"):
            key = action.split("_", 1)[1]
            kb.press(Key.ctrl); kb.press(key); kb.release(key); kb.release(Key.ctrl)
    except Exception as e:
        if _debug_mode:
            print(f"[Controller] Key press error: {e}")


def _send_key_event(action: str, down: bool) -> bool:
    if not _WININPUT_AVAILABLE:
        return False
    vk = _VK_MAP.get(action)
    if vk is None:
        return False
    try:
        flags = 0 if down else _KEYEVENTF_KEYUP
        ctypes.windll.user32.keybd_event(vk, 0, flags, 0)
        return True
    except Exception as e:
        if _debug_mode:
            print(f"[Controller] Win32 key event failed for {action}: {e}")
        return False


def _send_key_once(action: str) -> bool:
    if action.startswith("ctrl_"):
        if not _WININPUT_AVAILABLE:
            return False
        vk = _VK_MAP.get(action)
        if vk is None:
            return False
        try:
            ctypes.windll.user32.keybd_event(_VK_CTRL, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.01)
            ctypes.windll.user32.keybd_event(vk, 0, _KEYEVENTF_KEYUP, 0)
            ctypes.windll.user32.keybd_event(_VK_CTRL, 0, _KEYEVENTF_KEYUP, 0)
            return True
        except Exception as e:
            if _debug_mode:
                print(f"[Controller] Win32 ctrl key event failed for {action}: {e}")
            return False

    if not _send_key_event(action, True):
        return False
    time.sleep(0.01)
    _send_key_event(action, False)
    return True


def _set_held_action(action: str, active: bool, held_actions: Dict[str, bool], kb=None) -> None:
    if action is None or action == "none":
        return
    if action not in _HELD_ACTIONS:
        if active and not held_actions.get(action, False):
            _trigger_action(action, True, kb)
            held_actions[action] = True
        elif not active:
            held_actions[action] = False
        return

    already_down = held_actions.get(action, False)
    if active and not already_down:
        if not _send_key_event(action, True) and kb is not None:
            _press_key_once(kb, action)
        held_actions[action] = True
    elif not active and already_down:
        _send_key_event(action, False)
        held_actions[action] = False


def _release_held_inputs(held_actions: Dict[str, bool], mouse_buttons: Dict[str, bool]) -> None:
    for action, active in list(held_actions.items()):
        if active:
            _send_key_event(action, False)
            held_actions[action] = False
    if mouse_buttons.get("left"):
        _send_mouse_button("left", False)
        mouse_buttons["left"] = False
    if mouse_buttons.get("right"):
        _send_mouse_button("right", False)
        mouse_buttons["right"] = False


def _move_mouse(dx: int, dy: int, mouse=None) -> None:
    if dx == 0 and dy == 0:
        return
    if _WININPUT_AVAILABLE:
        try:
            ctypes.windll.user32.mouse_event(_MOUSEEVENTF_MOVE, dx, dy, 0, 0)
            return
        except Exception:
            pass
    if mouse is not None:
        try:
            mouse.move(dx, dy)
        except Exception:
            pass


def _send_mouse_button(button: str, down: bool, mouse=None) -> bool:
    if _WININPUT_AVAILABLE:
        try:
            if button == "left":
                flag = _MOUSEEVENTF_LEFTDOWN if down else _MOUSEEVENTF_LEFTUP
            else:
                flag = _MOUSEEVENTF_RIGHTDOWN if down else _MOUSEEVENTF_RIGHTUP
            ctypes.windll.user32.mouse_event(flag, 0, 0, 0, 0)
            return True
        except Exception:
            pass
    if mouse is not None and Button is not None:
        try:
            btn = Button.left if button == "left" else Button.right
            if down:
                mouse.press(btn)
            else:
                mouse.release(btn)
            return True
        except Exception:
            pass
    return False


def _trigger_action(action: str, use_pynput: bool = False, kb=None) -> None:
    if action in _action_callbacks and not use_pynput:
        # Queue for main thread to execute
        _queue_action(action)
    elif use_pynput and kb is not None:
        _press_key_once(kb, action)
    elif _debug_mode:
        print(f"[Controller] Action '{action}' not handled (pynput={use_pynput}, kb={kb is not None})")


def set_debug_mode(enabled: bool) -> None:
    global _debug_mode
    _debug_mode = enabled
    print(f"[Controller] Debug mode: {'enabled' if enabled else 'disabled'}")


def _map_loop(proc, force_game_mode: bool = False) -> None:
    global _active, _game_mode
    
    kb = None
    mouse = None
    if PYNPUT_AVAILABLE and KController and MController:
        try:
            kb = KController()
            mouse = MController()
            print("[Controller] pynput keyboard/mouse controllers initialized")
        except Exception as e:
            print(f"[Controller] Failed to initialize pynput: {e}")
            kb = None
            mouse = None

    axis_state = {
        "left": {"active": False, "start_time": 0, "last_repeat": 0},
        "right": {"active": False, "start_time": 0, "last_repeat": 0},
        "up": {"active": False, "start_time": 0, "last_repeat": 0},
        "down": {"active": False, "start_time": 0, "last_repeat": 0},
    }
    dpad_state = {"left": False, "right": False, "up": False, "down": False}
    buttons_prev: list = []
    held_actions: Dict[str, bool] = {}
    mouse_buttons = {"left": False, "right": False}
    combo_buttons = sorted({
        tuple(int(part) for part in combo.split("+")): action
        for combo, action in _button_combo_mapping.items()
        if action and action != "none" and "+" in combo
    }.items(), key=lambda item: len(item[0]), reverse=True)

    _active = True
    _game_mode = bool(proc) or bool(force_game_mode)
    
    print(f"[Controller] Mapping started - game_mode={_game_mode}, pynput={PYNPUT_AVAILABLE}")
    
    poll_count = 0
    last_state_log = 0
    
    try:
        while not _stop_event.is_set():
            if proc and proc.poll() is not None:
                print("[Controller] Game process exited, stopping mapper")
                break

            state = {}
            connected = False
            try:
                if controller:
                    connected = controller.is_connected()
                    if connected:
                        state = controller.get_state()
            except Exception as e:
                if _debug_mode:
                    print(f"[Controller] Error getting state: {e}")
                state = {}

            if not connected:
                time.sleep(0.1)
                continue

            axes = state.get("axes", [])
            buttons = state.get("buttons", [])
            hats = state.get("hats", [])
            triggered_actions = []
            
            now = time.time()
            poll_count += 1
            
            if _debug_mode and now - last_state_log > 1.0:
                print(f"[Controller] State - axes:{[round(a,2) for a in axes[:4]]} buttons:{buttons[:10]} hats:{hats}")
                last_state_log = now

            h = axes[0] if len(axes) > 0 else 0.0  # Left stick X
            v = axes[1] if len(axes) > 1 else 0.0  # Left stick Y
            rh = axes[2] if len(axes) > 2 else 0.0  # Right stick X
            rv = axes[3] if len(axes) > 3 else 0.0  # Right stick Y
            lt = (axes[4] + 1.0) / 2.0 if len(axes) > 4 else 0.0
            rt = (axes[5] + 1.0) / 2.0 if len(axes) > 5 else 0.0

            in_game = bool(proc) or bool(force_game_mode)

            if hats:
                hat = hats[0]
                if isinstance(hat, (tuple, list)) and len(hat) >= 2:
                    hat_x, hat_y = hat[0], hat[1]

                    dpad_actions = {
                        "left": hat_x < 0,
                        "right": hat_x > 0,
                        "up": hat_y > 0,
                        "down": hat_y < 0,
                    }
                    dpad_modifier = None
                    if in_game and len(buttons) > 8 and buttons[8]:
                        dpad_modifier = {
                            "left": "object_rotate_ccw",
                            "right": "object_rotate_cw",
                            "up": "ctrl_k",
                            "down": "ctrl_m",
                        }
                    elif in_game and len(buttons) > 9 and buttons[9]:
                        dpad_modifier = {
                            "left": "rotate_view_ccw",
                            "right": "rotate_view_cw",
                            "up": "overhead_toggle",
                            "down": "view_toggle",
                        }

                    for action, pressed in dpad_actions.items():
                        if in_game and dpad_modifier:
                            mapped_action = dpad_modifier.get(action)
                            if pressed and not dpad_state[action] and mapped_action:
                                dpad_state[action] = True
                                triggered_actions.append(mapped_action)
                                _trigger_action(mapped_action, True, kb)
                            elif not pressed:
                                dpad_state[action] = False
                        elif in_game:
                            _set_held_action(action, pressed, held_actions, kb)
                            if pressed:
                                triggered_actions.append(action)
                        elif pressed and not dpad_state[action]:
                            dpad_state[action] = True
                            triggered_actions.append(action)
                            _trigger_action(action, False, kb)
                        elif not pressed:
                            dpad_state[action] = False

            h_map = _axis_mapping.get(0, DEFAULT_AXIS_MAPPING.get(0, {}))
            v_map = _axis_mapping.get(1, DEFAULT_AXIS_MAPPING.get(1, {}))

            def check_axis_action(value: float, threshold: float, action: str, positive: bool):
                if action is None or action == "none":
                    return
                
                is_active = (value > threshold) if positive else (value < -threshold)
                if in_game:
                    _set_held_action(action, is_active, held_actions, kb)
                    if is_active:
                        triggered_actions.append(action)
                    return

                state_info = axis_state.get(action, {"active": False, "start_time": 0, "last_repeat": 0})
                
                if is_active:
                    if not state_info["active"]:
                        state_info["active"] = True
                        state_info["start_time"] = now
                        state_info["last_repeat"] = now
                        triggered_actions.append(action)
                        _trigger_action(action, in_game, kb)
                    else:
                        held_time = now - state_info["start_time"]
                        if held_time >= AXIS_REPEAT_DELAY:
                            time_since_repeat = now - state_info["last_repeat"]
                            if time_since_repeat >= AXIS_REPEAT_RATE:
                                state_info["last_repeat"] = now
                                triggered_actions.append(action)
                                _trigger_action(action, in_game, kb)
                else:
                    state_info["active"] = False
                
                axis_state[action] = state_info

            check_axis_action(h, AXIS_THRESHOLD, h_map.get("negative"), False)
            check_axis_action(h, AXIS_THRESHOLD, h_map.get("positive"), True)
            check_axis_action(v, AXIS_THRESHOLD, v_map.get("negative"), False)
            check_axis_action(v, AXIS_THRESHOLD, v_map.get("positive"), True)

            if in_game:
                dx = int(rh * MOUSE_SENSITIVITY) if abs(rh) > MOUSE_DEADZONE else 0
                dy = int(rv * MOUSE_SENSITIVITY) if abs(rv) > MOUSE_DEADZONE else 0
                _move_mouse(dx, dy, mouse)

                left_active = rt > 0.35
                right_active = lt > 0.35
                if left_active != mouse_buttons["left"]:
                    _send_mouse_button("left", left_active, mouse)
                    mouse_buttons["left"] = left_active
                if right_active != mouse_buttons["right"]:
                    _send_mouse_button("right", right_active, mouse)
                    mouse_buttons["right"] = right_active

            combo_used_edges = set()
            for combo, action in combo_buttons:
                if not all(i < len(buttons) and buttons[i] for i in combo):
                    continue
                newly_pressed = [
                    i for i in combo
                    if buttons[i] and not (buttons_prev[i] if i < len(buttons_prev) else False)
                ]
                if newly_pressed and not any(i in combo_used_edges for i in newly_pressed):
                    combo_used_edges.update(newly_pressed)
                    if _debug_mode:
                        print(f"[Controller] Combo {combo} pressed -> action '{action}'")
                    triggered_actions.append(action)
                    _trigger_action(action, in_game, kb)

            for i, pressed in enumerate(buttons):
                prev = buttons_prev[i] if i < len(buttons_prev) else False
                if pressed and not prev and i not in combo_used_edges:
                    action = _button_mapping.get(i)
                    if action and action != "none":
                        if _debug_mode:
                            print(f"[Controller] Button {i} pressed -> action '{action}'")
                        triggered_actions.append(action)
                        _trigger_action(action, in_game, kb)

            buttons_prev = buttons[:]

            if _ui_poll_callback:
                try:
                    _ui_poll_callback({
                        "axes": axes,
                        "buttons": buttons,
                        "hats": hats,
                        "actions": triggered_actions,
                    })
                except Exception:
                    pass

            time.sleep(POLL_INTERVAL)
    except Exception as e:
        print(f"[Controller] Map loop error: {e}")
    finally:
        _release_held_inputs(held_actions, mouse_buttons)
        print("[Controller] Mapping stopped")
        _active = False
        _game_mode = False


def start_mapping(proc=None, force_game_mode: bool = False) -> bool:
    global _thread, _stop_event
    if _thread and _thread.is_alive():
        print("[Controller] Mapper already running")
        return False
    
    if controller:
        try:
            controller.initialize()
            if controller.is_connected():
                info = controller.get_joystick_info()
                print(f"[Controller] Connected: {info.get('name', 'Unknown')} "
                      f"({info.get('num_axes', 0)} axes, {info.get('num_buttons', 0)} buttons, "
                      f"{info.get('num_hats', 0)} hats)")
            else:
                print("[Controller] No controller connected")
        except Exception as e:
            print(f"[Controller] Init error: {e}")
    
    _stop_event.clear()
    _thread = threading.Thread(target=_map_loop, args=(proc, force_game_mode), daemon=True)
    _thread.start()
    return True


def stop_mapping() -> None:
    global _stop_event, _thread
    _stop_event.set()
    if _thread:
        _thread.join(timeout=1.0)
    _thread = None
    print("[Controller] Mapper stopped")


def is_active() -> bool:
    return _active


def is_game_mode() -> bool:
    return _game_mode


def test_controller(duration: float = 5.0) -> Dict[str, Any]:
    if not controller:
        return {"error": "Controller module not available"}
    
    try:
        controller.initialize()
    except Exception as e:
        return {"error": f"Failed to initialize: {e}"}
    
    if not controller.is_connected():
        return {"error": "No controller connected"}
    
    info = controller.get_joystick_info()
    results = {
        "controller": info.get("name", "Unknown"),
        "num_axes": info.get("num_axes", 0),
        "num_buttons": info.get("num_buttons", 0),
        "num_hats": info.get("num_hats", 0),
        "button_presses": [],
        "axis_ranges": {},
        "hat_values": set(),
    }
    
    print(f"[Controller Test] Testing {info.get('name')} for {duration}s...")
    print("[Controller Test] Press buttons and move sticks/d-pad")
    
    start = time.time()
    while time.time() - start < duration:
        state = controller.get_state()
        
        for i, pressed in enumerate(state.get("buttons", [])):
            if pressed and i not in results["button_presses"]:
                results["button_presses"].append(i)
                print(f"  Button {i} pressed")
        
        for i, val in enumerate(state.get("axes", [])):
            if i not in results["axis_ranges"]:
                results["axis_ranges"][i] = {"min": val, "max": val}
            results["axis_ranges"][i]["min"] = min(results["axis_ranges"][i]["min"], val)
            results["axis_ranges"][i]["max"] = max(results["axis_ranges"][i]["max"], val)
        
        for hat in state.get("hats", []):
            results["hat_values"].add(str(hat))
        
        time.sleep(0.05)
    
    results["hat_values"] = list(results["hat_values"])
    print(f"[Controller Test] Complete: {results}")
    return results


def status() -> Dict[str, Any]:
    connected = False
    info = {}
    if controller:
        try:
            connected = controller.is_connected()
            if connected:
                info = controller.get_joystick_info()
        except Exception:
            pass
    
    return {
        "pynput_available": PYNPUT_AVAILABLE,
        "controller_present": controller is not None,
        "controller_connected": connected,
        "controller_info": info,
        "mapper_active": _active,
        "game_mode": _game_mode,
        "debug_mode": _debug_mode,
        "callbacks_registered": len(_action_callbacks),
        "button_mapping": _button_mapping.copy(),
        "button_combo_mapping": _button_combo_mapping.copy(),
    }
