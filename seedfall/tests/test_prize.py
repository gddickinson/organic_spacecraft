"""Striking colours — the outcome between "kill it" and "let it go".

The endgame sweep found the fighting sound and the arc around it thin:
nothing between destruction and escape, recovered tonnage never priced, and
`nonlethal` — the starting captain's own weapon trait — read by nothing.
These play the middle outcome end to end: a beaten crew strikes, the captain
decides once, and every branch of the decision moves the ledgers it names.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import aftermath as aftermath_sim
from ..sim import battle_state
from ..sim import combat as combat_sim
from ..sim import consorts as consort_sim
from ..sim import damage as damage_sim
from ..sim import prize as prize_sim
from ..sim.encounters import make_enemy
from ..sim.ship import hull_pct
from .harness import Suite


def _battle(seed: str, faction: str = "concordat", difficulty: float = 0.8):
    game = new_game(seed)
    rng = RNG(seed)
    enemy = make_enemy(rng, faction, difficulty)
    b = combat_sim.start(game.ship, game.ship_stats, enemy,
                         bonuses=game.bonuses, officers=game.officers,
                         rep=0.0, game=game, rng=rng)
    b.enemy_faction = faction
    return game, b, rng


def _wound(b, share: float = 0.3) -> None:
    """Open the enemy hull to the point a crew starts thinking about it."""
    for layer in b.enemy.ship.layers:
        layer.hp = round(layer.max * share)


def run(suite: Suite) -> None:
    check = suite.check

    @check("a beaten crew strikes its colours, and the fight ends on it")
    def _():
        game, b, rng = _battle("strike")
        _wound(b)
        assert hull_pct(b.enemy.ship) < prize_sim.STRIKE_HULL
        for _turn in range(40):
            if b.over:
                break
            b.enemy.resolve = prize_sim.STRIKE_AT - 4
            combat_sim.take_turn(b, {"type": "brace"}, rng)
        assert b.result == "struck", (
            f"forty turns against a broken, spent crew: {b.result}")
        assert any("strikes their colours" in text for _t, text, _k in b.log)
        return f"struck on turn {b.turn}; the log says so"

    @check("the Bloom never strikes — it has nobody to strike with")
    def _():
        game, b, rng = _battle("no-strike", faction="bloom")
        b.no_parley = True
        _wound(b, 0.2)
        for _turn in range(30):
            if b.over:
                break
            b.enemy.resolve = prize_sim.STRIKE_AT - 4
            combat_sim.take_turn(b, {"type": "brace"}, rng)
        assert b.result != "struck", "a mass surrendered"
        return f"thirty turns and no colours: {b.result or 'still fighting'}"

    @check("a prize crew sails her home, and the fleet is one hull longer")
    def _():
        game, b, rng = _battle("take-prize")
        battle_state.finish(b, "struck")
        was_crew = game.ship.crew
        was_fleet = len(game.fleet)
        uids = {s.uid for s in game.fleet} | {game.ship.uid}
        told = prize_sim.take(game, b)
        assert told["ok"], told.get("why")
        assert len(game.fleet) == was_fleet + 1
        hull = told["ship"]
        assert hull.uid not in uids, "the prize kept a uid the fleet knows"
        assert hull.escort and hull.docked_at is None
        assert game.ship.crew == was_crew - told["crew"]
        assert hull in consort_sim.escorts_of(game) or any(
            s.uid == hull.uid for s in game.fleet if s.escort), (
            "taken, and not sailing in company")
        # One decision per engagement.
        again = prize_sim.strip(game, b)
        assert not again["ok"], "stripped a hull already taken"
        return (f"{hull.name} under a prize crew of {told['crew']}, "
                "sailing in company; the decision is spent")

    @check("no hands to spare, no prize — and the reason is named")
    def _():
        game, b, rng = _battle("no-hands")
        battle_state.finish(b, "struck")
        need = prize_sim.crew_needed(b.enemy.ship)
        game.ship.crew = need
        ok, why = prize_sim.can_take(game, b)
        assert not ok and why, "took a prize with nobody left to con the flag"
        told = prize_sim.take(game, b)
        assert not told["ok"]
        return f"refused: '{why}'"

    @check("stripping her holds is priced, and letting her go is remembered")
    def _():
        game, b, rng = _battle("strip-prize")
        battle_state.finish(b, "struck")
        aboard_before = dict(game.ship.cargo)
        told = prize_sim.strip(game, b)
        assert told["ok"] and told["moved"], "nothing came across"
        assert told["worth"] > 0, "tonnage moved and nobody priced it"
        gained = sum(game.ship.cargo.values()) - sum(aboard_before.values())
        assert gained > 0

        game2, b2, _ = _battle("release-prize")
        battle_state.finish(b2, "struck")
        was = game2.rep.get("concordat", 0.0)
        out = prize_sim.release(game2, b2)
        assert out["ok"]
        assert game2.rep.get("concordat", 0.0) > was, (
            "mercy moved nothing on the ledger")
        return (f"stripped {round(sum(told['moved'].values()))} t worth "
                f"{told['worth']:,.0f}; releasing bought "
                f"{game2.rep['concordat'] - was:+.1f} standing")

    @check("nonlethal means what the glossary says: nobody dies")
    def _():
        # `data/part_types` has always glossed the trait "never kills crew",
        # and `damage._breach` never heard of it — the Photic Flash Organ,
        # the one armament every new captain starts with, vented crew
        # exactly like a railgun.
        game, b, rng = _battle("gentle")
        crew = b.enemy.ship.crew
        total = sum(l.max for l in b.enemy.ship.layers)
        damage_sim._apply_to_layers(b, b.enemy, total * 2, ("nonlethal",), rng)
        assert all(l.hp <= 0 for l in b.enemy.ship.layers)
        assert b.enemy.ship.crew == crew, (
            f"a nonlethal weapon vented {crew - b.enemy.ship.crew} crew")

        game2, b2, rng2 = _battle("harsh")
        crew2 = b2.enemy.ship.crew
        total2 = sum(l.max for l in b2.enemy.ship.layers)
        damage_sim._apply_to_layers(b2, b2.enemy, total2 * 2, (), rng2)
        assert b2.enemy.ship.crew < crew2, (
            "an ordinary breach spared everyone — the control proves nothing")
        return (f"hull opened twice over: nonlethal spares all {crew}, "
                f"bare breach takes {crew2 - b2.enemy.ship.crew}")

    @check("a struck hull sits between driving off and killing, in standing")
    def _():
        costs = {}
        for result in ("driven-off", "struck", "destroyed"):
            game, b, rng = _battle(f"cost-{result}")
            battle_state.finish(b, result)
            was = game.rep.get("concordat", 0.0)
            aftermath_sim.resolve(game, b, rng)
            costs[result] = was - game.rep.get("concordat", 0.0)
        assert 0 < costs["driven-off"] < costs["struck"] < costs["destroyed"], (
            costs)
        # And taking the prize afterwards lands the total beside a kill.
        game, b, rng = _battle("cost-taken")
        battle_state.finish(b, "struck")
        was = game.rep.get("concordat", 0.0)
        aftermath_sim.resolve(game, b, rng)
        prize_sim.take(game, b)
        taken_total = was - game.rep.get("concordat", 0.0)
        assert costs["struck"] < taken_total, (
            "taking the hull cost nothing beyond the striking")
        return (f"driven-off {costs['driven-off']:g} < struck "
                f"{costs['struck']:g} < destroyed {costs['destroyed']:g}; "
                f"struck-and-taken {taken_total:g}")
