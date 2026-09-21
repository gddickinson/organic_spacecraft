"""The concourse, drawn: the structure, the doors, and the people on them.

A place was a heading and four numbers. The game draws hulls, holdings,
worlds, gates, wrecks and the inside of a gun turret, and the one thing it
never drew was **anywhere people are** — so a class-A capital of ten million
and a shed on a frontier rock were the same screen with different lists.

Three layers, all of them read off `sim/places.py` and `sim/shore.py` rather
than authored:

- **What it is.** A quay has a mast and booms, a habitat is a drum turning
  against the stars, a holding is a dome dug into a body, a settlement is a
  line of sheds, and your own hull is your own hull. The lit windows are the
  population digit, so ten million looks like ten million.
- **What is open.** Every door that will admit the crew, in a strip along
  the deck, tinted by what sort of place it is and lit only if it is open
  *now*. A rock with five doors and an arcology with eighty are the same
  drawing at two densities, which is the honest way to show the difference.
- **Who is on it.** People, walking. Counted from the crowd and placed
  deterministically, so a place looks the same every time you put in — and
  they gather in front of the doors there are most of, which is what a
  concourse looks like from a gangway.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..core.rng import RNG
from ..data import venues as venue_table
from ..sim import places as places_sim
from ..sim import shore
from . import painting, theme

#: What each sort of door is lit in. The concourse's own legend, and the
#: same tints the tabs use, so a colour means one thing on both.
DOOR_TINT = {
    "chandler": "steel", "market": "osteo", "tech": "lumen",
    "bank": "osteo", "office": "steel", "law": "warn",
    "transport": "steel", "lodging": "chloro", "eatery": "osteo",
    "clinic": "lumen", "sport": "chloro", "arts": "xeno",
    "entertainment": "xeno", "temple": "ink", "vice": "warn",
}

#: The sky behind each kind of place.
SKY = {
    "port": "#0b1420", "habitat": "#05070c", "holding": "#0c1410",
    "downside": "#141009", "ship": "#080d12",
}

#: Where the deck sits, and how much of the frame the structure gets.
DECK = 0.74
DOOR_H = 0.16

#: What a holding of a given class is *shaped* like. `Place.look` carries the
#: class id, so an ARCA drum and a STACK arcology stop being the same picture
#: — which they were, because both are habitats and the scene branched on the
#: kind.
LOOKS = {
    "arca_drum": "drum", "coral_reef": "drum", "free_port": "drum",
    "stack_arcology": "tower", "bastion_post": "bunker",
    "lichen_dome": "dome", "pomona_grove": "dome",
    "gravid_nursery": "dome", "tardigrade_vault": "dome",
    "habitat": "drum", "holding": "dome", "port": "quay",
    "downside": "sheds", "ship": "hull",
}

#: The most people to draw, however many live here. A crowd is a texture;
#: two hundred figures in a 180-pixel band is a smear.
CROWD_MOST = 42
CROWD_LEAST = 2


def crowd_for(place) -> int:
    """How many figures stand for this many people."""
    if place.heads <= 0:
        return 0
    return max(CROWD_LEAST,
               min(CROWD_MOST, int(place.people * 4 + place.amenity * 2)))


def paint(p: QPainter, rect: QRectF, game, place) -> None:
    """The whole scene."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setClipRect(rect)
    p.translate(rect.x(), rect.y())
    w, h = rect.width(), rect.height()
    rng = RNG(f"{getattr(game, 'seed', 'verge')}:scene:{place.id}")
    p.fillRect(QRectF(0, 0, w, h), QColor(SKY.get(place.kind, "#0a1512")))
    if place.kind in ("habitat", "ship", "port"):
        _stars(p, w, h, rng)
    _structure(p, w, h, place, rng)
    doors = shore.open_here(game, place)
    _deck(p, w, h, place)
    _frontage(p, w, h, doors)
    _doors(p, w, h, doors, rng)
    _people(p, w, h, place, doors, rng)
    p.setPen(QPen(QColor(theme.LINE), 1.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRectF(0.5, 0.5, w - 1, h - 1))
    p.restore()


def _stars(p: QPainter, w: float, h: float, rng) -> None:
    ink = QColor(theme.INK)
    for _n in range(46):
        x, y = rng.float(0, w), rng.float(0, h * DECK)
        ink.setAlpha(rng.int(30, 130))
        p.fillRect(QRectF(x, y, 1.2, 1.2), ink)


def _structure(p: QPainter, w: float, h: float, place, rng) -> None:
    """What this place *is*, in one shape, with its windows lit."""
    deck = h * DECK
    plate = QColor(theme.PANEL).lighter(112)
    edge = QColor(theme.LINE2 if hasattr(theme, "LINE2") else theme.LINE)
    p.setPen(Qt.PenStyle.NoPen)
    look = LOOKS.get(getattr(place, "look", "") or place.kind,
                     LOOKS.get(place.kind, "dome"))
    if look == "tower":
        # A city stacked upward, which is what an arcology is and what makes
        # it not a drum.
        p.setBrush(plate)
        steps = ((0.36, 1.00), (0.30, 0.66), (0.22, 0.38), (0.13, 0.16))
        for half, base in steps:
            p.drawRect(QRectF(w * (0.5 - half * 0.5), deck * base * 0.96,
                              w * half, deck * (1.02 - base * 0.96)))
        p.setPen(QPen(edge, 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(0, deck), QPointF(w, deck))
    elif look == "bunker":
        p.setBrush(plate)
        path = QPainterPath()
        path.moveTo(w * 0.22, deck)
        path.lineTo(w * 0.30, deck * 0.62)
        path.lineTo(w * 0.70, deck * 0.62)
        path.lineTo(w * 0.78, deck)
        path.closeSubpath()
        p.drawPath(path)
        p.setPen(QPen(QColor(theme.tint("warn")), 1.6))
        for side in (-1, 1):
            at = w * (0.5 + side * 0.22)
            p.drawLine(QPointF(at, deck * 0.62), QPointF(at, deck * 0.40))
        p.setPen(Qt.PenStyle.NoPen)
    elif look == "drum":
        # A drum, seen end-on and a little from the side.
        p.setBrush(plate)
        p.drawEllipse(QPointF(w * 0.5, deck * 0.52), w * 0.20, deck * 0.42)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(edge, 1.4))
        for n in range(3):
            r = 0.20 - 0.05 * n
            p.drawEllipse(QPointF(w * 0.5, deck * 0.52), w * r, deck * (0.42 - 0.09 * n))
    elif look == "quay":
        p.setBrush(plate)
        p.drawRect(QRectF(w * 0.30, deck * 0.28, w * 0.40, deck * 0.72))
        p.drawRect(QRectF(w * 0.46, deck * 0.04, w * 0.08, deck * 0.30))
        p.setPen(QPen(edge, 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for side in (-1, 1):
            p.drawLine(QPointF(w * (0.5 + side * 0.20), deck * 0.42),
                       QPointF(w * (0.5 + side * 0.40), deck * 0.30))
    elif look == "sheds":
        p.setBrush(plate)
        for n in range(5):
            x = w * (0.16 + 0.15 * n)
            tall = deck * rng.float(0.16, 0.34)
            p.drawRect(QRectF(x, deck - tall, w * 0.09, tall))
    elif look == "hull":
        path = QPainterPath()
        path.moveTo(w * 0.24, deck * 0.68)
        path.lineTo(w * 0.42, deck * 0.42)
        path.lineTo(w * 0.72, deck * 0.46)
        path.lineTo(w * 0.78, deck * 0.66)
        path.lineTo(w * 0.60, deck * 0.80)
        path.lineTo(w * 0.30, deck * 0.80)
        path.closeSubpath()
        p.setBrush(plate)
        p.drawPath(path)
    else:
        p.setBrush(plate)
        path = QPainterPath()
        path.moveTo(w * 0.28, deck)
        path.cubicTo(w * 0.30, deck * 0.34, w * 0.70, deck * 0.34,
                     w * 0.72, deck)
        path.closeSubpath()
        p.drawPath(path)
    _windows(p, w, h, place, rng)


def _windows(p: QPainter, w: float, h: float, place, rng) -> None:
    """Lit windows, counted off the population digit.

    Nothing else in the picture carries *how many people*: doors are what is
    open and figures are a texture, and both run out long before ten million
    does. Windows do not — they just get denser.
    """
    lit = max(0, min(260, place.people * place.people * 5 + place.heads // 400))
    if lit <= 0:
        return
    deck = h * DECK
    glow = QColor(theme.tint("osteo"))
    for _n in range(int(lit)):
        x = rng.float(w * 0.30, w * 0.70)
        y = rng.float(deck * 0.30, deck * 0.96)
        glow.setAlpha(rng.int(70, 210))
        p.fillRect(QRectF(x, y, 2.2, 1.6), glow)


def _deck(p: QPainter, w: float, h: float, place) -> None:
    """The gangway everybody is standing on."""
    deck = h * DECK
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(theme.GROUND).lighter(118))
    p.drawRect(QRectF(0, deck, w, h - deck))
    p.setPen(QPen(QColor(theme.LINE), 1.2))
    p.drawLine(QPointF(0, deck), QPointF(w, deck))


def _frontage(p: QPainter, w: float, h: float, doors) -> None:
    """The wall the doors are set into.

    Without it the doors floated in front of the structure as a row of
    coloured boxes. A concourse is a frontage with holes in it, and the
    holes are what is open.
    """
    if not doors:
        return
    deck = h * DECK
    top = deck - h * DOOR_H * 1.25
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(theme.GROUND).darker(115))
    p.drawRect(QRectF(0, top, w, deck - top))
    p.setPen(QPen(QColor(theme.LINE), 1.0))
    p.drawLine(QPointF(0, top), QPointF(w, top))


def _doors(p: QPainter, w: float, h: float, doors, rng) -> None:
    """Every open door, in a strip, tinted by what sort of place it is."""
    if not doors:
        return
    deck = h * DECK
    shown = doors[:34]
    span = w / max(1, len(shown))
    wide = min(span * 0.62, w * 0.035)
    for n, venue in enumerate(shown):
        tint = QColor(theme.tint(DOOR_TINT.get(venue.kind, "dim")))
        tall = h * DOOR_H * (0.66 + 0.24 * (venue.cr > 80))
        x = span * (n + 0.5) - wide * 0.5
        body = QColor(tint)
        body.setAlpha(42)
        p.fillRect(QRectF(x, deck - tall, wide, tall), body)
        p.setPen(QPen(tint, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(x, deck - tall, wide, tall))
        # A lit sign over the ones worth walking to.
        if venue.cr > 80 or venue.kind in ("clinic", "vice", "bank"):
            sign = QColor(tint)
            sign.setAlpha(200)
            p.fillRect(QRectF(x, deck - tall - 2.5, wide, 2), sign)


def _people(p: QPainter, w: float, h: float, place, doors, rng) -> None:
    """The crowd, on the deck, gathered where there is most to do."""
    count = crowd_for(place)
    if count <= 0:
        return
    deck = h * DECK
    band = h - deck
    ink = QColor(theme.INK)
    for _n in range(count):
        # Depth first, so the ones at the back are smaller and dimmer —
        # which is all the perspective a band this shallow can carry.
        depth = rng.float(0.0, 1.0)
        y = deck + band * (0.30 + 0.62 * depth)
        tall = band * (0.30 + 0.34 * depth)
        x = rng.float(w * 0.02, w * 0.98)
        ink.setAlpha(int(70 + 110 * depth))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(ink)
        # Narrower than the first draft, which made a concourse look like a
        # row of chess pawns, and with a stride so the crowd is walking
        # rather than queuing.
        wide = max(1.1, tall * 0.13)
        stride = rng.float(0.0, 1.0)
        p.drawEllipse(QPointF(x, y - tall), wide * 0.82, wide * 0.90)
        path = QPainterPath()
        path.moveTo(x - wide * (0.7 + 0.5 * stride), y)
        path.lineTo(x - wide * 0.42, y - tall * 0.74)
        path.lineTo(x + wide * 0.42, y - tall * 0.74)
        path.lineTo(x + wide * (0.7 + 0.5 * (1.0 - stride)), y)
        path.closeSubpath()
        p.drawPath(path)


class PlaceScene(painting.Painted, QWidget):
    """One place, drawn, with whoever is on it."""

    def __init__(self, game, place, height: int = 170):
        super().__init__()
        self.game = game
        self.place = place
        self._height = height
        self.setMinimumHeight(height)
        # **Not `MinimumExpanding`.** That policy takes `sizeHint` as the
        # *floor*, so a wide hint made this widget the screen's minimum
        # width — measured at 844 px of an 837 px column. `Preferred` lets
        # `minimumSizeHint` govern and still takes every pixel offered.
        self.setSizePolicy(QSizePolicy.Policy.Preferred,
                           QSizePolicy.Policy.Fixed)
        self.setAccessibleName(f"{place.name} — {place.kind_name}")
        self.setToolTip("  ·  ".join(places_sim.says(place)))

    def sizeHint(self) -> QSize:
        return QSize(self._height * 5, self._height)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        """**A banner may be narrow.** `MinimumExpanding` takes `sizeHint`
        as the floor, so a 160-tall scene claimed 800 px of a 1040 px window
        and pushed the Concourse seven pixels past its column."""
        return QSize(220, self._height)

    def draw(self, p: QPainter) -> None:
        paint(p, QRectF(0, 0, self.width(), self.height()),
              self.game, self.place)


def legend(game, place) -> str:
    """What the picture is showing, for anybody who would rather read it."""
    doors = shore.open_here(game, place)
    kinds = sorted({v.kind for v in doors})
    return (f"{len(doors)} door(s) open over {len(kinds)} kinds; "
            f"{place.heads:,} people; "
            + ", ".join(venue_table.KIND_NAME[k] for k in kinds[:6])
            + ("…" if len(kinds) > 6 else "."))
