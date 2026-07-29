"""A transfer as the burns it is actually made of.

`flight._leg` hands back one lump: so many days, so much reaction mass. That
is the right shape for the economy — every contract deadline, market tick and
fuel budget in the game is tuned against it — and the wrong shape for telling
a captain what their ship is about to do. The braking burn existed only in a
comment: *"it is the braking burn that leaves you hot."*

**What this deliberately does not do.** The first draft derived a cruise speed
from the quote — distance over time — and reported the burns needed to reach
it. The numbers came out at four and a half thousand kilometres a second, and
told every captain of every hull that their engines were hopelessly
inadequate. They were not wrong. A NAVIS crosses 6.5 AU in five days, which
*is* 0.75% of light speed, and no drive in the module list reaches that by
burning at 0.08 m/s².

That is not a fault in the ships. The game does not fly interplanetary legs on
Newton: it has a `jump` rating, a Foldrunner Coil, a relativistic burn profile,
and `clock.advance_days` carries a `dilation` argument precisely because a
hard crossing runs the crew's clock slower than the sector's. Imposing a
brachistochrone on that and then complaining the engines cannot do it would be
inventing a physics the game does not use, in order to fail it.

So the plan describes the crossing in the terms the game actually has, and
every figure in it is either taken from the quote or computed from the hull:

* **The mass splits in half.** Half of what `flight` charges goes into
  getting under way and half into stopping — which is why arriving is not
  free, and why the heat lands on arrival rather than departure.
* **The turns are real.** Swinging onto the heading, and the flip end-for-end
  before the braking burn, take the time this hull's attitude clusters
  actually need: under a minute for a SPORE, eight for a LEVIATHAN.
* **The coast is the rest**, and on any ordinary crossing it is nearly all of
  it. That is what a transfer mostly is.

`flight` remains the authority on days and reaction mass. This is that quote,
explained.
"""

from __future__ import annotations

import math

from . import flight, thrusters

#: Seconds in a day.
DAY_S = 86_400.0

#: The share of a transfer's reaction mass spent stopping rather than
#: starting. A half: the leg is symmetric, you have to lose exactly what you
#: gained, and this is the number the arrival heat has always implied.
BRAKING_SHARE = 0.5


def plan(game, body, burn_id: str = "standard") -> dict:
    """Break a quoted transfer into the burns that fly it."""
    return explain(game, flight.intercept(game, body, burn_id))


def explain(game, quote: dict) -> dict:
    """The phases of an already-quoted leg.

    Takes the quote rather than re-deriving it, so the plan and the burn
    board beside it cannot come apart.
    """
    ship = game.ship
    kit = thrusters.summary(ship)
    days = max(1, quote["days"])
    fuel = quote["fuel"]

    onto = thrusters.slew_seconds(ship, math.pi / 2)
    flip = thrusters.slew_seconds(ship, math.pi)
    manoeuvre = onto + flip
    coast = max(0.0, days * DAY_S - manoeuvre)

    phases = [
        ("Turn onto the heading", onto, 0.0,
         f"90° at {kit['slew_rate']:.4f} rad/s²"),
        ("Burn out", 0.0, fuel * (1.0 - BRAKING_SHARE),
         f"{kit['main_kn']:,.0f} kN from {kit['drives']} drive(s)"),
        ("Coast", coast, 0.0, "engines cold — most of a crossing is this"),
        ("Flip", flip, 0.0, "one hundred and eighty degrees, end for end"),
        ("Burn in", 0.0, fuel * BRAKING_SHARE,
         "the braking burn, and why you arrive hot"),
    ]
    return {
        "ok": kit["main_kn"] > 0,
        "why": ("" if kit["main_kn"] > 0 else
                "No drive fitted. This hull is not going anywhere."),
        "phases": phases, "quote": quote,
        "accel": kit["main_accel"], "slew_rate": kit["slew_rate"],
        "onto_s": onto, "flip_s": flip, "coast_s": coast,
        "manoeuvre_s": manoeuvre,
        "braking_fuel": fuel * BRAKING_SHARE,
        "share_turning": manoeuvre / max(1e-9, days * DAY_S),
    }


def note(game, body, burn_id: str = "standard") -> str:
    """One line for the helm: what the crossing is actually made of."""
    out = plan(game, body, burn_id)
    if not out["ok"]:
        return out["why"]
    return (f"{out['braking_fuel']:,.1f} t of the {out['quote']['fuel']:,.0f} "
            f"is the braking burn · {_span(out['flip_s'])} to flip her "
            f"end for end · {out['accel']:.3f} m/s² under way.")


def rows(game, body, burn_id: str = "standard") -> list[tuple[str, str, str]]:
    """The plan as a panel: phase, how long, and what it costs."""
    out = plan(game, body, burn_id)
    table = []
    for name, seconds, fuel, detail in out["phases"]:
        when = _span(seconds) if seconds > 0 else "—"
        table.append((name, when,
                      f"{detail} · {fuel:,.1f} t" if fuel else detail))
    return table


def _span(seconds: float) -> str:
    if seconds <= 0:
        return "—"
    if seconds < 90:
        return f"{seconds:,.0f} s"
    if seconds < 7200:
        return f"{seconds / 60:,.0f} min"
    if seconds < 3 * DAY_S:
        return f"{seconds / 3600:,.1f} h"
    return f"{seconds / DAY_S:,.1f} d"
