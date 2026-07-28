"""Does this feature actually move anything?

`test_reachable.py` proves a function is called. It cannot prove the call
matters: the Bloom's growth multiplier was consumed by `summary()` from the day
it was written while contributing nothing whatever to the simulation, and a
reachability check passes on that happily.

This is the stronger claim. Each lever below names a thing the game says it
does, a way to neutralise it, and a measurement of the world. Neutralise the
lever, run the same seeded scenario, and the measurement has to move. If it
does not, the feature is decoration however thoroughly it is wired.

Neutralising works by replacing a module attribute, because the codebase calls
across modules as `module.function(...)` — the lookup happens at call time, so
the substitution is seen by every caller. A lever that patched something
imported by name would silently do nothing, which is exactly the failure this
file exists to catch, so `test_efficacy.py` checks each lever actually changes
the number before trusting the comparison.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Lever:
    """One claimed effect, and how to find out whether it is real."""
    id: str
    what: str
    #: (module, attribute, replacement) — the neutral version of the effect.
    patch: tuple
    #: Runs a scenario and returns a number to compare.
    probe: Callable
    #: What happens to the measurement when the feature is switched OFF.
    #: "lower" and "higher" are the strong claims; "differs" only asks that
    #: something moved. Naming it after the neutralised run rather than the
    #: live one avoids the sign confusion that got every lever backwards on
    #: the first attempt.
    direction: str = "differs"
    #: How much of a change counts, as a fraction of the live measurement.
    margin: float = 0.02


@contextmanager
def neutralised(lever: Lever):
    module, attribute, replacement = lever.patch
    original = getattr(module, attribute)
    setattr(module, attribute, replacement)
    try:
        yield
    finally:
        setattr(module, attribute, original)


def measure(lever: Lever) -> tuple[float, float]:
    """(with the feature, without it)."""
    live = float(lever.probe())
    with neutralised(lever):
        dead = float(lever.probe())
    return live, dead


def verdict(lever: Lever) -> tuple[bool, str]:
    """Whether this feature demonstrably moves the world."""
    live, dead = measure(lever)
    scale = max(abs(live), 1e-9)
    shift = (dead - live) / scale          # how the world moves without it
    if lever.direction == "lower":
        ok = shift <= -lever.margin
    elif lever.direction == "higher":
        ok = shift >= lever.margin
    else:
        ok = abs(shift) >= lever.margin
    return ok, (f"{lever.id}: {live:.4g} with the feature, {dead:.4g} without "
                f"({shift:+.1%}); switching it off should read "
                f"{lever.direction}")
