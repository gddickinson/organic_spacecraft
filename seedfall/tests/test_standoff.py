"""A berth that stands off the structure, and the arm that comes out to it.

Every berth was a fitting on a hull: you flew at it and made fast. A holding
is a bonded store on a frame of tanks — nothing about it wants a freighter's
nose in among them — and its four gantry stubs are exactly what a boom would
swing from. So it offers a **standoff**: the hull holds station in open space
off the end of an arm, and the arm comes out and takes it.

The claims:

- **The berth is off the structure**, not on it, so a ship at one never
  touches the hull.
- **Holding still is the manoeuvre.** The boom runs out while the hull is in
  reach and steady and runs back in when it is not, so this is
  station-keeping rather than a threshold to cross.
- **Near and slow is not enough.** Everything a fitting asks for can be true
  and the ship is still not moored until the arm has it.
- **The structure says which act it is.** A standoff's clearance gives a
  different instruction and a tighter rate, because it is a different thing
  to do.
- **It is drawn**, because a manoeuvre whose whole content is *hold still
  while this happens* cannot be flown off a percentage in a table.
"""

from __future__ import annotations

import dataclasses
import math

from ..core.state import new_game
from ..sim import autopilot as pilot_sim
from ..sim import clearance as clearance_sim
from ..sim import conn as conn_sim
from ..sim import flight
from ..sim import moorings
from ..sim import outcome as outcome_sim
from ..sim import track as track_sim
from .harness import Suite

_HELD = None


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    global _HELD
    _HELD = QApplication.instance() or QApplication([])
    return _HELD


def _standoff(seed: str = "boom"):
    """An approach on a holding, which is the sort with booms."""
    game = new_game(seed)
    flight.travel_to(game, 0)
    quay = next(c for c in track_sim.contacts(game) if c.kind == "anchorage")
    conn = conn_sim.start(game, dataclasses.replace(quay, berth="holding"))
    return game, conn


def run(suite: Suite) -> None:
    check = suite.check

    @check("a standoff berth is off the structure, not on it")
    def _():
        game, conn = _standoff()
        assert moorings.sort_of(conn.target) == "standoff"
        found = moorings.nearest(conn)
        out = math.dist(found["at"], (0.0, 0.0, 0.0))
        assert out > conn.target.radius_km, (
            f"the berth is {out:.3f} km out and the hull is "
            f"{conn.target.radius_km:.3f} — a ship at it would be inside the "
            "tank frame")
        # And the boom is hinged *on* the structure, which is the other end.
        from ..data.berths3d import berth_points, hinge_points
        hinge = dict(hinge_points("holding"))[found["name"]]
        assert math.dist(hinge, (0.0, 0.0, 0.0)) < 1.0, hinge
        assert math.dist(dict(berth_points("holding"))[found["name"]],
                         (0.0, 0.0, 0.0)) > 1.0
        # A fitting is not a standoff, so the distinction is a real one.
        assert moorings.sort_of(dataclasses.replace(
            conn.target, berth="hub") if hasattr(conn.target, "berth")
            else conn.target) in ("fitting", "standoff")
        return (f"the berth is {out * 1000:,.0f} m out of a "
                f"{conn.target.radius_km * 1000:,.0f} m hull, and the boom is "
                "hinged on the frame")

    @check("holding still is the manoeuvre, and drifting undoes it")
    def _():
        game, conn = _standoff()
        found = moorings.nearest(conn)
        conn.pos = list(found["at"])
        conn.vel = [0.0, 0.0, 0.0]
        # Steady: it comes out, and takes the time it takes.
        for _ in range(200):
            if conn.boom >= 1.0:
                break
            moorings.boom_step(conn, 1.0)
        assert conn.boom >= 1.0, conn.boom
        took = moorings.BOOM_SECONDS
        assert took > 30.0, took
        # Now shove the hull: the arm goes back in.
        conn.vel = [moorings.hold_rate(conn.target) * 4.0, 0.0, 0.0]
        for _ in range(20):
            moorings.boom_step(conn, 1.0)
        assert conn.boom < 1.0, (
            "the hull is moving four times the rate the arm can catch and the "
            "boom is still out")
        # Steady again and it comes back out: this is station-keeping, not a
        # threshold that latches.
        conn.vel = [0.0, 0.0, 0.0]
        for _ in range(200):
            if conn.boom >= 1.0:
                break
            moorings.boom_step(conn, 1.0)
        assert conn.boom >= 1.0
        return (f"out in {took:.0f} s of holding under "
                f"{moorings.hold_rate(conn.target):.2f} m/s, back in when it "
                "drifts, out again when it steadies")

    @check("near and slow is not moored until the arm has you")
    def _():
        # Everything a *fitting* asks for, and still not alongside.
        game, conn = _standoff()
        found = moorings.nearest(conn)
        conn.pos = list(found["at"])
        conn.vel = [0.0, 0.0, 0.0]
        conn.boom = 0.0
        assert moorings.at_berth(conn), "not even at the berth"
        assert conn.range_km <= conn_sim.ALONGSIDE_KM + conn.target.radius_km
        assert conn.speed <= conn_sim.ALONGSIDE_RATE
        assert not outcome_sim.alongside(conn, conn_sim.ALONGSIDE_KM,
                                         conn_sim.ALONGSIDE_RATE), (
            "a hull holding in open space off a gantry, with nothing made "
            "fast, was called moored")
        conn.boom = 1.0
        assert outcome_sim.alongside(conn, conn_sim.ALONGSIDE_KM,
                                     conn_sim.ALONGSIDE_RATE)
        return "at the berth, stopped, and not moored until the boom is out"

    @check("the structure says which act it is, and it is a different one")
    def _():
        game = new_game("boom-say")
        flight.travel_to(game, 0)
        quay = next(c for c in track_sim.contacts(game)
                    if c.kind == "anchorage")
        fitting = clearance_sim.request(
            game, dataclasses.replace(quay, berth="hub"))
        standoff = clearance_sim.request(
            game, dataclasses.replace(quay, berth="holding"))
        assert fitting.granted and standoff.granted
        assert fitting.sort == "fitting" and standoff.sort == "standoff"
        # A tighter rate, because a boom has to catch what a fitting is
        # merely arrived at — and it is stated, not implied.
        assert standoff.max_closing < fitting.max_closing, (
            standoff.max_closing, fitting.max_closing)
        said = clearance_sim.line(standoff)
        assert "hold station" in said.lower() and "come out" in said.lower(), \
            said
        assert "hold at" not in said.lower(), (
            "a standoff was given a fitting's instruction")
        return (f"fitting {fitting.max_closing:.2f} m/s against standoff "
                f"{standoff.max_closing:.2f}; “{said.split('.')[0][-58:]}”")

    @check("the boom is drawn as far out as it has actually come")
    def _():
        # **Reach, not brightness.** This first counted lit pixels in the whole
        # frame: 26 with the arm in, 43 at half, 63 at full, and the rising
        # numbers looked like an arm coming out. They were not. A mutation that
        # drew the tip at the berth *whatever* `conn.boom` said — an arm always
        # at full stretch — passed it, 44 against 43, because the count was
        # mostly reading the change of tint and pen at capture (amber 1.8 px
        # while it travels, lumen 2.4 px once it has you) rather than length.
        #
        # So the picture is asked the question the code claims to answer: walk
        # the arm's own path, from the gantry it is hinged on to the berth, and
        # find the furthest point along it that is lit. The path comes from the
        # data — `hinge_points` and `moorings.points` — through the same camera
        # the window builds, so the drawing has no say in where it is looked
        # for. Measured: 0.25 out reads 0.32, 0.50 reads 0.56, 0.75 reads 0.82,
        # 1.0 reads 1.00. The bias is the tip's own dot; the tolerance covers
        # it and is still nowhere near half a boom.
        from PyQt6.QtGui import QColor
        from ..data.berths3d import hinge_points
        from ..ui import render3d, theme
        from ..ui import viewport as viewport_ui

        keep = _app()
        assert keep is not None
        game, conn = _standoff()
        found = moorings.nearest(conn)
        conn.berth = found["name"]
        # **Side on, not from the berth.** Sitting the camera at the fitting
        # points the arm straight down the lens, where a boom half out and a
        # boom fully out are the same handful of pixels — measured, 7 samples
        # either way. It is drawn reaching *across* the picture, so that is
        # where the check has to stand to see it. Far enough out, too, that the
        # whole arm is in frame: at three radii the berth end fell 28 px below
        # a 300-px window and the outer quarter could not be seen at all.
        at = found["at"]
        span = math.dist(at, (0.0, 0.0, 0.0)) or 1.0
        side = (-at[1] / span, at[0] / span, 0.0)
        conn.pos = [c * conn.target.radius_km * 4.5 for c in side]
        conn.vel = [0.0, 0.0, 0.0]
        # And **looking at it**: the fore camera points along the nose, and
        # moving a hull does not turn it. Without this the frame was a
        # starfield and a slice of the world, with the structure and its arm
        # off to one side entirely.
        away = math.dist(conn.pos, (0.0, 0.0, 0.0)) or 1.0
        conn.nose = [-c / away for c in conn.pos]

        wide, high = 420, 300
        feed = viewport_ui.Viewport(conn, "fore")
        feed.resize(wide, high)
        _vid, _label, vec = feed.view
        cam = viewport_ui.basis(vec, conn)
        camera = render3d.Camera(at=conn.pos, forward=cam[0], up=cam[2],
                                 width=wide, height=high,
                                 half_fov=viewport_ui.HALF_FOV)
        spin = moorings.spin_at(conn.target, conn.elapsed)
        berths = dict(moorings.points(conn.target, spin))
        scale = conn.target.radius_km
        turn = math.cos(spin), math.sin(spin)
        hinge = next(
            ((x * turn[0] - y * turn[1], x * turn[1] + y * turn[0], z)
             for name, place in hinge_points(conn.target.berth)
             if name == conn.berth
             for x, y, z in [tuple(c * scale for c in place)]), None)
        assert hinge is not None, "the assigned berth has no gantry to hinge on"
        ends = camera.project(hinge), camera.project(berths[conn.berth])
        assert all(e is not None for e in ends), "the arm is not in the frame"
        (x0, y0), (x1, y1) = ((e[0].x(), e[0].y()) for e in ends)

        tints = [QColor(theme.tint("amber")), QColor(theme.tint("lumen"))]

        def reach(out: float) -> float:
            """How far along the arm's path the picture is lit, 0 to 1."""
            conn.boom = out
            image = viewport_ui.Viewport(conn, "fore")
            image.resize(wide, high)
            shot = image.grab().toImage()
            for step in range(100, -1, -1):
                along = step / 100.0
                cx = x0 + (x1 - x0) * along
                cy = y0 + (y1 - y0) * along
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        px, py = int(cx + dx), int(cy + dy)
                        if not (0 <= px < wide and 0 <= py < high):
                            continue
                        got = shot.pixelColor(px, py)
                        if any(abs(got.red() - t.red()) < 40
                               and abs(got.green() - t.green()) < 40
                               and abs(got.blue() - t.blue()) < 40
                               for t in tints):
                            return along
            return 0.0

        rows = []
        for out in (0.0, 0.25, 0.5, 0.75, 1.0):
            drawn = reach(out)
            assert abs(drawn - out) < 0.12, (
                f"the boom {out:.0%} out is drawn {drawn:.0%} of the way to "
                "the berth")
            rows.append(f"{out:.0%}→{drawn:.0%}")
        return "commanded against drawn, along the arm: " + " · ".join(rows)
