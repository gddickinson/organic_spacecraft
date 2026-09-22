"""A craft in an engagement: off the cradle under fire, and what it costs.

The cradle was fitted (`tests/test_craft.py`) and the fight was not: a hull
carrying a fighter fought every engagement in the game with the fighter
strapped to its flank, because `sim/craft.can_launch` refuses a sortie
during a battle and nothing else offered one. So the one thing a carrier is
for could not be done on the one occasion it is for.

`sim/craft_battle.py` is the answer, and these are its claims:

- **She launches into a running fight** and makes a run the same turn — real
  damage, through `sim/damage` where a shell goes, so a run strips layers
  and breaches hulls like anything else that hits.
- **They answer.** A hull still fighting turns its close-in fire on her, and
  the more mounts it has the harder that is to fly through.
- **Shot down is a person, not a corpse**: the craft is gone for good, the
  pilot comes home with a wound on them, and the nerve of the ship goes with
  her.
- **She can be called in**, which is the decision the whole thing is for: a
  cradle is cheaper than a pilot.
- **The fight ends and she comes home** — or, if the hull she flew off is
  lost, she goes with it.
- **A run is worth making.** Measured over eight engagements: what she adds,
  what it costs, and how often the gamble ends with an empty cradle.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import aftermath as aftermath_sim
from ..sim import combat as combat_sim
from ..sim import craft as craft_sim
from ..sim import craft_battle
from ..sim import encounters as enc_sim
from ..sim.ship import hull_pct
from . import captain_ai
from .harness import Suite

LAUNCH = {"type": "craft"}
HOME = {"type": "craft", "order": "home"}


def _fight(seed: str = "craft-battle", difficulty: float = 1.2,
           faction: str = "charter"):
    """A chronicle with a craft on the cradle, in an engagement."""
    game = new_game(seed)
    rng = RNG(seed)
    enemy = enc_sim.make_enemy(rng, faction, difficulty=difficulty)
    battle = combat_sim.start(game.ship, game.ship_stats, enemy,
                              bonuses=game.bonuses, officers=game.officers,
                              game=game, rng=rng)
    # Where the chronicle keeps it, which is what `sim` asks (`ui/window`).
    game.battle = battle
    return game, battle, rng


def _said(battle) -> str:
    return " ".join(text for _turn, text, _kind in battle.log)


def run(suite: Suite) -> None:
    check = suite.check

    @check("she goes off the cradle into a running fight, and runs in the same turn")
    def _():
        game, battle, rng = _fight("into-the-fight")
        craft = craft_sim.aboard(game)[0]
        # The cradle tab is not the door while the shooting is on.
        shut, why = craft_sim.can_launch(game, craft)
        assert not shut and "engagement" in why, why
        was = hull_pct(battle.enemy.ship)
        ok, _why, offered = craft_battle.may_launch(battle)
        assert ok and offered is craft, (ok, _why)
        combat_sim.take_turn(battle, LAUNCH, rng)
        assert craft.state == "out" and craft.pilot, craft
        assert craft.struck == 1, "launched and made no run"
        assert hull_pct(battle.enemy.ship) < was, "a run that did nothing"
        assert craft.name in _said(battle)
        # And the ship kept fighting while she was away: the seats ran.
        assert battle.turn > 1
        return (f"{craft.name} away on turn 1 with "
                f"{craft_sim.name_of(game, craft.pilot)} flying; "
                f"{battle.enemy_name} down to {hull_pct(battle.enemy.ship):.0%}")

    @check("only a certified pilot, a whole craft and a gun make a launch")
    def _():
        game, battle, _rng = _fight("refusals")
        craft = craft_sim.aboard(game)[0]
        refused = {}
        craft.hp = 0
        refused["wrecked"] = craft_battle.may_launch(battle)[1]
        craft.hp = craft_sim.kind_of(craft).hull
        craft.fuel = 0.0
        refused["dry"] = craft_battle.may_launch(battle)[1]
        craft.fuel = 6.0
        craft.class_id = "dory"          # a tender: seats, hold, no guns
        refused["unarmed"] = craft_battle.may_launch(battle)[1]
        craft.class_id = "wasp"
        craft.state = "out"
        refused["already out"] = craft_battle.may_launch(battle)[1]
        craft.state = "cradled"
        game.craft = []
        refused["no cradle"] = craft_battle.may_launch(battle)[1]
        assert all(refused.values()), refused
        assert len(set(refused.values())) == len(refused), refused
        # And a refusal spends nothing: the turn does not advance.
        turn = battle.turn
        combat_sim.take_turn(battle, LAUNCH, RNG("refused"))
        assert battle.turn == turn, "a refused launch spent the turn"
        return "; ".join(f"{k}: “{v[:28]}…”" for k, v in
                         list(refused.items())[:3])

    @check("they shoot back, and she can be called in before they get on her")
    def _():
        game, battle, rng = _fight("called-in", difficulty=1.6)
        craft = craft_sim.aboard(game)[0]
        kind = craft_sim.kind_of(craft)
        combat_sim.take_turn(battle, LAUNCH, rng)
        hurt = 0
        for _n in range(6):
            if battle.over or craft.state != "out":
                break
            combat_sim.take_turn(battle, captain_ai.orders(battle), rng)
            hurt = kind.hull - craft.hp
        assert hurt > 0, "six turns in among them and nothing touched her"
        assert craft.struck >= 2, craft.struck
        if craft.state == "out" and not battle.over:
            runs = craft.struck
            combat_sim.take_turn(battle, HOME, rng)
            assert craft.state == "cradled" and craft.pilot == ""
            assert craft.struck == runs, "called in and made a run anyway"
            assert craft.fuel > 0.0
            assert craft_battle.may_recall(battle)[1] == "Nothing is out."
        return (f"{hurt} points off her in {craft.struck} runs; the cradle "
                "took her back")

    @check("shot down is a pilot with a wound, not an officer spent")
    def _():
        game, battle, rng = _fight("shot-down", difficulty=1.8)
        craft = craft_sim.aboard(game)[0]
        combat_sim.take_turn(battle, LAUNCH, rng)
        who = craft.pilot
        name = craft_sim.name_of(game, who)
        craft.hp = 1                       # one more pass than she had in her
        officers = len(game.officers)
        nerve = battle.player.resolve
        for _n in range(4):
            if battle.over or craft.state == "lost":
                break
            combat_sim.take_turn(battle, captain_ai.orders(battle), rng)
        assert craft.state == "lost", "a craft on one point flew on for ever"
        assert craft_sim.aboard(game) == [], "a wreck is still on the list"
        key = "captain" if who == "captain" else who.split(":")[-1]
        assert float(game.wounds.get(key, 0)) >= craft_battle.PILOT_HURT, (
            game.wounds)
        assert len(game.officers) == officers, "the pilot went with her"
        assert battle.player.resolve < nerve
        assert "clear of her" in _said(battle)
        # And the boat is gone with her: the crossing knows it.
        from ..sim import crossing
        assert not crossing.has_boat(game)
        return (f"{name} is out of her and carrying "
                f"{game.wounds[key]:g} stamina of hurt; the cradle is empty")

    @check("the fight ends and she comes home — unless the hull does not")
    def _():
        game, battle, rng = _fight("homecoming")
        craft = craft_sim.aboard(game)[0]
        combat_sim.take_turn(battle, LAUNCH, rng)
        guard = 0
        while not battle.over and craft.state == "out" and guard < 40:
            guard += 1
            combat_sim.take_turn(battle, captain_ai.orders(battle), rng)
        if craft.state == "out":
            craft.fuel = 2.0
            game.ship.cargo["volatiles"] = 9.0
            battle.result = "driven-off"
            aftermath_sim.resolve(game, battle, rng)
            assert craft.state == "cradled" and craft.pilot == ""
            assert craft.fuel > 2.0, "home with a dry tank and nobody filled it"
            assert craft_battle.flying(game) is None
        # And the other ending: a hull that is lost takes its cradle with it.
        game2, battle2, rng2 = _fight("lost-with-her")
        combat_sim.take_turn(battle2, LAUNCH, rng2)
        aloft = craft_sim.aboard(game2)[0]
        battle2.result, battle2.over = "lost", True
        aftermath_sim.resolve(game2, battle2, rng2)
        assert aloft.state == "lost", aloft.state
        return (f"{craft.name} back on the cradle at {craft.fuel:.1f} t; a "
                "hull that goes down takes hers with it")

    @check("whoever flies her is off their station, captain or officer")
    def _():
        game, battle, rng = _fight("off-station")
        craft = craft_sim.aboard(game)[0]
        # An officer away is an officer not at their post: the hull's own
        # numbers say so while she is out.
        officer = next(k for k, _n, _w, ok, _why
                       in craft_sim.pilots(game, craft) if ok
                       and k != "captain")
        before = game.ship_stats
        assert craft_battle.launch(battle, officer)["ok"]
        game.recompute()
        after = game.ship_stats
        moved = [f for f in ("speed", "jump", "sensor", "accuracy", "scan")
                 if getattr(before, f) != getattr(after, f)]
        assert moved, "an officer flew a sortie and the bridge never noticed"
        assert craft_sim.away(game) == {officer}
        assert len(craft_sim.at_stations(game)) == len(game.officers) - 1
        craft_battle.recall(battle)
        game.recompute()
        # Back within a whisker: the tank she came home with is mass in the
        # hold, so the hull's own numbers move a little either way.
        assert all(abs(getattr(game.ship_stats, f) - getattr(before, f))
                   < abs(getattr(before, f)) * 0.01 for f in moved), (
            "they came back and the seat stayed empty")
        # And a captain in a cockpit cannot con the ship: the station orders
        # are refused, by name, while everything else goes on.
        # And left to itself a launch sends an officer, never the captain.
        assert craft_battle.launch(battle)["ok"]
        assert "captain" not in craft_sim.away(game), craft_sim.away(game)
        craft_battle.recall(battle)
        assert craft_battle.launch(battle, "captain")["ok"]
        turn = battle.turn
        combat_sim.take_turn(battle, {"type": "station", "order": "salvo"},
                             rng)
        assert battle.turn == turn, "conned the ship from a cockpit"
        assert "Call her in" in _said(battle)
        combat_sim.take_turn(battle, HOME, rng)
        combat_sim.take_turn(battle, {"type": "station", "order": "salvo"},
                             rng)
        assert battle.turn > turn, "called her in and still could not order"
        return (f"the navigator away cost the hull {', '.join(moved)}; "
                "a captain in the cockpit cannot take a station")

    @check("a hull with the hands for a cradle launches at you, and your mounts answer")
    def _():
        from ..data.chassis import CHASSIS_BY_ID
        big = small = None
        for n in range(12):
            game, battle, rng = _fight(f"theirs-{n}", difficulty=2.6,
                                       faction="concordat")
            rated = CHASSIS_BY_ID[battle.enemy.ship.chassis].crew
            if battle.enemy_flight and big is None:
                big = (game, battle, rng, rated)
            if not battle.enemy_flight and small is None:
                small = (game, battle, rated)
            if big and small:
                break
        assert big is not None, "no hull in twelve carried a craft"
        assert small is not None, "every hull in twelve carried a craft"
        game, battle, rng = big[:3]
        assert big[3] >= craft_battle.CARRIER_CREW, big[3]
        assert small[2] < craft_battle.CARRIER_CREW, small[2]
        assert len(battle.enemy_flight) <= craft_battle.THEIR_MOST
        assert "come round at you" in _said(battle)
        # They run in at you, and your close-in fire takes them apart.
        hull = sum(layer.hp for layer in battle.player.ship.layers)
        guard = 0
        while not battle.over and battle.enemy_flight and guard < 20:
            guard += 1
            combat_sim.take_turn(battle, captain_ai.orders(battle), rng)
        assert sum(layer.hp for layer in battle.player.ship.layers) < hull
        said = _said(battle)
        assert "flight runs in" in said, said[-400:]
        if not battle.enemy_flight and not battle.over:
            assert "flight is gone" in said, said[-400:]
        return (f"a {CHASSIS_BY_ID[battle.enemy.ship.chassis].name} of "
                f"{big[3]} hands launched {craft_battle.THEIR_MOST} at you; "
                f"{len(battle.enemy_flight)} still up after {guard} turns")

    @check("a run is worth making, and what she is sent at is the gamble")
    def _():
        """Measured over sixteen engagements, eight of each weight."""
        def fought(seed: str, faction: str, hard: float, launched: bool):
            game, battle, rng = _fight(seed, difficulty=hard, faction=faction)
            craft = craft_sim.aboard(game)[0]
            if launched:
                combat_sim.take_turn(battle, LAUNCH, rng)
            guard = 0
            while not battle.over and guard < 40:
                guard += 1
                combat_sim.take_turn(battle, captain_ai.orders(battle), rng)
            return 1.0 - hull_pct(battle.enemy.ship), craft

        tiers = {}
        for faction, hard in (("charter", 1.3), ("concordat", 2.6)):
            with_her = without = 0.0
            lost = runs = 0
            for n in range(8):
                seed = f"worth-{faction}-{n}"
                hurt, craft = fought(seed, faction, hard, True)
                with_her += hurt
                runs += craft.struck
                lost += 1 if craft.state == "lost" else 0
                without += fought(seed, faction, hard, False)[0]
            tiers[faction] = (with_her / 8, without / 8, lost, runs / 8)
            assert with_her > without, (faction, with_her, without)
            assert runs >= 8 * 3, f"{faction}: {runs} runs in eight fights"

        light, heavy = tiers["charter"], tiers["concordat"]
        assert light[2] <= 2, f"a one-gun patrol killed her {light[2]} times"
        assert heavy[2] >= 2, ("a hull with a battery on it never once got "
                               f"her: {heavy}")
        assert heavy[2] > light[2], (light, heavy)
        return (f"a patrol: {light[0]:.0%} taken off it against "
                f"{light[1]:.0%} without her, {light[3]:.0f} runs a fight, "
                f"lost {light[2]} in 8 — a warship: {heavy[0]:.0%} against "
                f"{heavy[1]:.0%}, lost {heavy[2]} in 8")
