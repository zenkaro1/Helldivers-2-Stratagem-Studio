"""Find and fix double-encoded UTF-8 (mojibake) in project text files."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".venv", ".tmp", "dist", "build", "userdata", "__pycache__", ".git"}
SUFFIXES = {".md", ".txt", ".py", ".json", ".cmd", ".yml", ".yaml", ".ini"}
MARKERS = ("Ã", "â€", "Â")


def repair(text: str) -> str:
    fixed_lines = []
    for line in text.splitlines(keepends=True):
        if any(marker in line for marker in MARKERS):
            for encoding in ("cp1252", "latin-1"):
                try:
                    line = line.encode(encoding).decode("utf-8")
                    break
                except (UnicodeEncodeError, UnicodeDecodeError):
                    continue
        fixed_lines.append(line)
    return "".join(fixed_lines)


def main() -> int:
    fix = "--fix" in sys.argv
    total = 0
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP for part in path.parts):
            continue
        if path.suffix.lower() not in SUFFIXES:
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if not any(marker in original for marker in MARKERS):
            continue
        updated = repair(original)
        hits = sum(original.count(marker) for marker in MARKERS)
        total += 1
        print(f"{hits:5}  {path.relative_to(ROOT)}")
        if fix and updated != original:
            path.write_text(updated, encoding="utf-8")
    print(f"\n{total} Datei(en) betroffen" + (" - repariert." if fix else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
