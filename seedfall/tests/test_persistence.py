"""A chronicle survives the one thing every other check skipped: a restart.

Every save/load check before 2026-09 loaded its save in the process that
wrote it — where the type registry was already full, the id counters were
already past every id in the save, and an attribute set at runtime was
still sitting on the object. None of that is true of a player who quits and
comes back, and all three broke the game for them while the suite stayed
green: Resume failed for every save, ids collided (the flagship could
vanish), and hunger debt, envoy quiet periods and tutorial progress were
silently dropped.

So these checks cross a process boundary for real, feed the reader damaged
and older files, and hold the clock to "a step with no day in it is not a
day".
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .harness import Suite

ROOT = Path(__file__).resolve().parents[2]


def _py(code: str, save: Path) -> dict:
    """Run `code` in a fresh interpreter against `save`; its last stdout
    line is JSON. A fresh process is the whole point: nothing imported here
    can leak into what that one knows."""
    env = dict(os.environ, SEEDFALL_SAVE=str(save), QT_QPA_PLATFORM="offscreen")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, env=env, cwd=str(ROOT), timeout=300)
    lines = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
    assert lines, f"no result (exit {proc.returncode}): {proc.stderr[-600:]}"
    return json.loads(lines[-1])


WRITE = """
import json
from seedfall.core.state import new_game
from seedfall.sim import shipyard
g = new_game("persist-a")
g.advance_days(40)
g.credits = 900000
for k in ("ore", "volatiles", "phosphate", "biomass", "silicon", "alloy"):
    g.stores[k] = 9000
sid = next(s.id for s in g.galaxy.systems if s.port and "shipyard" in s.port.services)
g.location_id = sid
g.short_days = 12.5
g.conn_seconds = 77.0
print(json.dumps({"ok": g.save(), "fleet": [s.uid for s in g.fleet],
                  "ship": g.ship.uid, "day": g.day, "rng": g.rng_seed}))
"""

RESUME = """
import json
{extra}
from seedfall.core.state import load_game, load_problem
from seedfall.sim.ship import make_ship
g = load_game()
if g is None:
    print(json.dumps({{"ok": False, "why": load_problem()}}))
else:
    fresh = make_ship("spore", [], "Newcomer")
    print(json.dumps({{"ok": True, "day": g.day, "fleet": [s.uid for s in g.fleet],
                      "ship": g.ship.uid, "fresh": fresh.uid, "rng": g.rng_seed,
                      "short": g.short_days, "flown": g.conn_seconds,
                      "same": any(s is g.ship for s in g.fleet)}}))
"""


def run(suite: Suite) -> None:
    check = suite.check
    tmp = Path(tempfile.mkdtemp(prefix="seedfall-persist-"))
    save = tmp / "save.json"
    wrote = _py(WRITE, save)

    @check("a save resumes in a fresh process that imports only the game")
    def _():
        assert wrote["ok"], wrote
        got = _py(RESUME.format(extra="import seedfall.core.state"), save)
        assert got["ok"], got["why"]
        assert got["day"] == wrote["day"] and got["rng"] == wrote["rng"], got
        return f"day {got['day']}, {len(got['fleet'])} hull(s), fresh process"

    @check("…and in one that imports what `python -m seedfall` imports")
    def _():
        try:
            import PyQt6  # noqa: F401
        except ImportError:
            return "PyQt6 absent — the plain import above stands in"
        got = _py(RESUME.format(extra="import seedfall.ui.app"), save)
        assert got["ok"], got["why"]
        return "resumed with the window's imports only"

    @check("an id issued after a restart is never one the save already holds")
    def _():
        got = _py(RESUME.format(extra=""), save)
        assert got["fresh"] not in got["fleet"], (
            f"new hull uid {got['fresh']} collides with {got['fleet']}")
        assert got["same"], "the flagship is not the object in the fleet"
        return f"fleet {got['fleet']} · next hull {got['fresh']}"

    @check("what used to be a runtime attribute survives the restart")
    def _():
        got = _py(RESUME.format(extra=""), save)
        assert got["short"] == 12.5 and got["flown"] == 77.0, got
        return "hunger debt 12.5 d and 77 s flown came back"

    @check("under test, an undeclared attribute fails the write instead of "
           "vanishing")
    def _():
        from ..core import save as save_mod
        from ..core.state import new_game
        g = new_game("persist-b")
        g.officers[0].mood_swing = 3            # not a field
        try:
            save_mod.encode({"game": g})
        except TypeError as err:
            assert "mood_swing" in str(err)
            return "refused: " + str(err)[:60]
        finally:
            del g.officers[0].mood_swing
        raise AssertionError("an undeclared attribute was written silently")

    @check("an unreadable save is moved aside and explained, never deleted")
    def _():
        from ..core import save as save_mod
        cases = {
            "truncated": save.read_text()[:5000],
            "a list": "[1, 2, 3]",
            "no state": json.dumps({"version": 2}),
            "a missing field": json.dumps({"version": 2, "state": {"game": {
                "__t__": "Game", "seed": "x"}}}),
        }
        moved = 0
        for name, text in cases.items():
            bad = tmp / f"{name.replace(' ', '_')}.json"
            bad.write_text(text)
            assert save_mod.read(bad) is None, name
            assert save_mod.last_error(), f"{name}: no reason given"
            assert not bad.exists(), f"{name}: left in place to be cleared"
            kept = list(tmp.glob(bad.stem + ".*.bad"))
            assert kept, f"{name}: not kept aside"
            moved += 1
        assert moved == len(cases) == 4, f"{moved} of {len(cases)} cases ran"
        return f"{len(cases)} kinds of damage, each kept as .bad with a reason"

    @check("a save from a newer build is refused but left where it is")
    def _():
        from ..core import save as save_mod
        newer = tmp / "newer.json"
        newer.write_text(json.dumps({"version": save_mod.SAVE_VERSION + 1,
                                     "state": {}}))
        assert save_mod.read(newer) is None
        assert newer.exists() and "newer" in save_mod.last_error()
        return save_mod.last_error()

    @check("a version-1 save still loads (the migration table is walked)")
    def _():
        from ..core import save as save_mod
        payload = json.loads(save.read_text())
        payload["version"] = 1
        payload["state"]["game"].pop("ids", None)
        old = tmp / "v1.json"
        old.write_text(json.dumps(payload))
        data = save_mod.read(old)
        assert data and data["game"].day == wrote["day"]
        return f"v1 → v{save_mod.SAVE_VERSION}, day {data['game'].day}"

    @check("a chronicle that decodes but cannot be played is refused on load")
    def _():
        from ..core import state as state_mod
        from ..core.state import new_game
        g = new_game("persist-c")
        g.fleet = [s for s in g.fleet if s is not g.ship]
        problems = state_mod.validate(g)
        assert any("flagship" in p or "empty" in p for p in problems), problems
        g2 = new_game("persist-d")
        g2.credits = float("nan")
        assert any("purse" in p for p in state_mod.validate(g2))
        return "; ".join(problems)

    @check("the previous save is kept as .bak when a new one is written")
    def _():
        from ..core import save as save_mod
        from ..core.state import new_game
        spot = tmp / "bak.json"
        g = new_game("persist-e")
        assert save_mod.write(g.to_save(), spot)
        g.advance_days(3)
        assert save_mod.write(g.to_save(), spot)
        back = spot.with_name(spot.name + ".bak")
        assert back.exists() and json.loads(back.read_text())
        return "one generation kept"

    @check("a step with no whole day in it is not a day: no tick, no luck spent")
    def _():
        from ..core.state import new_game
        g = new_game("persist-f")
        g.advance_days(2)
        day, seed, credits = g.day, g.rng_seed, g.credits
        for _ in range(2000):
            g.advance_days(0.0004)          # 0.8 d in all
        assert g.day == day and g.rng_seed == seed, (g.day, g.rng_seed)
        assert math.isclose(g.credits, credits), "a slice was billed as a day"
        g.advance_days(0.2)                 # crosses into the next day
        assert g.day == day + 1
        return "2,000 slices: calendar, luck and purse untouched until a day passed"

    @check("sub-day slices do not forgive a starving colony")
    def _():
        from ..core.state import new_game
        from ..data.colonies import COLONIES
        from ..sim import colony as colony_sim
        g = new_game("persist-g")
        g.credits, g.stores = 900000, {k: 9000 for k in g.stores}
        g.research.unlocked = sorted({*g.research.unlocked,
                                      *(c.tech for c in COLONIES if c.tech)})
        home = g.system
        col = None
        for c in COLONIES:
            for body in home.bodies:
                if colony_sim.can_found(g, home, body, c.id)[0]:
                    col, _why = colony_sim.found(g, home, body, c.id)
                    break
            if col is not None:
                break
        assert col is not None, "nothing foundable at home with every tech"
        col.starving = 30
        for _ in range(500):
            g.advance_days(0.001)
        assert col.starving == 30, f"forgiven: {col.starving}"
        return "30 days of hunger still owed after 500 slices"

    @check("a process with no screen never writes the player's own save")
    def _():
        # An offscreen probe once autosaved over ~/.seedfall/save.json.
        env = {k: v for k, v in os.environ.items() if k != "SEEDFALL_SAVE"}
        env["QT_QPA_PLATFORM"] = "offscreen"
        out = subprocess.run(
            [sys.executable, "-c",
             "from seedfall.core.save import save_path; print(save_path())"],
            capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=60)
        where = out.stdout.strip()
        assert where and ".seedfall" not in where, where
        return f"headless save goes to {Path(where).name}"

    @check("importing the tests never deletes a save its caller named")
    def _():
        # The tidy-up removed whatever SEEDFALL_SAVE named, and its .bak, at
        # exit — a play-test lost three run saves to it (2026-09-18).
        with tempfile.TemporaryDirectory() as tmp:
            keep = Path(tmp) / "mine.json"
            keep.write_text("{}")
            keep.with_name("mine.json.bak").write_text("{}")
            env = dict(os.environ, SEEDFALL_SAVE=str(keep))
            subprocess.run([sys.executable, "-c", "import seedfall.tests"],
                           env=env, cwd=str(ROOT), timeout=60, check=True)
            left = sorted(p.name for p in Path(tmp).iterdir())
        assert left == ["mine.json", "mine.json.bak"], left
        return "the caller's save and its .bak both survive"

    @check("a seed plays the same after another chronicle in this process")
    def _():
        # "Begin again" used to play a seed differently from a fresh launch:
        # the id counters were the process's, and ids reach the dice.
        import hashlib
        from ..core import save as save_mod
        from ..core.state import new_game

        def played(seed: str) -> str:
            g = new_game(seed)
            g.advance_days(120)
            blob = json.dumps(save_mod.encode({"game": g}), sort_keys=True)
            return hashlib.sha256(blob.encode()).hexdigest()[:16]

        first = played("persist-same")
        other = new_game("persist-other")
        other.advance_days(90)
        again = played("persist-same")
        assert first == again, f"{first} then {again}"
        return f"state hash {first} both times, with another chronicle between"
