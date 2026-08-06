"""Where to take a cargo, and how you came to know it.

Measured across four sectors: within a starting jump range only 5% of
lane/goods combinations are profitable — but there are about twenty of them per
sector and the best is worth some fourteen hundred credits a tonne, and the
rate climbs to 16% as the drive improves. So the trades exist and are
reachable. They are simply invisible: six of twelve openings offer no
profitable run the player can *see*, because finding one means visiting every
neighbour and writing down prices first.

That makes this an information problem, and it has two honest sources. Your own
register — ports you have stood in, with prices that go stale. And the
harbourmaster, who knows what his own power's other ports are short of, will
say so if he thinks well enough of you, and does not know the exact figure.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data.commodities import BY_ID
from ..world.economy import demands
from ..world.galaxy import distance
from . import market as market_sim

#: Standing below which the desk has nothing to say to you.
#:
#: Set against the standing bands, not picked. The first value here was -8,
#: which is the floor of "Neutral" — and the Dry Choir *starts* at -10, so a
#: new captain standing on a Dry Choir quay was locked out of the mechanic on
#: day one for no reason of their own. Found by flying a career and getting
#: zero runs at Halcyon Wake. Distrusted (-25) is the honest line: the desk
#: talks to anyone it has no active reason to distrust.
COLD = -25.0

#: How many of its own ports a desk will name, by how well it likes you.
def desk_reach(standing: float) -> int:
    if standing < COLD:
        return 0
    if standing >= 40:
        return 4
    if standing >= 15:
        return 3
    return 2


#: What the desk's estimate is worth against a price you wrote down yourself.
HEARSAY = 0.75

#: The least a spread can be, as a share of what you pay, and still be worth
#: flying.
#:
#: Derived from the market, not chosen. `tick_market` drags supply toward
#: equilibrium by about 1.8% a day and adds a random walk on top, so over a
#: week's voyage a price moves several per cent on its own. Measured on a real
#: run: the desk said a port paid 590, it paid 530 by the time the hull got
#: there, and the margin had been 14. A spread thinner than the drift is not a
#: trade, it is a coin toss with a fuel bill.
#:
#: Then measured properly, flying 120 openings and banding the outcome by the
#: spread the run advertised:
#:
#:     spread   runs  won   net/t
#:      0-4%      16   31%    -161
#:      4-8%       6   33%     -32
#:      8-12%      2    0%     -56
#:     12-16%      3   33%     -87
#:     16-20%      4   50%     -19
#:     24-28%      1  100%     +50
#:
#: Small samples, but the direction does not waver: below a fifth, a run loses
#: on average however good the spread looks when you load. The desk will not
#: recommend one.
MIN_SPREAD = 0.20

#: How much of a price gap the market closes on its own, per day of voyage.
#:
#: `market.tick_market` drags supply toward equilibrium by about 1.8% a day,
#: which the `MIN_SPREAD` note above already relies on — it is written down
#: there and was never *applied*. A run is quoted at the moment you are
#: standing at the desk and flown over the days that follow, so the margin you
#: are shown is not the margin you get.
DRIFT_PER_DAY = 0.018

#: Days a light year of voyage costs, for pricing the wait.
#:
#: Measured on the desk's own runs rather than guessed: 5.5 ly took 7 days,
#: 8.5 took 9, 10.6 took 11. About a day a light year plus a day and a half of
#: getting under way, and near enough for discounting a price.
DAYS_PER_LY = 1.0
DAYS_FIXED = 1.5


@dataclass(frozen=True)
class Run:
    commodity: str
    target_id: int
    target_name: str
    buy_here: int
    pays: int
    ly: float
    source: str          # "register" | "desk"
    confidence: float

    @property
    def margin(self) -> int:
        return self.pays - self.buy_here

    @property
    def days(self) -> float:
        """Roughly how long getting there takes."""
        return DAYS_FIXED + DAYS_PER_LY * self.ly

    @property
    def survives(self) -> float:
        """The share of the quoted margin still there when you arrive.

        **`ly` was carried on every run and read by `reachable` alone.** The
        desk knew how far each run was and priced none of it, so a thin margin
        eleven days away ranked level with a fat one seven days away, and the
        board recommended runs whose spread had closed before the hull got
        there. Measured over 24 careers, following the desk earned 44,627
        against 47,910 for trading on what you could see — the advice was
        worse than no advice.
        """
        return (1.0 - DRIFT_PER_DAY) ** self.days

    @property
    def worth(self) -> float:
        """Margin discounted by trust in the number *and* by the journey."""
        return self.margin * self.confidence * self.survives

    @property
    def on_arrival(self) -> float:
        """What the margin is expected to be worth by the time you are there."""
        return self.margin * self.survives


def _buyable(game, here) -> dict[str, int]:
    """What this port will sell you, at what you would actually pay.

    Through `market.quote_buy` — the counter's own door — not the raw price.
    This card carried the bug `voyage`'s docstring documents fixing: it read
    `buy_price` without the grudge bias or the office rate, so the desk
    forecast an outlay the counter would not honour.
    """
    if not here.market:
        return {}
    out = {}
    for cid in here.market.stock:
        good = BY_ID.get(cid)
        if good is None or not good.legal:
            continue
        price = market_sim.quote_buy(game, here, cid)
        if price is not None and here.market.stock[cid].units > 0:
            out[cid] = price
    return out


def from_register(game, here) -> list[Run]:
    """Runs your own notes support. Real prices, and possibly out of date."""
    runs = []
    for cid, cost in _buyable(game, here).items():
        # Every port the register knows, not the top four. `best_markets`
        # defaults to a *display* limit, and inheriting it here meant the runs
        # this desk could offer depended on how many rows a panel draws — which
        # only showed up when the ordering changed and a different four
        # survived.
        for row in market_sim.best_markets(game, cid, selling=True, limit=99):
            target = row["system"]
            if target.id == here.id or row["price"] <= cost:
                continue
            runs.append(Run(commodity=cid, target_id=target.id,
                            target_name=target.name, buy_here=cost,
                            pays=row["price"], ly=distance(target, here),
                            source="register", confidence=row["confidence"]))
    return runs


def from_desk(game, here) -> list[Run]:
    """What the harbourmaster will tell you about his own power's ports.

    He names ports, and what they are short of. He does not quote you their
    board — that is their business — so the figure is an estimate and is
    discounted accordingly.
    """
    if not here.port:
        return []
    faction = here.port.faction
    standing = game.rep.get(faction, 0)
    reach = desk_reach(standing)
    if not reach:
        return []

    theirs = [s for s in game.galaxy.systems
              if s.id != here.id and s.market and s.port
              and s.port.faction == faction]
    theirs.sort(key=lambda s: distance(s, here))
    buyable = _buyable(game, here)

    runs = []
    for target in theirs[:reach]:
        for cid in demands(target.market, limit=3):
            cost = buyable.get(cid)
            if cost is None:
                continue
            # What *this* captain's counter at that port would actually pay —
            # their standing and their grudges travel with them. The HEARSAY
            # discount below carries the uncertainty; the base figure should
            # not add its own error by quoting a stranger's price.
            pays = market_sim.quote_sell(game, target, cid)
            if pays is None or pays <= cost:
                continue
            runs.append(Run(commodity=cid, target_id=target.id,
                            target_name=target.name, buy_here=cost,
                            pays=pays, ly=distance(target, here),
                            source="desk", confidence=HEARSAY))
    return runs


def runs(game, here, limit: int = 6) -> list[Run]:
    """Everything worth loading here, best first, your own notes preferred."""
    best: dict[tuple[str, int], Run] = {}
    for run in from_register(game, here) + from_desk(game, here):
        if run.margin <= 0:
            continue
        key = (run.commodity, run.target_id)
        held = best.get(key)
        # A price you wrote down beats a price somebody described to you —
        # **which this said and did not do.** It took whichever run had the
        # higher `worth`, and the register happened to win often enough that the
        # check on it passed: a desk rumour quoting a better number than your own
        # notes replaced them silently. Reordering the register by what a run is
        # worth per day was enough to flip it, which is how it surfaced.
        if held is None:
            best[key] = run
        elif held.source != "register" and run.source == "register":
            best[key] = run
        elif held.source == run.source and run.worth > held.worth:
            best[key] = run
    ordered = sorted(best.values(), key=lambda r: -r.worth)
    return ordered[:limit]


def reachable(game, run) -> bool:
    return run.ly <= game.ship_stats.jump


def voyage(game, run, tonnes: float | None = None) -> dict:
    """What the whole trip costs and clears, not just the margin per tonne.

    Ranking by margin alone is how a captain ends up flying a four-credit
    spread across nine light-years and paying for the reaction mass out of
    their own pocket. Measured: a career following per-tonne margins made
    thirty-five runs and finished eight thousand credits down.
    """
    from .actions import jump_quote
    from .ship import cargo_free
    from . import wharfage as wharfage_sim

    target = game.galaxy.systems[run.target_id]
    quote = jump_quote(game, target)
    fuel_t = quote["fuel"]
    fuel_price = 0
    if game.system.market:
        fuel_price = market_sim.quote_buy(game, game.system, "volatiles") or 0

    room = cargo_free(game.ship, game.ship_stats)
    afford = (int(game.credits // wharfage_sim.unit_cost(
        game, game.system, run.buy_here)) if run.buy_here else 0)
    # And what the port actually has on the quay. **Measured: 12 of 15
    # recommended runs forecast more tonnage than the port held, the worst by
    # 2.7×** — a desk quoting a 287-tonne voyage out of a berth holding 59. It
    # mattered twice over: the figures on the card were unloadable, and
    # `worth_flying` ranks by `net`, which scales with tonnage, so runs were
    # ordered by cargo that did not exist. `trade.buy` has always capped at the
    # stock; this is the same number, read at forecast time.
    stocked = 0.0
    if game.system.market and run.commodity in game.system.market.stock:
        stocked = game.system.market.stock[run.commodity].units
    if tonnes is None:
        tonnes = max(0.0, min(room, afford, stocked))

    outlay = run.buy_here * tonnes
    fuel = fuel_t * fuel_price
    # Confidence discounts the *spread*, not the takings. Applying it to
    # revenue says you only receive three quarters of the price, which made
    # every run the harbourmaster described look like a loss and emptied the
    # desk. What is uncertain is the margin, not whether they pay you.
    expected = run.margin * run.confidence * tonnes
    # A quay takes its cut at both ends of a run, and a desk that forecast the
    # spread and the fuel and not the wharfage would be quoting a number the
    # counter cannot pay. Both ends are asked of `sim/wharfage.py` — the same
    # function that takes the money — and the far end is asked about the port
    # the run actually points at, not this one.
    dues = (wharfage_sim.due_on(game, game.system, run.buy_here * tonnes)
            + wharfage_sim.due_on(game, target, run.pays * tonnes))
    return {"tonnes": tonnes, "outlay": round(outlay), "fuel": round(fuel),
            "days": quote["days"], "fuel_t": fuel_t,
            "takings": round(run.pays * tonnes), "dues": dues,
            "net": round(expected - fuel - dues),
            "in_range": quote["in_range"]}


def worth_flying(game, here, limit: int = 6) -> list[tuple]:
    """Runs ranked by what the voyage actually clears, best first."""
    out = []
    for run in runs(game, here, limit=99):
        if not reachable(game, run):
            continue
        # Against what survives the voyage, not what is quoted at the desk.
        # A spread that is only just over the floor when you load is under it
        # by the time you arrive, which is exactly the trade `MIN_SPREAD`
        # exists to refuse.
        if run.on_arrival < run.buy_here * MIN_SPREAD:
            continue          # inside the drift; not a trade
        trip = voyage(game, run)
        if trip["tonnes"] < 1 or trip["net"] <= 0:
            continue
        out.append((run, trip))
    out.sort(key=lambda pair: -pair[1]["net"])
    return out[:limit]


def summary(game, here) -> dict:
    found = runs(game, here, limit=99)
    near = [r for r in found if reachable(game, r)]
    return {"runs": len(found), "reachable": len(near),
            "best": max((r.margin for r in near), default=0),
            "standing": game.rep.get(here.port.faction, 0) if here.port else 0,
            "reach": desk_reach(game.rep.get(here.port.faction, 0)
                                if here.port else 0)}
