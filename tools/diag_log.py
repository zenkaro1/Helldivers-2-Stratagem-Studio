"""Verify the macro log and the menu-hold sequence end to end."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(r"C:\Projekte\Website Design\hd2-stratagem-studio")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["HD2SS_HOME"] = str(ROOT / ".tmp" / "logtest")
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.context import AppContext  # noqa: E402
from app.core.database import StratagemDatabase  # noqa: E402
from app.core.models import Loadout  # noqa: E402
from app.core.storage import Storage  # noqa: E402
from app.paths import STRATAGEM_DB  # noqa: E402

app = QApplication(sys.argv)
settings = Storage().load_settings()
settings.macro.dry_run = True
settings.macro.hold_menu = True
loadouts = {"default": Loadout(slots=["eagle_500kg_bomb", None, None, None])}
ctx = AppContext(StratagemDatabase(STRATAGEM_DB), Storage(), settings, loadouts)
print("triggered:", ctx.trigger_slot(0))
time.sleep(1.2)
log = Path(os.environ["HD2SS_HOME"]) / "macro.log"
print("---- macro.log ----")
print(log.read_text(encoding="utf-8") if log.exists() else "missing")
