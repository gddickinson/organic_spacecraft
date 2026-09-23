"""What a cargo contract costs to source, and what the card quotes.

Split out of `sim/contracts.py` when it reached five hundred lines, along the
seam the file already had: everything here is about **money before the work
starts** — the margin a posting pays over its own cargo, the haulage rate,
what sourcing costs the captain standing at the counter, and the quote the
board prints. What the contract *is*, how boards are generated and how work
is checked off stay next door.

Re-exported from `sim/contracts.py`, so `contracts.quote` is still the door.
"""

from __future__ import annotations

from ..data.commodities import BY_ID


#: What a cargo contract pays over what the cargo costs to source.
#:
#: The reward used to be `amount * (base * 0.55 + rate * 0.4)`, and `base *
#: 0.55` is the *floor* price — what a market with no stock of a good will pay
#: for it. Nobody sells at the floor: a real counter charges about `base * 1.1`.
#: So the board priced its work against a number that does not exist, and
#: measurement said 44% of cargo contracts paid less than their own cargo cost,
#: worst case fifty thousand credits down on a silicon job. Cheap goods
#: survived because the flat rate term carried them; expensive ones were traps.
CARGO_MARGIN = (1.28, 1.65)

#: Credits per tonne per light-year for carrying somebody else's cargo.
HAULAGE = 5.5


def cargo_cost(game, sysm, cid: str, amount: float,
               for_player: bool = False) -> float:
    """What sourcing this cargo costs at this port.

    Generation prices it neutrally — a contract's fee cannot depend on the
    standing of whoever happens to read the board. A *quote* prices it for the
    captain actually standing there, because that is what they will be charged.
    Getting that backwards made the board's quote wrong by two per cent, which
    the check caught.

    Falls back to the commodity's own price when the port stocks none of it —
    you would have to fetch it, which is not cheaper.

    The player's quote goes through `market.quote_buy`, which is the same
    helper the till uses. Calling `buy_price` here instead left the board
    quoting the plain price while the counter charged the one this power's
    memory of you decides — a difference of nearly nine hundred credits on a
    single cargo, which `test_cargo` caught the day the grudge landed.

    The same split decides the wharfage. `sim/wharfage.py` charges a share of
    every deal over a counter, and the share depends on the captain's standing
    with whoever holds the quay — so it belongs in the player's quote and not in
    the fee. Without it the card under-quoted a delivery by 542 credits on
    16,640, which `test_cargo` caught the day the due was added.
    """
    from ..world.economy import buy_price
    if for_player and sysm.market and sysm.port:
        from . import market as market_sim
        from . import wharfage as wharfage_sim
        from . import quayside as quayside_sim
        price = market_sim.quote_buy(game, sysm, cid)
        if price is not None:
            goods = price * amount
            # And getting it across (`sim/quayside`), for the same reason the
            # due is here: it is what the captain standing there will be
            # charged, and a card that leaves it out under-quotes.
            return (goods + wharfage_sim.due_on(game, sysm, goods)
                    + quayside_sim.fee(game, amount * BY_ID[cid].bulk, sysm))
    else:
        price = buy_price(sysm.market, cid, 0.0, 0.0) if sysm.market else None
    if price is None:
        price = BY_ID[cid].base * 1.1
    return price * amount


#: The kinds a captain completes by putting a commodity in the hold and
#: carrying it somewhere. `check` needs cargo for all three; `quote` priced
#: two of them and `shape` derived the fee from the goods for two of them, so
#: `relic` was the one cargo contract that was neither priced nor floored.
#: Measured over 271 of them: median net −402 against the market, **62%
#: losing money**, while deliver and prospect never lose a credit. The
#: whitelist was written twice and read like coverage both times.
CARGO_KINDS = ("deliver", "prospect", "relic")


def quote(game, contract) -> dict | None:
    """What the cargo will cost you here, and what you would clear.

    The board used to show a fee and nothing else, so a contract that lost
    fifty thousand credits looked exactly like one that made twelve.
    """
    if contract.kind not in CARGO_KINDS or not contract.commodity:
        return None
    sysm = game.galaxy.systems[contract.issued_at]
    held = game.ship.cargo.get(contract.commodity, 0)
    short = max(0.0, contract.amount - held)
    cost = cargo_cost(game, sysm, contract.commodity, short,
                      for_player=True)
    return {"cost": round(cost), "held": held, "short": short,
            "net": round(contract.reward - cost)}
