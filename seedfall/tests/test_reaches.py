"""The Far Reaches: three regions past the rim, behind gates you relight.

The claims, in the spec's own order (`reviews/2026-09-17/innovations/
01-far-reaches.md`):

- **The Verge is never re-rolled.** Regions generate deterministically, and
  opening all three leaves every Verge system byte-identical — hashed before
  and after — except the condensate line the Shoals give the buyers' markets,
  which is the point of opening them.
- **The ancient Weave does not move**: sites, rings and dawn chain.
- **Across the rim is infinitely far**, so nothing reaches it without the gate.
- **The relight preview is the act**: credits, materials and days.
- **The deep gate carries a hull both ways**, and lands it at the entry.
- **Every region rule moves its number**, and switching it off moves it back.
- **A save with regions open survives a fresh process**, and a save from
  before the Reaches can open one.
- **Opening all three costs the day at most 60% more.**
- **The Bloom walks the deep gate** at the Weave's pace, and not before.
- **The endings stay the Verge's.**
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ..core import save as save_mod
from ..core.state import new_game
from ..data.regions import (CONDENSATE, CONDENSATE_BUYERS, DEEP_TECH, REGIONS,
                            RELIGHT_DAYS, RELIGHT_GOODS)
from ..sim import flight, gates as gates_sim, regions as regions_sim
from ..sim import relight as relight_sim, weave as weave_sim
from ..world import regions as world_regions
from ..world.galaxy import distance, verge
from .efficacy import Lever, verdict
from .harness import Suite

IDS = [spec.id for spec in REGIONS]


def rich(seed: str):
    """A captain who can pay for any relight, so only the rules bite."""
    game = new_game(seed)
    game.credits = 5_000_000
    game.research.unlocked = list({*game.research.unlocked, DEEP_TECH})
    for cid, need in RELIGHT_GOODS.items():
        game.stores[cid] = need * 4
    game.ship.cargo["volatiles"] = 200
    game.recompute()
    return game


def put(game, sid: int) -> None:
    game.location_id = sid
    flight.arrive_in_system(game)


def open_region(game, rid: str) -> dict:
    """Stand at the anchor, read it, and relight it through the one door."""
    sid = relight_sim.anchor_of(game, rid)
    put(game, sid)
    weave_sim.ensure(game).read.append(sid)
    out = relight_sim.relight(game, rid)
    assert out["ok"], out
    return out


def _digest(obj) -> str:
    blob = json.dumps(save_mod.encode(obj), sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _verge_hash(game) -> str:
    """Every Verge system, with the one line opening the Shoals may add."""
    rows = []
    for system in verge(game.galaxy):
        row = save_mod.encode(system)
        stock = (row.get("market") or {}).get("stock") or {}
        stock.pop(CONDENSATE, None)
        rows.append(row)
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def run(suite: Suite) -> None:
    check = suite.check

    @check("regions generate deterministically, and the Verge is not re-rolled")
    def _():
        a, b = rich("reaches-same"), rich("reaches-same")
        buyers_before = sum(1 for s in verge(a.galaxy)
                            if s.market and CONDENSATE in s.market.stock)
        assert buyers_before == 0, "a Verge market stocked condensate unopened"
        # The opening itself, hashed either side: the days a relight works
        # are days like any other, and the Verge lives through them.
        for rid in IDS:
            before = _verge_hash(a)
            world_regions.generate(a.galaxy, rid, a.day)
            if rid == "shoals":
                world_regions.open_buyers(a.galaxy)
            assert _verge_hash(a) == before, f"opening {rid} changed the Verge"
        for rid in reversed(IDS):           # the other order
            world_regions.generate(b.galaxy, rid, 0)

        def grown(game, rid):
            return [(s.name, round(s.x, 9), round(s.y, 9), s.star,
                     _digest(s.bodies))
                    for s in world_regions.systems_of(game.galaxy, rid)]
        for rid in IDS:
            assert grown(a, rid) == grown(b, rid), (
                f"one seed grew two different {rid}s, opened in two orders")
        assert all(s.id == i for i, s in enumerate(a.galaxy.systems))
        counts = {rid: len(world_regions.systems_of(a.galaxy, rid)) for rid in IDS}
        assert counts == {s.id: s.count for s in REGIONS}, counts
        return (f"{len(a.galaxy.systems)} systems (42 + {counts}), ids == index, "
                "Verge hash identical before and after")

    @check("the ancient Weave is the same Weave after the Reaches open")
    def _():
        game = rich("reaches-weave")
        shape = (weave_sim.sites(game.galaxy), weave_sim.ancient_links(game.galaxy),
                 weave_sim.lit_at_dawn(game.galaxy))
        for rid in IDS:
            open_region(game, rid)
        weave_sim._SHAPE.clear()            # asked afresh, not remembered
        again = (weave_sim.sites(game.galaxy),
                 weave_sim.ancient_links(game.galaxy),
                 weave_sim.lit_at_dawn(game.galaxy))
        assert again == shape, "opening a region re-sampled the ancient Weave"
        assert all(s < 42 for s in again[0])
        return f"{len(shape[0])} ancient sites, rings and dawn chain unchanged"

    @check("across the rim is infinitely far, and only the gate crosses it")
    def _():
        from ..sim import actions, reach
        game = rich("reaches-far")
        out = open_region(game, "shoals")
        entry, anchor = out["entry"], game.system
        assert distance(anchor, entry) == float("inf")
        assert all(distance(s, anchor) == float("inf")
                   for s in world_regions.systems_of(game.galaxy, "shoals"))
        game.ship_stats.jump = 10_000.0
        within = reach.component(game, jump=10_000.0)
        assert not within & {s.id for s in world_regions.systems_of(
            game.galaxy, "shoals")}, "a drive reached past the rim"
        said = actions.jump_to(game, entry.id)
        assert not said["ok"] and "rim" in said["why"], said
        span = world_regions.span(game.galaxy, entry, anchor)
        assert span == 0.0, span            # entry to anchor is the crossing
        return f"a 10,000 ly drive reaches {len(within)} Verge systems and none past it"

    @check("the relight preview is the act: credits, materials and days")
    def _():
        game = rich("reaches-preview")
        sid = relight_sim.anchor_of(game, "cradle")
        put(game, sid)
        said = relight_sim.preview(game, "cradle")
        assert not said["ok"] and "survey" in said["why"], said["why"]
        from ..sim import survey
        body = min(range(len(game.system.bodies)),
                   key=lambda i: game.system.bodies[i].radius_km)
        game.ship_stats.scan = max(game.ship_stats.scan, 0.6)
        got = survey.perform(game, body, "deep")
        assert got["ok"], got
        put(game, sid)                        # the survey may have flown her
        said = relight_sim.preview(game, "cradle")
        assert said["ok"], said["why"]
        day = game.day
        out = relight_sim.relight(game, "cradle")
        assert out["ok"], out
        assert abs(out["spent"]["credits"] - said["credits"]) < 1e-6
        for cid, need in said["goods"].items():
            assert abs(out["spent"][cid] - need) < 1e-6, (cid, out["spent"])
        assert game.day - day == said["days"] == RELIGHT_DAYS
        return (f"₡{said['credits']:,.0f}, {said['goods']}, {said['days']} d "
                "quoted, and exactly that spent")

    @check("the deep gate carries a hull both ways, free, to the entry")
    def _():
        game = rich("reaches-gate")
        out = open_region(game, "hollow")
        anchor, entry = game.location_id, out["entry"].id
        said = gates_sim.quote(game, entry)
        assert said["ok"] and said["credits"] == 0, said
        money = game.credits
        went = gates_sim.use(game, entry)
        assert went["ok"] and game.location_id == entry, went
        assert game.system.region == "hollow"
        back = gates_sim.use(game, anchor)
        assert back["ok"] and game.location_id == anchor, back
        assert game.credits >= money - 5_000, "a toll was charged somewhere"
        rings = world_regions.region(game.galaxy, "hollow").rings
        assert rings and all(weave_sim.network(game).get(a) for a, _b in rings)
        return (f"anchor {anchor} → entry {entry} → anchor, ₡0 in tolls; "
                f"{len(rings)} Hollow rings lit")

    @check("every region rule moves its number, and switching it off moves it back")
    def _():
        game = rich("reaches-rules")
        for rid in IDS:
            open_region(game, rid)
        shoals = world_regions.region(game.galaxy, "shoals").entry_id
        cradle = world_regions.region(game.galaxy, "cradle").entry_id
        rogue = next((s, i) for s in world_regions.systems_of(game.galaxy, "hollow")
                     for i, b in enumerate(s.bodies) if b.sunless)
        from ..sim import detection, piracy, survey

        def at(sid):
            put(game, sid)
            return game

        def dark_air():
            put(game, rogue[0].id)
            flight.hold_at(game, rogue[0].bodies[rogue[1]])
            game.ship.o2 = 1.0
            game.advance_days(5)
            return game.ship.o2

        def cradle_after(what):
            def probe():
                put(game, cradle)
                game.ship.morale, game.ship.heat = 0.8, 0.0
                game.advance_days(10)
                return getattr(game.ship, what)
            return probe

        levers = [
            Lever("shoals-sensor", "the nebula halves the array",
                  (regions_sim, "sensor_scale", lambda g: 1.0),
                  lambda: detection.sensor_of(at(shoals)), "higher"),
            Lever("shoals-sweep", "and the sweep's reach with it",
                  (regions_sim, "sensor_scale", lambda g: 1.0),
                  lambda: survey.reach(at(shoals)), "higher"),
            Lever("shoals-survey", "a survey reads less in the gas",
                  (regions_sim, "survey_scale", lambda g: 1.0),
                  lambda: survey.preview(at(shoals), game.system.bodies[0],
                                         "pass")["quality"], "higher"),
            Lever("shoals-law", "nobody's law reaches the Shoals",
                  (regions_sim, "lawless", lambda g, s: 0.0),
                  lambda: piracy.lawlessness(game, game.galaxy.systems[shoals]),
                  "lower"),
            Lever("hollow-dark", "no light, no air off the intima",
                  (regions_sim, "lit", lambda g: True), dark_air, "higher"),
            Lever("cradle-dose", "the dose takes morale",
                  (regions_sim, "dose", lambda g, st=None: 0.0),
                  cradle_after("morale"), "higher"),
            Lever("cradle-heat", "the light keeps the hull hot",
                  (regions_sim, "irradiate", lambda g, d, st: {}),
                  cradle_after("heat"), "lower"),
        ]
        assert len(levers) == 7, "a region rule went unmeasured"
        lines = []
        for lever in levers:
            ok, said = verdict(lever)
            assert ok, said
            lines.append(said.split(";")[0])
        assert len(lines) == len(levers)
        return " · ".join(lines)

    @check("shielding and a melanised rind cut the Cradle's dose")
    def _():
        game = rich("reaches-dose")
        put(game, open_region(game, "cradle")["entry"].id)
        bare = regions_sim.dose(game)
        game.research.unlocked.append("melanin")
        rind = regions_sim.dose(game)
        game.ship_stats.crew_guard = 0.45
        both = regions_sim.dose(game)
        assert bare == 1.0 and bare > rind > both > 0, (bare, rind, both)
        return f"dose {bare:.2f} bare, {rind:.2f} with a rind, {both:.2f} shielded too"

    @check("condensate is made in the Shoals and bought dear by two powers")
    def _():
        from ..sim import market as market_sim
        game = rich("reaches-condensate")
        open_region(game, "shoals")
        havens = [s for s in world_regions.systems_of(game.galaxy, "shoals")
                  if s.market]
        buyers = [s for s in verge(game.galaxy) if s.market
                  and CONDENSATE in s.market.stock]
        assert havens and all(CONDENSATE in s.market.stock for s in havens)
        assert buyers and all(s.port.faction in CONDENSATE_BUYERS for s in buyers)
        cheap = min(market_sim.quote_buy(game, s, CONDENSATE) for s in havens)
        dear = max(market_sim.quote_sell(game, s, CONDENSATE) for s in buyers)
        assert dear > cheap * 1.5, (cheap, dear)
        return (f"{len(havens)} havens sell from ₡{cheap}, {len(buyers)} buyers "
                f"pay up to ₡{dear} a tonne")

    @check("a save with the Reaches open survives a fresh process")
    def _():
        game = rich("reaches-save")
        for rid in IDS:
            open_region(game, rid)
        gates_sim.use(game, world_regions.region(game.galaxy, "cradle").entry_id)
        path = Path(tempfile.mkdtemp(prefix="seedfall-reaches-")) / "s.json"
        assert save_mod.write({"game": game}, path)
        code = ("import json\nfrom seedfall.core.state import load_game\n"
                f"g = load_game({str(path)!r})\n"
                "print(json.dumps({'n': len(g.galaxy.systems), "
                "'regions': [r.id for r in g.galaxy.regions], "
                "'at': g.system.name, 'region': g.system.region, "
                "'rings': [r.rings for r in g.galaxy.regions]}))\n")
        env = dict(os.environ, SEEDFALL_SAVE=str(path), QT_QPA_PLATFORM="offscreen")
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                              text=True, env=env, timeout=300,
                              cwd=str(Path(__file__).resolve().parents[2]))
        lines = [l for l in proc.stdout.splitlines() if l.startswith("{")]
        assert lines, proc.stderr[-600:]
        got = json.loads(lines[-1])
        want = {"n": len(game.galaxy.systems), "regions": IDS,
                "at": game.system.name, "region": "cradle",
                "rings": [r.rings for r in game.galaxy.regions]}
        assert got == want, (got, want)
        return f"{got['n']} systems, {got['regions']}, aboard at {got['at']}"

    @check("a save from before the Reaches opens a region")
    def _():
        game = rich("reaches-old")
        raw = save_mod.encode({"game": game})
        body = raw["game"]
        body["galaxy"].pop("regions", None)
        for system in body["galaxy"]["systems"]:
            system.pop("region", None)
            for b in system["bodies"]:
                b.pop("sunless", None)
        body["weave"] = None
        old = save_mod.decode(raw)["game"]
        old.recompute()
        assert old.galaxy.regions == [] and old.system.region == "verge"
        out = open_region(old, "shoals")
        assert gates_sim.use(old, out["entry"].id)["ok"]
        return f"opened on day {old.day}, standing at {old.system.name}"

    @check("the Bloom walks a lit deep gate at the Weave's pace")
    def _():
        from ..sim import threat

        def played(carry: bool) -> tuple:
            game = rich("reaches-bloom")
            out = open_region(game, "shoals")
            anchor, entry = game.system, out["entry"]
            anchor.bloom, entry.bloom = 0.6, 0.0
            game.bloom_clock = 0.0
            real = gates_sim.bloom_links
            if not carry:
                gates_sim.bloom_links = lambda g: [
                    x for x in real(g)
                    if (min(x[0], x[1]), max(x[0], x[1]))
                    not in set(weave_sim.deep_links(g))]
            try:
                game.advance_days(threat.SPREAD_INTERVAL - 1)
                early = entry.bloom
                game.advance_days(1)
            finally:
                gates_sim.bloom_links = real
            return early, entry.bloom

        early, crossed = played(True)
        _early, shut = played(False)
        assert early == 0.0, f"growth crossed {early} before the season was out"
        assert crossed > 0.02 and shut == 0.0, (crossed, shut)
        return (f"0.00 at day {threat.SPREAD_INTERVAL - 1}, {crossed:.3f} at "
                f"day {threat.SPREAD_INTERVAL}; 0.00 with the deep link shut")

    @check("the endings stay the Verge's")
    def _():
        from ..sim import threat
        game = rich("reaches-endings")
        before = threat.victory_progress(game)
        heart = threat.bloom_sim.heart_system(game).id
        for rid in IDS:
            world_regions.generate(game.galaxy, rid, game.day)
        for system in world_regions.systems_of(game.galaxy, "cradle"):
            system.bloom = 1.0
        after = threat.victory_progress(game)
        assert after == before, {k: (before[k], after[k]) for k in after
                                 if after[k] != before[k]}
        assert after["containment"][1] == 84 and after["ruin"][1] == 42
        assert threat.harbours_left(game)[1] == len(
            [s for s in verge(game.galaxy) if s.port])
        game.bloom_state = None             # asked afresh, with 78 in the sky
        assert threat.bloom_sim.heart_system(game).id == heart
        return (f"containment over {after['containment'][1] // 2}, ruin over "
                f"{after['ruin'][1]}, with the whole Cradle overgrown")

    @check("the Cradle is left unclaimed, and its only quays are the Kith's")
    def _():
        game = rich("reaches-kith")
        open_region(game, "cradle")
        cradle = world_regions.systems_of(game.galaxy, "cradle")
        # Innovation 2 lays the Kith's gatherings in at the relight
        # (`sim/kith_world`): ports of theirs, on ground nobody claims.
        ported = [s for s in cradle if s.port is not None]
        assert all(s.faction is None for s in cradle)
        assert ported and all(s.port.faction == "kith" for s in ported)
        from ..sim import ventures
        assert not any(s.region == "cradle"
                       for s in ventures._claimable(game, "charter"))
        return (f"{len(cradle)} Cradle systems, none claimed; "
                f"{len(ported)} Kith gatherings, no other quay")

    @check("opening all three costs the day at most 60% more")
    def _():
        def per_day(game) -> float:
            start = time.perf_counter()
            game.advance_days(60)
            return (time.perf_counter() - start) * 1000.0 / 60

        closed, wide = rich("reaches-perf"), rich("reaches-perf")
        home = wide.location_id
        for rid in IDS:
            open_region(wide, rid)
        put(wide, home)
        closed.advance_days(RELIGHT_DAYS * len(IDS))   # the same calendar
        shut, opened = [], []
        for _ in range(3):
            shut.append(per_day(closed))
            opened.append(per_day(wide))
        ratio = min(opened) / max(1e-9, min(shut))
        assert ratio <= 1.6, f"{min(opened):.2f} against {min(shut):.2f} ms/day"
        return (f"{min(shut):.2f} ms/day with none open, {min(opened):.2f} with "
                f"all three ({ratio:.2f}x)")
