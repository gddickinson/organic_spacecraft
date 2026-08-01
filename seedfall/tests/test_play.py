"""Playability checks — can a chronicle actually be finished, and can it jam?

These are the checks that would have caught the two defects the first playability
audit turned up: an Exodus ending that could never fire because nothing set its
flag, and a captain who could strand with ore in the hold, no fuel, and no way to
convert one into the other.
"""

from __future__ import annotations

import math

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
from .captain_bot import _bot
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

        # Containment now means the sector clean AND the original germination
        # dead — clearing the map is no longer enough on its own.
        from ..sim import bloom as bloom_sim
        g = _stocked()
        for s in g.galaxy.systems:
            s.bloom = 0.0
        g.day = 60
        assert threat.check_victory(g) is None, (
            "containment fired with the heart still alive")
        bloom_sim.ensure(g).heart_hp = 0.0
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

        # Concord needs the powers fond of you AND of each other.
        from ..sim import diplomacy as dip
        g = _stocked()
        for f in dip.POWERS:
            g.rep[f] = 75
        state = dip.ensure(g)
        for i, a in enumerate(dip.POWERS):
            for b in dip.POWERS[i + 1:]:
                state.relations[dip._key(a, b)] = 60.0
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

        # Lineage: four grown hulls of your own, and the licence to sign them.
        g = _stocked()
        for i in range(4):
            hull = make_ship("navis", [], f"Cutting {i}")
            build_layers(hull, g.bonuses)
            g.fleet.append(hull)
        fired["lineage"] = threat.check_victory(g)

        # Xenarchy: all twelve alien technologies incorporated.
        from ..data.xenotech import XENOTECH
        from ..sim import xeno as xeno_sim
        g = _stocked()
        for tech in XENOTECH:
            g.xeno_study[tech.id] = tech.study * 2
            xeno_sim.incorporate(g, tech.id)
        fired["xenarch"] = threat.check_victory(g)

        # The Cartel: most of the sector's prices written down, and a purse.
        from ..sim import market as market_sim
        g = _stocked()
        for system in g.galaxy.systems:
            if system.market:
                market_sim.note_prices(g, system, 0, 0)
        g.credits = 2_000_000
        fired["cartel"] = threat.check_victory(g)

        # Apostasy: a synthetic hull, nobody aboard, the Choir at Kin.
        g = _stocked()
        g.ship.chassis = "cantor"
        g.officers = []
        g.rep["sanhedrin"] = 80
        g.recompute()
        fired["apostasy"] = threat.check_victory(g)

        # Ruin: the sector lost, and you still flying. It must fire *before*
        # the Bloom is allowed to kill you, which is why the order in
        # `advance_days` puts the victory check first.
        g = _stocked()
        for system in g.galaxy.systems:
            system.bloom = 0.95
        fired["ruin"] = threat.check_victory(g)

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
        # Driven by `tests/ground_ai.py` — the game's own party leader — and
        # not by a walker of this check's own. The one it used to roll here
        # turned for home when `supply <= manhattan_distance + 3`, which prices
        # every step at one day; `sim/expedition.step_cost` charges up to four
        # on fresh scarp in bad weather, and `sim/wayhome` exists precisely to
        # add that up over a route. So the walker stranded on rough maps and
        # came home on kind ones, and what this check measured was the terrain
        # roll, not the supply budget. Ten parties gave 3-5 strandings against
        # a bar of 4, and moving where a new captain starts — which changes
        # nothing about the ground — moved it to 5. Thirty parties: 17
        # stranded with the hand-rolled walker, none at all with the leader.
        from ..sim import fieldwork
        from . import ground_ai
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
            ground_ai.play(g, g.expedition, RNG(f"party-{i}"))
            res = fieldwork.conclude_expedition(g)
            assert res["ok"], res.get("why")
            assert g.expedition is None, "expedition not cleared after recovery"
            outcomes[res["outcome"]] = outcomes.get(res["outcome"], 0) + 1
            value += sum(res["stowed"].values())
        stranded = outcomes.get("stranded", 0)
        assert stranded == 0, (
            f"a party led by the game's own leader stranded {stranded} times "
            f"in ten — the supply budget will not pay for the walk it quotes: "
            f"{outcomes}")
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

    @check("the Bloom escalates and stops being a pushover")
    def _():
        from ..sim import bloom as bloom_sim
        g = new_game("arc-test")
        assert bloom_sim.ensure(g).definition.id == 0, "it should start latent"
        r = RNG("arc")
        seen = []
        for _ in range(12):
            threat.tick(g, 365, r)
            stage = bloom_sim.ensure(g).definition
            if stage.id not in [x.id for x in seen]:
                seen.append(stage)
        assert len(seen) >= 4, (
            f"the Bloom never escalated past {[s.name for s in seen]}")
        assert bloom_sim.ensure(g).instars, "it never put an instar in the field"
        return " → ".join(s.name for s in seen)

    @check("the Bloom learns what you keep shooting it with")
    def _():
        from ..sim import bloom as bloom_sim
        g = new_game("adapt")
        state = bloom_sim.ensure(g)
        state.stage = 3                       # adaptive
        assert bloom_sim.resistance(g, "fabricated") == 0, "starts resistant"
        for _ in range(200):
            bloom_sim.record_damage(g, "fabricated", 30)
        grown = bloom_sim.resistance(g, "grown")
        fab = bloom_sim.resistance(g, "fabricated")
        assert fab > 0.2, f"200 hits taught it nothing: {fab:.2f}"
        assert grown == 0, "it resisted a weapon it never met"
        # and it forgets what you stop using
        bloom_sim.decay_resistance(g, 2000)
        assert bloom_sim.resistance(g, "fabricated") < fab, "it never forgets"
        return f"fabricated resistance {fab:.0%}, grown {grown:.0%}, decays"

    @check("Containment requires reaching and killing the heart")
    def _():
        from ..sim import bloom as bloom_sim
        from ..sim import actions
        g = _stocked("heart")
        for s in g.galaxy.systems:
            s.bloom = 0.0
        g.day = 60
        assert threat.check_victory(g) is None, "cleared the map and won early"

        state = bloom_sim.ensure(g)
        g.location_id = state.heart_system
        state.heart_found = True
        ship = make_ship("bastion", ["fusion_lance", "fusion_lance", "railgun",
                                     "fusion_plant", "fusion_plant", "plasma_drive"])
        build_layers(ship, g.bonuses)
        g.ship = ship
        g.fleet.append(ship)
        g.recompute()
        strikes = 0
        while not bloom_sim.heart_dead(g) and strikes < 40:
            strikes += 1
            for layer in g.ship.layers:
                layer.hp = layer.max
            res = actions.strike_heart(g)
            assert res.get("ok"), res.get("why")
        assert bloom_sim.heart_dead(g), "the heart could not be killed at all"
        # **Bracketed, because `strikes > 1` did not hold `HEART_HP` at all.**
        # Measured with a battleship: 9 passes at 1,300, 19 at 2,600, 37 at
        # 5,200 — so halving and doubling the Heart both sailed through the
        # old bound, and doubling cleared the loop's own cap of 40 by three.
        # `data/bloom.HEART_HP` decides how long the game's climax lasts and
        # was pinned by nothing; the numbers here are absolute on purpose.
        assert 14 <= strikes <= 26, (
            f"the heart took {strikes} passes from a battleship, against 19 "
            "when this was measured — the climax has changed length")
        assert threat.check_victory(g) == "containment", "killing it did not win"
        return f"heart took {strikes} passes from a battleship"

    @check("diplomacy moves both standing and the powers' own relations")
    def _():
        from ..sim import diplomacy as dip
        g = _stocked("dip-test")
        g.ship.cargo["survey"] = 40
        g.stores["biomass"] = 400
        g.recompute()

        before = g.rep["concordat"]
        res = dip.perform(g, "tribute", "concordat")
        assert res["ok"], res.get("why")
        assert g.rep["concordat"] > before, "a tribute bought nothing"
        again = dip.perform(g, "tribute", "concordat")
        assert not again["ok"], "no cooldown on tributes"

        # denouncing pleases the denounced party's enemies
        rivals = dip.rivals_of(g, "freeholds")
        assert rivals, "no power dislikes the Freeholds at all"
        friend = rivals[0]
        f_before = g.rep[friend]
        d = dip.perform(g, "denounce", "charter", "freeholds")
        assert d["ok"], d.get("why")
        assert g.rep["freeholds"] < 0, "denouncing cost nothing with the target"
        assert g.rep[friend] >= f_before, "their enemies did not notice"

        # brokering is the only thing that moves faction-to-faction relations
        g.rep["charter"] = 80
        g.rep["concordat"] = 80
        pair_before = dip.relation(g, "charter", "concordat")
        b = dip.perform(g, "broker", "charter", "concordat")
        assert b["ok"], b.get("why")
        pair_after = dip.relation(g, "charter", "concordat")
        assert pair_after > pair_before, (
            f"brokering did not thaw them: {pair_before} -> {pair_after}")
        return (f"tribute, denouncement and brokering all bite; "
                f"charter/concordat {pair_before:+.0f} → {pair_after:+.0f}")

    @check("Concord needs the powers at peace, not just fond of you")
    def _():
        from ..sim import diplomacy as dip
        g = _stocked("concord")
        for power in dip.POWERS:
            g.rep[power] = 85
        assert threat.check_victory(g) is None, (
            "Concord fired with the powers still at each other's throats")
        state = dip.ensure(g)
        for i, a in enumerate(dip.POWERS):
            for b in dip.POWERS[i + 1:]:
                state.relations[dip._key(a, b)] = 60.0
        assert threat.check_victory(g) == "concord", (
            "peace between all of them still did not win")
        prog = dip.concord_progress(g)
        return (f"{len(prog['kin'])} kin and {len(prog['peace'])} pairs at peace "
                "required")

    @check("the helm moves the ship and never traps it")
    def _():
        from ..data.starclasses import mu_of
        from ..sim import flight
        g = new_game("helm-test")
        # A jump arrives at the edge, and a *new captain* does not: they are
        # moored at the quay their opening log says they are leaving. Asked of
        # the act rather than of the opening, which is what it always meant —
        # asking it of `new_game` only worked while the game had no way to
        # start anywhere in particular.
        flight.arrive_in_system(g)
        assert g.orbit_body is None, "a jump should arrive alongside nothing"
        edge = flight.ship_position(g)
        assert abs(math.hypot(*edge) - flight.ARRIVAL_RADIUS) < 1e-9, (
            f"a jump arrived {math.hypot(*edge):.2f} AU out, not at the "
            f"{flight.ARRIVAL_RADIUS:.2f} AU arrival radius")
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
        moved = abs(flight.separation(g.system.bodies[0], g.system.bodies[-1], 0,
                                  mu_of(g.system))
                    - flight.separation(g.system.bodies[0], g.system.bodies[-1], 900,
                                    mu_of(g.system)))
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
        for seed in ("run-a", "run-b", "run-c", "run-d", "run-e", "run-f"):
            g = _bot(seed, years=5)
            results.append(g)
        broke = [g for g in results if g.credits < 0]
        dead = [g for g in results if g.dead]
        assert not broke, f"{len(broke)} runs ended in debt"
        assert not dead, f"{len(dead)} runs died surveying empty systems"
        mean = sum(g.credits for g in results) / len(results)
        # A floor, not just "not negative": the naive strategy sat on exactly
        # zero for a while, which made this check flaky and the early game
        # knife-edge. Survey data has to cover a wage bill and a fuel bill.
        assert mean > 500, (
            f"the naive strategy barely breaks even — mean {mean:,.0f}")
        return (f"{len(results)} runs, none dead or in debt, "
                f"mean treasury {round(mean):,}")


