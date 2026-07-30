"""What the picket mesh is hearing, from systems you are not in.

The traffic module has always been able to derive the hulls working *any*
system — it is a pure function of the sector and the day — and nothing ever
asked it about anywhere but the system the ship was sitting in. So the chart
could not warn a captain that two raiders were working the system they were
about to jump into, which is the complaint `sim/traffic.py` opens with.

Being able to see it is what a CHORUS Node buys, and this panel is where the
purchase shows. Everything here comes from `traffic.watched`, which is the same
`mesh_reaches` the sim asks — a screen that decided for itself which systems it
could see would eventually disagree with the one that decides what an encounter
rolls against.
"""

from __future__ import annotations

from ..sim import traffic as traffic_sim
from .widgets import Panel, label, note, spacer


def chart_mark(game, system) -> int:
    """Hostile hulls the mesh is reporting in this system, for the chart.

    The sector chart draws a marker where this is non-zero, because a system
    reporting hulls nobody claims is the one thing a captain wants to know
    *before* committing to a jump — the panel below is the detail, and the chart
    is the warning.

    Zero where the mesh does not reach, which is not the same as zero hostiles,
    and is why the panel says which systems are being heard from at all.
    """
    return sum(1 for hull in traffic_sim.plotted(game, system) if hull.hostile)


def build(game) -> Panel | None:
    """None when nothing of yours is listening beyond the system you are in."""
    rows = traffic_sim.watched(game)
    elsewhere = [row for row in rows if not row["here"]]
    aboard = bool(getattr(game.ship_stats, "has_drift", False))
    if not elsewhere and not aboard:
        return None

    p = Panel("What the mesh is hearing")
    p.add(note("A CHORUS Node reconciles against every other node in the mesh, "
               "so it hears what they hear — in systems you have stood in, and "
               "wherever a Node of your own is planted. Traffic elsewhere is "
               "still there; you simply cannot see it."))
    if not elsewhere:
        p.add(spacer(3))
        p.add(note("Nothing beyond this system is reporting yet. The mesh needs "
                   "somewhere it has been: fly, and the places you have stood "
                   "stay plotted."))
        return p

    trouble = sum(row["hostile"] for row in elsewhere)
    p.add_row("Systems reporting",
              f"{len(elsewhere)} beyond this one",
              "chloro" if not trouble else "warn")
    if trouble:
        p.add_row("Running dark out there",
                  f"{trouble} hull{'' if trouble == 1 else 's'} nobody claims",
                  "warn")

    for row in elsewhere[:8]:
        system = row["system"]
        hulls = row["hulls"]
        p.add(spacer(3))
        p.add(label(system.name, "h3",
                    "warn" if row["hostile"] else ""))
        kinds = {}
        for hull in hulls:
            kinds[hull.errand] = kinds.get(hull.errand, 0) + 1
        p.add_row("Working the system",
                  " · ".join(f"{n} {kind}" for kind, n in sorted(kinds.items())))
        if row["hostile"]:
            p.add_row("Of those", f"{row['hostile']} running dark", "warn")
    return p
