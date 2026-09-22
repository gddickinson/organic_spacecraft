"""How a walk ends, and what it leaves on the chronicle.

Three ways out, one close:

- **leave** — everybody still standing gets to the way out, carrying whoever
  is not. What was found comes too;
- **wiped** — nobody in the party is standing. On a site where people live,
  the locals carry you out, and you lose what you were carrying out of it;
  on a dead hull or a struck prize the ship's own boat comes, and whoever
  was left lying where the party fell is left there for good;
- **gave up** — the watch has you, and you went quietly.

`close` banks everything through the doors that already account for it, and
nothing else:

- kit into the captain's own possessions (`game.kit`), where the concourse
  can buy it back — **no credit is ever found on a deck**;
- cargo into the hold, as far as the hold has room (`ship.add_cargo`);
- evidence onto the bench (`inquiry.add`), relic study onto the xenology
  desk (`xeno.add_study`);
- a crime somebody saw becomes a charge (`dockets.allege`);
- a nest burned out is the captain fighting the Bloom (`responses.provoke`);
- wounds are kept (`game.wounds`), a death is a death (`officer.retired`),
  and the walk's own time is spent through `advance_days`.
"""

from __future__ import annotations

from ..data import kit as kit_table
from ..data.offences import LAWFUL
from . import afoot_cast, afoot_incidents, afoot_people, loyalty
from .afoot_state import party, say

#: What a nest burned out aboard a dead hull is worth against the Bloom, as
#: a share of burning back a system, and in Charter standing.
NEST_BURN = 0.2
NEST_STANDING = 2.0
#: How sure a power is of what its own people saw with their own eyes.
SEEN = 0.9
#: How many past walks the chronicle remembers, for the codex and renown.
HISTORY = 40
#: Days a wiped party spends recovering, carried out or brought home.
CARRIED_DAYS = 2.0
#: A night in the cells, for going quietly.
DETAINED_DAYS = 1.0
#: Sites where somebody lives who would find a body in a corridor and carry
#: it somewhere. On anything else — a dead hull, a struck prize — whoever is
#: left lying there stays there.
LIVING = ("port", "habitat", "downside", "holding", "ship", "kith",
          "station", "base")


def leave(game, walk) -> dict:
    """Out through the way you came, with whoever you can carry. Anybody
    left lying on a deck where people live is found and brought back to the
    hull, hurt; on a dead hull they are left for good."""
    carried = {a.carrying for a in party(walk) if a.carrying >= 0}
    left = [a for a in party(walk) if a.status in ("down", "stable")
            and a.id not in carried]
    if walk.kind in LIVING:
        return close(game, walk, "left", brought=left)
    return close(game, walk, "left", left_behind=left)


def wiped(game, walk) -> dict:
    """Nobody standing. Somebody else decides what happens next."""
    living = walk.kind in LIVING
    outcome = "carried" if living else "rescued"
    left = [] if living else [a for a in party(walk)
                              if a.status == "down" and a.folk != "captain"]
    return close(game, walk, outcome, left_behind=left, keep_found=False)


def give_up(game, walk) -> dict:
    """Go quietly. The watch writes it down and walks you to the gangway."""
    if not any(a.hostile and a.folk in ("constable", "customs")
               for a in walk.actors):
        return {"ok": False, "why": "There is nobody here to give up to."}
    # They take what the law here forbids, and keep you for the night.
    from .afoot_said import seize
    taken = seize(game, walk)
    walk.seconds += DETAINED_DAYS * 86400.0
    if taken:
        say(walk, "The watch takes " + ", ".join(taken) + ".", "bad")
    return close(game, walk, "arrested", keep_found=False)


def close(game, walk, outcome: str, left_behind=(), keep_found=True,
          brought=()) -> dict:
    """End the walk and write what it did onto the chronicle. `brought` are
    the party left down where people live, found and carried home."""
    walk.over = True
    walk.outcome = outcome
    said = []
    if walk.kind == "prize" and not walk.prize_done:
        from . import prize
        prize.release_hull(game, walk.prize, walk.prize_faction)
        walk.prize_done = "released"
        said.append("She was let go.")
    for body in left_behind:
        body.status = "dead"
    said += [f"{who.name} was found where they fell and brought back to the "
             "hull." for who in brought]
    said += _people(game, walk)
    if keep_found:
        said += _bank(game, walk)
    else:
        lost = len(walk.found.get("kit", []))
        if lost:
            said.append(f"What was picked up on the way ({lost} "
                        f"thing{'s' if lost != 1 else ''}) stayed behind.")
    said += _seized(game, walk)
    said += _crimes(game, walk)
    afoot_incidents.snubbed(game, walk)
    _remember(game, walk)
    days = walk.seconds / 86400.0
    if outcome in ("carried", "rescued"):
        days += CARRIED_DAYS
    game.afoot = None
    text = _summary(walk, outcome)
    game.add_log(text, "good" if outcome == "left" else "warn")
    game.walked["last"] = {"outcome": outcome, "text": text,
                           "said": said[:8]}
    if days > 0:
        game.advance_days(days)
    return {"ok": True, "outcome": outcome, "text": text, "said": said,
            "days": round(days, 3)}


def _summary(walk, outcome: str) -> str:
    words = {"left": "The party came back from",
             "carried": "The party was carried out of",
             "rescued": "The boat brought the party back from",
             "arrested": "The watch walked the party out of"}
    return f"{words.get(outcome, 'Back from')} {walk.name}."


# ── people ─────────────────────────────────────────────────────────────────

def _people(game, walk) -> list:
    """Wounds kept, the dead mourned, machines worn."""
    said = []
    wounds = game.wounds
    for who in party(walk):
        if who.folk == "robot":
            said += _machine(game, who)
            continue
        key = "captain" if who.folk == "captain" else str(who.officer)
        strain = float((walk.found.get("strain") or {}).get(key, 0))
        if who.status == "dead" and who.folk != "captain":
            said += _fallen(game, walk, who)
            wounds.pop(key, None)
            continue
        # What a stun took wears off on the way home; the rest is a wound.
        missing = max(0, who.hp_max - max(0, who.hp) - who.numb) + strain
        if missing > 0:
            wounds[key] = round(missing, 1)
            said.append(f"{who.name} is carrying {missing:g} stamina of hurt.")
        else:
            wounds.pop(key, None)
    return said


def _fallen(game, walk, who) -> list:
    officer = afoot_people.officer_of(game, who.officer)
    if officer is None:
        return []
    officer.retired = True
    fallen = game.walked.setdefault("fallen", {})
    fallen[str(officer.id)] = (f"Died aboard {walk.name}, day {game.day}.")
    loyalty.record(game, "crew_death")
    game.add_log(f"{officer.name} did not come back from {walk.name}.", "bad")
    return [f"{officer.name} is dead."]


def _machine(game, who) -> list:
    from . import robots
    robot = next((r for r in game.robots if r.id == who.robot), None)
    if robot is None:
        return []
    lost = 1.0 - max(0, who.hp) / max(1, who.hp_max)
    if who.status == "dead":
        robot.condition = min(robot.condition, robots.BROKEN_AT * 0.9)
        return [f"{robot.name} was wrecked and needs a yard."]
    if lost > 0:
        robot.condition = max(0.0, robot.condition - lost * 0.5)
        return [f"{robot.name} came back dented."]
    return []


# ── what was found ─────────────────────────────────────────────────────────

def _bank(game, walk) -> list:
    said = []
    found = walk.found
    for kid in found.get("kit", []):
        if kid in kit_table.ITEM_BY_ID:
            game.kit.append(kid)
    if found.get("kit"):
        said.append(f"{len(found['kit'])} thing(s) into the captain's "
                    "keeping.")
    if found.get("cargo"):
        said += _cargo(game, found["cargo"], walk)
    if found.get("evidence"):
        from . import inquiry
        for kind, amount in found["evidence"].items():
            inquiry.add(game.research, kind, float(amount))
        said.append("New work for the bench: " + ", ".join(
            f"{v:g} {k}" for k, v in found["evidence"].items()) + ".")
    study = sum((found.get("study") or {}).values())
    if study:
        from . import xeno
        target = xeno.best_unfinished(game)
        if target is not None:
            xeno.add_study(game, target.id, float(study))
            said.append(f"{study:g} towards understanding {target.name}.")
    for line in found.get("intel", []):
        game.add_log(line, "")
    signed = int((found.get("hands") or {}).get("signed", 0))
    if signed:
        from .afoot_talk import berths_left
        took = min(signed, berths_left(game))
        game.ship.crew += took
        said.append(f"{took} new hand(s) signed on.")
    if (found.get("burned") or {}).get("nest"):
        from . import responses
        responses.provoke(game, "burn", NEST_BURN)
        game.adjust_rep("charter", NEST_STANDING)
        said.append("A nest of the Bloom burned out.")
    return said


def _cargo(game, cargo: dict, walk=None) -> list:
    """What was found goes home — as far as the hold has room for it **and
    the way home will carry it**.

    The second half was missing. A haul went into the hold whole however the
    party had reached the place: twelve tonnes came back across two
    kilometres of vacuum carried by three people on a line. The way out is
    the way back (`sim/crossing.lift_t`), and a boat with a three-tonne hold
    makes three trips, not thirty.
    """
    from . import crossing
    from .ship import add_cargo, cargo_free
    room = cargo_free(game.ship, game.ship_stats)
    way = getattr(walk, "way", "aboard") if walk is not None else "aboard"
    heads = len([a for a in party(walk)]) if walk is not None else 1
    lift = crossing.lift_t(game, way, heads)
    moved, left = {}, 0.0
    for cid, tonnes in cargo.items():
        want = float(tonnes)
        got = min(want, room, lift)
        if got > 0.05:
            add_cargo(game.ship, cid, got)
            room -= got
            lift -= got
            moved[cid] = got
        left += max(0.0, want - max(0.0, got))
    said = []
    if moved:
        said.append("Into the hold: " + ", ".join(f"{t:g} t {c}"
                                                 for c, t in moved.items())
                    + ".")
    if left > 0.05:
        said.append(f"{left:g} t was left where it lay — "
                    + ("no room in the hold." if room <= 0.05 else
                       f"{_way_words(way)} takes no more."))
    elif not moved:
        said.append("No room in the hold for what was found.")
    return said


#: What each way home is called when it runs out of room.
_WAY_WORDS = {"boat": "the boat", "shuttle": "their shuttle",
              "suits": "what a party carries on a line"}


def _way_words(way: str) -> str:
    return _WAY_WORDS.get(way, "the way home")


def _seized(game, walk) -> list:
    out = []
    for kid in walk.found.get("seized", []):
        if kid in game.kit:
            game.kit.remove(kid)
            out.append(f"The {kit_table.ITEM_BY_ID[kid].name.lower()} was "
                       "kept by the watch.")
    return out


def _crimes(game, walk) -> list:
    from . import dockets
    out = []
    for row in walk.seen_doing:
        what, power, weight = row[:3]
        if power not in LAWFUL:
            continue
        charge = dockets.allege(game, power, what,
                                f"on the deck at {walk.name}", weight,
                                seen=SEEN)
        if charge is not None:
            out.append(f"{power.title()} has it on file: {what}.")
    return out


def _remember(game, walk) -> None:
    """The emptied lockers, for this season, and a line in the history."""
    emptied = walk.found.get("emptied", [])
    spent = walk.found.get("spent", [])
    if walk.kind not in ("ship", "holding"):
        season = str(afoot_cast.epoch(game, walk.kind))
        marks = game.walked.setdefault(walk.site, {})
        if emptied or spent:
            marks[season] = sorted(set(marks.get(season, [])) | set(emptied)
                                   | {i for i, _s in spent})
        if spent:
            # A console hacked, a relic studied, a nest burned: they stay
            # that way, rather than coming back whole for the next visit.
            done = dict(marks.get(f"{season}:spent", {}))
            done.update({str(i): s for i, s in spent})
            marks[f"{season}:spent"] = done
        if walk.kind == "wreck" and not any(
                a.side == "npc" and a.standing and a.mood == "hostile"
                for a in walk.actors):
            marks["cleared"] = True
    history = game.walked.setdefault("history", [])
    history.append([int(game.day), walk.kind, walk.name, walk.outcome])
    del history[:-HISTORY]
    _tally(game, walk)


def _tally(game, walk) -> None:
    """What a career on foot adds up to, for renown (`progress`)."""
    tally = game.walked.setdefault("tally", {})
    tally["walks"] = tally.get("walks", 0) + 1
    kinds = tally.setdefault("kinds", [])
    if walk.kind not in kinds:
        kinds.append(walk.kind)
    if walk.kind == "prize" and walk.prize_done in ("taken", "stripped"):
        tally["prizes"] = tally.get("prizes", 0) + 1
    burned = (walk.found.get("burned") or {}).get("nest", 0)
    if burned:
        tally["nests"] = tally.get("nests", 0) + int(burned)


def progress(game) -> dict:
    """A career on foot, as renown reads it (`renown_facts.wave_b`, facts
    named `afoot:<key>`): walks come home from, prizes boarded and decided
    on their own decks, dead hulls cleared, kinds of place walked, nests
    burned out by hand."""
    walked = getattr(game, "walked", {}) or {}
    tally = walked.get("tally", {})
    cleared = sum(1 for key, marks in walked.items()
                  if key.startswith("wreck:") and isinstance(marks, dict)
                  and marks.get("cleared"))
    return {"walks": tally.get("walks", 0), "boarded": tally.get("prizes", 0),
            "cleared": cleared, "kinds": len(tally.get("kinds", [])),
            "nests": tally.get("nests", 0)}
