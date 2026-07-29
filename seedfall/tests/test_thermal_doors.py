"""Every way heat gets into a hull, and whether any of them skips the ceiling.

Two cycles went into bounding heat, and `INTERFACE.md` came out of them saying
"call `cook()` wherever heat is **added**; there are exactly two such places,
`combat._fire` and `flight.travel_to`". There were six. The other four —
a crossing watch in `transit`, a flight incident in `flight`, an action's own
effects in `actions`, and taking a hit in `damage` — put heat in without ever
consulting the ceiling.

An incident on its own took a hull sitting exactly at the ceiling to **2.36x**
its rated cap, which is the compounding the ceiling exists to prevent: every
penalty for running hot scales with how far over you are.

The fix is not another `cook()` call. `ship.add_heat` is the only way to put
heat into a hull and it clamps on the way in, so a new caller cannot forget —
which is what four of six did.

While measuring it, a smaller thing in the same function: a fuel incident
rolled two to eight tonnes, took as much of it as the tank held, and reported
the roll. One in five said "8 t of reaction mass gone" to a captain who had
lost three.

The claims:

- **Nothing adds heat except through `add_heat`.** The general one, and the
  one that would have found all four at once.
- **No path can put a hull over the ceiling**, measured by playing.
- **`add_heat` clamps, floors and does not invent heat.**
- **An incident reports what it took.**
"""

from __future__ import annotations

import pathlib
import re

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import flight
from ..sim.ship import HEAT_CEILING, add_heat
from .harness import Suite

#: Raw arithmetic on a hull's heat. `add_heat` is the only sanctioned way in.
RAW = re.compile(r"\.heat\s*\+=")

#: `sim/customs.py` has its own `add_heat` — scrutiny from the revenue, not
#: thermal load. It shares nothing with `sim/ship.py` and imports nothing from
#: it; the name is a coincidence and this check must not trip on it.
NOT_THERMAL = {"customs.py"}


def _sim_sources():
    root = pathlib.Path(__file__).resolve().parent.parent
    for folder in ("sim", "core", "world", "ui", "bridge"):
        for path in (root / folder).rglob("*.py"):
            yield path


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing puts heat into a hull except through add_heat")
    def _():
        # The general question. Four of the six sites skipped the ceiling and
        # the documentation said there were two — no amount of testing the
        # two that worked would have found the four that did not.
        raw = []
        for path in _sim_sources():
            if path.name == "ship.py":
                continue          # where `add_heat` itself lives
            for line in path.read_text(encoding="utf-8").splitlines():
                if RAW.search(line):
                    raw.append(f"{path.name}: {line.strip()[:56]}")
        assert not raw, (
            f"{len(raw)} place(s) add heat without the ceiling: {raw}")
        return "every heat addition goes through add_heat"

    @check("no way of flying can put a hull over the ceiling")
    def _():
        # Measured rather than reasoned: fly hard, take incidents, and watch.
        worst = 0.0
        for seed in range(24):
            game = new_game(f"fly{seed}")
            cap = game.ship_stats.heat_cap
            for leg in range(10):
                game.ship.cargo["volatiles"] = 9999
                flight.travel_to(game, leg % len(game.system.bodies), "hard")
                worst = max(worst, game.ship.heat / cap)
                if game.dead:
                    break
        assert worst <= HEAT_CEILING + 1e-6, (
            f"flying reached {worst:.2f}x the rated cap against a ceiling of "
            f"{HEAT_CEILING}")
        assert worst > 1.0, (
            f"nothing ever went over its cap at all ({worst:.2f}x), so this "
            "measured nothing")
        return f"{worst:.2f}x the cap at the very worst, ceiling {HEAT_CEILING}"

    @check("an incident cannot push a cooked hull further")
    def _():
        # The exact case: a hull already at the ceiling, then a fault.
        worst = 0.0
        seen = set()
        for seed in range(200):
            game = new_game(f"inc{seed}")
            cap = game.ship_stats.heat_cap
            game.ship.heat = cap * HEAT_CEILING
            res = flight._incident(game, RNG(f"i{seed}"),
                                   flight.BURNS_BY_ID["hard"])
            seen.add(res["name"])
            worst = max(worst, game.ship.heat / cap)
        assert len(seen) >= 3, f"only {sorted(seen)} ever happened"
        assert worst <= HEAT_CEILING + 1e-6, (
            f"a fault took a hull already at the ceiling to {worst:.2f}x")
        return (f"{len(seen)} kinds of fault, none of them past "
                f"{worst:.2f}x the cap")

    @check("add_heat clamps, floors, and invents nothing")
    def _():
        game = new_game("helper")
        ship = game.ship
        cap = 50.0
        ship.heat = 0.0
        add_heat(ship, 10.0, cap)
        assert abs(ship.heat - 10.0) < 1e-9, ship.heat
        add_heat(ship, 500.0, cap)
        assert abs(ship.heat - cap * HEAT_CEILING) < 1e-9, ship.heat
        # Taking heat out works, and never goes below nothing.
        add_heat(ship, -1000.0, cap)
        assert ship.heat == 0.0, ship.heat
        # And adding nothing changes nothing, even from over the cap.
        ship.heat = cap * 1.5
        add_heat(ship, 0.0, cap)
        assert abs(ship.heat - cap * 1.5) < 1e-9, ship.heat
        return "clamped at the ceiling, floored at nothing, inert at zero"

    @check("a fault reports the reaction mass it actually took")
    def _():
        # It rolled two to eight, took what the tank held, and reported the
        # roll: one in five told a captain with three tonnes that eight had
        # gone.
        wrong, checked = 0, 0
        for seed in range(300):
            game = new_game(f"fuel{seed}")
            game.ship.cargo["volatiles"] = 3.0
            before = game.ship.cargo.get("volatiles", 0)
            res = flight._incident(game, RNG(f"j{seed}"),
                                   flight.BURNS_BY_ID["hard"])
            if "reaction mass" not in res["detail"]:
                continue
            checked += 1
            took = before - game.ship.cargo.get("volatiles", 0)
            said = float(res["detail"].split()[0])
            if abs(said - took) > 0.01:
                wrong += 1
        assert checked > 30, checked
        assert not wrong, (
            f"{wrong} of {checked} fuel faults reported more than they took")
        return f"{checked} fuel faults, every one reporting its own arithmetic"
