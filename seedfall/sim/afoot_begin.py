"""Beginning a walk: laying the site out, dressing the party, putting them down.

Split from `sim/afoot.py`, the front door, which re-exports every name here
so callers keep asking it. The seam is the moment the party sets foot on the
deck: everything before it — who can go, what they carry, where they stand,
who else is there — is here, and everything after it is there.

**What a person carries is decided once, here** (`_dress`), and the start
screen asks the same function what it would decide (`preview_kit`), so what
the screen says somebody will carry is what they carry.
"""

from __future__ import annotations

from ..core import ids
from ..core.rng import RNG
from ..data import afoot_arms as arms
from ..data.afoot_derelicts import BOARDING_DAYS
from . import (afoot_cast, afoot_incidents, afoot_map, afoot_people,
               afoot_plans, afoot_sites)
from .afoot_state import Actor, Walk, party, say, uid

#: What a ship keeps for a boarding party that brings nothing of its own:
#: the shotgun, which `data/kit.py` has always called "the boarding weapon,
#: and everybody knows it", and a jack to go under it.
SHIPS_ISSUE_ARMS = ("shotgun", "jack")
SHIPS_ISSUE_SUIT = "vacc_suit"


def can_begin(game, site, keys) -> tuple:
    from .afoot import current, look, pool
    if current(game) is not None:
        return False, "A party is already out."
    if site is None or not site.ok:
        return False, getattr(site, "why", "") or "There is nothing to walk."
    if not keys:
        return False, "Choose who goes."
    if len(keys) > afoot_people.PARTY_MOST:
        return False, f"No more than {afoot_people.PARTY_MOST}."
    ready = {k for k, _n, _w, ok, _why in pool(game) if ok}
    missing = [k for k in keys if k not in ready]
    if missing:
        return False, "Not everybody named can go."
    return True, ""


def begin(game, site_key: str, keys: list, arms_mode: str = "legal") -> dict:
    """Walk a site from where the hull is, with these people."""
    site = afoot_sites.by_key(game, site_key)
    ok, why = can_begin(game, site, keys)
    if not ok:
        return {"ok": False, "why": why}
    laid = afoot_plans.plan(game, site)
    walk = _walk(game, site, laid)
    return _start(game, walk, site, laid, keys, arms_mode)


def begin_prize(game, hull, faction: str, keys: list) -> dict:
    """Board a struck hull, before deciding what to do with her."""
    site = afoot_sites.prize_site(game, hull, faction)
    ok, why = can_begin(game, site, keys)
    if not ok:
        return {"ok": False, "why": why}
    laid = afoot_plans.plan_hull(game, site, hull)
    walk = _walk(game, site, laid)
    walk.prize, walk.prize_faction = hull, faction or ""
    return _start(game, walk, site, laid, keys, "all")


def _walk(game, site, laid) -> Walk:
    return Walk(id=ids.next_id("walk", game), site=site.key, kind=site.kind,
                name=site.name, system_id=game.location_id,
                place_id=site.place_id, faction=site.faction, law=site.law,
                tech=site.tech, decks=laid.decks, rooms=laid.rooms,
                things=laid.things,
                next_uid=max([t.id for t in laid.things]
                             + [r.id for r in laid.rooms] + [0]) + 1)


def airless(site) -> bool:
    """Is there nothing to breathe aboard? A Dry Choir frame, a holed wreck."""
    if site.kind == "wreck":
        from ..data.afoot_derelicts import DERELICT_BY_ID
        return not DERELICT_BY_ID[site.wreck].air
    return site.style == "synthetic"


def preview_kit(game, key: str, site, arms_mode: str = "legal") -> tuple:
    """(weapon, armour, kit) this person would carry to this site — asked
    before a walk begins, so the start screen can say it."""
    from .afoot_state import Deck
    walk = Walk(id=-1, site=site.key, kind=site.kind, name=site.name,
                law=site.law, decks=[Deck("probe", air=not airless(site))])
    who = Actor(id=-1, name="", side="party", folk="captain"
                if key == "captain" else "officer", deck=0, x=0, y=0, hp=1,
                hp_max=1)
    if key.startswith("officer:"):
        who.officer = int(key.split(":")[1])
    elif key.startswith("robot:"):
        who.folk, who.robot = "robot", int(key.split(":")[1])
    _dress(game, walk, who, key, site, arms_mode)
    return who.weapon, who.armour, list(who.kit)


def _start(game, walk, site, laid, keys, arms_mode) -> dict:
    rng = RNG(f"{game.seed}:afoot:cast:{site.key}:{game.day}")
    for deck in walk.decks:
        deck.air = deck.air and not airless(site)
    deck, x, y = laid.entry
    spots = _gather(walk, deck, x, y, len(keys))
    for key, spot in zip(keys, spots):
        enlist(game, walk, key, deck, spot[0], spot[1], site, arms_mode)
    afoot_cast.populate(game, walk, site, rng)
    if walk.prize is not None:
        afoot_cast.prize_cargo(walk)
    afoot_cast.stock(game, walk, site)
    afoot_incidents.draw(game, walk, site, rng)
    walk.selected = party(walk)[0].id
    for who in party(walk):
        who.mp = afoot_people.move_of(game, who)
    if site.kind in ("ship", "holding"):
        # Your own hull and your own ground are known to you: no fog on the
        # plan of a place you own, only on who is standing where.
        from .afoot_deeds import reveal
        for deck in range(len(walk.decks)):
            reveal(walk, deck)
    from .afoot import look
    look(walk)
    game.afoot = walk
    if site.kind in ("wreck", "prize"):
        game.advance_days(BOARDING_DAYS)
    arrive = {"ship": f"{len(keys)} walking the decks of the {site.name}.",
              "prize": f"{len(keys)} across to {site.name}.",
              "wreck": f"{len(keys)} aboard {site.name}."}
    say(walk, arrive.get(site.kind, f"{len(keys)} ashore at {site.name}."),
        "good")
    game.add_log(f"A party goes afoot: {site.name}.", "")
    from . import tutorial_watch
    tutorial_watch.deed(game, "walked")
    return {"ok": True, "walk": walk}


def _gather(walk, deck: int, x: int, y: int, count: int) -> list:
    """Squares near the way in for the party to stand on."""
    probe = Actor(id=-1, name="", side="party", folk="", deck=deck, x=x, y=y,
                  hp=1, hp_max=1)
    free = afoot_map.reach(walk, probe, 6)
    free.pop((x, y), None)
    for t in walk.things:           # nobody starts stood in the airlock
        if t.deck == deck and t.kind in ("airlock", "gangway", "lift"):
            free.pop((t.x, t.y), None)
    order = sorted(free, key=lambda s: (free[s], s))
    return ([(x, y)] + order)[:count]


def enlist(game, walk, key: str, deck: int, x: int, y: int, site,
           arms_mode: str = "legal") -> Actor:
    """Put one of yours on the deck, dressed for where they are going."""
    who = Actor(id=uid(walk), name="", side="party", folk="officer",
                deck=deck, x=x, y=y, hp=1, hp_max=1, mood="friendly")
    if key == "captain":
        who.folk, who.name = "captain", afoot_people.captain_name(game)
    elif key.startswith("officer:"):
        who.officer = int(key.split(":")[1])
        who.name = afoot_people.officer_of(game, who.officer).name
    else:
        who.folk, who.robot = "robot", int(key.split(":")[1])
        robot = next(r for r in game.robots if r.id == who.robot)
        who.name = robot.name
    walk.actors.append(who)
    _dress(game, walk, who, key, site, arms_mode)
    rec = afoot_people.record(game, who)
    who.hp_max = afoot_people.stamina(rec)
    who.zero_g = rec.skill("zero_g")
    wound = float((game.wounds or {}).get(
        "captain" if key == "captain" else str(who.officer), 0) or 0)
    if who.robot >= 0:
        robot = next(r for r in game.robots if r.id == who.robot)
        wound = who.hp_max * (1.0 - robot.condition)
    who.hp = max(1, int(round(who.hp_max - wound)))
    return who


def _dress(game, walk, who, key, site, arms_mode) -> None:
    """What they carry: their own things, and the ship's issue for a boarding.

    `arms_mode` is "legal" (leave behind whatever this law level forbids),
    "all" (carry it anyway, and answer for it) or "none" (go unarmed).
    """
    from ..data import kit as kit_table
    owned = afoot_people.kit_for(game, key)
    if arms_mode != "all":
        owned = [k for k in owned
                 if kit_table.legal_at(kit_table.ITEM_BY_ID[k], site.law)]
    machine = who.robot >= 0
    boarding = site.kind in ("wreck", "prize")
    weapon = "" if arms_mode == "none" else afoot_people.best_weapon(owned)
    if boarding and not weapon and arms_mode != "none" and not machine:
        weapon = SHIPS_ISSUE_ARMS[0]
    needs_seal = (not all(d.air and d.outside_air for d in walk.decks)
                  and afoot_people.breathes(game, who))
    armour = afoot_people.best_armour(owned, needs_seal)
    if needs_seal and not (armour and arms.guard(armour).sealed):
        armour = SHIPS_ISSUE_SUIT
    elif boarding and not armour and not machine:
        armour = SHIPS_ISSUE_ARMS[1]
    useful = [k for k in owned if k not in (weapon, armour) and (
        k in arms.CONSUMABLES or kit_table.ITEM_BY_ID[k].gives)]
    who.weapon, who.armour = weapon, armour
    who.kit = [k for k in (weapon, armour) if k] + useful


def join(game, walk, npc) -> None:
    """One of your own, found at their station, comes along."""
    npc.side, npc.mood, npc.folk = "party", "friendly", "officer"
    site = afoot_sites.Site(key=walk.site, kind=walk.kind, name=walk.name,
                            what="", style="", law=walk.law)
    _dress(game, walk, npc, f"officer:{npc.officer}", site, "legal")
    npc.zero_g = afoot_people.record(game, npc).skill("zero_g")
    npc.mp = afoot_people.move_of(game, npc)


