"""Machines you own, and whether the distance to them is felt.

The design turns on one claim: **a robot is worth what its autonomy can carry
across the gap to whoever is supervising it.** That is not decoration — it is
the reason there are four classes of the same thing and the reason a captain
has to choose. So the checks are about whether that claim is true in play,
rather than about whether a data table has twenty rows in it.

The curve is the ECSS ladder against real light time: a lunar round trip is
three to five seconds and is already at the edge of hand-flying; Mars is eight
to forty minutes, which is why nobody drives a rover with a joystick. Those two
figures are what `sim/robots.HALF_LIFE_S` is set from, and the first check
holds them there.

The claims:

- **The ladder is the real one**: a teleoperated hand is whole alongside, half
  gone at the Moon, and finished at one AU; a goal-directed one is not.
- **Distance is measured through the game**, not asserted — the same holding,
  the same two machines, and the levels come out an order of magnitude apart.
- **A machine on the bridge is a hand the bridge already reads**, so the ship's
  stats move when one signs on, through the door officers use.
- **A machine at a holding changes what the holding produces**, and the tick
  and the forecast agree about how much.
- **It is paid for**, daily, out of commodities the market trades; unfed it
  wears twice as fast and eventually stops.
- **A machine is neither loyal nor mutinous** — it works at exactly its level,
  which is what having no loyalty field buys.
- **The screen says what it is worth where it is**, not what is on its card.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..data.robots import ROBOTS, ROBOTS_BY_ID
from ..sim import colony as colony_sim
from ..sim import robots as robots_sim
from ..sim import works as works_sim
from .harness import Suite

#: The two real figures the ladder is calibrated against.
MOON_ROUND_TRIP_S = 4.0          # 3–5 s, Earth to the Moon and back
MARS_ROUND_TRIP_S = 40 * 60.0    # the far end of the Mars round trip

#: Every technology any class needs, so a check can build all twenty.
ALL_TECH = sorted({r.tech for r in ROBOTS if r.tech})


def _yard(seed="robots"):
    """A game with the bench, the money and the materials to build anything."""
    game = new_game(seed)
    game.credits = 500_000
    for key in ("alloy", "silicon", "magnetite", "biomass", "phosphate",
                "xenolith", "volatiles"):
        game.stores[key] = game.stores.get(key, 0) + 400
    for tech in ALL_TECH:
        if tech not in game.research.unlocked:
            game.research.unlocked.append(tech)
    return game


def _holding(game, class_id="radix_mine", body_index=1):
    body = game.system.bodies[body_index]
    colony = colony_sim.Colony(
        id=len(game.colonies) + 1, class_id=class_id,
        name=f"Holding {len(game.colonies) + 1}", system_id=game.system.id,
        body_id=body.id, need=0, online=True)
    game.colonies.append(colony)
    return colony


def run(suite: Suite) -> None:
    check = suite.check

    @check("the autonomy ladder is the real one")
    def _():
        # Alongside, everything works. The rungs only separate at range, and
        # they separate at the ranges the real figures say they should.
        for level in (1, 2, 3, 4):
            assert robots_sim.grip(level, 0.0) == 1.0, level
        moon = robots_sim.grip(1, MOON_ROUND_TRIP_S)
        assert 0.45 < moon < 0.55, (
            f"a teleoperated hand at the Moon works at {moon:.2f}; the whole "
            "point of that figure is that it is the halfway house")
        mars = robots_sim.grip(2, MARS_ROUND_TRIP_S)
        assert mars < 0.4, f"preplanned at Mars range is {mars:.2f}"
        far = 2 * 1.0 * robots_sim.LIGHT_S_PER_AU
        assert robots_sim.grip(1, far) < 0.01, "teleoperation survives an AU"
        assert robots_sim.grip(4, far) > 0.99, "a goal-directed hand felt an AU"
        # Monotone in autonomy at every range that matters, or the ladder is
        # not a ladder.
        for lag in (10.0, 600.0, 3600.0, 40_000.0):
            got = [robots_sim.grip(a, lag) for a in (1, 2, 3, 4)]
            assert got == sorted(got), (lag, got)
        return (f"Moon {moon:.0%} for E1 · Mars {mars:.0%} for E2 · at 1 AU "
                f"E1 {robots_sim.grip(1, far):.1%} against E4 "
                f"{robots_sim.grip(4, far):.1%}")

    @check("the same holding, two machines, an order of magnitude apart")
    def _():
        # Measured through the game: one holding, two machines posted to it,
        # and the only difference between them is which rung they are on.
        game = _yard()
        colony = _holding(game)
        rigger = robots_sim.build(game, "rigger")          # E1, level 4
        verger = robots_sim.build(game, "verger")          # E3, level 3
        for robot in (rigger, verger):
            ok, why = robots_sim.post(game, robot, f"colony:{colony.id}")
            assert ok, why
        gap = robots_sim.gap_au(game, rigger)
        assert gap > 0.2, f"the holding is only {gap:.3f} AU off; move the test"
        assert abs(gap - robots_sim.gap_au(game, verger)) < 1e-9
        weak = robots_sim.effective(game, rigger)
        strong = robots_sim.effective(game, verger)
        assert strong > weak * 10, (
            f"level 4 teleoperated {weak:.3f} against level 3 adaptive "
            f"{strong:.3f} at {gap:.2f} AU — the rung is not being felt")
        assert weak < 0.1, f"a hand-flown frame at {gap:.2f} AU works at {weak:.2f}"
        return (f"{gap:.2f} AU · {robots_sim.lag_seconds(game, rigger) / 60:.0f} "
                f"min round trip · rigger {weak:.3f} against verger {strong:.2f}")

    @check("a machine on the bridge is a hand the bridge already reads")
    def _():
        game = _yard("bridge")
        before = game.recompute()
        was = (before.regen, before.scan)
        assert robots_sim.build(game, "precentor") is not None   # engineering 4
        assert robots_sim.build(game, "servitor") is not None    # science 3
        after = game.recompute()
        assert after.regen > was[0], f"repair unmoved: {was[0]} → {after.regen}"
        assert after.scan > was[1], f"scan unmoved: {was[1]} → {after.scan}"
        hands = robots_sim.standing(game)
        assert len(hands) == 2, hands
        # And a stowed machine is not standing a watch.
        robots_sim.post(game, robots_sim.owned(game)[0], robots_sim.STOWED)
        assert len(robots_sim.standing(game)) == 1
        stowed = game.recompute()
        assert stowed.regen < after.regen, "a stowed machine still held a seat"
        return (f"regen {was[0]:.2f} → {after.regen:.2f}, scan {was[1]:.2f} → "
                f"{after.scan:.2f}; stowing one gave the seat back")

    @check("a machine works at its level, being neither loyal nor mutinous")
    def _():
        # `Hand` carries no loyalty field on purpose: `loyalty.effective_level`
        # falls back to the neutral value, so a machine gets neither the 1.2 a
        # devoted officer gives nor the 0.45 a mutinous one does. If those
        # bands ever move, this fires.
        from ..sim import stations
        game = _yard("loyal")
        robots_sim.build(game, "precentor")
        hand = robots_sim.standing(game)[0]
        rated = ROBOTS_BY_ID["precentor"].level
        assert abs(hand.level - rated) < 1e-9, hand.level
        held = stations.officer_level([hand], "engineering")
        assert abs(held - rated) < 1e-9, (
            f"a machine rated {rated} holds its station at {held}")
        return f"rated {rated}, stands the watch at {held:.2f}"

    @check("a machine at a holding changes what the holding produces")
    def _():
        game = _yard("works")
        colony = _holding(game)
        bare = dict(works_sim.yields_of(colony))
        assert bare, "the holding produces nothing to begin with"
        assert works_sim.crewed_yields(game, colony) == bare
        verger = robots_sim.build(game, "verger")
        robots_sim.post(game, verger, f"colony:{colony.id}")
        lifted = works_sim.crewed_yields(game, colony)
        for key, was in bare.items():
            assert lifted[key] > was, key
        # And what the tick actually banks is the lifted figure, not the
        # card. Measured as a difference, because a holding pays its own
        # upkeep out of the same stores and a cleared depot simply starves.
        before = dict(game.stores)
        colony_sim.tick(game, 1.0)
        for key, was in bare.items():
            banked = game.stores.get(key, 0.0) - before.get(key, 0.0)
            assert banked > was * 1.0001, (
                f"{key}: banked {banked:.4f} against a bare {was:.4f} — the "
                "tick is reading the card rather than the holding")
        share = lifted["ore"] / bare["ore"] - 1.0
        return (f"one Verger lifts {colony.name} by {share:.0%}, and the day's "
                f"tick banked {game.stores.get('ore', 0):.3f} t of ore")

    @check("they are paid for, and an unfed one wears out faster")
    def _():
        game = _yard("fed")
        robots_sim.build(game, "verger")
        want = robots_sim.daily_upkeep(game)
        assert want, "a machine that costs nothing has no decision attached"
        game.stores["silicon"] = 100.0
        game.stores["magnetite"] = 100.0
        before = dict(game.stores)
        robots_sim.tick(game, 10.0, game.rng)
        for key, rate in want.items():
            if key == "credits":
                continue
            spent = before.get(key, 0) - game.stores.get(key, 0)
            assert spent > rate * 9, f"{key}: spent {spent:.4f} over ten days"
        fed = robots_sim.owned(game)[0].condition
        # The same ten days with nothing in the stores.
        starved = _yard("starved")
        robots_sim.build(starved, "verger")
        starved.stores.clear()
        starved.ship.cargo.clear()
        lines = robots_sim.tick(starved, 10.0, starved.rng)
        hungry = robots_sim.owned(starved)[0].condition
        assert hungry < fed, f"unfed {hungry:.4f} against fed {fed:.4f}"
        assert any("short of" in text for _kind, text in lines), lines
        return (f"ten days: fed {fed:.3f} condition, unfed {hungry:.3f}, and "
                "the log said which")

    @check("a machine wears out, stops, and only the living ones mend")
    def _():
        # Swept, and this check is why it exists: `MEND_PER_DAY` and
        # `BROKEN_AT` were held only by the wide set, so the difference
        # between a frame that is dead metal and one that heals overnight —
        # which is the whole grown-against-built trade — was not named by any
        # suite that knew what it meant.
        game = _yard("wear")
        welded = robots_sim.build(game, "hullwright")     # fabricated
        grown = robots_sim.build(game, "myrmidon")        # grown
        for robot in (welded, grown):
            robot.condition = robots_sim.BROKEN_AT + 0.02
        game.stores["alloy"] = 200.0
        game.stores["biomass"] = 200.0
        # Worked, both fall. The rate is the same; what differs is what
        # happens when they are put down.
        robots_sim.tick(game, 60.0, game.rng)
        assert welded.broken, f"still working at {welded.condition:.3f}"
        assert not grown.broken, (
            f"a grown machine worked itself under at {grown.condition:.3f} — "
            "it is supposed to mend faster than it wears")
        # A broken machine holds no station and costs nothing to keep.
        stopped = robots_sim.build(game, "precentor")
        stopped.condition = 0.0
        assert robots_sim.effective(game, stopped) == 0.0
        assert not any(h.role_name == "Precentor"
                       for h in robots_sim.standing(game))
        # Put down, the living one comes back and the welded one does not.
        for robot in (welded, grown):
            robot.posting = robots_sim.STOWED
        was = welded.condition
        robots_sim.tick(game, 40.0, game.rng)
        assert abs(welded.condition - was) < 1e-9, (
            f"a welded frame mended itself in the hold: {was:.3f} → "
            f"{welded.condition:.3f}")
        assert grown.condition > 0.99, grown.condition
        return (f"60 days of work put the welded frame under at "
                f"{welded.condition:.2f} and left the grown one at "
                f"{grown.condition:.2f}; 40 days stowed mended one and not "
                "the other")

    @check("every class can be built, and none of them is free")
    def _():
        game = _yard("all")
        made = []
        for klass in ROBOTS:
            ok, why = robots_sim.can_build(game, klass.id)
            assert ok, f"{klass.id}: {why}"
            made.append(robots_sim.build(game, klass.id))
        assert all(made), "a build that passed its own gate returned nothing"
        assert len(robots_sim.owned(game)) == len(ROBOTS)
        # Every one is gated on something, costs something and eats something.
        for klass in ROBOTS:
            assert klass.cost, klass.id
            assert klass.upkeep, f"{klass.id} costs nothing to keep"
            assert klass.stat or klass.duties, (
                f"{klass.id} can neither stand a watch nor hold a duty")
        # And the gate bites: a fresh captain cannot build the clever ones.
        fresh = new_game("fresh")
        fresh.credits = 500_000
        for key in ("alloy", "silicon", "magnetite", "biomass", "phosphate",
                    "xenolith"):
            fresh.stores[key] = 400
        refused = [k.id for k in ROBOTS
                   if not robots_sim.can_build(fresh, k.id)[0]]
        assert len(refused) > len(ROBOTS) // 2, refused
        return (f"{len(made)} classes built · {len(refused)} of {len(ROBOTS)} "
                "refused to a captain on day one")

    @check("the screen says what a machine is worth where it stands")
    def _():
        # The defect this panel exists to avoid: showing the rating rather
        # than the reading. A statue must not read "lvl 4".
        from ..ui import robots_panel
        game = _yard("panel")
        colony = _holding(game)
        rigger = robots_sim.build(game, "rigger")
        robots_sim.post(game, rigger, f"colony:{colony.id}")
        got = robots_sim.effective(game, rigger)
        rated = ROBOTS_BY_ID["rigger"].level
        assert got < rated * robots_panel.USEFUL, (got, rated)
        where = robots_panel.where_line(game, rigger)
        assert colony.name in where, where
        said = robots_panel.lag_line(game, rigger)
        assert "round trip" in said, said
        # The minutes on the screen are the minutes in the sim.
        minutes = robots_sim.lag_seconds(game, rigger) / 60.0
        assert f"{minutes:.0f} min" in said, (said, minutes)

        # And through the panel itself, not through its helpers. Swept, and
        # the first version of this check MISSED a mutation that printed the
        # rating instead of the reading — because it never built the widget.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        keep = QApplication.instance() or QApplication([])
        assert keep is not None
        from ..ui.widgets import Pill
        panel = robots_panel.build(game)
        pills = [p.text() for p in panel.findChildren(Pill)]
        assert f"LVL {rated}.0" not in pills, (
            f"the panel calls a statue a level {rated}: {pills}")
        assert any(f"/{rated}" in text for text in pills), (
            f"the panel never says what it is actually working at: {pills}")
        assert f"LVL {got:.2f}/{rated}".upper() in pills, pills
        panel.deleteLater()
        return (f"{where} · {said} · the panel says "
                f"{[t for t in pills if '/' in t][0]}, not lvl {rated}")

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
        near = (robots_sim.effective(game, verger),
                robots_sim.effective(game, anchorite))
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
        far_au = robots_sim.gap_au(game, verger)
        assert far_au > 10_000, f"{far_au:,.0f} AU is not another system"
        away = (robots_sim.effective(game, verger),
                robots_sim.effective(game, anchorite))
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
        years = far_au * robots_sim.LIGHT_S_PER_AU * 2 / (86400 * 365.25)
        assert years > 1.0, years
        return (f"{light_years:.1f} ly · {years:.1f} years of round trip · "
                f"verger {near[0]:.2f} → {away[0]:.4f}, anchorite "
                f"{near[1]:.2f} → {away[1]:.2f}")
