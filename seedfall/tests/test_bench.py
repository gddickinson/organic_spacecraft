"""Bench checks — what a programme says it will eat is what it eats.

`needs()` is documented as "how much of each kind a programme will consume end
to end", and the screen prints it as "26 wanted". `draw()` then spent
`total / 60` a day while a careful programme runs about 128 days, so the bench
actually ate 2.1x the advertised figure — measured at wanted 26 against used
56, on every track, for every tech. The sixty was a duration nobody had checked
against the real one.

It also ignored the approach. Running parallel tracks costs, in its own words,
"three benches' worth of material", and the readout quoted the careful figure.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.inquiry import APPROACHES, EVIDENCE
from ..sim import inquiry
from ..sim import research as research_sim
from .harness import Suite

KINDS = [e.id for e in EVIDENCE]


def _bench(seed: str, approach: str = "careful", stock: float = 8000):
    game = new_game(seed)
    for kind in KINDS:
        inquiry.add(game.research, kind, stock)
    tech = next(t for t in research_sim.researchable(game.research.unlocked))
    research_sim.set_project(game.research, tech.id)
    inquiry.set_approach(game.research, approach)
    return game, tech


def _run(game, tech, cap: int = 500) -> dict:
    before = {k: inquiry.held(game.research, k) for k in KINDS}
    start, guard = game.day, 0
    while tech.id not in game.research.unlocked and guard < cap:
        guard += 1
        game.advance_days(10)
    return {"days": game.day - start,
            "done": tech.id in game.research.unlocked,
            "used": {k: before[k] - inquiry.held(game.research, k)
                     for k in KINDS}}


def run(suite: Suite) -> None:
    check = suite.check

    @check("what the bench says it wants is what it takes")
    def _():
        # The bug: the screen quoted the end-to-end total and the draw was
        # paced against a hardcoded sixty days.
        worst = 0.0
        lines = []
        for approach in ("careful", "parallel", "push"):
            wanted = {k: 0.0 for k in KINDS}
            used = {k: 0.0 for k in KINDS}
            runs = 0
            for index in range(8):
                game, tech = _bench(f"want-{index}", approach)
                asked = inquiry.needs(tech.id, game.research)
                out = _run(game, tech)
                if not out["done"]:
                    continue
                runs += 1
                for kind in KINDS:
                    wanted[kind] += asked.get(kind, 0.0)
                    used[kind] += out["used"][kind]
            assert runs, f"no {approach} programme finished"
            for kind in KINDS:
                if wanted[kind] <= 0:
                    continue
                ratio = used[kind] / wanted[kind]
                worst = max(worst, abs(ratio - 1.0))
                lines.append(f"{approach[:4]}/{kind[:4]} {ratio:.2f}x")
        assert worst < 0.25, (
            f"the bench takes {1 + worst:.2f}x what it advertises: "
            + ", ".join(lines[:6]))
        return f"{len(lines)} track/approach pairs, worst {1 + worst:.2f}x"

    @check("an approach's appetite is in the figure it quotes")
    def _():
        # "Three benches on the same problem. It costs three benches' worth of
        # material" — and the readout used to quote the careful number.
        game, tech = _bench("appetite")
        quoted = {}
        for approach in APPROACHES:
            if approach.needs_precedent:
                continue
            inquiry.set_approach(game.research, approach.id)
            asked = inquiry.needs(tech.id, game.research)
            quoted[approach.id] = sum(asked.values())
        assert quoted["parallel"] > quoted["careful"] * 1.5, (
            f"parallel quotes {quoted['parallel']:.0f} against careful's "
            f"{quoted['careful']:.0f} — it costs 1.9x and says so nowhere")
        for approach in APPROACHES:
            if approach.needs_precedent:
                continue
            ratio = quoted[approach.id] / quoted["careful"]
            assert abs(ratio - approach.draw) < 0.02, (
                f"{approach.id} quotes {ratio:.2f}x and draws {approach.draw}x")
        return " · ".join(f"{k} {v:.0f}" for k, v in sorted(quoted.items()))

    @check("the four approaches are a decision")
    def _():
        out = {}
        for approach in ("careful", "parallel", "push"):
            days = setbacks = 0.0
            runs = 0
            for index in range(12):
                game, tech = _bench(f"decide-{index}", approach)
                before = 0
                out_run = _run(game, tech)
                if not out_run["done"]:
                    continue
                days += out_run["days"]
                runs += 1
            out[approach] = days / max(1, runs)
        assert out["push"] < out["parallel"] < out["careful"], (
            f"not ordered by speed: {out}")
        pushy = next(a for a in APPROACHES if a.id == "push")
        careful = next(a for a in APPROACHES if a.id == "careful")
        assert pushy.setback > careful.setback, "hurrying risks nothing"
        return " · ".join(f"{k} {v:.0f}d" for k, v in out.items())

    @check("a starved bench crawls but is never a dead end")
    def _():
        # STARVED_FLOOR exists because gating hard on evidence bricked the
        # opening: a captain who had not surveyed anything could never begin.
        starved = new_game("starved-bench")
        tech = next(t for t in research_sim.researchable(starved.research.unlocked))
        research_sim.set_project(starved.research, tech.id)
        inquiry.set_approach(starved.research, "careful")
        thin = _run(starved, tech)
        assert thin["done"], "an unsupplied programme never finishes at all"

        game, tech2 = _bench("fed-bench")
        fed = _run(game, tech2)
        assert fed["days"] < thin["days"] * 0.85, (
            f"stocking the bench saves nothing: {thin['days']} → {fed['days']}")
        return f"{thin['days']} days starved against {fed['days']} fed"

    @check("evidence is spent, so the next programme starts poorer")
    def _():
        # A chronicle opens with some evidence already on the shelves, so the
        # starting stock is not what you added — comparing against the number
        # passed to the fixture was my arithmetic, and it read as the bench
        # generating evidence out of nothing.
        game, tech = _bench("spent", stock=400)
        opening = {k: inquiry.held(game.research, k) for k in KINDS}
        first = _run(game, tech)
        assert first["done"]
        assert any(first["used"][k] > 0 for k in KINDS), "nothing was consumed"
        for kind in KINDS:
            left = inquiry.held(game.research, kind)
            assert abs(left - (opening[kind] - first["used"][kind])) < 0.01, (
                f"{kind}: {opening[kind]:.0f} - {first['used'][kind]:.0f} "
                f"should leave {opening[kind] - first['used'][kind]:.0f}, "
                f"and there is {left:.0f}")

        # And a second programme starts from the reduced shelves.
        second_tech = next(t for t in research_sim.researchable(
            game.research.unlocked) if t.id != tech.id)
        research_sim.set_project(game.research, second_tech.id)
        second = _run(game, second_tech)
        assert second["done"]
        both = sum(first["used"].values()) + sum(second["used"].values())
        assert both > sum(first["used"].values()) * 1.5, (
            "the second programme cost nothing")
        return (f"{sum(first['used'].values()):.0f} then "
                f"{sum(second['used'].values()):.0f}, off shelves that "
                "went down by exactly that")
