"""Playability checks — can a chronicle actually be finished, and can it jam?

These are the checks that would have caught the two defects the first playability
audit turned up: an Exodus ending that could never fire because nothing set its
flag, and a captain who could strand with ore in the hold, no fuel, and no way to
convert one into the other.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.lore import VICTORIES
from ..data.tech import TECH
from ..sim import actions
from ..sim import colony as colony_sim
from ..sim import threat
from ..sim.ship import add_cargo, build_layers, make_ship
from ..world.economy import sell_price
from ..world.galaxy import in_range
from .harness import Suite


def _stocked(seed="play"):
    g = new_game(seed)
    g.research.unlocked = [t.id for t in TECH]
    g.credits = 10_000_000
    for k in ("ore", "volatiles", "phosphate", "biomass", "silicon", "alloy",
              "magnetite", "spidroin", "trehalose", "xenolith"):
        g.stores[k] = 99999
    g.recompute()
    return g


def run(suite: Suite) -> None:
    check = suite.check

    @check("every ending can actually fire")
    def _():
        fired = {}

        g = _stocked()
        for s in g.galaxy.systems:
            s.bloom = 0.0
        g.day = 60
        fired["containment"] = threat.check_victory(g)

        # Exodus must be reachable through the action a player can take, not by
        # forcing the flag — nothing set it for the first three builds.
        g = _stocked()
        ark = make_ship("leviathan", [], "Ark")
        build_layers(ark, g.bonuses)
        g.fleet.append(ark)
        g.recompute()
        assert threat.check_victory(g) is None, "exodus fired without launching"
        res = actions.launch_exodus(g)
        assert res["ok"], res.get("why")
        fired["exodus"] = threat.check_victory(g)

        g = _stocked()
        for f in ("charter", "concordat", "freeholds", "sanhedrin"):
            g.rep[f] = 75
        fired["concord"] = threat.check_victory(g)

        g = _stocked()
        g.flags["contact_made"] = True
        fired["genesis"] = threat.check_victory(g)

        g = _stocked()
        sysm = g.galaxy.systems[0]
        for i in range(12):
            g.colonies.append(colony_sim.Colony(
                id=i, class_id="arca_drum" if i == 0 else "lichen_dome",
                name=f"c{i}", system_id=sysm.id, body_id="0", need=1, days=1,
                online=True, pop=1_000_000 if i == 0 else 10_000))
        fired["dominion"] = threat.check_victory(g)

        for vid, *_ in VICTORIES:
            assert fired.get(vid) == vid, (
                f"{vid} did not fire when its conditions were met "
                f"(got {fired.get(vid)!r})")
        return f"all {len(VICTORIES)} endings reachable"

    @check("a launched ark cannot be launched from nothing")
    def _():
        g = new_game("no-ark")
        res = actions.launch_exodus(g)
        assert not res["ok"], "launched an Exodus with no LEVIATHAN"
        assert not g.flags.get("exodus_launched"), "flag set anyway"
        return "refused, as it should be"

    @check("a broke and empty captain is never truly stuck")
    def _():
        jams = []
        for i in range(12):
            g = new_game(f"jam-{i}")
            g.credits = 0
            g.ship.cargo = {}
            g.recompute()
            reach = in_range(g.galaxy.systems, g.system, g.ship_stats.jump)
            if not reach:
                jams.append((g.seed, "nowhere in range at all"))
                continue
            # Either we can make fuel here, or somebody will tow us.
            ice = any(b.resources.get("volatiles", 0) > 0.05
                      for b in g.system.bodies)
            can_make = g.ship_stats.drink > 0 and ice
            tow = actions.distress_call(g) if actions.is_stranded(g) else None
            rescued = bool(tow and tow.get("ok"))
            if not (can_make or rescued or not actions.is_stranded(g)):
                jams.append((g.seed, "no fuel, no ice, no tow"))
        assert not jams, f"deadlocked chronicles: {jams}"
        return "12 destitute starts, every one recoverable"

    @check("the mining root can crack ice for fuel")
    def _():
        g = new_game("ice")
        assert g.ship_stats.drink > 0, (
            "the starting loadout cannot produce reaction mass from ice, so ore "
            "in the hold can never become fuel away from a port")
        body = next((i for i, b in enumerate(g.system.bodies)
                     if b.resources.get("volatiles", 0) > 0.2), None)
        assert body is not None, "no ice in the starting system to test against"
        g.system.bodies[body].surveyed = True
        g.ship.cargo = {}
        res = actions.extract(g, body, 60)
        assert res["ok"], res.get("why")
        got = res["got"].get("volatiles", 0)
        assert got > 0, f"60 days on an ice body yielded no volatiles: {res['got']}"
        return f"60 days on ice → {got:.0f} t of reaction mass"

    @check("a landing party can get down, work a site and come home")
    def _():
        from ..sim import expedition as exp_sim
        from ..sim import fieldwork
        outcomes: dict[str, int] = {}
        value = 0.0
        for i in range(10):
            g = new_game(f"land-{i}")
            body = next((j for j, b in enumerate(g.system.bodies)
                         if b.kind in ("rocky", "moon", "asteroid", "ice",
                                       "comet", "ocean")), None)
            if body is None:
                continue
            g.system.bodies[body].surveyed = True
            g.ship.cargo["biomass"] = 60
            r = fieldwork.launch_expedition(g, body, [o.id for o in g.officers], 1)
            assert r["ok"], r.get("why")
            exp = g.expedition
            rng = RNG(f"party-{i}")
            guard = 0
            while not exp.over and guard < 150:
                guard += 1
                if exp_sim.options_here(exp):
                    exp_sim.attempt(exp, 0, g.officers, rng)
                    continue
                home = abs(exp.x - exp_sim.LANDER[0]) + abs(exp.y - exp_sim.LANDER[1])
                if exp.supply <= home + 3 and not exp.at_lander:
                    dx = (exp_sim.LANDER[0] > exp.x) - (exp_sim.LANDER[0] < exp.x)
                    dy = 0 if dx else (exp_sim.LANDER[1] > exp.y) - (exp_sim.LANDER[1] < exp.y)
                    exp_sim.move(exp, dx, dy, g.officers, rng)
                    continue
                if exp.at_lander and exp.supply <= 4:
                    exp_sim.lift_off(exp)
                    break
                for dx, dy in ((0, -1), (1, 0), (-1, 0), (0, 1)):
                    t = exp.tile(exp.x + dx, exp.y + dy)
                    if t and not t.visited:
                        exp_sim.move(exp, dx, dy, g.officers, rng)
                        break
                else:
                    exp_sim.move(exp, *rng.pick([(0, -1), (1, 0), (-1, 0), (0, 1)]),
                                 g.officers, rng)
            assert guard < 150, "expedition never terminated"
            if not exp.over:
                exp_sim.finish(exp, "aborted")
            res = fieldwork.conclude_expedition(g)
            assert res["ok"], res.get("why")
            assert g.expedition is None, "expedition not cleared after recovery"
            outcomes[res["outcome"]] = outcomes.get(res["outcome"], 0) + 1
            value += sum(res["stowed"].values())
        stranded = outcomes.get("stranded", 0)
        assert stranded <= 4, (
            f"most expeditions strand — the supply budget is punishing: {outcomes}")
        assert value > 0, "ten expeditions brought back nothing at all"
        return (f"{outcomes}, mean value {value / 10:.0f}")

    @check("contracts generate, complete and expire")
    def _():
        from ..sim import contracts as contract_sim
        g = _stocked("contract-test")
        port = next(s for s in g.galaxy.systems if s.port)
        g.location_id = port.id
        board = contract_sim.generate(g.rng("board"), g, port)
        assert board, "a port posted nothing at all"
        kinds = {c.kind for c in board}
        for c in board:
            assert c.reward > 0, f"{c.kind} pays nothing"
            assert c.deadline > g.day, f"{c.kind} is already expired"
            assert c.title, f"{c.kind} has no title"

        # a prospecting contract completes when the goods are presented
        pros = next((c for c in board if c.kind == "prospect"), None)
        if pros is None:
            pros = next(c for c in contract_sim.generate(g.rng("b2"), g, port)
                        if c.kind == "prospect")
        contract_sim.accept(g, pros)
        g.stores[pros.commodity] = pros.amount + 10
        before = g.credits
        g.advance_days(1)
        assert pros.done, "delivered the goods and the contract did not close"
        assert g.credits > before, "a completed contract paid nothing"

        # and one left too long fails
        g2 = _stocked("expiry")
        port2 = next(s for s in g2.galaxy.systems if s.port)
        g2.location_id = port2.id
        late = contract_sim.generate(g2.rng("b3"), g2, port2)[0]
        contract_sim.accept(g2, late)
        rep_before = g2.rep[late.issuer]
        g2.advance_days(late.deadline - g2.day + 5)
        assert late.failed, "an overdue contract never expired"
        assert g2.rep[late.issuer] < rep_before, "failing one cost no standing"
        return f"{len(board)} posted across {len(kinds)} kinds; pay and expiry both work"

    @check("the helm moves the ship and never traps it")
    def _():
        from ..sim import flight
        g = new_game("helm-test")
        assert g.orbit_body is None, "a jump should arrive at the system edge"
        body = g.system.bodies[0]
        opts = flight.options(g, body)
        assert len(opts) == len(flight.BURNS), "burn profiles missing"
        assert any(o["fuel"] == 0 for o in opts), (
            "no free profile — a captain with an empty tank could not reach the "
            "ice that would refill it")
        fast = next(o for o in opts if o["burn"].id == "hard")
        slow = next(o for o in opts if o["burn"].id == "coast")
        assert fast["days"] < slow["days"] and fast["fuel"] > slow["fuel"], (
            "burn profiles do not trade time against reaction mass")

        g.ship.cargo["volatiles"] = 200
        before = g.day
        res = flight.travel_to(g, 0, "standard")
        assert res["ok"], res.get("why")
        assert g.orbit_body == body.id, "the burn did not arrive"
        assert g.day > before, "the transfer took no time"

        # empty tank still gets there
        g2 = new_game("helm-dry")
        g2.ship.cargo = {}
        r = flight.ensure_at(g2, 0)
        assert r["ok"] and r["fuel"] == 0, "an empty ship cannot reach a body"

        # bodies actually move
        moved = abs(flight.separation(g.system.bodies[0], g.system.bodies[-1], 0)
                    - flight.separation(g.system.bodies[0], g.system.bodies[-1], 900))
        return (f"{len(opts)} profiles; orbits shift {moved:.2f} AU over 900 days")

    @check("the mini-games are winnable and terminate")
    def _():
        from ..sim import minigames as mg
        g = new_game("mini")

        # Docking: play greedily toward zero and it should close.
        wins = 0
        for i in range(20):
            d = mg.start_docking(RNG(f"dock-{i}"), "Test Port",
                                 g.ship_stats, g.officers)
            guard = 0
            while not d.over and guard < 40:
                guard += 1
                axis = max(d.error, key=lambda a: abs(d.error[a]))
                step = max(1, min(abs(d.error[axis]), d.precision * 4))
                mg.correct(d, axis, step if d.error[axis] > 0 else -step,
                           RNG(f"t-{i}-{guard}"))
            assert d.over, "a docking approach never resolved"
            wins += 1 if d.won else 0
        assert wins > 0, "docking is unwinnable even played perfectly"

        # Decoding: brute force must find it, and scoring must be sane.
        solved = 0
        for i in range(10):
            d = mg.start_decoding(RNG(f"dec-{i}"), "Test", g.ship_stats, g.officers)
            assert mg.score(d.secret, d.secret) == (mg.CODE_LENGTH, 0), \
                "a perfect guess does not score as perfect"
            guard = 0
            while not d.over and guard < 40:
                guard += 1
                mg.guess(d, [(guard + k) % d.palette for k in range(mg.CODE_LENGTH)])
            assert d.over, "a decoding bench never resolved"
            solved += 1 if d.won else 0
        return f"docking won {wins}/20 played well; decoding terminated 10/10"

    @check("a plain trading run stays solvent for five years")
    def _():
        results = []
        for seed in ("run-a", "run-b", "run-c", "run-d"):
            g = _bot(seed, years=5)
            results.append(g)
        broke = [g for g in results if g.credits < 0]
        dead = [g for g in results if g.dead]
        assert not broke, f"{len(broke)} runs ended in debt"
        assert not dead, f"{len(dead)} runs died surveying empty systems"
        mean = sum(g.credits for g in results) / len(results)
        return (f"{len(results)} runs, none dead or in debt, "
                f"mean treasury {round(mean):,}")


def _bot(seed: str, years: int = 5):
    """A deliberately simple captain: survey, sell the data, refuel, move on.

    If this cannot stay solvent, the early game is not playable.
    """
    g = new_game(seed)
    r = RNG(f"bot-{seed}")
    while g.day < 365 * years and not g.dead and not g.victory:
        sysm = g.system
        todo = [i for i, b in enumerate(sysm.bodies) if not b.surveyed]
        if todo:
            actions.survey(g, todo[0])
            continue

        if sysm.port and sysm.market:
            rep = g.rep.get(sysm.port.faction, 0)
            data = g.ship.cargo.get("survey", 0)
            if data >= 1:
                price = sell_price(sysm.market, "survey", rep, g.ship_stats.trade) or 250
                g.credits += data * price
                add_cargo(g.ship, "survey", -data)
                g.adjust_rep(sysm.port.faction, min(6, data * 0.4))
            fuel_price = (sell_price(sysm.market, "volatiles", rep, 0) or 40) * 1.35
            want = 70 - g.ship.cargo.get("volatiles", 0)
            afford = int(min(want, g.credits * 0.6 // max(1, fuel_price)))
            if afford > 0:
                g.credits -= afford * fuel_price
                add_cargo(g.ship, "volatiles", afford)

        reach = in_range(g.galaxy.systems, sysm, g.ship_stats.jump)
        reach = [s for s in reach if s.bloom < 0.3] or reach
        if not reach:
            break
        affordable = [s for s in reach
                      if g.ship.cargo.get("volatiles", 0)
                      >= actions.jump_quote(g, s)["fuel"]]
        if not affordable:
            # top up from ice rather than sitting there
            ice = next((i for i, b in enumerate(sysm.bodies)
                        if b.resources.get("volatiles", 0) > 0.1), None)
            if ice is None:
                break
            sysm.bodies[ice].surveyed = True
            actions.extract(g, ice, 40)
            continue
        target = next((s for s in affordable if not s.visited), r.pick(affordable))
        if not actions.jump_to(g, target.id)["ok"]:
            break
    return g
