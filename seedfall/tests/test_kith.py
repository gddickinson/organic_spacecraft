"""The Kith: first contact, and the lexicon that opens them.

The claims, in the spec's order (`reviews/2026-09-17/innovations/02-kith.md`);
the gift economy's are in `test_kith_gift.py`:

- **First contact fires on entering the Cradle, once**, and a despatch
  records it; before it the Kith are hidden.
- **Gatherings are laid in from their own seeds**, never on the entry, never
  claiming the ground, and the same whenever they are placed.
- **Each way of learning raises comprehension** — listening, the bench, an
  exchange, watching their stars — and switching it off stops it.
- **The gates refuse with reasons**, bracketed, and **the misread odds shown
  are the odds rolled**.
- **An old save with an open Cradle gets its gatherings on load**, the same
  ones, and **a chronicle with the Kith survives a fresh process**.
- **The gathering is the port screen**, and its buttons act.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ..core import save as save_mod
from ..data import kith as data
from ..data.factions import THE_POWERS
from ..sim import gates, kith, kith_acts, kith_world
from ..world.galaxy import verge
from . import kith_kit as kit
from .efficacy import Lever, verdict
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("first contact fires on entering the Cradle, once")
    def _():
        from ..sim import comms
        game = kit.opened("kith-contact")
        assert not kith.met(game) and "kith" not in THE_POWERS
        day = game.day
        assert gates.use(game, kit.entry(game))["ok"]
        state = game.kith
        assert kith.met(game) and state.met_day == day
        assert state.met_at == kit.entry(game)
        sightings = [s for s in comms.inbox(game) if s.frm == "kith:sighting"]
        assert len(sightings) == 1, sightings
        anchor = game.galaxy.regions[0].anchor_id
        gates.use(game, anchor)
        gates.use(game, kit.entry(game))
        kit.put(game, kith_world.gatherings(game.galaxy)[0].id)
        again = [s for s in comms.inbox(game) if s.frm == "kith:sighting"]
        lines = [t for _d, t, _k in game.log if "Kith colony" in t]
        assert len(again) == 1 and len(lines) == 1 and state.met_day == day
        return f"met on day {day} at {game.galaxy.systems[state.met_at].name}; " \
               "back through twice, still one sighting"

    @check("gatherings are laid in from their own seeds, off the entry")
    def _():
        game, other = kit.opened("kith-place"), kit.opened("kith-place")
        places = kith_world.gatherings(game.galaxy)
        assert data.GATHERINGS_MIN <= len(places) <= data.GATHERINGS_MAX
        assert kit.entry(game) not in {s.id for s in places}
        for system in places:
            assert system.faction is None and system.port.faction == "kith"
            assert system.market.gift_economy and not system.market.stock
        # Placed again (the clock, a load): nothing changes.
        assert kith_world.ensure(game) == []
        seen = [(s.id, s.port.name) for s in kith_world.gatherings(other.galaxy)]
        assert seen == [(s.id, s.port.name) for s in places]
        grafts = {kith_world.graft_of(game.galaxy, s).part for s in places}
        assert grafts == {g.part for g in data.GRAFTS}, grafts
        return (f"{len(places)} gatherings: "
                + ", ".join(s.port.name for s in places)
                + "; all three grafts grown somewhere")

    @check("listening teaches up to its cap, and its preview is the act")
    def _():
        game = kit.at_gathering("kith-listen")
        said = kith.listen_preview(game, 10)
        before = kith.domains(game)
        out = kith.listen(game, 10)
        assert out["ok"] and out["days"] == 10
        for d in data.DOMAINS:
            assert abs(out["gain"][d] - said["gain"][d]) < 1e-9, (d, out, said)
        assert kith.domain(game, "kin") > before["kin"] + 0.02
        assert abs(game.kith.recordings - 10 / data.DAYS_PER_RECORDING) < 1e-9
        kith.listen(game, 600)
        top = max(game.kith.lexicon.values())
        assert data.LISTEN_CAP == 0.55 and 0.54 < top <= 0.55 + 1e-9, top

        def probe():
            fresh = kit.at_gathering("kith-listen")
            kith.listen(fresh, 20)
            return kith.domain(fresh, "kin")
        ok, why = verdict(Lever("listen", "a day at the gathering teaches",
                                (kith, "_hear", lambda *a: None), probe,
                                "lower"))
        assert ok, why
        return (f"10 days: Kin +{out['gain']['kin']:.3f} as quoted; capped at "
                f"{top:.3f} after 610; {why.split(';')[0]}")

    @check("the bench teaches the phrase it solved, and nothing else")
    def _():
        game = kit.at_gathering("kith-bench")
        game.kith.recordings = 2.0
        glyphs = kith.bench_glyphs("kith:offer")
        assert len(glyphs) == 6 and glyphs[:4] == [
            data.SIGNS_BY_ID[s].glyph for s in data.PHRASES_BY_ID["offer"].signs]
        assert kith.begin_decode(game, "offer")["ok"]
        assert game.kith.recordings == 1.0
        res = kit.solve(game)
        assert res["won"] and res["back"] == "port", res
        share = res["points"] / data.DECODE_SCALE
        phrase = data.PHRASES_BY_ID["offer"].signs
        for sign in data.SIGNS:
            have = kith.comprehension(game, sign.id)
            assert abs(have - (share if sign.id in phrase else 0.0)) < 1e-9
        kith.begin_decode(game, "greeting")
        lost = kit.solve(game, lose=True)
        assert not lost["won"] and kith.comprehension(game, "peace") == 0.0
        assert not kith.begin_decode(game, "greeting")["ok"]    # none left

        def probe():
            fresh = kit.at_gathering("kith-bench")
            fresh.kith.recordings = 1.0
            kith.begin_decode(fresh, "stars")
            kit.solve(fresh)
            return kith.domain(fresh, "place")
        ok, why = verdict(Lever("bench", "a solved song teaches its signs",
                                (kith, "teach", lambda *a, **k: 0.0), probe,
                                "lower"))
        assert ok, why
        return (f"{res['points']} points taught each of 4 signs "
                f"{share:.3f}; a lost bench taught nothing; recordings spent")

    @check("an exchange teaches its words, and their stars teach Place")
    def _():
        from ..sim import survey
        game = kit.at_gathering("kith-words")
        kit.fluent(game, 0.5, ("exchange",))
        cid = kit.good_taken_as(game, ("prized", "welcome", "plain"))
        game.ship.cargo[cid] = 10
        before = {s: kith.comprehension(game, s) for s in data.SIGNS_BY_ID}
        got = kith_acts.offer(game, cid, 10)
        spoken = set(data.SPOKEN[got["reaction"]])
        risen = {s for s in data.SIGNS_BY_ID
                 if kith.comprehension(game, s) > before[s] + 1e-9}
        assert risen == spoken, (risen, spoken)
        game.ship_stats.scan = max(game.ship_stats.scan, 0.6)

        def look():
            fresh = kit.at_gathering("kith-words")
            body = min(range(len(fresh.system.bodies)),
                       key=lambda i: fresh.system.bodies[i].radius_km)
            fresh.ship_stats.scan = 0.8
            survey.perform(fresh, body, "pass")
            return kith.domain(fresh, "place")
        ok, why = verdict(Lever("stars", "a look at their star teaches Place",
                                (kith, "observe", lambda g, r: 0.0), look,
                                "lower"))
        assert ok, why
        return (f"{cid} taken as {got['reaction']} taught "
                f"{sorted(spoken)}; {why.split(';')[0]}")

    @check("the gates refuse with reasons, and flip exactly at the bar")
    def _():
        assert (data.TRADE_NEEDS, data.PASSAGE_NEEDS, data.ACCORD_NEEDS,
                data.ACCORD_STANDING, data.TOLERATED) == (0.4, 0.5, 0.7, 40, 15)
        game = kit.at_gathering("kith-gates")
        kit.fluent(game, 0.39, ("exchange",))
        ok, why = kith.can(game, "gift")
        assert not ok and "0.4" in why and "Listen" in why, why
        kit.fluent(game, 0.40, ("exchange",))
        assert kith.can(game, "gift")[0]
        kit.fluent(game, 0.49, ("place",))
        kit.fluent(game, 0.6, ("intent",))
        ok, why = kith.can(game, "passage")
        assert not ok and "Place 0.49" in why, why
        kit.fluent(game, 0.50, ("place",))
        assert kith.can(game, "passage")[0]
        game.rep["kith"] = 14
        assert "tolerate" in kith.can(game, "berth")[1]
        game.rep["kith"] = 15
        assert kith.can(game, "berth")[0]
        kit.fluent(game, 0.69)
        game.rep["kith"] = 40
        assert "0.7" in kith.can(game, "accord")[1]
        kit.fluent(game, 0.70)
        game.rep["kith"] = 39
        assert "standing 40" in kith.can(game, "accord")[1]
        game.rep["kith"] = 40
        assert kith.can(game, "accord")[0]
        kit.put(game, kit.entry(game))
        assert "no Kith gathering" in kith.can(game, "gift")[1]
        return "gift 0.39/0.40, passage 0.49/0.50, berth 14/15, accord " \
               "0.69/0.70 and 39/40 — each refusal names its bar"

    @check("the misread odds shown are the odds rolled")
    def _():
        game = kit.at_gathering("kith-odds")
        kit.fluent(game, 0.4, ("exchange",))
        # 0.8 × 0.6² on a grown hull (0.85): the stated formula, bracketed.
        odds = kith.misread_odds(game, "gift")
        assert odds == round(0.8 * 0.36 * 0.85, 4), odds
        cid = kit.good_taken_as(game, ("prized", "welcome", "plain"))
        game.ship.cargo[cid] = 5
        said = kith_acts.preview_gift(game, cid, 5)
        seen = []
        real = kith.roll
        kith.roll = lambda g, p: (seen.append(p), real(g, p))[1]
        try:
            kith_acts.offer(game, cid, 5)
        finally:
            kith.roll = real
        assert seen[0] == said["misread"] == odds, (seen, said["misread"])
        trials = 4000
        hits = sum(kith.roll(game, odds) for _ in range(trials))
        rate = hits / trials
        sigma = (odds * (1 - odds) / trials) ** 0.5
        assert abs(rate - odds) < 3.5 * sigma, (rate, odds)
        kit.fluent(game, 1.0)
        assert kith.misread_odds(game, "accord") == 0.0
        return (f"stated {odds:.2%}, the act rolled on {seen[0]:.2%}, and "
                f"{trials} rolls came up {rate:.2%} (±{sigma:.2%})")

    @check("the rate is the officer, the array and the throat; idle is a quarter")
    def _():
        assert (data.LISTEN_RATE, data.SCIENCE_WORTH, data.SENSOR_REF,
                data.THROAT_LISTEN, data.THROAT_MISREAD,
                data.PASSIVE_SHARE) == (0.012, 0.25, 3.0, 1.5, 0.6, 0.25)
        game = kit.at_gathering("kith-rate")
        for officer in game.officers:
            officer.level = 2 if officer.stat == "science" else officer.level
        game.ship_stats.sensor = 3.0
        assert abs(kith.listen_rate(game) - 0.018) < 1e-12
        game.ship_stats.sensor = 9.0                 # the array's cap, 1.6
        assert abs(kith.listen_rate(game) - 0.0288) < 1e-12
        game.ship.fitted.append("light_throat")
        game.ship_stats.sensor = 3.0
        assert abs(kith.listen_rate(game) - 0.027) < 1e-12
        kit.fluent(game, 0.4, ("exchange",))
        assert kith.misread_odds(game, "gift") == 0.1469    # × 0.6
        game.ship.fitted.remove("light_throat")
        game.recompute()                            # the array as fitted
        start = dict(game.kith.lexicon)
        game.advance_days(1)                        # there, not attending
        idle = kith.comprehension(game, "self") - start.get("self", 0.0)
        game.kith.lexicon = dict(start)
        game.kith.session = [game.location_id, 1, kith.listen_rate(game)]
        game.advance_days(1)
        heard = kith.comprehension(game, "self") - start.get("self", 0.0)
        assert abs(idle / heard - 0.25) < 1e-6, (idle, heard)
        return (f"0.018 a day at science 2 and a stock array, 0.027 with a "
                f"throat (odds 0.1469); an idle day {idle / heard:.2f} of one "
                "attended")

    @check("an old save's open Cradle gets its gatherings on load, the same")
    def _():
        from ..core.state import load_game
        game = kit.opened("kith-old")
        want = [(s.id, s.port.name) for s in kith_world.gatherings(game.galaxy)]
        raw = save_mod.encode({"game": game})
        body = raw["game"]
        body.pop("kith", None)
        for system in body["galaxy"]["systems"]:
            if system.get("region") == "cradle":
                system["port"], system["market"] = None, None
            stock = (system.get("market") or {}).get("stock") or {}
            stock.pop("songglass", None)
        path = Path(tempfile.mkdtemp(prefix="seedfall-kith-")) / "old.json"
        path.write_text(json.dumps({"version": save_mod.SAVE_VERSION,
                                    "state": raw}))
        old = load_game(path)
        assert old is not None and old.kith is None
        got = [(s.id, s.port.name) for s in kith_world.gatherings(old.galaxy)]
        assert got == want, (got, want)
        assert any(s.market and "songglass" in s.market.stock
                   for s in verge(old.galaxy))
        return f"{len(got)} gatherings back on load, as grown: {got[0][1]}…"

    @check("a chronicle with the Kith survives a fresh process")
    def _():
        game = kit.at_gathering("kith-save")
        kit.fluent(game, 0.8)
        cid = kit.good_taken_as(game, ("prized", "welcome"))
        game.ship.cargo[cid] = 10
        kith_acts.offer(game, cid, 10)
        path = Path(tempfile.mkdtemp(prefix="seedfall-kith-")) / "s.json"
        assert save_mod.write({"game": game}, path)
        code = ("import json\nfrom seedfall.core.state import load_game\n"
                "from seedfall.sim import kith\n"
                f"g = load_game({str(path)!r})\n"
                "print(json.dumps({'p': kith.progress(g), "
                "'debts': g.kith.debts, 'prefs': g.kith.known_prefs, "
                "'charted': g.kith.charted}))\n")
        env = dict(os.environ, SEEDFALL_SAVE=str(path),
                   QT_QPA_PLATFORM="offscreen")
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                              text=True, env=env, timeout=300,
                              cwd=str(Path(__file__).resolve().parents[2]))
        lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("{")]
        assert lines, proc.stderr[-600:]
        got = json.loads(lines[-1])
        want = json.loads(json.dumps({
            "p": kith.progress(game), "debts": game.kith.debts,
            "prefs": game.kith.known_prefs, "charted": game.kith.charted}))
        assert got == want, (got, want)
        return (f"{got['p']['exchanges']} exchange, "
                f"{len(got['debts'])} debt and the lexicon read back")

    @check("the gathering is the port screen there, and its buttons act")
    def _():
        from PyQt6.QtWidgets import QPushButton
        from .qtkit import main_window
        game = kit.at_gathering("kith-screen")
        kit.fluent(game, 0.6)
        game.ship.cargo["ore"] = 30
        from ..ui import kith_codex
        assert not kith_codex.shown(kit.opened("kith-screen"))
        win = main_window(game)
        try:
            win.go("port")
            view = win.views["port"]
            pressed = []
            for text in ("Ask first", "Offer", "Listen 10 days"):
                btn = next(b for b in view.findChildren(QPushButton)
                           if b.text() == text and b.isEnabled())
                btn.click()
                pressed.append(text)
                view = win.views["port"]
            assert game.kith.exchanges >= 1 and game.kith.recordings >= 2.5
            win.go("codex")
            tabs = [b.text() for b in win.views["codex"].findChildren(
                QPushButton)]
            assert "The Kith" in tabs, tabs
        finally:
            win.close()
        return "pressed " + ", ".join(pressed) + "; the Codex has its tab"
