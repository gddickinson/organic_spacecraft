"""A world's profile, derived from the world — never stored, never guessed twice.

`data/uwp.py` says what the eight characteristics *mean*; this works out what
they are for one body in this sector. Two rules, and they are the reason this
is a read rather than a field:

- **Nothing new is saved.** Every digit comes from something the chronicle
  already holds — the body's radius, its biome, its temperature, the port's
  level, who holds the system, what `sim/piracy` says about the law out here
  — so an old save grows a profile with no migration and a profile can never
  disagree with the world it describes.
- **What the world does not determine, the seed does, once.** Two rocky moons
  of the same size need not have the same government, and the difference has
  to be stable across a reload and across two screens asking in the same
  frame. `RNG(f"{seed}:uwp:…")` is drawn from the *sector's* seed, never
  `game.rng` — a screen that advanced the chronicle's luck by looking at a
  planet is the fault this project has been bitten by most.

The result is Traveller's spine laid over the Verge's own bones: one short
string that the port, the market, the law and the encounter tables can all
read, and which says something true about the place.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data.uwp import Profile, codes

#: Radius in km at or above which a world earns each size digit. Traveller's
#: scale is 1,600 km a step, which is exactly what this sector generates
#: against, so the two need no reconciling.
SIZE_STEPS = (800, 1_600, 3_200, 4_800, 6_400, 8_000, 9_600, 11_200,
              12_800, 14_400, 16_000)

#: What each biome breathes, before temperature and size have their say.
#: `world/planets.py` grows eight of them and they map cleanly onto the
#: atmosphere scale — which is a sign the two models are describing the same
#: universe rather than being made to agree.
BIOME_AIR = {
    "verdant": 6, "microbial": 5, "aerial": 9, "sulfuric": 11,
    "cryo": 1, "subsurface": 1, "regolith": 0, "barren": 0,
}

#: And how wet each one is, in tenths of the surface.
BIOME_WATER = {
    "verdant": 6, "microbial": 4, "aerial": 2, "sulfuric": 1,
    "cryo": 7, "subsurface": 3, "regolith": 0, "barren": 0,
}

#: A port's level against the starport class it earns. The Verge builds three
#: grades and Traveller names six; a capital gets the grade above its level,
#: which is what makes a capital worth flying to.
PORT_CLASS = {3: 4, 2: 3, 1: 2, 0: 1}

#: What each power's worlds are like to live under: `(government, law, tech)`
#: before the world itself and the seed adjust them. These are the factions'
#: own characters, written once — the Charter licenses everything, the
#: Freeholds license nothing, the Sanhedrin's law is its doctrine.
FACTION_RULE = {
    "charter": (8, 7, 11),
    "concordat": (1, 5, 11),
    "freeholds": (2, 2, 8),
    "sanhedrin": (13, 8, 9),
    "abyssals": (7, 1, 10),
    "bloom": (0, 0, 0),
}
DEFAULT_RULE = (0, 1, 7)


def _size(body) -> int:
    radius = float(getattr(body, "radius_km", 0) or 0)
    if getattr(body, "kind", "") in ("asteroid", "comet"):
        return 0
    for index, step in enumerate(SIZE_STEPS):
        if radius < step:
            return max(0, index - 1)
    return 10


def _air(body, rng) -> int:
    """What there is to breathe, from the biome, the size and the heat."""
    kind = getattr(body, "kind", "")
    if kind in ("asteroid", "comet"):
        return 0
    if kind == "gas":
        return 10                       # exotic: there is no surface to stand on
    got = BIOME_AIR.get(getattr(body, "biome", ""), 1)
    size = _size(body)
    if size <= 2:
        got = min(got, 1)               # too small to hold anything
    heat = int(getattr(body, "temp_k", 250) or 250)
    if heat > 400 and got in (5, 6, 8):
        got = 7                         # thin and tainted by what boiled off
    if heat < 120 and got >= 5:
        got = 4
    return max(0, min(15, got + rng.int(-1, 1)))


def _water(body, rng) -> int:
    kind = getattr(body, "kind", "")
    if kind in ("asteroid", "comet", "gas"):
        return 0
    if kind == "ocean":
        return max(7, min(10, 8 + rng.int(-1, 2)))
    if kind == "ice":
        return max(4, min(10, 7 + rng.int(-2, 2)))
    got = BIOME_WATER.get(getattr(body, "biome", ""), 0)
    if _air(body, RNG("still")) <= 1:
        got = min(got, 1)               # nothing to hold it down
    return max(0, min(10, got + rng.int(-1, 1)))


def _people(game, system, body, rng) -> int:
    """How many live here: the colony, the port and the capital say so."""
    got = 0
    if getattr(body, "colony", None) is not None:
        got = 4
    port = getattr(system, "port", None)
    if port is not None and _is_home(system, body):
        got = max(got, 2 + int(port.level))
        if getattr(port, "capital", False):
            got += 2
    if got <= 0:
        return 0
    # **Capped at millions.** Traveller's scale runs to trillions because the
    # Imperium has eleven thousand worlds; the Verge has forty-odd and is a
    # frontier fifty years old. A capital here is a city, and a profile that
    # said "hundreds of billions" of Marrow Reach would be describing a
    # different game.
    return max(0, min(7, got + rng.int(-1, 1)))


def _is_home(system, body) -> bool:
    """Is this the body the system's port actually sits at?

    The first body that could hold a port, which is how the sector places
    one. A profile that put a hub's population on a comet in the same system
    would be the sort of quiet nonsense a derived reading has to avoid.
    """
    rows = [b for b in getattr(system, "bodies", [])
            if getattr(b, "kind", "") not in ("gas", "comet")]
    return bool(rows) and rows[0].id == body.id


def profile(game, system, body) -> Profile:
    """This world in eight characteristics. The one door; cheap to call."""
    seed = getattr(game, "seed", "verge")
    rng = RNG(f"{seed}:uwp:{getattr(system, 'id', 0)}:{body.id}")
    size = _size(body)
    air = _air(body, rng)
    water = _water(body, rng)
    people = _people(game, system, body, rng)
    port = getattr(system, "port", None)
    star = 0
    if port is not None and _is_home(system, body):
        star = PORT_CLASS.get(int(port.level), 1)
        if getattr(port, "capital", False):
            star = min(5, star + 1)
    elif people > 0:
        star = 1
    who = getattr(system, "faction", None) or (
        getattr(port, "faction", None) if port is not None else None)
    gov, law, tech = FACTION_RULE.get(who or "", DEFAULT_RULE)
    if people <= 0:
        gov, law, tech = 0, 0, 0
    else:
        gov = max(0, min(13, gov + rng.int(-1, 1)))
        law = max(0, min(12, law + rng.int(-2, 2) - _lawless(game, system)))
        tech = max(0, min(15, tech + rng.int(-1, 1)
                          + (1 if star >= 4 else 0)
                          - (2 if people <= 3 else 0)))
    return Profile(
        starport=star, size=size, atmosphere=air, hydrographics=water,
        population=people, government=gov, law=law, tech=tech,
        bases=_bases(system, port, star), zone=_zone(game, system, law),
        gas_giant=any(getattr(b, "kind", "") == "gas"
                      for b in getattr(system, "bodies", [])))


def _lawless(game, system) -> int:
    """How far out of anybody's reach this is, as a law-level penalty.

    `sim/piracy.lawlessness` already answers this for the whole sector and
    the hunt board and every freight line read it; the profile reads the same
    number rather than inventing a second opinion about how wild the Verge is.
    """
    try:
        from . import piracy
        out = float(piracy.lawlessness(game, system))
    except (ImportError, AttributeError, TypeError):
        return 0
    return int(max(0.0, min(4.0, out * 4.0)))


def _bases(system, port, star: int) -> tuple:
    """What else is here that a captain cares about."""
    made = []
    if star >= 4:
        made.append("naval")
    if port is not None and "survey" in (getattr(port, "services", ()) or ()):
        made.append("scout")
    if getattr(system, "bloom", 0.0) > 0.35:
        made.append("bloom")
    return tuple(made)


def _zone(game, system, law: int) -> str:
    """Green, amber or red — the travel advisory, in Traveller's own terms.

    Amber is "go carefully": no law at all, or so much of it that a hull with
    a hold is a problem. Red is interdicted, which in the Verge means the
    Bloom has it.
    """
    if getattr(system, "bloom", 0.0) >= 0.6:
        return "red"
    if getattr(system, "bloom", 0.0) > 0.2:
        return "amber"
    # **An advisory is about people.** A barren rock with no law on it is not
    # "go carefully", it is nothing at all — and reading it as amber made 138
    # of 165 bodies in a fresh sector amber, which is an advisory that
    # advises nothing. Only somewhere with somebody on it can be dangerous
    # to put in at.
    if _population_of(system, law) and (law <= 0 or law >= 10):
        return "amber"
    return "green"


def _population_of(system, law: int) -> bool:
    """Is anybody here at all? A port or a colony is the whole test."""
    if getattr(system, "port", None) is not None:
        return True
    return any(getattr(b, "colony", None) is not None
               for b in getattr(system, "bodies", []))


# ── what the rest of the game asks ─────────────────────────────────────────

def port_world(system):
    """The body the system's port stands on, or None where there is none."""
    rows = [b for b in getattr(system, "bodies", [])
            if getattr(b, "kind", "") not in ("gas", "comet")]
    return rows[0] if rows else None


def says(game, system, body) -> list:
    """The profile as sentences, with the code and the classifications."""
    from ..data import uwp
    got = profile(game, system, body)
    lines = [f"{uwp.code(got)}   ·   "
             + ("  ".join(f"{c} {uwp.TRADE_NAMES[c]}" for c in codes(got))
                or "no classification")]
    lines.extend(uwp.says(got))
    lines.extend(uwp.trades(got))
    if got.bases:
        lines.append("Bases: " + ", ".join(got.bases) + ".")
    if got.zone != "green":
        lines.append("Travel advisory: "
                     + ("interdicted — the Bloom holds it" if got.zone == "red"
                        else "amber — go carefully"))
    if got.gas_giant:
        lines.append("A gas giant in the system: fuel without a port.")
    return lines
