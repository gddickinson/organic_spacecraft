"""Somewhere to walk: everything the party could set foot in from where the hull is.

A site is read off what the game already keeps, never stored:

- **your own hull**, always;
- every **place** alongside (`sim/places.py`): the quay, a habitat drum, a
  holding of yours, a power's settlement on the ground — with a Kith
  gathering, which is a quay the Kith keep, walked as the Kith's own hall;
- a **derelict** adrift in the system, if the chronicle's seed put one here
  (`data/afoot_derelicts.py`);
- a **struck prize**, which is never on this list: it exists only for the
  minutes after a battle and is boarded from the battle's own dialog
  (`prize_site`).

Each site carries the four numbers a place answers — people, amenity, tech,
law — because the cast, the loot and the constables are all read off them,
and a `key` that seeds its plan. The same key is the same deck plan in every
visit and every process.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.rng import RNG
from ..data import afoot_derelicts as wrecks
from ..data.chassis import CHASSIS_BY_ID
from . import places as places_sim

#: What a site's kind is laid out as, when it is not a hull of some family.
STYLE = {"port": "station", "habitat": "habitat", "holding": "settlement",
         "downside": "settlement", "kith": "xeno", "station": "station",
         "base": "settlement"}


@dataclass(frozen=True)
class Site:
    """Somewhere the party can walk."""

    key: str
    #: ship | port | habitat | holding | downside | kith | wreck | prize
    kind: str
    name: str
    what: str
    style: str
    faction: str = ""
    law: int = 0
    tech: int = 9
    heads: int = 0
    amenity: int = 0
    place_id: str = ""
    #: The colony class a holding or habitat is, or the chassis of a hull.
    look: str = ""
    #: The derelict's kind (`data/afoot_derelicts.py`), for a wreck.
    wreck: str = ""
    ok: bool = True
    why: str = ""
    #: Your own ground — a holding or a drum of yours — or your own hull.
    mine: bool = False
    #: Who a quay serves, as `Place.served`: the world under it.
    served: int = 0


def here(game) -> list:
    """Every site the party could walk from where the hull is, hull first."""
    out = [own_hull(game)]
    for place in places_sim.here(game):
        if place.kind == "ship":
            continue
        out.append(_from_place(game, place))
    got = derelict(game, game.system)
    if got is not None:
        out.append(got)
    return out


def by_key(game, key: str):
    return next((s for s in here(game) if s.key == key), None)


def own_hull(game) -> Site:
    """Your own hull, whatever it is. A hull with nobody aboard to walk it
    is still a site; the party is whoever is aboard."""
    ship = game.ship
    chassis = CHASSIS_BY_ID.get(ship.chassis)
    family = getattr(chassis, "family", "grown")
    place = places_sim.ship(game)
    return Site(key=f"ship:{ship.uid}", kind="ship", name=ship.name,
                what=(f"Your own hull — {chassis.name if chassis else 'a hull'}"
                      f", {getattr(chassis, 'tier', '').lower()}."),
                style=family, law=0,
                tech=getattr(place, "tech", places_sim.SHIP_TECH_BASE),
                heads=getattr(place, "heads", ship.crew),
                amenity=getattr(place, "amenity", 1), place_id="ship",
                look=ship.chassis)


def _from_place(game, place) -> Site:
    from . import kith_world
    kind = place.kind
    if kind == "port" and kith_world.is_gathering(game.system):
        kind = "kith"
    ok, why = True, ""
    if kind != "holding" and not places_sim.livable(place):
        ok, why = False, "Nobody lives here to walk among."
    return Site(key=f"place:{place.id}", kind=kind, name=place.name,
                what=place.what, style=STYLE.get(kind, "station"),
                faction=place.faction, law=place.law, tech=place.tech,
                heads=place.heads, amenity=place.amenity,
                place_id=place.id, look=place.look, ok=ok, why=why,
                mine=bool(place.mine), served=place.served)


def derelict(game, system):
    """The dead hull adrift in this system, if the seed put one here."""
    if system is None:
        return None
    rng = RNG(f"{game.seed}:derelict:{system.id}")
    odds = wrecks.ODDS_WITH_PORT if system.port else wrecks.ODDS_WITHOUT
    if not rng.chance(odds):
        return None
    where = {"verge"}
    if getattr(system, "region", "verge") != "verge":
        where = {"reaches"}
    if float(getattr(system, "bloom", 0.0) or 0.0) > 0.05:
        where.add("bloom")
    pool = [(d.weight, d) for d in wrecks.DERELICTS if d.where in where]
    if not pool:
        return None
    kind = rng.weighted(pool)
    name = f"{rng.pick(_WRECK_NAMES)}, {kind.name}"
    return Site(key=f"wreck:{system.id}", kind="wreck", name=name,
                what=kind.blurb, style=_wreck_style(kind), law=0,
                tech=10, heads=0, amenity=0,
                look=kind.structure or kind.chassis, wreck=kind.id)


def _wreck_style(kind) -> str:
    """Whose yard built what is left: the hull's family, or the family of
    the structure it was."""
    from ..data.colonies import COLONIES_BY_ID
    from ..data.establishments import ESTABLISHMENT_BY_ID
    if not kind.structure:
        return CHASSIS_BY_ID[kind.chassis].family
    made = ESTABLISHMENT_BY_ID.get(kind.structure) or COLONIES_BY_ID.get(
        kind.structure)
    return getattr(made, "family", "") or "station"


def prize_site(game, hull, faction: str) -> Site:
    """A struck hull, for the minutes she can be boarded."""
    chassis = CHASSIS_BY_ID.get(hull.chassis)
    return Site(key=f"prize:{hull.uid}:{game.day}", kind="prize",
                name=hull.name,
                what=(f"Struck, and waiting to see what you do. "
                      f"{chassis.name if chassis else 'A hull'}, "
                      f"{hull.crew} aboard."),
                style=getattr(chassis, "family", "fabricated"),
                faction=faction or "", law=0, tech=10,
                heads=int(getattr(hull, "crew", 0) or 0), look=hull.chassis)


_WRECK_NAMES = ("Quiet Margin", "Last Reading", "Patience", "Held Breath",
                "Open Question", "Lantern", "Second Thought", "Saltmarsh",
                "Thin Air", "Standing Order", "Long Division", "Kestrel",
                "Weatherglass", "Honest Measure", "Far Harbour", "Undertow")
