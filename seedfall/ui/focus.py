"""Keeping the player's place on the keyboard across a rebuild.

Almost every action rebuilds its screen (`View.refresh`), and the rebuild
frees the widget that had the focus. Qt then hands focus to the next widget
that will take it, which was the heading bar's first button — so on the
keyboard every action ended with the player thrown out of the screen they
were working in.

A widget is found again by what it is called: its `objectName` when it has
one (the flying controls and cards do), its text otherwise, and *which one*
of the widgets sharing that name — thirteen Buy buttons are thirteen
different places. When the widget is gone (a button that disappeared because
its act was done) the focus goes to the nearest survivor of the same kind,
then to the screen itself, never to the heading bar.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget

from .widgets import defer


def _name(w: QWidget) -> str:
    if w.objectName():
        return w.objectName()
    text = getattr(w, "text", None)
    if callable(text):
        try:
            return str(text())
        except TypeError:
            return ""
    return ""


def _takers(view) -> list:
    """Every widget on the screen that takes the focus by Tab, in order."""
    inner = view.widget()
    if inner is None:
        return []
    return [w for w in inner.findChildren(QWidget)
            if w.focusPolicy() & Qt.FocusPolicy.TabFocus and w.isEnabled()]


def remember(view):
    """Where the focus is on this screen, as something a rebuild keeps."""
    app = QApplication.instance()
    w = app.focusWidget() if app is not None else None
    if w is None or not view.isAncestorOf(w):
        return None
    kind, name = type(w).__name__, _name(w)
    same = [x for x in _takers(view)
            if type(x).__name__ == kind and _name(x) == name]
    nth = same.index(w) if w in same else 0
    return kind, name, nth


def restore(view, held) -> None:
    """Put the focus back where `remember` found it, once the new widgets
    are shown — a widget that has not been shown yet cannot take it."""
    if held is None:
        return
    defer(lambda: _land(view, held))


def _land(view, held) -> None:
    try:
        if not view.isVisible():
            return
        kind, name, nth = held
        takers = [w for w in _takers(view) if w.isVisible()]
        same = [w for w in takers
                if type(w).__name__ == kind and _name(w) == name]
        if same:
            target = same[min(nth, len(same) - 1)]
        else:
            kin = [w for w in takers if type(w).__name__ == kind]
            target = kin[0] if kin else (takers[0] if takers else view)
        target.setFocus(Qt.FocusReason.OtherFocusReason)
    except RuntimeError:
        return          # the screen was rebuilt again before the loop came back


def where(view) -> str:
    """The focused widget's name on this screen, or "" — for the checks."""
    app = QApplication.instance()
    w = app.focusWidget() if app is not None else None
    if w is None or not view.isAncestorOf(w):
        return ""
    return _name(w)
