"""Aftermath checks — what a fight leaves behind belongs to the rules.

Every consequence of an engagement used to live in `ui/battle_view.py._finish()`:
the salvage, the loot, the cargo off the wreck, bounty progress, seized
xenology, instar kills, consorts lost, loyalty, and every standing change that
follows from shooting at somebody. `sim/combat.py` held a loot dict and nothing
else. Nothing headless could resolve an engagement, so every balance run that
fought a battle collected no loot, no standing and no bounty credit — and the
one-directional rule the project runs on was broken in the place it mattered
most.

The other half: a kill told only its victim. Destroying a Concordat hull moved
the Concordat and nobody else, in a sector where `sim/allegiance.py` already
knew exactly who would be glad to hear it.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import aftermath as aftermath_sim
from ..sim import combat, diplomacy as dip, encounters
from ..sim.ship import build_layers, make_ship, stats
from . import captain_ai
from .harness import Suite

POWERS = ("charter", "concordat", "freeholds", "sanhedrin")


def _armed(game):
    ship = make_ship("navis", ["slug_battery", "mag_lance", "carapace",
                               "reaction_organ", "opsin_eyes", "chemo_gut"])
    build_layers(ship, game.bonuses)
    game.ship = ship
    game.recompute()
    return ship


def _fought(seed: str, faction: str = "concordat", result: str | None = None):
    """A real engagement, played out, optionally forced to an outcome."""
    game = new_game(seed)
    ship = _armed(game)
    rng = RNG(f"f-{seed}")
    battle = combat.start(ship, stats(ship),
                          encounters.make_enemy(rng, faction, 0.6),
                          rng=rng, game=game)
    for _ in range(60):
        if battle.over:
            break
        combat.take_turn(battle, captain_ai.orders(battle), rng)
    if result is not None:
        battle.result = result
        battle.over = True
    return game, battle, rng


def _at_war(game) -> None:
    for index, a in enumerate(POWERS):
        for b in POWERS[index + 1:]:
            dip.shift_relation(game, a, b, -90 - dip.relation(game, a, b))


def run(suite: Suite) -> None:
    check = suite.check

    @check("an engagement pays out with no screen anywhere near it")
    def _():
        # The whole architectural point: this could not be done at all before.
        game, battle, rng = _fought("headless", result="destroyed")
        before = game.credits
        out = aftermath_sim.resolve(game, battle, rng)
        assert not out["already"]
        assert game.credits > before, "no salvage reached the treasury"
        assert out["credits"] == game.credits - before, (
            "the payout and the report disagree")
        assert out["salvage"] > 0, "nothing came off the wreck"
        assert out["standing"], "a kill moved nobody's standing"
        return (f"{out['credits']:,} in loot, {out['research']} research, "
                f"{len(out['recovered'])} cargo type(s), "
                f"{len(out['standing'])} standing change(s)")

    @check("the screen and the ledger do the same thing")
    def _():
        # The extraction has to be faithful, not merely tidy. Two identical
        # games: one resolved through the view, one through the sim.
        try:
            from .test_ui import _use_offscreen
            _use_offscreen()
            from PyQt6.QtWidgets import QApplication
        except ImportError:
            return "skipped: no Qt"

        from ..ui import theme
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(theme.stylesheet())

        def ledger(game):
            return (round(game.credits, 3),
                    {p: round(game.rep.get(p, 0), 3) for p in POWERS},
                    round(game.research.banked, 3))

        direct_game, direct_battle, rng = _fought("agree", result="destroyed")
        aftermath_sim.resolve(direct_game, direct_battle, RNG("seize-agree"))
        expected = ledger(direct_game)

        ui_game, ui_battle, _rng = _fought("agree", result="destroyed")
        win = MainWindow(ui_game)
        win.dialog = lambda *a, **k: None
        win.toast = lambda *a, **k: None
        win.battle = ui_battle
        # Same seize roll as the direct path, so the comparison is of the
        # bookkeeping and not of the dice.
        ui_game.rng = lambda _tag="": RNG("seize-agree")
        win.views["battle"]._finish()
        got = ledger(ui_game)
        win.close()

        assert got == expected, f"screen {got} != rules {expected}"
        return "credits, standing and research identical down both paths"

    @check("an engagement cannot be paid out twice")
    def _():
        game, battle, rng = _fought("twice", result="destroyed")
        first = aftermath_sim.resolve(game, battle, rng)
        after = (game.credits, dict(game.rep))
        second = aftermath_sim.resolve(game, battle, rng)
        assert first["credits"] > 0, "nothing was paid the first time"
        assert second["already"], "the second resolve did not know"
        assert (game.credits, dict(game.rep)) == after, (
            "the salvage was collected twice")
        return "salvage, standing and bounties all collected exactly once"

    @check("a kill is noted by everyone who dislikes the victim")
    def _():
        hot, battle, rng = _fought("war", result="destroyed")
        _at_war(hot)
        before = {p: hot.rep.get(p, 0) for p in POWERS}
        out = aftermath_sim.resolve(hot, battle, rng)
        victim = battle.enemy_faction
        assert victim and victim != "bloom"
        assert hot.rep[victim] < before[victim], "the victim did not mind"
        gained = [p for p in POWERS if p != victim
                  and hot.rep.get(p, 0) > before[p]]
        assert len(gained) == len(POWERS) - 1, (
            f"only {len(gained)} of {len(POWERS) - 1} rivals were glad: "
            f"{out['pleased']}")
        return (f"{victim} {out['standing'][0][1]:+g}, and "
                + aftermath_sim.phrase_pleased(out["pleased"]))

    @check("nobody gloats in a sector at peace")
    def _():
        calm, battle, rng = _fought("peace", result="destroyed")
        for index, a in enumerate(POWERS):
            for b in POWERS[index + 1:]:
                dip.shift_relation(calm, a, b, 30 - dip.relation(calm, a, b))
        before = {p: calm.rep.get(p, 0) for p in POWERS}
        out = aftermath_sim.resolve(calm, battle, rng)
        assert not out["pleased"], f"gloating at +30 all round: {out['pleased']}"
        victim = battle.enemy_faction
        unmoved = [p for p in POWERS if p != victim
                   and calm.rep.get(p, 0) == before[p]]
        assert len(unmoved) == len(POWERS) - 1, "somebody moved anyway"
        return "a kill in a cordial sector moves only its victim"

    @check("everybody is in favour of one less instar")
    def _():
        # It used to be the Charter alone, hardcoded, in a screen.
        game, battle, rng = _fought("bloom", faction="bloom", result="destroyed")
        before = {p: game.rep.get(p, 0) for p in POWERS}
        out = aftermath_sim.resolve(game, battle, rng)
        moved = [p for p in POWERS if game.rep.get(p, 0) > before[p]]
        assert len(moved) == len(POWERS), (
            f"only {moved} approved of killing a Bloom mass")
        assert all(delta > 0 for _f, delta in out["standing"])
        return f"all {len(moved)} powers approve"

    @check("standing off costs less than finishing it")
    def _():
        rout_game, rout, rng = _fought("rout", result="driven-off")
        rout_victim = rout.enemy_faction
        rout_before = rout_game.rep.get(rout_victim, 0)
        aftermath_sim.resolve(rout_game, rout, rng)
        routed = rout_before - rout_game.rep.get(rout_victim, 0)

        kill_game, kill, rng2 = _fought("rout", result="destroyed")
        kill_victim = kill.enemy_faction
        kill_before = kill_game.rep.get(kill_victim, 0)
        aftermath_sim.resolve(kill_game, kill, rng2)
        killed = kill_before - kill_game.rep.get(kill_victim, 0)

        assert 0 < routed < killed, (
            f"driving one off costs {routed} against {killed} for a kill")

        talk_game, talk, rng3 = _fought("rout", result="parley")
        talk_victim = talk.enemy_faction
        talk_before = talk_game.rep.get(talk_victim, 0)
        aftermath_sim.resolve(talk_game, talk, rng3)
        assert talk_game.rep.get(talk_victim, 0) > talk_before, (
            "standing down gains nothing")
        return (f"parley + · driven off −{routed:g} · destroyed −{killed:g}")
