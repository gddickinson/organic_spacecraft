"""Which subsystem ticks are a rate, and which are a decision per call.

`core/clock.advance_days` hands `n` days to fourteen ticks. One that scales a
*rate* by `n` gives the same answer however the span is chopped; one that makes
a *decision* once per call does not, and a long jump gives it one decision to
cover the whole span. That is #116, and it has been found the hard way four
times running — `exchequer.settle` first, then repair, then the freight desk,
then officer ageing — each discovered only when the honest clock made a check
go red.

**This is the sweep that should have been written first.** It calls every tick
two ways on identical games, once for thirty days and once thirty times for
one, and diffs the whole encoded game. The list it produces is the work
remaining on #116, all at once, instead of one surprise a cycle.

Measured when it was written — four of fourteen:

    decision   ventures  exchequer  approach  loyalty
    rate       dormancy colony shipyard market lifespan upkeep
               robots threat memory legacy

**The instrument nearly lied, and validating it is half this file.** The first
version fingerprinted the game through the save encoder and reported *every*
tick as a decision, which should have been unbelievable on its face — a decay
tick cannot be per-call. Two fresh games from the same seed did not match
each other: `Ship.uid` and `Officer.id` come from module-level counters that
keep climbing across games, so the fingerprints differed before any tick ran.
The two controls below run first for that reason, and if they fail the verdicts
below them are noise.
"""

from __future__ import annotations

import json

from ..core import save as save_mod
from ..core.state import new_game
from ..sim import (approach, colony, dormancy, exchequer, legacy, lifespan,
                   loyalty, market, memory, robots, shipyard, threat, upkeep,
                   ventures)
from .harness import Suite

DAYS = 30

#: Ticks known to decide once per call rather than scale by the days given.
#:
#: Every one of these makes a long jump differ from the same span walked, and
#: every one is work remaining on #116. Shrinking this list is the task;
#: *growing* it silently is what the check below exists to prevent.
PER_CALL = {"ventures", "exchequer", "approach", "loyalty"}


class _Fixed:
    """A generator with no state, so only structure shows in the diff."""

    seed = 0

    def next(self):
        return 0.5

    def float(self, a=0.0, b=1.0):
        return (a + b) / 2.0

    def int(self, a, b):
        return (a + b) // 2

    def chance(self, p):
        return p >= 0.5

    def pick(self, xs):
        xs = list(xs)
        return xs[len(xs) // 2] if xs else None

    def weighted(self, rows):
        rows = list(rows)
        return rows[len(rows) // 2][1] if rows else None

    def shuffle(self, xs):
        return xs


TICKS = {
    "dormancy": lambda g, n, r: list(dormancy.tick(g, n, r)),
    "colony": lambda g, n, r: colony.tick(g, n),
    "shipyard": lambda g, n, r: list(shipyard.tick_builds(g, n)),
    "market": lambda g, n, r: list(market.tick(g, n, r)),
    "ventures": lambda g, n, r: list(ventures.tick(g, n, r)),
    "exchequer": lambda g, n, r: list(exchequer.settle(g, n)),
    "approach": lambda g, n, r: list(approach.tick(g, n, r)),
    "lifespan": lambda g, n, r: list(lifespan.tick(g, n, r)),
    "upkeep": lambda g, n, r: list(upkeep.tick(g, n, r)),
    "robots": lambda g, n, r: list(robots.tick(g, n, r)),
    "loyalty": lambda g, n, r: list(loyalty.tick(g, n, 0.0)),
    "threat": lambda g, n, r: list(threat.tick(g, n, r)),
    "memory": lambda g, n, r: memory.tick(g, n),
    "legacy": lambda g, n, r: list(legacy.tick(g, n, r)),
}


def _norm(o):
    """Drop the counter-derived ids that differ between identical games."""
    if isinstance(o, float):
        return round(o, 3)
    if isinstance(o, dict):
        return {k: _norm(v) for k, v in o.items()
                if not (k in ("id", "uid") and isinstance(v, int))}
    if isinstance(o, list):
        return [_norm(v) for v in o]
    return o


def _print(game) -> str:
    return json.dumps(_norm(save_mod.encode({"game": game})),
                      sort_keys=True, default=str)


def _is_rate(name) -> bool:
    """Does this tick give the same game for one call of 30 as thirty of one?"""
    call = TICKS[name]
    whole = new_game("sweep")
    whole.day = DAYS
    call(whole, float(DAYS), _Fixed())
    walked = new_game("sweep")
    for day in range(DAYS):
        walked.day = day + 1
        call(walked, 1.0, _Fixed())
    return _print(whole) == _print(walked)


def run(suite: Suite) -> None:
    check = suite.check

    @check("the instrument can tell two identical games apart from a change")
    def _():
        # Run first and on purpose. The first version of this sweep reported
        # all fourteen ticks as per-call, because `Ship.uid` and `Officer.id`
        # come from module counters that climb across games — the prints
        # differed before any tick ran.
        one, two = new_game("probe"), new_game("probe")
        assert _print(one) == _print(two), (
            "two fresh games from one seed do not match, so every verdict "
            "below is noise")
        memory.tick(one, 30.0)
        memory.tick(two, 30.0)
        assert _print(one) == _print(two), (
            "the same tick applied the same way to two games disagrees")
        # And it must be able to *see* a change. Two earlier versions of this
        # line used memory decay and neither worked: five days moves a
        # salience by 0.27% and the print rounds to three places, and a fresh
        # game has no memories to decay at all, so the tick was a no-op. A
        # sensitivity probe has to change something that certainly exists.
        two.credits += 1
        assert _print(one) != _print(two), (
            "a credit of difference is invisible to the print — it is too "
            "coarse to detect anything at all")
        return "identical games match, and a single credit of change shows"

    @check("no tick decides per call except the ones we know about")
    def _():
        found = {name for name in sorted(TICKS) if not _is_rate(name)}
        new = found - PER_CALL
        assert not new, (
            f"{sorted(new)} decide once per call and are not on the list — "
            "a long jump now gives them one decision for the whole span, "
            "which is #116 all over again")
        return (f"{len(TICKS)} ticks · {len(found)} decide per call: "
                f"{', '.join(sorted(found))}")

    @check("the ones on the list really are still broken")
    def _():
        # A list of known faults has to stay honest in both directions: an
        # entry that has quietly been fixed makes the guard above weaker than
        # it looks, because it is spending a licence nobody needs.
        fixed = {name for name in PER_CALL if _is_rate(name)}
        assert not fixed, (
            f"{sorted(fixed)} are on the per-call list and now scale properly "
            "— take them off it, the guard is loose by that much")
        return f"all {len(PER_CALL)} still decide per call: {', '.join(sorted(PER_CALL))}"
