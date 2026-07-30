"""The picket mesh: what a CHORUS Node lets you see, and where it stops.

**Two guards were excusing each other over this one.** `test_grants` asks
whether every colony effect is read *by name* somewhere and found `"drift"` in
`sim/ship.py` — where the only thing it did was set `Stats.has_drift`, a flag
`test_declared` had on its allowed list precisely because nothing gated on it. So
the colony effect counted as consumed *because* a dead ship stat mentioned it,
and the ship stat was excused *because* somebody would get round to it. Between
them the whole `drift` effect did nothing at all, on a 21,000-credit module and an
18,000-credit colony whose descriptions both promise it plainly:

    module:  "reconciling against every other node in the mesh"
    colony:  "Reads the traffic: other hulls in this system stay plotted."

`sim/traffic.py` could always derive the hulls working *any* system — it is a pure
function of the sector and the day — and nothing ever asked it about anywhere but
the system the ship was in. So the effect had a specification and an
implementation waiting for each other.

The claims:

- **Without a node you see only where you are**, and the traffic elsewhere is
  really there — the difference is sight, not emptiness.
- **A node aboard plots the systems you have stood in**, and no others.
- **A Node planted in a system plots that system**, node aboard or not.
- **What the mesh shows is what standing there shows** — the same hulls, by name,
  from one derivation rather than two.
- **The chart's warning is true**: a hostile the mesh reports at a system is a
  hostile that is actually there when you arrive.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import traffic as traffic_sim
from ..ui import mesh_panel
from .harness import Suite


def _elsewhere(game, limit: int = 6) -> list:
    """Systems that are not the one the ship is in, that have traffic at all."""
    out = []
    for system in game.galaxy.systems:
        if system.id == game.location_id:
            continue
        if traffic_sim.in_system(game, system):
            out.append(system)
        if len(out) >= limit:
            break
    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("without a node you see only the system you are in")
    def _():
        game = new_game("mesh-blind")
        assert not game.ship_stats.has_drift, "this hull opened with a node"
        away = _elsewhere(game)
        assert len(away) >= 3, len(away)

        # The traffic is there. That is the point: what the node buys is sight.
        real = sum(len(traffic_sim.in_system(game, s)) for s in away)
        seen = sum(len(traffic_sim.plotted(game, s)) for s in away)
        assert real >= 3, real
        assert seen == 0, (
            f"{seen} of {real} hulls in {len(away)} other systems were plotted "
            "with nothing of yours listening")
        # And where you stand, you see.
        assert traffic_sim.plotted(game) == traffic_sim.in_system(game)
        rows = traffic_sim.watched(game)
        assert [row["here"] for row in rows] == [True] * len(rows), rows
        return (f"{real} hulls across {len(away)} systems, none of them plotted; "
                "the one you are in reads in full")

    @check("a node aboard plots where you have been, and nowhere else")
    def _():
        game = new_game("mesh-aboard")
        away = _elsewhere(game)
        assert len(away) >= 3
        stood_in, never = away[:2], away[2:]
        for system in stood_in:
            system.visited = True
        for system in never:
            system.visited = False

        game.ship_stats.has_drift = True
        for system in stood_in:
            assert traffic_sim.plotted(game, system), (
                f"{system.name} was visited and the mesh is not reporting it")
        for system in never:
            assert not traffic_sim.plotted(game, system), (
                f"{system.name} has never been visited and the mesh is "
                "reporting it — the node hears the mesh, it does not invent it")

        # Turning the flag off puts the lights out again, which is the direct
        # test that the *flag* is what is being read.
        game.ship_stats.has_drift = False
        assert not any(traffic_sim.plotted(game, s) for s in stood_in), (
            "the mesh kept reporting with the node removed")
        return (f"{len(stood_in)} visited systems plotted, "
                f"{len(never)} unvisited dark, and dark again without the node")

    @check("a Node planted somewhere plots that system, aboard or not")
    def _():
        game = new_game("mesh-colony")
        away = _elsewhere(game)
        assert away
        target = away[0]
        target.visited = False              # so only the colony can explain it
        assert not traffic_sim.plotted(game, target)

        from ..sim import colony as colony_sim
        from ..data.colonies import COLONIES_BY_ID
        assert "drift" in (COLONIES_BY_ID["chorus_node"].effects or {}), (
            "the CHORUS Node colony no longer grants drift")
        planted = colony_sim.Colony(
            id=901, class_id="chorus_node", name="Node", system_id=target.id,
            body_id=target.bodies[0].id, need=0, online=True)
        game.colonies.append(planted)
        assert colony_sim.drifting(game, target.id)
        assert traffic_sim.plotted(game, target), (
            "a CHORUS Node is planted there and the system is not plotted")

        planted.online = False
        assert not traffic_sim.plotted(game, target), (
            "a colony that is not online is still reporting")
        return f"{target.name} plotted by its own Node, dark once it is offline"

    @check("what the mesh shows is what standing there shows")
    def _():
        # One derivation, not two. A screen that worked out its own idea of who
        # is out there would eventually disagree with the one an encounter rolls
        # against, and the whole point of `traffic` being pure is that it cannot.
        game = new_game("mesh-same")
        away = _elsewhere(game)
        for system in away:
            system.visited = True
        game.ship_stats.has_drift = True
        pairs = 0
        for system in away:
            far = traffic_sim.plotted(game, system)
            standing = traffic_sim.in_system(game, system)
            assert [h.id for h in far] == [h.id for h in standing]
            assert [h.name for h in far] == [h.name for h in standing], (
                f"{system.name}: the mesh names different hulls from the ones "
                "that are there")
            pairs += len(far)
        assert pairs > 4, pairs

        # And the panel and the chart read the same function as the sim.
        for system in away:
            mark = mesh_panel.chart_mark(game, system)
            assert mark == sum(1 for h in traffic_sim.plotted(game, system)
                              if h.hostile)
        game.ship_stats.has_drift = False
        assert all(mesh_panel.chart_mark(game, s) == 0 for s in away), (
            "the chart marks trouble in systems the mesh cannot hear")
        return f"{pairs} hulls, identical by id and name from either side"

    @check("the warning is true: what it reports is what is waiting")
    def _():
        # The complaint `sim/traffic.py` opens with is that "a Concordat patrol
        # jumped me at Loam Span" arrived with no warning it could have given.
        # This is that warning being worth something.
        game = new_game("mesh-true")
        away = _elsewhere(game, limit=12)
        for system in away:
            system.visited = True
        game.ship_stats.has_drift = True
        warned = [s for s in away if mesh_panel.chart_mark(game, s)]
        assert warned, (
            "no system in this sector is reporting anything hostile, so this "
            "check cannot say whether a warning is true")
        for system in warned:
            said = mesh_panel.chart_mark(game, system)
            game.location_id = system.id       # arrive
            found = traffic_sim.hostiles(game, system)
            assert len(found) == said, (
                f"{system.name}: the chart warned of {said} and {len(found)} "
                "were there")
        return (f"{len(warned)} system(s) warned about, and every count was "
                "what was actually there on arrival")
