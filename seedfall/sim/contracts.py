"""Contracts — optional work, posted at ports.

A contract is a promise with a deadline attached. Accepting one costs nothing;
failing one costs standing. Progress is checked whenever the clock moves and
whenever you dock, so a contract completes the moment its terms are met rather
than when you remember to hand it in.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.save import register
from ..core.util import credits as cr
from ..data.commodities import BY_ID
from ..data.contracts import CARGO_WANTED, KINDS, POSTINGS
from ..data.factions import FACTIONS_BY_ID
from ..world.galaxy import distance
from . import allegiance

_uid = itertools.count(1)

MAX_ACTIVE = 6

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
    """
    from ..world.economy import buy_price
    rep = trade = 0.0
    if for_player:
        rep = game.rep.get(sysm.port.faction, 0) if sysm.port else 0
        trade = game.ship_stats.trade
    price = buy_price(sysm.market, cid, rep, trade) if sysm.market else None
    if price is None:
        price = BY_ID[cid].base * 1.1
    return price * amount


def quote(game, contract) -> dict | None:
    """What the cargo will cost you here, and what you would clear.

    The board used to show a fee and nothing else, so a contract that lost
    fifty thousand credits looked exactly like one that made twelve.
    """
    if contract.kind not in ("deliver", "prospect") or not contract.commodity:
        return None
    sysm = game.galaxy.systems[contract.issued_at]
    held = game.ship.cargo.get(contract.commodity, 0)
    short = max(0.0, contract.amount - held)
    cost = cargo_cost(game, sysm, contract.commodity, short,
                      for_player=True)
    return {"cost": round(cost), "held": held, "short": short,
            "net": round(contract.reward - cost)}


@register
@dataclass
class Contract:
    id: int
    kind: str
    issuer: str                 # faction id
    issued_at: int              # system id where it was posted
    title: str
    posting: str
    target_system: int | None = None
    target_body: str | None = None
    commodity: str | None = None
    amount: float = 0.0
    progress: float = 0.0
    reward: int = 0
    rep: int = 0
    deadline: int = 0           # absolute day
    accepted: bool = False
    done: bool = False
    failed: bool = False
    chain: str | None = None    # the commission this stage belongs to
    stage: int = 0
    #: What completing it cost with the issuer's enemies, for the screen.
    cost: list = field(default_factory=list)

    @property
    def definition(self):
        return KINDS[self.kind]

    def days_left(self, day: int) -> int:
        return self.deadline - day


# ── generation ─────────────────────────────────────────────────────────────

def _pick_target(rng, game, sysm, far: bool):
    """A system that is somewhere worth going, and reachable in principle."""
    systems = [s for s in game.galaxy.systems
               if s.id != sysm.id and s.bloom < 0.4]
    if not systems:
        return sysm
    systems.sort(key=lambda s: distance(s, sysm))
    pool = systems[len(systems) // 2:] if far else systems[:max(3, len(systems) // 3)]
    return rng.pick(pool or systems)


def generate(rng, game, sysm) -> list[Contract]:
    """The board at a port. Bigger ports post more, and post better."""
    if not sysm.port:
        return []
    faction = sysm.port.faction
    count = 2 + sysm.port.level
    out: list[Contract] = []

    for _ in range(count):
        kind = rng.weighted([
            (4, "deliver"), (4, "prospect"), (3, "survey"),
            (2, "bounty"), (2, "relic"), (2, "expedition"),
        ])
        d = KINDS[kind]
        deadline = game.day + rng.int(*d.deadline)
        c = Contract(id=next(_uid), kind=kind, issuer=faction, issued_at=sysm.id,
                     title="", posting=rng.pick(POSTINGS[kind]),
                     rep=d.rep, deadline=deadline)

        if not shape(rng, game, sysm, c, faction):
            continue
        out.append(c)
    return out


def shape(rng, game, sysm, c: Contract, faction: str, scale: float = 1.0) -> bool:
    """Fill in a contract's target, amount and fee from its kind.

    Shared by the ordinary board and by commissions, so a chain stage is an
    ordinary contract in every respect except who is asking and what follows
    from finishing it. ``scale`` adjusts how much is asked for *before* the
    title is written, because a posting that reads "carry 62 t" and completes
    at 31 t is a posting nobody can plan a hold around. Returns False if this
    kind cannot be posted here.
    """
    kind = c.kind
    d = KINDS[kind]

    if kind in ("deliver", "prospect"):
        c.commodity = rng.pick(CARGO_WANTED)
        c.amount = max(1, round(rng.int(20, 80) * scale))
        c.reward = round(cargo_cost(game, sysm, c.commodity, c.amount)
                         * rng.float(*CARGO_MARGIN)
                         + c.amount * d.rate * 0.25)
        if kind == "deliver":
            target = _pick_target(rng, game, sysm, far=rng.chance(0.5))
            c.target_system = target.id
            c.title = (f"Carry {c.amount:g} t of {BY_ID[c.commodity].name} "
                       f"to {target.name}")
        else:
            c.title = (f"Supply {c.amount:g} t of {BY_ID[c.commodity].name}")
    elif kind == "survey":
        target = _pick_target(rng, game, sysm, far=True)
        c.target_system = target.id
        c.amount = max(1, min(len(target.bodies),
                              round(rng.int(2, 4) * scale)))
        c.reward = round(d.rate * c.amount * rng.float(0.8, 1.4))
        c.title = f"Survey {c.amount:g} bodies at {target.name}"
    elif kind == "bounty":
        c.commodity = rng.pick(["freeholds", "concordat", "sanhedrin", "bloom"])
        if c.commodity == faction:
            c.commodity = "bloom"
        c.amount = max(1, round(rng.int(1, 2) * scale))
        c.reward = round(d.rate * c.amount * rng.float(0.8, 1.5))
        enemy = FACTIONS_BY_ID[c.commodity].short
        c.title = f"Destroy {c.amount:g} {enemy} hull(s)"
    elif kind == "relic":
        c.commodity = "xenolith"
        c.amount = max(1, round(rng.int(1, 3) * scale))
        c.reward = round(d.rate * c.amount * rng.float(0.9, 1.3))
        c.title = f"Deliver {c.amount:g} intact xenolith(s)"
    else:                                   # expedition
        target = _pick_target(rng, game, sysm, far=rng.chance(0.6))
        landable = [b for b in target.bodies if b.kind not in ("gas", "star")]
        if not landable:
            return False
        body = rng.pick(landable)
        c.target_system = target.id
        c.target_body = body.id
        c.amount = 1
        c.reward = round(d.rate * rng.float(0.8, 1.5))
        c.title = f"Put a party on {body.name}"

    # Distance pays. For cargo it pays *haulage* — a flat fee per tonne per
    # light-year — rather than multiplying the value of the goods, which turned
    # a long silicon run into a hundred and thirty thousand credits.
    if c.target_system is not None:
        ly = distance(game.galaxy.systems[c.target_system], sysm)
        if kind in ("deliver", "prospect"):
            c.reward = round(c.reward + c.amount * ly * HAULAGE)
        else:
            c.reward = round(c.reward * (1 + ly / 40))
    return True


# ── the player's book ──────────────────────────────────────────────────────

def accept(game, contract: Contract) -> tuple[bool, str]:
    # Commission stages do not count against the board limit: they are not
    # work you chose to juggle, they are the next thing somebody asked for.
    active = [c for c in game.contracts
              if not c.done and not c.failed and not c.chain]
    if len(active) >= MAX_ACTIVE:
        return False, f"You are already carrying {MAX_ACTIVE} contracts."
    contract.accepted = True
    game.contracts.append(contract)
    return True, ""


def abandon(game, contract: Contract) -> None:
    contract.failed = True
    game.adjust_rep(contract.issuer, -contract.rep)


def _cargo_held(game, cid: str) -> float:
    return game.ship.cargo.get(cid, 0) + game.stores.get(cid, 0)


def check(game) -> list[tuple[Contract, str]]:
    """Advance every accepted contract. Returns (contract, outcome) events."""
    events: list[tuple[Contract, str]] = []
    for c in list(game.contracts):
        if c.done or c.failed:
            continue
        if game.day > c.deadline:
            c.failed = True
            game.adjust_rep(c.issuer, -c.rep)
            events.append((c, "expired"))
            continue

        if c.kind == "deliver":
            if (game.location_id == c.target_system
                    and _cargo_held(game, c.commodity) >= c.amount):
                _take_cargo(game, c.commodity, c.amount)
                _pay(game, c)
                events.append((c, "done"))
        elif c.kind in ("prospect", "relic"):
            here = game.system.port and game.location_id == c.issued_at
            if here and _cargo_held(game, c.commodity) >= c.amount:
                _take_cargo(game, c.commodity, c.amount)
                _pay(game, c)
                events.append((c, "done"))
        elif c.kind == "survey":
            target = game.galaxy.systems[c.target_system]
            c.progress = sum(1 for b in target.bodies if b.surveyed)
            if c.progress >= c.amount:
                _pay(game, c)
                events.append((c, "done"))
        elif c.kind == "expedition":
            if c.progress >= 1:
                _pay(game, c)
                events.append((c, "done"))
    return events


def note_kill(game, faction_id: str | None) -> list[Contract]:
    """Combat tells the book when something has been destroyed."""
    hit = []
    for c in game.contracts:
        if c.done or c.failed or c.kind != "bounty":
            continue
        if faction_id and c.commodity == faction_id:
            c.progress += 1
            if c.progress >= c.amount:
                _pay(game, c)
            hit.append(c)
    return hit


def note_landing(game, system_id: int, body_id: str) -> list[Contract]:
    """A landing party reports in against any ground contract."""
    hit = []
    for c in game.contracts:
        if c.done or c.failed or c.kind != "expedition":
            continue
        if c.target_system == system_id and c.target_body == body_id:
            c.progress = 1
            hit.append(c)
    return hit


def _take_cargo(game, cid: str, amount: float) -> None:
    from .ship import add_cargo
    from_ship = min(game.ship.cargo.get(cid, 0), amount)
    add_cargo(game.ship, cid, -from_ship)
    rest = amount - from_ship
    if rest > 0:
        game.stores[cid] = max(0.0, game.stores.get(cid, 0) - rest)


def _pay(game, c: Contract) -> None:
    c.done = True
    game.credits += c.reward
    game.adjust_rep(c.issuer, c.rep)
    # Being seen to do a power's work is a position, not a neutral errand.
    # Whose enemies mind, and how much, is `sim/allegiance.py`.
    c.cost = allegiance.charge(game, c.issuer, c.rep)


def active(game) -> list[Contract]:
    """Board work in hand. Commission stages are listed with their commission."""
    return [c for c in game.contracts
            if not c.done and not c.failed and not c.chain]


def all_open(game) -> list[Contract]:
    return [c for c in game.contracts if not c.done and not c.failed]


def summary(c: Contract, day: int) -> str:
    left = c.days_left(day)
    return f"{cr(c.reward)} · {left} day(s) left"
