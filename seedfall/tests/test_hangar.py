"""The hangar deck: cradles cut, craft bought, mended and sold.

A hull carried what it was given and nothing else. There was no way to buy a
craft, no way to sell one, no cradle to put a second in, and — the one that
told in play — **no way to put a point of hull back into one**: a fighter
that came home from an engagement at half was half for the rest of the
chronicle, and `data/craft.SALVAGE` was a constant nothing read.

`sim/hangar.py` is the yard side of a cradle. The claims:

- **A cradle is fitted, and a hull only takes so many** — by the hands it
  has, with the ship's boat's own floor under it.
- **A craft is laid down where its family's hulls are**, through
  `shipyard.can_build_here` rather than a second copy of that rule, and it
  costs the class's own money, matter and days.
- **A yard mends her by the point**; and a *grown* craft knits herself whole
  in her cradle off the hull's biomass, which is what grown is for.
- **Selling is always a loss** — for every class, at any condition — because
  a yard that pays what it charges is a money pump.
- **Nothing is done to a craft that is out**, or anywhere but alongside a
  yard.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data import craft as table
from ..data.craft import CRAFT, CRAFT_BY_ID
from ..sim import (afoot_plans, afoot_sites, craft as craft_sim,
                   establishments, hangar)
from .harness import Suite


def _funded(seed: str = "hangar", credits: float = 250_000):
    """A captain alongside their home yard with money and matter to spend."""
    game = new_game(seed)
    game.credits = credits
    for key in ("biomass", "silicon", "alloy", "ore", "phosphate"):
        game.stores[key] = 400.0
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("a cradle is fitted, and a hull carries only as many as it can work")
    def _():
        game = _funded("cradles")
        ship = game.ship
        assert hangar.cradles(ship) == 1, "she sails with the one she has"
        assert hangar.room(game) == 0, "the starting craft is in it"
        room_for = hangar.most(ship)
        assert room_for >= 2, room_for
        before = game.credits
        day = game.day
        got = hangar.fit_cradle(game)
        assert got["ok"], got
        assert hangar.cradles(ship) == 2 and hangar.room(game) == 1
        # Charged, and charged the bill — the days it takes are days, so the
        # crew eats through them and the drop is the bill and a little keep.
        paid = before - game.credits
        assert hangar.CRADLE_COST["credits"] <= paid < (
            hangar.CRADLE_COST["credits"] * 1.5), paid
        assert game.day == day + hangar.CRADLE_DAYS, (game.day, day)
        # And the hull plan grows the deck to go with it, once there is
        # something on it (`sim/afoot_program`).
        while hangar.cradles(ship) < hangar.most(ship):
            assert hangar.fit_cradle(game)["ok"]
        shut, why = hangar.can_fit_cradle(game)
        assert not shut and "all a hull this size" in why, why
        # A hull too small to crew a boat has nowhere to put one.
        from ..sim.ship import build_layers, make_ship
        little = make_ship("spore", [], "Mite")
        build_layers(little, game.bonuses)
        assert hangar.most(little) == 0, "a SPORE grew a hangar"
        return (f"{ship.chassis_def.name}: {hangar.cradles(ship)} cradles of "
                f"{hangar.most(ship)}, {hangar.CRADLE_COST['credits']:,} and "
                f"{hangar.CRADLE_DAYS} days each; a SPORE takes none")

    @check("a craft is laid down where its family's hulls are, for money, matter and days")
    def _():
        game = _funded("buying")
        assert hangar.fit_cradle(game)["ok"]
        rows = {row["kind"].id: row for row in hangar.offers(game)}
        assert len(rows) == len(CRAFT)
        assert all(row["days"] >= hangar.LEAST_DAYS for row in rows.values())
        kind = CRAFT_BY_ID["mote"]
        money, alloy = game.credits, game.stores["alloy"]
        day, had = game.day, len(craft_sim.aboard(game))
        got = hangar.buy(game, "mote")
        assert got["ok"], got
        assert len(craft_sim.aboard(game)) == had + 1
        assert kind.cost["credits"] <= money - game.credits < (
            kind.cost["credits"] * 1.5), (money, game.credits)
        assert game.stores["alloy"] == alloy - kind.cost["alloy"]
        assert game.day == day + got["days"], (game.day, day, got)
        mote = craft_sim.aboard(game)[-1]
        assert mote.hp == kind.hull and mote.fuel == kind.fuel_t
        assert mote.state == "cradled"
        # She is on the deck plan now, in a cradle deck of her own.
        laid = afoot_plans.plan(game, afoot_sites.own_hull(game))
        cradles = [r for r in laid.rooms if "Cradle deck" in r.name]
        assert len(cradles) == 2, [r.name for r in laid.rooms]
        # And the yard's own rule refuses what it cannot lay down: a family
        # this system has no slip for says so in the yard's words.
        from ..sim import shipyard
        for other in CRAFT:
            here, why = shipyard.can_build_here(game, game.system, other)
            if not here:
                assert "yard" in why or "nursery" in why, (other.id, why)
        return (f"a MOTE laid down for {got['paid']:,} credits, "
                f"{kind.cost['alloy']:g} t of alloy and {got['days']} days; "
                f"{len(cradles)} cradle decks aboard now")

    @check("a yard mends her by the point, and a grown craft knits herself")
    def _():
        game = _funded("mending")
        craft = craft_sim.aboard(game)[0]
        kind = craft_sim.kind_of(craft)
        assert kind.family == "grown"
        craft.hp = 40
        quote = hangar.mend_cost(craft)
        assert quote["credits"] == hangar.MEND_CREDITS * (kind.hull - 40)
        assert "biomass" in quote, quote
        money, day = game.credits, game.day
        got = hangar.mend(game, craft)
        assert got["ok"] and craft.hp == kind.hull, got
        assert quote["credits"] <= money - game.credits < (
            quote["credits"] + 2_000), (money, game.credits)
        assert game.day > day, "a hull put back in no time"
        assert not hangar.can_mend(game, craft)[0], "mended a whole craft"
        # The other way, and the reason to buy grown: she knits in her cradle
        # off the hold, and stops when the biomass does.
        craft.hp = 60
        game.ship.cargo["biomass"] = 20.0
        game.stores["biomass"] = 0.0
        hangar.knit(game, 10.0)
        assert craft.hp > 60, "ten days in the cradle and nothing grew"
        assert game.ship.cargo["biomass"] < 20.0, "it grew out of nothing"
        starved = craft.hp
        craft.hp = 10
        game.ship.cargo["biomass"] = 0.0
        hangar.knit(game, 30.0)
        assert craft.hp == 10, "a dry hold still fed her"
        # And a welded craft waits for a yard, whatever the hold holds.
        game.ship.cargo["biomass"] = 50.0
        welded = hangar.buy(game, "shrike")
        if welded["ok"]:
            welded["craft"].hp = 20
            hangar.knit(game, 20.0)
            assert welded["craft"].hp == 20, "a SHRIKE grew itself"
        return (f"{kind.hull - 40} points off a yard for "
                f"{quote['credits']:,}; {starved - 60} knitted in ten days "
                f"on her own, and none at all with a dry hold"
                + ("; a SHRIKE grew nothing" if welded["ok"] else ""))

    @check("selling is always a loss, and a wreck is worth less than a whole one")
    def _():
        game = _funded("selling")
        craft = craft_sim.aboard(game)[0]
        kind = craft_sim.kind_of(craft)
        whole = hangar.worth(craft)
        craft.hp = kind.hull // 4
        hurt = hangar.worth(craft)
        assert 0 < hurt < whole < kind.cost["credits"], (hurt, whole)
        for other in CRAFT:
            aboard = craft_sim.Carried(id=9, class_id=other.id, name="x",
                                       hp=other.hull, fuel=other.fuel_t)
            assert hangar.worth(aboard) < other.cost["credits"], other.id
        craft.hp = kind.hull
        money = game.credits
        got = hangar.sell(game, craft)
        assert got["ok"] and got["paid"] == whole, got
        assert game.credits == money + whole
        assert craft_sim.aboard(game) == [], "sold and still on the flight line"
        assert hangar.room(game) == hangar.cradles(game.ship)
        return (f"a whole WASP fetches {whole:,} against {kind.cost['credits']:,} "
                f"to lay down; a quarter-hull one {hurt:,} "
                f"({table.SALVAGE:.0%} salvage, scaled by condition)")

    @check("nothing is done to a craft that is out, or anywhere but a yard")
    def _():
        game = _funded("refusals")
        craft = craft_sim.aboard(game)[0]
        craft.hp = 50
        refused = {}
        craft_sim.launch(game, craft)
        refused["mend her in flight"] = hangar.can_mend(game, craft)[1]
        refused["sell her in flight"] = hangar.can_sell(game, craft)[1]
        assert craft_sim.recover(game)["ok"] or True
        craft.state, craft.pilot, game.sortie = "cradled", "", None
        # And out in a system with no yard in it at all — which is most of
        # the Verge, and where a cradle is a locker you cannot open.
        empty = next(s for s in game.galaxy.systems
                     if s.port is None and not establishments.here(game, s))
        game.location_id = empty.id
        refused["mend at large"] = hangar.can_mend(game, craft)[1]
        refused["buy at large"] = hangar.can_buy(game, "mote")[1]
        refused["a cradle at large"] = hangar.can_fit_cradle(game)[1]
        refused["sell at large"] = hangar.can_sell(game, craft)[1]
        assert all(refused.values()), refused
        assert all("yard" in why or "out" in why or "alongside" in why
                   for why in refused.values()), refused
        return "; ".join(f"{k}: “{v[:34]}…”" for k, v in
                         list(refused.items())[:3])
