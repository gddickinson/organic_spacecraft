"""The rules the screens used to hold, held by the sim — and the screens kept out.

Review item #28 found them still in `ui/`: the rumour desk and the hiring
board drew their own luck, shore leave moved the calendar from a button
handler, paying an officer off assigned `game.officers`, the drydock priced
its own repair, and two dozen acts were written to the chronicle by whatever
screen happened to press them — so the same act by the bridge or a check went
unrecorded. Each is a sim function now, answering `{ok, why, text}` and
writing its own line.

Two of those were worse than misplaced. `game.rng` advances the save's seed
on every call, so a desk that drew it on every redraw showed **a different
board every time it was drawn** (measured: 20 ports of 20, on a second draw
the same day) and made merely looking at a port move the luck of everything
rolled after it.

The structural checks at the bottom are the ratchet: a new `add_log` or a new
`.rng(` in `ui/` has to be argued onto a list with its reason beside it.
"""

from __future__ import annotations

import ast
import pathlib
from types import SimpleNamespace

from ..core.state import new_game
from .harness import Suite

UI = pathlib.Path(__file__).resolve().parent.parent / "ui"

#: `add_log` calls a screen may still make, by (file, function), and why.
LOG_ALLOWED = {
    ("app.py", "main"): "a note about how this window was opened (under a "
                        "bridge, briefing skipped) — a fact about the session, "
                        "not an act in the chronicle",
}

#: `.rng(` draws a screen may still take, by (file, function). Each is an
#: act's own roll — drawn once per press and handed straight into the sim
#: act — not a board redrawn on every refresh, which is the defect this suite
#: exists for. Defaulting each to a draw inside its sim act is mechanical and
#: left for the next pass rather than done blind across seven screens.
RNG_ALLOWED = {
    ("battle_view.py", "begin"), ("battle_view.py", "_finish"),
    ("dig_view.py", "_work"),
    ("expedition_view.py", "_move"), ("expedition_view.py", "_attempt"),
    ("expedition_view.py", "_shelter"), ("expedition_view.py", "_rest"),
    ("minigame_view.py", "begin"), ("minigame_view.py", "_auto_pass"),
    ("minigame_view.py", "_auto_all"), ("minigame_view.py", "_fire"),
    ("minigame_view.py", "_customs"),
    ("transit_view.py", "_stand"), ("transit_view.py", "_choose"),
    ("window.py", "battle_act"),
}


def _calls(attr: str) -> set:
    """Every `<x>.<attr>(...)` in `ui/`, as (file, enclosing function)."""
    found = set()
    for path in sorted(UI.glob("*.py")):
        tree = ast.parse(path.read_text())

        def walk(node, fn, path=path):
            for child in ast.iter_child_nodes(node):
                inner = (child.name if isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn)
                if (isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and child.func.attr == attr):
                    found.add((path.name, inner))
                walk(child, inner)
        walk(tree, "<module>")
    return found


def _at_port(seed: str):
    game = new_game(seed)
    port = next(s for s in game.galaxy.systems if s.port)
    game.location_id = port.id
    game.recompute()
    return game, port


def _answered(res: dict, what: str) -> None:
    for key in ("ok", "why", "text"):
        assert key in res, f"{what} answered without {key!r}: {sorted(res)}"


def _logged(game, text: str, what: str) -> None:
    assert text, f"{what} said nothing"
    assert any(line[1] == text for line in game.log[-6:]), (
        f"{what} did not write its line: {text!r}")


def run(suite: Suite) -> None:
    check = suite.check

    @check("the rumour desk is the same all month, and looking costs no luck")
    def _():
        from ..sim import rumours as rumour_sim
        same = 0
        for i in range(20):
            game, port = _at_port(f"uirules-rumour-{i}")
            seed_before = game.rng_seed
            first = [(r.kind, r.system_id, r.true)
                     for r in rumour_sim.board(game, port)]
            again = [(r.kind, r.system_id, r.true)
                     for r in rumour_sim.board(game, port)]
            assert first == again, f"seed {i}: the board reshuffled on a redraw"
            assert game.rng_seed == seed_before, (
                "drawing the desk advanced the chronicle's luck")
            same += 1
        return f"{same} ports of {same} show one board all day, seed untouched"

    @check("the hiring board is the quay's, whenever it is first looked at")
    def _():
        from ..sim import crew as crew_sim
        game, port = _at_port("uirules-berths")
        seed_before = game.rng_seed
        first = [(o.name, o.role, o.level) for o in crew_sim.pool_at(game, port)]
        game.rng("something else entirely")        # the chronicle moves on
        game.rng("and again")
        later = [(o.name, o.role, o.level) for o in crew_sim.pool_at(game, port)]
        assert first and first == later, "the board depends on when it was asked"
        # Signed on, and gone from the board.
        game.credits = 90_000
        game.officers = []
        hand = crew_sim.pool_at(game, port)[0]
        assert crew_sim.hire(game, hand)["ok"]
        still = [(o.name, o.role) for o in crew_sim.pool_at(game, port)]
        assert (hand.name, hand.role) not in still, "a signed hand is still offered"
        return f"{len(first)} hands, the same board twice, the signed one gone"

    @check("shore leave is a week, taken through the sim")
    def _():
        from ..sim import crew as crew_sim
        game, _port = _at_port("uirules-leave")
        day = game.day
        before = [o.loyalty for o in game.officers]
        res = crew_sim.shore_leave(game)
        _answered(res, "shore leave")
        assert res["ok"], res
        assert game.day == day + crew_sim.SHORE_LEAVE_DAYS == day + 7, (
            f"{game.day - day} days passed, not seven")
        after = [o.loyalty for o in game.officers]
        assert after != before, "the bridge felt nothing"
        _logged(game, res["text"], "shore leave")
        game.officers = []
        assert not crew_sim.shore_leave(game)["ok"], "leave for an empty bridge"
        return f"day {day} → {game.day}, loyalty moved, and the log says so"

    @check("paying an officer off is the sim's, and the chronicle hears it")
    def _():
        from ..sim import crew as crew_sim
        game, _port = _at_port("uirules-payoff")
        leaving = game.officers[0]
        res = crew_sim.pay_off(game, leaving)
        _answered(res, "paying off")
        assert res["ok"] and leaving not in game.officers, res
        _logged(game, res["text"], "paying off")
        again = crew_sim.pay_off(game, leaving)
        assert not again["ok"] and again["why"], "paid off somebody not aboard"
        return f"{leaving.name} ashore; a second pay-off refused with a reason"

    @check("the drydock prices its own repair, and charges what it quoted")
    def _():
        import inspect
        from ..sim import services as services_sim
        # No door for a price brought from outside: the screen used to pass
        # its own figure in, and the till charged whatever it was handed.
        assert list(inspect.signature(services_sim.repair).parameters) == \
            ["game"], "repair takes a price from its caller again"
        game, _port = _at_port("uirules-dock")
        refused = services_sim.repair(game)
        assert not refused["ok"] and refused["why"], "repaired an undamaged hull"
        game.ship.layers[0].hp = max(0, game.ship.layers[0].hp - 12)
        game.credits = 50_000
        quote = services_sim.repair_quote(game)
        res = services_sim.repair(game)
        _answered(res, "repair")
        assert res["ok"] and res["cost"] == quote["cost"], (res, quote)
        assert game.credits == 50_000 - quote["cost"], "the till charged another figure"
        _logged(game, res["text"], "repair")
        return f"{quote['damage']:.0f} points quoted at {quote['cost']:,} and charged it"

    @check("each moved act writes its own line to the chronicle")
    def _():
        from ..sim import berthing as berth_sim
        from ..sim import commitments
        from ..sim import contracts as contract_sim
        from ..sim import dormancy
        from ..sim import engage as engage_sim
        from ..sim import flightdeck as deck_sim
        from ..sim import freeflight as free_sim
        from ..sim import hostiles as hostiles_sim
        from ..sim import minigames as mg
        from ..sim import track as track_sim
        acts = []

        game, port = _at_port("uirules-acts")
        job = contract_sim.board_for(game, port)[0]
        for what, res in (("taking a contract",
                           commitments.take_contract(game, job)),
                          ("abandoning it",
                           commitments.abandon_contract(game, job))):
            _answered(res, what)
            assert res["ok"], res
            _logged(game, res["text"], what)
            acts.append(what)
        assert job.failed, "abandoned and still open"

        hull = SimpleNamespace(hull_id="uirules-hull", name="Kestrel", kind="hull")
        for what in ("marking a hull", "clearing the mark"):
            res = hostiles_sim.toggle(game, hull)
            _answered(res, what)
            _logged(game, res["text"], what)
            acts.append(what)
        assert not hostiles_sim.is_marked(game, hull.hull_id)

        res = engage_sim.fire_on(game, None, hull)
        _answered(res, "a refused trigger")
        assert not res["ok"] and res["battle"] is None
        _logged(game, res["why"], "a refused trigger")
        acts.append("a refused trigger")

        mg.begin_decoding(game, "Test Culture", "vent_symbiosis")
        game.decoding.won = game.decoding.over = True
        res = mg.finish_decoding(game)
        _answered(res, "closing the bench")
        _logged(game, res["text"], "closing the bench")
        assert game.decoding is None and game.decoding_tech is None
        acts.append("closing the bench")

        game.research.unlocked.append("trehalose")
        game.stores.update({"biomass": 600, "trehalose": 600, "magnetite": 200})
        assert dormancy.put_under(game, "vitrify",
                                  dormancy.most_that_can_sleep(game))["ok"]
        game.advance_days(60)
        res = dormancy.bring_up(game)
        _answered(res, "waking the sleepers")
        assert res["ok"] and game.sleep is None, res
        for _kind, text in res["lines"]:
            _logged(game, text, "waking the sleepers")
        acts.append("waking the sleepers")

        conn, why = free_sim.begin(game)
        assert conn is not None, why
        game.conn = conn
        seen = track_sim.contacts(game)
        res = deck_sim.lay_course(game, conn, seen[0])
        _answered(res, "laying a course")
        assert conn.mark == seen[0].name
        _logged(game, res["text"], "laying a course")
        deck_sim.drop_course(conn)
        assert conn.mark == ""
        res = berth_sim.stand_down(game, conn)
        _answered(res, "securing from the conn")
        assert conn.landed, "stood down and not billed"
        _logged(game, res["text"], "securing from the conn")
        acts.append("laying a course and securing")
        return f"{len(acts)} acts, each in the log by its own door"

    @check("no screen writes the chronicle for an act, outside the list")
    def _():
        found = _calls("add_log")
        extra = sorted(found - set(LOG_ALLOWED))
        assert not extra, f"a screen writes the log itself: {extra}"
        stale = sorted(set(LOG_ALLOWED) - found)
        assert not stale, (f"allowed but no longer there — take the row "
                           f"out: {stale}")
        return f"{len(found)} left, each with its reason on the list"

    @check("no screen draws luck on a redraw, and the act-time draws are listed")
    def _():
        found = _calls("rng")
        for panel in ("rumours_panel.py", "berths_panel.py", "port_view.py",
                      "ship_view.py", "fire_panel.py"):
            assert not any(f == panel for f, _fn in found), (
                f"{panel} draws from game.rng again")
        extra = sorted(found - RNG_ALLOWED)
        assert not extra, f"a new draw in the interface: {extra}"
        stale = sorted(RNG_ALLOWED - found)
        assert not stale, f"allowed but no longer there — take the row out: {stale}"
        return f"{len(found)} act-time draws, none on a redraw"
