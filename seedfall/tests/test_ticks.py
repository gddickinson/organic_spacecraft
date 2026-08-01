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

`loyalty` has since been fixed and taken off the list, which is what the third
check below is for — it went red the moment the fix landed and said so.

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
PER_CALL: set = set()

#: Ticks the structural sweep cannot judge, because they consume randomness.
#:
#: **These are where the sweep produces false positives, and it produced two.**
#: It drives every tick with a stateless generator so only structure shows —
#: which turns `chance(p)` into a threshold that clears in both runs or
#: neither, depending on nothing but whether `p` lands above a half. A tick
#: that rolls a probability scaled by the span will differ under that driver
#: and be identical in play.
#:
#: Both survivors of #116's list turned out to be exactly that. Measured under
#: a *real* generator, 200 trials a side, one call of thirty days against
#: thirty of one:
#:
#:     ventures   0.505 ± 0.045 live   against   0.540 ± 0.047   (0.5 s.e.)
#:     approach   0.905 ± 0.021 sent   against   0.895 ± 0.022   (0.3 s.e.)
#:
#: Neither is a difference. An earlier version of this file asserted the
#: opposite for `ventures` off **60** trials — 0.400 against 0.500 — and that
#: check was pinning noise. Under-powered measurement encoded as a guard is
#: worse than no guard, because it reads as evidence.
RANDOM = {"approach", "ventures", "dormancy", "market", "lifespan", "upkeep",
          "robots", "threat", "legacy"}


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


#: How far two runs may differ and still count as the same rate.
#:
#: **Not exact equality, and the reason is worth stating.** A tick that applies
#: two per-day rates in sequence can never match itself across chopping,
#: because the two do not commute: `loyalty` records a payday and then drifts
#: toward the ship's mood, and interleaving those thirty times lands 0.23 of a
#: point away from doing each once. That is convergence, not a defect — the
#: gap shrinks with the step, and the clock's step is one day. What this file
#: is for is finding ticks that are *materially* per-call, like the dead-band
#: that made a month of paydays vanish entirely when asked for a day at a
#: time.
TOLERANCE = 0.02


def _strip(o):
    """Drop the counter-derived ids that differ between identical games."""
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items()
                if not (k in ("id", "uid") and isinstance(v, int))}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def _apart(x, y) -> bool:
    """Do these two encoded games differ by more than rounding?"""
    if isinstance(x, (int, float)) and isinstance(y, (int, float)) \
            and not isinstance(x, bool) and not isinstance(y, bool):
        return abs(x - y) > TOLERANCE * max(1.0, abs(x), abs(y))
    if isinstance(x, dict) and isinstance(y, dict):
        return (set(x) != set(y)
                or any(_apart(x[k], y[k]) for k in x))
    if isinstance(x, list) and isinstance(y, list):
        return len(x) != len(y) or any(_apart(a, b) for a, b in zip(x, y))
    return x != y


def _print(game):
    return _strip(save_mod.encode({"game": game}))


def _is_rate(name) -> bool:
    """Does this tick give the same game for one call of 30 as thirty of one?

    **Both games are given the same first day before they diverge.** Several
    subsystems build their state lazily and stamp it with the day they were
    first asked — `exchequer.purse` is born carrying `settled = game.day` —
    so a run that jumps to day 30 before the first call starts from different
    stored state than one that steps. That is when the state was *created*,
    not how the tick scales, and it had `exchequer` flagged here for a whole
    cycle before the difference was traced.
    """
    call = TICKS[name]
    whole, walked = new_game("sweep"), new_game("sweep")
    for game in (whole, walked):
        game.day = 1
        call(game, 1.0, _Fixed())
    whole.day = DAYS
    call(whole, float(DAYS - 1), _Fixed())
    for day in range(1, DAYS):
        walked.day = day + 1
        call(walked, 1.0, _Fixed())
    return not _apart(_print(whole), _print(walked))


def run(suite: Suite) -> None:
    check = suite.check

    @check("the instrument can tell two identical games apart from a change")
    def _():
        # Run first and on purpose. The first version of this sweep reported
        # all fourteen ticks as per-call, because `Ship.uid` and `Officer.id`
        # come from module counters that climb across games — the prints
        # differed before any tick ran.
        one, two = new_game("probe"), new_game("probe")
        assert not _apart(_print(one), _print(two)), (
            "two fresh games from one seed do not match, so every verdict "
            "below is noise")
        memory.tick(one, 30.0)
        memory.tick(two, 30.0)
        assert not _apart(_print(one), _print(two)), (
            "the same tick applied the same way to two games disagrees")
        # And it must be able to *see* a change. Two earlier versions of this
        # line used memory decay and neither worked: five days moves a
        # salience by 0.27% and the print rounds to three places, and a fresh
        # game has no memories to decay at all, so the tick was a no-op. A
        # sensitivity probe has to change something that certainly exists.
        two.credits *= 2
        assert _apart(_print(one), _print(two)), (
            "doubling the purse is invisible to the diff — it is too coarse "
            "to detect anything at all")
        return "identical games match, and a doubled purse shows"

    @check("no tick decides per call except the ones we know about")
    def _():
        found = {name for name in sorted(TICKS)
                 if name not in RANDOM and not _is_rate(name)}
        new = found - PER_CALL
        assert not new, (
            f"{sorted(new)} decide once per call and are not on the list — "
            "a long jump now gives them one decision for the whole span, "
            "which is #116 all over again")
        looked = len(TICKS) - len(RANDOM & set(TICKS))
        return (f"{looked} ticks judged by structure, {len(found)} per call · "
                f"{len(RANDOM & set(TICKS))} left to the trials check below")

    @check("a month of paydays is a month however it is asked for")
    def _():
        # Measured on the officers directly rather than through the
        # whole-game diff above, which works to 2% and cannot see this. Two
        # of the three things wrong with `loyalty` were under that
        # resolution: the dead-band that dropped any move under 0.005, and a
        # drift that added per day instead of compounding. They are real —
        # the dead-band is *why* the scale carried a 0.25 floor, since a
        # thirtieth of a month's credit fell under it and vanished — so they
        # are pinned here where the numbers are visible.
        from ..sim import loyalty
        runs = {}
        for step in (30, 10, 1):
            game = new_game("loy")
            for _ in range(30 // step):
                game.day += step
                list(loyalty.tick(game, float(step), True))
            runs[step] = [loyalty.loyalty_of(o) for o in game.officers]
        base = runs[30]
        for step, got in runs.items():
            for want, have in zip(base, got):
                assert abs(want - have) < 0.5, (
                    f"a month in steps of {step} left an officer at "
                    f"{have:.3f} against {want:.3f} in one call")
        return " · ".join(
            f"{step}d {'/'.join(f'{v:.1f}' for v in got)}"
            for step, got in sorted(runs.items(), reverse=True))

    @check("a power's books are done once a month, not once a call")
    def _():
        # The sweep above runs 30 days and cannot see this: `SETTLE_DAYS` is
        # 30, so one cadence fits in one call either way and the two agree
        # exactly. The gap only opens across several — which is why it
        # survived until a 900-day jump was tried.
        from ..sim import diplomacy as dip_sim
        from ..sim import exchequer as ex_sim
        from ..sim import settlement as settle_sim
        got = {}
        for step in (900, 1):
            game = new_game("exq")
            ex_sim.ensure(game)          # purses born on day 0, as in play
            for _ in range(900 // step):
                game.day += step
                list(ex_sim.settle(game, float(step)))
            got[step] = sum(len(settle_sim.of_power(game, p))
                            for p in dip_sim.POWERS)
        assert got[900] >= got[1] * 0.7, (
            f"900 days in one call founded {got[900]} settlements against "
            f"{got[1]} a day at a time — the books are being done once per "
            "call again")
        return (f"900 days: {got[900]} settlements founded in one call, "
                f"{got[1]} walked")

    @check("the ticks that roll dice come out the same either way")
    def _():
        # What the structural sweep cannot judge, measured properly: 200
        # trials a side under a real generator. This check replaced one that
        # asserted the *opposite* off 60 trials — 0.400 ventures against
        # 0.500 — which was noise dressed as a finding.
        import statistics as stats

        from ..core.rng import RNG
        from ..sim import approach, ventures

        def sweep(name, run, count=200):
            got = {}
            for step in (30, 1):
                seen = []
                for trial in range(count):
                    game = new_game(f"{name}{trial}")
                    rng = RNG(f"{name}r{trial}")
                    for _ in range(30 // step):
                        game.day += step
                        run(game, float(step), rng)
                    seen.append(_count(name, game))
                got[step] = (stats.mean(seen),
                             stats.stdev(seen) / (count ** 0.5))
            return got

        def _count(name, game):
            if name == "v":
                return len(ventures.live(game))
            return 1 if getattr(game, "envoy", None) is not None else 0

        said = []
        for name, run in (("v", lambda g, n, r: list(ventures.tick(g, n, r))),
                          ("a", lambda g, n, r: list(approach.tick(g, n, r)))):
            got = sweep(name, run)
            (whole, e_w), (walked, e_k) = got[30], got[1]
            spread = (e_w ** 2 + e_k ** 2) ** 0.5
            assert abs(walked - whole) < 3.0 * spread, (
                f"{name}: {whole:.3f} in one call against {walked:.3f} walked, "
                f"{abs(walked - whole) / max(spread, 1e-9):.1f} standard "
                "errors — that is a real per-call difference, put it back on "
                "the list")
            said.append(f"{name} {whole:.3f} vs {walked:.3f} "
                        f"({abs(walked - whole) / max(spread, 1e-9):.1f} s.e.)")
        return " · ".join(said)

    @check("the ones on the list really are still broken")
    def _():
        # A list of known faults has to stay honest in both directions: an
        # entry that has quietly been fixed makes the guard above weaker than
        # it looks, because it is spending a licence nobody needs.
        fixed = {name for name in PER_CALL if _is_rate(name)}
        assert not fixed, (
            f"{sorted(fixed)} are on the per-call list and now scale properly "
            "— take them off it, the guard is loose by that much")
        return (f"{len(PER_CALL)} on the list"
                + (f": {', '.join(sorted(PER_CALL))}" if PER_CALL else
                   " — every structural tick now scales with the days given"))
