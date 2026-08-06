"""Striking colours, and what a captain does with a hull that has struck.

The endgame sweep's verdict on combat was that the fighting is sound and
nothing sits between "kill it" and "let it go": no surrender, no prize,
`driven-off` pays ten research, and the cargo a wreck carries — measured at
1.5–10× the credit loot — was never even priced. This module is the middle
outcome. A crew with a broken hull and no nerve left strikes its colours
(`enemy_ai.enemy_turn` decides that, on the same resolve the fight already
runs on), and the captain chooses once, through here.

Three doors, one decision (`Battle.prized`):

- `take` — put a prize crew aboard and she sails in company. Everything
  downstream already works, because a consort *is* a `Side`: deployment,
  interception, losses, upkeep all key on `game.fleet` and `uid`.
- `strip` — empty her holds into yours and let the hull limp home.
- `release` — let them go whole. Worth standing, not money.

Nothing here decides whether striking happens; it only spends the result.
"""

from __future__ import annotations

from ..data.chassis import CHASSIS_BY_ID
from .ship import add_cargo, cargo_free, next_uid

#: Below this resolve a broken crew considers striking at all …
STRIKE_AT = 22.0
#: … and only with the hull genuinely opened up.
STRIKE_HULL = 0.5
#: Chance per enemy turn once both hold. A grapple adds 0.3 — being held
#: fast with no nerve left is what striking is for.
STRIKE_ODDS = 0.3

#: Share of a chassis's complement a prize crew must be to sail her home.
PRIZE_SHARE = 0.15

#: What taking the hull costs with its owner, on top of the battle's own
#: settlement — between driving them off (4) and killing them (14), and
#: nearer the kill: you have their ship.
PRIZE_COST = 8.0
#: Letting a struck crew go whole is remembered kindly.
RELEASE_GAIN = 4.0


def crew_needed(enemy_ship) -> int:
    chassis = CHASSIS_BY_ID.get(enemy_ship.chassis)
    complement = getattr(chassis, "crew", 8) or 8
    return max(2, round(complement * PRIZE_SHARE))


def offer(game, battle) -> dict:
    """What can be done with the struck hull, every option with its reason."""
    if battle.result != "struck" or battle.prized:
        return {}
    need = crew_needed(battle.enemy.ship)
    can, why = can_take(game, battle)
    return {"need": need, "can_take": can, "why": why,
            "cargo": {cid: t for cid, t in battle.enemy.ship.cargo.items()
                      if t > 0.5}}


def can_take(game, battle) -> tuple[bool, str]:
    if battle.result != "struck":
        return False, "Nobody has struck."
    if battle.prized:
        return False, "That decision is made."
    need = crew_needed(battle.enemy.ship)
    if game.ship.crew <= need + 1:
        return False, (f"A prize crew is {need} hands, and you cannot "
                       "spare them.")
    return True, ""


def take(game, battle) -> dict:
    """Put a prize crew aboard. She joins the fleet, sailing in company."""
    ok, why = can_take(game, battle)
    if not ok:
        return {"ok": False, "why": why}
    hull = battle.enemy.ship
    need = crew_needed(hull)
    game.ship.crew -= need
    hull.crew = need
    hull.uid = next_uid()
    hull.escort = True
    hull.docked_at = None
    hull.morale = 0.5
    game.fleet.append(hull)
    battle.prized = "taken"
    fid = battle.enemy_faction
    if fid and fid != "bloom":
        game.adjust_rep(fid, -PRIZE_COST)
    game.add_log(f"{hull.name} taken as a prize — {need} hands aboard her, "
                 "sailing in company.", "good")
    return {"ok": True, "ship": hull, "crew": need}


def strip(game, battle) -> dict:
    """Empty her holds into yours and let the hull limp home."""
    if battle.result != "struck" or battle.prized:
        return {"ok": False, "why": "Nothing here has struck to you."}
    room = cargo_free(game.ship, game.ship_stats)
    moved: dict[str, float] = {}
    for cid, tonnes in list(battle.enemy.ship.cargo.items()):
        got = min(tonnes, room)
        if got > 0.5:
            add_cargo(game.ship, cid, got)
            add_cargo(battle.enemy.ship, cid, -got)
            room -= got
            moved[cid] = moved.get(cid, 0) + got
    battle.prized = "stripped"
    from . import aftermath
    worth = aftermath.worth_of(moved)
    game.add_log(f"{battle.enemy.ship.name} stripped to the frames — "
                 f"{round(sum(moved.values()))} t taken, worth about "
                 f"{worth:,.0f}.", "good")
    return {"ok": True, "moved": moved, "worth": worth}


def release(game, battle) -> dict:
    """Let them limp home whole. Worth standing, not money."""
    if battle.result != "struck" or battle.prized:
        return {"ok": False, "why": "Nothing here has struck to you."}
    battle.prized = "released"
    fid = battle.enemy_faction
    if fid and fid != "bloom":
        from . import diplomacy as dip
        gain = RELEASE_GAIN * dip.courtship(game.rep.get(fid, 0.0))
        game.adjust_rep(fid, gain)
        from . import grudge
        grudge.note(game, fid, "kindness",
                    f"you let {battle.enemy.ship.name} limp home after "
                    "she struck", salience=1.1)
    game.add_log(f"{battle.enemy.ship.name} limps for home under a flag "
                 "nobody will salute for a while.", "")
    return {"ok": True}
