"""Radiative equilibria and heat budgets for the NAVIS hull.

Equilibrium of a body with absorptivity/emissivity ratio r: sigma T^4 A =
r S A_proj. For any convex body averaged over attitude, the mean projected
area is exactly A/4 (Cauchy), so the attitude-averaged result equals the
sphere's (S/4 sigma)^(1/4). The drawn spheroid flies pole-sunward (Plate I),
which halves its sunlit cross-section relative to broadside.
"""

from math import pi, sqrt

from . import constants as C
from .navis import A_SEMI, B_SEMI, geometry
from .value import V, collect

CREW_HEAT_W = 5e3
CREW_RADIATOR_K = 290.0
CORE_K = 283.0
MLI_EMISSIVITY = 0.02
CLOSE_AU = 0.3
CLOSE_ALBEDO = 0.9
CLOSE_RADIATOR_K = 400.0
LIFE_K = (273.0, 313.0)


def t_eq(proj_over_area=0.25, ratio=1.0, au=1.0):
    return (ratio * C.S_1AU / au ** 2 * proj_over_area / C.SIGMA) ** 0.25


def values():
    area = geometry()["area"]
    a_pole = pi * B_SEMI ** 2
    a_broad = pi * A_SEMI * B_SEMI
    t_avg = t_eq()
    close_w = C.S_1AU / CLOSE_AU ** 2 * a_pole
    return collect(
        "thermal",
        t_dark=V(t_avg, "K", "dark hull, attitude-averaged, 1 AU"),
        t_earth_albedo=V(t_eq(ratio=0.7), "K", "albedo 0.3"),
        t_reflective=V(t_eq(ratio=0.3), "K", "alpha/eps = 0.3"),
        t_pole=V(t_eq(a_pole / area), "K", "pole-sunward, dark"),
        t_broad=V(t_eq(a_broad / area), "K", "broadside, dark"),
        sun_pole_mw=V(C.S_1AU * a_pole / 1e6, "MW", "intercepted pole-on"),
        sun_broad_mw=V(C.S_1AU * a_broad / 1e6, "MW", "intercepted broadside"),
        crew_radiator=V(CREW_HEAT_W / (C.SIGMA * CREW_RADIATOR_K ** 4), "m2"),
        shell_inner_au=V((t_avg / LIFE_K[1]) ** 2, "AU"),
        shell_outer_au=V((t_avg / LIFE_K[0]) ** 2, "AU"),
        t_close=V(t_avg / sqrt(CLOSE_AU), "K", "dark hull at 0.3 AU"),
        close_mw=V(close_w / 1e6, "MW", "intercepted pole-on at 0.3 AU"),
        close_reflective_mw=V(close_w * (1 - CLOSE_ALBEDO) / 1e6, "MW"),
        close_radiator=V(close_w / (C.SIGMA * CLOSE_RADIATOR_K ** 4), "m2"),
        core_bare_mw=V(C.SIGMA * CORE_K ** 4 * area / 1e6, "MW", "bare hull at 283 K"),
        core_mli_kw=V(MLI_EMISSIVITY * C.SIGMA * CORE_K ** 4 * area / 1e3, "kW"),
    )
