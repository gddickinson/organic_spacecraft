"""The hunt: a board at the quay, a search you can afford, and what you take.

The other direction from `sim/nemeses`. A rival finding you is weather with a
name; this is the captain choosing the fight. The play-test's armed fighter
completed **no bounty in fifteen career-years**, because a bounty contract
said "destroy two Freehold hulls" and nothing in the game would tell you where
one was. So the board says where, and how old the word is, and a search says
what it will cost and what it will find before you spend a day on it.

Every act here has a quote and the act spends the quote: `search_odds` is
what `search` rolls against, `buy_off_terms` what `buy_off` charges,
`trophy_terms` what `mount_trophy` and `sell_trophy` do. `test_nemeses`
drives each pair through both doors.
"""

from __future__ import annotations

import math

from ..core.rng import RNG
from ..data import countermeasures as cm
from ..data.factions import FACTIONS_BY_ID
from ..world.galaxy import distance
from . import nemeses as nem_sim

#: A board turns over monthly, like the contract board beside it.
TURNOVER = 30

#: How far a quay's board looks for raiders to post, in light years. Raiders
#: never work a system with a port (`piracy.lawlessness`), and across three
#: sectors the nearest raider to a start port sat 27 to 48 ly off — at 25 a
#: new captain's first board posted nothing at all.
RAIDER_REACH = 40.0

#: What a notorious raider is worth, per point of the sector's typical threat
#: — about 7,000 on a typical day-300 board. Tuned by flying a hunter career
#: (three sectors, three years, the opening NAVIS armed as it could afford):
#: at 1,800 its hunting netted +8k, +3k and −3k over the three years; at
#: 3,000 it nets +35k, +5k and +6k — bounties and loot less repairs and the
#: guns it bought — beside an explorer's 25 credits a day.
RAIDER_BOUNTY = 3000.0

#: What a posted raider's hull mends a day. A third of a rival's
#: (`nemeses.MEND`): a raider has no yard, only its own hold and its own hands.
RAIDER_MEND = 0.01

#: What a raider's paper pays, by how the meeting ended: the hull brought in,
#: or the raiding stopped. See `collect`.
DRIVEN_SHARE = 0.5
PAID_ON = {"destroyed": 1.0, "struck": 1.0, "driven-off": DRIVEN_SHARE}

#: A raider collected leaves a slot somebody else fills, after this long.
RESPAWN_DAYS = 120

#: Paper taken off a board lapses after this many days.
PAPER_DAYS = 120

#: How much a day's search sees, per light year of array and per share of
#: the quarry's signature. At a stock NAVIS's 3.6 ly: a lit hull 44% a day,
#: a dark one 15%, a shroud 6%, a cloak 2% — the ladder the sky already draws.
SWEEP = 0.16

#: Longest search the desk will quote.
MOST_DAYS = 10

#: What a mercenary rival costs to retire, per level, before the grudge.
BUY_OFF_PER_LEVEL = 3000.0


def _short(power: str) -> str:
    return getattr(FACTIONS_BY_ID.get(power), "short", power or "Nobody")


# ── the board ──────────────────────────────────────────────────────────────

def board(game, system=None) -> list:
    """What the board at this quay lists: wanted rivals, then raiders."""
    system = system if system is not None else game.system
    if getattr(system, "port", None) is None:
        return []
    held = getattr(game, "hunt", None)
    rows = []
    for nem in nem_sim.roster(game):
        if nem.bounty and nem.status in ("active", "wounded"):
            seen = nem_sim.sighting(game, nem)
            rows.append({"key": f"nemesis:{nem.id}", "kind": "nemesis",
                         "name": nem.name, "reward": nem.bounty["reward"],
                         "issuer": nem.bounty["issuer"],
                         "system_id": seen["system_id"], "where": seen["where"],
                         "age": seen["age"], "conf": seen["conf"],
                         "taken": _held(held, f"nemesis:{nem.id}")})
    rows.extend(_raiders(game, system, held))
    return rows


def _raiders(game, system, held) -> list:
    """Raiders in reach of this quay, where the law says raiders work.

    **Where they work is `piracy`'s, not the board's.** A system posts a raider
    only if `raider_chance` is above nothing there — the chart's own "unmarked
    hulls work systems like this one". The hull is the one `traffic` plotted
    when there is one; when the slots rolled none, it is the one the quay has
    heard of and your array has never held, which is what running dark is.
    Measured on three sectors, traffic alone put **no** raider inside the
    opening pocket of two of them, and a hunter there had nothing to hunt for
    years.

    Reach is by hopping, at your drive: a price behind a wall would be the
    trap the contract board was fixed for (`test_postings`).
    """
    from ..data.lore import HULL_NAMES
    from . import encounters, piracy, reach, traffic
    within = reach.component(game, start=system.id)
    period = game.day // TURNOVER
    rng = RNG(f"{game.seed}:hunts:{system.id}:{period}")
    collected = (held.marks.get("collected", {}) if held is not None else {})
    reward = int(round(RAIDER_BOUNTY * encounters.typical_threat(game), -2))
    if not _can_pay(game, system.port.faction, reward):
        return []
    rows = []
    for other in sorted(game.galaxy.systems, key=lambda s: distance(s, system)):
        if distance(other, system) > RAIDER_REACH:
            break
        if other.id not in within or piracy.raider_chance(game, other) <= 0:
            continue
        hulls = [(h.id, h.name) for h in traffic.in_system(game, other)
                 if h.errand == "raider"]
        if not hulls:
            pool = HULL_NAMES["freeholds"]
            hulls = [(f"{other.id}:posted", pool[other.id % len(pool)])]
        for hull_id, name in hulls:
            since = collected.get(hull_id)
            if since is not None and game.day - int(since) < RESPAWN_DAYS:
                continue
            rows.append({"key": f"raider:{hull_id}", "kind": "raider",
                         "name": name, "reward": reward,
                         "issuer": system.port.faction,
                         "system_id": other.id, "where": other.name, "age": 0,
                         "conf": 1.0, "hull": hull_id,
                         "taken": _held(held, f"raider:{hull_id}")})
    # A board posts a few, not every raider in reach — stably for the month.
    return rng.shuffle(rows)[:3] if len(rows) > 3 else rows


def _can_pay(game, power: str, reward: float) -> bool:
    """A power posts only paper its purse can honour."""
    from . import diplomacy, exchequer
    if power not in diplomacy.POWERS:
        return False
    return exchequer.purse(game, power).credits >= reward


def pay(game, power: str, reward: float) -> float:
    """The price, out of the issuer's purse and into yours — **nothing is
    conjured**. What the purse cannot cover it does not pay."""
    from . import diplomacy, exchequer
    if power not in diplomacy.POWERS:
        return 0.0
    purse = exchequer.purse(game, power)
    paid = max(0.0, min(float(reward), purse.credits))
    purse.credits -= paid
    game.credits += paid
    return paid


def _held(held, key: str) -> bool:
    return held is not None and any(r["key"] == key and not r.get("done")
                                    for r in held.taken)


def taken(game) -> list:
    """Paper you hold that is still good."""
    held = getattr(game, "hunt", None)
    if held is None:
        return []
    return [r for r in held.taken if not r.get("done")
            and game.day <= int(r.get("until", 0))]


def take(game, key: str) -> dict:
    """Take the paper off the board. It comes with a fresh sighting."""
    row = next((r for r in board(game) if r["key"] == key), None)
    if row is None:
        return {"ok": False, "why": "That is not on this board.", "text": ""}
    if row["taken"]:
        return {"ok": False, "why": "You already hold that paper.", "text": ""}
    record = {k: row[k] for k in ("key", "kind", "name", "reward", "issuer",
                                   "system_id")}
    record.update(day=int(game.day), until=int(game.day) + PAPER_DAYS,
                  done=False)
    if row["kind"] == "nemesis":
        nem = nem_sim.by_id(game, int(key.split(":")[1]))
        record["nemesis"] = nem.id
        nem_sim.spot(game, nem, nem.location_id, 0.9)
        record["system_id"] = nem.location_id
    else:
        record["hull"] = row["hull"]
    nem_sim.state(game).taken.append(record)
    where = game.galaxy.systems[record["system_id"]].name
    text = (f"Took {_short(row['issuer'])} paper on {row['name']}: "
            f"{row['reward']:,.0f}, last seen at {where}.")
    game.add_log(text, "")
    return {"ok": True, "why": "", "text": text, "record": record}


# ── the search ─────────────────────────────────────────────────────────────

def _quarry(game, key: str):
    """(record or rival, signature, where it really is) for a key."""
    kind, _sep, ident = key.partition(":")
    if kind == "nemesis":
        nem = nem_sim.by_id(game, int(ident))
        if nem is None:
            return None, cm.LOUD, None
        base = cm.DARK if nem.archetype == "corsair" else cm.LOUD
        if "ghost" in nem.traits:
            base = cm.SHROUDED if base is cm.DARK else cm.DARK
        return nem, base, (nem.location_id if nem.status == "active" else None)
    record = next((r for r in taken(game) if r["key"] == key), None)
    if record is None:
        return None, cm.LOUD, None
    from . import detection
    return record, detection.for_hull("raider", record["hull"]), \
        record["system_id"]


def search_odds(game, key: str, days: int) -> dict:
    """What a search here will cost and find, before a day is spent.

    Two numbers, because they are different questions: `find` is the chance
    of seeing the quarry *if it is here*, which is the array against its
    signature; `here` is what your sighting says about whether it is.
    """
    days = max(1, min(MOST_DAYS, int(days)))
    quarry, hiding, _truth = _quarry(game, key)
    if quarry is None:
        return {"ok": False, "why": "Nothing on your paper by that name.",
                "days": days, "find": 0.0, "here": 0.0, "odds": 0.0,
                "per_day": 0.0, "hiding": hiding.name}
    sensor = float(getattr(game.ship_stats, "sensor", 2.0))
    per_day = 1.0 - math.exp(-SWEEP * sensor * hiding.share)
    find = 1.0 - (1.0 - per_day) ** days
    if key.startswith("nemesis:"):
        seen = nem_sim.sighting(game, quarry)
        here = seen["conf"] if seen["system_id"] == game.location_id else 0.0
    else:
        here = 1.0 if quarry["system_id"] == game.location_id else 0.0
    return {"ok": True, "why": "", "days": days, "per_day": per_day,
            "find": find, "here": here, "odds": here * find,
            "hiding": hiding.name}


def search(game, key: str, days: int, band: int | None = None) -> dict:
    """Spend days looking. Rolls exactly what `search_odds` quoted.

    The quarry lies still while it is looked for (`nemeses._move` skips a
    pinned rival) — a hull that moves is a hull that gets seen — which is
    what makes the quote the act rather than a hope.
    """
    quote = search_odds(game, key, days)
    if not quote["ok"]:
        return {"ok": False, "why": quote["why"], "text": ""}
    quarry, _hiding, truth = _quarry(game, key)
    rng = game.rng("hunt")
    found_on = next((d for d in range(1, quote["days"] + 1)
                     if rng.chance(quote["per_day"])), None)
    here = truth == game.location_id
    spent = found_on if (here and found_on) else quote["days"]
    held = nem_sim.state(game)
    if key.startswith("nemesis:") and here:
        held.marks["pinned"] = quarry.id
    try:
        game.advance_days(spent)
    finally:
        held.marks.pop("pinned", None)
    if not (here and found_on) or game.dead:
        if key.startswith("nemesis:"):
            nem_sim.spot(game, quarry, game.location_id, 0.1)
        text = f"{spent} days of looking at {game.system.name}. Nothing."
        game.add_log(text, "")
        return {"ok": True, "why": "", "found": False, "days": spent,
                "text": text, "encounter": None}
    if key.startswith("nemesis:"):
        from . import rivals
        met = rivals.encounter(game, quarry, found=True, band=band)
    else:
        met = _raider_meeting(game, quarry, band)
    text = f"Found on day {spent}: {met['enemy']['name']}."
    game.add_log(text, "good")
    return {"ok": True, "why": "", "found": True, "days": spent,
            "text": text, "encounter": met}


def _raider_meeting(game, record: dict, band) -> dict:
    """A notorious raider, run to ground. Nobody's register: no colours.

    **The same hull every time you find it**, kept on the paper, as a rival's
    is kept on the rival. Rebuilt fresh at every search, a raider you had
    holed and driven off came back whole the next morning, and a starting
    hull's bounty rate against them was 30% a meeting however many times it
    had beaten the same crew. Kept, the holes stay — mended by `RAIDER_MEND`
    a day, which is slowly: a raider has nowhere to put in.
    """
    from . import encounters, running_dark
    from .ship import stats
    rng = RNG(f"{game.seed}:raider:{record['hull']}:{record['day']}")
    d = encounters.draw_threat(game, rng)
    ship = record.get("ship")
    if ship is None:
        made = encounters.make_enemy(rng, "freeholds", d)
        ship = made["ship"]
        ship.name = record["name"]
        record["ship"], record["seen"] = ship, int(game.day)
    for layer in ship.layers:
        layer.hp = min(layer.max, layer.hp + layer.max * RAIDER_MEND
                       * max(0, game.day - record.get("seen", game.day)))
    record["seen"], record["uid"] = int(game.day), ship.uid
    enemy = {"ship": ship, "stats": stats(ship, {}), "faction": None,
             "name": f"Unregistered raider «{record['name']}»",
             "personality": "balanced",
             "resolve": encounters.RESOLVE_BASE + d * encounters.RESOLVE_PER_SCALE,
             "loot": {"credits": round(1300 * (1 + d * 0.6)),
                      "research": round(13 * (1 + d * 0.4))}}
    return {"enemy": enemy, "no_parley": False, "band": band,
            "first_volley": "player" if running_dark.dark(game) else None,
            "intro": f"You have found the {record['name']}. No colours, "
                     "no transponder, and a price on the hull."}


def collect(game, battle) -> dict | None:
    """A raider on your paper, dealt with. Called from `rival_ends.settle`.

    **The paper is for the lane as well as the hull.** Destroyed or struck,
    the hull is brought in and the whole price is paid. Driven off, the
    raider is gone from the system it worked — the slot stands empty for
    `RESPAWN_DAYS` — and the power pays `DRIVEN_SHARE` of it, because what
    it wanted was the raiding stopped. Measured before this: a hunter's
    raiders broke off in 20 of 27 meetings, each one paid nothing, and a
    three-year hunting career netted −16 credits a day.

    A rival's own price is paid in `rival_ends`, and only for a dead one:
    a rival who breaks off comes back.
    """
    share = PAID_ON.get(battle.result)
    if share is None:
        return None
    uid = getattr(battle.enemy.ship, "uid", None)
    record = next((r for r in taken(game) if r.get("uid") == uid
                   and r["kind"] == "raider"), None)
    if record is None:
        return None
    record["done"] = True
    record["ship"] = None                  # gone from the lanes either way
    paid = pay(game, record["issuer"], record["reward"] * share)
    from . import rivals
    game.adjust_rep(record["issuer"], rivals.BOUNTY_STANDING * share)
    held = nem_sim.state(game)
    held.marks.setdefault("collected", {})[record["hull"]] = int(game.day)
    game.add_log(f"{_short(record['issuer'])} pays "
                 + ("the price" if share >= 1 else "for the lane cleared")
                 + f" on the {record['name']}: {paid:,.0f}.", "good")
    return {"reward": paid, "issuer": record["issuer"]}


# ── ending it with money ──────────────────────────────────────────────────

def buy_off_terms(game, nid: int) -> dict:
    nem = nem_sim.by_id(game, nid)
    if nem is None or nem.status not in ("active", "wounded"):
        return {"ok": False, "why": "Nobody to pay.", "price": 0}
    if not nem_sim.archetype(nem).buy_off:
        return {"ok": False, "why": f"{nem.name} is not for sale.", "price": 0}
    price = int(round(BUY_OFF_PER_LEVEL * nem.level
                      * (1.0 + nem.grudge.get("theirs", 0) / 100.0), -2))
    if game.credits < price:
        return {"ok": False, "why": f"The fee is {price:,}.", "price": price}
    return {"ok": True, "why": "", "price": price}


def buy_off(game, nid: int) -> dict:
    """A better fee than the cartel's. They take it and go."""
    terms = buy_off_terms(game, nid)
    if not terms["ok"]:
        return {"ok": False, "why": terms["why"], "text": ""}
    nem = nem_sim.by_id(game, nid)
    game.credits -= terms["price"]
    nem.status = "retired"
    nem.history.append([int(game.day), game.location_id, "parley",
                        "you paid them off"])
    text = f"{nem.name} takes {terms['price']:,} and leaves the lanes."
    game.add_log(text, "good")
    return {"ok": True, "why": "", "text": text}


# ── trophies ───────────────────────────────────────────────────────────────

def trophy_terms(game, tid: str) -> dict:
    """What fitting a trophy would take off, and what a yard would give."""
    from ..data.parts import part, part_value
    from . import shipyard
    held = getattr(game, "hunt", None)
    record = next((r for r in (held.trophies if held else ())
                   if r["id"] == tid and r["state"] == "held"), None)
    made = part(tid) if record else None
    if made is None:
        return {"ok": False, "why": "No such trophy in the hold.",
                "worth": 0, "replaces": None, "name": ""}
    # What a breaker pays for anything (`shipyard.SCRAP_SHARE`): a trophy is
    # a used gun with a story, and the yard does not buy stories.
    worth = int(round(part_value(made) * shipyard.SCRAP_SHARE, -1))
    ship = game.ship
    guns = sorted((pid for pid in ship.fitted
                   if part(pid) and part(pid).slot == made.slot),
                  key=lambda pid: part(pid).wpn.dmg if part(pid).wpn else 0)
    room = ship.chassis_def.slots.get(made.slot, 0) > len(guns)
    off = None if room or not guns else guns[0]
    fitted = [p for p in ship.fitted if p != off] + [tid]
    ok, errors, _brown = shipyard.validate(ship.chassis_def, fitted)
    return {"ok": ok, "why": "; ".join(errors), "worth": worth,
            "replaces": part(off).name if off else None, "off": off,
            "name": made.name, "sellable": game.system.port is not None}


def mount_trophy(game, tid: str) -> dict:
    terms = trophy_terms(game, tid)
    if not terms["ok"]:
        return {"ok": False, "why": terms["why"] or "It will not fit.",
                "text": ""}
    ship = game.ship
    ship.fitted = [p for p in ship.fitted if p != terms["off"]] + [tid]
    _mark(game, tid, "mounted")
    game.recompute()
    text = (f"{terms['name']} is fitted"
            + (f" in place of the {terms['replaces']}." if terms["replaces"]
               else "."))
    game.add_log(text, "good")
    return {"ok": True, "why": "", "text": text}


def sell_trophy(game, tid: str) -> dict:
    terms = trophy_terms(game, tid)
    if not terms["name"]:
        return {"ok": False, "why": terms["why"], "text": ""}
    if not terms["sellable"]:
        return {"ok": False, "why": "No yard here to sell it to.", "text": ""}
    game.credits += terms["worth"]
    _mark(game, tid, "sold")
    text = f"Sold {terms['name']} for {terms['worth']:,}."
    game.add_log(text, "good")
    return {"ok": True, "why": "", "text": text}


def _mark(game, tid: str, how: str) -> None:
    for record in nem_sim.state(game).trophies:
        if record["id"] == tid:
            record["state"] = how
