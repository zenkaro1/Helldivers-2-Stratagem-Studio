from __future__ import annotations

import pytest

from app.core.database import StratagemDatabase
from app.core.voice.matcher import VoiceMatcher, normalize, similarity
from app.paths import STRATAGEM_DB


@pytest.fixture(scope="module")
def db() -> StratagemDatabase:
    return StratagemDatabase(STRATAGEM_DB)


@pytest.fixture(scope="module")
def matcher() -> VoiceMatcher:
    return VoiceMatcher(threshold=0.62)


def test_normalizes_numbers_and_units() -> None:
    assert normalize("500 kg") == "500kg"
    assert normalize("Orbital 120 mm HE Barrage") == "orbital 120mm he barrage"


def test_similarity_exact_and_contained() -> None:
    assert similarity("eagle 500kg bomb", "eagle 500kg bomb") == 1.0
    assert similarity("500kg", "eagle 500kg bomb") > 0.85


def test_german_phrase_resolves(matcher: VoiceMatcher, db: StratagemDatabase) -> None:
    match = matcher.match("Adler fünfhundert Kilo Bombe", db.items)
    assert match.stratagem is not None
    assert match.stratagem.id == "eagle_500kg_bomb"
    assert match.score >= 0.62


def test_exact_english(matcher: VoiceMatcher, db: StratagemDatabase) -> None:
    match = matcher.match("eagle airstrike", db.items)
    assert match.stratagem is not None
    assert match.stratagem.id == "eagle_airstrike"


def test_mission_stratagems(matcher: VoiceMatcher, db: StratagemDatabase) -> None:
    assert matcher.match("Nachschub", db.items).stratagem.id == "resupply"
    assert matcher.match("Verstärkung", db.items).stratagem.id == "reinforce"
    assert matcher.match("SOS Bake", db.items).stratagem.id == "sos_beacon"


def test_mixed_language(matcher: VoiceMatcher, db: StratagemDatabase) -> None:
    match = matcher.match("Orbitaler Laser", db.items)
    assert match.stratagem is not None
    assert match.stratagem.id == "orbital_laser"


def test_short_spoken_name(matcher: VoiceMatcher, db: StratagemDatabase) -> None:
    match = matcher.match("380er Sperrfeuer", db.items)
    assert match.stratagem is not None
    assert match.stratagem.id == "orbital_380mm_he_barrage"


def test_slot_commands(matcher: VoiceMatcher, db: StratagemDatabase) -> None:
    match = matcher.match("Slot zwei", db.items)
    assert match.slot == 2
    assert match.stratagem is None


def test_unknown_is_rejected(matcher: VoiceMatcher, db: StratagemDatabase) -> None:
    match = matcher.match("foo bar baz", db.items)
    assert match.stratagem is None
    assert not match.ok


def test_threshold_is_configurable(db: StratagemDatabase) -> None:
    strict = VoiceMatcher(threshold=0.99)
    assert strict.match("laser dingens", db.items).stratagem is None
    loose = VoiceMatcher(threshold=0.5)
    assert loose.match("laser dingens", db.items).stratagem is not None
