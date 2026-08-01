"""Where the law is not, and therefore where the raiders are.

Raiders existed before this file: `sim/traffic` gives one in six systems an
unmarked hull, and `sim/encounters` makes it the thing that jumps you. What
did not exist was any reason for them to be *where they are*.

    traffic:    hostile_ok = system.port is None or system.bloom > 0.15
    encounters: danger     = bloom * 0.9 + (0.04 if port else 0.14) + 0.09·dark

**One fact, asked twice, and both times of the same field.** Measured across
252 systems in six sectors, raiders appear in 25 of 127 portless systems and 1
of 125 with a port — and they already avoid a squadron, 17% at nothing on
station against 0–2% anywhere else. But that correlation is an accident: both
questions read `port`, and a fleet had nothing to do with either.

So the law is a real quantity here, and it is made of the things that actually
police a volume:

- **A squadron on station.** The strongest signal by far, and the one the game
  did not have until `sim/fleets` — somebody's hulls being *here*, which is a
  reading of what that power's margin sustains. A power that collapses stops
  policing, and its space goes bad.
- **A port**, because a dock is a place with people who notice.
- **A claim**, because a power that says a system is theirs is a power with an
  opinion about what happens in it.
- **Distance from the nearest capital**, 0 to 21 across a sector: the far edge
  is far from everybody's reach.
- **The Bloom**, which empties a system of everyone who would have looked.

The number this produces is used by both doors that used to guess separately,
so a system cannot be lawful enough to keep raiders out and dangerous enough to
jump you at the same time.
"""

from __future__ import annotations

import math

#: Where a system sits before anything is known about it.
#:
#: Everything below subtracts from this, so the question the model asks is
#: "who is looking after this place", not "how bad is it".
#:
#: **Chosen for the spread, not the level.** At 0.72 the scale piled up
#: against its own ceiling — p60 0.80 against p90 0.91, thirty per cent of the
#: sector inside a tenth of the range — so the number carried almost no
#: information and the raider threshold had to sit at 0.92 to mean anything.
#: At 0.45 it uses its range: p25 0.03, p50 0.39, p75 0.58, p90 0.64.
WILD = 0.45

#: What somebody's hulls actually being here is worth.
#:
#: The largest single term, and it should be: a patrol on station is the only
#: thing in the list that can do anything about a raider today. Two hulls take
#: a system from wild to well under the raider threshold on their own.
PER_HULL = 0.20

#: The most a squadron can be credited with, however large it is.
#: Four hulls is a presence; twelve is not four times as much law.
GUARD_CAP = 0.45

#: What a dock is worth — people who notice — and what a claim is worth: a
#: power with an opinion about the system, but not necessarily anybody in it.
PORT_WORTH = 0.16
CLAIM_WORTH = 0.10

#: How much of the far edge's lawlessness is distance alone.
#:
#: Measured: nearest-capital distance runs 0 to 21 across a sector, median 14.
#: At 0.30 the far edge carries about a third of the way from policed to wild
#: on remoteness by itself, which is what makes the frontier the frontier.
REACH_WORTH = 0.30

#: What unlicensed growth does to it. A system the Bloom is eating empties of
#: everyone who would have been watching, and it is the one term that can push
#: a system with a port and a squadron back over the line.
BLOOM_WORTH = 0.55

#: At and above this, unmarked hulls work the system.
#:
#: Set against the distribution the sector actually produces rather than
#: chosen round. It is a floor and not the whole story: `traffic.RAIDER_SHARE`
#: scales the chance *within* it, so this only says where nobody works
#: unmarked at all. At 0.63 — the point where 11% of systems qualified — the
#: sector carried 9 raider systems against the old gate's 26, because the
#: least policed places are the portless ones and they carry about one hull
#: each. A lower floor with a slope above it puts the piracy back without
#: putting it in the capitals.
RAIDERS_FROM = 0.40


def _reach(game, system) -> float:
    """How far this system is from the nearest capital, 0 (at one) to 1.

    Capitals rather than any port, because reach is a thing governments have:
    an outpost three jumps beyond the last station is nobody's back yard.
    """
    caps = [s for s in game.galaxy.systems
            if getattr(s, "port", None) is not None and s.port.capital]
    if not caps:
        return 1.0
    here = (getattr(system, "x", 0.0), getattr(system, "y", 0.0))
    near = min(math.dist(here, (s.x, s.y)) for s in caps)
    span = max(1e-6, max(math.dist((a.x, a.y), (s.x, s.y))
                         for a in game.galaxy.systems for s in caps[:1]))
    return max(0.0, min(1.0, near / span))


def lawlessness(game, system) -> float:
    """How little law there is here, 0 (policed) to 1 (nobody is looking).

    **The one door.** `traffic` used to decide whether raiders could work a
    system and `encounters` used to decide how dangerous arriving was, each
    from its own arithmetic over the same field, so the two could disagree
    about the same volume and nothing would notice.
    """
    from . import fleets
    from . import territory as territory_sim

    loose = WILD
    guard = sum(fleets.squadron_at(game, system).values())
    loose -= min(GUARD_CAP, PER_HULL * guard)
    if getattr(system, "port", None) is not None:
        loose -= PORT_WORTH
    if territory_sim.claimant(game, system):
        loose -= CLAIM_WORTH
    loose += REACH_WORTH * _reach(game, system)
    loose += BLOOM_WORTH * float(getattr(system, "bloom", 0.0) or 0.0)
    return max(0.0, min(1.0, loose))


#: What share of a completely lawless system's hulls are unmarked.
#:
#: Multiplied by `lawlessness`, so a system at 0.8 puts about a third of its
#: traffic in raiders and one at 0.45 puts an eighth. Calibrated to keep the
#: sector carrying about as much piracy as the old flat 18%-behind-a-port-gate
#: did — 26 systems in 252 — while moving *which* systems. It lives here and
#: not in `sim/traffic` because it is a fact about piracy.
RAIDER_SHARE = 0.42


def raider_chance(game, system) -> float:
    """How likely any one hull here is working unmarked, 0 to 1.

    **The one door**, and it replaced two. `sim/traffic` asked whether raiders
    could work a system and then rolled its own flat chance; the floor and the
    slope were in different files and the Bloom was counted in both. A caller
    wanting "is this a pirate system" asks whether this is above zero.
    """
    loose = lawlessness(game, system)
    return RAIDER_SHARE * loose if loose >= RAIDERS_FROM else 0.0



#: How far stolen cargo will travel to find a buyer, in sector units.
#:
#: Measured against what the sector actually offers: across three sectors the
#: distance from a market to the nearest system raiders work runs 5.3 to 44.6
#: with a median of 16.9. At 20 the nearest markets sit at about three
#: quarters pull and the median one at a sixth, so a fence is a property of a
#: few places rather than a flat discount everywhere.
FENCE_REACH = 20.0


def fence_pull(game, system) -> float:
    """How much stolen cargo reaches this market, 0 (none) to 1 (a flood).

    **The other half of piracy, and it cannot live where the raiders are.**
    Measured: raiders never work a system with a port — `lawlessness` sees to
    that — and a market is a port. The two are disjoint by construction, so
    "raider presence feeds the local black market" describes something that
    can never happen.

    What can happen is that the cargo travels. This is a market's *distance*
    from where hulls are actually being taken, which is a real and well-spread
    quantity where the local one is flat: every market in the game sits at
    lawlessness 0.00 to 0.06.
    """
    from . import traffic as traffic_sim
    here = (getattr(system, "x", 0.0), getattr(system, "y", 0.0))
    near = None
    for other in getattr(game, "galaxy", None).systems:
        if not traffic_sim.hostiles(game, other):
            continue
        gap = math.dist(here, (other.x, other.y))
        near = gap if near is None else min(near, gap)
    if near is None:
        return 0.0
    return max(0.0, min(1.0, 1.0 - near / FENCE_REACH))


def note(game, system) -> str:
    """One line on how well kept this system is, for a screen to print."""
    loose = lawlessness(game, system)
    # Banded on the quantiles the sector produces: a quarter of systems come
    # in under 0.03, half under 0.39, and the raider threshold is p89.
    if loose < 0.20:
        return "Well kept: patrolled, docked and watched."
    if loose < RAIDERS_FROM:
        return "Quiet enough. Somebody would notice."
    if loose < 0.80:
        return "Poorly kept. Unmarked hulls work systems like this one."
    return "Nobody is looking after this at all."
