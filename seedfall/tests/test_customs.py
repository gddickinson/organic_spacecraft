"""Contraband checks — the run has to be worth making and possible to lose.

Wildseed was the dearest good in the table, flagged illegal, and neither fact
did anything: the Freeholds both sold it and bought it, so it never crossed
anybody else's space, and nobody ever looked in the hold. Measured before any
of this was written, it beat the best legal arbitrage in the sector and cost a
three-point standing ding that did not even apply where you sold it.

These hold both halves in place. A premium nobody can seize is free money; a
search with nothing worth carrying through it is a tax.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.commodities import BY_ID, COMMODITIES
from ..data.contraband import REGIMES
from ..sim import customs as customs_sim
from ..sim.ship import build_layers, make_ship
from ..world.economy import buy_price
from .harness import Suite

BANNED = [c.id for c in COMMODITIES if not c.legal]


def _at_outlawing_port(seed: str, cid: str = "wildseed"):
    """A game parked at a port that will seize `cid`."""
    game = new_game(seed)
    for system in game.galaxy.systems:
        if system.port and customs_sim.outlaws(system.port.faction, cid):
            game.location_id = system.id
            return game, system
    return game, None


def _career(seed: str, runs: int, fitted: bool, rng) -> float:
    """Fly the run `runs` times and return what the purse did."""
    game, dest = _at_outlawing_port(seed)
    if dest is None:
        return 0.0
    ports = [s for s in game.galaxy.systems if s.port and s.market]
    posted = [p for p in (buy_price(s.market, "wildseed") for s in ports) if p]
    if not posted:
        return 0.0
    cost = min(posted)
    faction = dest.port.faction

    if fitted:
        ship = make_ship("navis", ["reaction_organ", "void_hold",
                                   "false_manifest", "chemo_gut",
                                   "opsin_eyes", "radiator_bloom"])
        build_layers(ship, game.bonuses)
        game.ship = ship
        game.recompute()
        game.rep[faction] = 60

    purse = 0.0
    for _ in range(runs):
        room = customs_sim.absorbs(game, faction)
        price = customs_sim.premium(game, faction, "wildseed")
        game.ship.cargo["wildseed"] = room
        purse -= cost * room
        out = customs_sim.inspect(game, rng, approach=2.0 if fitted else 0.0)
        if out["caught"]:
            purse -= out["fine"]
        else:
            purse += price * room
            game.ship.cargo.pop("wildseed", None)
            customs_sim.add_heat(game, faction, 0.18)
        game.advance_days(30)
    return purse


def run(suite: Suite) -> None:
    check = suite.check

    @check("the regimes are coherent and name real goods")
    def _():
        assert BANNED, "nothing in the commodity table is contraband at all"
        policing = [r for r in REGIMES if r.outlaws]
        assert policing, "every power is indifferent; there is nothing to smuggle"
        free = [r for r in REGIMES if not r.outlaws]
        assert free, ("every power outlaws it, so there is nowhere to run it "
                      "from and no safe dock anywhere")
        for reg in REGIMES:
            assert 0.0 <= reg.zeal <= 1.0, f"{reg.faction} zeal {reg.zeal}"
            for cid in reg.outlaws:
                assert cid in BY_ID, f"{reg.faction} outlaws unknown {cid!r}"
                assert not BY_ID[cid].legal, (
                    f"{reg.faction} outlaws {cid}, which is a legal good")
            if reg.outlaws:
                assert reg.zeal > 0, f"{reg.faction} outlaws but never looks"
                assert reg.writ and reg.notice and reg.waved, (
                    f"{reg.faction} seizes cargo and says nothing about it")
        return (f"{len(policing)} powers policing, {len(free)} not, "
                f"{len(BANNED)} contraband good(s)")

    @check("the run exists: it is dearer where it is forbidden")
    def _():
        margins = []
        for index in range(8):
            game, dest = _at_outlawing_port(f"exists-{index}")
            if dest is None:
                continue
            ports = [s for s in game.galaxy.systems if s.port and s.market]
            posted = [p for p in (buy_price(s.market, "wildseed") for s in ports)
                      if p]
            best = max(
                (customs_sim.premium(game, s.port.faction, "wildseed") or 0)
                for s in ports)
            if posted:
                margins.append(best - min(posted))
        assert margins, "no sector had both a source and a buyer"
        assert min(margins) > 0, (
            f"the run loses money in the best case somewhere: {min(margins)}")
        mean = sum(margins) / len(margins)
        return f"{len(margins)} sectors, mean best margin {mean:,.0f} the tonne"

    @check("a clean hold is never searched, a dirty one can be")
    def _():
        game, dest = _at_outlawing_port("search")
        assert dest is not None
        rng = RNG("search")
        clean = customs_sim.inspect(game, rng)
        assert not clean["searched"], "boarded with nothing aboard"
        assert not clean["caught"]

        caught = cleared = 0
        for index in range(120):
            trial, _d = _at_outlawing_port(f"search-{index}")
            trial.ship.cargo["wildseed"] = 10
            out = customs_sim.inspect(trial, RNG(f"s-{index}"))
            assert out["searched"], "carrying, and not looked at"
            caught += out["caught"]
            cleared += not out["caught"]
        assert caught and cleared, (
            f"the search is not a gamble: {caught} caught, {cleared} cleared")
        return f"{caught} seized and {cleared} cleared in 120 dockings"

    @check("being caught costs the cargo, a fine, standing and a memory")
    def _():
        game, dest = _at_outlawing_port("caught")
        faction = dest.port.faction
        game.ship.cargo["wildseed"] = 30
        game.credits = 400000
        before = (game.credits, game.rep.get(faction, 0))
        # Pin the odds at the ceiling rather than fishing for a seed that
        # happens to fail the roll.
        game.scrutiny[faction] = 5.0
        out = customs_sim.inspect(game, RNG("caught"))
        assert out["caught"], "scrutiny at the ceiling and still waved through"
        assert "wildseed" not in game.ship.cargo, "they left the cargo aboard"
        assert game.credits < before[0], "no fine"
        assert game.rep.get(faction, 0) < before[1], "no standing cost"
        assert customs_sim.heat(game, faction) > 5.0, "they did not remember"
        return (f"30 t seized, fined {round(before[0] - game.credits):,}, "
                f"standing {round(before[1] - game.rep.get(faction, 0))} down")

    @check("their interest fades if you lay off")
    def _():
        game, dest = _at_outlawing_port("cool")
        faction = dest.port.faction
        customs_sim.add_heat(game, faction, 1.0)
        hot = customs_sim.chance(game, faction)
        game.advance_days(200)
        cold = customs_sim.heat(game, faction)
        assert cold < 0.4, f"still at {cold:.2f} after two hundred days"
        assert customs_sim.chance(game, faction) < hot, "no cooler for waiting"
        game.advance_days(200)
        assert customs_sim.heat(game, faction) == 0.0, "never clears entirely"
        return f"1.00 → {cold:.2f} in 200 days → clear"

    @check("every mitigation helps and all of them together do not retire it")
    def _():
        game, dest = _at_outlawing_port("mitigate")
        faction = dest.port.faction
        bare = customs_sim.chance(game, faction)

        game.rep[faction] = 80
        standing = customs_sim.chance(game, faction)
        assert standing < bare, "standing buys nothing"

        approached = customs_sim.chance(game, faction, approach=3.0)
        assert approached < standing, "a clean approach buys nothing"

        ship = make_ship("navis", ["reaction_organ", "void_hold",
                                   "false_manifest", "chemo_gut",
                                   "opsin_eyes", "radiator_bloom"])
        build_layers(ship, game.bonuses)
        game.ship = ship
        game.recompute()
        assert game.ship_stats.conceal > 0, "the fit conceals nothing"
        everything = customs_sim.chance(game, faction, approach=3.0)
        assert everything < approached, "a concealed hold buys nothing"

        # Subtracting the reliefs let a fitted-out hull with good standing drive
        # this under the floor and stop being a smuggler at all.
        assert everything > 0.04, (
            f"every mitigation stacked makes you untouchable: {everything:.3f}")
        assert everything < bare * 0.75, (
            "the mitigations together barely move it, so none of them is worth "
            f"fitting: {bare:.3f} → {everything:.3f}")
        return f"{bare:.0%} bare → {everything:.0%} fully fitted out"

    @check("an unposted buyer takes only what they can move")
    def _():
        game, dest = _at_outlawing_port("absorb")
        faction = dest.port.faction
        room = customs_sim.absorbs(game, faction)
        assert 0 < room < 200, f"they will take {room} t in one visit"
        customs_sim.add_heat(game, faction, 0.8)
        assert customs_sim.absorbs(game, faction) < room, (
            "a nervous market takes just as much")
        assert customs_sim.premium(game, faction, "wildseed") < \
            customs_sim.premium(new_game("absorb"), faction, "wildseed"), \
            "a nervous market pays just as well"
        return f"{room:g} t a visit cold, {customs_sim.absorbs(game, faction):g} t hot"

    @check("smuggling pays, and pays better if you commit to it")
    def _():
        runs = 6
        bare = [_career(f"pay-{i}", runs, False, RNG(f"b-{i}")) for i in range(12)]
        kitted = [_career(f"pay-{i}", runs, True, RNG(f"k-{i}")) for i in range(12)]
        mean_bare = sum(bare) / len(bare)
        mean_kit = sum(kitted) / len(kitted)
        assert mean_bare > 0, (
            f"the run loses money even flown well: {mean_bare:,.0f}")
        assert mean_kit > mean_bare * 1.25, (
            "fitting out and building standing barely beats a bare hull, so "
            f"there is no reason to commit: {mean_bare:,.0f} → {mean_kit:,.0f}")
        return (f"{runs} runs: bare {mean_bare:,.0f}, "
                f"fitted out {mean_kit:,.0f}")

    @check("hammering one port stops paying")
    def _():
        # Scrutiny is the brake. Without it the same dock is an unlimited
        # money printer, which is what the first cut of this actually was.
        rng = RNG("grind")
        game, dest = _at_outlawing_port("grind")
        faction = dest.port.faction
        first = customs_sim.premium(game, faction, "wildseed")
        for _ in range(5):
            customs_sim.add_heat(game, faction, 0.18)
        later = customs_sim.premium(game, faction, "wildseed")
        assert later < first, "the price never sours"
        assert customs_sim.chance(game, faction) > 0.5, (
            "five runs at one dock and they are still not looking hard")
        return f"{first:,} → {later:,} the tonne after five runs at one dock"
