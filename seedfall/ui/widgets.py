"""Reusable pieces of the interface: labels, panels, bars, cards and tabs.

The base :class:`View` every screen subclasses lives in `ui/view_base.py` and
is re-exported here, so a screen still writes `from .widgets import View`.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                             QSizePolicy, QVBoxLayout, QWidget)

from . import theme
from . import painting
from . import soundmap

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


#: Whether inline explanations are drawn at all.
#:
#: **Module state, pushed in by `MainWindow.apply_options`** — `note` is a
#: free function called from 270 places, most inside panel builders with no
#: view and no `Game` to ask. `View.hint` was the only gate and is called
#: **10** times against those 270, so "Inline hints" turned off under four per
#: cent of them: measured on the port screen, 89 labels either way. An option
#: that changes almost nothing is the lie `sim/options.py` opens by forbidding.
HINTS = True


def note(text: str) -> QLabel:
    """An inline explanation, hidden when the player has turned them off.

    **Hidden rather than `None`.** Returning `None` works for the panels —
    `Panel.add` skips it — and breaks the fifteen places that put a note straight
    into a layout with `addWidget`, which Qt answers with "cannot add a null
    widget". A widget that is explicitly hidden is excluded from its layout and
    takes no space at all, so all two hundred and eighty call sites get the
    setting without one of them changing.
    """
    made = label("" if not HINTS else text, "note", wrap=True)
    if not HINTS:
        made.setHidden(True)
    return made


def body(text: str) -> QLabel:
    lb = label(text, "", wrap=True)
    lb.setStyleSheet(f"color: {theme.INK2};")
    return lb


def defer(fn) -> None:
    """Run this after the current event has finished being delivered.

    The rule it exists for: **a signal handler must not destroy the widget
    that emitted it.** Almost every handler here rebuilds its own screen, and
    `View.refresh` unparents the old widgets, which frees them immediately —
    so Qt returns from the emit into a corpse. With a `Card` that aborted the
    process; with a `QLineEdit` mid-keystroke it segfaulted outright.

    Anything wired to `textChanged`, `currentIndexChanged`, `clicked` on a
    hand-rolled widget, or anything else that rebuilds, goes through here.
    """
    QTimer.singleShot(0, fn)


def body_or(widget):
    """A widget, or an invisible spacer when a hint has been turned off."""
    return widget if widget is not None else spacer(0)


def mono_label(text: str) -> QLabel:
    return label(text, "label")


def button(text: str, on_click=None, kind: str = "", tip: str = "",
           enabled: bool = True, why: str = "") -> QPushButton:
    """A push button. `why` is what a *disabled* one says when hovered.

    A greyed-out button that will not say why is a dead end: the Port's
    thirteen Sell buttons and the Research screen had no tooltips at all.
    The reason is the tooltip only while the button is off, so an enabled
    button keeps its own `tip`.
    """
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    shown = why if (why and not enabled) else tip
    if shown:
        b.setToolTip(shown)
    b.setEnabled(enabled)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.clicked.connect(soundmap.click)   # first: it sounds before a dialog
    if on_click:
        b.clicked.connect(lambda: on_click())
    return b


#: How a control that is *firing right now* is drawn. A pilot watching the
#: computer work needs to see which thruster it is using, and the pad is six
#: identical buttons — so the lit one carries its own border and glow rather
#: than a word nobody will read in the half-second it is on.
LIT_STYLE = ("border: 1px solid {tint}; color: {tint}; "
             "background: rgba(90, 210, 160, 0.14);")


def light(btn, on: bool, tint: str = "lumen") -> None:
    """Light a button, or put it out. Idempotent, and safe on any button.

    Set as an explicit stylesheet rather than a Qt property, because the
    theme's sheet is applied to the whole window and a property would need a
    re-polish on every refresh — which is a repaint of everything, sixty times
    a berthing.
    """
    btn.setStyleSheet(LIT_STYLE.format(tint=theme.tint(tint)) if on else "")


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

    @painting.safe_paint
    def paintEvent(self, _ev):  # noqa: N802
        p = QPainter(self)
        if not painting.alive(self, p):
            return
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


class Elided(QLabel):
    """One line of text that shortens itself with "…" rather than push.

    The heading bar's ship name ran "NAVIS «Patient Incr" into the meters
    beside it at 1360 px, and the position overprinted at 1040. This label
    asks for its full width when there is room and gives it up when there
    is not; the whole text stays on the tooltip.
    """

    def __init__(self, text: str = "", least: int = 60):
        super().__init__()
        self._full = ""
        self._least = least
        self.set_full(text)

    def set_full(self, text: str) -> None:
        if text == self._full:
            return
        self._full = text
        self.setToolTip(text)
        self.setAccessibleName(text)
        self._fit(self.width())
        self.updateGeometry()

    def full(self) -> str:
        return self._full

    def sizeHint(self):  # noqa: N802
        hint = super().sizeHint()
        hint.setWidth(self.fontMetrics().horizontalAdvance(self._full) + 4)
        return hint

    def minimumSizeHint(self):  # noqa: N802
        hint = super().minimumSizeHint()
        hint.setWidth(min(self._least, self.sizeHint().width()))
        return hint

    def resizeEvent(self, ev):  # noqa: N802
        super().resizeEvent(ev)
        self._fit(ev.size().width())

    def _fit(self, width: int) -> None:
        shown = self.fontMetrics().elidedText(
            self._full, Qt.TextElideMode.ElideRight, max(0, width - 2))
        if shown != self.text():
            self.setText(shown)


class Pill(QLabel):
    """A hairline capsule label."""

    def __init__(self, text: str, tint: str = "dim"):
        super().__init__()
        self._tint = None
        self.set_tint(text, tint)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

    def set_tint(self, text: str, tint: str = "dim") -> None:
        """Change what it says and its colour, restyling only on a change —
        a board updated in place (`ui/market_grid.py`) calls this every
        refresh, and a stylesheet set is a re-polish."""
        self.setText(text.upper())
        if tint == self._tint:
            return
        self._tint = tint
        colour = theme.tint(tint)
        self.setStyleSheet(
            f"font-family: '{theme.mono_family()}'; font-size: 8px;"
            f"letter-spacing: 1.3px; color: {colour};"
            f"border: 1px solid {colour}; border-radius: 8px; padding: 2px 8px;")


class Panel(QFrame):
    """A bordered block with a vertical layout you add rows to."""

    def __init__(self, heading: str = "", tint: str = ""):
        super().__init__()
        self.setProperty("role", "panel")
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(15, 13, 15, 13)
        self.box.setSpacing(7)
        # Side by side, the shorter panel used to have its rows dragged apart
        # to fill the taller one's height. The frame still matches; the content
        # stays where it was put.
        self.box.setAlignment(ALIGN_TOP)
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

    def add_stacked(self, key: str, value: str, tint: str = "") -> "Panel":
        """`add_row` for a sentence: the key above, the value wrapped under
        it. Side by side, a row's minimum width is its whole sentence, and a
        panel of them pushed the Academy and the Helm's burn board wide."""
        self.box.addWidget(label(key, "dim", tint))
        self.box.addWidget(label(str(value), "", wrap=True))
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
    """A clickable tile. Emits :attr:`clicked` when pressed — by the mouse,
    or by Space or Enter once it has the keyboard focus."""

    clicked = pyqtSignal()

    def __init__(self, selectable: bool = True):
        super().__init__()
        self.setProperty("role", "card")
        self._selected = False
        self._selectable = selectable
        if selectable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            # **A card is a button, so the keyboard reaches it.** Cards carry
            # the system's bodies, the research tree, the hull classes and the
            # new-game choices, and none of them took focus — so none of that
            # could be played without a mouse.
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(13, 11, 13, 11)
        self.box.setSpacing(4)

    def add(self, *widgets) -> "Card":
        for w in widgets:
            if w is None:
                continue
            made = body(w) if isinstance(w, str) else w
            # The first line on a card is its name: what a screen reader
            # says, and what `ui/focus.py` finds it by after a rebuild.
            if not self.accessibleName() and isinstance(made, QLabel):
                self.setAccessibleName(made.text())
                self.setObjectName(f"card:{made.text()}")
            self.box.addWidget(made)
        return self

    def set_selected(self, on: bool) -> None:
        self._selected = on
        colour = theme.tint("chloro") if on else theme.LINE
        bg = "rgba(84,207,124,0.07)" if on else theme.PANEL
        # The focus ring is repeated here because a widget's own sheet beats
        # the application's whatever the specificity — without it a selected
        # card that had the focus showed no sign of it.
        self.setStyleSheet(
            f"QFrame[role='card'] {{ border: 1px solid {colour}; background: {bg};"
            "border-radius: 3px; }"
            f"QFrame[role='card']:focus {{ border: 1px solid {theme.tint('lumen')}; }}")

    def keyPressEvent(self, ev):  # noqa: N802
        """Space and Enter press the card, deferred like a click is."""
        keys = (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter)
        if self._selectable and ev.key() in keys:
            ev.accept()
            QTimer.singleShot(0, self.clicked.emit)
            return
        super().keyPressEvent(ev)

    def mousePressEvent(self, ev):  # noqa: N802
        """Emit *after* the event has finished being delivered.

        Almost every handler on a card rebuilds the screen it lives on, and
        `View.refresh` unparents the old widgets — which destroys the C++
        object there and then. Emitting inline meant the very next statement,
        `super().mousePressEvent(ev)`, touched a freed Card and aborted the
        process: clicking a body on the System screen or a node on the
        Research screen killed the game outright.

        Deferring by one turn of the event loop lets Qt finish with the widget
        before anything can delete it. Nothing below this line may touch self.
        """
        super().mousePressEvent(ev)
        if self._selectable and ev.button() == Qt.MouseButton.LeftButton:
            QTimer.singleShot(0, self.clicked.emit)


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


def __getattr__(name: str):
    """`View` and `WrapRow`, re-exported from `ui/view_base.py`.

    Lazily, because `view_base` builds on the pieces above: an eager import
    at the top of this file would be circular, and one at the bottom breaks
    the moment anything imports `view_base` first.
    """
    if name in ("View", "WrapRow"):
        from . import view_base
        return getattr(view_base, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
