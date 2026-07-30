"""The walk back to the lander, costed before it is taken.

The ground poses exactly one arithmetic decision and it was invisible. A party
carries `supply` in days; every step spends one day on ground it has already
crossed and up to three on ground it has not, plus whatever the weather is doing.
Reach the lander and the haul comes up, capped at what four people can lift. Run
out first and the party is **stranded**: `expedition.STRANDED_SHARE` of that,
which is 40%, and everything else stays where it fell.

The screen showed "Supply · 7 days" and nothing whatever about how far away the
lander was. `tests/ground_ai.py` had already written the consequence down for the
*driver* — "the one decision the ground actually poses — how much supply to keep
in hand for the walk home — was invisible to a driver that never walked home" —
and the captain was in the same position, with 60% of a hold riding on it.

So: the cheapest known way back, what it costs in days, and whether the supplies
cover it. Dijkstra over the tiles the party has *seen*, adding up
`expedition.step_cost`, which is the same function `move` charges. A route always
exists, because the party's own footprints are visited ground.

Deliberately *not* a prediction of the weather. `step_cost` reads what it is doing
now, so this is "at this weather" and the readout says so — a front that arrives
while the party is walking makes the walk dearer, and that is the risk of leaving
it late rather than an error in the quote.
"""

from __future__ import annotations

import heapq

from . import expedition as exp_sim


def _known(exp, tile) -> bool:
    """Can the party plan a route over this tile at all?

    Seen or crossed. An unseen tile is one nobody has looked at, and routing
    through it would be inventing terrain — the same reason the chart refuses to
    price a jump into a system you have never visited.
    """
    return bool(tile.seen or tile.visited)


def route(exp) -> list[tuple[int, int]]:
    """The cheapest known way from where the party is to the lander.

    The list of tiles to step onto, in order, not including the one they are
    standing on. Empty when they are already there.
    """
    start = (exp.x, exp.y)
    goal = exp_sim.LANDER
    if start == goal:
        return []
    best: dict[tuple[int, int], tuple] = {start: (0.0, 0)}
    came: dict[tuple[int, int], tuple[int, int]] = {}
    queue: list = [((0.0, 0), start)]
    seen: set = set()
    while queue:
        spent, at = heapq.heappop(queue)
        if at in seen:
            continue
        seen.add(at)
        if at == goal:
            break
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0),
                       (-1, -1), (1, -1), (-1, 1), (1, 1)):
            nxt = exp.tile(at[0] + dx, at[1] + dy)
            if nxt is None or not _known(exp, nxt):
                continue
            step = exp_sim.step_cost(exp, nxt)
            # Ties go to ground already crossed. They cost the same in days —
            # measured, a dust storm adds one to every step, so the party's own
            # footprints and a fresh ridge both came to two — but a known track
            # is what a party would actually walk, and it is the route the
            # screen is drawing. Without this the quote was right and the line
            # on the map wandered off through terrain nobody had set foot on.
            through = (spent[0] + step, spent[1] + (0 if nxt.visited else 1))
            key = (nxt.x, nxt.y)
            if through < best.get(key, (float("inf"), float("inf"))):
                best[key] = through
                came[key] = at
                heapq.heappush(queue, (through, key))
    if goal not in came and goal != start:
        return []
    path = [goal]
    while path[-1] != start:
        path.append(came[path[-1]])
    path.reverse()
    return path[1:]


def cost(exp) -> int:
    """Days of supply the cheapest known way home spends, at this weather."""
    days = 0
    for x, y in route(exp):
        tile = exp.tile(x, y)
        if tile is None:
            continue
        days += exp_sim.step_cost(exp, tile)
    return days


def standing(exp) -> dict:
    """Everything the screen and a party leader need about getting home.

    `spare` is the decision: days of supply left over once the walk is paid for.
    Zero or less means the party is already committed to stranding unless the
    ground gets kinder, which is worth saying in those words rather than leaving
    a captain to subtract two numbers nobody has shown them.

    **Counts the days the party cannot move.** Some fronts pin a party where it
    stands — `weather.pinned` — and the first version of this quoted "4 days home,
    3 to spare" to a party held fast by a katabatic gale, which is a trap rather
    than a forecast: those days are spent whatever anybody wants, and the walk has
    not begun. Found by the check that walks the quoted route and was refused at
    the first step.
    """
    from . import weather as weather_sim

    if exp.over:
        return {"home": True, "days": 0, "spare": exp.supply, "ok": True,
                "steps": 0, "why": "", "stranding": False, "pinned": False,
                "waiting": 0}
    here = (exp.x, exp.y) == exp_sim.LANDER
    held = weather_sim.pinned(exp)
    waiting = weather_sim.days_left(exp) if held else 0
    if here:
        return {"home": True, "days": 0, "spare": exp.supply, "ok": True,
                "steps": 0, "why": "At the lander.", "stranding": False,
                "pinned": held, "waiting": waiting}
    way = route(exp)
    days = cost(exp) + waiting
    spare = exp.supply - days
    if not way:
        return {"home": False, "days": days, "spare": spare, "ok": False,
                "steps": 0, "why": "No known way back from here.",
                "stranding": True, "pinned": held, "waiting": waiting}
    why = ""
    if spare < 0:
        why = f"{-spare} day(s) short of the lander — they will strand."
    elif held:
        why = (f"{weather_sim.current(exp).name}: nothing moves for "
               f"{waiting} more day(s), and they are counted here.")
    return {
        "home": False, "days": days, "spare": spare, "steps": len(way),
        "ok": spare >= 0, "stranding": spare < 0,
        "pinned": held, "waiting": waiting, "why": why,
    }


def step_towards_home(exp) -> tuple[int, int]:
    """The next step of the cheapest way back, as a direction. (0, 0) if there.

    A party leader's one move, so `tests/ground_ai.py` and the chronicle walk the
    same route the screen is quoting rather than a straight line of their own.
    """
    way = route(exp)
    if not way:
        return 0, 0
    nx, ny = way[0]
    return nx - exp.x, ny - exp.y
