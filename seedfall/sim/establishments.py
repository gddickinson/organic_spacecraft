"""Which establishments are in a system, read off the chronicle's seed.

Nothing here is stored and nothing spends luck: the same system has the same
yard, the same Grand and the same den in every visit and every process,
drawn from `RNG(f"{seed}:establish:{system id}")` the way a derelict is. How
many a system has depends on its trade (`data/establishments.ODDS`): a
Fleet Hub has three or four, a quiet rock with no port one at most, and
the kinds that need a port to trade with only turn up where there is one.

`here(game, system)` is every establishment in a system as `Found` rows;
`sim/places.py` turns each into a `Place`, and `builds_here` answers the
yard's question for `sim/shipyard.can_build_here`.

**A stake** is a tenth of a house bought while alongside it
(`data/establishments.WORTH`): it pays out of the house's own takings every
`STAKE_DAYS` — never out of nothing, and never more than the takings of a
business that size — and a statement comes by despatch each quarter. Sold
back, it fetches `SELL_BACK` of its price.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.rng import RNG
from ..data import establishments as table
from ..data.establishments import ESTABLISHMENTS, ODDS, WORDS


@dataclass(frozen=True)
class Found:
    """One establishment, at one body of one system."""

    kind: object
    name: str
    body_id: str
    body_name: str


def here(game, system) -> list:
    """Every establishment in this system, in the order the seed drew them."""
    if system is None or not getattr(system, "bodies", None):
        return []
    rng = RNG(f"{getattr(game, 'seed', 'verge')}:establish:{system.id}")
    port = getattr(system, "port", None)
    trade = "capital" if port is not None and getattr(
        port, "capital", False) else "port" if port is not None else "none"
    out, used = [], set()
    for odds in ODDS[trade]:
        if not rng.chance(odds):
            break
        pool = [(e.weight, e) for e in ESTABLISHMENTS
                if e.id not in used and (port is not None or not e.needs_port)
                and any(b.kind in e.at for b in system.bodies)]
        if not pool:
            break
        kind = rng.weighted(pool)
        used.add(kind.id)
        body = rng.pick([b for b in system.bodies if b.kind in kind.at])
        name = rng.pick(kind.names).format(body=body.name,
                                           word=rng.pick(WORDS))
        out.append(Found(kind, name, body.id, body.name))
    return out


def builds_here(game, system, need: str) -> bool:
    """Does a yard in this system lay down hulls that need `need`?"""
    return any(f.kind.builds == need for f in here(game, system))


# ── stakes ─────────────────────────────────────────────────────────────────

def stake_terms(game, place) -> dict:
    """What a stake in this place costs and pays, and whether one can be
    bought or sold here today."""
    worth = table.WORTH.get(getattr(place, "look", ""), 0)
    held = (getattr(game, "stakes", {}) or {}).get(place.id)
    price = int(held["price"]) if held else int(worth * table.STAKE_SHARE)
    out = {"ok": False, "why": "", "price": price, "held": bool(held),
           "monthly": int(price * table.STAKE_MONTHLY),
           "back": int(price * table.SELL_BACK)}
    if not worth:
        out["why"] = "It is not for sale."
    elif not place.here:
        out["why"] = "Stakes are signed for in person. Come alongside."
    elif not held and game.credits < price:
        out["why"] = f"A stake is {price:,} cr."
    else:
        out["ok"] = True
    return out


def buy_stake(game, place) -> dict:
    got = stake_terms(game, place)
    if not got["ok"] or got["held"]:
        return {"ok": False, "why": got["why"] or "You hold one already."}
    game.credits -= got["price"]
    game.stakes[place.id] = {"price": got["price"], "paid": float(game.day),
                             "told": float(game.day), "name": place.name,
                             "system": place.system_id}
    _tell(game, place.name, place.system_id, f"A stake in {place.name}",
          f"The house has you on its books for a tenth: "
          f"{got['price']:,} cr, and {got['monthly']:,} cr a month out of "
          "the takings while it trades.")
    game.add_log(f"A stake in {place.name}: {got['price']:,} cr.", "good")
    return {"ok": True, "price": got["price"]}


def sell_stake(game, place) -> dict:
    got = stake_terms(game, place)
    if not got["held"]:
        return {"ok": False, "why": "You hold no stake here."}
    if not got["ok"]:
        return {"ok": False, "why": got["why"]}
    del game.stakes[place.id]
    game.credits += got["back"]
    game.add_log(f"Sold the stake in {place.name}: {got['back']:,} cr.", "")
    return {"ok": True, "back": got["back"]}


def tick(game, days: float) -> None:
    """Share out the takings to every stakeholder, and send the quarter's
    statement. Nothing is paid for a month not yet traded."""
    for held in list((getattr(game, "stakes", {}) or {}).values()):
        month = int(held["price"] * table.STAKE_MONTHLY)
        while float(game.day) - float(held["paid"]) >= table.STAKE_DAYS:
            held["paid"] = float(held["paid"]) + table.STAKE_DAYS
            game.credits += month
            held["banked"] = int(held.get("banked", 0)) + month
        if float(game.day) - float(held["told"]) >= table.STATEMENT_DAYS:
            held["told"] = float(game.day)
            _tell(game, held["name"], held["system"],
                  f"{held['name']}: the quarter",
                  f"The house's statement: {held.get('banked', 0):,} cr "
                  "paid out to you from the takings this quarter.")
            held["banked"] = 0


def _tell(game, name: str, system_id: int, subject: str, body: str) -> None:
    from . import comms
    comms.send(game, f"est:{name}", name, "news", subject, body,
               system_id=system_id)
