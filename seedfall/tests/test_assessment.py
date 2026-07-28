"""Assessment checks — a defeat that teaches something.

Combat grew arcs, bands, crew stations, consorts and abilities, and the screen
grew a scrolling list of damage lines. A captain could lose a NAVIS in two
turns to a battleship and be shown nothing that explained it. The read is only
worth having if it is honest, so these check it against what actually happens
rather than against what it claims.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import assessment, combat, encounters
from ..sim import tactical as tac
from ..sim.ship import make_ship, stats
from . import captain_ai
from .harness import Suite

VERDICT_ORDER = ["outmatched", "the lighter hull", "a real fight",
                 "the heavier hull", "unopposed"]


def _armed_player():
    ship = make_ship("navis", ["slug_battery", "mag_lance", "reaction_organ",
                               "opsin_eyes", "chemo_gut"])
    ship.cargo = {"ore": 400, "alloy": 400}
    return ship


def _fight(player, player_stats, scale, seed, game, faction="concordat"):
    rng = RNG(seed)
    battle = combat.start(player, player_stats,
                          encounters.make_enemy(rng, faction, scale),
                          rng=rng, game=game)
    return battle, rng


def _play_out(battle, rng, turns=60):
    for _ in range(turns):
        if battle.over:
            break
        combat.take_turn(battle, captain_ai.orders(battle), rng)
    return battle.result in ("destroyed", "driven-off")


def run(suite: Suite) -> None:
    check = suite.check

    @check("the read does not lie about who is winning")
    def _():
        # The first version compared raw hull and raw damage and was not even
        # monotonic: enemy hull is a chassis lottery that ignores difficulty
        # while armament and armour both track it, so a scale-3 battleship
        # could read as an easier fight than a scale-1 scout.
        game = new_game("honest")
        hulls = [_armed_player(),
                 make_ship("pike", ["railgun", "mass_driver", "fusion_torch",
                                    "lattice_echo", "silicon_core"])]
        hulls[1].cargo = {"ore": 400, "alloy": 400}

        wins: dict[str, list[int]] = {}
        for hull in hulls:
            st = stats(hull)
            for scale in (0.5, 1.5, 2.5, 3.5):
                for index in range(10):
                    battle, rng = _fight(hull, st, scale,
                                         f"h-{hull.chassis}-{scale}-{index}", game)
                    verdict = assessment.weight(battle)["verdict"]
                    wins.setdefault(verdict, []).append(int(_play_out(battle, rng)))

        rates = {v: sum(r) / len(r) for v, r in wins.items() if len(r) >= 8}
        assert len(rates) >= 2, f"not enough verdicts to compare: {list(wins)}"
        ranked = sorted(rates, key=lambda v: VERDICT_ORDER.index(v))
        values = [rates[v] for v in ranked]
        assert values == sorted(values), (
            "a worse-sounding verdict won more often: "
            + ", ".join(f"{v} {rates[v]:.0%}" for v in ranked))
        return " · ".join(f"{v} {rates[v]:.0%} (n={len(wins[v])})" for v in ranked)

    @check("an outmatched captain is told so before a shot is fired")
    def _():
        # Sampled, not a single draw: a scale-3.5 encounter is a distribution
        # of hulls and a minority of them really are winnable, so asserting on
        # one seed tests the seed rather than the read.
        game = new_game("warned")
        grim = warned = 0
        for index in range(24):
            player = _armed_player()
            battle, _rng = _fight(player, stats(player), 3.5, f"warned-{index}",
                                  game)
            assert battle.turn == 1, "the read arrived after the shooting started"
            read = assessment.read(battle)
            if read["weight"]["verdict"] in ("outmatched", "the lighter hull"):
                grim += 1
                said = " ".join(t for _k, t in read["advice"]).lower()
                if "outmatched" in said or "hull will not take" in said:
                    warned += 1
        assert grim >= 18, (
            f"only {grim}/24 scale-3.5 battleships read as a bad idea")
        assert warned >= grim * 0.7, (
            f"{grim} grim reads but only {warned} said anything about it")
        return f"{grim}/24 read as a bad idea, {warned} said so in as many words"

    @check("the read names why nothing is bearing")
    def _():
        # The single most common reason a fight goes wrong, and the one the
        # scrolling log buries: broadside mounts with the target dead ahead.
        game = new_game("arcs")
        player = _armed_player()
        battle, _rng = _fight(player, stats(player), 1.0, "arcs", game)
        battle.player.body = tac.Body2D(0, 0, 0, 0)
        battle.enemy.body = tac.Body2D(0, -tac.BAND_UNITS * 2.5, 180, 0)

        guns = assessment.mounts(battle)
        assert guns["off_arc"], "nothing is off-arc with the target dead ahead"
        said = " ".join(t for _k, t in assessment.advice(battle)).lower()
        assert "bears" in said or "arc" in said, (
            f"the arc problem was never mentioned: {said!r}")
        assert "°" in said, "the advice does not say how far off"

        # Turn beam-on and the complaint must go away.
        battle.player.body = tac.Body2D(0, 0, 90, 0)
        after = assessment.mounts(battle)
        assert len(after["bearing"]) > len(guns["bearing"]), (
            "turning beam-on brought nothing onto the target")
        return (f"{len(guns['off_arc'])} mounts off-arc bow-on, "
                f"{len(after['bearing'])} bearing beam-on")

    @check("the read is quiet when there is nothing to say")
    def _():
        game = new_game("quiet-read")
        player = _armed_player()
        battle, _rng = _fight(player, stats(player), 0.5, "quiet-read", game)
        # Point the guns where they work so no arc or range complaint fires.
        battle.player.body = tac.Body2D(0, 0, 0, 0)
        battle.enemy.body = tac.Body2D(tac.BAND_UNITS * 2.5, 0, 270, 0)
        advice = assessment.advice(battle)
        assert len(advice) <= 3, f"{len(advice)} pieces of advice is a lecture"
        for _tint, text in advice:
            assert text.strip(), "an empty line of advice"
        return f"{len(advice)} thing(s) worth saying"

    @check("every reading survives a fight from start to finish")
    def _():
        # read() is called on every repaint, including the turn somebody dies.
        game = new_game("robust")
        player = _armed_player()
        seen = set()
        for scale in (0.5, 2.0, 3.5):
            battle, rng = _fight(player, stats(player), scale, f"rb{scale}", game)
            for _ in range(40):
                read = assessment.read(battle)
                assert set(read) >= {"weight", "mounts", "advice", "intent"}
                seen.add(read["weight"]["verdict"])
                assert read["intent"], "the enemy is doing nothing describable"
                if battle.over:
                    break
                combat.take_turn(battle, captain_ai.orders(battle), rng)
            assessment.read(battle)      # and once more after it ends
        assert seen <= set(VERDICT_ORDER), f"unknown verdict in {seen}"
        return f"{len(seen)} verdict(s) seen across three fights, no crashes"

    @check("an unarmed enemy is never called dangerous")
    def _():
        game = new_game("unarmed")
        player = _armed_player()
        battle, _rng = _fight(player, stats(player), 1.0, "unarmed", game)
        battle.enemy.st.weapons = []
        read = assessment.read(battle)
        assert read["weight"]["their_turns"] == float("inf"), (
            "an enemy with no weapons is still given a time to break you")
        assert read["weight"]["verdict"] == "unopposed", (
            f"an unarmed enemy reads as {read['weight']['verdict']!r}")
        assert read["their_band"] is None, "an unarmed hull has a band envelope"
        return "an unarmed hull reads as unopposed"
