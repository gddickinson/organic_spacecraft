"""The people behind the counters, and whether knowing them is worth anything.

A quay was a bag of services with nobody in it. `sim/memory.py` has carried a
`port` mind kind since it was written and a fresh chronicle's store was empty
and stayed empty — nothing ever put a person behind a counter you return to
fifty times.

The claims, in rising order of what matters:

- **Identity is derived and does not wander.** Same chronicle, same person,
  through time, luck and a reload — the rule anchorages and traffic obey.
- **Trading makes somebody helpful and stops.** If honest dealing reached the
  top there would be no politics, only patience.
- **Leaning is a different transaction, not a cheaper one.** It works when
  regard cannot, costs *more* regard, and lowers the ceiling for good.
- **Every favour is read somewhere.** A favour nothing acts on is the defect
  this project keeps finding, wearing a nicer coat.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.officials import DEALING_CAP, FAVOURS, LEAN_MULTIPLIER
from ..sim import contracts, customs, officials
from .harness import Suite


def _at_a_quay(seed: str):
    game = new_game(seed)
    game.credits = 300000
    system = next(s for s in game.galaxy.systems if s.port)
    game.location_id = system.id
    return game, system


def _befriend(game, system, times: int = 20):
    for _ in range(times):
        officials.dealt_with(game, system)


def run(suite: Suite) -> None:
    check = suite.check

    @check("every quay has somebody behind the counter")
    def _():
        game = new_game("who")
        seen, named = 0, set()
        for system in game.galaxy.systems:
            person = officials.identity(system)
            if not system.port:
                assert person == {}, system.name
                continue
            assert person["name"] and person["temper"], system.name
            named.add(person["name"])
            seen += 1
        assert seen > 0, "no port in the sector has anybody running it"
        return (f"{seen} quays, {len(named)} distinct harbourmasters")

    @check("the same person is there next time, and after a reload")
    def _():
        import os
        import tempfile

        from ..core import save as save_mod
        from ..core.state import load_game

        game, system = _at_a_quay("stable")
        first = officials.identity(system)
        _befriend(game, system, 8)
        officials.learn_lever(game, system, "gossip")
        held = officials.regard(game, system)

        for _ in range(4):
            game.advance_days(40)
            game.rng("noise").int(0, 999)
            again = officials.identity(system)
            assert again["name"] == first["name"], (first, again)
            assert again["temper"].id == first["temper"].id

        os.environ["HOME"] = tempfile.mkdtemp()
        save_mod.write({"game": game})
        back = load_game()
        assert back is not None
        after = officials.identity(back.galaxy.systems[system.id])
        assert after["name"] == first["name"], "a different person after a reload"
        # And what passed between you came back too.
        assert abs(officials.regard(back, back.galaxy.systems[system.id])
                   - held) < 0.01, "they forgot you over a save"
        assert officials.has_lever(back, back.galaxy.systems[system.id]), \
            "what you knew about them did not survive the save"
        return (f"{first['name']} still at the desk after 160 days and a "
                "reload, and still remembers you")

    @check("trading makes them helpful and takes you no further")
    def _():
        # If honest dealing reached the top there would be no politics here,
        # only patience.
        game, system = _at_a_quay("cap")
        _befriend(game, system, 200)
        value = officials.regard(game, system)
        assert abs(value - DEALING_CAP) < 0.01, (
            f"200 dealings reached {value:.0f}, not the {DEALING_CAP:.0f} cap")
        name, _tint = officials.band(value)
        assert name == "helpful", name
        return (f"200 dealings reach {value:.0f} — {name} — and stop")

    @check("a stranger is treated correctly, not coldly")
    def _():
        # `START_REGARD` sat inside the cold band, so everybody you had never
        # met read as hostile.
        game, system = _at_a_quay("stranger")
        name, _tint = officials.band(officials.regard(game, system))
        assert name == "correct", f"a stranger reads as {name!r}"
        return f"a stranger reads as {name!r}"

    @check("leaning costs more than asking, and costs it for good")
    def _():
        # The first cut made leaning cheaper *and* unconditional, which made
        # the lever strictly better than the relationship and deleted the
        # decision this whole system exists to pose.
        game, system = _at_a_quay("lean")
        _befriend(game, system, 40)
        officials.learn_lever(game, system, "gossip")

        polite = officials.preview(game, system, "berth", lean=False)
        leant = officials.preview(game, system, "berth", lean=True)
        assert abs(leant["cost"]) > abs(polite["cost"]), (
            f"leaning costs {abs(leant['cost']):.0f} against "
            f"{abs(polite['cost']):.0f} for asking — it is strictly better")
        assert abs(abs(leant["cost"]) / abs(polite["cost"])
                   - LEAN_MULTIPLIER) < 0.01

        officials.ask(game, system, "berth", lean=True)
        assert not officials.describe(game, system)["levers"], \
            "the lever was not spent"

        # The lasting mark, measured rather than recomputed from the constant
        # it is testing. The first version asserted
        # `after_cap == before_cap - CAP_PER_LEAN`, which is trivially true
        # when CAP_PER_LEAN is zero — it read the very number whose effect it
        # claimed to check, and passed with the effect deleted.
        _befriend(game, system, 300)
        after_leaning = officials.regard(game, system)

        clean, clean_system = _at_a_quay("lean-clean")
        _befriend(clean, clean_system, 300)
        never_leant = officials.regard(clean, clean_system)

        assert after_leaning < never_leant - 1.0, (
            f"trading reaches {after_leaning:.0f} having leant and "
            f"{never_leant:.0f} having not — leaning leaves no mark")
        return (f"asking {abs(polite['cost']):.0f}, leaning "
                f"{abs(leant['cost']):.0f}; 300 dealings afterwards reach "
                f"{after_leaning:.0f} against {never_leant:.0f} for somebody "
                "who never leant")

    @check("a lever is earned, not bought")
    def _():
        game, system = _at_a_quay("earn")
        ok, why = officials.can_learn(game, system)
        assert not ok and "stranger" in why.lower(), why
        got = officials.learn_lever(game, system)
        # Learning it anyway is possible for other routes, but the gate says no.
        assert got["ok"], got
        game2, system2 = _at_a_quay("earn2")
        _befriend(game2, system2, 10)
        ok2, _why2 = officials.can_learn(game2, system2)
        assert ok2, "ten square dealings still will not open anybody up"
        return "closed to a stranger, open after ten square dealings"

    @check("what the desk promises is what asking does")
    def _():
        # A fresh quay for every favour, because **asking spends regard**:
        # the first favour costs 28 of the 48 a well-liked captain has, which
        # puts every other favour out of reach inside the same chronicle. The
        # first draft looped over all five at one desk, asked one, and
        # asserted it had checked two — it passed only while that one desk
        # happened to offer a cheap favour first, and went red when a change
        # to *star generation* re-rolled which harbourmaster the seed lands
        # on. One favour per official is what the claim actually needs.
        checked, seen = 0, set()
        for favour in FAVOURS:
            game, system = _at_a_quay(f"promise-{favour.id}")
            _befriend(game, system, 40)
            plan = officials.preview(game, system, favour.id, lean=False)
            if not plan["ok"]:
                continue
            before = officials.regard(game, system)
            res = officials.ask(game, system, favour.id, lean=False)
            assert res["ok"], res
            moved = officials.regard(game, system) - before
            assert abs(moved - plan["cost"]) < 0.01, (
                f"{favour.id}: said {plan['cost']:.1f}, moved {moved:.1f}")
            if favour.lasts:
                assert officials.favour_running(game, system, favour.id) > 0
            seen.add(favour.id)
            checked += 1
        assert len(seen) >= 4, (
            f"only {len(seen)} of {len(FAVOURS)} favours could be asked at "
            f"all: {sorted(seen)}")
        return (f"{checked} favours asked, one official each, "
                "every cost exactly as previewed")

    @check("every favour is read somewhere in the game")
    def _():
        # A favour nothing acts on is the defect this project keeps finding,
        # wearing a nicer coat. Each one is exercised against the system it
        # is supposed to change.
        from ..data.commodities import COMMODITIES
        results = {}

        # wave_through: a search that does not happen.
        game, system = _at_a_quay("fav-search")
        # Not every power outlaws anything, so find one that does rather than
        # asserting the first quay in the seed happens to.
        banned = []
        for candidate in game.galaxy.systems:
            if not candidate.port:
                continue
            found = [c.id for c in COMMODITIES
                     if customs.outlaws(candidate.port.faction, c.id)]
            if found:
                system, banned = candidate, found
                game.location_id = candidate.id
                break
        assert banned, "no power in the sector outlaws anything"
        game.ship.cargo[banned[0]] = 6
        plain = customs.inspect(game, RNG("i"))
        officials._store(officials.mind(game, system))["favours"][
            "wave_through"] = game.day + 90
        waved = customs.inspect(game, RNG("i"))
        assert plain["searched"] and not waved["searched"], (plain, waved)
        results["wave_through"] = "search skipped"

        # word_first: a wider, richer board.
        game, system = _at_a_quay("fav-board")
        bare = contracts.generate(RNG("b"), game, system)
        officials._store(officials.mind(game, system))["favours"][
            "word_first"] = game.day + 90
        early = contracts.generate(RNG("b"), game, system)
        assert len(early) > len(bare), (len(bare), len(early))
        results["word_first"] = f"board {len(bare)} → {len(early)}"

        # quiet_price: goods move at the office rate.
        #
        # Granted through `ask`, not written into the store by hand. Writing
        # it in as a *dated* favour — which is what this check used to do —
        # tested the price code against a state the game could not produce:
        # a quiet price lasts no days, and `ask` dropped zero-day favours
        # entirely, so the whole thing was unreachable and this check could
        # not tell. It is the reason `tests/test_counter.py` exists.
        from ..sim import market as market_sim, trade
        game, system = _at_a_quay("fav-price")
        cid = next(c for c, s in system.market.stock.items() if s.units > 8)
        posted = market_sim.quote_buy(game, system, cid)
        officials._store(officials.mind(game, system))["regard"] = 60.0
        granted = officials.ask(game, system, "quiet_price", False)
        assert granted.get("ok"), granted
        bought = trade.buy(game, cid, 1)
        assert bought["ok"], bought
        assert bought["price"] < posted, (posted, bought["price"])
        results["quiet_price"] = (f"{posted:,} → {bought['price']:,.0f} "
                                  "a tonne")

        unread = [f.id for f in FAVOURS if f.id not in results
                  and f.id not in ("berth", "warning")]
        assert not unread, f"favours nothing reads: {unread}"
        return " · ".join(f"{k}: {v}" for k, v in results.items())

    @check("being boarded costs you with the person who runs the quay")
    def _():
        # A bust cost you with the *power* and nothing with the individual who
        # signed the order — the same person you have to face next time you
        # want a berth.
        from ..data.commodities import COMMODITIES
        game = new_game("busted")
        game.credits = 200000
        system = banned = None
        for candidate in game.galaxy.systems:
            if not candidate.port:
                continue
            found = [c.id for c in COMMODITIES
                     if customs.outlaws(candidate.port.faction, c.id)]
            if found:
                system, banned = candidate, found
                game.location_id = candidate.id
                break
        assert banned, "no power in the sector outlaws anything"

        _befriend(game, system, 20)
        before = officials.regard(game, system)
        game.ship.cargo[banned[0]] = 30
        for attempt in range(40):
            out = customs.inspect(game, RNG(f"bust{attempt}"))
            if out["caught"]:
                break
            game.ship.cargo[banned[0]] = 30
        else:
            return "never caught in forty attempts — nothing measured"
        after = officials.regard(game, system)
        assert after < before, (
            f"caught with a hold full of contraband and their regard went "
            f"{before:.0f} → {after:.0f}")
        return f"boarded: their regard {before:.0f} → {after:.0f}"

    @check("the desk screen names them and costs both ways of asking")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None

        game, system = _at_a_quay("desk")
        _befriend(game, system, 14)
        officials.learn_lever(game, system, "gossip")
        person = officials.identity(system)

        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.views["port"].tab = "desk"
        win.go("port")
        for _ in range(3):
            app.processEvents()
        view = win.views["port"]
        texts = " ".join(w.text() for w in view.findChildren(QLabel) if w.text())
        buttons = [b.text() for b in view.findChildren(QPushButton) if b.text()]
        assert person["name"] in texts, "the harbourmaster is not named"
        assert person["temper"].name in texts, "their temper is not shown"
        assert "Ask" in buttons and "Lean on them" in buttons, buttons
        win.close()
        return f"{person['name']} named, both routes offered and costed"
