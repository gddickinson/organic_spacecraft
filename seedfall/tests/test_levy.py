"""The levy on a holding: taken, received, and said out loud.

`territory.collect_tithe` skimmed thirty per cent off a colony's output before it
reached the captain's stores, and `colony.tick` **threw its return away**.
Measured on a RADIX Mine yielding 2.6 t of ore a day: over thirty days the works
turned out 78 t, the captain received 54.6 — and the Charter's purse moved by
**nothing at all**. No log line, no event, nobody the richer. Thirty per cent of a
holding simply ceased to exist.

Two rules the game applies everywhere else, and did not apply here. A share taken
off somebody is a share somebody else receives — `wharfage.collect` moves both
sides in one function for precisely this reason, and task #95 was the whole cycle
about powers who paid for nothing. And a deduction a captain cannot see is not a
cost, it is a mystery: task #100's wharfage is named on the board, in the log, and
on the desk's forecast for exactly this.

There was a third thing wrong, quieter. The demand screen has always quoted "a
levy would cost X a year", worked out as `base × 0.55` inside
`territory.yearly_worth` — and since the levy credited nobody, **there was no act
for that forecast to agree or disagree with.** Both read `value_of` now, and the
quote comes out right: 8,829 a year against thirty days that took 726, which
scales to 8,830.

The claims:

- **What is taken is what the claimant receives**, to the credit, and the purse
  records it as its own line.
- **The captain is told** — which power, which holding, what goods, what worth.
- **The year the screen quotes is the year the levy takes.**
- **Defying pays nothing**, and ceding leaves nothing to pay with.
- **The purse panel shows it.**
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.territory import LEVY_SHARE
from ..sim import colony as colony_sim
from ..sim import exchequer as exchequer_sim
from ..sim import territory as terr_sim
from ..sim import works as works_sim
from .harness import Suite


def _holding(seed: str = "levy", claimed_by: str | None = "charter"):
    """A captain with a working colony, optionally under somebody's levy."""
    game = new_game(seed)
    game.credits = 400_000
    game.ship.fitted.append("seed_bay")
    game.research.unlocked.append("bioleach")
    game.recompute()
    for key in ("alloy", "ore", "biomass", "volatiles", "phosphate", "silicon"):
        game.stores[key] = 9000
    body = next(b for b in game.system.bodies
                if b.kind in ("asteroid", "moon", "rocky"))
    colony_sim.found(game, game.system, body, "radix_mine")
    game.advance_days(200)
    assert game.colonies, "nothing was planted"
    colony = game.colonies[0]
    assert works_sim.yields_of(colony), "the holding turns out nothing"
    if claimed_by:
        colony.tithe_to = claimed_by
    return game, colony


def run(suite: Suite) -> None:
    check = suite.check

    @check("what the levy takes is what the claimant receives")
    def _():
        # The conservation claim. Before this the goods came off the top and
        # reached nobody: measured, 23.4 t of ore a month and a purse that did
        # not move.
        game, colony = _holding("conserve")
        purse = exchequer_sim.purse(game, "charter")
        credits_before, levies_before = purse.credits, purse.levies

        rates = dict(works_sim.yields_of(colony))
        days = 30.0
        gains, _events = colony_sim.tick(game, days)

        got = purse.credits - credits_before
        assert abs((purse.levies - levies_before) - got) < 1e-6, (
            "the purse gained and the levy line did not")
        assert got > 0, "a levy on a working holding and the purse did not move"

        # And the goods: the captain keeps what is left, not the whole.
        for cid, rate in rates.items():
            if cid in ("credits", "research"):
                continue
            whole = rate * days
            kept = gains.get(cid, 0.0)
            assert abs(kept - whole * (1 - LEVY_SHARE)) < 0.01, (
                f"{cid}: produced {whole:.2f}, kept {kept:.2f}, and the levy "
                f"is {LEVY_SHARE:.0%}")
        taken = {cid: rate * days * LEVY_SHARE for cid, rate in rates.items()
                 if cid not in ("credits", "research")}
        assert abs(terr_sim.value_of(taken) - got) < 0.01, (
            f"{terr_sim.value_of(taken):.2f} of goods went and "
            f"{got:.2f} arrived")
        return (f"{sum(taken.values()):.1f} t off {colony.name} in a month, "
                f"worth {got:,.0f}, every credit of it in the Charter's purse")

    @check("the captain is told a levy was taken")
    def _():
        # A deduction nobody can see is not a cost. `colony.tick` called
        # `collect_tithe` and dropped the answer on the floor.
        game, colony = _holding("told")
        _gains, events = colony_sim.tick(game, 30.0)
        said = [text for _kind, text in events if "levy" in text.lower()]
        assert said, f"thirty per cent went and the events were {events}"
        line = said[0]
        assert "Charter" in line, line
        assert colony.name in line, line
        assert " t ore" in line, f"the goods are not named: {line}"
        assert "worth about" in line, f"the worth is not named: {line}"
        assert any(kind == "warn" for kind, text in events if text == line), (
            "a power taking a third of your output is not neutral news")

        # And through the clock, which is the door a captain actually reads:
        # `colony.tick` returning an event is no use if `advance_days` drops it.
        game2, _colony2 = _holding("told-clock")
        mark = len(game2.log)
        game2.advance_days(45)
        logged = [text for _day, text, _kind in game2.log[mark:]
                  if "levy" in text.lower()]
        assert logged, (
            "the event is returned and the ship's log never carries it: "
            + str([t for _d, t, _k in game2.log[mark:]][:6]))
        return logged[0]

    @check("the year the screen quotes is the year the levy takes")
    def _():
        # Forecast against act. The demand screen has always quoted
        # `yearly_worth × LEVY_SHARE`; until the levy paid somebody there was
        # nothing to check it against.
        game, colony = _holding("quote")
        quoted = terr_sim.yearly_worth(game, colony) * LEVY_SHARE
        purse = exchequer_sim.purse(game, "charter")
        before = purse.credits
        colony_sim.tick(game, 365.0)
        took = purse.credits - before
        assert abs(took - quoted) < max(1.0, quoted * 0.02), (
            f"the screen quotes {quoted:,.0f} a year and a year took "
            f"{took:,.0f}")
        return (f"{quoted:,.0f} quoted for the year, {took:,.0f} taken — "
                f"within {abs(took - quoted):.1f}")

    @check("defying pays nothing, and ceding leaves nothing to pay")
    def _():
        # The other two answers, checked against the purse rather than against
        # the standing they move, which `test_territory` already holds.
        game, colony = _holding("defy", claimed_by=None)
        colony.defiant = True
        purse = exchequer_sim.purse(game, "charter")
        before = purse.credits
        gains, events = colony_sim.tick(game, 60.0)
        assert purse.credits == before, (
            f"a defiant holding paid {purse.credits - before:.2f} anyway")
        assert not [t for _k, t in events if "levy" in t.lower()], events
        rates = works_sim.yields_of(colony)
        for cid, rate in rates.items():
            if cid in ("credits", "research"):
                continue
            assert abs(gains.get(cid, 0.0) - rate * 60.0) < 0.01, (
                f"{cid}: a defiant holding was skimmed regardless")

        # And a holding that has been handed over is not there to be levied.
        game2, colony2 = _holding("cede")
        system = game2.galaxy.systems[colony2.system_id]
        res = terr_sim.answer(game2, system, "charter", "cede")
        assert res["ok"], res
        assert not game2.colonies, game2.colonies
        purse2 = exchequer_sim.purse(game2, "charter")
        was = purse2.credits
        colony_sim.tick(game2, 60.0)
        assert purse2.credits == was, "a ceded holding went on paying a levy"
        return ("sixty days defiant: nothing taken and nothing said; a ceded "
                "holding pays nothing because it is not yours")

    @check("the purse panel shows the levy as its own line")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, colony = _holding("panel")
        colony_sim.tick(game, 120.0)
        purse = exchequer_sim.purse(game, "charter")
        assert purse.levies > 0, purse

        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("diplomacy")
        view = win.views["diplomacy"]
        view.refresh()
        for _ in range(3):
            app.processEvents()
        said = " ".join(lab.text() for lab in view.findChildren(QLabel)
                        if lab.text())
        win.close()
        assert "Levies off your ground" in said, (
            f"the purse panel never mentions the levy: {said[:400]}")
        from ..core.util import credits as cr
        assert cr(purse.levies) in said, (
            f"{cr(purse.levies)} taken off your ground and the panel says "
            "otherwise")
        return (f"the panel reads \"Levies off your ground {cr(purse.levies)}\" "
                "beside the wharfage")
