"""What a site is laid out as: the one door from a site to its deck plan.

Every plan is drawn in the shape of the thing it is a plan of, from the
program of spaces that thing needs (`sim/afoot_program`, `afoot_placeprog`):

- **a hull** — your own, a struck prize, a wreck — is sliced through its
  own silhouette (`sim/afoot_hullplan`), from its card and its fitted list:
  refit her and the plan changes, because the plan is the fitted list; a
  Dry Choir frame is its lattice (`afoot_latticeplan`);
- **a quay** is its can, arm and mast; **a Fleet Hub** its spine, four
  arms and two rings (`sim/afoot_stationplan`);
- **a habitat or a holding** is whatever `data/works3d.traits_of` says its
  class is built as — a drum, a tower, a dome, a ring, works dug into the
  ground, or modules on a keel (`afoot_stationplan`, `afoot_worksplan`,
  `afoot_groundplan`);
- **a settlement** is sheds and streets on the world it works, open to the
  sky or sealed against it as the world's air decides;
- **an establishment** — a yard, a hotel, a wheel, a den — is the shape its
  table gives it (`data/establishments.py`), holding the rooms its trade
  needs;
- **a Kith gathering** is the Kith's own hall.

`plan(game, site)` is seeded on the chronicle and the site's key, so a quay
is the same quay every time.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data import afoot_derelicts as wrecks
from ..data.afoot_rooms import ROOM_BY_ID
from ..data.chassis import CHASSIS_BY_ID
from ..data.colonies import COLONIES_BY_ID
from ..data.establishments import ESTABLISHMENT_BY_ID
from . import afoot_groundplan as groundplan
from . import afoot_hullplan as hullplan
from . import afoot_placeprog as placeprog
from . import afoot_program as program
from . import afoot_stationplan as stationplan
from . import afoot_worksplan as worksplan
from .afoot_gen import Want, assemble

#: Atmosphere codes a person can breathe unmasked (the UWP's standard,
#: thin and dense, untainted).
BREATHABLE = (5, 6, 8)
#: Classes whose works are dug into the body they stand on: a mine's
#: roots, a still's condenser bell. They are laid out on the ground — all
#: but a skimmer, whose bell hangs in a gas giant it cannot stand on.
DUG_IN = ("roots", "bell")
#: Shapes that stand on a world, and take its gravity. Everything else is
#: weightless, or spun (`afoot_ringplan`, a drum's floor).
ON_THE_GROUND = ("ground", "tower", "dome")


def plan(game, site):
    """Lay out the site. Returns `afoot_gen.Laid`."""
    rng = RNG(f"{game.seed}:afoot:{site.key}")
    return assemble(rng, _paint(game, site, rng))


def plan_hull(game, site, hull):
    """A plan for a hull that is not the chronicle's own — a struck prize."""
    rng = RNG(f"{game.seed}:afoot:{site.key}")
    return assemble(rng, _hull(rng, hull))


def _paint(game, site, rng) -> list:
    if site.kind == "ship":
        return _hull(rng, game.ship, game)
    if site.kind == "prize":
        return _hull(rng, _stand_in(rng, site.look))
    if site.kind == "wreck":
        return _wreck(rng, game, site)
    if site.kind == "kith":
        return worksplan.gathering(rng, placeprog.gathering())
    place, venues = _place(game, site)
    if site.kind == "port":
        hub = bool(getattr(getattr(game.system, "port", None), "capital",
                           False))
        own, halls = placeprog.quay(rng, site, venues, hub)
        return (stationplan.hub if hub else stationplan.quay)(
            rng, own, halls, "station")
    if site.kind in ("station", "base"):
        return _establishment(rng, game, site, place, venues)
    if site.kind == "downside":
        good = site.what.rsplit("working ", 1)[-1].rstrip(".")
        wants = placeprog.settlement(rng, site, venues, good)
        return _by_shape(rng, game, site, place, wants, "ground",
                         "settlement")
    return _works(rng, game, site, place, venues)


def _works(rng, game, site, place, venues) -> list:
    """A habitat or a holding, by what its class is built as."""
    klass = COLONIES_BY_ID.get(site.look)
    wants = placeprog.works(rng, site, klass, venues)
    style = getattr(klass, "family", "") or "station"
    if style == "synthetic":
        return worksplan.modules(rng, wants, style, air=False,
                                 name=site.name)
    return _by_shape(rng, game, site, place, wants, shape_of(klass), style)


def shape_of(klass) -> str:
    """What a class of holding is built as, from its traits."""
    from ..data.works3d import traits_of
    traits = set(traits_of(klass)) if klass is not None else set()
    for trait in ("drum", "tower", "dome", "ring"):
        if trait in traits:
            return trait
    if traits & set(DUG_IN) and "scoop" not in traits:
        return "ground"
    return "keel"


def _establishment(rng, game, site, place, venues) -> list:
    """A yard, a hotel, a wheel or a den, in the shape it is built as."""
    kind = ESTABLISHMENT_BY_ID[site.look]
    wants = placeprog.establishment(rng, site, kind, venues)
    return _by_shape(rng, game, site, place, wants, kind.shape, kind.family)


def _by_shape(rng, game, site, place, wants, shape: str, style: str) -> list:
    """Lay a place's program out in the shape named — and anything that
    stands on a world weighs what that world makes it weigh."""
    painted = _shaped(rng, game, site, place, wants, shape, style)
    if shape in ON_THE_GROUND:
        for deck in painted:
            deck.g = _world_g(game, place)
    return painted


def _shaped(rng, game, site, place, wants, shape: str, style: str) -> list:
    if shape == "ground":
        return groundplan.settlement(rng, wants, style,
                                     _breathable(game, place), name=site.name)
    if shape == "quay":
        own = [w for w in wants if w.kind in ("docks", "customs", "harbour",
                                              "traffic") or w.venue == ""]
        halls = [w for w in wants if w not in own]
        return stationplan.quay(rng, own, halls, style)
    blueprint = {"ring": stationplan.ringed, "drum": stationplan.drum,
                 "tower": worksplan.tower, "dome": worksplan.dome}.get(shape)
    if blueprint is not None:
        return blueprint(rng, wants, style)
    return worksplan.modules(rng, wants, style, name=site.name)


def _place(game, site) -> tuple:
    from . import places as places_sim
    from . import shore
    place = places_sim.by_id(game, site.place_id)
    return place, (shore.open_here(game, place) if place is not None else [])


def _world_g(game, place) -> float:
    """The surface gravity of the world a place stands on."""
    body = _body(game, place)
    return round(float(getattr(body, "gravity", 1.0) or 0.0), 2) \
        if body is not None else 1.0


def _body(game, place):
    system = game.system
    return next((b for b in getattr(system, "bodies", ()) or ()
                 if b.id == getattr(place, "body_id", None)), None)


def _breathable(game, place) -> bool:
    """Can the world this place stands on be breathed?"""
    from . import profile as profile_sim
    body = _body(game, place)
    if body is None:
        return False
    return profile_sim.profile(game, game.system, body).atmosphere \
        in BREATHABLE


# ── hulls ──────────────────────────────────────────────────────────────────

def _hull(rng, hull, own=None) -> list:
    """A hull's decks, from its card and what is fitted to it. `own` is the
    game when the hull is the chronicle's own: the doors open aboard (the
    mess, the sickbay) are then the rooms they are."""
    chassis = CHASSIS_BY_ID.get(getattr(hull, "chassis", ""), None) or \
        CHASSIS_BY_ID["tender"]
    wants = program.ship(chassis, getattr(hull, "fitted", []) or [],
                         _aboard(own) if own is not None else ())
    return hullplan.decks(rng, chassis, wants, chassis.family)


def _aboard(game) -> list:
    from . import places as places_sim
    from . import shore
    place = places_sim.ship(game)
    return shore.open_here(game, place) if place is not None else []


def _stand_in(rng, chassis_id: str):
    """A hull of this class with what one usually carries, for a plan with
    no hull in hand."""
    from types import SimpleNamespace
    chassis = CHASSIS_BY_ID.get(chassis_id) or CHASSIS_BY_ID["tender"]
    return SimpleNamespace(chassis=chassis.id,
                           fitted=program.typical_fit(rng, chassis))


def _wreck(rng, game, site) -> list:
    """The hull it was, and whatever its end added: a vault, the Bloom's
    heart — or the structure it was, with nobody left to open its doors."""
    kind = wrecks.DERELICT_BY_ID[site.wreck]
    if kind.structure:
        est = ESTABLISHMENT_BY_ID.get(kind.structure)
        if est is not None:
            wants = placeprog.establishment(rng, site, est, [])
            return _by_shape(rng, game, site, None, wants, est.shape,
                             est.family)
        klass = COLONIES_BY_ID[kind.structure]
        return _by_shape(rng, game, site, None,
                         placeprog.works(rng, site, klass, []),
                         shape_of(klass), klass.family)
    chassis = CHASSIS_BY_ID[kind.chassis]
    wants = program.ship(chassis, program.typical_fit(rng, chassis))
    for extra in kind.rooms:
        room = ROOM_BY_ID[extra]
        wants.append(Want(extra, room.name, lock=2 if extra == "vault" else 0,
                          area=12, zone=0.1))
    return hullplan.decks(rng, chassis, wants, chassis.family)
