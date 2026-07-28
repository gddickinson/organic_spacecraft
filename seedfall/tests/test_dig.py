"""Dig checks — a site worked layer by layer rather than resolved in a call.

Excavating was: spend twelve days, receive a number of points, occasionally
read that the face collapsed. Everything the setting says about Abyssal work —
that it is layered, that it is fragile, that the interesting part is always
under the part that is easy to reach — was in the codex and nowhere in the
game.

These hold the strata to being a decision, and hold banking-as-you-go to being
what makes stopping worth doing.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.strata import FINDS, METHODS, STRATA
from ..data.xenotech import XENOTECH
from ..sim import dig as dig_sim
from ..sim import xeno as xeno_sim
from ..sim.ship import hull_pct
from .harness import Suite


def _sited(seed: str):
    """A game with a found relic somewhere in the home system."""
    game = new_game(seed)
    index = body = None
    for position, candidate in enumerate(game.system.bodies):
        if candidate.relic:
            index, body = position, candidate
            break
    if body is None:
        body = game.system.bodies[0]
        body.relic = XENOTECH[0].id
        index = 0
    body.relic_found = True
    return game, index, body


def _dig_out(seed: str, method: str):
    game, index, _body = _sited(seed)
    started = dig_sim.begin(game, index)
    assert started["ok"], started.get("why")
    site = started["dig"]
    game.dig = site
    rng = RNG(f"trench-{seed}")
    guard = 0
    while not site.over and guard < 10:
        guard += 1
        dig_sim.work(game, site, method, rng)
    return game, site


def run(suite: Suite) -> None:
    check = suite.check

    @check("the strata and the ways of working them are coherent")
    def _():
        total = sum(s.share for s in STRATA)
        assert abs(total - 1.0) < 0.001, f"the strata sum to {total}, not one"
        depths = [s.fragility for s in STRATA]
        assert depths == sorted(depths), (
            f"the site is not more fragile the deeper it goes: {depths}")
        for stratum in STRATA:
            assert stratum.name and stratum.text, f"{stratum.id} says nothing"
        for method in METHODS:
            assert method.days > 0, f"{method.id} takes no time"
            assert method.name and method.blurb, f"{method.id} says nothing"
        quick = min(METHODS, key=lambda m: m.days)
        slow = max(METHODS, key=lambda m: m.days)
        assert quick.care > slow.care, "hurrying is no rougher on the find"
        assert quick.yield_mul < slow.yield_mul, "hurrying costs no yield"
        return (f"{len(STRATA)} strata, {len(METHODS)} methods, "
                f"{sum(len(v) for v in FINDS.values())} named finds")

    @check("a trench worked to the bottom banks its understanding")
    def _():
        game, site = _dig_out("bottom", "careful")
        assert site.over and site.outcome == "bottomed", (
            f"the dig ended {site.outcome!r}")
        assert site.layer == len(STRATA), "bottomed without reaching the bottom"
        assert site.points > 0, "a dig that taught nothing"
        assert xeno_sim.study_of(game, site.tech_id) >= site.points - 0.01, (
            "the points were never credited against the technology")
        body = game.system.bodies[site.body_index]
        assert not body.relic_found, "the site is still advertising a find"
        assert body.digs > 0, "the site does not remember being worked"
        return (f"{site.days} days, {site.points:.0f} points, "
                f"{site.relics:.1f} t crated")

    @check("backfilling keeps everything already out of the ground")
    def _():
        # Banking per layer rather than at the end is what makes stopping a
        # choice instead of a way of throwing the dig away.
        game, index, _body = _sited("backfill")
        site = dig_sim.begin(game, index)["dig"]
        game.dig = site
        rng = RNG("backfill")
        dig_sim.work(game, site, "careful", rng)
        dig_sim.work(game, site, "careful", rng)
        banked = site.points
        credited = xeno_sim.study_of(game, site.tech_id)
        assert banked > 0, "two layers taught nothing"

        dig_sim.stop(game, site)
        assert site.over and site.outcome == "backfilled"
        assert site.points == banked, "backfilling took back what was banked"
        assert xeno_sim.study_of(game, site.tech_id) == credited, (
            "the understanding was withdrawn on leaving")
        return f"{banked:.0f} points kept after two of four strata"

    @check("how you work a layer is a real decision")
    def _():
        runs = 20
        results = {}
        for method in ("careful", "brisk", "cut"):
            points = days = hull = 0.0
            for index in range(runs):
                game, site = _dig_out(f"cmp-{index}", method)
                points += site.points
                days += site.days
                hull += 1.0 - hull_pct(game.ship)
            results[method] = (points / runs, days / runs, hull / runs)

        careful, brisk, cut = (results[k] for k in ("careful", "brisk", "cut"))
        assert careful[0] > cut[0] * 1.5, (
            f"care wins you nothing: {careful[0]:.0f} against {cut[0]:.0f}")
        assert cut[1] < careful[1], "cutting through is not faster"
        assert cut[2] > careful[2], "cutting through costs no hull"
        assert brisk[0] / brisk[1] > careful[0] / careful[1], (
            "working briskly is not a better rate than working properly, so "
            "there is no reason ever to choose it")
        return " · ".join(f"{k} {v[0]:.0f}pts/{v[1]:.0f}d" for k, v in results.items())

    @check("finds and spoils both actually happen")
    def _():
        found, spoiled = set(), 0
        for index in range(30):
            game, index_body, _body = _sited(f"reach-{index}")
            site = dig_sim.begin(game, index_body)["dig"]
            game.dig = site
            rng = RNG(f"reach-{index}")
            while not site.over:
                method = "careful" if index % 2 else "cut"
                out = dig_sim.work(game, site, method, rng)
                if out.get("find"):
                    found.add(out["find"][0])
                if out.get("spoiled"):
                    spoiled += 1
        every = {name for pool in FINDS.values() for name, _text in pool}
        assert found, "nothing was ever lifted intact in thirty digs"
        assert spoiled, "nothing was ever spoiled in thirty digs"
        missing = every - found
        assert len(missing) <= 1, f"finds that never came up: {sorted(missing)}"
        return f"{len(found)} of {len(every)} finds seen, {spoiled} spoiled layers"

    @check("a site worked before gives up less")
    def _():
        game, index, body = _sited("fatigue")
        first = dig_sim.begin(game, index)["dig"]
        game.dig = first
        fresh = dig_sim.layer_value(game, first, "careful")["points"]
        body.digs = 2
        tired = dig_sim.layer_value(game, first, "careful")["points"]
        assert tired < fresh, (
            f"a site worked twice still gives {tired:.0f} against {fresh:.0f}")
        return f"{fresh:.0f} points fresh → {tired:.0f} after two seasons"
