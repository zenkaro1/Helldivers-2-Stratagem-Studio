"""Persistence for settings and loadouts (JSON in the user config directory)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..paths import config_dir
from .models import AppSettings, Loadout


class Storage:
    def __init__(self, directory: Path | None = None):
        self.dir = directory or config_dir()
        self.dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.dir / "settings.json"
        self.loadouts_path = self.dir / "loadouts.json"

    # -- settings ---------------------------------------------------------
    def load_settings(self) -> AppSettings:
        data = self._read(self.settings_path, {})
        return AppSettings.from_dict(data)

    def save_settings(self, settings: AppSettings) -> None:
        self._write(self.settings_path, settings.to_dict())

    # -- loadouts ---------------------------------------------------------
    def load_loadouts(self) -> dict[str, Loadout]:
        data = self._read(self.loadouts_path, {})
        raw = data.get("loadouts") if isinstance(data, dict) else None
        if not isinstance(raw, dict) or not raw:
            return {"default": Loadout(name="Standard")}
        loadouts: dict[str, Loadout] = {}
        for key, value in raw.items():
            if isinstance(value, dict):
                loadouts[key] = Loadout.from_dict(value)
        return loadouts or {"default": Loadout()}

    def save_loadouts(self, loadouts: dict[str, Loadout]) -> None:
        payload = {
            "version": 1,
            "loadouts": {key: loadout.to_dict() for key, loadout in loadouts.items()},
        }
        self._write(self.loadouts_path, payload)

    # -- helpers ----------------------------------------------------------
    def _read(self, path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default

    def _write(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        try:
            tmp.replace(path)
        except OSError:
            path.write_text(text, encoding="utf-8")
