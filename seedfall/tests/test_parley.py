"""Talking your way out, and running: the two acts that had no forecast.

Every other button in this game quotes itself. `stations.order_preview` prints a
line per helm order on the very panel these two sit on; a ground option names its
odds and its prize; an overture says what it buys. **"Hail them" said nothing at
all** — press it and either the engagement ends or the enemy takes a free turn,
with the probability written down nowhere a captain could read it. "Disengage" was
the same.

And the hail never asked what the power actually *remembers*. `b.rep` is the
standing on the books; `grudge.feeling` is the memory behind it, which the game
already spends on prices, on whether a harbourmaster will do you a favour and on
whether work is posted at all. Measured: a Charter that remembers a destroyed hull
sits at -88 and a hail's chance was **unchanged by it**.

The claims:

- **The number on the button is the number the dice see** — stated, then measured
  by hailing four hundred times and counting.
- **Every part of it is named, and each part moves it** the way the name says.
- **What they remember counts.** 18% clean, 3% remembering a kill.
- **A refused hail costs the turn it says it costs.**
- **The Bloom cannot be talked to**, and says so rather than rolling.
- **The screen prints what the sim says**, on the panel and not only in a tooltip.
"""

from __future__ import annotations

import math

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import combat as combat_sim
from ..sim import encounters as enc_sim
from ..sim import grudge as grudge_sim
from ..sim import parley as parley_sim
from .harness import Suite

#: Hails per situation in the frequency check. 400 gives a standard error of
#: about 2.5 points at p=0.5, so a three-sigma band is 7.5 — wide enough not to
#: flake and far tighter than any of the terms being claimed.
TRIALS = 400


def _battle(game, rng, rep=0.0, faction="charter", difficulty=1.0):
    enemy = enc_sim.make_enemy(rng, faction, difficulty=difficulty)
    game.rep[faction] = rep
    b = combat_sim.start(game.ship, game.ship_stats, enemy,
                         bonuses=game.bonuses, officers=game.officers,
                         game=game, rng=rng, rep=rep)
    b.enemy_faction = faction
    return b


def _hail_rate(seed: str, rep: float, trials: int = TRIALS) -> tuple:
    """State the chance from a fresh battle, then hail that many times."""
    stated = None
    won = 0
    for index in range(trials):
        game = new_game(seed)
        rng = RNG(f"{seed}-{index}")
        b = _battle(game, RNG(seed), rep=rep)
        if stated is None:
            stated = parley_sim.odds(b)["chance"]
        combat_sim.take_turn(b, {"type": "hail"}, rng)
        if b.result == "parley":
            won += 1
    return stated, won / trials


def run(suite: Suite) -> None:
    check = suite.check

    @check("the chance on the button is the chance the dice see")
    def _():
        # A forecast for a probabilistic act is checked by *running* it, which
        # is the same shape as the docking mini-game's check: state the number,
        # then take the action hundreds of times and count.
        lines = []
        for rep in (0.0, 60.0, 100.0):
            stated, got = _hail_rate("hail-rate", rep)
            band = 3.0 * math.sqrt(max(stated, 1e-6) * (1 - stated) / TRIALS)
            assert abs(got - stated) <= band + 0.01, (
                f"standing {rep:+.0f}: the panel says {stated:.1%} and "
                f"{TRIALS} hails came out at {got:.1%}, outside three sigma "
                f"({band:.1%})")
            lines.append(f"{stated:.0%} said / {got:.0%} run")
        return f"{TRIALS} hails at each of three standings: " + " · ".join(lines)

    @check("every part of the chance is named, and each one moves it")
    def _():
        game = new_game("terms")
        rng = RNG("terms")

        # Standing, both ways from the same battle.
        low = parley_sim.odds(_battle(new_game("terms"), RNG("t"), rep=-80.0))
        mid = parley_sim.odds(_battle(new_game("terms"), RNG("t"), rep=0.0))
        high = parley_sim.odds(_battle(new_game("terms"), RNG("t"), rep=95.0))
        assert low["chance"] < mid["chance"] < high["chance"], (
            low["chance"], mid["chance"], high["chance"])
        assert any("standing" in name for name, _v in high["terms"]), high

        # The upper hand. Hurt them and the same hail gets easier; take the
        # damage yourself and it gets harder.
        even = _battle(new_game("terms"), RNG("t"), rep=40.0)
        base = parley_sim.odds(even)["chance"]
        hurt_them = _battle(new_game("terms"), RNG("t"), rep=40.0)
        for layer in hurt_them.enemy.ship.layers:
            layer.hp = layer.max * 0.3
        winning = parley_sim.odds(hurt_them)
        hurt_you = _battle(new_game("terms"), RNG("t"), rep=40.0)
        for layer in hurt_you.player.ship.layers:
            layer.hp = layer.max * 0.3
        losing = parley_sim.odds(hurt_you)
        assert winning["chance"] > base > losing["chance"], (
            f"winning {winning['chance']:.2f} · even {base:.2f} · "
            f"losing {losing['chance']:.2f}")
        assert any("upper hand" in n for n, _v in winning["terms"]), winning
        assert any("winning" in n for n, _v in losing["terms"]), losing

        # Their nerve. `WAVERING_AT` is a cliff on purpose — a hull whose resolve
        # has gone will listen — so it is checked on both sides of it, **at 40
        # and 50 written here** rather than at the constant plus or minus five.
        # The first draft did the latter, so the two probes moved with the number
        # they were testing and the check passed with it set anywhere at all —
        # which `tests/tripwire.py` duly reported as "protected only by a suite
        # that does not name its subject".
        steady = _battle(new_game("terms"), RNG("t"), rep=0.0)
        steady.enemy.resolve = 50.0
        shaken = _battle(new_game("terms"), RNG("t"), rep=0.0)
        shaken.enemy.resolve = 40.0
        assert parley_sim.odds(shaken)["chance"] > \
            parley_sim.odds(steady)["chance"], (
                "a hull at 40 resolve is no easier to talk to than one at 50 — "
                "the line is not between them")
        assert any("nerve" in n for n, _v in parley_sim.odds(shaken)["terms"])
        assert not any("nerve" in n for n, _v in parley_sim.odds(steady)["terms"]), (
            "a hull at 50 resolve is being counted as one whose nerve has gone")
        gap = (parley_sim.odds(shaken)["chance"]
               - parley_sim.odds(steady)["chance"])
        assert 0.2 <= gap <= 0.3, (
            f"crossing the line is worth {gap:.0%}, and a broken nerve is "
            "supposed to be worth about a quarter of the chance")

        # And somebody aboard who can talk. `st.diplomacy` is a comms officer at
        # 0.05 a level, and the opening crew has none — so the term reads zero on
        # every starting hull and is only worth anything once one is hired.
        talky = _battle(new_game("terms"), RNG("t"), rep=0.0)
        talky.player.st.diplomacy = 0.15
        told = parley_sim.odds(talky)
        assert any("talk" in n for n, _v in told["terms"]), told
        assert told["chance"] > mid["chance"]
        return (f"standing {low['chance']:.0%}→{high['chance']:.0%} · upper hand "
                f"{losing['chance']:.0%}→{winning['chance']:.0%} · a shaken "
                f"enemy and a talker both count, and each is named")

    @check("what a power remembers of you counts against the hail")
    def _():
        # The whole reason the module grew a door. The standing on the books and
        # the memory behind it are different numbers, and only the first was
        # being read — while the rest of the game spends the second on prices,
        # on favours and on whether work is posted at all.
        clean = new_game("memory")
        before = parley_sim.odds(_battle(clean, RNG("m"), rep=0.0))

        sore = new_game("memory")
        for _ in range(3):
            grudge_sim.note(sore, "charter", "kill",
                            "you destroyed the Steadfast", 1.6)
        feeling = grudge_sim.feeling(sore, "charter")
        after = parley_sim.odds(_battle(sore, RNG("m"), rep=0.0))
        assert feeling < -40, f"the grudge did not take: {feeling}"
        assert after["chance"] < before["chance"] - 0.05, (
            f"{before['chance']:.1%} clean and {after['chance']:.1%} with a "
            f"feeling of {feeling:.0f} — the memory is not being read")
        assert any("remember" in n for n, _v in after["terms"]), after

        # And it cuts both ways: a power that owes you is easier to talk to.
        owed = new_game("memory")
        grudge_sim.note(owed, "charter", "rescue", "you stood off the Bloom", 1.4)
        kindly = parley_sim.odds(_battle(owed, RNG("m"), rep=0.0))
        assert kindly["chance"] >= before["chance"], (
            f"a power that remembers you kindly ({grudge_sim.feeling(owed, 'charter'):.0f}) "
            f"is no easier to talk to: {kindly['chance']:.1%} against "
            f"{before['chance']:.1%}")
        return (f"{before['chance']:.0%} clean · {after['chance']:.0%} "
                f"remembering a kill (feeling {feeling:.0f}) · "
                f"{kindly['chance']:.0%} remembering a rescue")

    @check("a refused hail hands them the turn, as the panel says it will")
    def _():
        # The cost of the gamble, which was never stated and is the whole reason
        # the odds matter. Hail from a hopeless standing until one is refused,
        # and watch the enemy's turn happen anyway.
        for index in range(40):
            game = new_game("cost")
            rng = RNG(f"cost-{index}")
            b = _battle(game, RNG("cost"), rep=-95.0)
            told = parley_sim.odds(b)
            assert told["chance"] < 0.1, told
            before = sum(max(0.0, l.hp) for l in b.player.ship.layers)
            turns = b.turn
            combat_sim.take_turn(b, {"type": "hail"}, rng)
            if b.result == "parley":
                continue                      # the long shot came in; try again
            after = sum(max(0.0, l.hp) for l in b.player.ship.layers)
            assert b.turn > turns or after < before or b.log, (
                "the hail was refused and nothing happened at all — the "
                "enemy's turn is what makes this a gamble")
            assert parley_sim.COSTS_A_TURN
            return (f"refused at {told['chance']:.0%}: the turn advanced to "
                    f"{b.turn} and the hull went {before:.0f} → {after:.0f}")
        raise AssertionError("forty hails at under ten per cent all succeeded")

    @check("the Bloom is told it cannot be talked to, not rolled against")
    def _():
        game = new_game("bloom-talk")
        rng = RNG("bt")
        b = _battle(game, rng, rep=0.0)
        b.no_parley = True
        told = parley_sim.odds(b)
        assert told["mute"] and told["chance"] == 0.0, told
        assert told["why"], "mute and with nothing to say about it"
        turns = b.turn
        combat_sim.take_turn(b, {"type": "hail"}, rng)
        assert b.result != "parley", "the mass stood down"
        assert b.turn == turns, (
            "hailing the Bloom cost a turn — it is not a gamble, it is a "
            "category error, and the screen says so before you press it")
        return f"mute, and the reason given: {told['why']!r}"

    @check("the battle screen prints the numbers the sim gives")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("screen-talk")
        rng = RNG("st")
        battle = _battle(game, rng, rep=55.0)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        # `win.battle`, which is where the view looks — the same door
        # `test_orderplan` uses. Hanging it on the game gets "No engagement".
        win.battle = battle
        win.go("battle")
        view = win.views["battle"]
        view.refresh()
        for _ in range(3):
            app.processEvents()
        said = " ".join(lab.text() for lab in view.findChildren(QLabel)
                        if lab.text())
        win.close()

        talk = parley_sim.odds(battle)
        run_ = parley_sim.escape_odds(battle)
        assert f"{talk['chance']:.0%} they stand down" in said, (
            f"the panel never quotes the hail: {said[-400:]}")
        assert "they fire anyway" in said, (
            "the panel quotes the odds and not the cost of missing them")
        if battle.fleeable:
            assert f"{run_['chance']:.0%} you shake them" in said, (
                f"the panel never quotes the burn: {said[-400:]}")
        for name, _value in talk["terms"]:
            assert name in said, f"{name!r} is in the sum and not on the panel"
        return (f"the panel reads {talk['chance']:.0%} to talk and "
                f"{run_['chance']:.0%} to run, with "
                f"{len(talk['terms'])} named reasons")

    @check("straining against a grapple spends the turn it says it spends")
    def _():
        # A held "flee" returned free of charge — and `grappled` only counts
        # down in the end-of-turn the free return skipped, so repeating the
        # order was an infinite loop for any scripted driver. It goes the way
        # of the refused hail now: the enemy takes its turn, the clock moves,
        # and the grapple eventually slackens.
        game = new_game("held-flee")
        rng = RNG("held-flee")
        b = _battle(game, rng)
        b.player.grappled = 2
        turns = b.turn
        combat_sim.take_turn(b, {"type": "flee"}, rng)
        assert b.over or b.turn == turns + 1, (
            f"a held flee left the turn at {b.turn}")
        tries = 1
        while not b.over and b.player.grappled and tries < 6:
            combat_sim.take_turn(b, {"type": "flee"}, rng)
            tries += 1
        assert b.over or not b.player.grappled, (
            f"{tries} strains and the grapple never slackened")
        return (f"held fast: {tries} strain(s), each a real turn, and the "
                "grapple let go")
