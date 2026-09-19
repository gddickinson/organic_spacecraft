"""A trading house's books: the one door its account moves through.

A house account that could be written from anywhere would be the next place
money is conjured, so nothing else writes `TradingHouse.account`. `post` adds a
signed row and moves the balance by exactly that much; `to_purse` and
`from_purse` are the only two places the house and the captain's purse touch,
and they post too. So the account always equals the sum of what was posted,
and what crossed into the purse is on record both ways — which is the whole of
what `reconcile` checks and `test_freightlines` holds it to.

Rows are `[day, line id, kind, amount]`, line id 0 for the house itself. They
are pruned after `LEDGER_DAYS`; the lifetime totals by line and kind are kept
for ever, so "lifetime" never depends on how long a save has been played.
"""

from __future__ import annotations

from ..data.freightlines import LEDGER_DAYS, TRIP_KINDS


def post(game, house, line_id: int, kind: str, amount: float) -> float:
    """Move the house account by `amount` and write it down. Returns it."""
    amount = float(amount)
    if abs(amount) < 1e-9:
        return 0.0
    house.account += amount
    house.ledger.append([game.day, int(line_id), kind, round(amount, 2)])
    per = house.totals.setdefault(str(int(line_id)), {})
    per[kind] = per.get(kind, 0.0) + amount
    if line_id and kind in TRIP_KINDS:
        line = next((l for l in house.lines if l.id == line_id), None)
        if line is not None:
            line.trip_net += amount
    return amount


def to_purse(game, house, amount: float, kind: str = "sweep") -> float:
    """Pay money out of the house into the captain's purse. Returns it."""
    amount = max(0.0, min(float(amount), house.account))
    if amount <= 0:
        return 0.0
    post(game, house, 0, kind, -amount)
    game.credits += amount
    house.purse_in += amount
    return amount


def from_purse(game, house, amount: float) -> float:
    """Pay the captain's money into the house. Returns what moved."""
    amount = max(0.0, min(float(amount), game.credits))
    if amount <= 0:
        return 0.0
    game.credits -= amount
    house.purse_out += amount
    post(game, house, 0, "deposit", amount)
    return amount


def prune(game, house) -> None:
    """Drop itemised rows older than the ledger keeps. Totals stay."""
    cut = game.day - LEDGER_DAYS
    if house.ledger and house.ledger[0][0] < cut:
        house.ledger = [row for row in house.ledger if row[0] >= cut]


def recent(game, house, line_id: int | None = None, days: int = 90) -> dict:
    """What each kind came to over the last `days`, for one line or all."""
    since = game.day - days
    out: dict[str, float] = {}
    for day, lid, kind, amount in house.ledger:
        if day < since or (line_id is not None and lid != line_id):
            continue
        out[kind] = out.get(kind, 0.0) + amount
    return out


def lifetime(house, line_id: int | None = None) -> dict:
    """What each kind has come to since the charter, for one line or all."""
    out: dict[str, float] = {}
    for key, per in house.totals.items():
        if line_id is not None and key != str(line_id):
            continue
        for kind, amount in per.items():
            out[kind] = out.get(kind, 0.0) + amount
    return out


def net(kinds: dict, trading_only: bool = False) -> float:
    """The bottom line of a set of totals — the captain's own money moving
    in and out (`deposit`, `sweep`, `withdraw`) is not profit, so it is left
    out; `trading_only` leaves out time costs as well."""
    skip = {"deposit", "sweep", "withdraw"}
    return sum(v for k, v in kinds.items()
               if k not in skip and (not trading_only or k in TRIP_KINDS))


def reconcile(game, house) -> dict:
    """Whether the books balance: the account against everything posted,
    and the purse flows against the rows that recorded them."""
    everything = lifetime(house)
    posted = sum(everything.values())
    out_rows = everything.get("deposit", 0.0)
    in_rows = -(everything.get("sweep", 0.0) + everything.get("withdraw", 0.0))
    return {"account": house.account, "posted": posted,
            "balanced": abs(house.account - posted) < 0.01,
            "purse_out": house.purse_out, "purse_in": house.purse_in,
            "deposits": out_rows, "sweeps": in_rows,
            "fee": house.fee,
            "purse_ok": (abs(out_rows - house.purse_out) < 0.01
                         and abs(in_rows - house.purse_in) < 0.01)}
