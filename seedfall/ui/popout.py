"""One door for opening a pop-out window, and for letting it go.

The conn, the flight controls, the approach view, the tactical and gunner
stations and the plotting board each open as their own window, held on the
`MainWindow` so there is only ever one of each. **None of them was ever
freed.** A `QDialog` parented to the main window is hidden by *Close*, not
destroyed, and the next open built a fresh one beside the corpse — measured,
five open-and-close cycles left 88 widgets behind per conn window, 44 per
flight panel, 41 per plotting board, 39 per tactical station, 21 per approach
view and 12 per gunner's station, for the length of the session.

So every pop-out is kept through `open_one`: `WA_DeleteOnClose` so closing is
freeing, and the window's slot on the main window cleared when the object is
destroyed. The second half matters as much as the first. `Esc` closes a
dialog through `reject`, which in Qt 6.3 and later deletes it *without*
delivering the `closeEvent` that used to clear the slot — and a slot left
pointing at a deleted window is a `RuntimeError` on the next refresh, or a
flight clock that thinks somebody is still watching (`flight_clock.on_deck`).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt


def open_one(win, name: str, build):
    """Raise `win.<name>` if it is open; otherwise build it, keep it, show it.

    `build` is called with no arguments and returns the window. The window is
    returned either way, so a caller can drive the one that is up.
    """
    existing = getattr(win, name, None)
    if existing is not None:
        existing.raise_()
        existing.activateWindow()
        return existing
    window = build()
    keep(win, name, window)
    window.show()
    return window


def keep(win, name: str, window) -> None:
    """Hold `window` as `win.<name>` until it closes, then let it go.

    The slot is cleared from `destroyed` rather than from `closeEvent`,
    because that is the one signal every route out emits. The handler touches
    nothing but a Python attribute: it can run while the main window itself is
    coming down, when calling into Qt would be calling into a corpse.
    """
    window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    setattr(win, name, window)

    def gone(*_):
        if getattr(win, name, None) is window:
            setattr(win, name, None)

    window.destroyed.connect(gone)


#: Every slot on the main window a pop-out is kept in. One list, because a
#: window that is coming down has to take all of them with it and a name
#: missing from here is a window that outlives its parent.
SLOTS = ("conn_window", "flight_window", "approach_window",
         "tactical_window", "gunner_window", "plot_window", "turret_window",
         "craft_window", "comms_window", "log_wide_window")


def close_all(win) -> int:
    """Close every pop-out this window is keeping. Returns how many.

    **A pop-out outlives the window that made it**, and that is fatal rather
    than untidy: each of these holds a `ui/viewport.Viewport`, and a viewport
    whose main window has been destroyed paints into a device that is gone —
    measured, `render3d.draw` at `painter.setBrush`, "Cannot destroy paint
    device that is being painted", and the process down with exit 139 and no
    traceback. `tests/test_verbs._put_down` learned the same lesson about the
    main window itself; this is the other half of it.
    """
    shut = 0
    for name in SLOTS:
        window = getattr(win, name, None)
        # Some of these slots hold a flag rather than a window — the wide
        # log is a bool on the main window — so this asks the object, not
        # the name.
        if window is None or not hasattr(window, "close"):
            continue
        setattr(win, name, None)
        try:
            window.close()
            window.deleteLater()
            shut += 1
        except RuntimeError:          # already a corpse; nothing to do
            continue
    return shut
