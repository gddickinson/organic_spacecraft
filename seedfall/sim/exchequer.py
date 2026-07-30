"""The public purse: what the powers earn, and what they do with it.

Before this, the four powers of the Verge were penniless in the literal sense.
They held ports, ran ventures, annexed systems and blockaded each other, and no
credit ever changed hands over any of it. A port's level was fixed at galaxy
generation and stayed there for the whole chronicle — so the map you flew in
year one was the map you flew in year twelve.

Now every power keeps a treasury:

- **Income** is its ports, in proportion to their level, more from a capital,
  less from a system somebody has put a shortage on.
- **Outlay** is the square of those same levels. Holding a Fleet Hub costs
  almost everything a Fleet Hub earns.
- **A surplus builds.** Once a month a power founds an outpost on ground it
  holds, or promotes one up `world.galaxy.PORT_KINDS` — outpost to station to
  hub — which is the same ladder that made every port in the sector.
- **A deficit gives something up.** The cheapest port to keep goes down a step,
  and an outpost that goes down a step closes altogether, taking its market with
  it. A capital never closes and a Free Port of the player's is never touched.
- **A venture costs its sponsor a stake**, and a power that cannot find the
  stake does not start one. A power with more money than plans gets restless
  instead.

The player is on this ledger too, for exactly one thing: a Free Port of their
own pays them a harbour due.

**One door.** `promote`, `found` and `demote` are the only functions that write
a port's level, name, id or services, and the screen's ledger is computed by
`income` and `outlay` — the same two functions `settle` spends from. A forecast
that reads a different function from the act is the bug this project has found
more times than any other.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.settlements import FOUND_COST as SETTLE_COST
from ..data.exchequer import (CAPITAL_BONUS, FOUND_COST, HARBOUR_DUE,
                              INDUSTRY_YIELD, OPENING_PURSE, RESERVE,
                              RICH_APPETITE, SETTLE_DAYS, SHORTAGE_YIELD,
                              STEP_COST, UPKEEP_COEFF, VENTURE_STAKE,
                              WAR_CHEST, YIELD_PER_LEVEL)
from ..data.factions import FACTIONS_BY_ID
from ..world.economy import make_market
from ..world.galaxy import PORT_KINDS
from . import diplomacy as dip
from . import market as market_sim


@register
@dataclass
class Purse:
    """One power's money, and what it last did with it."""
    power: str
    credits: float = 0.0
    #: What it last spent money on, or gave up. Shown on the diplomacy screen.
    last: str = ""
    #: The day the books were last done.
    settled: int = 0
    #: Ventures it has paid for, and works it has paid for. Kept because "how
    #: busy has this power been" is the question the ledger is for.
    ventures: int = 0
    works: int = 0
    #: Steps given up, which is the same question from the other end.
    losses: int = 0


@register
@dataclass
class Exchequer:
    purses: dict = field(default_factory=dict)


def ensure(game) -> Exchequer:
    """Created on first use, so an existing chronicle keeps working."""
    state = getattr(game, "exchequer", None)
    if state is None:
        state = game.exchequer = Exchequer()
    for power in dip.POWERS:
        if power not in state.purses:
            state.purses[power] = Purse(power=power,
                                        credits=float(OPENING_PURSE),
                                        settled=game.day)
    return state


def purse(game, power: str) -> Purse:
    return ensure(game).purses[power]


# ── what a power holds ─────────────────────────────────────────────────────

def holdings(game, power: str) -> list:
    """The systems whose port answers to this power.

    Read off `port.faction` rather than `system.faction`: an annexed system
    changes hands while whoever built the berth still owns the berth, and an
    independent freehold sits in a system the Freeholds are counted as holding
    without paying a credit into their purse.
    """
    return [s for s in game.galaxy.systems
            if s.port and s.port.faction == power and not s.port.independent
            and not s.port.player_built]


def scarce(game, system) -> bool:
    """Is somebody's shortage running here?"""
    return any(s.definition.supply < 1.0
               for s in market_sim.at(game, system.id))


def industries(game, power: str) -> int:
    """How many of the captain's processes this power has been licensed."""
    from . import industry
    return sum(1 for powers in industry.state(game).held.values()
               if power in powers)


def yield_of(game, system) -> float:
    """What one port pays its holder each day."""
    port = system.port
    if port is None:
        return 0.0
    out = port.level * YIELD_PER_LEVEL
    if port.capital:
        out *= 1.0 + CAPITAL_BONUS
    # What they have been taught to make. A power that buys a process off the
    # captain is buying this line — see `sim/industry.py`.
    out *= 1.0 + INDUSTRY_YIELD * industries(game, port.faction)
    if scarce(game, system):
        out *= SHORTAGE_YIELD
    return out


def upkeep_of(port) -> float:
    """What holding it costs each day. The square of the level, on purpose."""
    return UPKEEP_COEFF * port.level ** 2


def income(game, power: str) -> float:
    from . import settlement as settlement_sim
    return (sum(yield_of(game, s) for s in holdings(game, power))
            + settlement_sim.income(game, power))


def outlay(game, power: str) -> float:
    return sum(upkeep_of(s.port) for s in holdings(game, power))


def margin(game, power: str) -> float:
    return income(game, power) - outlay(game, power)


# ── the one door onto a port's level ───────────────────────────────────────

def _kind(level: int):
    return next(k for k in PORT_KINDS if k[2] == level)


def promote(game, system) -> str | None:
    """One step up the ladder. Returns what happened, or None if it cannot."""
    port = system.port
    if port is None or port.level >= PORT_KINDS[-1][2]:
        return None
    kind = _kind(port.level + 1)
    was = port.name
    port.id, port.name, port.level, port.services = kind[0], kind[1], kind[2], kind[3]
    return f"{was} at {system.name} is now a {port.name}"


def found(game, system, power: str) -> str | None:
    """A new outpost, and a new market with it, on ground a power holds."""
    if system.port is not None:
        return None
    kind = PORT_KINDS[0]
    from ..world.galaxy import Port
    system.port = Port(kind[0], kind[1], kind[2], kind[3], power)
    system.market = make_market(game.rng(f"found-{system.id}"), system)
    # Whatever this power has been taught to make, it makes here too. Without
    # this, a berth built after a licence was sold would be the one port of
    # theirs that never got the industry — and nothing would ever say why.
    from . import industry
    industry.industrialise(game, system)
    return f"a new {kind[1]} is open at {system.name}"


def plant(game, system, body_id: str, power: str) -> str | None:
    """Put people on a body. The one door onto founding a settlement here.

    **Not `settle`** — that name was taken, by the function that does the books.
    The first draft used it and Python quietly kept whichever came last in the
    file, so the monthly settlement ran with a body id where its day count
    should have been.
    """
    from . import settlement as settlement_sim
    body = next((b for b in system.bodies if b.id == body_id), None)
    if body is None:
        return None
    made = settlement_sim.found(game, system, body, power)
    if made is None:
        return None
    return (f"people are on the ground at {body.name}, working "
            f"{made.good}")


def demote(game, system) -> str | None:
    """One step down, and off the map altogether from the bottom step."""
    port = system.port
    if port is None:
        return None
    if port.level <= PORT_KINDS[0][2]:
        if port.capital:
            return None                     # a seat of power does not close
        if system.id == game.location_id:
            return None                     # not with your hull alongside
        system.port = None
        system.market = None
        return f"the berth at {system.name} is abandoned"
    kind = _kind(port.level - 1)
    was = port.name
    port.id, port.name, port.level, port.services = kind[0], kind[1], kind[2], kind[3]
    return f"{was} at {system.name} is cut back to a {port.name}"


# ── what a power does with the money ───────────────────────────────────────

def payback(game, power: str, cost: int, what: str) -> float:
    """Days for one work to pay for itself, or `inf` if it never does.

    **The exchequer chose by price, and price is not value.** `_invest` took the
    cheapest work it could afford, and the equilibrium the upkeep curve is built
    on means the cheap works are the ones that never pay: promoting an outpost to
    a station adds 90 a day of yield and 90 a day of upkeep — *net nothing* — and
    promoting a station to a hub is 60 a day worse than not bothering. Founding a
    berth clears 60 a day for 40,000, and settling ground clears 32 for 32,000.
    So the rule "take the cheapest" bought the two works with no return before
    either of the two with one, and a sector's powers planted **six settlements
    in year one and none in the seven years after**.

    Sorting by payback fixes it without inventing a preference: a power does the
    thing that pays for itself soonest, and the works that never pay are what it
    does with money it has nothing better to do with — which is exactly what a
    Fleet Hub is.
    """
    if what.startswith("settle:"):
        # Asked of the settlement module, which counts the years a new one
        # *loses* money — see `settlement.payback_days`. Dividing the cost by the
        # mature rate reads 1,000 days where the truth is 1,485.
        from . import settlement as settlement_sim
        return settlement_sim.payback_days()
    if False:
        gain = 0.0
    elif what == "found":
        gain = YIELD_PER_LEVEL * PORT_KINDS[0][2] - upkeep_at(PORT_KINDS[0][2])
    else:
        level = int(what.split(":", 1)[1]) if ":" in what else 0
        gain = ((YIELD_PER_LEVEL * level - upkeep_at(level))
                - (YIELD_PER_LEVEL * (level - 1) - upkeep_at(level - 1)))
    if gain <= 0:
        return float("inf")
    return cost / gain


def upkeep_at(level: int) -> float:
    """What a berth of this level costs a day. The curve, without a port."""
    return UPKEEP_COEFF * max(0, level) ** 2


def works_open(game, power: str) -> list[tuple[int, object, str]]:
    """Everything this power could spend on, soonest-paying first.

    Each entry is `(cost, system, what)`, where `what` is `"promote:<level>"`,
    `"found"`, or `"settle:<body id>"`. The list is the whole of the power's
    ambition: build up a berth it holds, found one on ground it holds and has
    never built on, or put people on a body worth working.
    """
    out: list[tuple[int, object, str]] = []
    for system in holdings(game, power):
        want = system.port.level + 1
        if want in STEP_COST:
            out.append((STEP_COST[want], system, f"promote:{want}"))
    for system in game.galaxy.systems:
        if system.faction == power and system.port is None:
            out.append((FOUND_COST, system, "found"))
    # And people on the ground. A berth is a place to tie up; a settlement is a
    # place things come from, which is the half of an economy the sector did not
    # have — 161 bodies and not one of them worked. See `sim/settlement.py`.
    from . import settlement as settlement_sim
    for system, body, _good in settlement_sim.sites_for(game, power)[:3]:
        out.append((SETTLE_COST, system, f"settle:{body.id}"))
    out.sort(key=lambda row: (payback(game, power, row[0], row[2]),
                              row[0], row[1].id))
    return out


def _invest(game, power: str, p: Purse) -> str | None:
    """Spend, if there is anything worth spending on and enough to spare."""
    for cost, system, what in works_open(game, power):
        if p.credits - cost < RESERVE:
            continue
        if what.startswith("settle:"):
            told = plant(game, system, what.split(":", 1)[1], power)
        elif what.startswith("promote"):
            told = promote(game, system)
        else:
            told = found(game, system, power)
        if told is None:
            continue
        p.credits -= cost
        p.works += 1
        return told
    return None


def _retrench(game, power: str, p: Purse) -> str | None:
    """Give up the cheapest thing to keep. Nothing else recovers the upkeep."""
    held = holdings(game, power)
    if not held:
        return None
    # The lowest level first, and among equals the one that yields least: a
    # power in trouble gives up the berth it gets least from, not its seat.
    held.sort(key=lambda s: (s.port.capital, s.port.level,
                             yield_of(game, s), s.id))
    for system in held:
        told = demote(game, system)
        if told is not None:
            p.losses += 1
            return told
    return None


def appetite(game, power: str) -> float:
    """How willing this power is to start a venture, as a multiplier.

    Zero when it cannot pay the stake — which is the whole reason for a purse.
    """
    p = purse(game, power)
    if p.credits < VENTURE_STAKE:
        return 0.0
    return RICH_APPETITE if p.credits >= WAR_CHEST else 1.0


def stake(game, power: str) -> bool:
    """Take the stake for a venture. False if the power cannot find it."""
    p = purse(game, power)
    if p.credits < VENTURE_STAKE:
        return False
    p.credits -= VENTURE_STAKE
    p.ventures += 1
    return True


def due(game, days: float) -> float:
    """What the player's own Free Ports pay them over this many days."""
    mine = [s for s in game.galaxy.systems
            if s.port and s.port.player_built]
    return sum(s.port.level for s in mine) * HARBOUR_DUE * days


def settle(game, days: float) -> list[tuple[str, str]]:
    """Accrue the day's money, and once a month decide what to do with it.

    **No rng, unlike every other tick in `core/clock.py`.** A power's decisions
    are fully determined by what it holds and what it has: the cheapest work it
    can afford, or the least valuable berth it can give up. There is nothing to
    roll, and a parameter nobody reads is a dead field wearing a different hat.
    """
    state = ensure(game)
    events: list[tuple[str, str]] = []
    if days <= 0:
        return events

    paid = due(game, days)
    if paid > 0:
        game.credits += paid

    for power in dip.POWERS:
        p = state.purses[power]
        took, owed = income(game, power) * days, outlay(game, power) * days
        p.credits += took - owed
        if game.day - p.settled < SETTLE_DAYS:
            continue
        p.settled = game.day
        told = (_retrench(game, power, p) if p.credits < 0
                else _invest(game, power, p))
        if told:
            p.last = told
            short = FACTIONS_BY_ID[power].short
            events.append(("warn" if p.credits < 0 else "",
                           f"{short}: {told}."))
    return events


# ── what the screens read ──────────────────────────────────────────────────

def settlement_of(game, power: str) -> list:
    from . import settlement as settlement_sim
    return settlement_sim.of_power(game, power)


def settlement_income(game, power: str) -> float:
    from . import settlement as settlement_sim
    return settlement_sim.income(game, power)


def ledger(game) -> list[dict]:
    """One row per power, from the same functions `settle` spends from."""
    out = []
    for power in dip.POWERS:
        p = purse(game, power)
        held = holdings(game, power)
        out.append({
            # Off the purse itself rather than the loop variable: a row that
            # says whose money it is should be asking the money.
            "power": p.power,
            "name": FACTIONS_BY_ID[p.power].short,
            "tint": FACTIONS_BY_ID[p.power].tint,
            "credits": p.credits,
            "took": income(game, power),
            "paid": outlay(game, power),
            "margin": margin(game, power),
            "ports": len(held),
            "levels": sum(s.port.level for s in held),
            "pinched": sum(1 for s in held if scarce(game, s)),
            "settlements": len(settlement_of(game, p.power)),
            "ground": settlement_income(game, p.power),
            "last": p.last,
            "works": p.works,
            "losses": p.losses,
            "ventures": p.ventures,
            "next": _next_work(game, power, p),
        })
    out.sort(key=lambda row: -row["credits"])
    return out


def _next_work(game, power: str, p: Purse) -> str:
    """What this power is saving up for, in words."""
    if p.credits < 0:
        return "in deficit — something will have to go"
    open_now = works_open(game, power)
    if not open_now:
        return "nothing left to build"
    cost, system, what = open_now[0]
    short = ("found a berth at" if what == "found"
             else "settle" if what.startswith("settle:") else "build up")
    want = cost + RESERVE - p.credits
    if want <= 0:
        return f"about to {short} {system.name}"
    rate = margin(game, power)
    when = f", {round(want / rate)} days at this rate" if rate > 0 else ""
    return f"{short} {system.name} — {round(want):,} short{when}"


def summary(game) -> dict:
    """The sector's infrastructure, in one line, for a check or a screen."""
    ports = [s for s in game.galaxy.systems if s.port]
    return {
        "ports": len(ports),
        "levels": sum(s.port.level for s in ports),
        "built": sum(purse(game, p).works for p in dip.POWERS),
        "lost": sum(purse(game, p).losses for p in dip.POWERS),
        "purse": sum(purse(game, p).credits for p in dip.POWERS),
    }
