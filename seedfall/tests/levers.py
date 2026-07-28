"""The claims the game makes, and how to switch each one off.

One entry per feature that says it changes a number. Kept apart from the check
that runs them so adding a lever is a small, obvious edit.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import aftermath as aftermath_sim
from ..sim import allegiance
from ..sim import bloom as bloom_sim
from ..sim import charts as chart_sim
from ..sim import colony as colony_sim_for_lever
from ..sim import combat, consorts, contracts as contract_sim_for_lever
from ..sim import customs as customs_sim, diplomacy as dip
from ..sim import dig as dig_sim
from ..sim import encounters
from ..sim import expedition as expedition_sim
from ..sim import flight as flight_sim
from ..sim import freight as freight_sim_for_lever
from ..sim import inquiry, loading, loyalty, market as market_sim
from ..sim import mining, notes as notes_sim
from ..sim import research as research_sim
from ..sim import responses as response_sim
from ..sim import stations, territory as territory_sim
from ..sim import grudge as grudge_sim
from ..sim import transit as transit_sim
from ..sim import weather as weather_sim
from ..sim import works as works_sim
from ..sim.ship import build_layers, make_ship, stats
from ..world.economy import buy_price
from . import captain_ai
from .efficacy import Lever
from .probes import (_grudge_cost, _ground_odds, _forecast_reach, _seat_worth, _overture_honesty, _annex_research, _bench_overdraw, _hard_burn_hull, _wasted_ground,
                     _chart_spread, _contract_net, _cut_dig_points,
                     _desk_runs, _kill_goodwill, _levied_output,
                     _note_evidence, _smuggling_purse,
                     _spread_standing)


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

LEVERS: list[Lever] = [
    Lever("ground-odds",
          "the ground screen says what an attempt is worth trying",
          patch=(expedition_sim, "odds_for", lambda _e, _i, _o: {}),
          probe=_ground_odds, direction="lower"),

    Lever("colony-forecast",
          "the seed dialog says what will grow",
          patch=(colony_sim_for_lever, "forecast",
                 lambda _g, _s, _b, _c: {"yields": {}, "upkeep": {},
                                         "effects": {}, "a_day": 0.0,
                                         "outlay": 0.0, "days": 1,
                                         "payback": None}),
          probe=_forecast_reach, direction="lower"),

    Lever("seat-value",
          "the bridge says what taking a station is worth",
          patch=(stations, "seat_value",
                 lambda _s, _o: {k: {"level": 0, "gain": 0.0, "says": None}
                                 for k in stations.STATION_IDS}),
          probe=_seat_worth, direction="lower"),

    Lever("overture-preview",
          "the screen foretells what an overture moves",
          patch=(dip, "preview",
                 lambda _g, _a, _f, _o=None: {"standing": [], "relations": None,
                                              "gain": 0}),
          probe=_overture_honesty, direction="lower"),

    Lever("work-gates",
          "a colony work names a technology that exists",
          patch=(works_sim, "available",
                 lambda _g, _c: [(w, False, "off") for w in
                                 __import__("seedfall.data.works",
                                            fromlist=["WORKS"]).WORKS]),
          probe=_annex_research, direction="lower"),

    Lever("bench-pacing",
          "the bench eats what the screen says it will",
          patch=(inquiry, "span_of", lambda _t, _r, _rate: 60.0),
          probe=_bench_overdraw, direction="higher"),

    Lever("burn-heat",
          "a hard burn leaves the hull hot",
          patch=(flight_sim, "burn_heat", lambda _b, _s: 0.0),
          probe=_hard_burn_hull, direction="lower"),

    Lever("rig-stops",
          "a rig stops when the hold is full",
          patch=(mining, "days_of_room",
                 lambda _b, _m, _s, _r, days: days),
          probe=_wasted_ground, direction="higher"),

    Lever("freight-desk",
          "the harbourmaster names his own power's ports",
          patch=(freight_sim_for_lever, "from_desk", lambda _g, _h: []),
          probe=_desk_runs, direction="lower"),

    Lever("cargo-pricing",
          "a cargo contract is priced against what the cargo costs",
          patch=(contract_sim_for_lever, "cargo_cost",
                 lambda _g, _s, cid, amount, for_player=False:
                 __import__("seedfall.data.commodities", fromlist=["BY_ID"])
                 .BY_ID[cid].base * 0.55 * amount),
          probe=_contract_net, direction="lower"),

    Lever("field-notes",
          "what a landing party reads is worth something",
          patch=(notes_sim, "file",
                 lambda _g, _n, _b, _s: {"ok": False, "why": "off"}),
          probe=_note_evidence, direction="lower"),

    Lever("kill-goodwill",
          "a power's enemies are glad to hear it lost a hull",
          patch=(aftermath_sim, "_pleased", lambda _g, _f, _w: []),
          probe=_kill_goodwill, direction="lower"),

    Lever("chart-contents",
          "a chart is priced on what is in the system",
          patch=(chart_sim, "components",
                 lambda _g, s: {"base": 1.0, "body": float(len(s.bodies))}),
          probe=_chart_spread, direction="lower"),

    Lever("territory-levy",
          "a power that annexed the ground takes its share",
          patch=(territory_sim, "collect_tithe",
                 lambda _g, _c, _y, _d: {}),
          probe=_levied_output, direction="higher"),

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
          patch=(inquiry, "draw", lambda _r, _t, _d, _rate=1.0: (1.0, [])),
          probe=_days_to_first_tech, direction="lower"),

    Lever("grudge-prices",
          "a power that remembers you badly charges you more",
          patch=(grudge_sim, "price_bias", lambda _g, _f: 1.0),
          probe=_grudge_cost, direction="lower"),
]

LEVERS_BY_ID = {lever.id: lever for lever in LEVERS}
