"""The concourse: what is open here, what it sells, and what a night costs.

Three counters, one module, because they are one question — *what can a
captain do with money at this port* — and the answer to all three comes out
of the same world profile:

- **The chandler.** Personal equipment, from `data/kit.py`. What is on the
  shelf is the world's tech level; what the desk will let you carry off is
  its law level. A railgun is ordinary at law 2 and four years in a cell at
  law 9, and it is the *same list* either way.
- **The bank.** Somewhere to keep money that is not in the hull, and a
  letter of credit to move it without carrying it. **It makes no money** —
  it holds it and moves it, which is the whole of what a bank does that this
  game needs and the only shape that cannot become a printing press.
- **Eating and entertainment.** A night ashore, which costs credits and buys
  morale, loyalty, standing and sometimes something worth hearing.

Every credit that moves here moves through `spend` or `take`, so there is one
door to read when somebody asks where the money went.
"""

from __future__ import annotations

from ..data import kit as kit_table
from ..data import venues as venue_table
from . import places as places_sim
from . import profile as profile_sim

#: What a chandler pays for a thing you are selling back, as a share of what
#: it asks for the same thing. The same spread rule the cargo market keeps:
#: a counter that pays what it charges is a money printer, and this project
#: has been bitten by exactly that (`solvency`).
BUYBACK = 0.45

#: How much of the crew goes ashore at once, and the least it can be. A night
#: ashore is bought for the watch, not for one person.
ASHORE_SHARE = 0.6


def _where(game, at):
    """A place, whatever was handed in.

    **Every counter here takes a place now** (`sim/places.py`) — a quay, a
    habitat drum, a holding of yours, a power's settlement — because people
    are not only at starports and a drum with a million in it had nothing to
    sell anybody. A *system* is still accepted and means its port, so every
    caller written before places existed still reads the quay it meant.
    """
    if at is None:
        return None
    if hasattr(at, "amenity"):
        return at
    return next((p for p in places_sim.in_system(game, at)
                 if p.kind == "port"), None)


def barred(game, at) -> str:
    """Why a counter here will not serve the crew, or "": they have to be
    across (`sim/crossing`) — made fast alongside, or over by the boat, a
    shuttle or a line. Asked by every door that takes money."""
    from . import crossing
    place = _where(game, at)
    return crossing.barred(game, place) if place is not None else ""


def open_here(game, at, kind: str = "") -> list:
    """Every door open at this place, best first.

    Gated on four things and nothing else (`data/venue_types.open_to`): how
    much of a place it is, how many people are in it, how advanced it is, and
    whether the law here tolerates it. That last one runs backwards — a chop
    shop and a fence need a *low* law level — which is why a frontier rock
    offers a captain things a Charter arcology will not.
    """
    place = _where(game, at)
    if place is None or not places_sim.livable(place):
        return []
    rows = venue_table.VENUES if not kind else venue_table.BY_KIND.get(kind, ())
    here = [v for v in rows if venue_table.open_to(v, place)]
    return sorted(here, key=lambda v: (-v.cr, v.name))


def selling(game, at, offer: str) -> list:
    """Every door here that sells one particular thing.

    The join between a concourse and the modules that trade through it: the
    clinic asks for `surgery`, the hiring hall for `hire`, the chandler for
    `shelf`, and none of them needs to know the venue tables.
    """
    return [v for v in open_here(game, at) if v.sells(offer)]


def shelves(game, at, category: str = "") -> list:
    """What is on a shelf here, as `(item, price, legal)` rows.

    Sorted by what it costs, because that is the order a captain shops in.
    An illegal thing is still *listed* where somebody carries it — the back
    room and the fence both do — and the desk will still take it off you at
    the gate, so knowing both is the decision.

    **Somebody has to be selling.** A place with nobody on it, or with no
    door that offers `shelf`, answers with an empty counter rather than a
    catalogue; a rocky body with no port was answering with the lot, because
    a profile is a fact about a *world* and a shop is a fact about a *place*.
    """
    place = _where(game, at)
    if place is None or not selling(game, place, "shelf"):
        return []
    # A back room or a fence is what puts contraband on a shelf at all.
    back = bool(selling(game, place, "fence"))
    rows = []
    for item in kit_table.ITEMS:
        if category and item.category != category:
            continue
        if item.cr <= 0:
            continue                       # keepsakes are not for sale
        if not kit_table.stocked_at(item, place.tech):
            continue
        legal = kit_table.legal_at(item, place.law)
        if not legal and not back:
            continue                       # only a back room carries these
        rows.append({"item": item,
                     "cr": kit_table.price_at(item, place.tech),
                     "legal": legal})
    return sorted(rows, key=lambda r: (r["item"].category, r["cr"]))


def owned(game) -> list:
    """What the captain owns, as items."""
    return [kit_table.ITEM_BY_ID[i] for i in getattr(game, "kit", []) or []
            if i in kit_table.ITEM_BY_ID]


def buy(game, at, item_id: str) -> dict:
    """Buy one thing off a shelf here."""
    shut = barred(game, at)
    if shut:
        return {"ok": False, "why": shut}
    row = next((r for r in shelves(game, at) if r["item"].id == item_id),
               None)
    if row is None:
        return {"ok": False, "why": "They do not stock it here."}
    if game.credits < row["cr"]:
        return {"ok": False,
                "why": f"{row['cr']:,} credits, and you have "
                       f"{int(game.credits):,}."}
    game.credits -= row["cr"]
    game.kit = list(getattr(game, "kit", []) or []) + [item_id]
    note = "" if row["legal"] else " The desk would take it off you here."
    game.add_log(f"Bought {row['item'].name} for {row['cr']:,} credits."
                 + note, "" if row["legal"] else "warn")
    return {"ok": True, "why": "", "cr": row["cr"], "item": row["item"]}


def sell(game, at, item_id: str) -> dict:
    """Sell something back. Always below what the same shelf asks."""
    held = list(getattr(game, "kit", []) or [])
    if item_id not in held:
        return {"ok": False, "why": "You do not have one."}
    place = _where(game, at)
    item = kit_table.ITEM_BY_ID.get(item_id)
    if place is None or item is None or not selling(game, place, "shelf"):
        return {"ok": False, "why": "Nobody here is buying."}
    if barred(game, place):
        return {"ok": False, "why": barred(game, place)}
    if item.cr <= 0:
        return {"ok": False, "why": "It is worth nothing to anybody else."}
    paid = max(1, int(kit_table.price_at(item, place.tech) * BUYBACK))
    held.remove(item_id)
    game.kit = held
    game.credits += paid
    game.add_log(f"Sold {item.name} for {paid:,} credits.")
    return {"ok": True, "why": "", "cr": paid, "item": item}


# ── the bank ───────────────────────────────────────────────────────────────

def bank_here(game, at) -> bool:
    """Whether anything here will hold money for you."""
    return bool(selling(game, at, "bank"))


def deposit(game, at, amount: float) -> dict:
    """Put money somewhere that is not the hull.

    **No interest, and that is deliberate.** A bank that paid a captain to
    leave money in it would be the one thing this game refuses to have: a
    counter that makes credits out of nothing. What a deposit buys is that
    the money is not aboard when the hull is boarded, and that it can be
    drawn at any other port that has a counting house.
    """
    if not bank_here(game, at):
        return {"ok": False, "why": "There is nowhere here to bank it."}
    if barred(game, at):
        return {"ok": False, "why": barred(game, at)}
    amount = int(max(0, min(amount, game.credits)))
    if amount <= 0:
        return {"ok": False, "why": "Nothing to deposit."}
    game.credits -= amount
    game.deposited = float(getattr(game, "deposited", 0.0)) + amount
    game.add_log(f"Deposited {amount:,} credits. "
                 f"{int(game.deposited):,} on account.")
    return {"ok": True, "why": "", "cr": amount}


def withdraw(game, at, amount: float) -> dict:
    """Draw on the account, at any port that has a counter."""
    if not bank_here(game, at):
        return {"ok": False, "why": "There is nowhere here to draw on it."}
    if barred(game, at):
        return {"ok": False, "why": barred(game, at)}
    held = float(getattr(game, "deposited", 0.0))
    amount = int(max(0, min(amount, held)))
    if amount <= 0:
        return {"ok": False, "why": "Nothing on account."}
    game.deposited = held - amount
    game.credits += amount
    game.add_log(f"Drew {amount:,} credits. "
                 f"{int(game.deposited):,} left on account.")
    return {"ok": True, "why": "", "cr": amount}


def account_line(game) -> str:
    """What the counter would say if you asked."""
    held = float(getattr(game, "deposited", 0.0))
    if held <= 0:
        return "Nothing on account."
    return (f"{int(held):,} credits on account, drawable at any port with a "
            "counting house.")


# ── a night ashore ─────────────────────────────────────────────────────────

def ashore_cost(game, venue) -> int:
    """What taking the watch to this place would cost, all in."""
    heads = max(1, int(getattr(game.ship, "crew", 1) * ASHORE_SHARE))
    return int((venue.cr + venue_table.ASHORE_OVERHEAD) * heads)


def ashore_note(game, at, venue) -> str:
    """What it would buy, before the captain pays for it."""
    said = [f"{ashore_cost(game, venue):,} credits for the watch"]
    if venue.morale:
        said.append(f"morale +{venue.morale:.0%}")
    if venue.loyalty:
        said.append(f"loyalty +{venue.loyalty:.0f}")
    if venue.standing:
        said.append(f"standing +{venue.standing:.2f}")
    if venue.rumour:
        said.append(f"{venue.rumour:.0%} of hearing something")
    return "  ·  ".join(said)


def ashore(game, at, venue_id: str, rng=None) -> dict:
    """Take the watch ashore. Money out; morale, loyalty and talk back.

    **The draw is the sim's, not the screen's.** A night ashore is an act and
    it is allowed to move the chronicle's luck; a *screen* is not
    (`tests/test_uirules`), so the concourse calls this and this asks the
    game. A check may put its own stream in.
    """
    rng = rng if rng is not None else game.rng("ashore")
    place = _where(game, at)
    venue = venue_table.VENUE_BY_ID.get(venue_id)
    if place is None or venue is None or venue not in open_here(game, place):
        return {"ok": False, "why": "That is not open here."}
    if barred(game, place):
        return {"ok": False, "why": barred(game, place)}
    cost = ashore_cost(game, venue)
    if game.credits < cost:
        return {"ok": False,
                "why": f"{cost:,} credits, and you have "
                       f"{int(game.credits):,}."}
    game.credits -= cost
    ship = game.ship
    ship.morale = min(1.0, ship.morale + venue.morale)
    lifted = []
    if venue.loyalty:
        from . import loyalty as loyalty_sim
        for officer in getattr(game, "officers", []) or []:
            if getattr(officer, "retired", False):
                continue
            loyalty_sim.shift(officer, venue.loyalty)
            lifted.append(officer.name)
    # Standing is with whoever holds the place. A holding of your own has
    # no faction to be pleased with you, so being seen there buys nothing.
    if venue.standing and place.faction:
        game.adjust_rep(place.faction, venue.standing)
    heard = ""
    if venue.rumour and rng.chance(venue.rumour):
        heard = _heard(game, place, rng)
    game.add_log(
        f"The watch ashore at {venue.name.lower()}, {place.name}: "
        f"{cost:,} credits."
        + (f" {heard}" if heard else ""), "good")
    return {"ok": True, "why": "", "cr": cost, "heard": heard,
            "lifted": lifted}


def _heard(game, place, rng) -> str:
    """Something worth hearing, in the concourse's own voice.

    Drawn from what the sector actually is rather than invented: a world
    nearby, a power's mood, or a hull somebody has seen. A rumour that
    pointed at nothing would be worse than no rumour.
    """
    from ..data import uwp
    rows = [s for s in game.galaxy.systems
            if s.id != getattr(place, "system_id", -1) and s.port]
    if not rows:
        return "Nothing worth repeating."
    other = rng.pick(rows[:12])
    world = profile_sim.port_world(other)
    if world is None:
        return f"Somebody has been asking after hulls bound for {other.name}."
    got = profile_sim.profile(game, other, world)
    codes = uwp.codes(got)
    if codes:
        code = rng.pick(list(codes))
        return (f"Word is {other.name} is {uwp.TRADE_NAMES[code].lower()} — "
                + uwp.TRADES.get(code, "worth a look") + ".")
    return f"Word is nobody has put in at {other.name} for a season."
