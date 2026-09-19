"""ARCA spin habitat, LEVIATHAN and LICHEN: structure, spin, shielding, air.

ARCA hoop load: air pressure P R plus the spin-weight of everything that
rotates, sigma v^2 (sigma = rotating mass per m^2, v = rim speed). Using the
drum's own mass (2.4 Gt spread over drum wall + end caps) for sigma gives
~300 MN/m on top of the 130 MN/m from the air. The regolith shield is 1 m of
compacted slag (~3 t/m^3, 300 g/cm^2) and rotates with the drum; a 10 m
rotating shield would need 1,500-3,000 g/cm^2 of mass the 2-3 Gt budget
does not contain.
"""

from math import atan, pi, sqrt

from . import constants as C
from .value import V, collect

R, L, RPM = 2500.0, 10_000.0, 0.6
P = 52e3
DRUM_MASS = 2.4e12               # kg (Habitat: ~2-3 Gt; spin-up uses 2.5)
SHIELD_T, SHIELD_RHO = 1.0, 3000.0
AIR_COLUMN_G_CM2 = 140.0
SILK_RHO = 1300.0
WORK_MK1, WORK_MK2 = 100e6, 200e6
STEEL_RHO, STEEL_WORK = 7850.0, 500e6
WALK_V, DROP_H = 1.4, 2.0
SPINUP_YEARS = 3.0
SUN_CORD_W = 15e9
LEV_DRUMS, LEV_R, LEV_L, LEV_RPM = 12, 3000.0, 12_000.0, 0.52
LICHEN_SPAN, LICHEN_RISE, REGOLITH_RHO = 500.0, 150.0, 1500.0
PERCHLORATE_WT = (0.004, 0.006)  # Hecht et al. 2009, Phoenix site


def omega(rpm):
    return rpm * 2 * pi / 60


def drum_area(r, length):
    return 2 * pi * r * length + 2 * pi * r * r


def values():
    w = omega(RPM)
    v = w * R
    area = drum_area(R, L)
    rim_area = 2 * pi * R * L
    sigma = DRUM_MASS / area
    n_air = P * R
    n_spin = sigma * v * v
    n_tot = n_air + n_spin
    t1, t2 = n_tot / WORK_MK1, n_tot / WORK_MK2
    mk2_saving = (t1 - t2) * SILK_RHO * rim_area
    shield = SHIELD_T * SHIELD_RHO / 10                     # g/cm^2
    wt = sqrt(2 * DROP_H / R)
    drop_cm = R * (wt - atan(wt)) * 100
    spin_e = 0.5 * 2.5e12 * v * v
    # LEVIATHAN at ARCA's areal mass
    lev_area = LEV_DRUMS * drum_area(LEV_R, LEV_L)
    lev_mass = sigma * lev_area
    wl = omega(LEV_RPM)
    # LICHEN
    r_sph = (LICHEN_SPAN ** 2 / 4 + LICHEN_RISE ** 2) / (2 * LICHEN_RISE)
    floor_kg = pi * (LICHEN_SPAN / 2) ** 2 * 1.0 * REGOLITH_RHO
    o2 = [floor_kg * f * C.M_O2 / C.M_CLO4 / 1e3 for f in PERCHLORATE_WT]
    return collect(
        "habitat",
        g_rim=V(w * w * R / C.G0, "g"), rim_speed=V(v, "m/s"),
        inner_area=V(rim_area / 1e6, "km2"), volume=V(pi * R * R * L / 1e9, "km3"),
        n_air=V(n_air / 1e6, "MN/m"), n_spin=V(n_spin / 1e6, "MN/m"),
        n_total=V(n_tot / 1e6, "MN/m"), sigma=V(sigma / 1e3, "t/m2"),
        tendon_mk1=V(t1, "m"), tendon_mk2=V(t2, "m"),
        mk2_saving_gt=V(mk2_saving / 1e12, "Gt"),
        mk2_saving_pct=V(100 * mk2_saving / DRUM_MASS, "%"),
        silk_kg_m2=V(n_tot / WORK_MK2 * SILK_RHO, "kg/m2", "silk at 200 MPa"),
        steel_kg_m2=V(n_tot / STEEL_WORK * STEEL_RHO, "kg/m2", "steel at 500 MPa"),
        silk_vs_steel=V(STEEL_RHO / STEEL_WORK / (SILK_RHO / WORK_MK2), "x"),
        shield=V(shield, "g/cm2"),
        shield_plus_air=V(shield + AIR_COLUMN_G_CM2, "g/cm2"),
        shield_10m_lo=V(10 * 1500 / 10, "g/cm2"), shield_10m_hi=V(10 * 3000 / 10, "g/cm2"),
        coriolis_pct=V(100 * 2 * w * WALK_V / C.G0, "%"),
        drop_cm=V(drop_cm, "cm", "anti-spinward"),
        spinup_j=V(spin_e, "J", mode="log", tol=0.05),
        spinup_twh=V(spin_e / 3.6e15, "TWh"),
        spinup_mw=V(spin_e / (SPINUP_YEARS * C.YEAR_S) / 1e6, "MW"),
        suncord_km=V(2 * sqrt(SUN_CORD_W / C.S_1AU / pi) / 1e3, "km"),
        lev_mass_gt=V(lev_mass / 1e12, "Gt", "12 drums at ARCA's areal mass"),
        lev_area_km2=V(lev_area / 1e6, "km2"),
        lev_g=V(wl * wl * LEV_R / C.G0, "g"),
        lev_old_ratio=V(lev_mass / 12e12, "x the old 12 Gt"),
        lichen_radius=V(r_sph, "m"),
        lichen_membrane=V(P * r_sph / 2 / 1e6, "MN/m"),
        lichen_uplift=V(P * pi * (LICHEN_SPAN / 2) ** 2 / 1e9, "GN"),
        lichen_blanket_mars=V(P / (REGOLITH_RHO * 3.71), "m"),
        lichen_blanket_moon=V(P / (REGOLITH_RHO * 1.62), "m"),
        lichen_o2_lo=V(o2[0], "t", "1 O2 per ClO4- (chlorite dismutase)"),
        lichen_o2_hi=V(o2[1], "t"),
        lichen_py_lo=V(o2[0] * 1e3 / C.BVAD_O2_KG / C.YEAR_D, "person-years"),
        lichen_py_hi=V(o2[1] * 1e3 / C.BVAD_O2_KG / C.YEAR_D, "person-years"),
        lichen_old_needs=V(1400e3 * C.M_CLO4 / C.M_O2 / floor_kg * 100 / 2, "wt%",
                           "perchlorate for 1,400 t if all 4 O were released"),
    )

