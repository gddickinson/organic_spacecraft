"""What a landing party crosses ground in, and what it costs to own one.

`Expedition.rover` was a number from nought to ten. Hazards knocked it down,
a day's work put it back, and it bought exactly one thing: a day off the
cost of a step while it stayed above eight. It was not a machine — no class,
no mass, no seats, no opinion about the nine terrains a party walks over —
so a dune sea and a scarp were the same problem to it, and a party that
owned nothing crossed them just as well.

And `data/careers.SKILLS` has carried **drive** — "anything with wheels or
tracks on a surface" — since the lifepath was written, read by nothing.

The claims:

- **A machine is a thing you own**: bought at a yard where its family's
  hulls are built, stowed in the hold, mended by the point and sold back at
  a loss, the way a craft is.
- **It rides down in the lander's hold against the supplies**, so what fits
  is a choice a captain makes rather than a thing that is simply there.
- **It has an opinion about ground**: a day off what it is made for, a day
  *on* what it refuses, because the party leaves it and walks.
- **Air is a rule**: a lift fan is dead weight where there is nothing to
  push against.
- **A party with nothing still walks**, which is the state the game shipped
  in.
- **What the ground does to it is kept**: wear by its own build, mended
  between landings, and left where it stopped if the party has to walk out.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.expedition import SUPPLY_LOADS, TERRAIN
from ..data.vehicles import VEHICLES, VEHICLES_BY_ID, WHOLE
from ..sim import (craft as craft_sim, descent, expedition as exp_sim,
                   fieldwork, garage, hangar, vehicles as veh)
from ..world.planets import BODY_KINDS
from .harness import Suite
from .quay import stand_at


def _with_ground(seed: str = "vehicles"):
    """A chronicle with something to stand on, surveyed, and money."""
    for n in range(12):
        game = new_game(f"{seed}-{n}")
        found = [i for i, b in enumerate(game.system.bodies)
                 if BODY_KINDS[b.kind][2]]
        if found:
            game.credits = 300_000
            for key in ("biomass", "alloy", "silicon"):
                game.stores[key] = 400.0
            game.ship.cargo["biomass"] = 80
            body = game.system.bodies[found[0]]
            body.surveyed = True
            stand_at(game, game.system)
            return game, found[0], body
    raise AssertionError("no landable body in twelve sectors")


def _lander(game):
    return next(c for c in craft_sim.aboard(game)
                if craft_sim.kind_of(c).role == "lander")


def run(suite: Suite) -> None:
    check = suite.check

    @check("a machine is a thing you own: built, stowed, mended and sold")
    def _():
        game, _index, _body = _with_ground("owning")
        held = veh.aboard(game)
        assert len(held) == 1 and veh.kind_of(held[0]).id == "rover", held
        assert held[0].condition == WHOLE and held[0].state == "stowed"
        money = game.credits
        got = garage.buy_vehicle(game, "crawler")
        assert got["ok"], got
        assert len(veh.aboard(game)) == 2
        assert money - game.credits >= got["paid"]
        # Worn, mended, and sold back at a loss.
        crawler = got["vehicle"]
        crawler.condition = 4
        quote = garage.vehicle_mend_cost(crawler)
        assert quote["credits"] == garage.VEHICLE_MEND * (WHOLE - 4)
        mended = garage.mend_vehicle(game, crawler)
        assert mended["ok"] and crawler.condition == WHOLE, mended
        paid = garage.sell_vehicle(game, crawler)["paid"]
        assert 0 < paid < VEHICLES_BY_ID["crawler"].cost["credits"]
        assert len(veh.aboard(game)) == 1
        return (f"a CRAWLER built for {got['paid']:,}, put right for "
                f"{quote['credits']:,} and sold back for {paid:,}")

    @check("it rides down in the lander's hold, against the supplies")
    def _():
        game, index, body = _with_ground("riding")
        pod = _lander(game)
        hold = craft_sim.kind_of(pod).hold_t
        rover = veh.aboard(game)[0]
        light = SUPPLY_LOADS[0][1]
        assert veh.can_take(game, rover, pod, body, light)[0]
        # A season's supplies leaves nothing to put it in.
        assert not veh.can_take(game, rover, pod, body, hold)[0]
        shut = veh.can_take(game, rover, pod, body, hold)[1]
        assert "hold left after the supplies" in shut, shut
        got = fieldwork.launch_expedition(game, index,
                                          [o.id for o in game.officers[:2]])
        assert got["ok"], got
        exp = game.expedition
        assert exp.vehicle == "rover" and exp.rover == WHOLE
        assert veh.on_the_ground(game) is rover
        assert rover.state == veh.DOWN
        return (f"a {veh.kind_of(rover).mass_t:g} t ROVER down in a "
                f"{hold:g} t hold beside {light} t of supplies")

    @check("a machine has an opinion about ground, and walking is the other one")
    def _():
        game, index, _body = _with_ground("ground")
        assert fieldwork.launch_expedition(
            game, index, [o.id for o in game.officers[:1]])["ok"]
        exp = game.expedition
        kind = VEHICLES_BY_ID[exp.vehicle]
        rows = {}
        for tid in sorted(TERRAIN):
            rows[tid] = (veh.ground(exp, tid), veh.step_change(exp, tid))
        for tid in kind.crosses:
            assert rows[tid] == ("good", -1), (tid, rows[tid])
        for tid in kind.refuses:
            assert rows[tid] == ("foot", 1), (tid, rows[tid])
        others = [t for t in TERRAIN
                  if t not in kind.crosses and t not in kind.refuses]
        assert all(rows[t] == ("ok", 0) for t in others), rows
        # And the step costs the sim charges move with it — measured
        # against the same tile on foot, so the weather is the same weather.
        made = [t for t in exp.tiles if t.terrain in kind.crosses
                and not t.visited]
        if made:
            drove = exp_sim.step_cost(exp, made[0])
            exp.vehicle = ""
            walked = exp_sim.step_cost(exp, made[0])
            exp.vehicle = kind.id
            assert drove <= walked, (drove, walked, made[0].terrain)
        # On foot is the other state, and it is allowed.
        exp.vehicle, exp.rover = "", 0
        assert veh.ground(exp, "scarp") == "foot"
        assert veh.step_change(exp, "scarp") == 0, "walking was charged twice"
        assert "On foot" in veh.says(exp)
        return (f"a {kind.name}: {len(kind.crosses)} terrains a day cheaper, "
                f"{len(kind.refuses)} a day dearer on foot, "
                f"{len(others)} unchanged")

    @check("a lift fan is dead weight where there is nothing to push against")
    def _():
        game, _index, body = _with_ground("air")
        pod = _lander(game)
        flyers = [k for k in VEHICLES if k.needs_air]
        assert flyers, "no vehicle claims to need air"
        for kind in flyers:
            held = veh.give(game, kind.id)
            ok, why = veh.can_take(game, held, pod, body, 0.0)
            if not veh.has_air(game, body):
                assert not ok and "air" in why, (kind.id, why)
            game.vehicles = [v for v in game.vehicles if v is not held]
        # The rule reads the world's own profile, so a thick atmosphere
        # takes one down.
        from ..sim import profile as profile_sim
        airy = next((b for b in game.system.bodies
                     if BODY_KINDS[b.kind][2]
                     and profile_sim.profile(game, game.system, b).atmosphere
                     >= veh.AIR_ENOUGH), None)
        held = veh.give(game, flyers[0].id)
        if airy is not None:
            assert veh.can_take(game, held, pod, airy, 0.0)[0]
        return (f"{len(flyers)} classes fly on air; {body.name} has "
                f"{'some' if veh.has_air(game, body) else 'none'}"
                + (f", {airy.name} has enough" if airy is not None else ""))

    @check("what the ground does to it is kept, and a stranded party walks out without it")
    def _():
        game, index, _body = _with_ground("wear")
        rover = veh.aboard(game)[0]
        assert fieldwork.launch_expedition(
            game, index, [o.id for o in game.officers[:1]])["ok"]
        exp = game.expedition
        # A machine that builds tougher takes less of the same toll.
        exp.vehicle = "crawler"
        tough = veh.wear(exp, 4)
        exp.vehicle = "kite"
        brittle = veh.wear(exp, 4)
        assert tough < brittle, (tough, brittle)
        exp.vehicle = rover.class_id
        exp.rover = 5
        exp.over, exp.outcome = True, "returned"
        fieldwork.conclude_expedition(game)
        assert rover.state == "stowed" and rover.condition == 5, rover
        assert garage.can_mend_vehicle(game, rover)[0]
        # And a party that walks out of the field leaves it where it stopped.
        assert fieldwork.launch_expedition(
            game, index, [o.id for o in game.officers[:1]])["ok"]
        game.expedition.over, game.expedition.outcome = True, "stranded"
        fieldwork.conclude_expedition(game)
        assert rover.state == "lost", rover.state
        assert veh.aboard(game) == [], "a machine left behind is still aboard"
        return (f"a CRAWLER takes {tough} of a 4-point toll where a KITE "
                f"takes {brittle}; a stranded party left the rover where it "
                "stopped")
