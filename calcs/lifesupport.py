"""The O2/CO2/N loop, per crew member and at NAVIS and ARCA scale.

Photosynthesis to sugar has a photosynthetic quotient of 1 (one CO2 fixed
per O2 released). Crew respiration runs RQ = 0.92 (BVAD REV1), so the crew
returns fewer moles of CO2 than the intima needs to remake their O2.
Decomposing waste to CO2 cannot close that gap, because decomposition burns
O2 in the same proportion; the shortfall must come from outside the loop
(mined carbonate, or intima products richer than sugar, PQ > 1).
"""

from math import exp

from . import constants as C
from .value import V, collect

NAVIS_CREW = 50

# ARCA atmosphere (Habitat): 52 kPa at the rim, 34 % O2 by volume, 293 K
ARCA_R, ARCA_L, ARCA_RPM = 2500.0, 10_000.0, 0.6
ARCA_P, ARCA_X_O2, ARCA_T = 52e3, 0.34, 293.0
ARCA_POP = 1_000_000
ARCA_LIVING_M2 = 100e6
VEG_O2_G_M2_D = 15.0            # managed-landscape O2 yield the Habitat assumes


def per_person():
    o2 = C.BVAD_O2_KG
    co2_fixed = o2 * C.PS_CO2_PER_O2
    sugar = o2 * C.PS_SUGAR_PER_O2
    rq = (C.BVAD_CO2_KG / C.M_CO2) / (o2 / C.M_O2)
    gap = co2_fixed - C.BVAD_CO2_KG
    return dict(co2_fixed=co2_fixed, sugar=sugar, rq=rq, co2_gap=gap)


def urine_nitrogen_g():
    """N excreted in urine, g/person/day, from BVAD Table 4-26 x urine volume."""
    mg = C.BVAD_URINE_MG_L
    litres = C.BVAD_URINE_WATER_KG
    n = (mg["urea"] * 2 * 14.007 / C.M_UREA
         + mg["creatinine"] * 3 * 14.007 / C.M_CREATININE
         + mg["nh4_hippurate"] * 2 * 14.007 / C.M_NH4_HIPPURATE
         + mg["nh4no3"] * 2 * 14.007 / C.M_NH4NO3)
    return n * litres / 1e3


def arca_air():
    """ARCA air and O2 inventory with the centrifugal barometric profile."""
    w = ARCA_RPM * 2 * 3.141592653589793 / 60
    m_air = ARCA_X_O2 * C.M_O2 + (1 - ARCA_X_O2) * C.M_N2          # g/mol
    rho_rim = ARCA_P * m_air / 1e3 / (C.R_GAS * ARCA_T)
    k = w * w * m_air / 1e3 / (2 * C.R_GAS * ARCA_T)                 # 1/m^2
    kr2 = k * ARCA_R ** 2
    mass = ARCA_L * 3.141592653589793 * rho_rim * (1 - exp(-kr2)) / k  # kg
    o2_mass_frac = ARCA_X_O2 * C.M_O2 / m_air
    p_axis = ARCA_P * exp(-kr2)
    scale_h = C.R_GAS * ARCA_T / (m_air / 1e3) / C.G0
    n = 2000
    dr = ARCA_R / n
    column = sum(rho_rim * exp(-k * (ARCA_R ** 2 - ((i + 0.5) * dr) ** 2)) * dr
                 for i in range(n))                                   # kg/m^2
    return dict(mass_t=mass / 1e3, o2_mass_frac=o2_mass_frac, p_axis=p_axis,
                rho_rim=rho_rim, scale_h=scale_h, column=column / 10)


def values():
    p = per_person()
    air = arca_air()
    o2_t_day = ARCA_POP * C.BVAD_O2_KG / 1e3
    reserve_yr = air["mass_t"] * air["o2_mass_frac"] / o2_t_day / C.YEAR_D
    n_g = urine_nitrogen_g()
    return collect(
        "life",
        o2=V(C.BVAD_O2_KG, "kg/p/d"), co2=V(C.BVAD_CO2_KG, "kg/p/d"),
        water=V(C.BVAD_POTABLE_WATER_KG, "kg/p/d"), food=V(C.BVAD_FOOD_DRY_KG, "kg/p/d"),
        co2_fixed=V(p["co2_fixed"], "kg/p/d", "CO2 fixed to remake 0.816 kg O2"),
        sugar=V(p["sugar"], "kg/p/d"),
        co2_gap=V(p["co2_gap"], "kg/p/d", "CO2 the crew does not return"),
        co2_gap_pct=V(100 * p["co2_gap"] / p["co2_fixed"], "%"),
        rq=V(p["rq"], "", "from BVAD's O2 and CO2 masses", tol=0.02),
        crew_o2=V(NAVIS_CREW * C.BVAD_O2_KG, "kg/d"),
        crew_co2=V(NAVIS_CREW * C.BVAD_CO2_KG, "kg/d"),
        crew_food=V(NAVIS_CREW * C.BVAD_FOOD_DRY_KG, "kg/d"),
        crew_water=V(NAVIS_CREW * C.BVAD_POTABLE_WATER_KG, "kg/d"),
        crew_co2_fixed=V(NAVIS_CREW * p["co2_fixed"], "kg/d"),
        urine_n=V(n_g, "g N/p/d", "BVAD urine composition x 1.62 L"),
        arca_urine_n=V(n_g * ARCA_POP / 1e6, "t N/day"),
        arca_air=V(air["mass_t"] / 1e6, "Mt"),
        arca_o2_mass_frac=V(air["o2_mass_frac"], "", "34 % by volume as a mass fraction"),
        arca_p_axis=V(air["p_axis"] / 1e3, "kPa"),
        arca_scale_h=V(air["scale_h"] / 1e3, "km", "isothermal scale height at 1 g"),
        arca_air_column=V(air["column"], "g/cm2", "radial air column rim->axis"),
        arca_o2_reserve=V(reserve_yr, "yr", "O2 inventory / 1 M x 0.816 kg/d"),
        arca_o2_need=V(o2_t_day * 1e6 / ARCA_LIVING_M2, "g/m2/d", "over 100 km2"),
        arca_o2_t_day=V(o2_t_day, "t/d"),
        arca_co2_t_day=V(ARCA_POP * C.BVAD_CO2_KG / 1e3, "t/d"),
        arca_o2_mt=V(air["mass_t"] * air["o2_mass_frac"] / 1e6, "Mt"),
        arca_co2_1pct_yr=V(air["mass_t"] * 1e3 / (ARCA_X_O2 * C.M_O2 + (1 - ARCA_X_O2) * C.M_N2)
                           * 0.01 * C.M_CO2 / (ARCA_POP * C.BVAD_CO2_KG) / C.YEAR_D, "yr",
                           "CO2 to 1 % by volume if nothing fixes it"),
        arca_veg_km2=V(o2_t_day * 1e6 / VEG_O2_G_M2_D / 1e6, "km2", "at 15 g O2/m2/d"),
    )
