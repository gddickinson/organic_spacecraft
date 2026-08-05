"""Empire checks — colonies that keep developing after they are planted.

A colony used to be a purchase: plant it, and it emitted the same numbers
forever. These hold the works layer to the promise that investing in a
settlement changes what it is.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.works import MAX_WORKS, WORKS
from ..sim import colony as colony_sim
from ..sim import works as works_sim
from .harness import Suite

#: The same vocabulary a colony class may use — works feed the same aggregator.
KNOWN_EFFECTS = {"gestation", "build_here", "sensor", "watch", "drift",
                 "diplomacy", "medical", "vault", "megastructure",
                 "fabricate", "ward", "port", "xenoyard", "drydock"}


def _settled(seed: str, class_id: str = "radix_mine", tech: str = "bioleach",
             portless: bool = False):
    """A game with one matured colony, and the means to develop it."""
    g = new_game(seed)
    g.credits = 900000
    g.ship.fitted.append("seed_bay")
    g.research.unlocked.append(tech)
    g.recompute()
    for key in ("alloy", "ore", "biomass", "volatiles"):
        g.stores[key] = 9000
    sites = ("asteroid", "moon", "rocky")
    if portless:
        system = next(s for s in g.galaxy.systems
                      if s.port is None and any(b.kind in sites for b in s.bodies))
    else:
        system = g.system
    body = next(b for b in system.bodies if b.kind in sites)
    col, why = colony_sim.found(g, system, body, class_id)
    assert col is not None, f"could not plant a colony: {why}"
    g.advance_days(col.need + 20)
    assert col.online, "the colony never matured"
    return g, col, system


def run(suite: Suite) -> None:
    check = suite.check

    @check("every work is buildable somewhere and its effects are understood")
    def _():
        from ..data.colonies import COLONIES
        families = {c.family for c in COLONIES}
        produced = set()
        for c in COLONIES:
            produced |= set(c.yields)
        for work in WORKS:
            bad = set(work.effects) - KNOWN_EFFECTS
            assert not bad, f"{work.id} has unhandled effect {bad}"
            assert work.days > 0, f"{work.id} takes no time"
            assert work.cost, f"{work.id} is free"
            bad_fam = set(work.families) - families
            assert not bad_fam, f"{work.id} restricted to unknown family {bad_fam}"
            if work.needs_yield:
                assert set(work.needs_yield) & produced, (
                    f"{work.id} requires a yield no colony produces")
        return f"{len(WORKS)} works, at most {MAX_WORKS} to a colony"

    @check("a finished work changes what the colony produces")
    def _():
        g, col, _ = _settled("deepen")
        before = works_sim.yields_of(col)
        upkeep_before = works_sim.upkeep_of(col)
        assert works_sim.begin(g, col, "deepen")["ok"], "could not begin"
        assert col.job == "deepen", "the work did not start"
        g.advance_days(95)
        assert col.works == ["deepen"], f"work did not finish: {col.works}"
        assert col.job is None, "the work stayed under way after finishing"

        after = works_sim.yields_of(col)
        assert after["ore"] > before["ore"] * 1.5, (
            f"deepening barely helped: {before['ore']:.2f} → {after['ore']:.2f}")
        assert (sum(works_sim.upkeep_of(col).values())
                > sum(upkeep_before.values())), "a deeper mine costs no more to run"
        return (f"ore/day {before['ore']:.2f} → {after['ore']:.2f}, "
                f"upkeep rose")

    @check("work effects reach the rest of the game")
    def _():
        seen = []
        for work_id, probe in (
                ("garrison", lambda g, c: colony_sim.ward_at(g, c.system_id)),
                # The colony's own effect, which is the granularity
                # `shipyard.can_build_here` consults. This used to read
                # `colony_fx["build_systems"]`, an aggregate the game itself
                # never opened — so it proved the bookkeeping rather than the
                # slipway.
                ("slipway",
                 lambda g, c: bool(works_sim.effects_of(c).get("build_here"))),
                ("mast", lambda g, c: g.colony_fx["sensor_by_system"].get(c.system_id, 0)),
        ):
            g, col, _ = _settled(f"fx-{work_id}")
            g.recompute()
            before = probe(g, col)
            assert works_sim.begin(g, col, work_id)["ok"], f"{work_id} refused"
            g.advance_days(160)
            g.recompute()
            after = probe(g, col)
            assert after and after != before, (
                f"{work_id} finished but changed nothing: {before} → {after}")
            seen.append(f"{work_id} {before}→{after}")
        return " · ".join(seen)

    @check("a free harbour opens a market where a work grants one")
    def _():
        # The port effect used to be read only when a colony matured, so a
        # harbour built afterwards granted the effect and no actual market.
        g, col, system = _settled("harbour", portless=True)
        assert system.port is None, "picked a system that already had a port"
        assert works_sim.begin(g, col, "harbour")["ok"], "harbour refused"
        g.advance_days(200)
        assert "harbour" in col.works, "the harbour never finished"
        assert system.port is not None, (
            "the work granted the port effect but opened no harbour")
        assert system.market is not None, "a harbour with nothing to trade"
        return f"{system.name} now trades"

    @check("works cost material, and a colony cannot overreach")
    def _():
        g, col, _ = _settled("limits")
        g.credits = 0
        g.stores.clear()
        g.ship.cargo.clear()
        offered = dict((w.id, (ok, why)) for w, ok, why in works_sim.available(g, col))
        assert offered, "nothing offered at all"
        assert not any(ok for ok, _why in offered.values()), (
            "a penniless empire can still build")
        assert works_sim.begin(g, col, "deepen")["ok"] is False, "built for free"

        g.credits = 900000
        for key in ("alloy", "ore", "biomass", "volatiles"):
            g.stores[key] = 9000
        before = g.credits
        works_sim.begin(g, col, "mast")
        assert g.credits < before, "the work cost nothing"
        # One at a time.
        second = works_sim.begin(g, col, "deepen")
        assert not second["ok"], "two works ran at once"

        col.works = [w.id for w in WORKS[:MAX_WORKS]]
        col.job = None
        assert not any(ok for _w, ok, _why in works_sim.available(g, col)), (
            f"a colony took on more than {MAX_WORKS} works")
        return f"costs charged, one at a time, capped at {MAX_WORKS}"

    @check("an empire costs more to administer the bigger it gets")
    def _():
        # A Grove paid itself back in 45 days and yielded for ever, there
        # are about 125 plantable sites in a sector, and nothing capped how
        # many you held — so colony spam was the strategy and the game had
        # no late-game credit sink at all. Played: the marginal worth of one
        # more holding has to fall as the empire grows.
        from ..sim.colony import Colony, _WORTH

        def worth_a_day(count: int, days: int = 60) -> float:
            game = new_game("admin-curve")
            game.credits = 10 ** 7
            for key in ("biomass", "volatiles", "ore", "alloy", "phosphate"):
                game.stores[key] = 10 ** 6
            game.colonies = [
                Colony(id=i, class_id="pomona_grove", name=f"Grove {i}",
                       system_id=game.galaxy.systems[i % 40].id, body_id=0,
                       need=1, online=True, pop=400)
                for i in range(count)]
            was_credits, was_stores = game.credits, dict(game.stores)
            gains, _events = colony_sim.tick(game, days)
            moved = sum((game.stores.get(k, 0) - was_stores.get(k, 0))
                        * _WORTH.get(k, 0)
                        for k in set(list(game.stores) + list(was_stores)))
            moved += sum(v * _WORTH.get(k, 0) for k, v in gains.items())
            return (game.credits - was_credits + moved) / days

        small, large = worth_a_day(5), worth_a_day(25)
        marginal_small = (worth_a_day(6) - small)
        marginal_large = (worth_a_day(26) - large)
        assert marginal_small > marginal_large > 0, (
            f"the sixth holding is worth {marginal_small:.0f} a day and the "
            f"twenty-sixth {marginal_large:.0f} — an empire that never gets "
            "harder to run has no ceiling and no sink")
        assert works_sim.admin_total(1) == 0, (
            "a single holding is billed for administering itself")

        # And the seed card says so before the credits are spent.
        game, _col, system = _settled("admin-quote")
        body = next(b for b in system.bodies if b.kind in ("asteroid", "moon",
                                                           "rocky"))
        plan = colony_sim.forecast(game, system, body, "pomona_grove")
        assert plan["admin"] > 0, "the card quoted an empire that runs itself"
        return (f"the 6th holding is worth {marginal_small:.0f}/day and the "
                f"26th {marginal_large:.0f}; the card quotes "
                f"{plan['admin']:.0f}/day before you commit")

    @check("a colony's works survive a save and reload")
    def _():
        import json

        from ..core.save import decode, encode

        g, col, _ = _settled("persist")
        works_sim.begin(g, col, "deepen")
        g.advance_days(95)
        works_sim.begin(g, col, "garrison")
        g.advance_days(10)

        reloaded = decode(json.loads(json.dumps(encode(g))))
        back = next(c for c in reloaded.colonies if c.id == col.id)
        assert back.works == col.works, f"works lost: {back.works} != {col.works}"
        assert back.job == col.job, "the work under way was lost"
        assert abs(back.job_days - col.job_days) < 0.001, "progress was lost"
        assert (works_sim.yields_of(back)["ore"]
                == works_sim.yields_of(col)["ore"]), "yields differ after reload"
        return f"{back.works} kept, {back.job} still {works_sim.progress(back):.0%} done"
