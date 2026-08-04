"""Where the ship is, and whether the whole game agrees about it.

The defect, measured at the opening of six seeds: every one of them puts a
Fleet Hub in orbit of body 0 and leaves `game.orbit_body` unset. `flight`'s
only answer for "unset" was a fixed point on the system's edge, so:

    the opening log        "The Ladon is under way from Fleet Hub."
    distance to Fleet Hub   645,000,000 km
    berthing.can_conn       "Fleet Hub is 4.31 AU off. The conn is for the
                             last few kilometres — plot a transfer to it first."

Every contact in the system, the home quay included, was hours of light away
from a captain who had not moved. That is why the conn opened on nothing and
its controls did nothing: they were correct, and the position was wrong.

So there is one door for the question now — `flight.ship_position` — and two
states behind it:

- **alongside a body**, where the position *is* the body's, worked out from
  the calendar every time it is asked. A copy kept in a field would be a
  second answer that goes stale the moment the clock moves;
- **free space**, `game.ship_xy`, written by `flight.stand_off`.

The claims:

- **A new captain is at their own quay**, and the conn opens on it.
- **Everything asks the same door.** Not "the numbers agree" — the same
  function, checked by moving the ship and watching every consumer follow.
- **A moored ship rides its orbit**, because the world takes it with it.
- **A jump stands off**, at the arrival radius, and says so in the state
  rather than in an assumption.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..data.starclasses import mu_of
from ..sim import anchorage as anchorage_sim
from ..sim import berthing
from ..sim import flight
from ..sim import track as track_sim
from .harness import Suite

#: Seeds flown here. Six chronicles rather than one, because the opening bug
#: was invisible in any single seed that happened to have no port.
SEEDS = ("a", "b", "conn", "helm-test", "budget", "silhouette")


def run(suite: Suite) -> None:
    check = suite.check

    @check("a new captain is moored at the quay they are leaving")
    def _():
        # The defect, in the words the game itself used. Measured before the
        # fix: 6 of 6 seeds refused the conn on their own home port.
        refused, moored = [], 0
        for seed in SEEDS:
            game = new_game(seed)
            body, _index = anchorage_sim.anchor_body(game.system)
            if body is None:
                continue
            moored += 1
            assert game.orbit_body == body.id, (
                f"{seed}: the log says under way from "
                f"{game.system.port.name} and the ship is alongside "
                f"{game.orbit_body!r}")
            home = next(c for c in track_sim.contacts(game)
                        if c.kind == "anchorage")
            ok, why = berthing.can_conn(game, home)
            if not ok:
                refused.append(f"{seed}: {why}")
        assert moored >= 4, f"only {moored} of {len(SEEDS)} seeds have a port"
        assert not refused, "\n".join(refused)
        return (f"{moored} chronicles, every one of them alongside its own "
                "quay with the conn open on it")

    @check("everything asks the same door for where the ship is")
    def _():
        # Not "the numbers agree" — the same function. Moved by the one writer
        # and every consumer read again: a second copy of the position kept
        # anywhere shows up here as a reader that did not move with it.
        game = new_game("one-door")
        quay = next((c for c in track_sim.contacts(game)
                     if c.kind == "anchorage"), None)
        assert quay is not None, "no anchorage in this system to measure to"
        # Two bodies, neither of them the one the quay is at, so the distance
        # to it is a real number at both ends.
        elsewhere = [b for i, b in enumerate(game.system.bodies)
                     if i != quay.body_index]
        near = min(elsewhere, key=flight.semi_major)
        far = max(elsewhere, key=flight.semi_major)
        readings = {}
        for body in (near, far):
            flight.hold_at(game, body)
            here = flight.ship_position(game)
            at = track_sim.at(game, quay, game.day)
            readings[body.id] = {
                "position": here,
                "reach": berthing.reach_to(game, quay),
                "by hand": math.dist(at, here),
            }
        # `reach_to` answers in km and the hand-worked figure in AU. What is
        # being asked is that they are the *same measurement*: if berthing kept
        # a position of its own the ratio would not survive moving the ship
        # across the system.
        ratios = [r["reach"] / r["by hand"] for r in readings.values()]
        assert min(ratios) > 0.0 and abs(ratios[0] - ratios[1]) < 1.0, (
            f"berthing and the chart disagree about the scale: {ratios}")
        moved = math.dist(readings[near.id]["position"],
                          readings[far.id]["position"])
        assert moved > 1.0, (
            f"the ship moved from the innermost orbit to the outermost and "
            f"the position changed by {moved:.3f} AU")
        assert readings[far.id]["reach"] != readings[near.id]["reach"], (
            "berthing did not notice the ship moving across the system")
        return (f"inner to outer orbit: {moved:.2f} AU, and berthing followed "
                f"({readings[near.id]['reach'] / 1e6:.0f} → "
                f"{readings[far.id]['reach'] / 1e6:.0f} million km) on one "
                "reading, not two")

    @check("a moored ship rides its orbit round the star")
    def _():
        # A hull alongside a world is in orbit, not parked at a fixed point.
        # Derived rather than stored for exactly this: a stored copy would say
        # the ship is where the body was on the day it moored, so a captain who
        # waits a month would wake up light-minutes off the quay they are tied
        # to — with the game insisting they are moored.
        game = new_game("riding")
        body = game.system.bodies[0]
        flight.hold_at(game, body)
        quay = next((c for c in track_sim.contacts(game)
                     if c.kind == "anchorage" and c.body_index == 0), None)
        start = flight.ship_position(game)
        game.advance_days(120)
        later = flight.ship_position(game)
        went = math.hypot(later[0] - start[0], later[1] - start[1])
        assert went > 0.05, (
            f"120 days alongside a body and the ship moved {went:.4f} AU — it "
            "is parked in space, not in orbit")
        with_body = flight.position(body, game.day, mu_of(game.system))
        drift = math.hypot(later[0] - with_body[0], later[1] - with_body[1])
        assert drift < 1e-9, (
            f"the ship is {drift:.4f} AU off the body it is moored to")
        if quay is not None:
            ok, why = berthing.can_conn(game, quay)
            assert ok, f"four months at the quay and the conn refuses it: {why}"
        return (f"120 days: the body swept {went:.2f} AU and took the ship "
                "with it, still at the quay")

    @check("a jump stands the ship off, and writes it down")
    def _():
        game = new_game("jumped")
        flight.hold_at(game, game.system.bodies[0])
        flight.arrive_in_system(game)
        assert game.orbit_body is None, "a jump left the ship alongside a body"
        out = math.hypot(*flight.ship_position(game))
        assert abs(out - flight.ARRIVAL_RADIUS) < 1e-9, (
            f"arrived {out:.2f} AU out against an arrival radius of "
            f"{flight.ARRIVAL_RADIUS:.2f}")
        # And a stand-off that is *given* a place holds that place, which is
        # what stops "alongside nothing" from meaning one particular point.
        # Two numbers in, three out: a place named on the plane is a place
        # at zero height, which is exactly where it used to be.
        flight.stand_off(game, (1.5, -2.5))
        assert flight.ship_position(game) == (1.5, -2.5, 0.0), (
            flight.ship_position(game))
        # And a place named with a height keeps it.
        flight.stand_off(game, (1.5, -2.5, 0.75))
        assert flight.ship_position(game) == (1.5, -2.5, 0.75), (
            flight.ship_position(game))
        # Mooring again drops the free-space position rather than leaving it
        # lying about for the next stand-off to pick up.
        flight.hold_at(game, game.system.bodies[1])
        assert game.ship_xy is None, (
            "mooring kept a free-space position, which is a second answer "
            "waiting to be believed")
        return (f"jump → {out:.2f} AU out; a placed stand-off holds its place; "
                "mooring clears it")

    @check("a save from before there was a position still knows where it is")
    def _():
        # `ship_xy` did not exist until this cycle, and a chronicle saved
        # before it must not open somewhere new. Both old states, restored by
        # hand as a loaded save presents them.
        game = new_game("old-save")
        body = game.system.bodies[-1]
        flight.hold_at(game, body)
        game.ship_xy = None                      # as an old save has it
        alongside = flight.ship_position(game)
        assert alongside == flight.position(body, game.day, mu_of(game.system))
        game.orbit_body = None
        adrift = flight.ship_position(game)
        assert abs(math.hypot(*adrift) - flight.ARRIVAL_RADIUS) < 1e-9, adrift
        return ("an old save moored reads its body; an old save adrift reads "
                f"the {flight.ARRIVAL_RADIUS:.2f} AU edge it always did")
