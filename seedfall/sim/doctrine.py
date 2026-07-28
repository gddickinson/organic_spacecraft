"""The battle computer: what the stations you are not sitting at should do.

You are one person on a bridge with three seats. You take one personally each
turn and the officers hold the other two — and what "hold" meant was literal:

    if not directed:
        order_id = side.helm_order or "hold"    # repeat, forever

An unattended helm repeated whatever you last told it until you came back to
it. Order *close* on turn one and go to gunnery, and the helm would fly you
straight down the enemy's throat at point-blank for the rest of the
engagement, past the range where your own mounts stop bearing, while a
perfectly competent navigator sat there doing exactly what they were told.
That is not a hard choice about where to spend your attention. It is a
punishment for looking away.

So: a battle computer chooses. It reads the plane — range band, aspect, heat,
hull, what bears — and picks an order for each seat nobody is in, and it says
which and why *before* the turn resolves.

**It is not free and it is not better than you.** `doctrine` is a stat off the
compute fitting, from 0.15 for the wet-stack core you launch with to 1.00 for
a Cold Ledger. Below `MINIMUM` there is no computer and the old repeat-forever
behaviour stands, which is what every existing check was written against.
Above it, the computer picks from a shortlist that widens with the rating: a
poor one keeps you out of trouble, a good one fights the ship. And a station
you sit at yourself still gets the full turn rate and the better shooting, so
the reason to choose a seat is untouched — the computer only stops the other
two seats being stupid.
"""

from __future__ import annotations

from . import assessment, tactical as tac

#: Below this the hull has no battle computer worth the name and stations fall
#: back to repeating their last order — the behaviour the game shipped with.
MINIMUM = 0.30

#: Heat, as a share of the cap, at which the computer stops shooting and
#: starts venting whatever else is going on.
HOT = 0.82

#: Hull integrity below which it stops trading and starts trying to leave.
HURT = 0.35


def fitted(stats) -> bool:
    """Does this hull have a battle computer at all?"""
    return getattr(stats, "doctrine", 0.0) >= MINIMUM


def grade(stats) -> str:
    """What to call it on a screen."""
    rating = getattr(stats, "doctrine", 0.0)
    if rating < MINIMUM:
        return "none"
    if rating < 0.5:
        return "rudimentary"
    if rating < 0.75:
        return "competent"
    return "excellent"


def _hull_share(side) -> float:
    total = sum(layer.max for layer in side.ship.layers) or 1.0
    return sum(layer.hp for layer in side.ship.layers) / total


def _heat_share(side) -> float:
    cap = getattr(side.st, "heat_cap", 0) or 1.0
    return getattr(side.ship, "heat", 0) / cap


def _bearing_count(side, other) -> int:
    """How many mounts have the target in their arc right now.

    The mounts hang off `side.st.weapons`, not `side.weapons` — reading the
    latter silently returned an empty list, so every count was zero, gunnery
    always concluded "nothing bears" and the helm came about forever chasing
    an arc it was already in. Nothing raised; it simply gave bad advice with
    complete confidence.
    """
    rel = tac.relative_bearing(side.body, other.body)
    mounts = getattr(side.st, "weapons", None) or []
    return sum(1 for w in mounts if tac.bears(tac.arc_of(w), rel))


def _band(side, other) -> int:
    """Range band between two hulls, from the plane rather than the Battle.

    Taking the band off `battle.range_units` coupled every decision to a
    Battle object that `run_helm` does not have — it is handed two sides and
    nothing else. The two bodies already know how far apart they are.
    """
    return tac.band_for(tac.separation(side.body, other.body))


def helm(side, other) -> tuple[str, str]:
    """Where to put the bow, and why."""
    rating = side.st.doctrine
    band = _band(side, other)
    want = assessment.preferred_band(side)
    hull = _hull_share(side)

    if hull < HURT and side.st.speed > other.st.speed * 1.08:
        return "open", (f"Hull at {hull*100:.0f}%. We are faster than they "
                        "are; break off before the next exchange.")

    if want is not None:
        low, high = want
        if band > high:
            return "close", (f"Our mounts want band {low}–{high} and we are "
                             f"at {band}. Closing.")
        if band < low:
            return "open", (f"We are inside our own envelope at band {band}; "
                            f"the mounts want {low}–{high}. Opening.")

    # In the envelope: point the guns. A better computer knows that turning to
    # bear beats closing further once the range is already right.
    if rating >= 0.5 and _bearing_count(side, other) == 0:
        return "comeabout", ("In the envelope with nothing bearing. Swinging "
                             "the bow across.")
    if rating >= 0.75 and band <= 2 and _bearing_count(side, other) < 2:
        return "broadside", ("Close and only part of the battery bears. "
                             "Turning beam-on.")
    return "hold", (f"Band {band} suits us. Holding the aspect we have.")


def gunnery(side, other) -> tuple[str, str]:
    """What to shoot with, and why."""
    rating = side.st.doctrine
    heat = _heat_share(side)
    bearing = _bearing_count(side, other)

    if heat > HOT:
        return "hold_fire", (f"Hull at {heat*100:.0f}% of the heat cap. "
                             "Holding fire before something warps.")
    if bearing == 0:
        return "hold_fire", "Nothing bears. No sense cooking the mounts."
    if rating >= 0.5 and heat > 0.6 and bearing > 1:
        return "aimed", (f"Warm at {heat*100:.0f}%. One mount, carefully, "
                         "rather than the lot.")
    if bearing > 1:
        return "salvo", f"{bearing} mounts bear. Everything that will."
    return "aimed", "One mount bears. Taking the time to place it."


def engineering(side, other) -> tuple[str, str]:
    """What to do with the power and the damage, and why."""
    rating = side.st.doctrine
    heat = _heat_share(side)
    hull = _hull_share(side)
    breached = any(layer.hp <= 0 for layer in side.ship.layers)

    if heat > HOT:
        return "vent", f"Heat at {heat*100:.0f}%. Dumping everything we can."
    if breached:
        return "damage_control", "A layer is open. Patching it."
    if rating >= 0.5 and hull < HURT:
        return "route_engines", (f"Hull at {hull*100:.0f}%. Power to the "
                                 "drive; we need to not be here.")
    if rating >= 0.5 and _bearing_count(side, other) > 0 and heat < 0.5:
        return "route_guns", "Cool and bearing. Power to the mounts."
    return "vent", "Nothing urgent. Keeping the hull cold."


#: Which function answers for which seat.
SEATS = {"helm": helm, "gunnery": gunnery, "engineering": engineering}


def order_for(side, other, station: str) -> tuple[str, str] | None:
    """The computer's order for one seat, or None if there is no computer."""
    if not fitted(side.st) or other is None:
        return None
    chooser = SEATS.get(station)
    if chooser is None:
        return None
    return chooser(side, other)


def plan(battle, side=None, other=None) -> dict:
    """What the computer intends at every seat nobody is sitting in.

    The battle screen shows this *before* the turn resolves, because a system
    that acts on your behalf without saying what it is about to do is the
    defect this project keeps finding, wearing a uniform.
    """
    side = side or battle.player
    other = other or battle.enemy
    if not fitted(side.st):
        return {}
    taken = getattr(side, "station", None)
    out = {}
    for station in SEATS:
        if station == taken:
            continue
        got = order_for(side, other, station)
        if got:
            out[station] = got
    return out


def note(side) -> str:
    """One line for a screen: what this hull's computer is worth."""
    rating = getattr(side.st, "doctrine", 0.0)
    if not fitted(side.st):
        return ("No battle computer. Any station you are not sitting at "
                "repeats its last order until you come back to it.")
    return (f"Battle computer: {grade(side.st)} ({rating:.2f}). Stations you "
            "leave will choose for themselves.")
