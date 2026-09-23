"""Pitching a camp on a world, and what it is worth once it is up.

The expedition's only building was the lander, and the only place its supply
clock could be refilled was orbit. A camp is the second building: carried
down in the lander's hold against the supplies and the vehicle, pitched on a
tile, struck again, and — the whole point — **a place days of supply can be
left and picked back up**.

Everything here is small and readable on purpose:

- `pitch` puts the camp on the party's own tile and moves days into it;
- `draw` takes days back out when they are standing in it;
- `at_camp` is what `sim/expedition.shelter` and `rest` ask before they
  charge a day of supply or hand out a day's repairs.

A party that lifts off leaves whatever is still in the camp, the same way
`expedition.STRANDED_SHARE` leaves what nobody is carrying: the camp comes
back up with them (it is struck and stowed), and the days inside it do not.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data import camps as table
from ..data.camps import CAMPS_BY_ID, PITCH_DAYS


@register
@dataclass
class Camp:
    """One camp, in the hold or pitched on a world."""

    id: int
    class_id: str
    name: str
    #: stowed | down | lost. Where it *stands* and what is in it are the
    #: expedition's (`sim/expedition.Expedition.camp*`), because the game on
    #: the ground is played out of one object.
    state: str = "stowed"
    log: list = field(default_factory=list)


def kind_of(held) -> table.CampClass:
    return CAMPS_BY_ID[held.class_id]


def aboard(game) -> list:
    """Every camp this hull owns."""
    return [c for c in getattr(game, "camps", []) or [] if c.state != "lost"]


def stowed(game) -> list:
    return [c for c in aboard(game) if c.state == "stowed"]


def down(game):
    """The camp that went down with the party, or None."""
    return next((c for c in aboard(game) if c.state == "down"), None)


def give(game, class_id: str = "bivouac", name: str = "") -> Camp:
    """Put a camp in the hold. The one door for acquiring one."""
    kind = CAMPS_BY_ID[class_id]
    held = Camp(id=len(getattr(game, "camps", []) or []) + 1,
                class_id=class_id,
                name=name or _name_for(game, kind))
    game.camps = list(getattr(game, "camps", []) or []) + [held]
    return held


def _name_for(game, kind) -> str:
    hull = getattr(getattr(game, "ship", None), "name", "") or "the hull"
    return f"{hull}'s {kind.name.title()}"


def best_for(game, lander, room_t: float):
    """The roomiest camp that will fit in what is left of the hold."""
    from . import craft as craft_sim
    if lander is None:
        return None
    able = [c for c in stowed(game)
            if kind_of(c).mass_t <= room_t
            and kind_of(c).sleeps >= 1
            and craft_sim.kind_of(lander).hold_t >= kind_of(c).mass_t]
    return max(able, key=lambda c: kind_of(c).holds, default=None)


# ── on the ground ──────────────────────────────────────────────────────────

def kind_for(exp):
    """The class of camp this party has with them, or None."""
    return CAMPS_BY_ID.get(getattr(exp, "camp", "") or "")


def is_up(exp) -> bool:
    """Is it pitched anywhere?"""
    return kind_for(exp) is not None and getattr(exp, "camp_x", -1) >= 0


def at_camp(exp) -> bool:
    """Is the party standing in its own camp?"""
    return (is_up(exp) and exp.camp_x == exp.x and exp.camp_y == exp.y)


def can_pitch(exp) -> tuple:
    """May they put one up here? `(ok, why)`."""
    if exp is None or exp.over:
        return False, "Nobody is on the ground."
    if kind_for(exp) is None:
        return False, "No camp came down with them."
    if is_up(exp):
        return False, "The camp is already up. Strike it to move it."
    if exp.supply <= PITCH_DAYS:
        return False, "Not enough supply left to spend a day pitching it."
    return True, ""


def pitch(exp, days: int = 0) -> dict:
    """Put the camp up here, and leave `days` of supply in it."""
    ok, why = can_pitch(exp)
    if not ok:
        return {"ok": False, "why": why}
    kind = kind_for(exp)
    exp.camp_x, exp.camp_y = exp.x, exp.y
    exp.supply = max(0, exp.supply - PITCH_DAYS)
    exp.days += PITCH_DAYS
    left = max(0, min(int(days), kind.holds, exp.supply))
    exp.camp_supply = left
    exp.supply -= left
    from .expedition import say
    say(exp, f"{kind.name.title()} up on this tile"
             + (f", with {left} day(s) of supply in it." if left else "."),
        "good")
    return {"ok": True, "left": left}


def can_strike(exp) -> tuple:
    if not is_up(exp):
        return False, "Nothing is pitched."
    if exp.over:
        return False, "Nobody is on the ground."
    if not at_camp(exp):
        return False, (f"The {kind_for(exp).name.lower()} is at "
                       f"{exp.camp_x},{exp.camp_y}, not here.")
    return True, ""


def strike(exp) -> dict:
    """Take it down and carry it on. Whatever is in it comes with them."""
    ok, why = can_strike(exp)
    if not ok:
        return {"ok": False, "why": why}
    kind = kind_for(exp)
    took, exp.camp_supply = exp.camp_supply, 0
    exp.camp_x = exp.camp_y = -1
    exp.supply += took
    exp.days += PITCH_DAYS
    from .expedition import say
    say(exp, f"{kind.name.title()} struck"
             + (f"; {took} day(s) of supply back on their backs."
                if took else "."), "")
    return {"ok": True, "took": took}


def draw(exp, days: int = 0) -> dict:
    """Take supply back out of the camp they are standing in."""
    if not at_camp(exp):
        return {"ok": False, "why": "They are not in the camp."}
    took = max(0, min(int(days) or exp.camp_supply, exp.camp_supply))
    if not took:
        return {"ok": False, "why": "The camp is empty."}
    exp.camp_supply -= took
    exp.supply += took
    from .expedition import say
    say(exp, f"{took} day(s) of supply out of the camp.", "good")
    return {"ok": True, "took": took}


def rest_worth(exp) -> float:
    """What a day's rest is worth here: one in the open, more in a camp."""
    return kind_for(exp).rest if at_camp(exp) else 1.0


def shelters(exp) -> bool:
    """Does sitting out the weather cost supply? Not under a roof."""
    return at_camp(exp)


def take_down(game, exp, camp) -> dict:
    """It rides down with the party, stowed until somebody pitches it."""
    camp.state = "down"
    exp.camp = camp.class_id
    exp.camp_x = exp.camp_y = -1
    exp.camp_supply = 0
    return {"ok": True, "camp": camp}


def bring_up(game, exp=None) -> dict:
    """It comes up with the lander; what is still inside it does not."""
    camp = down(game)
    if camp is None:
        return {"ok": False, "why": "Nothing went down."}
    camp.state = "stowed"
    left = int(getattr(exp, "camp_supply", 0) or 0) if exp is not None else 0
    if left:
        game.add_log(f"{left} day(s) of supply left in the camp on the way "
                     "up.", "warn")
    return {"ok": True, "left": left}


def says(exp) -> str:
    """One line for a screen."""
    kind = kind_for(exp)
    if kind is None:
        return "No camp came down with them."
    if not is_up(exp):
        return (f"{kind.name.title()} in the lander — a day to pitch it, and "
                f"it holds {kind.holds} days of supply.")
    where = "here" if at_camp(exp) else f"at {exp.camp_x},{exp.camp_y}"
    return (f"{kind.name.title()} {where} with {exp.camp_supply} day(s) in "
            f"it; rest is worth {kind.rest:g}× inside.")
