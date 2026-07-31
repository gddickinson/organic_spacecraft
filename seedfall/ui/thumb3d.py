"""A small rendered portrait, for the catalogue to actually show something.

The Codex's "Fleet classes" tab lists **thirty-five hull classes** — name,
binomial, tier, blurb, role, crew, mass, hull, hold, jump, build time — and not
one picture. Nor do the nineteen colony and station classes. The catalogue
screen is the one place in the game whose whole job is to show you the
catalogue, and it was a wall of text sitting on top of five hull silhouettes,
four berths, nine star classes and seven kinds of world that the sky had been
drawing for cycles.

So: a widget that renders one subject at a readable size, on the same renderer
everything else uses. `ui/render3d.py` for meshes, `ui/spheres.py` for worlds,
`ui/stars3d.py` for stars — no second drawing path, so a hull in the codex and
the same hull on the tactical plot are the same ship.

Deliberately small and still. A catalogue is read, not flown: there is no
animation, no timer, and one repaint per card.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..data import berths3d, hulls3d, models3d, surfaces, worlds3d
from . import render3d, spheres, stars3d

#: How the portrait is framed. A hull is authored at half-length 1, so it is
#: two units end to end plus its furniture, and the first framing at 3.4 cut
#: the docking ridge off the top of every card. Far enough back that the whole
#: ship fits with room to breathe.
SUBJECT_AT = 5.0
HALF_FOV = math.radians(29)

#: Where a holding of your own sits. Closer than a hull, because a work is
#: authored about a unit across rather than two, and at `SUBJECT_AT` the
#: nineteen came out as models on a shelf at the far end of the card.
#:
#: Measured rather than eyeballed: the tallest of the nineteen through its own
#: attitude is a SOL-FORGE at 1.25 units off the axis, and at this range the
#: frame's half-height is 1.50 — so the biggest fills 83% of the card and
#: nothing clips. At 2.4 the mirror lost its rim.
WORK_AT = 2.7

#: Where a machine sits, and how it is held. Authored about a unit tall, so
#: closer than a work; the tilt is `models3d.ATTITUDE["work"]`'s, because the
#: same argument applies — a thing with a head and feet has a right way up, and
#: a positive tilt puts its head at the bottom of the card.
ROBOT_AT = 2.1
ROBOT_TILT = -1.32
ROBOT_SPIN = 0.7

#: Where a xenoform sits. Authored about a unit across, and held a little more
#: side-on than a machine: most of these are wider than they are tall, and a
#: mat seen from directly above is a disc.
LIFE_AT = 2.0
LIFE_TILT = -1.05
LIFE_SPIN = 0.55

#: The void a portrait is drawn against. `theme.TINTS` has no key for it —
#: `theme.tint("void")` falls back to a *light* ink, which is how the first
#: draft came out with every hull on a pale grey card.
VOID = "#05070a"

#: Where the light comes from, in the tile's own frame. Over the viewer's left
#: shoulder: the one direction that gives a hull a lit face, a shaded face and
#: a rim, which is what makes a picture of a solid read as a solid.
LIGHT = (-0.55, -0.40, 0.72)

#: How a hull is held. Broadside, because a ship is a profile — the same
#: reasoning, and very nearly the same number, as `models3d.ATTITUDE`.
HULL_TILT = 1.24
HULL_SPIN = 0.62

#: How far a star's corona may reach on a card, as a share of the tile's
#: shorter side. Uncapped it runs to eleven disc radii, which on a tile this
#: size is still tinted at the corner — so each class sat on a card of a
#: different colour, and the page read as a layout fault rather than as light.
GLOW_SHARE = 0.46

#: A world is shown gibbous rather than full: a terminator is what says
#: "sphere" and a fully lit disc is what says "circle".
WORLD_LIGHT = (-0.72, -0.28, 0.36)


class Thumb(QWidget):
    """One catalogue portrait: a hull class, a berth, a world or a star."""

    def __init__(self, kind: str, subject, height: int = 92,
                 width: int | None = None):
        super().__init__()
        self.kind = kind
        self.subject = subject
        self._height = height
        self.setMinimumHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding,
                           QSizePolicy.Policy.Fixed)
        # A portrait stacked down a panel rather than sitting in a card grid
        # will take the whole width if it is allowed to: measured on the life
        # catalogue, a 620-pixel band with an 80-pixel organism in the middle
        # of it. A cap turns the band back into a picture.
        if width is not None:
            self.setMaximumWidth(width)

    def sizeHint(self) -> QSize:
        return QSize(self._height * 2, self._height)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(VOID))
        camera = render3d.Camera(at=(0.0, 0.0, 0.0), forward=(0.0, 0.0, 1.0),
                                 up=(0.0, 1.0, 0.0), width=w, height=h,
                                 half_fov=HALF_FOV)
        paint(painter, camera, self.kind, self.subject)
        painter.end()


def paint(painter, camera: render3d.Camera, kind: str, subject) -> None:
    """Draw one subject into an already-set-up frame.

    Split from the widget so a check can render a portrait without building
    one, and so the catalogue sheet and the card show the same picture.
    """
    if kind == "hull":
        render3d.draw(painter, camera, hulls3d.mesh_for_chassis(subject),
                      (0.0, 0.0, SUBJECT_AT), 1.0, LIGHT,
                      spin=HULL_SPIN, tilt=HULL_TILT)
    elif kind == "berth":
        shown = models3d.present("anchorage", subject)
        render3d.draw(painter, camera, shown["mesh"], (0.0, 0.0, SUBJECT_AT),
                      1.0, LIGHT, spin=0.6, tilt=shown["tilt"])
    elif kind == "work":
        # A holding of your own, through the same door the sky uses: the
        # portrait on the card *is* the structure you fly up to. `subject` is
        # a colony class or its id, so a card can pass either.
        look = getattr(subject, "id", subject)
        shown = models3d.present("anchorage", look)
        render3d.draw(painter, camera, shown["mesh"], (0.0, 0.0, WORK_AT),
                      1.0, LIGHT, spin=0.6, tilt=shown["tilt"])
    elif kind == "robot":
        # A machine, through the same renderer everything else uses. Held
        # nearer broadside than a berth and the right way up, like a work:
        # a robot has a head, feet and a front, and at the berth attitude
        # every one of them was a foreshortened lump.
        from ..data import robots3d
        look = getattr(subject, "id", subject)
        mesh = robots3d.mesh_for(look)
        if mesh is None:
            return
        render3d.draw(painter, camera, mesh, (0.0, 0.0, ROBOT_AT), 1.0, LIGHT,
                      spin=ROBOT_SPIN, tilt=ROBOT_TILT)
    elif kind == "life":
        # An organism, built from its own record: the body plan is the
        # silhouette, the biochemistry the colour, a trait a feature you can
        # see. `subject` is a Lifeform, or (form, metabolism, traits).
        from ..data import life3d
        if hasattr(subject, "metabolism"):
            shape = life3d.for_lifeform(subject)
        else:
            form, met, *rest = tuple(subject) + ((),)
            shape = life3d.build(form, met, rest[0] if rest else ())
        render3d.draw(painter, camera, shape.mesh, (0.0, 0.0, LIFE_AT), 1.0,
                      LIGHT, spin=LIFE_SPIN, tilt=LIFE_TILT)
    elif kind == "ship":
        shown = models3d.present("hull", subject)
        render3d.draw(painter, camera, shown["mesh"], (0.0, 0.0, SUBJECT_AT),
                      1.0, LIGHT, spin=HULL_SPIN, tilt=shown["tilt"])
    elif kind == "world":
        radius = 1.0
        spheres.draw(painter, camera, worlds3d.paint_for(subject),
                     (0.0, 0.0, SUBJECT_AT), radius, WORLD_LIGHT,
                     spin=0.4, tilt=0.38,
                     features=surfaces.features_for(subject, f"codex:{subject}"),
                     stretch=surfaces.stretch_for(subject),
                     detail=lambda lat, lon, span, k=subject: surfaces.detail_near(
                         k, f"codex:{k}", lat, lon, span))
    elif kind == "star":
        from ..data.starclasses import STAR_CLASSES
        from ..sim.sky import Sight
        star = STAR_CLASSES.get(subject)
        if star is None:
            return
        # Placed so every class comes out the same size on the card: this is a
        # colour-and-kind comparison, and a neutron star drawn true to scale
        # against an A-type would be one pixel beside a beach ball. The sky
        # draws them true; the catalogue draws them level.
        want = min(camera.w, camera.h) * 0.22
        distance = star.radius_km / math.tan(math.atan(want / camera.focal))
        stars3d.draw(painter, camera,
                     Sight(name=star.name, kind="star",
                           at=(0.0, 0.0, distance), radius_km=star.radius_km,
                           tint=star.core, look=subject, halo=star.halo),
                     max_glow=min(camera.w, camera.h) * GLOW_SHARE)
