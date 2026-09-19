"""A trading house, and the freight lines it runs while you are elsewhere.

Every tonne the captain traded used to move in the captain's own hold, with
the captain sitting in it, so trade could not scale: the honest all-in freight
trader of the play-test was broke by year three on four seeds of five. A house
is how it scales. You charter one at a Station or a Fleet Hub, put haulers of
your own on **lines** — two ports, a good, a rule for buying and one for
selling, a cadence — and hire a master for each. The lines trade through the
real counters on the sector's clock, so they pay the quay, move the price, and
saturate a route that is worked too hard.

**Nothing here makes money.** A credit reaches the house account only from a
counter sale `apply_sale` saw, from the captain's own purse, or from an
underwriter's purse on a claim the house paid a loaded premium for; it
reaches the purse only by a sweep or a withdrawal. `lineledger` is the one
door, and `lineledger.reconcile` is the proof.

This module is the front door: the charter, the account, opening and standing
down a line, and the day. A trip is `sim/linetrips.py`, the route and its risk
`sim/lineroute.py`, the forecast `sim/lineforecast.py`, and the people who
sail them `sim/masters.py`, and the hulls that do `sim/haulers.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core import ids
from ..core.save import register
from ..data.commodities import BY_ID
from ..data.freightlines import (CADENCES, CHARTER_FEE, CHARTER_UPKEEP,
                                 HAND_A_DAY, RESERVE, SETTLE_DAYS)
from . import customs as customs_sim
from . import diplomacy as dip_sim
from . import enforce as enforce_sim
from . import exchequer as exchequer_sim
from . import haulers as haulers_sim
from . import lineledger as ledger
from . import lineroute
from . import market as market_sim
from . import linetrips
from . import masters as masters_sim
from . import renown as renown_sim


@register
@dataclass
class FreightLine:
    id: int
    hauler: int
    master: int
    origin: int
    dest: int
    good: str
    tonnes: int
    #: The buying rule's ceiling and the selling rule's floor. None is "at
    #: any price" and "whatever it fetches".
    max_buy: int | None = None
    min_sell: int | None = None
    #: Days from one sailing to the next; 0 is continuous.
    cadence: int = 0
    active: bool = True
    #: Asked to stand down, which it does at its next port.
    stopping: bool = False
    phase: str = "ferry"
    due: int = 0
    #: The day it came alongside where it is waiting.
    since: int = 0
    opened: int = 0
    trips: int = 0
    started: int = 0
    next_start: int = 0
    #: The trip under way: what it will meet, and what its cargo cost.
    fate: str = ""
    delay: int = 0
    damage: float = 0.0
    paid: float = 0.0
    #: Everything the last departure laid out — cargo, mass, dues, premium —
    #: which a sweep leaves in the account for the next one.
    stake: float = 0.0
    insured: bool = False
    trip_net: float = 0.0
    #: The last trip, for the lines table.
    last: str = ""
    last_net: float | None = None
    last_day: int = 0
    #: Why she is sitting still, in words, or "".
    waiting: str = ""
    #: Her hands' pay, accrued daily and settled with the month.
    hands_due: float = 0.0


@register
@dataclass
class TradingHouse:
    #: The system whose port issued the charter, and the power behind it —
    #: who takes the upkeep, and who underwrites the house's hulls.
    chartered_at: int
    power: str
    founded: int = 0
    fee: int = 0
    account: float = 0.0
    reserve: float = RESERVE
    sweep: bool = True
    insured: bool = False
    next_settle: int = 0
    owed_charter: float = 0.0
    owed_hands: float = 0.0
    lines: list = field(default_factory=list)
    masters: list = field(default_factory=list)
    #: `[day, line id, kind, amount]` rows, and lifetime totals by line —
    #: written only by `sim/lineledger.py`.
    ledger: list = field(default_factory=list)
    totals: dict = field(default_factory=dict)
    #: What has crossed between the house and the captain's purse, each way.
    purse_in: float = 0.0
    purse_out: float = 0.0
    #: Standing earned by the house's trade, per power: [period start, gained].
    regard: dict = field(default_factory=dict)
    #: The best trip the house has ever cleared.
    record: float = 0.0


# ── the charter ─────────────────────────────────────────────────────────────

def charter_terms(game) -> dict:
    """What a charter here would cost, or why there is none to be had."""
    if getattr(game, "house", None) is not None:
        return {"ok": False, "why": "You already hold a charter."}
    here = game.system
    port = getattr(here, "port", None)
    if port is None or port.level < 2:
        return {"ok": False, "why": ("A house is chartered at a Station or a "
                                     "Fleet Hub, and there is none here.")}
    if port.independent or port.player_built or port.faction not in dip_sim.POWERS:
        return {"ok": False, "why": "Nobody here issues charters."}
    dealing, why = enforce_sim.may_trade(game, here)
    if not dealing:
        return {"ok": False, "why": why}
    fee = CHARTER_FEE[min(3, port.level)]
    if renown_sim.perk(game, "charter"):
        fee = 0                   # waived for a Captain (`sim/renown`)
    out = {"ok": True, "why": "", "fee": fee, "upkeep": CHARTER_UPKEEP,
           "power": port.faction, "port": f"{here.name} {port.name}",
           "system": here.id}
    if game.credits < fee:
        out.update(ok=False, why=(f"The charter is {fee:,} and the purse "
                                  f"holds {round(game.credits):,}."))
    return out


def charter(game) -> dict:
    """Register a house. The fee goes to the power that issued it."""
    terms = charter_terms(game)
    if not terms["ok"]:
        return terms
    game.credits -= terms["fee"]
    exchequer_sim.purse(game, terms["power"]).credits += terms["fee"]
    # The counting-house is the house's first factor: its own port's prices
    # are on the register from the day it opens.
    market_sim.note_prices(game, game.system)
    game.house = TradingHouse(chartered_at=terms["system"],
                              power=terms["power"], founded=game.day,
                              fee=terms["fee"],
                              next_settle=game.day + SETTLE_DAYS)
    game.add_log(f"A trading house is chartered at {terms['port']} — "
                 f"{terms['fee']:,} paid, {terms['upkeep']:,} a month to "
                 "keep.", "good")
    return {"ok": True, "house": game.house, **terms}


def deposit(game, amount: float) -> dict:
    """Pay money into the house; back pay and arrears come off it first."""
    house = getattr(game, "house", None)
    if house is None:
        return {"ok": False, "why": "There is no house."}
    moved = ledger.from_purse(game, house, amount)
    if moved <= 0:
        return {"ok": False, "why": "Nothing to pay in."}
    _clear_arrears(game, house)
    game.add_log(f"{round(moved):,} paid into the house account.", "")
    return {"ok": True, "moved": moved}


def withdraw(game, amount: float) -> dict:
    """Take money out of the house into the purse."""
    house = getattr(game, "house", None)
    if house is None:
        return {"ok": False, "why": "There is no house."}
    moved = ledger.to_purse(game, house, amount, "withdraw")
    if moved <= 0:
        return {"ok": False, "why": "The account is empty."}
    game.add_log(f"{round(moved):,} drawn from the house account.", "")
    return {"ok": True, "moved": moved}


def set_terms(game, reserve: float | None = None, sweep: bool | None = None,
              insured: bool | None = None) -> dict:
    """How the house keeps its money: what a sweep leaves, whether it
    sweeps, and whether its hulls and cargoes are insured."""
    house = getattr(game, "house", None)
    if house is None:
        return {"ok": False, "why": "There is no house."}
    if reserve is not None:
        house.reserve = max(0.0, float(reserve))
    if sweep is not None:
        house.sweep = bool(sweep)
    if insured is not None:
        house.insured = bool(insured)
    return {"ok": True, "reserve": house.reserve, "sweep": house.sweep,
            "insured": house.insured}


# ── lines ───────────────────────────────────────────────────────────────────

def draft(game, hauler: int, master: int, origin: int, dest: int, good: str,
          tonnes: int, max_buy=None, min_sell=None, cadence: int = 0):
    """A line on paper: what `open_terms` prices and `open_line` opens."""
    return FreightLine(id=0, hauler=hauler, master=master, origin=origin,
                       dest=dest, good=good, tonnes=int(tonnes),
                       max_buy=int(max_buy) if max_buy else None,
                       min_sell=int(min_sell) if min_sell else None,
                       cadence=int(cadence or 0), opened=game.day)


def open_terms(game, line) -> dict:
    """Whether a line on paper can run, and the forecast it runs to."""
    from . import lineforecast
    house = getattr(game, "house", None)
    if house is None:
        return {"ok": False, "why": "Charter a house first."}
    systems = game.galaxy.systems
    hull = lineroute.hull_of(game, line)
    master = lineroute.master_of(game, line)
    ok, why = (haulers_sim.can_haul(game, hull) if hull is not None
               else (False, "No hull."))
    if not ok:
        return {"ok": False, "why": why}
    if master is None or master.line_id is not None:
        return {"ok": False, "why": "Choose a master who is not on a line."}
    if line.origin == line.dest:
        return {"ok": False, "why": "A line runs between two ports."}
    origin, dest = systems[line.origin], systems[line.dest]
    for end in (origin, dest):
        if end.market is None or end.port is None:
            return {"ok": False, "why": f"{end.name} has no market."}
        if str(end.id) not in game.register:
            return {"ok": False, "why": (f"The house has no factor at "
                                         f"{end.name} — go and see it first.")}
    good = BY_ID.get(line.good)
    if good is None or not good.legal or line.good not in origin.market.stock:
        return {"ok": False, "why": "A line carries lawful goods its home "
                                    "port stocks."}
    if customs_sim.outlaws(dest.port.faction, line.good):
        return {"ok": False, "why": f"{dest.name} will not take it."}
    if line.tonnes < 1 or line.cadence not in CADENCES:
        return {"ok": False, "why": "Set a tonnage and a cadence."}
    st = lineroute.hauler_stats(game, hull)
    ferry = lineroute.path(game, hull.docked_at, line.origin, st.jump)
    if ferry is None:
        return {"ok": False, "why": (f"{hull.name} cannot get from where she "
                                     f"lies to {origin.name}.")}
    told = lineforecast.forecast(game, line)
    if "first" not in told:
        return {"ok": False, "why": told["why"]}
    leg = lineroute.leg(ferry, st.speed) if len(ferry) > 1 else None
    ferry_fuel = ferry_price = 0
    if leg:
        berth = systems[hull.docked_at]
        ferry_fuel = leg["fuel"]
        ferry_price = (market_sim.quote_buy(game, berth, "volatiles")
                       if berth.market else None)
        if not ferry_price:
            return {"ok": False, "why": (f"{hull.name} lies where nobody "
                                         "sells her the reaction mass to "
                                         "reach her home port.")}
        if house.account < ferry_fuel * ferry_price * 1.2:
            return {"ok": False, "why": ("The house account cannot pay her "
                                         "passage to her home port.")}
    return {"ok": True, "why": "", "forecast": told,
            "ferry_days": leg["days"] if leg else 0,
            "ferry_fuel": ferry_fuel, "ferry_price": ferry_price or 0}


def open_line(game, line) -> dict:
    """Put a hauler and a master on a line. If she is already alongside at
    the home port she loads and sails today, at the prices just quoted."""
    terms = open_terms(game, line)
    if not terms["ok"]:
        return terms
    house = game.house
    hull = lineroute.hull_of(game, line)
    master = lineroute.master_of(game, line)
    line.id = ids.next_id("line", game)
    line.opened = game.day
    hull.line_id = line.id
    master.line_id = line.id
    house.lines.append(line)
    origin = game.galaxy.systems[line.origin]
    if terms["ferry_days"]:
        linetrips.buy(game, house, line, game.galaxy.systems[hull.docked_at],
                      "volatiles", terms["ferry_fuel"], terms["ferry_price"],
                      kind="fuel")
        line.phase, line.due = "ferry", game.day + terms["ferry_days"]
        hull.docked_at = None
    else:
        line.phase = "load"
    good = BY_ID[line.good]
    game.add_log(f"{hull.name} is on the {origin.name}–"
                 f"{game.galaxy.systems[line.dest].name} line, carrying "
                 f"{good.short}, with {master.name} as master.", "good")
    linetrips.advance(game, house, line)
    return {"ok": True, "line": line, **terms}


def stop(game, line) -> dict:
    """Stand a line down: at once if she is alongside at home, otherwise at
    her next port."""
    house = getattr(game, "house", None)
    if house is None or line not in house.lines or not line.active:
        return {"ok": False, "why": "That line is not running."}
    if line.phase == "load":
        stand_down(game, house, line)
        return {"ok": True, "now": True}
    line.stopping = True
    return {"ok": True, "now": False}


def stand_down(game, house, line, lost: bool = False) -> None:
    """The line stops; the hull and the master are free where they are."""
    laden = line.phase in ("out", "sell")
    line.active = False
    line.stopping = False
    line.phase = "idle"
    line.waiting = ""
    hull = lineroute.hull_of(game, line)
    if hull is not None:
        hull.line_id = None
        if hull.docked_at is None:
            # In passage, she makes the port she was bound for.
            hull.docked_at = line.dest if laden else line.origin
    master = lineroute.master_of(game, line)
    if master is not None:
        master.line_id = None
    if not lost:
        where = game.galaxy.systems[hull.docked_at].name if hull else "port"
        game.add_log(f"The {game.galaxy.systems[line.origin].name}–"
                     f"{game.galaxy.systems[line.dest].name} line stands "
                     f"down; the hauler lies at {where}.", "")


def running(game) -> list:
    house = getattr(game, "house", None)
    return [l for l in house.lines if l.active] if house is not None else []


# ── the day ─────────────────────────────────────────────────────────────────

def tick(game, n: int) -> None:
    """The house's day: every line's trip, and the month's books when due.

    Draws nothing from the day's stream: a trip rolls its own dice at
    departure (`linetrips.depart`), so a chronicle with no house plays exactly
    as it did before there were houses.
    """
    house = getattr(game, "house", None)
    if house is None or n <= 0:
        return
    for line in running(game):
        hull = lineroute.hull_of(game, line)
        if hull is not None:
            line.hands_due += hull.crew * HAND_A_DAY * n
        linetrips.advance(game, house, line)
    if game.day >= house.next_settle:
        settle(game, house)
    ledger.prune(game, house)


def settle(game, house) -> None:
    """The month: the charter, the hands, the masters, and the sweep."""
    house.next_settle = game.day + SETTLE_DAYS
    house.owed_charter += CHARTER_UPKEEP
    _clear_arrears(game, house)
    for line in house.lines:
        if line.hands_due <= 0:
            continue
        if house.account >= line.hands_due:
            ledger.post(game, house, line.id, "upkeep", -line.hands_due)
        else:
            house.owed_hands += line.hands_due
        line.hands_due = 0.0
    for master in masters_sim.payroll(game, house):
        line = next((l for l in house.lines
                     if l.id == master.line_id and l.active), None)
        if line is not None:
            stand_down(game, house, line)
        masters_sim.leave(game, house, master)
    if house.owed_charter > 0 or house.owed_hands > 0:
        game.add_log(f"The house is {round(house.owed_charter + house.owed_hands):,} "
                     "in arrears. Its hauls wait until it is paid.", "warn")
    keep = kept(house)
    if house.sweep and house.account > keep:
        ledger.to_purse(game, house, house.account - keep)


def kept(house) -> float:
    """What a sweep leaves: the reserve, and what every running line laid out
    on its last cargo. A sweep that took the working capital left a line
    buying ten tonnes into a sixty-tonne hold — measured, the second trip of a
    tender that cleared 12,900 on its first cleared 588, and the house was in
    arrears by day 180."""
    return house.reserve + sum(l.stake for l in house.lines if l.active)


def _clear_arrears(game, house) -> None:
    """Pay what the house owes, charter first, as far as the account goes."""
    pay = min(house.owed_charter, max(0.0, house.account))
    if pay > 0:
        ledger.post(game, house, 0, "charter", -pay)
        exchequer_sim.purse(game, house.power).credits += pay
        house.owed_charter -= pay
    pay = min(house.owed_hands, max(0.0, house.account))
    if pay > 0:
        ledger.post(game, house, 0, "upkeep", -pay)
        house.owed_hands -= pay
