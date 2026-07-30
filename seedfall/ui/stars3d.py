"""What a star looks like out of a window, class by class.

`data/starclasses.py` has carried a `core` colour for every class since it was
written — an M dwarf's salmon, a G-type's cream, an A-type's blue-white, a black
hole's violet — and `ui/viewport._star` drew the disc as:

    p.setBrush(QColor(255, 253, 244))
    p.drawEllipse(point, radius, radius)

The same off-white, for all nine. The `tint` it had just worked out from the
class was assigned to a local and never used. So the catalogue held nine stars
and the sky held one, and **the black hole — whose own blurb says there is
nothing to see and that the accretion disc is the only reason you know where it
is — was drawn as the brightest object in the picture**, identical to an
A-type.

There is a comment two lines above the offending one congratulating an earlier
cycle for noticing that the *corona* colour was going unused. It fixed the halo
and left the core exactly as it was.

Three things separate the classes here, and all three come from the data:

* **Colour.** The disc is the class's own, with a hot centre whose whiteness
  follows luminosity — which is what makes an A-type read as violent and an M
  dwarf as an ember, rather than both as "a circle".
* **Reach.** The corona spreads and brightens with luminosity, on a log scale
  because the range is 0.0002 to 22 and a linear one would give eight of the
  nine classes no corona at all.
* **Kind.** A black hole is not a dim star and a neutron star is not a small
  one. Both get the picture their entry describes.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPen, QRadialGradient

from ..data.starclasses import DEFAULT, STAR_CLASSES
from . import render3d

#: How far the corona reaches past the disc, at the Sun's luminosity, and how
#: much a decade of brightness moves it. An A-type at 22 L reaches about twice
#: as far as a G-type; an M dwarf at 0.04 barely past its own edge.
CORONA_AT_SOL = 5.0
CORONA_PER_DECADE = 1.9

#: The most and least the corona may reach, in disc radii. The floor keeps a
#: dim star from having no glow at all — it is still a star — and the ceiling
#: stops a blue giant washing the whole frame.
CORONA_MIN, CORONA_MAX = 1.7, 11.0

#: How white the middle of the disc goes, at the Sun's luminosity and per
#: decade either side. A photosphere is limb-darkened; this is that, cheaply.
CORE_WHITE_AT_SOL = 0.55
CORE_WHITE_PER_DECADE = 0.22

#: Classes that are not simply a hot ball, and what they are instead.
DARK = "X"          # a black hole: an absence, and a ring
COMPACT = ("D", "N")  # degenerate: small, fierce, and hard-edged
PAIR = "B"          # two stars about a common centre — so, two discs

#: How far apart the two members of a binary sit, in disc radii, and how much
#: smaller the companion is.
#:
#: Its entry calls it "two stars about a common centre" and says the light on a
#: hull's plating shifts as they turn about each other, and it was drawn as one
#: disc — in a cream within eight points of the G-type's, so the two classes
#: rendered as the same star. A pair that looks like a pair is both truer to the
#: entry and the thing that tells them apart.
PAIR_GAP = 1.55
PAIR_SIZE = 0.72

#: The accretion ring's width and brightness, as shares of the horizon radius.
RING_WIDTH = 0.55
RING_ALPHA = 210


def _decades(luminosity: float) -> float:
    """How many powers of ten from the Sun this star is, clamped."""
    return max(-4.0, min(1.6, math.log10(max(1e-6, luminosity))))


def class_for(sight):
    """The class this sight belongs to. `sky.build` puts its letter in `look`."""
    return STAR_CLASSES.get(getattr(sight, "look", "") or "", DEFAULT)


def corona_reach(star) -> float:
    """How far the glow spreads, in disc radii."""
    return max(CORONA_MIN, min(CORONA_MAX,
                               CORONA_AT_SOL + CORONA_PER_DECADE
                               * _decades(star.luminosity)))


def core_white(star) -> float:
    """How far the middle of the disc is pushed toward white, 0..1."""
    return max(0.0, min(0.95, CORE_WHITE_AT_SOL + CORE_WHITE_PER_DECADE
                        * _decades(star.luminosity)))


def _blend(colour: QColor, toward: QColor, share: float) -> QColor:
    share = max(0.0, min(1.0, share))
    return QColor(round(colour.red() + (toward.red() - colour.red()) * share),
                  round(colour.green()
                        + (toward.green() - colour.green()) * share),
                  round(colour.blue() + (toward.blue() - colour.blue()) * share))


def _hex(value: str, fallback: str) -> QColor:
    return QColor(value if isinstance(value, str) and value.startswith("#")
                  else fallback)


def draw(painter, camera: render3d.Camera, sight, min_radius: float = 2.4,
         max_glow: float = 0.0):
    """Paint one star. Returns its screen radius, or 0 if it is off the lens.

    `max_glow` caps how far the corona may reach in pixels. The sky wants no
    cap — a blue giant should wash the window. A catalogue card does: the glow
    runs to eleven disc radii at the bright end, so on a small tile it was
    still tinted at the corner and every star sat on a differently-coloured
    card, which reads as a design accident rather than as light.
    """
    seen = camera.project(sight.at)
    if seen is None:
        return 0.0
    point, _ahead = seen
    star = class_for(sight)
    # Never smaller than a bright point: a star at four AU is a tenth of a
    # degree across and would round to nothing.
    radius = max(min_radius, render3d.screen_radius(
        camera, sight.range_km, sight.radius_km))
    core = _hex(getattr(sight, "tint", ""), star.core)
    halo = _hex(getattr(sight, "halo", ""), star.halo)

    if star.id == DARK:
        _black_hole(painter, point, radius, core, halo)
        return radius

    reach = radius * corona_reach(star)
    if max_glow > 0.0:
        reach = min(reach, max_glow)
    glow = QRadialGradient(point, reach)
    lit = _blend(halo, QColor("#ffffff"), core_white(star) * 0.6)
    glow.setColorAt(0.0, QColor(lit.red(), lit.green(), lit.blue(), 215))
    glow.setColorAt(0.18, QColor(halo.red(), halo.green(), halo.blue(), 150))
    glow.setColorAt(1.0, QColor(halo.red(), halo.green(), halo.blue(), 0))
    painter.setBrush(glow)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(point, reach, reach)

    # The disc: the class's own colour, hottest in the middle. A gradient
    # rather than a flat fill, because a flat disc of any colour reads as a
    # sticker and the limb darkening is most of what says "this is a ball of
    # gas and not a hole punched in the sky".
    if star.id == PAIR:
        # Two of them, about a common centre.
        _disc(painter, QPointF(point.x() - radius * PAIR_GAP * 0.5, point.y()),
              radius, core, halo, star)
        _disc(painter, QPointF(point.x() + radius * PAIR_GAP * 0.5,
                               point.y() - radius * 0.22),
              radius * PAIR_SIZE, _blend(core, halo, 0.45), halo, star)
    else:
        _disc(painter, point, radius, core, halo, star)

    if star.id in COMPACT:
        # Degenerate matter has an edge. A rim picks it out against its own
        # corona, which is otherwise the only thing you can see.
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.setPen(QPen(_blend(core, QColor("#ffffff"), 0.5), 1.2))
        painter.drawEllipse(point, radius, radius)
        painter.setPen(Qt.PenStyle.NoPen)
    return radius


def _disc(painter, point: QPointF, radius: float, core: QColor,
          halo: QColor, star) -> None:
    """One photosphere: the class's colour, hottest in the middle."""
    face = QRadialGradient(point, radius)
    face.setColorAt(0.0, _blend(core, QColor("#ffffff"), core_white(star)))
    face.setColorAt(0.72, core)
    face.setColorAt(1.0, _blend(core, halo, 0.65))
    painter.setBrush(face)
    painter.drawEllipse(point, radius, radius)


def _black_hole(painter, point: QPointF, radius: float, core: QColor,
                halo: QColor) -> None:
    """An absence, and the ring that says where it is.

    Drawn from the entry's own words: "nothing to see. The accretion disc is
    the only reason you know where it is." So the horizon is *black* — not dim,
    black — and everything readable is the ring outside it.
    """
    outer = radius * (1.0 + RING_WIDTH)
    ring = QRadialGradient(point, outer)
    ring.setColorAt(0.0, QColor(0, 0, 0, 0))
    ring.setColorAt(max(0.01, radius / outer * 0.98), QColor(0, 0, 0, 0))
    ring.setColorAt(min(0.999, radius / outer), QColor(
        core.red(), core.green(), core.blue(), RING_ALPHA))
    ring.setColorAt(1.0, QColor(halo.red(), halo.green(), halo.blue(), 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(ring)
    painter.drawEllipse(point, outer, outer)

    painter.setBrush(QColor(0, 0, 0))
    painter.drawEllipse(point, radius, radius)
