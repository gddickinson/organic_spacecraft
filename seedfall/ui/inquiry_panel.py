"""The bench: what evidence you hold, what the programme wants, and how hard
you mean to push it."""

from __future__ import annotations

from ..core.util import num
from ..data.inquiry import EVIDENCE, EVIDENCE_BY_ID
from ..data.tech import PROVISIONAL_WORTH, TECH_BY_ID
from ..sim import inquiry
from .widgets import Panel, Pill, TabBar, button, label, mono_label, note, spacer


def lockers(game) -> Panel:
    """What is on the shelves, and where more of it comes from."""
    res = game.research
    p = Panel("The bench")
    p.add(note("A programme is fed by evidence, and the four kinds come from "
               "four different parts of the job. A propulsion programme cannot "
               "be fed by botany."))
    wanted = inquiry.needs(res.current, res) if res.current else {}
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
    # The cost that "days to unlock" cannot see, and without which pushing was
    # simply the best way to run every programme.
    p.add_row("Result comes out unreplicated", f"{current.provisional:.0%}",
              "warn" if current.provisional >= 0.3 else "")
    if current.provisional:
        p.add(note(f"An unreplicated technology works at "
                   f"{PROVISIONAL_WORTH:.0%} until somebody goes back over "
                   "the figures."))
    if not ok:
        p.add(label(why, "", "warn"))

    short = [EVIDENCE_BY_ID[k].name for k in getattr(res, "starved", []) or []]
    if short:
        p.add(spacer(3))
        p.add(label("The bench is marking time for want of "
                    + ", ".join(short).lower() + ".", "", "warn", wrap=True))
    return p


def unconfirmed(view, game) -> Panel | None:
    """Results that work and have not been checked.

    Pushing a programme hands you the technology and a debt: it delivers a
    fraction of what it promises until the work is confirmed. This is where
    the debt is visible and where it is paid.
    """
    res = game.research
    shaky = list(getattr(res, "provisional", []) or [])
    if not shaky and not getattr(res, "confirming", None):
        return None

    p = Panel("Unconfirmed results")
    p.add(note(f"These work at {PROVISIONAL_WORTH:.0%} of what they promise. "
               "Confirming one costs bench time and nothing else."))
    doing = getattr(res, "confirming", None)
    if doing:
        tech = TECH_BY_ID.get(doing)
        p.add_row(tech.name if tech else doing,
                  f"{res.confirm_days:.0f} days to go", "chloro")
    for tid in shaky:
        if tid == doing:
            continue
        tech = TECH_BY_ID.get(tid)
        if tech is None:
            continue
        cost = inquiry.confirm_cost(res, tid)
        p.add_row(tech.name, f"{cost:.0f} days to check", "warn")
        p.add_buttons(button(f"Confirm {tech.name}",
                             lambda t=tid: view.confirm(t),
                             enabled=not doing,
                             tip="Bench time. The programme under way keeps "
                                 "running." if not doing else
                                 "Something is already being checked."))
    return p
