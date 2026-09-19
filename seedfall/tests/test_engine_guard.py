"""The engine's own guard rails: one clock, honest memos, loud excepts.

Review 2026-09-17 (#32–#34). Each check pins something the engine now
refuses to do quietly:

- **The clock is not re-entrant.** A tick that advanced the clock would run
  half a day inside another; `clock.advance_days` raises instead, and a span
  that is not a finite, non-negative number is refused before it can hang the
  loop (`inf`) or wind the calendar back (a negative).
- **`exchequer.income` is memoised and cannot go stale**: its memo is keyed on
  every input it reads, so moving any of them is a recomputation.
- **No rules module imports `core.state` or `core.clock` at import time**, so
  the one-way `core → sim` edge `clock` needs stays one-way.
- **A broad `except` names what it is for**, and hands anything else to
  `core.guard.swallowed` — loud under test, one line in play.
- And two small truths: every name a `sim` module's `__all__` promises
  exists, and the crew gauge's morale is the ship's.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import math
import pkgutil
import subprocess
import sys

from ..core import clock
from ..core import guard
from ..core.state import new_game
from ..sim import exchequer as ex
from ..sim import industry as industry_sim
from ..sim import market as market_sim
from ..sim import memory as memory_sim
from ..sim import settlement as settle_sim
from ..sim import telemetry
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("a tick that advances the clock is refused, and the clock recovers")
    def _():
        game = new_game("reentry")
        real = memory_sim.tick

        def nested(g, days):
            real(g, days)
            g.advance_days(1)            # the thing no tick may do
        memory_sim.tick = nested
        try:
            try:
                game.advance_days(1)
            except clock.ClockReentered as err:
                said = str(err)
            else:
                raise AssertionError("a nested advance ran inside a day")
        finally:
            memory_sim.tick = real
        assert "still running" in said, said
        assert not clock._RUNNING, "the guard stayed shut after the raise"
        day = game.day
        game.advance_days(3)
        assert game.day == day + 3, "the clock did not recover"
        return f"refused with: {said[:60]}…"

    @check("a span that is not a finite, non-negative number is refused")
    def _():
        game = new_game("spans")
        day, credits = game.day, game.credits
        for bad in (float("nan"), float("inf"), -1, -0.5):
            try:
                game.advance_days(bad)
            except ValueError:
                continue
            raise AssertionError(f"advance_days({bad!r}) was taken")
        assert (game.day, game.credits) == (day, credits)
        game.advance_days(0)             # nothing, and allowed
        return "nan, inf and negative spans refused; the calendar untouched"

    @check("income's memo agrees with the sum through every kind of change")
    def _():
        game = new_game("purse-memo")
        game.advance_days(2)             # opens the books
        powers = list(ex.dip.POWERS)
        sums = [0]
        real = ex._income

        def counted(g, power):
            sums[0] += 1
            return real(g, power)

        seen: list = []

        def agree(when: str) -> None:
            seen.append(when)
            for power in powers:
                memo, fresh = ex.income(game, power), real(game, power)
                assert memo == fresh, f"{when}: {power} {memo} != {fresh}"

        ex._income = counted
        try:
            agree("start")
            before = sums[0]
            agree("again")
            assert sums[0] == before, "an unchanged day was summed again"
            held = ex.holdings(game, powers[0])
            system = held[0]
            ex.promote(game, system)
            agree("a port promoted")
            system.bloom = min(1.0, system.bloom + 0.3)
            agree("the Bloom grew")
            market_sim.all_shocks(game).append(market_sim.Shock(
                id=99_001, kind=next(iter(market_sim.SHOCKS_BY_ID)),
                system_id=system.id, commodity="ore", until=game.day + 30))
            agree("a shortage began")
            industry_sim.state(game).held.setdefault("probe", []).append(
                powers[0])
            agree("a licence sold")
            system.port.faction = powers[1]
            agree("a berth changed flag")
            sites = settle_sim.sites_for(game, powers[2])
            if sites:
                target, body, _good = sites[0]
                settle_sim.found(game, target, body, powers[2])
                agree("a settlement founded")
            game.advance_days(1)
            agree("a day later")
        finally:
            ex._income = real
        return (f"{len(seen) - 2} kinds of change, every one recomputed "
                f"({sums[0]} sums for {len(seen) * len(powers)} asks)")

    @check("no rules module reaches back into core.state or core.clock")
    def _():
        # One fresh interpreter, every `sim`, `world` and `data` module in
        # turn: the first one after which either is loaded is the offender.
        probe = (
            "import importlib, pkgutil, sys\n"
            "for pkg in ('seedfall.data', 'seedfall.world', 'seedfall.sim'):\n"
            "    base = importlib.import_module(pkg)\n"
            "    for info in pkgutil.iter_modules(base.__path__, pkg + '.'):\n"
            "        importlib.import_module(info.name)\n"
            "        hit = [m for m in ('seedfall.core.state',\n"
            "               'seedfall.core.clock') if m in sys.modules]\n"
            "        if hit:\n"
            "            print(info.name, hit[0]); sys.exit(1)\n"
            "print('clean')\n")
        out = subprocess.run([sys.executable, "-c", probe],
                             capture_output=True, text=True, timeout=300)
        assert out.returncode == 0 and "clean" in out.stdout, (
            f"{out.stdout.strip()} {out.stderr.strip()[-300:]}")
        count = sum(1 for pkg in ("data", "world", "sim")
                    for _ in pkgutil.iter_modules(
                        importlib.import_module(f"seedfall.{pkg}").__path__))
        return f"{count} modules imported; neither core.state nor core.clock"

    @check("a swallowed exception is loud under test and one line in play")
    def _():
        try:
            try:
                raise KeyError("probe")
            except KeyError as err:
                guard.swallowed("engine-guard probe", err)
        except KeyError:
            pass
        else:
            raise AssertionError("swallowed under test")
        tests = sys.modules.pop("seedfall.tests")
        heard = io.StringIO()
        try:
            with contextlib.redirect_stderr(heard):
                for _ in range(3):
                    guard.swallowed("engine-guard play", ValueError("x"))
        finally:
            sys.modules["seedfall.tests"] = tests
            guard._SEEN.discard("engine-guard play")
        lines = heard.getvalue().strip().splitlines()
        assert len(lines) == 1 and "engine-guard play" in lines[0], lines
        return "re-raised under test; three hits in play said once"

    @check("every name a sim module's __all__ promises is there")
    def _():
        missing = []
        import seedfall.sim as sim_pkg
        for info in pkgutil.iter_modules(sim_pkg.__path__, "seedfall.sim."):
            module = importlib.import_module(info.name)
            for name in getattr(module, "__all__", ()):
                if not hasattr(module, name):
                    missing.append(f"{info.name}.{name}")
        assert not missing, f"promised and absent: {missing}"
        return "no phantom names (xeno's `known` was one)"

    @check("the crew gauge reads the ship's morale, not a constant")
    def _():
        game = new_game("gauge-morale")
        for morale in (0.2, 0.9):
            game.ship.morale = morale
            got = telemetry.crew(game)["morale"]
            assert math.isclose(got, morale), (got, morale)
        return "0.2 reads 0.2 and 0.9 reads 0.9 (it read 1.0 for both)"
