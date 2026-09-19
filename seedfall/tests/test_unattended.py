"""Machines with nobody to supervise them: nobody alive, nobody fed, nobody
awake, nobody within a light-year.

Split out of `tests/test_robots.py` when it reached 624 lines. The seam is
the one the design turns on: that file holds the ladder and the price of a
machine standing next to its captain; this one holds what a machine is worth
when the captain is dead, starving, asleep or a system away. Two death paths
asked only whether any *person* was left, and a hull the Dry Choir would call
fully crewed was reported as abandoned — so these checks sit together.
"""

from __future__ import annotations

from ..sim import robots as robots_sim, telepresence as tele_sim
from .harness import Suite
from .test_robots import _holding, _yard


def run(suite: Suite) -> None:
    check = suite.check

    @check("machines can hold a hull that has nobody alive on it")
    def _():
        # The defect: two death paths — the air running out in `core/clock`
        # and the stores running out in `sim/upkeep` — asked only whether any
        # *person* was left. Measured with three machines standing
        # engineering, science and comms and the ship's own stats reading
        # regen 1.71 and research 1.38 off them: both lines fired. A hull the
        # Dry Choir would call fully crewed was reported as abandoned.
        def last_breath(seed, machines):
            game = _yard(seed)
            for class_id in machines:
                robots_sim.build(game, class_id)
            game.officers.clear()
            game.ship.crew = 2
            game.ship.o2 = 0.02
            for layer in game.ship.layers:
                layer.hp = 0.0            # breached: the air cannot be remade
            game.recompute()
            for _ in range(60):
                game.advance_days(1)
                if game.dead:
                    break
            return game

        alone = last_breath("die", ())
        assert alone.ship.crew <= 0 and alone.dead, (
            "a hull with nobody and nothing aboard should still end")
        held = last_breath("hold", ("precentor", "servitor"))
        assert held.ship.crew <= 0, held.ship.crew
        assert not held.dead, "the machines were aboard and it ended anyway"
        assert robots_sim.crewless(held)
        assert robots_sim.watchkeepers(held) == 2
        assert any("machines are still standing" in text
                   for _day, text, _kind in held.log), "nothing said so"
        # And it goes on being a ship: the bench runs and the stats are the
        # machines'.
        stats = held.recompute()
        assert stats.regen > 0 and stats.research > 0, stats
        from ..sim import dormancy
        assert dormancy.ship_work(held) > 0.5, dormancy.ship_work(held)
        # The best evidence that it is still a working ship: the machines
        # mend the breach that killed the crew. `repair_tick` reads `regen`,
        # and `regen` here is the Precentor standing engineering.
        # Set from a known state rather than from wherever the sixty days
        # left it, or the bar depends on the seed.
        for layer in held.ship.layers:
            layer.hp = layer.max * 0.1
        whole = sum(layer.max for layer in held.ship.layers)
        was_hull = sum(layer.hp for layer in held.ship.layers)
        banked = held.research.banked
        held.advance_days(200)
        assert not held.dead, "it died over the next two hundred days"
        now_hull = sum(layer.hp for layer in held.ship.layers)
        assert now_hull > whole * 0.5, (
            f"the hull went {was_hull / whole:.0%} → {now_hull / whole:.0%} "
            "of whole; nothing is repairing it")
        # And the bench turns, which is `dormancy.ship_work` counting them.
        # (Points bank rather than unlock, because nothing has been chosen to
        # research — that is the player's decision, not the machines'.)
        assert held.research.banked > banked, "the bench stood idle"
        return (f"the last two died and {robots_sim.watchkeepers(held)} "
                f"machines carried the hull 200 days further, mending it from "
                f"{was_hull / whole:.0%} to {now_hull / whole:.0%} of whole")

    @check("starving to the last hand ends the same way, and machines hold")
    def _():
        # The *other* death path — `sim/upkeep`, when the stores run out —
        # and the first version of this suite never reached it, so a mutation
        # deleting its machine branch passed clean.
        def starve(seed, machines):
            game = _yard(seed)
            for class_id in machines:
                robots_sim.build(game, class_id)
            game.officers.clear()
            game.ship.crew = 2
            game.stores.clear()
            game.ship.cargo.clear()
            game.recompute()
            for _ in range(400):
                game.advance_days(1)
                if game.dead or game.ship.crew <= 0:
                    break
            return game

        alone = starve("starve", ())
        assert alone.dead, "a hull with nobody left aboard did not end"
        held = starve("starve-held", ("precentor", "servitor"))
        assert held.ship.crew <= 0, held.ship.crew
        assert not held.dead, "the machines were aboard and it ended anyway"
        assert any("machines have the hull" in text
                   for _day, text, _kind in held.log), "nothing said so"
        # A machine in a crate holds nothing either. Stowed first, because
        # that is the easier mistake to make and a sweep caught it: the
        # condition is "aboard **and** working", not "not broken".
        for robot in robots_sim.owned(held):
            robot.posting = robots_sim.STOWED
        assert robots_sim.watchkeepers(held) == 0, (
            "a machine crated in the hold was counted as standing a watch")
        for robot in robots_sim.owned(held):
            robot.posting = robots_sim.ABOARD
        assert robots_sim.watchkeepers(held) == 2
        # And one that has worn through holds nothing.
        for robot in robots_sim.owned(held):
            robot.condition = 0.0
        assert robots_sim.watchkeepers(held) == 0, "a broken frame is a watch"
        assert not robots_sim.crewless(held)
        return ("stores gone: alone the chronicle ends, with two machines it "
                "does not — and it does again once they wear through")

    @check("a sleeping crew still has its machines on watch")
    def _():
        # `awake_share` counted only people, so a hull whose crew were all
        # under read as unmanned however many machines were awake — and with
        # a complement of zero it returned 1.0 through a guard, which is the
        # right answer for no reason.
        from ..sim import dormancy
        game = _yard("asleep")
        game.recompute()
        assert abs(dormancy.awake_share(game) - 1.0) < 1e-9, "somebody is under"

        # Put as many under as the hull allows, with nothing mechanical aboard.
        # `available` yields (method, allowed, why); "watch" is the one that
        # is nobody sleeping, so take the first that actually puts them under.
        method = next(m for m, ok, _why in dormancy.available(game)
                      if ok and m.id != "watch")
        under = dormancy.most_that_can_sleep(game)
        assert under > 0, "nobody can sleep on this hull; move the check"
        got = dormancy.put_under(game, method.id, under)
        assert got.get("ok"), got
        bare = dormancy.awake_share(game)
        bare_work = dormancy.ship_work(game)
        assert bare < 0.5, f"{under} under and the share is still {bare:.2f}"

        # The same sleeping hull, with machines that never go under.
        robots_sim.build(game, "precentor")
        robots_sim.build(game, "servitor")
        with_machines = dormancy.awake_share(game)
        assert with_machines > bare * 1.15, (
            f"{under} asleep: {bare:.3f} without machines, "
            f"{with_machines:.3f} with two — they are not being counted")
        assert dormancy.ship_work(game) > bare_work, "the bench felt nothing"
        return (f"{dormancy.complement(game)} aboard with {under} under: "
                f"watch {bare:.0%} alone, {with_machines:.0%} with two "
                f"machines · bench {bare_work:.0%} → "
                f"{dormancy.ship_work(game):.0%}")

    @check("a holding in another system is a light-year away, and it shows")
    def _():
        # The rule that decides what you leave behind when you sail: only a
        # goal-directed machine is worth a gram of the mass it took to get
        # there.
        game = _yard("elsewhere")
        colony = _holding(game)
        verger = robots_sim.build(game, "verger")
        anchorite = robots_sim.build(game, "anchorite")
        for robot in (verger, anchorite):
            robots_sim.post(game, robot, f"colony:{colony.id}")
        near = (tele_sim.effective(game, verger),
                tele_sim.effective(game, anchorite))
        # Sail away. The holding does not move; the ship does.
        from ..world import galaxy
        here = game.system
        # The nearest neighbour, because "another system" is a range and the
        # far end of this sector is forty light years, where nothing at all
        # can be supervised. That is true and is a different claim.
        other = min((s for s in game.galaxy.systems if s.id != here.id),
                    key=lambda s: galaxy.distance(here, s))
        light_years = galaxy.distance(here, other)
        game.location_id = other.id
        far_au = tele_sim.gap_au(game, verger)
        assert far_au > 10_000, f"{far_au:,.0f} AU is not another system"
        away = (tele_sim.effective(game, verger),
                tele_sim.effective(game, anchorite))
        # Out of contact, each rung falls to exactly what it can do by
        # itself — which for an adaptive machine is a quarter and for a
        # goal-directed one is most of it, because executing the mission
        # without you is what E4 *is*.
        assert away[0] < near[0] * 0.30, (
            f"an adaptive machine kept {away[0]:.3f} of {near[0]:.3f} across "
            f"{light_years:.1f} light years")
        assert away[1] > near[1] * 0.55, (
            f"a goal-directed machine kept only {away[1]:.3f} of "
            f"{near[1]:.3f} — it is bought to be left behind")
        assert away[1] > away[0] * 2.0, away
        years = far_au * tele_sim.LIGHT_S_PER_AU * 2 / (86400 * 365.25)
        assert years > 1.0, years
        return (f"{light_years:.1f} ly · {years:.1f} years of round trip · "
                f"verger {near[0]:.2f} → {away[0]:.4f}, anchorite "
                f"{near[1]:.2f} → {away[1]:.2f}")
