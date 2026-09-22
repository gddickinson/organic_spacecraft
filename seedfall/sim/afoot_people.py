"""Who can walk, what their numbers are, and what they have about them.

Everybody on a deck answers two questions through here: **what is their
record** (six scores and some skills, `lifepath.Record`'s shape) and **what
are they carrying**. The answers come from where they already come from —

- an **officer** is `lifepath.of(game, officer)`, read afresh on every roll,
  so a cortex link fitted in a clinic mid-walk counts on the next throw; they
  carry what `person.of` says they own;
- **the captain** has never had a record, because the captain was never a
  person the game could see. They get one here, derived from the seed and
  the opening choices and stored nowhere, like everybody else's: an origin
  is a career, and a stock is a lineage. They carry the captain's own kit
  (`game.kit`), which is everything the concourse ever sold them;
- a **machine** is its class: its level in its duty, and a body that is
  strong, steady and slow;
- anybody else keeps their numbers on their `Actor`, dealt from their
  archetype when they were put on the deck.

**Stamina** is Traveller's: strength, dexterity and endurance together. At
nothing somebody is down; at minus their endurance they are dead.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data import afoot_arms as arms
from ..data import kit as kit_table
from ..data.lineages import LINEAGES_BY_ID, of_stock
from ..data.lore import CREW_LAST
from ..data.robots import ROBOTS_BY_ID
from . import checks, lifepath, lifespan

#: What each origin taught the captain, as Traveller skills, and which two
#: scores it leaned on. Every origin also commands: Leadership 1, Pilot 1.
ORIGIN_SKILLS = {
    "surveyor": ({"sciences": 2, "survival": 1, "recon": 1}, ("int", "edu")),
    "journeyman": ({"mechanic": 2, "engineer": 1, "vacc_suit": 1},
                   ("dex", "int")),
    "grafter": ({"broker": 2, "streetwise": 1, "persuade": 1},
                ("soc", "end")),
    "cantor": ({"computers": 2, "sciences": 1, "xenology": 1},
               ("int", "edu")),
    "survivor": ({"survival": 2, "gun_combat": 1, "medic": 1},
                 ("end", "str")),
    "fugitive": ({"stealth": 2, "deception": 1, "gun_combat": 1},
                 ("dex", "int")),
}
COMMAND = {"leadership": 1, "pilot": 1, "gun_combat": 0}

#: Machines that can walk a deck: anything aboard, working, and light enough
#: to go through a door. A three-tonne stevedore frame can; a rig cannot.
WALKING_TONNES = 4.0

#: The most people in a party. Four is a fire team, and more than four is a
#: crowd that fills a corridor.
PARTY_MOST = 4


class Sheet(lifepath.Record):
    """A record for somebody who has no service history: scores and skills."""


def captain_record(game) -> lifepath.Record:
    """The captain, as a person: stable for the chronicle, stored nowhere."""
    rng = RNG(f"{game.seed}:captain")
    begun = getattr(game, "beginning", None)
    origin = getattr(begun, "origin", "surveyor") or "surveyor"
    taught, leans = ORIGIN_SKILLS.get(origin, ORIGIN_SKILLS["surveyor"])
    scores = {c: rng.int(1, 6) + rng.int(1, 6) for c in checks.CHARACTERISTIC_IDS}
    for cid in leans:
        scores[cid] = min(15, scores[cid] + 2)
    scores["soc"] = min(15, scores["soc"] + 1)     # they own a starship
    skills = dict(COMMAND)
    for name, level in taught.items():
        skills[name] = max(skills.get(name, -1), level)
    return Sheet(name=captain_name(game), station="captain",
                 characteristics=scores, skills=skills)


def captain_name(game) -> str:
    rng = RNG(f"{game.seed}:captain:name")
    return f"Captain {rng.pick(CREW_LAST)}"


def captain_lineage(game):
    begun = getattr(game, "beginning", None)
    return LINEAGES_BY_ID.get(of_stock(getattr(begun, "stock", None)))


def robot_record(robot) -> lifepath.Record:
    """A machine as a sheet: its level in its duty, and a steady body."""
    klass = ROBOTS_BY_ID.get(getattr(robot, "class_id", ""))
    level = int(getattr(klass, "level", 1) or 1)
    duty = {"repair": "mechanic", "cargo": "athletics", "works": "mechanic",
            "mine": "mechanic", "survey": "sciences", "ground": "survival"}
    skills = {"athletics": 1}
    for d in getattr(klass, "duties", ()) or ():
        skills[duty.get(d, "mechanic")] = max(1, level - 1)
    if getattr(klass, "stat", "") in ("tactical", "weapons"):
        skills["gun_combat"] = max(1, level - 1)
    return Sheet(name=getattr(robot, "name", "machine"), station="machine",
                 characteristics={"str": 9 + level, "dex": 5 + level,
                                  "end": 10 + level, "int": 3 + level,
                                  "edu": 3, "soc": 0},
                 skills=skills)


def record(game, actor) -> lifepath.Record:
    """This actor's scores and skills, from wherever they really come from."""
    if actor.folk == "captain":
        return captain_record(game)
    if actor.officer >= 0:
        officer = officer_of(game, actor.officer)
        if officer is not None:
            return lifepath.of(game, officer)
    if actor.robot >= 0:
        robot = next((r for r in getattr(game, "robots", []) or []
                      if r.id == actor.robot), None)
        if robot is not None:
            return robot_record(robot)
    return Sheet(name=actor.name, characteristics=dict(actor.stats),
                 skills=dict(actor.skills))


def officer_of(game, officer_id: int):
    return next((o for o in getattr(game, "officers", []) or []
                 if o.id == officer_id), None)


def stamina(rec) -> int:
    """Strength, dexterity and endurance together."""
    return max(3, rec.score("str") + rec.score("dex") + rec.score("end"))


def breathes(game, actor) -> bool:
    """Does this body need air? A recording, a frame and a mind do not."""
    if actor.robot >= 0 or actor.folk in ("sentry", "frame"):
        return False
    if actor.folk == "captain":
        lineage = captain_lineage(game)
        return getattr(lineage, "breathes", True)
    if actor.officer >= 0:
        officer = officer_of(game, actor.officer)
        if officer is not None:
            return getattr(lifespan.lineage_of(officer, game), "breathes", True)
    return actor.folk not in ("thrall", "creeper")


def carried(actor) -> float:
    """Kilograms on their person."""
    return sum(kit_table.ITEM_BY_ID[i].mass for i in actor.kit
               if i in kit_table.ITEM_BY_ID
               and kit_table.ITEM_BY_ID[i].mass <= kit_table.CARRIED)


def move_of(game, actor) -> int:
    """Squares a round: six, bent by quickness, armour, load and wounds."""
    rec = record(game, actor)
    squares = arms.BASE_MOVE + checks.modifier(rec.score("dex"))
    worn = arms.guard(actor.armour)
    if worn is not None:
        squares -= worn.slow
    if carried(actor) > kit_table.CARRIED:
        squares -= arms.LOADED
    if actor.hp_max and actor.hp * 2 < actor.hp_max:
        squares -= 2
    if actor.stance == "sneak" or actor.carrying >= 0:
        squares = squares // 2
    return max(arms.LEAST_MOVE, squares)


# ── the party ──────────────────────────────────────────────────────────────

def pool(game) -> list:
    """Everybody who could walk: `(key, name, what, ok, why)` each.

    The key is `captain`, `officer:<id>` or `robot:<id>`.
    """
    rows = [("captain", captain_name(game), "In command.", True, "")]
    wounds = getattr(game, "wounds", {}) or {}
    asleep = _asleep(game)
    for officer in lifespan.active(getattr(game, "officers", []) or []):
        ok, why = True, ""
        if officer.id in asleep:
            ok, why = False, "Under, in the long sleep."
        elif float(wounds.get(str(officer.id), 0)) * 2 >= stamina(
                lifepath.of(game, officer)):
            ok, why = False, "Still mending from the last time."
        rows.append((f"officer:{officer.id}", officer.name,
                     officer.role_name, ok, why))
    for robot in getattr(game, "robots", []) or []:
        klass = ROBOTS_BY_ID.get(robot.class_id)
        if klass is None or (robot.posting or "") != "aboard":
            continue
        ok, why = True, ""
        if robot.broken:
            ok, why = False, "Broken down; it needs a yard."
        elif klass.mass_t > WALKING_TONNES:
            ok, why = False, f"{klass.mass_t:g} t will not go through a door."
        rows.append((f"robot:{robot.id}", robot.name, klass.name, ok, why))
    return rows


def _asleep(game) -> set:
    """Officers under in the long sleep (`sim/dormancy.py`)."""
    from . import dormancy
    sleep = dormancy.current(game)
    return {int(i) for i in (getattr(sleep, "officers", None) or [])}


def kit_for(game, key: str) -> list:
    """What this person has to bring: kit ids light enough to carry."""
    if key == "captain":
        ids = list(getattr(game, "kit", []) or [])
    elif key.startswith("officer:"):
        from . import person
        officer = officer_of(game, int(key.split(":")[1]))
        ids = list(person.of(game, officer).kit) if officer else []
    else:
        ids = []
    return [i for i in ids if i in kit_table.ITEM_BY_ID
            and kit_table.ITEM_BY_ID[i].mass <= kit_table.CARRIED]


def best_weapon(kit: list, law: int | None = None) -> str:
    """The most damaging weapon carried — legal here, if a law is given."""
    rows = [i for i in kit if i in arms.ARM_BY_ID and i]
    if law is not None:
        rows = [i for i in rows
                if kit_table.legal_at(kit_table.ITEM_BY_ID[i], law)]
    if not rows:
        return ""
    return max(rows, key=lambda i: (arms.ARM_BY_ID[i].dice * 3.5
                                    + arms.ARM_BY_ID[i].plus,
                                    kit_table.ITEM_BY_ID[i].bonus))


def best_armour(kit: list, need_seal: bool = False) -> str:
    """The best protection carried — a sealed suit first when there is no air."""
    rows = [i for i in kit if i in arms.GUARD_BY_ID]
    if need_seal:
        sealed = [i for i in rows if arms.GUARD_BY_ID[i].sealed]
        if sealed:
            return max(sealed, key=lambda i: arms.GUARD_BY_ID[i].protect)
    if not rows:
        return ""
    return max(rows, key=lambda i: (arms.GUARD_BY_ID[i].protect,
                                    -arms.GUARD_BY_ID[i].slow))
