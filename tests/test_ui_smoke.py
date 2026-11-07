from __future__ import annotations

import os
import uuid
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.context import AppContext  # noqa: E402
from app.core.database import StratagemDatabase  # noqa: E402
from app.core.models import AppSettings, Loadout  # noqa: E402
from app.core.storage import Storage  # noqa: E402
from app.main import build_application  # noqa: E402
from app.paths import STRATAGEM_DB  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402

TMP = Path(__file__).resolve().parent.parent / ".tmp"


@pytest.fixture(scope="module")
def app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return build_application(["pytest"])


@pytest.fixture()
def context(app: QApplication) -> AppContext:
    database = StratagemDatabase(STRATAGEM_DB)
    storage = Storage(TMP / f"ui-{uuid.uuid4().hex}")
    settings = AppSettings()
    settings.hotkeys.enabled = False
    settings.voice.enabled = False
    loadouts = {"default": Loadout(name="Test", slots=["eagle_500kg_bomb", None, None, "resupply"])}
    return AppContext(database, storage, settings, loadouts)


def test_window_builds_and_navigates(app: QApplication, context: AppContext) -> None:
    window = MainWindow(context)
    try:
        assert window.stack.count() == 4
        for index in range(4):
            window._select(index)
            assert window.stack.currentIndex() == index
        window.refresh if hasattr(window, "refresh") else None
    finally:
        window.ctx.settings.minimize_to_tray = False
        window.close()
        window.overlay.hide()
        window.overlay.deleteLater()
        window.deleteLater()
        app.processEvents()


def test_voice_text_executes_slot(app: QApplication, context: AppContext) -> None:
    match = context.submit_text("Adler fünfhundert Kilo", execute=False)
    assert match.stratagem is not None
    assert match.stratagem.id == "eagle_500kg_bomb"


def test_unknown_voice_text(app: QApplication, context: AppContext) -> None:
    match = context.submit_text("irgendwas ganz anderes", execute=False)
    assert not match.ok
    assert match.alternatives == [] or isinstance(match.alternatives, list)


def test_hotkey_trigger_uses_slot(app: QApplication, context: AppContext) -> None:
    context.settings.macro.dry_run = True
    assert context.trigger_slot(0) is True
    assert context.cooldown_remaining("eagle_500kg_bomb") > 0


def test_randomize_keeps_four_slots(app: QApplication, context: AppContext) -> None:
    context.randomize()
    assert len(context.loadout.slots) == 4
    assert all(slot for slot in context.loadout.slots)


def test_mission_hotkey_slots(context: AppContext) -> None:
    context.settings.macro.dry_run = True
    context.set_mission("erdbau")
    context.settings.hotkeys.mission_slots = ["f9", "f10", ""]
    context.apply_hotkeys()

    assert context.trigger_mission_slot(0) is True
    assert context.trigger_mission_slot(3) is False
    assert "prospecting_drill" in context.settings.recent

    # gleiche Belegung, andere Mission: Platz 1 nimmt jetzt das Flaggen-Stratagem
    context.set_mission("flag")
    flag_stratagems = [item.id for item in context.mission_stratagems()]
    assert flag_stratagems
    assert context.trigger_mission_slot(0) is True
    assert flag_stratagems[0] in context.settings.recent


def test_custom_voice_keywords(context: AppContext) -> None:
    target = "orbital_380mm_he_barrage"
    context.loadout.slots[0] = target
    context.settings.voice.only_loadout = True

    assert context.submit_text("bumm bumm", execute=False).stratagem is None
    assert context.add_custom_keyword(target, "bumm bumm") is True
    match = context.submit_text("bumm bumm", execute=False)
    assert match.stratagem is not None and match.stratagem.id == target
    # doppelt (case-insensitiv) wird abgelehnt
    assert context.add_custom_keyword(target, "BUMM BUMM") is False
    assert len(context.custom_keywords(target)) == 1

    context.remove_custom_keyword(target, "bumm bumm")
    assert context.custom_keywords(target) == []
    assert context.submit_text("bumm bumm", execute=False).stratagem is None

    # eingebaute Zahlen-Aliase funktionieren weiterhin ohne eigenen Eintrag
    assert context.submit_text("dreihundertachtzig", execute=False).stratagem.id == target


def test_outside_loadout_is_reported(context: AppContext) -> None:
    context.settings.voice.only_loadout = True
    context.loadout.slots = ["eagle_500kg_bomb", None, None, None]

    match = context.submit_text("dreihundertachtzig", execute=False)
    assert match.stratagem is None
    assert match.ok is False
    assert match.outside_loadout is not None
    assert match.outside_loadout.id == "orbital_380mm_he_barrage"

    context.settings.voice.only_loadout = False
    direct = context.submit_text("dreihundertachtzig", execute=False)
    assert direct.stratagem is not None
    assert direct.outside_loadout is None


def test_numeric_keywords(context: AppContext) -> None:
    context.settings.voice.only_loadout = True
    context.loadout.slots[1] = "orbital_120mm_he_barrage"
    assert context.submit_text("120", execute=False).stratagem.id == "orbital_120mm_he_barrage"
    assert context.submit_text("120mm", execute=False).stratagem.id == "orbital_120mm_he_barrage"

    # nicht im Loadout -> nur über ein eigenes Keyword erreichbar
    context.loadout.slots[1] = None
    assert context.submit_text("120", execute=False).stratagem is None
    context.add_custom_keyword("orbital_120mm_he_barrage", "120")
    assert context.submit_text("120", execute=False).stratagem.id == "orbital_120mm_he_barrage"

    # eine einzelne Ziffer darf keine 500 treffen
    assert context.submit_text("5", execute=False).stratagem is None


def test_slots_reject_duplicates(context: AppContext) -> None:
    context.set_slot(0, "eagle_500kg_bomb")
    errors: list[str] = []
    context.error.connect(errors.append)
    context.set_slot(2, "eagle_500kg_bomb")
    assert context.loadout.slots[0] == "eagle_500kg_bomb"
    assert context.loadout.slots[2] is None
    assert errors and "nicht zweimal" in errors[-1]
    assert "Slot 1" in errors[-1]
    # ein anderes Stratagem geht weiterhin
    context.set_slot(2, "orbital_380mm_he_barrage")
    assert context.loadout.slots[2] == "orbital_380mm_he_barrage"


def test_legacy_loadout_duplicates_are_cleaned() -> None:
    from app.core.models import Loadout

    loadout = Loadout.from_dict({"name": "Alt", "slots": [
        "resupply", "resupply", "eagle_500kg_bomb", "resupply"]})
    assert loadout.slots == ["resupply", None, "eagle_500kg_bomb", None]


def test_kits_grid_shows_every_kit(app: QApplication, context: AppContext) -> None:
    for index in range(6):
        context.create_loadout(f"Kit {index}")
    window = MainWindow(context)
    window.show()
    app.processEvents()
    try:
        window.pages[0].refresh()
        app.processEvents()
        assert len(window.pages[0]._kit_cards) == len(context.loadouts)
    finally:
        window.close()
        window.overlay.deleteLater()
        window.deleteLater()


def test_error_shows_in_app_toast(app: QApplication, context: AppContext) -> None:
    window = MainWindow(context)
    window.show()
    app.processEvents()
    try:
        assert not window.toast.isVisible()
        context.set_slot(0, "eagle_500kg_bomb")
        context.set_slot(1, "eagle_500kg_bomb")
        app.processEvents()
        assert window.toast.isVisible()
        assert "nicht zweimal" in window.toast.text.text()
    finally:
        window.toast.hide()
        window.close()
        window.overlay.hide()
        window.overlay.deleteLater()
        window.deleteLater()


def test_picker_star_click_keeps_dialog_open(app: QApplication, context: AppContext) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from app.ui.dialogs import StratagemPicker

    context.favorite_stratagems()
    picker = StratagemPicker(context, None)
    picker._set_tab("orbital")
    picker.show()
    app.processEvents()
    row = picker.list.item(0)
    widget = picker.list.itemWidget(row)
    try:
        was_favorite = context.is_favorite(widget.stratagem.id)
        QTest.mouseClick(widget.star, Qt.MouseButton.LeftButton)
        app.processEvents()
        assert context.is_favorite(widget.stratagem.id) != was_favorite
        assert picker.result() == 0  # still open, not accepted
    finally:
        picker.close()


def test_picker_single_click_picks(app: QApplication, context: AppContext) -> None:
    from PySide6.QtWidgets import QDialog

    from app.ui.dialogs import StratagemPicker

    picker = StratagemPicker(context, None)
    picked: list[str] = []
    picker.picked.connect(picked.append)
    try:
        picker._set_tab("orbital")
        picker._choose("orbital_380mm_he_barrage")
        assert picked == ["orbital_380mm_he_barrage"]
        assert picker.result() == QDialog.DialogCode.Accepted
    finally:
        picker.close()


def test_custom_keyword_dialog(context: AppContext) -> None:
    from app.ui.dialogs import KeywordDialog

    context.add_custom_keyword("resupply", "nachschlag")
    dialog = KeywordDialog(context)
    try:
        assert dialog.list.count() == 1
        assert dialog.empty.isHidden()
    finally:
        dialog.close()


def test_block_on_cooldown(context: AppContext) -> None:
    import time

    context.loadout.slots[1] = "orbital_380mm_he_barrage"
    stratagem = context.db.get(context.loadout.slots[1])
    assert stratagem is not None
    context.settings.macro.dry_run = True
    context._cooldowns[stratagem.id] = time.time() + 60

    infos: list[str] = []
    context.info.connect(infos.append)

    context.settings.macro.block_on_cooldown = False
    assert context.trigger_slot(1) is True

    context._cooldowns[stratagem.id] = time.time() + 60
    context.settings.macro.block_on_cooldown = True
    assert context.trigger_slot(1) is False
    assert infos and "Cooldown" in infos[-1]


def test_eagle_charges_and_rearm(context: AppContext) -> None:
    import time

    context.settings.macro.dry_run = True
    context.settings.macro.block_on_cooldown = False
    eagle = context.db.get("eagle_500kg_bomb")
    assert eagle is not None and eagle.uses == 1
    context.loadout.slots[0] = eagle.id

    assert context.remaining_uses(eagle) == 1
    assert context.trigger_slot(0) is True
    time.sleep(0.1)
    assert context.remaining_uses(eagle) == 0

    # Standard: nicht sperren – der Befehl geht trotzdem raus
    assert context.trigger_slot(0) is True
    time.sleep(0.1)
    assert context.remaining_uses(eagle) == 0

    # Mit Sperre: Rearm blockt
    context.settings.macro.block_on_cooldown = True
    infos: list[str] = []
    context.info.connect(infos.append)
    assert context.trigger_slot(0) is False
    assert infos and "Rearm" in infos[-1]

    # Rearm abgelaufen -> wieder voll
    context._cooldowns[eagle.id] = time.time() - 1
    assert context.remaining_uses(eagle) == 1


def test_extra_stratagems(context: AppContext) -> None:
    context.settings.macro.dry_run = True
    context.set_extra(0, "m_104_incinerator_frv")
    assert context.extra_stratagems()[0] is not None
    assert context.extra_stratagems()[0].id == "m_104_incinerator_frv"

    errors: list[str] = []
    context.error.connect(errors.append)
    context.set_slot(0, "eagle_500kg_bomb")
    context.set_extra(1, "eagle_500kg_bomb")
    assert errors and "Loadout" in errors[-1]
    assert context.extra_stratagems()[1] is None

    context.set_extra(1, "m_104_incinerator_frv")
    assert errors and "Extra 1" in errors[-1]

    context.settings.hotkeys.enabled = True
    context.apply_hotkeys()
    context._on_hotkey("extra1")
    assert "m_104_incinerator_frv" in context.settings.recent

    context.set_extra(0, None)
    assert context.extra_stratagems()[0] is None


def test_eagle_rearm_is_side_objective(context: AppContext) -> None:
    from app.core.models import SIDE_OBJECTIVES

    assert "eagle_rearm" in dict(SIDE_OBJECTIVES)
    assert context.settings.hotkeys.side.get("eagle_rearm") == "shift+f7"
    context.settings.macro.dry_run = True
    context.settings.hotkeys.enabled = True
    context.apply_hotkeys()
    context._on_hotkey("side:eagle_rearm")
    assert "eagle_rearm" in context.settings.recent


def test_side_objective_hotkey(context: AppContext) -> None:
    context.settings.macro.dry_run = True
    context.settings.hotkeys.enabled = True
    context.settings.hotkeys.side = {"nux_223_hellbomb": "f7"}
    context.apply_hotkeys()
    context._on_hotkey("side:nux_223_hellbomb")
    assert "nux_223_hellbomb" in context.settings.recent


def test_hotkey_conflicts_are_reported(context: AppContext) -> None:
    context.settings.hotkeys.enabled = True
    errors: list[str] = []
    context.error.connect(errors.append)
    context.settings.hotkeys.slots = ["f1", "f2", "f3", "f1"]
    context.apply_hotkeys()
    assert errors and "F1" in errors[-1] and "doppelt" in errors[-1]

    # PTT-Kollision wird ebenfalls erkannt
    errors.clear()
    context.settings.hotkeys.slots = ["f1", "f2", "f3", "f4"]
    context.settings.voice.ptt_key = "f2"
    context.apply_hotkeys()
    assert errors and "Push-to-Talk" in errors[-1]


def test_mission_selection_updates_stratagems(app: QApplication,
                                              context: AppContext) -> None:
    assert context.mission is not None
    context.set_mission("erdbau")
    ids = [item.id for item in context.mission_stratagems()]
    assert ids == ["prospecting_drill", "tectonic_drill", "seismic_probe"]
    context.set_mission("none")
    assert context.mission_stratagems() == []


def test_favorites_and_recent(app: QApplication, context: AppContext) -> None:
    assert not context.is_favorite("resupply")
    context.toggle_favorite("resupply")
    assert context.is_favorite("resupply")
    assert [item.id for item in context.favorite_stratagems()] == ["resupply"]

    context.settings.macro.dry_run = True
    assert context.trigger_slot(0) is True
    assert context.recent_stratagems()[0].id == "eagle_500kg_bomb"


def test_picker_builds(app: QApplication, context: AppContext) -> None:
    from app.ui.dialogs import StratagemPicker

    context.toggle_favorite("orbital_laser")
    picker = StratagemPicker(context, "orbital_laser")
    try:
        assert picker.list.count() >= 1
        picker._set_tab("orbital")
        assert picker.list.count() >= 1
    finally:
        picker.close()


def test_delete_kit_switches_active(context: AppContext) -> None:
    context.create_loadout("Wegwerf-Kit")
    key = context.settings.active_loadout
    assert key in context.loadouts
    context.delete_loadout(key)
    assert key not in context.loadouts
    assert context.settings.active_loadout in context.loadouts


def test_last_kit_cannot_be_deleted(context: AppContext) -> None:
    for key in list(context.loadouts)[1:]:
        context.delete_loadout(key)
    assert len(context.loadouts) == 1
    errors: list[str] = []
    context.error.connect(errors.append)
    context.delete_loadout(next(iter(context.loadouts)))
    assert len(context.loadouts) == 1
    assert errors and "mindestens" in errors[0].lower()


def test_ship_module_toggle(context: AppContext) -> None:
    orbital = context.db.get("orbital_380mm_he_barrage")
    assert orbital is not None
    before = context.effective_cooldown(orbital)
    context.toggle_ship_module("zero_g_breech_loading")
    assert context.has_ship_module("zero_g_breech_loading")
    assert context.effective_cooldown(orbital) < before
    context.toggle_ship_module("zero_g_breech_loading")
    assert context.effective_cooldown(orbital) == before


def test_second_instance_exits_cleanly(app: QApplication, monkeypatch) -> None:
    """A second start must show a message instead of crashing (UnboundLocalError)."""
    from PySide6.QtCore import QLockFile

    from app import main as app_main

    monkeypatch.setattr(QLockFile, "tryLock", lambda self, timeout=0: False)
    messages: list[str] = []
    monkeypatch.setattr(app_main.diagnostics, "message",
                        lambda title, text: messages.append(title))
    lock = app_main._acquire_instance(Storage(TMP / f"ui-{uuid.uuid4().hex}"))
    assert lock is None
    assert messages == ["Stratagem Studio"]
