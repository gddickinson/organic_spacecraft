"""NAVIS metabolism: the ore ratio, the mass ledger and the energy ledger.

Mass: phosphorus sets the digging. Energy: asteroid organics are a fuel
with no oxidiser. The oxidants actually on hand (the intima's spare O2, the
rock's ferric iron, a little sulfate) unlock only a fraction of the power
growth needs; electrolytic O2 costs more than the organics return. The
difference has to be imported (sunlight via an electro-organ: a bet).

Inputs marked ASSUMPTION are the program's own estimates, not sourced data.
"""

from . import constants as C
from .growth import NAVIS_M0, TAU_D, WILD_RMAX, time_to
from .navis import CREW, O2_YIELD_G_M2_D, geometry
from .value import V, collect

SHIP_T = 24_000.0
BONE_MINERAL_T = 2_400.0         # ~10 % of the ship (Compendium)
P_GRADE = 0.001                  # ~0.1 wt% P in carbonaceous chondrite
ORGANIC_C = 0.02                 # >= 2 wt% organic C (CM ~2, CI ~3.5)
O2_PER_C = 1.05                  # mol O2 per mol C, H-poor kerogen-like matter
FE_TOTAL = 0.183                 # CI chondrite Fe, ~18 wt% (Lodders 2003)
FERRIC_SHARE = (0.25, 0.5)       # ASSUMPTION: share of that iron that is Fe(III)
KJ_PER_E_FE3 = 74.0              # Fe3+/Fe2+ (0.77 V) vs organics, acid gut: upper bound
SULFATE_S = (0.0, 0.02)          # ASSUMPTION: S present as sulfate (may be ~0)
KJ_PER_E_SO4 = 6.0               # sulfate reduction at neutral pH, per mol e-
ORGANIC_DEPOSIT_TPD = (4.0, 13.0)  # organic share of the deposit (dry organics .. all)
GROWTH_EFFICIENCY = 0.5          # ASSUMPTION: stored / consumed power in growth
MAINT_MW = 0.1                   # basal upkeep of 24 kt of mostly inert tissue
SUN_TO_CHEM = 0.10               # PV + electrosynthesis, ~10 % (Liu et al. 2016)
RADIATOR_K = (280.0, 320.0)


def mw(joules_per_day):
    return joules_per_day / C.DAY_S / 1e6


def ledger():
    wild_d = time_to(SHIP_T, NAVIS_M0, WILD_RMAX)
    grow = SHIP_T / wild_d                                         # t/day
    p_t = BONE_MINERAL_T * 6 * C.M_P / C.M_HA
    ratio = p_t / P_GRADE / SHIP_T
    rock = ratio * grow
    rock_peak = ratio * WILD_RMAX
    intima = geometry()["area_in"]
    o2_whole = intima * O2_YIELD_G_M2_D / 1e3                      # kg/day
    o2_spare = o2_whole - CREW * C.BVAD_O2_KG
    fuel_mol_c = rock * 1e6 * ORGANIC_C / C.M_C
    fuel = mw(fuel_mol_c * O2_PER_C * C.KJ_PER_MOL_O2_ORGANIC * 1e3)
    o2_for_fuel_t = fuel_mol_c * O2_PER_C * C.M_O2 / 1e6
    elec = mw(o2_for_fuel_t * 1e6 / C.M_O2 * C.KJ_PER_MOL_O2_ELECTROLYSIS * 1e3)
    p_o2 = mw(o2_spare * 1e3 / C.M_O2 * C.KJ_PER_MOL_O2_ORGANIC * 1e3)
    p_fe = [mw(rock * 1e6 * FE_TOTAL * s / C.M_FE * KJ_PER_E_FE3 * 1e3) for s in FERRIC_SHARE]
    p_so4 = [mw(rock * 1e6 * s / C.M_S * 8 * KJ_PER_E_SO4 * 1e3) for s in SULFATE_S]
    chem = (p_o2 + p_fe[0] + p_so4[0], p_o2 + p_fe[1] + p_so4[1])
    stored = [mw(t * 1e3 * C.BIOMASS_MJ_PER_KG * 1e6) for t in ORGANIC_DEPOSIT_TPD]
    need = [s / GROWTH_EFFICIENCY + MAINT_MW for s in stored]
    # tissue energy still missing after the rock's own chemistry, as stored energy
    imp = (stored[0] - GROWTH_EFFICIENCY * chem[1], stored[1] - GROWTH_EFFICIENCY * chem[0])
    heat = [n - s for n, s in zip(need, stored)]
    return dict(grow=grow, p_t=p_t, ratio=ratio, rock=rock, rock_peak=rock_peak,
                photo_t=o2_whole / 1e3 / 1.066, o2_spare=o2_spare, fuel=fuel,
                o2_for_fuel=o2_for_fuel_t, elec=elec, p_o2=p_o2, p_fe=p_fe,
                p_so4=p_so4, chem=chem, stored=stored, need=need, imp=imp, heat=heat,
                intima=intima)


def values():
    d = ledger()
    area = geometry()["area"]
    # SUN_TO_CHEM is sunlight -> new biomass, so it already includes growth losses
    sun_area = [i * 1e6 / (SUN_TO_CHEM * C.S_1AU) for i in d["imp"]]
    rad = (d["heat"][0] * 1e6 / (C.SIGMA * RADIATOR_K[1] ** 4),
           d["heat"][1] * 1e6 / (C.SIGMA * RADIATOR_K[0] ** 4))
    light_area = d["grow"] * 1e6 / O2_YIELD_G_M2_D
    rate_chem = [d["grow"] * c / n for c, n in zip(d["chem"], (d["need"][1], d["need"][0]))]
    years_chem = [time_to(SHIP_T, NAVIS_M0, r) / C.YEAR_D for r in rate_chem]
    kw = dict(
        p_in_bone=V(d["p_t"], "t"), ore_ratio=V(d["ratio"], "x ship mass"),
        ore_total_kt=V(d["ratio"] * SHIP_T / 1e3, "kt"),
        tailings_kt=V((d["ratio"] - 1) * SHIP_T / 1e3, "kt"),
        rock_tpd=V(d["rock"], "t/d", "average over gestation"),
        rock_peak_tpd=V(d["rock_peak"], "t/d", "at the 16 t/day ceiling"),
        tailings_tpd=V(d["rock"] - d["grow"], "t/d"),
        growth_tpd=V(d["grow"], "t/d"),
        photo_tpd=V(d["photo_t"], "t/d", "whole intima lit at ~30 g/m2/d"),
        photo_pct=V(100 * d["photo_t"] / d["grow"], "%"),
        light_area=V(light_area, "m2", "lit area to grow by light alone"),
        light_x_hull=V(light_area / area, "x outer hull"),
        fuel_mw=V(d["fuel"], "MW", "organics' fuel value if fully oxidised"),
        o2_spare_t=V(d["o2_spare"] / 1e3, "t O2/d", "whole intima lit, less the crew's"),
        intima_eff=V(100 * O2_YIELD_G_M2_D / 1.066 * C.BIOMASS_MJ_PER_KG * 1e3 / C.DAY_S
                     / C.S_1AU, "%", "sunlight stored as biomass"),
        o2_for_fuel=V(d["o2_for_fuel"], "t O2/d"),
        elec_mw=V(d["elec"], "MW", "to electrolyse that O2"),
        p_o2_mw=V(d["p_o2"], "MW", "spare intima O2 burns this much", mode="log", tol=0.3),
        p_fe_lo=V(d["p_fe"][0], "MW"), p_fe_hi=V(d["p_fe"][1], "MW"),
        p_so4_hi=V(d["p_so4"][1], "MW"),
        chem_lo=V(d["chem"][0], "MW"), chem_hi=V(d["chem"][1], "MW"),
        stored_lo=V(d["stored"][0], "MW"), stored_hi=V(d["stored"][1], "MW"),
        need_lo=V(d["need"][0], "MW"), need_hi=V(d["need"][1], "MW"),
        import_lo=V(d["imp"][0], "MW", "tissue energy the rock cannot supply"),
        import_hi=V(d["imp"][1], "MW"),
        import_power_lo=V(d["need"][0] - d["chem"][1], "MW", "power import, as consumed"),
        import_power_hi=V(d["need"][1] - d["chem"][0], "MW"),
        sun_lo=V(d["imp"][0] / SUN_TO_CHEM, "MW", "sunlight an electro-organ must catch"),
        sun_hi=V(d["imp"][1] / SUN_TO_CHEM, "MW"),
        collector_lo=V(sun_area[0], "m2"), collector_hi=V(sun_area[1], "m2"),
        collector_x_hull=V(sun_area[1] / area, "x outer hull"),
        chem_share_lo=V(100 * d["chem"][0] / d["need"][1], "%"),
        chem_share_hi=V(100 * d["chem"][1] / d["need"][0], "%"),
        heat_lo=V(d["heat"][0], "MW"), heat_hi=V(d["heat"][1], "MW"),
        radiator_lo=V(rad[0], "m2"), radiator_hi=V(rad[1], "m2"),
        chem_rate_lo=V(rate_chem[0], "t/d"), chem_rate_hi=V(rate_chem[1], "t/d"),
        chem_years_lo=V(years_chem[1], "yr"), chem_years_hi=V(years_chem[0], "yr"),
        crew_mw=V(0.005, "MW"), maint_mw=V(MAINT_MW, "MW"),
        tau=V(TAU_D, "d"),
    )
    return collect("metab", **kw)
