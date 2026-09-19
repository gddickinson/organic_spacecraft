"""The base class every screen subclasses, and the row that wraps.

Split out of `ui/widgets.py` when that file passed five hundred lines. The
seam is real: `widgets` holds the pieces a panel is made of, this holds the
thing a screen *is* — a scroll area with a column, and the rules for
rebuilding it without freeing a widget mid-signal. `widgets` still re-exports
`View`, so the twenty-three screens that import it from there are unchanged.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtWidgets import (QBoxLayout, QGridLayout, QHBoxLayout,
                             QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from .widgets import ALIGN_TOP, defer, label, note, spacer


class WrapRow(QWidget):
    """Side by side when there is room for it, one above the other when not.

    **A row of panels set the screen's minimum width to their sum.** Measured
    on a shown window at the enforced minimum of 1040×680, the Shipyard's
    fittings and "After refit" asked for 938 px of an 811 px column, and with
    horizontal scrolling off the right-hand panel was simply cut — the
    "After refit" clipping the backlog carried for weeks. Eleven of fifteen
    screens overflowed the same way.

    So the row reports the *narrowest* it can be (its widest child) as its
    minimum, and on every resize picks a direction: across when the width it
    was given holds every child at its own minimum, down when it does not.
    The children's minima do not depend on the direction, so the choice is
    stable — it cannot flip back and forth on one width.
    """

    def __init__(self, spacing: int = 12):
        super().__init__()
        self._box = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self._box.setContentsMargins(0, 0, 0, 0)
        self._box.setSpacing(spacing)
        self._kids: list[QWidget] = []

    def add(self, widget: QWidget, stretch: int = 1,
            align=None) -> "WrapRow":
        """`align` (say `Qt.AlignmentFlag.AlignTop`) keeps a child at its own
        height instead of the row's — a picture beside a long panel."""
        if align is None:
            self._box.addWidget(widget, stretch)
        else:
            self._box.addWidget(widget, stretch, align)
        self._kids.append(widget)
        return self

    def _shown(self) -> list:
        return [w for w in self._kids if not w.isHidden()]

    def need(self) -> int:
        """The width it takes to put every child side by side."""
        kids = self._shown()
        if not kids:
            return 0
        widths = [max(w.minimumSizeHint().width(), w.minimumWidth())
                  for w in kids]
        return sum(widths) + self._box.spacing() * (len(kids) - 1)

    def across(self) -> bool:
        return self._box.direction() == QBoxLayout.Direction.LeftToRight

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        base = super().minimumSizeHint()
        kids = self._shown()
        if not kids:
            return base
        narrow = max(max(w.minimumSizeHint().width(), w.minimumWidth())
                     for w in kids)
        return QSize(narrow, base.height())

    def resizeEvent(self, ev):  # noqa: N802
        super().resizeEvent(ev)
        want = (QBoxLayout.Direction.LeftToRight
                if ev.size().width() >= self.need()
                else QBoxLayout.Direction.TopToBottom)
        if self._box.direction() != want:
            self._box.setDirection(want)
            self.updateGeometry()


class Pane(QScrollArea):
    """A scrolling column that knows when its contents change height.

    `View` is one of these plus the rules for rebuilding a screen. The battle
    uses two more side by side, so its orders stay put while the readout
    beside them scrolls (`ui/battle_view.py`).
    """

    def __init__(self, margins=(22, 18, 22, 40)):
        super().__init__()
        self.setWidgetResizable(True)
        # **As needed, not always off.** With it off, anything wider than
        # the column was cut with no way to reach it: at 1040×680 all
        # thirteen of the Port's Sell buttons sat past the right edge. The
        # rows wrap first (`WrapRow`); the scroll bar is the backstop for
        # whatever cannot.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._inner = QWidget()
        self.col = QVBoxLayout(self._inner)
        self.col.setContentsMargins(*margins)
        self.col.setSpacing(12)
        self.col.setAlignment(ALIGN_TOP)
        self.setWidget(self._inner)

    def _sync_scroll(self) -> None:
        """Let the scroll area find out that the screen changed height.

        Rebuilding the column does not tell the scroll area its contents grew,
        and the layout's true minimum is not known until the new widgets have
        been polished — so a screen taller than the viewport was squashed into
        it instead of scrolling. Measure once now for the common case and once
        more after the event loop has settled, when the number is right.
        """
        self._inner.ensurePolished()
        self.col.invalidate()
        self.col.activate()
        self._inner.setMinimumHeight(self._need())
        self.updateGeometry()
        QTimer.singleShot(0, self._settle)

    def _need(self) -> int:
        """The column's height at the width it will actually get. The plain
        minimum sizes a wrapped line at a guessed width, so a two-line
        despatch was laid out one line tall for the first frame."""
        need = self.col.minimumSize().height()
        width = self.viewport().width()
        if width > 0 and self.col.hasHeightForWidth():
            need = max(need, self.col.heightForWidth(width))
        return need

    def _settle(self) -> None:
        try:
            self.col.activate()
        except RuntimeError:
            return          # the screen went down before the loop came back
        need = self._need()
        if need != self._inner.minimumHeight():
            self._inner.setMinimumHeight(need)
            self.updateGeometry()

    def showEvent(self, ev):  # noqa: N802
        super().showEvent(ev)
        self._sync_scroll()

    def resizeEvent(self, ev):  # noqa: N802
        super().resizeEvent(ev)
        QTimer.singleShot(0, self._settle)


class View(Pane):
    """Base class for every screen.

    Subclasses implement :meth:`build`, adding widgets to ``self.col``. The
    window calls :meth:`refresh` whenever the world changes.
    """

    heading = ""
    subheading = ""
    #: A screen that fills the window with panes of its own (the battle)
    #: rather than a column that runs on down the page.
    fills = False

    def __init__(self, win):
        super().__init__()
        self.win = win

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

        **Focus comes back to the control that had it**, by `objectName`
        (`ui/focus.py`). A rebuild frees the focused widget, and Qt handed
        focus to the first thing that would take it — the heading bar — so
        every action on the keyboard ended with the player's place lost.
        """
        from . import focus
        held = focus.remember(self)
        kept = self.keep()
        while self.col.count():
            item = self.col.takeAt(0)
            w = item.widget()
            if w is not None and not any(w is k for k in kept):
                self.park(w)
        self.build()
        if not self.fills:
            self.col.addStretch(1)
        # Rebuilding the column does not on its own tell the scroll area that
        # its contents changed size, so a screen taller than the viewport was
        # silently squashed instead of scrolling. Ask for the recalculation.
        self._sync_scroll()
        focus.restore(self, held)

    def keep(self) -> tuple:
        """Widgets a rebuild leaves standing for `build` to put back.

        Nothing, for almost every screen. The research tree keeps its cards
        and changes them in place (`ui/tech_tree.py`): taken out of the
        column but never unparented, they cost nothing to put back, where
        making them again cost a quarter of a second.
        """
        return ()

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

    def build(self) -> None:      # pragma: no cover - overridden
        raise NotImplementedError

    def head(self, heading: str, sub: str = "") -> None:
        self.col.addWidget(label(heading, "h1"))
        if sub:
            self.col.addWidget(label(sub, "sub", wrap=True))
        self.col.addWidget(spacer(4))

    def row(self, *widgets, spacing: int = 12) -> QWidget:
        """A band of widgets, added to the column: side by side when the
        column is wide enough for them, stacked when it is not (`WrapRow`)."""
        w = WrapRow(spacing)
        for x in widgets:
            if x is not None:
                w.add(x, 1)
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
