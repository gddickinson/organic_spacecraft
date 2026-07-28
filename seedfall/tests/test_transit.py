"""Transit checks — a crossing you fly rather than wait out.

Flying somewhere was: pick a destination, pay the reaction mass, watch the
calendar move. The helm could plot an intercept and route around a star and
then had nothing to do for eleven days.

These hold the watches to actually costing something, and to the three
resources a crossing spends — time, reaction mass, hull — being genuinely in
tension rather than one option being quietly best.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.watches import EVENT_CHANCE, WATCHES, watches_for
from ..sim import transit as transit_sim
from ..sim.ship import hull_pct
from .harness import Suite


def _setup(seed: str, fuel: float = 120.0):
    game = new_game(seed)
    game.ship.cargo = {"volatiles": fuel}
    index = max(range(len(game.system.bodies)),
                key=lambda i: game.system.bodies[i].orbit)
    return game, index


def _fly(seed: str, policy: str = "safe", limit: int = 30):
    game, index = _setup(seed)
    started = transit_sim.begin(game, index, "standard")
    assert started["ok"], started.get("why")
    crossing = started["transit"]
    rng = RNG(f"watch-{seed}")
    guard = 0
    while not crossing.over and guard < limit:
        guard += 1
        if crossing.event:
            choices = transit_sim.options(crossing)
            if policy == "fast":
                pick = min(choices, key=lambda o: (o.days, o.fuel))
            else:
                pick = min(choices, key=lambda o: (o.risk, o.damage))
            transit_sim.choose(game, crossing, pick.id, rng)
        else:
            transit_sim.stand(game, crossing, rng)
    return game, crossing


def run(suite: Suite) -> None:
    check = suite.check

    @check("every watch is legible and every option costs something")
    def _():
        for watch in WATCHES:
            assert watch.text and watch.name, f"{watch.id} says nothing"
            assert len(watch.options) >= 2, f"{watch.id} is not a choice"
            ids = [o.id for o in watch.options]
            assert len(set(ids)) == len(ids), f"{watch.id} repeats an option id"
            for option in watch.options:
                assert option.label and option.blurb, (
                    f"{watch.id}/{option.id} says nothing")
                spends = (option.days or option.fuel or option.damage
                          or option.heat or option.risk)
                gains = option.salvage or option.research
                assert spends or gains, (
                    f"{watch.id}/{option.id} costs nothing and is worth nothing")
                if option.risk:
                    assert option.risk_text, (
                        f"{watch.id}/{option.id} can go wrong and never says how")
        assert 0 < EVENT_CHANCE < 1, "watches are certain or impossible"
        assert watches_for(2) >= 1 and watches_for(40) > watches_for(4), (
            "a long crossing is not divided into more watches than a short one")
        return f"{len(WATCHES)} watches, {sum(len(w.options) for w in WATCHES)} options"

    @check("a crossing flown to the end puts you alongside")
    def _():
        game, crossing = _fly("arrive")
        assert crossing.over, "the crossing never finished"
        assert crossing.outcome == "arrived", f"ended {crossing.outcome!r}"
        body = game.system.bodies[crossing.body_index]
        assert game.orbit_body == body.id, "arrived without being in orbit"
        assert crossing.days_spent > 0 and crossing.fuel_spent > 0, (
            "a crossing that cost nothing")
        assert crossing.stood == crossing.watches, (
            f"arrived after {crossing.stood} of {crossing.watches} watches")
        return (f"{crossing.watches} watches, {crossing.days_spent} days, "
                f"{crossing.fuel_spent:.0f} t")

    @check("cutting the burn leaves you where you were, minus the mass")
    def _():
        game, index = _setup("abort")
        before_body = game.orbit_body
        before_fuel = game.ship.cargo.get("volatiles", 0)
        started = transit_sim.begin(game, index, "standard")
        crossing = started["transit"]
        rng = RNG("abort")
        transit_sim.stand(game, crossing, rng)
        if crossing.event:
            transit_sim.choose(game, crossing,
                               transit_sim.options(crossing)[0].id, rng)
        spent = crossing.fuel_spent
        transit_sim.abort(game, crossing)

        assert crossing.over and crossing.outcome == "aborted"
        assert game.orbit_body == before_body, "aborting still moved the ship"
        assert spent > 0, "half a crossing cost no mass at all"
        assert game.ship.cargo.get("volatiles", 0) < before_fuel, (
            "the mass burned came back")
        return f"turned back after {crossing.days_spent} days and {spent:.0f} t"

    @check("time, mass and hull are genuinely in tension")
    def _():
        # If one policy were best on every axis the watches would be a formality.
        fast_days = fast_hull = 0.0
        safe_days = safe_hull = 0.0
        runs = 24
        for index in range(runs):
            game, crossing = _fly(f"tension-{index}", "fast")
            fast_days += crossing.days_spent
            fast_hull += 1.0 - hull_pct(game.ship)
            game, crossing = _fly(f"tension-{index}", "safe")
            safe_days += crossing.days_spent
            safe_hull += 1.0 - hull_pct(game.ship)

        assert fast_days < safe_days, (
            f"hurrying saved no time: {fast_days / runs:.1f} against "
            f"{safe_days / runs:.1f} days")
        assert fast_hull > safe_hull, (
            f"hurrying cost no hull: {fast_hull / runs:.1%} against "
            f"{safe_hull / runs:.1%}")
        return (f"fast {fast_days / runs:.1f} d / {fast_hull / runs:.1%} hull · "
                f"safe {safe_days / runs:.1f} d / {safe_hull / runs:.1%} hull")

    @check("every watch can actually come up")
    def _():
        seen = set()
        for index in range(90):
            game, index_body = _setup(f"reach-{index}")
            started = transit_sim.begin(game, index_body, "coast")
            crossing = started["transit"]
            rng = RNG(f"reach-{index}")
            guard = 0
            while not crossing.over and guard < 30:
                guard += 1
                if crossing.event:
                    seen.add(crossing.event)
                    transit_sim.choose(game, crossing,
                                       transit_sim.options(crossing)[0].id, rng)
                else:
                    transit_sim.stand(game, crossing, rng)
        # The star-flare watch only fires on a leg that runs in close.
        expected = {w.id for w in WATCHES if not w.hot_only}
        missing = expected - seen
        assert not missing, f"watches that never came up in 90 crossings: {missing}"
        return f"{len(seen)} of {len(WATCHES)} watches seen across 90 crossings"

    @check("a crossing survives a save and reload")
    def _():
        import json

        from ..core.save import decode, encode

        game, index = _setup("persist-transit")
        started = transit_sim.begin(game, index, "standard")
        crossing = started["transit"]
        game.transit = crossing        # persisted like any other state
        rng = RNG("persist")
        transit_sim.stand(game, crossing, rng)
        before = (crossing.stood, crossing.days_spent,
                  round(crossing.fuel_spent, 3), crossing.event)

        back = decode(json.loads(json.dumps(encode(game))))
        got = back.transit
        assert got is not None, "the crossing was lost"
        after = (got.stood, got.days_spent, round(got.fuel_spent, 3), got.event)
        assert after == before, f"{after} != {before}"
        assert transit_sim.options(got) == transit_sim.options(crossing), (
            "the watch came back offering different choices")
        return f"watch {got.stood}/{got.watches} came back intact"
