"""The living sky: flares, comets, storms, rogues, aurorae and the nova.

The claims, in the spec's order (`reviews/2026-09-17/innovations/
07-phenomena.md`):

- **The sky is the seed's**: two chronicles of one seed have one sky, and
  reading it — every door a screen asks — changes nothing in the save, and
  the sky's day takes nothing from the chronicle's luck.
- **Forecasts precede events with the stated lead, and are honest**: the
  confidence a forecast states is the share of such forecasts that come true.
- **Every effect moves its number**, switched off through `efficacy.Lever`.
- **Shelter avoids the dose**: a berth or a lee, all of it; an orbit, a share.
- **A storm refuses the jump with a reason, and reopens** — the quote, the
  jump, reach, a freight line's route and the deep gates alike.
- (Comets, rogues and the nova — the bodies that come and go — are
  `test_skybodies`.)
- **Observe is its preview**, and the data sells by rarity, once.
- **A save mid-phenomenon survives a fresh process.**
- **The sky costs the day little**, with every region open.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ..core import save as save_mod
from ..core.state import new_game
from ..data import phenomena as data
from ..sim import actions, flight, inquiry, reach
from ..sim import phenomena as sky_sim
from ..sim import phenomena_bodies as bodies_sim
from ..sim import phenomena_forecast as forecast_sim
from ..sim import phenomena_science as science
from ..sim import phenomena_tick as tick_sim
from . import phenomena_kit as kit
from .efficacy import verdict
from .harness import Suite


def _encoded(game) -> str:
    return json.dumps(save_mod.encode({"game": game}), sort_keys=True,
                      default=str)


def _readers(game) -> None:
    """Every door a screen asks of the sky."""
    sky_sim.active(game)
    sky_sim.visible(game)
    sky_sim.forecasts(game)
    sky_sim.shelter(game)
    sky_sim.dose(game)
    sky_sim.exposed(game)
    sky_sim.progress(game)
    science.observe_quote(game)
    science.sale_quote(game)
    for system in game.galaxy.systems[:12]:
        sky_sim.lane_closed(game, game.system, system)
    reach.component(game)


def run(suite: Suite) -> None:
    check = suite.check

    @check("the sky is the seed's, and reading it changes nothing")
    def _():
        a, b = new_game("sky-same"), new_game("sky-same")
        b.advance_days(40)                   # a different day, the same sky
        for season in range(12):
            assert sky_sim.season_map(a, season) == \
                sky_sim.season_map(b, season), season
        other = new_game("sky-other")
        assert sky_sim.season_map(other, 3) != sky_sim.season_map(a, 3)
        a.advance_days(200)
        before, luck = _encoded(a), a.rng_seed
        for _ in range(3):
            _readers(a)
        assert _encoded(a) == before, "asking the sky wrote the save"
        tick_sim.tick(a, 1)                  # the sky's own day, on its own
        assert a.rng_seed == luck, "the sky drew from the chronicle's luck"
        count = sum(len(v) for s in range(12)
                    for v in sky_sim.season_map(a, s).values())
        return (f"{count} scheduled in twelve seasons, identical in two "
                "chronicles; three rounds of every reader left the save "
                "byte-identical and the luck untouched")

    @check("a forecast comes with the stated lead, and its confidence is honest")
    def _():
        said = []
        real_send = forecast_sim._send

        def heard(game, event, target):
            said.append((game.day, event, forecast_sim.confidence(
                game, event.kind), forecast_sim.lead_days(game, event.kind)))
            return real_send(game, event, target)

        forecast_sim._send = heard
        try:
            for seed in ("sky-fc1", "sky-fc2", "sky-fc3", "sky-fc4"):
                game = new_game(seed)
                sky = sky_sim.state(game)
                for _day in range(900):
                    game.day += 1          # the forecast alone, day by day
                    forecast_sim.issue(game, sky)
        finally:
            forecast_sim._send = real_send
        assert len(said) > 150, len(said)
        early = [(d, e) for d, e, _c, lead in said if e.start - d > lead]
        assert not early, f"forecast before its lead: {early[:3]}"
        late = [(d, e) for d, e, _c, _l in said if e.start <= d]
        assert not late, f"forecast after it began: {late[:3]}"
        stated = sum(c for _d, _e, c, _l in said) / len(said)
        came = sum(1 for _d, e, _c, _l in said if e.real) / len(said)
        assert abs(stated - came) < 0.06, (stated, came)
        ahead = sorted(e.start - d for d, e, _c, _l in said)
        return (f"{len(said)} forecasts, {ahead[len(ahead) // 2]} days ahead "
                f"at the median; stated {stated:.0%}, came true {came:.0%}")

    @check("better sensors and a CHORUS Node see further and cry wolf less")
    def _():
        game = new_game("sky-sensors")
        game.ship_stats.scan = 0.3
        low = (forecast_sim.lead_days(game, "comet"),
               forecast_sim.confidence(game, "flare"))
        game.ship_stats.scan = 0.9
        high = (forecast_sim.lead_days(game, "comet"),
                forecast_sim.confidence(game, "flare"))
        real = forecast_sim.chorus
        forecast_sim.chorus = lambda g: True
        try:
            node = (forecast_sim.lead_days(game, "comet"),
                    forecast_sim.confidence(game, "flare"))
        finally:
            forecast_sim.chorus = real
        assert low[0] < high[0] < node[0] and low[1] < high[1] < node[1]
        assert data.COMET.lead == 45 and data.FLARE.real == 0.70
        return (f"comet lead {low[0]} → {high[0]} → {node[0]} days; flare "
                f"confidence {low[1]:.0%} → {high[1]:.0%} → {node[1]:.0%}")

    @check("shelter: a berth or a lee takes all of it, an orbit a share")
    def _():
        game, flare = kit.find("sky-shelter", "flare",
                               lambda g, e: g.galaxy.systems[e.system_id].port
                               and e.end - e.start >= 3)
        kit.at(game, flare)
        game.ship.cargo["volatiles"] = 50
        flight.stand_off(game)
        open_air = sky_sim.dose(game)
        flight.hold_at(game, kit.berth_body(game))
        berth = sky_sim.dose(game)
        body = max((b for b in game.system.bodies
                    if b.id != kit.berth_body(game).id),
                   key=lambda b: b.radius_km, default=None)
        assert body is not None
        flight.hold_at(game, body)
        orbit = sky_sim.dose(game)
        said = sky_sim.keep_lee(game)
        assert said["ok"], said
        lee = sky_sim.dose(game)
        fuel = game.ship.cargo["volatiles"]
        game.advance_days(1)
        burned = fuel - game.ship.cargo.get("volatiles", 0.0)
        assert open_air > 0.5 and berth == 0.0 and lee == 0.0, (
            open_air, berth, lee)
        assert 0.0 < orbit < open_air, (orbit, open_air)
        assert abs(burned - data.LEE_FUEL) < 1e-6, burned
        # And the geometry, in free space: behind a body, in its cone.
        star_km = 695_700.0
        assert sky_sim.shelter  # the door the dose reads
        from ..sim.phenomena_shelter import in_umbra
        assert in_umbra((5.0 + 1e-5, 0, 0), (5.0, 0, 0), 60_000, star_km)
        assert not in_umbra((5.0 - 1e-5, 0, 0), (5.0, 0, 0), 60_000, star_km)
        assert not in_umbra((5.0 + 1e-5, 1e-3, 0), (5.0, 0, 0), 60_000,
                            star_km)
        return (f"dose {open_air:.2f} in the open, {orbit:.2f} holding orbit "
                f"at {body.name}, 0 at the quay, 0 in the lee for "
                f"{burned:g} t a day")

    @check("an unsheltered flare costs 1-3% of morale, and never a life")
    def _():
        rows = []
        for seed in ("sky-cost1", "sky-cost2", "sky-cost3", "sky-cost4"):
            game, flare = kit.find(seed, "flare",
                                   lambda g, e: e.end - e.start >= 2)
            kit.put(game, flare.system_id)
            kit.on_day(game, flare.start - 1)
            crew = game.ship.crew

            def cost(neutral: bool) -> float:
                twin = save_mod.decode(save_mod.encode({"game": game}))["game"]
                twin.recompute()
                real = sky_sim.dose
                if neutral:
                    sky_sim.dose = lambda g, st=None: 0.0
                try:
                    twin.advance_days(flare.end - flare.start + 1)
                finally:
                    sky_sim.dose = real
                return twin.ship.morale, twin.ship.crew

            (hit, crew_hit), clear = cost(False), cost(True)[0]
            rows.append(clear - hit)
            assert crew_hit == crew, "a flare killed somebody"
        assert rows and all(0.004 <= r <= 0.06 for r in rows), rows
        mean = sum(rows) / len(rows)
        assert 0.01 <= mean <= 0.03, rows
        return "morale lost " + ", ".join(f"{r:.1%}" for r in rows)

    @check("every phenomenon's effect moves its number, switched off")
    def _():
        levers = _levers()
        assert len(levers) >= 12, "an effect went unmeasured"
        lines = []
        for lever in levers:
            ok, said = verdict(lever)
            assert ok, said
            lines.append(said.split(":")[0])
        assert len(lines) == len(levers)
        return f"{len(lines)} levers: " + ", ".join(lines)

    @check("a storm refuses the jump with a reason, everywhere, and reopens")
    def _():
        from ..world.galaxy import distance
        game, storm = kit.find("sky-storm", "storm",
                               lambda g, e: e.end - e.start >= 4)
        eye = game.galaxy.systems[storm.system_id]
        near = min((s for s in game.galaxy.systems if s.id != eye.id),
                   key=lambda s: distance(s, eye))
        kit.put(game, near.id)
        kit.on_day(game, storm.start + 1)
        game.ship.cargo["volatiles"] = 300
        quote = actions.jump_quote(game, eye)
        refused = actions.jump_to(game, eye.id)
        assert quote["closed"] and not refused["ok"]
        assert "ion storm" in refused["why"] and "days" in refused["why"]
        assert eye.id not in reach.component(game)
        assert eye.id not in reach.routes_from(game)
        from ..sim import lineroute
        assert lineroute.path(game, near.id, eye.id, 30.0) is None
        from ..sim import gates as gates_sim
        real = gates_sim.route
        gates_sim.route = lambda g, to, frm=None: [to]
        try:
            ring = gates_sim.quote(game, eye.id)
        finally:
            gates_sim.route = real
        assert not ring["ok"] and "ion storm" in ring["why"], ring
        kit.on_day(game, storm.end)
        opened = actions.jump_to(game, eye.id)
        assert opened["ok"], opened
        return (f"{eye.name}: jump, reach, a line and a ring all refused on "
                f"day {storm.start + 1}; jumped in on day {storm.end}")

    @check("observe is its preview, once an event; the data sells by rarity")
    def _():
        game, comet = kit.find("sky-watch", "comet")
        kit.at(game, comet, 1)
        quote = science.observe_quote(game)
        day, held = game.day, inquiry.held(game.research, "phenomena")
        out = science.observe(game)
        assert out["ok"] and game.day - day == quote["days"]
        assert abs(inquiry.held(game.research, "phenomena") - held
                   - quote["evidence"]) < 1e-9
        again = science.observe_quote(game)
        assert again.get("event") != out["event"], "watched the same twice"
        from ..sim.phenomena import Observation
        prices = {k.id: science.price(Observation(
            "x", k.id, 0, 0, 1.0, 0.0), "charter", False)
            for k in (*data.KINDS, data.NOVA)}
        ladder = [prices[k] for k in data.PRIORITY]
        assert ladder == sorted(ladder, reverse=True), prices
        burst = Observation("x", "nova", 0, 0, 1.0, 0.0, stage="burst")
        assert science.price(burst, "sanhedrin", False) > \
            2 * science.price(burst, "charter", False)
        first = science.price(game.sky.observed[0], "charter", True)
        assert first > science.price(game.sky.observed[0], "charter", False)
        port = next(s for s in game.galaxy.systems
                    if s.port and s.port.faction == "charter")
        kit.put(game, port.id)
        sale = science.sale_quote(game)
        from ..sim import exchequer
        money, purse = game.credits, exchequer.purse(game, "charter").credits
        sold = science.sell(game)
        # The quote is what lands: the button read 4,819 and paid 4,738,
        # the wharfage unmentioned — and the buyer's purse pays for it.
        assert sold["ok"] and game.credits - money == sale["net"], (
            sale["net"], game.credits - money)
        assert sold["total"] == sale["total"]
        spent = purse - exchequer.purse(game, "charter").credits
        assert abs(spent - (sale["total"] - sale["due"])) < 1, spent
        assert not science.sale_quote(game)["ok"], "sold twice"
        return (f"{quote['days']} d for {quote['evidence']:g} evidence; "
                f"ladder {ladder}; sold for {sold['total']:,}")

    @check("a save in the middle of a comet survives a fresh process")
    def _():
        game, comet = kit.find("sky-save", "comet")
        kit.at(game, comet, 2)
        science.observe(game)
        body = game.system.bodies[-1]
        path = Path(tempfile.mkdtemp(prefix="seedfall-sky-")) / "s.json"
        assert save_mod.write({"game": game}, path)
        code = ("import json\nfrom seedfall.core.state import load_game\n"
                f"g = load_game({str(path)!r})\n"
                "b = g.system.bodies[-1]\n"
                "g.advance_days(1)\n"
                "print(json.dumps({'body': b.id, 'until': b.transient_until,"
                " 'transients': g.sky.transients, 'seen': len(g.sky.observed),"
                " 'kind': type(g.sky.observed[0]).__name__}))\n")
        env = dict(os.environ, SEEDFALL_SAVE=str(path),
                   QT_QPA_PLATFORM="offscreen")
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                              text=True, env=env, timeout=300,
                              cwd=str(Path(__file__).resolve().parents[2]))
        lines = [l for l in proc.stdout.splitlines() if l.startswith("{")]
        assert lines, proc.stderr[-600:]
        got = json.loads(lines[-1])
        assert got["body"] == body.id and got["until"] == comet.end, got
        assert got["transients"] == game.sky.transients, got
        assert got["seen"] == 1 and got["kind"] == "Observation", got
        before = new_game("sky-old")
        before.advance_days(3)
        raw = save_mod.encode({"game": before})
        raw["game"].pop("sky", None)
        for system in raw["game"]["galaxy"]["systems"]:
            for b in system["bodies"]:
                b.pop("transient_until", None)
        old = save_mod.decode(raw)["game"]
        old.recompute()
        old.advance_days(1)
        assert old.sky is not None
        return f"{body.name} and the watch came back in a new process"

    @check("watching the sky speeds the programmes it feeds, and no others")
    def _():
        def days(tech_id: str, stocked: bool) -> int:
            game = new_game("sky-bench")
            game.research.current, game.research.progress = tech_id, 0.0
            start = game.day
            while game.research.current == tech_id and game.day < 1500:
                for kind in ("survey", "specimen", "hardware", "reading"):
                    inquiry.add(game.research, kind, 300)
                if stocked:
                    inquiry.add(game.research, "phenomena", 300)
                game.advance_days(2)
            return game.day - start

        fed, plain = days("melanin", True), days("melanin", False)
        other, other_plain = days("osteoid", True), days("osteoid", False)
        uplift = plain / fed - 1.0
        assert 0.10 <= uplift <= 0.20, (fed, plain)
        assert other == other_plain, (other, other_plain)
        assert data.UPLIFT == 0.15 and "melanin" in data.FEEDS
        return (f"melanised rind {plain} → {fed} days (+{uplift:.0%}); "
                f"osteoid trusses {other_plain} either way")

    @check("the sky costs the day little, with every region open")
    def _():
        from ..world import regions as world_regions

        def per_day(game) -> float:
            start = time.perf_counter()
            game.advance_days(60)
            return (time.perf_counter() - start) * 1000.0 / 60

        live, quiet = new_game("sky-perf"), new_game("sky-perf")
        for game in (live, quiet):
            for rid in ("shoals", "hollow", "cradle"):
                world_regions.generate(game.galaxy, rid, 0)
        # The whole sky off, readers included: the day, the schedule, gluts.
        doors = [(sky_sim, "tick", lambda *a, **k: None),
                 (sky_sim, "_today", lambda g: {}),
                 (bodies_sim, "gluts", lambda g: {})]
        real = [getattr(module, name) for module, name, _off in doors]
        on, off = [], []
        try:
            for _ in range(3):
                on.append(per_day(live))
                for module, name, neutral in doors:
                    setattr(module, name, neutral)
                off.append(per_day(quiet))
                for (module, name, _n), was in zip(doors, real):
                    setattr(module, name, was)
        finally:
            for (module, name, _n), was in zip(doors, real):
                setattr(module, name, was)
        ratio = min(on) / max(1e-9, min(off))
        assert ratio <= 1.3, f"{min(on):.2f} against {min(off):.2f} ms/day"
        return (f"{min(off):.2f} ms/day without the sky, {min(on):.2f} with "
                f"it ({ratio:.2f}x), 78 systems")


def _levers() -> list:
    from . import phenomena_levers
    return phenomena_levers.levers()
