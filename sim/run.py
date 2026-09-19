"""Command-line entry point for the GESTALT simulations.

Examples
--------
    python -m sim.run                 # render every design's animation
    python -m sim.run navis arca      # just these two
    python -m sim.run --fast          # low frame-count smoke test
    python -m sim.run --check         # import + run the models, render nothing
"""

import argparse
import os
import time

from . import params
from . import systems
from . import animate

ORDER = ["navis", "arca", "lichen", "gravid"]


def preview_png(gif_path):
    """Extract a representative middle frame from a GIF as a PNG (for docs/checks)."""
    from PIL import Image
    im = Image.open(gif_path)
    im.seek(im.n_frames // 2)
    out = gif_path.replace(".gif", "-preview.png")
    im.convert("RGB").save(out)
    return out


def check():
    """Run every system model once, then check parameters and documents."""
    from . import doccheck
    from calcs.docscheck import check as docs_check
    for k in ORDER:
        d = params.DESIGNS[k]
        if d.mass_final_t:
            g = systems.growth(d)
            print(f"  ok  {k:8s} growth: {g['mass_t'][-1]:,.0f} t in {g['gestation_years']:.1f} yr")
        if d.wall_m:
            th = systems.thermal(d)
            print(f"  ok  {k:8s} thermal: skin mean {th['T_mean']:.0f} K, interior RC "
                  f"tau {th['tau_years']:.2f} yr, steady {th['T_steady']:.0f} K")
        if d.rpm:
            sp = systems.spin_gravity(d)
            print(f"  ok  {k:8s} spin: {sp['g_rim'] / 9.80665:.3f} g at the rim")
        if d.air_mass_t:
            ls = systems.life_support(d, years=5, n=50)
            print(f"  ok  {k:8s} air: O2 reserve {ls['buffer_years']:.0f} yr, CO2 settles "
                  f"{ls['co2_ppm'][-1]:.0f} ppm, O2 drifts {ls['o2_drift_pct_per_century']:+.2f} "
                  f"points/century without carbonate make-up")
        if d.cradles:
            ge = systems.gestation(d)
            print(f"  ok  {k:8s} nursery: {ge['ships_per_year']:.1f} ships/yr")
    systems.energy_budget(params.DESIGNS["navis"])
    print("all system models validated")
    ok = doccheck.check(verbose=False)
    ok_docs, _ = docs_check(verbose=False)
    return 0 if ok and ok_docs else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render GESTALT design simulations")
    ap.add_argument("designs", nargs="*", help="subset of: " + ", ".join(ORDER))
    ap.add_argument("--outdir", default="assets/sim")
    ap.add_argument("--fast", action="store_true", help="few frames — a quick smoke test")
    ap.add_argument("--check", action="store_true", help="validate models, render nothing")
    a = ap.parse_args(argv)

    if a.check:
        raise SystemExit(check())

    keys = a.designs or ORDER
    os.makedirs(a.outdir, exist_ok=True)
    for k in keys:
        d = params.DESIGNS[k]
        out = os.path.join(a.outdir, f"sim-{k}.gif")
        kw = dict(frames=6, fps=6) if a.fast else {}
        t0 = time.time()
        animate.BUILDERS[k](d, out, **kw)
        png = preview_png(out)
        sz = os.path.getsize(out) // 1024
        print(f"  ok  {k:8s} -> {out} ({sz} KB, {time.time()-t0:.1f}s)  + {os.path.basename(png)}")
    print(f"rendered {len(keys)} simulation(s) to {a.outdir}/")


if __name__ == "__main__":
    main()
