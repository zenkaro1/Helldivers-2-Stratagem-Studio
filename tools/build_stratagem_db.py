"""Build the raw stratagem database from the community wiki.

Run:  python tools/build_stratagem_db.py
Output: data/stratagems_raw.json (rows as parsed from the wiki tables)

The rendered HTML is the reliable machine-readable source: the wikitext only
transcludes templates, and the arrow codes are <img> tags inside the tables.
"""

from __future__ import annotations

import html as htmllib
import json
import re
import sys
import urllib.request
from pathlib import Path

API = (
    "https://helldivers.wiki.gg/api.php?action=parse&page=Stratagems"
    "&prop=text&format=json&formatversion=2"
)
UA = "hd2-stratagem-studio/0.1 (personal, non-commercial)"

TAG_RE = re.compile(r"<[^>]+>")
ARROW_RE = re.compile(r'alt="Stratagem Arrow (Up|Down|Left|Right)\.svg"')
HEADING_RE = re.compile(r"<h([234])[^>]*>(.*?)</h\1>", re.S)
TABLE_RE = re.compile(r"<table.*?</table>", re.S)
SUBGROUP_RE = re.compile(r"<big><b>(.*?)</b></big>", re.S)


def strip_tags(value: str) -> str:
    text = htmllib.unescape(TAG_RE.sub("", value))
    text = re.sub(r"\[\s*edit[^\]]*\]", "", text)
    text = re.sub(r"\[\s*edit source\s*\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_html() -> str:
    req = urllib.request.Request(API, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.load(resp)
    return payload["parse"]["text"]


def classify(name: str, permit: str) -> str:
    if permit == "Offensive Permit":
        return "orbital" if name.startswith("Orbital") else "eagle"
    if permit == "Defensive Permit":
        if name.startswith("A/"):
            return "sentry"
        if name.startswith("MD-"):
            return "mine"
        return "emplacement"
    if permit == "Supply Permit":
        if re.match(r"^(?:EXO-|TD-|M-1\d\d\s)", name):
            return "vehicle"
        if name.startswith(("B-", "B/", "LIFT-", "SH-", "AX/")):
            return "backpack"
        return "support"
    return "mission"


def parse(html: str) -> list[dict]:
    headings = [
        (m.start(), f"h{m.group(1)}", strip_tags(m.group(2)))
        for m in HEADING_RE.finditer(html)
    ]
    subgroups = [(m.start(), strip_tags(m.group(1))) for m in SUBGROUP_RE.finditer(html)]
    mission_start = html.find("<summary>Mission Stratagems</summary>")

    rows: list[dict] = []
    for table in TABLE_RE.finditer(html):
        start = table.start()
        body = table.group(0)
        first_row = re.search(r"<tr[^>]*>(.*?)</tr>", body, re.S)
        headers = [strip_tags(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", first_row.group(1), re.S)] if first_row else []
        if not headers:
            continue

        def col(name: str, default: int) -> int:
            for i, h in enumerate(headers):
                if h.lower().startswith(name):
                    return i
            return default

        i_name = col("name", 1)
        i_code = col("stratagem code", 2)
        i_cool = col("base cooldown", 3)
        i_level = col("unlock level", -1)
        i_source = col("source", -1)
        ncols = len(headers)

        permit = next((t for p, lvl, t in reversed(headings) if lvl == "h3" and p < start), "")
        is_mission = mission_start != -1 and start > mission_start
        if is_mission:
            permit = "Mission Stratagem"
        subgroup = ""
        if is_mission:
            subgroup = next((t for p, t in reversed(subgroups) if p < start), "")

        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S)[1:]:
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)
            if len(cells) != ncols:
                continue
            name_m = re.search(r'title="([^"]+)"[^>]*>(.*?)</a>', cells[i_name], re.S)
            if not name_m:
                continue
            name = strip_tags(name_m.group(2)) or htmllib.unescape(name_m.group(1))
            arrows = ARROW_RE.findall(cells[i_code])
            if not arrows:
                continue
            icon_m = re.search(r'src="([^"]+\.(?:svg|png)(?:\?[^"]*)?)"', cells[0])
            rows.append(
                {
                    "name": name,
                    "permit": permit,
                    "subgroup": subgroup,
                    "category": classify(name, permit),
                    "code": "".join(a[0] for a in arrows),
                    "cooldown": strip_tags(cells[i_cool]),
                    "level": strip_tags(cells[i_level]) if i_level >= 0 else "",
                    "source": strip_tags(cells[i_source]) if i_source >= 0 else "",
                    "icon": icon_m.group(1) if icon_m else "",
                }
            )
    return rows


def main() -> int:
    html = fetch_html()
    rows = parse(html)
    out = Path(__file__).resolve().parent.parent / "data" / "stratagems_raw.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"parsed {len(rows)} stratagems -> {out}")
    for row in rows:
        print(
            f"{row['category']:11} {row['name'][:40]:40} {row['code']:10} "
            f"{row['cooldown']:>7} lvl {row['level']:>3}  {row['permit'][:9]}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
