"""Probes for the newer levers, kept apart so `levers.py` stays readable.

`levers.py` crossed five hundred lines as the lever list grew. The list and the
older probes stay there; everything written from the freight desk onward lives
here. Split by age rather than by theme on purpose — a themed split would have
meant deciding which of `customs`, `trade` and `contracts` a cargo probe
belongs to, and the answer is all three.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import aftermath as aftermath_sim
from ..sim import allegiance
from ..sim import diplomacy as dip
from ..sim import customs as customs_sim
from ..sim import dig as dig_sim
from ..sim import inquiry

# ── the desk finds runs your own notes cannot ──────────────────────────────

def _hard_burn_hull() -> float:
    """Hull lost touring a system on hard burns and then sitting a month."""
    from ..sim import flight
    from ..sim.ship import hull_pct
    lost = 0.0
    for index in range(10):
        game = new_game(f"lever-burn-{index}")
        game.ship.cargo = {"volatiles": 600}
        before = hull_pct(game.ship)
        for body in range(1, len(game.system.bodies)):
            result = flight.travel_to(game, body, "hard")
            if not result.get("ok") or result.get("dead"):
                break
        game.advance_days(30)
        lost += before - hull_pct(game.ship)
    return lost / 10


def _wasted_ground() -> float:
    """Depletion spent per tonne actually lifted, working a nearly full hold."""
    from ..sim.actions import extract
    total = 0.0
    runs = 0
    for index in range(6):
        game = new_game(f"lever-rig-{index}")
        for body in game.system.bodies:
            body.surveyed = True
        i = max(range(len(game.system.bodies)),
                key=lambda n: sum(game.system.bodies[n].resources.values()))
        game.ship.cargo = {"alloy": game.ship_stats.cargo * 0.92}
        body = game.system.bodies[i]
        before = body.depleted
        result = extract(game, i, 60, "cut")
        if not result.get("ok") or result.get("dead"):
            continue
        lifted = sum(result.get("got", {}).values())
        if lifted <= 0:
            continue
        total += (body.depleted - before) / lifted
        runs += 1
    return total / max(1, runs)


def _desk_runs() -> float:
    """Runs a captain can see from a port, knowing only the port they are on.

    Measured for somebody who has *not* been everywhere. The first version of
    this probe noted every market in the sector first, and the efficacy harness
    correctly reported the lever as inert: for a captain whose register already
    holds every port, the harbourmaster has nothing to add. His whole value is
    to one who has not been there yet, which is every new captain.
    """
    from ..sim import freight as freight_sim
    from ..sim import market as market_sim
    total = ports = 0
    for index in range(3):
        game = new_game(f"lever-desk-{index}")
        game.credits = 400_000
        for system in game.galaxy.systems:
            if not system.port or not system.market:
                continue
            game.location_id = system.id
            game.register.clear()
            market_sim.note_prices(game, system, 0, 0)
            total += len(freight_sim.runs(game, system, limit=99))
            ports += 1
    return total / max(1, ports)


# ── a cargo contract pays for its own cargo ────────────────────────────────

def _contract_net() -> float:
    """Mean credits a cargo contract clears over what its cargo costs."""
    from ..core.rng import RNG as _RNG
    from ..sim import contracts as contract_sim
    from ..world.economy import buy_price
    nets = []
    for index in range(4):
        game = new_game(f"lever-cargo-{index}")
        for system in [s for s in game.galaxy.systems if s.port][:5]:
            for c in contract_sim.generate(
                    _RNG(f"lc-{index}-{system.id}"), game, system):
                if c.kind not in ("deliver", "prospect"):
                    continue
                price = buy_price(system.market, c.commodity, 0, 0)
                if price is not None:
                    nets.append(c.reward - price * c.amount)
    return sum(nets) / max(1, len(nets))


# ── what the ground told you is worth something ────────────────────────────

def _note_evidence() -> float:
    """Evidence on the bench after a party reads a wreck properly."""
    from .test_notes import _landed, _read_the_room
    from ..sim import fieldwork
    from ..sim import expedition as exp_sim
    total = 0.0
    for index in range(5):
        game, party, rng = _landed(f"lever-notes-{index}")
        _read_the_room(game, party, rng)
        exp_sim.finish(party, "returned")
        before = sum(inquiry.held(game.research, k)
                     for k in ("hardware", "specimen", "reading"))
        fieldwork.conclude_expedition(game)
        total += sum(inquiry.held(game.research, k)
                     for k in ("hardware", "specimen", "reading")) - before
    return total / 5


# ── a kill is noticed by more than its victim ──────────────────────────────

def _kill_goodwill() -> float:
    """Standing gained with everyone else when a power loses a hull."""
    from .test_aftermath import _at_war, _fought
    from ..sim import aftermath as aftermath_sim
    total = 0.0
    for index in range(6):
        game, battle, rng = _fought(f"lever-kill-{index}", result="destroyed")
        _at_war(game)
        victim = battle.enemy_faction
        before = {p: game.rep.get(p, 0) for p in dip.POWERS}
        aftermath_sim.resolve(game, battle, rng)
        total += sum(game.rep.get(p, 0) - before[p]
                     for p in dip.POWERS if p != victim)
    return total / 6


# ── a chart is worth what is in the system ─────────────────────────────────

def _chart_spread() -> float:
    """Ratio of the dearest chart in the sector to the cheapest.

    A flat per-body rate leaves this near one: what is in a system stops
    mattering and every survey is worth the same as every other.
    """
    from ..sim import charts as chart_sim
    game = new_game("lever-charts")
    for system in game.galaxy.systems:
        for body in system.bodies:
            body.surveyed = True
    values = sorted(chart_sim.best_buyer(game, s)[1]
                    for s in game.galaxy.systems)
    return values[-1] / max(1, values[0])


# ── a levy takes a share of what a holding makes ───────────────────────────

def _levied_output() -> float:
    """A year of stores off one holding, with a power's name on the ground."""
    from .test_territory import _planted
    from ..sim import territory as territory_sim
    game, _col, system = _planted("lever-levy", "charter")
    territory_sim.answer(game, system, "charter", "levy")
    before = dict(game.stores)
    game.advance_days(365)
    return sum(max(0.0, game.stores.get(k, 0) - before.get(k, 0))
               for k in set(game.stores) | set(before))


# ── the powers notice whose work you take ──────────────────────────────────

def _spread_standing() -> float:
    """Total standing after working every power evenly, in a hostile sector.

    Summed rather than measured on one power: the whole claim is that you
    cannot bank goodwill everywhere at once.
    """
    powers = ("charter", "concordat", "freeholds", "sanhedrin")
    game = new_game("lever-sides")
    for index in range(28):
        power = powers[index % len(powers)]
        game.adjust_rep(power, 5)
        allegiance.charge(game, power, 5)
    return sum(game.rep.get(p, 0) for p in powers)


# ── somebody looks in the hold ─────────────────────────────────────────────

def _smuggling_purse() -> float:
    """What six contraband runs leave in the purse."""
    from ..tests.test_customs import _career
    total = 0.0
    runs = 8
    for index in range(runs):
        total += _career(f"lever-smug-{index}", 6, False, RNG(f"ls-{index}"))
    return total / runs


# ── hurrying a dig costs you the find ──────────────────────────────────────

def _cut_dig_points() -> float:
    """Understanding banked cutting straight down through a site.

    Cutting is the roughest method, so it is where the spoil roll bites
    hardest — a probe on the careful method would barely move.
    """
    from ..data.xenotech import XENOTECH
    total = 0.0
    runs = 12
    for index in range(runs):
        game = new_game(f"lever-dig-{index}")
        body = game.system.bodies[0]
        body.relic = XENOTECH[0].id
        body.relic_found = True
        body.digs = 0
        started = dig_sim.begin(game, 0)
        if not started["ok"]:
            continue
        site = started["dig"]
        game.dig = site
        rng = RNG(f"dig-{index}")
        guard = 0
        while not site.over and guard < 10:
            guard += 1
            dig_sim.work(game, site, "cut", rng)
        total += site.points
    return total / runs
