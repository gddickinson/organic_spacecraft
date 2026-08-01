"""Territory checks — claims and holdings have to be able to collide.

The sector had both and they passed through each other. `_claimable()` in
`ventures.py` explicitly excluded any system the player held a colony in, so
the powers politely declined to contest your ground; and `can_found()` never
looked at `system.faction`, so you could plant inside somebody's declared space
and nobody said a word. An empire game where territory is never contested is an
empire game with the empire taken out.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.territory import ANSWERS, LEVY_SHARE, UNWELCOME
from ..sim import colony as colony_sim
from ..sim import territory as territory_sim
from ..sim import ventures as venture_sim
from ..sim import works as works_sim
from .harness import Suite


def _planted(seed: str, claimed_by: str | None = None):
    """A game with one matured holding, optionally on somebody's register."""
    game = new_game(seed)
    game.credits = 2_000_000
    game.ship.fitted.append("seed_bay")
    for tech in ("bioleach", "melanin", "oect", "intima"):
        game.research.unlocked.append(tech)
    game.recompute()
    for key in ("alloy", "ore", "biomass", "volatiles", "phosphate", "silicon"):
        game.stores[key] = 90000
    system = game.system
    system.faction = None
    # Keep the Bloom out of it. A holding can mature and be eaten inside the
    # same advance_days call, which leaves `online` True on an object that is
    # no longer in `game.colonies` — the first version of this helper asserted
    # on `online` and handed back a colony that had already been overgrown.
    system.bloom = 0.0
    body = next(b for b in system.bodies
                if b.kind in ("asteroid", "moon", "rocky"))
    colony, why = colony_sim.found(game, system, body, "radix_mine")
    assert colony, why
    game.advance_days(colony.need + 5)
    assert colony.online, "the holding never matured"
    assert colony in game.colonies, "the holding was lost before the test began"
    system.faction = claimed_by
    return game, colony, system


def run(suite: Suite) -> None:
    check = suite.check

    @check("a power will annex ground you hold")
    def _():
        # The exclusion in _claimable() meant this could never happen at all.
        game, colony, system = _planted("annexable")
        options = venture_sim._claimable(game, "charter")
        assert any(s.id == system.id for s in options), (
            "the powers still step around anywhere the player holds")
        venture = venture_sim.Venture(id=1, kind="annex", power="charter",
                                      place=system.id, until=game.day)
        events = venture_sim._apply(game, venture, RNG("annex"))
        assert system.faction == "charter", "the annexation did not land"
        assert game.demand is not None, "nobody asked you anything about it"
        assert game.demand.system_id == system.id
        assert game.demand.power == "charter"
        assert game.demand.worth > 0, "the demand does not know what is at stake"
        assert any(kind == "warn" for kind, _t in events), (
            "a power moving on your holding read as ordinary news")
        # `holdings_in` rather than a count stored on the demand. `Demand`
        # carried one, set here and read by nobody in the game — a copy that can
        # disagree with the live answer the moment a colony is lost.
        held = territory_sim.holdings_in(game, system.id)
        return (f"{system.name} annexed, demand raised over "
                f"{len(held)} holding(s) worth {round(game.demand.worth):,}")

    @check("all three answers are genuinely different")
    def _():
        out = {}
        for ans in ANSWERS:
            game, colony, system = _planted(f"answer-{ans.id}", "charter")
            before = game.rep.get("charter", 0)
            res = territory_sim.answer(game, system, "charter", ans.id)
            assert res["ok"], res.get("why")
            out[ans.id] = (
                len(territory_sim.holdings_in(game, system.id)),
                game.rep.get("charter", 0) - before,
                getattr(colony, "tithe_to", None),
                getattr(colony, "defiant", False))

        assert out["levy"][0] == 1 and out["levy"][2] == "charter", (
            "paying the levy did not keep the holding and set the tithe")
        assert out["cede"][0] == 0, "ceding did not give up the holding"
        assert out["cede"][1] > out["levy"][1] > 0, (
            "ceding does not read better with them than paying")
        assert out["defy"][0] == 1 and out["defy"][3], "defying did not mark it"
        assert out["defy"][1] < 0, "refusing a power costs nothing"
        return " · ".join(f"{k} held={v[0]} standing{v[1]:+.0f}"
                          for k, v in out.items())

    @check("a levy actually takes a share of what the holding makes")
    def _():
        free, col_free, _s = _planted("levy-free")
        levied, col_levied, sys_levied = _planted("levy-free", "charter")
        territory_sim.answer(levied, sys_levied, "charter", "levy")
        assert col_levied.tithe_to == "charter"

        def year(game) -> float:
            before = dict(game.stores)
            game.advance_days(365)
            return sum(max(0.0, game.stores.get(k, 0) - before.get(k, 0))
                       for k in set(game.stores) | set(before))

        kept_free, kept_levied = year(free), year(levied)
        assert kept_free > 0, "the holding produced nothing to levy"
        share = 1 - kept_levied / kept_free
        assert abs(share - LEVY_SHARE) < 0.05, (
            f"the levy took {share:.0%}, not {LEVY_SHARE:.0%}")
        return (f"{kept_free:,.0f} t a year free, {kept_levied:,.0f} t levied "
                f"— {share:.0%} to the Charter")

    @check("a defiant holding is eventually taken")
    def _():
        taken = 0
        for index in range(12):
            game, colony, system = _planted(f"defy-{index}", "charter")
            territory_sim.answer(game, system, "charter", "defy")
            assert colony.defiant
            for _ in range(8):
                game.advance_days(365)
                if colony not in game.colonies:
                    taken += 1
                    break
        assert taken >= 8, (
            f"only {taken} of 12 defiant holdings were ever taken in 8 years")
        return f"{taken} of 12 taken within eight years of refusing"

    @check("a claim that lapses takes the risk with it")
    def _():
        game, colony, system = _planted("lapse", "charter")
        territory_sim.answer(game, system, "charter", "defy")
        assert colony.defiant
        system.faction = None                 # the claim is gone
        territory_sim.seizures(game, 365, RNG("lapse"))
        assert not colony.defiant, (
            "still standing off against a power that no longer claims it")
        assert colony in game.colonies
        return "the standoff ends with the claim"

    @check("planting on a register costs standing, and can be refused outright")
    def _():
        game = new_game("trespass")
        game.credits = 2_000_000
        game.ship.fitted.append("seed_bay")
        for tech in ("bioleach", "melanin", "oect", "intima"):
            game.research.unlocked.append(tech)
        game.recompute()
        for key in ("alloy", "ore", "biomass", "volatiles", "phosphate"):
            game.stores[key] = 90000
        system = game.system
        system.bloom = 0.0
        system.faction = "charter"
        sites = [b for b in system.bodies
                 if b.kind in ("asteroid", "moon", "rocky") and b.colony is None]
        assert sites, "nowhere to plant in the home system"

        # Distrusted first, on an empty site, so the refusal is about standing
        # and not about the body being occupied.
        #
        # **The two standings are absolute, and they bracket the bar.** This
        # read `UNWELCOME - 10`, which moved with the constant: double the bar
        # to -50 and the standing became -60, still under, still refused,
        # still green — so `UNWELCOME` swept as protected while nothing held
        # it. -26 and -24 sit a point either side of -25, so moving the bar in
        # either direction puts one of them on the wrong side.
        assert UNWELCOME == -25.0, (
            f"the bar moved to {UNWELCOME}; the standings below bracket -25 "
            "with absolute values and have to be re-bracketed by hand, which "
            "is the point of them")
        game.rep["charter"] = -26.0
        ok, refusal = colony_sim.can_found(game, system, sites[0], "radix_mine")
        assert not ok, "planted anyway at -26 standing, under the bar"
        assert "let you put anything down" in refusal, (
            f"refused for the wrong reason: {refusal!r}")

        # And a point the other side of it, they will have you — so this is a
        # bar and not a blanket refusal.
        game.rep["charter"] = -24.0
        ok, why = colony_sim.can_found(game, system, sites[0], "radix_mine")
        assert ok, f"refused at -24, which is above the bar: {why!r}"

        game.rep["charter"] = 40
        before = game.rep["charter"]
        planted, why = colony_sim.found(game, system, sites[0], "radix_mine")
        assert planted, why
        assert game.rep["charter"] < before, "planting on their ground was free"
        return (f"charter {before:+.0f} → {game.rep['charter']:+.0f} for "
                "planting, and refused outright when distrusted")

    @check("unclaimed ground stays free")
    def _():
        game, colony, system = _planted("free-ground")
        assert territory_sim.claimant(game, system) is None
        assert territory_sim.trespass_cost(game, system) == 0
        said, _tint = territory_sim.status(game, colony)
        assert "outright" in said, f"unclaimed ground reads as {said!r}"
        assert territory_sim.confront(game, system, "charter") is None, (
            "a confrontation over ground nobody claims")
        return "no claimant, no cost, no question to answer"

    @check("a demand survives being put down")
    def _():
        import os
        import tempfile

        from ..core import save as save_mod
        from ..core.state import load_game

        game, _colony, system = _planted("resume-demand")
        venture = venture_sim.Venture(id=1, kind="annex", power="charter",
                                      place=system.id, until=game.day)
        venture_sim._apply(game, venture, RNG("annex"))
        assert game.demand is not None
        before = (game.demand.system_id, game.demand.power,
                  round(game.demand.worth))

        os.environ["HOME"] = tempfile.mkdtemp()
        save_mod.write({"game": game})
        back = load_game()
        assert back.demand is not None, "the question was lost over a save"
        after = (back.demand.system_id, back.demand.power,
                 round(back.demand.worth))
        assert after == before, f"{after} != {before}"
        return "the question, the power and the stake all came back"
