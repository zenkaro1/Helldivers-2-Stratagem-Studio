"""Curate traits / uses: sentries are always guided, laser has 3 uses."""

from __future__ import annotations

import json
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "stratagems.json"

TRAITS = {
    "a_mls_4x_rocket_sentry": ["Explosiv"],
    "a_ac_8_autocannon_sentry": ["Automatik"],
    "a_g_16_gatling_sentry": ["Automatik"],
    "a_mg_43_machine_gun_sentry": ["Automatik"],
    "a_las_98_laser_sentry": ["Laser"],
    "a_flam_40_flame_sentry": ["Feuer"],
    "a_arc_3_tesla_tower": ["Elektro"],
    "a_m_12_mortar_sentry": ["Explosiv", "Indirekt"],
    "a_m_23_ems_mortar_sentry": ["EMP", "Indirekt"],
    "a_gm_17_gas_mortar_sentry": ["Gas", "Indirekt"],
}
USES = {"orbital_laser": 3}


def main() -> int:
    payload = json.loads(DB.read_text(encoding="utf-8"))
    items = payload["stratagems"] if isinstance(payload, dict) else payload
    for item in items:
        if item["id"] in TRAITS:
            item["traits"] = TRAITS[item["id"]]
        if item["id"] in USES:
            item["uses"] = USES[item["id"]]
    DB.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    print("traits/uses updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
