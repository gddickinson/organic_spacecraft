"""The living hull: a grown body remembers, and becomes something.

A grown hull changed after launch only by refit, exactly like a welded one.
`sim/adaptation.py` records the load each act puts on the body, lets an
adaptation emerge at a threshold, and folds the ones that set in into
`ship.stats()`. The claims, each driven through the act rather than the
recorder wherever an act exists:

- **Every channel fills from its real act** — a hit, a hot arrival, a jump,
  a season under a dim or a glaring star, a working, a survey, a dive, a
  hard crossing.
- **A threshold makes an emergence**; left alone it sets in on the sixtieth
  day, fed it sets in on the day the quote named and costs what it said.
- **Every adaptation moves its stats**, measured switched off.
- **Welded bodies never adapt**, and a budget caps what a grown one keeps.
- **Pruning is what its quote says**, and only where a surgeon is.
- **It survives a restart**, and old saves load.
- **Research, refit and adaptation stack inside every hard range.**
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ..data.adaptations import ADAPTATIONS, AUTO_SET_DAYS, CHANNELS, RATE
from ..data.chassis import CHASSIS
from ..data.parts import PARTS
from ..data.tech import TECH_BY_ID
from ..sim import actions, flight, stores
from ..sim import adaptation as adapt_sim
from ..sim import survey as survey_sim
from ..sim.ship import stats
from . import adaptation_kit as kit
from .efficacy import Lever, measure
from .harness import Suite

ROOT = Path(__file__).resolve().parents[2]


def _set_in(game, ids) -> None:
    game.ship.adaptations = list(ids)
    game.recompute()


def run(suite: Suite) -> None:
    check = suite.check

    @check("every channel fills from its own act, driven through the act")
    def _():
        got = {}
        game = kit.fresh("adapt-acts")
        lost = kit.fight(game, "acts")
        assert lost > 0, "the fight never landed a hit — no act to record"
        got["impact"] = game.ship.stress.get("impact", 0.0)

        game = kit.fresh("adapt-heat")
        flight.stand_off(game)
        for leg in range(6):
            game.ship.cargo["volatiles"] = 9999
            flight.travel_to(game, leg % len(game.system.bodies), "hard")
        got["heat"] = game.ship.stress.get("heat", 0.0)

        game = kit.fresh("adapt-jump")
        game.ship.cargo["volatiles"] = 900
        reach = [s for s in game.galaxy.systems if s.id != game.location_id
                 and actions.jump_quote(game, s)["in_range"]]
        steady = actions.jump_quote(game, reach[0])
        assert actions.jump_to(game, reach[0].id)["ok"]
        assert abs(game.ship.stress["crossing"] - steady["ly"]) < 1e-9
        assert game.ship.stress.get("burn", 0.0) == 0.0, "a steady transit burned"
        back = next(s for s in game.galaxy.systems if s.id != game.location_id
                    and actions.jump_quote(game, s, "hard")["in_range"])
        assert actions.jump_to(game, back.id, "hard")["ok"]
        got["crossing"] = game.ship.stress["crossing"]
        got["burn"] = game.ship.stress["burn"]
        assert got["burn"] == 1.0, got

        for channel, dark in (("dark", True), ("glare", False)):
            game = kit.fresh(f"adapt-{channel}")
            assert kit.under_star(game, dark), f"no {channel} star in the sector"
            game.advance_days(10)
            got[channel] = game.ship.stress.get(channel, 0.0)
            assert got[channel] == 10.0, (channel, got[channel])
        # Bracketed on the star classes either side of each line: a white
        # dwarf (0.18) is dark and a red dwarf (0.32) is not; an A-type
        # (1.00) glares and an F-type (0.86) does not.
        assert (adapt_sim.DARK_BELOW, adapt_sim.GLARE_FROM) == (0.25, 0.9)
        for heat, want in ((0.18, "dark"), (0.32, ""), (0.86, ""),
                           (1.00, "glare")):
            game.system.heat = heat
            assert adapt_sim.sky(game, 1) == want, (heat, want)

        game = kit.fresh("adapt-gut")
        for index in range(len(game.system.bodies)):
            res = actions.extract(game, index, 20, "cut")
            if res.get("ok") and res["got"]:
                assert abs(game.ship.stress["gut"] - sum(res["got"].values())) < 1e-6
                break
        got["gut"] = game.ship.stress.get("gut", 0.0)

        game = kit.fresh("adapt-eyes")
        game.ship.cargo["volatiles"] = 400
        fresh_look = survey_sim.perform(game, 0, "pass")
        assert fresh_look["ok"] and fresh_look["research"] > 0
        first = game.ship.stress["eyes"]
        survey_sim.perform(game, 0, "pass")
        # The same look twice teaches the eyes nothing.
        assert game.ship.stress["eyes"] == first == 1.0, game.ship.stress
        got["eyes"] = first

        game = kit.fresh("adapt-depth")
        index = kit.over_ocean(game)
        assert index is not None, "no subsurface ocean in the sector"
        assert actions.dive(game, index)["ok"]
        got["depth"] = game.ship.stress["depth"]

        empty = [c for c in CHANNELS if not got.get(c)]
        assert not empty, f"channels the act did not fill: {empty}"
        return ", ".join(f"{c} {v:,.0f}" for c, v in got.items())

    @check("a threshold crossed makes an emergence, and says so")
    def _():
        game = kit.fresh("adapt-emerge")
        waiting = kit.emerging(game, "long_haul_metabolism")
        assert waiting and waiting["id"] == "long_haul_metabolism", waiting
        assert waiting["due"] == waiting["since_day"] + AUTO_SET_DAYS
        told = [t for _d, t, _k in game.log if "Something is growing" in t]
        assert told, "the emergence happened in silence"
        below = kit.fresh("adapt-below")
        below.ship.stress["crossing"] = 129.0
        kit.under_plain_star(below)
        below.advance_days(3)
        assert below.ship.emerging is None, "emerged under its threshold"
        assert adapt_sim.ADAPTATIONS_BY_ID["long_haul_metabolism"].threshold == 130
        # And a channel stops filling a quarter past its top threshold.
        assert adapt_sim.STRESS_CAP == 1.25
        adapt_sim.record(below.ship, "crossing", 1e6)
        assert below.ship.stress["crossing"] == 600.0, below.ship.stress
        return f"at 130 ly: {told[-1][:60]}…; at 129: nothing; capped at 600"

    @check("left alone it sets in on the sixtieth day, not the fifty-ninth")
    def _():
        game = kit.fresh("adapt-auto")
        waiting = kit.emerging(game, "acute_opsins")
        assert AUTO_SET_DAYS == 60 and waiting["due"] - game.ship_day == 60
        game.advance_days(59)
        assert game.ship.emerging is not None and not game.ship.adaptations
        scan = game.ship_stats.scan
        game.advance_days(1)
        assert game.ship.adaptations == ["acute_opsins"], game.ship.adaptations
        assert game.ship.emerging is None
        assert abs(game.ship_stats.scan - (scan + 0.05)) < 1e-9, (
            "set in, but the stats the game reads were not recomputed")
        return f"set in on ship day {game.ship_day}, {AUTO_SET_DAYS} after"

    @check("encourage costs exactly what its quote said, and sets in on the day")
    def _():
        game = kit.fresh("adapt-feed")
        kit.stocked(game)
        kit.emerging(game, "mineral_gut")
        quote = adapt_sim.encourage_quote(game)
        assert quote["ok"], quote["why"]
        # A NAVIS is the body the bill is written for.
        assert quote["cost"] == {"phosphate": 4.0, "biomass": 12.0}, quote
        assert quote["days"] == 20, quote
        have = {k: stores.held(game, k) for k in quote["cost"]}
        res = adapt_sim.encourage(game)
        assert res["ok"] and res["cost"] == quote["cost"]
        for key, n in quote["cost"].items():
            assert abs(have[key] - stores.held(game, key) - n) < 1e-9, key
        assert not adapt_sim.encourage(game)["ok"], "fed twice"
        game.advance_days(19)
        assert not game.ship.adaptations, "set in before the quoted day"
        game.advance_days(1)
        assert game.ship.adaptations == ["mineral_gut"]
        poor = kit.fresh("adapt-poor")
        poor.stores.clear()
        poor.ship.cargo.pop("phosphate", None)
        kit.emerging(poor, "mineral_gut")
        refused = adapt_sim.encourage(poor)
        assert not refused["ok"] and "phosphate" in refused["why"], refused
        return (f"{quote['cost']} taken, set in {quote['days']} days later; "
                f"refused with no phosphate")

    @check("suppress draws the channel down to what its quote said")
    def _():
        game = kit.fresh("adapt-starve")
        kit.emerging(game, "long_haul_metabolism")
        quote = adapt_sim.suppress_quote(game.ship)
        res = adapt_sim.suppress(game)
        assert res["ok"] and res["left"] == quote["left"]
        # A full threshold below nothing: 260 ly before it is offered again.
        assert game.ship.stress["crossing"] == quote["left"] == -130.0
        assert game.ship.emerging is None
        game.advance_days(AUTO_SET_DAYS + 5)
        assert not game.ship.adaptations and game.ship.emerging is None
        return f"crossing starved to {quote['left']:.0f}; nothing came back"

    @check("every adaptation moves the stats it claims, switched off")
    def _():
        moved = 0
        for grown in ADAPTATIONS:
            # The opening NAVIS: every adaptation can grow in a grown hull,
            # and it carries a mining root for the gut's rates to multiply.
            game = kit.fresh(f"adapt-fx-{grown.id}")
            _set_in(game, [grown.id])
            for effect in grown.gives + grown.takes:
                def probe(stat=effect.stat, game=game):
                    return getattr(stats(game.ship, game.bonuses), stat)
                lever = Lever(grown.id, effect.stat,
                              patch=(adapt_sim, "fx", lambda _ship: {}),
                              probe=probe)
                live, dead = measure(lever)
                sign = 1 if effect.amount > 0 else -1
                assert (live - dead) * sign > 0, (
                    f"{grown.id}: {effect.stat} {live} with it, {dead} without")
                moved += 1
            if grown.dose != 1.0:
                assert adapt_sim.dose_multiplier(game.ship) == grown.dose
        # Every row has a gain and a cost, so an empty table cannot pass.
        assert moved >= 2 * len(ADAPTATIONS) >= 32, moved
        return f"{moved} effects across {len(ADAPTATIONS)} adaptations"

    @check("no adaptation's gain is worth more than a tier-2 fitting's")
    def _():
        base = kit.fresh("adapt-worth")
        cheap = [p for p in PARTS if not p.tech or getattr(
            TECH_BY_ID.get(p.tech), "tier", 9) <= 2]
        worst = (0.0, "")
        for grown in ADAPTATIONS:
            for effect in grown.gives:
                before = getattr(base.ship_stats, effect.stat)
                _set_in(base, [grown.id])
                gain = getattr(base.ship_stats, effect.stat) - before
                _set_in(base, [])
                best = 0.0
                for part in cheap:
                    fitted = base.ship.fitted
                    base.ship.fitted = fitted + [part.id]
                    best = max(best, getattr(stats(base.ship, base.bonuses),
                                             effect.stat) - before)
                    base.ship.fitted = fitted
                assert best > 0, f"no tier-2 part moves {effect.stat}"
                assert gain <= best * 1.05, (
                    f"{grown.id} gives {effect.stat} +{gain:.3f}; the best "
                    f"tier-2 fitting gives +{best:.3f}")
                worst = max(worst, (gain / best, f"{grown.id} {effect.stat}"))
        assert worst[1], "no adaptation's gain was compared with anything"
        return f"the nearest is {worst[1]} at {worst[0]:.0%} of a fitting"

    @check("fabricated and synthetic hulls never record, emerge or set in")
    def _():
        welded = [c for c in CHASSIS if c.family not in RATE]
        assert len(welded) >= 17, f"only {len(welded)} welded hulls to try"
        for chassis in welded:
            game = kit.fresh("adapt-welded", chassis.id)
            for channel in CHANNELS:
                adapt_sim.record(game.ship, channel, 1e6)
            assert kit.under_star(game, dark=True)
            game.advance_days(90)
            assert not game.ship.stress and game.ship.emerging is None
            assert adapt_sim.budget(game.ship) == 0
        return f"{len(welded)} welded hulls, 90 days each: nothing"

    @check("the budget caps the count, by the size of the body")
    def _():
        rooms = {}
        for chassis in ("spore", "navis", "testudo", "leviathan", "graft",
                        "threshold", "revenant"):
            game = kit.fresh(f"adapt-budget-{chassis}", chassis)
            for channel in CHANNELS:
                game.ship.stress[channel] = adapt_sim.CEILING[channel]
            kit.under_plain_star(game)
            game.advance_days(AUTO_SET_DAYS * 7)
            rooms[chassis] = len(game.ship.adaptations)
            assert rooms[chassis] == adapt_sim.budget(game.ship), rooms
            assert game.ship.emerging is None
        assert rooms == {"spore": 1, "navis": 3, "testudo": 4, "leviathan": 5,
                         "graft": 1, "threshold": 3, "revenant": 3}, rooms
        return ", ".join(f"{k} {v}" for k, v in rooms.items())

    @check("hybrids record at half rate; xeno at 1.5x, drawing at random")
    def _():
        for chassis, rate in (("navis", 1.0), ("graft", 0.5),
                              ("revenant", 1.5)):
            game = kit.fresh("adapt-rate", chassis)
            assert adapt_sim.record(game.ship, "crossing", 10.0) == 10 * rate
        drawn = set()
        for seed in range(8):
            game = kit.fresh(f"adapt-xeno-{seed}", "revenant")
            kit.emerging(game, "motile_trim")
            grew = game.ship.emerging["id"]
            drawn.add(grew)
            # Something else grew, so the burn that triggered it is spent —
            # or it would trigger again the day after this one sets in.
            assert grew == "motile_trim" or game.ship.stress["burn"] < 0, (
                grew, game.ship.stress)
        assert len(drawn) > 1, f"eight xeno bodies all grew {drawn}"
        return f"xeno drew {len(drawn)} different adaptations from one trigger"

    @check("pruning costs what its quote says, and only at a Fleet Hub")
    def _():
        game = kit.fresh("adapt-prune")
        _set_in(game, ["callused_rind"])
        assert kit.away_from_hubs(game)
        assert not adapt_sim.prune_quote(game, "callused_rind")["ok"]
        assert kit.at_hub(game), "no gestation bay anywhere in the sector"
        game.officers = []                  # no payroll muddying the purse
        quote = adapt_sim.prune_quote(game, "callused_rind")
        assert quote["ok"], quote["why"]
        assert (quote["credits"], quote["days"]) == (3000, 8), quote
        armour = game.ship_stats.armour
        credits, day = game.credits, game.day
        res = adapt_sim.prune(game, "callused_rind")
        assert res["ok"] and res["credits"] == quote["credits"]
        assert game.credits == credits - quote["credits"], (
            credits - game.credits, quote)
        assert game.day == day + quote["days"]
        assert game.ship.adaptations == [] and game.ship_stats.armour < armour
        return f"{quote['credits']:,} credits and {quote['days']} days, as quoted"

    @check("research, refit and adaptation stack inside every hard range")
    def _():
        from ..data.tech import TECH
        game = kit.fresh("adapt-stack")
        game.research.unlocked = [t.id for t in TECH]
        game.ship.fitted += ["sail_film", "vesper_organ", "interferometer",
                             "dsup_chromatin", "regrowth_surge"]
        _set_in(game, [a.id for a in ADAPTATIONS])
        st = game.ship_stats
        for stat, (low, high) in adapt_sim.BOUNDS.items():
            value = getattr(st, stat)
            assert low is None or value >= low - 1e-9, (stat, value)
            assert high is None or value <= high + 1e-9, (stat, value)
        # And at the edge: a hull already at the top of a range stays there.
        st.scan, st.evade, st.crew_guard = 0.99, 0.7, 0.84
        adapt_sim.apply(st, game.ship)
        assert st.scan <= 1.0 and st.evade <= 0.7 and st.crew_guard <= 0.85
        return (f"all {len(ADAPTATIONS)} at once, every tech: scan "
                f"{game.ship_stats.scan:.2f}, evade {game.ship_stats.evade:.2f}")

    @check("it survives a restart, and a save from before it loads")
    def _():
        tmp = Path(tempfile.mkdtemp(prefix="seedfall-adapt-"))
        env = dict(os.environ, SEEDFALL_SAVE=str(tmp / "save.json"),
                   QT_QPA_PLATFORM="offscreen")

        def py(code: str) -> dict:
            proc = subprocess.run([sys.executable, "-c", code], env=env,
                                  cwd=str(ROOT), capture_output=True,
                                  text=True, timeout=300)
            lines = [l for l in proc.stdout.splitlines() if l.startswith("{")]
            assert lines, proc.stderr[-600:]
            return json.loads(lines[-1])

        wrote = py(WRITE)
        read = py(READ)
        assert read == wrote, (wrote, read)
        from ..core import save as save_mod
        game = kit.fresh("adapt-old")
        old = json.loads(json.dumps(save_mod.encode({"game": game})))
        assert _strip(old) >= 1, "no ship in the save to strip"
        back = save_mod.decode(old)["game"]
        assert back.ship.stress == {} and back.ship.adaptations == []
        assert back.ship.emerging is None
        return f"{wrote['held']} and {wrote['stress']} came back in a new process"

    @check("the Body tab draws all three states, and its buttons work")
    def _():
        from .qtkit import main_window
        game = kit.fresh("adapt-ui")
        kit.stocked(game)
        kit.emerging(game, "acute_opsins")
        win = main_window(game)
        win.go("ship")
        view = win.views["ship"]
        view._switch("body")
        pressed = _press(view, "Encourage")
        assert pressed and game.ship.emerging["encouraged"]
        game.ship.adaptations = ["long_haul_metabolism"]
        game.ship.emerging = None
        kit.emerging(game, "melanised_rind")
        view.refresh()
        assert _press(view, "Suppress") and game.ship.emerging is None
        assert kit.at_hub(game)
        view.refresh()
        assert _press(view, "Prune") and not game.ship.adaptations
        welded = kit.fresh("adapt-ui-welded", "halyard")
        win2 = main_window(welded)
        win2.go("ship")
        win2.views["ship"]._switch("body")
        text = " ".join(_texts(win2.views["ship"]))
        win.close()
        win2.close()
        assert "never adapt" in text, text[:200]
        return "encouraged, suppressed and pruned by the buttons; welded says so"


def _press(view, text: str) -> bool:
    from PyQt6.QtWidgets import QPushButton
    for b in view.widget().findChildren(QPushButton):
        if b.text() == text and b.isEnabled():
            b.click()
            return True
    return False


def _texts(view) -> list:
    from PyQt6.QtWidgets import QLabel
    return [lb.text() for lb in view.widget().findChildren(QLabel)]


def _strip(node) -> int:
    """Take the living hull out of every saved Ship, as a save written before
    it existed would read. Returns how many ships it stripped."""
    count = 0
    if isinstance(node, dict):
        if node.get("__t__") == "Ship":
            for key in ("stress", "adaptations", "emerging"):
                node.pop(key)
            count += 1
        for value in node.values():
            count += _strip(value)
    elif isinstance(node, list):
        for value in node:
            count += _strip(value)
    return count


WRITE = """
import json
from seedfall.core.state import new_game
g = new_game("adapt-persist")
g.ship.stress = {"crossing": 97.5, "dark": -40.0}
g.ship.adaptations = ["callused_rind", "long_haul_metabolism"]
g.ship.emerging = {"id": "acute_opsins", "trigger": "acute_opsins",
                   "since_day": 3, "due": 63, "encouraged": True}
g.recompute()
g.save()
print(json.dumps({"held": g.ship.adaptations, "stress": g.ship.stress,
                  "emerging": g.ship.emerging, "jump": g.ship_stats.jump,
                  "armour": g.ship_stats.armour}))
"""

READ = """
import json
from seedfall.core.state import load_game
g = load_game()
print(json.dumps({"held": g.ship.adaptations, "stress": g.ship.stress,
                  "emerging": g.ship.emerging, "jump": g.ship_stats.jump,
                  "armour": g.ship_stats.armour}))
"""
