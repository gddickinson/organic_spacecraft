"""Burn checks — the four profiles have to be a decision.

Measured before any of this: flying a system end to end took 55 days coasting
and 10 on a hard burn, and the hard burn cost about three hundred credits of
reaction mass and 1.2% of a hull that heals itself. Nobody would ever have
coasted. The hard burn's own blurb promised that "the crew will feel it and the
radiators will complain", and neither happened — a burn never touched heat.

Heat, meanwhile, was a one-way ratchet: nothing outside combat added it and
nothing shed it, so a ship sat at thirty for twelve hundred days with radiators
rated at twenty-four a turn.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import flight
from ..sim.ship import cool, hull_pct
from .harness import Suite


def _fuelled(seed: str, heat: float = 0.0):
    game = new_game(seed)
    game.ship.cargo = {"volatiles": 600}
    game.ship.heat = heat
    return game


def _tour(seed: str, burn_id: str, rest: int = 30) -> dict:
    """Fly every body in the home system on one profile, then sit a month."""
    game = _fuelled(seed)
    start_day, start_hull = game.day, hull_pct(game.ship)
    incidents = fuel = 0
    for index in range(1, len(game.system.bodies)):
        result = flight.travel_to(game, index, burn_id)
        if not result.get("ok") or result.get("dead"):
            break
        incidents += 1 if result.get("incident") else 0
        fuel += result.get("fuel", 0)
    game.advance_days(rest)
    return {"days": game.day - start_day, "fuel": fuel,
            "incidents": incidents, "heat": game.ship.heat,
            "hull": start_hull - hull_pct(game.ship)}


def run(suite: Suite) -> None:
    check = suite.check

    @check("the radiators work when nobody is shooting")
    def _():
        # They did not. Heat was added only by a flight incident and shed only
        # by a combat turn, so it followed you around indefinitely.
        game = _fuelled("shed", heat=40.0)
        cap = game.ship_stats.heat_cap
        assert game.ship.heat < cap, "the fixture starts over the cap"
        game.advance_days(1)
        after_a_day = game.ship.heat
        assert after_a_day < 40.0, "a day at rest shed nothing"
        game.advance_days(120)
        assert game.ship.heat == 0.0, (
            f"still at {game.ship.heat:.1f} after four months")
        return f"40 → {after_a_day:.1f} in a day → nothing in four months"

    @check("a burn puts heat in the hull, in proportion")
    def _():
        got = {}
        for burn in flight.BURNS:
            game = _fuelled(f"heat-{burn.id}")
            index = len(game.system.bodies) - 1
            result = flight.travel_to(game, index, burn.id)
            assert result["ok"], result.get("why")
            got[burn.id] = game.ship.heat
        assert got["coast"] == 0, "coasting heats the hull"
        assert got["hard"] > got["standard"] > got["economy"] > 0, (
            f"not monotone with the profile: {got}")
        cap = new_game("heat-coast").ship_stats.heat_cap
        assert got["hard"] > cap * 0.4, (
            f"a hard burn arrives at {got['hard']:.0f} of a {cap:.0f} cap, "
            "which nobody would notice")
        return " · ".join(f"{k} {v:.0f}" for k, v in got.items())

    @check("over the cap the hull cooks, under it nothing happens")
    def _():
        cold = _fuelled("cook-cold", heat=0.0)
        before = hull_pct(cold.ship)
        cold.advance_days(60)
        assert hull_pct(cold.ship) >= before - 0.0001, (
            "a cold hull lost integrity sitting still")

        hot = _fuelled("cook-hot")
        cap = hot.ship_stats.heat_cap
        hot.ship.heat = cap * 2
        start = hull_pct(hot.ship)
        out = cool(hot.ship, hot.ship_stats, 1)
        assert out["cooked"] > 0, "over the cap and nothing cooked"
        hot.advance_days(60)
        assert hull_pct(hot.ship) < start, "a hull at twice the cap took nothing"
        return (f"cold hull untouched; at {cap * 2:.0f} of {cap:.0f} it cooks "
                f"{out['cooked']:.1f} a day")

    @check("burning hard is faster and it costs you")
    def _():
        # The decision. Before this, a hard burn saved nineteen days for three
        # hundred credits and 1.2% of a self-healing hull.
        runs = {b.id: [] for b in flight.BURNS}
        for index in range(20):
            for burn in flight.BURNS:
                runs[burn.id].append(_tour(f"tour-{index}", burn.id))

        def mean(bid, key):
            rows = runs[bid]
            return sum(r[key] for r in rows) / len(rows)

        assert mean("hard", "days") < mean("coast", "days") * 0.7, (
            "a hard burn is not appreciably faster")
        assert mean("hard", "hull") > mean("economy", "hull") + 0.02, (
            f"burning hard costs {mean('hard', 'hull'):.1%} of the hull "
            f"against {mean('economy', 'hull'):.1%} — no reason not to")
        assert mean("hard", "incidents") > mean("economy", "incidents") * 1.5, (
            "a hard burn is no likelier to go wrong")
        assert mean("coast", "fuel") == 0, "coasting is not free"
        return " · ".join(
            f"{b.id} {mean(b.id, 'days'):.0f}d/{mean(b.id, 'fuel'):.0f}t/"
            f"{mean(b.id, 'hull'):.0%} hull" for b in flight.BURNS)

    @check("a single hard burn is not punished, a habit is")
    def _():
        # Arriving hot once is free; the cost is not letting it shed.
        once = _fuelled("once")
        index = len(once.system.bodies) - 1
        before = hull_pct(once.ship)
        flight.travel_to(once, index, "hard")
        assert once.ship.heat <= once.ship_stats.heat_cap, (
            "one hard burn from cold already puts you over the cap")
        once.advance_days(30)
        assert hull_pct(once.ship) >= before - 0.0001, (
            "one hard burn cooked the hull")
        return "one burn from cold arrives under the cap and costs nothing"

    @check("what the helm says you will arrive at is what happens")
    def _():
        # The panel prints `heat + burn.heat * cap`. It has to be the truth.
        for burn in flight.BURNS:
            game = _fuelled(f"quote-{burn.id}", heat=10.0)
            cap = game.ship_stats.heat_cap
            index = len(game.system.bodies) - 1
            days = flight.quote(game, game.system.bodies[index], burn.id)["days"]
            shed = min(10.0, game.ship_stats.vent
                       * __import__("seedfall.sim.ship", fromlist=["REST_VENT"])
                       .REST_VENT * days)
            said = 10.0 - shed + burn.heat * cap
            flight.travel_to(game, index, burn.id)
            assert abs(game.ship.heat - said) < 0.5, (
                f"{burn.id}: said {said:.1f}, arrived at {game.ship.heat:.1f}")
        return "all four profiles arrive at the figure the helm quotes"

    @check("coasting is still always possible and always free")
    def _():
        # The deadlock guard. A captain with an empty tank must be able to
        # reach the ice that refills it.
        game = new_game("stranded-burn")
        game.ship.cargo = {}
        index = len(game.system.bodies) - 1
        quote = flight.quote(game, game.system.bodies[index], "coast")
        assert quote["fuel"] == 0
        result = flight.travel_to(game, index, "coast")
        assert result["ok"], result.get("why")
        assert game.orbit_body == game.system.bodies[index].id
        return f"reached it on nothing in {result['days']} days"

    @check("a warning about a destination distinguishes between destinations")
    def _():
        """Found by a player at the helm: every body in the system reported
        "you will be working 0.40 AU from the star", including one nine AU out.

        `path_note` took the *minimum* of the ship's distance and the target's,
        so a hull parked close in reported its own position whatever you
        clicked. A warning attached to a choice has to tell the choices apart.
        """
        import math
        from ..sim import flight as flight_sim

        told = 0
        for index in range(6):
            game = new_game(f"note-{index}")
            if len(game.system.bodies) < 3:
                continue
            # Park close to the star, which is what made them all identical.
            game.orbit_body = min(
                game.system.bodies,
                key=lambda b: math.hypot(*flight_sim.intercept(
                    game, b, "standard")["aim"])).id

            radii, notes = [], []
            for body in game.system.bodies:
                aim = flight_sim.intercept(game, body, "standard")["aim"]
                radii.append(math.hypot(*aim))
                notes.append(flight_sim.path_note(game, body) or "")
            if max(radii) - min(radii) < 1.0:
                continue                      # a tight system; nothing to tell apart

            hot = [n for n, r in zip(notes, radii)
                   if r < flight_sim.HOT_RADIUS and "working" in n]
            cool = [n for n, r in zip(notes, radii)
                    if r >= flight_sim.HOT_RADIUS and "working" in n]
            assert not cool, (
                f"seed {index}: a body outside {flight_sim.HOT_RADIUS} AU was "
                f"still warned about working close to the star")
            assert len(set(notes)) > 1, (
                f"seed {index}: every body gave the same note {notes[0]!r}")
            # And the figure quoted is the destination's own distance.
            for note, radius in zip(notes, radii):
                if "working" in note:
                    said = float(note.split("working ")[1].split(" AU")[0])
                    assert abs(said - radius) < 0.01, (
                        f"quoted {said} AU for a body at {radius:.2f}")
            told += 1
        assert told >= 3, f"only {told} systems were spread enough to check"
        return (f"{told} systems: only bodies inside "
                f"{flight_sim.HOT_RADIUS} AU are warned about, each with its "
                "own distance")

