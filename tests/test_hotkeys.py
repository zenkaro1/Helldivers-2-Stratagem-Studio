"""Unit tests for the keyboard-hook hotkey backend (no real hook installed)."""

from __future__ import annotations

import os

import pytest

from app.core import hotkeys as hk

os.environ.setdefault("HD2SS_NO_HOOKS", "1")


@pytest.fixture()
def manager(qapp) -> hk.HotkeyManager:
    instance = hk.HotkeyManager()
    yield instance
    instance.clear()


@pytest.fixture()
def keyboard_state(monkeypatch):
    pressed: set[str] = set()

    def fake_is_down(vk: int) -> bool:
        return any(hk._vk_for(name) == vk for name in pressed)

    monkeypatch.setattr(hk, "_is_down", fake_is_down)
    return pressed


def test_parse_combo() -> None:
    assert hk._parse_combo("ctrl+alt+f2") == (frozenset({"ctrl", "alt"}), "f2")
    assert hk._parse_combo("f8") == (frozenset(), "f8")
    assert hk._parse_combo("gibtsnicht") is None


def test_vk_lookup() -> None:
    assert hk._vk_for("w") == 0x57
    assert hk._vk_for("f1") == 0x70
    assert hk._vk_for("ctrl") == 0x11
    assert hk._vk_for("unbekannt") is None


def test_bindings_stored(manager) -> None:
    assert manager.apply({"slot2": "ctrl+alt+f2"}) == []
    assert manager.bindings == {"ctrl+alt+f2": "slot2"}
    assert manager._reverse[hk._vk_for("f2")] == [(frozenset({"ctrl", "alt"}), "slot2")]


def test_dispatch_with_modifiers(manager) -> None:
    fired: list[str] = []
    manager.triggered.connect(fired.append)
    manager.apply({"slot2": "ctrl+alt+f2", "side:x": "f7"})

    manager._handle_key(hk._vk_for("ctrl"), True)
    manager._handle_key(hk._vk_for("alt"), True)
    manager._handle_key(hk._vk_for("f2"), True)
    manager._handle_key(hk._vk_for("f2"), False)
    manager._handle_key(hk._vk_for("ctrl"), False)
    manager._handle_key(hk._vk_for("alt"), False)
    manager._handle_key(hk._vk_for("f7"), True)

    assert fired == ["slot2", "side:x"]


def test_wrong_modifier_does_not_fire(manager) -> None:
    fired: list[str] = []
    manager.triggered.connect(fired.append)
    manager.apply({"slot1": "ctrl+f1"})

    manager._handle_key(hk._vk_for("f1"), True)  # ohne ctrl
    assert fired == []

    manager._handle_key(hk._vk_for("ctrl"), True)
    manager._handle_key(hk._vk_for("f1"), True)
    assert fired == ["slot1"]


def test_suspend_blocks_triggers(manager) -> None:
    fired: list[str] = []
    manager.triggered.connect(fired.append)
    manager.apply({"slot1": "f1"})
    manager.suspend(True)
    manager._handle_key(hk._vk_for("f1"), True)
    assert fired == []
    manager.suspend(False)
    manager._handle_key(hk._vk_for("f1"), True)
    assert fired == ["slot1"]


def test_invalid_combo_reports_error(manager) -> None:
    errors = manager.apply({"slot1": "gibtsnicht"})
    assert errors and "unbekannte Taste" in errors[0]


def test_ptt_press_release(qapp, keyboard_state) -> None:
    ptt = hk.PushToTalk()
    events: list[str] = []
    ptt.pressed.connect(lambda: events.append("down"))
    ptt.released.connect(lambda: events.append("up"))
    ptt.bind("f8", threaded=False)

    keyboard_state.add("f8")
    ptt._tick()
    ptt._tick()  # auto-repeat must not re-fire
    keyboard_state.discard("f8")
    ptt._tick()
    assert events == ["down", "up"]
    ptt.unbind()


def test_key_capture(qapp, keyboard_state) -> None:
    capture = hk.KeyCapture()
    combos: list[str] = []
    capture.captured.connect(combos.append)
    capture.start(2000)

    keyboard_state.update({"ctrl", "shift"})
    capture._tick()
    keyboard_state.add("h")
    capture._tick()
    assert combos == ["ctrl+shift+h"]
