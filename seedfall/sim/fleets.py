"""What a power can put in space, from what it has left after the ports.

Measured before this file existed. The powers have real purses — `sim/exchequer`
gives each of them income, outlay and a margin, and they found and promote ports
with it. And the sector has hulls: eighty-four of them, twenty-one on patrol,
each flying somebody's flag. **The two had nothing to do with each other.**

    traffic._busyness  = 1 + port.level (+1 capital, +2 lit anchor, −1 bloom)

A power's presence in the sector was a reading of its *infrastructure* and
never of its *treasury*, so a power could be bankrupt and still have exactly as
many hulls on station as one that was thriving. Nothing anywhere in the game
answered "how much can this power actually field", and `sim/control.means` —
what a structure may do about a hull it does not want — read port levels for
the same reason: there was nothing better to read.

**A fleet is what the margin sustains.** Nothing is stored, which is the
discipline `sim/anchorage` uses for a quay's whole existence and
`sim/control.holders` for who is in a berth: the answer is recomputed from the
economy every time it is asked, so it cannot drift and a save cannot carry a
stale one. It also makes the trade real and visible — a power that founds
another port is paying for it with hulls, because founding raises outlay and
outlay is subtracted before this is worked out.

Measured across ten sectors at three dates, 120 power-days:

    margin      p10 98   p50 274   p90 336   (range −139 … 454)
    at 45/day   median 6 hulls, most 10, and 10 of 120 power-days with none

That last figure is the point of the whole thing. A power *can* overextend
itself into having no fleet at all — Charter does it in the "oob" sector by day
720, reaching seven holdings on a margin of −53 — and when it does, its
capitals still shoot from their own batteries but nothing comes out after you.
"""

from __future__ import annotations

from . import exchequer as exchequer_sim

#: What one hull costs a power to keep in space, a day.
#:
#: Chosen against the margins the economy actually produces rather than picked
#: round: at 30 a day the median power fields nine and almost nobody is ever
#: without a fleet, which makes the ports-against-hulls trade invisible; at 60
#: the median is four and the sector feels empty next to the twenty-one patrol
#: hulls already in it. 45 puts the median at six and leaves overextension
#: biting in about one power-day in twelve.
UPKEEP = 45.0

#: What a holding is worth as a place to keep hulls: its port level, so a
#: developed system holds more than an outpost.
#:
#: **There was a `CAPITAL_WEIGHT` beside this and it has been deleted.** It
#: multiplied a capital's share threefold — and measured across four sectors,
#: *every capital in the game is level 3 and no ordinary port ever is*, so the
#: two constants were never distinguishable and the second was a knob doing
#: what the first already did. A check could not pin it either: dropping it to
#: 1.0 changed no verdict, because the level had been answering all along.
#: One door. A capital still keeps three times an outpost's hulls; it does so
#: because it is a bigger port, which is the reason that was always true.
LEVEL_WEIGHT = 1.0

#: What a system a power is *trying to take* is worth as a place to keep hulls,
#: against one it already holds.
#:
#: Below 1.0 on purpose: a power defends its own ground harder than it presses
#: somebody else's, so the attacker is usually the smaller squadron and taking
#: a system off its holder is an achievement rather than a formality.
#:
#: Measured over eight sectors flown a decade each, with wars live. Systems
#: carrying two flags at once, and how often the holder is out-shipped on its
#: own holding:
#:
#:     0.0   contested  0    out-shipped  0    holdings left bare 1
#:     0.3   contested 65    out-shipped  6    holdings left bare 1
#:     0.6   contested 77    out-shipped  9    holdings left bare 1
#:     1.0   contested 77    out-shipped 34    holdings left bare 4
#:     1.6   contested 76    out-shipped 48    holdings left bare 7
#:
#: At 0 there is no such thing as a contested system, which is where this
#: started. At 1.0 the attacker weighs as much as the defender and the holder
#: is out-shipped in 44% of contests, which reads as a sector with no
#: home ground at all. 0.6 puts contest almost everywhere a war reaches while
#: leaving out-shipping to about one contested system in eight.
FRONT_WEIGHT = 0.6


def sustains(game, power: str) -> float:
    """The daily margin this power has left once its ports are paid for.

    Straight through to `exchequer.margin`, which is income minus the upkeep
    of everything it holds. Named here because the fleet is a *reading* of it
    and a screen should be able to say so.
    """
    return float(exchequer_sim.margin(game, power))


def strength(game, power: str) -> int:
    """Hulls this power can keep in space at all, sector-wide."""
    return max(0, int(sustains(game, power) // UPKEEP))


def _weights(game, power: str) -> list:
    """(system, share) for everywhere this power keeps hulls.

    **Two kinds of place, and until wars existed there was only one.** Hulls
    sat on holdings, and holdings are the systems where a power has a port —
    so no two powers' squadrons could ever be in the same system. Measured
    after a decade with nine live wars, powers with hulls in one system came
    out `{1: 195, 0: 141}`: never two, by construction. That made
    `keeper_of`'s whole reason for existing — "a power can be out-shipped over
    its own holding" — describe something that could not happen, and it left
    a fleet action with nowhere to occur.

    A power at war also keeps hulls **off** what it is trying to take, which
    is what `sim/war.spoils` names. That is the only way two flags end up in
    one volume.
    """
    out = []
    for system in exchequer_sim.holdings(game, power):
        port = system.port
        out.append((system, float(
            LEVEL_WEIGHT * max(1, int(getattr(port, "level", 1))))))
    from . import war as war_sim
    for system in war_sim.spoils(game, power):
        out.append((system, float(
            FRONT_WEIGHT * max(1, int(getattr(system.port, "level", 1))))))
    return out


def stations(game, power: str) -> dict:
    """{system id: hulls} for this power, summing to `strength`.

    Largest remainder, and deliberately not a draw: a fleet that reshuffled
    every time the question was asked would put a squadron somewhere different
    on each of the three screens that ask, and `sim/traffic` learned that the
    hard way — it is seeded on the system and the slot precisely so the hull
    you hailed yesterday is the same hull today.
    """
    total = strength(game, power)
    spread = _weights(game, power)
    if total <= 0 or not spread:
        return {}
    whole = sum(weight for _system, weight in spread)
    exact = [(system, total * weight / whole) for system, weight in spread]
    out = {system.id: int(share) for system, share in exact}
    left = total - sum(out.values())
    # The remainder goes to the biggest shares first, ties broken by system id
    # so the answer is the same every time it is worked out.
    for system, share in sorted(exact, key=lambda pair: (-(pair[1] % 1.0),
                                                         pair[0].id)):
        if left <= 0:
            break
        out[system.id] += 1
        left -= 1
    return out


def guard_at(game, system, power: str) -> int:
    """How many of this power's hulls are on station in this system."""
    return int(stations(game, power).get(getattr(system, "id", system), 0))


def squadron_at(game, system) -> dict:
    """{power: hulls} for everybody with something in this system."""
    from . import diplomacy as diplomacy_sim
    out = {}
    for power in diplomacy_sim.POWERS:
        here = guard_at(game, system, power)
        if here:
            out[power] = here
    return out


def keeper_of(game, system) -> str:
    """Whose fleet holds this system, or "" if nobody's does.

    The strongest squadron present, which is not always whose port it is — a
    power can be out-shipped over its own holding, and that is worth being
    able to see.

    **That sentence was false for as long as it stood.** Hulls only ever sat on
    holdings, so `squadron_at` never returned two powers and this was a `max()`
    over a dict that could not have two entries: measured across six sectors,
    `keeper_of` agreed with `system.port.faction` in 99 of 99 non-empty cases
    and differed in 0. It is true now because `_weights` puts hulls on what a
    power is trying to take as well as on what it holds — measured over eight
    sectors flown a decade each, 77 systems carry two flags and the holder is
    out-shipped on 9 of them.
    """
    here = squadron_at(game, system)
    if not here:
        return ""
    return max(sorted(here), key=lambda power: here[power])


def note(game, system) -> str:
    """One line on what is on station here, for a screen to print."""
    here = squadron_at(game, system)
    if not here:
        return "Nothing on station: no power keeps hulls here."
    from ..data.factions import FACTIONS_BY_ID
    parts = []
    for power in sorted(here, key=lambda p: (-here[p], p)):
        named = FACTIONS_BY_ID.get(power)
        parts.append(f"{named.short if named else power} {here[power]}")
    return "On station: " + ", ".join(parts)
