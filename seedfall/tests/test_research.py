"""Research checks — a programme with inputs, not a progress bar.

Research used to be one undifferentiated pool: everything you did anywhere fed
one number, so nothing you chose to do changed what you could learn. These hold
the evidence model to actually connecting research to the rest of the game, and
hold the approaches to being different bargains — without ever letting a
captain brick their own game by picking a project too early.
"""

from __future__ import annotations

import statistics

from ..core.rng import RNG
from ..core.state import new_game
from ..data.inquiry import (APPROACHES, BRANCH_MIX, EVIDENCE, EVIDENCE_BY_ID,
                            STARVED_FLOOR)
from ..data.tech import TECH
from ..sim import inquiry
from ..sim import research as research_sim
from ..sim.actions import survey
from .harness import Suite


def _first_project(game):
    tech = next(t for t in research_sim.researchable(game.research.unlocked))
    research_sim.set_project(game.research, tech.id)
    return tech


def run(suite: Suite) -> None:
    check = suite.check

    @check("every branch draws on evidence, and every kind has a source")
    def _():
        import pathlib
        branches = {t.branch for t in TECH}
        missing = branches - set(BRANCH_MIX)
        assert not missing, f"branches with no evidence mix: {missing}"
        for branch, mix in BRANCH_MIX.items():
            assert abs(sum(mix.values()) - 1.0) < 0.001, (
                f"{branch} mix sums to {sum(mix.values())}")
            unknown = set(mix) - set(EVIDENCE_BY_ID)
            assert not unknown, f"{branch} wants unknown evidence {unknown}"

        # A kind nothing ever grants is a locker that stays empty for ever.
        root = pathlib.Path(__file__).resolve().parents[1]
        source = "\n".join(p.read_text() for p in root.rglob("*.py")
                           if p.parent.name != "tests" and p.name != "inquiry.py")
        ungranted = [e.id for e in EVIDENCE if f'"{e.id}"' not in source]
        assert not ungranted, f"nothing in the game grants {ungranted}"
        return f"{len(branches)} branches, {len(EVIDENCE)} kinds, all sourced"

    @check("a captain who sets a project on turn one is not stuck")
    def _():
        # Gating all progress on evidence meant a fresh captain who picked a
        # project and flew made literally zero progress for a year.
        game = new_game("turn-one")
        tech = _first_project(game)
        while game.research.current and game.day < 900:
            game.advance_days(30)
        assert not game.research.current, (
            f"a year and a half on and still {game.research.progress:.0f}/"
            f"{tech.cost}")
        assert tech.id in game.research.unlocked
        assert STARVED_FLOOR > 0, "the starved floor was removed"
        return f"{tech.name} in {game.day} days doing nothing in particular"

    @check("going and getting the evidence measurably pays")
    def _():
        def trial(active: bool) -> float:
            days = []
            for seed in range(12):
                game = new_game(f"pay-{seed}")
                _first_project(game)
                while game.research.current and game.day < 1500:
                    done = False
                    if active:
                        for index, body in enumerate(game.system.bodies):
                            if not body.surveyed:
                                survey(game, index)
                                done = True
                                break
                    if not done:
                        game.advance_days(30)
                days.append(game.day)
            return statistics.median(days)

        idle, working = trial(False), trial(True)
        assert working < idle * 0.7, (
            f"surveying barely helped: {working:.0f} d against {idle:.0f} d")
        return f"{idle:.0f} days idle → {working:.0f} days surveying as you go"

    @check("the approaches are different bargains")
    def _():
        results = {}
        for approach in APPROACHES:
            days = []
            for seed in range(24):
                game = new_game(f"appr-{seed}")
                _first_project(game)
                inquiry.set_approach(game.research, approach.id)
                for kind in EVIDENCE_BY_ID:
                    inquiry.add(game.research, kind, 600)
                while game.research.current and game.day < 2000:
                    game.advance_days(30)
                days.append(game.day)
            results[approach.id] = statistics.median(days)

        assert results["push"] < results["careful"], (
            f"pushing is not faster: {results}")
        assert results["parallel"] < results["careful"], (
            f"parallel tracks are not faster: {results}")
        return " · ".join(f"{k} {v:.0f}d" for k, v in results.items())

    @check("pushing costs progress often enough to matter")
    def _():
        setbacks = {"careful": 0, "push": 0}
        for approach in setbacks:
            for seed in range(60):
                game = new_game("setback")
                _first_project(game)
                inquiry.set_approach(game.research, approach)
                if inquiry.roll(game.research, RNG(f"s{seed}"), 90) == "setback":
                    setbacks[approach] += 1
        assert setbacks["careful"] == 0, "careful work suffered a setback"
        assert setbacks["push"] > 8, (
            f"pushing went wrong only {setbacks['push']}/60 times")

        # And a setback genuinely costs progress.
        game = new_game("cost")
        tech = _first_project(game)
        game.research.progress = 100.0
        delta = inquiry.apply_event(game.research, "setback", tech.id)
        assert delta < 0 and game.research.progress < 100.0, "a setback cost nothing"
        gain = inquiry.apply_event(game.research, "breakthrough", tech.id)
        assert gain > 0, "a breakthrough gained nothing"
        return f"push {setbacks['push']}/60 setbacks, careful none"

    @check("reverse-engineering needs something to take apart")
    def _():
        game = new_game("copy")
        _first_project(game)
        game.research.evidence = {}
        game.xeno_study = {}
        offers = dict((a.id, (ok, why)) for a, ok, why in inquiry.available(game))
        assert "copy" in offers, "reverse-engineering was not listed"
        assert not offers["copy"][0], "reverse-engineered from nothing"
        assert offers["copy"][1], "refused without saying why"

        inquiry.add(game.research, "hardware", 120)
        offers = dict((a.id, ok) for a, ok, _w in inquiry.available(game))
        assert offers["copy"], "salvage on the bench was not enough"
        return "refused with an empty bench, allowed with salvage"

    @check("a starved bench slows down without stopping")
    def _():
        game = new_game("starve")
        tech = _first_project(game)
        game.research.evidence = {}
        served, missing = inquiry.draw(game.research, tech.id, 30)
        assert missing, "an empty bench reported no shortfall"
        assert abs(served - STARVED_FLOOR) < 0.001, (
            f"an empty bench runs at {served:.2f}, not the {STARVED_FLOOR} floor")

        for kind in inquiry.needs(tech.id):
            inquiry.add(game.research, kind, 900)
        fed, missing = inquiry.draw(game.research, tech.id, 30)
        assert not missing, f"a full bench still short of {missing}"
        assert fed > served, "a full bench is no faster than an empty one"
        return f"starved {served:.2f} → supplied {fed:.2f}"

    @check("evidence and approach survive a save and reload")
    def _():
        import json

        from ..core.save import decode, encode

        game = new_game("persist-research")
        _first_project(game)
        inquiry.set_approach(game.research, "parallel")
        for kind, amount in (("survey", 40), ("hardware", 90), ("reading", 15)):
            inquiry.add(game.research, kind, amount)
        before = inquiry.summary(game.research)

        back = decode(json.loads(json.dumps(encode(game))))
        assert inquiry.summary(back.research) == before, "the lockers emptied"
        assert back.research.approach == "parallel", "the approach was lost"
        assert back.research.current == game.research.current
        return f"{len([v for v in before.values() if v])} lockers and the approach kept"
