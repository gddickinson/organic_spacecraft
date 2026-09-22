"""Who is there when you arrive, and what is in the lockers.

A plan is walls and furniture; this puts people on it and things in it, and
both follow from what the site already is:

- **staff** stand behind their counters: a keeper in a chandlery, a
  clinician in a clinic, a clerk at the bank, an agent at a hiring hall, the
  harbourmaster in the harbour office (`data/afoot_rooms.py`);
- **crowds** wander the rooms, as many as the place's population digit and
  amenity say;
- **constables** walk the corridors, as many as the law level puts there,
  and a low law level puts somebody else in the back rooms instead;
- **your own hull** has your officers at their stations and your hands about
  the decks, and **your holding** has your own people working it;
- a **wreck** has whoever its end left aboard (`data/afoot_derelicts.py`);
- a **struck prize** has her surrendered crew in the berths, her master on
  the bridge, and whoever will not accept it yet.

Everything is dealt from the `rng` handed in — the walk's own, seeded from
the site — so nothing here moves the chronicle's luck.

**Lockers are restocked by the season.** What is in a container is seeded on
the site, the container and the quarter (`game.day // RESTOCK`), and a
container emptied is remembered in `game.walked` for that quarter. A wreck
never restocks. Your own hull and your own holdings hold nothing to take:
what is yours is already on the books.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data import afoot_derelicts as wrecks
from ..data import kit as kit_table
from ..data.afoot_folk import FOLK_BY_ID
from ..data.afoot_rooms import LOOT, ROOM_BY_ID, VENUE_STAFF
from ..data.commodities import BY_ID as COMMODITIES
from . import afoot_furnish, afoot_map, afoot_people
from .afoot_state import GROUND, HALL, Actor, uid

#: Days a looted locker stays empty at a place where people live.
RESTOCK = 90
#: Squares of a room's floor each of a crowd needs: a small room is not
#: packed wall to wall.
FLOOR_EACH = 6

#: What each role aboard your own hull stands its watch in.
STATIONS = {"science": ("lab", "sensors", "bridge"),
            "nav": ("bridge",), "engineer": ("engineering", "drive", "power"),
            "medic": ("clinic", "quarters"), "comms": ("bridge", "core"),
            "tactical": ("weapons", "bridge")}

#: Containers, and how often a try at one finds anything.
CONTAINERS = ("locker", "crate", "strongbox", "desk", "bench", "body")
FIND = 0.45


def folk(walk, rng, folk_id: str, deck: int, x: int, y: int, room: int = -1,
         mood: str = "", faction: str = "", name: str = "") -> Actor:
    """Put one archetype on the deck, its scores dealt from its template."""
    spec = FOLK_BY_ID[folk_id]
    stats = {cid: max(1, min(15, base + rng.int(-1, 1)))
             for cid, base in zip(("str", "dex", "end", "int", "edu", "soc"),
                                  spec.stats)}
    hp = max(3, stats["str"] + stats["dex"] + stats["end"])
    who = Actor(id=uid(walk), name=name or spec.name, side="npc", folk=folk_id,
                deck=deck, x=x, y=y, hp=hp, hp_max=hp,
                mood=mood or spec.mood, weapon=spec.weapon,
                armour=spec.armour, stats=stats, skills=dict(spec.skills),
                faction=faction, post=[deck, x, y], room=room)
    walk.actors.append(who)
    return who


def free_spot(walk, deck: int, room=None, rng=None, near=None) -> tuple:
    """An empty square in a room (or anywhere on the deck), or None."""
    g = afoot_map.ground(walk, deck)
    taken = {(a.x, a.y) for a in walk.actors if a.deck == deck}
    if room is not None:
        cells = room.cells()
    else:
        cells = [(x, y) for y in range(g.deck.h) for x in range(g.deck.w)
                 if g.deck.at(x, y) in (HALL, GROUND)]
    ways = {(t.x, t.y) for t in walk.things if t.deck == deck
            and t.kind in ("lift", "airlock", "gangway")}
    cells = [c for c in cells if g.passable(*c) and c not in taken
             and c not in ways]
    # Nobody is put down in a doorway, where they would stand in the way.
    def at(x):                  # round a ring's seam
        return x % g.wide if g.wide else x
    by_door = {(at(t.x + dx), t.y + dy) for t in walk.things
               if t.deck == deck and t.kind in ("door", "hatch")
               for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    cells = [c for c in cells if c not in by_door] or cells
    # Nobody is put where nobody could step up beside them: a person boxed
    # in by furniture cannot be talked to, served or helped.
    cells = [c for c in cells if sum(
        1 for dx, dy in afoot_map.STEPS if g.passable(c[0] + dx, c[1] + dy)
        and (at(c[0] + dx), c[1] + dy) not in taken) >= 2] or cells
    if near is not None:
        wide = afoot_map.span(walk, deck)
        cells.sort(key=lambda c: afoot_map.distance(*c, *near, wide))
        return cells[0] if cells else None
    return rng.pick(cells) if cells else None


def _staff_spot(walk, room, rng):
    """Where somebody who works here stands: their post, or the nearest
    free square to it when a colleague is already standing there."""
    spot = afoot_furnish.post(walk, room)
    taken = {(a.x, a.y) for a in walk.actors if a.deck == room.deck}
    if spot is not None and spot not in taken:
        return spot
    return free_spot(walk, room.deck, room, rng, near=spot)


def populate(game, walk, site, rng) -> None:
    """Everybody who is here, by kind of site."""
    if site.kind == "ship":
        _own_hull(game, walk, rng)
    elif site.kind == "prize":
        _prize(game, walk, site, rng)
    elif site.kind == "wreck":
        _wreck(walk, site, rng, cleared=bool(
            (getattr(game, "walked", {}) or {}).get(site.key, {})
            .get("cleared")))
    else:
        _place(game, walk, site, rng)


def _place(game, walk, site, rng) -> None:
    own = site.kind == "holding" or site.mine
    mood = "friendly" if own else ""
    for room in walk.rooms:
        kind = ROOM_BY_ID[room.kind]
        staff = VENUE_STAFF.get(room.venue, kind.staff)
        for folk_id in staff:
            spot = _staff_spot(walk, room, rng)
            if spot is not None:
                folk(walk, rng, folk_id, room.deck, *spot, room=room.id,
                     mood=mood, faction=site.faction)
        crowd = kind.crowd if not own or kind.crowd == "worker" else ""
        if not crowd:
            continue
        most = min(kind.crowd_most, 1 + site.amenity + (site.heads > 10_000),
                   len(room.cells()) // FLOOR_EACH)
        for _n in range(rng.int(0, most)):
            spot = free_spot(walk, room.deck, room, rng)
            if spot is not None:
                folk(walk, rng, crowd, room.deck, *spot, room=room.id,
                     mood=mood, faction=site.faction)
    _watch(walk, site, rng)


def _watch(walk, site, rng) -> None:
    """Constables, as many as the law level puts on the corridors — and
    where the law is thin, somebody who is glad of it."""
    law = site.law
    count = 0 if site.kind in ("holding", "kith") else min(4, law // 3)
    for _n in range(count):
        deck = rng.int(0, len(walk.decks) - 1)
        spot = free_spot(walk, deck, rng=rng)
        if spot is not None:
            folk(walk, rng, "constable", deck, *spot, faction=site.faction)
    if law <= 3 and site.kind in ("port", "habitat", "downside", "station",
                                  "base"):
        for folk_id in ("pickpocket", "thug")[: 1 + (law <= 1)]:
            deck = rng.int(0, len(walk.decks) - 1)
            spot = free_spot(walk, deck, rng=rng)
            if spot is not None:
                folk(walk, rng, folk_id, deck, *spot, faction="")


def _own_hull(game, walk, rng) -> None:
    """Your officers at their stations; your hands about the decks."""
    walking = {a.officer for a in walk.actors if a.side == "party"}
    from . import lifespan
    for officer in lifespan.active(game.officers):
        if officer.id in walking:
            continue
        room = _station(walk, officer.role)
        spot = (_staff_spot(walk, room, rng) if room is not None
                else free_spot(walk, 0, None, rng))
        if spot is None:
            continue
        rec = afoot_people.record(game, _probe(officer))
        most = afoot_people.stamina(rec)
        # At their station with whatever the last walk left them carrying,
        # so one who joins the party joins it hurt.
        wound = float((game.wounds or {}).get(str(officer.id), 0) or 0)
        hp = max(1, int(round(most - wound)))
        walk.actors.append(Actor(
            id=uid(walk), name=officer.name, side="npc", folk="officer",
            deck=room.deck if room else 0, x=spot[0], y=spot[1], hp=hp,
            hp_max=most, officer=officer.id, mood="friendly",
            post=[room.deck if room else 0, spot[0], spot[1]],
            room=room.id if room else -1))
    hands = max(0, min(4, int(game.ship.crew) // 12))
    for _n in range(hands):
        deck = rng.int(0, len(walk.decks) - 1)
        spot = free_spot(walk, deck, rng=rng)
        if spot is not None:
            folk(walk, rng, "hand", deck, *spot, mood="friendly")


def _probe(officer) -> Actor:
    return Actor(id=-1, name=officer.name, side="npc", folk="officer",
                 deck=0, x=0, y=0, hp=1, hp_max=1, officer=officer.id)


def _station(walk, role: str):
    for kind in STATIONS.get(role, ("bridge",)):
        room = next((r for r in walk.rooms if r.kind == kind), None)
        if room is not None:
            return room
    return next((r for r in walk.rooms if r.kind == "bridge"), None)


def _prize(game, walk, site, rng) -> None:
    """Her crew: most of them struck, one or two who have not."""
    hull = walk.prize
    aboard = max(1, min(8, int(getattr(hull, "crew", 4) or 4)))
    holdouts = min(aboard - 1, rng.int(0, 2) + (aboard >= 6))
    bridge = _tagged(walk, "bridge")
    master_room = _tagged(walk, "cabin") or bridge
    if master_room is not None:
        spot = free_spot(walk, master_room.deck, master_room, rng)
        if spot is not None:
            folk(walk, rng, "prisoner", master_room.deck, *spot,
                 room=master_room.id, faction=site.faction,
                 name=f"Master of the {hull.name}").note = "master"
    berths = [r for r in walk.rooms if r.kind in ("quarters", "bridge")]
    guarded = [r for r in walk.rooms if r.kind in ("hold", "weapons",
                                                   "engineering", "drive")]
    for n in range(aboard - 1):
        hostile = n < holdouts
        room = rng.pick((guarded if hostile and guarded else berths)
                        or walk.rooms)
        spot = free_spot(walk, room.deck, room, rng)
        if spot is not None:
            folk(walk, rng, "holdout" if hostile else "prisoner", room.deck,
                 *spot, room=room.id, faction=site.faction)


def _wreck(walk, site, rng, cleared: bool = False) -> None:
    """Whoever the wreck's end left aboard — unless a party has already
    been through and put them down: a dead hull does not refill."""
    kind = wrecks.DERELICT_BY_ID[site.wreck]
    for folk_id, least, most in () if cleared else kind.cast:
        for _n in range(rng.int(least, most)):
            room = rng.pick(walk.rooms)
            if folk_id == "creeper":
                room = _tagged(walk, "nest") or room
            spot = free_spot(walk, room.deck, room, rng)
            if spot is not None:
                folk(walk, rng, folk_id, room.deck, *spot, room=room.id)


def _tagged(walk, tag: str):
    kinds = {"bridge": ("bridge", "core"), "cabin": ("cabin",),
             "nest": ("nest",), "hold": ("hold",)}
    return next((r for r in walk.rooms if r.kind in kinds.get(tag, (tag,))),
                None)


# ── what is in the lockers ─────────────────────────────────────────────────

def epoch(game, kind: str) -> int:
    """Which season's stock a site's lockers hold. A wreck has only one."""
    return 0 if kind in ("wreck", "prize") else int(game.day) // RESTOCK


def stock(game, walk, site) -> None:
    """Fill every container, less anything already taken this season. Not
    on your own hull or your own ground: what is in your own people's
    lockers is theirs, and there is nothing of yours to find in them."""
    if site.kind in ("ship", "holding") or site.mine:
        return
    season = epoch(game, site.kind)
    marks = (getattr(game, "walked", {}) or {}).get(site.key, {})
    taken = set(marks.get(str(season), []))
    spent = marks.get(f"{season}:spent", {})
    for t in walk.things:
        if str(t.id) in spent:
            t.state = spent[str(t.id)]
    burned = {t.deck for t in walk.things if t.kind == "spore_node"
              and t.state == "done"}
    walk.things[:] = [t for t in walk.things
                      if not (t.kind == "spores" and t.deck in burned)]
    rich = 1.0
    if site.kind == "wreck":
        rich = wrecks.DERELICT_BY_ID[site.wreck].loot
    for t in walk.things:
        if t.id in taken:
            if t.kind in CONTAINERS:
                t.state = "searched"
            continue
        room = next((r for r in walk.rooms if r.id == t.room), None)
        kind = ROOM_BY_ID[room.kind] if room is not None else None
        rng = RNG(f"{game.seed}:loot:{site.key}:{season}:{t.id}")
        if t.kind in CONTAINERS and kind is not None and kind.loot in LOOT:
            t.holds = _items(rng, LOOT[kind.loot], site, rich)
            if t.kind == "strongbox":
                t.state, t.lock = "locked", 3
            elif t.kind == "locker" and rng.chance(0.4):
                t.state, t.lock = "locked", rng.int(1, 2)
        elif t.kind == "cargo" and site.kind == "wreck":
            t.holds = _salvage(rng)
        elif t.kind == "relic":
            t.holds = [f"study:{rng.int(18, 40)}"]
        elif t.kind in ("console", "bench") and site.kind == "wreck":
            t.holds = [f"evidence:{rng.pick(('survey', 'specimen'))}:"
                       f"{rng.int(6, 16)}"]


def _items(rng, table: tuple, site, rich: float) -> list:
    """What a container holds: a try or two at the categories it keeps."""
    categories, tries = table
    out = []
    for _n in range(tries):
        if not rng.chance(min(0.9, FIND * rich)):
            continue
        pool = [i for i in kit_table.ITEMS if i.category in categories
                and kit_table.stocked_at(i, max(site.tech, 7))
                and 0 < i.cr <= 8_000 * rich]
        if pool:
            # Cheaper things are commoner: weight by the inverse of price.
            got = rng.weighted([(1.0 / max(20, i.cr) ** 0.5, i) for i in pool])
            out.append(got.id)
    return out


#: What a dead hull's hold was carrying when she died: ordinary freight.
#: Nothing licensed, nothing alien — those were the first things taken.
SALVAGE = ("ore", "volatiles", "biomass", "alloy", "spidroin", "silicon",
           "trehalose")


def _salvage(rng) -> list:
    """What is left in a dead hull's hold: a few tonnes of something."""
    got = rng.pick([c for c in SALVAGE if c in COMMODITIES])
    return [f"cargo:{got}:{rng.int(2, 9)}"]


def prize_cargo(walk) -> None:
    """Share a struck hull's real cargo out among the cargo in her hold."""
    hull = walk.prize
    stacks = [t for t in walk.things if t.kind == "cargo"]
    goods = [(cid, t) for cid, t in (getattr(hull, "cargo", {}) or {}).items()
             if t > 0.5]
    for stack in stacks:
        stack.holds = []
    for n, (cid, tonnes) in enumerate(goods):
        if stacks:
            stacks[n % len(stacks)].holds.append(f"cargo:{cid}:{tonnes:.1f}")
