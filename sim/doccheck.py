"""Check the simulations' parameters and outputs against the documents' numbers.

The reference values come from ``calcs``, whose own ``--check`` ties each of
them to the number printed in the documents; together the two checks close
the loop from ``sim/params.py`` to the published text.
"""

from calcs.registry import all_values

from . import params as P
from . import systems as S


def rows():
    v = {k: x.value for k, x in all_values().items()}
    nav, arc, lic, grv = (P.DESIGNS[k] for k in ("navis", "arca", "lichen", "gravid"))
    g_nav, g_arc = S.growth(nav), S.growth(arc)
    ls = S.life_support(arc, years=1, n=10)
    sp = S.spin_gravity(arc)
    eb = S.energy_budget(nav)
    return [
        # (what, sim value, document value, relative tolerance)
        ("NAVIS body length, m (drawings: 100)", 2 * nav.a, 100.0, 0.0),
        ("NAVIS beam, m (drawings: 50)", 2 * nav.b, 50.0, 0.0),
        ("NAVIS grown mass, t", nav.mass_final_t, v["navis.mass"], 0.0),
        ("NAVIS gestation, yr", g_nav["gestation_years"], v["growth.navis_years"], 0.02),
        ("NAVIS crew", nav.crew, 50.0, 0.0),
        ("NAVIS growth, t/day", eb["growth_tpd"], v["metab.growth_tpd"], 0.02),
        ("ore : ship", eb["ore_ratio"], v["metab.ore_ratio"], 0.02),
        ("ARCA drum mass, Gt (docs: 2-3)", arc.mass_final_t / 1e9, 2.5, 0.2),
        ("ARCA gestation, yr (docs: ~30)", g_arc["gestation_years"], 30.0, 0.15),
        ("ARCA air, Mt", arc.air_mass_t / 1e6, v["life.arca_air"], 0.01),
        ("ARCA O2 by mass", arc.o2_mass_fraction, v["life.arca_o2_mass_frac"], 0.01),
        ("ARCA O2 reserve, yr", ls["buffer_years"], v["life.arca_o2_reserve"], 0.02),
        ("ARCA rim gravity, g", sp["g_rim"] / 9.80665, v["habitat.g_rim"], 0.01),
        ("ARCA population", arc.crew, 1e6, 0.0),
        ("LICHEN span / rise, m", lic.dome_span_m + lic.dome_rise_m / 1e3, 500.15, 0.0),
        ("LICHEN over-blanket, m", lic.wall_m, v["habitat.lichen_blanket_mars"], 0.01),
        ("GRAVID cradles (docs: 12-24)", grv.cradles, 18.0, 0.34),
        ("GRAVID gestation, yr", grv.gestation_years, v["growth.gravid_years"], 0.01),
        ("GRAVID feed, t/day", grv.dep_ceiling_tpd, 26.0, 0.0),
    ]


def check(verbose=True):
    bad, rs = 0, rows()
    for what, sim, doc, tol in rs:
        ok = abs(sim - doc) <= tol * abs(doc) + 1e-9
        bad += not ok
        if verbose or not ok:
            print(f"  {'ok' if ok else 'MISMATCH':8s} {what:40s} sim={sim:<12.5g} docs={doc:.5g}")
    print(f"params vs documents: {len(rs)} checks, {bad} mismatch(es)")
    return bad == 0
