"""Every gate agrees with the act it guards.

The sim has seventeen functions whose whole job is to answer "may I?" —
`can_found`, `can_build_here`, `can_afford`, `is_stranded` and the rest. A
screen asks the gate to decide whether to offer a button; the act asks its own
conditions when the button is pressed. When the two disagree the captain gets
a live button that answers with a toast, or a greyed one hiding something they
could have done.

This project has now found that twice by accident. `is_stranded` read a body's
richness where `extract` reads its depletion, so a captain with no fuel at a
worked-out moon was refused the tow that exists for exactly that. `quote`
priced two contract kinds where `check` completed three.

So it is asked on purpose here, across every gate that can be driven headless.
It found a third straight away: **`crew.hire` refuses a station that is
already crewed and nothing on the berths board knew.** Measured over sixty
ports, **49% of candidates could not be signed** — a fresh bridge holds
science, engineering and nav, and the recruit pool draws evenly from all six
roles — and every one of them drew a live "Sign on". Fifty-five boards in
sixty had at least one; four had four.

The claims:

- **Gate and act agree**, swept over every pair that can be played.
- **A station already crewed is refused, and the card names who holds it.**
- **The board does not offer a berth it cannot give.**

One thing an agreement check cannot do, and should not pretend to: where the
act *calls* the gate — `start_build` asks `can_build_here` — changing the gate
moves both answers together and they agree all the way down. That is the
architecture you want; it just means the rule itself has to be held by a
check about the rule, not about the agreement.
"""

from __future__ import annotations

import collections

from ..core.rng import RNG
from ..core.state import new_game
from ..data.chassis import CHASSIS_BY_ID
from ..data.colonies import COLONIES
from ..sim import actions, colony, crew, mining, shipyard
from .harness import Suite


def _rich(seed: str):
    """A captain who can afford anything, so only the gate's own rule bites."""
    game = new_game(seed)
    game.credits = 5_000_000
    for goods in ("biomass", "ore", "phosphate", "spidroin", "volatiles",
                  "alloy", "silicon", "magnetite", "xenolith"):
        game.stores[goods] = 9000
    game.research.unlocked = list({*game.research.unlocked,
                                   *(c.tech for c in COLONIES if c.tech)})
    game.recompute()
    return game


def _sweep_found(disagree: collections.Counter) -> int:
    checked = 0
    for seed in range(6):
        game = _rich(f"gate-found-{seed}")
        for system in game.galaxy.systems[:4]:
            for body in system.bodies:
                body.surveyed = True
                for spec in COLONIES:
                    ok, why = colony.can_found(game, system, body, spec.id)
                    res = colony.found(game, system, body, spec.id)
                    got = bool(res[0] if isinstance(res, tuple) else res)
                    checked += 1
                    if ok != got:
                        disagree[f"can_found/{spec.id}: gate {ok}, act {got} "
                                 f"({why[:30]})"] += 1
                    if got:
                        game.colonies = [c for c in game.colonies
                                         if c.body_id != body.id]
                        body.colony = None
    return checked


def _sweep_hire(disagree: collections.Counter) -> int:
    """Both of `can_hire`'s rules, so a rich captain does not hide the fee.

    The first draft gave every captain half a million credits, so the branch
    about the signing fee never bound and deleting it went unnoticed.
    """
    checked = 0
    for seed in range(20):
        for purse in (500_000, 0):
            game = new_game(f"gate-hire-{seed}")
            game.credits = purse
            port = next(s for s in game.galaxy.systems if s.port)
            game.location_id = port.id
            for hand in crew.recruit_pool(RNG(f"gh{seed}"), port.port.level):
                ok, why = crew.can_hire(game, hand)
                res = crew.hire(game, hand)
                checked += 1
                if ok != bool(res.get("ok")):
                    disagree[f"can_hire: gate {ok}, act "
                             f"{bool(res.get('ok'))} "
                             f"({(res.get('why') or why)[:30]})"] += 1
    return checked


def _sweep_extract(disagree: collections.Counter) -> int:
    checked = 0
    for seed in range(8):
        game = new_game(f"gate-mine-{seed}")
        for stock in ({}, {"biomass": 2}, {"biomass": 400, "volatiles": 400}):
            game.ship.cargo = dict(stock)
            game.credits = 60_000
            for index in range(len(game.system.bodies)):
                for method in mining.METHODS_BY_ID:
                    ok, why = mining.can_afford(game, method, 20)
                    held = dict(game.ship.cargo)
                    res = actions.extract(game, index, 20, method_id=method)
                    checked += 1
                    if not ok and res.get("ok"):
                        disagree[f"can_afford/{method}: gate said no and the "
                                 f"rig ran anyway ({why[:30]})"] += 1
                    game.ship.cargo = held
    return checked


def _sweep_build(disagree: collections.Counter) -> int:
    checked = 0
    for seed in range(6):
        game = _rich(f"gate-build-{seed}")
        for system in game.galaxy.systems[:4]:
            for chassis in list(CHASSIS_BY_ID.values())[:6]:
                ok, why = shipyard.can_build_here(game, system, chassis)
                res = shipyard.start_build(game, chassis.id, [], system)
                laid = res[0] is not None
                checked += 1
                if not ok and laid:
                    disagree[f"can_build_here/{chassis.id}: gate said no and "
                             f"the hull went down ({why[:30]})"] += 1
                if ok and not laid and "here" in str(res[1]).lower():
                    disagree[f"can_build_here/{chassis.id}: gate said yes and "
                             f"the yard refused the place ({str(res[1])[:30]})"] += 1
    return checked


def run(suite: Suite) -> None:
    check = suite.check

    @check("every gate agrees with the act it guards")
    def _():
        # The general one. Each sweep drives a gate and its act over the same
        # state and compares the two answers.
        disagree: collections.Counter = collections.Counter()
        counts = {
            "can_found / found": _sweep_found(disagree),
            "can_hire / hire": _sweep_hire(disagree),
            "can_afford / extract": _sweep_extract(disagree),
            "can_build_here / start_build": _sweep_build(disagree),
        }
        assert not disagree, (
            f"{sum(disagree.values())} disagreement(s) between a gate and "
            f"what it guards: {list(disagree)[:4]}")
        for name, n in counts.items():
            assert n > 20, f"{name} only exercised {n} times"
        return " · ".join(f"{n} {name.split(' /')[0]}"
                          for name, n in counts.items())

    @check("a station already crewed is refused, and by name")
    def _():
        # The case the sweep found. A fresh bridge holds three of the six
        # roles, so half a board is candidates for a chair that is taken.
        game = new_game("crewed")
        game.credits = 500_000
        port = next(s for s in game.galaxy.systems if s.port)
        game.location_id = port.id
        held = {o.stat: o for o in game.officers}
        assert len(held) >= 3, held

        blocked, free = 0, 0
        for seed in range(30):
            for hand in crew.recruit_pool(RNG(f"named{seed}"),
                                          port.port.level):
                ok, why = crew.can_hire(game, hand)
                if hand.stat in held:
                    blocked += 1
                    assert not ok, (
                        f"{hand.role_name} offered while "
                        f"{held[hand.stat].name} holds the station")
                    assert held[hand.stat].name in why, (
                        f"the refusal does not name the incumbent: {why!r}")
                else:
                    free += 1
                    assert ok, f"a free station refused: {why}"
        assert blocked > 20 and free > 20, (blocked, free)
        return (f"{blocked} candidates for a taken chair, every refusal naming "
                f"its incumbent; {free} free ones all signable")

    @check("the rules the gates hold are still the rules")
    def _():
        # The complement, and the thing the sweep above cannot do. `hire`
        # calls `can_hire` and `start_build` calls `can_build_here`, so
        # changing a gate moves both answers together and they agree all the
        # way down — which is the architecture you want, and exactly why the
        # rule itself has to be measured by its outcome instead.
        game = new_game("rules")
        port = next(s for s in game.galaxy.systems if s.port)
        game.location_id = port.id
        pool = crew.recruit_pool(RNG("rules"), port.port.level)
        hand = next(h for h in pool
                    if h.stat not in {o.stat for o in game.officers})

        game.credits = hand.wage - 1
        aboard = len(game.officers)
        assert not crew.hire(game, hand).get("ok"), (
            "signed on with less than the fee in the treasury")
        assert len(game.officers) == aboard, "they came aboard anyway"
        assert game.credits == hand.wage - 1, "the treasury moved regardless"

        game.credits = hand.wage + 500
        assert crew.hire(game, hand).get("ok"), "could not sign with the fee"
        assert len(game.officers) == aboard + 1
        assert game.credits == 500, (
            f"the fee was {hand.wage:,} and {hand.wage + 500 - game.credits:,} "
            "left the treasury")

        # And a hull needs somewhere to be laid down. Nothing in the suite was
        # holding this: making `can_build_here` answer yes everywhere passed
        # every check in the project.
        bare = new_game("bare")
        bare.credits = 5_000_000
        for goods in ("alloy", "silicon", "biomass", "ore", "phosphate"):
            bare.stores[goods] = 9000
        bare.recompute()
        chassis = CHASSIS_BY_ID["navis"]
        nowhere = [s for s in bare.galaxy.systems
                   if not shipyard.can_build_here(bare, s, chassis)[0]]
        assert nowhere, "every system in the sector can lay down a hull"
        hull, why = shipyard.start_build(bare, chassis.id, [], nowhere[0])
        assert hull is None, (
            f"a hull went down at {nowhere[0].name}, which has no yard and no "
            "slipway of yours")
        assert why, "refused without saying why"
        return (f"the fee is charged and refused on its own terms; "
                f"{len(nowhere)} systems will not take a keel")

    @check("the berths board does not offer what it cannot give")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        for seed in range(30):
            game = new_game(f"berth-ui-{seed}")
            game.credits = 90_000
            port = next(s for s in game.galaxy.systems if s.port)
            game.location_id = port.id
            win = MainWindow(game)
            win.toast = lambda *a, **k: None
            win.go("port")
            view = win.views["port"]
            view.tab = "crew"
            view.refresh()
            for _ in range(3):
                app.processEvents()
            buttons = [b for b in view.findChildren(QPushButton)
                       if b.text() == "Sign on"]
            rows = " ".join(lab.text() for lab in view.findChildren(QLabel)
                            if lab.text())
            pool = list(getattr(view, "_pool", None)
                        or getattr(win.views["port"], "_pool", []) or [])
            win.close()
            if not buttons or not pool or len(buttons) != len(pool):
                continue
            want = [crew.can_hire(game, hand)[0] for hand in pool]
            got = [b.isEnabled() for b in buttons]
            assert got == want, (
                f"seed {seed}: buttons {got} against {want} — the board "
                "offers a berth it cannot give")
            if not all(want):
                blocked = next(h for h, w in zip(pool, want) if not w)
                assert crew.can_hire(game, blocked)[1] in rows, (
                    "the card does not say why the berth is closed")
                return (f"{len(pool)} candidates, {want.count(False)} closed "
                        "and each saying why")
        raise AssertionError("no board in thirty had a closed berth")
