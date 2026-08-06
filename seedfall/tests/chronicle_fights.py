"""The chronicle's fights, lifted out of `tests/chronicle.py` at the ratchet.

The driver's combat half: going looking for trouble through the same door an
arrival uses, and taking the engagement with the captain the tactical suite
flies. Split along the seam the two functions already were — nothing here
reads the driver's plan except the fights list it appends to.
"""

from __future__ import annotations


def _seek_trouble(game, rng, plan) -> None:
    """Go looking for a fight, if a decade of flying has not produced one.

    **Coverage was luck, and the honest clock proved it.** This driver reached
    "fought something" only when an arrival happened to hand it an encounter:
    one in a whole decade on seed `chronicle-cover`, and measured separately,
    *zero* encounters in 360 in-system arrivals across 30 seeds — the ones it
    got came from interstellar jumps. So when `advance_days` began walking day
    by day and the tick stream moved, that single roll went away and the check
    that calls itself "everything it claims to" was covering the whole tactical
    suite on one die.

    So the driver asks instead of waiting. It goes through the same door the
    arrival does — `encounters.roll_encounter` — in the systems where raiders
    actually work, which `sim/piracy` derives rather than guesses. Nothing is
    fabricated: if the sector has nowhere lawless enough, this finds nothing
    and the check fails, which is the correct outcome.
    """
    from ..sim import encounters as enc_sim, piracy as piracy_sim
    known = [s for s in game.galaxy.systems
             if piracy_sim.raider_chance(game, s) > 0]
    known.sort(key=lambda s: -piracy_sim.lawlessness(game, s))
    for system in known[:6]:
        for _ in range(12):
            met = enc_sim.roll_encounter(game, system, rng)
            if met and met.get("enemy"):
                plan.setdefault("fights", []).append(_fight(game, met, rng))
                return


def _fight(game, encounter, rng) -> str:
    """Actually take the engagement, with the captain the tactical suite uses.

    The chronicle claimed to do everything and never once fired: encounters
    were generated on arrival and thrown away, so a decade of play exercised
    none of the positional model, none of the stations, and none of the
    aftermath. Four encounters a decade is not many — which is exactly why
    nobody noticed.
    """
    from ..sim import aftermath as aftermath_sim
    from ..sim import combat as combat_sim
    from ..sim import consorts as consort_sim
    from .captain_ai import orders

    battle = combat_sim.start(
        game.ship, game.ship_stats, encounter["enemy"],
        bonuses=game.bonuses, officers=game.officers,
        rep=game.rep.get(encounter["enemy"].get("faction"), 0),
        no_parley=encounter.get("no_parley", False), game=game,
        rng=rng, fleet=consort_sim.escorts_of(game))
    battle.enemy_faction = encounter["enemy"].get("faction")
    guard = 0
    while not battle.over and guard < 80:
        guard += 1
        combat_sim.take_turn(battle, orders(battle), rng)
    if not battle.over:
        battle.over = True
        battle.result = "driven-off"
    aftermath_sim.resolve(game, battle, rng)
    return battle.result or "unresolved"
