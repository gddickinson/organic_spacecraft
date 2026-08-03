"""Collisions are allowed. They have to be meant.

The player: "have the auto-pilot attempt to prevent collisions when it can …
if you want to ram something or crash land you need to override … there
should be collision alerts and automatic safety guards that need to be
removed."

So there are three separate claims to hold, and they pull against each other:

* the computer **brakes** rather than flying her into something it could
  still have stopped for;
* the screens **say so first**, while there is still room to act;
* and none of it stands in the way of a captain who means it — ramming a
  hull, cutting a collar, putting her down on a world.
"""

from __future__ import annotations

import dataclasses
import math

from ..core.state import new_game
from ..sim import anchorage as anchorage_sim
from ..sim import berthing as berth_sim
from ..sim import collision
from ..sim import conn as conn_sim
from ..sim import flightdeck as deck_sim
from ..sim import freeflight as free_sim
from ..sim import track as track_sim
from .harness import Suite


def _running_at(gap_km: float, speed: float = 40.0, seed: str = "coll"):
    """A free flight running for a mark with something `gap_km` in the way."""
    game = new_game(seed)
    conn, why = free_sim.begin(game)
    assert conn is not None, why
    game.conn = conn
    conn.rcs = 60.0
    hull = next(c for c in track_sim.contacts(game) if c.kind == "hull")
    conn.mark, conn.auto = hull.name, "run"
    vec = free_sim.toward(game, conn, hull)
    span = math.dist(vec, (0.0, 0.0, 0.0)) or 1.0
    unit = [c / span for c in vec]
    seed_sight = next(s for s in conn.sky if s.kind == "anchorage")
    rock = dataclasses.replace(
        seed_sight, name="Obstacle", radius_km=2.0,
        at=tuple(p + u * gap_km for p, u in zip(conn.pos, unit)))
    conn.sky = list(conn.sky) + [rock]
    conn.vel = [u * speed for u in unit]
    return game, conn, unit


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing is said while there is room, and everything when there is not")
    def _():
        # The reading that matters is not the range but whether she can still
        # be stopped in it: `v²/2a` against the room left. It goes from yes to
        # no while every other number still looks calm, which is exactly why a
        # pilot cannot be left to work it out.
        seen = {}
        for gap in (60.0, 30.0, 20.0):
            _game, conn, _unit = _running_at(gap)
            threat = collision.scan(None, conn)
            seen[gap] = threat.level if threat is not None else "clear"
        assert seen[60.0] == "clear", seen
        assert seen[30.0] == "watch", seen
        assert seen[20.0] == "imminent", seen
        # And it says it in words a captain can act on.
        _game, conn, _unit = _running_at(20.0)
        said = collision.line(collision.scan(None, conn))
        assert "COLLISION" in said and "Obstacle" in said, said
        return (f"60 km {seen[60.0]} · 30 km {seen[30.0]} · 20 km "
                f"{seen[20.0]}, and the words to go with it")

    @check("the computer brakes for what it can still stop for")
    def _():
        # Armed and running for a mark with something in the way: the burn
        # this tick is the one that sheds the excess, whatever the mode
        # wanted. With the safeties off it is the mode's own burn again —
        # that is the override, and it is the whole of it.
        _game, conn, unit = _running_at(20.0)
        conn.safeties = True
        guarded = deck_sim.computer(_game, conn)
        conn.safeties = False
        free = deck_sim.computer(_game, conn)
        assert guarded[0] is not None, "the computer did nothing about it"
        push = conn_sim.thrust_axis(conn, guarded[0], guarded[1])
        toward = sum(a * b for a, b in zip(push, unit))
        assert toward < -0.5, (
            f"the guarded burn pushes {toward:+.2f} along the hazard bearing "
            "— it is not braking")
        assert guarded[0] != free[0], (
            "the safeties changed nothing about what the computer flew")
        return (f"guarded burn {guarded[0]!r} at {toward:+.2f} along the "
                f"bearing; unguarded {free[0]!r}")

    @check("a hand-burn into something unstoppable is refused, with the reason")
    def _():
        _game, conn, _unit = _running_at(20.0)
        threat = collision.scan(None, conn)
        assert threat.level == "imminent", threat.level
        into = next(a for a in ("forward", "back", "left", "right", "up",
                                "down")
                    if sum(x * y for x, y in zip(
                        conn_sim.thrust_axis(conn, a, False),
                        collision._bearing(conn, threat))) > 0.5)
        ok, why = collision.allow_burn(conn, into, False, threat)
        assert not ok, "a burn straight into it was allowed"
        assert "Safeties" in why and "Obstacle" in why, why
        # Away from it is always allowed — the guard is not a cage.
        away = next(a for a in ("forward", "back", "left", "right", "up",
                                "down")
                    if sum(x * y for x, y in zip(
                        conn_sim.thrust_axis(conn, a, False),
                        collision._bearing(conn, threat))) < -0.5)
        assert collision.allow_burn(conn, away, False, threat)[0]
        # And with the safeties off nothing is refused at all.
        conn.safeties = False
        assert collision.allow_burn(conn, into, False, threat)[0], (
            "the safeties were off and the burn was still refused")
        return f"{into!r} refused, {away!r} allowed, and nothing refused off"

    @check("a contact that was ordered is not argued with")
    def _():
        # Three deliberate acts, and the guard must be silent through all of
        # them: putting her down on a world, cutting into a berth, and flying
        # a bay's corridor — which is contact by invitation.
        game = new_game("coll-mean")
        places = anchorage_sim.in_system(game)
        assert places
        game.orbit_body = game.system.bodies[places[0].body_index].id
        quay = next(c for c in track_sim.contacts(game)
                    if c.kind == "anchorage"
                    and berth_sim.can_conn(game, c)[0])
        conn, why = berth_sim.begin(game, quay)
        assert conn is not None, why
        conn.vel = [0.0, 60.0, 0.0]            # straight at it, far too fast
        assert collision.scan(game, conn) is not None, (
            "a hull driven at a quay raised no warning at all")
        conn.forcing = True
        assert collision.scan(game, conn) is None, (
            "the guard argued with an ordered cut")
        conn.forcing, conn.ditching = False, True
        assert collision.scan(game, conn) is None, (
            "the guard argued with an ordered descent")
        return "warned unbidden; silent through a cut and a descent"

    @check("every flying screen can see it")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QPushButton
        app = QApplication.instance() or QApplication([])
        assert app is not None
        from ..sim import instruments as panel_sim
        from ..ui.viewport import basis
        from ..ui import viewport_hud
        _game, conn, _unit = _running_at(20.0)
        rows = {name: value for name, value, _k in panel_sim.readout(conn)}
        assert "Collision" in rows, sorted(rows)
        assert "Obstacle" in rows["Collision"], rows["Collision"]
        # and out of the window, where a pilot is actually looking
        cam = basis((0.0, 1.0, 0.0), conn)
        got = viewport_hud.points(conn, cam, 464, 320)
        assert got["threat"] is not None, "no warning drawn in the window"
        # the safeties have a control, and it says which way it is set
        conn.safeties = False
        rows = {name: value for name, value, _k in panel_sim.readout(conn)}
        assert "Safeties" in rows and "OFF" in rows["Safeties"], rows
        from ..ui.conn_window import ConnWindow
        from ..ui.window import MainWindow
        win = MainWindow(_game)
        win.toast = lambda *a, **k: None
        win.dialog = lambda *a, **k: None
        window = ConnWindow(win)
        names = {b.objectName() for b in window.findChildren(QPushButton)}
        assert "safeties" in names, "no way to turn the safeties off"
        window.close()
        return "a panel row, a mark in the window, and a control for it"

    return True
