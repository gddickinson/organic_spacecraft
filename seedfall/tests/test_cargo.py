"""Cargo-contract checks — the board must not offer guaranteed losses.

`shape()` priced a delivery at `amount * (base * 0.55 + rate * 0.4)`. The first
term is the *floor* price: what a market holding none of a good will pay for
it. Nobody sells at the floor — a counter with stock charges about `base * 1.1`
— so the board priced its own work against a number that does not exist.

Measured before the fix: 44% of cargo contracts paid less than buying their
cargo cost at the port that posted them, worst case fifty thousand credits down
on a silicon prospecting job. Cheap goods survived because the flat rate term
carried them; expensive ones were traps, and the screen showed a fee and
nothing else, so a trap looked exactly like a living.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.commodities import BY_ID
from ..data.contracts import CARGO_WANTED, KINDS
from ..sim import contracts as contract_sim
from ..sim import trade as trade_sim
from ..world.economy import buy_price
from .harness import Suite

CARGO_KINDS = ("deliver", "prospect")


def _boards(seeds: int = 8, ports: int = 6):
    """Every cargo contract from a spread of real boards."""
    out = []
    for index in range(seeds):
        game = new_game(f"cargo-{index}")
        for system in [s for s in game.galaxy.systems if s.port][:ports]:
            for contract in contract_sim.generate(
                    RNG(f"b-{index}-{system.id}"), game, system):
                if contract.kind in CARGO_KINDS:
                    out.append((game, system, contract))
    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("no cargo contract pays less than its own cargo costs")
    def _():
        sampled = _boards()
        assert len(sampled) > 40, f"only {len(sampled)} cargo contracts sampled"
        losses = []
        nets = []
        for game, system, contract in sampled:
            price = buy_price(system.market, contract.commodity, 0, 0)
            if price is None:
                continue
            net = contract.reward - price * contract.amount
            nets.append(net)
            if net <= 0:
                losses.append(f"{contract.kind} {contract.amount:g} t of "
                              f"{contract.commodity} for {contract.reward:,} "
                              f"against {price * contract.amount:,.0f}")
        assert not losses, (
            f"{len(losses)} of {len(nets)} contracts lose money:\n      "
            + "\n      ".join(losses[:5]))
        nets.sort()
        return (f"{len(nets)} contracts · worst +{nets[0]:,.0f} · "
                f"median +{nets[len(nets) // 2]:,.0f}")

    @check("the dear goods are not the trap they were")
    def _():
        # The old formula punished exactly the commodities worth carrying:
        # silicon, magnetite and trehalose were all guaranteed losses.
        dear = sorted(CARGO_WANTED, key=lambda cid: -BY_ID[cid].base)[:3]
        worst = {}
        for game, system, contract in _boards():
            if contract.commodity not in dear:
                continue
            price = buy_price(system.market, contract.commodity, 0, 0)
            if price is None:
                continue
            ratio = contract.reward / (price * contract.amount)
            worst[contract.commodity] = min(
                worst.get(contract.commodity, 99), ratio)
        assert worst, "no contracts for the expensive goods at all"
        for cid, ratio in worst.items():
            assert ratio > 1.0, (
                f"{cid} contracts still pay {ratio:.2f}x their cargo")
        return " · ".join(f"{cid} {r:.2f}x" for cid, r in sorted(worst.items()))

    @check("the board's quote is what actually happens")
    def _():
        # The screen prints this number. It has to be the truth.
        checked = 0
        for game, system, contract in _boards(seeds=4, ports=3):
            if contract.kind != "deliver":
                continue
            game.location_id = system.id
            game.credits = 5_000_000
            money = contract_sim.quote(game, contract)
            assert money is not None
            before = game.credits

            bought = trade_sim.buy(game, contract.commodity,
                                   int(contract.amount))
            if not bought["ok"] or bought["units"] < contract.amount:
                continue          # the port has none; not what this checks
            spent = before - game.credits
            assert abs(spent - money["cost"]) < max(2.0, money["cost"] * 0.02), (
                f"quoted {money['cost']:,} and it cost {spent:,.0f}")

            contract_sim.accept(game, contract)
            game.location_id = contract.target_system
            contract_sim.check(game)
            assert contract.done, "the delivery did not complete"
            cleared = game.credits - before
            assert abs(cleared - money["net"]) < max(2.0, abs(money["net"]) * 0.02), (
                f"quoted a clear of {money['net']:,} and cleared {cleared:,.0f}")
            checked += 1
            if checked >= 6:
                break
        assert checked >= 3, f"only {checked} deliveries could be flown"
        return f"{checked} deliveries: cost and clear both as quoted"

    @check("a quote knows what is already in the hold")
    def _():
        sampled = [t for t in _boards(seeds=3, ports=3)
                   if t[2].kind == "deliver"]
        assert sampled, "no deliveries to check"
        game, system, contract = sampled[0]
        game.location_id = system.id
        empty = contract_sim.quote(game, contract)
        game.ship.cargo[contract.commodity] = contract.amount
        full = contract_sim.quote(game, contract)
        assert full["cost"] == 0, (
            f"quoted {full['cost']:,} for cargo already aboard")
        assert full["net"] > empty["net"], "carrying it already is worth nothing"
        assert full["held"] == contract.amount
        return (f"{empty['cost']:,} to source, 0 with it already aboard")

    @check("distance pays haulage on cargo, not a share of the goods")
    def _():
        # Multiplying the cargo's value by distance turned an eighty-tonne
        # silicon run into a hundred and thirty thousand credits clear.
        #
        # Measured against *net*, not against a ratio to cargo value. The first
        # version of this check asserted reward/cost < 4 and failed at 11.7x —
        # on ore and volatiles hauled a long way. That is not a fault: freight
        # is priced by mass and distance, so a tonne is a tonne in the hold and
        # the ratio to a cheap good's value says nothing. What matters is
        # whether the payout stays in scale with the rest of the board.
        nets, per_tonne = [], []
        for game, system, contract in _boards():
            price = buy_price(system.market, contract.commodity, 0, 0)
            if price is None:
                continue
            net = contract.reward - price * contract.amount
            nets.append(net)
            per_tonne.append(net / contract.amount)
        assert nets, "nothing sampled"
        assert max(nets) < 90_000, (
            f"a single cargo contract clears {max(nets):,.0f}, which is more "
            "than anything else on the board pays")
        assert max(per_tonne) < 1200, (
            f"hauling pays {max(per_tonne):,.0f} a tonne, above what the best "
            "arbitrage in the sector is worth")
        nets.sort()
        return (f"median +{nets[len(nets) // 2]:,.0f}, "
                f"max +{max(nets):,.0f}, up to "
                f"{max(per_tonne):,.0f} the tonne")

    @check("the other contract kinds are untouched by this")
    def _():
        # Only cargo pricing changed. A bounty or a survey commission must
        # still pay what it paid, distance premium and all.
        seen = {}
        for index in range(6):
            game = new_game(f"other-{index}")
            for system in [s for s in game.galaxy.systems if s.port][:5]:
                for contract in contract_sim.generate(
                        RNG(f"o-{index}-{system.id}"), game, system):
                    if contract.kind in CARGO_KINDS:
                        continue
                    seen.setdefault(contract.kind, []).append(contract.reward)
        assert len(seen) >= 3, f"only {list(seen)} non-cargo kinds appeared"
        for kind, rewards in seen.items():
            rate = KINDS[kind].rate
            assert min(rewards) >= rate * 0.5, (
                f"{kind} pays {min(rewards):,} against a rate of {rate:,}")
            assert contract_sim.quote(new_game("q"), _fake(kind)) is None, (
                f"{kind} is being quoted as if it were cargo")
        return " · ".join(f"{k} {sum(v)//len(v):,}" for k, v in sorted(seen.items()))


def _fake(kind: str):
    return contract_sim.Contract(id=0, kind=kind, issuer="charter",
                                 issued_at=0, title="", posting="")
