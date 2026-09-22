"""The deck, drawn: walls, doors, things, people, and what the party can see.

Painted from the walk and nothing else, in the GESTALT palette: a grown
hull's walls are tissue-green and rounded at the chambers, a Yards hull's
are steel, a Dry Choir frame's are cold cyan, a xeno hulk's violet. Three
depths of fog — never seen, seen before, in sight now — and people are
drawn only where somebody in the party can see them.

What the pointer is over is the canvas's own business: the square, the
path to it and what it would cost, the odds on whoever is standing there.
All of it is *asked* of the sim (`afoot_map`, `afoot_fight`) and none of it
moves anything. A click hands the square to the screen, which decides.

The canvas fits the whole deck when it can. A deck too big to fit at a
readable size is drawn at a fixed size with the camera on whoever is in
hand.

**A ring's level has no ends to draw.** It is a strip whose two ends are one
corridor (`Deck.wrap`), so the canvas turns it under whoever is in hand —
they stand in the middle, the ring runs on past both edges, and walking
round it is walking, not falling off the map at the seam (`roll`). The two
edges are marked as the one place they are.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..data.afoot_things import THING_BY_ID
from ..sim import afoot, afoot_fight, afoot_map
from ..sim.afoot_state import GROUND, HALL, WALL, WINDOW, actor_at, party
from . import painting, theme
from .afoot_marks import draw_thing, hover_text, label_spot, tokens

#: Wall colours by style: what the deck is made of.
WALLS = {"grown": "#2f5a3b", "fabricated": "#3b4b5e", "hybrid": "#46523f",
         "synthetic": "#24505a", "xeno": "#4d3c63", "station": "#3b4b5e",
         "habitat": "#35543f", "settlement": "#5a4b39"}
FLOORS = {"grown": "#15261f", "xeno": "#1c1826", "synthetic": "#101c22",
          "settlement": "#1f1b15"}
#: Open ground: earth under a sky you can breathe, grey regolith under none.
OPEN_GROUND = {True: "#2b291c", False: "#28282e"}
#: A person's colour, by side and temper.
MOODS = {"friendly": "chloro", "neutral": "ink", "wary": "osteo",
         "hostile": "warn", "surrendered": "dim", "fled": "dim"}

#: Squares on a side, fitted; and the size a deck too big to fit is drawn at.
MOST_TILE, LEAST_TILE, FIXED_TILE = 26, 11, 14
HUD = 22


class AfootCanvas(QWidget):
    """The deck the screen is looking at."""

    def __init__(self, view):
        super().__init__()
        self.view = view
        self.hover = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName("afoot_canvas")
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self._seen_key = None
        self._seen = set()
        #: How far a ring is turned, and how far round it is, for this paint.
        self._roll, self._wide = 0, 0

    def sizeHint(self):  # noqa: N802
        return QSize(560, 420)

    def minimumSizeHint(self):  # noqa: N802
        return QSize(340, 260)

    # ── geometry ──────────────────────────────────────────────────────────

    @property
    def walk(self):
        return afoot.current(self.view.game)

    def frame(self):
        """(tile, x0, y0): the tile size and where square (0, 0) is drawn."""
        walk = self.walk
        deck = walk.decks[walk.viewing]
        w, h = self.width(), self.height() - HUD
        fit = min(w / max(1, deck.w), h / max(1, deck.h))
        if fit >= LEAST_TILE:
            tile = min(MOST_TILE, fit)
            return (tile, (w - tile * deck.w) / 2, (h - tile * deck.h) / 2)
        tile = FIXED_TILE
        who = next((a for a in walk.actors if a.id == walk.selected), None)
        cx, cy = (who.x, who.y) if who and who.deck == walk.viewing else (
            deck.w // 2, deck.h // 2)
        if deck.wrap:
            cx = (cx - self.roll()) % deck.w
        # A side that fits is centred; one that does not follows the one in
        # hand as far as its edge — and a ring's level has no edge to reach,
        # being turned so they stand in the middle of it.
        x0 = w / 2 - (cx + 0.5) * tile
        y0 = h / 2 - (cy + 0.5) * tile
        x0 = (w - deck.w * tile) / 2 if deck.w * tile <= w else min(
            0.0, max(w - deck.w * tile, x0))
        y0 = (h - deck.h * tile) / 2 if deck.h * tile <= h else min(
            0.0, max(h - deck.h * tile, y0))
        return tile, x0, y0

    def square_at(self, px: float, py: float):
        walk = self.walk
        if walk is None:
            return None
        tile, x0, y0 = self.frame()
        x, y = int((px - x0) // tile), int((py - y0) // tile)
        deck = walk.decks[walk.viewing]
        if 0 <= x < deck.w and 0 <= y < deck.h:
            return ((x + self.roll()) % deck.w if deck.wrap else x, y)
        return None

    def roll(self) -> int:
        """The deck column drawn at the left edge: 0, or on a ring's level
        whatever puts the one in hand (or the first of the party on it) in
        the middle column."""
        walk = self.walk
        deck = walk.decks[walk.viewing]
        if not deck.wrap:
            return 0
        here = [a for a in party(walk) if a.deck == walk.viewing]
        who = next((a for a in here if a.id == walk.selected),
                   here[0] if here else None)
        return (who.x - deck.w // 2) % deck.w if who is not None else 0

    def col(self, x: int) -> int:
        """The column a deck square is drawn in, this paint."""
        return (x - self._roll) % self._wide if self._wide else x

    def seen_now(self) -> set:
        """What the party can see on this deck, worked out once a move."""
        walk = self.walk
        key = (id(walk), walk.viewing, walk.version, walk.round, tuple(
            (a.deck, a.x, a.y) for a in party(walk, standing=True)))
        if key != self._seen_key:
            self._seen_key = key
            self._seen = afoot.visible(walk, walk.viewing)
        return self._seen

    # ── input ─────────────────────────────────────────────────────────────

    def mouseMoveEvent(self, ev):  # noqa: N802
        got = self.square_at(ev.position().x(), ev.position().y())
        if got != self.hover:
            self.hover = got
            self.update()

    def leaveEvent(self, ev):  # noqa: N802
        self.hover = None
        self.update()

    def mousePressEvent(self, ev):  # noqa: N802
        got = self.square_at(ev.position().x(), ev.position().y())
        if got is None:
            return
        self.setFocus()
        if ev.button() == Qt.MouseButton.LeftButton:
            self.view.clicked(*got)
        elif ev.button() == Qt.MouseButton.RightButton:
            self.view.approach(*got)

    #: Arrows, and Home/End/PgUp/PgDn for the diagonals — the numeric pad's
    #: own layout with Num Lock off. The digits belong to the screen keys.
    KEYS = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0),
            Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1),
            Qt.Key.Key_Home: (-1, -1), Qt.Key.Key_PageUp: (1, -1),
            Qt.Key.Key_End: (-1, 1), Qt.Key.Key_PageDown: (1, 1)}

    def keyPressEvent(self, ev):  # noqa: N802
        step = self.KEYS.get(ev.key())
        if step is not None:
            self.view.step(*step)
            return
        if ev.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.view.end_turn()
            return
        if ev.key() == Qt.Key.Key_Tab:
            self.view.next_member()
            return
        super().keyPressEvent(ev)

    def focusNextPrevChild(self, forward):  # noqa: N802
        return False            # Tab is the next person, not the next widget

    # ── painting ──────────────────────────────────────────────────────────

    @painting.safe_paint
    def paintEvent(self, _ev):  # noqa: N802
        p = QPainter(self)
        if not painting.alive(self, p):
            return
        p.fillRect(self.rect(), QColor(theme.GROUND))
        walk = self.walk
        if walk is None:
            p.end()
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        tile, x0, y0 = self.frame()
        deck = walk.decks[walk.viewing]
        self._roll, self._wide = self.roll(), deck.w if deck.wrap else 0
        now = self.seen_now()
        self._terrain(p, walk, deck, tile, x0, y0, now)
        self._seam(p, deck, tile, x0, y0)
        self._rooms(p, walk, tile, x0, y0)
        self._things(p, walk, tile, x0, y0, now)
        self._reach(p, walk, tile, x0, y0)
        self._people(p, walk, tile, x0, y0, now)
        self._hover(p, walk, tile, x0, y0, now)
        p.end()

    def _rect(self, x, y, tile, x0, y0, inset: float = 0.0) -> QRectF:
        return QRectF(x0 + self.col(x) * tile + inset, y0 + y * tile + inset,
                      tile - 2 * inset, tile - 2 * inset)

    def _seam(self, p, deck, tile, x0, y0) -> None:
        """A ring's two edges, marked as joined: a dashed line down each,
        and an arrow saying the corridor goes on round."""
        if not self._wide:
            return
        pen = QPen(QColor(theme.tint("lumen")), 1, Qt.PenStyle.DashLine)
        p.setPen(pen)
        top, bottom = y0, y0 + deck.h * tile
        for x in (x0, x0 + deck.w * tile):
            p.drawLine(QPointF(x, top), QPointF(x, bottom))
        p.setFont(QFont(theme.mono_family(), max(7, int(tile * 0.5))))
        box = QRectF(x0, bottom, tile * 1.5, tile * 1.2)
        p.drawText(box, Qt.AlignmentFlag.AlignCenter, "↻")
        p.drawText(box.translated(deck.w * tile - tile * 1.5, 0),
                   Qt.AlignmentFlag.AlignCenter, "↻")

    def _terrain(self, p, walk, deck, tile, x0, y0, now) -> None:
        wall = QColor(WALLS.get(deck.style, WALLS["fabricated"]))
        floor = QColor(FLOORS.get(deck.style, theme.PANEL2))
        hall = QColor(floor).lighter(118)
        ground = QColor(OPEN_GROUND[deck.outside_air])
        grown = deck.style in ("grown", "xeno")
        for y in range(deck.h):
            row = deck.rows[y]
            for x in range(deck.w):
                if not deck.was_seen(x, y) and (x, y) not in now:
                    continue
                cell = row[x]
                if cell == " ":
                    continue
                lit = (x, y) in now
                if cell in (WALL, WINDOW):
                    colour = QColor(wall if lit else wall.darker(190))
                    rect = self._rect(x, y, tile, x0, y0)
                    if grown:
                        p.setPen(Qt.PenStyle.NoPen)
                        p.setBrush(colour)
                        p.drawRoundedRect(rect, tile * 0.35, tile * 0.35)
                    else:
                        p.fillRect(rect, colour)
                    if cell == WINDOW:
                        p.fillRect(self._rect(x, y, tile, x0, y0, tile * 0.35),
                                   QColor(theme.tint("lumen")))
                    continue
                base = hall if cell == HALL else ground \
                    if cell == GROUND else floor
                p.fillRect(self._rect(x, y, tile, x0, y0),
                           base if lit else base.darker(210))
        if not deck.air:
            p.fillRect(QRectF(x0, y0, deck.w * tile, deck.h * tile),
                       QColor(40, 160, 190, 18))

    def _rooms(self, p, walk, tile, x0, y0) -> None:
        if tile < 12:
            return
        p.setFont(QFont(theme.mono_family(), max(6, int(tile * 0.36))))
        fm = QFontMetricsF(p.font())
        ink = QColor(theme.INK3)
        drawn: list = []
        for room in walk.rooms:
            if room.deck != walk.viewing or not room.known:
                continue
            p.setPen(QPen(ink))
            # On the room's own first row of floor: a room is the shape of
            # the hull it is in, not the box round it. Cut to the room's own
            # width, and left out rather than printed across a neighbour's.
            lx, ly, span = label_spot(room)
            cols = max(span, 3)
            if self._wide:          # a room turned across the edge is cut
                cols = min(cols, self._wide - self.col(lx))
            room_w = cols * tile - 4
            text = fm.elidedText(room.name.upper(), Qt.TextElideMode.ElideRight,
                                 room_w)
            box = QRectF(x0 + self.col(lx) * tile + 2, y0 + ly * tile + 1,
                         fm.horizontalAdvance(text), fm.height())
            if not text or any(box.intersects(other) for other in drawn):
                continue
            drawn.append(box)
            p.drawText(box, Qt.AlignmentFlag.AlignLeft, text)

    def _things(self, p, walk, tile, x0, y0, now) -> None:
        deck = walk.decks[walk.viewing]
        for t in walk.things:
            if t.deck != walk.viewing or not (
                    deck.was_seen(t.x, t.y) or (t.x, t.y) in now):
                continue
            kind = THING_BY_ID.get(t.kind)
            colour = QColor(theme.tint(getattr(kind, "tint", "dim")))
            if (t.x, t.y) not in now:
                colour = colour.darker(180)
            rect = self._rect(t.x, t.y, tile, x0, y0)
            draw_thing(p, t, rect, colour, tile)

    def _reach(self, p, walk, tile, x0, y0) -> None:
        who = next((a for a in walk.actors if a.id == walk.selected), None)
        if who is None or walk.mode != "action" or who.deck != walk.viewing \
                or not who.standing:
            return
        tint = QColor(theme.tint("lumen"))
        tint.setAlpha(34)
        for sq in afoot_map.reach(walk, who):
            p.fillRect(self._rect(*sq, tile, x0, y0, 1), tint)

    def _people(self, p, walk, tile, x0, y0, now) -> None:
        marks = tokens(walk)
        for a in walk.actors:
            if a.deck != walk.viewing or a.status == "gone":
                continue
            if any(b.carrying == a.id for b in walk.actors):
                continue
            if a.side != "party" and (a.x, a.y) not in now:
                continue
            tint = "chloro" if a.side == "party" else MOODS.get(a.mood, "ink")
            colour = QColor(theme.tint(tint))
            rect = self._rect(a.x, a.y, tile, x0, y0, tile * 0.14)
            if a.status in ("down", "stable", "dead"):
                p.setPen(QPen(colour.darker(150 if a.status != "dead" else 250),
                              max(1.5, tile * 0.1)))
                p.drawLine(rect.topLeft(), rect.bottomRight())
                p.drawLine(rect.topRight(), rect.bottomLeft())
                continue
            p.setPen(QPen(colour, 1.2))
            fill = QColor(colour)
            fill.setAlpha(70 if a.side == "npc" else 140)
            p.setBrush(fill)
            p.drawEllipse(rect)
            if a.id == walk.selected:
                p.setPen(QPen(QColor(theme.tint("lumen")), 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(self._rect(a.x, a.y, tile, x0, y0, 0.5))
            if a.carrying >= 0 or a.stance:
                p.setPen(QPen(QColor(theme.tint("osteo")), 1.5))
                p.drawArc(self._rect(a.x, a.y, tile, x0, y0, 1.5),
                          30 * 16, 120 * 16)
            p.setPen(QPen(QColor(theme.INK)))
            mark = marks.get(a.id, "?")
            p.setFont(QFont(theme.mono_family(), max(6, int(
                tile * (0.42 if len(mark) == 1 else 0.32))), QFont.Weight.Bold))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, mark)

    def _hover(self, p, walk, tile, x0, y0, now) -> None:
        text = hover_text(self.view.game, walk, self.hover, now)
        if self.hover is not None:
            p.setPen(QPen(QColor(theme.tint("lumen")), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(self._rect(*self.hover, tile, x0, y0, 0.5))
            who = next((a for a in walk.actors if a.id == walk.selected), None)
            if who is not None and who.deck == walk.viewing and who.standing:
                route = afoot_map.path(walk, who, *self.hover)
                if route:
                    pen = QPen(QColor(theme.tint("lumen")), 1.2,
                               Qt.PenStyle.DashLine)
                    p.setPen(pen)
                    last = QPointF(x0 + (self.col(who.x) + 0.5) * tile,
                                   y0 + (who.y + 0.5) * tile)
                    for sq in route:
                        nxt = QPointF(x0 + (self.col(sq[0]) + 0.5) * tile,
                                      y0 + (sq[1] + 0.5) * tile)
                        # A step across a ring's seam is one square, not a
                        # line across the whole of the ring.
                        if abs(nxt.x() - last.x()) <= tile * 1.5:
                            p.drawLine(last, nxt)
                        last = nxt
        band = QRectF(0, self.height() - HUD, self.width(), HUD)
        p.fillRect(band, QColor(theme.PANEL))
        p.setPen(QPen(QColor(theme.INK2)))
        p.setFont(QFont(theme.mono_family(), 9))
        inner = band.adjusted(8, 0, -8, 0)
        # Shortened to fit, never clipped mid-letter at a narrow window.
        text = QFontMetricsF(p.font()).elidedText(
            text, Qt.TextElideMode.ElideRight, inner.width())
        p.drawText(inner,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   text)
