"""What an engagement leaves behind.

All of this used to live in `ui/battle_view.py._finish()`: the salvage, the
loot, the cargo pulled off the wreck, bounty progress, seized xenology files,
instar kills, consorts lost, loyalty, and every standing change in the game
that follows from shooting at somebody. `sim/combat.py` held a loot dict and
nothing else.

Two things were wrong with that. It breaks the one-directional rule the project
runs on — rules live in `sim/`, screens draw them — so nothing headless could
resolve an engagement's consequences, and every balance run that fought a
battle collected no loot, no standing and no bounty credit. And a kill told
only its victim: destroying a Charter hull moved the Charter and nobody else,
in a sector where `sim/allegiance.py` already knows exactly who else cares.

`resolve()` does the work and hands back what happened. The screen reads it.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from . import allegiance
from . import bloom as bloom_sim
from . import consorts as consort_sim
from . import contracts as contract_sim
from . import inquiry
from . import loyalty as loyalty_sim
from . import research as research_sim
from .fieldwork import seize_notes
from .ship import add_cargo, cargo_free

#: Standing given up with the power whose hull you destroyed.
KILL_COST = 14.0

#: And with one you merely drove off.
ROUT_COST = 4.0

#: Standing gained when you stand down rather than finish it.
PARLEY_GAIN = 8.0

#: What a courtesy is worth in credits after a parley.
PARLEY_FEE = 400

#: How much a power's enemies enjoy watching it lose a hull, as a share of
#: what the loss cost the owner.
SCHADENFREUDE = 0.45

#: A struck hull humbles its owner — dearer than driving it off, cheaper
#: than killing the crew. (Taking her as a prize afterwards adds
#: `prize.PRIZE_COST` on top, which lands the total beside a kill: you have
#: their ship.)
STRUCK_COST = 6.0

_MOOD = {"destroyed": "victory", "driven-off": "victory", "parley": "parley",
         "struck": "victory", "lost": "defeat", "escaped": "defeat",
         "routed": "defeat"}


def _pleased(game, faction: str | None, weight: float) -> list[tuple[str, float]]:
    """Everyone who is glad this power just lost a hull.

    Reuses the allegiance severity ramp, so a power its rivals merely dislike
    gains them little and a power at war with the sector gains them a lot.
    """
    if not faction or faction == "bloom":
        return []
    moved = []
    for other, sev in allegiance.offended_by(game, faction):
        gain = round(weight * sev * SCHADENFREUDE, 1)
        if gain >= 0.1:
            game.adjust_rep(other, gain)
            moved.append((other, gain))
    return moved


def _remember(game, faction_id: str, kind: str, text: str,
              salience: float) -> None:
    """A power remembers what you did to its hulls, by name and by day.

    Standing is one number and it decays; a memory is a specific thing with a
    date on it, and it is what an envoy actually brings up.
    """
    if not faction_id:
        return
    from ..data.factions import FACTIONS_BY_ID
    from ..data.personas import FACTION_PERSONA
    from . import memory as memory_sim
    faction = FACTIONS_BY_ID.get(faction_id)
    mind = memory_sim.mind_for(
        game, f"faction:{faction_id}",
        name=faction.name if faction else faction_id, kind="faction",
        persona=FACTION_PERSONA.get(faction_id, "envoy"))
    mind.remember(game.day, kind, text, salience, tags=["combat", faction_id])


def _standing(game, battle, out: dict) -> None:
    fid = battle.enemy_faction
    if battle.result == "destroyed":
        if fid and fid != "bloom":
            # **Destroying a hull is the gravest thing in the offence table**,
            # it never prescribes, and every power that keeps a register will
            # charge it — not only the one that lost the ship. `report` works
            # out which of them could have known; the owner always does.
            from . import dockets
            name = getattr(battle.enemy, "name", None) or "a hull"
            dockets.report(game, "killing", f"you destroyed {name}",
                           weight=1.0, against=fid)
            game.adjust_rep(fid, -KILL_COST)
            out["standing"].append((fid, -KILL_COST))
            out["pleased"] = _pleased(game, fid, KILL_COST)
            # **And its friends, which nobody was charging.** `_pleased` above
            # walks `allegiance.offended_by` so a power's *rivals* are glad of
            # a kill; there was no matching walk of `defenders_of`, so the
            # people who like it did not mind at all. A captain could work
            # through one power's shipping hull by hull and stay welcome
            # everywhere except with the victim.
            #
            # `allegiance.charge_attack` is the one door for that arithmetic —
            # `sim/diplomacy` already spends it to denounce a power — and it
            # is asked at the same weight the kill costs the victim. Measured
            # on a chronicle where the Sanhedrin had warmed to the Charter at
            # 60: killing a Charter hull costs the Charter 14.0 and the
            # Sanhedrin 8.6. At day one, with nobody yet fond of anybody, it
            # costs nothing extra — which is the point rather than a gap.
            out["standing"].extend(
                (other, -cost) for other, cost
                in allegiance.charge_attack(game, fid, KILL_COST, {fid}))
            _remember(game, fid, "kill",
                      f"you destroyed the {battle.enemy_name}", 1.4)
        elif fid == "bloom":
            # Everybody is in favour of one less of those. It used to be the
            # Charter alone, hardcoded, in a screen.
            for power in ("charter", "concordat", "freeholds", "sanhedrin"):
                game.adjust_rep(power, 4)
                out["standing"].append((power, 4))
    elif battle.result == "parley" and fid:
        game.adjust_rep(fid, PARLEY_GAIN)
        out["standing"].append((fid, PARLEY_GAIN))
        _remember(game, fid, "kindness",
                  f"you let the {battle.enemy_name} go when you had it", 1.0)
        game.credits += PARLEY_FEE
        out["fee"] = PARLEY_FEE
    elif battle.result == "driven-off" and fid and fid != "bloom":
        game.adjust_rep(fid, -ROUT_COST)
        out["standing"].append((fid, -ROUT_COST))
        out["pleased"] = _pleased(game, fid, ROUT_COST)
        _remember(game, fid, "slight",
                  f"you drove the {battle.enemy_name} off", 0.9)
    elif battle.result == "struck" and fid and fid != "bloom":
        game.adjust_rep(fid, -STRUCK_COST)
        out["standing"].append((fid, -STRUCK_COST))
        out["pleased"] = _pleased(game, fid, STRUCK_COST)
        _remember(game, fid, "slight",
                  f"the {battle.enemy_name} struck its colours to you", 1.1)


def _salvage(game, battle, out: dict) -> None:
    loot = battle.loot or {}
    credits = loot.get("credits", 0)
    research = loot.get("research", 0)
    game.credits += credits
    research_sim.grant(game.research, research)
    salvage = 25 + research * 0.8
    inquiry.add(game.research, "hardware", salvage)
    out["credits"] = credits
    out["research"] = research
    out["salvage"] = salvage

    room = cargo_free(game.ship, game.ship_stats)
    for cid, tonnes in list(battle.enemy.ship.cargo.items()):
        take = min(tonnes, room)
        if take > 0.5:
            add_cargo(game.ship, cid, take)
            room -= take
            out["recovered"][cid] = out["recovered"].get(cid, 0) + take
    out["recovered_worth"] = worth_of(out["recovered"])


def worth_of(goods: dict) -> int:
    """Credit worth of a pile of cargo, at base prices.

    The screen printed recovered tonnage with no figure on it, between two
    lines that *are* in credits — and the cargo is the larger half of a
    wreck: measured, 1.5–10× the credit loot. A captain cannot see the
    reason to fight if the ledger will not say it.
    """
    from ..data.commodities import BY_ID
    return round(sum((BY_ID[cid].base if cid in BY_ID else 60) * tonnes
                     for cid, tonnes in goods.items()))


def resolve(game, battle, rng) -> dict:
    """Apply everything an engagement leaves behind. Returns what happened.

    Idempotent by flag: a battle already resolved returns its emptiness rather
    than paying out twice, because the screen and the clock can both reach it.
    """
    out = {"result": battle.result, "faction": battle.enemy_faction,
           "standing": [], "pleased": [], "recovered": {}, "bounties": [],
           "dead": [], "seized": None, "instar": False, "credits": 0,
           "research": 0, "salvage": 0.0, "fee": 0, "already": False,
           "recovered_worth": 0}
    if getattr(battle, "settled", False):
        out["already"] = True
        return out
    battle.settled = True

    fid = battle.enemy_faction

    killed = getattr(battle, "instar", None)
    if killed is not None and battle.result in ("destroyed", "driven-off"):
        roaming = next((i for i in bloom_sim.ensure(game).instars
                        if i.id == killed), None)
        if roaming is not None:
            bloom_sim.kill_instar(game, roaming)
            out["instar"] = True
            game.add_log("The mass is scattered. It will not reach anywhere.",
                         "good")

    loyalty_sim.record(game, _MOOD.get(battle.result, ""))
    if battle.result == "destroyed" and fid == "bloom":
        loyalty_sim.record(game, "bloom_kill")
    elif battle.result == "destroyed" and fid in ("charter", "concordat"):
        loyalty_sim.record(game, "kill_licensed")

    # Consorts lost in the action are lost for good, whatever the outcome.
    dead = consort_sim.losses(battle)
    if dead:
        gone = {c.uid for c in dead}
        game.fleet = [s for s in game.fleet if s.uid not in gone]
        for consort in dead:
            game.add_log(f"{consort.name} was lost with all hands.", "bad")
        loyalty_sim.record(game, "consort_lost", scale=len(dead))
    out["dead"] = [c.name for c in dead]

    if battle.result == "lost":
        return out

    if battle.result == "destroyed":
        _salvage(game, battle, out)
        out["bounties"] = list(contract_sim.note_kill(game, fid))
        if fid:
            out["seized"] = seize_notes(game, fid, rng)
    elif battle.result == "driven-off":
        research_sim.grant(game.research, 10)
        out["research"] = 10

    _standing(game, battle, out)
    game.add_log(f"Engagement with {battle.enemy_name}: {battle.result}.",
                 "good" if battle.result in ("destroyed", "parley", "driven-off")
                 else "warn")
    return out


def phrase_pleased(moved: list[tuple[str, float]]) -> str:
    """How the screen says who enjoyed it."""
    if not moved:
        return ""
    return ", ".join(f"{FACTIONS_BY_ID[f].short} +{g:g}" for f, g in moved)
