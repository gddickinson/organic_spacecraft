"""What an engagement's ending does to a rival — and what ordinary fights raise.

`aftermath.resolve` calls `settle` for every engagement, before it decides
anything of its own, and `settle` answers in two halves:

- **A rival's meeting**, recognised by the hull (`nemeses.by_ship`) so it
  works whoever started the fight — the battle screen, the bridge, a scripted
  career. Each of the eight result ids is one branch below and **no new id is
  made**: the battle's own `result` is what every tally counts.
- **The rises.** A raider you ran from, a Concordat hull that struck to you,
  a Bloom hull you did not finish: the events the design names, noticed where
  they already end.

Its luck is keyed on the rival and the day, never `aftermath`'s `rng`: that
stream goes on to seize a xenology file, and a draw here would change which.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data.nemeses import ENDINGS, WINNER, trophy_part
from . import nemeses as nem_sim
from . import rivals
from .ship import add_cargo

#: How long history runs in a dossier before the oldest meeting drops off.
HISTORY_KEEP = 12


def settle(game, battle, out: dict) -> dict:
    """Spend the ending on whoever it concerns. Returns what happened to a
    rival, for the aftermath card; {} for a fight with nobody's rival in it."""
    said = {}
    nem = nem_sim.by_ship(game, battle.enemy.ship)
    if nem is not None and battle.result in ENDINGS:
        said = _meeting(game, nem, battle)
    elif nem is None:
        _rise_from(game, battle)
    _allies_after(game, battle)
    from . import hunts
    paid = hunts.collect(game, battle)
    if paid:
        said.setdefault("bounty", paid["reward"])
        said.setdefault("issuer", paid["issuer"])
    return said


def _meeting(game, nem, battle) -> dict:
    result = battle.result
    status, words = ENDINGS[result]
    rng = RNG(f"{game.seed}:ending:{nem.id}:{game.day}:{len(nem.history)}")
    here = game.system
    nem.history.append([int(game.day), here.id, result,
                        rivals.say(nem, words)])
    del nem.history[:-HISTORY_KEEP]
    nem_sim.spot(game, nem, here.id, 1.0)
    nem.trail = [here.id, int(game.day)]
    said = {"name": nem.name, "ending": status, "result": result,
            "words": rivals.say(nem, words)}
    grudge = nem.grudge
    if WINNER[result] == "them":
        grudge["yours"] = min(100.0, grudge.get("yours", 0) + rivals.GRUDGE_STEP)
    if result == "destroyed":
        said.update(_destroyed(game, nem))
    elif result == "driven-off":
        nem.status = "wounded"
        nem.back_on = int(game.day) + rng.int(*nem_sim.RETURN_DAYS)
        nem.retreats += 1
        grudge["theirs"] = min(100.0, grudge.get("theirs", 0)
                               + rivals.GRUDGE_STEP)
        said["back_on"] = nem.back_on
        nem_sim.taunt(game, nem, "wounded")
    elif result == "struck":
        arch = nem_sim.archetype(nem)
        nem.status = "allied"
        nem.loyal = rng.chance(arch.ally * (1.0 - grudge.get("theirs", 0) / 200.0))
        grudge["theirs"] = max(0.0, grudge.get("theirs", 0) - 30.0)
        nem_sim.taunt(game, nem, "spared")
    elif result == "parley":
        grudge["theirs"] = max(0.0, grudge.get("theirs", 0) - 10.0)
        near = nem_sim.neighbours(game, here.id)
        if near:
            nem.location_id = rng.pick(near).id
        nem_sim.taunt(game, nem, "truce")
    elif result in ("escaped", "routed", "lost"):
        grudge["theirs"] = min(100.0, grudge.get("theirs", 0) + 5.0)
        if result == "routed":
            said["plundered"] = _plunder(game, nem)
        nem_sim.taunt(game, nem, "won")
    else:                                   # stalemate
        grudge["theirs"] = min(100.0, grudge.get("theirs", 0) + 5.0)
    nem_sim.remember(game, nem, "slight" if WINNER[result] == "you"
                     else "meeting", said["words"] + f" at {here.name}", 1.0)
    game.add_log(f"{nem.name}: {said['words']}.",
                 "good" if WINNER[result] == "you" else "warn")
    return said


def _destroyed(game, nem) -> dict:
    nem.status = "dead"
    out = {}
    if nem.bounty:
        from . import hunts
        issuer = nem.bounty["issuer"]
        reward = hunts.pay(game, issuer, nem.bounty["reward"])
        game.adjust_rep(issuer, rivals.BOUNTY_STANDING)
        out.update(bounty=reward, issuer=issuer)
        from ..data.factions import FACTIONS_BY_ID
        who = getattr(FACTIONS_BY_ID.get(issuer), "short", issuer)
        game.add_log(f"{who} pays the price on {nem.name}: "
                     f"{reward:,.0f}.", "good")
        for record in nem_sim.state(game).taken:
            if record.get("nemesis") == nem.id:
                record["done"] = True
    trophy = take_trophy(game, nem)
    if trophy is not None:
        out["trophy"] = trophy["name"]
    return out


def take_trophy(game, nem) -> dict | None:
    """Their best mount, cut out of the wreck: a unique named fitting."""
    from ..data.parts import part
    guns = [part(pid) for pid in nem.ship.fitted
            if part(pid) is not None and part(pid).wpn is not None]
    if not guns:
        return None
    best = max(guns, key=lambda p: p.wpn.dmg)
    record = {"id": f"trophy-{nem.id}-{best.id}", "owner": nem.name,
              "base": best.id, "state": "held"}
    made = register_trophy(record)
    nem_sim.state(game).trophies.append(record)
    game.add_log(f"Cut out of the wreck: {made.name}.", "good")
    return {"id": record["id"], "name": made.name}


def register_trophy(record: dict):
    """Put a trophy into the fittings registry, from its record alone."""
    from ..data.parts import PARTS_BY_ID
    base = PARTS_BY_ID.get(record.get("base", ""))
    if base is None:
        return None
    made = trophy_part(record, base)
    PARTS_BY_ID[made.id] = made
    return made


def _plunder(game, nem) -> dict:
    """They take a cut, and it goes into *their* hold — where it will be
    if you ever finish them."""
    taken = {}
    for cid, tonnes in list(game.ship.cargo.items()):
        if cid == "volatiles" or tonnes < 1:
            continue
        cut = round(tonnes * rivals.PLUNDER_SHARE, 1)
        if cut <= 0:
            continue
        add_cargo(game.ship, cid, -cut)
        add_cargo(nem.ship, cid, cut)
        taken[cid] = cut
    if taken:
        from .aftermath import worth_of
        game.add_log(f"{nem.name} takes a cut of the hold — about "
                     f"{worth_of(taken):,.0f} worth.", "bad")
    return taken


def come_back(game, nem, rng) -> list:
    """Out of the yard: a level up, a new fitting, and a longer memory."""
    nem.level = min(nem_sim.LEVEL_MAX, nem.level + 1)
    rivals.refit(game, nem, rng)
    nem.status = "active"
    nem.back_on = -1
    if nem.bounty:
        nem.bounty["reward"] = int(round(nem.bounty["reward"] * 1.25, -2))
    nem_sim.taunt(game, nem, "return")
    return [("warn", f"{nem.name} is back in the lanes — level {nem.level}, "
                     "and refitted.")]


def _rise_from(game, battle) -> None:
    """The rises an ordinary fight can cause, where it ends."""
    fid, result = battle.enemy_faction, battle.result
    here = game.system
    words = ENDINGS.get(result, ("", ""))[1].format(they="they", them="them")
    if result in ("escaped", "driven-off", "routed") and (
            fid == "freeholds" or fid is None):
        # A Freehold hull where raiders work, or one on nobody's register
        # at all — a posted raider (`hunts._raider_meeting`) is the latter.
        from . import piracy
        if piracy.raider_chance(game, here) > 0:
            nem_sim.rise(game, "corsair", near=here,
                         cause=f"The captain of {battle.enemy_name} — {words} "
                               f"at {here.name} — has a long memory.")
    elif fid == "concordat" and result == "struck":
        nem_sim.rise(game, "ace", near=here,
                     cause=f"The captain who struck {battle.enemy_name} to "
                           "you has not stopped hearing about it.")
    elif fid == "bloom" and result in ("escaped", "driven-off", "stalemate",
                                       "routed"):
        nem_sim.rise(game, "husk", near=here,
                     cause="The Bloom hull you did not finish at "
                           f"{here.name} was once a Charter ship.")


def _allies_after(game, battle) -> None:
    """A rival who stood beside you has paid the debt — or died paying it."""
    for consort in getattr(battle, "consorts", ()):
        nem = nem_sim.by_ship(game, consort.ship)
        if nem is None or nem.status != "allied":
            continue
        dead = all(layer.hp <= 0 for layer in consort.ship.layers)
        nem.status = "dead" if dead else "retired"
        nem.history.append([int(game.day), game.location_id,
                            battle.result or "stalemate",
                            "stood beside you" + (" and died" if dead else "")])
        game.add_log(f"{nem.name} " + ("died paying an old debt." if dead
                                       else "has paid the debt, and goes."),
                     "warn" if dead else "good")


def ashore(game) -> None:
    """A spared rival whose hull you took as a prize is put ashore: the hull
    is yours now, and two records of one ship would be one ship too many."""
    fleet = {s.uid for s in game.fleet}
    for nem in nem_sim.roster(game):
        if nem.ship is not None and nem.ship.uid in fleet:
            nem.status = "retired"
            nem.ship = None
