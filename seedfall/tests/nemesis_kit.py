"""The rivalry checks' fixtures. Not a suite: `test_nemeses` and
`test_nemeses_ui` build their chronicles, rivals and fights here.

Rivals are raised through `nemeses.rise` wherever the check is about the
rise, and made directly (`rival`) where it is about something a rival does —
a check of the search should not also be a check of the rise odds.
"""

from __future__ import annotations

from contextlib import contextmanager

from ..core.rng import RNG
from ..core.state import new_game
from ..data.nemeses import ARCHETYPES_BY_ID
from ..sim import aftermath as aftermath_sim
from ..sim import combat, encounters
from ..sim import nemeses as nem_sim
from ..sim import rivals
from ..sim.ship import build_layers, make_ship, stats
from . import captain_ai

#: The reasonably fitted hull the balance targets are measured against: the
#: same warfit NAVIS `test_balance` uses, on day 540 of a chronicle.
WARFIT = ("navis", ["slug_battery", "mag_lance", "carapace",
                    "ossified_bracing", "reaction_organ", "opsin_eyes",
                    "chemo_gut", "radiator_bloom"])
MID_GAME = 540


def warfit(game):
    ship = make_ship(*WARFIT)
    build_layers(ship, game.bonuses)
    ship.cargo = {"ore": 400, "alloy": 400, "volatiles": 60}
    return ship


def mid_game(seed: str = "nemesis-kit"):
    """A chronicle on day 540 flying the warfit, docked where it began."""
    game = new_game(seed)
    game.day = MID_GAME
    game.ship = warfit(game)
    game.fleet = [game.ship]
    game.recompute()
    return game


def rival(game, kind: str = "corsair", traits=(), level: int = 1,
          where=None, seed: str = "kit", nid: int | None = None):
    """A rival made directly, at `level`, sitting at `where` (default: here).

    Risen at level one and refitted up, which is the only way a level-five
    rival exists in play — a first draft built level five fresh and chose a
    battleship, which no returning rival ever flies.
    """
    rng = RNG(f"rival-{seed}-{kind}-{level}")
    arch = ARCHETYPES_BY_ID[kind]
    nem = nem_sim.Nemesis(
        id=nid if nid is not None else _next_id(game),
        name=f"Kit {kind.title()}", archetype=kind,
        faction=arch.sails or "freeholds",
        threat=encounters.draw_threat(game, rng),
        location_id=(where if where is not None else game.location_id),
        grudge={"theirs": 50.0, "yours": 10.0})
    nem.traits = list(traits) or [arch.traits[0]]
    rivals.refit(game, nem, rng)
    while nem.level < level:                 # each return, as `settle` does it
        nem.level += 1
        nem.retreats += 1
        nem.grudge["theirs"] = min(100.0, nem.grudge["theirs"]
                                   + rivals.GRUDGE_STEP)
        rivals.refit(game, nem, rng)
    nem_sim.state(game).nemeses.append(nem)
    return nem


def _next_id(game) -> int:
    from ..core import ids
    return ids.next_id("nemesis", game)


def battle_with(game, enc: dict, seed: str = "kit-fight"):
    """`combat.start` exactly as the battle screen calls it, and the opening."""
    rng = RNG(seed)
    b = combat.start(game.ship, game.ship_stats, enc["enemy"],
                     bonuses=game.bonuses, officers=game.officers,
                     rep=game.rep.get(enc["enemy"].get("faction"), 0),
                     no_parley=enc.get("no_parley", False), game=game,
                     rng=rng, band=enc.get("band") or 3)
    b.enemy_faction = enc["enemy"].get("faction")
    rivals.opening(game, b, enc)
    return b, rng


def ended(game, enc: dict, result: str, seed: str = "kit-end") -> tuple:
    """A fight forced to `result` and resolved through the one door."""
    from ..sim import battle_state
    b, rng = battle_with(game, enc, seed)
    battle_state.finish(b, result)
    out = aftermath_sim.resolve(game, b, rng)
    return b, out


def fought(game, enc: dict, seed: str) -> str:
    """Played out by the captain the tactical suite flies."""
    b, rng = battle_with(game, enc, seed)
    for _ in range(60):
        if b.over:
            break
        combat.take_turn(b, captain_ai.orders(b), rng)
    return b.result or "unresolved"


def win_rate(game, level: int, fights: int) -> tuple[float, dict]:
    """Seeded fights of a fresh warfit against rivals of every kind at
    `level`. A struck crew is a win, as in `test_balance`."""
    kinds = sorted(ARCHETYPES_BY_ID)
    wins, tally = 0, {}
    for index in range(fights):
        kind = kinds[index % len(kinds)]
        rng = RNG(f"rate-{level}-{index}")
        arch = ARCHETYPES_BY_ID[kind]
        traits = [rng.pick(list(arch.traits))]
        if rng.chance(0.5):
            traits.append(rng.pick([t for t in arch.traits if t not in traits]))
        nem = rival(game, kind, traits, level, seed=f"rate-{index}",
                    nid=10_000 + index)
        nem_sim.state(game).nemeses.remove(nem)
        enc = rivals.encounter(game, nem)
        ship = warfit(game)
        b = combat.start(ship, stats(ship), enc["enemy"], rng=rng, game=game,
                         no_parley=enc["no_parley"], band=enc["band"] or 3)
        b.enemy_faction = enc["enemy"]["faction"]
        rivals.opening(game, b, enc)
        for _ in range(60):
            if b.over:
                break
            combat.take_turn(b, captain_ai.orders(b), rng)
        tally[b.result] = tally.get(b.result, 0) + 1
        wins += b.result in ("destroyed", "driven-off", "struck")
    return wins / fights, tally


@contextmanager
def certain_rises():
    """Every trigger rises on the day — the odds are the rise's own check."""
    held = dict(nem_sim.RISE_ODDS)
    for key in nem_sim.RISE_ODDS:
        nem_sim.RISE_ODDS[key] = 1.0
    try:
        yield
    finally:
        nem_sim.RISE_ODDS.update(held)


def raider_country(game):
    """A system raiders work, with the ship moved there."""
    from ..sim import piracy
    wild = [s for s in game.galaxy.systems if piracy.raider_chance(game, s) > 0]
    assert wild, "this sector has nowhere raiders work"
    game.location_id = wild[0].id
    return wild[0]


def plain_fight(game, faction: str, seed: str) -> dict:
    """An ordinary enemy, not anybody's rival."""
    rng = RNG(seed)
    return {"enemy": encounters.make_enemy(rng, faction, 1.2),
            "no_parley": faction == "bloom"}
