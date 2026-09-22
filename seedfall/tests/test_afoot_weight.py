"""Afoot's weight: nothing in the Verge makes a floor pull.

- **every deck weighs what its structure gives it**: a hull and a quay are
  weightless, a Habitat Girdle's berths four-tenths, a ring's levels and a
  drum's floor spun, anything on the ground its world's own gravity;
- **weightless, the untrained go hand over hand** — twice the cost of a
  step — shoot unbraced, and a gun's kick sets them drifting; Zero-G skill
  or magnetic boots put them right, and the people who live aboard are at
  home in it;
- **a heavy world slows everybody**;
- **a ring's floor closes on itself**: a walk off one end comes on at the
  other, the short way round — a step off either end, a whole circuit
  either way, and sight, reach and a grenade's burst across the seam as
  anywhere else on it.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.chassis import CHASSIS_BY_ID
from ..sim import (afoot, afoot_fight, afoot_gen, afoot_hullplan, afoot_map,
                   afoot_people, afoot_plans, afoot_program, afoot_sites,
                   places)
from ..sim.afoot_state import Actor, party
from . import afoot_kit
from .harness import Suite


def _stand(walk, me, g: float):
    walk.decks[me.deck].g = g
    walk.version += 1


def run(suite: Suite) -> None:
    check = suite.check

    @check("every deck weighs what its structure gives it")
    def _():
        game = afoot_kit.settle(new_game("weight-decks"))
        hull = afoot_plans.plan(game, afoot_sites.own_hull(game))
        # Weightless, but for the deck a Habitat Girdle's berths are on.
        assert all(d.g in (0.0, 0.4) for d in hull.decks), [
            d.g for d in hull.decks]
        chassis = CHASSIS_BY_ID["navis"]
        fit = afoot_program.typical_fit(RNG("g"), chassis) + ["crew_girdle"]
        wants = afoot_program.ship(chassis, fit)
        painted = afoot_hullplan.decks(RNG("g"), chassis, wants, "grown")
        girdled = afoot_gen.assemble(RNG("g"), painted)
        assert any(d.g == 0.4 for d in girdled.decks), "no spun berths"
        seen = {}
        for place in places.in_system(game):
            if place.kind == "ship" or not places.livable(place):
                continue
            laid = afoot_plans.plan(game, afoot_sites._from_place(game,
                                                                  place))
            for deck in laid.decks:
                name = deck.name
                if name.startswith(("The first ring", "The second ring",
                                    "The ring")):
                    assert deck.wrap and 0.5 < deck.g <= 1.0, (name, deck.g)
                    seen["ring"] = deck.g
                elif name == "Inside the drum":
                    assert deck.wrap and deck.g >= 0.9, deck.g
                    seen["drum"] = deck.g
                elif name in ("The spine", "The quay", "The axis", "The hub"):
                    assert deck.g == 0, (place.name, name, deck.g)
                    seen["weightless"] = 0.0
        assert {"ring", "drum", "weightless"} <= set(seen), seen
        return (f"hulls weightless, a girdle's berths 0.4 g, rings "
                f"{seen['ring']} g and unrolled, a drum's floor "
                f"{seen['drum']} g")

    @check("weightless, the untrained go hand over hand and drift; boots or Zero-G put it right")
    def _():
        game = afoot_kit.fresh("weight-drift")
        site = next(s for s in afoot.sites(game) if s.kind == "ship")
        assert afoot.begin(game, site.key, ["captain"])["ok"]
        walk = game.afoot
        me = party(walk)[0]
        _stand(walk, me, 0.0)
        me.zero_g, me.kit = -3, [k for k in me.kit if k != "mag_boots"]
        near = afoot_map.reach(walk, me, 6)
        untrained = max(near.values())
        step = afoot_map.price(walk, me.deck, [(me.x + 1, me.y)], me)
        g = afoot_map.ground(walk, me.deck)
        taken = {(a.x, a.y) for a in walk.actors if a.deck == me.deck}
        spot = next((me.x + dx, me.y + dy) for dx, dy in afoot_map.STEPS
                    if g.passable(me.x + dx, me.y + dy)
                    and (me.x + dx, me.y + dy) not in taken)
        foe = Actor(id=9990, name="Target", side="npc", folk="raider",
                    deck=me.deck, x=spot[0], y=spot[1], hp=50, hp_max=50,
                    mood="hostile", stats={"str": 7, "dex": 7, "end": 7,
                                           "int": 7, "edu": 7, "soc": 7})
        walk.actors.append(foe)
        me.weapon = "shotgun"
        drift = afoot_fight.terms(game, walk, me, foe)
        me.kit = me.kit + ["mag_boots"]
        braced = afoot_fight.terms(game, walk, me, foe)
        booted = afoot_map.price(walk, me.deck, [(me.x + 1, me.y)], me)
        assert step == 2 and booted == 1, (step, booted)
        assert drift["ok"] and braced["ok"], (drift["why"], braced["why"])
        assert braced["extra"] - drift["extra"] == -afoot_fight.UNBRACED
        me.kit = [k for k in me.kit if k != "mag_boots"]
        me.mp = 6
        afoot_fight.attack(game, walk, me, foe, RNG("kick"))
        assert me.mp == 0, "the kick of a shotgun set nobody drifting"
        assert afoot_map.at_home(foe), "a raider aboard is not at home in it"
        return (f"a step costs {step} untrained, {booted} in boots; unbraced "
                f"{afoot_fight.UNBRACED:+d} to hit; {untrained} of movement "
                "spent to reach six squares' worth")

    @check("a heavy world slows everybody, and a ring's floor closes on itself")
    def _():
        game = afoot_kit.fresh("weight-heavy")
        site = next(s for s in afoot.sites(game) if s.kind == "ship")
        assert afoot.begin(game, site.key, ["captain"])["ok"]
        walk = game.afoot
        me = party(walk)[0]
        _stand(walk, me, 1.0)
        light = afoot_people.move_of(game, me)
        _stand(walk, me, 2.6)
        heavy = afoot_people.move_of(game, me)
        assert heavy < light, (light, heavy)
        game.afoot = None
        game = new_game("weight-ring")
        port = next(s for s in afoot_sites.here(game) if s.kind == "port")
        object.__setattr__(game.system.port, "capital", True)
        assert afoot.begin(game, port.key, ["captain"])["ok"]
        walk = game.afoot
        ring = next(i for i, d in enumerate(walk.decks) if d.wrap)
        me = party(walk)[0]
        g = afoot_map.ground(walk, ring)
        row = next(y for y in range(walk.decks[ring].h)
                   if g.passable(0, y) and g.passable(walk.decks[ring].w - 1,
                                                       y))
        me.deck, me.x, me.y = ring, 1, row
        wide = walk.decks[ring].w
        route = afoot_map.path(walk, me, wide - 2, row)
        assert route and len(route) <= 4, len(route)
        # Off either end, a square at a time, and all the way round.
        me.x = wide - 1
        assert afoot.move(game, me.id, wide, row)["ok"] and me.x == 0
        assert afoot.move(game, me.id, -1, row)["ok"] and me.x == wide - 1
        corridor = all(afoot_map.ground(walk, ring).passable(x, row)
                       for x in range(wide))
        if corridor:
            for a in walk.actors:       # nobody to step round on the way
                if a is not me and a.deck == ring and a.y == row:
                    a.status = "gone"
            for sign in (1, -1):
                for _n in range(wide):
                    me.mp = 99          # no round passes, so nobody hails
                    got = afoot.move(game, me.id, me.x + sign, row)
                    assert got["ok"] and got["moved"] == 1, (sign, me.x, got)
                assert me.x == wide - 1, (sign, me.x)
        # Seen, reached and measured across the seam as anywhere else.
        me.x = wide - 1
        assert afoot_map.sees(walk, ring, wide - 1, row, 2, row)
        assert (2, row) in afoot.visible(walk, ring)
        assert afoot_map.distance(wide - 1, row, 2, row, wide) == 3
        other = Actor(id=9991, name="Across", side="npc", folk="patron",
                      deck=ring, x=0, y=row, hp=9, hp_max=9)
        assert afoot_map.apart(walk, me, other) == 1
        return (f"moves {light} → {heavy} at 2.6 g; round the ring's seam "
                f"in {len(route)} steps, not {wide - 3}; off both ends"
                + (" and all the way round, both ways" if corridor else "")
                + "; seen and reached across it")
