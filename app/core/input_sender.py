"""Sending keystrokes to the game and running stratagem macros off the UI thread.

The game reads raw keyboard input, so the macro engine uses ``SendInput`` with
scan codes.  Virtual-key mode is available as a fallback for unusual layouts.
"""

from __future__ import annotations

import ctypes
import os
import threading
import time
from typing import Callable, Iterable

from PySide6.QtCore import QObject, Signal

from .keymap import DIRECTION_SCHEMES, KEYS, KeyDef
from .models import MacroSettings, Stratagem

INPUT_KEYBOARD = 1
INPUT_MOUSE = 0
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_ulong), ("u", _INPUTUNION)]


def _send_input(*inputs: _INPUT) -> None:
    if os.name != "nt":
        raise OSError("SendInput is only available on Windows")
    amount = len(inputs)
    array = (_INPUT * amount)(*inputs)
    sent = ctypes.windll.user32.SendInput(amount, array, ctypes.sizeof(_INPUT))
    if sent != amount:
        raise OSError(f"SendInput failed (sent {sent}/{amount})")


class MacroSender:
    """Low level key/mouse emitter with a dry-run mode for tests and previews."""

    def __init__(self, mode: str = "scancode", dry_run: bool = False,
                 event_cb: Callable[[str], None] | None = None):
        self.mode = mode
        self.dry_run = dry_run
        self.event_cb = event_cb

    def key(self, name: str, down: bool) -> None:
        name = name.lower()
        definition = KEYS.get(name)
        if definition is None:
            raise KeyError(f"unknown key: {name}")
        if self.event_cb:
            self.event_cb(name if down else f"-{name}")
        if self.dry_run:
            return
        _send_input(self._keyboard_input(definition, down))

    def click(self, button: str = "left") -> None:
        if self.event_cb:
            self.event_cb("click")
        if self.dry_run or button != "left":
            return
        _send_input(_INPUT(type=INPUT_MOUSE, u=_INPUTUNION(
            mi=_MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, 0))))
        time.sleep(0.035)
        _send_input(_INPUT(type=INPUT_MOUSE, u=_INPUTUNION(
            mi=_MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, 0))))

    def _keyboard_input(self, definition: KeyDef, down: bool) -> _INPUT:
        flags = 0
        if self.mode == "scancode":
            flags |= KEYEVENTF_SCANCODE
            scan, vk = definition.scan, 0
        else:
            scan, vk = 0, definition.vk
        if definition.extended:
            flags |= KEYEVENTF_EXTENDEDKEY
        if down is False:
            flags |= KEYEVENTF_KEYUP
        return _INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(
            ki=_KEYBDINPUT(vk, scan, flags, 0, 0)))


Step = tuple[str, object]


def build_sequence(code: str, settings: MacroSettings) -> list[Step]:
    """Translate a stratagem code into a list of input/sleep steps."""
    scheme = DIRECTION_SCHEMES.get(settings.direction_scheme, DIRECTION_SCHEMES["wasd"])
    steps: list[Step] = []
    if settings.hold_menu and settings.menu_key:
        steps.append(("down", settings.menu_key))
        steps.append(("sleep", settings.pre_delay_ms))
    for direction in code:
        key = scheme.get(direction)
        if key is None:
            raise ValueError(f"invalid direction: {direction!r}")
        if settings.key_hold_ms > 0:
            steps.append(("down", key))
            steps.append(("sleep", settings.key_hold_ms))
            steps.append(("up", key))
        else:
            steps.append(("tap", key))
        steps.append(("sleep", settings.key_gap_ms))
    if settings.hold_menu and settings.menu_key:
        steps.append(("up", settings.menu_key))
        steps.append(("sleep", settings.post_delay_ms))
    if settings.auto_throw:
        steps.append(("sleep", settings.throw_delay_ms))
        steps.append(("click", "left"))
    return steps


def run_steps(sender: MacroSender, steps: Iterable[Step], on_event: Callable[[str], None] | None = None) -> None:
    for kind, value in steps:
        if kind == "down":
            sender.key(str(value), True)
        elif kind == "up":
            sender.key(str(value), False)
        elif kind == "tap":
            sender.key(str(value), True)
            time.sleep(0.012)
            sender.key(str(value), False)
        elif kind == "click":
            sender.click(str(value))
        elif kind == "sleep":
            if sender.dry_run:
                continue
            time.sleep(int(value) / 1000.0)


class MacroRunner(QObject):
    """Runs one macro at a time on a background thread."""

    started = Signal(str, str)      # stratagem name, source
    finished = Signal(str)          # stratagem name
    failed = Signal(str)
    key_event = Signal(str)
    busy_changed = Signal(bool)

    def __init__(self, settings_provider: Callable[[], MacroSettings], parent: QObject | None = None):
        super().__init__(parent)
        self._settings_provider = settings_provider
        self._lock = threading.Lock()
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    def run(self, stratagem: Stratagem, source: str = "hotkey") -> bool:
        return self.run_code(stratagem.code, stratagem.name, source)

    def run_code(self, code: str, label: str, source: str = "hotkey") -> bool:
        if not self._lock.acquire(blocking=False):
            return False
        self._busy = True
        self.busy_changed.emit(True)
        thread = threading.Thread(
            target=self._worker, args=(code, label, source), daemon=True
        )
        thread.start()
        return True

    def _worker(self, code: str, label: str, source: str) -> None:
        from .. import diagnostics

        settings = self._settings_provider()
        sender = MacroSender(mode=settings.input_mode, dry_run=settings.dry_run)
        diagnostics.macro_log(
            f"start '{label}' code={code} source={source} hold_menu={settings.hold_menu} "
            f"menu_key={settings.menu_key} hold={settings.key_hold_ms}ms gap={settings.key_gap_ms}ms "
            f"throw={settings.auto_throw} mode={settings.input_mode} dry_run={settings.dry_run}")
        try:
            steps = build_sequence(code, settings)
            self.started.emit(label, source)
            run_steps(sender, steps)
            self.finished.emit(label)
            diagnostics.macro_log(f"done  '{label}'")
        except Exception as exc:  # noqa: BLE001 - surfaced in the UI
            diagnostics.macro_log(f"error '{label}': {exc}")
            self.failed.emit(str(exc))
        finally:
            self._busy = False
            self._lock.release()
            self.busy_changed.emit(False)
