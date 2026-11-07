"""Curate data/stratagems_raw.json into the app database and fetch icons.

Run after build_stratagem_db.py:
    python tools/build_db.py [--no-icons]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "stratagems_raw.json"
OUT = ROOT / "data" / "stratagems.json"
ICON_DIR = ROOT / "data" / "icons"
UA = "hd2-stratagem-studio/0.1 (personal, non-commercial)"

SKIP_NAMES = {
    "Call In Super Destroyer",  # wiki easter egg entry, not a real stratagem
}

# German is not an official translation: these are voice aliases so German
# speech ("Adler 500 Kilo") still resolves.  Users may edit them in the JSON.
GERMAN_OVERRIDES = {
    "eagle_500kg_bomb": ["adler 500 kg bombe", "500 kg bombe", "fünfhundert kilo bombe", "500er bombe"],
    "eagle_110mm_rocket_pods": ["adler raketen", "raketenpod", "110er raketen"],
    "eagle_airstrike": ["adler luftschlag", "luftschlag"],
    "eagle_strafing_run": ["adler bordwaffenangriff", "bordwaffenangriff"],
    "eagle_cluster_bomb": ["adler streubombe", "streubombe"],
    "eagle_napalm_airstrike": ["adler napalm luftschlag", "napalm luftschlag"],
    "eagle_smoke_strike": ["adler rauchschlag", "rauchschlag"],
    "eagle_rearm": ["adler aufmunitionieren", "aufmunitionieren", "rearm"],
    "orbital_laser": ["orbitaler laser", "laser"],
    "orbital_railcannon_strike": ["orbitaler railgun schlag", "railcannon"],
    "orbital_380mm_he_barrage": ["380er sperrfeuer", "380 mm sperrfeuer", "dreihundertachtzig"],
    "orbital_120mm_he_barrage": ["120er sperrfeuer", "120 mm sperrfeuer"],
    "orbital_napalm_barrage": ["napalm sperrfeuer", "orbitales napalm"],
    "orbital_gatling_barrage": ["gatling sperrfeuer", "gatling"],
    "orbital_airburst_strike": ["luftburst", "orbitaler luftburst"],
    "orbital_precision_strike": ["präzisionsschlag", "präzision"],
    "orbital_walking_barrage": ["laufendes sperrfeuer", "wanderndes sperrfeuer"],
    "orbital_gas_strike": ["gasschlag", "gassperrfeuer"],
    "orbital_smoke_strike": ["rauchschlag", "orbitaler rauch"],
    "orbital_ems_strike": ["ems schlag", "ems"],
    "resupply": ["nachschub", "versorgung", "resupply"],
    "reinforce": ["verstärkung", "reinforce", "verstärkung rufen"],
    "sos_beacon": ["sos bake", "sos signal", "notsignal", "sos"],
    "nux_223_hellbomb": ["höllenbombe", "hellbomb"],
    "seaf_artillery": ["seaf artillerie", "artillerie"],
    "mg_43_machine_gun": ["maschinengewehr", "mg 43"],
    "m_105_stalwart": ["stalwart"],
    "mg_206_heavy_machine_gun": ["schweres maschinengewehr", "hmg"],
    "ac_8_autocannon": ["autokanone", "autocannon"],
    "gr_8_recoilless_rifle": ["rückstoßfreies gewehr", "recoilless"],
    "eat_17_expendable_anti_tank": ["einweg panzerabwehr", "eat", "panzerfaust"],
    "flam_40_flamethrower": ["flammenwerfer"],
    "gl_21_grenade_launcher": ["granatwerfer"],
    "arc_3_arc_thrower": ["blitzwerfer", "arc werfer"],
    "las_98_laser_cannon": ["laserkanone"],
    "las_99_quasar_cannon": ["quasar kanone", "quasar"],
    "faf_14_spear": ["speer", "spear"],
    "rs_422_railgun": ["railgun"],
    "sh_32_shield_generator_pack": ["schildgenerator", "schild rucksack", "schildpaket"],
    "sh_20_ballistic_shield_backpack": ["ballistischer schild", "schildrucksack"],
    "lift_850_jump_pack": ["sprungpaket", "jump pack", "sprung rucksack"],
    "b_1_supply_pack": ["nachschubpaket", "supply pack"],
    "ax_ar_23_guard_dog": ["wachhund", "guard dog"],
    "a_mg_43_machine_gun_sentry": ["maschinengewehr geschütz", "mg geschütz"],
    "a_g_16_gatling_sentry": ["gatling geschütz"],
    "a_ac_8_autocannon_sentry": ["autokanone geschütz"],
    "a_m_12_mortar_sentry": ["mörser", "mörsergeschütz"],
    "a_mls_4x_rocket_sentry": ["raketengeschütz"],
    "a_arc_3_tesla_tower": ["tesla turm", "tesla"],
    "e_mg_101_hmg_emplacement": ["hmg stellung", "schwere mg stellung"],
    "e_at_12_anti_tank_emplacement": ["panzerabwehrstellung"],
    "md_6_anti_personnel_minefield": ["minenfeld", "antipersonenminen"],
    "md_17_anti_tank_mines": ["panzerabwehrminen", "panzerminen"],
    "exo_45_patriot_exosuit": ["patriot exoanzug", "exoanzug", "mech"],
    "exo_49_emancipator_exosuit": ["emanzipator exoanzug"],
    "m_102_gunner_frv": ["gunner fahrzeug", "frv"],
    "oribital_illumination_flare": [],
}

# Word level fallback translation used to synthesise a German alias for every
# entry, so a full German sentence has a chance to fuzzy-match.
TERMS = {
    "eagle": "adler", "orbital": "orbital", "strike": "schlag", "barrage": "sperrfeuer",
    "bomb": "bombe", "airstrike": "luftschlag", "run": "angriff", "cluster": "streu",
    "napalm": "napalm", "smoke": "rauch", "gas": "gas", "laser": "laser",
    "walking": "laufend", "gatling": "gatling", "airburst": "luftburst",
    "precision": "präzision", "railcannon": "railgun", "machine": "maschinen",
    "gun": "gewehr", "heavy": "schwer", "grenade": "granat", "launcher": "werfer",
    "rocket": "rakete", "pods": "raketen", "autocannon": "autokanone",
    "flamethrower": "flammenwerfer", "recoilless": "rückstoßfrei", "rifle": "gewehr",
    "expendable": "einweg", "spear": "speer", "stalwart": "stalwart",
    "quasar": "quasar", "commando": "kommando", "sentry": "geschütz",
    "tower": "turm", "mortar": "mörser", "emplacement": "stellung", "mines": "minen",
    "minefield": "minenfeld", "shield": "schild", "generator": "generator",
    "relay": "relais", "backpack": "rucksack", "pack": "paket", "supply": "nachschub",
    "jump": "sprung", "hover": "schwebe", "guard": "wach", "dog": "hund",
    "rover": "rover", "exosuit": "exoanzug", "vehicle": "fahrzeug", "drill": "bohrer",
    "probe": "sonde", "flag": "flagge", "artillery": "artillerie", "beacon": "bake",
    "rearm": "aufmunitionieren", "reinforce": "verstärkung", "resupply": "nachschub",
    "hellbomb": "höllenbombe", "tectonic": "tektonisch", "seismic": "seismisch",
    "aquifer": "grundwasser", "hive": "nest", "dark": "dunkel", "fluid": "flüssigkeit",
    "data": "daten", "upload": "hochladen", "extraction": "extraktion",
    "activate": "aktivieren", "earth": "erde", "illumination": "beleuchtung",
    "flare": "leuchtfackel", "break": "brechen", "anti": "anti", "tank": "panzer",
    "personnel": "personen", "tesla": "tesla", "directional": "gerichtet",
    "ballistic": "ballistisch", "mine": "mine", "support": "unterstützung",
    "weapon": "waffe", "system": "system", "patriot": "patriot",
    "emancipator": "emanzipator", "breakthrough": "durchbruch", "lumberer": "holzfäller",
    "apex": "apex", "epoch": "epoche", "speargun": "speerpistole", "leveller": "nivellierer",
    "sterilizer": "sterilisator", "cremator": "einäscherer", "defoliation": "entlaubung",
    "one": "eine", "true": "wahre", "silo": "silo", "maxigun": "maxigun",
}

DROP_KEYS = {"unavailable"}


def slug(name: str) -> str:
    text = name.lower()
    text = text.replace("&", " and ").replace("+", " plus ")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def parse_seconds(value: str) -> int | None:
    m = re.match(r"^([\d.]+)\s*s?", value.strip())
    if not m:
        return None
    return int(float(m.group(1)))


def auto_german(name: str) -> str:
    words = re.findall(r"[A-Za-zÄÖÜäöüß0-9/+-]+", name)
    out = []
    for word in words:
        low = word.lower()
        out.append(TERMS.get(low, low))
    return " ".join(out)


def short_alias(name: str) -> str:
    """'MG-43 Machine Gun' -> 'machine gun'."""
    return re.sub(r"^(?:[A-Z]{1,4}[/-]?[A-Z0-9-]*\d+|[A-Z]{2,4}/)\s+", "", name).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-icons", action="store_true")
    args = parser.parse_args()

    rows = json.loads(RAW.read_text(encoding="utf-8"))
    curated: list[dict] = []
    seen: dict[str, dict] = {}

    for row in rows:
        if row["subgroup"].lower() in DROP_KEYS:
            continue
        if row["name"] in SKIP_NAMES:
            continue
        sid = slug(row["name"])
        if sid in seen:
            seen[sid].setdefault("alt_codes", []).append(row["code"])
            continue
        icon_name = Path(row["icon"].split("?")[0]).name
        entry = {
            "id": sid,
            "name": row["name"],
            "category": row["category"],
            "code": row["code"],
            "cooldown": parse_seconds(row["cooldown"]),
            "unlock_level": parse_seconds(row["level"]),
            "unlock_source": row["source"],
            "icon": f"icons/{sid}.svg",
            "icon_source": row["icon"],
            "aliases": [],
        }
        curated.append(entry)
        seen[sid] = entry

    for entry in curated:
        aliases = {entry["name"].lower(), auto_german(entry["name"])}
        short = short_alias(entry["name"])
        if short and short.lower() != entry["name"].lower():
            aliases.add(short.lower())
        aliases.update(GERMAN_OVERRIDES.get(entry["id"], []))
        entry["aliases"] = sorted({a for a in aliases if a})

    curated.sort(key=lambda e: (CATEGORY_ORDER.index(e["category"]), e["name"]))
    payload = {
        "version": 1,
        "source": "https://helldivers.wiki.gg/wiki/Stratagems",
        "note": "aliases are voice hints (German ones are approximate, not official)",
        "count": len(curated),
        "stratagems": curated,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(curated)} stratagems -> {OUT}")

    if args.no_icons:
        return 0

    ICON_DIR.mkdir(parents=True, exist_ok=True)
    missing = []
    for entry in curated:
        target = ROOT / "data" / entry["icon"]
        if target.exists() and target.stat().st_size > 200:
            continue
        url = "https://helldivers.wiki.gg" + entry["icon_source"]
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                target.write_bytes(resp.read())
        except (urllib.error.URLError, OSError) as exc:
            missing.append((entry["name"], str(exc)))
    print(f"icons: {len(curated) - len(missing)} ok, {len(missing)} missing")
    for name, exc in missing:
        print("  missing:", name, exc)
    return 0


CATEGORY_ORDER = [
    "orbital", "eagle", "support", "backpack", "vehicle",
    "sentry", "mine", "emplacement", "mission",
]

if __name__ == "__main__":
    sys.exit(main())
