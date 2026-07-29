"""Whether the other side has anything to shoot with.

`make_enemy` gave every NPC hull a flat 4–20 tonnes of ore, alloy and biomass.
Those are salvage — stores meant to be worth pulling off a wreck — and they
were quietly doing a second job as ammunition nobody had ever sized against a
fight.

Measured over forty engagements: a mean of **12 rounds** against a **31-turn
fight**. NPCs ran dry in 35 of 40, on turn 11, and spent **63% of every
engagement unarmed**, clicking a dry gun while the player worked on them. The
consequence, over twenty fights against a mixed-armament navis: *the player
took no damage at all in thirteen of them.*

Every ammunition type was stocked — `alloy`, `biomass` and `ore` cover all
eighteen armed mounts in the game — so the "is every declared thing consumed"
question came back clean. It was the *quantity* that had never been measured
against anything.

The magazine is sized to the hull's own mounts now, and (see below) NPCs are
armed with something that can hurt you. Combat changed a great deal and it
should have: mean damage to the player went from **21 to 150–196** depending
on difficulty, and the player began losing engagements at all — 4 to 10 in
40, where it had simply never happened before. Wrecks are worth more too;
unspent rounds are legitimate salvage, a mean 31 tonnes recovered per kill
against 60 now.

The claims:

- **Every mount an NPC carries has ammunition for it.** The general one,
  swept over every faction and difficulty. It is what would have found this.
- **An NPC can fight the whole engagement**, measured by playing.
- **The player is actually shot at.** A fight you can take no damage in is
  not a fight, and that was the visible symptom.
- **A magazine is spent, not bottomless** — the guard on the other side.

The other half of the same illness lives in `test_balance`, which asked only
whether an NPC's throw was above zero. A single point-defence cannon clears
that at 8 damage, and `_weapon_pool` raised the tier until *some* weapon
existed — for a fabricated hull the first to appear is the flak gun. **40% of
NPC hulls came out armed with nothing but point-defence**, Concordat warships
at difficulty two included, and the check called them armed. `MAIN_GUN_DAMAGE`
is the bar now, and that check asks the question worth asking.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import combat, encounters
from ..sim.ship import build_layers, make_ship, stats
from .harness import Suite
from . import captain_ai

MIXED = ["slug_battery", "mag_lance", "reaction_organ", "opsin_eyes",
         "chemo_gut"]
FACTIONS = ("charter", "concordat", "freeholds", "sanhedrin")


def _armed(seed: str, strength: float = 1.8):
    """A capable player hull against a fresh NPC."""
    game = new_game(seed)
    ship = make_ship("navis", MIXED)
    build_layers(ship, game.bonuses)
    game.ship = ship
    ship.cargo = {"ore": 400, "alloy": 300}
    game.recompute()
    rng = RNG(f"mag-{seed}")
    battle = combat.start(ship, stats(ship),
                          encounters.make_enemy(rng, "concordat", strength),
                          rng=rng, game=game, officers=game.officers)
    return game, battle, rng


def _ammo_needs(side) -> dict:
    """What this hull's mounts eat, per turn of firing everything."""
    needs: dict[str, float] = {}
    for mount in side.st.weapons:
        if mount.wpn.ammo:
            cid, per = mount.wpn.ammo
            needs[cid] = needs.get(cid, 0.0) + per
    return needs


def run(suite: Suite) -> None:
    check = suite.check

    @check("every mount an NPC carries has ammunition for it")
    def _():
        # The general question, and the one that would have found this: not
        # "is the ammunition type stocked" — it always was — but "is there
        # enough of it to fire the mount that needs it more than once".
        #
        # The bar is an absolute number of rounds, not `ROUNDS_MIN`. Reading
        # it off the constant being guarded is the tautology this project
        # keeps rediscovering: with the magazine cut to three rounds, the
        # first draft of this check passed without blinking.
        enough = 15
        assert encounters.ROUNDS_MIN >= enough, (
            f"ROUNDS_MIN is {encounters.ROUNDS_MIN}, below the {enough} rounds "
            "a mount needs to still be firing halfway through an engagement")
        starved, checked = [], 0
        for faction in FACTIONS:
            for difficulty in (0.5, 1.0, 2.0, 3.0, 4.0):
                for trial in range(6):
                    rng = RNG(f"{faction}-{difficulty}-{trial}")
                    enemy = encounters.make_enemy(rng, faction, difficulty)
                    hold = enemy["ship"].cargo
                    for mount in enemy["stats"].weapons:
                        if not mount.wpn.ammo:
                            continue
                        cid, per = mount.wpn.ammo
                        checked += 1
                        if hold.get(cid, 0) < per * enough:
                            starved.append(
                                f"{faction}/{difficulty} {mount.name}: "
                                f"{hold.get(cid, 0):.0f} t of {cid}")
        assert not starved, (
            f"{len(starved)} mount(s) on NPC hulls without a magazine behind "
            f"them: {starved[:6]}")
        assert checked > 100, checked
        return (f"{checked} armed mounts across {len(FACTIONS)} factions and "
                "five difficulties, every one fed")

    @check("an NPC can fight the whole engagement, not the first third of it")
    def _():
        # Measured by playing. The old stock left NPCs unarmed for 63% of
        # every fight; the claim is that the share is now small.
        unarmed = []
        for seed in range(24):
            _g, battle, rng = _armed(f"whole{seed}")
            needs = _ammo_needs(battle.enemy)
            if not needs:
                continue
            dry_from, turns = None, 0
            while not battle.over and turns < 60:
                combat.take_turn(battle, captain_ai.orders(battle), rng)
                turns += 1
                if dry_from is None and all(
                        battle.enemy.ship.cargo.get(cid, 0) < per
                        for cid, per in needs.items()):
                    dry_from = turns
            unarmed.append(0.0 if dry_from is None
                           else (turns - dry_from) / max(1, turns))
        assert len(unarmed) >= 15, unarmed
        share = sum(unarmed) / len(unarmed)
        # Measured at 0% now against 63% before. A threshold of 20% would
        # pass a magazine of three rounds, because the salvage stores feed
        # the guns for a while on their own.
        assert share < 0.05, (
            f"NPC hulls spend {share:.0%} of the average engagement with "
            "nothing to shoot")
        return (f"{len(unarmed)} engagements, {share:.0%} of the average one "
                "spent dry")

    @check("the player is actually shot at")
    def _():
        # The symptom that made this visible: thirteen of twenty fights in
        # which the player took no damage whatever.
        quiet, taken = 0, []
        for seed in range(24):
            game, battle, rng = _armed(f"shot{seed}")
            before = sum(l.hp for l in battle.player.ship.layers)
            turns = 0
            while not battle.over and turns < 60:
                combat.take_turn(battle, captain_ai.orders(battle), rng)
                turns += 1
            hurt = before - sum(l.hp for l in battle.player.ship.layers)
            taken.append(hurt)
            quiet += hurt < 1
        assert quiet <= len(taken) // 4, (
            f"{quiet} of {len(taken)} engagements cost the player nothing at "
            "all — the other side cannot be fighting")
        mean = sum(taken) / len(taken)
        assert mean > 25, (
            f"the average engagement costs {mean:.0f} off the hull, which is "
            "not an engagement")
        return (f"{len(taken)} fights, {mean:.0f} off the hull on average, "
                f"{quiet} of them bloodless")

    @check("a magazine is spent, not bottomless")
    def _():
        # The guard on the other side: the fix must not have made ammunition
        # a formality. An NPC in a long fight has to work through a real
        # share of what it carries.
        spent = []
        for seed in range(24):
            _g, battle, rng = _armed(f"spend{seed}", strength=2.0)
            needs = _ammo_needs(battle.enemy)
            if not needs:
                continue
            start = {cid: battle.enemy.ship.cargo.get(cid, 0) for cid in needs}
            if sum(start.values()) <= 0:
                continue
            turns = 0
            while not battle.over and turns < 80:
                combat.take_turn(battle, captain_ai.orders(battle), rng)
                turns += 1
            left = sum(battle.enemy.ship.cargo.get(cid, 0) for cid in needs)
            spent.append(1 - left / sum(start.values()))
        assert len(spent) >= 15, spent
        worst = max(spent)
        assert worst > 0.30, (
            f"the hardest-fought NPC got through only {worst:.0%} of its "
            "magazine — ammunition has stopped being a constraint at all")
        assert encounters.ROUNDS_MAX <= 60, (
            f"ROUNDS_MAX is {encounters.ROUNDS_MAX}: a magazine that large is "
            "not a magazine, it is a promise never to run out")
        return (f"{len(spent)} engagements, up to {worst:.0%} of a magazine "
                "burned through")

    @check("a light patrol is armed like a light patrol")
    def _():
        # The armament curve, measured directly rather than through a win
        # rate. It used to be a cliff, not a curve: scale 0.5, 1 and 2 all
        # came out at 8–16 points of throw, because every one of them was
        # carrying flak and nothing else, and then scale 3 jumped to 85. The
        # low end of the range had no gradient in it at all.
        #
        # Requiring a main gun fixed the flat bottom and created a new fault
        # in its place — a light patrol drew from the same rack as a
        # battleship, because a fabricated hull's first main gun is tier
        # three and tier three holds the breach torpedo. `_rack` is what
        # gives the curve a bottom as well as a top.
        curve = {}
        for difficulty in (0.5, 1.0, 2.0, 3.0):
            throws = []
            for faction in FACTIONS:
                for trial in range(20):
                    rng = RNG(f"curve-{faction}-{difficulty}-{trial}")
                    enemy = encounters.make_enemy(rng, faction, difficulty)
                    throws.append(sum(w.wpn.dmg
                                      for w in enemy["stats"].weapons if w.wpn))
            curve[difficulty] = sum(throws) / len(throws)

        steps = sorted(curve)
        for lighter, heavier in zip(steps, steps[1:]):
            assert curve[heavier] > curve[lighter], (
                f"a scale-{heavier} threat throws {curve[heavier]:.0f} against "
                f"{curve[lighter]:.0f} for a scale-{lighter} one — the "
                "difficulty curve is flat here")
        # And the ends are genuinely different weights of ship, rather than
        # a gradient so shallow it reads as noise.
        assert curve[steps[-1]] > curve[steps[0]] * 2.5, (
            f"scale {steps[-1]} throws {curve[steps[-1]]:.0f} against "
            f"{curve[steps[0]]:.0f} at scale {steps[0]} — too flat to be a "
            "difficulty setting")
        return " · ".join(f"d{d} {v:.0f}" for d, v in sorted(curve.items()))

    @check("a new captain's own mounts are fed too")
    def _():
        # The same question asked of the player's opening hull, because the
        # identical mistake there would be worse: a first fight nobody can
        # shoot in.
        game = new_game("opening")
        dry = []
        for mount in game.ship_stats.weapons:
            if not mount.wpn.ammo:
                continue
            cid, per = mount.wpn.ammo
            if game.ship.cargo.get(cid, 0) < per:
                dry.append(f"{mount.name} needs {per:g} t of {cid}")
        assert not dry, (
            f"a new captain starts with mounts they cannot fire: {dry}")
        return (f"{len(game.ship_stats.weapons)} opening mount(s), "
                "none of them dry")
