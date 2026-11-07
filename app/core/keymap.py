"""Windows key/scan-code definitions shared by the macro engine and the UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeyDef:
    scan: int
    vk: int
    extended: bool = False


def _letters() -> dict[str, KeyDef]:
    # (scan code, virtual key) pairs for the US layout, letters are layout-stable.
    table = {
        "q": (0x10, 0x51), "w": (0x11, 0x57), "e": (0x12, 0x45), "r": (0x13, 0x52),
        "t": (0x14, 0x54), "z": (0x2C, 0x5A), "u": (0x16, 0x55), "i": (0x17, 0x49),
        "o": (0x18, 0x4F), "p": (0x19, 0x50), "a": (0x1E, 0x41), "s": (0x1F, 0x53),
        "d": (0x20, 0x44), "f": (0x21, 0x46), "g": (0x22, 0x47), "h": (0x23, 0x48),
        "j": (0x24, 0x4A), "k": (0x25, 0x4B), "l": (0x26, 0x4C), "y": (0x15, 0x59),
        "x": (0x2D, 0x58), "c": (0x2E, 0x43), "v": (0x2F, 0x56), "b": (0x30, 0x42),
        "n": (0x31, 0x4E), "m": (0x32, 0x4D),
    }
    return {name: KeyDef(scan, vk) for name, (scan, vk) in table.items()}


KEYS: dict[str, KeyDef] = {
    **_letters(),
    "1": KeyDef(0x02, 0x31), "2": KeyDef(0x03, 0x32), "3": KeyDef(0x04, 0x33),
    "4": KeyDef(0x05, 0x34), "5": KeyDef(0x06, 0x35), "6": KeyDef(0x07, 0x36),
    "7": KeyDef(0x08, 0x37), "8": KeyDef(0x09, 0x38), "9": KeyDef(0x0A, 0x39),
    "0": KeyDef(0x0B, 0x30),
    "up": KeyDef(0x48, 0x26, True),
    "down": KeyDef(0x50, 0x28, True),
    "left": KeyDef(0x4B, 0x25, True),
    "right": KeyDef(0x4D, 0x27, True),
    "space": KeyDef(0x39, 0x20),
    "tab": KeyDef(0x0F, 0x09),
    "enter": KeyDef(0x1C, 0x0D, True),
    "esc": KeyDef(0x01, 0x1B),
    "shift": KeyDef(0x2A, 0x10),
    "ctrl": KeyDef(0x1D, 0x11),
    "alt": KeyDef(0x38, 0x12),
    "f1": KeyDef(0x3B, 0x70), "f2": KeyDef(0x3C, 0x71), "f3": KeyDef(0x3D, 0x72),
    "f4": KeyDef(0x3E, 0x73), "f5": KeyDef(0x3F, 0x74), "f6": KeyDef(0x40, 0x75),
    "f7": KeyDef(0x41, 0x76), "f8": KeyDef(0x42, 0x77), "f9": KeyDef(0x43, 0x78),
    "f10": KeyDef(0x44, 0x79), "f11": KeyDef(0x57, 0x7A), "f12": KeyDef(0x58, 0x7B),
    "f13": KeyDef(0x64, 0x7C), "f14": KeyDef(0x65, 0x7D), "f15": KeyDef(0x66, 0x7E),
    "f16": KeyDef(0x67, 0x7F), "f17": KeyDef(0x68, 0x80), "f18": KeyDef(0x69, 0x81),
    "f19": KeyDef(0x6A, 0x82), "f20": KeyDef(0x6B, 0x83), "f21": KeyDef(0x6C, 0x84),
    "f22": KeyDef(0x6D, 0x85), "f23": KeyDef(0x6E, 0x86), "f24": KeyDef(0x6F, 0x87),
}

DIRECTION_SCHEMES: dict[str, dict[str, str]] = {
    "wasd": {"U": "w", "D": "s", "L": "a", "R": "d"},
    "arrows": {"U": "up", "D": "down", "L": "left", "R": "right"},
}

KEY_LABELS = {
    "up": "\u2191", "down": "\u2193", "left": "\u2190", "right": "\u2192",
    "ctrl": "STRG", "shift": "SHIFT", "alt": "ALT", "space": "LEER",
    "enter": "ENTER", "esc": "ESC", "tab": "TAB",
}


def pretty_key(key: str) -> str:
    if not key:
        return "\u2014"
    parts = []
    for part in key.lower().split("+"):
        part = part.strip()
        parts.append(KEY_LABELS.get(part, part.upper()))
    return "+".join(parts)
