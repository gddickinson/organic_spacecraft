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
    """Run every system model once so numbers/shapes are validated without rendering."""
    for k in ORDER:
        d = params.DESIGNS[k]
        systems.growth(d); systems.thermal(d); systems.energy_budget(d)
        if d.rpm:
            systems.spin_gravity(d)
        if d.air_mass_t:
            systems.life_support(d, years=5, n=50)
        if d.cradles:
            systems.gestation(d)
        print(f"  ok  {k:8s} models run clean")
    print("all system models validated")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render GESTALT design simulations")
    ap.add_argument("designs", nargs="*", help="subset of: " + ", ".join(ORDER))
    ap.add_argument("--outdir", default="assets/sim")
    ap.add_argument("--fast", action="store_true", help="few frames — a quick smoke test")
    ap.add_argument("--check", action="store_true", help="validate models, render nothing")
    a = ap.parse_args(argv)

    if a.check:
        return check()

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
