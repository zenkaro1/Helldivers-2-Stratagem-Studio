"""Add rough radius / armor-penetration / trait data to stratagems.json.

Values are approximations for the UI (radius in metres, AP on the in-game
1-10 scale).  They can be corrected in data/stratagems.json at any time.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "stratagems.json"

# id: (radius, ap, traits)
STATS: dict[str, tuple[int | None, int | None, list[str]]] = {
    # -- orbital -----------------------------------------------------
    "orbital_precision_strike": (6, 6, ["Explosiv", "Panzerbrechend"]),
    "orbital_gatling_barrage": (16, 3, ["Sperrfeuer", "Automatik"]),
    "orbital_airburst_strike": (18, 3, ["Explosiv"]),
    "orbital_120mm_he_barrage": (30, 4, ["Sperrfeuer", "Explosiv"]),
    "orbital_380mm_he_barrage": (60, 5, ["Sperrfeuer", "Explosiv"]),
    "orbital_walking_barrage": (40, 5, ["Sperrfeuer", "Explosiv"]),
    "orbital_laser": (12, 6, ["Laser", "Gelenkt"]),
    "orbital_railcannon_strike": (5, 8, ["Panzerbrechend"]),
    "orbital_ems_strike": (18, 0, ["EMP"]),
    "orbital_smoke_strike": (18, 0, ["Rauch"]),
    "orbital_gas_strike": (20, 0, ["Gas"]),
    "orbital_napalm_barrage": (45, 3, ["Napalm", "Sperrfeuer"]),
    "orbital_confetti": (25, 2, ["Explosiv"]),
    # -- eagle -------------------------------------------------------
    "eagle_500kg_bomb": (30, 7, ["Explosiv", "Panzerbrechend"]),
    "eagle_airstrike": (24, 5, ["Explosiv"]),
    "eagle_cluster_bomb": (32, 3, ["Streumunition"]),
    "eagle_napalm_airstrike": (28, 3, ["Napalm"]),
    "eagle_110mm_rocket_pods": (18, 5, ["Gelenkt"]),
    "eagle_smoke_strike": (24, 0, ["Rauch"]),
    "eagle_strafing_run": (10, 3, ["Automatik"]),
    "eagle_fly_by": (14, 3, ["Automatik"]),
    "eagle_gas_airstrike": (26, 0, ["Gas"]),
    # -- support weapons ---------------------------------------------
    "gr_8_recoilless_rifle": (None, 7, ["Panzerbrechend", "Einzelschuss"]),
    "eat_17_expendable_anti_tank": (None, 7, ["Panzerbrechend", "Einweg"]),
    "eat_411_leveller": (None, 7, ["Panzerbrechend", "Einweg"]),
    "eat_700_expendable_napalm": (None, 4, ["Napalm", "Einweg"]),
    "faf_14_spear": (None, 8, ["Gelenkt", "Panzerbrechend"]),
    "ms_11_solo_silo": (None, 8, ["Gelenkt", "Panzerbrechend"]),
    "ac_8_autocannon": (None, 5, ["Automatik"]),
    "rs_422_railgun": (None, 8, ["Panzerbrechend"]),
    "las_98_laser_cannon": (None, 6, ["Laser"]),
    "las_99_quasar_cannon": (None, 7, ["Panzerbrechend", "Laser"]),
    "las_44_nova": (None, 5, ["Laser"]),
    "mg_43_machine_gun": (None, 3, ["Automatik"]),
    "mg_206_heavy_machine_gun": (None, 4, ["Automatik"]),
    "m_1000_maxigun": (None, 4, ["Automatik"]),
    "mgx_42_bullet_storm": (None, 3, ["Automatik"]),
    "arc_3_arc_thrower": (None, 4, ["Elektro"]),
    "flam_40_flamethrower": (None, 2, ["Feuer"]),
    "40_k_meltagun": (None, 6, ["Feuer", "Panzerbrechend"]),
    "apw_1_anti_materiel_rifle": (None, 6, ["Panzerbrechend"]),
    "amw_20_apex": (None, 6, ["Panzerbrechend"]),
    "gl_21_grenade_launcher": (None, 4, ["Explosiv"]),
    "gl_28_belt_fed_grenade_launcher": (None, 4, ["Explosiv", "Automatik"]),
    "gl_52_de_escalator": (None, 4, ["Explosiv"]),
    "rl_77_airburst_rocket_launcher": (None, 4, ["Explosiv", "Gelenkt"]),
    "mls_4x_commando": (None, 6, ["Gelenkt"]),
    "sta_x3_w_a_s_p_launcher": (None, 5, ["Gelenkt"]),
    "tx_41_sterilizer": (None, 1, ["Gas"]),
    "plas_45_epoch": (None, 6, ["Explosiv", "Laser"]),
    "s_11_speargun": (None, 7, ["Panzerbrechend"]),
    "cqc_1_one_true_flag": (None, 2, ["Nahkampf"]),
    "cqc_20_breaching_hammer": (None, 3, ["Nahkampf"]),
    "cqc_9_defoliation_tool": (None, 2, ["Nahkampf", "Feuer"]),
    # -- sentries ----------------------------------------------------
    "a_g_16_gatling_sentry": (None, 3, ["Automatik"]),
    "a_mg_43_machine_gun_sentry": (None, 3, ["Automatik"]),
    "a_ac_8_autocannon_sentry": (None, 5, ["Automatik"]),
    "a_mls_4x_rocket_sentry": (None, 5, ["Gelenkt"]),
    "a_las_98_laser_sentry": (None, 6, ["Laser"]),
    "a_flam_40_flame_sentry": (None, 2, ["Feuer"]),
    "a_arc_3_tesla_tower": (None, 4, ["Elektro"]),
    "a_m_12_mortar_sentry": (None, 4, ["Explosiv", "Indirekt"]),
    "a_m_23_ems_mortar_sentry": (None, 0, ["EMP", "Indirekt"]),
    "a_gm_17_gas_mortar_sentry": (None, 0, ["Gas", "Indirekt"]),
    # -- mines -------------------------------------------------------
    "md_6_anti_personnel_minefield": (None, 2, ["Explosiv"]),
    "md_17_anti_tank_mines": (None, 6, ["Explosiv", "Panzerbrechend"]),
    "md_8_gas_mines": (None, 0, ["Gas"]),
    "md_i4_incendiary_mines": (None, 3, ["Napalm"]),
    # -- emplacements ------------------------------------------------
    "e_at_12_anti_tank_emplacement": (None, 7, ["Panzerbrechend"]),
    "e_gl_21_grenadier_battlement": (None, 4, ["Explosiv"]),
    "e_mg_101_hmg_emplacement": (None, 4, ["Automatik"]),
    "fx_12_shield_generator_relay": (None, 0, ["Schild"]),
    # -- backpacks ---------------------------------------------------
    "sh_32_shield_generator_pack": (None, 0, ["Schild"]),
    "sh_20_ballistic_shield_backpack": (None, 0, ["Schild"]),
    "sh_51_directional_shield": (None, 0, ["Schild"]),
    "ax_ar_23_guard_dog": (None, 3, ["Drohne", "Automatik"]),
    "ax_las_5_rover": (None, 4, ["Drohne", "Laser"]),
    "ax_arc_3_k_9": (None, 4, ["Drohne", "Elektro"]),
    "ax_flam_75_hot_dog": (None, 2, ["Drohne", "Feuer"]),
    "ax_tx_13_dog_breath": (None, 1, ["Drohne", "Gas"]),
    "b_1_supply_pack": (None, 0, ["Versorgung"]),
    "b_100_portable_hellbomb": (None, 8, ["Explosiv", "Panzerbrechend"]),
    "b_md_c4_pack": (None, 6, ["Explosiv"]),
    "b_flam_80_cremator": (None, 3, ["Feuer"]),
    "lift_850_jump_pack": (None, 0, ["Mobilität"]),
    "lift_860_hover_pack": (None, 0, ["Mobilität"]),
    "lift_182_warp_pack": (None, 0, ["Mobilität"]),
    # -- vehicles ----------------------------------------------------
    "exo_45_patriot_exosuit": (None, 4, ["Fahrzeug", "Automatik"]),
    "exo_49_emancipator_exosuit": (None, 7, ["Fahrzeug", "Panzerbrechend"]),
    "exo_51_lumberer_exosuit": (None, 5, ["Fahrzeug", "Automatik"]),
    "exo_55_breakthrough_exosuit": (None, 6, ["Fahrzeug", "Explosiv"]),
    "td_110_maelstrom": (None, 6, ["Fahrzeug", "Panzerbrechend"]),
    "td_220_bastion_mk_xvi": (None, 6, ["Fahrzeug", "Automatik"]),
    "m_102_gunner_frv": (None, 4, ["Fahrzeug", "Automatik"]),
    "m_103_supply_frv": (None, 0, ["Fahrzeug", "Versorgung"]),
    "m_104_incinerator_frv": (None, 4, ["Fahrzeug", "Feuer"]),
    "m_105_stalwart": (None, 2, ["Fahrzeug", "Automatik"]),
    # -- mission -----------------------------------------------------
    "resupply": (None, 0, ["Versorgung"]),
    "reinforce": (None, 0, ["Verstärkung"]),
    "sos_beacon": (None, 0, ["Verstärkung"]),
    "eagle_rearm": (None, 0, ["Eagle"]),
}


def main() -> int:
    payload = json.loads(DB.read_text(encoding="utf-8"))
    items = payload["stratagems"] if isinstance(payload, dict) else payload
    changed = 0
    for item in items:
        stats = STATS.get(item["id"])
        if stats is None:
            continue
        radius, ap, traits = stats
        item["radius"] = radius
        item["ap"] = ap
        item["traits"] = traits
        changed += 1
    DB.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    print(f"updated {changed} of {len(items)} stratagems")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
