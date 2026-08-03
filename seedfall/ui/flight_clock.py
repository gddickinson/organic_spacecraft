"""The one clock that flies `game.conn`, and the one beat it delivers.

Split out of `ui/window.py`, which owns the timer, along the seam the clock
made when it moved there: the bridge, the Conn window and the flight panel
each ran a private QTimer on the shared `Conn`, so two open windows flew the
ship at double time and three Run/Stop buttons could read three different
answers. Now every window's button calls `set_conn_clock`, `Conn.clock_on` is
the one fact they all read, and this is the beat itself.

These are `MainWindow` methods in module clothing — each takes the window as
`win` and is bound in the class body — so a check that drives `win.fly_beat()`
is driving exactly what the timer fires.
"""

from __future__ import annotations


def set_conn_clock(win, on: bool) -> None:
    """Run or hold the one beat that flies `game.conn`.

    The only writer of `Conn.clock_on`. Every Run/Stop button — bridge, Conn
    window, flight panel — calls here and reads there, so no window can hold
    a private answer to "is time passing".
    """
    conn = win.conn
    on = bool(on) and conn is not None and not conn.landed
    if conn is not None:
        conn.clock_on = on
    if on:
        from .pilot_view import BEAT_MS
        win.flight_timer.start(BEAT_MS)
    else:
        win.flight_timer.stop()


def fly_beat(win) -> None:
    """One beat of the flight: steer, fly, pay, and tell every window.

    The whole of what the three per-window tick handlers used to do, once.
    The computer is `freeflight.computer` — the single dispatcher over
    `Conn.auto` — and the bill is `berthing.charge_flown`, which the bridge
    paid and the other two windows never did: measured, an hour flown from
    the Conn window left the stardate untouched.
    """
    from ..sim import berthing as berth_sim
    from ..sim import conn as conn_sim
    from ..sim import freeflight as free_sim
    conn = win.conn
    if conn is None or conn.landed:
        win.set_conn_clock(False)
        return
    # No time passes while you are being shot at — the rule the whole battle
    # layer stands on, and one the per-window clocks used to leak around:
    # the Conn window's own timer beat on under fire.
    if win.battle is not None and not win.battle.over:
        win.set_conn_clock(False)
        return
    if conn.over:
        out = berth_sim.commit(win.game, conn)
        if out.get("lost"):
            win.toast("The hull is gone.", "bad")
        elif out.get("moved"):
            win.toast(f"{conn.outcome.title()} at {out['moved']}. "
                      f"{out['fuel']:.2f} t spent.", "good")
        win.set_conn_clock(False)
        win.refresh()
        return
    free_sim.hold_course(win.game, conn)
    axis, main, throttle = free_sim.computer(win.game, conn)
    last = conn_sim.apply(conn, axis, main=main, ticks=1, throttle=throttle)
    pilot = win.views.get("pilot")
    if pilot is not None:
        pilot.last = last
    berth_sim.charge_flown(win.game, conn)
    if win.check_ending():
        win.set_conn_clock(False)
        return
    win.beat_refresh()


def beat_refresh(win) -> None:
    """Redraw what a beat changes, without the full `refresh`.

    Deliberately *not* `refresh()`: that recomputes the whole game, redraws
    every open board and — the part that made the clock feel like treacle —
    used to write the entire sector to disk on every call. A beat updates the
    flying surfaces and the stardate; the heavy redraw still happens on every
    real act.
    """
    win._refresh_hud()
    if win.current == "pilot":
        view = win.views.get("pilot")
        if view is not None:
            view.refresh()
    for name in ("conn_window", "flight_window", "approach_window"):
        window = getattr(win, name, None)
        if window is not None:
            window.refresh()
