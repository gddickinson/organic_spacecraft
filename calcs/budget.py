"""Earth Program ground budget: burn rate x phase span, and the kill points."""

from .value import V, collect

# (phase, burn $B/yr, span yr) — Earth Program cost table
PHASES = [("P0", 0.25, 5), ("P1", 0.45, 7), ("P2", 0.70, 15), ("P3", 1.20, 15)]
YEARS = 40
CELLS_NOW = 1e6          # most cells patterned by directed morphogenesis today
CELLS_HULL = 1e19        # order of a NAVIS hull (navis.cells)


def values():
    cum, out = 0.0, {}
    for name, burn, span in PHASES:
        cost = burn * span
        cum += cost
        out[f"{name.lower()}_cost"] = V(cost, "$B")
        out[f"{name.lower()}_cum"] = V(cum, "$B")
    total = cum
    running = 0.0
    for name, burn, span in PHASES:
        running += burn * span
        out[f"{name.lower()}_pct"] = V(100 * running / total, "%", tol=0.12)
    out["total"] = V(total, "$B")
    out["per_year"] = V(total / YEARS, "$B/yr")
    from math import log10
    out["orders_gap"] = V(log10(CELLS_HULL / CELLS_NOW), "orders", tol=0.08)
    return collect("budget", **out)
