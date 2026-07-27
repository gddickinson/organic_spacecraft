"""System dynamics for the GESTALT simulations.

Each function models one major system and returns time-series arrays. The models
are deliberately simple, closed-form or single-ODE, but grounded in the canonical
numbers (sim/params.py) so the curves match the program documents:

  growth        — the mining-limited, capped-rate growth curve (Dossier)
  life_support  — closed-loop O2/CO2 with a day/night photosynthesis cycle (Habitat)
  spin_gravity  — rim gravity, gradient and Coriolis deflection (Habitat)
  thermal       — radiative-equilibrium temperature with a day/night swing (Dossier)
  energy_budget — the two-engine metabolism split (Metabolism)
"""

import numpy as np
from . import params as P


def growth(design, n=240):
    """Grown mass and deposition rate over the gestation, tonnes and t/day.

    Deposition ramps to the mining ceiling: rate(t) = ceiling * (1 - e^{-t/tau}),
    so mass(t) = ceiling * (t + tau (e^{-t/tau} - 1)).  tau ~ 0.6 yr reproduces
    the Dossier growth curve (~13 t/day average, ~24,000 t at 5 years).
    """
    T = design.growth_years * P.YEAR
    t = np.linspace(0, T, n)
    tau = 0.6 * P.YEAR
    rate = design.dep_ceiling_tpd * (1 - np.exp(-t / tau))
    mass = design.dep_ceiling_tpd * (t + tau * (np.exp(-t / tau) - 1))
    if design.mass_final_t and mass[-1] > 0:             # scale to the canonical grown mass
        k = design.mass_final_t / mass[-1]
        mass = mass * k; rate = rate * k
    tailings = mass * 8.0          # ore:product ~ 9:1 -> ~8x the deposited mass
    return dict(t_days=t, t_years=t / P.YEAR, mass_t=mass, rate_tpd=rate,
                tailings_t=tailings, frac=mass / mass.max())


def life_support(design, years=3.0, n=600):
    """Closed-loop O2/CO2 with a diel photosynthesis cycle.

    The atmosphere is an enormous buffer, so the O2 fraction barely moves while
    CO2 shows a small day/night ripple: photosynthesis (daylight) draws CO2 down
    and releases O2; respiration does the reverse at night.
    """
    t = np.linspace(0, years * P.YEAR, n)               # days
    air_kg = design.air_mass_t * 1e3
    o2_kg = air_kg * design.o2_fraction
    # crew + biosphere respiration, and a matched daily-mean photosynthesis
    resp = design.crew * 0.84                            # kg O2/day consumed (per person)
    daylight = np.clip(np.sin(2 * np.pi * t), 0, None)   # half the day lit
    photo_mean = resp / max(daylight.mean(), 1e-6)       # balance the loop on average
    photo = photo_mean * daylight
    # integrate the tiny net O2 change against the huge reservoir
    dt = np.gradient(t)
    net = np.cumsum((photo - resp) * dt)                 # kg, net O2 added
    o2_pct = 100.0 * (o2_kg + net) / air_kg
    co2_ripple = -np.cumsum((photo - resp) * dt) / air_kg * 1e6  # ppm-ish wiggle
    co2_ripple = co2_ripple - co2_ripple.mean() + 400.0
    # how long the O2 reserve lasts if photosynthesis stops entirely
    buffer_days = o2_kg / max(resp, 1e-9)
    return dict(t_days=t, o2_pct=o2_pct, co2_ppm=co2_ripple,
                buffer_years=buffer_days / P.YEAR, daylight=daylight)


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
    # inertial: released at rim moving tangentially at rim_v, no force (free-fall in space)
    x0, y0 = R, 0.0
    vx0, vy0 = 0.0, rim_v
    xi = x0 + vx0 * ts
    yi = y0 + vy0 * ts
    th = omega * ts                                      # frame rotation
    xr = xi * np.cos(-th) - yi * np.sin(-th)             # into co-rotating frame
    yr = xi * np.sin(-th) + yi * np.cos(-th)
    return dict(g_rim=g_rim, rim_v=rim_v, r=r, g_of_r=g_of_r,
                drop_x=xr, drop_y=yr, R=R, omega=omega)


def thermal(design, days=2.0, n=400):
    """Skin temperature with a day/night swing; the interior stays buffered.

    Radiative equilibrium sets the mean; the lit face heats and the dark face
    cools around it. The massive, insulated interior barely moves.
    """
    S = P.SOLAR_1AU / design.au**2
    absorb = (1 - design.albedo)
    t = np.linspace(0, days, n)                          # days
    lit = np.clip(np.sin(2 * np.pi * t), 0, None)        # sun above the horizon
    T_mean = (absorb * S * 0.25 / P.SIGMA) ** 0.25       # radiative-equilibrium mean
    amp = 55.0                                           # diel surface swing (thermal-lagged)
    T_skin = T_mean + amp * np.sin(2 * np.pi * t - 1.0)
    T_interior = np.full_like(t, 293.0)                  # held by mass + the over-blanket
    return dict(t_days=t, T_skin=T_skin, T_interior=T_interior,
                T_mean=T_mean, lit=lit)


def energy_budget(design):
    """The two-engine metabolism: photosynthesis (air) vs mining (body)."""
    return dict(
        photo_biomass_tpd=0.45,      # what the lit hull can build
        growth_tpd=13.0,             # what it actually grows at
        area_ratio=29,               # x hull area to close growth by light
        feedstock_MW=1.4,            # chemical energy from asteroid organics
        synth_MW=(0.8, 2.6),         # energy to synthesise 13 t/day
        sunlight_MW=6.4,             # intercepted, mostly reflected
        ore_ratio=9,                 # ore : ship
    )


def gestation(design, n=240):
    """Cradle fill and embryo growth across the nursery, staggered by stage."""
    T = design.gestation_years * P.YEAR
    t = np.linspace(0, T * 1.6, n)                       # run past one cycle
    stages = np.linspace(0.0, 0.85, design.cradles)      # each cradle offset in its cycle
    # each cradle's embryo fraction cycles 0 -> 1 (hatch) -> 0
    phase = (t[:, None] / T + stages[None, :]) % 1.0
    frac = np.clip(1.2 * (0.5 - np.abs(phase - 0.5)) * 2, 0, 1)  # triangle up to hatch
    throughput = design.dep_ceiling_tpd                         # per-cradle deposition, t/day
    return dict(t_days=t, t_years=t / P.YEAR, frac=frac, stages=stages,
                throughput_tpd=throughput)
