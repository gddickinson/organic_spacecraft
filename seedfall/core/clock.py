"""The daily tick: everything that happens when time passes.

Lifted out of `state.py` when that file crossed five hundred lines — which it
did the day time stopped being uniform, because two clocks take twice the
plumbing of one.

`Game.advance_days` delegates straight here and is still the only place the
calendar is written. Read `advance_days` below for the split between sector
time and ship time; it is the design statement that makes a hard burn cost
something.
"""

from __future__ import annotations

import math

from . import ids, sectortime, shiptime


class ClockReentered(RuntimeError):
    """`advance_days` was called from inside a day that is still running."""


#: The games whose clock is running at this moment, by identity. A set rather
#: than a flag on `Game` because it is not state: `ui/crash.py` writes a
#: recovery save from wherever an exception left the day, and a flag saved
#: with it would load a chronicle that refuses ever to advance again.
_RUNNING: set = set()


def advance_days(game, n: float, dilation: float = 1.0) -> None:
    """The only clock in the game, and the only place `day` is written.

    Callers pass fractions — a short local transit, a burn quoted to a
    tenth of a day — and `day` used to take them, drifting to a float.
    Everything downstream assumes a whole number: `day % 365` for the
    stardate, contract deadlines, chart dates, the day a memory was
    formed. The display helper crashed outright on the first fractional
    day (`format code 'd' for object of type 'float'`), which is how this
    was found — by mining something in a running window.

    The fraction is carried rather than dropped, so no time is lost or
    invented over a long chronicle.

    **Time is relative, so there are two clocks.** `n` is always *sector*
    time — what the Verge experiences, and what every deadline, market,
    colony and faction runs on. `dilation` is how many sector days pass
    for each day aboard: at 1.0 the two clocks agree, and at 6.0 a crew
    living through a fortnight comes out the other side to find the sector
    three months older.

    Which clock a system runs on is a real design statement:

    - **Sector time** — markets, ventures, diplomacy, colonies, contract
      deadlines, the Bloom, hulls building at a yard you are not aboard.
      The universe does not care how fast you are going.
    - **Ship time** — research on your own bench, repair, cooling, the
      crew ageing, what they eat, morale, the watches they stand.

    That split is what stops a hard burn from being free. It buys your
    crew their lives back, and it costs you everything you would have got
    done in the time you skipped.
    **A jump of N days has to equal N jumps of one, and it did not.** Every
    subsystem below is handed `n` and asked to do a tick's work with it. Ones
    that scale a *rate* by it are fine; ones that make a *decision* once per
    call are not. Measured on seed "a" across 900 days, the same game three
    ways:

        one jump of 900   charter −252  concordat −198  freeholds −138
        90 jumps of 10    charter +515  concordat +257  freeholds +345
        900 jumps of 1    charter +489  concordat +256  freeholds +279

    Traced to `exchequer.settle`, which took 900 days of bills and made **one**
    investment — 0 settlements against 6. Fixing it there was tried and is the
    wrong place: by then its *inputs* have diverged too, because the market and
    colony ticks were handed the same span.

    `MAX_STEP` is 1 rather than something coarser because that turns the claim
    from "within six per cent" into an equality with no tolerance in it.

    **It is not re-entrant, and it refuses to be.** A tick that advanced the
    clock itself would run every subsystem inside a half-finished day — the
    markets ticked, the payroll not yet paid — and then finish the outer day
    on the far side of the inner one. No caller does this today (every
    `advance_days` outside the tests is a player action or a wait, and the
    full suite runs clean with this guard raising), so the guard costs
    nothing and turns the day somebody writes one into a traceback naming
    the problem rather than a chronicle that drifts.

    A span that is not a finite, non-negative number is refused the same
    way. `inf` looped for ever (`inf - 1` is `inf`), `nan` raised from deep
    inside the calendar arithmetic, and a negative span wound `day` back —
    all three reachable from the remote bridge before it validated input.
    """
    left = float(n)
    if not math.isfinite(left) or left < 0.0:
        raise ValueError(f"advance_days wants a finite span >= 0, not {n!r}")
    if game.dead or game.victory:
        return
    key = id(game)
    if key in _RUNNING:
        raise ClockReentered(
            "advance_days was called while this game's day was still running; "
            "a tick must not advance the clock itself")
    _RUNNING.add(key)
    # Whatever the day makes — memories, shocks, contracts — takes its ids
    # from this chronicle's own book (`core/ids.bind`).
    if isinstance(getattr(game, "ids", None), dict):
        ids.bind(game.ids)
    try:
        if left > MAX_STEP:
            while left > 0.0 and not (game.dead or game.victory):
                span = min(left, float(MAX_STEP))
                left -= span
                _one_step(game, span, dilation)
            return
        _one_step(game, left, dilation)
    finally:
        _RUNNING.discard(key)


#: Log kinds a deliberate wait stands down on.
#:
#: `warn` belongs here and it is the whole point: the crew starving is
#: *warned* three times ("it is starting to tell") and only `bad` once
#: everybody is dead. Standing down on `bad` alone stops the wait after
#: the first death, which is exactly too late to do anything about it.
STAND_DOWN_KINDS = ("bad", "warn")


def wait_days(game, days: int, ignoring=()) -> dict:
    """A deliberate wait, standing down on news that deserves a hand.

    `advance_days` is the physical clock and stays exact — a transit or a
    dig bills the days it bills. *Waiting* is different: nobody is flying,
    so there is no reason to sit through news you would have acted on.
    Played before this existed: a year alongside a Fleet Hub starved three
    crew one at a time, with credits in the purse and biomass on sale a
    berth away, while the log said "it is starting to tell" five times.

    Always stops for a question the window would lock on — an envoy, a
    demand, an aftermath situation — and for death or an ending. Stops on
    any ``bad`` log entry when `Options.wait_stands_down` says so. Returns
    a digest: what passed, what it cost, and everything said meanwhile.

    `ignoring` is news already read. Some warnings recur every few days —
    a hold short of biomass says "it is starting to tell" over and over —
    and standing down on each one turned a long wait into a wall the
    player hammered: measured in play, eight stops in fourteen days for
    one shortage. Pressing *carry on* passes back what stopped it, which
    is what makes the button mean "I have seen that" rather than "ask me
    again in three days". Genuinely new bad news still stops it.
    """
    from ..sim import options as options_sim
    on_bad = bool(options_sim.get(game, "wait_stands_down"))
    start_day, start_credits = game.day, game.credits
    said: list[tuple] = []
    stopped = ""
    told: list[str] = []
    seen = set(ignoring or ())
    if _awaiting_answer(game):
        # Asked with a question already on the bridge: no day passes at
        # all. Checking only after the step spent one a press, which is a
        # day of upkeep for nothing while the answer is what is wanted.
        return {"ok": True, "asked": int(days), "days": 0, "credits": 0,
                "stopped": "something is waiting on an answer",
                "good": [], "bad": [], "told": [], "said": 0}
    for _ in range(max(0, int(days))):
        tail = game.log[-1] if game.log else None
        advance_days(game, 1)
        fresh = _since(game.log, tail)
        said.extend(fresh)
        if game.dead or game.victory:
            stopped = "the chronicle turned"
            break
        if _awaiting_answer(game):
            stopped = "something is waiting on an answer"
            break
        news = [t for _d, t, kind in fresh
                if kind in STAND_DOWN_KINDS and t not in seen]
        if on_bad and news:
            stopped = "bad news"
            told = news
            break
    return {"ok": True, "asked": int(days),
            "days": game.day - start_day,
            "credits": round(game.credits - start_credits),
            "stopped": stopped,
            "good": [t for _d, t, k in said if k == "good"],
            "bad": [t for _d, t, k in said if k in ("bad", "warn")],
            # What stopped it, to hand back on "carry on" so the same
            # recurring warning does not stop the next spell as well.
            "told": told,
            "said": len(said)}


def _since(log, tail) -> list[tuple]:
    """The entries appended after `tail`. The log drops from the *front*
    when it is full, so walking back from the end until `tail` is met is
    sound whatever the cap did."""
    if tail is None:
        return list(log)
    out = []
    for entry in reversed(log):
        if entry == tail:
            break
        out.append(entry)
    return list(reversed(out))


def _awaiting_answer(game) -> bool:
    """A question the window would divert into, live right now."""
    from ..sim import approach as approach_sim
    if approach_sim.holds(game):
        return True
    for name in ("demand", "situation"):
        waiting = getattr(game, name, None)
        if waiting is not None and not getattr(waiting, "over", False):
            return True
    return False


#: The longest span any subsystem tick is asked to cover in one go.
#:
#: One day. At ten the answer stops depending on how the caller chopped the
#: time but still sits 5.3% from playing it out day by day; at one the jump
#: *is* the walk. A thirty-day transit costs 25 ms against 8 at ten.
MAX_STEP = 1


def _one_step(game, n: float, dilation: float) -> None:
    """One tick of everything, over a span no longer than `MAX_STEP`."""
    # The epsilon is not decoration: a hundred tenth-days sum to
    # 9.999999999999998, so taking the whole part naively loses a day
    # every ten. Over a chronicle of thousands of days that is a real
    # drift in every deadline the game holds.
    raw = float(n)
    carried = game._part_day + raw
    whole = int(carried + 1e-9)
    game._part_day = max(0.0, carried - whole)
    n = whole

    # Proper time, carried separately for exactly the same reason. Never
    # longer than sector time: `dilation` below 1 would be a clock running
    # backwards relative to the Verge, which nothing in the game means.
    dilation = max(1.0, float(dilation or 1.0))
    aboard = game._part_ship + raw / dilation
    ship_n = int(aboard + 1e-9)
    game._part_ship = max(0.0, aboard - ship_n)

    # **A step with no whole day in it is not a day.** The flight clock bills
    # a beat's worth of time on every beat, and each of those used to run the
    # whole daily tick with `n = 0`. Rates scaled by zero were harmless;
    # *decisions* were not: a colony owing nothing counted as fed, so 392-456
    # days of starvation were forgiven by one 30-second burn; a patrol floors
    # its span at 0.2 days, so 5,000 slices summing to 0.0005 days rolled ten
    # Charter stops; and every slice cost a full tick (30 days in 21.7 s
    # against 0.04 s). The fraction is carried above. The one thing allowed
    # inside a day is a contract whose terms were just met completing — and
    # it draws no luck to do it, so the stream of chance is untouched too.
    if n == 0 and ship_n == 0:
        sectortime.settle_contracts(game)
        return
    r = game.rng("tick")
    game.day += n
    game.ship_day += ship_n
    st = game.ship_stats

    # The day in phases, in the day's own order: the two clocks interleave,
    # and every phase draws from the one `r`, so this sequence *is* the rules
    # — reordering it is a different chronicle. Measured: the same seed gives
    # the same state hash over a played year before and after the split.
    manned = shiptime.bench(game, ship_n, st, r)
    sectortime.holdings(game, n, r)
    shiptime.hull(game, ship_n, st, manned)
    sectortime.economy(game, n, r)
    paid = shiptime.aboard(game, n, ship_n, st, r)
    if paid is None:
        return
    shiptime.crew(game, n, ship_n, st, paid)
    sectortime.reckoning(game, n, r)
