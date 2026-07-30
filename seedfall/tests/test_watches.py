"""The watches of a crossing, and whether their choices are choices.

`data/watches.py` opens by stating its own design rule: "Every option here
costs one of the three things a transit has to spend — time, reaction mass, or
the hull — so there is no option that is simply best."

Four options broke it, and the general question found them all at once: **does
any option dominate another** — cost no more on every axis, and pay at least
as much? On `hulk`, stripping the beacon was free and paid three times what
logging it paid, so logging it was never worth picking. On `contact`, all
three collapsed: hailing was free, riskless, and the only one that paid, which
made running dark (two days) and holding course (nothing) both pointless. Two
of seven watches contained no decision at all.

Underneath that was a second thing. `contact/hold` declared **45% risk — the
largest number in the table — and `risk_damage=0`**. When it fired the game
printed "They were not nobody." and nothing happened. It could not be priced
any other way, because a risk could only ever cost hull, and being stopped and
looked over costs *time*. Hence `risk_days`.

And the screen never said what any of it cost. It rendered "Might go wrong:
30%" and stopped, so holding through debris (30% of thirty off the hull) and
running a bad slug (35% of twenty-four) read as the same gamble.

The claims:

- **Every declared risk costs something.** The one that finds a dead 45%.
- **No option dominates another.** The general one, over all seven watches.
- **What a risk costs is what going wrong does**, measured by playing.
- **The screen prices the risk**, not just its probability.
"""

from __future__ import annotations

import copy

from ..core.rng import RNG
from ..core.state import new_game
from ..data.watches import WATCHES, WATCHES_BY_ID
from ..sim import transit as transit_sim
from .harness import Suite


def _cost(option, net_hull: float | None = None) -> dict:
    """Everything an option takes, on every axis, in expectation.

    `net_hull` is the hull actually still missing once the option's own days
    have elapsed. Declared damage overstates the cost, because the hull is
    organic and regrows — `contact/hold` was first written as ten off the
    hull plus two days, and the two days healed the ten.
    """
    declared = option.damage + option.risk * option.risk_damage
    return {"days": option.days + option.risk * option.risk_days,
            "fuel": option.fuel,
            "hull": declared if net_hull is None else net_hull,
            "heat": option.heat,
            "abort": 1.0 if option.aborts else 0.0}


def _gain(option) -> dict:
    out = {"research": option.research}
    for cid, amount in option.salvage.items():
        out[f"t {cid}"] = amount
    return out


def _dominates(a, b, net: dict | None = None) -> bool:
    """`a` costs no more than `b` on every axis and pays at least as much."""
    net = net or {}
    ca, cb = _cost(a, net.get(a.id)), _cost(b, net.get(b.id))
    ga, gb = _gain(a), _gain(b)
    axes = set(ga) | set(gb)
    no_worse = (all(ca[k] <= cb[k] + 1e-9 for k in ca)
                and all(ga.get(k, 0) >= gb.get(k, 0) - 1e-9 for k in axes))
    better = (any(ca[k] < cb[k] - 1e-9 for k in ca)
              or any(ga.get(k, 0) > gb.get(k, 0) + 1e-9 for k in axes))
    return no_worse and better


class _Rigged:
    """An RNG whose risk rolls are decided in advance, and nothing else."""

    def __init__(self, wrong: bool, seed: str = "rigged") -> None:
        self._wrong = wrong
        self._real = RNG(seed)

    def chance(self, _p: float) -> bool:
        return self._wrong

    def __getattr__(self, name):
        return getattr(self._real, name)


def _resolve(game, crossing, option_id: str, wrong: bool) -> dict:
    """Answer a watch with the risk forced one way. Returns the end state."""
    res = transit_sim.choose(game, crossing, option_id, _Rigged(wrong))
    assert res.get("ok"), res
    return {"went_wrong": bool(res.get("went_wrong")),
            "hull": sum(l.hp for l in game.ship.layers),
            "fuel": game.ship.cargo.get("volatiles", 0.0),
            "day": game.day}


def _in_transit(seed: str, want: str):
    """Fly until the wanted watch comes up. Returns the game and transit."""
    for attempt in range(80):
        game = new_game(f"{seed}{attempt}")
        game.ship.cargo["volatiles"] = 900
        target = next((i for i, b in enumerate(game.system.bodies)
                       if b.id != game.orbit_body), None)
        if target is None:
            continue
        res = transit_sim.begin(game, target, "standard")
        if not res.get("ok"):
            continue
        crossing, rng = res["transit"], RNG(f"{seed}-{attempt}")
        for _ in range(80):
            transit_sim.stand(game, crossing, rng)
            if crossing.event or crossing.over:
                break
        if crossing.event == want:
            return game, crossing, rng
    return None, None, None



def _panel(app, MainWindow, QLabel, want: str, tries: int = 5) -> str:
    """The transit panel's text, on a chronicle that will actually show it.

    `MainWindow.go` refuses to leave a demand, an envoy, a dig or a situation
    for anything but a battle — a rule this file has no business restating, so
    it is *asked* rather than copied: land on the view, and if the window went
    somewhere else, fly a different chronicle. Found when a captain moored at
    their home quay from turn one flew a different leg, and the debris watch
    came up on a game that happened to have an envoy waiting; the panel was
    never built and the check read an empty string as a missing risk line.
    """
    for attempt in range(tries):
        game, crossing, _rng = _in_transit(f"ui-{want}-{attempt}", want)
        if crossing is None:
            continue
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.transit = crossing
        win.go("transit")
        for _ in range(3):
            app.processEvents()
        shown = win.centralWidget() is win.views["transit"] or bool(
            [lab for lab in win.views["transit"].findChildren(QLabel)
             if lab.text()])
        rows = " ".join(lab.text() for lab in
                        win.views["transit"].findChildren(QLabel)
                        if lab.text())
        win.close()
        if shown and rows:
            return rows
    return ""


def run(suite: Suite) -> None:
    check = suite.check

    @check("every declared risk costs something")
    def _():
        # `contact/hold` declared 45% and cost nothing at all: the biggest
        # risk in the table resolved to an ominous sentence and no effect.
        # Asked generally, because the point is that no *future* option can
        # declare a risk and forget to price it either.
        empty, priced = [], 0
        for watch in WATCHES:
            for option in watch.options:
                if not option.risk:
                    continue
                if not (option.risk_damage or option.risk_days
                        or option.aborts):
                    empty.append(f"{watch.id}/{option.id} "
                                 f"({option.risk:.0%})")
                else:
                    priced += 1
        assert not empty, (
            f"risks that cost nothing when they fire: {empty}")
        assert priced >= 6, priced
        return f"{priced} risks declared, every one of them with a consequence"

    @check("no watch option is simply better than another")
    def _():
        # The file's own docstring is the specification. Four options broke
        # it, across two watches, and no amount of testing the ones that
        # worked would have found them.
        #
        # The hull is measured rather than read off the data. Declared damage
        # is not what an option costs, because the hull regrows while the
        # option's own days elapse — reasoning from the numbers alone blesses
        # a trade that is dead in play, which is how the first retune of
        # `contact/hold` got eighteen off the hull down to a real three.
        dead, pairs, measured = [], 0, {}
        for watch in WATCHES:
            game, crossing, _rng = _in_transit(f"dom-{watch.id}", watch.id)
            net = {}
            if crossing is not None:
                for option in watch.options:
                    if option.aborts:
                        continue        # ends the crossing; not comparable
                    full = sum(l.max for l in game.ship.layers)
                    branches = []
                    for wrong in (True, False):
                        end = _resolve(copy.deepcopy(game),
                                       copy.deepcopy(crossing),
                                       option.id, wrong)
                        branches.append((full - end["hull"], end["went_wrong"]))
                    lost = {w: v for v, w in branches}
                    net[option.id] = (option.risk * lost.get(True, 0.0)
                                      + (1 - option.risk) * lost.get(False, 0.0))
                measured[watch.id] = net
            for a in watch.options:
                for b in watch.options:
                    if a is b:
                        continue
                    pairs += 1
                    if _dominates(a, b, net):
                        dead.append(f"{watch.id}: {a.id!r} dominates "
                                    f"{b.id!r}")
        assert not dead, (
            f"{len(dead)} option(s) nobody would ever pick: {dead}")
        # The sweep must actually have something to say: every watch offers a
        # real choice, and the hull really was measured rather than assumed.
        assert all(len(w.options) >= 2 for w in WATCHES), (
            [w.id for w in WATCHES if len(w.options) < 2])
        assert len(measured) == len(WATCHES), (
            f"only {sorted(measured)} were reached, so the rest were judged "
            "on declared numbers")
        return (f"{pairs} ordered pairs across {len(measured)} watches, "
                "hull measured, none dead")

    @check("going wrong leaves you worse off than not going wrong")
    def _():
        # Not measured against the declared numbers, because the hull is
        # organic and regrows at about 2.3 a day: `contact/hold` was first
        # written as ten off the hull plus two days, and the two days healed
        # the ten. Declared costs can cancel each other out.
        #
        # So: resolve the same option twice from the same state, once with
        # the risk forced on and once forced off, and demand the wrong branch
        # actually end worse. That is the question a captain is asking, and
        # it is what the original 45%-for-nothing failed.
        checked, rows = [], []
        for watch in WATCHES:
            for option in watch.options:
                if not option.risk:
                    continue
                ends = {}
                for wrong in (True, False):
                    game, crossing, _rng = _in_transit(f"w-{watch.id}",
                                                       watch.id)
                    if crossing is None:
                        break
                    ends[wrong] = _resolve(game, crossing, option.id, wrong)
                if len(ends) != 2:
                    continue
                bad, fine = ends[True], ends[False]
                assert bad["went_wrong"] and not fine["went_wrong"], ends
                worse = {axis: fine[axis] - bad[axis]
                         for axis in ("hull", "fuel")}
                worse["days"] = bad["day"] - fine["day"]
                hurt = {a: v for a, v in worse.items() if v > 0.01}
                assert hurt, (
                    f"{watch.id}/{option.id} declares a {option.risk:.0%} "
                    f"risk and going wrong leaves the ship in the same state "
                    f"as going right: {worse}")
                checked.append(f"{watch.id}/{option.id}")
                rows.append(f"{option.id} "
                            + "+".join(f"{v:.0f} {a}"
                                       for a, v in sorted(hurt.items())))
        assert len(checked) >= 6, checked
        return f"{len(checked)} risks, each one costing: " + " · ".join(rows)

    @check("a risk that costs days actually costs them")
    def _():
        # `risk_days` was added for the contact, so it needs its own proof
        # rather than riding on the sweep above: the crossing's own clock and
        # the sector calendar both have to move.
        game, crossing, _rng = _in_transit("days", "contact")
        assert crossing is not None, "no contact watch in eighty crossings"
        option = next(o for o in WATCHES_BY_ID["contact"].options
                      if o.id == "hold")
        assert option.risk_days == 3, option.risk_days

        spent, day = crossing.days_spent, game.day
        transit_sim.choose(game, crossing, "hold", _Rigged(True))
        moved = crossing.days_spent - spent
        assert moved == option.risk_days, (
            f"the crossing's own clock moved {moved} days for a "
            f"{option.risk_days}-day boarding")
        assert game.day - day == option.risk_days, (
            f"the sector calendar moved {game.day - day} days")
        return f"{moved} days off the crossing and off the calendar"

    @check("the watch panel says what going wrong will cost")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        seen = 0
        for want in ("contact", "debris"):
            rows = _panel(app, MainWindow, QLabel, want)
            assert rows, (
                f"no chronicle reached a {want} watch with the transit panel "
                "showing — every candidate was holding something else")
            for option in WATCHES_BY_ID[want].options:
                if not option.risk:
                    continue
                assert option.risk_text in rows, (
                    f"{want}/{option.id}: the screen offers a "
                    f"{option.risk:.0%} risk and never says what goes wrong")
                if option.risk_damage:
                    assert f"{round(option.risk_damage)} more off the hull" \
                        in rows, (
                        f"{want}/{option.id}: risks "
                        f"{round(option.risk_damage)} off the hull and the "
                        f"screen shows only the percentage")
                seen += 1
        assert seen >= 3, seen
        return f"{seen} risks priced on the panel, not just their odds"
