"""Data model for stratagems, loadouts and settings."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ARROW_GLYPHS = {"U": "\u2191", "D": "\u2193", "L": "\u2190", "R": "\u2192"}
ARROW_NAMES = {"U": "Oben", "D": "Unten", "L": "Links", "R": "Rechts"}

CATEGORY_META = {
    "orbital": {"label": "Orbital", "color": "#e2544a"},
    "eagle": {"label": "Eagle", "color": "#e8754b"},
    "support": {"label": "Waffe", "color": "#59a9d6"},
    "backpack": {"label": "Rucksack", "color": "#6cc0c9"},
    "vehicle": {"label": "Fahrzeug", "color": "#7fa8d8"},
    "sentry": {"label": "Geschütz", "color": "#8dc55a"},
    "mine": {"label": "Minen", "color": "#a3c25c"},
    "emplacement": {"label": "Stellung", "color": "#7bb36b"},
    "mission": {"label": "Mission", "color": "#f5d13f"},
}

CATEGORY_ORDER = [
    "orbital", "eagle", "support", "backpack", "vehicle",
    "sentry", "mine", "emplacement", "mission",
]

# Side objectives: not tied to a mission, own hotkey each.
SIDE_OBJECTIVES: tuple[tuple[str, str], ...] = (
    ("nux_223_hellbomb", "Hellbomb"),
    ("seaf_artillery", "SEAF-Artillerie"),
    ("eagle_rearm", "Eagle Rearm"),
)


def category_label(key: str) -> str:
    return CATEGORY_META.get(key, {}).get("label", key.title())


def category_color(key: str) -> str:
    return CATEGORY_META.get(key, {}).get("color", "#8f9283")


AP_LABELS = [
    (2, "Leicht"),
    (4, "Mittel"),
    (6, "Schwer"),
    (7, "Tank"),
]


def ap_label(value: int | None) -> str:
    """Human readable armour penetration class for the rough 1-10 value."""
    if not value:
        return ""
    if value >= 8:
        return "Tank II"
    for limit, label in AP_LABELS:
        if value <= limit:
            return label
    return "Tank"


@dataclass(frozen=True, slots=True)
class Stratagem:
    id: str
    name: str
    category: str
    code: str
    cooldown: int | None = None
    unlock_level: int | None = None
    unlock_source: str = ""
    icon: str = ""
    aliases: tuple[str, ...] = ()
    uses: int | None = None
    radius: int | None = None
    ap: int | None = None
    traits: tuple[str, ...] = ()

    @property
    def arrows(self) -> tuple[str, ...]:
        return tuple(self.code)

    @property
    def code_pretty(self) -> str:
        return " ".join(ARROW_GLYPHS[c] for c in self.code)

    @property
    def is_mission(self) -> bool:
        return self.category == "mission"

    @property
    def cooldown_text(self) -> str:
        if not self.cooldown:
            return "kein Cooldown"
        return f"{self.cooldown}s Cooldown"

    @property
    def uses_text(self) -> str:
        return str(self.uses) if self.uses else "—"

    @property
    def level_text(self) -> str:
        return str(self.unlock_level) if self.unlock_level else "—"

    @property
    def ap_text(self) -> str:
        return ap_label(self.ap) or "—"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Stratagem":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            category=str(data.get("category", "mission")),
            code=str(data["code"]),
            cooldown=data.get("cooldown"),
            unlock_level=data.get("unlock_level"),
            unlock_source=str(data.get("unlock_source", "")),
            icon=str(data.get("icon", "")),
            aliases=tuple(data.get("aliases") or ()),
            uses=data.get("uses"),
            radius=data.get("radius"),
            ap=data.get("ap"),
            traits=tuple(data.get("traits") or ()),
        )


@dataclass(frozen=True, slots=True)
class Mission:
    id: str
    name: str
    subtitle: str = ""
    stratagems: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.name} // {self.subtitle}" if self.subtitle else self.name

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mission":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            subtitle=str(data.get("subtitle", "")),
            stratagems=tuple(data.get("stratagems") or ()),
        )


@dataclass(slots=True)
class Loadout:
    name: str = "Mein Loadout"
    slots: list[str | None] = field(default_factory=lambda: [None, None, None, None])
    quick: dict[str, str | None] = field(
        default_factory=lambda: {
            "resupply": "resupply",
            "reinforce": "reinforce",
            "sos_beacon": "sos_beacon",
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "slots": list(self.slots), "quick": dict(self.quick)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Loadout":
        slots = list(data.get("slots") or [])
        slots = (slots + [None] * 4)[:4]
        # Older files could contain the same stratagem in several slots.
        seen: set[str] = set()
        for index, value in enumerate(slots):
            if value is None:
                continue
            if value in seen:
                slots[index] = None
            else:
                seen.add(value)
        quick = dict(data.get("quick") or {})
        return cls(
            name=str(data.get("name") or "Mein Loadout"),
            slots=slots,
            quick={
                "resupply": quick.get("resupply", "resupply"),
                "reinforce": quick.get("reinforce", "reinforce"),
                "sos_beacon": quick.get("sos_beacon", "sos_beacon"),
            },
        )


@dataclass(slots=True)
class MacroSettings:
    menu_key: str = "ctrl"
    direction_scheme: str = "wasd"  # wasd | arrows
    hold_menu: bool = True
    key_hold_ms: int = 25
    key_gap_ms: int = 50
    pre_delay_ms: int = 80
    post_delay_ms: int = 55
    auto_throw: bool = True
    throw_delay_ms: int = 150
    input_mode: str = "scancode"  # scancode | vk
    dry_run: bool = False
    block_on_cooldown: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "MacroSettings":
        data = data or {}
        default = cls()
        return cls(
            menu_key=str(data.get("menu_key", default.menu_key)),
            direction_scheme=str(data.get("direction_scheme", default.direction_scheme)),
            hold_menu=bool(data.get("hold_menu", default.hold_menu)),
            key_hold_ms=int(data.get("key_hold_ms", default.key_hold_ms)),
            key_gap_ms=int(data.get("key_gap_ms", default.key_gap_ms)),
            pre_delay_ms=int(data.get("pre_delay_ms", default.pre_delay_ms)),
            post_delay_ms=int(data.get("post_delay_ms", default.post_delay_ms)),
            auto_throw=bool(data.get("auto_throw", default.auto_throw)),
            throw_delay_ms=int(data.get("throw_delay_ms", default.throw_delay_ms)),
            input_mode=str(data.get("input_mode", default.input_mode)),
            dry_run=bool(data.get("dry_run", default.dry_run)),
            block_on_cooldown=bool(data.get("block_on_cooldown",
                                           default.block_on_cooldown)),
        )


@dataclass(slots=True)
class VoiceSettings:
    enabled: bool = True
    ptt_key: str = "f8"
    device: int | None = None
    backend: str = "local"  # local | openai
    model: str = "small"
    language: str = "de"  # de | en | auto
    threshold: float = 0.62
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"
    api_model: str = "whisper-1"
    only_loadout: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VoiceSettings":
        data = data or {}
        default = cls()
        device = data.get("device", default.device)
        return cls(
            enabled=bool(data.get("enabled", default.enabled)),
            ptt_key=str(data.get("ptt_key", default.ptt_key)),
            device=int(device) if device is not None else None,
            backend=str(data.get("backend", default.backend)),
            model=str(data.get("model", default.model)),
            language=str(data.get("language", default.language)),
            threshold=float(data.get("threshold", default.threshold)),
            api_key=str(data.get("api_key", default.api_key)),
            api_base=str(data.get("api_base", default.api_base)),
            api_model=str(data.get("api_model", default.api_model)),
            only_loadout=bool(data.get("only_loadout", default.only_loadout)),
        )


@dataclass(slots=True)
class HotkeySettings:
    enabled: bool = True
    slots: list[str] = field(default_factory=lambda: ["f1", "f2", "f3", "f4"])
    quick: dict[str, str] = field(
        default_factory=lambda: {"resupply": "f5", "reinforce": "f6"}
    )
    # Position based: mission stratagem 1..3 keep their key for every mission.
    mission_slots: list[str] = field(default_factory=lambda: ["f9", "f10", "f11"])
    # Side objectives are not tied to a mission and get their own keys.
    side: dict[str, str] = field(
        default_factory=lambda: {
            "nux_223_hellbomb": "f7",
            "seaf_artillery": "ctrl+f7",
            "eagle_rearm": "shift+f7",
        }
    )

    # Free slots: event stratagems that are not part of the loadout.
    extra: list[str] = field(default_factory=lambda: ["f12", "shift+f12"])

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "HotkeySettings":
        data = data or {}
        default = cls()
        slots = list(data.get("slots") or default.slots)
        slots = (slots + [""] * 4)[:4]
        quick = dict(default.quick)
        quick.update(data.get("quick") or {})
        mission_slots = list(data.get("mission_slots") or default.mission_slots)
        mission_slots = (mission_slots + [""] * 3)[:3]
        side = dict(default.side)
        side.update({str(k): str(v) for k, v in (data.get("side") or {}).items()})
        extra = list(data.get("extra") or default.extra)
        extra = (extra + [""] * 2)[:2]
        return cls(enabled=bool(data.get("enabled", True)), slots=slots, quick=quick,
                   mission_slots=mission_slots, side=side, extra=extra)


@dataclass(frozen=True, slots=True)
class ShipModule:
    """A Super Destroyer module that changes cooldowns or Eagle uses."""

    id: str
    name: str
    section: str
    effect: str  # cooldown | eagle_uses
    value: float
    targets: tuple[str, ...] = ()
    note: str = ""

    def applies_to(self, stratagem: "Stratagem") -> bool:
        if "all" in self.targets:
            return True
        if stratagem.category in self.targets:
            return True
        return stratagem.id in self.targets

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShipModule":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            section=str(data.get("section", "")),
            effect=str(data.get("effect", "cooldown")),
            value=float(data.get("value", 0)),
            targets=tuple(data.get("targets") or ()),
            note=str(data.get("note", "")),
        )


def effective_cooldown(base: int | None, stratagem: Stratagem,
                       modules: tuple[ShipModule, ...]) -> int | None:
    """Apply all installed cooldown modules multiplicatively."""
    if not base:
        return base
    factor = 1.0
    for module in modules:
        if module.effect == "cooldown" and module.applies_to(stratagem):
            factor *= max(0.0, 1.0 - module.value / 100.0)
    return max(1, round(base * factor))


def effective_uses(base: int | None, stratagem: Stratagem,
                   modules: tuple[ShipModule, ...]) -> int | None:
    if base is None:
        return None
    total = base
    for module in modules:
        if module.effect == "eagle_uses" and module.applies_to(stratagem):
            total += int(module.value)
    return total


@dataclass(slots=True)
class AppSettings:
    macro: MacroSettings = field(default_factory=MacroSettings)
    voice: VoiceSettings = field(default_factory=VoiceSettings)
    hotkeys: HotkeySettings = field(default_factory=HotkeySettings)
    active_loadout: str = "default"
    active_mission: str = "none"
    favorites: list[str] = field(default_factory=list)
    recent: list[str] = field(default_factory=list)
    favorite_kits: list[str] = field(default_factory=list)
    ship_modules: list[str] = field(default_factory=list)
    custom_aliases: dict[str, list[str]] = field(default_factory=dict)
    extra_stratagems: list[str | None] = field(
        default_factory=lambda: [None, None])
    show_overlay: bool = True
    minimize_to_tray: bool = True
    notifications: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "macro": asdict(self.macro),
            "voice": asdict(self.voice),
            "hotkeys": {
                "enabled": self.hotkeys.enabled,
                "slots": list(self.hotkeys.slots),
                "quick": dict(self.hotkeys.quick),
                "mission_slots": list(self.hotkeys.mission_slots),
                "side": dict(self.hotkeys.side),
                "extra": list(self.hotkeys.extra),
            },
            "active_loadout": self.active_loadout,
            "active_mission": self.active_mission,
            "favorites": list(self.favorites),
            "recent": list(self.recent),
            "favorite_kits": list(self.favorite_kits),
            "ship_modules": list(self.ship_modules),
            "custom_aliases": {key: list(value)
                               for key, value in self.custom_aliases.items()},
            "extra_stratagems": list(self.extra_stratagems),
            "show_overlay": self.show_overlay,
            "minimize_to_tray": self.minimize_to_tray,
            "notifications": self.notifications,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AppSettings":
        data = data or {}
        return cls(
            macro=MacroSettings.from_dict(data.get("macro")),
            voice=VoiceSettings.from_dict(data.get("voice")),
            hotkeys=HotkeySettings.from_dict(data.get("hotkeys")),
            active_loadout=str(data.get("active_loadout", "default")),
            active_mission=str(data.get("active_mission", "none")),
            favorites=[str(item) for item in (data.get("favorites") or [])],
            recent=[str(item) for item in (data.get("recent") or [])],
            favorite_kits=[str(item) for item in (data.get("favorite_kits") or [])],
            ship_modules=[str(item) for item in (data.get("ship_modules") or [])],
            custom_aliases={
                str(key): [str(word) for word in (value or [])]
                for key, value in (data.get("custom_aliases") or {}).items()
            },
            extra_stratagems=(
                (list(data.get("extra_stratagems") or []) + [None, None])[:2]),
            show_overlay=bool(data.get("show_overlay", True)),
            minimize_to_tray=bool(data.get("minimize_to_tray", True)),
            notifications=bool(data.get("notifications", True)),
        )


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
