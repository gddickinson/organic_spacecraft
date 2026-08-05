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

from ..sim import allegiance
from ..sim import colony as colony_sim
from ..sim import crew as crew_sim
from ..sim import lifespan as lifespan_sim
from ..sim import customs as customs_sim
from ..sim import inquiry as inquiry_sim
from ..sim import market as market_sim
from ..sim import approach as approach_sim
from ..sim import diplomacy as dip_sim
from ..sim import dormancy as dormancy_sim
from ..sim import responses as response_sim
from ..sim import ventures as venture_sim
from ..sim import exchequer as exchequer_sim
from ..sim import legacy as legacy_sim
from ..sim import memory as memory_sim
from ..sim import loyalty as loyalty_sim
from ..sim import programmes as programmes_sim
from ..sim import research as research_sim
from ..sim import shipyard as shipyard_sim
from ..sim import threat as threat_sim
from ..sim import xeno as xeno_sim
from ..sim import chains as chain_sim
from ..sim import comms as comms_sim
from ..sim import contracts as contract_sim
from ..sim import territory as territory_sim
from ..sim import upkeep as upkeep_sim
from ..data.territory import SEIZED as TERRITORY_SEIZED
from ..world.economy import tick_market
from ..sim import robots as robots_sim
from ..sim.ship import cool, is_breached, repair_tick


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
    """
    if game.dead or game.victory:
        return
    left = float(n)
    if left > MAX_STEP:
        while left > 0.0 and not (game.dead or game.victory):
            span = min(left, float(MAX_STEP))
            left -= span
            _one_step(game, span, dilation)
        return
    _one_step(game, left, dilation)


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
    for name in ("envoy", "demand", "situation"):
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
    r = game.rng("tick")
    # The epsilon is not decoration: a hundred tenth-days sum to
    # 9.999999999999998, so taking the whole part naively loses a day
    # every ten. Over a chronicle of thousands of days that is a real
    # drift in every deadline the game holds.
    raw = float(n)
    carried = game._part_day + raw
    whole = int(carried + 1e-9)
    game._part_day = max(0.0, carried - whole)
    n = whole
    game.day += n

    # Proper time, carried separately for exactly the same reason. Never
    # longer than sector time: `dilation` below 1 would be a clock running
    # backwards relative to the Verge, which nothing in the game means.
    dilation = max(1.0, float(dilation or 1.0))
    aboard = game._part_ship + raw / dilation
    ship_n = int(aboard + 1e-9)
    game._part_ship = max(0.0, aboard - ship_n)
    game.ship_day += ship_n
    st = game.ship_stats

    rate = st.research + 0.25
    game.research.last_event = None
    # A skeleton watch does not run a research programme. This is the brake
    # that stops dormancy and a hard burn from stacking into a free lunch:
    # both cost you the ship's own work, so doing both costs it twice.
    manned = dormancy_sim.ship_work(game)
    for kind, text in dormancy_sim.tick(game, ship_n, r):
        game.add_log(text, kind)
    done = research_sim.tick(game.research, ship_n, rate * manned, r)

    # Whatever the tree could not use goes to the bench's standing work.
    #
    # This is the fix for a real dead end: the tree is sixty-two nodes and the
    # game carries on after every one of its ten endings, so once
    # `researchable` comes back empty the day's points went into
    # `research.banked` — a number `ui/tech_view.py` displays and nothing could
    # ever spend. Measured, 146,040 points over the ten years after the tree
    # closed. See `sim/programmes.py`.
    # Only taken when there is somewhere to put it: `take_spare` zeroes what
    # it hands over, so taking it with the bench stood down would destroy it.
    if programmes_sim.can_take(game):
        found = programmes_sim.tick(game,
                                    research_sim.take_spare(game.research))
        if found is not None:
            from ..data.programmes import PROGRAMMES_BY_ID
            spec = PROGRAMMES_BY_ID[found.programme]
            game.add_log(
                f"Round {found.round} of {spec.name.lower()} is written up. "
                "The findings are yours to place.", "good")
    # Checking unreplicated work is bench time like any other.
    firmed = research_sim.confirm_tick(game.research, ship_n * manned)
    if firmed:
        from ..data.tech import TECH_BY_ID
        game.recompute()
        game.add_log(f"{TECH_BY_ID[firmed].name} is confirmed. The figures "
                     "hold up.", "good")
    if game.research.last_event == "provisional":
        game.add_log("The result is in, and nobody has replicated it. It "
                     "works. It does not work as well as the paper says.",
                     "warn")
    if game.research.last_event == "setback":
        game.add_log("The programme has gone backwards — a result nobody "
                     "could replicate, and a season spent on it.", "bad")
    elif game.research.last_event == "breakthrough":
        game.add_log("A breakthrough on the bench. Weeks of work fell out "
                     "in an afternoon.", "good")
    if getattr(game.research, "starved", None) and not done:
        short = ", ".join(game.research.starved)
        if r.chance(0.25):
            game.add_log(f"The bench is short of {short}; the programme is "
                         "marking time.", "warn")
    if done:
        game.recompute()
        from ..data.tech import TECH_BY_ID
        game.add_log(f"Research complete: {TECH_BY_ID[done].name}.", "good")

    customs_sim.cool(game, n)

    for colony, power in territory_sim.seizures(game, n, r):
        game.add_log(TERRITORY_SEIZED.format(colony=colony.name), "bad")

    _gains, events = colony_sim.tick(game, n)
    for kind, text in events:
        game.add_log(text, kind)

    for ship in shipyard_sim.tick_builds(game, n):
        game.add_log(f"{ship.name} is complete and standing by.", "good")

    repair_tick(game.ship, ship_n * manned, st)
    cooked = cool(game.ship, st, ship_n)
    if cooked["cooked"] > 1:
        game.add_log("The radiators cannot keep up. The hull is cooking.",
                     "warn")

    # A smelter bay turns ore into alloy on the way home, which is the
    # difference between hauling rock and hauling money.
    if st.refine > 0:
        ore = game.ship.cargo.get("ore", 0)
        smelted = min(ore, st.refine * 1.5 * ship_n * manned)
        if smelted > 0.01:
            game.ship.cargo["ore"] = ore - smelted
            if game.ship.cargo["ore"] <= 0.0001:
                game.ship.cargo.pop("ore", None)
            game.ship.cargo["alloy"] = game.ship.cargo.get("alloy", 0) + smelted * 0.45

    for sys in game.galaxy.systems:
        if sys.market:
            tick_market(sys.market, n, r,
                        sys.port.level if sys.port else 1)
    for kind, text in market_sim.tick(game, n, r):
        game.add_log(text, kind)
    market_sim.apply_to_markets(game)
    for kind, text in venture_sim.tick(game, n, r):
        game.add_log(text, kind)
    # And somebody pays for all of it. The powers' purses take the day's
    # income, and once a month they build with the surplus or give something
    # up for the deficit — which is the only thing that has ever changed the
    # sector's infrastructure other than the player. See `sim/exchequer.py`.
    for kind, text in exchequer_sim.settle(game, n):
        game.add_log(text, kind)
    dip_sim.drift(game, n)
    # And the powers act on their own account, rather than only drifting back
    # toward a baseline while the captain does all the talking.
    for kind, text in approach_sim.tick(game, n, r):
        game.add_log(text, kind)

    # Payroll. Miss it and the crew notices immediately.
    wages = crew_sim.daily_wages(game.officers) * ship_n
    paid = game.credits >= wages
    if paid:
        game.credits -= wages
    elif r.chance(0.3):
        game.add_log("Payroll missed. The bridge is very quiet.", "bad")

    # Air. The intima makes it; without one you are drawing on a tank.
    life_layer = next((l for l in game.ship.layers if l.life), None)
    air_ok = (not is_breached(game.ship)
              and (life_layer is None or life_layer.hp > life_layer.max * 0.2))
    if air_ok:
        game.ship.o2 = min(1.0, game.ship.o2 + 0.06 * ship_n)
    else:
        game.ship.o2 -= ship_n / max(1, st.o2_days)
        if game.ship.o2 <= 0:
            game.ship.o2 = 0
            # Only what breathes. The opening screen sells a Dry Choir
            # lineage on "no air to run out of", and this block used to
            # asphyxiate a hull full of recordings on exactly the same
            # schedule as a wet crew.
            lungs = upkeep_sim.breathers(game)
            if lungs > 0:
                lost = min(lungs, max(1, round(lungs * 0.08 * ship_n)))
                game.ship.crew = max(0, game.ship.crew - lost)
                game.add_log(f"Air is gone. {lost} of the crew did not "
                             "make it.", "bad")
                loyalty_sim.record(game, "crew_death")
                if game.ship.crew <= 0 and not lifespan_sim.active(
                        game.officers):
                    # Unless something aboard does not need the air. A hull
                    # with machines standing its watches is not abandoned —
                    # it is what `hullforms` has called crewless Dry Choir
                    # work since the families were written.
                    if robots_sim.watchkeepers(game):
                        game.add_log(
                            "The last of the crew is gone. The machines are "
                            "still standing their watches, and the hull is "
                            "under way.", "warn")
                    else:
                        game.die("Nobody left aboard to hold the watch.")
                        return
            elif r.chance(0.2):
                game.add_log("The air is gone. Nothing aboard has lungs, "
                             "and the silence is unremarkable.", "warn")

    # Time on the people aboard, and what they eat while it passes. Both
    # are per lineage: a Dry Choir recording neither ages nor breathes,
    # and until this existed it did both exactly like everybody else.
    for kind, text in lifespan_sim.tick(game, ship_n, r):
        game.add_log(text, kind)
    for kind, text in upkeep_sim.tick(game, ship_n, r):
        game.add_log(text, kind)
    # The machines eat too, and wear out doing it. On the sector clock rather
    # than the ship's: a Verger left at a holding goes on working while the
    # hull is in transit, which is the whole reason to leave one there.
    # (Imported at module scope — a second `from ... import` down here made
    # the name local to this whole function, so the *earlier* use of it in the
    # air branch was unbound and the crewless path crashed.)
    for kind, text in robots_sim.tick(game, n, r):
        game.add_log(text, kind)
    if game.dead:
        return

    crew_sim.morale_tick(game.ship, ship_n, paid, is_breached(game.ship), st.morale)
    crew_sim.grant_xp(game.officers, "*", ship_n * 1.5, game=game)
    if is_breached(game.ship):
        loyalty_sim.record(game, "breach", scale=min(2.0, n / 10))
    for kind, text in loyalty_sim.tick(game, n, paid):
        game.add_log(text, kind)

    # Notes banked against a technology whose prerequisites have since been
    # met can finally be made sense of.
    # **The sector says things to you.** Derived from what has changed since
    # it last reported, so it cannot repeat itself or drift — `sim/comms`.
    comms_sim.tick(game, 1)
    comms_sim.sweep(game)
    for contract, outcome in contract_sim.check(game):
        if outcome == "done":
            game.add_log(f"Contract complete: {contract.title}. "
                         f"Paid {round(contract.reward):,} credits.", "good")
            if contract.cost:
                game.add_log("Word gets round who you work for — "
                             f"{allegiance.phrase(contract.cost)}.", "warn")
            for kind, text in chain_sim.on_contract_done(game, contract):
                game.add_log(text, kind)
        else:
            game.add_log(f"Contract expired: {contract.title}.", "bad")
            for kind, text in chain_sim.on_contract_failed(game, contract):
                game.add_log(text, kind)

    for tech in xeno_sim.settle(game):
        game.add_log(f"Xenotechnology incorporated: {tech.name}.", "good")

    for kind, text in threat_sim.tick(game, n, r):
        game.add_log(text, kind)
    memory_sim.tick(game, n)
    for kind, text in legacy_sim.tick(game, n, r):
        game.add_log(text, kind)
    response_sim.decay(game, n)
    for kind, text in response_sim.check(game, r):
        game.add_log(text, kind)
    # Endings are checked before the Bloom is allowed to kill you, because
    # one of them is surviving it: Ruin fires when the sector is lost and
    # you are still flying, and the old order set `dead` first so it could
    # never fire at all.
    win = threat_sim.check_victory(game)
    if win and not game.victory and not legacy_sim.in_epoch(game):
        game.victory = win
    # Inside an epoch the Bloom is no longer the clock — the epoch's own
    # pressure is. Without this the Ruin aftermath killed you on its first
    # tick, because the sector is still ninety-five per cent overgrown by
    # definition and `overgrown` fires every time.
    if game.overgrown and not game.victory and not legacy_sim.in_epoch(game):
        game.dead = True
        game.ending = "overgrown"
    game.recompute()
