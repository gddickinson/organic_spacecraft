"""A berth is a place on the structure, not a point on a bounding sphere.

Coming alongside was a distance from a *point*: `range_km <= ALONGSIDE_KM +
radius_km` and slow enough. `radius_km` is a bounding sphere, so a hull that
crept up on the **far side** of a Fleet Hub — nowhere near a mast — and
stopped was moored, and the structure the window spends the whole approach
drawing had nothing to do with it.

`data/berths3d.BERTH_POINTS` says where the berths are, off the same numbers
the mesh builders use: a quay's one arm ends in a warn-lit box, and that box
is the berth; a hub's four lit masts are four berths. `sim/moorings.py` is the
sim side. The claims:

- **A berth is where the model draws one**, at every scale — the points and
  the mesh cannot drift apart, because they are the same numbers.
- **The far side of a structure is not a berth**, which is the whole point.
- **The computer can still berth**, flown, from every drift the conn suite
  throws at it — and it flies a corridor rather than boring at the middle.
- **A berth is chosen on final approach**: freely while there is room to
  change your mind, and held once committed.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..data import berths3d
from ..sim import autopilot as pilot_sim
from ..sim import conn as conn_sim
from ..sim import flight
from ..sim import moorings
from ..sim import track as track_sim
from .harness import Suite


class _Target:
    """A stand-in target, so the geometry can be asked at any scale."""

    kind = "anchorage"

    def __init__(self, berth: str, radius_km: float) -> None:
        self.berth, self.radius_km = berth, radius_km


class _At:
    """A stand-in approach at a chosen place — geometry, not flying."""

    def __init__(self, target, pos) -> None:
        self.target, self.pos, self.berth = target, list(pos), ""

    @property
    def range_km(self) -> float:
        return math.dist(self.pos, (0.0, 0.0, 0.0))


def run(suite: Suite) -> None:
    check = suite.check

    @check("every sort of berth has berths, where the model draws them")
    def _():
        # The points and the mesh are the same numbers by construction; what
        # this holds is that none of them is empty, that they are on the
        # structure rather than at its centre, and that they scale with it.
        seen = {}
        for sort in berths3d.BERTHS:
            points = berths3d.berth_points(sort)
            assert points, f"a {sort} has nowhere to tie up"
            spans = [math.dist(at, (0.0, 0.0, 0.0)) for _n, at in points]
            assert min(spans) > 0.2, (sort, spans)
            seen[sort] = (len(points), max(spans))
        # A hub is a fleet berth and has more places to put a hull than a quay.
        assert seen["hub"][0] > seen["quay"][0], seen
        # And in km they follow the structure's own size.
        small = moorings.points(_Target("hub", 0.4))
        large = moorings.points(_Target("hub", 4.0))
        assert len(small) == len(large) == seen["hub"][0]
        assert abs(math.dist(large[0][1], (0, 0, 0))
                   - 10 * math.dist(small[0][1], (0, 0, 0))) < 1e-9
        return " · ".join(f"{k} {v[0]} at {v[1]:.2f}" for k, v in seen.items())

    @check("the far side of a structure is not a berth")
    def _():
        # The defect, at four sorts and four scales. "Alongside the fitting" is
        # a hull that has come up outside the berth; "the far side" is contact
        # on the opposite skin, which the old rule accepted as a mooring.
        rows = []
        for sort, radius in (("quay", 0.4), ("hub", 0.4), ("holding", 0.3),
                             ("gate", 1.2)):
            target = _Target(sort, radius)
            name, at = moorings.points(target)[0]
            out = math.dist(at, (0.0, 0.0, 0.0)) or 1.0
            close = [c * (out + radius * 0.15) / out for c in at]
            far = [-c * radius / out for c in at]
            here = moorings.nearest(_At(target, close))
            there = moorings.nearest(_At(target, far))
            assert here["at_it"], (sort, here)
            assert not there["at_it"], (sort, there)
            rows.append(f"{sort} {here['km']:.3f} vs {there['km']:.3f}")
        return "at the fitting against the far side, km: " + " · ".join(rows)

    @check("a berth is chosen on final approach, and held once committed")
    def _():
        # Two mistakes bracket the rule, and both were measured. Re-picking
        # every tick makes the computer chase a moving aim; committing twelve
        # kilometres out picks a mast before the drift has played out. So:
        # free outside the corridor, held inside it.
        target = _Target("hub", 0.4)
        corridor = moorings.corridor_km(target)
        assert corridor > 0.4, corridor
        names = [n for n, _at in moorings.points(target)]
        places = dict(moorings.points(target))
        far = _At(target, [0.0, -12.0, 0.0])
        first = moorings.assign(far)
        # **Come round to another mast and it changes its mind** — but the
        # scenario has to be one where the two are actually different places.
        # This used to reposition from 12 km on one side to 12 km on the
        # other and demand a change; measured, four masts of a 0.4 km hub are
        # within 94 m of each other at that range, against a berth reach of
        # 140. Switching on 94 m at 12 km *is* the flapping the hysteresis
        # exists to stop, so the check now stands where the choice is real.
        # The berth on the *other side*, not merely a different one: adjacent
        # masts of a hub are 135 m apart at this range, inside the reach, and
        # a computer that swapped between them there would be flapping.
        other = max(places, key=lambda n: math.dist(places[first], places[n]))
        assert other != first and len(names) > 1
        at = places[other]
        out = math.dist(at, (0.0, 0.0, 0.0)) or 1.0
        far.pos = [c * (corridor * 1.4) / out for c in at]
        assert moorings.assign(far) == other, (
            "another berth is plainly the near one and it will not change "
            "its mind")
        # And a rival that is barely nearer does not steal the assignment.
        far.pos = [0.0, -12.0, 0.0]
        held = moorings.assign(far)
        far.pos = [12.0, 0.0, 0.0]
        margin = (math.dist(far.pos, places[held])
                  - min(math.dist(far.pos, p) for p in places.values()))
        assert 0 < margin < moorings.reach_km(target), margin
        assert moorings.assign(far) == held, (
            f"a berth {margin * 1000:.0f} m nearer — inside the reach — took "
            "the assignment off the one already being flown")
        # Inside it, the choice sticks even if another fitting is nearer.
        near = _At(target, [0.0, 0.0, 0.0])
        names = [n for n, _at in moorings.points(target)]
        near.berth = names[0]
        near.pos = list(moorings.points(target)[2][1])   # sitting on another
        assert near.range_km <= corridor, near.range_km
        assert moorings.assign(near) == names[0], (
            "committed to a berth and then changed its mind on finals")
        return (f"corridor at {corridor:.3f} km: free outside it, held inside")

    @check("the computer still berths, and berths at a berth")
    def _():
        # Flown, from a real approach, and asked *where* it ended up — not
        # merely that it said "alongside".
        game = new_game("berthing-real")
        flight.travel_to(game, 0)
        quay = next(c for c in track_sim.contacts(game)
                    if c.kind == "anchorage")
        conn = conn_sim.start(game, quay)
        pilot_sim.fly(conn, "close", 2000)
        assert conn.outcome == "alongside", (conn.outcome, conn.range_km)
        found = moorings.nearest(conn)
        assert found is not None and found["at_it"], found
        assert conn.berth == found["name"], (conn.berth, found["name"])
        return (f"berthed at {found['name']}, {found['km'] * 1000:,.0f} m off "
                f"it, with a reach of {found['reach_km'] * 1000:,.0f} m")

    @check("a hull stopped on the wrong side is not moored")
    def _():
        # The same approach, walked to the far side and stopped dead. Slow,
        # near the structure, and nowhere near a fitting: under the old rule
        # this was a berthing.
        from ..sim import outcome as outcome_sim
        game = new_game("wrong-side")
        flight.travel_to(game, 0)
        quay = next(c for c in track_sim.contacts(game)
                    if c.kind == "anchorage")
        conn = conn_sim.start(game, quay)
        name, at = moorings.points(conn.target)[0]
        conn.berth = name
        out = math.dist(at, (0.0, 0.0, 0.0)) or 1.0
        conn.pos = [-c * (conn.target.radius_km + 0.05) / out for c in at]
        conn.vel = [0.0, 0.0, 0.0]
        assert conn.range_km <= conn_sim.ALONGSIDE_KM + conn.target.radius_km
        assert conn.speed <= conn_sim.ALONGSIDE_RATE
        assert not outcome_sim.alongside(conn, conn_sim.ALONGSIDE_KM,
                                         conn_sim.ALONGSIDE_RATE), (
            "stopped on the far side of the structure and called it moored")
        # And on the right side, the same two thresholds do say yes.
        conn.pos = [c * (out + conn.target.radius_km * 0.1) / out for c in at]
        assert outcome_sim.alongside(conn, conn_sim.ALONGSIDE_KM,
                                     conn_sim.ALONGSIDE_RATE)
        return ("near and slow on the far side: refused; near and slow at the "
                "fitting: moored")
