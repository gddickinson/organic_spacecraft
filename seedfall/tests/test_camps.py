"""What a landing party pitches when it means to stay.

An expedition is a supply clock: days come down in the lander's hold, every
step spends them, and a party that runs out walks home with what is on its
backs and leaves the rest. The only building on the map was the lander, and
the only place the clock could be refilled was orbit — so every landing was
one outward walk and one walk back, and the shape of a survey was a star.

A camp is the second building. The claims:

- **It comes down in the same hold**, after the supplies and the vehicle,
  so what fits is the third leg of one decision.
- **It holds days**, and a party that walks back into its own camp picks
  them up again — which is what makes a route out of a star.
- **It sits out weather for nothing**: the day goes, the stores do not.
- **A day's rest inside is worth more** than a day on regolith.
- **What is left in it is left**: the camp comes up with the lander, the
  days inside it do not.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.camps import CAMPS, CAMPS_BY_ID, PITCH_DAYS
from ..sim import camps, expedition as exp_sim, fieldwork, garage
from ..world.planets import BODY_KINDS
from .harness import Suite
from .quay import stand_at


def _down(seed: str = "camps"):
    """A party on the ground with what the hull sails with."""
    for n in range(12):
        game = new_game(f"{seed}-{n}")
        found = [i for i, b in enumerate(game.system.bodies)
                 if BODY_KINDS[b.kind][2]]
        if not found:
            continue
        game.credits = 300_000
        for key in ("biomass", "alloy", "silicon"):
            game.stores[key] = 400.0
        game.ship.cargo["biomass"] = 80
        stand_at(game, game.system)
        index = found[0]
        game.system.bodies[index].surveyed = True
        got = fieldwork.launch_expedition(game, index,
                                          [o.id for o in game.officers[:2]])
        assert got["ok"], got
        return game, index, game.expedition
    raise AssertionError("no landable body in twelve sectors")


def run(suite: Suite) -> None:
    check = suite.check

    @check("a camp comes down after the supplies and the vehicle")
    def _():
        game, _index, exp = _down("carried")
        assert exp.camp, "nothing came down to pitch"
        kind = camps.kind_for(exp)
        assert kind is not None and camps.down(game) is not None
        assert not camps.is_up(exp), "it arrived already pitched"
        # It is the third thing in the hold, and the hold is finite.
        from ..sim import craft as craft_sim, vehicles as veh
        pod = next(c for c in craft_sim.aboard(game)
                   if craft_sim.kind_of(c).role == "lander")
        hold = craft_sim.kind_of(pod).hold_t
        ride = veh.on_the_ground(game)
        used = kind.mass_t + (veh.kind_of(ride).mass_t if ride else 0.0)
        assert used <= hold, (used, hold)
        # Nothing that will not fit comes down: a field station is too big
        # beside a season's supplies.
        big = max(CAMPS, key=lambda c: c.mass_t)
        assert camps.best_for(game, pod, big.mass_t - 0.1) is None
        return (f"a {kind.name} of {kind.mass_t:g} t down beside "
                f"{'a ' + veh.kind_of(ride).name if ride else 'nothing'} in "
                f"a {hold:g} t hold")

    @check("it holds days, and a party that walks back into it picks them up")
    def _():
        game, _index, exp = _down("holding")
        kind = camps.kind_for(exp)
        had = exp.supply
        got = camps.pitch(exp, days=5)
        assert got["ok"] and got["left"] == 5, got
        assert exp.supply == had - 5 - PITCH_DAYS, (exp.supply, had)
        assert camps.at_camp(exp) and camps.is_up(exp)
        # Walk away and it is not theirs to spend.
        exp.x, exp.y = exp.x + 1, exp.y
        assert not camps.at_camp(exp)
        assert not camps.draw(exp)["ok"]
        assert "not in the camp" in camps.draw(exp)["why"]
        # Walk back and it is.
        exp.x, exp.y = exp.camp_x, exp.camp_y
        back = camps.draw(exp, 3)
        assert back["ok"] and back["took"] == 3
        assert exp.camp_supply == 2 and exp.supply == had - 2 - PITCH_DAYS
        # Struck, the rest comes with them.
        struck = camps.strike(exp)
        assert struck["ok"] and struck["took"] == 2
        assert not camps.is_up(exp) and exp.supply == had - PITCH_DAYS
        return (f"a {kind.name} took 5 days, gave 3 back on the way through "
                f"and the last 2 when it was struck; it holds {kind.holds}")

    @check("weather costs the day and not the stores, under a roof")
    def _():
        game, _index, exp = _down("weather")
        assert camps.pitch(exp, days=0)["ok"]
        # Out in it: the day and the stores.
        exp.x = exp.camp_x + 1
        was, days = exp.supply, exp.days
        exp_sim.shelter(exp, game.rng("w"))
        outside = was - exp.supply
        assert exp.days > days, "sitting it out cost no time"
        # Back inside it: the day, and not the stores.
        exp.x = exp.camp_x
        was, days = exp.supply, exp.days
        exp_sim.shelter(exp, game.rng("w"))
        inside = was - exp.supply
        assert exp.days > days, "sitting it out cost no time"
        assert outside >= 1 and inside == 0, (outside, inside)
        assert any("kept the stores" in text for _t, text, _k in exp.log)
        return (f"a day out in it costs {outside} of supply; the same day "
                f"in the camp costs {inside}")

    @check("a day's rest inside is worth more than a day on regolith")
    def _():
        game, _index, exp = _down("resting")
        assert camps.pitch(exp, days=0)["ok"]
        party = [o for o in game.officers]
        # Outside.
        exp.x = exp.camp_x + 1
        exp.rover = 2
        exp_sim.rest(exp, party, game.rng("r"))
        outside = exp.rover - 2
        # Inside.
        exp.x = exp.camp_x
        exp.rover = 2
        exp_sim.rest(exp, party, game.rng("r"))
        inside = exp.rover - 2
        assert camps.rest_worth(exp) > 1.0
        assert inside >= outside, (inside, outside)
        return (f"{outside} points of the machine put back in the open "
                f"against {inside} in a {camps.kind_for(exp).name}")

    @check("what is left in it is left, and the camp itself comes up")
    def _():
        game, index, exp = _down("leaving")
        held = camps.down(game)
        assert camps.pitch(exp, days=6)["ok"]
        exp.over, exp.outcome = True, "returned"
        out = fieldwork.conclude_expedition(game)
        assert out["ok"], out
        assert held.state == "stowed", held.state
        assert camps.down(game) is None
        assert any("left in the camp" in text for _d, text, _k in game.log)
        # And the yard will sell you a better one.
        offers = {row["kind"].id: row for row in garage.camp_offers(game)}
        assert len(offers) == len(CAMPS)
        station = offers["station"]
        if station["ok"]:
            bought = garage.buy_camp(game, "station")
            assert bought["ok"], bought
            assert CAMPS_BY_ID["station"].holds > camps.kind_for(exp).holds
        return ("six days left behind in a struck camp; the yard sells a "
                f"field station that holds {CAMPS_BY_ID['station'].holds}")
