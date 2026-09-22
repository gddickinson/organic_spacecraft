"""Afoot's deck plans are plans *of* the thing: its shape, and all of it.

The claims `sim/afoot_hullplan`, `afoot_stationplan`, `afoot_worksplan` and
`afoot_groundplan` make, held to:

- every hull class lays its **whole program** out — every space its crew,
  cargo, role and fitted parts need — inside **its own silhouette**, with
  the bridge forward and the drives aft, every deck joined by a lift and a
  way aboard;
- every class of holding is laid out **as its traits say it is built** — a
  drum's town, a tower's floors, a dome's open ground, a spun ring's
  unrolled levels off a hub,
  works dug into the ground, modules on a keel — and nothing it needs is
  dropped;
- a quay is a can, an arm and a mast, and a Fleet Hub a spine with four
  berths and two rings;
- a settlement is open to a sky it can breathe, and sealed against one it
  cannot;
- every structural trait `data/works3d` can emit has a working space.
"""

from __future__ import annotations

from dataclasses import replace

from ..core.rng import RNG
from ..data import afoot_programs as programs
from ..data.afoot_rooms import ROOM_BY_ID
from ..data.chassis import CHASSIS
from ..data.colonies import COLONIES
from ..data.works3d import traits_of
from ..sim import (afoot_gen, afoot_groundplan, afoot_hullplan, afoot_plans,
                   afoot_placeprog, afoot_program, afoot_sites)
from ..sim.afoot_gen import Want
from ..sim.afoot_state import FLOOR, GROUND, HALL
from . import afoot_kit
from .harness import Suite


def _hull_plan(chassis):
    wants = afoot_program.ship(chassis,
                               afoot_program.typical_fit(RNG("f"), chassis))
    painted = afoot_hullplan.decks(RNG("x"), chassis, wants, chassis.family)
    return wants, painted, afoot_gen.assemble(RNG("y"), painted)


def _mean_x(laid, kinds) -> float:
    xs = [x for r in laid.rooms if r.kind in kinds for x, _y in r.cells()]
    return sum(xs) / len(xs) if xs else 0.0


def _lost(painted) -> list:
    return [w.name for p in painted for w in p.sheet.lost()]


def _holding(game, klass):
    base = next(s for s in afoot_sites.here(game)
                if s.kind in ("holding", "habitat"))
    # No place behind it: the shape is the class's own, not the doors of
    # whatever drum the fixture happens to borrow (those are held by the
    # door check, against real places).
    return replace(base, key=f"place:shape-{klass.id}", look=klass.id,
                   kind="habitat" if klass.pop >= 1000 else "holding",
                   heads=klass.pop, name=klass.name, place_id="")


def run(suite: Suite) -> None:
    check = suite.check

    @check("every hull class lays out its whole program inside its own silhouette")
    def _():
        bad, spaces = [], 0
        for chassis in CHASSIS:
            wants, painted, laid = _hull_plan(chassis)
            spaces += len(wants)
            names = {r.name for r in laid.rooms}
            bad += [f"{chassis.id}: {w.name} not laid out" for w in wants
                    if w.name not in names]
            if chassis.family == "synthetic":
                continue
            hull = afoot_hullplan.Hull(chassis)
            while hull.width < laid.decks[0].w:
                hull.grow()
            for n, deck in enumerate(laid.decks):
                outside = [(x, y) for y, row in enumerate(deck.rows)
                           for x, c in enumerate(row) if c in (FLOOR, HALL)
                           and not hull.inside(x, y)]
                if outside:
                    bad.append(f"{chassis.id} deck {n}: floor outside the "
                               f"hull at {outside[:3]}")
        assert not bad, bad[:6]
        return f"{len(CHASSIS)} hull classes, {spaces} spaces, every one aboard"

    @check("the bridge is forward and the drives aft; every deck is joined and there is a way aboard")
    def _():
        bad = []
        for chassis in CHASSIS:
            _wants, _painted, laid = _hull_plan(chassis)
            lifts = [t for t in laid.things if t.kind == "lift"]
            if any(t.link < 0 for t in lifts):
                bad.append(f"{chassis.id}: a lift that goes nowhere")
            if len(_decks_reached(laid)) != len(laid.decks):
                bad.append(f"{chassis.id}: a deck nobody can ride to")
            if len(laid.decks) > 1 and not lifts:
                bad.append(f"{chassis.id}: decks with no lift between them")
            if not any(t.kind in ("airlock", "gangway") for t in laid.things):
                bad.append(f"{chassis.id}: no way aboard")
            if chassis.family == "synthetic" or not chassis.crew:
                continue
            fore = _mean_x(laid, ("bridge",))
            aft = _mean_x(laid, ("drive",))
            if aft and fore <= aft:
                bad.append(f"{chassis.id}: the bridge is aft of the drives")
        assert not bad, bad[:6]
        return f"{len(CHASSIS)} hulls: flown from forward, driven from aft, all joined"

    @check("every class of holding is laid out as its traits say it is built, all of it")
    def _():
        game = afoot_kit.settle(afoot_kit.fresh("afoot-shapes"))
        bad, shapes = [], {}
        for klass in COLONIES:
            site = _holding(game, klass)
            rng = RNG(f"{game.seed}:afoot:{site.key}")
            painted = afoot_plans._paint(game, site, rng)
            lost = _lost(painted)
            if lost:
                bad.append(f"{klass.id}: dropped {lost[:3]}")
            names = [p.name for p in painted]
            ground = any(GROUND in "".join(p.sheet.build(0, lambda: 0)[0])
                         for p in painted)
            shape = afoot_plans.shape_of(klass)
            ok = _shaped(shape, names, painted, ground)
            shapes[shape] = shapes.get(shape, 0) + 1
            if not ok:
                bad.append(f"{klass.id}: not laid out as a {shape} {names}")
        assert not bad, bad[:6]
        return f"{len(COLONIES)} classes: " + ", ".join(
            f"{n} {k}" for k, n in sorted(shapes.items()))

    @check("a quay is a can, an arm and a mast; a Fleet Hub a spine with four berths and two rings")
    def _():
        game = afoot_kit.fresh("afoot-shapes-port")
        site = next(s for s in afoot_sites.here(game) if s.kind == "port")
        got = {}
        for capital in (False, True):
            object.__setattr__(game.system.port, "capital", capital)
            laid = afoot_plans.plan(game, site)
            names = [d.name for d in laid.decks]
            ways = sum(1 for t in laid.things if t.kind == "gangway")
            got[capital] = (names, ways)
        quay, hub = got[False], got[True]
        assert quay[0][0] == "The quay" and quay[0][-1] == "The mast", quay
        assert quay[1] == 1, quay
        assert hub[0][0] == "The spine", hub
        rings = hub[0][1:]
        assert rings and all(n.startswith(("The first ring",
                                           "The second ring"))
                             for n in rings), hub
        assert any(n.startswith("The second ring") for n in rings), hub
        assert hub[1] == 4, hub
        return (f"quay: {len(quay[0])} decks, one arm; hub: a spine, "
                f"{hub[1]} berths, two rings over {len(rings)} levels")

    @check("every door the Concourse lists is a room you can walk into, by name")
    def _():
        from ..core.state import new_game
        from ..sim import places, shore
        seen, doors, bad = 0, 0, []
        for seed in ("shape-doors-a",):
            game = afoot_kit.settle(new_game(seed))
            for system in game.galaxy.systems[:16]:
                game.location_id = system.id
                for place in places.in_system(game, system):
                    if place.kind == "ship" or not places.livable(place):
                        continue
                    site = afoot_sites._from_place(game, place)
                    laid = afoot_plans.plan(game, site)
                    rooms = {r.venue: r.name for r in laid.rooms if r.venue}
                    for venue in shore.open_here(game, place):
                        doors += 1
                        if rooms.get(venue.id) != venue.name:
                            bad.append(f"{place.name}: {venue.name}")
                    seen += 1
        assert not bad, bad[:6]
        return f"{doors} doors over {seen} places, every one a room afoot"

    @check("a settlement is open to a sky it can breathe and sealed against one it cannot")
    def _():
        wants = [Want("works", f"Shed {n}", area=14, zone=0.5 - n / 10)
                 for n in range(8)]
        open_ = afoot_groundplan.settlement(RNG("s"), wants, "settlement",
                                            True)[0]
        sealed = afoot_groundplan.settlement(RNG("s"), wants, "settlement",
                                             False)[0]
        o_rows = "".join(open_.sheet.build(0, lambda: 0)[0])
        s_rows = "".join(sealed.sheet.build(0, lambda: 0)[0])
        assert open_.outside_air and GROUND in o_rows
        assert not sealed.outside_air and HALL in s_rows
        assert any(r.want is not None and r.want.kind == "hangar"
                   for r in sealed.sheet.regions), "no hangar on an airless pad"
        assert not _lost([open_, sealed])
        return ("breathable: open streets and a pad; airless: tubes, a "
                "landing hangar, vacuum outside")

    @check("every structural trait has a working space, and every space a kind of room")
    def _():
        traits = {t for c in COLONIES for t in traits_of(c)}
        missing = sorted(traits - set(programs.TRAIT_SPACE))
        assert not missing, f"traits with no working space: {missing}"
        kinds = {k for rows in programs.TRAIT_SPACE.values()
                 for k, *_r in rows}
        kinds |= {k for rows in programs.ROLE.values() for k, *_r in rows}
        kinds |= set(programs.ZONE) | set(programs.AREA)
        kinds |= {k for k, *_r in programs.STATION_CORE}
        kinds |= {w.kind for w in afoot_placeprog.gathering()}
        unknown = sorted(k for k in kinds if k not in ROOM_BY_ID)
        assert not unknown, f"spaces with no kind of room: {unknown}"
        return f"{len(traits)} traits, {len(kinds)} kinds of space, all furnished"


def _shaped(shape: str, names: list, painted: list, ground: bool) -> bool:
    """Is this plan the shape its class is built as?"""
    if shape == "drum":
        return "Inside the drum" in names and ground
    if shape == "tower":
        return len(painted) >= 2 and names[0] == "Skybridge level"
    if shape == "dome":
        return names[0] == "Under the dome" and ground and all(
            n.startswith("The galleries") for n in names[1:])
    if shape == "ring":
        return names[0] == "The hub" and len(names) >= 2 and all(
            n.startswith("The ring") and p.sheet.wrap and p.g > 0
            for n, p in zip(names[1:], painted[1:]))
    if shape == "ground":
        return len(painted) == 1 and _has_street(painted[0].sheet)
    return 1 <= len(painted) <= 3


def _decks_reached(laid) -> set:
    """Every deck a party coming aboard can reach, riding the lifts."""
    by_id = {t.id: t for t in laid.things}
    seen, todo = {laid.entry[0]}, [laid.entry[0]]
    while todo:
        deck = todo.pop()
        for t in laid.things:
            if t.kind == "lift" and t.deck == deck and t.link in by_id:
                there = by_id[t.link].deck
                if there not in seen:
                    seen.add(there)
                    todo.append(there)
    return seen


def _has_street(sheet) -> bool:
    return any(r.kind in ("hall", "ground") for r in sheet.regions)
