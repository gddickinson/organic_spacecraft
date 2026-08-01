"""When two powers are at war, and what that lets them take from each other.

**Derived, never stored.** A war is a reading of the relation matrix, the same
way `sim/anchorage` reads a quay's existence, `sim/fleets` reads what a purse
sustains and `sim/piracy` reads how policed a volume is. Nothing here has to be
saved, nothing can drift out of step with the diplomacy it describes, and a
chronicle loaded from disk agrees with the one that wrote it.

What this exists to make possible, measured before it was written. Over 1,800
days across three sectors, with 15 to 18 ventures running to resolution:

    system.faction changed hands            0, 2, 2 systems
    of those, taken from another power      0, 0, 0
    port.faction changed hands              0, 0, 0

Annexation could only ever take *unclaimed* ground — `_claimable` asked for
`s.faction is None` — so the sector's map filled in and never changed hands. A
quay that cleared you last month could not come to fly another flag, because no
mechanism moved a berth between powers at all.

Note that the register and the berth are deliberately two facts and stay two
here: `system.faction` is who has the volume on their books and `port.faction`
is who runs the quay. `sim/exchequer.holdings` reads the second and says why —
"an annexed system changes hands while whoever built the berth still owns the
berth". At generation they disagree on 2 of 63 ported systems already. Taking a
system in war moves both, because that is what taking it means; annexing empty
ground still moves only the register.
"""

from __future__ import annotations

from . import diplomacy as dip

#: The relation at or below which two powers are fighting.
#:
#: Chosen against what the matrix actually reaches rather than picked round.
#: Measured over eight sectors, the worst relation any pair reached in 1,800
#: days: -57, -69, -67, -81, -60, -95, -63, -78 — median -68.
#:
#:     threshold -40   war in 8 of 8 sectors
#:     threshold -50   war in 8 of 8
#:     threshold -60   war in 6 of 8
#:     threshold -70   war in 3 of 8
#:     threshold -80   war in 2 of 8
#:
#: At -50 or above every sector is always at war somewhere, which makes the
#: state carry no information; at -70 it is a rarity most chronicles never see.
#: -60 makes a war something three sectors in four live through, and it starts
#: partway in rather than at generation — one measured sector sat at -45 for
#: seven steps of 150 days before dropping to -57.
WAR_AT = -60.0


def at_war(game, a: str, b: str) -> bool:
    """Are these two powers fighting? **The one door.**"""
    if a == b:
        return False
    return dip.relation(game, a, b) <= WAR_AT


def belligerents(game, power: str) -> list[str]:
    """Everyone this power is at war with, worst relation first."""
    other = [p for p in dip.POWERS if p != power and at_war(game, power, p)]
    return sorted(other, key=lambda p: dip.relation(game, power, p))


def wars(game) -> list[tuple[str, str]]:
    """Every war in the sector as an ordered pair, worst first."""
    seen = set()
    for a in dip.POWERS:
        for b in belligerents(game, a):
            seen.add(tuple(sorted((a, b))))
    return sorted(seen, key=lambda pair: dip.relation(game, *pair))


def spoils(game, power: str) -> list:
    """Systems this power could take, because it is at war with the holder.

    Whoever runs the quay is who you have to beat for it, so this reads
    `port.faction` — the same field `exchequer.holdings` counts a power's
    income from, which is what makes the taking worth anything.
    """
    foes = set(belligerents(game, power))
    if not foes:
        return []
    return [s for s in game.galaxy.systems
            if getattr(s, "port", None) is not None
            and s.port.faction in foes
            and not s.port.independent
            and not s.port.player_built]


def note(game, power: str) -> str:
    """One line on who this power is fighting, for a screen to print."""
    from ..data.factions import FACTIONS_BY_ID
    foes = belligerents(game, power)
    if not foes:
        return "At war with nobody."
    named = [(FACTIONS_BY_ID[f].short if f in FACTIONS_BY_ID else f)
             for f in foes]
    return "At war with " + ", ".join(named) + "."
