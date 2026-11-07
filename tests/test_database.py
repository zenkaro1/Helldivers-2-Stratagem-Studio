from __future__ import annotations

import json

import pytest

from app.core.database import StratagemDatabase, normalize
from app.paths import ICON_DIR, STRATAGEM_DB


@pytest.fixture(scope="module")
def db() -> StratagemDatabase:
    return StratagemDatabase(STRATAGEM_DB)


def test_database_loads(db: StratagemDatabase) -> None:
    assert len(db) >= 100
    assert db.version >= 1
    assert "wiki" in db.source


def test_ids_are_unique(db: StratagemDatabase) -> None:
    ids = [item.id for item in db.items]
    assert len(ids) == len(set(ids))


def test_codes_are_valid(db: StratagemDatabase) -> None:
    for item in db.items:
        assert item.code, item.name
        assert 2 <= len(item.code) <= 9, (item.name, item.code)
        assert set(item.code) <= set("UDLR"), (item.name, item.code)


def test_icons_exist(db: StratagemDatabase) -> None:
    missing = [item.name for item in db.items if not (ICON_DIR / f"{item.id}.svg").exists()]
    assert not missing


def test_known_codes(db: StratagemDatabase) -> None:
    assert db.require("eagle_500kg_bomb").code == "URDDD"
    assert db.require("resupply").code == "DDUR"
    assert db.require("reinforce").code == "UDRLU"
    assert db.require("orbital_380mm_he_barrage").code == "RDUULDD"
    assert db.require("gr_8_recoilless_rifle").code == "DLRRL"


def test_search_finds_short_names(db: StratagemDatabase) -> None:
    names = [item.name for item in db.search("500")]
    assert any("500kg" in name for name in names)
    assert [item.id for item in db.search("railcannon")][0] == "orbital_railcannon_strike"


def test_random_loadout_is_sensible(db: StratagemDatabase) -> None:
    picks = db.random_loadout()
    assert len(picks) == 4
    assert len({item.id for item in picks}) == 4
    assert all(not item.is_mission for item in picks)
    assert any(item.category in {"support", "backpack", "vehicle"} for item in picks)


def test_normalize_handles_umlauts() -> None:
    assert normalize("Präzision") == "praezision"


def test_json_is_utf8_readable() -> None:
    payload = json.loads(STRATAGEM_DB.read_text(encoding="utf-8"))
    assert payload["count"] == len(payload["stratagems"])
