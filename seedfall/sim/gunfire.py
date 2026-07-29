"""What happened in an exchange, in a shape something can draw.

`combat._fire` resolves a shot and writes a sentence. That is enough for a log
and not nearly enough for a picture: by the time the turn is over, all that
survives of "the Fusion Lance opened the enemy's flank" is the sentence. There
is no record of what fired, from where, at what, or whether it connected.

So an engagement now keeps its shots. One `Shot` per attempt — including the
ones that never left the tube, because "the lance would not train that far" is
exactly the thing a captain needs to *see* rather than read, and it is the
whole argument for having turned the ship.

Cleared at the top of every turn, never saved. A battle is transient and so is
this.
"""

from __future__ import annotations

from dataclasses import dataclass

#: How a weapon reads when it goes off. Derived from what it is rather than
#: from a second table that could drift: a thing with ammunition throws
#: something, a thing that seeks flies after you, and a thing that runs hot
#: with no magazine is pouring energy down a line.
BEAM = "beam"
ROUND = "round"
SEEKING = "seeking"
FLAK = "flak"

#: What became of it.
HIT = "hit"
MISS = "miss"
SWATTED = "swatted"          # point defence caught it
DRY = "dry"                  # no ammunition aboard
NO_BEAR = "no-bear"          # out of range band
NO_ARC = "no-arc"            # outside the mount's arc


@dataclass(frozen=True)
class Shot:
    """One attempt, and what came of it."""

    frm: str                 # who fired, by name
    to: str                  # who at
    weapon: str              # what with
    look: str                # beam | round | seeking | flak
    outcome: str
    damage: float = 0.0
    #: Where the two hulls were when it happened, in tactical coordinates,
    #: so a picture drawn afterwards is drawn where it actually occurred.
    frm_at: tuple = (0.0, 0.0)
    to_at: tuple = (0.0, 0.0)
    #: True when the shot was the player's.
    mine: bool = False

    @property
    def landed(self) -> bool:
        return self.outcome == HIT

    @property
    def flew(self) -> bool:
        """Did anything actually leave the ship?"""
        return self.outcome in (HIT, MISS, SWATTED)


def look_of(weapon) -> str:
    """How this weapon reads when it fires.

    Read off the weapon itself. A second table mapping id to appearance is a
    second table to keep in step, and this file has watched that go wrong
    elsewhere in the project more than once.
    """
    traits = getattr(weapon, "traits", ()) or ()
    if "flak" in traits:
        return FLAK
    if "seeking" in traits:
        return SEEKING
    if getattr(weapon, "ammo", None):
        return ROUND
    return BEAM


def record(battle, frm, to, weapon_name: str, weapon, outcome: str,
           damage: float = 0.0) -> Shot:
    """Note a shot on the battle, and hand it back."""
    shot = Shot(frm=frm.ship.name, to=to.ship.name, weapon=weapon_name,
                look=look_of(weapon), outcome=outcome, damage=damage,
                frm_at=(frm.body.x, frm.body.y),
                to_at=(to.body.x, to.body.y),
                mine=frm is battle.player)
    battle.shots.append(shot)
    return shot


def clear(battle) -> None:
    """A new turn. What was fired last turn has stopped being news."""
    battle.shots = []


def summary(battle) -> dict:
    """What the exchange came to, for a panel or a check."""
    shots = list(getattr(battle, "shots", ()))
    return {
        "fired": len([s for s in shots if s.flew]),
        "hits": len([s for s in shots if s.landed]),
        "damage": round(sum(s.damage for s in shots), 1),
        "refused": len([s for s in shots
                        if s.outcome in (DRY, NO_BEAR, NO_ARC)]),
        "mine": len([s for s in shots if s.mine]),
        "theirs": len([s for s in shots if not s.mine]),
    }
