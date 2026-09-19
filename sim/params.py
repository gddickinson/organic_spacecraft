"""Canonical parameters for the GESTALT design simulations.

Where a value is also a document number it is taken from ``calcs`` (the
package that recomputes, and checks, the documents' figures), so the
simulations cannot drift from the documents. The remaining literals are
design inputs quoted from the documents or labelled assumptions;
``sim.doccheck`` compares every one of them with the documents' values.

See ../INTERFACE.md and sim/INTERFACE.md for how the modules connect.
"""

from dataclasses import dataclass, field

from calcs import constants as CC
from calcs import growth as CG
from calcs import habitat as CH
from calcs import lifesupport as CL
from calcs import navis as CN

SOLAR_1AU = CC.S_1AU      # W/m^2, solar constant at 1 AU
SIGMA = CC.SIGMA          # Stefan-Boltzmann constant, W/m^2/K^4
DAY = CC.DAY_S            # s
YEAR = CC.YEAR_D          # days


@dataclass(frozen=True)
class Design:
    """A grown-vehicle design and the parameters its simulation needs."""
    key: str
    name: str
    kind: str                       # 'spheroid' | 'drum' | 'dome' | 'nursery'
    # geometry (metres) — semi-axes / radius / length as appropriate
    a: float = 0.0                  # long semi-axis or radius
    b: float = 0.0                  # short semi-axis
    length: float = 0.0
    # growth (Dossier model: dM/dt = min(M / tau, ceiling))
    mass_final_t: float = 0.0       # grown mass, tonnes
    growth_years: float = 5.0       # the documents' stated gestation (checked, not imposed)
    dep_ceiling_tpd: float = 16.0   # deposition ceiling, t/day
    tau_d: float = CG.TAU_D         # e-folding time of unconstrained growth, days
    m0_t: float = CG.NAVIS_M0       # germinated seed mass, tonnes
    crew: float = 0.0
    rpm: float = 0.0                # spin, if any
    # atmosphere
    air_mass_t: float = 0.0         # atmosphere mass, tonnes
    o2_mole_fraction: float = 0.21  # O2 share of the air by volume (moles)
    pressure_kpa: float = 101.0
    # life support (ARCA): light-driven photosynthesis with CO2 limitation
    veg_area_m2: float = 0.0        # vegetated area under the sun-cord
    o2_yield_g_m2_d: float = 20.0   # daily-mean O2 yield at saturating CO2 (assumed)
    co2_half_sat_ppm: float = 300.0     # CO2 at which photosynthesis runs at half rate
    co2_makeup_tpd: float = 0.0     # CO2 from mined carbonate, t/day (closes the RQ gap)
    # surface dome
    dome_span_m: float = 0.0
    dome_rise_m: float = 0.0
    # interior thermal RC (assumptions, labelled): wall conduction and heat capacity
    wall_m: float = 0.0             # insulating wall / over-blanket thickness, m
    wall_k: float = 0.0             # its effective conductivity, W/m/K
    wall_area_m2: float = 0.0
    heat_cap_j_k: float = 0.0       # interior heat capacity, J/K
    internal_w: float = 0.0         # internal heat load (people, metabolism), W
    # nursery
    cradles: int = 0
    gestation_years: float = 0.0
    albedo: float = 0.6             # hull reflectivity for the thermal model
    au: float = 1.0                 # heliocentric distance for the thermal model
    systems: tuple = field(default_factory=tuple)  # which panels to show

    @property
    def o2_mass_fraction(self):
        """O2 share of the air by mass (34 % by volume is ~37 % by mass)."""
        x = self.o2_mole_fraction
        return x * CC.M_O2 / (x * CC.M_O2 + (1 - x) * CC.M_N2)


_NG = CN.geometry()
_DOME_R = (CH.LICHEN_SPAN ** 2 / 4 + CH.LICHEN_RISE ** 2) / (2 * CH.LICHEN_RISE)
_DOME_AREA = 2 * 3.141592653589793 * _DOME_R * CH.LICHEN_RISE     # spherical cap
_DOME_FLOOR = 3.141592653589793 * (CH.LICHEN_SPAN / 2) ** 2
_DOME_VOL = 3.141592653589793 * CH.LICHEN_RISE ** 2 * (3 * _DOME_R - CH.LICHEN_RISE) / 3

# ---- the main designs, grounded in the program docs ----
DESIGNS = {
    "navis": Design(
        key="navis", name="NAVIS — the crewed explorer", kind="spheroid",
        a=CN.A_SEMI, b=CN.B_SEMI, length=2 * CN.A_SEMI,          # 100 x 50 m body
        mass_final_t=CN.MASS_T, growth_years=5.0, dep_ceiling_tpd=CG.WILD_RMAX,
        crew=CN.CREW, pressure_kpa=CN.P_CABIN / 1e3,
        # cabin-side wall: 5.5 m of mostly mycelial tissue (k ~0.05 W/m/K, assumed);
        # heat capacity dominated by the 0.5 m water-rich intima
        wall_m=CN.WALL_T, wall_k=0.05, wall_area_m2=_NG["area_in"],
        heat_cap_j_k=_NG["area_in"] * CN.INTIMA_T * 4.2e6, internal_w=5e3,
        albedo=0.6, au=1.0,
        systems=("growth", "metabolism", "thermal")),
    "arca": Design(
        key="arca", name="ARCA — the million-person world", kind="drum",
        a=CH.R, length=CH.L,
        mass_final_t=CH.DRUM_MASS / 1e3, growth_years=30.0,
        # the ceiling ARCA's ~30-year gestation implies
        dep_ceiling_tpd=CH.DRUM_MASS / 1e3 / (30.0 * YEAR), m0_t=3.0,
        rpm=CH.RPM, crew=float(CL.ARCA_POP),
        air_mass_t=CL.arca_air()["mass_t"], o2_mole_fraction=CL.ARCA_X_O2,
        pressure_kpa=CL.ARCA_P / 1e3,
        veg_area_m2=60e6, o2_yield_g_m2_d=20.0, co2_half_sat_ppm=300.0,
        co2_makeup_tpd=0.0, au=1.0,
        systems=("spin", "lifesupport")),
    "lichen": Design(
        key="lichen", name="LICHEN — the surface settlement", kind="dome",
        dome_span_m=CH.LICHEN_SPAN, dome_rise_m=CH.LICHEN_RISE, pressure_kpa=CH.P / 1e3,
        crew=10_000.0,
        # buried under the regolith over-blanket (k ~0.5 W/m/K compacted/icy, assumed);
        # heat capacity: interior air + 1 m of soil floor
        wall_m=CH.P / (CH.REGOLITH_RHO * 3.71), wall_k=0.5, wall_area_m2=_DOME_AREA,
        heat_cap_j_k=(_DOME_VOL * 0.6 * 1000.0
                      + _DOME_FLOOR * 1.0 * CH.REGOLITH_RHO * 800.0),
        internal_w=10_000 * 100.0,
        albedo=0.25, au=1.52,   # Mars distance
        systems=("thermal", "pressure")),
    "gravid": Design(
        key="gravid", name="GRAVID — the nursery", kind="nursery",
        length=1200.0, cradles=12, gestation_years=CG.time_to(CN.MASS_T, CG.NAVIS_M0,
                                                               CG.CRADLE_RMAX) / YEAR,
        dep_ceiling_tpd=CG.CRADLE_RMAX, au=1.0,
        systems=("gestation",)),
}

# palette matching the GESTALT identity (dark-field microscopy)
COL = dict(ground="#0a1512", ground2="#0e1c18", ink="#e2f0e8", ink2="#a9c2b6",
           ink3="#7c9689", chloro="#54cf7c", lumen="#4fd6d0", osteo="#e6ac6d",
           rock="#8a8072", shell="#b09e7e", warm="#d68c60", line="#2a3a34")
