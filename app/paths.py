"""Filesystem locations used by the app."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))

# Code + bundled data: in a PyInstaller build __file__ lives in the unpacked
# bundle, so the relative layout (app/, data/) stays the same.
PACKAGE_DIR = Path(__file__).resolve().parent
APP_ROOT = Path(sys.executable).resolve().parent if FROZEN else PACKAGE_DIR.parent
DATA_DIR = PACKAGE_DIR.parent / "data"
ICON_DIR = DATA_DIR / "icons"
STRATAGEM_DB = DATA_DIR / "stratagems.json"

APP_NAME = "HD2 Stratagem Studio"
APP_SLUG = "hd2-stratagem-studio"
APP_WINDOW_TITLE = "Stratagem Studio – Helldivers 2 Loadout & Voice Macros"

ASSETS_DIR = PACKAGE_DIR / "assets"
LOGO_FILE = ASSETS_DIR / "logo.png"
LOGO_ICO_FILE = ASSETS_DIR / "logo.ico"
LOGO_MARK_FILE = ASSETS_DIR / "logo-mark.png"

_cached: Path | None = None


def _override() -> Path | None:
    value = os.environ.get("HD2SS_HOME")
    return Path(value) if value else None


def _portable() -> bool:
    return (APP_ROOT / "portable.txt").exists()


def _candidates() -> list[Path]:
    if _portable():
        return [APP_ROOT / "userdata"]
    result: list[Path] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        result.append(Path(appdata) / "HD2StratagemStudio")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        result.append(Path(local) / "HD2StratagemStudio")
    result.append(APP_ROOT / "userdata")
    result.append(Path(tempfile.gettempdir()) / "HD2StratagemStudio")
    return result


def _has_data(path: Path) -> bool:
    try:
        return (path / "settings.json").is_file() or (path / "loadouts.json").is_file()
    except OSError:
        return False


def config_dir() -> Path:
    """Writable directory for settings, loadouts and models.

    Keeps using an existing data folder (e.g. the ``userdata`` fallback from an
    earlier start) instead of switching to an empty AppData folder, so kits and
    favourites never disappear.  Otherwise it falls back through AppData ->
    LocalAppData -> project folder -> temp.
    """
    global _cached
    if _cached is not None:
        return _cached

    override = _override()
    if override is not None:
        override.mkdir(parents=True, exist_ok=True)
        _cached = override
        return override

    candidates = _candidates()
    for path in candidates:
        if _has_data(path):
            _cached = path
            return path

    last_error: Exception | None = None
    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            _cached = path
            return path
        except OSError as exc:  # locked, read-only or denied
            last_error = exc
            continue
    raise OSError(f"Kein beschreibbarer Datenordner gefunden: {last_error}")
