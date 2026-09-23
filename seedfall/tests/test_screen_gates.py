"""The gate a *control* is lit by is the gate the act refuses on.

`tests/test_gates.py` asks the same question of the sim's own gate
functions — `can_found` against `found`, `can_hire` against `hire` — where
the act calls the gate and the two cannot drift. This suite asks it of the
gates a **screen** assembles for itself out of several sim answers, which is
where they do drift, because nothing calls anything.

A play session through the real windows — press what is enabled, on every
screen, for four chronicles — turned up the same defect eleven times in
different clothes. A button was lit by one question and the handler behind
it refused by another:

    Buy                       → "No room in the hold."
    Take on 40 t — ~₡1,160    → "Not enough credits."
    Launch — Captain Erskine  → "Another craft is out; the cradle deck is busy."
    Land a party              → "A WASP seats 1 — the pilot, and nobody else."
    Work it — 90 days         → "No room in the hold for anything it would raise."
    Let the harbourmaster …   → "Not in this orbit: fly there first."
    Sell all survey data      → "Nobody is at Fleet Hub's counter."
    Draw out                  → "The account is empty."
    Denounce a rival — …      → "That ground was worked 0 day(s) ago."
    Fly her down yourself     → "Another craft is out; the cradle deck is busy."

Every one of them is a control a player can press and only ever be told no
by, which is worse than no control: it reads as a broken game rather than as
a rule. The project has swept this class before — `sim/conn.can_burn` records
a gate refusing a burn it could well afford — and this suite is the sweep
made permanent.

The property is one sentence: **for every act with a screen-side gate, the
gate says yes exactly when the act does.** Nothing here presses a button;
each check asks the two doors the same question in the same state and holds
them to the same answer, which is the only version of this that cannot rot.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.expedition import SUPPLY_LOADS
from ..sim import craft as craft_sim
from ..sim import descent as descent_sim
from ..sim import descent_flight, diplomacy_acts, flight
from ..sim import mining as mining_sim
from ..sim import trade as trade_sim
from ..world.planets import BODY_KINDS
from .harness import Suite


def _trading(seed: str = "gates"):
    """A chronicle standing at a counter with something to buy."""
    for n in range(10):
        game = new_game(f"{seed}-{n}")
        from .quay import stand_at
        if game.system.port is not None:
            stand_at(game, game.system)
            return game
    raise AssertionError("no port in ten sectors")


def _world(seed: str = "gates-world"):
    """A chronicle in orbit of something a lander may go down on."""
    for n in range(14):
        game = new_game(f"{seed}-{n}")
        game.ship.cargo["biomass"] = 400
        for index, body in enumerate(game.system.bodies):
            if not BODY_KINDS[body.kind][2]:
                continue
            body.surveyed = True
            flight.hold_at(game, body)
            if descent_sim.best(game, body) is not None:
                return game, index, body
    raise AssertionError("nothing to land on in fourteen sectors")


def run(suite: Suite) -> None:
    check = suite.check

    @check("the market's Buy is lit by the till's own answer")
    def _():
        from ..data.commodities import BY_ID
        rows, disagreed = 0, []
        for n in range(4):
            game = _trading(f"buy-{n}")
            for cid in BY_ID:
                for purse, hold in ((0, 0), (0, 400), (50_000, 0),
                                    (50_000, 400)):
                    game.credits = purse
                    # Fill or empty the hold by the one door that owns it.
                    for other in list(game.ship.cargo):
                        if other != "survey":
                            game.ship.cargo[other] = 0
                    if not hold:
                        game.ship.cargo["ore"] = 99_999
                    gate = trade_sim.can_buy(game, cid)[0]
                    act = trade_sim.buy(game, cid, 1)
                    rows += 1
                    if gate != bool(act.get("ok")):
                        disagreed.append((cid, purse, hold, act.get("why")))
        assert rows >= 100, rows
        assert not disagreed, disagreed[:4]
        return (f"{rows} counter states across four sectors, every commodity "
                "and both empty and full: the button and the till never "
                "disagreed")

    @check("a craft's Launch is lit only when the deck can launch her")
    def _():
        game, _index, _body = _world("launch")
        craft = craft_sim.aboard(game)
        assert len(craft) >= 2, craft
        rows = []
        for holder in craft:
            deck = craft_sim.can_launch(game, holder)
            for key, _name, _what, ok, _why in craft_sim.pilots(game, holder):
                # The screen's rule (`ui/craft_panel`): the ticket *and* the
                # deck. What it used to be: the ticket alone.
                lit = ok and deck[0]
                got = craft_sim.can_launch(game, holder, key)
                assert lit == got[0], (holder.name, key, lit, got)
                rows.append((holder.name, key, lit))
        # And with one out, nothing else may go: the state that produced the
        # refusal in the play session.
        out = craft_sim.launch(game, craft[0])
        assert out["ok"], out
        for holder in craft:
            deck_ok, why = craft_sim.can_launch(game, holder)
            assert not deck_ok, holder.name
            assert "already out" in why or "cradle deck is busy" in why, why
        return (f"{len(rows)} pilot/craft pairs agreed with the deck, and "
                "with one out every launch on the panel goes dark")

    @check("a descent is offered only when it can actually be flown")
    def _():
        game, index, body = _world("descent-gate")
        craft = descent_sim.best(game, body)
        assert descent_flight.can_fly(game, craft, body)[0]
        got = descent_flight.begin(game, craft, index)
        assert got["ok"], got
        # Now she is out, and the door says so rather than the act saying it.
        again = descent_flight.can_fly(game, descent_sim.best(game, body)
                                       or craft, body)
        assert not again[0], again
        assert not descent_flight.begin(game, craft, index)["ok"]
        # And the two doors agree on a world nothing aboard can leave again.
        heavy = next((b for b in game.system.bodies
                      if BODY_KINDS[b.kind][2] and b.gravity > 2.0), None)
        if heavy is not None:
            assert not descent_sim.can_land(game, craft, heavy)[0]
        return (f"{again[1]} — and the act agrees, rather than the button "
                "finding out")

    @check("a party is offered a load the hold can actually pay for")
    def _():
        from ..sim import fieldwork
        game, index, body = _world("supplies")
        light = SUPPLY_LOADS[0][1]
        game.ship.cargo["biomass"] = light - 1
        # The screen's gate (`ui/worldmap_view._may_land`) is the biomass
        # the lightest load wants; the act's refusal is the same number.
        got = fieldwork.launch_expedition(
            game, index, [o.id for o in game.officers[:1]], load=0)
        assert not got["ok"], got
        assert "biomass" in got["why"], got["why"]
        game.ship.cargo["biomass"] = light
        got = fieldwork.launch_expedition(
            game, index, [o.id for o in game.officers[:1]], load=0)
        assert got["ok"], got
        return (f"{light - 1} t of biomass refuses the lightest load and "
                f"{light} t takes it — one number, and the screen greys on it")

    @check("a working is offered only where there is room and upkeep for it")
    def _():
        from ..sim import actions
        rows, disagreed = 0, []
        for n in range(4):
            game = new_game(f"gates-mine-{n}")
            for index, body in enumerate(game.system.bodies[:4]):
                for hold, fuel in ((0, 200), (99_999, 200), (0, 0)):
                    game.ship.cargo["ore"] = hold
                    game.ship.cargo["volatiles"] = fuel
                    method = mining_sim.DEFAULT_METHOD
                    room = mining_sim.days_of_room(
                        body, method, game.ship_stats,
                        max(0, 400 - hold), 30)
                    gate = (room > 0
                            and mining_sim.can_afford(game, method, room)[0])
                    if not gate:
                        got = actions.extract(game, index, days=30,
                                              method_id=method)
                        rows += 1
                        if got.get("ok"):
                            disagreed.append((body.name, hold, fuel))
        assert rows >= 8, rows
        assert not disagreed, disagreed[:4]
        return (f"{rows} states the panel would have greyed, and the rig "
                "refused every one of them")

    @check("an overture is offered only when its own ground is not worked out")
    def _():
        game = new_game("gates-dip")
        game.credits = 500_000
        from ..sim import diplomacy as dip
        powers = [p for p in dip.POWERS][:3]
        if len(powers) < 3:
            return "fewer than three powers in this sector"
        seat, target = powers[0], powers[1]
        for faction in powers:
            game.rep[faction] = 60
        done = diplomacy_acts.perform(game, "denounce", seat, target)
        if not done.get("ok"):
            return f"the sector would not let one be made: {done.get('why')}"
        # The cooldown belongs to the *target*, so the same denunciation
        # ordered from another court is the same worked ground — and the
        # gate has to know it, or the button lights and the act refuses.
        other_seat = powers[2]
        offered = {a.id: (ok, why) for a, ok, why
                   in diplomacy_acts.available(game, other_seat, target)}
        assert not offered["denounce"][0], offered["denounce"]
        act = diplomacy_acts.perform(game, "denounce", other_seat, target)
        assert not act["ok"], act
        # And against somebody else it is open again.
        third = diplomacy_acts.available(game, other_seat, seat)
        assert dict((a.id, ok) for a, ok, _w in third)["denounce"], third
        return (f"denouncing {target} is shut from every court "
                f"({offered['denounce'][1]}) and open against another")
