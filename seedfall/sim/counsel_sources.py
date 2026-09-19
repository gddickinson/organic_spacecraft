"""Where the first officer's suggestions come from, one function per door.

Each source reads state and returns suggestions (`sim/counsel.S`), and each
suggestion names the act that carries it out (`verb`, `args`) — the same
sim function a screen's button calls — and the screen that shows it. A
source offers a move only when the act's own preconditions hold today, or
says in `blocked` the exact refusal the act would give. `sim/counsel.act`
performs it; the suite performs every one of them on a copy.
"""

from __future__ import annotations

from .counsel_kit import S, buyable, hop_to, in_market, nearest

#: Reaction mass below this and the first officer says so: a jump across
#: the NAVIS's ten-light-year drive takes about nine tonnes.
FUEL_LOW = 12
#: Days of food a crossing should not start short of.
FOOD_DAYS = 30
#: Hull share at which "get her repaired" becomes urgent.
HULL_LOW = 0.5
#: Hands aboard, as a share of berths, below which signing on is urgent.
HANDS_LOW = 0.6
#: Purse a freight run or a charter should leave behind it.
KEEP = 4_000
#: A raider bounty is offered to a hull throwing at least this much and at
#: least `HUNT_HULL` whole: the hunter bot's measured threshold
#: (`reviews/2026-09-17/changes/nemeses.md`: positive income at 15).
HUNT_FIRE = 15
HUNT_HULL = 0.75
#: How far ahead an Assembly sitting is worth making for.
SITTING_DAYS = 45


def urgent(game) -> list:
    """Fuel, food, hull, hands — anything that ends a career if ignored."""
    from . import lifespan, services, upkeep
    from .ship import hull_pct
    out = []
    here = game.system
    fuel = game.ship.cargo.get("volatiles", 0.0)
    if fuel < FUEL_LOW:
        want = int(FUEL_LOW * 4 - fuel)
        why = f"{fuel:.0f} t of reaction mass aboard — one jump, perhaps."
        if in_market(game) and buyable(game, "volatiles", want):
            out.append(S("fuel", "Take on reaction mass", why, "port",
                         "market", verb="buy",
                         args={"cid": "volatiles", "units": want},
                         weight=100))
        else:
            port = nearest(game, lambda s: s.market is not None
                           and s.port is not None)
            move = hop_to(game, port) if port else None
            if move:
                out.append(S("fuel", f"Make for {port.name} and refuel", why,
                             "map", system=port.id, weight=100, **move))
    plan = upkeep.forecast(game, FOOD_DAYS)
    if not plan["ok"]:
        short = max(plan["short"], key=plan["short"].get)
        units = int(plan["short"][short]) + 1
        why = (f"Short of {short} for a month: {plan['short'][short]:.0f} t "
               "more, or the crew start going without.")
        if in_market(game) and buyable(game, short, units):
            out.append(S("food", f"Buy {short}", why, "port", "market",
                         verb="buy", args={"cid": short, "units": units},
                         weight=99))
    if hull_pct(game.ship) < HULL_LOW and here.port and \
            "repair" in here.port.services:
        quote = services.repair_quote(game)
        if quote["damage"] >= 1:
            ok = game.credits >= quote["cost"]
            out.append(S("hull", "Put the hull in dock",
                         f"The hull is at {hull_pct(game.ship):.0%}. The "
                         f"drydock here quotes ₡{quote['cost']:,}.",
                         "port", "services", verb="repair", weight=98,
                         blocked="" if ok else
                         f"They want {quote['cost']:,} for the work."))
    berths = int(getattr(game.ship_stats, "berths", 0) or 0)
    free = lifespan.berths_free(game)
    if (berths and game.ship.crew < berths * HANDS_LOW and free > 0
            and here.port and "recruit" in here.port.services):
        count = min(free, int((game.credits - KEEP) // lifespan.SIGNING_FEE))
        if count > 0 and lifespan.can_sign_on(game, count)[0]:
            out.append(S("hands", f"Sign on {count} hands",
                         f"{game.ship.crew} hands in {berths} berths, and "
                         "they age out whether you watch or not.",
                         "port", "crew", verb="sign_on",
                         args={"count": count}, weight=97))
    return out


def answers(game) -> list:
    """A question on the bridge that nothing else moves until it is answered."""
    from . import approach
    out = []
    if approach.holds(game):
        out.append(S("envoy", "An envoy is waiting",
                     "A power has come to you with a proposition.", "envoy",
                     verb="answer", args={"what": "envoy"}, weight=96))
    demand = getattr(game, "demand", None)
    if demand is not None and not getattr(demand, "over", False):
        out.append(S("demand", "A power wants an answer about your ground",
                     "Levy, cede or defy — it will not wait for ever.",
                     "demand", verb="answer", args={"what": "demand"},
                     weight=96))
    situation = getattr(game, "situation", None)
    if situation is not None and not getattr(situation, "over", False):
        out.append(S("situation", "The epoch is asking something",
                     "An aftermath situation is waiting on your answer.",
                     "legacy", verb="answer", args={"what": "situation"},
                     weight=96))
    return out


def bench(game, track: str | None) -> list:
    """An idle bench: the next technology on the road you are furthest down."""
    from . import research
    from .counsel_kit import road_tech
    res = game.research
    if res.current:
        return []
    tech = road_tech(game, track)
    if tech is None:
        return []
    if not research.can_research(tech.id, res.unlocked):
        return []
    why = ("The bench is idle and the days are going to waste."
           + (f" It is on the road to {track.title()}." if track else ""))
    return [S("research", f"Research {tech.name}", why, "tech",
              verb="research", args={"tech": tech.id}, weight=90)]


def freight(game) -> list:
    """The desk's best run from this quay, when the purse can load it."""
    from . import freight as freight_sim
    if not in_market(game) or game.credits < KEEP * 2:
        return []
    for run, trip in freight_sim.worth_flying(game, game.system, limit=3):
        units = int(min(trip["tonnes"],
                        (game.credits - KEEP) // max(1, run.buy_here)))
        if units < 1 or run.commodity == "volatiles":
            continue
        if not buyable(game, run.commodity, units):
            continue
        return [S("freight", f"Load {units} t {run.commodity} for "
                             f"{run.target_name}",
                  f"The desk makes it ₡{trip['net']:,} clear after fuel and "
                  f"dues, {trip['days']:.0f} days out.", "port", "desk",
                  system=run.target_id, verb="buy",
                  args={"cid": run.commodity, "units": units}, weight=70)]
    return []


def contracts(game) -> list:
    """Work in hand: go where it is done. Or take some, if none is held."""
    from . import contracts as contract_sim
    out = []
    held = contract_sim.active(game)
    for c in held:
        # Prospecting and relic work is brought back to where it was posted;
        # the rest is done at its target. Here already, the other sources
        # (surveys, the clock settling a delivery) do the work.
        where = (c.issued_at if c.kind in ("prospect", "relic")
                 else c.target_system)
        if where is None or where == game.location_id:
            continue
        target = game.galaxy.systems[where]
        move = hop_to(game, target)
        if move:
            out.append(S(f"contract:{c.id}", f"{c.title}: make for "
                                             f"{target.name}",
                         f"₡{round(c.reward):,} when it is done; "
                         f"{c.deadline - game.day} days left.", "map",
                         system=target.id, weight=65, **move))
            break
    if not held and in_market(game):
        for c in contract_sim.board_for(game, game.system):
            if c.kind == "survey" and len(held) < contract_sim.MAX_ACTIVE:
                out.append(S(f"take:{c.id}", f"Take the {c.title}",
                             f"₡{round(c.reward):,} for work an explorer "
                             "does anyway.", "port", "contracts",
                             verb="take_contract", args={"id": c.id},
                             weight=62))
                break
    return out


def surveys(game) -> list:
    """An unsurveyed body in this system."""
    from . import survey
    for i, body in enumerate(game.system.bodies):
        if body.surveyed:
            continue
        for method in ("pass", "sweep"):
            ok = any(m.id == method and allowed
                     for m, allowed, _w in survey.available(game, body))
            if ok:
                return [S("survey", f"Survey {body.name}",
                          "Unlooked-at, and in this system. Every survey "
                          "sells, and feeds the bench.", "system",
                          verb="survey", args={"body": i, "method": method},
                          weight=50)]
    return []
