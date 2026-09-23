"""The careful captain: plays the way the screens teach, for `test_renown`.

Not a suite. The honest player the Voyage is tuned on (`reviews/2026-09-17/
innovations/09-renown.md`, "Notes from Wave A"):

- takes the first officer's counsel (`sim/counsel`) in order — fuel, food,
  hands, the desk's best run, contracts, surveys, the next rung on the road;
- keeps the crew: signs on hands, fills an empty station, repairs, feeds;
- fights only what the assessment says it can win, otherwise hails or
  breaks off (`sim/assessment`, `sim/parley`); a lost fight is death — this
  captain is never refloated;
- runs dark on a lawless leg (`sim/running_dark`);
- researches toward the Genesis protocol, fits the melt head when it can,
  and dives an ocean it has surveyed.

No exploit it knows of: surveys once, sells what it brought, buys nothing
back, and every credit it holds came through a counter or a purse.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import actions, assessment, counsel, lifespan, parley, piracy
from ..sim import research as research_sim, running_dark, services, trade
from ..sim import crew as crew_sim, stores, upkeep
from ..sim.ship import hull_pct
from ..world.galaxy import distance
from .captain_ai import orders

#: Reaction mass kept aboard, and food in days: counsel only shouts below
#: twelve tonnes, which is one jump from stranded.
FUEL_KEEP = 120
FOOD_DAYS = 240
#: The purse at which the melt head is bought: its ₡18,000, twenty tonnes
#: of biomass and twenty-six of ore, and a little over.
MELT_HEAD_PURSE = 21_000
#: The moves this captain takes from counsel, and those that cost no day.
TRUST = {"buy", "repair", "sign_on", "research", "sell_survey", "survey",
         "take_contract", "jump", "dive", "relight", "dock"}
INSTANT = {"buy", "repair", "sign_on", "research", "sell_survey",
           "take_contract"}


def _market(g) -> bool:
    return bool(g.system.port and g.system.market)


def _road(g) -> None:
    """The bench, as counsel would set it on the road this captain follows."""
    from ..sim import renown
    from ..sim.counsel_kit import road_tech
    if g.research.current:
        return
    tech = road_tech(g, renown.focus(g))
    if tech is not None:
        research_sim.set_project(g.research, tech.id)


def _ashore(g) -> None:
    """At a quay: **come alongside first** (`sim/quayside` — the counter is
    where the hull is made fast), read the board (the Port screen writes the
    prices down), sell what was brought, feed and fuel, crew, repair."""
    from ..sim import anchorage, crossing, flight, market, places, quayside
    if not quayside.alongside(g):
        # Fly to the quay's own world and let the harbourmaster bring her
        # in: the counter is where the hull is made fast (`sim/quayside`),
        # and lighterage from the jump radius is ruinous.
        body, _index = anchorage.anchor_body(g.system)
        if body is not None:
            flight.hold_at(g, body)
        place = places.by_id(g, f"port-{g.location_id}")
        if place is not None:
            crossing.cross(g, place, "dock")
    market.note_prices(g, g.system, g.rep.get(g.system.port.faction, 0),
                       g.ship_stats.trade)
    if g.ship.cargo.get("survey", 0) >= 1:
        trade.sell_survey_data(g)
    food = set(upkeep.demand(g))
    for cid in list(g.ship.cargo):
        if cid not in food and cid not in ("volatiles", "survey") \
                and g.ship.cargo.get(cid, 0) >= 1:
            trade.sell(g, cid, int(g.ship.cargo[cid]))
    for cid, per_day in upkeep.demand(g).items():
        if cid != "volatiles":
            want = int(per_day * FOOD_DAYS - g.ship.cargo.get(cid, 0))
            if want > 0:
                trade.buy(g, cid, want)
    want = int(FUEL_KEEP - g.ship.cargo.get("volatiles", 0))
    if want > 0:
        trade.buy(g, "volatiles", want)
    free = lifespan.berths_free(g)
    hire = min(free, int((g.credits - 6000) // lifespan.SIGNING_FEE))
    if hire > 0 and g.ship.crew < g.ship_stats.berths * 0.8:
        lifespan.sign_on(g, hire)
    held = {o.stat for o in lifespan.active(g.officers)}
    for cand in sorted(crew_sim.pool_at(g, g.system), key=lambda o: -o.level):
        if cand.stat not in held and g.credits > cand.wage + 8000:
            if crew_sim.hire(g, cand).get("ok"):
                held.add(cand.stat)
    if hull_pct(g.ship) < 0.9 and "repair" in g.system.port.services:
        services.repair(g)
    if g.ship.disabled:
        services.clear_faults(g)


def fight(g, encounter, rng) -> str:
    """Win it, talk it down, or leave. Never refloated."""
    from ..sim import aftermath, combat, consorts, rivals
    b = combat.start(g.ship, g.ship_stats, encounter["enemy"],
                     bonuses=g.bonuses, officers=g.officers,
                     rep=g.rep.get(encounter["enemy"].get("faction"), 0),
                     no_parley=encounter.get("no_parley", False), game=g,
                     rng=rng, fleet=consorts.escorts_of(g),
                     band=encounter.get("band") or 3)
    b.enemy_faction = encounter["enemy"].get("faction")
    rivals.opening(g, b, encounter)
    hailed, guard = False, 0
    while not b.over and guard < 80:
        guard += 1
        mine, theirs = hull_pct(b.player.ship), hull_pct(b.enemy.ship)
        if (assessment.weight(b)["ratio"] < assessment.EVEN
                or (mine < 0.45 and theirs > mine)):
            talk = 0.0 if hailed else parley.odds(b)["chance"]
            act = {"type": "hail"} if talk > parley.escape_odds(b)["chance"] \
                else {"type": "flee"}
            hailed = hailed or act["type"] == "hail"
        else:
            act = orders(b)
        combat.take_turn(b, act, rng)
        g.recompute()
        b.player.st = g.ship_stats
    if not b.over:
        b.over, b.result = True, "stalemate"
    aftermath.resolve(g, b, rng)
    return b.result or ""


def jump(g, target: int, rng) -> bool:
    system = g.galaxy.systems[target]
    dark = piracy.lawlessness(g, system) > 0.35 and not system.port
    if dark != running_dark.dark(g):
        running_dark.set_dark(g, dark)
    out = actions.jump_to(g, target)
    if out.get("ok") and out.get("encounter") and not g.dead:
        fight(g, out["encounter"], rng)
    if _market(g) and running_dark.dark(g):
        running_dark.set_dark(g, False)
    return bool(out.get("ok"))


def _melt_head(g) -> None:
    """Fit the melt head at a yard, once the physiology is known."""
    from ..data.chassis import CHASSIS_BY_ID
    from ..data.parts import PARTS_BY_ID
    from ..sim import shipyard
    if (g.ship_stats.can_dive or "piezolyte" not in g.research.unlocked
            or g.credits < MELT_HEAD_PURSE or not _market(g)
            or "shipyard" not in g.system.port.services):
        return
    for cid, need in (("biomass", 20), ("ore", 26)):
        short = need - stores.held(g, cid)
        if short > 0:
            trade.buy(g, cid, int(short) + 1)
    if not shipyard.can_refit_here(g)[0]:
        from ..sim import anchorage, flight
        yards = anchorage.offering(g, "shipyard")
        if not yards:
            return
        flight.travel_to(g, yards[0].body_index, "standard")   # alongside
    chassis = CHASSIS_BY_ID[g.ship.chassis]
    same = [p for p in g.ship.fitted
            if PARTS_BY_ID[p].slot == "utility" and p != "melt_head"]
    for drop in [None] + sorted(same, key=lambda p: PARTS_BY_ID[p].mass):
        fitted = [p for p in g.ship.fitted if p != drop] + ["melt_head"]
        if shipyard.validate(chassis, fitted)[0]:
            if shipyard.apply_refit(g, g.ship, fitted)[0]:
                g.recompute()
            return


def _counsel(g, rng, skip: dict) -> bool:
    """The first officer's moves, in order; True once a day is spent."""
    for _ in range(6):
        moves = counsel.advise(g, 8)
        move = next((m for m in moves if not m["blocked"]
                     and m["verb"] in TRUST
                     and skip.get(m["id"] + str(m["args"]), -1) < g.day), None)
        if move is None:
            return False
        key = move["id"] + str(move["args"])
        if move["verb"] == "jump":
            if not jump(g, move["args"]["to"], rng):
                skip[key] = g.day + 30
            return True
        if not counsel.act(g, move)["ok"]:
            skip[key] = g.day + 30
            continue
        if move["id"] == "freight":
            skip["bound"] = move["system"]
        if move["verb"] not in INSTANT:
            return True
    return False


def _roam(g, rng, prefer=None) -> None:
    near = [s for s in g.galaxy.systems if s.id != g.location_id
            and distance(s, g.system) <= g.ship_stats.jump]
    if not near:
        g.advance_days(10)
        return
    if prefer is not None:
        goal = g.galaxy.systems[prefer]
        target = min(near, key=lambda s: distance(s, goal))
    else:
        fresh = sorted((s for s in near if not s.visited),
                       key=lambda s: distance(s, g.system))
        target = fresh[0] if fresh else rng.pick(
            [s for s in near if s.port] or near)
    quote = actions.jump_quote(g, target)
    if g.ship.cargo.get("volatiles", 0) < quote["fuel"]:
        _ice(g)
        return
    jump(g, target.id, rng)


def _ice(g) -> None:
    """Broke and short of mass: melt some out of the nearest ice, as a
    captain with an empty purse must; call for a tow if there is none."""
    from ..sim import mining
    ice = [(b.resources.get("volatiles", 0), i)
           for i, b in enumerate(g.system.bodies)
           if b.resources.get("volatiles", 0) > 0.05
           and not mining.worked_out(b)]
    if not ice:
        if actions.is_stranded(g):
            actions.distress_call(g)
        else:
            g.advance_days(5)
        return
    body = max(ice)[1]
    g.system.bodies[body].surveyed = True
    if not actions.extract(g, body, 40).get("ok"):
        g.advance_days(5)


def turn(g, rng, plan: dict) -> None:
    """One decision. Every branch spends a day or ends with the clock."""
    _road(g)
    if _market(g):
        _ashore(g)
        _melt_head(g)
    _answer(g)
    skip = plan.setdefault("skip", {})
    if _counsel(g, rng, skip):
        return
    bound = skip.get("bound")
    if bound == g.location_id:
        skip.pop("bound")
        bound = None
    _roam(g, rng, bound)


def _answer(g) -> None:
    """Refuse an envoy; pay a demand's levy, or cede, or defy — the bridge's
    own `reply`, so nothing is left locking the window."""
    from ..bridge import protocol
    from ..sim import approach
    if approach.holds(g):
        protocol.reply(g, "refuse", "envoy")
    demand = getattr(g, "demand", None)
    if demand is not None and not demand.over:
        for choice in ("levy", "cede", "defy"):
            if protocol.reply(g, choice).get("ok"):
                break


def career(seed: str, years: float = 5.0):
    """A whole career. Returns the game as it ended."""
    from ..sim import renown
    g = new_game(seed)
    rng = RNG(f"careful-{seed}")
    plan: dict = {}
    renown.follow(g, "genesis")         # the Voyage's "Follow this road"
    while g.day < years * 365 and not g.dead and not g.victory:
        day = g.day
        turn(g, rng, plan)
        if g.day == day:
            g.advance_days(1)
    return g
