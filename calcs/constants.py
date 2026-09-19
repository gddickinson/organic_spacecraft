"""Physical constants and sourced inputs shared by every calcs module.

Each value carries its source. Program *design choices* (crew, pressure,
dimensions) live in the module that uses them, not here.
"""

from math import pi

# ---- physics ----
S_1AU = 1361.0            # W/m^2, total solar irradiance at 1 AU (Kopp & Lean 2011)
SIGMA = 5.670374419e-8    # W/m^2/K^4, Stefan-Boltzmann (CODATA 2018)
G0 = 9.80665              # m/s^2
R_GAS = 8.314462618       # J/mol/K
DAY_S = 86400.0           # s
YEAR_D = 365.25           # days
YEAR_S = YEAR_D * DAY_S   # s
F_FARADAY = 96485.33      # C/mol

# ---- molar masses, g/mol ----
M_O2, M_N2, M_CO2, M_H2O = 31.998, 28.014, 44.009, 18.015
M_C, M_P, M_FE, M_S = 12.011, 30.974, 55.845, 32.06
M_CLO4 = 99.45            # perchlorate anion
M_HA = 1004.6             # hydroxyapatite Ca10(PO4)6(OH)2
M_UREA, M_CREATININE = 60.06, 113.12
M_NH4_HIPPURATE, M_NH4NO3 = 196.2, 80.04

# ---- NASA BVAD REV1 (Anderson et al. 2018, NASA/TP-2015-218570/REV1) ----
# Table 3-33, nominal crew metabolic interface values, per crew-member-day
BVAD_O2_KG = 0.816
BVAD_CO2_KG = 1.04
BVAD_POTABLE_WATER_KG = 2.5
BVAD_RQ = 0.92            # stated respiratory quotient (volumetric)
BVAD_URINE_WATER_KG = 1.62
# Table 4-57, nominal IVA food dry mass
BVAD_FOOD_DRY_KG = 0.617
# Table 4-26, urine contaminants (mg/L): urea, creatinine, NH4 hippurate, NH4NO3
BVAD_URINE_MG_L = {"urea": 13400.0, "creatinine": 1504.0,
                   "nh4_hippurate": 1250.0, "nh4no3": 756.0}

# ---- GCR behind water, free space (Globus & Strout 2017, Table 2; NASA OLTARIS) ----
# shield mass in t/m^2 -> dose equivalent in mSv/yr
GCR_WATER_MSV = ((1, 200.0), (2, 147.0), (3, 101.0), (4, 67.0), (5, 43.0), (6, 26.5), (7, 16.1))
GCR_BASELINE_SV = 0.66          # lightly shielded cruise, MSL/RAD (Zeitlin et al. 2013)


def gcr_behind_water(t_per_m2):
    """Log-linear interpolation of the OLTARIS free-space water table, Sv/yr."""
    from math import exp, log
    pts = GCR_WATER_MSV
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= t_per_m2 <= x1:
            f = (t_per_m2 - x0) / (x1 - x0)
            return exp(log(y0) + f * (log(y1) - log(y0))) / 1e3
    raise ValueError("outside the table")


# ---- chemistry ----
# Energy released oxidising typical organic matter, per mol O2 consumed
# (Thornton's rule, ~13.7 kJ per g O2).
KJ_PER_MOL_O2_ORGANIC = 440.0
# Water electrolysis enthalpy (HHV), per mol O2 produced: 2 x 285.83 kJ
KJ_PER_MOL_O2_ELECTROLYSIS = 571.66
# Photosynthesis 6CO2 + 6H2O -> C6H12O6 + 6O2, by mass
PS_CO2_PER_O2 = 6 * M_CO2 / (6 * M_O2)      # kg CO2 fixed per kg O2 released
PS_SUGAR_PER_O2 = 180.16 / (6 * M_O2)       # kg sugar per kg O2
BIOMASS_MJ_PER_KG = 17.5                    # heat of combustion of dry biomass

# ---- atmosphere / planets ----
EARTH_COLUMN_G_CM2 = 1033.0   # sea-level air column, g/cm^2
MARS_P_PA, MARS_G = 610.0, 3.711


def column_g_cm2(pressure_pa, g):
    """Atmospheric mass column above the surface, g/cm^2."""
    return pressure_pa / g / 10.0


def spheroid_area(a, b):
    """Surface area of a prolate spheroid (semi-axes a >= b), m^2."""
    from math import asin, sqrt
    if abs(a - b) < 1e-12:
        return 4 * pi * a * a
    e = sqrt(1 - (b / a) ** 2)
    return 2 * pi * b * b * (1 + a / (b * e) * asin(e))
