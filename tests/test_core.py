from __future__ import annotations

import json
import uuid
from pathlib import Path

import numpy as np
import pytest

from app.core.input_sender import MacroSender, build_sequence, run_steps
from app.core.models import AppSettings, Loadout, MacroSettings
from app.core.storage import Storage
from app.core.voice.matcher import VoiceMatcher
from app.core.voice.transcribe import to_wav_bytes

TMP = Path(__file__).resolve().parent.parent / ".tmp"


def test_default_sequence_is_ctrl_wrapped() -> None:
    steps = build_sequence("URDDD", MacroSettings())
    assert steps[0] == ("down", "ctrl")
    assert ("click", "left") == steps[-1]
    downs = [value for kind, value in steps if kind == "down"]
    assert downs[:2] == ["ctrl", "w"]
    assert sum(1 for kind, _ in steps if kind == "click") == 1


def test_sequence_without_menu_hold() -> None:
    settings = MacroSettings(hold_menu=False, auto_throw=False)
    steps = build_sequence("UR", settings)
    kinds = [kind for kind, _ in steps]
    assert "click" not in kinds
    assert ("down", "ctrl") not in steps
    assert kinds.count("down") == 2


def test_arrow_keys_scheme() -> None:
    settings = MacroSettings(direction_scheme="arrows", hold_menu=False)
    steps = build_sequence("UD", settings)
    assert ("down", "up") in steps
    assert ("down", "down") in steps


def test_invalid_direction_raises() -> None:
    with pytest.raises(ValueError):
        build_sequence("UX", MacroSettings())


def test_sender_dry_run_reports_events() -> None:
    events: list[str] = []
    sender = MacroSender(dry_run=True, event_cb=events.append)
    run_steps(sender, build_sequence("UR", MacroSettings()))
    assert "ctrl" in events and "-ctrl" in events
    assert events.count("click") == 1


def test_real_sendinput_accepts_a_harmless_key() -> None:
    """SendInput must not raise for a key the foreground app ignores."""
    sender = MacroSender(mode="scancode", dry_run=False)
    sender.key("f24", True)
    sender.key("f24", False)


def test_settings_roundtrip(tmp_path: Path | None = None) -> None:
    storage = Storage(TMP / f"storage-{uuid.uuid4().hex}")
    settings = AppSettings()
    settings.macro.key_gap_ms = 55
    settings.voice.ptt_key = "f9"
    settings.hotkeys.slots[0] = "alt+1"
    settings.hotkeys.mission_slots = ["f9", "f10", ""]
    settings.active_mission = "erdbau"
    settings.favorites = ["resupply"]
    settings.recent = ["eagle_500kg_bomb"]
    storage.save_settings(settings)
    loaded = storage.load_settings()
    assert loaded.macro.key_gap_ms == 55
    assert loaded.voice.ptt_key == "f9"
    assert loaded.hotkeys.slots[0] == "alt+1"
    assert loaded.hotkeys.mission_slots == ["f9", "f10", ""]
    assert loaded.active_mission == "erdbau"
    assert loaded.favorites == ["resupply"]
    assert loaded.recent == ["eagle_500kg_bomb"]


def test_mission_catalog() -> None:
    from app.core.database import StratagemDatabase
    from app.paths import STRATAGEM_DB

    db = StratagemDatabase(STRATAGEM_DB)
    assert db.mission("none") is not None
    mission = db.mission("erdbau")
    assert mission is not None
    assert mission.name == "Erdbau"
    ids = [item.id for item in db.mission_stratagems("erdbau")]
    assert ids == ["prospecting_drill", "tectonic_drill", "seismic_probe"]
    assert db.mission_stratagems("does-not-exist") == []
    # Hellbomb/SEAF are extra hotkeys, not mission stratagems; ICBM is gone.
    assert db.mission("seaf") is None
    assert db.mission("icbm") is None
    assert db.mission("sssd").stratagems == ("sssd_delivery",)
    assert db.mission("dark_fluid").stratagems == ("dark_fluid_vessel",)


def test_armor_labels_and_traits() -> None:
    from app.core.database import StratagemDatabase
    from app.core.models import ap_label
    from app.paths import STRATAGEM_DB

    assert ap_label(0) == ""
    assert ap_label(1) == "Leicht"
    assert ap_label(3) == "Mittel"
    assert ap_label(5) == "Schwer"
    assert ap_label(7) == "Tank"
    assert ap_label(9) == "Tank II"

    db = StratagemDatabase(STRATAGEM_DB)
    laser = db.get("orbital_laser")
    rocket_sentry = db.get("a_mls_4x_rocket_sentry")
    mortar = db.get("a_m_12_mortar_sentry")
    assert laser is not None and laser.uses == 3
    assert rocket_sentry is not None
    assert rocket_sentry.traits == ("Explosiv",)
    assert mortar is not None and "Gelenkt" not in mortar.traits


def test_stratagem_combat_stats() -> None:
    from app.core.database import StratagemDatabase
    from app.paths import STRATAGEM_DB

    db = StratagemDatabase(STRATAGEM_DB)
    heavy = db.get("orbital_380mm_he_barrage")
    bomb = db.get("eagle_500kg_bomb")
    launcher = db.get("gr_8_recoilless_rifle")
    sentry = db.get("a_ac_8_autocannon_sentry")
    assert heavy is not None and heavy.radius == 60 and heavy.ap == 5
    assert "Explosiv" in heavy.traits
    assert bomb is not None and bomb.radius == 30 and bomb.ap == 7
    assert launcher is not None and launcher.radius is None and launcher.ap == 7
    assert sentry is not None and sentry.ap == 5
    assert db.get("resupply") is not None


def test_ship_modules_change_cooldowns() -> None:
    from app.core.database import StratagemDatabase
    from app.core.models import ShipModule, effective_cooldown, effective_uses
    from app.paths import STRATAGEM_DB

    db = StratagemDatabase(STRATAGEM_DB)
    orbital = db.get("orbital_380mm_he_barrage")
    eagle = db.get("eagle_500kg_bomb")
    assert orbital is not None and eagle is not None
    assert len(db.ship_modules) >= 8

    orbital_mod = db.ship_module("zero_g_breech_loading")
    morale = db.ship_module("morale_augmentation")
    bay = db.ship_module("expanded_weapons_bay")
    assert orbital_mod is not None and morale is not None and bay is not None

    assert effective_cooldown(orbital.cooldown, orbital, ()) == 240
    assert effective_cooldown(orbital.cooldown, orbital, (orbital_mod,)) == 216
    assert effective_cooldown(orbital.cooldown, orbital, (orbital_mod, morale)) == 205
    # Orbital-Module dürfen den Eagle nicht beeinflussen
    assert effective_cooldown(eagle.cooldown, eagle, (orbital_mod,)) == 15
    assert effective_uses(eagle.uses, eagle, (bay,)) == 2
    assert effective_uses(eagle.uses, eagle, (orbital_mod,)) == 1

    module = ShipModule.from_dict({"id": "x", "name": "X", "section": "Test",
                                   "effect": "cooldown", "value": 10,
                                   "targets": ["all"]})
    assert module.applies_to(orbital) and module.applies_to(eagle)


def test_loadout_roundtrip() -> None:
    storage = Storage(TMP / f"storage-{uuid.uuid4().hex}")
    loadouts = {"default": Loadout(name="Test", slots=["resupply", None, "eagle_500kg_bomb", None])}
    storage.save_loadouts(loadouts)
    loaded = storage.load_loadouts()
    assert loaded["default"].name == "Test"
    assert loaded["default"].slots[2] == "eagle_500kg_bomb"
    assert loaded["default"].quick["resupply"] == "resupply"


def test_settings_json_is_readable() -> None:
    storage = Storage(TMP / f"storage-{uuid.uuid4().hex}")
    storage.save_settings(AppSettings())
    payload = json.loads(storage.settings_path.read_text(encoding="utf-8"))
    assert payload["voice"]["ptt_key"] == "f8"


def test_wav_roundtrip() -> None:
    audio = np.zeros(1600, dtype=np.float32)
    data = to_wav_bytes(audio)
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WAVE"
    assert len(data) > 1600


def test_matcher_threshold_from_settings() -> None:
    matcher = VoiceMatcher(0.8)
    matcher.threshold = 0.5
    assert matcher.threshold == 0.5
