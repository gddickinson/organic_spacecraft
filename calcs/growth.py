"""The Dossier's growth model and what it implies for every grown class.

dM/dt = min(M / tau, R_max): exponential while the body is small (its own
tissue sets the pace), then capped by how fast it can be fed. tau = 55 d
(doubling ~38 d). A cradle (GRAVID) or parent raises R_max; it cannot
shorten the exponential start, which the embryo's own biology sets.
"""

from math import exp, log

from .navis import geometry
from .value import V, collect

TAU_D = 55.0
WILD_RMAX = 16.0        # t/day, mining-limited ceiling (Dossier)
CRADLE_RMAX = 26.0      # t/day, one GRAVID cradle's feed
NAVIS_M0 = 1.0          # t, the germinated 0.5 t seed once it has taken up water
                        # ("Anchor & root: mass ~1 -> 50 t", Dossier mission profile)
HEAL_SURGE = (10.0, 30.0)   # local deposition surge over the baseline, x
SOMATIC_MU = 1e-9           # mutations per bp per division
TARGET_BP = 1e3             # ~one growth-control gene's coding sequence
SEED_LIMIT_GY = 5000.0      # dormant seed's 1/e repair limit (Compendium)
YEAR = 365.25


def time_to(mass_t, m0_t, rmax, tau=TAU_D):
    """Days for dM/dt = min(M/tau, rmax) to grow m0 -> mass."""
    m_cap = rmax * tau
    if mass_t <= m_cap:
        return tau * log(mass_t / m0_t)
    t_cap = tau * log(m_cap / m0_t) if m_cap > m0_t else 0.0
    return t_cap + (mass_t - max(m_cap, m0_t)) / rmax


def mass_at(t_d, m0_t, rmax, tau=TAU_D):
    m_cap = rmax * tau
    t_cap = tau * log(m_cap / m0_t)
    if t_d <= t_cap:
        return m0_t * exp(t_d / tau)
    return m_cap + rmax * (t_d - t_cap)


def curve(m0_t=NAVIS_M0, rmax=WILD_RMAX, target=24_000.0, n=200):
    """(years, mass t, rate t/day) samples up to the target mass."""
    t_end = time_to(target, m0_t, rmax)
    out = []
    for i in range(n + 1):
        t = t_end * i / n
        m = mass_at(t, m0_t, rmax)
        out.append((t / YEAR, m, min(m / TAU_D, rmax)))
    return out


def values():
    navis = 24_000.0
    m0 = NAVIS_M0
    wild = time_to(navis, m0, WILD_RMAX)
    cradle = time_to(navis, m0, CRADLE_RMAX)
    t_cap = TAU_D * log(WILD_RMAX * TAU_D / m0)
    base = navis / wild * 1e3 / geometry()["area"]                  # kg/m2/day
    wall_kg = navis * 1e3 / geometry()["v_shell"]                  # mean kg/m3
    gouge = [0.5 * wall_kg / (base * s) for s in HEAL_SURGE]        # days, 0.5 m
    full = [5.5 * wall_kg / (base * s) / 30.44 for s in HEAL_SURGE]  # months, 5.5 m
    testudo = time_to(150_000.0, 5.0, CRADLE_RMAX)
    amber = time_to(130_000.0, 5.0, CRADLE_RMAX)
    spore = time_to(60.0, 0.003, CRADLE_RMAX)
    y = lambda d: d / YEAR   # noqa: E731
    return collect(
        "growth",
        tau=V(TAU_D, "d"), doubling=V(TAU_D * log(2), "d", "biology's doubling time"),
        rmax=V(WILD_RMAX, "t/d"), cap_mass=V(WILD_RMAX * TAU_D, "t"),
        cap_year=V(y(t_cap), "yr", tol=0.15),
        navis_years=V(y(wild), "yr", "germinated seed (1 t) -> 24 kt, wild"),
        navis_avg=V(navis / wild, "t/d", "average deposition"),
        navis_per_m2=V(base, "kg/m2/d", "per m2 of hull"),
        heal_gouge_lo=V(gouge[1], "d"), heal_gouge_hi=V(gouge[0], "d"),
        heal_wall_lo=V(full[1], "months"), heal_wall_hi=V(full[0], "months"),
        unconstrained_yr=V(y(TAU_D * log(navis / m0)), "yr", "no ceiling"),
        unconstrained_peak=V(navis / TAU_D, "t/d"),
        slow10_years=V(y(time_to(navis, m0, WILD_RMAX / 10)), "yr", "ceiling ten times lower"),
        stage_50t=V(y(time_to(50, m0, WILD_RMAX)), "yr", tol=0.15),
        stage_6kt=V(y(time_to(6_000, m0, WILD_RMAX)), "yr"),
        stage_16kt=V(y(time_to(16_000, m0, WILD_RMAX)), "yr"),
        mass_1yr=V(mass_at(YEAR, m0, WILD_RMAX), "t", tol=0.1),
        mass_3yr=V(mass_at(3 * YEAR, m0, WILD_RMAX), "t"),
        gravid_years=V(y(cradle), "yr", "germinated seed -> 24 kt at 26 t/day"),
        gravid_speedup=V(100 * (1 - cradle / wild), "%", "shorter than wild"),
        gravid_ships_lo=V(12 / y(cradle), "/yr", "12 cradles"),
        gravid_ships_hi=V(24 / y(cradle), "/yr", "24 cradles"),
        gravid_feed_kg_s=V(CRADLE_RMAX * 1e3 / 86400, "kg/s"),
        testudo_years=V(y(testudo), "yr", "5 t seed -> 150 kt, one cradle"),
        testudo_needed=V(150_000.0 / (2.5 * YEAR), "t/d", "for the old 2-3 yr claim"),
        amber_years=V(y(amber), "yr", "5 t seed -> 130 kt, one cradle"),
        spore_years=V(y(spore), "yr", "3 kg seed -> 60 t (never reaches a ceiling)"),
        mutant_divisions=V(1e19 * SOMATIC_MU * TARGET_BP, "divisions", "hitting a growth gene",
                           mode="log", tol=0.3),
        seed_wall_light=V(SEED_LIMIT_GY / 0.6, "yr", "at ~0.6 Sv/yr"),
        seed_wall_shielded=V(SEED_LIMIT_GY / 0.2, "yr", "at ~0.2 Sv/yr (~1 t/m2 of water)"),
        spore_old_doubling=V(21 * log(2) / log(60 / 0.003), "d", "implied by 3 weeks"),
    )
