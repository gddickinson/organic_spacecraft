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


def run(suite: Suite) -> None:
    check = suite.check

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
        mine = [a for a in places if a.extras.get("colony") == col.id]
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
