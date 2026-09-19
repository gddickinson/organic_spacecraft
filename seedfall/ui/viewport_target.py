"""The thing being approached, as a camera sees it: the solid, its bracket, and
the arm coming out to take the ship.

Split out of `ui/viewport.py` when that file passed five hundred lines, along
the seam the camera already had. `Viewport` draws the *sky* — stars, the
system's star, the worlds and hulls out there — which is the same whatever the
ship is doing. This draws the *target*, which is the one object in the frame
with a range, a bracket, a berth and a boom, and the only part of the picture
that changes with the approach. It holds no rules: sizes come from the target,
attitudes from `data/models3d` and `sim/moorings`, and the boom from the flight.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient

from ..data import models3d, surfaces, worlds3d
from . import render3d, spheres, theme
from .viewport_math import HALF_FOV, _unit, project


def _detail(look: str, name: str):
    """The ground-texture hook for one body, or None where there is no kind.

    A closure rather than a list, because the lattice `surfaces.detail_near`
    walks depends on where the camera is looking and how much ground the frame
    holds — neither of which this module knows until the world is projected.
    """
    if not look:
        return None
    return lambda lat, lon, span: surfaces.detail_near(look, name, lat, lon,
                                                       span)


def model_for(conn):
    """Which mesh, and how it is oriented, for what is out there.

    `None` for a world, which is painted rather than built: see
    `ui/spheres.py`.
    """
    kind = conn.target.kind
    if kind == "body":
        # A world is not drawn from a mesh any more — `draw` sends it to
        # `ui/spheres.py`. The spin is still wanted, because the surface has
        # to turn, and a world keeps the shallow tilt it always had.
        return None, conn.elapsed / 5400.0, 0.35
    # Through the same door the sky uses, so the shape you picked out at
    # range is the shape — and the attitude — you come alongside.
    if kind == "anchorage":
        # The angle the *docking* is using, so the fitting a pilot is
        # flying at is under the fitting they can see.
        from ..sim import moorings
        shown = models3d.present("anchorage",
                                 getattr(conn.target, "berth", ""),
                                 conn.elapsed,
                                 spin=moorings.spin_at(conn.target,
                                                       conn.elapsed))
    elif kind == "hull":
        shown = models3d.present("hull",
                                 getattr(conn.target, "errand", ""),
                                 conn.elapsed)
    else:
        shown = models3d.present("anchorage", "gate", conn.elapsed)
    return shown["mesh"], shown["spin"], shown["tilt"]


def draw(view, p: QPainter, conn, cam, w: int, h: int):
    """The thing being approached, as a lit solid at its real size.

    Returns the box its reticle and label took, or None if it drew none.
    `view` is the camera drawing it, for its glare, its light and whether it
    is a thumbnail.

    It used to be a flat disc with a gradient behind it, which reads as a
    distant object at twelve kilometres and as a flat disc at six hundred
    metres — a poor thing to watch while berthing a hull against a yard.
    """
    r_km = conn.range_km
    if r_km <= 1e-9 or conn.target.radius_km <= 0:
        return          # station keeping: there is no target, only sky
    fwd, right, up = cam
    # The renderer works in the target's own frame, where the ship is at
    # `conn.pos` and the thing being approached is at the origin.
    camera = render3d.Camera(at=conn.pos, forward=fwd, up=up,
                             width=w, height=h, half_fov=HALF_FOV)
    radius = render3d.screen_radius(camera, r_km, conn.target.radius_km)
    mesh, spin, tilt = model_for(conn)

    # Far enough off to be a point of light rather than a shape.
    if radius < 2.2:
        at = project(_unit([-c for c in conn.pos]), cam, w, h)
        if at is None:
            return
        tint = QColor(theme.tint("chloro") if conn.target.kind == "body"
                      else theme.tint("lumen"))
        glow = QRadialGradient(QPointF(at[0], at[1]), 6.0)
        glow.setColorAt(0.0, QColor(tint.red(), tint.green(), tint.blue(), 220))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(glow)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(at[0], at[1]), 6.0, 6.0)
    else:
        # A ringed world in two halves, the same as the sky does it: the
        # far arc before the world and the near arc after, so the world
        # occludes the part of the ring passing behind it. Painter's
        # algorithm has no other answer to a flat annulus that
        # interpenetrates the sphere it circles.
        ringed = getattr(conn.target, "ringed", False)
        hard = view.glare(conn)
        light = view.light(conn)
        if ringed:
            render3d.draw(p, camera, worlds3d.RINGS_MESH, (0.0, 0.0, 0.0),
                          conn.target.radius_km, light,
                          spin=spin, tilt=tilt, glare=hard)
        if conn.target.kind == "body":
            look = getattr(conn.target, "look", "") or "rocky"
            name = getattr(conn.target, "name", "")
            spheres.draw(p, camera, worlds3d.paint_for(look),
                         (0.0, 0.0, 0.0), conn.target.radius_km, light,
                         spin=spin, tilt=tilt, glare=hard,
                         features=surfaces.features_for(look, name),
                         stretch=surfaces.stretch_for(look),
                         detail=_detail(look, name))
        else:
            render3d.draw(p, camera, mesh, (0.0, 0.0, 0.0),
                          conn.target.radius_km, light,
                          spin=spin, tilt=tilt, glare=hard)
            boom(p, camera, conn)
        if ringed:
            render3d.draw(p, camera, worlds3d.RINGS_FRONT, (0.0, 0.0, 0.0),
                          conn.target.radius_km, light,
                          spin=spin, tilt=tilt, glare=hard)

    if view.compact:
        return
    # **Only on the camera that can actually see it.** `project` returns
    # None for a direction behind the lens, and this used to fall back to
    # the centre of the frame — so berthing a hull at 998 m drew a dashed
    # bracket labelled "Fleet Hub · 998 m" in the middle of *all six*
    # feeds, with the hub visible in exactly one of them. On the dorsal
    # camera the bracket sat on top of a planet and named it as the quay.
    #
    # Found by rendering the six feeds as a contact sheet and looking at
    # it. No figure could have shown it: every number on every feed was
    # right, and five of the six pictures were a lie about where the thing
    # was. A reticle is a claim about direction, so it may only be drawn
    # where the direction lands.
    toward = project(_unit([-c for c in conn.pos]), cam, w, h)
    if toward is None:
        return
    sx, sy = toward[0], toward[1]
    # A bracket and the range, so the main screen is readable on its own.
    # **Capped to the frame**: at a standoff berth the hull holds station
    # a few tens of metres off a structure that fills the view, and a
    # bracket sized to its screen radius came out wider than the window —
    # a dashed line straight across the picture, marking nothing.
    box = max(min(radius + 14, min(w, h) * 0.42), 18)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(theme.tint("warn")), 1.2, Qt.PenStyle.DashLine))
    p.drawRect(QRectF(sx - box, sy - box, box * 2, box * 2))
    p.setPen(QColor(theme.INK2))
    p.setFont(QFont(theme.mono_family(), 9))
    span = (f"{r_km * 1000:,.0f} m" if r_km < 2 else f"{r_km:,.1f} km")
    said = f"{conn.target.name} · {span}"
    p.drawText(QPointF(sx - box, sy - box - 6), said)
    # The pixels this has used, so `draw_sights` can keep off them: a sight
    # label ran into this bracket at 130.3 km, measured on the aft camera.
    room = p.fontMetrics().horizontalAdvance(said)
    return (sx - box, sy - box - 6 - p.fontMetrics().ascent(),
            max(sx + box, sx - box + room), sy + box)


def boom(p: QPainter, camera, conn) -> None:
    """The arm coming out to take the ship, at a standoff berth.

    **Drawn because it is real.** `sim/moorings.boom_step` runs it out
    while the hull holds station and back in when it drifts, and a
    manoeuvre whose whole content is *hold still while this happens*
    cannot be flown off a percentage in a table. It reaches from the
    gantry it is hinged on toward the berth, as far as it has got.
    """
    from ..data.berths3d import hinge_points
    from ..sim import moorings

    # Belt and braces, knowingly: `moorings.boom_step` already zeroes the
    # boom at anything that is not a standoff, so removing this line draws
    # nothing anywhere and no check moves. Kept because the window should
    # not depend on the sim's housekeeping to avoid drawing a gantry arm
    # on a quay that has none.
    if moorings.sort_of(conn.target) != "standoff":
        return
    out = float(getattr(conn, "boom", 0.0) or 0.0)
    if out <= 0.0:
        return
    want = getattr(conn, "berth", "")
    sort = getattr(conn.target, "berth", "") or ""
    scale = float(conn.target.radius_km or 0.0)
    spin = moorings.spin_at(conn.target, conn.elapsed)
    # Through the model's *whole* rotation, the same door the mesh and the
    # berths go through. Rotating the hinge by spin alone put the arm's
    # root off the structure it is bolted to by the tilt, which is the
    # fault `models3d.place` exists to make impossible.
    tilt = models3d.attitude_of("anchorage", sort)[1]
    berths = dict(moorings.points(conn.target, spin))
    for name, at in hinge_points(sort):
        if name != want or name not in berths:
            continue
        hinge = render3d.place(tuple(c * scale for c in at), spin, tilt)
        far = berths[name]
        tip = tuple(h + (f - h) * out for h, f in zip(hinge, far))
        here, there = camera.project(hinge), camera.project(tip)
        if here is None or there is None:
            return
        tint = QColor(theme.tint("lumen" if out >= 1.0 else "amber"))
        p.setPen(QPen(tint, 2.4 if out >= 1.0 else 1.8))
        p.drawLine(here[0], there[0])
        p.setBrush(tint)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(there[0], 3.2, 3.2)
        return
