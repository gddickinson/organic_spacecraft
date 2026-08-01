"""The fleet action at a contested system, and the one hull you bring to it.

**Framing, not gunfire.** There are already twelve combat modules and 2,470
lines of them; `sim/combat` is the only thing that constructs a `Battle` and
`sim/consorts` already handles hulls fighting alongside the flag. This module
resolves nothing. It answers who is contesting a system, how the weight of
metal falls, and what that does to the annexation being fought over — and it
answers all of it derived, so nothing is stored and a save cannot carry a stale
order of battle.

**The scale is measured, and it is not the one the task asked for.** Task #114
was titled "a battle of two hundred hulls". The economy sustains a mean of 23
hulls in the *entire sector* (measured over six: 25, 26, 23, 24, 20, 22),
because `fleets.UPKEEP` is 45/day against the margins `sim/exchequer` produces.
And a contested system, measured over eight sectors flown a decade each:

    contested systems per sector   10, 11, 13, 0, 8, 0, 0, 13   (mean 6.9)
    hulls in one                   min 2, median 3, max 4

Three of those sectors are at peace throughout and have none at all. So a fleet
action here is a handful of hulls over a quay, not an armada — which is why one
hull can matter, and why this file frames a skirmish honestly instead of
pretending to a line of battle the economy cannot pay for.
"""

from __future__ import annotations

from . import diplomacy as dip
from . import fleets as fleets_sim
from . import war as war_sim

#: What the balance of hulls over a system is worth to the annexation of it.
#:
#: `ventures.odds` weighed the sponsor's levies, its standing with everybody
#: else and whether the player had leant on it, and **not one term asked who
#: had hulls over the place being taken**. A power could be out-shipped three
#: to one above the target and annex it at exactly the same odds.
#:
#: 0.25 against a `BASE_ODDS` of about a half, so total command of the volume
#: is worth about as much as the player's own intervention (`SWAY`) and no
#: more: the fleet decides the odds, it does not replace the politics.
BALANCE_SWAY = 0.25


def holder(game, system) -> str | None:
    """Whose quay is being fought over."""
    port = getattr(system, "port", None)
    return port.faction if port is not None else None


def sides(game, system) -> tuple[str, str] | None:
    """(holder, challenger) at this system, or None if nothing is contested.

    The challenger is the strongest squadron present that the holder is at war
    with — `fleets.squadron_at` can now return more than one power because
    `fleets._weights` stations hulls on what a power is trying to take.
    """
    keeps = holder(game, system)
    if keeps is None:
        return None
    here = fleets_sim.squadron_at(game, system)
    foes = [p for p in here
            if p != keeps and war_sim.at_war(game, keeps, p)]
    if not foes:
        return None
    # Ties broken by name so the answer is the same every time it is asked.
    return keeps, max(sorted(foes), key=lambda p: here[p])


def strength_at(game, system) -> dict:
    """{power: hulls} over this system, the player's own hull included.

    A captain who is *here* and has *taken a side* is one more hull in the
    line. That is the whole of the player's part in a fleet action: not
    command, presence.
    """
    here = dict(fleets_sim.squadron_at(game, system))
    ours = committed(game, system)
    if ours:
        here[ours] = here.get(ours, 0) + 1
    return here


def committed(game, system) -> str | None:
    """Which side the player's hull is on here, if any.

    Being in the system is not enough and neither is having an opinion — it is
    both. The opinion is `Venture.stance`, which the player already sets from
    the ventures panel and which `ventures.odds` already reads, so taking a
    side in a fleet action needs no new state and no new screen.
    """
    from . import ventures as ventures_sim
    if getattr(game, "location_id", None) != getattr(system, "id", None):
        return None
    keeps = holder(game, system)
    for venture in ventures_sim.live(game):
        if venture.kind != "annex" or venture.place != system.id:
            continue
        if venture.stance == "backed":
            return venture.power
        if venture.stance == "opposed":
            return keeps
    return None


def balance(game, system, power: str) -> float:
    """How the weight of metal over this system falls for `power`.

    -1 when the other side has it all, +1 when this one does, 0 when it is
    even. Everybody who is not `power` counts against it, because a system
    with three flags over it is not a place `power` is having its own way.
    """
    here = strength_at(game, system)
    mine = float(here.get(power, 0))
    theirs = float(sum(n for p, n in here.items() if p != power))
    if mine + theirs <= 0:
        return 0.0
    return (mine - theirs) / (mine + theirs)


def actions(game) -> list:
    """Every contested system in the sector, heaviest first."""
    out = []
    for system in game.galaxy.systems:
        pair = sides(game, system)
        if pair is None:
            continue
        out.append((system, pair, strength_at(game, system)))
    return sorted(out, key=lambda row: (-sum(row[2].values()), row[0].id))


def note(game, system) -> str:
    """One line on the action here, for a screen to print."""
    from ..data.factions import FACTIONS_BY_ID

    def short(fid):
        named = FACTIONS_BY_ID.get(fid)
        return named.short if named else fid

    pair = sides(game, system)
    if pair is None:
        return fleets_sim.note(game, system)
    keeps, other = pair
    here = strength_at(game, system)
    ours = committed(game, system)
    line = (f"Contested: {short(keeps)} {here.get(keeps, 0)} against "
            f"{short(other)} {here.get(other, 0)}.")
    if ours:
        line += f" You are counted with {short(ours)}."
    return line
