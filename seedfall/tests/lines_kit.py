"""Fixtures for the freight-line checks: a house, haulers, masters, a route.

Every fixture is built through the sim's own doors — the charter, the hire,
the deposit, the forecast — so a check that uses one is also a check that
those doors work. Only the hulls are conjured into the fleet: laying one down
at a yard is `shipyard`'s business and has its own suite, and waiting the
thirty-odd days on the slip would cost every check here a month of clock.
"""

from __future__ import annotations

import copy

from ..core.state import new_game
from ..sim import freightlines as lines_sim
from ..sim import lineforecast
from ..sim import lineledger
from ..sim import market as market_sim
from ..sim import masters as masters_sim
from ..sim import upkeep
from ..sim.ship import build_layers, make_ship

#: A sector whose home port has nine markets within a TENDER's reach.
SEED = "s5"


def house(seed: str = SEED, chassis: str = "tender",
          deposit: float = 200_000):
    """A chartered house with one hauler at the home port and its best
    master aboard, and a register that has seen every port."""
    game = new_game(seed)
    game.credits = 900_000
    for system in game.galaxy.systems:
        if system.market is not None:
            market_sim.note_prices(game, system)
    told = lines_sim.charter(game)
    assert told["ok"], told
    hull = hauler(game, chassis)
    lines_sim.deposit(game, deposit)
    return game, hull, hire(game)[0]


def hauler(game, chassis: str = "tender", name: str | None = None):
    """A hull of a hauling class berthed at the home port, with the drive
    the Yards fit to it as standard."""
    drive = "reaction_organ" if chassis in ("atlas", "medusa") else "ion_cluster"
    ship = make_ship(chassis, [drive], name or f"{chassis.title()} "
                                               f"{len(game.fleet)}")
    build_layers(ship, game.bonuses)
    ship.docked_at = game.location_id
    game.fleet.append(ship)
    return ship


def hire(game, count: int = 1) -> list:
    """The ablest masters on offer, walking the recruit desks for more."""
    got = []
    home = game.location_id
    ports = [s for s in game.galaxy.systems
             if s.port is not None and "recruit" in s.port.services]
    for port in [game.galaxy.systems[home]] + ports:
        game.location_id = port.id
        for master in sorted(masters_sim.pool_at(game, port),
                             key=lambda m: -m.skill):
            if len(got) < count and masters_sim.hire(game, master)["ok"]:
                got.append(master)
        if len(got) >= count:
            break
    game.location_id = home
    return got


def feed(game, days: int = 400) -> None:
    for cid, a_day in upkeep.demand(game).items():
        game.ship.cargo[cid] = max(game.ship.cargo.get(cid, 0), a_day * days)


def wait(game, days: int) -> None:
    """Days on the clock, the captain's crew fed."""
    for _ in range(days):
        feed(game)
        game.advance_days(1)


def route(game, hull, master, lawless: bool = False, cadence: int = 0):
    """The best line from the home port, by what it clears in ninety days —
    through a system at 0.40 lawlessness or worse, or kept under 0.20."""
    best = None
    for dest in game.galaxy.systems:
        if dest.market is None or dest.id == game.location_id:
            continue
        for cid in game.system.market.stock:
            line = lines_sim.draft(game, hull.uid, master.id,
                                   game.location_id, dest.id, cid, 9999,
                                   cadence=cadence)
            told = lines_sim.open_terms(game, line)
            if not told["ok"] or not told["forecast"]["ok"]:
                continue
            worst = told["forecast"]["risk"]["worst"]
            if (worst < 0.40) if lawless else (worst >= 0.20):
                continue
            cash = told["forecast"]["per90"]
            if best is None or cash > best[0]:
                best = (cash, line, told["forecast"])
    assert best is not None, f"no {'lawless' if lawless else 'policed'} route"
    return best[1], best[2]


def one_trip(game, line, trip: int, walk: int = 0):
    """Fly one trip of a line in a copy of the chronicle: its own dice
    (`trip`), and its own market weather (`walk` moves the day's stream).
    Returns the copy and the line as it came home."""
    twin = copy.deepcopy(game)
    twin.rng_seed = (twin.rng_seed + 7919 * walk) & 0xFFFFFFFF
    paper = copy.deepcopy(line)
    paper.trips, paper.cadence = trip, 90
    opened = lines_sim.open_line(twin, paper)
    assert opened["ok"], opened
    sailed = twin.house.lines[-1]
    for _ in range(200):
        if sailed.trips != trip or not sailed.active:
            break
        feed(twin)
        twin.advance_days(1)
    return twin, sailed


def trip_cash(game, line) -> float:
    """What a line's trips have cleared, repairs left out — the forecast
    prices wear per trip, and the yard bills it only when she is worn."""
    kinds = lineledger.lifetime(game.house, line.id)
    return sum(v for k, v in kinds.items()
               if k in lineforecast.TRIP_CASH)


def done_net(game, line) -> float:
    """What a line has cleared on its finished trips, wages and upkeep in."""
    under_way = line.phase in ("out", "sell", "home")
    total = lineledger.net(lineledger.lifetime(game.house, line.id))
    return total - (line.trip_net if under_way else 0.0)
