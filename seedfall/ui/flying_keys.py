"""Keys for the six axes, on every screen a hand can fly from.

The pad was mouse-only: six buttons for six directions, each a pointer trip.
A held key is a held thruster — the same `flight_clock.start_burn` /
`end_burn` doors the buttons wire through, so a key and a button cannot mean
different things. W/S along the line of flight, A/D across it, R/F up and
down — chosen to sit under one hand and to collide with nothing the screens
bind (Qt gives any focused text field the key first; only unhandled presses
reach these handlers).

Auto-repeat is swallowed on purpose: the *first* press starts the order and
the release ends it, which is what a hold is. Treating each repeat as a new
press would fire `end_burn`'s one-tick fallback dozens of times a second.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt

from . import flight_clock

#: Which key flies which axis. The axis ids are `data/mounts.AXES`'s.
KEYS = {
    Qt.Key.Key_W: "forward", Qt.Key.Key_S: "back",
    Qt.Key.Key_A: "left", Qt.Key.Key_D: "right",
    Qt.Key.Key_R: "up", Qt.Key.Key_F: "down",
}


def press(win, event) -> bool:
    """A key goes down. True if it was a flying key (consume the event)."""
    axis = KEYS.get(event.key())
    if axis is None:
        return False
    if event.isAutoRepeat():
        return True
    flight_clock.start_burn(win, axis)
    return True


def release(win, event) -> bool:
    """The key comes up. True if it was a flying key (consume the event)."""
    axis = KEYS.get(event.key())
    if axis is None:
        return False
    if event.isAutoRepeat():
        return True
    # Only the key that holds the order releases it — mashing two keys and
    # lifting the first must not cut the second one's burn.
    if getattr(win, "burn_order", None) == axis:
        flight_clock.end_burn(win)
    return True
