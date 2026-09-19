"""One efficacy probe per signature: switch it off, and see its number move.

Not a suite; `test_arcs` runs every row of `PROBES` and fails a signature
that has none. Each probe measures the number at the point the game reads
it — the burn's cut, the helm's share, a holding's yield — once with an
officer holding the signature and once without, on the same state and the
same luck.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data import arcs as data
from ..sim import arcs as arcs_sim


def _held(game, sig_id: str | None, variant: str = "claim"):
    """The science officer holds `sig_id` (None: nobody holds anything),
    their story told — so the day's dealing leaves them as they are."""
    officer = game.officers[0]
    officer.arc = next((a.id for a in data.ARCS if a.signature == sig_id),
                       data.ARCS[0].id)
    officer.arc_beat = 3
    officer.signature = sig_id
    officer.arc_state = {"chose": ["", "", ""], "variant": variant,
                         "paid": int(game.day)}
    game.recompute()
    return officer


def _both(seed: str, sig_id: str, measure) -> tuple:
    """`measure(game)` without the signature, then with it, same state."""
    out = []
    for held in (None, sig_id):
        game = new_game(seed)
        _held(game, held)
        out.append(measure(game))
    return tuple(out)


def burn() -> tuple:
    """A mid-game gun deck on a large mass: the cut, same luck both times."""
    from ..data.parts import part
    from ..sim import threat

    def cut(game):
        game.ship_stats.weapons = [part("mag_lance")] * 12
        system = game.system
        system.bloom = 0.9
        res, why = threat.cleanse(game, system, RNG("probe-burn"))
        assert res is not None, why
        return res["cut"]
    return _both("arc-probe-burn", "kessel_steady", cut)


def freehold_floor() -> tuple:
    def standing(game):
        game.rep["freeholds"] = -40.0
        arcs_sim.tick(game, 1)
        return game.rep["freeholds"]
    return _both("arc-probe-floor", "paid_in_full", standing)


def decode() -> tuple:
    from ..sim import minigames
    return _both("arc-probe-decode", "second_mind", lambda game: (
        minigames.begin_decoding(game, "probe", None).tries))


def scan() -> tuple:
    return _both("arc-probe-scan", "second_mind",
                 lambda game: game.ship_stats.scan)


def confirm() -> tuple:
    from ..data.tech import TECH
    from ..sim import inquiry
    tech = max(TECH, key=lambda t: t.cost)
    return _both("arc-probe-confirm", "peer_reviewed", lambda game: (
        inquiry.confirm_cost(game.research, tech.id, game.officers)))


def drill() -> tuple:
    from ..sim import stations
    return _both("arc-probe-drill", "drill",
                 lambda game: stations.helm_share(game.officers, 0))


def colony_yield() -> tuple:
    from ..sim import colony as colony_sim, works

    def ore(game):
        game.credits = 900_000
        game.ship.fitted.append("seed_bay")
        game.research.unlocked.append("bioleach")
        game.recompute()
        for key in ("alloy", "ore", "biomass", "volatiles"):
            game.stores[key] = 9000
        body = next(b for b in game.system.bodies
                    if b.kind in ("asteroid", "moon", "rocky"))
        col, why = colony_sim.found(game, game.system, body, "radix_mine")
        assert col is not None, why
        return sum(works.crewed_yields(game, col).values())
    return _both("arc-probe-yield", "green_thumb", ore)


def jump() -> tuple:
    return _both("arc-probe-jump", "dead_reckoning",
                 lambda game: game.ship_stats.jump)


def diplomacy() -> tuple:
    return _both("arc-probe-tongue", "light_tongued",
                 lambda game: game.ship_stats.diplomacy)


def comprehension() -> tuple:
    """Nothing without the Kith; the whole lift with them."""
    game = new_game("arc-probe-kith")
    _held(game, "light_tongued")
    bare = arcs_sim.comprehension(game)
    game.kith = object()                # the Kith, as far as this reads
    try:
        return bare, arcs_sim.comprehension(game)
    finally:
        del game.kith


def morale() -> tuple:
    def low(game):
        game.ship.morale = 0.2
        arcs_sim.tick(game, 1)
        return game.ship.morale
    return _both("arc-probe-morale", "remembered", low)


def reroll() -> tuple:
    """The quoted odds of a hard ground option, and the odds rolled."""
    from ..sim import expedition as exp_sim

    def odds(game):
        system = next(s for s in game.galaxy.systems
                      if any(b.kind not in ("gas", "star") for b in s.bodies))
        body = next(b for b in system.bodies if b.kind not in ("gas", "star"))
        party = exp_sim.generate(RNG("arc-probe-land"), system, body,
                                 [o.id for o in game.officers], 400)
        index = next(i for i, (_t, stat, _d, _r)
                     in enumerate(exp_sim.options_here(_at(party, "ruin")))
                     if stat)
        said = exp_sim.odds_for(_at(party, "ruin"), index,
                                game.officers)["chance"]
        rng, wins = RNG("arc-probe-rolls"), 0
        for _ in range(1500):
            party.supply = 400
            wins += bool(exp_sim.attempt(_at(party, "ruin"), index,
                                         game.officers, rng)["success"])
        return said, wins / 1500
    return _both("arc-probe-luck", "lucky", odds)


def _at(party, feature: str):
    party.here.feature, party.here.resolved = feature, False
    return party


def study() -> tuple:
    from ..sim import responses

    def xenolith(game):
        game.system.bloom = 0.6
        return responses.study_value(game, game.system)["xenolith"]
    return _both("arc-probe-study", "unafraid", xenolith)


def landed() -> tuple:
    """A month of the claimed share, out of the Freeholds' purse."""
    from ..sim import exchequer

    def month(game):
        officer = game.officers[0]
        if officer.signature:
            officer.arc_state["paid"] = int(game.day) - 30
        purse = exchequer.purse(game, "freeholds")
        before = (game.credits, purse.credits)
        arcs_sim.tick(game, 1)
        return game.credits - before[0], before[1] - purse.credits
    return _both("arc-probe-landed", "landed", month)


#: signature id -> [(what is measured, probe)]. `test_arcs` fails any
#: signature in `data/arcs.SIGNATURES` without a row, and any row whose
#: number does not move.
PROBES = {
    "kessel_steady": [("burn cut", burn)],
    "paid_in_full": [("Freeholds standing held", freehold_floor)],
    "second_mind": [("decoding tries", decode), ("survey quality", scan)],
    "peer_reviewed": [("days to confirm", confirm)],
    "drill": [("unattended helm share", drill)],
    "green_thumb": [("holding yield a day", colony_yield)],
    "dead_reckoning": [("jump range", jump)],
    "light_tongued": [("diplomacy", diplomacy),
                      ("Kith comprehension", comprehension)],
    "remembered": [("morale floor", morale)],
    "lucky": [("ground odds, quoted and rolled", reroll)],
    "unafraid": [("xenolith from a study", study)],
    "landed": [("a month's share, and the purse it came from", landed)],
}

assert set(PROBES) == set(data.SIGNATURES), "a signature with no probe"
