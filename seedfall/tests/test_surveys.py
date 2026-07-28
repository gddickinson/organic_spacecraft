"""Survey checks — four ways of looking, and each has to be a real choice.

A player asked how surveys work and why they all seemed the same. They were:
one button, three days, no cost, no risk, and the same kind of answer for a
comet as for an ocean world — while thirteen sensor fittings and a drone
technology existed only to nudge a single `scan` float.

These hold the four methods to being different from each other in ways that
matter, and to the project's usual rule: what a method says it cannot see, it
genuinely cannot see.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.surveys import CATEGORIES, METHODS, METHODS_BY_ID
from ..sim import flight
from ..sim import survey as survey_sim
from .harness import Suite


def _sharpen(game, scan: float = 0.0, sensor: float = 0.0) -> None:
    """Give the ship better instruments, in a way that survives the clock.

    `ship_stats` is *derived*: `advance_days` calls `recompute()`, which
    rebuilds it from the hull and throws any override away. A check that poked
    it directly measured a high scan rating for the forecast and a low one for
    the survey, and blamed the forecast. `stock_fx` is a real input and is
    folded back in every time.
    """
    fx = dict(getattr(game, "stock_fx", {}) or {})
    if scan:
        fx["scan"] = scan
    if sensor:
        fx["sensor"] = sensor
    game.stock_fx = fx
    game.recompute()


def _rich(seed: str):
    """A game with a body that has something of every kind on it."""
    from ..data.xenotech import XENOTECH
    game = new_game(seed)
    game.stores.update({"silicon": 60, "alloy": 60, "volatiles": 60})
    body = next((b for b in game.system.bodies if b.lifeforms),
                game.system.bodies[0])
    body.relic = body.relic or XENOTECH[0].id
    body.relic_found = False
    body.surveyed = False
    return game, game.system.bodies.index(body), body


def run(suite: Suite) -> None:
    check = suite.check

    @check("the methods are coherent, and none is merely a worse other")
    def _():
        assert len(METHODS) >= 3, "one survey is not a choice"
        for method in METHODS:
            assert method.finds, f"{method.id} finds nothing"
            assert set(method.finds) <= set(CATEGORIES), method.finds
            assert method.gives and method.costs and method.blurb, method.id
            assert method.days > 0 and method.quality > 0
        # Every method must be the best at *something*, or it is furniture.
        for method in METHODS:
            others = [m for m in METHODS if m.id != method.id]
            better = (
                all(method.days < m.days for m in others)
                or all(len(method.finds) >= len(m.finds) for m in others)
                or not method.alongside
                or not method.cost)
            assert better, f"{method.id} is beaten on every axis"
        assert any(not m.alongside for m in METHODS), "everything needs flying"
        assert any("relic" in m.finds for m in METHODS), "nothing finds a site"
        assert any("relic" not in m.finds for m in METHODS), (
            "every method finds buried sites, so depth is not a trade")
        return (f"{len(METHODS)} methods, "
                f"{sum(1 for m in METHODS if not m.alongside)} without flying, "
                f"{sum(1 for m in METHODS if m.cost)} costing stores")

    @check("what a method says it cannot see, it cannot see")
    def _():
        # The rule the whole design rests on. A sweep must not turn up life.
        blind_held = 0
        for method in METHODS:
            for attempt in range(6):
                game, index, body = _rich(f"blind-{method.id}-{attempt}")
                game.research.unlocked.append("dronework")
                _sharpen(game, scan=1.0, sensor=99.0)
                found = survey_sim.perform(game, index, method.id)
                assert found.get("ok"), found.get("why")
                if "lifeforms" not in method.finds:
                    assert not found["lifeforms"], (
                        f"{method.id} claims to be blind to life and "
                        f"catalogued {len(found['lifeforms'])}")
                if "anomaly" not in method.finds:
                    assert not found["anomaly"], f"{method.id} saw an anomaly"
                if "relic" not in method.finds:
                    assert not found["relic"], (
                        f"{method.id} claims not to see underground and found "
                        "a buried site")
                blind_held += 1
        return f"{blind_held} surveys, every method blind to what it said"

    @check("only a deep look reliably finds what is buried")
    def _():
        # The reason to spend nine days: a close pass should mostly miss.
        rates = {}
        for method_id in ("pass", "deep"):
            hits = tries = 0
            for attempt in range(24):
                game, index, body = _rich(f"dig-{method_id}-{attempt}")
                _sharpen(game, scan=0.5)
                found = survey_sim.perform(game, index, method_id)
                if found.get("ok"):
                    tries += 1
                    hits += bool(found.get("relic"))
            rates[method_id] = hits / max(1, tries)
        assert rates["pass"] == 0.0, (
            f"a close pass found a buried site {rates['pass']*100:.0f}% of the "
            "time, so depth buys nothing")
        assert rates["deep"] > 0.6, (
            f"a deep survey only found one {rates['deep']*100:.0f}% of the time")
        return (f"close pass {rates['pass']*100:.0f}% · "
                f"deep survey {rates['deep']*100:.0f}%")

    @check("the forecast is what the survey costs")
    def _():
        checked = 0
        for method in METHODS:
            game, index, body = _rich(f"cost-{method.id}")
            game.research.unlocked.append("dronework")
            _sharpen(game, scan=0.6, sensor=99.0)
            said = survey_sim.preview(game, body, method.id)
            before_day = game.day
            before = {c: game.ship.cargo.get(c, 0) + game.stores.get(c, 0)
                      for c in said["cost"]}
            found = survey_sim.perform(game, index, method.id)
            assert found.get("ok"), found.get("why")
            assert game.day - before_day == said["days"], (
                f"{method.id}: said {said['days']} days, took "
                f"{game.day - before_day}")
            for commodity, amount in said["cost"].items():
                after = game.ship.cargo.get(commodity, 0) + \
                    game.stores.get(commodity, 0)
                assert abs((before[commodity] - after) - amount) < 0.01, (
                    f"{method.id}: said {amount:g} {commodity}, took "
                    f"{before[commodity] - after:g}")
            checked += 1

        # Again with a nearly dry tank. `flight.ensure_at` quietly drops to a
        # coast when there is not enough reaction mass for a standard burn, and
        # a coast is slower — a forecast that always quotes the standard burn
        # promises twelve days for a fourteen-day trip. Without this case the
        # coast path is never taken and the fix is unproven.
        coasted = 0
        for method in METHODS:
            if not method.alongside:
                continue
            game, index, body = _rich(f"dry-{method.id}")
            _sharpen(game, scan=0.6, sensor=99.0)
            standard = flight.quote(game, body, "standard")
            if standard["fuel"] <= 0 or game.orbit_body == body.id:
                continue
            # Enough for the charges, not enough to burn hard.
            game.ship.cargo["volatiles"] = max(
                0.0, float(method.cost.get("volatiles", 0)))
            game.stores["volatiles"] = 60
            said = survey_sim.preview(game, body, method.id)
            before_day = game.day
            found = survey_sim.perform(game, index, method.id)
            assert found.get("ok"), found.get("why")
            assert game.day - before_day == said["days"], (
                f"{method.id} on a dry tank: said {said['days']} days, took "
                f"{game.day - before_day} — the coast was not forecast")
            coasted += 1
        return (f"{checked} methods, days and stores exactly as forecast; "
                f"{coasted} re-checked on a dry tank")

    @check("equipment and technology decide what you may do")
    def _():
        game, index, body = _rich("gates")
        game.research.unlocked = [t for t in game.research.unlocked
                                  if t != "dronework"]
        offered = {m.id: (ok, why) for m, ok, why in
                   survey_sim.available(game, body)}
        assert not offered["probes"][0] and "dronework" in offered["probes"][1]
        assert not offered["deep"][0] and "scan" in offered["deep"][1].lower()

        # Give them the kit and the gates open.
        game.research.unlocked.append("dronework")
        _sharpen(game, scan=0.6)
        opened = {m.id: ok for m, ok, _w in survey_sim.available(game, body)}
        assert opened["probes"] and opened["deep"], opened

        # And running out of stores closes one again.
        game.stores["silicon"] = 0
        game.ship.cargo.pop("silicon", None)
        shut = {m.id: (ok, why) for m, ok, why in
                survey_sim.available(game, body)}
        assert not shut["probes"][0] and "silicon" in shut["probes"][1]
        return "drones need the technology, depth needs the instruments, "\
               "and both need what they consume"

    @check("a sweep only reaches as far as the array does")
    def _():
        game, index, body = _rich("reach")
        far = max(game.system.bodies,
                  key=lambda b: survey_sim.reach_to(game, b))
        _sharpen(game, sensor=-3.0)
        offered = {m.id: (ok, why) for m, ok, why in
                   survey_sim.available(game, far)}
        assert not offered["sweep"][0], "swept a body beyond the array"
        assert "AU" in offered["sweep"][1], offered["sweep"][1]
        _sharpen(game, sensor=99.0)
        assert survey_sim.available(game, far)[0][1], "a huge array still refused"
        return (f"{survey_sim.reach_to(game, far):.1f} AU refused at 0.5, "
                "allowed at 99")

    @check("a listening post lengthens what you can sweep from where you are")
    def _():
        # Three colony classes advertise sensor reach and `colony.effects` has
        # tallied it per system since the day they were written. Nothing ever
        # read the tally: the sweep compared against the bare hull stat, so a
        # CHORUS node bought exactly nothing.
        from ..data.colonies import COLONIES
        from ..sim import colony as colony_sim
        listening = [c for c in COLONIES if c.effects.get("sensor", 0) > 0]
        assert listening, "no colony promises sensor reach any more"

        game, index, body = _rich("listen")
        far = max(game.system.bodies,
                  key=lambda b: survey_sim.reach_to(game, b))
        bare = survey_sim.reach(game)
        assert not survey_sim.available(game, far)[0][1], (
            "the far body was already within reach, so this proves nothing")

        # Plant one properly and let it come online — a hand-set `colony_fx` is
        # thrown away by the next `recompute`, which is how this stayed hidden.
        best = max(listening, key=lambda c: c.effects["sensor"])
        col = colony_sim.Colony(
            id=9001, class_id=best.id, name="Test post",
            system_id=game.system.id, body_id=game.system.bodies[0].id, need=0)
        col.online = True
        game.colonies.append(col)
        game.recompute()

        grown = survey_sim.reach(game)
        assert grown > bare, (
            f"{best.id} promises {best.effects['sensor']} sensor and the reach "
            f"stayed at {bare:.2f}")
        assert survey_sim.watching(game) == best.effects["sensor"], \
            survey_sim.watching(game)
        return (f"{len(listening)} works promise reach; {best.id} takes it "
                f"from {bare:.2f} to {grown:.2f} AU")

    @check("the old survey still means what every other check thinks it means")
    def _():
        # `actions.survey` is a close pass, and dozens of checks depend on it.
        from ..sim.actions import survey as old
        game = new_game("compat")
        before = game.day
        found = old(game, 0)
        assert found["research"] > 0 and game.day > before
        assert game.system.bodies[0].surveyed
        return "actions.survey is unchanged: a close pass, as it always was"
