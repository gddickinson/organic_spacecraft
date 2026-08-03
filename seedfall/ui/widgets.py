"""Reusable pieces of the interface: labels, panels, bars, cards and the base
:class:`View` every screen subclasses."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QSizePolicy,
                             QVBoxLayout, QWidget)

from . import theme
from . import painting

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

    def hint(self, text: str):
        """An inline explanation, or nothing if the player turned them off.

        These are how most of this game explains itself, so the setting is not
        a beginner toggle — it is for somebody who has read them all.
        """
        from ..sim import options as options_sim
        if not options_sim.get(self.game, "hints"):
            return None
        return note(text)

    def refresh_later(self) -> None:
        """Rebuild after the current event, for handlers that would free their
        own widget mid-signal. See `defer`."""
        defer(self.refresh)

    def refresh(self) -> None:
        """Rebuild this screen, without freeing anything mid-event.

        The rule that keeps costing us a segfault: **a signal handler must not
        destroy the widget that emitted it.** Every handler here rebuilds, and
        this used to drop the last reference to the old widgets synchronously
        — so Qt returned from the emit into freed memory. It killed the
        process through a `Card`, through a `QLineEdit` mid-keystroke, and
        through a `QComboBox` whose popup was still delivering the click that
        dismissed it.

        Each was fixed at its call site with `defer`, one at a time, as players
        found them. This closes the class instead: every outgoing widget goes
        through `park`, whether or not the call site remembered.
        """
        while self.col.count():
            item = self.col.takeAt(0)
            if item.widget() is not None:
                self.park(item.widget())
        self.build()
        self.col.addStretch(1)
        # Rebuilding the column does not on its own tell the scroll area that
        # its contents changed size, so a screen taller than the viewport was
        # silently squashed instead of scrolling. Ask for the recalculation.
        self._sync_scroll()

    def park(self, w) -> None:
        """Take one widget off the screen without freeing it mid-event.

        The rule `refresh` explains, for one widget — used by it for the whole
        column, and by a screen swapping one readout for a fresher one while
        the pilot holds a button down elsewhere. Held on the view, not in a
        local: a local dies with the calling frame and takes the C++ object
        with it, which is the whole bug. *Appended*, never replaced — two
        rebuilds in one event would otherwise drop the first batch, the same
        bug in a rarer hat.
        """
        w.setParent(None)
        w.hide()
        if getattr(self, "_doomed", None) is None:
            self._doomed = []
            defer(self._release)
        self._doomed.append(w)

    def _release(self) -> None:
        """Let the previous screen's widgets go, now the event has finished."""
        self._doomed = None

    def _sync_scroll(self) -> None:
        """Let the scroll area find out that the screen changed height.

        Rebuilding the column does not tell the scroll area its contents grew,
        and the layout's true minimum is not known until the new widgets have
        been polished — so a screen taller than the viewport was squashed into
        it instead of scrolling. Measure once now for the common case and once
        more after the event loop has settled, when the number is right.
        """
        self.col.invalidate()
        self.col.activate()
        self._inner.setMinimumHeight(self.col.minimumSize().height())
        self.updateGeometry()
        QTimer.singleShot(0, self._settle)

    def _settle(self) -> None:
        self.col.activate()
        need = self.col.minimumSize().height()
        if need != self._inner.minimumHeight():
            self._inner.setMinimumHeight(need)
            self.updateGeometry()

    def showEvent(self, ev):  # noqa: N802
        super().showEvent(ev)
        self._sync_scroll()

    def resizeEvent(self, ev):  # noqa: N802
        super().resizeEvent(ev)
        QTimer.singleShot(0, self._settle)

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
