"""Micrometeoroid impact rates on the NAVIS hull (Grun et al. 1985, 1 AU).

F(m) is the cumulative flux of particles heavier than m grams onto a
surface element, per m^2 per s. For a convex body the whole-surface hit rate
is ~F x (outer area); the answer is order-of-magnitude (focusing, velocity
and shape factors of ~2 are ignored).
"""

from math import pi

from . import constants as C
from .navis import geometry
from .value import V, collect

GRAIN_DENSITY = 2.5   # g/cm^3, for the size labels


def grun(m):
    """Grun et al. (1985) interplanetary flux at 1 AU, m in g, per m^2 per s."""
    return ((2.2e3 * m ** 0.306 + 15.0) ** -4.38
            + 1.3e-9 * (m + 1e11 * m ** 2 + 1e27 * m ** 4) ** -0.36
            + 1.3e-16 * (m + 1e6 * m ** 2) ** -0.85)


def per_year(m):
    return grun(m) * C.YEAR_S


def diameter_um(m_g):
    return (6 * m_g / GRAIN_DENSITY / pi) ** (1 / 3) * 1e4


def mass_flux_kg_m2_yr(m_lo=1e-18, m_hi=1e2, n=4000):
    """Total incident mass per m^2 per year, integrating m dN over log-mass."""
    from math import log10
    lo, hi = log10(m_lo), log10(m_hi)
    tot = 0.0
    step = (hi - lo) / n
    for i in range(n):
        m1, m2 = 10 ** (lo + i * step), 10 ** (lo + (i + 1) * step)
        dn = grun(m1) - grun(m2)
        tot += dn * (m1 * m2) ** 0.5
    return tot * C.YEAR_S / 1e3


def values():
    area = geometry()["area"]
    out = {}
    for tag, m in (("ug", 1e-6), ("mg", 1e-3), ("g", 1.0)):
        out[f"flux_{tag}"] = V(per_year(m), "/m2/yr", f"Grun, m > {m:g} g",
                               mode="log", tol=0.15)
        out[f"hits_{tag}"] = V(per_year(m) * area, "/yr", "on the 13,400 m2 hull",
                               mode="log", tol=0.15)
    out["hits_ug_decade"] = V(per_year(1e-6) * area * 10, "/decade", mode="log", tol=0.15)
    out["years_per_g"] = V(1 / (per_year(1.0) * area), "yr", "between >1 g hits",
                           mode="log", tol=0.15)
    out["d_ug"] = V(diameter_um(1e-6), "um")
    out["mass_flux"] = V(mass_flux_kg_m2_yr(), "kg/m2/yr", mode="log", tol=0.3)
    return collect("meteoroids", **out)
