"""What is on a world's map, and what used to be.

`sim/worldmap.py` says what the ground is like. This says who is on it —
cities, towns, villages, outposts, mines, farms, research stations and
garrisons, and the abandoned stations, worked-out mines and ruins they
leave behind.

Three rules decide it, in this order:

1. **What the game already knows goes on first.** A player's colony, an NPC
   settlement (`sim/settlement`) and a ground base (`sim/establishments`)
   are real, saved things that other systems read; they are placed on the
   map at a stable cell rather than invented again. The map agrees with the
   rest of the game or it is worse than no map.
2. **The profile decides the rest.** How developed a world is is its
   Traveller population digit (`sim/profile`) — nought is ground nobody has
   walked, seven is a world with a city on it — so the same number that
   drives the port, the law and the market drives what you can see from
   orbit.
3. **A history, briefly.** Some of what was put down failed: a seam ran
   out, a colony lost its reason. Those become what `data/developments`
   says they fall to, which is how a world ends up with a ruin next to a
   worked-out mine and a story you can read off the map.

Derived and never stored, from `RNG(f"{seed}:sites:{system}:{body}")`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.rng import RNG
from ..data.developments import (APART, DEVELOPMENTS_BY_ID, LADDER, WORKS)
from . import worldmap

#: How many places a world carries, by its population digit. A world with
#: nobody on it still gets whatever the sector has put there — a base, a
#: wreck — and no more.
BY_POPULATION = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 8, 7: 10,
                 8: 12, 9: 14, 10: 16}

#: The share of what was ever built that has since failed. A world reads
#: better with a couple of dead places on it than with none: it is the
#: difference between a map and a plan.
RUINED = 0.22

#: How likely a world is to have something down on it that should not be.
WRECK_ODDS = 0.30


@dataclass(frozen=True)
class Site:
    """One thing on a world's surface."""

    x: int
    y: int
    kind: str
    name: str
    #: The real thing behind it, where there is one: `colony:<id>`,
    #: `settlement:<id>`, `est:<id>`, or "" for one this map invented.
    anchor: str = ""

    @property
    def what(self):
        return DEVELOPMENTS_BY_ID[self.kind]

    @property
    def heads(self) -> int:
        return self.what.heads

    @property
    def empty(self) -> bool:
        return self.what.empty


_MADE: dict = {}


def of(game, body) -> tuple:
    """Everything on this world. The one door; cheap to call twice."""
    key = (getattr(game, "seed", "verge"), getattr(game.system, "id", 0),
           getattr(body, "id", "?"), _anchors_key(game, body))
    got = _MADE.get(key)
    if got is None:
        got = _build(game, body, ":".join(str(k) for k in key[:3]))
        _MADE[key] = got
    return got


def at(game, body, x: int, y: int):
    """What is on that cell, or None."""
    return next((s for s in of(game, body)
                 if s.x == x % worldmap.WIDE and s.y == y), None)


def _anchors_key(game, body) -> str:
    """What the *saved* world has put here, so the map is rebuilt when it
    changes — a colony founded today is on the map today."""
    from . import settlement as settlement_sim
    bits = [str(getattr(body, "colony", None) or "")]
    held = settlement_sim.on_body(game, game.system.id, body.id)
    bits.append(str(getattr(held, "id", "") if held else ""))
    return "|".join(bits)


# ── placing them ───────────────────────────────────────────────────────────

def _score(world, cell, want) -> float:
    """How well this cell suits that kind of place.

    Additive and readable, in the shape the world simulator this borrowed
    from uses: ground it likes, ground it refuses, a coast if it wants one,
    and a mild preference for the low and the flat, because people build
    where it is easy to build.
    """
    if cell.water:
        return -1.0
    if cell.terrain in want.avoids:
        return -1.0
    score = 1.0
    if cell.terrain in want.likes:
        score += 2.0
    if want.coastal and _coastal(world, cell):
        score += 1.5
    score += (1.0 - cell.height) * 0.8
    score += cell.wet * 0.4
    return score


def _coastal(world, cell) -> bool:
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if world.at(cell.x + dx, cell.y + dy).water:
            return True
    return False


def _far_enough(placed, x: int, y: int, kind: str) -> bool:
    want = APART.get(kind, 1)
    for site in placed:
        gap = max(abs(site.x - x), abs(site.y - y))
        near = min(APART.get(site.kind, 1), want)
        if gap < max(1, near):
            return False
    return True


def _pick(world, rng, placed, kind: str):
    """The best cell for one of these, with a little taste in it."""
    want = DEVELOPMENTS_BY_ID[kind]
    rows = []
    for cell in world.cells:
        score = _score(world, cell, want)
        if score <= 0 or not _far_enough(placed, cell.x, cell.y, kind):
            continue
        rows.append((score + rng.float(0.0, 0.9), cell))
    if not rows:
        return None
    rows.sort(key=lambda row: -row[0])
    return rows[0][1]


def _build(game, body, seed: str) -> tuple:
    from . import establishments as est_sim
    from . import settlement as settlement_sim
    from . import profile as profile_sim
    world = worldmap.of(game, body)
    rng = RNG(f"{seed}:sites")
    got = profile_sim.profile(game, game.system, body)
    people = int(getattr(got, "population", 0) or 0)
    placed: list = []

    # 1. What the game already knows is here.
    if getattr(body, "colony", None) is not None:
        colony = next((c for c in game.colonies if c.id == body.colony), None)
        if colony is not None:
            cell = _pick(world, rng, placed, "town")
            if cell is not None:
                placed.append(Site(cell.x, cell.y, "town", colony.name,
                                   anchor=f"colony:{colony.id}"))
    held = settlement_sim.on_body(game, game.system.id, body.id)
    if held is not None:
        cell = _pick(world, rng, placed, "mine")
        if cell is not None:
            placed.append(Site(cell.x, cell.y, "mine",
                               f"{body.name} Works",
                               anchor=f"settlement:{held.id}"))
    for found in est_sim.here(game, game.system):
        if found.body_id != body.id or found.kind.kind != "base":
            continue
        kind = _est_kind(found.kind.id)
        cell = _pick(world, rng, placed, kind)
        if cell is not None:
            placed.append(Site(cell.x, cell.y, kind, found.name,
                               anchor=f"est:{found.kind.id}"))

    # 2. What the profile says the rest of the world holds.
    want = BY_POPULATION.get(min(10, people), 0)
    for kind in _ladder_for(people):
        if len(placed) >= want:
            break
        cell = _pick(world, rng, placed, kind)
        if cell is None:
            continue
        placed.append(Site(cell.x, cell.y, kind,
                           _name_for(rng, body, kind)))

    # 3. And what failed.
    living = [s for s in placed if not s.empty and not s.anchor]
    for site in list(living):
        if len(living) <= 1 or not rng.chance(RUINED):
            continue
        falls = site.what.falls_to
        if not falls:
            continue
        placed[placed.index(site)] = Site(site.x, site.y, falls,
                                          _dead_name(rng, site), "")
        living.remove(site)
    if rng.chance(WRECK_ODDS):
        cell = _pick(world, rng, placed, "outpost")
        if cell is not None:
            placed.append(Site(cell.x, cell.y, "wreck",
                               _dead_name(rng, None)))
    return tuple(placed)


def _ladder_for(people: int) -> list:
    """The kinds a world of this population puts down, biggest first."""
    out: list = []
    if people >= 7:
        out.append("city")
    if people >= 5:
        out += ["town", "town"]
    if people >= 3:
        out += ["village", "village", "village"]
    out += ["outpost", "outpost"]
    out += list(WORKS)
    out += ["village", "outpost", "outpost", "outpost"]
    return out


def _est_kind(est_id: str) -> str:
    """Which rung one of the six ground bases stands on."""
    return {"mining_base": "mine", "research_base": "research",
            "garrison": "garrison", "farm_base": "farm",
            "smugglers_den": "outpost", "retreat": "village"
            }.get(est_id, "outpost")


#: Words a place on a world is called, kept plain: a name should read as a
#: place somebody lives rather than as a fantasy.
_FIRST = ("North", "South", "High", "Low", "Old", "New", "Far", "Near",
          "Deep", "Long", "Cold", "Dry")
_PLACE = ("Reach", "Landing", "Crossing", "Field", "Bluff", "Hollow",
          "Stand", "Camp", "Works", "Bend", "Rise", "Bore", "Spur")
_DEAD = ("nobody goes back to", "the charts still carry", "the last shift "
         "left", "the register has not struck off")


def _name_for(rng, body, kind: str) -> str:
    stem = f"{rng.pick(_FIRST)} {rng.pick(_PLACE)}"
    if kind in ("mine", "farm", "research", "garrison"):
        return f"{body.name} {rng.pick(_PLACE)}"
    return stem


def _dead_name(rng, site) -> str:
    if site is None:
        return f"the wreck at {rng.pick(_PLACE)}"
    return site.name


def says(game, body) -> str:
    """One line for a screen: what is on this world."""
    here = of(game, body)
    if not here:
        return "Nothing has ever been put down here."
    alive = [s for s in here if not s.empty]
    dead = [s for s in here if s.empty]
    heads = sum(s.heads for s in alive)
    bits = []
    if alive:
        bits.append(f"{len(alive)} place{'' if len(alive) == 1 else 's'}"
                    + (f", {heads:,} people" if heads else ""))
    if dead:
        bits.append(f"{len(dead)} abandoned")
    return f"{body.name}: " + " · ".join(bits) + "."
