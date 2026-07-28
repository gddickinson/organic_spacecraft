"""The development desk for one colony: what it has built, and what it could."""

from __future__ import annotations

from ..core.util import credits as cr
from ..core.util import duration, num
from ..data.works import MAX_WORKS, WORKS_BY_ID
from ..sim import works as works_sim
from .widgets import Panel, Pill, button, label, mono_label, note, spacer


def _cost_line(cost: dict) -> str:
    return " · ".join(cr(n) if k == "credits" else f"{n:g} {k}"
                      for k, n in cost.items())


def _gain_line(work) -> str:
    """What finishing this actually buys, in the player's terms."""
    bits = []
    for key, mul in work.yield_mul.items():
        bits.append(f"{key} ×{mul:g}")
    for key, add in work.yield_add.items():
        bits.append(f"+{cr(add)}/day" if key == "credits" else f"+{add:g} {key}/day")
    for key, value in work.effects.items():
        bits.append(f"{key} +{value:g}" if isinstance(value, (int, float))
                    else str(key))
    if work.pop_mul != 1.0:
        bits.append(f"population ×{work.pop_mul:g}")
    return " · ".join(bits) or "—"


def build(view, game, col) -> Panel:
    """The works panel for one colony. ``view`` supplies the callbacks."""
    p = Panel(f"Develop · {col.name}")
    finished = works_sim.done(col)
    p.add_row("Works", f"{len(finished)}/{MAX_WORKS}",
              "chloro" if finished else "dim")

    if finished:
        p.add(spacer(3), mono_label("Standing"))
        for work in finished:
            p.add_row(work.name, _gain_line(work), "chloro")

    job = getattr(col, "job", None)
    if job:
        work = WORKS_BY_ID.get(job)
        if work is not None:
            left = max(0, work.days - getattr(col, "job_days", 0.0))
            p.add(spacer(4), mono_label("Under way"))
            p.add(label(work.name, "h3", "lumen"))
            p.add_row("Remaining", duration(left))
            p.add_bar(works_sim.progress(col), "lumen")
            p.add_buttons(button("Abandon it",
                                 lambda: view.abandon_work(col),
                                 kind="danger"))
        return p

    offers = works_sim.available(game, col)
    if not offers:
        p.add(spacer(3))
        p.add(note("There is nothing further to build here. This is what the "
                   "place is now."))
        return p

    p.add(spacer(4), mono_label("Could be built"))
    for work, ok, why in offers:
        p.add(spacer(3))
        p.add(label(work.name, "h3", "chloro" if ok else "dim"))
        p.add(note(work.blurb))
        p.add_row(_cost_line(work.cost), duration(work.days))
        p.add_row("Buys you", _gain_line(work), "lumen" if ok else "dim")
        if not ok:
            p.add(label(why, "", "warn"))
        p.add_buttons(button(f"Begin — {duration(work.days)}",
                             lambda _=False, wid=work.id: view.begin_work(col, wid),
                             kind="primary" if ok else "", enabled=ok))
    return p
