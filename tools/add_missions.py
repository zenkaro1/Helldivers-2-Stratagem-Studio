"""Add mission catalog and usage counts to the app data."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"C:\Projekte\Website Design\hd2-stratagem-studio")
DATA = ROOT / "data"

MISSIONS = {
    "missions": [
        {"id": "none", "name": "Keine Mission", "subtitle": "Standard-Loadout",
         "stratagems": []},
        {"id": "erdbau", "name": "Erdbau", "subtitle": "Tiefenbohrung",
         "stratagems": ["prospecting_drill", "tectonic_drill", "seismic_probe"]},
        {"id": "flag", "name": "Flagge hissen", "subtitle": "Super Earth Flagge",
         "stratagems": ["super_earth_flag"]},
        {"id": "sssd", "name": "SSSD-Übergabe", "subtitle": "Datenbergung",
         "stratagems": ["sssd_delivery", "nux_223_hellbomb"]},
        {"id": "icbm", "name": "ICBM starten", "subtitle": "Raketensilo",
         "stratagems": ["nux_223_hellbomb", "seaf_artillery"]},
        {"id": "seaf", "name": "SEAF-Artillerie", "subtitle": "Geschützbatterie",
         "stratagems": ["seaf_artillery"]},
        {"id": "hive", "name": "Nestsprengung", "subtitle": "Hive Breaker",
         "stratagems": ["hive_breaker_drill"]},
        {"id": "dark_fluid", "name": "Dunkle Flüssigkeit", "subtitle": "Dark Fluid",
         "stratagems": ["dark_fluid_vessel", "nux_223_hellbomb"]},
    ]
}

USES = {
    "eagle_strafing_run": 3,
    "eagle_airstrike": 3,
    "eagle_cluster_bomb": 2,
    "eagle_napalm_airstrike": 2,
    "eagle_110mm_rocket_pods": 2,
    "eagle_smoke_strike": 3,
    "eagle_500kg_bomb": 1,
}


def main() -> None:
    (DATA / "missions.json").write_text(
        json.dumps(MISSIONS, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    path = DATA / "stratagems.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for entry in payload["stratagems"]:
        entry["uses"] = USES.get(entry["id"])
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print("missions:", len(MISSIONS["missions"]), "| uses set:", len(USES))


if __name__ == "__main__":
    main()
