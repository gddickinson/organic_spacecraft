"""Ship time: the phases of a day that run on the crew's own clock.

Split out of `core/clock._one_step`, which had grown to 260 lines with the
two clocks interleaved in one body. **The order is the day's and it lives in
`clock._one_step`**, not here: the phases draw from one `game.rng("tick")`
stream and write one log, so running them in any other order is a different
game (the same-seed state hash over a played year is what pins that). What
each phase is handed says which clock it runs on — `ship_n` is days aboard,
`n` is sector days — and a phase that needs both says why.

The `st` every phase is handed is the stats object as it stood when the day
began, deliberately: a research completion mid-day calls `game.recompute()`,
which replaces `game.ship_stats`, and the tick has always read the old one.
"""

from __future__ import annotations

from ..sim import adaptation as adaptation_sim
from ..sim import crew as crew_sim
from ..sim import dormancy as dormancy_sim
from ..sim import lifespan as lifespan_sim
from ..sim import loyalty as loyalty_sim
from ..sim import phenomena as sky_sim
from ..sim import programmes as programmes_sim
from ..sim import regions as regions_sim
from ..sim import research as research_sim
from ..sim import robots as robots_sim
from ..sim import clinic as clinic_sim
from ..sim import upkeep as upkeep_sim
from ..sim.ship import COOK, cool, is_breached, repair_tick


def bench(game, ship_n: int, st, r) -> float:
    """The ship's own research, and how much of it a thin watch can run.

    Returns `manned`, the share of the ship's work the watch can do, which
    the hull phase spends too.
    """
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
    # Once per spell of shortage, not a quarter-chance every day of it — see
    # `research.shortage_news`. (No draw from `r` here any more: the old roll
    # was the only thing this line spent the day's luck on.)
    short = research_sim.shortage_news(game.research, done)
    if short:
        game.add_log(f"The bench is short of {short}; the programme is "
                     "marking time.", "warn")
    if done:
        game.recompute()
        from ..data.tech import TECH_BY_ID
        game.add_log(f"Research complete: {TECH_BY_ID[done].name}.", "good")
    return manned


def hull(game, ship_n: int, st, manned: float) -> None:
    """Repair, cooling and the smelter — work done by the hands aboard."""
    repair_tick(game.ship, ship_n * manned, st)
    cooked = cool(game.ship, st, ship_n)
    adaptation_sim.record(game.ship, "heat", cooked["cooked"] / COOK)
    regions_sim.irradiate(game, ship_n, st)   # the Cradle's dose and heat
    sky_sim.irradiate(game, ship_n, st)       # a flare's, or the nova's
    if cooked["cooked"] > 1:
        game.add_log("The radiators cannot keep up. The hull is cooking.",
                     "warn")
    for kind, text in adaptation_sim.tick(game, ship_n):
        game.add_log(text, kind)

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


def aboard(game, n: int, ship_n: int, st, r):
    """Payroll, air, age, food and the machines.

    Returns whether payroll was met, or None when the day has to stop here —
    the air killed the last of the crew, or something did. The machines run
    on the sector clock (`n`), and the comment below says why.
    """
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
              and (life_layer is None or (life_layer.hp > life_layer.max * 0.2
                                          and regions_sim.lit(game))))
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
                        return None
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
    # And whatever a clinic is owed for keeping somebody young. On the
    # ship's clock, like everything else about the people aboard.
    for kind, text in clinic_sim.tick(game, ship_n):
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
        return None
    return paid


def crew(game, n: int, ship_n: int, st, paid: bool) -> None:
    """Morale, experience and loyalty. A breach is judged on sector days:
    the scale of it is how long the Verge watched you leak."""
    crew_sim.morale_tick(game.ship, ship_n, paid, is_breached(game.ship), st.morale)
    crew_sim.grant_xp(game.officers, "*", ship_n * 1.5, game=game)
    if is_breached(game.ship):
        loyalty_sim.record(game, "breach", scale=min(2.0, n / 10))
    for kind, text in loyalty_sim.tick(game, n, paid):
        game.add_log(text, kind)
