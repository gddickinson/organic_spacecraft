"""The law digit, and what it finally stops you carrying.

Every world has had a law level since `data/uwp.py` was written — the table
that holds it is literally a list of what it forbids — and nothing in the
game had ever read it. Contraband was a *power's* business: one list per
faction, applied identically at every quay that power holds.

Measured across six sectors, 248 worlds, that was wrong in both directions:

    charter     mean law 7.0   76% at 6+   16% at 9+
    sanhedrin   mean law 8.1  100% at 6+   41% at 9+
    concordat   mean law 4.5    23%         0%
    freeholds   mean law 1.7     2%         0%

A Charter capital and a Charter outpost opened a hold with exactly the same
appetite, and the Sanhedrin — whose worlds are the strictest in the sector
and whose doctrine *is* the law — never opened one at all, because the
faction's own list is empty. The one power you could carry anything past was
the one that should have been hardest.

`sim/lawlevel.py` is the reading. The claims:

- **A world's law is derived, and the sector is a spread** rather than one
  number per flag.
- **Two questions at every quay, and the harder answer wins**: whose flag it
  is, and what the law is here.
- **The ladder is a ladder** — what a world seizes gets rarer as the digit
  climbs, and the bulk trade is never on it, so an ordinary cargo run is
  untouched by any of this.
- **Forbidden here means no counter and a better unposted price**, which is
  the machinery contraband already had, now reachable by a world.
- **The boarding names the authority that is actually doing it.**
"""

from __future__ import annotations

import collections

from ..core.state import new_game
from ..data.commodities import BY_ID
from ..data.contraband import LAW_LADDER
from ..sim import customs, lawlevel
from ..sim import profile as profile_sim
from ..sim import trade as trade_sim
from .harness import Suite


def _ports(seeds: int = 6) -> list:
    """Every port in a handful of sectors, with its own chronicle."""
    out = []
    for n in range(seeds):
        game = new_game(f"lawlevel-{n}")
        for system in game.galaxy.systems:
            if system.port is not None:
                out.append((game, system))
    return out


def _at(game, system):
    """Stand the chronicle at this port, so `game.system` is it."""
    game.location_id = system.id
    return system


def run(suite: Suite) -> None:
    check = suite.check

    @check("every world has a law, and the sector is a spread not a number")
    def _():
        laws: collections.Counter = collections.Counter()
        by_power: dict = {}
        for game, system in _ports():
            _at(game, system)
            law = lawlevel.digit(game, system)
            laws[law] += 1
            by_power.setdefault(system.port.faction or "none", []).append(law)
        assert sum(laws.values()) >= 100, laws
        assert len(laws) >= 6, f"only {sorted(laws)} law levels in six sectors"
        # And within one power the worlds differ, which is the whole point.
        spread = {fac: (min(rows), max(rows)) for fac, rows in by_power.items()
                  if len(rows) >= 8}
        assert spread, by_power
        widest = max(spread.items(), key=lambda kv: kv[1][1] - kv[1][0])
        assert widest[1][1] - widest[1][0] >= 4, spread
        return (f"{sum(laws.values())} ports, {len(laws)} law levels; "
                + " · ".join(f"{fac} {lo}–{hi}"
                             for fac, (lo, hi) in sorted(spread.items())))

    @check("the harder of the two answers is what the quay actually does")
    def _():
        rows, harder = [], 0
        for game, system in _ports():
            _at(game, system)
            faction = system.port.faction
            theirs = set(getattr(customs.regime(faction), "outlaws", ()) or ())
            here = set(customs.seized_here(game, system))
            assert theirs <= here, (faction, theirs - here)
            if here - theirs:
                harder += 1
            rows.append(len(here))
        assert harder >= 20, f"the world's own law never added anything"
        return (f"{harder} of {len(rows)} ports seize something their flag "
                f"does not; the most any one quay takes is {max(rows)} goods "
                f"and {rows.count(0)} take nothing at all")

    @check("the power whose doctrine is the law finally opens a hold")
    def _():
        looked, blind = [], []
        for game, system in _ports():
            _at(game, system)
            faction = system.port.faction
            if faction != "sanhedrin":
                continue
            # Before this, the Sanhedrin's regime was empty: zero zeal, no
            # list, and therefore never a search however tight the world.
            assert not customs.regime(faction).outlaws
            game.ship.cargo["xenolith"] = 6
            carrying = customs.aboard(game, faction)
            odds = customs.chance(game, faction)
            (looked if carrying and odds > 0 else blind).append(system.name)
        assert looked, "no Sanhedrin port in six sectors"
        assert not blind, blind[:4]
        return (f"{len(looked)} Sanhedrin ports, every one of them now with "
                "a list of its own and odds of using it")

    @check("the ladder is a ladder, and the bulk trade is never on it")
    def _():
        shares: dict = {}
        total = 0
        for game, system in _ports():
            _at(game, system)
            here = customs.seized_here(game, system)
            total += 1
            for _rung, cid in LAW_LADDER:
                shares[cid] = shares.get(cid, 0) + (1 if cid in here else 0)
        assert total >= 100, total
        order = [cid for _rung, cid in LAW_LADDER]
        got = [shares[cid] for cid in order]
        assert got == sorted(got, reverse=True), dict(zip(order, got))
        # And nothing a freight run carries is ever seizable anywhere.
        for cid in ("ore", "volatiles", "biomass", "phosphate", "alloy",
                    "silicon"):
            assert cid not in shares, cid
            assert not any(cid == c for _r, c in LAW_LADDER)
        return " · ".join(f"{cid} {shares[cid] / total:.0%}" for cid in order)

    @check("forbidden here means no counter, and a better price off the books")
    def _():
        rows = []
        for game, system in _ports():
            _at(game, system)
            faction = system.port.faction
            for cid in customs.seized_here(game, system):
                if cid not in BY_ID:
                    continue
                game.ship.cargo[cid] = 10
                # No posted counter.
                got = trade_sim.sell(game, cid, 1)
                assert not got["ok"], (system.name, cid, got)
                assert "counter" in got["why"], got["why"]
                # And an unposted buyer who pays over the odds for it.
                price = customs.premium(game, faction, cid)
                assert price and price > BY_ID[cid].base, (cid, price)
                rows.append((cid, price / BY_ID[cid].base))
            if len(rows) > 40:
                break
        assert len(rows) >= 20, len(rows)
        best = max(rows, key=lambda r: r[1])
        return (f"{len(rows)} forbidden goods across the sector, every one "
                f"refused at the desk and worth {min(r[1] for r in rows):.2f}"
                f"–{best[1]:.2f}× base off the books")

    @check("the boarding names the authority that is actually doing it")
    def _():
        from ..core.rng import RNG
        local = power = None
        for game, system in _ports():
            _at(game, system)
            faction = system.port.faction
            here = customs.seized_here(game, system)
            mine = [c for c in here if not customs.outlaws(faction, c)]
            if mine and local is None:
                game.ship.cargo[mine[0]] = 4
                out = customs.inspect(game, RNG("local"))
                assert out["searched"], out
                assert out["local"], out
                assert out["writ"] and "statute" in out["writ"], out["writ"]
                local = (system.name, out["writ"])
            theirs = [c for c in here if customs.outlaws(faction, c)]
            if theirs and power is None and getattr(
                    customs.regime(faction), "writ", ""):
                game.ship.cargo.clear()
                game.ship.cargo[theirs[0]] = 4
                out = customs.inspect(game, RNG("power"))
                assert out["searched"] and not out["local"], out
                assert out["writ"] == customs.regime(faction).writ, out
                power = (system.name, out["writ"])
            if local and power:
                break
        assert local and power, (local, power)
        return (f"{local[0]}: {local[1]} · {power[0]}: {power[1]}")

    @check("a world that licenses charts will not buy them either")
    def _():
        from .quay import stand_at
        found, looked = [], 0
        for game, system in _ports(12):
            looked += 1
            _at(game, system)
            if "survey" not in customs.seized_here(game, system):
                continue
            stand_at(game, system)
            game.ship.cargo["survey"] = 20
            got = trade_sim.sell_survey_data(game)
            assert not got["ok"], got
            assert "licensed" in got["why"], got["why"]
            found.append((system.name, lawlevel.digit(game, system)))
        assert looked >= 100, looked
        # The top rung is rare by design — 2% of ports in six sectors — and
        # a check that shrugs when it finds none is a check that passes for
        # ever once the rung stops being reachable at all.
        assert found, f"no world licenses charts in {looked} ports"
        return (f"{len(found)} of {looked} ports license charts — "
                f"{found[0][0]} at law {found[0][1]} — and the Survey "
                "Office window is shut at every one")

    @check("nobody is sent to a counter that would confiscate the cargo")
    def _():
        """The far end only, and that distinction is load-bearing.

        A power that seizes a good on sight and pays you to bring it in is
        not contradicting itself: the impound is how it collects and the
        commission is the licence. Asked of the *issuing* port too, this
        found that every Sanhedrin world sits at law 6 or above — so the
        Sanhedrin's own relic commission could not be offered anywhere in
        the sector, which is a rule eating a feature rather than shaping it.
        """
        from ..sim import contracts as contract_sim
        checked, licensed = 0, 0
        for game, system in _ports(5):
            _at(game, system)
            for contract in contract_sim.board_for(game, system):
                if not contract.commodity or contract.kind == "bounty":
                    continue
                if contract.kind != "deliver":
                    licensed += 1 if customs.seizes(
                        game, contract.commodity, system) else 0
                    continue
                where = game.galaxy.systems[contract.target_system]
                assert not customs.seizes(game, contract.commodity, where), (
                    f"{system.name} sends {contract.commodity} to "
                    f"{where.name}, which impounds it")
                checked += 1
        assert checked >= 40, checked
        return (f"{checked} deliveries across five sectors, not one of them "
                f"to a counter that would take the cargo; {licensed} orders "
                "placed by a power for a good it impounds, which is how it "
                "collects")

    @check("what the law is here is said before anybody is boarded")
    def _():
        said = 0
        for game, system in _ports():
            _at(game, system)
            line = lawlevel.says(game, system)
            assert line and line[0].isupper() and line.endswith("."), line
            here = customs.seized_here(game, system)
            for cid in lawlevel.forbids(game, system):
                assert BY_ID[cid].name in line, (line, cid)
                assert cid in here
            said += 1
        assert said >= 100, said
        return (f"{said} ports, each saying its own law level and naming "
                "exactly what it takes")
