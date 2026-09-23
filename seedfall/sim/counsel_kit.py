"""The shapes and small reads the counsel sources share.

`S` is a suggestion. The rest answer the questions every source asks the
same way — can this be bought here, what is the next jump toward there, what
does the road to an ending want researched next — so two sources cannot
disagree about them, and each asks the function the act itself will.
"""

from __future__ import annotations

from ..data.milestone_tracks import ROADS, RUNG_TECH
from ..data.tech import TECH_BY_ID


def S(sid, title, why, screen, tab="", *, system=None, verb="go", args=None,
      weight=0, blocked=""):
    """One suggestion: what, why, the act (`verb`, `args`), the screen that
    shows it (`screen`, `tab`, `system`), how pressing it ranks, and — if
    the act would refuse today — the refusal, word for word."""
    return {"id": sid, "title": title, "why": why, "screen": screen,
            "tab": tab, "system": system, "verb": verb,
            "args": dict(args or {}), "weight": weight, "blocked": blocked}


def in_market(game) -> bool:
    here = game.system
    return bool(here.port and here.market)


def buyable(game, cid: str, units: int) -> bool:
    """Would `trade.buy` take at least one tonne of this here, now?

    The same gates in the same order: the counter will deal with you, it
    stocks the good, there is room, you can pay a tonne and its due."""
    from . import enforce, market as market_sim, quayside, wharfage
    from ..data.commodities import bulk_of
    from .ship import cargo_free
    here = game.system
    if not in_market(game) or units < 1:
        return False
    if not enforce.may_trade(game, here)[0]:
        return False
    if not quayside.may_move(game, 1.0, here)[0]:
        return False          # too far off the quay for anything to cross
    price = market_sim.quote_buy(game, here, cid)
    if price is None or cid not in here.market.stock:
        return False
    room = int(cargo_free(game.ship, game.ship_stats) / bulk_of(cid))
    afford = int(game.credits // wharfage.unit_cost(game, here, price))
    return min(room, afford, here.market.stock[cid].units) >= 1


def nearest(game, wanted):
    """The nearest system (this region, by hops) that `wanted` accepts."""
    from . import reach
    found = reach.routes_from(game)
    best = None
    for sid, row in found.items():
        system = game.galaxy.systems[sid]
        if sid == game.location_id or not wanted(system):
            continue
        key = (row["hops"], row["days"], sid)
        if best is None or key < best[0]:
            best = (key, system)
    return best[1] if best else None


def hop_to(game, target) -> dict | None:
    """The next jump toward `target`, as a suggestion's act — or None when
    the drive cannot get there at all. A jump the tank cannot pay for is
    offered with the refusal `actions.jump_to` gives, word for word."""
    from . import actions, lineroute
    if target is None or target.id == game.location_id:
        return None
    route = lineroute.path(game, game.location_id, target.id,
                           game.ship_stats.jump)
    if not route or len(route) < 2:
        return None
    step = route[1]
    quote = actions.jump_quote(game, step)
    if not quote["in_range"]:
        return None
    blocked = ""
    have = game.ship.cargo.get("volatiles", 0)
    if have < quote["fuel"]:
        blocked = (f"Not enough reaction mass: {quote['fuel']} t of "
                   f"volatiles needed, {int(have)} aboard.")
    return {"verb": "jump", "args": {"to": step.id}, "blocked": blocked}


def road(track: str | None, goal: str | None = None) -> list:
    """The technologies an ending's road asks for (or the road to `goal`),
    prerequisites first."""
    goal = goal or ROADS.get(track or "")
    out: list = []

    def walk(tid: str) -> None:
        if tid in out or tid not in TECH_BY_ID:
            return
        for req in TECH_BY_ID[tid].reqs:
            walk(req)
        out.append(tid)

    if goal:
        walk(goal)
    return out


def road_tech(game, track: str | None):
    """What to research next: the cheapest open node toward the track's next
    rung when that rung is a technology, else on the ending's road, else the
    cheapest open node at all."""
    from . import renown, research
    unlocked = game.research.unlocked
    open_now = sorted(research.researchable(unlocked), key=lambda t: t.cost)
    step = renown.next_step(game, track) if track else None
    rung = RUNG_TECH.get(step["milestone"].fact) if step else None
    first = road(track, rung) if rung else []
    for wanted in (first, road(track)):
        picks = [t for t in open_now if t.id in wanted]
        if picks:
            return picks[0]
    return open_now[0] if open_now else None
