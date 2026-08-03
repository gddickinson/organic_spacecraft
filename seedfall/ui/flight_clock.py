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

    **A held thruster outranks the computer.** `win.burn_order` is the hand
    on the stick — set on press, cleared on release, from any window or key
    — and while it stands, each beat is another minute of that thrust, so
    the speed *builds* instead of stepping: a press used to be one
    instantaneous impulse, which is what made the engines feel like a
    switch. `win.time_scale` beats several minutes at once; the burn, the
    computer and the bill all scale with it because they are all inside the
    loop.
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
    for _ in range(max(1, int(getattr(win, "time_scale", 1)))):
        free_sim.hold_course(win.game, conn)
        order = getattr(win, "burn_order", None)
        if order:
            last = conn_sim.apply(conn, order, main=conn.arm_main, ticks=1,
                                  throttle=conn.throttle)
            win.burn_fired = True
        else:
            axis, main, throttle = free_sim.computer(win.game, conn)
            last = conn_sim.apply(conn, axis, main=main, ticks=1,
                                  throttle=throttle)
        if conn.over:
            break
    pilot = win.views.get("pilot")
    if pilot is not None:
        pilot.last = last
    berth_sim.charge_flown(win.game, conn)
    if win.check_ending():
        win.set_conn_clock(False)
        return
    win.beat_refresh()


def start_burn(win, axis: str) -> None:
    """A hand comes down on a thruster: a standing order the beat consumes.

    Called on *press* (button or key) from any flying screen. While the
    order stands and the clock runs, every beat is another minute of that
    thrust — velocity builds over time, the plume stays lit on every
    diagram, and releasing the control is what ends the burn. With the
    clock held, nothing flies until release, and `end_burn` keeps the old
    precise press.
    """
    win.burn_order = axis
    win.burn_fired = False


def end_burn(win) -> None:
    """The hand comes off. If no beat consumed the order, press once.

    A quick click inside one beat (a click is 80–150 ms against a 250 ms
    beat) would otherwise burn nothing and read as a dead control — and
    with the clock *held*, this is the whole act: one press, at the coast
    and throttle the console shows, exactly what `pilot.quote` promises.
    """
    from ..sim import berthing as berth_sim
    from ..sim import conn as conn_sim
    from ..sim import freeflight as free_sim
    axis = getattr(win, "burn_order", None)
    fired = getattr(win, "burn_fired", False)
    win.burn_order = None
    conn = win.conn
    if not axis or fired or conn is None or conn.over or conn.landed:
        return
    running = bool(getattr(conn, "clock_on", False))
    free_sim.hold_course(win.game, conn)
    last = conn_sim.apply(conn, axis, main=conn.arm_main,
                          ticks=1 if running else conn.coast_min,
                          throttle=conn.throttle)
    pilot = win.views.get("pilot")
    if pilot is not None:
        pilot.last = last
    berth_sim.charge_flown(win.game, conn)
    win.beat_refresh()


def hold_wire(win, btn, axis: str) -> None:
    """Wire a thrust button for press-and-hold, on the one pair of doors.

    Every pad — bridge, conn console, flight panel — wires through here, so
    a held thruster means the same thing whichever screen the hand is on.
    """
    btn.pressed.connect(lambda a=axis: start_burn(win, a))
    btn.released.connect(lambda: end_burn(win))


#: The time-compression rungs the one beat may run at. A long run for a
#: distant mark is minutes of real time watching a range fall; the one-clock
#: design makes a multiplier safe to add in exactly one place.
SCALES = (1, 4, 16)


def cycle_scale(win) -> int:
    """Step the beat's compression round the rungs. Returns what was set."""
    here = int(getattr(win, "time_scale", 1))
    steps = list(SCALES)
    win.time_scale = steps[(steps.index(here) + 1) % len(steps)] \
        if here in steps else 1
    win.beat_refresh()
    return win.time_scale


def beat_refresh(win) -> None:
    """Redraw what a beat changes, without the full `refresh`.

    Deliberately *not* `refresh()`: that recomputes the whole game, redraws
    every open board and — the part that made the clock feel like treacle —
    used to write the entire sector to disk on every call. A beat updates the
    flying surfaces and the stardate; the heavy redraw still happens on every
    real act.
    """
    win._refresh_hud()
    view = win.views.get(win.current) if win.current else None
    if win.current == "pilot" and view is not None:
        view.refresh()
    elif hasattr(view, "beat_sync"):
        # A main-rail screen that wants to read the beat without paying for
        # a rebuild — the helm updates its clock chip this way. A full
        # `refresh()` here would eat the button under the player's finger,
        # which is the exact fault #150 recorded.
        view.beat_sync()
    for name in ("conn_window", "flight_window", "approach_window"):
        window = getattr(win, name, None)
        if window is not None:
            window.refresh()
