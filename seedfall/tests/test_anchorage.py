"""Places you can put in, and whether the chart will admit they exist.

A player at the helm: *"the map only shows the sun and planets. What about
stations, the fleet hub and other shipyards? How would I navigate back to a
shipyard if it is not on the map?"*

They could not, because a `Port` had no position at all — it hung off a
`System` with no body, no orbit and no coordinates. These checks hold that a
berth is now a *place*: it has somewhere to be, it is reachable by the same
flight machinery a body is, and the screens say where you are standing.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.colonies import COLONIES
from ..sim import anchorage, colony as colony_sim, flight
from ..sim import gates as gates_sim
from ..sim import track as track_sim
from ..sim import weave as weave_sim
from .harness import Suite


def _with_holding(seed: str, want: str = "build_here"):
    """A game with one of your own settlements standing in the home system."""
    game = new_game(seed)
    cid = next((c.id for c in COLONIES if c.effects.get(want)), None)
    assert cid, f"no colony class offers {want} any more"
    col = colony_sim.Colony(id=9101, class_id=cid, name="Test Holding",
                            system_id=game.system.id,
                            body_id=game.system.bodies[-1].id, need=0)
    col.online = True
    game.colonies.append(col)
    game.recompute()
    return game, col




def conn_from(game, contact):
    """An approach on a contact, for asking what the window would draw."""
    from ..sim import conn as conn_sim
    return conn_sim.start(game, contact)


def _rich(seed: str):
    """A captain who can pay for anything, so only the rules bite."""
    from ..data.gates import BUILD_GOODS, WAKE_GOODS
    game = new_game(seed)
    game.credits = 20_000_000
    game.research.unlocked = list({*game.research.unlocked, "weavecraft"})
    for goods in (WAKE_GOODS, BUILD_GOODS):
        for cid, need in goods.items():
            game.stores[cid] = need * 20
    game.recompute()
    return game

def run(suite: Suite) -> None:
    check = suite.check
    @check("every anchor stands somewhere you can fly to")
    def _():
        # A player's report: the anchor is on the sector chart, invisible on
        # the helm, impossible to fly to, and nothing is happening around it.
        # It had no place *inside* its own system at all — it was a sector
        # abstraction. It is a berth like any other now, so every screen that
        # can plot an anchorage plots it for free.
        from ..sim import anchorage as anchorage_sim

        checked, faults = 0, []
        for seed in range(4):
            game = new_game(f"placed-{seed}")
            for gate in weave_sim.gates(game):
                game.location_id = gate.system_id
                system = game.system
                berths = anchorage_sim.in_system(game)
                mine = [a for a in berths if a.kind == "gate"]
                checked += 1
                if len(mine) != 1:
                    faults.append(f"{system.name}: {len(mine)} gate berths")
                    continue
                berth = mine[0]
                if not 0 <= berth.body_index < len(system.bodies):
                    faults.append(f"{berth.name} is at body "
                                  f"{berth.body_index} of {len(system.bodies)}")
                if berth.name != gate.name:
                    faults.append(f"{berth.name} against {gate.name}")
                # And not on top of the quay — arriving through the Weave
                # should drop you at the edge, not in the middle of a port.
                quay = next((a for a in berths if a.kind in ("quay", "hub")),
                            None)
                if quay is not None and quay.body_index == berth.body_index:
                    faults.append(f"{berth.name} shares a body with "
                                  f"{quay.name}")
        assert not faults, faults
        assert checked >= 30, checked

        # It reaches the screens that matter, by being a berth rather than by
        # any of them knowing what a gate is.
        game = new_game("placed-0")
        game.location_id = weave_sim.lit_at_dawn(game.galaxy)[0]
        contact = next((c for c in track_sim.contacts(game)
                        if c.berth == "gate"), None)
        assert contact is not None, "no gate contact for the conn or the plot"
        assert contact.body_index is not None
        from ..sim import berthing as berth_sim
        game.orbit_body = game.system.bodies[contact.body_index].id
        ok, why = berth_sim.can_conn(game, contact)
        assert ok, f"cannot take the conn on an anchor you are alongside: {why}"
        conn = conn_from(game, contact)
        assert conn.target.berth == "gate", conn.target.berth
        assert conn.target.radius_km > 0.8, (
            f"an anchor is {conn.target.radius_km} km across — smaller than "
            "a quay, which it is not")
        return (f"{checked} anchors, every one standing off a body of its "
                "own and reachable from the helm")

    @check("a lit anchor makes a system busy")
    def _():
        # The other half of the report: "shouldn't there be a lot of activity
        # around any gates?" There should, and now there is.
        from ..sim import traffic as traffic_sim

        lit_counts, dark_counts = [], []
        for seed in range(5):
            game = new_game(f"busy-{seed}")
            for gate in weave_sim.gates(game):
                system = game.galaxy.systems[gate.system_id]
                hulls = len(traffic_sim.in_system(game, system))
                (lit_counts if gate.lit else dark_counts).append(hulls)
        assert lit_counts and dark_counts, (len(lit_counts), len(dark_counts))
        lit_mean = sum(lit_counts) / len(lit_counts)
        dark_mean = sum(dark_counts) / len(dark_counts)
        assert lit_mean > dark_mean + 0.8, (
            f"a lit anchor works {lit_mean:.1f} hulls against a dark one's "
            f"{dark_mean:.1f} — nothing is coming through it")

        # And waking one is felt where the captain is standing.
        game = _rich("busy-wake")
        dark = next(g for g in weave_sim.gates(game) if not g.lit)
        system = game.galaxy.systems[dark.system_id]
        before = len(traffic_sim.in_system(game, system))
        game.location_id = dark.system_id
        assert gates_sim.wake(game)["ok"]
        after = len(traffic_sim.in_system(game, system))
        assert after > before, (
            f"the anchor is burning and the system still works {after} hulls "
            f"against {before}")
        return (f"lit anchors work {lit_mean:.1f} hulls, dark ones "
                f"{dark_mean:.1f}; waking one took {before} to {after}")


    @check("a berth is a place, not a screen you switch to")
    def _():
        # The whole defect: a Port had no position. It could not be drawn and
        # could not be flown to, so the one view you fly from could not show
        # you the one place you most need to fly back to.
        found = missing = 0
        for system in new_game("places").galaxy.systems:
            if not system.port:
                continue
            body, index = anchorage.anchor_body(system)
            if body is None:
                missing += 1
                continue
            assert 0 <= index < len(system.bodies)
            found += 1
        assert found > 0, "no port in the sector has anywhere to be"
        assert missing == 0, f"{missing} ports have no body to orbit"
        return f"{found} ports, every one of them in orbit of a real body"

    @check("a derived berth survives time, luck and a reload unchanged")
    def _():
        # Anchorages are derived rather than stored, which is what keeps them
        # from disagreeing with the port they belong to. The price of that
        # choice is that derivation must not depend on anything that moves:
        # not the clock, not the RNG, and not whatever a reload rebuilds. A
        # quay that came back somewhere else is a quay you can never reach.
        import os
        import tempfile

        from ..core import save as save_mod
        from ..core.state import load_game

        game = new_game("stable")
        first = [(a.id, a.body_id, a.kind) for a in anchorage.in_system(game)]
        assert first, "nothing to put in at in the home system"

        for _ in range(5):
            game.advance_days(37)
            game.rng("shuffle").int(0, 99)      # luck must not move a quay
            again = [(a.id, a.body_id, a.kind)
                     for a in anchorage.in_system(game)]
            assert again == first, f"the quay moved: {first} then {again}"

        os.environ["HOME"] = tempfile.mkdtemp()
        save_mod.write({"game": game})
        back = load_game()
        assert back is not None, "the chronicle would not reload"
        after = [(a.id, a.body_id, a.kind) for a in anchorage.in_system(back)]
        assert after == first, (
            f"the quay came back somewhere else: {first} then {after}")
        return (f"{len(first)} berth(s) held still across 185 days, five RNG "
                "draws and a reload")

    @check("everything you can put in at turns up, including your own ground")
    def _():
        game, col = _with_holding("mine")
        places = anchorage.in_system(game)
        kinds = {a.kind for a in places}
        assert "quay" in kinds or "hub" in kinds, kinds
        # By its id, which `in_system` builds as `colony-<id>`. This used to
        # reach through `Anchorage.extras`, a dict written at construction and
        # read by nothing in the game — only here. A field the suite is the sole
        # reader of is still dead, which is why the declared-field guard ignores
        # the tests when it looks.
        mine = [a for a in places if a.id == f"colony-{col.id}"]
        assert mine, "a standing holding is not on the chart"
        assert mine[0].services, "the holding offers nothing at all"
        return (f"{len(places)} places: " +
                ", ".join(f"{a.name} ({a.kind})" for a in places))

    @check("a quay is reachable by exactly the machinery a body is")
    def _():
        # An anchorage's position *is* its body's, which is what lets every
        # intercept, burn profile and transfer quote work on it unchanged.
        game = new_game("fly")
        game.ship.cargo["volatiles"] = 120
        place = next(a for a in anchorage.in_system(game))
        said = anchorage.quote(game, place)
        body = game.system.bodies[place.body_index]
        assert said["days"] == flight.quote(game, body, "standard")["days"]

        before = game.day
        res = flight.travel_to(game, place.body_index, "standard")
        assert res.get("ok"), res.get("why")
        assert game.day - before == said["days"], (
            f"said {said['days']} days, took {game.day - before}")
        assert game.orbit_body == place.body_id, (
            "flew to the quay and did not arrive alongside it")

        # And the game now agrees you are there.
        again = next(a for a in anchorage.in_system(game) if a.id == place.id)
        assert again.here, "arrived at the quay and it still says you are not"
        assert anchorage.docked_at(game) is not None
        return (f"flew to {place.name} in {said['days']} days and the chart "
                "agrees you are alongside")

    @check("the helm says where the hull is standing")
    def _():
        # "I think the game starts at a shipyard but it is hard to tell, other
        # than from the shipyard window."
        game = new_game("where")
        adrift = anchorage.where_am_i(game)
        assert "edge" in adrift.lower(), adrift

        place = next(a for a in anchorage.in_system(game))
        game.orbit_body = place.body_id
        alongside = anchorage.where_am_i(game)
        assert place.name in alongside, alongside
        assert alongside != adrift
        return f"“{adrift}” → “{alongside}”"

    @check("you can ask where the nearest shipyard is")
    def _():
        game, _col = _with_holding("yards")
        yards = anchorage.offering(game, "shipyard")
        assert yards, "nowhere in the home system lays down a hull"
        spans = [anchorage.reach_to(game, a) for a in yards]
        assert spans == sorted(spans), f"not sorted by range: {spans}"
        # And something that nothing offers comes back empty rather than lying.
        assert anchorage.offering(game, "nonesuch") == []
        return (f"{len(yards)} shipyard(s) here, nearest "
                f"{yards[0].name} at {spans[0]:.2f} AU")

    @check("the helm chart draws the places, not just the planets")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        game, _col = _with_holding("draw")
        game.ship.cargo["volatiles"] = 120
        win = MainWindow(game)
        win.resize(1400, 1000)
        win.go("helm")
        for _ in range(3):
            app.processEvents()

        view = win.views["helm"]
        texts = [w.text() for w in view.findChildren(QLabel) if w.text()]
        buttons = [b.text() for b in view.findChildren(QPushButton) if b.text()]
        named = 0
        for place in anchorage.in_system(game):
            assert any(place.name in t for t in texts), (
                f"{place.name} is nowhere on the helm")
            named += 1
        assert any("course" in b.lower() or "dock" in b.lower()
                   for b in buttons), buttons
        win.close()
        return f"{named} places named on the helm, each with a control"
