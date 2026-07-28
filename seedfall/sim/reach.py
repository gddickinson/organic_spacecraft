"""What you can actually get to, as opposed to what is one jump away.

The chart drew a dashed ring at the jump range and greyed the button to "Out
of range". That answers "can I jump there in one hop", which is not the
question a captain is asking. The question is "can I get there at all" — by
hopping, star to star, refuelling as you go — and often the answer is no.

Flooding from the start at starting jump range reaches anywhere from 2 to all
42 systems depending on the seed; the median is 13 and a quarter of sectors
open with fewer than eight. Those walls were invisible. A captain handed a
two-system pocket saw forty stars beyond the ring, no different in the drawing
from the one next door, and nothing anywhere said that forty of them were
unreachable until the drive changed.

`MAX_LANE` in `world/galaxy.py` does not prevent this and was never meant to:
it guarantees no *star* sits alone, which does not stop a *cluster* sitting
alone.
"""

from __future__ import annotations

from ..data.chassis import CHASSIS_BY_ID
from ..data.parts import PARTS, PARTS_BY_ID
from ..world.galaxy import distance
from .ship import stats as ship_stats
from .shipyard import validate


def component(game, jump: float | None = None, start: int | None = None) -> set:
    """Every system reachable from here by hopping, at this jump range.

    Reachability is transitive and the chart was only ever drawing one step of
    it. Fuel is deliberately not modelled: reaction mass can be cut out of ice
    anywhere, so it paces a voyage rather than bounding it, and a wall that
    moved with the state of the tank would be a worse lie than no wall at all.
    """
    if jump is None:
        jump = game.ship_stats.jump
    here = game.location_id if start is None else start
    systems = game.galaxy.systems
    seen = {here}
    edge = [systems[here]]
    while edge:
        following = []
        for system in edge:
            for other in systems:
                if other.id not in seen and distance(system, other) <= jump:
                    seen.add(other.id)
                    following.append(other)
        edge = following
    return seen


def walled(game, jump: float | None = None) -> set:
    """The systems on the far side of the wall. Empty when there is none."""
    within = component(game, jump)
    return {s.id for s in game.galaxy.systems} - within


def horizon(game) -> dict:
    """How much of the sector this drive can see, in a form a screen can say."""
    within = component(game)
    total = len(game.galaxy.systems)
    return {"within": len(within), "total": total,
            "beyond": total - len(within),
            "jump": game.ship_stats.jump,
            "ids": within,
            "whole": len(within) >= total}


def _with_drive(game, part_id: str):
    """This hull's jump range with that drive in place of the one fitted."""
    chassis = CHASSIS_BY_ID[game.ship.chassis]
    fitted = [pid for pid in game.ship.fitted
              if PARTS_BY_ID[pid].slot != "drive"] + [part_id]
    if not validate(chassis, fitted)[0]:
        return None
    from .ship import Ship
    mock = Ship(uid=0, name="", chassis=chassis.id, fitted=fitted)
    return ship_stats(mock, getattr(game, "bonuses", None)).jump


def opens(game) -> list[dict]:
    """Every drive that would fit this hull, and what it would open up.

    Only drives the *chassis will accept*: a grown hull refuses the fabricated
    ones, so for a NAVIS the whole ladder is reaction_organ, sail_film and
    foldrunner — 8.9, 9.0 and 13.6 light-years. Listing the drives it cannot
    graft would make the ladder look gentle when it is in fact one very
    expensive step.
    """
    now = horizon(game)
    out = []
    for part in PARTS:
        if part.slot != "drive" or part.id in game.ship.fitted:
            continue
        jump = _with_drive(game, part.id)
        if jump is None or jump <= now["jump"] + 0.01:
            continue
        out.append({
            "part": part,
            "jump": jump,
            "within": len(component(game, jump)),
            "gain": len(component(game, jump)) - now["within"],
            "known": not part.tech or part.tech in game.research.unlocked,
        })
    out.sort(key=lambda row: row["jump"])
    return out


def next_step(game) -> dict | None:
    """The cheapest drive that would actually open ground. None if none does."""
    return next((row for row in opens(game) if row["gain"] > 0), None)


def note(game) -> str:
    """One line for the chart, stating the wall and what would move it."""
    now = horizon(game)
    if now["whole"]:
        return (f"All {now['total']} systems are reachable at "
                f"{now['jump']:.1f} ly.")
    step = next_step(game)
    line = (f"{now['within']} of {now['total']} systems are reachable at "
            f"{now['jump']:.1f} ly — {now['beyond']} lie beyond a gap no "
            "amount of hopping closes.")
    if step is None:
        return line + " No drive this hull will take reaches further."
    return (line + f" A {step['part'].name} would reach {step['jump']:.1f} ly "
            f"and open {step['gain']} more"
            + ("." if step["known"] else ", once researched."))
