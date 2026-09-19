"""The way out of a boxed-in start: a lane the Charter's pilots have charted.

Where a chronicle opens decides how much of it can be played. Flooding from
the start at the opening drive reaches anywhere from 2 to all 42 systems:
measured over forty seeds, **15 opened on fewer than eight** and **14 on a
single power's ports**, and nine of those had one neighbour. `sim/reach`
already draws the wall and names the drive that would move it — which for a
NAVIS is a Foldrunner Coil, fourteen technologies and seventy-eight thousand
credits away: a project, not a way out.

The generator is not touched. Every seeded fixture in the suite is written
against the sector it makes, and the fix is not to the sector but to the
opening: when the start pocket is small, the Charter files a pilot's chart of
the shortest crossing out of it — a *lane*, a single named hop between two
systems that the drive can hold on a charted line although it is past its
rated reach. Greedy: the shortest gap from anywhere inside the pocket to
anywhere outside, again, until the pocket holds `MIN_POCKET` systems and
`MIN_POWERS` powers' ports. Measured on the same forty seeds: every one ends
with at least eight systems and two powers, **no seed needs more than two
lanes**, and none is longer than 11.2 ly — at most 2.3 ly past the opening
drive. Seeds that open wide get nothing and are byte-for-byte the game they
were.

How the captain is told: the opening log names the lane, the chart's reach
line (`reach.note`) names it every time it is read, and the chart offers the
jump because `actions.jump_quote` says it is in range.
"""

from __future__ import annotations

from ..world.galaxy import distance

#: The smallest opening worth calling a sector.
MIN_POCKET = 8

#: And the fewest powers whose ports it should hold — one power's quays are a
#: single price list, a single set of politics and a single board.
MIN_POWERS = 2

#: A backstop, not a tuning knob: forty seeds never needed more than two.
MAX_LANES = 4


def joined(a, b) -> bool:
    """Is there a charted lane between these two systems?"""
    return b.id in getattr(a, "lanes", ())


def _pocket(systems, start: int, jump: float) -> set:
    """Everything reachable by hopping at `jump`, lanes included."""
    seen, edge = {start}, [systems[start]]
    while edge:
        following = []
        for system in edge:
            for other in systems:
                if other.id in seen:
                    continue
                if distance(system, other) <= jump or joined(system, other):
                    seen.add(other.id)
                    following.append(other)
        edge = following
    return seen


def _powers(systems, ids) -> set:
    return {systems[i].port.faction for i in ids
            if systems[i].port is not None and systems[i].port.faction}


def chart(game) -> list[tuple[int, int]]:
    """File the lanes a boxed-in opening needs. Called once, by `new_game`."""
    systems = game.galaxy.systems
    jump = game.ship_stats.jump
    filed = []
    for _ in range(MAX_LANES):
        pocket = _pocket(systems, game.location_id, jump)
        if len(pocket) >= MIN_POCKET and len(_powers(systems, pocket)) >= MIN_POWERS:
            break
        outside = [s for s in systems if s.id not in pocket]
        if not outside:
            break
        a, b = min(((systems[i], t) for i in pocket for t in outside),
                   key=lambda pair: distance(*pair))
        a.lanes.append(b.id)
        b.lanes.append(a.id)
        filed.append((a.id, b.id))
    for a, b in filed:
        game.add_log(f"The Charter's pilots have filed a chart for you: a lane "
                     f"from {systems[a].name} to {systems[b].name}, "
                     f"{distance(systems[a], systems[b]):.1f} ly — past your "
                     "drive's rated reach, and holdable on the charted line. "
                     "It is the way out of this pocket.", "good")
    return filed


def lanes(game) -> list[tuple]:
    """Every charted lane in the sector, once each, as (from, to) systems."""
    systems = game.galaxy.systems
    return [(s, systems[i]) for s in systems for i in getattr(s, "lanes", ())
            if s.id < i]


def note(game) -> str:
    """One line for the chart, naming the lanes. Empty when there are none."""
    got = lanes(game)
    if not got:
        return ""
    return " Charted lane" + ("s" if len(got) > 1 else "") + ": " + "; ".join(
        f"{a.name} to {b.name} ({distance(a, b):.1f} ly)" for a, b in got) + "."
