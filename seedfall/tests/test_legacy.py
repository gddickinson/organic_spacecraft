"""Aftermath checks — an ending is a turn in the history, not a stop.

Reaching an ending used to show a dialog and call `clear_save()`. That is a
strange thing for this game to do: containment leaves four powers with no
common enemy and a cleared sector to divide, and that is a situation, not a
credits roll.

So each of the ten endings now opens an epoch. These hold the epochs to being
real — every one reachable, every scenario answerable, every answer doing
exactly what its card said it would, and the whole thing surviving a save.
"""

from __future__ import annotations

import os
import tempfile

from ..core.rng import RNG
from ..core.state import new_game
from ..data.epochs import EPOCHS, EPOCHS_BY_ID
from ..data.lore import ENDINGS, VICTORIES
from ..data.scenarios import SCENARIOS, SCENARIOS_BY_ID
from ..sim import legacy as legacy_sim
from ..sim.threat import victory_progress
from .harness import Suite


def _in_epoch(seed: str, ending: str):
    game = new_game(seed)
    legacy_sim.begin(game, ending)
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("every ending has an aftermath, and every aftermath has situations")
    def _():
        ids = [v[0] for v in VICTORIES]
        missing = [vid for vid in ids if vid not in EPOCHS_BY_ID]
        assert not missing, f"endings with nowhere to go: {missing}"
        for vid in ids:
            assert vid in ENDINGS, f"{vid} has no closing text"
        orphan = [e.id for e in EPOCHS if e.id not in ids]
        assert not orphan, f"epochs for endings that do not exist: {orphan}"
        for epoch in EPOCHS:
            assert epoch.scenarios, f"{epoch.id} asks nothing of you"
            for sid in epoch.scenarios:
                scenario = SCENARIOS_BY_ID.get(sid)
                assert scenario, f"{epoch.id} names a missing scenario {sid}"
                assert scenario.epoch == epoch.id, (
                    f"{sid} belongs to {scenario.epoch}, listed under {epoch.id}")
                assert len(scenario.answers) >= 2, f"{sid} is not a choice"
            assert epoch.rate > 0 and epoch.hold_days > 0
            assert epoch.failure and epoch.triumph and epoch.pressure
        loose = [s.id for s in SCENARIOS
                 if s.id not in {x for e in EPOCHS for x in e.scenarios}]
        assert not loose, f"scenarios no epoch ever offers: {loose}"
        return (f"{len(EPOCHS)} epochs for {len(ids)} endings, "
                f"{len(SCENARIOS)} situations, none orphaned")

    @check("an answer does exactly what its card said it would")
    def _():
        # The project's rule, applied to forty cards: perform the thing and
        # compare. The card and `legacy.apply` read the same dict, and this is
        # what stops them being two dicts.
        performed = 0
        for scenario in SCENARIOS:
            for index, answer in enumerate(scenario.answers):
                game = _in_epoch(f"card-{scenario.id}-{index}", scenario.epoch)
                game.credits = 500_000
                for key in ("biomass", "silicon", "alloy", "ore"):
                    game.stores[key] = 300
                # Start mid-gauge on purpose: `apply` floors pressure at zero,
                # so measuring a card that buys time while the gauge is already
                # at zero reads "said −9, moved 0" and blames the card for the
                # floor.
                game.legacy.pressure = 0.5
                game.situation = legacy_sim.Situation(scenario_id=scenario.id,
                                                      day=game.day)
                before = {
                    "credits": game.credits,
                    "rep": dict(game.rep),
                    "pressure": game.legacy.pressure,
                    "stores": dict(game.stores),
                }
                result = legacy_sim.answer(game, index)
                assert result["ok"], result.get("why")

                want = answer.effect
                if "credits" in want:
                    assert abs((game.credits - before["credits"])
                               - want["credits"]) < 0.01, (
                        f"{scenario.id}/{index}: said {want['credits']:+,}")
                if "pressure" in want:
                    moved = game.legacy.pressure - before["pressure"]
                    assert abs(moved - want["pressure"]) < 0.001, (
                        f"{scenario.id}/{index}: said {want['pressure']:+.2f} "
                        f"pressure, moved {moved:+.2f}")
                for fid, delta in want.get("rep", {}).items():
                    moved = game.rep[fid] - before["rep"][fid]
                    assert moved * delta > 0, (
                        f"{scenario.id}/{index}: said {fid} {delta:+.0f}, "
                        f"moved {moved:+.0f}")
                for key, amount in want.get("stores", {}).items():
                    moved = game.stores[key] - before["stores"].get(key, 0)
                    assert abs(moved - amount) < 0.01, (
                        f"{scenario.id}/{index}: said {key} {amount:+g}, "
                        f"moved {moved:+g}")
                if want.get("flag"):
                    assert game.flags.get(want["flag"]) is True
                assert game.situation is None, "the situation stayed open"
                performed += 1
        return f"{performed} answers performed, every stated figure exact"

    @check("you can carry on past an ending, and the clock runs again")
    def _():
        game = new_game("carry")
        for system in game.galaxy.systems:
            system.bloom = 0.95
        # Ruin is *outliving* the sector, so it wants a captain who was in
        # it — see `threat._stood_through_it`. Burning it back once is the
        # cheapest record of that.
        from ..sim import responses as response_sim
        response_sim.provoke(game, "burn")
        game.advance_days(1)
        assert game.victory == "ruin", game.victory
        assert not game.dead

        legacy_sim.begin(game, game.victory)
        assert game.victory is None, "the ending was not taken"
        assert not game.dead and not game.overgrown
        assert legacy_sim.in_epoch(game)

        before = game.day
        game.advance_days(120)
        assert game.day > before, "the clock did not restart"
        assert legacy_sim.gauge(game)["pressure"] > 0, "no pressure accrued"
        return (f"ruin taken at day {before}, still flying at {game.day} with "
                f"{legacy_sim.gauge(game)['pressure'] * 100:.0f}% attrition")

    @check("Ruin is outlived, not waited out — and the loss can be reached")
    def _():
        # Ruin needed 90% of the sector merely touched, a live captain and
        # a hull over a quarter — which pure passivity satisfies about 180
        # days *before* the loss could fire, and victory is checked first.
        # So a living captain could not lose to the Bloom at all, and doing
        # nothing whatsoever was rewarded with an ending.
        from ..core.rng import RNG
        from ..sim import responses as response_sim
        from ..sim import threat as threat_sim

        idle = new_game("ruin-idle")
        for system in idle.galaxy.systems:
            system.bloom = 0.6
        idle.colonies = []
        assert not threat_sim.victory_progress(idle)["ruin"][2], (
            "a captain who did nothing at all was given an ending for it")
        assert threat_sim.check_victory(idle) != "ruin"

        stood = new_game("ruin-stood")
        for system in stood.galaxy.systems:
            system.bloom = 0.6
        stood.colonies = []
        response_sim.provoke(stood, "burn")
        assert threat_sim.victory_progress(stood)["ruin"][2], (
            "a captain who fought it and outlived it was refused the ending")

        # And the loss now fires on a condition that can be watched closing:
        # every harbour in the sector drowned, rather than all forty-two
        # systems past half.
        lost = new_game("loss-harbours")
        for system in lost.galaxy.systems:
            if system.port:
                system.bloom = 0.9
        left, total = threat_sim.harbours_left(lost)
        assert (left, total) == (0, total) and total > 0, (left, total)
        assert any(s.bloom <= 0.5 for s in lost.galaxy.systems), (
            "this fixture drowned the whole sector, so it proves nothing "
            "the old all-forty-two test did not")
        threat_sim.tick(lost, 30, RNG("loss"))
        assert lost.overgrown, (
            "every harbour in the Verge is gone and the chronicle goes on")
        return (f"idle: no ending; stood through it: Ruin; {total} harbours "
                f"drowned ends it with clean ground still on the chart")

    @check("an epoch closes, badly at the top and well at the end")
    def _():
        broke = _in_epoch("broke", "dominion")
        broke.legacy.pressure = 0.99
        broke.advance_days(40)
        assert broke.legacy.over and broke.legacy.outcome == "failure", (
            f"pressure ran to {broke.legacy.pressure:.2f} without closing")

        held = _in_epoch("held", "dominion")
        epoch = EPOCHS_BY_ID["dominion"]
        held.legacy.began = held.day - epoch.hold_days - 1
        held.advance_days(1)
        assert held.legacy.over and held.legacy.outcome == "triumph", (
            f"held for {epoch.hold_days} days and did not close well")
        return (f"failure at {BREAK_LABEL}, triumph after "
                f"{epoch.hold_days} days")

    @check("one epoch can follow another, and the chronicle keeps both")
    def _():
        game = _in_epoch("chain", "containment")
        game.legacy.pressure = 0.99
        game.advance_days(40)
        assert game.legacy.over
        legacy_sim.begin(game, "concord")
        assert legacy_sim.in_epoch(game)
        lived = legacy_sim.summary(game)
        assert len(lived) == 2, [row[0].id for row in lived]
        assert lived[0][0].id == "containment" and lived[0][1] == "failure"
        assert lived[1][0].id == "concord"
        return " → ".join(f"{row[0].name} ({row[1]})" for row in lived)

    @check("a situation waiting on an answer survives a save")
    def _():
        os.environ["HOME"] = tempfile.mkdtemp()
        from ..core import save as save_mod
        from ..core.state import load_game

        game = _in_epoch("saved", "cartel")
        rng = RNG("saved")
        for _ in range(20):
            game.advance_days(60)
            if legacy_sim.offer(game):
                break
        assert legacy_sim.offer(game), "no situation ever arrived"
        title = legacy_sim.offer(game)["title"]

        save_mod.write({"game": game})
        back = load_game()
        assert back is not None
        assert back.situation is not None and not back.situation.over
        assert legacy_sim.offer(back)["title"] == title
        assert back.legacy.epoch == "cartel"
        assert abs(back.legacy.pressure - game.legacy.pressure) < 0.001
        assert back.legacy.answered == game.legacy.answered
        result = legacy_sim.answer(back, 0)
        assert result["ok"], result.get("why")
        return f"'{title}' reloaded mid-question and answered"

    @check("every new ending can actually be reached")
    def _():
        from ..data.xenotech import XENOTECH
        from ..sim import xeno as xeno_sim

        reached = {}

        game = new_game("win-lineage")
        from ..sim.ship import build_layers, make_ship
        for index in range(4):
            hull = make_ship("navis", [], f"Cutting {index}")
            build_layers(hull, game.bonuses)
            game.fleet.append(hull)
        reached["lineage"] = victory_progress(game)["lineage"][2]

        game = new_game("win-xenarch")
        for tech in XENOTECH:
            game.xeno_study[tech.id] = tech.study * 2
            xeno_sim.incorporate(game, tech.id)
        reached["xenarch"] = victory_progress(game)["xenarch"][2]

        game = new_game("win-cartel")
        from ..sim import market as market_sim
        # Every system that *has* a market — the first thirty systems are not
        # thirty markets, which is how the first version of this fixture
        # registered eleven prices and reported the ending unreachable.
        for system in game.galaxy.systems:
            if system.market:
                market_sim.note_prices(game, system, 0, 0)
        game.credits = 2_000_000
        reached["cartel"] = victory_progress(game)["cartel"][2]

        game = new_game("win-apostasy")
        game.ship.chassis = "cantor"
        game.officers = []
        game.rep["sanhedrin"] = 80
        reached["apostasy"] = victory_progress(game)["apostasy"][2]

        game = new_game("win-ruin")
        for system in game.galaxy.systems:
            system.bloom = 0.95
        # Ruin is *outliving* the sector, so it asks for a captain who was
        # in it rather than one who waited somewhere quiet — burning it
        # back once is the cheapest record of that.
        from ..sim import responses as response_sim
        response_sim.provoke(game, "burn")
        reached["ruin"] = victory_progress(game)["ruin"][2]

        unreachable = [k for k, v in reached.items() if not v]
        assert not unreachable, f"endings nothing can reach: {unreachable}"
        return " · ".join(sorted(reached))


BREAK_LABEL = "100%"
