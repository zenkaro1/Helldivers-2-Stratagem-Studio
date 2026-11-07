"""Stratagem database: loading, lookup, search."""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

from .models import CATEGORY_ORDER, Mission, ShipModule, Stratagem


def normalize(text: str) -> str:
    text = text.lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"\s+", " ", text).strip()


class StratagemDatabase:
    def __init__(self, path: Path, missions_path: Path | None = None):
        self.path = path
        self.missions_path = missions_path or path.with_name("missions.json")
        self._items: list[Stratagem] = []
        self._by_id: dict[str, Stratagem] = {}
        self._by_category: dict[str, list[Stratagem]] = {}
        self._missions: list[Mission] = []
        self._ship_modules: list[ShipModule] = []
        self.version = 0
        self.source = ""
        self.load()

    @property
    def items(self) -> list[Stratagem]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def load(self) -> None:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        items = [Stratagem.from_dict(row) for row in data.get("stratagems", [])]
        self.version = int(data.get("version", 0))
        self.source = str(data.get("source", ""))
        self._items = items
        self._by_id = {item.id: item for item in items}
        self._by_category = {}
        for item in items:
            self._by_category.setdefault(item.category, []).append(item)
        self._missions = self._load_missions()
        self._ship_modules = self._load_ship_modules()

    def _load_ship_modules(self) -> list[ShipModule]:
        path = self.missions_path.with_name("ship_modules.json")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [ShipModule.from_dict(row) for row in payload.get("modules", [])]

    def _load_missions(self) -> list[Mission]:
        try:
            payload = json.loads(self.missions_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        missions = [Mission.from_dict(row) for row in payload.get("missions", [])]
        return missions

    # -- missions --------------------------------------------------------
    @property
    def missions(self) -> list[Mission]:
        return list(self._missions)

    @property
    def ship_modules(self) -> list[ShipModule]:
        return list(self._ship_modules)

    def ship_module(self, module_id: str) -> ShipModule | None:
        for module in self._ship_modules:
            if module.id == module_id:
                return module
        return None

    def mission(self, mission_id: str | None) -> Mission | None:
        for mission in self._missions:
            if mission.id == mission_id:
                return mission
        return None

    def mission_stratagems(self, mission_id: str | None) -> list[Stratagem]:
        mission = self.mission(mission_id)
        if mission is None:
            return []
        return [item for item in (self.get(sid) for sid in mission.stratagems) if item]

    def get(self, stratagem_id: str | None) -> Stratagem | None:
        if not stratagem_id:
            return None
        return self._by_id.get(stratagem_id)

    def require(self, stratagem_id: str) -> Stratagem:
        item = self.get(stratagem_id)
        if item is None:
            raise KeyError(stratagem_id)
        return item

    def by_category(self, category: str) -> list[Stratagem]:
        return list(self._by_category.get(category, []))

    def categories(self) -> list[tuple[str, list[Stratagem]]]:
        return [(key, self._by_category[key]) for key in CATEGORY_ORDER if key in self._by_category]

    def search(self, query: str, limit: int = 200) -> list[Stratagem]:
        query = normalize(query)
        if not query:
            return self._items[:limit]
        tokens = query.split()
        scored: list[tuple[float, Stratagem]] = []
        for item in self._items:
            haystack = normalize(item.name) + " " + " ".join(normalize(a) for a in item.aliases)
            score = 0.0
            for token in tokens:
                if token in normalize(item.name):
                    score += 2.0
                elif token in haystack:
                    score += 1.0
            if score:
                if normalize(item.name).startswith(query):
                    score += 1.0
                scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], pair[1].name))
        return [item for _, item in scored[:limit]]

    def random_loadout(self) -> list[Stratagem]:
        """Roughly sensible random picks: one support, one offensive, one defensive, one flex."""
        support = [s for s in self._items if s.category in {"support", "backpack", "vehicle"}]
        offense = [s for s in self._items if s.category in {"orbital", "eagle"}]
        defense = [s for s in self._items if s.category in {"sentry", "mine", "emplacement"}]
        picks: list[Stratagem] = []
        for pool in (support, offense, defense):
            if pool:
                picks.append(random.choice(pool))
        rest = [s for s in self._items if not s.is_mission and s not in picks]
        if rest and len(picks) < 4:
            picks.append(random.choice(rest))
        random.shuffle(picks)
        return picks
