"""Waste heat, and whether a warship can fire the guns it was built to carry.

Heat had no ceiling. A Bastion firing the five heavy mounts it has slots for
makes 74 heat a turn against a rated cap of 50 and a vent of 6, so heat ran
68 → 132 → 187 → 243 → 279 and kept climbing. The overheat penalty is a share
of how far over the cap you are, so it compounded: resolve fell 26, then 39,
then 53, then 65, and the ship routed on turn five **at 93% hull**, beaten by
its own radiators while the enemy did almost nothing.

There was no way back either. Cooling from 279 at six a turn takes 38 turns,
which is longer than the fight, so `vent` — the order that exists for exactly
this — could never catch up and cost you the gunnery seat for nothing. Every
thermal decision in the game was therefore fake: salvo's "far more heat", the
aimed shot's "less heat", holding fire to cool, both power routings.

`combat.cook()` holds heat at a multiple of the cap. Measured over 40 fights
with a heavy hull, favourable outcomes went from 7/40 to 26/40 and kills from
4 to 11 — and salvo against aimed became a real choice rather than a trap:
salvo is decisive and swingy (11 kills, 14 routs), aimed is attritional
(24 driven off, 2 kills).

The claims:

- **Heat is bounded**, so the penalty is a steady pressure and not a spiral.
- **A cooked hull can be brought back** inside the length of an engagement.
- **A warship can win with its own armament.**
- **Overheating still hurts** — this is a ceiling, not an amnesty.
- **A hull that never overheats is untouched by any of it.**
"""

from __future__ import annotations

import collections

from ..core.rng import RNG
from ..core.state import new_game
from ..data.parts import PARTS
from ..sim import combat, encounters
from ..sim import stations as st_mod
from ..sim.ship import build_layers, make_ship, stats
from .harness import Suite
from . import captain_ai

#: The five hottest mounts in the game — what a Bastion is built to carry.
HEAVY = [w.id for w in sorted([p for p in PARTS if p.slot == "weapon"],
                              key=lambda w: -w.wpn.heat)[:5]]


def _warship(seed: str):
    """A Bastion with the heavy battery, and magazines for all of it."""
    game = new_game(seed)
    ship = make_ship("bastion", HEAVY + ["reaction_organ"])
    build_layers(ship, game.bonuses)
    game.ship = ship
    ship.cargo = {"ore": 300, "alloy": 300, "volatiles": 300, "silicon": 300}
    game.recompute()
    return game, ship


def _explorer(seed: str):
    """The hull a chronicle opens with: two light mounts, nothing hot."""
    game = new_game(seed)
    ship = make_ship("navis", ["slug_battery", "mag_lance", "reaction_organ",
                               "opsin_eyes", "chemo_gut"])
    build_layers(ship, game.bonuses)
    game.ship = ship
    ship.cargo = {"ore": 200}
    game.recompute()
    return game, ship


def _engage(game, ship, seed: str, strength: float = 2.0):
    rng = RNG(f"th-{seed}")
    return combat.start(ship, stats(ship),
                        encounters.make_enemy(rng, "concordat", strength),
                        rng=rng, game=game, officers=game.officers), rng


def _burn(seed: str, cap_turns: int = 40):
    """Fire everything every turn and watch the thermals."""
    game, ship = _warship(seed)
    battle, rng = _engage(game, ship, seed)
    rated = battle.player.st.heat_cap
    heats, drops = [], []
    was = battle.player.resolve
    turn = 0
    while not battle.over and turn < cap_turns:
        combat.take_turn(battle, {"type": "station", "order": "salvo"}, rng)
        turn += 1
        heats.append(battle.player.ship.heat)
        drops.append(was - battle.player.resolve)
        was = battle.player.resolve
    return rated, heats, drops, battle


def run(suite: Suite) -> None:
    check = suite.check

    @check("a hull's heat cannot climb without limit")
    def _():
        # Measured against a multiple written here, not against the constant
        # that produces it — raising the ceiling has to be re-measured rather
        # than silently agreeing with itself.
        worst = 0.0
        for seed in range(8):
            rated, heats, _drops, _b = _burn(f"cap{seed}")
            assert rated > 0, rated
            worst = max(worst, max(heats) / rated)
        assert worst < 3.5, (
            f"firing continuously drove heat to {worst:.1f}× the rated cap — "
            "with no ceiling the overheat penalty compounds and the hull "
            "routs itself")
        return f"peak heat reached {worst:.2f}× the rated cap over 8 fights"

    @check("the overheat penalty is a pressure and not a spiral")
    def _():
        # It used to accelerate: −26, −39, −53, −65 on consecutive turns,
        # because the penalty scales with an unbounded number.
        worst = 0.0
        for seed in range(8):
            _rated, _heats, drops, _b = _burn(f"spiral{seed}")
            worst = max(worst, max(drops) if drops else 0.0)
        assert worst < 30, (
            f"a single turn cost {worst:.0f} resolve — the penalty is running "
            "away with itself")
        return f"the worst single turn cost {worst:.1f} resolve across 8 fights"

    @check("a cooked hull can be brought back inside one engagement")
    def _():
        # The point of the ceiling: `vent` has to be able to catch up, or the
        # order is decoration. From 279 at six a turn it took 38 turns, which
        # is longer than any fight.
        game, ship = _warship("recover")
        st = stats(ship)

        class _Side:
            pass

        side = _Side()
        side.ship, side.st, side.route = ship, st, None
        ship.heat = st.heat_cap * 4          # hotter than the ceiling allows
        combat.cook(ship, st.heat_cap)
        turns = 0
        while ship.heat > st.heat_cap and turns < 30:
            st_mod.run_engineering(side, "vent", True, game.officers)
            turns += 1
        assert ship.heat <= st.heat_cap, (
            f"thirty turns of venting hard and the hull is still at "
            f"{ship.heat:.0f} against a cap of {st.heat_cap:.0f}")
        assert turns <= 6, (
            f"venting hard took {turns} turns to get back under the cap — "
            "longer than the fight it would be needed in")
        return f"{turns} turns of venting hard to come back under the cap"

    @check("a warship can win with the armament it was built to carry")
    def _():
        # Before the ceiling this hull routed itself: 7 favourable outcomes in
        # 40 and almost no kills, at full hull, every time.
        kinds = collections.Counter()
        for seed in range(40):
            game, ship = _warship(f"win{seed}")
            battle, rng = _engage(game, ship, f"win{seed}")
            turn = 0
            while not battle.over and turn < 60:
                combat.take_turn(battle,
                                 {"type": "station", "order": "salvo"}, rng)
                turn += 1
            kinds[battle.result if battle.over else "timeout"] += 1
        good = kinds["destroyed"] + kinds["driven-off"]
        assert good >= 18, (
            f"a Bastion with the heavy battery comes out ahead in {good} of "
            f"40 engagements: {dict(kinds)}")
        assert kinds["destroyed"] >= 4, (
            f"only {kinds['destroyed']} of 40 engagements ended with the "
            "enemy destroyed — the heavy battery cannot finish anything")
        return (f"{good}/40 favourable, {kinds['destroyed']} of them kills — "
                f"{dict(kinds)}")

    @check("overheating still hurts, because this is a ceiling not an amnesty")
    def _():
        rated, heats, drops, battle = _burn("hurts")
        assert max(heats) > rated, (
            f"heat peaked at {max(heats):.0f} against a cap of {rated:.0f} — "
            "the ceiling has quietly stopped hulls overheating at all")
        assert any(d > 1.0 for d in drops), (
            "a hull ran far over its rated cap and lost no resolve for it")
        return (f"heat reached {max(heats):.0f} over a cap of {rated:.0f}, and "
                f"it cost up to {max(drops):.1f} resolve a turn")

    @check("a hull that never overheats is untouched by any of this")
    def _():
        # The starting chassis carries two light mounts. It should never go
        # near the cap, and the ceiling should therefore never be consulted.
        peak = 0.0
        kinds = collections.Counter()
        for seed in range(20):
            game, ship = _explorer(f"light{seed}")
            battle, rng = _engage(game, ship, f"light{seed}")
            turn = 0
            while not battle.over and turn < 60:
                combat.take_turn(battle, captain_ai.orders(battle), rng)
                turn += 1
                peak = max(peak, battle.player.ship.heat
                           / max(1e-9, battle.player.st.heat_cap))
            kinds[battle.result if battle.over else "timeout"] += 1
        assert peak < 0.6, (
            f"the opening hull reached {peak:.0%} of its heat cap — it is "
            "supposed to be nowhere near thermally limited")
        assert kinds["timeout"] == 0, dict(kinds)
        return (f"the opening hull peaked at {peak:.0%} of cap over 20 fights "
                f"— {dict(kinds)}")

    @check("a single salvo cannot break the ceiling on its own")
    def _():
        # `_fire` is the only thing in the game that adds heat, so it is the
        # only place the clamp lives. This drives it directly and from an
        # already-hot hull, because the whole-fight checks cannot tell: they
        # read heat between turns, by which point venting has pulled it down.
        # 2.5 is written here rather than taken from HEAT_CEILING, so raising
        # the ceiling has to be re-measured instead of agreeing with itself.
        game, ship = _warship("volley")
        battle, rng = _engage(game, ship, "volley")
        rated = battle.player.st.heat_cap
        battle.player.ship.heat = rated * 1.9        # already nearly cooked
        for weapon in battle.player.st.weapons:
            combat._fire(battle, battle.player, battle.enemy, weapon.id, rng)
            assert battle.player.ship.heat <= rated * 2.5, (
                f"firing took the hull to {battle.player.ship.heat:.0f} "
                f"against a rated cap of {rated:.0f} — the firing path is not "
                "holding the ceiling")
        return (f"{len(battle.player.st.weapons)} mounts fired from nearly "
                f"cooked, peak {battle.player.ship.heat:.0f} on a "
                f"{rated:.0f} cap")

    @check("cook() is what holds the line, and it holds it both ways")
    def _():
        game, ship = _warship("cook")
        st = stats(ship)
        ship.heat = st.heat_cap * 9
        combat.cook(ship, st.heat_cap)
        assert ship.heat <= st.heat_cap * 3.5, ship.heat
        assert ship.heat >= st.heat_cap, (
            f"cook() pulled a badly overheated hull down to {ship.heat:.0f}, "
            f"under its own cap of {st.heat_cap:.0f} — that is a repair, not "
            "a ceiling")
        # It must not invent heat in a cold hull, nor allow a negative one.
        ship.heat = 3.0
        combat.cook(ship, st.heat_cap)
        assert ship.heat == 3.0, ship.heat
        ship.heat = -20.0
        combat.cook(ship, st.heat_cap)
        assert ship.heat == 0.0, ship.heat
        return "clamps the hot, leaves the cold, floors the negative"
