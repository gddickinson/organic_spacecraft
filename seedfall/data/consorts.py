"""Standing orders for the hulls sailing with you.

A consort is not a second ship you pilot — you have one pair of hands and they
are on your own helm. What you give a consort is an intention, and its captain
interprets it. The three orders are genuinely different bargains: a screen
spends the escort to keep you whole, a flank spends patience to get behind
something, and a concentration spends everyone's safety to end a fight quickly.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConsortOrder:
    id: str
    name: str
    blurb: str
    #: How much of the enemy's attention this consort draws, relative to you.
    draw: float
    #: Multiplier on the damage its guns do.
    bite: float
    #: How hard it tries to hold station between you and the enemy.
    shield: float


ORDERS: list[ConsortOrder] = [
    ConsortOrder(
        "screen", "Screen me",
        "Hold between the enemy and your flag and be seen doing it. Draws fire "
        "that would otherwise land on you, and takes it on a smaller hull.",
        draw=2.4, bite=0.75, shield=1.0),
    ConsortOrder(
        "flank", "Work around the flank",
        "Stay wide and get behind them, where the fixed mounts do not reach. "
        "Slow to pay off, and hard to hit while it does.",
        draw=0.5, bite=1.25, shield=0.0),
    ConsortOrder(
        "concentrate", "Concentrate fire",
        "Close alongside your flag and put everything into the same target. "
        "The fastest way to end it, and nobody is screening anybody.",
        draw=1.0, bite=1.5, shield=0.25),
]

ORDERS_BY_ID = {o.id: o for o in ORDERS}
DEFAULT_ORDER = "screen"

#: A consort that falls below this fraction of its hull breaks off.
WITHDRAW_AT = 0.22
