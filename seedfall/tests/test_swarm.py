"""Machines that guard a holding, and why the controller is the objective.

**This task was mis-scoped and the measuring said so.** It was written as
drone warfare — light-lag deciding tactical engagements, the controller as the
thing to shoot. Measured against `sim/robots.grip`, which is where the law
already lives:

    halving a teleoperated hand needs 4.0 s of round trip = 599,585 km
    the tactical arena is 1,400 units and a band is 240

At 1,400 km the round trip is 9.3 ms and an E1 hand keeps 99.77% of itself.
Light-lag cannot decide a gunfight, and no amount of tuning would make it —
it is a **strategic** law, and the arena where it bites is the one the game
already had and never used it for.

Machines can be posted to a holding. `robots.effective` has priced them by
`grip` since the day they landed. And `colony.ward_at` — what defends a
system, read by `sim/control` and `sim/interdiction` for what a place may do
about an approaching hull — counted only built works. So twenty classes of
machine, four of them carrying a ground duty, defended nothing anywhere.

The data already held the whole design and never expressed it:

    loader      level 3, autonomy 1,  1,800 credits
    myrmidon    level 2, autonomy 2,  1,600 credits
    servitor    level 3, autonomy 4,  9,000 credits

Five times the price for autonomy. Measured now, in ward and in what the
world may do about you:

    loader     alongside 0.0900 rung 3 · away 0.0001 rung 2
    myrmidon   alongside 0.0600 rung 3 · away 0.0192 rung 2
    servitor   alongside 0.0900 rung 3 · away 0.0900 rung 3

That is "the controller is the objective", and the objective is your own hull
being in the system.

One defect this turned up, which is the old one in a new place: both callers
tested `ward_at(...) > 0.0`. That was right while a ward could only come from
a work worth 0.28, and wrong the moment a continuous quantity fed it — a
teleoperated guard nine AU out is worth 1e-7, which is greater than zero, and
it armed a world with a hand that could not have lifted a spanner.
`colony.is_warded` is the one door now.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.robots import ROBOTS_BY_ID
from ..sim import colony as colony_sim
from ..sim import flight
from ..sim import interdiction as idn
from ..sim import robots as robots_sim
from ..sim import settlement as settlement_sim
from ..sim import track as track_sim
from .harness import Suite


def _holding(seed="a"):
    """A game with a colony to guard, a settled world, and its contact."""
    game = new_game(seed)
    world = next(b for b in game.system.bodies
                 if b.kind in ("rocky", "ocean", "ice"))
    settlement_sim.held(game).append(settlement_sim.Settlement(
        id=9001, power="charter", system_id=game.system.id,
        body_id=world.id, good="ore", founded=game.day))
    contact = next(c for c in track_sim.contacts(game)
                   if c.kind == "body" and c.name == world.name)
    host = game.system.bodies[0]
    game.colonies.append(colony_sim.Colony(
        id=1, class_id="radix_mine", name="Deepcut", system_id=game.system.id,
        body_id=host.id, need=0, online=True))
    away = next(b for b in game.system.bodies if b.id != host.id)
    return game, contact, host, away


def _post(game, class_id):
    game.robots = [robots_sim.Robot(id=1, class_id=class_id, name="Guard",
                                    posting="colony:1")]
    return game.robots[0]


def run(suite: Suite) -> None:
    check = suite.check

    @check("light-lag decides nothing at gunfight range")
    def _():
        # The measurement that re-scoped this task. Stated as a check so the
        # next person does not spend the afternoon I nearly spent.
        from ..sim import tactical
        arena = tactical.ARENA
        for units in (tactical.BAND_UNITS, arena):
            # Read as kilometres, which is generous — the arena is abstract.
            lag = 2.0 * units / 299_792.458
            kept = robots_sim.grip(1, lag)
            assert kept > 0.99, (
                f"a teleoperated hand at {units:,.0f} km keeps {kept:.1%}")
        half = robots_sim.HALF_LIFE_S[1] * 299_792.458 / 2.0
        assert half > arena * 100, (
            f"halving a teleoperated hand takes {half:,.0f} km against an "
            f"arena {arena:,.0f} across — light-lag might reach a battle "
            "after all, and this whole file is scoped wrong")
        return (f"halving an E1 hand needs {half:,.0f} km; the arena is "
                f"{arena:,.0f} and a band {tactical.BAND_UNITS:,.0f}")

    @check("machines guard a holding, and only guards do")
    def _():
        game, _contact, host, _away = _holding()
        flight.hold_at(game, host)
        game.robots = []
        assert colony_sim.ward_at(game, game.system.id) == 0.0

        _post(game, "servitor")
        armed = colony_sim.ward_at(game, game.system.id)
        assert armed > 0, "a guard posted to a holding defends nothing"

        # A machine with no ground duty is not a guard, however good it is.
        spare = next(r for r in ROBOTS_BY_ID.values()
                     if robots_sim.GUARD_DUTY not in r.duties)
        _post(game, spare.id)
        assert colony_sim.ward_at(game, game.system.id) == 0.0, (
            f"{spare.id} has duties {spare.duties} and is standing guard")
        return (f"servitor {armed:.3f} · {spare.id} "
                f"({'/'.join(spare.duties)}) nothing")

    @check("what a guard is worth is where you are standing")
    def _():
        game, contact, host, away = _holding()
        said = []
        for class_id in ("loader", "myrmidon", "servitor"):
            _post(game, class_id)
            flight.hold_at(game, host)
            near = colony_sim.ward_at(game, game.system.id)
            near_rung = idn.means(game, contact)
            flight.hold_at(game, away)
            far = colony_sim.ward_at(game, game.system.id)
            far_rung = idn.means(game, contact)
            klass = ROBOTS_BY_ID[class_id]
            assert far <= near + 1e-12, (
                f"{class_id} is worth more from further away")
            if klass.autonomy <= 2:
                assert far < near * 0.5, (
                    f"{class_id} is autonomy {klass.autonomy} and kept "
                    f"{far / max(near, 1e-9):.0%} of itself across a system")
            else:
                assert far > near * 0.9, (
                    f"{class_id} is autonomy {klass.autonomy} and lost "
                    f"{1 - far / max(near, 1e-9):.0%} across a system")
            said.append(f"{class_id} {near:.3f}→{far:.3f} rung "
                        f"{near_rung}→{far_rung}")
        return " · ".join(said)

    @check("five times the price buys a guard that works when you leave")
    def _():
        # The trade the data has always described and never expressed.
        game, contact, host, away = _holding()
        cheap, dear = ROBOTS_BY_ID["loader"], ROBOTS_BY_ID["servitor"]
        assert dear.cost["credits"] >= cheap.cost["credits"] * 4, (
            "the expensive guard is not expensive")
        assert cheap.level == dear.level, (
            "these two differ by more than their autonomy, so the comparison "
            "is not about autonomy")

        _post(game, "loader")
        flight.hold_at(game, host)
        assert idn.means(game, contact) == idn.ARMED
        flight.hold_at(game, away)
        assert idn.means(game, contact) == idn.SPEAKS, (
            "a teleoperated guard still armed the world from across a system")

        _post(game, "servitor")
        flight.hold_at(game, away)
        assert idn.means(game, contact) == idn.ARMED, (
            "a goal-directed guard lost the world its teeth by being left")
        return (f"loader {cheap.cost['credits']:,} cr: armed only alongside · "
                f"servitor {dear.cost['credits']:,} cr: armed either way")

    @check("a ward has to be worth something to count")
    def _():
        # Both callers tested `> 0.0`, which armed a world with a hand worth
        # 1e-7. `colony.is_warded` is the one door and it has a floor.
        game, contact, host, away = _holding()
        _post(game, "loader")
        flight.hold_at(game, away)
        left = colony_sim.ward_at(game, game.system.id)
        assert 0.0 < left < colony_sim.WARD_ENOUGH, (
            f"an out-of-contact guard is worth {left:.6f}, which is not the "
            "vanishing-but-positive case this floor exists for")
        assert not colony_sim.is_warded(game, game.system.id)
        flight.hold_at(game, host)
        assert colony_sim.is_warded(game, game.system.id)
        # And the floor sits below one machine standing right there.
        assert colony_sim.WARD_ENOUGH < colony_sim.ward_at(game, game.system.id)
        return (f"out of contact {left:.6f} < floor "
                f"{colony_sim.WARD_ENOUGH} < alongside "
                f"{colony_sim.ward_at(game, game.system.id):.3f}")
