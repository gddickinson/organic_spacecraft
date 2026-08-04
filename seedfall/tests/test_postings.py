"""The contract board: whether the work on it can be done, and where it is.

`_pick_target` was documented as choosing a system "reachable in principle"
and the whole of its test was `bloom < 0.4`. Reachability is transitive and
nothing checked it, so the board offered work wherever the sector happened to
have a star.

Measured on fresh chronicles: **65% of every targeted posting named a system
outside the reachable component**. 15 of 42 systems can be flown to at the
opening drive; deliver ran 69% unreachable, survey 63%, expedition 57%. Taking
one and letting it lapse costs standing with the issuer, and the card said
nothing about where the work was — reward, deadline, standing, and no
destination at all.

Both halves are fixed here. The generator asks `reach.component`, which is the
same answer the chart gives. The card names the system and what the flight to
it costs, so a posting that is merely *demanding* still reads as demanding.

The claims:

- **Every posting names somewhere the hull can get to.** The general one.
- **And the deadline covers the flight** — one way, because that is what
  finishing it takes.
- **The card says where the work is.**
- **A hull walled into one system still gets a board.**
- **`route_to` agrees with `component`, and with what flying it costs.**
"""

from __future__ import annotations

import collections

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import contracts, reach as reach_sim
from ..sim.actions import jump_quote
from .harness import Suite


def _boards(count: int = 30):
    """(game, contracts) for a spread of fresh chronicles."""
    out = []
    for trial in range(count):
        game = new_game(f"post{trial}")
        out.append((game, contracts.generate(RNG(f"gen{trial}"),
                                             game, game.system)))
    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("every posting names somewhere the hull can actually get to")
    def _():
        # The general question. `bloom < 0.4` was the whole of the old test,
        # and two postings in three pointed outside the component.
        stray = collections.Counter()
        targeted = collections.Counter()
        for game, board in _boards():
            within = reach_sim.component(game)
            for c in board:
                if c.target_system is None:
                    continue
                targeted[c.kind] += 1
                if c.target_system not in within:
                    stray[c.kind] += 1
        assert sum(targeted.values()) > 50, dict(targeted)
        assert not stray, (
            "postings point outside the reachable component: "
            + ", ".join(f"{k} {v}/{targeted[k]}" for k, v in stray.items()))
        return (f"{sum(targeted.values())} targeted postings across "
                f"{len(targeted)} kinds, every one reachable")

    @check("the deadline covers the flight to the work")
    def _():
        # One way: `check()` completes a delivery, a survey and a ground
        # contract on arrival. Judging it round-trip flagged three postings
        # that are in fact perfectly doable, which is a worse answer than
        # none — a warning nobody needs teaches captains to ignore warnings.
        slack = []
        for game, board in _boards():
            for c in board:
                leg = contracts.trip(game, c)
                if leg is None or leg["hops"] is None:
                    continue
                spare = c.days_left(game.day) - leg["days"]
                # The flag the card colours itself from, checked against the
                # arithmetic rather than trusted. Asserting only `in_time` and
                # then computing slack separately left the flag itself
                # unverified — forcing it True broke nothing.
                assert leg["in_time"] == (spare >= 0), (
                    f"{c.kind} to {leg['name']}: in_time={leg['in_time']} "
                    f"with {leg['days']} days of flying against "
                    f"{c.days_left(game.day)} on the clock")
                assert leg["in_time"], (
                    f"{c.kind} to {leg['name']}: {leg['days']} days of flying "
                    f"against {c.days_left(game.day)} days on the clock")
                slack.append(spare)
        assert len(slack) > 50, len(slack)

        # Every real posting is comfortably in time, so "in_time is always
        # True" and "in_time is right" look identical across the whole board.
        # One deliberately impossible deadline separates them.
        game, board = _boards(1)[0]
        far = next(c for c in board
                   if c.target_system is not None
                   and (contracts.trip(game, c) or {}).get("hops"))
        was = far.deadline
        try:
            far.deadline = game.day + 1
            tight = contracts.trip(game, far)
            assert tight["days"] > 1, tight
            assert not tight["in_time"], (
                f"a posting {tight['days']} days away with one day on the "
                "clock still reads as makeable")
        finally:
            far.deadline = was
        assert contracts.trip(game, far)["in_time"], "restoring the deadline"

        assert min(slack) >= 10, (
            f"the tightest posting leaves {min(slack)} days spare after the "
            "flight, which is not a contract, it is a formality")
        return (f"{len(slack)} postings, tightest leaves {min(slack)} days "
                f"spare, median {sorted(slack)[len(slack)//2]}")

    @check("the board says where the work is and what the trip costs")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        shown = 0
        for trial in range(6):
            game = new_game(f"card{trial}")
            win = MainWindow(game)
            win.toast = lambda *a, **k: None
            win.go("port")
            view = win.views["port"]
            view.tab = "contracts"
            view.refresh()
            for _ in range(3):
                app.processEvents()
            texts = [lab.text() for lab in view.findChildren(QLabel)
                     if lab.text()]
            # The posted board is the sim's, through its one door —
            # `all_open` is what you have already taken, which is why the
            # first version of this check found nothing on screen at all.
            posted = contracts.board_for(game, game.system)
            targeted = [c for c in posted if c.target_system is not None]
            for c in targeted:
                leg = contracts.trip(game, c)
                if leg is None or leg["hops"] in (None, 0):
                    continue
                assert any(leg["name"] in t and "jump(s)" in t for t in texts), (
                    f"no card names {leg['name']} and the flight to it")
                assert any(f"{leg['days']} days each way" in t for t in texts), (
                    f"the card never states the {leg['days']} days to "
                    f"{leg['name']}")
                shown += 1
            win.close()
            if shown >= 4:
                break
        assert shown >= 4, f"only {shown} destinations were checked on screen"
        return f"{shown} postings named their destination and its flight"

    @check("a hull walled into one system still gets a board")
    def _():
        # The fallback matters: restricting to the component must not empty
        # the board for a captain in a pocket. Driven by replacing what
        # `_pick_target` asks rather than by faking `ship_stats`, which is
        # derived and would be rebuilt out from under the test.
        game = new_game("pocket")
        here = game.system.id
        original = reach_sim.component
        try:
            reach_sim.component = lambda g, jump=None, start=None: {here}
            board = contracts.generate(RNG("pocket"), game, game.system)
            assert board, "a walled-in captain was offered no work at all"
            strays = [c for c in board
                      if c.target_system is not None
                      and c.target_system != here]
            assert not strays, (
                f"{len(strays)} postings point out of the pocket")
        finally:
            reach_sim.component = original
        return f"{len(board)} postings, all of them at home"

    @check("a worked-out board fills again on the harbour's clock")
    def _():
        # `ui/board_panel.build` was the only caller of `generate` in the
        # codebase and it cached the result for the chronicle, so contracts
        # were a finite resource: a port whose board was worked out had no
        # postings for the rest of the game.
        game = new_game("board-turnover")
        sysm = next(s for s in game.galaxy.systems if s.port)
        game.location_id = sysm.id
        first = contracts.board_for(game, sysm)
        assert first, "the opening board posted nothing"
        game.boards[str(sysm.id)]["posts"] = []          # worked out
        assert not contracts.board_for(game, sysm), (
            "an emptied board refilled before the turnover")
        level = sysm.port.level
        turnover = max(30, contracts.BOARD_TURNOVER
                       - contracts.BOARD_TURNOVER_PER_LEVEL * level)
        game.day += turnover
        again = contracts.board_for(game, sysm)
        assert again, "the turnover posted nothing"
        # And an old save's bare list is adopted, not thrown away.
        game.boards[str(sysm.id)] = list(again)
        adopted = contracts.board_for(game, sysm)
        assert adopted == list(again), "a migrated board lost its postings"
        assert isinstance(game.boards[str(sysm.id)], dict), (
            "the migrated board was not stamped")
        return (f"{len(first)} posted, worked out, {len(again)} fresh after "
                f"{turnover} days; an old save's board adopted whole")

    @check("route_to agrees with component, and with what flying it costs")
    def _():
        game = new_game("routes")
        within = reach_sim.component(game)
        checked = 0
        for system in game.galaxy.systems:
            route = reach_sim.route_to(game, system.id)
            if system.id in within:
                assert route is not None, (
                    f"{system.name} is in the component and has no route")
                assert route["hops"] >= 0 and route["days"] >= 0, route
            else:
                assert route is None, (
                    f"{system.name} is outside the component and route_to "
                    f"returned {route}")
            checked += 1
        # And a single hop must cost exactly what the helm would charge for it.
        singles = [s for s in game.galaxy.systems
                   if s.id in within
                   and (reach_sim.route_to(game, s.id) or {}).get("hops") == 1]
        assert singles, "no system is one hop away in this seed"
        for system in singles:
            said = reach_sim.route_to(game, system.id)["days"]
            quoted = jump_quote(game, system)["days"]
            assert said == quoted, (
                f"{system.name}: route_to says {said} days, the helm quotes "
                f"{quoted}")
        return (f"{checked} systems agree with the component; "
                f"{len(singles)} single hops match the helm exactly")
