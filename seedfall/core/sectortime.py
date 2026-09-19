"""Sector time: the phases of a day that run on the Verge's clock.

The other half of `core/shiptime.py`, split out of `core/clock._one_step`.
Markets, colonies, the powers and their law, the Bloom and the endings run
here, on `n` — what the sector lives through whatever the ship is doing.
The order the phases run in is `clock._one_step`'s and nobody else's.
"""

from __future__ import annotations

from ..data.territory import SEIZED as TERRITORY_SEIZED
from ..sim import allegiance
from ..sim import approach as approach_sim
from ..sim import arcs as arcs_sim
from ..sim import assembly as assembly_sim
from ..sim import chains as chain_sim
from ..sim import colony as colony_sim
from ..sim import comms as comms_sim
from ..sim import contracts as contract_sim
from ..sim import customs as customs_sim
from ..sim import diplomacy as dip_sim
from ..sim import exchequer as exchequer_sim
from ..sim import freightlines as lines_sim
from ..sim import kith as kith_sim
from ..sim import legacy as legacy_sim
from ..sim import market as market_sim
from ..sim import memoir as memoir_sim
from ..sim import memory as memory_sim
from ..sim import nemeses as nemeses_sim
from ..sim import renown as renown_sim
from ..sim import phenomena as sky_sim
from ..sim import responses as response_sim
from ..sim import shipyard as shipyard_sim
from ..sim import territory as territory_sim
from ..sim import threat as threat_sim
from ..sim import ventures as venture_sim
from ..sim import xeno as xeno_sim
from ..world.economy import tick_market


def holdings(game, n: int, r) -> None:
    """Customs cooling off, ground seized, colonies and the yard's slips."""
    customs_sim.cool(game, n)

    for colony, power in territory_sim.seizures(game, n, r):
        game.add_log(TERRITORY_SEIZED.format(colony=colony.name), "bad")

    _gains, events = colony_sim.tick(game, n)
    for kind, text in events:
        game.add_log(text, kind)

    for ship in shipyard_sim.tick_builds(game, n):
        game.add_log(f"{ship.name} is complete and standing by.", "good")


def economy(game, n: int, r) -> None:
    """Every market, the ventures, the powers' purses, their talk and law."""
    sky_sim.tick(game, n, r)        # innovation 7: the sky, before the quays
    for sys in game.galaxy.systems:
        if sys.market:
            tick_market(sys.market, n, r,
                        sys.port.level if sys.port else 1)
    for kind, text in market_sim.tick(game, n, r):
        game.add_log(text, kind)
    market_sim.apply_to_markets(game)
    for kind, text in venture_sim.tick(game, n, r):
        game.add_log(text, kind)
    # And somebody pays for all of it. The powers' purses take the day's
    # income, and once a month they build with the surplus or give something
    # up for the deficit — which is the only thing that has ever changed the
    # sector's infrastructure other than the player. See `sim/exchequer.py`.
    for kind, text in exchequer_sim.settle(game, n):
        game.add_log(text, kind)
    lines_sim.tick(game, n)       # innovation 5: a trading house's lines
    dip_sim.drift(game, n)
    assembly_sim.tick(game, n)      # the powers in session: sim/assembly
    # And the powers act on their own account, rather than only drifting back
    # toward a baseline while the captain does all the talking.
    for kind, text in approach_sim.tick(game, n, r):
        game.add_log(text, kind)
    # And the powers' law runs: files swept, hearings decided, judgments
    # collected, instruments lifted, and patrols that finally have a reason
    # to come alongside. `sim/governance` is the one front door — the order
    # the six modules run in is the law's own and lives there, not here.
    from ..sim import governance as law_sim
    for kind, text in law_sim.tick(game, n, r):
        game.add_log(text, kind)


def reckoning(game, n: int, r) -> None:
    """What the day added up to: news, contracts, the Bloom, the endings."""
    # Notes banked against a technology whose prerequisites have since been
    # met can finally be made sense of.
    # **The sector says things to you.** Derived from what has changed since
    # it last reported, so it cannot repeat itself or drift — `sim/comms`.
    comms_sim.tick(game, 1)
    comms_sim.sweep(game)
    settle_contracts(game)

    for tech in xeno_sim.settle(game):
        game.add_log(f"Xenotechnology incorporated: {tech.name}.", "good")

    for kind, text in threat_sim.tick(game, n, r):
        game.add_log(text, kind)
    memory_sim.tick(game, n)
    nemeses_sim.tick(game, n, r)        # rivals rise, roam, mend and return
    kith_sim.tick(game, n)              # the Kith: the song heard, debts due
    arcs_sim.tick(game, n, r)           # the officers' own stories
    for kind, text in legacy_sim.tick(game, n, r):
        game.add_log(text, kind)
    response_sim.decay(game, n)
    for kind, text in response_sim.check(game, r):
        game.add_log(text, kind)
    renown_sim.tick(game)           # milestones, ranks: sim/renown
    # Endings are checked before the Bloom is allowed to kill you, because
    # one of them is surviving it: Ruin fires when the sector is lost and
    # you are still flying, and the old order set `dead` first so it could
    # never fire at all. A *rested* chronicle — its final epoch lived
    # through and closed — detects no further endings at all: the world an
    # epoch leaves behind satisfies its own ending's condition by
    # construction, so re-detection froze the calendar for ever.
    win = threat_sim.check_victory(game)
    if (win and not game.victory and not legacy_sim.in_epoch(game)
            and not legacy_sim.rested(game)):
        game.victory = win
    # Inside an epoch the Bloom is no longer the clock — the epoch's own
    # pressure is. Without this the Ruin aftermath killed you on its first
    # tick, because the sector is still ninety-five per cent overgrown by
    # definition and `overgrown` fires every time.
    if (game.overgrown and not game.victory and not legacy_sim.in_epoch(game)
            and not legacy_sim.rested(game)):
        game.dead = True
        game.ending = "overgrown"
    memoir_sim.settle(game)         # an ending or a loss, written up
    game.recompute()


def settle_contracts(game) -> None:
    """Complete or expire the contracts whose terms the calendar has met."""
    for contract, outcome in contract_sim.check(game):
        if outcome == "done":
            game.add_log(f"Contract complete: {contract.title}. "
                         f"Paid {round(contract.reward):,} credits.", "good")
            if contract.cost:
                game.add_log("Word gets round who you work for — "
                             f"{allegiance.phrase(contract.cost)}.", "warn")
            for kind, text in chain_sim.on_contract_done(game, contract):
                game.add_log(text, kind)
        else:
            game.add_log(f"Contract expired: {contract.title}.", "bad")
            for kind, text in chain_sim.on_contract_failed(game, contract):
                game.add_log(text, kind)
