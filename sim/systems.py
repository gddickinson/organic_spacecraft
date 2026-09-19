"""System dynamics for the GESTALT simulations.

Each function models one major system and returns time-series arrays. The
models are small, but each output is computed from the physics, not written
in to match a document:

  growth        — the Dossier's growth model, dM/dt = min(M/tau, ceiling)
  life_support  — ARCA's O2/CO2: light- and CO2-limited photosynthesis vs respiration
  spin_gravity  — rim gravity, gradient and Coriolis deflection
  thermal       — skin at radiative equilibrium; interior as a thermal RC circuit
  energy_budget — the metabolism's mass and energy ledger, from calcs
  gestation     — staggered cradle cycles in the nursery
"""

import numpy as np

from calcs import constants as CC
from calcs import metabolism as CM
from . import params as P


def growth(design, n=240):
    """Grown mass and deposition rate over the gestation, tonnes and t/day."""
    from calcs.growth import mass_at, time_to
    m0, rmax, tau = design.m0_t, design.dep_ceiling_tpd, design.tau_d
    t_end = time_to(design.mass_final_t, m0, rmax, tau)
    t = np.linspace(0, t_end, n)
    mass = np.array([mass_at(x, m0, rmax, tau) for x in t])
    rate = np.minimum(mass / tau, rmax)
    ratio = CM.ledger()["ratio"]                       # ore : ship, set by phosphorus
    tailings = mass * (ratio - 1)
    return dict(t_days=t, t_years=t / P.YEAR, mass_t=mass, rate_tpd=rate,
                tailings_t=tailings, frac=mass / mass.max(), gestation_years=t_end / P.YEAR)


def _air_moles(design):
    m_air = design.o2_mole_fraction * CC.M_O2 + (1 - design.o2_mole_fraction) * CC.M_N2
    return design.air_mass_t * 1e6 / m_air             # mol


def life_support(design, years=3.0, n=600, diel=False, co2_ppm0=400.0):
    """ARCA's air: O2 and CO2 inventories driven by light, CO2 and the crew.

    Photosynthesis = vegetated area x daily-mean yield x light(t) x
    CO2/(CO2 + K), with light(t) normalised to a daily mean of 1. The crew
    consumes O2 and returns CO2 at BVAD's RQ of 0.92; photosynthesis fixes
    one CO2 per O2. Nothing is scaled to balance: the
    CO2 level settles where uptake matches supply, and the RQ gap then drains
    O2 slowly unless mined carbonate (co2_makeup_tpd) tops the CO2 up.
    With diel=False, days are integrated at their mean light (for long runs).
    """
    steps_per_day = 24 if diel else 1
    n_steps = int(years * P.YEAR * steps_per_day)
    dt = 1.0 / steps_per_day                                 # days
    air_mol = _air_moles(design)
    o2 = design.o2_mole_fraction * air_mol                   # mol
    co2 = co2_ppm0 * 1e-6 * air_mol
    resp_o2 = design.crew * CC.BVAD_O2_KG * 1e3 / CC.M_O2    # mol/day
    resp_co2 = design.crew * CC.BVAD_CO2_KG * 1e3 / CC.M_CO2
    makeup = design.co2_makeup_tpd * 1e6 / CC.M_CO2
    p_max = design.veg_area_m2 * design.o2_yield_g_m2_d / CC.M_O2   # mol/day, mean light
    k = design.co2_half_sat_ppm * 1e-6 * air_mol
    t = np.arange(n_steps) * dt
    light = np.pi * np.clip(np.sin(2 * np.pi * t), 0, None) if diel else np.ones(n_steps)
    o2s, co2s, photo = np.empty(n_steps), np.empty(n_steps), np.empty(n_steps)
    for i in range(n_steps):
        p = p_max * light[i] * co2 / (co2 + k)
        o2 += (p - resp_o2) * dt
        co2 = max(co2 + (resp_co2 + makeup - p) * dt, 0.0)
        o2s[i], co2s[i], photo[i] = o2, co2, p
    keep = np.linspace(0, n_steps - 1, min(n, n_steps)).astype(int)
    o2_frac = o2s / air_mol
    return dict(t_days=t[keep], o2_pct=100 * o2_frac[keep], co2_ppm=1e6 * co2s[keep] / air_mol,
                photo_t_day=photo[keep] * CC.M_O2 / 1e6, resp_t_day=resp_o2 * CC.M_O2 / 1e6,
                buffer_years=o2s[0] / resp_o2 / P.YEAR, daylight=light[keep],
                o2_drift_pct_per_century=100 * (o2_frac[-1] - o2_frac[0]) / (t[-1] or 1) * 36525)


def spin_gravity(design):
    """Rim gravity, the gravity gradient, and a dropped object's Coriolis path."""
    R = design.a
    omega = design.rpm * 2 * np.pi / 60.0                # rad/s
    g_rim = omega**2 * R
    r = np.linspace(0, R, 60)
    g_of_r = omega**2 * r                                # linear gradient to 0 at axis
    rim_v = omega * R
    # drop a ball from the rim toward the axis; integrate in the inertial frame,
    # then express in the co-rotating frame to show the Coriolis curve.
    tf = np.sqrt(2 * R / max(g_rim, 1e-6)) * 0.6
    ts = np.linspace(0, tf, 120)
    x0, y0 = R, 0.0
    vx0, vy0 = 0.0, rim_v
    xi = x0 + vx0 * ts
    yi = y0 + vy0 * ts
    th = omega * ts                                      # frame rotation
    xr = xi * np.cos(-th) - yi * np.sin(-th)             # into co-rotating frame
    yr = xi * np.sin(-th) + yi * np.cos(-th)
    return dict(g_rim=g_rim, rim_v=rim_v, r=r, g_of_r=g_of_r,
                drop_x=xr, drop_y=yr, R=R, omega=omega)


def thermal(design, days=2.0, n=400, t_in0=293.0):
    """Skin temperature with a day/night swing; the interior as a thermal RC.

    Skin: radiative equilibrium sets the mean; the lit face heats and the dark
    face cools around it. Interior: C dT/dt = G (T_skin - T) + Q, with G the
    wall's conductance k A / L and Q the internal heat. The time constant C/G
    and the steady state T_skin_mean + Q/G come out of the parameters.
    """
    S = P.SOLAR_1AU / design.au**2
    absorb = (1 - design.albedo)
    t = np.linspace(0, days, n)                          # days
    lit = np.clip(np.sin(2 * np.pi * t), 0, None)        # sun above the horizon
    T_mean = (absorb * S * 0.25 / P.SIGMA) ** 0.25       # radiative-equilibrium mean
    amp = 55.0                                           # diel surface swing (thermal-lagged)
    T_skin = T_mean + amp * np.sin(2 * np.pi * t - 1.0)
    G = design.wall_k * design.wall_area_m2 / design.wall_m if design.wall_m else 0.0
    C = design.heat_cap_j_k or 1.0
    T_in = np.empty_like(t)
    T_in[0] = t_in0
    dt = np.diff(t, prepend=0.0) * P.DAY
    for i in range(1, n):
        T_in[i] = T_in[i - 1] + dt[i] * (G * (T_skin[i - 1] - T_in[i - 1]) + design.internal_w) / C
    tau_years = C / G / (P.DAY * P.YEAR) if G else float("inf")
    t_steady = T_mean + design.internal_w / G if G else float("inf")
    return dict(t_days=t, T_skin=T_skin, T_interior=T_in, T_mean=T_mean, lit=lit,
                tau_years=tau_years, T_steady=t_steady, conductance_w_k=G)


def energy_budget(design):
    """The metabolism's two engines and energy gap, from calcs (the Dossier's NAVIS)."""
    d = CM.ledger()
    return dict(
        photo_biomass_tpd=round(d["photo_t"], 2),       # what the whole lit intima builds
        growth_tpd=round(d["grow"], 1),                 # what the hull grows at
        area_ratio=round(d["grow"] * 1e6 / 30.0 / CM.geometry()["area"], 1),
        fuel_MW=round(d["fuel"], 2),                    # organics' fuel value, if burnable
        chem_MW=tuple(round(x, 2) for x in d["chem"]),  # what the rock's oxidants unlock
        synth_MW=tuple(round(x, 2) for x in d["stored"]),  # stored in new tissue
        need_MW=tuple(round(x, 2) for x in d["need"]),     # the growth engine's draw
        ore_ratio=round(d["ratio"], 1),                 # ore : ship, phosphorus-set
    )


def gestation(design, n=240):
    """Cradle fill and embryo growth across the nursery, staggered by stage."""
    T = design.gestation_years * P.YEAR
    t = np.linspace(0, T * 1.6, n)                       # run past one cycle
    stages = np.linspace(0.0, 0.85, design.cradles)      # each cradle offset in its cycle
    phase = (t[:, None] / T + stages[None, :]) % 1.0
    frac = np.clip(1.2 * (0.5 - np.abs(phase - 0.5)) * 2, 0, 1)  # triangle up to hatch
    throughput = design.dep_ceiling_tpd                         # per-cradle deposition, t/day
    return dict(t_days=t, t_years=t / P.YEAR, frac=frac, stages=stages,
                throughput_tpd=throughput, ships_per_year=design.cradles / design.gestation_years)
