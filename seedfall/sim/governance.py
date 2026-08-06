"""The one front door for the whole governance layer.

Six modules do the work — `dockets` alleges and files, `tribunal` hears,
`debts` collects, `warrants` enforce, `enforce` puts hulls alongside,
`clemency` forgives — and the clock asks exactly one of them. This is the
same shape as `sim/flightdeck.py`, and for the same reason: the alternative
is six calls in `core/clock.py`, in an order nobody wrote down, which the
next person to touch the file gets wrong.

**The order here is the law's order and it matters.** Sweep before hearing,
so a charge filed this month is not also decided this month and a captain
always has the notice the forum promised. Hear before collecting, so a
verdict's debt is not chased on the tick it was created. Collect before
lifting, so a debt paid this tick lifts its instrument this tick rather than
next month. Enforce last, because a patrol should act on the state of the
file as it stands *after* everything else has happened, not before.
"""

from __future__ import annotations

from . import law as law_sim


def tick(game, days: float, rng) -> list:
    """Run the law for `days`. Returns `(kind, text)` lines for the log.

    **Guarded against re-entering itself.** Anything down here that moves the
    calendar — a detention, a tow, a seizure — would come back through
    `core/clock.advance_days` into this function, and the recursion surfaces
    somewhere else entirely: measured once as a `RecursionError` raised in
    `settlement.maturity`, three modules from the cause. The flag costs
    nothing and makes that class of bug impossible rather than unlikely.
    """
    from . import clemency, debts, dockets, enforce, tribunal
    if getattr(game, "flags", None) is not None:
        if game.flags.get("law_running"):
            return []
        game.flags["law_running"] = True
    try:
        return _run(game, days, rng, clemency, debts, dockets, enforce,
                    tribunal)
    finally:
        if getattr(game, "flags", None) is not None:
            game.flags.pop("law_running", None)


def _run(game, days, rng, clemency, debts, dockets, enforce, tribunal) -> list:
    out: list = []
    out.extend(dockets.sweep(game, days, rng))
    out.extend(tribunal.tick(game, days, rng))
    out.extend(debts.tick(game, days, rng))
    out.extend(clemency.tick(game, days, rng))
    out.extend(enforce.tick(game, days, rng))
    return out


def standing_with(game, power: str) -> dict:
    """Everything the law says about one power, for a screen or a hail."""
    from . import debts, dockets, tribunal, warrants
    from ..data.forums import forum_of
    forum = forum_of(power)
    live = law_sim.open_charges(game, power)
    return {
        "power": power,
        "forum": forum.name if forum else "",
        "form": forum.form if forum else "",
        "blurb": forum.blurb if forum else "",
        "exposure": dockets.exposure(game, power),
        "open": len(live),
        "filed": len([c for c in live if c.state in ("filed", "answered")]),
        "owed": debts.total_owed(game, power),
        "warrants": [w for w in warrants.summary(game) if w["power"] == power],
        "summons": [c for c in tribunal.summons(game) if c.power == power],
        "note": dockets.note_for(game, power),
    }


def trouble(game) -> float:
    """One number for how much trouble the captain is in, sector-wide.

    The status bar reads this. It is deliberately not a reputation: standing
    is what they think of you and this is what they are *doing* about it, and
    a chronicle can absolutely have one without the other.
    """
    from ..data.offences import LAWFUL
    from . import dockets, warrants
    total = sum(dockets.exposure(game, p) for p in LAWFUL)
    total += 1.2 * len(warrants.in_force(game))
    return round(total, 2)


def note(game) -> str:
    """The status line. "" when the captain is in the clear."""
    from . import debts, warrants
    standing = warrants.worst(game)
    if standing is not None:
        return warrants.note(game)
    owed = debts.note(game)
    if owed:
        return owed
    filed = [c for c in law_sim.ensure(game).charges if c.state == "filed"]
    if filed:
        return f"{len(filed)} charge(s) outstanding"
    return ""


def any_business(game) -> bool:
    """Is there anything at all on the law screen? Keeps a dead tab hidden."""
    state = law_sim.ensure(game)
    return bool(state.charges or state.debts or state.warrants)
