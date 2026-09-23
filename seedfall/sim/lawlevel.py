"""What a world's law digit actually stops you carrying.

The Traveller profile has given every world a law level since `data/uwp.py`
was written, and `LAW_LEVELS` even reads as a list of what it forbids — and
nothing in the game had ever asked it. Contraband was a *power's* business:
one list per faction (`data/contraband.REGIMES`), applied identically at
every quay that power holds.

Measured across six sectors, that is wrong in both directions:

    charter     mean law 7.0   76% at 6 or above   16% at 9 or above
    sanhedrin   mean law 8.1  100% at 6 or above   41% at 9 or above
    concordat   mean law 4.5   23%                  0%
    freeholds   mean law 1.7    2%                  0%

A Charter capital at law 9 and a Charter outpost at law 2 opened a hold with
exactly the same appetite. And **the strictest worlds in the sector never
looked in one at all** — the Sanhedrin's regime is empty, so the power whose
doctrine *is* the law was the one power you could carry anything past.

So a port asks two questions now, and the harder answer wins:

- **whose flag is it** — the power's regime, unchanged; and
- **what is the law here** — `LAW_LADDER`, a short list of what a world
  starts seizing as the digit climbs, and `LAW_ZEAL`, how hard it looks.

Everything downstream is the machinery that already existed. A good this
world seizes has no posted counter (`sim/trade.sell`), has an unposted buyer
who pays a premium for it (`customs.premium`), and gets the hold opened
(`customs.inspect`) — because that is what being forbidden *is* in this
game, and it was already written for the faction half.

Derived, never stored: the digit comes from `sim/profile`, which derives it
from the sector.
"""

from __future__ import annotations

from ..data.contraband import (LAW_LADDER, LAW_NOTICE, LAW_WAVED, LAW_WRIT,
                               LAW_ZEAL)
from ..data.uwp import LAW_LEVELS

#: Below this the world has no opinion worth the paperwork, whatever the
#: ladder says. Law 1 and 2 are "no poison gas, no explosives" — neither of
#: which is in a hold this game models — so the first rung is the first
#: thing a world here actually takes off you.
QUIET = LAW_LADDER[0][0]


def digit(game, system=None) -> int:
    """The law level at this system's port world, or 0 where there is none.

    A system with no port has nobody to enforce anything, which is not the
    same as a lawless world with a port on it — that one is law 0 *and* has
    a quay, and is exactly where a smuggler wants to be.
    """
    from . import profile as profile_sim
    system = system if system is not None else getattr(game, "system", None)
    if system is None or getattr(system, "port", None) is None:
        return 0
    world = profile_sim.port_world(system)
    if world is None:
        return 0
    return int(profile_sim.profile(game, system, world).law or 0)


def forbids(game, system=None) -> tuple:
    """Everything this world seizes on its own account, by the ladder."""
    law = digit(game, system)
    return tuple(cid for rung, cid in LAW_LADDER if law >= rung)


def zeal(game, system=None) -> float:
    """How hard this world looks, on the 0..1 a `Regime` uses."""
    law = digit(game, system)
    if law < QUIET:
        return 0.0
    return min(1.0, law * LAW_ZEAL)


def writ(game, system=None) -> str:
    """What the offence is called when it is the world's own law."""
    return LAW_WRIT


def voice(game, system=None) -> tuple:
    """`(notice, waved)` — what a boarding under local statute sounds like."""
    return LAW_NOTICE, LAW_WAVED


def says(game, system=None) -> str:
    """One line for a screen: what the law here is, and what it takes.

    Written to be shown on the Port screen beside the black market, because
    a rule the captain can only discover by being boarded is not a rule,
    it is a trap.
    """
    from ..data.commodities import BY_ID
    law = digit(game, system)
    name, blurb = LAW_LEVELS.get(law, LAW_LEVELS[0])
    taken = [BY_ID[cid].name for cid in forbids(game, system) if cid in BY_ID]
    if not taken:
        return (f"Law level {law} ({name.lower()}): nothing you are likely "
                "to be carrying is restricted here.")
    return (f"Law level {law} ({name.lower()}): {blurb}. They seize "
            + ", ".join(taken) + ".")
