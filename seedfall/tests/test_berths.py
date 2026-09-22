"""Docking, every shape of berth and every way in: flown, towed, or refused.

A player asked for every docking variation to be tried and fixed. So every
sort of berth in the game — a quay, a Fleet Hub, a bonded holding, a base's
pad, and each of the twenty-one classes a holding can be built as — is flown
at from all round and from above, by two very different hulls, with the
harbour's boats and without them.

- **she gets alongside**, whatever the shape and whatever the bearing: round
  a free port's one sideways arm, in through a drum's mouth and a gestation
  shell's, onto a slip's cradles;
- **a berth refuses a hull too big for it** (`moorings.takes`) — a 990 m
  LEVIATHAN is not tying up to a 400 m quay, and its people come across by
  boat (`sim/crossing`) instead;
- **the boats belong to the structure** (`tug.has_tug`): a drum with a town
  in it keeps a tender whatever the system's port is, and a Weave gate keeps
  none;
- **the boats cast off at a bay's mouth**, where a tow would otherwise walk
  her in and straight back out again;
- **a tow costs nothing**: what the boats do, the thrusters do not pay for.
"""

from __future__ import annotations

import dataclasses
import math

from ..core.rng import RNG
from ..core.state import new_game
from ..data import berths3d, works3d
from ..data.chassis import CHASSIS_BY_ID
from ..sim import (afoot_program, autopilot, bays, berthing, clearance,
                   conn as conn_sim, crossing, flight, moorings, places,
                   targets, track, tug)
from ..sim.ship import build_layers, make_ship
from .harness import Suite

#: Every shape a berth is drawn as, bar the Weave gate, which nobody moors to.
LOOKS = [look for look in list(berths3d.BERTHS) + list(works3d.WORKS)
         if look != "gate"]
#: Bearings flown from, as a share of a turn round the berth's own line: the
#: far side first, then the quarters, and one from over the top.
BEARINGS = (0.0, 0.25, 0.5, 0.75)
#: How far off an approach opens, in km, and how many ticks it may take.
OPENS_KM, TICKS = 12.0, 8000


def _game(ship_id: str = "navis"):
    game = new_game("docking")
    chassis = CHASSIS_BY_ID[ship_id]
    ship = make_ship(ship_id, afoot_program.typical_fit(RNG("dock"), chassis),
                     "Probe")
    build_layers(ship)
    ship.cargo["volatiles"] = 400.0
    game.ship = ship
    game.recompute()
    flight.hold_at(game, flight.current_body(game))
    return game


def _contact(game, look: str):
    """The home quay's berth, drawn as any structure in the game."""
    hub = next(c for c in track.contacts(game) if c.kind == "anchorage"
               and c.name == game.system.port.name)
    return dataclasses.replace(hub, berth=look, name=f"The {look}")


def _fly(game, contact, share: float, boats: bool = True, up: bool = False):
    """Open an approach from one bearing and hand it to the computer."""
    conn, why = berthing.begin(game, contact)
    if conn is None:
        return None, why
    if not boats and conn.cleared is not None:
        conn.cleared = dataclasses.replace(conn.cleared, tug=False)
    spots = moorings.points(conn.target)
    at = spots[0][1] if spots else (1.0, 0.0, 0.0)
    out = math.hypot(at[0], at[1]) or 1.0
    x, y = at[0] / out, at[1] / out
    turn = math.pi + share * math.tau
    conn.pos = ([0.0, 0.0, OPENS_KM] if up else
                [OPENS_KM * (x * math.cos(turn) - y * math.sin(turn)),
                 OPENS_KM * (x * math.sin(turn) + y * math.cos(turn)), 0.0])
    conn.vel = [0.0, 0.0, 0.0]
    autopilot.fly(conn, "close", TICKS)
    game.docking = game.conn = None
    return conn, ""


def run(suite: Suite) -> None:
    check = suite.check

    @check("every shape of berth can be flown alongside, from every bearing and from above")
    def _():
        bad, flown, spent = [], 0, []
        for ship_id in ("navis", "spore"):
            game = _game(ship_id)
            for look in LOOKS:
                contact = _contact(game, look)
                for share in BEARINGS:
                    for up in (False, True) if share == 0.0 else (False,):
                        conn, why = _fly(game, contact, share, up=up)
                        if conn is None:
                            bad.append(f"{look}/{ship_id}: {why[:40]}")
                            continue
                        flown += 1
                        if conn.outcome != "alongside":
                            bad.append(
                                f"{look}/{ship_id}/{share:.2f}"
                                f"{'/up' if up else ''}: {conn.outcome} at "
                                f"{conn.range_km:.2f} km")
                        else:
                            spent.append(conn.opening_rcs - conn.rcs)
        assert not bad, f"{len(bad)} of {flown}: {bad[:5]}"
        return (f"{flown} approaches over {len(LOOKS)} shapes of berth, two "
                f"hulls, every bearing: all alongside, "
                f"{sum(spent) / len(spent):.2f} t of reaction mass each")

    @check("a berth refuses a hull too big for it, and the boats bring the crew across")
    def _():
        game = _game("leviathan")
        long_km = 0.99                       # a LEVIATHAN is 990 m of hull
        quay = _contact(game, "quay")
        said = clearance.request(game, quay)
        assert not said.granted and "hull" in said.why, said
        target = targets.target_from_contact(game, quay)
        assert not moorings.takes(target, long_km)
        conn, why = _fly(game, quay, 0.0)
        assert conn is None and "hull" in why, why
        # And the people still get in: their shuttle meets her in orbit.
        place = next(p for p in places.here(game) if p.kind == "port")
        ways = {w.id: w for w in crossing.ways(game, place)}
        assert ways["shuttle"].ok and not ways["dock"].ok, ways
        assert "hull" in ways["dock"].why, ways["dock"].why
        # A hull that fits is cleared at the same quay.
        small = _game("spore")
        assert clearance.request(small, _contact(small, "quay")).granted
        return (f"990 m of hull refused by a berth that runs to "
                f"{moorings.span_km(target) * 1000:,.0f} m; her people cross "
                "by shuttle")

    @check("the boats belong to the structure, not to the system's port")
    def _():
        game = _game()
        drum = _contact(game, "arca_drum")
        gate = dataclasses.replace(_contact(game, "gate"), berth="gate")
        quay = _contact(game, "quay")
        assert tug.has_tug(game, drum), "a drum with a town in it has no boats"
        assert not tug.has_tug(game, gate), "a Weave gate keeps boats"
        object.__setattr__(game.system.port, "level", 1)
        assert not tug.has_tug(game, quay), "a wayside quay keeps boats"
        assert tug.has_tug(game, drum), "the drum's boats were the port's"
        return (f"a drum keeps boats at any port; a quay from level "
                f"{tug.TUG_FROM}; a gate never")

    @check("a hull that stops asking is walked in for nothing, and having boats never costs more")
    def _():
        # Stand off at the corridor and burn nothing at all: the boats come
        # out, get a line on her, and walk her alongside on their own mass.
        game = _game()
        conn, why = berthing.begin(game, _contact(game, "hub"))
        assert conn is not None, why
        at = moorings.aim(conn)
        out = math.dist(at, (0.0, 0.0, 0.0)) or 1.0
        conn.pos = [c * moorings.corridor_km(conn.target) * 1.4 / out
                    for c in at]
        conn.vel = [0.0, 0.0, 0.0]
        held = conn.rcs
        for _ in range(4000):
            if conn.over:
                break
            conn_sim.apply(conn, None, main=False)
        assert conn.outcome == "alongside", (conn.outcome, conn.range_km)
        assert conn.towed > 0.0 and held == conn.rcs, (conn.towed, held)
        waited = conn.elapsed / 3600.0
        game.docking = game.conn = None
        # And a harbour with boats never costs a hull that flies herself:
        # the tow lets go the moment she is under power.
        worse = []
        for look in ("quay", "hub", "free_port", "fab_yard", "holding",
                     "field", "arca_drum", "gravid_nursery"):
            with_boats, _why = _fly(game, _contact(game, look), 0.25)
            alone, _why = _fly(game, _contact(game, look), 0.25, boats=False)
            for got in (with_boats, alone):
                assert got.outcome == "alongside", (look, got.outcome)
            if with_boats.opening_rcs - with_boats.rcs > \
                    alone.opening_rcs - alone.rcs + 0.01:
                worse.append(look)
        assert not worse, f"boats made these dearer: {worse}"
        return (f"walked alongside in {waited * 60:.0f} minutes for no mass "
                "at all; eight shapes of berth no dearer for having boats")

    @check("the way round a structure is the smallest turn that clears it")
    def _():
        game = _game()
        port = _contact(game, "free_port")
        conn, _why = _fly(game, port, 0.0)          # the far side from the arm
        assert conn.outcome == "alongside", (conn.outcome, conn.range_km)
        core = bays.hull_km(conn.target)
        assert conn.range_km > core, conn.range_km
        # The aim never asks her to fly through the middle.
        conn2, _why = _fly(game, port, 0.5)
        assert conn2.outcome == "alongside", conn2.outcome
        return (f"a free port's arm reached from either side, clear of "
                f"{core * 1000:,.0f} m of solid hull")
