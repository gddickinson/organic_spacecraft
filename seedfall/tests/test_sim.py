"""Simulation checks — the game rules, driven headlessly.

These are the checks that caught six real defects during the port, including a
sector generator that could strand the player on turn one and a combat resolver
that never terminated. Run them with ``python -m seedfall.tests``.
"""

from __future__ import annotations

from ..core import save as save_mod
from ..core.rng import RNG
from ..core.state import Game, has_save, load_game, new_game
from ..data import chassis as chassis_data
from ..data.hull_types import BUILD_NEED, LAYER_SETS, NO_REGEN
from ..data import parts as parts_data
from ..data import tech as tech_data
from ..data.colonies import COLONIES
from ..sim import colony as colony_sim
from ..sim import combat, encounters, shipyard, threat
from ..sim import actions
from ..sim.ship import make_ship, stats
from ..world import economy, galaxy
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    game = {}

    @check("new game")
    def _():
        game["g"] = new_game("smoke-test-seed")
        g = game["g"]
        assert g.galaxy.systems, "no systems"
        assert g.ship_stats is not None, "no derived stats"
        return (f"{len(g.galaxy.systems)} systems, jump {g.ship_stats.jump:.1f} ly, "
                f"hold {g.ship_stats.cargo:g} t")

    @check("determinism")
    def _():
        a = [s.name for s in new_game("same-seed").galaxy.systems]
        b = [s.name for s in new_game("same-seed").galaxy.systems]
        assert a == b, "same seed produced different sectors"
        return "same seed → same sky"

    @check("every chassis builds and derives finite stats")
    def _():
        for c in chassis_data.CHASSIS:
            sh = make_ship(c.id, [])
            st = stats(sh)
            assert st.jump == st.jump and st.accuracy == st.accuracy, f"{c.id} NaN"
            assert sh.layers, f"{c.id} has no layers"
        return f"{len(chassis_data.CHASSIS)} hulls"

    @check("every part fits some hull and costs something")
    def _():
        orphans = []
        for p in parts_data.PARTS:
            homes = [c for c in chassis_data.CHASSIS
                     if c.slots.get(p.slot, 0) > 0
                     and chassis_data.accepts_family(c, p.family)]
            if not homes:
                orphans.append(p.id)
            assert "credits" in p.cost, f"{p.id} has no credit cost"
        assert not orphans, f"parts that fit no hull: {orphans}"
        return f"{len(parts_data.PARTS)} parts"

    @check("tech tree is acyclic, reachable and consistently referenced")
    def _():
        unlocked = list(tech_data.STARTING_TECH)
        for _ in range(200):
            nxt = tech_data.researchable(unlocked)
            if not nxt:
                break
            unlocked += [t.id for t in nxt]
        missing = [t.id for t in tech_data.TECH if t.id not in unlocked]
        assert not missing, f"unreachable techs: {missing}"
        ids = {t.id for t in tech_data.TECH}
        for t in tech_data.TECH:
            for r in t.reqs:
                assert r in ids, f"{t.id} requires missing {r}"
        for c in chassis_data.CHASSIS:
            assert not c.tech or c.tech in ids, f"chassis {c.id} → {c.tech}"
        for p in parts_data.PARTS:
            assert not p.tech or p.tech in ids, f"part {p.id} → {p.tech}"
        for c in COLONIES:
            assert not c.tech or c.tech in ids, f"colony {c.id} → {c.tech}"
        return f"{len(tech_data.TECH)} techs all reachable"

    @check("no sector strands the player at start")
    def _():
        worst, worst_seed = 0.0, ""
        for i in range(40):
            g = galaxy.generate_sector(f"lane-{i}", 42)
            w = galaxy.widest_lane(g.systems)
            if w > worst:
                worst, worst_seed = w, f"lane-{i}"
        assert worst <= 7.0, (f"widest lane {worst:.2f} ly (seed {worst_seed}) "
                              "exceeds a starting jump")
        return f"widest lane across 40 sectors: {worst:.2f} ly"

    @check("time advances without exploding")
    def _():
        g = game["g"]
        d0 = g.day
        g.advance_days(120)
        assert g.day == d0 + 120, "day did not advance"
        assert g.credits == g.credits, "credits went NaN"
        return f"day {g.day}, treasury {round(g.credits)}"

    @check("jump to a reachable system")
    def _():
        g = game["g"]
        here = g.system
        reach = galaxy.in_range(g.galaxy.systems, here, g.ship_stats.jump)
        assert reach, "nothing in jump range from the start system"
        g.ship.cargo["volatiles"] = 120
        res = actions.jump_to(g, reach[0].id)
        assert res["ok"], res.get("why")
        assert g.location_id == reach[0].id, "did not move"
        return f"{len(reach)} systems in range; jumped in {res['days']} d"

    @check("survey and extraction")
    def _():
        g = game["g"]
        r = actions.survey(g, 0)
        assert r["body"].surveyed, "body not marked surveyed"
        e = actions.extract(g, 0, 30)
        assert e["ok"], e.get("why")
        got = ", ".join(e["got"]) or "nothing"
        return f"{len(r['lifeforms'])} organisms; extracted {got}"

    @check("market prices are sane and trade moves them")
    def _():
        g = game["g"]
        port = next((s for s in g.galaxy.systems if s.market), None)
        assert port, "no port anywhere in the sector"
        before = economy.buy_price(port.market, "ore")
        assert before and before > 0, "ore has no price"
        sell = economy.sell_price(port.market, "ore")
        assert sell < before, f"spread inverted: buy {before} sell {sell}"
        economy.apply_trade(port.market, "ore", 400)
        after = economy.buy_price(port.market, "ore")
        assert after > before, "buying did not raise the price"
        return f"ore {before}→{after} after a 400 t buy; spread {before - sell}"

    @check("found a colony and mature it")
    def _():
        g = game["g"]
        g.research.unlocked += ["bioleach", "waterrefinery", "melanin"]
        g.ship.fitted.append("seed_bay")     # grown colonies need a cradle aboard
        g.recompute()
        body = next((b for b in g.system.bodies
                     if b.kind in ("asteroid", "moon", "rocky")), None)
        assert body, "no suitable body here"
        g.credits = 999999
        for k in ("biomass", "ore", "volatiles"):
            g.stores[k] = 999
        col, why = colony_sim.found(g, g.system, body, "radix_mine")
        assert col, why
        g.advance_days(400)
        assert col.online, f"still gestating after 400 d (needs {col.need})"
        assert g.stores["ore"] > 0, "online colony produced no ore"
        return f"online in {col.need} d, depot ore {round(g.stores['ore'])}"

    @check("build a hull end to end")
    def _():
        g = game["g"]
        sysm = next((s for s in g.galaxy.systems
                     if s.port and "gestation" in s.port.services), None)
        sysm = sysm or next(s for s in g.galaxy.systems
                            if s.port and "shipyard" in s.port.services)
        g.location_id = sysm.id
        g.credits = 999999
        for k in ("ore", "biomass", "phosphate", "volatiles", "silicon", "alloy",
                  "magnetite", "spidroin", "trehalose"):
            g.stores[k] = 9999
        before = len(g.fleet)
        job, why = shipyard.start_build(
            g, "spore", ["reaction_organ", "intima_bloom", "opsin_eyes",
                         "bioelectric_net"], sysm, "Test Instar")
        assert job, why
        g.advance_days(400)
        assert len(g.fleet) == before + 1, "hull never completed"
        return f"{len(g.fleet)} hulls in the fleet"

    @check("design validation enforces slots and hull families")
    def _():
        spore = chassis_data.CHASSIS_BY_ID["spore"]
        ok, _errs, _ = shipyard.validate(spore, ["opsin_eyes"] * 3)
        assert not ok, "accepted 3 sensors in 1 slot"
        ok, errs, _ = shipyard.validate(spore, ["opsin_eyes"])
        assert ok, f"rejected a legal design: {errs}"
        pike = chassis_data.CHASSIS_BY_ID["pike"]
        ok, _, _ = shipyard.validate(pike, ["intima_bloom"])
        assert not ok, "grafted an intima onto a Yards hull"
        return "slot limits and family rules enforced"

    @check("every technology family is complete and coherent")
    def _():
        report = []
        for family in chassis_data.FAMILY_ORDER:
            hulls = chassis_data.by_family(family)
            assert hulls, f"{family} has no hulls"
            layers = LAYER_SETS.get(family)
            assert layers, f"{family} has no layer stack"
            total = sum(l.w for l in layers)
            assert abs(total - 1.0) < 1e-6, f"{family} layer weights sum to {total}"
            assert any(l.critical for l in layers), f"{family} has no critical layer"
            assert family in BUILD_NEED, f"{family} has no build requirement"
            assert family in chassis_data.FAMILY_LABEL, f"{family} has no label"
            assert family in chassis_data.FAMILY_TINT, f"{family} has no tint"
            report.append(f"{family}:{len(hulls)}")
        return " ".join(report)

    @check("hull families accept and refuse the right parts")
    def _():
        cases = [
            ("navis", "intima_bloom", True), ("navis", "fusion_lance", False),
            ("navis", "coherent_beam", False),
            ("pike", "railgun", True), ("pike", "intima_bloom", False),
            ("ordinal", "coherent_beam", True), ("ordinal", "railgun", True),
            ("ordinal", "intima_bloom", False),
            ("antiphon", "xeno_lattice", True), ("antiphon", "intima_bloom", False),
            ("palimpsest", "intima_bloom", True), ("palimpsest", "railgun", True),
            ("palimpsest", "coherent_beam", False),
        ]
        for hull, pid, want in cases:
            ch = chassis_data.CHASSIS_BY_ID[hull]
            got = chassis_data.accepts_family(ch, parts_data.PARTS_BY_ID[pid].family)
            assert got is want, f"{hull} + {pid}: expected {want}, got {got}"
        return f"{len(cases)} graft rules hold"

    @check("only the mechanical families refuse to heal")
    def _():
        healing, inert = [], []
        for c in chassis_data.CHASSIS:
            st = stats(make_ship(c.id, []))
            (inert if st.regen == 0 else healing).append(c.family)
        assert set(inert) <= NO_REGEN, f"unexpected non-healing family: {set(inert)}"
        assert not (set(healing) & NO_REGEN), f"{set(healing) & NO_REGEN} healed"
        return f"{len(inert)} inert hulls, {len(healing)} that mend"

    @check("every station class is plantable and its effects are understood")
    def _():
        known_effects = {"gestation", "build_here", "sensor", "watch", "drift",
                         "diplomacy", "medical", "vault", "megastructure",
                         "fabricate", "ward", "port", "xenoyard", "drydock"}
        kinds = {"asteroid", "comet", "rocky", "ocean", "gas", "moon", "ice", "star"}
        for c in COLONIES:
            assert c.sites, f"{c.id} can be planted nowhere"
            bad_sites = set(c.sites) - kinds
            assert not bad_sites, f"{c.id} lists unknown site {bad_sites}"
            bad_fx = set(c.effects) - known_effects
            assert not bad_fx, f"{c.id} has unhandled effect {bad_fx}"
            assert c.family in chassis_data.FAMILY_LABEL, f"{c.id} odd family"
        fams = {c.family for c in COLONIES}
        return f"{len(COLONIES)} classes across {len(fams)} technologies"

    @check("a Free Port opens a market where there was none")
    def _():
        g = new_game("harbour-seed")
        g.research.unlocked.append("oect")
        g.ship.fitted.append("seed_bay")
        g.credits = 999999
        for k in ("alloy", "biomass", "ore"):
            g.stores[k] = 999
        g.recompute()
        target = next(s for s in g.galaxy.systems if s.port is None and s.bloom < 0.1)
        g.location_id = target.id
        col, why = colony_sim.found(g, target, target.bodies[0], "free_port")
        assert col, why
        assert target.port is None, "harbour opened before the station matured"
        g.advance_days(col.need + 5)
        assert target.port is not None, "matured Free Port opened no harbour"
        assert target.market is not None, "harbour has no market"
        assert target.port.player_built, "harbour not marked as yours"
        price = economy.buy_price(target.market, "ore")
        assert price and price > 0, "market carries no prices"
        return f"{target.name} now trades ore at {price}"

    @check("a Monitor Station holds the Bloom off")
    def _():
        # Averaged over trials: a single unlucky roll should not decide whether
        # a game mechanic is judged to work.
        def mean_bloom(warded: bool, years: int, trials: int = 8) -> float:
            total = 0.0
            for t in range(trials):
                g = new_game(f"ward-{t}")
                # A partially-infested system, not the origin: that one is
                # already pinned at 1.0, where a ward has nothing to hold back.
                hot = next((s for s in g.galaxy.systems if 0.1 < s.bloom < 0.6), None)
                if hot is None:
                    continue
                if warded:
                    g.colonies.append(colony_sim.Colony(
                        id=900 + t, class_id="monitor_station", name="watch",
                        system_id=hot.id, body_id=hot.bodies[0].id, need=1,
                        days=1, online=True))
                threat.tick(g, 365 * years, RNG(f"ward-run-{t}"))
                total += hot.bloom
            return total / trials

        bare, guarded = mean_bloom(False, 2), mean_bloom(True, 2)
        assert guarded < bare - 0.05, (
            f"ward barely mattered: {bare:.2f} unwatched vs {guarded:.2f} watched")
        return f"2 years: {bare:.2f} unwatched → {guarded:.2f} watched (8 trials each)"

    @check("combat always terminates and spans real outcomes")
    def _():
        results: dict[str, int] = {}
        turn_sum = 0
        loadouts = [
            ["slug_battery", "lixiviant", "regrowth_surge", "intima_bloom",
             "chemo_gut", "reaction_organ", "opsin_eyes", "silicon_core",
             "radiator_bloom"],
            ["fusion_lance", "railgun", "ablative_plate", "fission_pile",
             "fusion_plant", "plasma_drive", "phased_array", "ai_core",
             "droplet_rad"],
            ["photic_flash", "sphincter_seal", "carapace", "intima_bloom",
             "chemo_gut", "reaction_organ", "opsin_eyes", "silicon_core",
             "radiator_bloom"],
        ]
        for i in range(90):
            r = RNG(f"combat-{i}")
            hull = ["navis", "pike", "palimpsest"][i % 3]
            ch = chassis_data.CHASSIS_BY_ID[hull]
            fit = [p for p in loadouts[i % 3]
                   if ch.slots.get(parts_data.PARTS_BY_ID[p].slot, 0) > 0
                   and chassis_data.accepts_family(ch, parts_data.PARTS_BY_ID[p].family)]
            player = make_ship(hull, fit)
            player.cargo = {"ore": 300, "biomass": 200, "alloy": 300}
            faction = ["freeholds", "concordat", "bloom"][i % 3]
            enemy = encounters.make_enemy(r, faction, (i % 4) + 0.5)
            b = combat.start(player, stats(player), enemy)
            guard = 0
            while not b.over and guard < 300:
                guard += 1
                act = {"type": "salvo"} if b.player.st.weapons else {"type": "brace"}
                combat.take_turn(b, act, r)
            assert b.over, f"combat never terminated ({hull} vs {faction})"
            results[b.result] = results.get(b.result, 0) + 1
            turn_sum += b.turn
        assert "destroyed" in results, f"never won by destroying the enemy: {results}"
        assert results.get("stalemate", 0) <= 12, f"too many stalemates: {results}"
        summary = " ".join(f"{k}:{v}" for k, v in results.items())
        return f"{summary} · mean {turn_sum / 90:.1f} turns"

    @check("an overmatched hull actually dies")
    def _():
        results: dict[str, int] = {}
        for i in range(40):
            r = RNG(f"overmatch-{i}")
            player = make_ship("spore", ["reaction_organ", "intima_bloom",
                                         "opsin_eyes", "bioelectric_net"])
            enemy = encounters.make_enemy(r, "concordat", 4)
            b = combat.start(player, stats(player), enemy)
            guard = 0
            while not b.over and guard < 300:
                guard += 1
                combat.take_turn(b, {"type": "brace"}, r)
            results[b.result] = results.get(b.result, 0) + 1
        assert "lost" in results, f"a 60 t pod never died to a battleship: {results}"
        return " ".join(f"{k}:{v}" for k, v in results.items())

    @check("a weaponless hull can still win by endurance")
    def _():
        results: dict[str, int] = {}
        for i in range(40):
            r = RNG(f"pacifist-{i}")
            player = make_ship("testudo", ["carapace", "regrowth_surge",
                                           "sphincter_seal", "melanin_ward",
                                           "intima_bloom", "chemo_gut",
                                           "reaction_organ", "radiator_bloom"])
            st = stats(player)
            assert not st.weapons, "TESTUDO loadout unexpectedly armed"
            enemy = encounters.make_enemy(r, "freeholds", 1)
            b = combat.start(player, st, enemy)
            guard = 0
            while not b.over and guard < 300:
                guard += 1
                combat.take_turn(b, {"type": "brace"}, r)
            results[b.result] = results.get(b.result, 0) + 1
        assert "stalemate" not in results, f"combat failed to terminate: {results}"
        assert results.get("driven-off"), f"endurance never won: {results}"
        return " ".join(f"{k}:{v}" for k, v in results.items())

    @check("bloom grows and can be burned back")
    def _():
        g = game["g"]
        r = RNG("bloom")
        before = threat.bloom_burden(g)
        threat.tick(g, 365, r)
        after = threat.bloom_burden(g)
        assert after > before, f"bloom did not grow: {before} → {after}"
        worst = next((s for s in g.galaxy.systems if s.bloom > 0.2), None)
        assert worst, "no infested system to test cleansing"
        g.location_id = worst.id
        g.ship = make_ship("navis", ["fusion_lance", "fusion_lance", "fusion_plant",
                                     "fusion_plant", "reaction_organ", "opsin_eyes",
                                     "silicon_core"])
        g.fleet.append(g.ship)
        g.recompute()
        res, why = threat.cleanse(g, worst, r)
        assert res, why
        return (f"burden {before:.2f}→{after:.2f}; "
                f"cleanse cut {res['cut'] * 100:.0f}%")

    @check("victory conditions are all evaluable")
    def _():
        p = threat.victory_progress(game["g"])
        for k in ("containment", "exodus", "concord", "genesis", "dominion"):
            assert k in p and isinstance(p[k][2], bool), f"{k} not evaluable"
        return ", ".join(f"{k} {int(v[0])}/{int(v[1])}" for k, v in p.items())

    @check("save round-trips and keeps ship identity")
    def _():
        import tempfile
        from pathlib import Path
        g = game["g"]
        path = Path(tempfile.mkdtemp()) / "save.json"
        day, cr, name = g.day, g.credits, g.ship.name
        assert save_mod.write(g.to_save(), path), "save returned False"
        data = save_mod.read(path)
        assert data, "load returned nothing"
        g2 = data["game"]
        for i, f in enumerate(g2.fleet):
            if f.uid == g2.ship.uid:
                g2.fleet[i] = g2.ship
                break
        g2.recompute()
        assert g2.day == day and round(g2.credits) == round(cr), "state lost"
        assert g2.ship.name == name, "ship lost"
        same = any(f is g2.ship for f in g2.fleet)
        assert same, "active ship is a copy, not the fleet entry"
        return f"day {g2.day} restored, {len(g2.galaxy.systems)} systems, identity kept"

    @check("bloom pressure is paced, not instant")
    def _():
        fractions = []
        for seed in ("pace-a", "pace-b", "pace-c"):
            g = new_game(seed)
            total = len(g.galaxy.systems)
            g.advance_days(365 * 5)
            fractions.append(len([s for s in g.galaxy.systems if s.bloom > 0.02]) / total)
        mean = sum(fractions) / len(fractions)
        assert mean <= 0.75, f"after 5 idle years {mean:.0%} infested — too fast"
        assert mean >= 0.10, f"after 5 idle years only {mean:.0%} infested — no pressure"
        return f"{mean:.0%} of the sector infested after 5 idle years"

    @check("a long unattended run stays finite")
    def _():
        g = new_game("endurance")
        for _ in range(20):
            g.advance_days(180)
        assert g.credits == g.credits, "credits went NaN"
        assert 0 <= g.ship.morale <= 1, "morale left its range"
        infested = len([s for s in g.galaxy.systems if s.bloom > 0.02])
        return f"{g.day} days simulated, {infested} systems infested"
