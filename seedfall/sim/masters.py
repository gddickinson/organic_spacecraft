"""Masters: the people who sail a trading house's haulers without you.

Kept apart from `sim/crew.py` on purpose. An officer stands a station on your
bridge, is read by `ship.stats`, and has convictions about how *you* run the
ship. A master never sees you: they are paid by the house, judged by what
their line clears, and loyal to whoever pays on time and does not lose their
hull for them. Nothing about the one reaches the other.

A master brings two things to a line, both from one number, `skill`:

- **A margin.** A poor master pays over the counter's price and takes under
  it — lighterage, bad timing, a drink with the wrong clerk. `slip` is that
  share. A master never does *better* than the counter: the counter's quote is
  the ceiling, so no master can make a line pay that the market would not.
- **Judgement.** Which lane to take through a bad system, when to sit tight.
  `judgement` scales down a route's risk.

Loyalty is moved by pay and by losses. Paid late, a master sours fast; a
master who loses a hull sours faster; below `QUIT_AT` they walk, and their
line stands down where the hauler lies.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core import ids
from ..core.rng import RNG
from ..core.save import register
from ..core.util import clamp
from ..data.lore import CREW_FIRST, CREW_LAST
from . import lineledger as ledger

#: What a master costs a month: a floor, and what skill adds on top.
WAGE_FLOOR = 180
WAGE_PER_SKILL = 520

#: The share of a counter's price the least able master fails to get, on each
#: side of a trade. Scaled down by skill — the best master in the Verge loses
#: a tenth of it.
MAX_SLIP = 0.04

#: How much of a route's risk the best judgement avoids.
JUDGEMENT = 0.4

#: Loyalty: where it starts, what moves it, and where a master walks.
START = 0.6
PAID = 0.02
UNPAID = 0.2
GOOD_TRIP = 0.01
ROBBED = 0.06
SEIZED = 0.04
LOST_HULL = 0.3
QUIT_AT = 0.25


@register
@dataclass
class Master:
    id: int
    name: str
    skill: float
    wage: int
    loyalty: float = START
    #: Wages earned and not yet paid.
    owed: float = 0.0
    line_id: int | None = None
    hired: int = 0
    #: Where they signed on.
    home: int = 0
    trips: int = 0
    losses: int = 0

    @property
    def rating(self) -> str:
        """Skill as a captain would say it."""
        return ("green" if self.skill < 0.25 else "steady" if self.skill < 0.45
                else "able" if self.skill < 0.65 else "first-rate")


def slip(master) -> float:
    """The share of a counter's price this master loses, each way."""
    skill = master.skill if master is not None else 0.0
    return MAX_SLIP * (1.0 - 0.9 * clamp(skill, 0.0, 1.0))


def judgement(master) -> float:
    """What this master leaves of a route's risk, 0..1."""
    skill = master.skill if master is not None else 0.0
    return 1.0 - JUDGEMENT * clamp(skill, 0.0, 1.0)


def pool_at(game, system) -> list:
    """Who is looking for a hull to master at this quay this month.

    **Seeded from its own key**, like the officers' board (`crew.pool_at`):
    who is on offer is a fact about the quay and the month, not about when you
    first looked, and looking draws no luck from the chronicle. Candidates
    carry id 0 until they sign — an id drawn for somebody you never hired is
    an id the book spends for nothing.
    """
    port = getattr(system, "port", None)
    if port is None or "recruit" not in port.services:
        return []
    rng = RNG(f"{game.seed}:masters:{system.id}:{game.day // 30}")
    signed = {(m.name, m.home) for m in _house_masters(game)}
    out = []
    for _ in range(port.level + 1):
        skill = clamp(rng.gauss(0.30 + 0.12 * (port.level - 2), 0.15),
                      0.05, 0.95)
        name = f"{rng.pick(CREW_FIRST)} {rng.pick(CREW_LAST)}"
        master = Master(id=0, name=name, skill=round(skill, 2),
                        wage=round(WAGE_FLOOR + WAGE_PER_SKILL * skill),
                        loyalty=round(clamp(START + rng.gauss(0, 0.08),
                                            0.4, 0.8), 2),
                        home=system.id)
        if (master.name, master.home) not in signed:
            out.append(master)
    return out


def _house_masters(game) -> list:
    house = getattr(game, "house", None)
    return list(house.masters) if house is not None else []


def can_hire(game, master) -> tuple[bool, str]:
    """Whether this master can be signed, and what stops it."""
    house = getattr(game, "house", None)
    if house is None:
        return False, "Charter a house first — a master signs with a house."
    here = game.system
    if master.home != here.id:
        return False, f"{master.name} is looking for a berth elsewhere."
    if not any(m.name == master.name and m.home == master.home
               for m in pool_at(game, here)):
        return False, f"{master.name} is no longer on the board."
    if house.account < master.wage:
        return False, (f"The signing fee is a month's wage, "
                       f"{master.wage:,}, and the house account holds "
                       f"{round(house.account):,}.")
    return True, ""


def hire(game, master) -> dict:
    """Sign a master on. The signing fee is a month's wage, from the house."""
    ok, why = can_hire(game, master)
    if not ok:
        return {"ok": False, "why": why}
    house = game.house
    master.id = ids.next_id("master", game)
    master.hired = game.day
    ledger.post(game, house, 0, "hire", -master.wage)
    house.masters.append(master)
    game.add_log(f"{master.name} signed on as a master with the house — "
                 f"{master.rating}, {master.wage:,} a month.", "good")
    return {"ok": True, "master": master, "fee": master.wage}


def dismiss_terms(game, master) -> dict:
    """What letting a master go costs: what they are owed, and a month."""
    house = getattr(game, "house", None)
    if house is None or master not in house.masters:
        return {"ok": False, "why": "Not a master of this house."}
    if master.line_id is not None:
        return {"ok": False, "why": (f"{master.name} is working a line. "
                                     "Stand the line down first.")}
    cost = round(master.owed + master.wage)
    if house.account < cost:
        return {"ok": False, "why": (f"Letting {master.name} go costs "
                                     f"{cost:,} and the account holds "
                                     f"{round(house.account):,}.")}
    return {"ok": True, "cost": cost}


def dismiss(game, master) -> dict:
    """Pay a master off. They take what they are owed and a month besides."""
    terms = dismiss_terms(game, master)
    if not terms["ok"]:
        return terms
    house = game.house
    ledger.post(game, house, 0, "severance", -terms["cost"])
    house.masters = [m for m in house.masters if m is not master]
    game.add_log(f"{master.name} was paid off and left the house.", "")
    return {"ok": True, "cost": terms["cost"]}


def pay_owed(game, master) -> dict:
    """Clear a master's back pay from the house account."""
    house = getattr(game, "house", None)
    if house is None or master not in house.masters:
        return {"ok": False, "why": "Not a master of this house."}
    if master.owed < 1:
        return {"ok": False, "why": f"{master.name} is owed nothing."}
    if house.account < master.owed:
        return {"ok": False, "why": (f"{master.name} is owed "
                                     f"{round(master.owed):,}; the account "
                                     f"holds {round(house.account):,}.")}
    paid = master.owed
    ledger.post(game, house, master.line_id or 0, "wages", -paid)
    master.owed = 0.0
    shift(master, PAID)
    game.add_log(f"{master.name}'s back pay is settled — {round(paid):,}.", "")
    return {"ok": True, "paid": paid}


def shift(master, delta: float) -> None:
    master.loyalty = clamp(master.loyalty + delta, 0.0, 1.0)


def payroll(game, house) -> list:
    """The month's wages. Paid on time is noticed a little; unpaid, a lot.

    Returns the masters who walked, having already stood their lines down
    through the caller's `on_quit`.
    """
    walked = []
    for master in list(house.masters):
        if house.account >= master.wage:
            ledger.post(game, house, master.line_id or 0, "wages",
                        -master.wage)
            shift(master, PAID)
        else:
            master.owed += master.wage
            shift(master, -UNPAID)
            game.add_log(f"{master.name} was not paid this month. The house "
                         f"owes {round(master.owed):,}.", "warn")
        if master.loyalty < QUIT_AT:
            walked.append(master)
    return walked


def after_trip(master, fate: str) -> None:
    """What a trip's outcome does to the master who sailed it."""
    master.trips += 1
    if fate in ("done", "delayed"):
        shift(master, GOOD_TRIP)
    elif fate == "robbed":
        shift(master, -ROBBED)
    elif fate == "seized":
        shift(master, -SEIZED)
    elif fate == "lost":
        master.losses += 1
        shift(master, -LOST_HULL)


def walks(master) -> bool:
    """Has this master had enough?"""
    return master.loyalty < QUIT_AT


def leave(game, house, master) -> None:
    """A master walks. Whatever they are owed they are owed still — the
    house's debt to them does not vanish with them, it is simply written off
    against the house's good name, which is the loyalty of the next one."""
    house.masters = [m for m in house.masters if m is not master]
    game.add_log(f"<b>{master.name} has quit the house.</b> "
                 + (f"{round(master.owed):,} in wages went unpaid. "
                    if master.owed >= 1 else "")
                 + "Their line stands down where the hauler lies.", "bad")
