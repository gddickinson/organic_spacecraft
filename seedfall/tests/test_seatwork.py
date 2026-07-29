"""Whichever way you order a turn, the crew still hold their seats.

`take_turn` takes two shapes of action. `{"type": "station", "order": ...}` is
the crew-station system: your seat runs your order and officers hold the other
two. `{"type": "fire", "weapon_id": ...}` and its siblings are the older
shape, kept because the battle screen still uses them — the firing picture's
per-mount buttons and the ability buttons both send one.

The older shape never ran the seats. Firing a named mount meant nobody flew
the ship that turn and nobody stood in the engineering section: measured on a
hull at 30 heat, the turn ended at 24.0 through the old door and 19.44 through
the new, and `helm_order` was still `None` afterwards. So the whole of
priority-three — positional combat with crew stations — switched itself off
whenever a captain picked a mount instead of ordering a salvo.

Only `move` had been migrated, which is how it stayed hidden: the obvious
comparison, salvo against salvo, agrees whatever you do, because with a light
hull the seats have nothing to show and with a heavy one the heat ceiling
erases the difference before it can be read.

The claims:

- **Both shapes leave the same state.** The general one.
- **The seats run on every turn that spends one.**
- **The captain's own seat is not double-run.**
- **A turn ordered either way still ends the same fight the same way.**

One consequence worth knowing: the helm runs before the guns, so a mount that
bears when you press the button may not bear when the shot goes. That was
already true of the station path; it is now true of the named-mount buttons
too, which is the point of the change rather than a side effect of it.
"""

from __future__ import annotations

import collections

from ..core.rng import RNG
from ..core.state import new_game
from ..data.parts import PARTS
from ..sim import combat, encounters, stations as st_mod
from ..sim.ship import build_layers, make_ship, stats
from .harness import Suite

HEAVY = [w.id for w in sorted([p for p in PARTS if p.slot == "weapon"],
                              key=lambda w: -w.wpn.heat)[:5]]


def _engaged(seed: str, heavy: bool = False, strength: float = 1.5):
    game = new_game(seed)
    if heavy:
        ship = make_ship("bastion", HEAVY + ["reaction_organ"])
        cargo = {"ore": 300, "alloy": 300, "volatiles": 300, "silicon": 300}
    else:
        ship = make_ship("navis", ["slug_battery", "mag_lance",
                                   "reaction_organ", "opsin_eyes", "chemo_gut"])
        cargo = {"ore": 300}
    build_layers(ship, game.bonuses)
    game.ship = ship
    ship.cargo = dict(cargo)
    game.recompute()
    rng = RNG(f"s-{seed}")
    battle = combat.start(ship, stats(ship),
                          encounters.make_enemy(rng, "concordat", strength),
                          rng=rng, game=game, officers=game.officers)
    return game, battle, rng


def _turn(seed: str, action: dict, heat: float = 30.0) -> dict:
    game, battle, rng = _engaged(seed)
    battle.player.ship.heat = heat
    act = dict(action)
    if act.get("type") == "fire":
        act["weapon_id"] = battle.player.st.weapons[0].id
    combat.take_turn(battle, act, rng)
    return {"heat": round(battle.player.ship.heat, 2),
            "helm_order": battle.player.helm_order,
            "station": battle.player.station}


def run(suite: Suite) -> None:
    check = suite.check

    @check("the seats run whichever shape of order spends the turn")
    def _():
        # The general question. Every action that consumes a turn must leave
        # the ship flown and the engineering section stood in.
        gunnery = _turn("shape", {"type": "station", "order": "aimed"})
        for label, action in (("fire a named mount", {"type": "fire"}),
                              ("fire everything", {"type": "salvo"})):
            older = _turn("shape", action)
            assert older["helm_order"] is not None, (
                f"{label}: nobody flew the ship — `helm_order` is still None "
                "after a turn that spent a turn")
            assert abs(older["heat"] - gunnery["heat"]) < 0.01, (
                f"{label}: the turn ended at {older['heat']} heat against "
                f"{gunnery['heat']} for the same act ordered as a station — "
                "the engineering section was not run")
        return (f"heat {gunnery['heat']} and the helm answering, by either "
                "shape of order")

    @check("the captain's own seat is run once, not twice")
    def _():
        # `_run_seats` is called with the seat the captain is in, so their own
        # station must not also be worked by an officer. Bracing is the case
        # that shows it: it is an engineering act on the older path.
        braced = _turn("twice", {"type": "brace"})
        assert braced["station"] == "engineering", braced
        # Bracing vents once for the brace and once for the section standing
        # unattended would be two vents; the section is *attended*, so the
        # officer's unattended vent must not also apply.
        game, battle, rng = _engaged("twice")
        battle.player.ship.heat = 30.0
        vent = battle.player.st.vent
        before = battle.player.ship.heat
        combat.take_turn(battle, {"type": "brace"}, rng)
        shed = before - battle.player.ship.heat
        assert battle.player.helm_order is not None, (
            "bracing did not run the seats — nobody flew the ship")
        # Exactly three full vents: the brace itself, the engineering section
        # standing *attended* because that is where the captain is, and the
        # end of the turn. An upper bound passed everything: a section that
        # was skipped, or run at the lower unattended rate, both shed less.
        assert abs(shed - vent * 3) < 0.01, (
            f"bracing shed {shed:.1f} against three vents of {vent:g} — "
            f"{'the section was skipped or run unattended' if shed < vent * 3 else 'it was run twice'}")
        return f"bracing sheds {shed:.1f}, exactly three vents of {vent:g}"

    @check("an engagement ends the same way whichever shape orders it")
    def _():
        # End to end: the same fight, ordered both ways, thirty seeds.
        def play(action, heavy):
            out = collections.Counter()
            hull = []
            for trial in range(30):
                game, battle, rng = _engaged(f"end{trial}", heavy=heavy,
                                             strength=2.0)
                turns = 0
                while not battle.over and turns < 60:
                    act = dict(action)
                    if act.get("type") == "fire":
                        act["weapon_id"] = battle.player.st.weapons[0].id
                    combat.take_turn(battle, act, rng)
                    turns += 1
                out[battle.result if battle.over else "timeout"] += 1
                hull.append(sum(l.hp for l in battle.enemy.ship.layers)
                            / max(1e-9, sum(l.max
                                            for l in battle.enemy.ship.layers)))
            return out, sum(hull) / len(hull)

        rows = []
        for heavy in (False, True):
            older, hull_a = play({"type": "salvo"}, heavy)
            newer, hull_b = play({"type": "station", "order": "salvo"}, heavy)
            assert older == newer, (
                f"{'heavy' if heavy else 'light'} hull: the same fight ends "
                f"{dict(older)} one way and {dict(newer)} the other")
            assert abs(hull_a - hull_b) < 0.005, (hull_a, hull_b)
            rows.append(f"{'heavy' if heavy else 'light'} {dict(newer)}")
        return " · ".join(rows)

    @check("firing a named mount still fires that mount")
    def _():
        # The seats must be added to the older path without displacing what it
        # was for: a captain who picks a mount fires *that* mount.
        # Neither mount bears at the opening — the hull starts 60 degrees off
        # and both arcs are shut, so a named shot legitimately does nothing
        # until somebody turns the ship. Fly into position first, the way a
        # captain would, then name the mount.
        from . import captain_ai
        game, battle, rng = _engaged("named")
        weapon = None
        for _ in range(12):
            bearing = [w for w in battle.player.st.weapons
                       if w.wpn.bears_at(battle.band) <= 0.5
                       and st_mod.bears_on(battle.player, battle.enemy, w)[0]]
            if bearing:
                weapon = bearing[0]
                break
            combat.take_turn(battle, {
                "type": "station",
                "order": captain_ai.helm_order_for(battle.player,
                                                   battle.enemy)}, rng)
            if battle.over:
                break
        assert weapon is not None, "no mount ever came to bear in twelve turns"

        marked = len(battle.log)
        before = sum(l.hp for l in battle.enemy.ship.layers)
        combat.take_turn(battle, {"type": "fire", "weapon_id": weapon.id}, rng)
        after = sum(l.hp for l in battle.enemy.ship.layers)
        # A battle log line is (turn, text, kind).
        named = [line[1] for line in battle.log[marked:]
                 if weapon.name.lower() in str(line[1]).lower()]
        # Either it fired or it said why it could not — the helm runs before
        # the guns, on this path as on the station path, so the ship may have
        # turned out from under the shot. Both outcomes name the mount the
        # captain picked, which is what this is checking.
        assert named or after < before, (
            f"nothing in the log mentions {weapon.name} and the enemy took no "
            f"damage: {[l[1] for l in battle.log[marked:]]}")
        assert battle.player.station == "gunnery", battle.player.station
        assert battle.player.helm_order is not None, (
            "the named shot went through and nobody flew the ship")
        return f"{weapon.name} fired, the captain at gunnery, the helm manned"

    @check("hailing and running do not spend a turn at the seats")
    def _():
        # Parley and flight resolve the engagement rather than working it, so
        # they must not quietly run the crew as well.
        for choice in ("hail", "flee"):
            game, battle, rng = _engaged(f"talk-{choice}")
            battle.player.ship.heat = 30.0
            was = battle.player.helm_order
            combat.take_turn(battle, {"type": choice}, rng)
            assert battle.player.helm_order == was, (
                f"{choice} ran the helm — it is a way out of the engagement, "
                "not a turn of it")
        return "hail and disengage leave the seats alone"
