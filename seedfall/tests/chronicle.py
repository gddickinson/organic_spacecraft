"""One captain, one save, a decade of doing everything.

Every other suite builds a fresh, narrow game: `test_verbs` clicks every
control on a chronicle that has never completed a survey, `test_ui` paints every
screen on a game with no history. So the state that only *accumulates* — charts,
colonies, contracts, treaties, scrutiny, field notes, digs, works — never meets
the screens that read it.

That gap shipped a crash: chart dates were stashed in the price register, and
`market.best_markets` reads `.sell` off everything in it, so a charted sector
plus a port screen raised `AttributeError` inside a Qt slot where Qt swallows
it. Rendering the README screenshots found it in minutes because that was one
long save touching every screen in sequence.

This is that, deliberately.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data.chassis import CHASSIS_BY_ID
from ..data.parts import PARTS, PARTS_BY_ID
from ..sim import charts as chart_sim
from ..sim import colony as colony_sim
from ..sim import contracts as contract_sim
from ..sim import crew as crew_sim
from ..sim import customs as customs_sim
from ..sim import dig as dig_sim
from ..sim import diplomacy as dip_sim
from ..sim import expedition as exp_sim
from ..sim import wayhome as wayhome_sim
from ..sim import anchorage as anchorage_sim
from ..sim import flight as flight_sim
from ..sim import freight as freight_sim
from ..sim import inquiry as inquiry_sim
from ..sim import market as market_sim
from ..sim import notes as notes_sim
from ..sim import research as research_sim
from ..sim import ship as ship_sim
from ..sim import shipyard as shipyard_sim
from ..sim import trade as trade_sim
from ..sim import works as works_sim
from ..sim.actions import extract, jump_quote, jump_to, survey
from ..sim.ship import cargo_free
from ..world.galaxy import distance


#: What the captain will not spend on cargo, so a refit stays reachable.
RESERVE = 16000

#: The purse is topped up to this each round. See `play` for why.
STIPEND = 45000

#: Kept aboard rather than sold: reaction mass, and the stuff refits, seeds
#: and colony works are built out of.
# Biomass is bought heavy on purpose: a party on the ground eats supplies out
# of the same hold a colony seed is grown from, and at 40 t the captain landed
# first and then found itself 15 t short of every seed for a decade.
STOCK = {"volatiles": 60, "biomass": 110, "phosphate": 40, "silicon": 25,
         "alloy": 25}


def _reachable(game):
    here = game.system
    return [s for s in game.galaxy.systems
            if s.id != here.id and distance(s, here) <= game.ship_stats.jump]


def _survey_here(game, rng, plan) -> int:
    """Survey the whole system, not a sample of it.

    Three bodies a round and then move on meant a five-body system was never
    finished, `system.scanned` never went true, and a decade of flying charted
    two systems. A chart is the record of a *completed* survey.
    """
    done = 0
    for index, body in enumerate(game.system.bodies):
        if body.surveyed or game.dead:
            continue
        survey(game, index)
        done += 1
    return done


def _trade_here(game, rng, plan) -> None:
    system = game.system
    if not system.market or not system.port:
        return
    market_sim.note_prices(game, system, game.rep.get(system.port.faction, 0),
                           game.ship_stats.trade)
    # Reaction mass, and the materials a refit or a seed is actually built
    # from. The first version sold everything but volatiles, which meant it
    # sold the biomass and phosphate a seed bay costs — so the bay never fitted
    # however much money the captain had, and nothing was ever planted.
    for cid, want in STOCK.items():
        short = want - game.ship.cargo.get(cid, 0)
        if short > 0:
            trade_sim.buy(game, cid, int(short))
    for cid in list(game.ship.cargo):
        if cid in STOCK:
            continue
        if customs_sim.outlaws(system.port.faction, cid):
            customs_sim.sell_quietly(game, cid)
        else:
            trade_sim.sell(game, cid, 9999)
    for contract in contract_sim.generate(rng, game, system)[:2]:
        contract_sim.accept(game, contract)

    # Take the best run the freight desk can name, and go where it points.
    # Without this the captain wanders and sells whatever falls into the hold:
    # measured over ten years that came to 2,000 credits, which is not enough
    # to fit a seed bay, so nothing was ever planted and half the state this
    # driver exists to accumulate never accumulated.
    # Keep a reserve. Spending sixty per cent of the purse on cargo at every
    # port call is a fine way to trade and a hopeless way to save: the captain
    # oscillated between 1,200 and 9,200 credits for a decade and never once
    # held the 15,000 a seed bay costs.
    plan["bound_for"] = None
    spare = game.credits - RESERVE
    if spare < 500:
        return
    for run, trip in freight_sim.worth_flying(game, system, limit=3):
        tonnes = min(trip["tonnes"], spare // max(1, run.buy_here))
        if tonnes < 1:
            continue
        if trade_sim.buy(game, run.commodity, int(tonnes)).get("ok"):
            plan["bound_for"] = run.target_id
            return


def _fit(game, part_id: str) -> bool:
    """Fit one named part, swapping out the lightest thing in its slot."""
    chassis = CHASSIS_BY_ID[game.ship.chassis]
    part = PARTS_BY_ID[part_id]
    if part_id in game.ship.fitted:
        return False
    if part.tech and part.tech not in game.research.unlocked:
        return False
    fitted = list(game.ship.fitted) + [part_id]
    if not shipyard_sim.validate(chassis, fitted)[0]:
        same = [pid for pid in game.ship.fitted
                if PARTS_BY_ID[pid].slot == part.slot]
        if not same:
            return False
        fitted = [pid for pid in game.ship.fitted
                  if pid != min(same, key=lambda p: PARTS_BY_ID[p].mass)]
        fitted.append(part_id)
        if not shipyard_sim.validate(chassis, fitted)[0]:
            return False
    if not shipyard_sim.apply_refit(game, game.ship, fitted)[0]:
        return False
    game.ship_stats = ship_sim.stats(game.ship, game.bonuses)
    return True


def _put_in_at_a_yard(game) -> bool:
    """Fly alongside a yard, because that is now what refitting requires.

    This driver was written when the rule was "the system has a port" and was
    never brought forward when `shipyard.can_refit_here` tightened it to
    "alongside a yard". It went on calling `apply_refit` from wherever it
    happened to be, getting `You are not alongside a yard` back, and dropping
    it on the floor — so the seed bay was almost never fitted and the decade
    planted nothing. Measured across 24 seeds: one of them ever planted a
    colony, and the coverage check was pinned to exactly that seed.
    """
    here = anchorage_sim.docked_at(game)
    if here is not None and here.offers("shipyard"):
        return True
    yards = anchorage_sim.offering(game, "shipyard")
    if not yards:
        return False
    flight_sim.travel_to(game, yards[0].body_index, "standard")
    return True


def _refit_here(game, rng, plan) -> None:
    """Fit a seed bay, then reach — the two things that open the game up.

    Reach matters more than it looks. At starting jump range a captain can
    flood-fill only three to eighteen of the forty-two systems depending on
    the seed, so a chronicle that never upgrades its drive spends a decade in
    a pocket. Measured before this existed: 144 jumps, six systems.

    Deliberately two named parts rather than a shopping loop. The greedy
    version bought every cheap thing with a jump term in it, and since fitted
    mass costs range it *lost* a light-year of reach while spending the purse.
    """
    if not game.system.port:
        return
    if not _put_in_at_a_yard(game):
        return
    if not game.ship_stats.can_colonise:
        _fit(game, "seed_bay")
    best = max((p for p in PARTS if p.slot == "drive"),
               key=lambda p: p.fx.get("jump", 0))
    if best.id not in game.ship.fitted:
        _fit(game, best.id)


def _hire_here(game, rng, plan) -> None:
    """Crew the empty stations.

    Not a nicety. Every ground option that pays a field note wants comms or
    medicine, and the starting crew is science, nav and engineering — so a
    captain who never visits the berths is offered a note 168 times in a
    decade and can take none of them. Both specialists recruit at ordinary
    rates, so this is a station to fill rather than dead content.
    """
    port = game.system.port
    if not port:
        return
    held = {o.stat for o in game.officers}
    for candidate in crew_sim.recruit_pool(rng, getattr(port, "level", 1)):
        if candidate.stat not in held:
            crew_sim.hire(game, candidate)
            return


def _study_here(game, rng, plan) -> None:
    """Keep a programme running, so the tree and its gated content open up."""
    res = game.research
    if res.current:
        return
    for tech, ok, _why in inquiry_sim.available(game):
        if ok:
            research_sim.set_project(res, tech.id)
            return


def _mine_here(game, rng, plan) -> None:
    if cargo_free(game.ship, game.ship_stats) < 30:
        return
    for index, body in enumerate(game.system.bodies):
        if body.surveyed and body.depleted < 0.5:
            extract(game, index, 30, "cut")
            return


def _dig_here(game, rng, plan) -> None:
    if game.dig is not None and not game.dig.over:
        if dig_sim.at_site(game, game.dig):
            dig_sim.work(game, game.dig, "careful", rng)
        else:
            dig_sim.stop(game, game.dig)          # too far to keep digging
        return
    for index, body in enumerate(game.system.bodies):
        if body.relic and body.relic_found:
            started = dig_sim.begin(game, index)
            if started.get("ok"):
                game.dig = started["dig"]
                dig_sim.work(game, game.dig, "brisk", rng)
            return


def _land_here(game, rng, plan) -> None:
    if game.expedition is not None:
        return
    body = next((b for b in game.system.bodies
                 if b.surveyed and b.kind not in ("gas", "star")), None)
    if body is None or game.ship.cargo.get("biomass", 0) < 12:
        return
    from ..sim.fieldwork import conclude_expedition, launch_expedition
    index = game.system.bodies.index(body)
    if not launch_expedition(game, index, [o.id for o in game.officers], 0).get("ok"):
        return
    party = game.expedition
    guard = 0
    while party is not None and not party.over and guard < 40:
        guard += 1
        # **Walk home while there is still supply for it.** Measured before this
        # was here: a decade of chronicles ended 50 landings stranded and 32
        # aborted and **not one returned**, so the whole way an expedition is
        # meant to end — reach the pad, lift, bank the haul — was never once
        # driven by the long game. `wayhome.standing` prices the walk with the
        # same function `move` charges, and a party that knows the price can hold
        # a smaller reserve: measured over forty landings, turning back on a
        # costed two days' spare returned 15 parties and stranded 5, where the
        # old tile-count rule at the same margin returned 9 and stranded 11.
        way = wayhome_sim.standing(party)
        if way["spare"] <= 2:
            if party.at_lander:
                exp_sim.lift_off(party)
                break
            step = wayhome_sim.step_towards_home(party)
            if step == (0, 0) or not exp_sim.move(
                    party, *step, game.officers, rng).get("ok"):
                break
            continue
        options = exp_sim.options_here(party)
        if options:
            # Weighted by what it pays, not only by what it is likely to work.
            # Picking the best odds every time meant stripping the salvage at
            # 83% and never reading the recorder at 33% — and the recorder is
            # the one that yields a note. 67 expeditions, zero notes filed.
            def worth(i):
                odds = exp_sim.odds_for(party, i, game.officers)
                prize = {"lore": 2.2, "study": 1.7}.get(odds.get("reward"), 1.0)
                return odds.get("chance", 0) * prize
            exp_sim.attempt(party, max(range(len(options)), key=worth),
                            game.officers, rng)
            continue
        moved = False
        for dx, dy in ((0, -1), (1, 0), (-1, 0), (0, 1)):
            if exp_sim.move(party, dx, dy, game.officers, rng).get("ok"):
                moved = True
                break
        if not moved:
            break
    if game.expedition is not None:
        if not game.expedition.over:
            exp_sim.finish(game.expedition, "aborted")
        conclude_expedition(game)


def _politics(game, rng, plan) -> None:
    for faction in dip_sim.POWERS:
        for action, ok, _why in dip_sim.available(game, faction):
            if not ok or action.id in ("denounce",):
                continue
            other = None
            if action.id == "broker":
                other = next((p for p in dip_sim.POWERS
                              if p != faction and game.rep.get(p, 0) >= 40), None)
                if other is None:
                    continue
            dip_sim.perform(game, action.id, faction, other)
            return


def _build(game, rng, plan) -> None:
    for colony in game.colonies:
        if colony.online and not colony.job:
            offers = [w for w, ok, _why in works_sim.available(game, colony) if ok]
            if offers:
                works_sim.begin(game, colony, offers[0].id)
                return
    # Every surveyed body against every class it will take, rather than the
    # first body and then giving up: a single candidate that happens to be
    # inside somebody's declared space, or short one material, used to be the
    # difference between seven colonies and none on the same driver.
    from ..data.colonies import colonies_for
    for site in game.system.bodies:
        if not site.surveyed or site.colony is not None:
            continue
        for klass in colonies_for(site.kind, game.research.unlocked):
            if colony_sim.can_found(game, game.system, site, klass.id)[0]:
                colony_sim.found(game, game.system, site, klass.id)
                return


def _refuel(game) -> bool:
    """Cut reaction mass out of whatever ice is here."""
    ice = next((i for i, b in enumerate(game.system.bodies)
                if b.resources.get("volatiles", 0) > 0.1), None)
    if ice is None:
        return False
    game.system.bodies[ice].surveyed = True
    if cargo_free(game.ship, game.ship_stats) < 20:
        spare = max((c for c in game.ship.cargo if c != "volatiles"),
                    key=lambda c: game.ship.cargo[c], default=None)
        if spare:
            trade_sim.jettison(game, spare)
    return extract(game, ice, 40, "cut").get("ok", False)


def _fight(game, encounter, rng) -> str:
    """Actually take the engagement, with the captain the tactical suite uses.

    The chronicle claimed to do everything and never once fired: encounters
    were generated on arrival and thrown away, so a decade of play exercised
    none of the positional model, none of the stations, and none of the
    aftermath. Four encounters a decade is not many — which is exactly why
    nobody noticed.
    """
    from ..sim import aftermath as aftermath_sim
    from ..sim import combat as combat_sim
    from ..sim import consorts as consort_sim
    from .captain_ai import orders

    battle = combat_sim.start(
        game.ship, game.ship_stats, encounter["enemy"],
        bonuses=game.bonuses, officers=game.officers,
        rep=game.rep.get(encounter["enemy"].get("faction"), 0),
        no_parley=encounter.get("no_parley", False), game=game,
        rng=rng, fleet=consort_sim.escorts_of(game))
    battle.enemy_faction = encounter["enemy"].get("faction")
    guard = 0
    while not battle.over and guard < 80:
        guard += 1
        combat_sim.take_turn(battle, orders(battle), rng)
    if not battle.over:
        battle.over = True
        battle.result = "driven-off"
    aftermath_sim.resolve(game, battle, rng)
    return battle.result or "unresolved"


def _move_on(game, rng, plan) -> bool:
    near = _reachable(game)
    if not near:
        return False
    # Somewhere new first, then wherever the hold is bound. Ranking the
    # freight run first looked right and wasn't: the desk kept naming the
    # same neighbouring port, so the captain shuttled one profitable lane
    # 144 times and saw six systems in ten years.
    #
    # Unless the hold is out of the things the game is played with, in which
    # case find a quay. Exploring blind walked the captain into a pocket of
    # port-less systems and left it there for thirteen straight rounds on
    # eleven tonnes of biomass, unable to plant anything it found.
    bound = plan.get("bound_for")
    short = any(game.ship.cargo.get(cid, 0) < want * 0.15
                for cid, want in STOCK.items())
    if short:
        near.sort(key=lambda s: (not s.port, distance(s, game.system)))
    else:
        near.sort(key=lambda s: (s.visited, s.id != bound,
                                 distance(s, game.system)))
    for attempt in range(2):
        for target in near[:4]:
            quote = jump_quote(game, target)
            if game.ship.cargo.get("volatiles", 0) < quote["fuel"]:
                continue
            arrived = jump_to(game, target.id)
            if arrived.get("ok"):
                if arrived.get("encounter") and not game.dead:
                    plan["fights"] = plan.get("fights", [])
                    plan["fights"].append(
                        _fight(game, arrived["encounter"], rng))
                return True
        # Nothing in reach of the tank. Refuel and try the same list again —
        # the first version returned True here, so a broke captain "moved on"
        # a hundred and seventy times and saw six systems in ten years.
        if attempt or not _refuel(game):
            return False
    return False


#: One turn of the chronicle, in the order a captain would take them.
BEATS = (_survey_here, _refit_here, _trade_here, _hire_here, _study_here,
         _mine_here, _dig_here, _build, _land_here, _politics)


def play(game, years: int = 10, on_beat=None, stipend: float = STIPEND) -> dict:
    """Live one chronicle. `on_beat(game, n)` runs after each round.

    `stipend` tops the purse up to a floor each round. It is a patron, and it
    is not pretending otherwise: this driver exists to put a decade of
    accumulated state in front of every screen, and whether a captain can get
    rich unaided is `test_play`'s question, not this one. Left unfunded the
    captain oscillated between 1,200 and 9,200 credits for ten years, never
    held the 15,000 a seed bay costs, and so never planted anything — which
    would have quietly reduced this to a suite that covers half what it says.
    Every *action* below is the real one; only the money is a gift.
    """
    rng = RNG(f"chronicle-{game.seed}")
    plan: dict = {"bound_for": None}
    start = game.day
    rounds = 0
    while game.day - start < years * 365 and not game.dead and not game.victory:
        rounds += 1
        if rounds > 400:
            break
        game.credits = max(game.credits, stipend)
        for beat in BEATS:
            if game.dead or game.victory:
                break
            beat(game, rng, plan)
        if game.system.scanned:
            chart_sim.stamp(game, game.system)
        if on_beat:
            on_beat(game, rounds)
        if game.dead or game.victory:
            break
        if not _move_on(game, rng, plan):
            game.advance_days(30)
    return {"rounds": rounds, "days": game.day - start, "dead": game.dead,
            "fights": list(plan.get("fights", [])),
            "victory": game.victory,
            "charted": len(getattr(game, "charts_made", {})),
            "colonies": len(game.colonies),
            "notes": len(notes_sim.held(game)),
            "contracts": len([c for c in game.contracts if c.done]),
            "treaties": len(dip_sim.ensure(game).treaties)}
