"""Reusable pieces of the interface: labels, panels, bars, cards and the base
:class:`View` every screen subclasses."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QSizePolicy,
                             QVBoxLayout, QWidget)

from . import theme

ALIGN_L = Qt.AlignmentFlag.AlignLeft
ALIGN_R = Qt.AlignmentFlag.AlignRight
ALIGN_TOP = Qt.AlignmentFlag.AlignTop


def label(text: str, role: str = "", tint: str = "", wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    if role:
        lb.setProperty("role", role)
    if tint:
        lb.setStyleSheet(f"color: {theme.tint(tint)};")
    lb.setWordWrap(wrap)
    lb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lb


def title(text: str, tint: str = "") -> QLabel:
    return label(text, "h3", tint)


def note(text: str) -> QLabel:
    return label(text, "note", wrap=True)


def body(text: str) -> QLabel:
    lb = label(text, "", wrap=True)
    lb.setStyleSheet(f"color: {theme.INK2};")
    return lb


def mono_label(text: str) -> QLabel:
    return label(text, "label")


def button(text: str, on_click=None, kind: str = "", tip: str = "",
           enabled: bool = True) -> QPushButton:
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    if tip:
        b.setToolTip(tip)
    b.setEnabled(enabled)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click:
        b.clicked.connect(lambda: on_click())
    return b


def hrule() -> QFrame:
    f = QFrame()
    f.setProperty("role", "hr")
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: {theme.LINE};")
    return f


def spacer(h: int = 8) -> QWidget:
    w = QWidget()
    w.setFixedHeight(h)
    return w


class Bar(QWidget):
    """A slim progress bar tinted by role."""

    def __init__(self, value: float = 0.0, tint: str = "chloro", height: int = 6):
        super().__init__()
        self._v = max(0.0, min(1.0, value))
        self._tint = tint
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_value(self, v: float, tint: str | None = None) -> None:
        self._v = max(0.0, min(1.0, v))
        if tint:
            self._tint = tint
        self.update()

    def paintEvent(self, _ev):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        radius = r.height() / 2
        track = QPainterPath()
        track.addRoundedRect(float(r.x()), float(r.y()), float(r.width()),
                             float(r.height()), radius, radius)
        p.fillPath(track, QColor(theme.LINE))
        if self._v > 0:
            fill = QPainterPath()
            fill.addRoundedRect(float(r.x()), float(r.y()),
                                max(r.height(), r.width() * self._v),
                                float(r.height()), radius, radius)
            p.fillPath(fill, QColor(theme.tint(self._tint)))
        p.end()


class Pill(QLabel):
    """A hairline capsule label."""

    def __init__(self, text: str, tint: str = "dim"):
        super().__init__(text.upper())
        colour = theme.tint(tint)
        self.setStyleSheet(
            f"font-family: '{theme.mono_family()}'; font-size: 8px;"
            f"letter-spacing: 1.3px; color: {colour};"
            f"border: 1px solid {colour}; border-radius: 8px; padding: 2px 8px;")
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)


class Panel(QFrame):
    """A bordered block with a vertical layout you add rows to."""

    def __init__(self, heading: str = "", tint: str = ""):
        super().__init__()
        self.setProperty("role", "panel")
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(15, 13, 15, 13)
        self.box.setSpacing(7)
        if heading:
            self.box.addWidget(title(heading, tint))

    def add(self, *widgets) -> "Panel":
        for w in widgets:
            if w is None:
                continue
            if isinstance(w, str):
                self.box.addWidget(body(w))
            else:
                self.box.addWidget(w)
        return self

    def add_row(self, key: str, value: str, tint: str = "") -> "Panel":
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 2, 0, 2)
        k = label(key, "dim")
        v = label(str(value), "", tint)
        v.setAlignment(ALIGN_R | Qt.AlignmentFlag.AlignVCenter)
        h.addWidget(k)
        h.addStretch(1)
        h.addWidget(v)
        self.box.addWidget(row)
        return self

    def add_bar(self, value: float, tint: str = "chloro") -> Bar:
        b = Bar(value, tint)
        self.box.addWidget(b)
        return b

    def add_buttons(self, *buttons) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 6, 0, 0)
        h.setSpacing(7)
        for b in buttons:
            if b is not None:
                h.addWidget(b)
        h.addStretch(1)
        self.box.addWidget(row)
        return row

    def stretch(self) -> "Panel":
        self.box.addStretch(1)
        return self


class Card(QFrame):
    """A clickable tile. Emits :attr:`clicked` when pressed."""

    clicked = pyqtSignal()

    def __init__(self, selectable: bool = True):
        super().__init__()
        self.setProperty("role", "card")
        self._selected = False
        self._selectable = selectable
        if selectable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(13, 11, 13, 11)
        self.box.setSpacing(4)

    def add(self, *widgets) -> "Card":
        for w in widgets:
            if w is None:
                continue
            self.box.addWidget(body(w) if isinstance(w, str) else w)
        return self

    def set_selected(self, on: bool) -> None:
        self._selected = on
        colour = theme.tint("chloro") if on else theme.LINE
        bg = "rgba(84,207,124,0.07)" if on else theme.PANEL
        self.setStyleSheet(
            f"QFrame[role='card'] {{ border: 1px solid {colour}; background: {bg};"
            "border-radius: 3px; }")

    def mousePressEvent(self, ev):  # noqa: N802
        if self._selectable and ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(ev)


class TabBar(QWidget):
    """Exclusive tab buttons, wrapped onto fixed rows.

    A dozen tabs in one row forces a minimum width wider than the view, which
    clips everything beside it. Wrapping is done by chunking into explicit rows
    rather than by a height-for-width layout: inside a scroll area the latter
    negotiates badly and collapses the column it sits above.
    """

    changed = pyqtSignal(str)
    PER_ROW = 7

    def __init__(self, tabs: list[tuple[str, str]], current: str | None = None,
                 per_row: int | None = None):
        super().__init__()
        per_row = per_row or self.PER_ROW
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 6)
        outer.setSpacing(2)
        self.buttons: dict[str, QPushButton] = {}

        for start in range(0, len(tabs), per_row):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(2)
            for tid, text in tabs[start:start + per_row]:
                b = button(text, kind="tab")
                b.setCheckable(True)
                b.clicked.connect(lambda _=False, t=tid: self.select(t))
                self.buttons[tid] = b
                h.addWidget(b)
            h.addStretch(1)
            outer.addWidget(row)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.current = current or tabs[0][0]
        self.buttons[self.current].setChecked(True)

    def select(self, tid: str) -> None:
        self.current = tid
        for k, b in self.buttons.items():
            b.setChecked(k == tid)
        self.changed.emit(tid)


class View(QScrollArea):
    """Base class for every screen.

    Subclasses implement :meth:`build`, adding widgets to ``self.col``. The
    window calls :meth:`refresh` whenever the world changes.
    """

    heading = ""
    subheading = ""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._inner = QWidget()
        self.col = QVBoxLayout(self._inner)
        self.col.setContentsMargins(22, 18, 22, 40)
        self.col.setSpacing(12)
        self.col.setAlignment(ALIGN_TOP)
        self.setWidget(self._inner)

    @property
    def game(self):
        return self.win.game

    def refresh(self) -> None:
        while self.col.count():
            item = self.col.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        self.build()
        self.col.addStretch(1)

    def build(self) -> None:      # pragma: no cover - overridden
        raise NotImplementedError

    def head(self, heading: str, sub: str = "") -> None:
        self.col.addWidget(label(heading, "h1"))
        if sub:
            self.col.addWidget(label(sub, "sub", wrap=True))
        self.col.addWidget(spacer(4))

    def row(self, *widgets, spacing: int = 12) -> QWidget:
        """A horizontal band of widgets, added to the column."""
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(spacing)
        for x in widgets:
            if x is not None:
                h.addWidget(x, 1)
        self.col.addWidget(w)
        return w

    def buttons(self, *btns) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(7)
        for b in btns:
            if b is not None:
                h.addWidget(b)
        h.addStretch(1)
        self.col.addWidget(w)
        return w

    def grid(self, widgets, cols: int = 3, spacing: int = 12) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(spacing)
        for i, item in enumerate(widgets):
            # Cards hold wrapped text, so let them shrink rather than demand
            # their natural width — otherwise the last column is clipped off.
            item.setSizePolicy(QSizePolicy.Policy.Ignored,
                               QSizePolicy.Policy.MinimumExpanding)
            g.addWidget(item, i // cols, i % cols)
        for c in range(cols):
            g.setColumnStretch(c, 1)      # equal columns, sharing the width
        self.col.addWidget(w)
        return w
