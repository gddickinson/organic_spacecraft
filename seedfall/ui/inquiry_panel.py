"""The bench: what evidence you hold, what the programme wants, and how hard
you mean to push it."""

from __future__ import annotations

from ..core.util import num
from ..data.inquiry import EVIDENCE, EVIDENCE_BY_ID
from ..data.tech import TECH_BY_ID
from ..sim import inquiry
from .widgets import Panel, Pill, TabBar, button, label, mono_label, note, spacer


def lockers(game) -> Panel:
    """What is on the shelves, and where more of it comes from."""
    res = game.research
    p = Panel("The bench")
    p.add(note("A programme is fed by evidence, and the four kinds come from "
               "four different parts of the job. A propulsion programme cannot "
               "be fed by botany."))
    wanted = inquiry.needs(res.current) if res.current else {}
    for kind in EVIDENCE:
        have = inquiry.held(res, kind.id)
        need = wanted.get(kind.id, 0.0)
        if need > 0:
            tint = "chloro" if have >= need * 0.25 else "warn"
            value = f"{num(round(have))} held · {num(round(need))} wanted"
        else:
            tint = "dim"
            value = f"{num(round(have))} held"
        p.add_row(kind.name, value, tint)
        p.add(note(kind.where))
    return p


def approaches(view, game) -> Panel | None:
    """How to run the programme under way."""
    res = game.research
    if not res.current:
        return None
    tech = TECH_BY_ID.get(res.current)
    if tech is None:
        return None

    current = inquiry.approach_of(res)
    p = Panel("How to run it")
    offers = inquiry.available(game)
    tabs = TabBar([(a.id, a.name) for a, _ok, _why in offers], current.id)
    tabs.changed.connect(view.set_approach)
    p.add(tabs)
    p.add(note(current.blurb))

    ok, why = next(((o, w) for a, o, w in offers if a.id == current.id), (True, ""))
    p.add_row("Pace", f"×{current.speed:g}")
    p.add_row("Evidence drawn", f"×{current.draw:g}",
              "warn" if current.draw > 1.5 else "")
    p.add_row("Setback in a season", f"{current.setback:.0%}",
              "warn" if current.setback >= 0.2 else "")
    p.add_row("Breakthrough in a season", f"{current.breakthrough:.0%}",
              "chloro" if current.breakthrough >= 0.15 else "")
    if not ok:
        p.add(label(why, "", "warn"))

    short = [EVIDENCE_BY_ID[k].name for k in getattr(res, "starved", []) or []]
    if short:
        p.add(spacer(3))
        p.add(label("The bench is marking time for want of "
                    + ", ".join(short).lower() + ".", "", "warn", wrap=True))
    return p
