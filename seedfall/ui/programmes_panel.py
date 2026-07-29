"""Standing programmes: what the bench runs once it has learned everything,
and what becomes of what it finds."""

from __future__ import annotations

from ..core.util import num
from ..data.factions import FACTIONS_BY_ID
from ..data.programmes import PROGRAMMES_BY_ID
from ..sim import programmes as prog_sim
from .widgets import Panel, button, label, mono_label, note


def running(view, game) -> Panel | None:
    """Which programme the bench is on, and which it could be on.

    Returns None while no branch is complete, because a captain who has not
    finished a branch should not be shown a board of things they cannot do.
    """
    open_now = prog_sim.available(game)
    if not open_now:
        return None

    live = prog_sim.state(game)
    p = Panel("Standing programmes")
    p.add(note("A branch you have finished leaves a line of inquiry that never "
               "does. Each round costs more than the last and yields a finding "
               "— which buys standing or money, and never a better hull."))

    spare = game.research.spare
    if game.research.current is None and spare >= 0:
        p.add_row("Points the tree cannot use", f"{num(round(spare))} waiting",
                  "chloro" if live.current else "warn")
    for spec in open_now:
        done = int(live.rounds.get(spec.id, 0))
        cost = prog_sim.round_cost(game, spec.id)
        here = live.current == spec.id
        share = live.progress / cost if here and cost else 0.0
        value = (f"round {done + 1} · {num(round(cost))} points"
                 + (f" · {share:.0%} done" if here else ""))
        p.add_row(("▶ " if here else "") + spec.name, value,
                  "chloro" if here else "dim")
        p.add(note(spec.blurb))
        if not here:
            p.add(button(f"Put the bench on {spec.name.lower()}",
                         lambda i=spec.id: _switch(view, i), kind="flat"))
    if live.current:
        p.add(button("Stand the bench down",
                     lambda: _switch(view, None), kind="flat"))
    return p


def findings(view, game) -> Panel | None:
    """What is in hand, and the three things that can be done with it."""
    live = prog_sim.state(game)
    if not live.findings:
        return None

    p = Panel("Findings in hand")
    p.add(note("Filed with one power it is worth most to them and costs you "
               "with their rivals. Published it reaches all four and thanks "
               "you less. Sold it buys nothing but money."))
    for found in list(live.findings):
        spec = PROGRAMMES_BY_ID.get(found.programme)
        if spec is None:
            continue
        p.add_row(f"{spec.name} — round {found.round}",
                  f"day {found.day} · worth {found.worth:g}", "lumen")

        sell = prog_sim.preview(game, found, "sell")
        openly = prog_sim.preview(game, found, "publish")
        p.add(mono_label(
            "publish: " + "  ".join(
                f"{_short(who)} {gain:+.1f}" for who, gain in openly["standing"])))
        p.add(button(f"Publish openly (+{sum(g for _w, g in openly['standing']):.0f} "
                     "across the sector)",
                     lambda f=found: _spend(view, f, "publish"), kind="flat"))
        for power in prog_sim.powers(game):
            plan = prog_sim.preview(game, found, "file", power)
            if not plan.get("ok"):
                continue
            gain = next((g for w, g in plan["standing"] if w == power), 0.0)
            cost = -sum(g for w, g in plan["standing"] if g < 0)
            text = (f"File with the {_short(power)} (+{gain:.0f}"
                    + (f", −{cost:.0f} elsewhere)" if cost else ")"))
            p.add(button(text, lambda f=found, w=power: _spend(view, f, "file", w),
                         kind="flat"))
        p.add(button(f"Sell it ({num(sell['credits'])} credits)",
                     lambda f=found: _spend(view, f, "sell"), kind="flat"))
    return p


def _short(power: str) -> str:
    got = FACTIONS_BY_ID.get(power)
    return got.short if got is not None else power


def _switch(view, programme_id) -> None:
    prog_sim.set_programme(view.game, programme_id)
    if programme_id:
        spec = PROGRAMMES_BY_ID[programme_id]
        view.win.toast(f"The bench takes up {spec.name.lower()}.")
    else:
        view.win.toast("The bench stands down.")
    view.win.refresh()


def _spend(view, found, door: str, power: str | None = None) -> None:
    out = prog_sim.spend(view.game, found, door, power)
    if not out.get("ok"):
        view.win.toast(out.get("why", "That cannot be done."))
        return
    if door == "sell":
        view.win.toast(f"Sold for {num(out['credits'])} credits.")
    else:
        view.win.toast(", ".join(f"{_short(w)} {g:+.1f}"
                                 for w, g in out["standing"]))
    view.win.refresh()
