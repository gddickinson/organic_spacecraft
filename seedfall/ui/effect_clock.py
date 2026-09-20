"""The short clock that runs an animation after the flight's own clock has stopped.

A collision is the one moment in the game where the beat that draws the
picture stops *because of* the thing being drawn: `flight_clock.fly_beat`
resolves the approach, calls `set_conn_clock(False)` and returns, so without
this the crash would be painted exactly once and then hold still for ever.
The first frame of an explosion is not an explosion.

So: a second timer, forty milliseconds, that runs only while something is
live and stops itself the moment nothing is. It is deliberately *not* the
flight clock — the flight clock moves the ship and bills the chronicle, and
an animation must not advance the calendar by so much as a minute.

**It repaints the big pictures only.** A `Viewport` draws a lit world, a mesh
and a starfield; seven of them at twenty-five frames a second is not free,
and the six 120-pixel thumbnails have nothing in them a frame apart. They get
the wash and the rim mark on their next ordinary repaint, which is the next
beat — and at 120 px that is all they were ever going to show.
"""

from __future__ import annotations

#: The animation's frame, in milliseconds. Twenty-five a second: enough for a
#: shake to read as a shake rather than as a stutter, cheap enough that a
#: whole second of it costs less than one beat of the flight computer.
FRAME_MS = 40

#: Under this many pixels across, a picture is not worth a frame of its own.
#: The same bar `ui/effect_paint` draws thumbnails at, and for the same
#: reason — one number, so the two cannot disagree about what a thumbnail is.
BIG_ENOUGH = 200


def surfaces(win) -> list:
    """Every picture worth animating, wherever in the window tree it lives.

    Found rather than registered, because the flying surfaces are spread over
    a screen and three pop-outs and every one of them is parented to the main
    window — so one search finds the bridge's feed, the conn's main screen and
    the outside view without any of those three having to know this exists.
    """
    from .approach_window import ApproachView
    from .battle3d import Battle3D
    from .viewport import Viewport
    out = []
    for kind in (Viewport, ApproachView, Battle3D):
        for widget in win.findChildren(kind):
            if min(widget.width(), widget.height()) >= BIG_ENOUGH:
                out.append(widget)
    return out


#: How many frames a found set of surfaces is kept for before the tree is
#: walked again. Measured: `findChildren` over a window with three pop-outs
#: open costs 4.2 ms, against 16.9 ms for the whole frame — a quarter of the
#: budget spent finding the two widgets that were there last time. Eight
#: frames is a third of a second, so a window opened mid-crash still joins
#: the animation while there is something left to see.
REFIND_EVERY = 8


def _surfaces_now(win) -> list:
    """The found set, kept for a few frames. See `REFIND_EVERY`."""
    held = getattr(win, "effect_surfaces", None)
    count = int(getattr(win, "effect_frames", 0))
    win.effect_frames = count + 1
    if held is None or count % REFIND_EVERY == 0:
        held = surfaces(win)
        win.effect_surfaces = held
    return held


def wanted(win) -> bool:
    """Is there anything moving that a still picture would misrepresent?

    Three things: an effect on the glass in either picture — the flight
    deck's or the engagement's — and a hazard the alarm border is throbbing
    over. The last matters as much as the first: an alarm that only advances
    when the flight clock beats reads as a flicker, and a pilot who has
    *held* the clock to think gets no alarm at all.
    """
    from ..sim import shock as shock_sim
    from . import effects
    if effects.live() or effects.live(scene=shock_sim.BATTLE):
        return True
    conn = getattr(win, "conn", None)
    if conn is None or conn.over or conn.landed:
        return False
    from . import viewport_hud
    level = getattr(viewport_hud.world(conn).get("hazard"), "level", "")
    return level in ("brake", "imminent")


def pump(win) -> None:
    """Start the frame clock, if there is anything for it to do.

    Cheap to call and safe to call often: every path that flies the ship ends
    up here, and a timer already running is left alone by `QTimer.start`.
    """
    timer = getattr(win, "effect_timer", None)
    if timer is None:
        return
    if wanted(win):
        if not timer.isActive():
            # A fresh run looks for its surfaces again: what was open the
            # last time something exploded is not what is open now.
            win.effect_surfaces = None
            win.effect_frames = 0
            timer.start(FRAME_MS)
    elif timer.isActive():
        timer.stop()


def frame(win) -> None:
    """One frame: repaint the big pictures, and stop when nothing is left.

    Repaint, not refresh. `beat_refresh` recomputes panels and rebuilds rows;
    at twenty-five frames a second that is the churn the Pilot screen was
    fixed for (#150), and it would eat the button under the player's finger
    while they were reaching for it.
    """
    if not wanted(win):
        timer = getattr(win, "effect_timer", None)
        if timer is not None:
            timer.stop()
        # One last frame, so the picture does not keep a half-faded flash.
        _repaint(win)
        return
    _repaint(win)


def _repaint(win) -> None:
    """Ask every surface for a frame, and forget the ones that have gone.

    **A widget found a moment ago can be gone by now.** Every pop-out is
    `WA_DeleteOnClose` (`ui/popout.py`), so closing the conn window destroys
    its cameras' C++ objects while the Python wrappers live on in the found
    set — and `update()` on one of those raises `RuntimeError` *inside a
    timer slot*, where PyQt cannot propagate it. Measured the hard way: with
    the found set cached across frames, the `flightops` suite died at exit
    134 on all five of five runs, every check passing and nothing failing,
    which is the exact shape of fault `ui/painting.py` exists to stop.

    Caught rather than asked about, on the same grounds `painting.safe_paint`
    gives: the object can go away between the question and the call.
    """
    kept = []
    for widget in _surfaces_now(win):
        try:
            widget.update()
        except RuntimeError:
            continue                  # its C++ side is gone; drop it
        kept.append(widget)
    win.effect_surfaces = kept
