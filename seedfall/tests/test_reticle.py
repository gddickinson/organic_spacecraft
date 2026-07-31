"""A reticle is a claim about direction, and may only be drawn where it lands.

Found by rendering the conn's six camera feeds as one contact sheet, a
kilometre off a Fleet Hub, and looking at it. The quay was in the fore view
and in no other — and **all six feeds carried a dashed bracket labelled
"Fleet Hub · 998 m" in the middle of the frame**. On the dorsal camera the
bracket sat on top of a planet and named it as the quay.

`render3d.project` returns None for a direction behind the lens. The bracket
fell back to the centre of the frame when it did:

    sx, sy = w * 0.5, h * 0.5
    toward = project(...)
    if toward is not None:
        sx, sy = toward

No figure could have shown this. Every number on every feed was correct — the
range was 998 m, the target was Fleet Hub — and five of the six *pictures*
were a lie about where it was. The claims here are therefore all read off
rendered pixels:

- **The bracket appears only where the target does.** One feed of six, and it
  is the one the hub is actually in.
- **It follows the geometry**, not the name of a camera: put the quay on the
  beam and the bracket moves to the beam camera and leaves the bow.
- **It is on the target**, not merely somewhere in the frame — within the
  hub's own drawn extent.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import autopilot as pilot_sim
from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from ..sim import flight
from ..sim import track as track_sim
from .harness import Suite

#: Held at module scope: a `keep = _app()` local dies when its helper returns,
#: and if it was the last reference Qt takes every widget down with it.
_HELD = None


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    global _HELD
    _HELD = QApplication.instance() or QApplication([])
    assert _HELD is not None
    return _HELD


def _closed_in(seed: str = "dock", to_km: float = 1.0):
    """A real approach, flown by the computer down to `to_km`."""
    game = new_game(seed)
    flight.travel_to(game, 0)
    quay = next(c for c in track_sim.contacts(game) if c.kind == "anchorage")
    conn, why = berth_sim.begin(game, quay)
    assert conn is not None, why
    for _ in range(400):
        if conn.over or conn.range_km <= to_km:
            break
        axis, main, throttle = pilot_sim.autopilot(conn, "close")
        conn_sim.apply(conn, axis, main=main, throttle=throttle)
    return game, conn


#: How wide a run of warn-tinted pixels has to be before it is *the bracket*
#: rather than something warn-coloured in the picture. The bracket is a dashed
#: rectangle at least a couple of hundred pixels across; a quay's docking
#: light is a lit box a pixel or two wide, and it is drawn in the same tint —
#: `data/berths3d.quay` ends its arm in `WARN` on purpose, because that is
#: what a docking light looks like.
#:
#: This exists because counting bare pixels could not tell them apart. One
#: stray lit pixel in the port feed read as "the bracket is on two cameras"
#: and failed a check that was right about everything it claimed. Measured on
#: the frame that found it: the bracket spans 219 px, the docking light 0.
BRACKET_SPAN = 20


def _bracket_pixels(conn, view_id: str, size=(380, 240)) -> set:
    """Where the warn-tinted bracket lands in one feed, as pixels.

    Read off the rendered image rather than asked of the drawing code: the
    fault was that the code drew it, correctly, in the wrong place.
    """
    from PyQt6.QtGui import QColor
    from ..ui import theme
    from ..ui.viewport import Viewport

    keep = _app()
    assert keep is not None
    feed = Viewport(conn, view_id)
    feed.resize(size[0], size[1])
    image = feed.grab().toImage()
    want = QColor(theme.tint("warn"))
    out = set()
    for y in range(image.height()):
        for x in range(image.width()):
            got = image.pixelColor(x, y)
            if (abs(got.red() - want.red()) < 30
                    and abs(got.green() - want.green()) < 30
                    and abs(got.blue() - want.blue()) < 30):
                out.add((x, y))
    return out


def _bracketed(conn, view_id: str) -> bool:
    """Is *the bracket* in this feed — not merely a warn-tinted pixel?"""
    found = _bracket_pixels(conn, view_id)
    if not found:
        return False
    xs = [x for x, _y in found]
    ys = [y for _x, y in found]
    return max(max(xs) - min(xs), max(ys) - min(ys)) >= BRACKET_SPAN


def run(suite: Suite) -> None:
    check = suite.check

    @check("the target bracket is drawn only where the target is")
    def _():
        # Measured before the fix: 6 feeds of 6 carried the bracket, with the
        # hub visible in one. After: 1 of 6.
        game, conn = _closed_in()
        assert conn.range_km < 2.0, conn.range_km
        marked = {view: len(_bracket_pixels(conn, view))
                  for view, _label, _vec in conn_sim.VIEWS}
        showing = [view for view, _l, _v in conn_sim.VIEWS
                   if _bracketed(conn, view)]
        assert showing == ["fore"], (
            f"the quay is dead ahead and the bracket is on {showing}: {marked}")
        return (f"{conn.range_km * 1000:.0f} m off a hub: the bracket is on "
                f"{len(showing)} feed of {len(marked)}, and it is the one the "
                "quay is in")

    @check("the bracket follows the geometry, not the name of a camera")
    def _():
        # Turned broadside on by hand — this is a claim about the renderer,
        # so the pose is set rather than flown. If the bracket were pinned to
        # the bow it would stay on `fore` through this; if it were pinned to
        # the frame centre it would be on all six.
        game, conn = _closed_in()
        bow = {view for view, _l, _v in conn_sim.VIEWS
               if _bracketed(conn, view)}
        # The ship is at (0, -r, 0) with its nose along +y, so the quay is
        # dead ahead. Point the nose along +x and the quay is off to port.
        conn.nose = [1.0, 0.0, 0.0]
        beam = {view for view, _l, _v in conn_sim.VIEWS
                if _bracketed(conn, view)}
        assert bow == {"fore"}, bow
        assert beam and beam != bow, (
            f"the nose came 90° round and the bracket stayed on {beam}")
        assert "fore" not in beam, (
            f"the quay is on the beam and the bow camera still brackets it: "
            f"{beam}")
        return f"nose on the target: {sorted(bow)} · nose 90° off: {sorted(beam)}"

    @check("the bracket sits on the target, not merely in the frame")
    def _():
        # A bracket in the right *feed* and the wrong place passes both checks
        # above. Two mutations proved it: nailing the bracket to the middle of
        # the frame, and offsetting it 90 px from where the target projects.
        #
        # The first draft caught neither, for two reasons worth writing down.
        # It compared the bracket's centre against the centre of every lit
        # pixel — **including the bracket's own**, which drags the target's
        # centroid toward the bracket and flatters any offset. And it measured
        # a bow-on approach, where the target projects 10 px from the middle
        # of the frame, so "nailed to the centre" and "on the target" are the
        # same picture.
        #
        # Measured with the nose 30° off, which is where those two part
        # company: the target lands 79 px from the frame's centre.
        #
        # **And against the target, not against everything bright.** The
        # second draft compared the bracket with the centroid of every lit
        # pixel that was not warn-tinted, calling that "the hull". A
        # kilometre off a hub the frame also holds a starfield and a planet:
        # measured, those "hull" pixels spanned 0–378 by 0–239, which is the
        # whole picture. The centroid of the whole picture is not the target,
        # and the 60 px it was allowed was slop tuned to one frame — it moved
        # to 70 the moment the structure's attitude was corrected. So the
        # target's centre is *projected* through the same camera the window
        # builds, which is a place the drawing code has no say in.
        import math

        from PyQt6.QtGui import QColor
        from ..ui import render3d, theme
        from ..ui import viewport as viewport_ui

        game, conn = _closed_in()
        # **Off the bearing to the target, not off a fixed vector.** This used
        # to set `nose = [0.5, 0.866, 0]`, which was 30° off the target for
        # the pose that approach happened to end in. Change anything upstream
        # and it is 30° off nothing in particular: measured after the berths
        # were corrected for the model's tilt, the target projected to y=291
        # in a 240 px frame — off the bottom of the picture — and the check
        # was comparing a bracket that was mostly not drawn. So the angle is
        # taken from where the target actually is, and 20° of the 31° half
        # field of view keeps it well inside the frame and well off centre.
        u = viewport_ui._unit([-c for c in conn.pos])
        side = viewport_ui._unit(viewport_ui._cross(u, (0.0, 0.0, 1.0)))
        lean = math.radians(20.0)
        conn.nose = [u[i] * math.cos(lean) + side[i] * math.sin(lean)
                     for i in range(3)]
        keep = _app()
        assert keep is not None
        wide, high = 380, 240
        feed = viewport_ui.Viewport(conn, "fore")
        feed.resize(wide, high)
        image = feed.grab().toImage()
        warn = QColor(theme.tint("warn"))
        marks = []
        for y in range(image.height()):
            for x in range(image.width()):
                got = image.pixelColor(x, y)
                if (abs(got.red() - warn.red()) < 55
                        and abs(got.green() - warn.green()) < 55
                        and abs(got.blue() - warn.blue()) < 55):
                    marks.append((x, y))
        assert len(marks) > 40, (
            f"{len(marks)} warn-tinted pixels — no bracket to speak of")
        _vid, _label, vec = feed.view
        cam = viewport_ui.basis(vec, conn)
        camera = render3d.Camera(at=conn.pos, forward=cam[0], up=cam[2],
                                 width=wide, height=high,
                                 half_fov=viewport_ui.HALF_FOV)
        seen = camera.project((0.0, 0.0, 0.0))   # the target's own centre
        assert seen is not None, "the target does not project into this feed"
        assert 0 <= seen[0].x() < wide and 0 <= seen[0].y() < high, (
            f"the target projects to {seen[0].x():.0f},{seen[0].y():.0f}, "
            "outside the frame — there is nothing here to check")
        # **The bracket's own box, not the average of its pixels.** It is a
        # rectangle drawn around the target: the middle of its extent is its
        # centre, while the mean of whichever dashes happen to survive the
        # tint test is wherever those dashes are.
        xs = [x for x, _y in marks]
        ys = [y for _x, y in marks]
        mark_x = (min(xs) + max(xs)) / 2
        mark_y = (min(ys) + max(ys)) / 2
        gap = math.hypot(mark_x - seen[0].x(), mark_y - seen[0].y())
        from_centre = math.hypot(mark_x - wide / 2, mark_y - high / 2)
        assert gap < 30, (
            f"the bracket's centre is {gap:.0f} px from where the target "
            "projects — it is bracketing empty space")
        assert from_centre > 40, (
            f"the target is off the bore and the bracket is {from_centre:.0f} "
            "px from the middle of the frame — it is nailed to the centre "
            "rather than following the target")
        return (f"nose 20° off: the bracket lands {gap:.0f} px from where the "
                f"target projects and {from_centre:.0f} px off frame centre")
