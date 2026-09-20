"""What the bridge's own controls do when they are pressed.

Split out of `ui/pilot_view.py` at the five-hundred-line ratchet, along the
seam `ui/conn_moves.py` already cut for the conn window: the screen is one
question and the acts its buttons perform are another. These are `PilotView`
methods in module clothing — each takes the view as `self` and is bound in
the class body — so a check that calls `view._cycle_throttle()` is calling
exactly what the button calls.
"""

from __future__ import annotations

from ..sim import pilot as pilot_sim


def _look(self, view_id: str) -> None:
    self.camera = view_id
    self.refresh()


def _toggle_main(self) -> None:
    self.use_main = not self.use_main
    self.refresh()


def _cycle_throttle(self) -> None:
    """Step round `pilot.THROTTLE_STEPS`, through the one door that sets it.

    **The first draft kept its own `self.throttle`** and passed it to
    `apply` as a keyword. Rendered and looked at, the button read
    "THROTTLE: 50%" and the ship panel one row below it read "Throttle
    100%" — the same fact, two answers, because `instruments.readout`
    reads `conn.throttle` and nothing had written it. The throttle lives
    on the conn; `pilot.set_throttle` is its only writer.
    """
    steps = list(pilot_sim.THROTTLE_STEPS)
    here = min(range(len(steps)),
               key=lambda i: abs(steps[i] - self.conn.throttle))
    pilot_sim.set_throttle(self.conn, steps[(here + 1) % len(steps)])
    self.refresh()


def _toggle(self) -> None:
    self.set_running(not self.running)
    self.refresh()


def _cycle_scale(self) -> None:
    from . import flight_clock
    flight_clock.cycle_scale(self.win)
    self.refresh()


def _open_channel(self) -> None:
    """Talk to the nearest thing on the array; switch inside the window."""
    from .comms_window import open_comms
    rows = self.ranged()
    if not rows:
        self.win.toast("Nothing within reach of the array.", "warn")
        return
    open_comms(self.win, rows[0][1])


def _to_conn(self) -> None:
    """Hand this flight to an approach, carrying the way already on."""
    from .conn_window import open_conn
    self.set_running(False)
    open_conn(self.win)
