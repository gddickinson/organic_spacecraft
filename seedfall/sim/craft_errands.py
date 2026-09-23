"""What a craft is *for*, once she is off the cradle: a run and a look.

Split out of `sim/craft.py` when it reached five hundred lines, along the
seam the file already had a heading for. `sim/craft.py` is the cradle, the
ticket and the flight; this is the two errands a single seat is sent on —
a firing run at a hull inside `engage.REACH_KM`, and an hour over something
worth looking at, which is survey data on the bench and a world properly on
the chart.

Not a fleet action: opening a battle is the ship's business (`sim/combat`),
and what a craft does inside one is `sim/craft_battle.py`. Re-exported from
`sim/craft.py`, so `craft.strike` is still the door every screen asks.
"""

from __future__ import annotations

from ..data import craft as table
from .craft import STRIKE_T, flying, kind_of, lose, sortie

#: What an hour of looking is worth as survey data, and how long a look
#: takes. They live here because this is the only module that spends them.
SCOUT_DATA, SCOUT_HOURS = 18.0, 1.0
#: The share of the target's own weight of fire that comes back at her.
RETURN_FIRE = 0.5


def targets(game) -> list:
    """Everything out here a craft could make a run at: the hulls, nearest
    first. A craft strafes ships; it does not shoot at worlds."""
    from . import engage, track
    conn = sortie(game)
    if conn is None:
        return []
    rows = [c for c in track.contacts(game) if c.kind == "hull"]
    return sorted(rows, key=lambda c: engage.range_km(game, conn, c))


def can_strike(game, contact) -> tuple:
    """May she make a run at this one?"""
    craft, conn = flying(game), sortie(game)
    if craft is None or conn is None:
        return False, "Nothing is out."
    if not kind_of(craft).guns:
        return False, f"{craft.name} carries no guns."
    if getattr(contact, "kind", "") != "hull":
        return False, "A craft strafes ships, not worlds."
    if craft.fuel <= STRIKE_T:
        return False, "No reaction mass for a run."
    from . import engage
    km = engage.range_km(game, conn, contact)
    if km > engage.REACH_KM:
        return False, (f"{km:,.0f} km — a run is made inside "
                       f"{engage.REACH_KM:,.0f} km.")
    return True, ""


def strike(game, contact, rng=None) -> dict:
    """One firing run: her guns at a hull, and whatever comes back.

    Not a fleet action — that is `sim/combat`, and opening a battle is the
    *ship's* business. This is what a single seat does: a pass, some damage,
    and the answer from whatever the other hull is carrying.
    """
    ok, why = can_strike(game, contact)
    if not ok:
        return {"ok": False, "why": why}
    craft = flying(game)
    rng = rng if rng is not None else game.rng("craft")
    kind = kind_of(craft)
    craft.fuel = max(0.0, craft.fuel - STRIKE_T)
    dealt = sum(sum(rng.int(1, 6) for _n in range(dice))
                for _name, dice in kind.guns)
    hostile = bool(getattr(contact, "hostile", False))
    back = 0
    if hostile:
        # What a working hull throws back at something the size of a launch.
        back = int(max(0, sum(rng.int(1, 6) for _n in range(2))
                       * RETURN_FIRE - kind.armour))
        craft.hp = max(0, craft.hp - back)
    craft.struck += 1
    from . import dockets, hostiles
    hull_id = getattr(contact, "hull_id", None) or contact.id
    hostiles.mark(game, hull_id)
    dockets.report(game, "affray",
                   f"{craft.name} made a firing run on {contact.name}",
                   weight=1.0)
    text = (f"{craft.name} runs in on {contact.name}: {dealt} through her "
            + ("plating" if hostile else "flank")
            + (f", and {back} back." if back else "."))
    game.add_log(text, "bad")
    conn = sortie(game)
    if conn is not None:
        conn.log.append(text)
    if craft.hp <= 0:
        return dict(lose(game, f"shot down by {contact.name}"), dealt=dealt,
                    took=back, text=text)
    return {"ok": True, "dealt": dealt, "took": back, "text": text,
            "hp": craft.hp}


def can_scout(game, contact) -> tuple:
    """May she go and look at this?"""
    craft, conn = flying(game), sortie(game)
    if craft is None or conn is None:
        return False, "Nothing is out."
    if getattr(contact, "kind", "") not in ("body", "hull", "anchorage"):
        return False, "There is nothing there to look at."
    from . import engage
    km = engage.range_km(game, conn, contact)
    if km > table.RANGE_KM:
        return False, (f"{km:,.0f} km off — a craft works inside "
                       f"{table.RANGE_KM:,.0f} km of the hull it flew from.")
    return True, ""


def scout(game, contact) -> dict:
    """An hour's looking, close up: survey data for the bench, and a body
    properly on the chart. What an array on a seat is for."""
    ok, why = can_scout(game, contact)
    if not ok:
        return {"ok": False, "why": why}
    craft = flying(game)
    kind = kind_of(craft)
    got = SCOUT_DATA * max(0.5, kind.sensor / 2.0)
    from . import inquiry
    inquiry.add(game.research, "survey", got)
    craft.fuel = max(0.0, craft.fuel - STRIKE_T * 0.5)
    conn = sortie(game)
    if conn is not None:
        conn.elapsed += SCOUT_HOURS * 3600.0
    index = getattr(contact, "body_index", None)
    seen = ""
    if getattr(contact, "kind", "") == "body" and index is not None:
        body = game.system.bodies[index]
        body.scanned = True
        seen = f" {body.name} is on the chart properly now."
    text = (f"{craft.name} spends an hour over {contact.name}: "
            f"{got:.0f} of survey data.{seen}")
    game.add_log(text, "good")
    if conn is not None:
        conn.log.append(text)
    return {"ok": True, "data": round(got, 1), "text": text}
