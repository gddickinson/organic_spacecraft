"""The harness the shock checks fly on: a frozen clock, a deck, a crash.

Split out of `tests/test_shock.py` when that file reached five hundred lines,
along the seam this project always uses for a suite that has grown: the
*claims* stay in the suite, and the machinery they all share — the clock
`ui/effects` reads, a window with the conn open on something you can hit,
flying her into it, and counting the pixels that moved — comes out here.

`NOW` is the one hook: `ui/effects.clock` is replaced with a read of it, the
way `soundmap.clock` is, so a check can ask what the glass looks like 300 ms
after a collision without waiting 300 ms for it.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import berthing as berth_sim
from ..sim import track as track_sim
from .qtkit import app as _app
from .qtkit import main_window


#: A frozen clock, so a check can ask what the picture looks like 300 ms after
#: a collision without waiting 300 ms for it. The one hook `ui/effects` leaves
#: for exactly this, the way `soundmap.clock` does.
NOW = [1_000.0]


def _at(when: float) -> float:
    NOW[0] = 1_000.0 + when
    return NOW[0]


def _deck(seed: str, kind: str = "anchorage"):
    """A window with the conn open on something that can be flown into."""
    from ..ui import effects
    from ..ui.conn_window import open_conn
    keep = _app()
    effects.clock = lambda: NOW[0]
    effects.clear()
    _at(0.0)
    game = new_game(seed)
    win = main_window(game, (1200, 820))
    target = next(c for c in track_sim.contacts(game)
                  if c.kind == kind and berth_sim.can_conn(game, c)[0])
    window = open_conn(win, target)
    window.resize(1000, 700)
    keep.processEvents()
    return win, window, win.conn


def _shut(win, window) -> None:
    keep = _app()
    window.close()
    keep.processEvents()
    win.close()
    keep.processEvents()


def _fly_into(win, conn, speed: float, beats: int = 3_000) -> None:
    """Point her at it, take the safeties off, and let the clock run."""
    conn.safeties = False
    span = conn.range_km
    conn.vel = [-p / span * speed for p in conn.pos]
    for _ in range(beats):
        win.fly_beat()
        if conn.over:
            return


def _fly_gently(win, conn, beats: int = 4_000) -> None:
    """Let the flight computer berth her, which is what it is for."""
    conn.auto = "close"
    win.set_conn_clock(True)
    for _ in range(beats):
        win.fly_beat()
        if conn.over:
            return


def _changed(feed, a: float, b: float) -> int:
    """How many sampled pixels differ between two instants of one camera."""
    _at(a)
    first = feed.grab().toImage()
    _at(b)
    again = feed.grab().toImage()
    w, h = feed.width(), feed.height()
    return sum(1 for y in range(0, h, 3) for x in range(0, w, 3)
               if first.pixel(x, y) != again.pixel(x, y))
