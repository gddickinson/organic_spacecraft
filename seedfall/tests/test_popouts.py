"""A pop-out window closed is a pop-out window freed.

The six flying and fighting windows — conn, flight controls, approach view,
tactical and gunner's stations, plotting board — were dialogs parented to the
main window, and *Close* only hid them. Every open built a fresh one beside
the last. Measured before `ui/popout.py`: five open-and-close cycles of each
left 88, 44, 21, 39, 12 and 41 widgets behind *per open*, for the rest of the
session. Counted here through the doors the game uses (`open_conn` and the
rest), because a window built directly by a check is not the window a player
closes.
"""

from __future__ import annotations

from .test_ui import _use_offscreen

_use_offscreen()

#: Open-and-close cycles per window. One is a warm-up: the first open of the
#: conn takes a flight, which is state the chronicle keeps, not a leak.
CYCLES = 4


def run(suite) -> bool:
    try:
        from PyQt6.QtCore import QCoreApplication, QEvent
        from PyQt6.QtWidgets import QApplication
    except ImportError as err:
        print(f"── pop-outs ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    from ..core.state import new_game
    from ..sim import anchorage as anchorage_sim
    from ..ui import (approach_window, conn_window, flight_window,
                      gunner_window, plot3d_window, tactical_window, theme)
    from ..ui.window import MainWindow

    check = suite.check
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    game = new_game("popout-seed")
    places = anchorage_sim.in_system(game)
    if places:
        game.orbit_body = game.system.bodies[places[0].body_index].id
    win = MainWindow(game)
    win.toast = lambda *a, **k: None
    win.dialog = lambda *a, **k: None
    win.confirm = lambda *a, **k: False

    def flush() -> None:
        # `deleteLater` is only honoured by the event loop, so a count taken
        # straight after `close()` would still see the window.
        for _ in range(3):
            app.processEvents()
            QCoreApplication.sendPostedEvents(
                None, QEvent.Type.DeferredDelete.value)

    doors = {
        "conn_window": conn_window.open_conn,
        "flight_window": flight_window.open_flight,
        "approach_window": approach_window.open_approach,
        "tactical_window": tactical_window.open_tactical,
        "gunner_window": gunner_window.open_gunnery,
        "plot_window": plot3d_window.open_plot,
    }

    def cycles(door, how) -> int:
        """Widgets left behind over `CYCLES` opens, after a warm-up open.

        The total, not a per-open average: integer division would round a
        leak of three widgets over four opens down to nothing.
        """
        how(door(win))
        flush()
        before = len(QApplication.allWidgets())
        for _ in range(CYCLES):
            how(door(win))
            flush()
        return len(QApplication.allWidgets()) - before

    @check("closing a pop-out frees it, through every door that opens one")
    def _():
        grown = {name: cycles(door, lambda w: w.close())
                 for name, door in doors.items()}
        kept = {name: n for name, n in grown.items() if n > 0}
        assert not kept, f"widgets left behind over {CYCLES} opens: {kept}"
        slots = {name: getattr(win, name, None) for name in doors}
        assert not any(slots.values()), f"slots still held: {slots}"
        return f"{len(doors)} windows, {CYCLES} cycles each, nothing kept"

    @check("Esc frees it too, and the main window lets go of it")
    def _():
        # `reject` is what Esc does, and from Qt 6.3 it closes a dialog
        # without delivering the `closeEvent` that cleared the slot. A slot
        # left pointing at a deleted window is a `RuntimeError` on the next
        # refresh, and a flight clock that thinks somebody is watching.
        grown = {name: cycles(door, lambda w: w.reject())
                 for name, door in doors.items()}
        kept = {name: n for name, n in grown.items() if n > 0}
        assert not kept, f"widgets left behind over {CYCLES} Escs: {kept}"
        slots = {name: getattr(win, name, None) for name in doors}
        assert not any(slots.values()), f"slots still held: {slots}"
        win.refresh()          # the loop over the pop-outs must not trip
        return "rejected, freed, and the refresh loop runs clean"

    @check("the instrument windows are freed the same way")
    def _():
        from ..ui import monitors
        grown = {}
        for instrument in monitors.SHAPES:
            def door(w, i=instrument):
                monitors.toggle(w, i)
                return w.monitors[i]
            grown[instrument] = cycles(door, lambda m: m.reject())
        kept = {name: n for name, n in grown.items() if n > 0}
        assert not kept, f"instrument widgets left behind: {kept}"
        assert not win.monitors, f"registry still holds {sorted(win.monitors)}"
        win.apply_options()    # walks the registry; must meet no corpse
        return f"{len(grown)} instruments, closed by Esc, nothing kept"

    @check("the count can still see a window that is not freed")
    def _():
        # A leak check that cannot fail proves nothing. Built without the
        # door, a flight panel is the old kind — hidden on close, never freed
        # — and the same count has to catch it.
        leaked = cycles(lambda w: flight_window.FlightWindow(w),
                        lambda w: w.close())
        assert leaked > 0, "a window hidden and kept was not counted"
        return (f"{leaked / CYCLES:.0f} widgets per open when the door is "
                "bypassed")

    win.close()
    return True
