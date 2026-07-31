"""Structures you fly into, and berths you could not otherwise reach.

Measured before `sim/bays.py` existed, by planting one of every holding and
comparing where its berths sit against the sphere the approach treats as solid:
**seven of nineteen had berths inside it.** Flown rather than computed — a conn
opened on an ARCA Habitat and driven straight in reported

    ARCA Deepcut at 12 m/s — 3,995 m from mast 3. The frames took it.

The biggest structure in the sector could not be docked with, and nor could a
GRAVID Nursery, an Orbital Drydock, a Fabricator Yard, a Free Port, a LICHEN
Dome or a CORAL Reef.

Two claims come out of that, and they are the two halves of this file:

- **A bounding radius is not a hull.** `radius_km` is the size a structure is
  drawn at, furniture and all; what a ship can strike is the solid middle.
  A berth on a mast, a gantry or a ring is *supposed* to be inside the sphere.
- **Some structures are meant to be flown into.** A drum a million people live
  inside and a gestation shell that hands out finished hulls have their berths
  in the middle on purpose, and reaching one is a corridor through an aperture
  rather than a matter of tolerance. Miss the aperture and you are at the rim.

The claims:

- **Every holding in the game can be docked with**, which seven could not.
- **A bay's way in is narrower than its solid part**, or there is no rim to
  miss and the corridor means nothing — the first draft had a 3.2 km opening
  through a 2.7 km middle.
- **On the centreline you get inside**; off it you hit the structure.
- **A hull berths inside a gestation shell** — the whole of #108's last piece,
  flown through the sim.
- **One door**: the physics and the outcome ask the same question about what is
  solid, and they used to ask `radius_km` in two separate places.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..data import berths3d, works3d
from ..data.colonies import COLONIES
from ..sim import bays
from ..sim import colony as colony_sim
from ..sim import conn as conn_sim
from ..sim import moorings
from ..sim import targets as targets_sim
from ..sim import track as track_sim
from .harness import Suite


def _at(class_id, seed="bay"):
    """A game with one of these planted, and the target for it."""
    game = new_game(seed)
    body = game.system.bodies[1]
    game.colonies.append(colony_sim.Colony(
        id=1, class_id=class_id, name="Deepcut", system_id=game.system.id,
        body_id=body.id, need=0, online=True))
    contact = next(c for c in track_sim.contacts(game)
                   if c.kind == "anchorage" and c.berth == class_id)
    return game, targets_sim.target_from_contact(game, contact)


def _fly(class_id, off_bores: float, speed: float = 0.4, seed="bay-fly"):
    """Fly in along the aperture's axis, offset sideways by `off_bores`.

    Returns (conn, how close it ever got). The closest approach is the reading
    that matters: a hull that gets inside the solid radius without a strike is
    a hull that went through the way in.
    """
    game, target = _at(class_id, seed)
    conn = conn_sim.start(game, target)
    way = bays.axis(target, moorings.spin_of(conn))
    side = (-way[1], way[0], 0.0)
    length = math.dist(side, (0.0, 0.0, 0.0)) or 1.0
    side = tuple(c / length for c in side)
    bore = bays.bore_km(target)
    conn.pos = [way[i] * conn.range_km + side[i] * bore * off_bores
                for i in range(3)]
    conn.vel = [-way[i] * speed for i in range(3)]
    nearest = conn.range_km
    for _ in range(30_000):
        conn_sim.apply(conn, None, main=False, ticks=1)
        nearest = min(nearest, conn.range_km)
        if conn.over:
            break
    return conn, nearest


def run(suite: Suite) -> None:
    check = suite.check

    @check("every holding in the game can be docked with")
    def _():
        # The defect, as arithmetic over all nineteen. A berth inside the
        # solid part is a berth no approach can reach — unless the structure
        # is one you fly into, which is what the bay is for.
        stranded = []
        for klass in COLONIES:
            radius = works3d.size_km(klass.id)
            solid = radius * bays.CORE_SHARE
            points = berths3d.berth_points(klass.id)
            nearest = min(math.dist(at, (0.0, 0.0, 0.0))
                          for _n, at in points) * radius
            if nearest < solid and not bays.is_bay(klass.id):
                stranded.append((klass.id, round(nearest, 2), round(solid, 2)))
        assert not stranded, (
            f"berths inside a solid hull and no way in: {stranded}")
        # And the bays really are bays: their berths *are* inside.
        inside = [k.id for k in COLONIES if bays.is_bay(k.id)]
        assert inside, "no structure in the game can be flown into"
        for look in inside:
            _game, target = _at(look)
            assert bays.berths_inside(target), (
                f"{look} is called a bay and has no berth inside it")
        return (f"{len(COLONIES)} holdings, none stranded · {len(inside)} you "
                f"fly into: {', '.join(inside)}")

    @check("a way in is narrower than the thing it goes through")
    def _():
        # Measured on the first draft: a drum at 0.78 of its radius gave a
        # 3.2 km opening through a 2.7 km solid middle, so every off-axis
        # approach flew past the structure entirely and there was no rim.
        for klass in COLONIES:
            if not bays.is_bay(klass.id):
                continue
            _game, target = _at(klass.id)
            bore, solid = bays.bore_km(target), bays.hull_km(target)
            assert 0 < bore < solid, (
                f"{klass.id}: a {bore:.2f} km way in through a {solid:.2f} km "
                "hull is not a corridor")
        said = []
        for klass in COLONIES:
            if bays.is_bay(klass.id):
                _game, target = _at(klass.id)
                said.append(f"{klass.id} {bays.bore_km(target) * 2000:,.0f} m "
                            f"across a {bays.hull_km(target) * 2:,.2f} km hull")
        return " · ".join(said)

    @check("on the centreline you get inside; off it you hit the structure")
    def _():
        for look in [k.id for k in COLONIES if bays.is_bay(k.id)]:
            _game, target = _at(look)
            solid = bays.hull_km(target)
            straight, deepest = _fly(look, 0.0)
            assert deepest < solid, (
                f"{look}: flown down the middle the hull never got inside "
                f"{solid:.2f} km — closest was {deepest:.2f}")
            assert straight.outcome != "adrift", (
                f"{look}: flying at the way in lost the structure entirely")
            # Just outside the bore and well inside the skin: that is the rim.
            rim, _near = _fly(look, 1.15, seed="rim")
            assert rim.outcome == "collision", (
                f"{look}: a hull 1.15 bores off the axis came away with "
                f"{rim.outcome!r} rather than hitting the rim")
        return "both bays let a hull down the middle and stop one off it"

    @check("a hull berths inside a gestation shell")
    def _():
        # The whole of #108's last piece, flown: through the aperture, and
        # made fast to a cradle that sits *within* the structure.
        held, _near = _fly("gravid_nursery", 0.0, speed=0.4, seed="womb")
        assert held.outcome == "alongside", (
            f"the approach ended {held.outcome!r}: "
            + (held.log[-1] if held.log else ""))
        assert held.berth, "alongside nothing in particular"
        _game, target = _at("gravid_nursery")
        inside = {name for name, _at_ in bays.berths_inside(target)}
        assert held.berth in inside, (
            f"berthed at {held.berth!r}, which is not one of the inside "
            f"berths {sorted(inside)}")
        assert held.range_km < bays.hull_km(target), (
            f"made fast {held.range_km:.3f} km out, which is not inside")
        return (f"through a {bays.bore_km(target) * 2000:,.0f} m mouth and "
                f"made fast at {held.berth}, {held.range_km * 1000:,.0f} m "
                f"from the middle: {held.log[-1]}")

    @check("a structure you fly into says so, and says how")
    def _():
        # The gap this closes: ARCA's berths are on the inner wall of a drum,
        # so berthing means flying the centreline, checking up, and crossing
        # to the wall — carry on down the middle and you strike the far end.
        # The physics did that from the day the bays landed and no screen said
        # a word about it.
        from ..sim import clearance as clearance_sim
        for look in [k.id for k in COLONIES if bays.is_bay(k.id)]:
            game, target = _at(look, seed=f"say-{look}")
            contact = next(c for c in track_sim.contacts(game)
                           if c.kind == "anchorage" and c.berth == look)
            conn = conn_sim.start(game, target)
            said = clearance_sim.request(game, contact, conn)
            assert said.granted, said.why
            assert said.sort == "bay", said.sort
            assert abs(said.bore_km - bays.bore_km(target)) < 1e-9
            told = clearance_sim.line(said)
            assert "inside" in told, told
            assert "centreline" in told, told
            # The width on the screen is the width in the sim.
            assert f"{bays.bore_km(target) * 2000:,.0f} m" in told, told
        # And a structure with no way in says nothing of the kind.
        game, port = _at("free_port", seed="say-port")
        contact = next(c for c in track_sim.contacts(game)
                       if c.kind == "anchorage" and c.berth == "free_port")
        plain = clearance_sim.request(game, contact,
                                      conn_sim.start(game, port))
        assert plain.sort != "bay" and plain.bore_km == 0.0
        assert "centreline" not in clearance_sim.line(plain)
        return told

    @check("the physics and the outcome agree about what is solid")
    def _():
        # It was asked in two places — `sim/conn`'s swept-path test and
        # `sim/outcome`'s arrival test — and both read `radius_km`, the
        # bounding sphere. `bays.hull_km` is the one door.
        _game, target = _at("free_port")
        solid = bays.hull_km(target)
        assert solid < target.radius_km, (solid, target.radius_km)
        # A world is left alone: a planet is solid to its radius.
        body = _game.system.bodies[1]
        world = targets_sim.target_from_body(body, body.name, 1)
        assert bays.hull_km(world) == world.radius_km, "a world grew a bay"
        # And a structure with no way in is solid everywhere: no corridor.
        game, port = _at("free_port", seed="solid")
        conn = conn_sim.start(game, port)
        conn.pos = [0.0, -0.01, 0.0]
        assert not bays.in_corridor(conn, moorings.spin_of(conn)), (
            "a Free Port has no aperture and something found one")
        return (f"{target.name}: drawn at {target.radius_km:.2f} km, solid to "
                f"{solid:.2f}, and a world still solid to its own radius")
