"""Render every page to PNG for visual review (offscreen, no hooks registered)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["HD2SS_HOME"] = str(ROOT / ".tmp" / "shot-home")
Path(os.environ["HD2SS_HOME"]).mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))

from app.context import AppContext  # noqa: E402
from app.core.database import StratagemDatabase  # noqa: E402
from app.core.models import Loadout  # noqa: E402
from app.core.storage import Storage  # noqa: E402
from app.main import build_application  # noqa: E402
from app.paths import STRATAGEM_DB  # noqa: E402
from app.ui.dialogs import KeywordDialog, StratagemPicker  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402

OUT = ROOT / ".tmp" / "shots"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    app = build_application([sys.argv[0]])
    db = StratagemDatabase(STRATAGEM_DB)
    storage = Storage()
    settings = storage.load_settings()
    settings.hotkeys.enabled = False
    settings.voice.enabled = False
    loadouts = storage.load_loadouts()
    loadout = loadouts["default"]
    loadout.name = "Bugs – Schwierigkeit 10"
    loadout.slots = ["eagle_500kg_bomb", "orbital_380mm_he_barrage", "gr_8_recoilless_rifle",
                     "sh_32_shield_generator_pack"]
    loadouts["Bots"] = Loadout(name="Bots – Schwierigkeit 9", slots=[
        "eagle_airstrike", "orbital_railcannon_strike", "ac_8_autocannon", "resupply"])
    loadouts["Defense"] = Loadout(name="Defense – Schwierigkeit 8", slots=[
        "a_g_16_gatling_sentry", "a_m_12_mortar_sentry", "e_mg_101_hmg_emplacement",
        "orbital_laser"])
    loadouts["Stealth"] = Loadout(name="Stealth – Schwierigkeit 9", slots=[
        "orbital_smoke_strike", "eagle_smoke_strike", "sh_51_directional_shield", None])
    loadouts["Bunker"] = Loadout(name="Bunker – Schwierigkeit 7", slots=[
        "e_mg_101_hmg_emplacement", "fx_12_shield_generator_relay", "resupply", None])
    loadouts["Solo"] = Loadout(name="Solo – Schwierigkeit 6", slots=[
        "eagle_strafing_run", "orbital_precision_strike", None, None])
    storage.save_loadouts(loadouts)

    ctx = AppContext(db, storage, settings, loadouts)
    ctx.set_mission("erdbau")
    ctx.set_extra(0, "m_104_incinerator_frv")
    for module in ("zero_g_breech_loading", "liquid_ventilated_cockpit",
                   "expanded_weapons_bay", "morale_augmentation"):
        ctx.toggle_ship_module(module)
    window = MainWindow(ctx)
    window.resize(1440, 900)
    window.show()
    app.processEvents()

    names = ["loadout", "macros", "voice", "settings"]
    for index, name in enumerate(names):
        window._select(index)
        app.processEvents()
        pixmap = window.grab()
        path = OUT / f"{name}.png"
        pixmap.save(str(path))
        print("saved", path, pixmap.width(), pixmap.height())

    window._select(0)
    page = window.pages[0]
    page.tabs.set_active(1)
    page._on_tab(1)
    app.processEvents()
    page.grab().save(str(OUT / "kits.png"))
    print("saved kits")
    page.tabs.set_active(0)
    page._on_tab(0)
    app.processEvents()

    for favorite in ("orbital_380mm_he_barrage", "eagle_500kg_bomb", "orbital_laser"):
        ctx.toggle_favorite(favorite)
    ctx.mark_recent("resupply")
    ctx.mark_recent("orbital_380mm_he_barrage")

    picker = StratagemPicker(ctx, "eagle_500kg_bomb", parent=window)
    picker.resize(780, 660)
    picker.show()
    app.processEvents()
    picker.grab().save(str(OUT / "picker.png"))
    print("saved picker")
    picker.close()

    ctx.add_custom_keyword("orbital_380mm_he_barrage", "380")
    ctx.add_custom_keyword("orbital_380mm_he_barrage", "dickes Sperrfeuer")
    ctx.add_custom_keyword("resupply", "nachschlag")
    keywords = KeywordDialog(ctx, parent=window)
    keywords.resize(640, 520)
    keywords.show()
    app.processEvents()
    keywords.grab().save(str(OUT / "keywords.png"))
    print("saved keywords")
    keywords.close()

    ctx.submit_text("adler fünfhundert kilo bombe", execute=False)
    app.processEvents()
    match = ctx.submit_text("nachschub", execute=False)
    print("matcher check:", match.stratagem.name if match.stratagem else None, match.score)

    saved_slots = list(ctx.loadout.slots)
    ctx.loadout.slots[1] = None
    ctx.settings.voice.only_loadout = True
    ctx.submit_text("orbitaler laser", execute=False)
    ctx.submit_text("nachschub", execute=False)
    window._select(2)
    app.processEvents()
    window.grab().save(str(OUT / "voice.png"))
    print("saved voice history")
    ctx.loadout.slots = saved_slots
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
