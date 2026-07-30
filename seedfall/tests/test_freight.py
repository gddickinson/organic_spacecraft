"""Freight-desk checks — a run it names has to be worth flying.

Measured across four sectors: within a starting jump only 5% of lane/goods
combinations show a positive spread, and six of twelve openings offered no
profitable legal run the player could *see*, because finding one meant visiting
every neighbour and writing the prices down first.

Then measured again, properly, by flying them: below a fifth of the buy price
a spread does not survive the voyage. `tick_market` drags supply toward
equilibrium about 1.8% a day with a random walk on top, so a thin margin is
gone by the time the hull arrives. On one traced run the desk said a port paid
590, it paid 530 on arrival, and the margin had been 14.

So the desk is an information tool with a floor under it, and the floor is the
part that makes it honest.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.factions import FACTIONS_BY_ID
from ..sim import freight
from ..sim import market as market_sim
from ..sim import trade as trade_sim
from ..sim.actions import jump_to
from .harness import Suite


def _travelled(seed: str):
    """A captain who has been about: prices noted everywhere."""
    game = new_game(seed)
    game.credits = 400_000
    for system in game.galaxy.systems:
        if system.market:
            market_sim.note_prices(game, system, 0, 0)
    return game


def _somewhere_with_runs(seeds: int = 30, want: int = 1):
    for index in range(seeds):
        game = _travelled(f"fr-{index}")
        for system in game.galaxy.systems:
            if not system.port:
                continue
            game.location_id = system.id
            flying = freight.worth_flying(game, system, limit=9)
            if len(flying) >= want:
                return game, system, flying
    return None, None, []


def run(suite: Suite) -> None:
    check = suite.check

    @check("the desk talks to a captain on their first day")
    def _():
        # It did not. COLD was -8, the floor of Neutral — and the Dry Choir
        # *starts* at -10, so a new captain on a Dry Choir quay was locked out
        # of the mechanic for no reason of their own. Found by flying a career
        # and getting zero runs at Halcyon Wake.
        opening = new_game("first-day")
        locked = [fid for fid, standing in opening.rep.items()
                  if FACTIONS_BY_ID.get(fid) and not FACTIONS_BY_ID[fid].hostile
                  and not FACTIONS_BY_ID[fid].hidden
                  and freight.desk_reach(standing) == 0]
        assert not locked, (
            f"powers that will not talk to a new captain: {locked} "
            f"(standing {[opening.rep[f] for f in locked]}, COLD "
            f"{freight.COLD})")
        assert freight.COLD < min(
            opening.rep[f] for f in ("charter", "concordat", "freeholds",
                                     "sanhedrin")), \
            "the threshold is above somebody's starting standing"
        return (f"COLD {freight.COLD:g}; every power will name "
                f"{freight.desk_reach(0)} of its ports at the opening")

    @check("standing buys more of the harbourmaster's attention")
    def _():
        reaches = [freight.desk_reach(s) for s in (-40, -10, 0, 20, 60)]
        assert reaches == sorted(reaches), f"not monotonic: {reaches}"
        assert reaches[0] == 0, "a distrusted captain is still told things"
        assert reaches[-1] > reaches[2], "standing buys nothing"
        return " · ".join(f"{s:+}→{r}" for s, r in
                          zip((-40, -10, 0, 20, 60), reaches))

    @check("the desk names only its own power's ports")
    def _():
        game = _travelled("own-ports")
        checked = 0
        for system in game.galaxy.systems:
            if not system.port or not system.market:
                continue
            game.location_id = system.id
            for run_ in freight.from_desk(game, system):
                target = game.galaxy.systems[run_.target_id]
                assert target.port and target.port.faction == system.port.faction, (
                    f"{system.port.faction} desk named a "
                    f"{target.port.faction if target.port else 'portless'} system")
                checked += 1
        assert checked > 5, f"only {checked} desk runs to check"
        return f"{checked} desk runs, every one of its own power's ports"

    @check("nothing thinner than the drift is ever recommended")
    def _():
        # The floor that makes the desk honest. Below a fifth, measurement said
        # a run loses on average however good the spread looks when you load.
        game, system, flying = _somewhere_with_runs(want=1)
        assert flying, "no port in thirty sectors had a run worth flying"
        thin = [r for r, _t in flying
                if r.margin < r.buy_here * freight.MIN_SPREAD]
        assert not thin, f"{len(thin)} run(s) inside the drift were named"
        for _r, trip in flying:
            assert trip["net"] > 0, "a run that does not clear its own burn"
        return (f"{len(flying)} runs, all at or above "
                f"{freight.MIN_SPREAD:.0%} and clearing the burn")

    @check("what it clears counts the reaction mass")
    def _():
        # Ranking by margin alone is how a captain flies a four-credit spread
        # nine light-years and pays for the mass themselves.
        game, system, flying = _somewhere_with_runs(want=1)
        assert flying
        run_, trip = flying[0]
        assert trip["fuel"] > 0, "the burn is free"
        assert trip["outlay"] > 0
        naive = run_.margin * trip["tonnes"]
        assert trip["net"] <= naive, (
            "the quoted clear is above the raw spread, so nothing was deducted")
        return (f"{trip['tonnes']:g} t: {trip['outlay']:,} out, "
                f"{trip['fuel']:,} of mass, clears {trip['net']:,}")

    @check("the register offers every port it knows, not the top few")
    def _():
        # `from_register` walks `best_markets`, which defaults to a *display*
        # limit of four. Inheriting it meant the runs this desk could offer
        # depended on how many rows a panel happens to draw — and it only
        # surfaced when the register's ordering changed and a different four
        # survived. Measured against the register itself rather than against a
        # number, so the claim is coverage and not a magic four.
        from ..sim import market as market_sim
        game = _travelled("coverage")
        checked = thin = 0
        for system in game.galaxy.systems:
            if not (system.port and system.market):
                continue
            game.location_id = system.id
            offered = {(r.commodity, r.target_id)
                       for r in freight.from_register(game, system)}
            # Every port the register knows that pays over the local price is a
            # run this desk should be able to name — of the goods it will
            # actually sell you. `_buyable` is that gate: legal, stocked, and
            # priced. Asking it rather than walking the stock keeps the claim
            # about the limit rather than about contraband.
            for cid, cost in freight._buyable(game, system).items():
                rows = market_sim.best_markets(game, cid, selling=True,
                                               limit=99)
                want = {(cid, r["system"].id) for r in rows
                        if r["system"].id != system.id and r["price"] > cost}
                missing = want - offered
                assert not missing, (
                    f"at {system.name} the register knows {len(want)} port(s) "
                    f"paying over the local price for {cid} and the desk offers "
                    f"{len(want) - len(missing)} — a display limit is bounding "
                    "what work exists")
                checked += len(want)
                if len(want) > 4:
                    thin += 1
        assert checked > 40, checked
        assert thin > 0, (
            "no commodity anywhere had more than four buyers, so this check "
            "never exercised the limit it exists for")
        return (f"{checked} register-known runs, every one offered; {thin} "
                "commodity-and-port sets larger than the old limit of four")

    @check("a price you wrote down beats a price you were told")
    def _():
        game = _travelled("prefer")
        both = 0
        for system in game.galaxy.systems:
            if not system.port or not system.market:
                continue
            game.location_id = system.id
            told = {(r.commodity, r.target_id) for r in freight.from_desk(game, system)}
            noted = {(r.commodity, r.target_id)
                     for r in freight.from_register(game, system)}
            overlap = told & noted
            if not overlap:
                continue
            picked = {(r.commodity, r.target_id): r
                      for r in freight.runs(game, system, limit=99)}
            for key in overlap:
                if key in picked:
                    both += 1
                    assert picked[key].source == "register", (
                        "hearsay was preferred to your own notes")
        assert both > 0, "no run was known from both sources"
        return f"{both} run(s) known both ways, all taken from the register"

    @check("following the desk beats having only your own notes")
    def _():
        # The whole claim, flown rather than argued.
        def career(seed: str, use_desk: bool) -> float:
            game = new_game(seed)
            game.location_id = next(
                (s.id for s in game.galaxy.systems if s.port), 0)
            start, day0 = game.credits, game.day
            guard = 0
            while game.day - day0 < 730 and not game.dead and guard < 300:
                guard += 1
                here = game.system
                if not here.market:
                    break
                market_sim.note_prices(game, here, 0, 0)
                if game.ship.cargo.get("volatiles", 0) < 40:
                    trade_sim.buy(game, "volatiles", 40)
                options = [r for r, _t in freight.worth_flying(game, here, 99)]
                if not use_desk:
                    options = [r for r in options if r.source == "register"]
                if not options:
                    from ..world.galaxy import distance
                    near = [s for s in game.galaxy.systems
                            if s.market and s.id != here.id
                            and distance(s, here) <= game.ship_stats.jump]
                    near.sort(key=lambda s: (str(s.id) in game.register,
                                             distance(s, here)))
                    if not near or not jump_to(game, near[0].id).get("ok"):
                        break
                    continue
                pick = options[0]
                if not trade_sim.buy(game, pick.commodity, 9999)["ok"]:
                    break
                if not jump_to(game, pick.target_id).get("ok") or game.dead:
                    break
                trade_sim.sell(game, pick.commodity, 9999)
            return game.credits - start

        blind = [career(f"career-{i}", False) for i in range(8)]
        told = [career(f"career-{i}", True) for i in range(8)]
        mean_blind = sum(blind) / len(blind)
        mean_told = sum(told) / len(told)
        assert mean_told > mean_blind, (
            f"the desk is worth nothing: {mean_blind:,.0f} → {mean_told:,.0f}")
        assert mean_told > 0, (
            f"even following the desk a trading career loses {mean_told:,.0f}")
        return (f"two years: {mean_blind:,.0f} on your own notes, "
                f"{mean_told:,.0f} with the desk")
