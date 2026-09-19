"""The Assembly: four powers in one room, and a captain who can move the room.

What the suite holds it to, each performed rather than asserted:

- it sits on its schedule, at each capital in turn, and what it tables is the
  sitting's own — looking at it, from any screen, changes nothing;
- the forecast is the vote when nothing changes, in the chamber or out of it;
- every lobby act does exactly what its preview said, and none gains standing;
- every effect key moves the number its reader computes (`assembly_probes`),
  and stops on the day the instrument lapses;
- the count moves the matrix by the rule, and a captain who brokers raises it
  where one who stays away does not;
- a chronicle saved with an agenda open resumes in a fresh process.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.assembly import (EFFECTS, RESOLUTIONS, SEAT_ORDER, SESSION_DAYS,
                             SESSION_JITTER)
from ..sim import assembly, assembly_lobby as lob, assembly_session as sess
from ..sim import assembly_vote as vote, diplomacy as dip, grudge
from . import assembly_probes as probes
from .harness import Suite


def _provisioned(game) -> None:
    """The captain is a clock here: fed and solvent, so the sector gets its
    years (see `test_war._provisioned`)."""
    game.credits = max(game.credits, 500_000)
    game.ship.cargo["biomass"] = max(game.ship.cargo.get("biomass", 0), 300)


def _until(game, day: int) -> None:
    while game.day < day and not game.dead:
        _provisioned(game)
        game.advance_days(1)


def _announced(seed: str):
    """A sector with the first agenda published and the sitting to come."""
    game = probes.sector(seed)
    state = assembly.ensure(game)
    _until(game, state.next_day - 20)
    assert state.announced and state.agenda, "nothing was tabled"
    return game, state


def _mean(game) -> float:
    P = dip.POWERS
    return sum(dip.relation(game, a, b) for i, a in enumerate(P)
               for b in P[i + 1:]) / 6


def run(suite: Suite) -> None:
    check = suite.check

    @check("it sits on schedule, at each capital in turn")
    def _():
        game = probes.sector("assembly-seat")
        state = assembly.ensure(game)
        seats, days, last = [], [], 0
        for _ in range(4):
            power, system = sess.seat(game, state)
            assert system is not None and system.port.faction == power
            assert system.port.capital or not any(
                s.port and s.port.capital and s.port.faction == power
                for s in game.galaxy.systems), f"{power} sat off its capital"
            due = state.next_day
            _until(game, due)
            assert state.history[-1]["day"] == due, "it sat on the wrong day"
            assert state.history[-1]["seat"] == power
            seats.append(power)
            days.append(due - last)
            last = due
        gaps = days[1:]
        assert all(abs(g - SESSION_DAYS) <= SESSION_JITTER for g in gaps), gaps
        assert seats == [p for p in SEAT_ORDER if sess.seat_system(game, p)][:4]
        return f"sat at {', '.join(seats)}; gaps {gaps} days"

    @check("the agenda is the sitting's own, and looking at it draws no luck")
    def _():
        looked, _s = _announced("assembly-same")
        still, _s = _announced("assembly-same")
        before = looked.rng_seed
        for item in _s.agenda:
            vote.forecast(looked, item.key)
            vote.forecast(looked, item.key, present=True)
            for act in lob.ACTS:
                lob.preview(looked, act, item.sponsor, item.key)
            lob.speech(looked, item.key)
        again = sess.draw(looked, assembly.state(looked))
        assert looked.rng_seed == before, "a forecast drew from game.rng"
        keys = [t.key for t in assembly.state(looked).agenda]
        assert keys == [t.key for t in assembly.state(still).agenda]
        assert [t.key for t in again] == keys, "a redraw tabled otherwise"
        return f"{len(keys)} motions, the same from every look: {keys}"

    @check("the forecast is the vote when nothing changes")
    def _():
        told = seen = 0
        for seed in ("assembly-fc1", "assembly-fc2", "assembly-fc3"):
            game, state = _announced(seed)
            _until(game, state.next_day - 1)
            ahead = {t.key: vote.forecast(game, t.key) for t in state.agenda}
            results = sess.sit(game)
            for r in results:
                seen += 1
                assert r["votes"] == ahead[r["key"]]["votes"], (seed, r)
                assert r["passed"] == ahead[r["key"]]["passes"], (seed, r)
                told += 1
        return f"{told} of {seen} motions voted exactly as forecast"

    @check("each lobby act does exactly what its preview said")
    def _():
        game, state = _announced("assembly-lobby")
        item = state.agenda[0]
        sponsor_sys = next(s for s in game.galaxy.systems
                           if s.faction == item.sponsor)
        game.charts_made[str(sponsor_sys.id)] = game.day
        done = []
        for act, side in (("petition", "for"), ("pay", "for"),
                          ("pay", "for"), ("leak", "against")):
            lob.position(game, item.key, side)
            who = next(p for p in dip.POWERS if p != item.sponsor)
            told = lob.preview(game, act, who, item.key)
            assert told["ok"], told["why"]
            rep = dict(game.rep)
            cash = game.credits
            row = dict(state.lobby.get(item.key, {}))
            felt = {p: grudge.direct(game, p) for p in dip.POWERS}
            lob.lobby(game, act, who, item.key)
            for p in dip.POWERS:
                moved = round(game.rep[p] - rep[p], 2)
                assert moved == told["standing"].get(p, 0.0), (act, p, moved)
                swung = round(state.lobby[item.key].get(p, 0) - row.get(p, 0), 2)
                assert swung == told["swing"].get(p, 0.0), (act, p, swung)
                grew = round(grudge.direct(game, p) - felt[p], 2)
                assert grew == told["feeling"].get(p, 0.0), (act, p, grew)
                assert moved <= 0, f"{act} gained standing with {p}"
            assert round(game.credits - cash) == told["credits"], act
            after = vote.forecast(game, item.key)
            assert after["votes"] == told["after"]["votes"], act
            done.append(act)
        assert state.spent, "the leak spent no intelligence"
        return f"{', '.join(done)}: standing, credits, swing, memory as quoted"

    @check("speaking in person swings the vote, and staying away does not")
    def _():
        shifted = 0
        for there in (True, False):
            game, state = _announced("assembly-speak")
            _until(game, state.next_day - 1)
            for item in state.agenda:
                lob.position(game, item.key, "for")
            _p, seat = sess.seat(game, state)
            if there:
                game.location_id = seat.id
            else:
                game.location_id = next(s.id for s in game.galaxy.systems
                                        if s.id != seat.id)
            ahead = {t.key: vote.forecast(game, t.key) for t in state.agenda}
            away = {t.key: vote.forecast(game, t.key, present=False)
                    for t in state.agenda}
            for item in state.agenda:
                for p in dip.POWERS:
                    gap = round(ahead[item.key]["scores"][p]
                                - away[item.key]["scores"][p], 2)
                    want = lob.speech(game, item.key)[p] if there else 0.0
                    assert abs(gap - want) < 0.02, (there, p, gap, want)
                    shifted += there and gap > 0
            for r in sess.sit(game):
                assert r["votes"] == ahead[r["key"]]["votes"]
        assert shifted, "a speech moved nobody"
        return f"present: {shifted} scores raised by the speech; absent: none"

    @check("every effect key moves the number its reader computes")
    def _():
        used = {k for r in RESOLUTIONS for k in r.effects}
        assert used == set(EFFECTS), f"keys and table disagree: {used ^ set(EFFECTS)}"
        assert set(probes.READERS) == set(EFFECTS), (
            f"no probe for {sorted(set(EFFECTS) - set(probes.READERS))}")
        said = []
        for key in EFFECTS:
            live = probes.measure(key, neutral=False)
            dead = probes.measure(key, neutral=True)
            assert abs(live - dead) > 0.02 * max(abs(live), abs(dead), 1e-9), (
                f"{key}: {live} with it, {dead} without")
            said.append(f"{key} {live:.3g}/{dead:.3g}")
        return f"{len(said)} keys: " + ", ".join(said)

    @check("an instrument lapses on the stated day, and says so")
    def _():
        game = probes.sector("assembly-lapse")
        # The sector's own sittings stood down, so nothing else is enacted
        # (or this one renewed) while the term runs.
        assembly.ensure(game).next_day = 10 ** 6
        act = probes.enact(game, "open_quays", sponsor="freeholds")
        assert act.until == game.day + 180
        _until(game, act.until - 1)
        assert assembly.effect(game, "wharfage", 1.0) == 0.5, "lapsed early"
        _until(game, act.until)
        assert assembly.effect(game, "wharfage", 1.0) == 1.0, "outlived its term"
        assert not assembly.state(game).active, "still on the books"
        assert any("has lapsed" in t for _d, t, _k in game.log[-40:])
        return f"in force to day {act.until - 1}, gone on day {act.until}"

    @check("the count moves the matrix: co-voters closer, losers apart")
    def _():
        moved = vote.moves({"charter": "yes", "concordat": "yes",
                            "freeholds": "no", "sanhedrin": "abstain"},
                           {"charter": 5.0, "concordat": 3.0,
                            "freeholds": -2.5, "sanhedrin": 0.5}, True)
        assert set(moved) == {"charter|concordat", "charter|freeholds",
                              "concordat|freeholds"}, moved
        assert vote.CO_VOTE[0] <= moved["charter|concordat"] <= vote.CO_VOTE[1]
        for pair in ("charter|freeholds", "concordat|freeholds"):
            assert -vote.LOST_VOTE[1] <= moved[pair] <= -vote.LOST_VOTE[0]
        game, state = _announced("assembly-moves")
        _until(game, state.next_day - 1)
        before = {k: v for k, v in dip.ensure(game).relations.items()}
        results = sess.sit(game)
        total: dict = {}
        for r in results:
            for pair, d in r["moved"].items():
                total[pair] = total.get(pair, 0.0) + d
        for pair, d in total.items():
            got = dip.ensure(game).relations[pair] - before[pair]
            assert abs(got - d) < 0.05 or pair in _shifted(results), (pair, got, d)
        return f"rule held; a sitting moved {len(total)} pairs as counted"

    @check("a captain who brokers raises the matrix; one who stays away does not")
    def _():
        rows = []
        for seed in ("assembly-br1", "assembly-br2"):
            idle = probes.sector(seed)
            _until(idle, 3 * 365)
            broker = probes.sector(seed)
            _broker(broker, 3 * 365)
            rows.append((round(_mean(broker) - _mean(new_game(seed)), 1),
                         round(_mean(idle) - _mean(new_game(seed)), 1)))
        gain = sum(b - i for b, i in rows) / len(rows)
        assert gain >= 10.0, f"brokering bought {gain:+.1f} over staying away"
        return f"broker vs idle over three years: {rows}"

    @check("the tab fits the small window, and its buttons do what it quotes")
    def _():
        from PyQt6.QtWidgets import QPushButton
        from . import qtkit
        game, state = _announced("assembly-screen")
        win = qtkit.main_window(game, (1040, 680))
        win.go("diplomacy")
        view = win.views["diplomacy"]
        view.tab = "assembly"
        win.refresh()
        qtkit.app().processEvents()
        assert view.horizontalScrollBar().maximum() == 0, "the tab scrolls sideways"

        def press(text: str) -> None:
            hit = next(b for b in view.findChildren(QPushButton)
                       if b.text() == text and b.isEnabled())
            hit.click()
            qtkit.app().processEvents()

        item = state.agenda[0]
        press("For it")
        assert state.positions.get(item.key) == "for", "the stance did not take"
        who = next(p for p in dip.POWERS if p != item.sponsor)
        told = lob.preview(game, "pay", who, item.key)
        cash = game.credits
        press("Pay for the vote")
        assert round(game.credits - cash) == told["credits"], "paid otherwise"
        assert state.lobby[item.key][who] == told["swing"][who]
        win.close()
        return (f"1040x680 without a side scroll; stance taken and "
                f"{-told['credits']:,} paid for {told['swing'][who]:+.1f}, "
                "as quoted")

    @check("a chronicle saved with the agenda open resumes in a fresh process")
    def _():
        import tempfile
        from pathlib import Path
        from .test_persistence import _py
        save = Path(tempfile.mkdtemp(prefix="seedfall-assembly-")) / "save.json"
        wrote = _py(_WRITE, save)
        back = _py(_READ, save)
        assert wrote["ok"] and back["ok"], (wrote, back)
        for key in ("agenda", "positions", "lobby", "active", "votes", "next"):
            assert wrote[key] == back[key], (key, wrote[key], back[key])
        return (f"{len(back['agenda'])} motions, {len(back['active'])} in "
                f"force, positions and lobby intact across the restart")


def _shifted(results) -> set:
    """Pairs a passed instrument also moved by itself (a recognition's shift,
    a ceasefire's lift)."""
    from ..data.assembly import RESOLUTIONS_BY_ID
    out = set()
    for r in results:
        extra = RESOLUTIONS_BY_ID[r["res"]].extra
        if r["passed"] and extra.get("shift"):
            out.add(assembly.pair_key(*extra["shift"][:2]))
        if r["passed"] and "lift" in extra:
            out.add(r["key"].split(":", 1)[1].replace(":", "|"))
    return out


def _broker(game, until: int) -> None:
    """The fixture's broker: takes the side that does the matrix most good,
    pays where a vote can be turned, and is at the seat on the day. It flies
    nowhere — the captain is a clock here too; `broker.py` in the play-test
    flies it."""
    state = assembly.ensure(game)
    planned = -1
    while game.day < until and not game.dead:
        _provisioned(game)
        if state.announced and state.session != planned:
            planned = state.session
            for item in state.agenda:
                _best_side(game, item.key)
                for _ in range(4):
                    who = min(dip.POWERS, key=lambda p: (
                        abs(vote.forecast(game, item.key, True)["scores"][p]
                            - vote.YES_AT), p))
                    lob.lobby(game, "pay", who, item.key)
        if state.announced and game.day == state.next_day - 1:
            game.location_id = sess.seat(game, state)[1].id
        game.advance_days(1)


def _best_side(game, key: str) -> None:
    best = (-1e9, "")
    for side in ("for", "against"):
        lob.position(game, key, side)
        told = vote.forecast(game, key, present=True)
        best = max(best, (sum(vote.moves(told["votes"], told["scores"],
                                         told["passes"]).values()), side))
    lob.position(game, key, best[1])


_WRITE = """
import json
from seedfall.core.state import new_game
from seedfall.sim import assembly, assembly_lobby as lob, assembly_vote as vote
# Not `seedfall.tests`: importing it points SEEDFALL_SAVE at a file of its own.
g = new_game("assembly-persist")
g.credits = 500000
st = assembly.ensure(g)
while not st.announced:
    g.ship.cargo["biomass"] = 300
    g.advance_days(1)
assembly.enact(g, assembly.Tabled(key="open_quays", res_id="open_quays",
               sponsor="freeholds"), g.day, 180)
key = st.agenda[0].key
lob.position(g, key, "for")
lob.lobby(g, "pay", "concordat", key)
print(json.dumps({"ok": g.save(), "agenda": [t.key for t in st.agenda],
  "positions": st.positions, "lobby": st.lobby, "next": st.next_day,
  "active": [[a.key, a.until] for a in st.active],
  "votes": vote.forecast(g, key, present=False)["votes"]}))
"""

_READ = """
import json
from seedfall.core.state import load_game
from seedfall.sim import assembly, assembly_vote as vote
g = load_game()
st = assembly.state(g)
key = st.agenda[0].key
print(json.dumps({"ok": True, "agenda": [t.key for t in st.agenda],
  "positions": st.positions, "lobby": st.lobby, "next": st.next_day,
  "active": [[a.key, a.until] for a in st.active],
  "votes": vote.forecast(g, key, present=False)["votes"]}))
"""
