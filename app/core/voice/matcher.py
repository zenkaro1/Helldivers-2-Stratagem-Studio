"""Turn a spoken transcript into a stratagem (or a slot command).

Matching happens on a normalised, German-to-English folded representation, so
"adler fünfhundert kilo bombe" and "eagle 500kg bomb" both resolve to the same
entry.  Everything is pure Python and unit tested.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from ..models import Stratagem

UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})

# Multi-word phrases first, then single tokens.
PHRASES = {
    "praezisionsschlag": "precision strike",
    "praezision": "precision",
    "rauchschlag": "smoke strike",
    "gasschlag": "gas strike",
    "gassperrfeuer": "gas strike",
    "luftschlag": "airstrike",
    "streubombe": "cluster bomb",
    "raketenpod": "rocket pods",
    "raketen": "rocket",
    "maschinengewehr": "machine gun",
    "schweres maschinengewehr": "heavy machine gun",
    "autokanone": "autocannon",
    "granatwerfer": "grenade launcher",
    "flammenwerfer": "flamethrower",
    "rueckstossfreies gewehr": "recoilless rifle",
    "rueckstossfrei": "recoilless",
    "einweg panzerabwehr": "expendable anti tank",
    "panzerabwehr": "anti tank",
    "panzerfaust": "eat",
    "blitzwerfer": "arc thrower",
    "laserkanone": "laser cannon",
    "schildgenerator": "shield generator",
    "schild rucksack": "shield backpack",
    "schildpaket": "shield pack",
    "sprungpaket": "jump pack",
    "sprung rucksack": "jump pack",
    "wachhund": "guard dog",
    "moersergeschuetz": "mortar sentry",
    "moerser": "mortar",
    "maschinengewehr geschuetz": "machine gun sentry",
    "gatling geschuetz": "gatling sentry",
    "raketengeschuetz": "rocket sentry",
    "tesla turm": "tesla tower",
    "hmg stellung": "hmg emplacement",
    "panzerabwehrstellung": "anti tank emplacement",
    "minenfeld": "minefield",
    "antipersonenminen": "anti personnel minefield",
    "panzerabwehrminen": "anti tank mines",
    "panzerminen": "anti tank mines",
    "exoanzug": "exosuit",
    "mech": "exosuit",
    "fahrzeug": "vehicle",
    "aufmunitionieren": "rearm",
    "verstaerkung": "reinforce",
    "hoellenbombe": "hellbomb",
    "nachschubpaket": "supply pack",
    "nachschub": "resupply",
    "versorgung": "resupply",
    "sos bake": "sos beacon",
    "sos signal": "sos beacon",
    "notsignal": "sos beacon",
}

TOKENS = {
    "adler": "eagle",
    "orbital": "orbital",
    "sperrfeuer": "barrage",
    "schlag": "strike",
    "bombe": "bomb",
    "angriff": "run",
    "streu": "cluster",
    "rauch": "smoke",
    "gas": "gas",
    "laufend": "walking",
    "wandernd": "walking",
    "luftburst": "airburst",
    "railgun": "railcannon",
    "raid": "railcannon",
    "gewehr": "rifle",
    "speer": "spear",
    "schild": "shield",
    "rucksack": "backpack",
    "paket": "pack",
    "sprung": "jump",
    "geschuetz": "sentry",
    "turm": "tower",
    "stellung": "emplacement",
    "minen": "mines",
    "bohrer": "drill",
    "sonde": "probe",
    "flagge": "flag",
    "artillerie": "artillery",
    "bake": "beacon",
    "tektonisch": "tectonic",
    "seismisch": "seismic",
    "grundwasser": "aquifer",
    "nest": "hive",
    "dunkel": "dark",
    "fluessigkeit": "fluid",
    "daten": "data",
    "hochladen": "upload",
    "extraktion": "extraction",
    "aktivieren": "activate",
    "beleuchtung": "illumination",
    "leuchtfackel": "flare",
    "gerichtet": "directional",
    "ballistisch": "ballistic",
    "unterstuetzung": "support",
    "waffe": "weapon",
    "kilo": "kg",
    "millimeter": "mm",
}

NUMBERS = {
    "fuenfhundert": "500",
    "dreihundertachtzig": "380",
    "dreihundert": "300",
    "einhundertzwanzig": "120",
    "hundertzwanzig": "120",
    "hundertzehn": "110",
    "zweihundert": "200",
    "vierhundert": "400",
    "eins": "1",
    "zwei": "2",
    "drei": "3",
    "vier": "4",
    "fuenf": "5",
}

FILLER = {
    "der", "die", "das", "den", "dem", "ein", "eine", "einen", "bitte", "mal",
    "jetzt", "schnell", "ruf", "rufe", "rufen", "wirf", "werfen", "benutze",
    "nutze", "starte", "mach", "the", "a", "an", "please", "now", "call", "in",
    "use", "throw", "drop", "auf", "den", "los", "komm", "her",
}

SLOT_RE = re.compile(r"\b(?:slot|platz|fach|taste)\s*([1-4])\b")
SLOT_WORDS = {"eins": "1", "zwei": "2", "drei": "3", "vier": "4"}


def fold(text: str) -> str:
    return text.lower().translate(UMLAUTS)


def normalize(text: str) -> str:
    text = fold(text)
    text = re.sub(r"(\d+)\s*(kg|mm)\b", r"\1\2", text)
    text = re.sub(r"[^a-z0-9\s+/-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split()
    words = [NUMBERS.get(w, w) for w in words]
    joined = " ".join(words)
    # phrases, longest first so "sos signal" wins over "signal"
    for phrase in sorted(PHRASES, key=len, reverse=True):
        joined = re.sub(rf"\b{re.escape(phrase)}\b", PHRASES[phrase], joined)
    words = [TOKENS.get(w, w) for w in joined.split()]
    words = [w for w in words if w not in FILLER]
    return " ".join(words).strip()


def similarity(query: str, candidate: str) -> float:
    if not query or not candidate:
        return 0.0
    if query == candidate:
        return 1.0
    # Bare numbers ("380", "120") match the number in a name like "380mm HE".
    if query.isdigit():
        numbers = re.findall(r"\d+", candidate)
        if query in numbers:
            return 0.99
        return SequenceMatcher(None, query, candidate).ratio() * 0.5
    if candidate in query or query in candidate:
        short, long_ = sorted((query, candidate), key=len)
        if len(short) >= 4:
            return 0.90 + 0.10 * (len(short) / len(long_))
    ratio = SequenceMatcher(None, query, candidate).ratio()
    q_tokens, c_tokens = set(query.split()), set(candidate.split())
    if not q_tokens or not c_tokens:
        return ratio
    overlap = len(q_tokens & c_tokens)
    coverage = overlap / len(q_tokens)
    precision = overlap / len(c_tokens)
    token_score = 0.65 * coverage + 0.35 * precision
    return max(ratio, token_score)


@dataclass
class VoiceMatch:
    stratagem: Stratagem | None = None
    score: float = 0.0
    slot: int | None = None
    spoken: str = ""
    normalized: str = ""
    alias: str = ""
    alternatives: list[tuple[str, float]] = field(default_factory=list)
    # Matched, but the stratagem is not part of the active loadout.
    outside_loadout: Stratagem | None = None

    @property
    def ok(self) -> bool:
        return self.stratagem is not None or self.slot is not None


class VoiceMatcher:
    def __init__(self, threshold: float = 0.62):
        self.threshold = threshold
        self._cache: dict[str, list[tuple[str, str]]] = {}
        self._custom: dict[str, list[str]] = {}

    def set_custom_aliases(self, custom: dict[str, list[str]] | None) -> None:
        """User keywords per stratagem id; they win over fuzzy guesses."""
        self._custom = {key: list(value) for key, value in (custom or {}).items()}
        self._cache.clear()

    def _candidates(self, stratagem: Stratagem) -> list[tuple[str, str]]:
        cached = self._cache.get(stratagem.id)
        if cached is None:
            values = {normalize(stratagem.name)}
            values.update(normalize(alias) for alias in stratagem.aliases)
            values.update(normalize(alias) for alias in self._custom.get(stratagem.id, []))
            values.discard("")
            cached = [(normalize(alias), alias) for alias in sorted(values, key=len, reverse=True)]
            self._cache[stratagem.id] = cached
        return cached

    def parse_slot(self, text: str) -> int | None:
        norm = normalize(text)
        match = SLOT_RE.search(norm)
        if match:
            return int(match.group(1))
        words = norm.split()
        for index, word in enumerate(words):
            if word in {"slot", "platz", "fach"} and index + 1 < len(words):
                value = SLOT_WORDS.get(words[index + 1])
                if value:
                    return int(value)
        return None

    def match(self, text: str, candidates: list[Stratagem]) -> VoiceMatch:
        normalized = normalize(text)
        result = VoiceMatch(spoken=text, normalized=normalized)
        if not normalized:
            return result

        slot = self.parse_slot(text)
        if slot is not None and slot == int(slot):
            result.slot = slot
            result.score = 1.0
            return result

        scored: list[tuple[float, Stratagem, str]] = []
        for item in candidates:
            best_score, best_alias = 0.0, ""
            for alias_norm, alias_raw in self._candidates(item):
                score = similarity(normalized, alias_norm)
                if score > best_score:
                    best_score, best_alias = score, alias_raw
            if best_score >= self.threshold * 0.75:
                scored.append((best_score, item, best_alias))

        scored.sort(key=lambda row: row[0], reverse=True)
        result.alternatives = [(item.name, round(score, 3)) for score, item, _ in scored[:4]]
        if not scored:
            return result

        best_score, best_item, best_alias = scored[0]
        if best_score < self.threshold:
            return result
        result.stratagem = best_item
        result.score = round(best_score, 3)
        result.alias = best_alias
        return result
