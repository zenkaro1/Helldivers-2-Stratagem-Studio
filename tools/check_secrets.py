"""Scan tracked files for secrets before publishing."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", re.I),
]

files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                       check=True).stdout.splitlines()
hits = 0
for name in files:
    path = ROOT / name
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    for pattern in PATTERNS:
        for match in pattern.finditer(text):
            hits += 1
            print(f"{name}: {match.group(0)[:40]}")
print(f"{hits} Treffer")
