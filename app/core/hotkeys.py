"""Global hotkeys via a low-level keyboard hook (works in fullscreen games).

``RegisterHotKey`` is ignored by some games/overlays, and polling
``GetAsyncKeyState`` from a Qt timer is throttled while another process owns the
foreground.  A ``WH_KEYBOARD_LL`` hook sees every key before the focused window
does - the same mechanism macro tools like AutoHotkey use.

The hook callback only compares the virtual key code and emits a Qt signal, so
it stays fast.  It is removed in :meth:`HotkeyManager.clear` (called on shutdown)
to avoid touching Python during interpreter finalisation.
"""

from __future__ import annotations

import ctypes
import os
import threading
import time
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal

from .keymap import KEYS

MODIFIER_VK = {"ctrl": 0x11, "alt": 0x12, "shift": 0x10, "windows": 0x5B}
MODIFIER_ORDER = ("ctrl", "alt", "shift", "windows")

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

POLL_MS = 18

_user32 = ctypes.windll.user32 if os.name == "nt" else None


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


if _user32 is not None:
    _HOOKPROC = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
    _user32.SetWindowsHookExW.restype = ctypes.c_void_p
    _user32.SetWindowsHookExW.argtypes = [
        ctypes.c_int, _HOOKPROC, ctypes.c_void_p, wintypes.DWORD]
    _user32.CallNextHookEx.restype = ctypes.c_ssize_t
    _user32.CallNextHookEx.argtypes = [
        ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
    _user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    _user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
else:  # pragma: no cover - only on non-Windows
    _HOOKPROC = None


def backend_available() -> bool:
    return _user32 is not None


def _is_down(vk: int) -> bool:
    if _user32 is None:
        return False
    return bool(_user32.GetAsyncKeyState(vk) & 0x8000)


def _vk_for(name: str) -> int | None:
    name = name.strip().lower()
    if name in MODIFIER_VK:
        return MODIFIER_VK[name]
    definition = KEYS.get(name)
    return definition.vk if definition else None


def _parse_combo(combo: str) -> tuple[frozenset[str], str] | None:
    parts = [part.strip().lower() for part in combo.split("+") if part.strip()]
    if not parts:
        return None
    key = parts[-1]
    modifiers = frozenset(part for part in parts[:-1] if part in MODIFIER_VK)
    if _vk_for(key) is None:
        return None
    return modifiers, key


class HotkeyManager(QObject):
    """Installs one keyboard hook and emits the action bound to a combination."""

    triggered = Signal(str)
    error = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._hook: int | None = None
        self._proc = None
        self._mods: set[str] = set()
        self._reverse: dict[int, list[tuple[frozenset[str], str]]] = {}
        self._bindings: dict[tuple[frozenset[str], str], str] = {}
        self._suspended = False

    # ------------------------------------------------------------------
    def _ensure_hook(self) -> bool:
        if _user32 is None or _HOOKPROC is None:
            return False
        if os.environ.get("HD2SS_NO_HOOKS") == "1":
            return True  # tests / --safe: never install a global hook
        if self._hook:
            return True

        def callback(n_code, w_param, l_param):
            try:
                if n_code == 0:
                    info = ctypes.cast(
                        l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    message = int(w_param)
                    self._handle_key(
                        int(info.vkCode),
                        message in (WM_KEYDOWN, WM_SYSKEYDOWN),
                    )
            except Exception:  # noqa: BLE001 - never break the hook chain
                pass
            return _user32.CallNextHookEx(None, n_code, w_param, l_param)

        self._proc = _HOOKPROC(callback)
        self._hook = _user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        return bool(self._hook)

    def _handle_key(self, vk: int, down: bool) -> None:
        for name, modifier_vk in MODIFIER_VK.items():
            if vk == modifier_vk:
                if down:
                    self._mods.add(name)
                else:
                    self._mods.discard(name)
                return
        if not down:
            return
        held = frozenset(self._mods)
        for modifiers, action in self._reverse.get(vk, []):
            if modifiers == held:
                if self._suspended:
                    return
                from .. import diagnostics

                diagnostics.macro_log(f"hotkey pressed: {action}")
                self.triggered.emit(action)
                return

    # ------------------------------------------------------------------
    def apply(self, bindings: dict[str, str]) -> list[str]:
        self.clear()
        if _user32 is None:
            return ["Globale Hotkeys sind nicht verfügbar (nur unter Windows)."]
        errors: list[str] = []
        for action, combo in bindings.items():
            parsed = _parse_combo(combo or "")
            if parsed is None:
                if (combo or "").strip():
                    errors.append(f"{combo}: unbekannte Taste")
                continue
            modifiers, key = parsed
            vk = _vk_for(key)
            if vk is None:
                continue
            self._reverse.setdefault(vk, []).append((modifiers, action))
            self._bindings[(modifiers, key)] = action
        if self._bindings and not self._ensure_hook():
            errors.append("Globaler Tastatur-Hook konnte nicht installiert werden.")
        return errors

    def suspend(self, value: bool) -> None:
        """Ignore keys while a macro is being sent (avoids self-triggering)."""
        self._suspended = value

    def clear(self) -> None:
        if _user32 is not None and self._hook:
            try:
                _user32.UnhookWindowsHookEx(self._hook)
            except Exception:  # noqa: BLE001
                pass
        self._hook = None
        self._proc = None
        self._reverse = {}
        self._bindings = {}
        self._mods = set()

    @property
    def bindings(self) -> dict[str, str]:
        return {"+".join([*sorted(mods, key=MODIFIER_ORDER.index), key]): action
                for (mods, key), action in self._bindings.items()}


class PushToTalk(QObject):
    """Emits pressed/released for one key, with auto-repeat filtered out.

    Polling runs in a small background thread: Windows throttles Qt timers of
    background processes, which made the key look "never pressed" while a
    fullscreen game had focus.
    """

    pressed = Signal()
    released = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._key = ""
        self._vk = 0
        self._down = False
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def bind(self, key: str, threaded: bool = True) -> list[str]:
        self.unbind()
        key = (key or "").strip().lower()
        if not key:
            return []
        vk = _vk_for(key)
        if vk is None:
            return [f"PTT-Taste {key}: unbekannte Taste"]
        self._key = key
        self._vk = vk
        if threaded and _user32 is not None:
            self._stop = threading.Event()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        return []

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._tick()
            time.sleep(0.01)

    def _tick(self) -> None:
        down = _is_down(self._vk)
        if down and not self._down:
            self._down = True
            self.pressed.emit()
        elif not down and self._down:
            self._down = False
            self.released.emit()

    def unbind(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=0.2)
            self._thread = None
        self._key = ""
        self._vk = 0
        self._down = False


CAPTURE_KEYS = list(KEYS)


class KeyCapture(QObject):
    """Grabs the next key combination pressed, for the hotkey editors."""

    captured = Signal(str)
    cancelled = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._down: set[str] = set()
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._tick)
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self.cancel)

    def start(self, timeout_ms: int = 6000) -> None:
        self._down = set()
        if _user32 is None:
            self.cancelled.emit()
            return
        self._timer.start()
        self._timeout.start(timeout_ms)

    def _tick(self) -> None:
        for name in MODIFIER_ORDER:
            vk = MODIFIER_VK[name]
            down = _is_down(vk)
            if down:
                self._down.add(name)
            else:
                self._down.discard(name)
        for name in CAPTURE_KEYS:
            vk = KEYS[name].vk
            if _is_down(vk) and name not in self._down:
                self._down.add(name)
                combo = "+".join(
                    [*sorted(self._down & set(MODIFIER_ORDER), key=MODIFIER_ORDER.index), name]
                )
                self._stop()
                self.captured.emit(combo)
                return

    def cancel(self) -> None:
        self._stop()
        self.cancelled.emit()

    def _stop(self) -> None:
        self._timer.stop()
        self._timeout.stop()
        self._down = set()


def shutdown() -> None:
    """The hook is removed by HotkeyManager.clear()."""
