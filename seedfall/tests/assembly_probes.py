"""One probe per Assembly effect key: the number its reader computes.

`test_assembly` runs each twice on the same sector with the instrument in
force — once as the game plays it, once with `assembly.effect` answering that
one key with its default — and the number has to move. This is the claim
`data/assembly` makes about every key: a resolution nobody's arithmetic reads
is a speech. A key in `EFFECTS` without a row here fails the suite.
"""

from __future__ import annotations

from types import SimpleNamespace

from ..core.state import new_game
from ..sim import aftermath, assembly, colony, customs, diplomacy as dip
from ..sim import enforce, exchequer, gates, inquiry, piracy, services
from ..sim import trade, ventures, war, warrants
from ..sim import wharfage


def sector(seed: str = "assembly-fx"):
    game = new_game(seed)
    dip.ensure(game)
    game.credits = 400_000
    return game


def enact(game, res_id: str, sponsor: str = "charter", **params):
    key = ":".join([res_id] + [params[k] for k in ("power", "a", "b")
                                if k in params])
    item = assembly.Tabled(key=key, res_id=res_id, sponsor=sponsor,
                           params=params)
    return assembly.enact(game, item, game.day, 180)


def _held_port(game, power: str):
    return next(s for s in game.galaxy.systems
                if s.port and s.port.faction == power
                and not s.port.independent and not s.port.player_built)


def _dock(game, system) -> None:
    game.location_id = system.id


def _wharfage(game):
    return wharfage.rate(game, _held_port(game, "charter"))


def _tithe(game):
    purse = exchequer.purse(game, "charter")
    exchequer.settle(game, 20)
    return purse.credits


def _containment(game):
    run = ventures.Venture(id=1, kind="containment", power="charter")
    return ventures.odds(game, run)


def _amnesty(game):
    warrants.issue(game, "charter", "licence", "a probe")
    _dock(game, _held_port(game, "charter"))
    game.ship.cargo["wildseed"] = 10.0
    return (float(enforce.may_seed(game)[0])
            + float(not customs.aboard(game, "charter")))


def _embargo(game):
    _dock(game, _held_port(game, "charter"))
    game.ship.cargo["ore"] = 20.0
    before = game.credits
    trade.sell(game, "ore", 20)
    return game.credits - before + 1.0


def _ceasefire(game):
    dip.shift_relation(game, "charter", "freeholds", -200)
    return float(war.at_war(game, "charter", "freeholds")) + 1.0


def _commons(game):
    _dock(game, _held_port(game, "charter"))
    game.ship.cargo["survey"] = 10.0
    trade.sell_survey_data(game)
    return inquiry.held(game.research, "survey")


def _salvage(game):
    _dock(game, _held_port(game, "charter"))
    battle = SimpleNamespace(loot={"credits": 2000, "research": 0},
                             enemy=SimpleNamespace(ship=SimpleNamespace(
                                 cargo={"ore": 20.0})))
    before = game.credits
    aftermath._salvage(game, battle, {"recovered": {}})
    return game.credits - before


def _choir(game):
    game.rep["sanhedrin"] = -50.0
    assembly.hold(game)
    return game.rep["sanhedrin"]


def _lawless(game):
    wild = max(game.galaxy.systems, key=lambda s: piracy.lawlessness(game, s))
    act = assembly.state(game).active[-1]
    act.params["systems"] = [wild.id]
    assembly.state(game).rev += 1
    return piracy.lawlessness(game, wild)


def _founding(game):
    game.ship.fitted.append("seed_bay")
    game.research.unlocked.append("bioleach")
    game.recompute()
    for key in ("ore", "biomass"):
        game.stores[key] = 900
    site = next((s, b) for s in game.galaxy.systems if not s.faction
                and s.bloom < 0.5 for b in s.bodies
                if b.kind in ("asteroid", "moon", "rocky") and b.colony is None)
    before = game.credits
    col, why = colony.found(game, site[0], site[1], "radix_mine")
    assert col is not None, why
    return game.credits - before


def _repairs(game):
    for layer in game.ship.layers:
        layer.hp = layer.max * 0.5
    return services.repair_quote(game)["cost"]


def _border(game):
    dip.shift_relation(game, "charter", "freeholds", -200)
    return float(len(war.spoils(game, "charter"))) + 1.0


def _search(game):
    _dock(game, _held_port(game, "charter"))
    game.ship.cargo["wildseed"] = 10.0
    return customs.chance(game, "charter")


def _tolls(game):
    far = max((s for s in game.galaxy.systems if s.faction),
              key=lambda s: (s.x - game.system.x) ** 2
              + (s.y - game.system.y) ** 2)
    return gates.toll(game, game.location_id, far.id)["credits"]


#: key -> (instrument, its parameters, the reader's number).
READERS = {
    "wharfage": ("open_quays", {}, _wharfage),
    "tithe": ("bloom_levy", {}, _tithe),
    "containment": ("bloom_levy", {}, _containment),
    "amnesty": ("amnesty", {}, _amnesty),
    "embargo": ("embargo", {"power": "concordat"}, _embargo),
    "ceasefire": ("ceasefire", {"a": "charter", "b": "freeholds"}, _ceasefire),
    "commons": ("commons", {}, _commons),
    "salvage_tax": ("salvage_law", {}, _salvage),
    "choir_floor": ("recognition", {}, _choir),
    "lawless": ("convoy", {"systems": []}, _lawless),
    "founding": ("colony_charter", {}, _founding),
    "repairs": ("harbour_dues", {}, _repairs),
    "border": ("border", {"a": "charter", "b": "freeholds"}, _border),
    "search": ("contraband", {}, _search),
    "tolls": ("free_passage", {}, _tolls),
}


def measure(key: str, neutral: bool) -> float:
    """The reader's number with the instrument in force, the key live or
    answered with its default."""
    res_id, params, probe = READERS[key]
    game = sector()
    enact(game, res_id, **params)
    if not neutral:
        return float(probe(game))
    real = assembly.effect

    def blind(g, k, default=None):
        return default if k == key else real(g, k, default)

    assembly.effect = blind
    try:
        return float(probe(game))
    finally:
        assembly.effect = real
