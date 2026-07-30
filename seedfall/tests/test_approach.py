"""The powers coming to you, and whether they have a reason to.

Diplomacy ran one way. Six actions, all player→faction; the powers only
drifted their grievances back toward a baseline. A captain could ignore the
whole board for twenty years and nobody would ever knock.

The claims worth pinning, in rising order of what matters:

- **Every approach is caused.** No live reason, no envoy — ever. A power that
  turns up because a die came up is a random event wearing a flag.
- **The preview is what happens.** Three answers, each costed before it is
  taken, and taking it does exactly that.
- **Refusing quietly costs what refusing costs.** An offer whose deadline is
  free to ignore is not a decision.
- **And a power remembers how you answered**, which was the one dealing with a
  power that left no trace at all. `preview` told a captain refusing a levy that
  "they will file it as a grievance, and grievances are counted", and the levy's
  own `costs` line says "they collect grievances". What actually happened was
  `dip.ensure(game).grievances = getattr(..., 0) + 1` — a counter on a field
  `DiplomaticState` does not declare, read by nobody and **wiped by the next
  save.** Three ways of promising a thing that did not happen.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.approaches import APPROACHES, AS_ANSWERED, QUIET_DAYS
from ..sim import approach, colony as colony_sim, diplomacy as dip
from ..sim import grudge as grudge_sim
from ..data.colonies import COLONIES
from .harness import Suite


def _rich(seed: str):
    """A captain with cargo, money, standing and ground — every trigger live."""
    game = new_game(seed)
    game.credits = 120000
    for cid in ("ore", "volatiles", "biomass", "alloy", "silicon"):
        game.ship.cargo[cid] = 80
    for fid in dip.POWERS:
        game.rep[fid] = 30.0
    return game


def _hold_ground(game, faction: str):
    system = next((s for s in game.galaxy.systems if s.faction == faction), None)
    if system is None:
        return None
    col = colony_sim.Colony(id=9301, class_id=COLONIES[0].id, name="Test",
                            system_id=system.id, body_id=system.bodies[0].id,
                            need=0)
    col.online = True
    game.colonies.append(col)
    game.recompute()
    return col


def run(suite: Suite) -> None:
    check = suite.check

    @check("every kind of approach states its ask, its price and its refusal")
    def _():
        for action in APPROACHES:
            assert action.opening and action.ask, action.id
            assert action.gives and action.costs, action.id
            assert action.window > 0, action.id
            assert action.refuse_rep < 0, (
                f"{action.id} costs nothing to refuse, so it is not an offer")
            assert action.accept_rep > 0, action.id
        return (f"{len(APPROACHES)} kinds, every one with a stated ask, "
                "payment and cost of refusal")

    @check("nobody comes calling without a reason")
    def _():
        # The whole design. A power that turns up because a die came up is a
        # random event wearing a flag.
        game = new_game("nocause")
        for fid in dip.POWERS:
            game.rep[fid] = -60.0          # nobody is talking to you
        game.ship.cargo.clear()
        game.colonies.clear()
        for fid in dip.POWERS:
            assert approach.reasons(game, fid) == [], (
                f"{fid} has a reason to approach a captain it will not speak "
                f"to: {approach.reasons(game, fid)}")
        fired = 0
        for attempt in range(400):
            if approach.tick(game, 30, RNG(f"n{attempt}")):
                fired += 1
        assert fired == 0, f"{fired} envoys arrived with nothing to want"
        return "400 months, no reasons, no envoys"

    @check("a shortage is read off the market, and only for what you carry")
    def _():
        # The first version read a `demand` mapping `Market` does not have, so
        # requisitions could never fire at all; the second found every power
        # short of `wildseed`, which nothing stocks and no captain hauls.
        game = _rich("short")
        for fid in dip.POWERS:
            found = approach._shortage(game, fid)
            if found is None:
                continue
            cid, supply = found
            assert game.ship.cargo.get(cid, 0) >= approach.MIN_REQUISITION, (
                f"{fid} asked for {cid}, which you are not carrying")
            assert supply <= approach.SHORT_SUPPLY, (cid, supply)
        # And with an empty hold there is nothing to requisition.
        game.ship.cargo.clear()
        for fid in dip.POWERS:
            assert approach._shortage(game, fid) is None
            assert "requisition" not in [k for k, _r in
                                         approach.reasons(game, fid)]
        return "shortages read from market stock, restricted to the hold"

    @check("what the screen promises is what taking it does")
    def _():
        checked = []
        for kind in ("requisition", "levy", "denounce_rival", "treaty_offer"):
            game = _rich(f"do-{kind}")
            rival = None
            if kind == "denounce_rival":
                rival = next(f for f in dip.POWERS if f != "charter")
            if kind == "levy" and _hold_ground(game, "charter") is None:
                continue
            envoy = approach._build(game, "charter", kind, rival, RNG(kind))
            game.envoy = envoy
            said = approach.preview(game, envoy, "accept")

            before_rep = dict(game.rep)
            before_cr = game.credits
            before_goods = (game.ship.cargo.get(envoy.goods, 0)
                            if envoy.goods else 0)
            res = approach.answer(game, envoy, "accept")
            assert res.get("ok"), res.get("why")

            assert game.credits - before_cr == said["credits"], (
                f"{kind}: said {said['credits']:+,}, moved "
                f"{game.credits - before_cr:+,}")
            for fid, delta in said["rep"].items():
                moved = game.rep[fid] - before_rep.get(fid, 0)
                assert abs(moved - delta) < 0.01 or abs(game.rep[fid]) >= 100, (
                    f"{kind}: said {fid} {delta:+.0f}, moved {moved:+.0f}")
            if said["goods"]:
                cid, delta = said["goods"]
                now = game.ship.cargo.get(cid, 0)
                assert abs((now - before_goods) - delta) < 0.01, (
                    f"{kind}: said {delta:g} t of {cid}, moved "
                    f"{now - before_goods:g}")
            # `envoy.choice` used to be checked here. It was written on every
            # answer and read by nothing in the game, and the *memory* is the
            # record now — so this asks the power what it remembers rather than
            # asking the envoy what it was told.
            assert envoy.over
            if f"{kind}|accept" in AS_ANSWERED:
                assert grudge_sim.because(game, envoy.faction), (
                    f"{kind}: accepted, and the power remembers nothing")
            checked.append(kind)
        assert len(checked) >= 3, checked
        return f"{len(checked)} kinds taken, every figure as previewed"

    @check("a treaty offered is a treaty signed")
    def _():
        game = _rich("treaty")
        assert not dip.has_treaty(game, "concordat")
        envoy = approach._build(game, "concordat", "treaty_offer", None,
                                RNG("t"))
        game.envoy = envoy
        approach.answer(game, envoy, "accept")
        assert dip.has_treaty(game, "concordat"), (
            "they offered terms, you signed, and there is no treaty")
        return "terms offered by the office, signed for nothing but standing"

    @check("letting it lapse costs exactly what refusing costs")
    def _():
        # An offer whose deadline is free to ignore is not a decision.
        outcomes = {}
        for how in ("refuse", "lapse"):
            game = _rich(f"lapse-{how}")
            envoy = approach._build(game, "charter", "denounce_rival",
                                    "freeholds", RNG("l"))
            game.envoy = envoy
            before = dict(game.rep)
            if how == "refuse":
                approach.answer(game, envoy, "refuse")
            else:
                game.day = envoy.expires + 1
                approach.tick(game, 1, RNG("x"))
            outcomes[how] = {f: round(game.rep[f] - before.get(f, 0), 3)
                             for f in dip.POWERS}
            assert game.envoy.over, how
        assert outcomes["refuse"] == outcomes["lapse"], (
            f"refusing moved {outcomes['refuse']} and lapsing moved "
            f"{outcomes['lapse']} — the deadline is free to ignore")
        return f"both cost {outcomes['refuse']}"

    @check("one envoy at a time, and a quiet spell afterwards")
    def _():
        game = _rich("queue")
        game.envoy = approach._build(game, "charter", "denounce_rival",
                                     "freeholds", RNG("q"))
        for attempt in range(50):
            assert approach.tick(game, 20, RNG(f"q{attempt}")) == [] \
                or game.envoy.over, "a second envoy arrived over the first"
            if game.envoy.over:
                break
        # After answering, that power holds off for a while.
        game = _rich("quiet")
        state = dip.ensure(game)
        state.approached = {"charter": game.day}
        game.day += QUIET_DAYS - 5
        for attempt in range(60):
            approach.tick(game, 1, RNG(f"z{attempt}"))
            live = getattr(game, "envoy", None)
            if live is not None and not live.over:
                assert live.faction != "charter", (
                    "the Charter came back inside the quiet spell")
                break
        return f"one at a time, and {QUIET_DAYS} quiet days per power"

    @check("pushing moves the price once and only once")
    def _():
        game = _rich("push")
        envoy = approach._build(game, "charter", "requisition", None,
                                RNG("p"))
        game.envoy = envoy
        if not envoy.credits:
            return "no requisition available in this seed"
        opening = envoy.credits
        said = approach.preview(game, envoy, "push")
        res = approach.answer(game, envoy, "push")
        assert res.get("ok"), res.get("why")
        assert envoy.credits > opening, (opening, envoy.credits)
        # `offer`, not `credits`. This check always compared the movement of
        # what is *on the table* — which was right — against a field the envoy
        # screen was rendering as "Treasury: +794". One number, two readings,
        # and the screen's was the wrong one. See `tests/test_envoy.py`.
        assert envoy.credits - opening == said["offer"], (
            f"said {said['offer']:+,}, moved {envoy.credits - opening:+,}")
        again = approach.answer(game, envoy, "push")
        assert not again.get("ok"), "you can push forever"
        return (f"{opening:,} → {envoy.credits:,} credits, and no second "
                "bite")

    @check("every way of dealing with a power leaves a dated memory")
    def _():
        # The general question, and the one that found the gap. An overture is
        # remembered (`diplomacy._remember`), and so is an answer to a demand for
        # ground — `territory.answer` notes all three of pay, cede and refuse.
        # An envoy's answer was remembered nowhere, so a captain who had refused
        # four levies saw a power that priced him badly and a diplomacy screen
        # that could not say why.
        from ..sim import approach as ap_sim
        from ..sim import diplomacy as dip_sim
        from ..sim import grudge as grudge_sim

        ways = {}

        # An overture.
        game = new_game("mem-overture")
        game.credits = 500_000
        for key in ("biomass", "ore", "alloy", "volatiles"):
            game.stores[key] = 9000
        offered = dip_sim.available(game, "charter")
        assert offered, "no overture is on offer at all"
        did = dip_sim.perform(game, offered[0][0].id, "charter")
        assert did.get("ok"), did
        ways["overture"] = [x["text"] for x in grudge_sim.because(game, "charter")]

        # An answer to a demand for ground.
        # `_planted` borrowed from `test_territory` rather than copied: it
        # matures a holding over real days and a second version of that would
        # drift from the first.
        from ..sim import territory as territory_sim
        from .test_territory import _planted
        game, _col, system = _planted("mem-demand", "charter")
        out = territory_sim.answer(game, system, "charter", "defy")
        assert out["ok"], out
        ways["demand"] = [x["text"] for x in grudge_sim.because(game, "charter")]

        # An envoy's answer, both ways.
        for answered in ("accept", "refuse"):
            game = new_game(f"mem-envoy-{answered}")
            game.credits = 500_000
            envoy = ap_sim.Envoy(kind="levy", faction="charter", credits=1000,
                                 expires=game.day + 30)
            game.envoy = envoy
            out = ap_sim.answer(game, envoy, answered)
            assert out.get("ok"), out
            ways[f"envoy {answered}"] = [
                x["text"] for x in grudge_sim.because(game, "charter")]

        for way, said in ways.items():
            assert said, (
                f"{way}: the Charter remembers nothing about it. Every dealing "
                "with a power has to leave something the diplomacy screen can "
                "name, or its coldness is unexplainable")
        return " · ".join(f"{k}: {v[0][:34]}" for k, v in ways.items())

    @check("a grievance is counted, and survives a save")
    def _():
        # The promise, checked as a promise: `preview` says grievances are
        # counted, so refusing has to move something that lasts. The counter it
        # used to increment was undeclared, so it came back from a reload as
        # nothing at all — which is the half of this that a check on the number
        # alone would have missed.
        import os
        import tempfile

        from ..core import save as save_mod
        from ..core.state import load_game
        from ..sim import approach as ap_sim
        from ..sim import grudge as grudge_sim

        game = new_game("counted")
        game.credits = 5_000_000
        before = (grudge_sim.feeling(game, "charter"),
                  grudge_sim.price_bias(game, "charter"))

        # What the screen says will happen.
        envoy = ap_sim.Envoy(kind="levy", faction="charter", credits=1000,
                            expires=game.day + 30)
        game.envoy = envoy
        said = ap_sim.preview(game, envoy, "refuse")
        promised = " ".join(said.get("lines", []))
        assert "grievance" in promised.lower(), (
            f"the refusal no longer promises a grievance: {promised!r}")

        ap_sim.answer(game, envoy, "refuse")
        after = (grudge_sim.feeling(game, "charter"),
                 grudge_sim.price_bias(game, "charter"))
        assert after[0] < before[0], (
            f"refusing the levy left the Charter feeling {after[0]:.1f} against "
            f"{before[0]:.1f} — a grievance that moves nothing is not counted")
        assert after[1] > before[1], (
            f"the price bias went {before[1]:.3f} → {after[1]:.3f}; a grievance "
            "they collect should cost the captain something")

        os.environ["HOME"] = tempfile.mkdtemp()
        assert save_mod.write({"game": game})
        back = load_game()
        assert grudge_sim.because(back, "charter"), (
            "the grievance did not survive the save — which is exactly what the "
            "undeclared counter did")
        assert abs(grudge_sim.feeling(back, "charter") - after[0]) < 1e-6
        return (f"feeling {before[0]:+.1f} → {after[0]:+.1f}, price "
                f"x{before[1]:.3f} → x{after[1]:.3f}, and both came back "
                "from a reload")

    @check("an envoy blocks the door and survives a reload")
    def _():
        import os
        import tempfile

        from ..core import save as save_mod
        from ..core.state import load_game
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None

        game = _rich("door")
        game.envoy = approach._build(game, "charter", "levy", None, RNG("d"))
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("map")
        assert win.current == "envoy", (
            f"wandered off to {win.current} with an envoy waiting")
        win.close()

        os.environ["HOME"] = tempfile.mkdtemp()
        save_mod.write({"game": game})
        back = load_game()
        assert back is not None and back.envoy is not None, "the envoy vanished"
        assert back.envoy.kind == game.envoy.kind
        assert back.envoy.credits == game.envoy.credits
        assert not back.envoy.over
        return "navigation held, and the envoy came back through a save"
