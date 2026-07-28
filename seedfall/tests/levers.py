"""The claims the game makes, and how to switch each one off.

One entry per feature that says it changes a number. Kept apart from the check
that runs them so adding a lever is a small, obvious edit.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import allegiance
from ..sim import bloom as bloom_sim
from ..sim import combat, consorts, customs as customs_sim, diplomacy as dip
from ..sim import dig as dig_sim
from ..sim import encounters
from ..sim import expedition as expedition_sim
from ..sim import inquiry, loading, loyalty, market as market_sim
from ..sim import mining, research as research_sim
from ..sim import responses as response_sim
from ..sim import stations, transit as transit_sim
from ..sim import weather as weather_sim
from ..sim import works as works_sim
from ..sim.ship import build_layers, make_ship, stats
from ..world.economy import buy_price
from . import captain_ai
from .efficacy import Lever


# ── the Bloom answers a captain who burns it ───────────────────────────────

def _bloom_spread() -> float:
    game = new_game("lever-bloom")
    state = response_sim.state(game)
    state.responses = ["stir", "harden", "swarm", "hunt"]
    state.stage = 2
    # A short window, and only lightly seeded. Run it long enough and every
    # system pins at its ceiling of 1.0, so a Bloom growing half again as fast
    # arrives at exactly the same total and the lever reads as inert.
    for system in game.galaxy.systems[:8]:
        system.bloom = 0.15
    start = sum(s.bloom for s in game.galaxy.systems)
    for _ in range(4):
        game.advance_days(90)
    return sum(s.bloom for s in game.galaxy.systems) - start


# ── a laden hull flies worse ───────────────────────────────────────────────

def _laden_speed() -> float:
    game = new_game("lever-load")
    ship = make_ship("navis", ["slug_battery", "mag_lance", "carapace",
                               "ossified_bracing", "reaction_organ",
                               "opsin_eyes", "chemo_gut", "radiator_bloom"])
    build_layers(ship, game.bonuses)
    ship.cargo = {"ore": 220}
    return stats(ship).speed


# ── a screening consort takes hits meant for you ───────────────────────────

def _flag_damage() -> float:
    game = new_game("lever-screen")
    taken = 0.0
    for index in range(8):
        ship = make_ship("navis", ["slug_battery", "mag_lance",
                                   "reaction_organ", "opsin_eyes", "chemo_gut"])
        build_layers(ship, game.bonuses)
        ship.cargo = {"ore": 300, "alloy": 300}
        fleet = []
        for n in range(2):
            escort = make_ship("vesper", ["mag_lance", "reaction_organ",
                                          "opsin_eyes"], f"Escort {n}")
            build_layers(escort, game.bonuses)
            escort.cargo = {"ore": 200, "alloy": 200}
            escort.escort = True
            fleet.append(escort)
        rng = RNG(f"screen-{index}")
        battle = combat.start(ship, stats(ship),
                              encounters.make_enemy(rng, "freeholds", 1.2),
                              rng=rng, game=game, fleet=fleet)
        for consort in battle.consorts:
            consort.order = "screen"
        for _ in range(30):
            if battle.over:
                break
            combat.take_turn(battle, captain_ai.orders(battle), rng)
        taken += battle.player.taken
    return taken / 8


# ── grievances fade, so the sector does not ratchet shut ───────────────────

def _worst_pair() -> float:
    game = new_game("lever-drift")
    game.credits = 500000
    a, b = dip.POWERS[0], dip.POWERS[1]
    dip.shift_relation(game, a, b, -40)
    for _ in range(12):
        game.advance_days(365)
    return min(dip.relation(game, x, y)
               for i, x in enumerate(dip.POWERS) for y in dip.POWERS[i + 1:])


# ── weather makes ground harder to cross ───────────────────────────────────

def _tiles_crossed() -> float:
    covered = 0
    for index in range(10):
        game = new_game(f"lever-wx-{index}")
        body = next(b for s in game.galaxy.systems for b in s.bodies
                    if b.kind not in ("gas", "star"))
        rng = RNG(f"wx-{index}")
        party = expedition_sim.generate(rng, game.system, body, [], 30)
        weather_sim.set_front(party, "gale", 900)
        for _ in range(30):
            if party.over:
                break
            if weather_sim.pinned(party):
                expedition_sim.shelter(party, rng)
                continue
            expedition_sim.move(party, *rng.pick([(0, -1), (1, 0), (-1, 0), (0, 1)]),
                                [], rng)
        covered += sum(1 for t in party.tiles if t.visited)
    return covered / 10


# ── a colony's works change what it produces ───────────────────────────────

def _colony_yield() -> float:
    game = new_game("lever-works")
    from ..sim import colony as colony_sim
    game.credits = 900000
    game.ship.fitted.append("seed_bay")
    game.research.unlocked.append("bioleach")
    game.recompute()
    for key in ("alloy", "ore", "biomass", "volatiles"):
        game.stores[key] = 9000
    body = next(b for b in game.system.bodies
                if b.kind in ("asteroid", "moon", "rocky"))
    colony, _why = colony_sim.found(game, game.system, body, "radix_mine")
    game.advance_days(colony.need + 20)
    works_sim.begin(game, colony, "deepen")
    game.advance_days(120)
    return works_sim.yields_of(colony).get("ore", 0.0)


# ── loyalty is felt at the crew stations ───────────────────────────────────

def _station_level() -> float:
    game = new_game("lever-loyal")
    for officer in game.officers:
        officer.loyalty = 95.0
        officer.stat = "nav"
    return stations.officer_level(game.officers, "nav")


# ── a market shock moves the price ─────────────────────────────────────────

def _shocked_price() -> float:
    game = new_game("lever-shock")
    system = next(s for s in game.galaxy.systems if s.market)
    cid = next(iter(system.market.stock))
    game.shocks = [market_sim.Shock(id=1, kind="convoy", system_id=system.id,
                                    commodity=cid, until=game.day + 200)]
    market_sim.apply_to_markets(game)
    return float(buy_price(system.market, cid))


# ── how you work a body changes what comes off it ──────────────────────────

def _bore_yield() -> float:
    from ..sim.actions import extract
    total = 0.0
    for index in range(6):
        game = new_game(f"lever-bore-{index}")
        game.stores["biomass"] = 900
        game.ship.cargo = {"volatiles": 60}
        for body in game.system.bodies:
            body.surveyed = True
        target = max(range(len(game.system.bodies)),
                     key=lambda i: sum(game.system.bodies[i].resources.values()))
        result = extract(game, target, 60, "bore")
        if result.get("ok") and not result.get("dead"):
            total += sum(result["got"].values())
    return total / 6


# ── evidence on the bench speeds a programme ───────────────────────────────

def _days_to_first_tech() -> float:
    game = new_game("lever-bench")
    tech = next(t for t in research_sim.researchable(game.research.unlocked))
    research_sim.set_project(game.research, tech.id)
    # Deliberately *empty*. Stocking it to the brim made the live run and the
    # neutralised one both fully supplied, so the lever compared full against
    # full and reported no difference at all.
    game.research.evidence = {}
    while game.research.current and game.day < 1200:
        game.advance_days(30)
    return float(game.day)


# ── the watches of a crossing cost something ───────────────────────────────

def _crossing_days() -> float:
    total = 0.0
    runs = 20
    for index in range(runs):
        game = new_game(f"lever-fly-{index}")
        game.ship.cargo = {"volatiles": 120}
        target = max(range(len(game.system.bodies)),
                     key=lambda i: game.system.bodies[i].orbit)
        started = transit_sim.begin(game, target, "standard")
        if not started["ok"]:
            continue
        crossing = started["transit"]
        rng = RNG(f"fly-{index}")
        guard = 0
        while not crossing.over and guard < 30:
            guard += 1
            if crossing.event:
                choices = transit_sim.options(crossing)
                pick = min(choices, key=lambda o: (o.risk, o.damage))
                transit_sim.choose(game, crossing, pick.id, rng)
            else:
                transit_sim.stand(game, crossing, rng)
        total += crossing.days_spent
    return total / runs


# ── the powers notice whose work you take ──────────────────────────────────

def _spread_standing() -> float:
    """Total standing after working every power evenly, in a hostile sector.

    Summed rather than measured on one power: the whole claim is that you
    cannot bank goodwill everywhere at once.
    """
    powers = ("charter", "concordat", "freeholds", "sanhedrin")
    game = new_game("lever-sides")
    for index in range(28):
        power = powers[index % len(powers)]
        game.adjust_rep(power, 5)
        allegiance.charge(game, power, 5)
    return sum(game.rep.get(p, 0) for p in powers)


# ── somebody looks in the hold ─────────────────────────────────────────────

def _smuggling_purse() -> float:
    """What six contraband runs leave in the purse."""
    from ..tests.test_customs import _career
    total = 0.0
    runs = 8
    for index in range(runs):
        total += _career(f"lever-smug-{index}", 6, False, RNG(f"ls-{index}"))
    return total / runs


# ── hurrying a dig costs you the find ──────────────────────────────────────

def _cut_dig_points() -> float:
    """Understanding banked cutting straight down through a site.

    Cutting is the roughest method, so it is where the spoil roll bites
    hardest — a probe on the careful method would barely move.
    """
    from ..data.xenotech import XENOTECH
    total = 0.0
    runs = 12
    for index in range(runs):
        game = new_game(f"lever-dig-{index}")
        body = game.system.bodies[0]
        body.relic = XENOTECH[0].id
        body.relic_found = True
        body.digs = 0
        started = dig_sim.begin(game, 0)
        if not started["ok"]:
            continue
        site = started["dig"]
        game.dig = site
        rng = RNG(f"dig-{index}")
        guard = 0
        while not site.over and guard < 10:
            guard += 1
            dig_sim.work(game, site, "cut", rng)
        total += site.points
    return total / runs


LEVERS: list[Lever] = [
    Lever("allegiance-cost",
          "the powers notice whose work you take",
          patch=(allegiance, "price", lambda _g, _p, _w: []),
          probe=_spread_standing, direction="higher"),

    Lever("customs-search",
          "somebody looks in the hold",
          patch=(customs_sim, "chance", lambda _g, _f, _a=0.0: 0.0),
          probe=_smuggling_purse, direction="higher"),

    Lever("dig-spoilage",
          "hurrying a dig takes the find apart on the way out",
          patch=(dig_sim, "spoil_chance", lambda _s, _m: 0.0),
          probe=_cut_dig_points, direction="higher"),

    Lever("bloom-provocation",
          "a provoked Bloom grows faster",
          patch=(response_sim, "growth_multiplier", lambda _g: 1.0),
          probe=_bloom_spread, direction="lower"),

    Lever("hull-loading",
          "a laden hull flies worse",
          patch=(loading, "factor", lambda _s, _t=0.0: 1.0),
          probe=_laden_speed, direction="lower"),

    Lever("consort-screening",
          "a screening consort takes hits meant for the flag",
          patch=(consorts, "choose_target", lambda b, _r: b.player),
          probe=_flag_damage, direction="higher"),

    Lever("relation-drift",
          "grievances fade instead of ratcheting shut",
          patch=(dip, "drift", lambda _g, _d: None),
          probe=_worst_pair, direction="lower"),

    Lever("ground-weather",
          "weather makes ground harder to cross",
          patch=(weather_sim, "move_cost", lambda _e, base: base),
          probe=_tiles_crossed, direction="higher"),

    Lever("colony-works",
          "a finished work changes what a colony produces",
          patch=(works_sim, "done", lambda _c: []),
          probe=_colony_yield, direction="lower"),

    Lever("crew-loyalty",
          "loyalty is felt at the crew stations",
          patch=(loyalty, "effective_level", lambda o: float(o.level)),
          probe=_station_level, direction="lower"),

    Lever("market-shocks",
          "a shock moves what a port charges",
          patch=(market_sim, "factor", lambda _g, _s, _c: 1.0),
          probe=_shocked_price, direction="lower"),

    Lever("mining-method",
          "a deep bore lifts more than the rig alone would",
          patch=(mining, "rate_for",
                 lambda body, _m, resource, rig: (
                     body.resources.get(resource, 0.0) * rig
                     * max(0.0, 1 - body.depleted))),
          probe=_bore_yield, direction="lower"),

    Lever("transit-watches",
          "standing the watches of a crossing costs something",
          patch=(transit_sim, "_eligible", lambda _g, _t: []),
          probe=_crossing_days, direction="lower"),

    Lever("research-evidence",
          "evidence on the bench speeds a programme",
          patch=(inquiry, "draw", lambda _r, _t, _d: (1.0, [])),
          probe=_days_to_first_tech, direction="lower"),
]

LEVERS_BY_ID = {lever.id: lever for lever in LEVERS}
