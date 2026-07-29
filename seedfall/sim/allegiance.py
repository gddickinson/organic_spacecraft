"""What it costs to be seen working for somebody.

The sector has six powers and a relations matrix that starts hostile in most
pairs, and none of it touched the work you actually did. You could run the
Charter's deliveries, collect a Concordat bounty and take Freehold prospecting
money in the same week while those three were at each other's throats, and
every one of them thought better of you for it. Standing was an accumulation
game with no tension in it anywhere.

Serving a power now costs you with its enemies, in proportion to how bad the
rift actually is. Two powers merely cool about each other barely notice; two
at war mind a great deal. The way out is not to do less work — it is to broker
the peace, which is what the diplomacy layer was always for and what nothing in
the daily game ever asked of it.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from . import diplomacy as dip

#: Above this the two powers are merely cool and nobody minds.
INDIFFERENT = -15.0
#: At or below this they mind as much as they are ever going to.
IMPLACABLE = -70.0
#: A share of what you gained with the issuer.
BITE = 0.75


def severity(game, power: str, other: str) -> float:
    """How much `other` minds you serving `power`, 0..1.

    Ramped rather than a threshold: a flat penalty for anyone under some line
    makes brokering a rift from dreadful to merely bad worth nothing at all,
    which is the opposite of the point.
    """
    if power == other:
        return 0.0
    value = dip.relation(game, power, other)
    if value >= INDIFFERENT:
        return 0.0
    span = INDIFFERENT - IMPLACABLE
    return min(1.0, (INDIFFERENT - value) / span)


def offended_by(game, power: str) -> list[tuple[str, float]]:
    """Powers that mind you working for this one, worst first."""
    out = [(other, severity(game, power, other))
           for other in FACTIONS_BY_ID
           if other != power and not FACTIONS_BY_ID[other].hidden
           and not FACTIONS_BY_ID[other].hostile]
    return sorted([(o, s) for o, s in out if s > 0], key=lambda t: -t[1])


def price(game, power: str, weight: float) -> list[tuple[str, float]]:
    """What serving `power` for `weight` standing would cost, unapplied.

    Strictly a share of what you gained, as `BITE` says. There used to be a
    flat floor of one point under this — harmless while every overture was
    worth six to fourteen standing, and ruinous the moment `courtship` made a
    gift to an old friend worth less than that. At 85 standing, relief bought
    +0.88 with the Charter and cost a floored 1.0 with each of two offended
    rivals: forty tonnes of biomass to end up 1.12 worse off overall. The
    button was a trap, and the floor was the whole reason.
    """
    if weight <= 0:
        return []
    out = [(other, round(weight * sev * BITE, 1))
           for other, sev in offended_by(game, power)]
    return [(other, cost) for other, cost in out if cost > 0]


def charge(game, power: str, weight: float) -> list[tuple[str, float]]:
    """Apply it. Returns what actually moved, for the log and the screen."""
    moved = price(game, power, weight)
    for other, cost in moved:
        game.adjust_rep(other, -cost)
    return moved


def note(game, power: str, weight: float) -> tuple[str, str]:
    """One line for the board, before you commit to anything."""
    moved = price(game, power, weight)
    if not moved:
        return "nobody else will mind", "dim"
    worst = ", ".join(f"{FACTIONS_BY_ID[o].short} −{c:g}" for o, c in moved[:3])
    tint = "warn" if moved[0][1] >= 3 else "osteo"
    return f"will cost you: {worst}", tint


def phrase(moved: list[tuple[str, float]]) -> str:
    """How the log puts it."""
    if not moved:
        return ""
    return "; ".join(f"{FACTIONS_BY_ID[o].short} {-c:+g}" for o, c in moved)
