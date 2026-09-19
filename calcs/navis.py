"""NAVIS reference body: geometry, wall mass, pressure, oxygen, cells, shielding.

The reference body is the drawn one (Starship drawings, Plate I): a prolate
spheroid 100 m between poles by 50 m beam (semi-axes 50 x 25 m), with a
5.5 m living wall; ~120 m overall with appendages. The grown mass is held at
24,000 t (the growth budget: ~5 yr at the mining ceiling, see growth.py), so
the wall's mean shielding column follows from mass / wall volume.

The wall is a constant-thickness shell. Its volume is exact (Steiner) as
long as the thickness is below the smallest radius of curvature (b^2/a =
12.5 m): V_shell = A t - M t^2 + (4 pi / 3) t^3, with A the outer area and
M the integral of mean curvature over the outer surface.
"""

from math import cos, exp, log, pi, sin, sqrt

from . import constants as C
from .value import V, collect

A_SEMI, B_SEMI = 50.0, 25.0     # m, drawn main body (100 x 50 m)
WALL_T = 5.5                    # m, six layers (Dossier section A-A)
MASS_T = 24_000.0               # t, grown mass (held; see module docstring)
SEED_T = 0.5                    # t, launched seed
CREW = 50
P_CABIN = 52e3                  # Pa
FIBRE_WORK_PA = 100e6           # silk-analogue working stress (SF ~10 on ~1 GPa)
MYCELIUM_PA = 1e6               # weak mycelium composite
PNEUMOSTAT_T = 1.0              # m
PNEUMOSTAT_WORK_PA = (10e6, 200e6)   # bulk working-stress range of the lamellae stack
O2_YIELD_G_M2_D = 30.0          # assumed lit-intima O2 yield
O2_MARGIN = 1.8
CELL_DENSITY = (1e12, 1e14)     # cells/m^3: sparse mycelial matrix .. dense tissue
INTIMA_T = 0.5                  # m, photosynthetic lining
INTIMA_DENSITY = 1e15           # cells/m^3: a dense microalgal culture (~1e9 per mL)
# pure-water attenuation implied by the Dossier's own 87 % / 25 % over 3.05 m
A530 = -log(0.87) / 3.05        # 1/m, blue-green
A680 = -log(0.25) / 3.05        # 1/m, red


def mean_curvature_integral(a, b, n=20000):
    """Integral of mean curvature H over a prolate spheroid's surface, m."""
    tot = 0.0
    dv = pi / n
    for i in range(n):
        v = (i + 0.5) * dv
        s, c = sin(v), cos(v)
        w = sqrt(a * a * s * s + b * b * c * c)
        k1 = a * b / w ** 3          # meridional curvature
        k2 = a / (b * w)             # parallel curvature
        tot += 0.5 * (k1 + k2) * 2 * pi * b * s * w * dv
    return tot


def geometry(a=A_SEMI, b=B_SEMI, t=WALL_T):
    area = C.spheroid_area(a, b)
    m_int = mean_curvature_integral(a, b)
    v_out = 4 / 3 * pi * a * b * b
    v_shell = area * t - m_int * t * t + 4 / 3 * pi * t ** 3
    area_in = area - 2 * m_int * t + 4 * pi * t * t     # inner parallel surface
    return dict(area=area, area_in=area_in, v_out=v_out, v_shell=v_shell,
                v_cabin=v_out - v_shell, m_int=m_int)


def hoop(p=P_CABIN, a=A_SEMI, b=B_SEMI):
    """Membrane forces at a prolate spheroid's equator, N/m (hoop, meridional)."""
    return p * b * (1 - b * b / (2 * a * a)), p * b / 2


def water_transmission(depth_m, coeff):
    return exp(-coeff * depth_m)


def values():
    g = geometry()
    col_kg_m2 = MASS_T * 1e3 * WALL_T / g["v_shell"]
    col = col_kg_m2 / 10.0                           # g/cm^2
    n_hoop, n_mer = hoop()
    t_fibre_mm = n_hoop / FIBRE_WORK_PA * 1e3
    o2_kg = CREW * C.BVAD_O2_KG
    o2_area = o2_kg * 1e3 / O2_YIELD_G_M2_D
    o2_lit = o2_area * O2_MARGIN
    mars_col = C.column_g_cm2(C.MARS_P_PA, C.MARS_G)
    water_m = col_kg_m2 / 1000.0
    cells = [g["v_shell"] * d for d in CELL_DENSITY]
    intima_cells = g["area_in"] * INTIMA_T * INTIMA_DENSITY
    sphere_area = 4 * pi * B_SEMI ** 2
    return collect(
        "navis",
        area=V(g["area"], "m2", "outer surface of the 100 x 50 m spheroid"),
        area_in=V(g["area_in"], "m2", "cabin-side (intima) surface, 5.5 m in"),
        wall_volume=V(g["v_shell"], "m3", "5.5 m constant-thickness wall"),
        cabin_volume=V(g["v_cabin"], "m3"),
        mass=V(MASS_T, "t", "grown mass (held)"),
        column=V(col, "g/cm2", "mean shielding column = mass x t / V_shell"),
        column_kg=V(col_kg_m2, "kg/m2"),
        mean_density=V(MASS_T * 1e3 / g["v_shell"], "kg/m3"),
        water_equiv=V(water_m, "m", "column as metres of water"),
        col_vs_earth=V(100 * col / C.EARTH_COLUMN_G_CM2, "%", "of Earth's air column"),
        col_vs_mars=V(col / mars_col, "x", "Mars surface air column"),
        seed_ratio=V(MASS_T / SEED_T, ":1"),
        gcr=V(C.gcr_behind_water(col_kg_m2 / 1e3), "Sv/yr", "OLTARIS free space, water"),
        gcr_old_305=V(C.gcr_behind_water(3.05), "Sv/yr", "what 305 g/cm2 would give"),
        hoop=V(n_hoop / 1e6, "MN/m", "equatorial hoop tension at 52 kPa"),
        meridional=V(n_mer / 1e6, "MN/m"),
        fibre_mm=V(t_fibre_mm, "mm", "silk-analogue at 100 MPa"),
        mycelium_m=V(n_hoop / MYCELIUM_PA, "m", "mycelium at 1 MPa"),
        pneumostat_margin=V(PNEUMOSTAT_T * 1e3 / t_fibre_mm, "x", "1 m pneumostat vs fibre need"),
        pneumostat_margin_lo=V(PNEUMOSTAT_T * PNEUMOSTAT_WORK_PA[0] / n_hoop, "x"),
        pneumostat_margin_hi=V(PNEUMOSTAT_T * PNEUMOSTAT_WORK_PA[1] / n_hoop, "x"),
        o2_crew_kg=V(o2_kg, "kg/day", "50 crew x BVAD 0.816"),
        o2_area=V(o2_area, "m2", "lit intima at 30 g O2/m2/day"),
        o2_lit=V(o2_lit, "m2", "with 1.8x margin"),
        o2_frac_lit=V(100 * o2_lit / g["area_in"], "%", "share of intima lit"),
        o2_frac_min=V(100 * o2_area / g["area_in"], "%"),
        t530=V(100 * water_transmission(water_m, A530), "%", "blue-green through the column"),
        t680=V(100 * water_transmission(water_m, A680), "%", "red through the column"),
        ice_extra=V(100 * (1000 / 917 - 1), "%", "ice thickness penalty"),
        cells_lo=V(cells[0], "cells", mode="log", tol=0.5),
        cells_hi=V(cells[1], "cells", mode="log", tol=0.5),
        intima_cells=V(intima_cells, "cells", mode="log", tol=0.5),
        cells=V(cells[1] + intima_cells, "cells", "wall + intima, order of magnitude",
                mode="log", tol=0.5),
        old_sphere_area=V(sphere_area, "m2", "the 50 m sphere the old figures used"),
    )
