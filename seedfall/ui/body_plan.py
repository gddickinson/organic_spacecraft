"""A person as a diagram: what is in them, and where.

The Clinic tab could say *A reflex lace · DEX +2 · strain 2* and a captain
had to hold the anatomy in their head. Every other system in this game that
fits things to a frame draws the frame — the hull has a layer stack, the
ship has a plan you can click, the turret has a bore — and the one frame
things are actually fitted to had no picture at all.

So: a standing figure, and a mark at every site something has been put into.
Nothing here is authored. The sites come off `data/treatments.py` — a muscle
weave is in the arms, a cortex link is in the skull, a vacuum rig is at the
throat — and the figure's own shading is the wear the years have put on
them, which is the number the surgery panel above it is offering to clear.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..data import treatments as table
from ..sim import clinic as clinic_sim
from ..sim import lifespan as lifespan_sim
from . import painting, theme

#: Where on a body each piece of work goes, in figure coordinates: `x` across
#: from the centre (−1 left, +1 right) and `y` down from the crown (0) to the
#: sole (1). One row per treatment that goes *into* somebody; the rest are
#: courses and cold berths and belong to the whole person.
SITES = {
    "hand_deck": (0.62, 0.52, "forearm"),
    "optic_suite": (-0.16, 0.055, "eyes"),
    "eye_grow": (0.16, 0.055, "eyes"),
    "muscle_weave": (-0.52, 0.34, "shoulders and arms"),
    "reflex_lace": (0.0, 0.30, "the spine"),
    "subdermal": (0.0, 0.26, "chest and forearms"),
    "vacuum_rig": (0.0, 0.14, "the throat"),
    "cortex_link": (0.0, 0.03, "the skull"),
    "chop_job": (-0.60, 0.50, "wherever they could reach"),
    "joint_rebuild": (0.42, 0.62, "hips and shoulders"),
    "spinal_lattice": (0.0, 0.40, "along the spine"),
    "neural_prune": (0.10, 0.02, "the skull"),
    "skin_graft": (-0.34, 0.24, "chest and face"),
    "organ_swap": (0.14, 0.30, "the chest"),
    "limb_regrow": (0.60, 0.70, "a leg"),
    "gene_tidy": (0.0, 0.20, "everywhere at once"),
    "heavy_frame": (0.0, 0.46, "bone and muscle"),
    "bright_line": (0.0, 0.06, "everywhere at once"),
}

#: The figure, in fractions of the frame's **height**. Driven by the height
#: and not the width on purpose: scaled across, a person in a 520×320 panel
#: came out as wide as they were tall, which is not a body and not a plate a
#: surgeon would recognise.
HEAD_Y = 0.115
HEAD_R = 0.058
SHOULDER_Y = 0.235
SHOULDER = 0.150
HIP_Y = 0.560
HIP = 0.108
ARM_W = 0.044
LEG_W = 0.058
SOLE = 0.965

#: How much of the frame either side is left for the leader lines' captions.
GUTTER = 0.30

def sites_for(game, officer) -> list:
    """Every fitted thing on this person, with where it is."""
    out = []
    for got in clinic_sim.fitted_to(game, officer):
        at = SITES.get(got.id)
        if at is None:
            continue
        out.append({"treatment": got, "x": at[0], "y": at[1], "where": at[2]})
    return out


def place_at(w: float, h: float, x: float, y: float) -> QPointF:
    """Figure coordinates to pixels: `x` across from the spine, `y` down."""
    return QPointF(w * 0.5 + x * h, y * h)


def _figure(w: float, h: float) -> QPainterPath:
    """A standing person: head, torso, two arms, two legs."""
    def at(x, y):
        return place_at(w, h, x, y)

    path = QPainterPath()
    path.addEllipse(at(0.0, HEAD_Y), h * HEAD_R, h * HEAD_R * 1.12)
    torso = QPainterPath()
    torso.moveTo(at(-0.052, HEAD_Y + HEAD_R * 0.92))
    torso.lineTo(at(-SHOULDER, SHOULDER_Y))
    torso.lineTo(at(-HIP, HIP_Y))
    torso.lineTo(at(HIP, HIP_Y))
    torso.lineTo(at(SHOULDER, SHOULDER_Y))
    torso.lineTo(at(0.052, HEAD_Y + HEAD_R * 0.92))
    torso.closeSubpath()
    path.addPath(torso)
    for side in (-1, 1):
        arm = QPainterPath()
        arm.moveTo(at(side * SHOULDER, SHOULDER_Y))
        arm.lineTo(at(side * (SHOULDER + ARM_W * 0.7), SHOULDER_Y + 0.02))
        arm.lineTo(at(side * (SHOULDER + ARM_W * 0.2), HIP_Y + 0.075))
        arm.lineTo(at(side * (SHOULDER - ARM_W * 0.6), HIP_Y + 0.060))
        arm.closeSubpath()
        path.addPath(arm)
        leg = QPainterPath()
        leg.moveTo(at(side * 0.012, HIP_Y))
        leg.lineTo(at(side * HIP, HIP_Y))
        leg.lineTo(at(side * (HIP - 0.018), SOLE))
        leg.lineTo(at(side * (LEG_W * 0.28), SOLE))
        leg.closeSubpath()
        path.addPath(leg)
    return path


def paint(p: QPainter, rect: QRectF, game, officer) -> None:
    """The figure, its wear, and a mark at every site."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.translate(rect.x(), rect.y())
    w, h = rect.width(), rect.height()
    p.fillRect(QRectF(0, 0, w, h), QColor(theme.GROUND))

    figure = _figure(w, h)
    wear = float(getattr(officer, "wear", 0.0) or 0.0)
    years = lifespan_sim.age_of(officer, game)
    lineage = lifespan_sim.lineage_of(officer, game)
    through = max(0.0, min(1.0, years / max(1.0, float(
        getattr(lineage, "span", 80)))))
    # The body itself: cooler and thinner the further through the run.
    skin = QColor(theme.tint("chloro"))
    skin.setAlpha(int(58 - 26 * through))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(skin)
    p.drawPath(figure)
    edge = QColor(theme.tint("chloro" if through < 0.7 else "osteo"))
    edge.setAlpha(200)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(edge, 1.4))
    p.drawPath(figure)

    if wear > 0.02:
        _wear(p, w, h, wear)
    _marks(p, w, h, game, officer)
    p.restore()


def _wear(p: QPainter, w: float, h: float, wear: float) -> None:
    """What decline has taken, marked at the joints it takes it from."""
    warn = QColor(theme.tint("warn"))
    warn.setAlpha(int(90 + 120 * min(1.0, wear)))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(warn)
    for x, y in ((-SHOULDER + 0.012, SHOULDER_Y + 0.008),
                 (SHOULDER - 0.012, SHOULDER_Y + 0.008),
                 (-HIP + 0.010, HIP_Y - 0.010),
                 (HIP - 0.010, HIP_Y - 0.010),
                 (-0.060, 0.775), (0.060, 0.775)):
        p.drawEllipse(place_at(w, h, x, y), h * 0.016, h * 0.016)


def _marks(p: QPainter, w: float, h: float, game, officer) -> None:
    """A lit ring and a leader line at every fitted site."""
    rows = sites_for(game, officer)
    if not rows:
        return
    lumen = QColor(theme.tint("lumen"))
    warn = QColor(theme.tint("warn"))
    font = p.font()
    font.setPointSizeF(max(6.5, h * 0.028))
    p.setFont(font)
    for n, row in enumerate(rows):
        got = row["treatment"]
        tint = warn if got.strain >= 2.0 else lumen
        # `SITES` is written in body coordinates — 0 at the crown, 1 at
        # the sole, ±0.62 at the outside of an arm — so both axes are
        # mapped onto the figure rather than onto the frame. Without this
        # an optic suite landed on somebody's collarbone.
        crown = HEAD_Y - HEAD_R
        at = place_at(w, h,
                      row["x"] * (SHOULDER + ARM_W) / 0.62,
                      crown + row["y"] * (SOLE - crown))
        glow = QColor(tint)
        glow.setAlpha(70)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(at, h * 0.026, h * 0.026)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(tint, 1.4))
        p.drawEllipse(at, h * 0.016, h * 0.016)
        # A leader out to whichever side the fitting is on, and the name in
        # the gutter kept clear for it. Stacked down the side rather than
        # level with the site, so two fittings an inch apart do not print
        # over each other.
        side = 1.0 if row["x"] >= 0 else -1.0
        gutter = w * GUTTER
        end_x = (w - gutter) if side > 0 else gutter
        row_y = h * (0.10 + 0.115 * n)
        p.drawLine(at, QPointF(end_x, row_y))
        p.setPen(QPen(QColor(theme.INK), 1.0))
        flags = (Qt.AlignmentFlag.AlignVCenter
                 | (Qt.AlignmentFlag.AlignLeft if side > 0
                    else Qt.AlignmentFlag.AlignRight))
        box = QRectF(end_x + (4 if side > 0 else -gutter - 4),
                     row_y - h * 0.05, gutter, h * 0.10)
        p.drawText(box, int(flags), got.name)


class BodyPlan(painting.Painted, QWidget):
    """One person, and everything that has been put into them."""

    def __init__(self, game, officer, height: int = 260):
        super().__init__()
        self.game = game
        self.officer = officer
        self._height = height
        self.setMinimumHeight(height)
        # **Not `MinimumExpanding`.** That policy takes `sizeHint` as the
        # *floor*, so a wide hint made this widget the screen's minimum
        # width — measured at 844 px of an 837 px column. `Preferred` lets
        # `minimumSizeHint` govern and still takes every pixel offered.
        self.setSizePolicy(QSizePolicy.Policy.Preferred,
                           QSizePolicy.Policy.Fixed)
        self.setAccessibleName(
            f"What is fitted to {getattr(officer, 'name', '')}")

    def sizeHint(self) -> QSize:
        return QSize(int(self._height * 1.5), self._height)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        """The plate shrinks; the labels move into whatever gutter is left."""
        return QSize(200, self._height)

    def draw(self, p: QPainter) -> None:
        paint(p, QRectF(0, 0, self.width(), self.height()),
              self.game, self.officer)


def says(game, officer) -> list:
    """The same thing in words, for a screen reader and for a caption."""
    rows = sites_for(game, officer)
    if not rows:
        return ["Nothing has been fitted to them."]
    said = []
    for row in rows:
        got = row["treatment"]
        said.append(f"{got.name} — {row['where']}"
                    + (f", strain {got.strain:.1g}" if got.strain else ""))
    strain = clinic_sim.strain_of(game, officer)
    if strain:
        said.append(f"{strain:.1g} of strain in all — "
                    f"{strain * table.STRAIN_LOYALTY:.0f} of their loyalty, "
                    "permanently.")
    return said
