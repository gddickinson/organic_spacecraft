"""The bench after the tree: standing programmes, and what a finding buys.

The tech tree is sixty-two nodes and 28,790 points end to end, and the game is
explicitly built to carry on past every one of its ten endings. So there is a
day when the last node lights and the bench has nothing to do — and measured on
a generous rate that day was 2,014, after which the ship accrued **146,040
research points over ten years that bought nothing at all**. Every laboratory,
every CHORUS node, the `research` bonus on eight technologies and the whole
survey economy behind them fed a number `ui/tech_view.py` displayed and no code
could ever spend.

`sim/programmes.py` gives it somewhere to go. A programme opens when its branch
is exhausted, never finishes, and completes rounds that cost more each time.
Each round yields a **finding**, and a finding buys standing or credits and
never a better hull — an endgame bench that improved the ship would only
inflate it.

The claims:

- **Nothing accrues that cannot be spent.** The general one, and the whole
  reason this exists.
- **Every round costs more than the last**, so a finished tree is not a
  fountain, and a finding is worth what its round cost.
- **All three doors are live and none is dominated**: filing wins with the
  power you file with, publishing wins across the sector, selling pays money.
- **Every point of standing and every credit came from a consumed finding.**
- **A programme opens only when its branch is complete**, and every branch has
  one.
- **The screen says which of the two situations it is.**
- **Findings survive a save.**
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.programmes import PROGRAMMES, PROGRAMMES_BY_ID, ROUND_GROWTH
from ..data.tech import TECH
from ..sim import programmes as prog_sim
from ..sim import research as research_sim
from .harness import Suite


def _finished(seed: str, programme: str | None = "cognition"):
    """A chronicle whose tree is done, with the bench on a programme."""
    game = new_game(seed)
    game.research.unlocked = [t.id for t in TECH]
    game.research.current = None
    game.recompute()
    if programme is not None:
        assert prog_sim.set_programme(game, programme), programme
    return game


def _one_branch(seed: str, branch: str):
    """A chronicle with exactly one branch exhausted, and no more."""
    game = new_game(seed)
    for tech in TECH:
        if tech.branch == branch and tech.id not in game.research.unlocked:
            game.research.unlocked.append(tech.id)
    game.recompute()
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing accrues on a finished tree that cannot be spent")
    def _():
        # The general one. Before this, `research.banked` grew for ever once
        # `researchable` came back empty — 146,040 points over ten years, on a
        # screen that displayed the figure.
        game = _finished("spendable")
        for _ in range(40):
            game.advance_days(30)
        live = prog_sim.state(game)
        rounds = sum(int(n) for n in live.rounds.values())

        assert game.research.banked < 1.0, (
            f"{game.research.banked:,.0f} points banked with the tree "
            "finished — banking is where they went to die")
        assert rounds >= 2, (
            f"1,200 days on a finished tree and only {rounds} round(s) of "
            "standing work")
        assert len(live.findings) == rounds, (live.findings, rounds)

        # And with the bench standing down the points *wait* rather than
        # vanishing: put it back on something and they are all still there.
        idle = _finished("idle", programme=None)
        for _ in range(20):
            idle.advance_days(30)
        waiting = idle.research.spare
        assert waiting > 100, (
            f"the bench stood down for 600 days and only {waiting:.0f} points "
            "are waiting — the rest went nowhere")
        assert prog_sim.state(idle).findings == []
        prog_sim.set_programme(idle, "statecraft")
        idle.advance_days(1)
        assert prog_sim.state(idle).findings, (
            "put back on a programme, and the waiting points bought nothing")
        return (f"{rounds} rounds and {len(live.findings)} findings in 1,200 "
                f"days; {waiting:,.0f} points held for a bench standing down")

    @check("every round costs more than the last, and pays more")
    def _():
        # What stops a finished tree being a points fountain.
        game = _finished("rising")
        seen = []
        for _ in range(8):
            cost = prog_sim.round_cost(game, "cognition")
            worth = prog_sim.worth_of_round(cost)
            seen.append((cost, worth))
            # Complete the round exactly, without the calendar.
            found = prog_sim.tick(game, cost)
            assert found is not None, (cost, prog_sim.state(game).progress)
            assert abs(found.worth - worth) < 0.01, (found.worth, worth)
        for (a, _wa), (b, _wb) in zip(seen, seen[1:]):
            assert b > a * 1.05, (
                f"round costs go {[round(c) for c, _w in seen]} — a later "
                "round is not dearer, so the bench prints findings")
        first, last = seen[0][0], seen[-1][0]
        assert last / first > ROUND_GROWTH ** 5, (first, last)
        # And the worth follows the cost rather than a second table.
        for cost, worth in seen:
            assert worth == prog_sim.worth_of_round(cost)
        return (f"eight rounds from {first:,.0f} to {last:,.0f} points, "
                f"paying {seen[0][1]:g} to {seen[-1][1]:g}")

    @check("all three doors are live and none is dominated")
    def _():
        # The choice has to be real. Filing must beat publishing *with the
        # power you file with*, and publishing must beat filing *summed across
        # the sector* — otherwise one of them is decoration.
        game = _finished("doors")
        game.advance_days(400)
        live = prog_sim.state(game)
        assert live.findings, "no finding to place"
        found = live.findings[0]

        openly = prog_sim.preview(game, found, "publish")
        assert openly["ok"], openly
        spread = dict(openly["standing"])
        assert len(spread) >= 4, spread

        best = max(prog_sim.powers(game),
                   key=lambda w: prog_sim.interest(found.programme, w))
        filed = prog_sim.preview(game, found, "file", best)
        mine = next(g for w, g in filed["standing"] if w == best)

        assert mine > spread[best] * 1.5, (
            f"filing with the power that cares most gives {mine:.1f} against "
            f"{spread[best]:.1f} for publishing — filing is pointless")
        assert sum(spread.values()) > sum(g for _w, g in filed["standing"]), (
            f"publishing gives {sum(spread.values()):.1f} across the sector "
            f"against {sum(g for _w, g in filed['standing']):.1f} for filing "
            "— publishing is pointless")

        sold = prog_sim.preview(game, found, "sell")
        assert sold["credits"] > 0 and not sold["standing"], sold

        # Filing with a power that does not care is a poor deal, which is what
        # makes *which* power a decision rather than a formality.
        worst = min(prog_sim.powers(game),
                    key=lambda w: prog_sim.interest(found.programme, w))
        thin = prog_sim.preview(game, found, "file", worst)
        least = next(g for w, g in thin["standing"] if w == worst)
        assert mine > least * 1.8, (
            f"the power that cares most gives {mine:.1f} and the one that "
            f"cares least {least:.1f} — the subject does not matter")

        # **And filing is partisan.** This is the whole difference between
        # filing and publishing, and nothing was asserting it: a mutation that
        # set `FILE_RIVAL_COST` to zero passed every check above, because at a
        # fresh chronicle's neutral relations `allegiance.offended_by` returns
        # nobody and there is nothing to see. It has to be looked for where the
        # rule actually applies — in a sector that has taken sides.
        from ..sim import allegiance
        from ..sim import diplomacy as dip
        rowdy = _finished("partisan")
        for _ in range(30):
            rowdy.advance_days(30)
        loose = prog_sim.state(rowdy).findings
        assert loose, "no finding in the partisan chronicle"
        # Make somebody care: a power at odds with another minds you serving it.
        for power in dip.POWERS:
            rowdy.rep[power] = 70
        dip.shift_relation(rowdy, "charter", "freeholds", -60)
        rowdy.recompute()
        with_rivals = [p for p in dip.POWERS if allegiance.offended_by(rowdy, p)]
        assert with_rivals, (
            "nobody in the sector minds anybody, so the partisan cost cannot "
            "be measured here")
        target = with_rivals[0]
        plan = prog_sim.preview(rowdy, loose[0], "file", target)
        gain = next(g for w, g in plan["standing"] if w == target)
        paid = -sum(g for _w, g in plan["standing"] if g < 0)
        assert paid > 0, (
            f"filing with the {target} costs nothing with anybody else, in a "
            "sector where they have declared enemies — filing and publishing "
            "are the same act")
        assert paid < gain, (
            f"filing with the {target} gains {gain:.1f} and costs {paid:.1f} "
            "elsewhere — nobody would ever file")
        return (f"file {best} {mine:+.1f} · publish {sum(spread.values()):+.1f} "
                f"over four · sell {sold['credits']:,} · the least interested "
                f"power offers {least:+.1f}")

    @check("every point of standing and credit came from a spent finding")
    def _():
        # The accounting claim. If `spend` ever grows a path that pays without
        # consuming, or a preview that promises what the act does not do, the
        # two totals part company here.
        promised_rep, moved_rep = 0.0, 0.0
        promised_cash, moved_cash = 0, 0
        spent = 0
        for index, door in enumerate(("file", "publish", "sell", "file")):
            game = _finished(f"ledger-{index}")
            for _ in range(30):
                game.advance_days(30)
            live = prog_sim.state(game)
            assert live.findings, "nothing found to spend"
            for found in list(live.findings):
                power = prog_sim.powers(game)[index % 4] if door == "file" \
                    else None
                plan = prog_sim.preview(game, found, door, power)
                before_rep = sum(game.rep.get(p, 0)
                                 for p in prog_sim.powers(game))
                before_cash = game.credits
                out = prog_sim.spend(game, found, door, power)
                assert out.get("ok"), out
                spent += 1
                promised_rep += sum(g for _w, g in plan["standing"])
                promised_cash += plan["credits"]
                moved_rep += (sum(game.rep.get(p, 0)
                                  for p in prog_sim.powers(game)) - before_rep)
                moved_cash += game.credits - before_cash
                # And it is gone: the same finding cannot be spent twice.
                again = prog_sim.spend(game, found, door, power)
                assert not again.get("ok"), (
                    "a finding was spent twice — the door does not consume it")
            assert not live.findings, live.findings

        assert spent >= 4, spent
        assert abs(promised_rep - moved_rep) < 0.5, (
            f"{promised_rep:.1f} of standing promised against {moved_rep:.1f} "
            "actually moved")
        assert promised_cash == moved_cash, (promised_cash, moved_cash)
        return (f"{spent} findings placed: {promised_rep:+.1f} standing and "
                f"{moved_cash:,} credits promised, and exactly that moved")

    @check("a programme opens only when its branch is finished")
    def _():
        # And every branch has one, so no amount of specialising leaves a
        # captain with a finished branch and nothing to do in it.
        fresh = new_game("gated")
        assert prog_sim.available(fresh) == [], (
            "programmes are open on day one, before anything is finished")

        branches = {p.branch for p in PROGRAMMES}
        tree_branches = {t.branch for t in TECH}
        assert tree_branches <= branches, (
            f"branches with no standing programme: "
            f"{sorted(tree_branches - branches)}")

        # One branch finished opens exactly its own programme.
        for spec in PROGRAMMES[:4]:
            game = _one_branch(f"gate-{spec.id}", spec.branch)
            open_ids = [p.id for p in prog_sim.available(game)]
            assert spec.id in open_ids, (spec.id, open_ids)
            assert prog_sim.set_programme(game, spec.id)
            # And a programme whose branch is *not* finished is refused.
            other = next(p for p in PROGRAMMES if p.branch != spec.branch)
            assert not prog_sim.set_programme(game, other.id), (
                f"{other.id} was accepted with {other.branch} unfinished")
        return (f"{len(PROGRAMMES)} programmes over {len(branches)} branches; "
                "none open before its own branch is done")

    @check("the research screen says which situation it is in")
    def _():
        # It said "pick something below" in both, and with the tree finished
        # there is nothing below to pick and the points are not waiting for a
        # choice — they are going to the bench.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication

        from ..ui.tech_view import TechView
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None

        said = {}
        for name, game in (("open", new_game("screen-open")),
                           ("done", _finished("screen-done"))):
            game.research.current = None
            win = MainWindow(game)
            win.toast = lambda *a, **k: None
            view = TechView(win)
            panel = view._current(game.ship_stats.research + 0.25)
            said[name] = panel.title() if hasattr(panel, "title") else ""
            text = []

            def gather(widget):
                for kid in widget.findChildren(object):
                    got = getattr(kid, "text", None)
                    if callable(got):
                        try:
                            text.append(got())
                        except Exception:
                            pass
            gather(panel)
            said[name] = " ".join(t for t in text if isinstance(t, str))
            win.close()

        assert "Pick something below" in said["open"], said["open"][:200]
        assert "Pick something below" not in said["done"], (
            "with every technology known the screen still tells the captain to "
            "pick one from the list below")
        assert "standing programme" in said["done"], said["done"][:200]
        return ("an unfinished tree says pick one; a finished one says where "
                "the points go instead")

    @check("findings and rounds survive a save")
    def _():
        import json

        from ..core.save import decode, encode

        game = _finished("persist")
        for _ in range(30):
            game.advance_days(30)
        live = prog_sim.state(game)
        assert live.findings and live.rounds, (live.findings, live.rounds)
        before = [(f.programme, f.round, f.day, f.worth) for f in live.findings]
        rounds = dict(live.rounds)

        back = decode(json.loads(json.dumps(encode(game))))
        after = prog_sim.state(back)
        assert [(f.programme, f.round, f.day, f.worth)
                for f in after.findings] == before, after.findings
        assert dict(after.rounds) == rounds, (after.rounds, rounds)
        assert after.current == live.current

        # And a reloaded finding can still be placed.
        out = prog_sim.spend(back, after.findings[0], "sell")
        assert out.get("ok"), out
        return (f"{len(before)} findings and {sum(rounds.values())} rounds "
                "came back, and one of them sold")
