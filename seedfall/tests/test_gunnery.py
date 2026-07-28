"""What a weapon actually delivers, against what the bridge says it will.

Found by playing: the chronicle suite claimed to do everything and had never
once fired a shot — encounters were rolled on arrival and thrown away. Wiring
combat into it produced thirty engagements in a decade, and every one of them
ended the same way, with both hulls at a hundred per cent.

The cause was two implementations of one rule. `combat._fire` floors damage at
`max(dmg * 0.15, dmg - armour)` — the comment says "something always gets
through, or two well-armoured hulls would shoot at each other until the sun
went out" — and then `_apply_to_layers` discarded anything at or below half a
point. For a three-damage weapon the floor is 0.45, so it was swallowed whole:
the Photic Flash Organ, the *only* armament a new captain starts with, dealt
exactly nothing to any armoured hull, thirty turns running, while the log said
"hits for 0" and the read panel correctly reported 0.45 a turn.
"""

from __future__ import annotations

import statistics

from ..core.rng import RNG
from ..core.state import new_game
from ..data.armaments import ARMAMENTS
from ..sim import assessment, combat, damage, encounters
from ..sim.ship import hull_pct
from .harness import Suite

#: The floor `_fire` guarantees, as a share of a weapon's damage.
LEAK = 0.15


def _engagement(seed: str, strength: float = 1.0, faction: str = "concordat"):
    game = new_game(seed)
    rng = RNG(f"g-{seed}")
    battle = combat.start(game.ship, game.ship_stats,
                          encounters.make_enemy(rng, faction, strength),
                          rng=rng, game=game, officers=game.officers)
    return game, battle, rng


def run(suite: Suite) -> None:
    check = suite.check

    @check("a weapon lighter than the armour still gets its floor through")
    def _():
        # The bug, stated as a rule. Every armament must be able to hurt an
        # armoured hull, however slowly, or endurance is not a strategy — it
        # is the only outcome.
        swallowed = []
        for part in ARMAMENTS:
            if not part.wpn:
                continue
            floor = part.wpn.dmg * LEAK
            game, battle, rng = _engagement(f"floor-{part.id}")
            heavy = battle.enemy
            heavy.st = heavy.st.__class__(**{**heavy.st.__dict__,
                                             "armour": part.wpn.dmg * 50})
            before = hull_pct(heavy.ship)
            landed = damage._apply_to_layers(battle, heavy, floor,
                                             part.wpn.traits, rng)
            if landed <= 0 or hull_pct(heavy.ship) >= before:
                swallowed.append(f"{part.name} (floor {floor:.2f})")
        assert not swallowed, (
            "weapons whose guaranteed minimum is discarded before it reaches "
            f"the hull: {swallowed}")
        return (f"{len([p for p in ARMAMENTS if p.wpn])} armaments, every "
                f"floor down to {min(p.wpn.dmg * LEAK for p in ARMAMENTS if p.wpn):.2f} "
                "reaching the hull")

    @check("the opening hull can hurt something, however slowly")
    def _():
        # The specific case that shipped: a new captain's only weapon against
        # an ordinary patrol boat.
        game, battle, rng = _engagement("opening")
        assert battle.player.st.weapons, "the opening hull is unarmed"
        before = hull_pct(battle.enemy.ship)
        for _ in range(25):
            if battle.over:
                break
            combat.take_turn(battle, {"type": "station", "order": "salvo"}, rng)
        after = hull_pct(battle.enemy.ship)
        assert battle.player.dealt > 0, (
            f"twenty-five salvos from the opening hull dealt "
            f"{battle.player.dealt}")
        assert after < before, f"enemy hull unchanged at {after * 100:.1f}%"
        return (f"{battle.player.dealt:.1f} damage over 25 salvos — "
                f"{before * 100:.0f}% → {after * 100:.1f}%")

    @check("the bridge does not report a hit as nothing")
    def _():
        # "hits for 0", thirty turns running, reads exactly like a weapon that
        # is working. Below a point it now says what is happening.
        game, battle, rng = _engagement("saying")
        for _ in range(20):
            if battle.over:
                break
            combat.take_turn(battle, {"type": "station", "order": "salvo"}, rng)
        lines = [text for _turn, text, _kind in battle.log]
        assert not any("for 0." in line for line in lines), (
            "the log still reports a landed hit as zero: "
            + next(line for line in lines if "for 0." in line))
        assert any("glances off" in line for line in lines), (
            "nothing was reported as glancing, so this is not being exercised")
        return f"{len(lines)} log lines, none of them a hit reported as zero"

    @check("what the read panel says you throw is what you throw")
    def _():
        # The assessment was right all along and the combat model was not,
        # which is how the bug hid: the honest number was on the screen while
        # the ledger delivered nothing. They have to be one number.
        gaps = []
        for index in range(8):
            game, battle, rng = _engagement(f"throw-{index}")
            said = assessment.read(battle)["weight"]["my_throw"]
            if said <= 0:
                continue
            hits, dealt = 0, 0.0
            for _ in range(30):
                if battle.over:
                    break
                before = battle.player.dealt
                combat.take_turn(battle,
                                 {"type": "station", "order": "salvo"}, rng)
                if battle.player.dealt > before:
                    hits += 1
                    dealt += battle.player.dealt - before
            if not hits:
                continue
            per_hit = dealt / hits
            gaps.append(abs(per_hit - said) / said)
        assert gaps, "no engagement landed a shot to compare"
        worst = max(gaps)
        assert worst < 0.35, (
            f"the read panel and the guns disagree by {worst * 100:.0f}% "
            "on what a shot lands")
        return (f"{len(gaps)} engagements, damage per landed shot within "
                f"{worst * 100:.0f}% of what the bridge said")

    @check("an engagement can end more than one way")
    def _():
        # Before the fix: 360 engagements, 100% driven-off, both hulls at 100%.
        # A fight with one outcome is not a fight.
        import collections
        ends = collections.Counter()
        for index in range(14):
            for strength in (0.6, 3.5):
                game, battle, rng = _engagement(f"vary-{index}", strength)
                guard = 0
                while not battle.over and guard < 70:
                    guard += 1
                    combat.take_turn(
                        battle, {"type": "station", "order": "salvo"}, rng)
                ends[battle.result or "unresolved"] += 1
        assert len(ends) >= 2, (
            f"every engagement ended the same way: {dict(ends)}")
        return " · ".join(f"{k} {v}" for k, v in ends.most_common())
