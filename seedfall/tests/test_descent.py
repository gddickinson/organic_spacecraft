"""Putting a party on a world: the craft that can, and what she carries.

`sim/landing.py` did the arithmetic years ago and wrote it down: **a
starship in this game cannot land on a world** — a rocky world pulls a
hundred and forty times harder than the drive can push — and that is why a
landing party goes down in a lander while the ship holds orbit. The lander
was the one thing in that sentence nobody owned: a word in the expedition's
prose, a fixed pad square on its 7×7 zone, and some biomass out of the hold.

Now it is a craft on the cradle. The claims:

- **A hull carries one from the first day**, beside the fighter, in the
  second of the two cradles a NAVIS can work.
- **Her drive is what decides where she can go down** — the same comparison
  the ship's own landing makes, with a reserve for lifting off a full hold
  again, so a WASP manages a moon and a heavy world wants a lander built for
  it.
- **The party is her seats and the supplies are her hold**, and both refuse
  by the number rather than silently truncating.
- **She is on the world while they are**: not the ship's boat, not something
  a yard can reach, and back on the cradle when they come up.
- **No lander, no landing.** The expedition door refuses in the words of the
  craft that could not do it.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.craft import CRAFT, CRAFT_BY_ID, LIFT_RESERVE
from ..sim import (craft as craft_sim, crossing, descent, fieldwork,
                   hangar, landing)
from ..world.planets import BODY_KINDS
from .harness import Suite


def _with_ground(seed: str = "descent"):
    """A chronicle in a system with something to stand on, surveyed."""
    for n in range(12):
        game = new_game(f"{seed}-{n}")
        found = [i for i, b in enumerate(game.system.bodies)
                 if BODY_KINDS[b.kind][2]]
        if found:
            game.ship.cargo["biomass"] = 80
            body = game.system.bodies[found[0]]
            body.surveyed = True
            return game, found[0], body
    raise AssertionError("no landable body in twelve sectors")


def _lander(game):
    return next(c for c in craft_sim.aboard(game)
                if craft_sim.kind_of(c).role == "lander")


def run(suite: Suite) -> None:
    check = suite.check

    @check("a hull cannot land, and the lander she carries can")
    def _():
        game, index, body = _with_ground("carried")
        pod = _lander(game)
        kind = craft_sim.kind_of(pod)
        assert kind.lands and kind.seats > 1, kind
        assert hangar.cradles(game.ship) == 2, "no room for both"
        assert len(craft_sim.aboard(game)) == 2
        # The hull's own arithmetic, unchanged: a world is not for ships.
        assert landing.kind_allows(body), body.kind
        ok, why = descent.can_land(game, pod, body)
        assert ok, why
        # A gas giant is neither landable nor liftable-from.
        giant = next((b for b in game.system.bodies
                      if not BODY_KINDS[b.kind][2]), None)
        if giant is not None:
            shut, said = descent.can_land(game, pod, giant)
            assert not shut and "stand on" in said, said
        return (f"{pod.name} on the second cradle: {kind.seats} seats, "
                f"{kind.hold_t:g} t of hold, {kind.days:g} days of air, and "
                f"she lifts off {descent.lifts_from(pod):.2f} g")

    @check("her drive decides where she can go down, class by class")
    def _():
        game, _index, _body = _with_ground("drive")
        rows = []
        for kind in CRAFT:
            craft = craft_sim.Carried(id=9, class_id=kind.id, name=kind.name,
                                      hp=kind.hull, fuel=kind.fuel_t)
            ceiling = descent.lifts_from(craft)
            assert abs(ceiling - kind.thrust_g / LIFT_RESERVE) < 1e-9
            rows.append((kind.name, ceiling, kind.lands))
        heavy = {name: g for name, g, _l in rows}
        assert heavy["DORY"] < heavy["WASP"] < heavy["CATAPHRACT"], heavy
        # And the refusal names the world's own pull.
        game.craft = [craft_sim.Carried(id=1, class_id="dory", name="Dory",
                                        hp=110, fuel=10.0)]
        heavy_world = max(game.system.bodies,
                          key=lambda b: (BODY_KINDS[b.kind][2], b.gravity))
        if heavy_world.gravity > heavy["DORY"]:
            shut, said = descent.can_land(game, game.craft[0], heavy_world)
            assert not shut and "pulls" in said and "lifts off" in said, said
        return "; ".join(f"{name} to {g:.2f} g" for name, g, _l in rows)

    @check("the party is her seats and the supplies are her hold")
    def _():
        game, index, body = _with_ground("seats")
        pod = _lander(game)
        kind = craft_sim.kind_of(pod)
        room = descent.party_room(pod)
        assert room == kind.seats - 1, (room, kind.seats)
        crowd = [o.id for o in game.officers] * 5
        refused = fieldwork.launch_expedition(game, index, crowd[:room + 2])
        assert not refused["ok"] and "besides the pilot" in refused["why"]
        got = fieldwork.launch_expedition(game, index,
                                          [o.id for o in game.officers[:2]],
                                          load=2)
        assert got["ok"], got
        exp = game.expedition
        assert exp.craft == pod.id, (exp.craft, pod.id)
        assert exp.supply <= kind.days, (exp.supply, kind.days)
        assert exp.supply > 0
        return (f"{room} down besides the pilot, {exp.supply:g} days of "
                f"supply in a hold of {kind.hold_t:g} t")

    @check("she is on the world while they are, and comes up with them")
    def _():
        game, index, body = _with_ground("aground")
        pod = _lander(game)
        fuel = pod.fuel
        assert fieldwork.launch_expedition(
            game, index, [o.id for o in game.officers[:1]])["ok"]
        assert pod.state == descent.DOWN and pod.pilot
        assert descent.on_the_ground(game) is pod
        assert pod.fuel < fuel, "a descent cost her nothing"
        spent = fuel - pod.fuel
        # Not the boat, and not a thing a yard can reach.
        assert not any(c is pod for c in [crossing.the_boat(game)] if c)
        assert not hangar.can_mend(game, pod)[0]
        assert "on a world" in hangar.can_sell(game, pod)[1]
        assert not descent.can_land(game, pod, body)[0]
        game.expedition.over = True
        fieldwork.conclude_expedition(game)
        assert pod.state == "cradled" and pod.pilot == ""
        assert descent.on_the_ground(game) is None
        return (f"{pod.name} down on {body.name} and up again, "
                f"{spent:.1f} t of her tank spent and the cradle's hold "
                "filling her back up")

    @check("no lander, no landing — in the words of the craft that could not")
    def _():
        game, index, body = _with_ground("bare")
        pod = _lander(game)
        game.craft = [c for c in game.craft if c is not pod]
        refused = fieldwork.launch_expedition(
            game, index, [o.id for o in game.officers[:1]])
        assert not refused["ok"], refused
        # The WASP *is* built to set down — the user asked for that — so the
        # reason a party cannot go down in her is her single seat, which is
        # the refusal that belongs to the craft actually aboard.
        assert "seats 1" in refused["why"], refused["why"]
        # And with nothing at all on the cradle, the hull says so itself.
        game.craft = []
        bare = descent.why_none(game, body)
        assert "no craft at all" in bare, bare
        # A wrecked lander is a reason of its own.
        game.craft = [craft_sim.Carried(id=3, class_id="isopod", name="Pod",
                                        hp=0, fuel=16.0)]
        assert "wrecked" in descent.why_none(game, body)
        return (f"“{refused['why'][:56]}…”; and with an empty cradle, "
                f"“{bare[:44]}…”")
