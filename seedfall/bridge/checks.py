"""What an argument from outside must be before a verb will act on it.

The protocol takes JSON from a pipe, and the verbs behind it were written for
a window whose controls can only produce sensible values. Review 2026-09-17
(#30) drove them with the values a pipe can carry instead, and every one of
these got through:

- `buy` with `NaN` tonnes: `min(units, room, afford, stocked)` in
  `sim/trade` is `NaN` when its first argument is, so credits and cargo both
  became `NaN` and the save carried it for ever.
- `survey -1` surveyed the last body, and `jump -1` targeted the last
  system: Python's negative index, working as designed on the wrong input.
- `extract` with zero days ran a working anyway.
- `remember` with `text=null` wrote a memory that raised on every later
  line from that speaker.

So every number is checked finite and inside a stated range, every index
against the list it indexes, and every string for type and length, **here,
at the boundary** — the sim behind it keeps trusting its callers, which are
otherwise all the game's own. A refusal is a `Refused`, which `dispatch`
turns into `{"ok": False, "why": ...}` like any other.
"""

from __future__ import annotations

import math

#: The longest line the server will read, in bytes. The longest legitimate
#: command is a `remember` with a few hundred characters of text; 64 KiB is
#: two orders of magnitude of headroom, and a bound where there was none.
MAX_LINE = 64 * 1024

#: The longest string any verb takes, unless it says otherwise.
MAX_WORDS = 200


class Refused(ValueError):
    """An argument the protocol will not act on, and why, in words."""


def whole(value, name: str, lo: int, hi: int) -> int:
    """An integer in `lo..hi`. A float must be integral; a bool is not one.

    Strings of digits are taken, because a hand-typed command sends "3" as
    readily as 3; "nan", "-1" and "3.5" are all refused on their merits.
    """
    if isinstance(value, bool) or value is None:
        raise Refused(f"{name} must be a whole number, not {value!r}.")
    if isinstance(value, str):
        try:
            value = int(value.strip())
        except ValueError:
            raise Refused(f"{name} must be a whole number, not {value!r}.")
    elif isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise Refused(f"{name} must be a whole number, not {value!r}.")
        value = int(value)
    elif not isinstance(value, int):
        raise Refused(f"{name} must be a whole number, not "
                      f"{type(value).__name__}.")
    if not lo <= value <= hi:
        raise Refused(f"{name} must be from {lo} to {hi}, not {value}.")
    return value


def index(value, name: str, items) -> int:
    """A position in `items`, and never one counted from the end."""
    if not items:
        raise Refused(f"There is no {name} to choose from.")
    return whole(value, name, 0, len(items) - 1)


def amount(value, name: str, hi: float, lo: float = 0.0,
           inclusive: bool = False) -> float:
    """A finite number above `lo` (or at it, with `inclusive`) and up to `hi`.

    `NaN` fails every comparison, which is exactly how it walked through
    `min()`: the test here is `isfinite`, not a comparison that `NaN` can
    lose quietly.
    """
    if isinstance(value, bool) or value is None:
        raise Refused(f"{name} must be a number, not {value!r}.")
    if isinstance(value, str):
        try:
            value = float(value.strip())
        except ValueError:
            raise Refused(f"{name} must be a number, not {value!r}.")
    if not isinstance(value, (int, float)):
        raise Refused(f"{name} must be a number, not {type(value).__name__}.")
    value = float(value)
    if not math.isfinite(value):
        raise Refused(f"{name} must be a finite number, not {value!r}.")
    low_ok = value >= lo if inclusive else value > lo
    if not low_ok or value > hi:
        bound = "at least" if inclusive else "more than"
        raise Refused(f"{name} must be {bound} {lo:g} and at most {hi:g}, "
                      f"not {value:g}.")
    return value


def words(value, name: str, limit: int = MAX_WORDS,
          required: bool = False) -> str:
    """A string, not too long, and not empty when it is `required`."""
    if not isinstance(value, str):
        raise Refused(f"{name} must be text, not "
                      f"{'null' if value is None else type(value).__name__}.")
    if len(value) > limit:
        raise Refused(f"{name} is {len(value):,} characters; the most is "
                      f"{limit:,}.")
    if required and not value.strip():
        raise Refused(f"{name} cannot be empty.")
    return value


def ended(game) -> str:
    """Why nothing more can be done in this chronicle, or "" if it goes on.

    A chronicle that has ended in death or in one of the endings is over in
    the window — the endings screen is all that is left — and it was not over
    on the pipe: the verbs went on buying, surveying and remembering in it.
    """
    if getattr(game, "dead", False):
        return "The chronicle has ended: the ship is lost."
    if getattr(game, "victory", None):
        return "The chronicle has ended. Nothing more is done in it."
    return ""
