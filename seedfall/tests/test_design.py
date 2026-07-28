"""Design checks — mass as the price of everything you bolt on.

Fitted mass used to be free, so every design was the same design: the heaviest,
best part in every slot. These hold loading to biting, to biting on the right
scale across hulls that differ by nine orders of magnitude in structural mass,
and to never being able to strand a captain who filled the hold.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data import chassis as chassis_data
from ..data.chassis import CHASSIS, CHASSIS_BY_ID
from ..data.parts import PARTS
from ..sim import loading
from ..sim.ship import make_ship, stats
from ..world.galaxy import distance
from .harness import Suite


def _build(chassis_id: str, share: float, heavy: bool):
    ch = CHASSIS_BY_ID[chassis_id]
    fitted = []
    for slot, count in ch.slots.items():
        options = [p for p in PARTS if p.slot == slot
                   and chassis_data.accepts_family(ch, p.family)]
        options.sort(key=lambda p: -p.mass if heavy else p.mass)
        fitted += [p.id for p in options[:max(1, round(count * share))]]
    return make_ship(chassis_id, fitted)


def run(suite: Suite) -> None:
    check = suite.check

    @check("what you bolt on is no longer free")
    def _():
        light = _build("navis", 1.0, heavy=False)
        heavy = _build("navis", 1.0, heavy=True)
        assert loading.part_mass(heavy) > loading.part_mass(light) * 1.5, (
            "the two builds do not differ enough in mass to test with")
        light_st, heavy_st = stats(light), stats(heavy)
        assert heavy_st.speed < light_st.speed, (
            f"a hull {loading.part_mass(heavy) - loading.part_mass(light):.0f} t "
            f"heavier flies as fast: {heavy_st.speed:.2f} vs {light_st.speed:.2f}")
        assert loading.factor(heavy) < loading.factor(light), "loading is inert"
        return (f"{loading.part_mass(light):.0f} t → {loading.part_mass(heavy):.0f} t "
                f"costs {(1 - loading.factor(heavy) / loading.factor(light)) * 100:.0f}% "
                "of the loading factor")

    @check("loading reads on the same scale for every hull")
    def _():
        # Structural mass runs from a 60 t SPORE to a 12-billion-tonne
        # LEVIATHAN, so it is useless as a basis. Slots and hold rating are on
        # the same scale as the parts and cargo that fill them.
        bad = []
        for ch in CHASSIS:
            sensible = _build(ch.id, 0.7, heavy=False)
            sensible.cargo = {"ore": ch.cargo * 0.5}
            value = loading.factor(sensible)
            if value < 0.8:
                bad.append(f"{ch.id} {value:.2f}")
        assert not bad, ("a sensibly fitted hull is already penalised: "
                         + ", ".join(bad))
        return f"{len(CHASSIS)} hulls, all fine at a sensible fit"

    @check("overloading is possible, and says so")
    def _():
        maxed = _build("navis", 1.0, heavy=True)
        maxed.cargo = {"ore": CHASSIS_BY_ID["navis"].cargo}
        assert loading.loading(maxed) > 1.0, "a maxed hull is not over its marks"
        assert loading.factor(maxed) < 1.0, "being over the marks costs nothing"
        reads, _tint = loading.note(maxed)
        assert reads in ("heavy", "overloaded", "grossly overloaded"), (
            f"an overloaded hull reads as {reads!r}")

        bare = make_ship("navis", ["reaction_organ"])
        assert loading.factor(bare) > 1.0, "a stripped hull gains nothing"
        assert loading.note(bare)[0] == "light", "a stripped hull does not read light"
        return f"maxed reads {reads!r} at {loading.loading(maxed):.2f} of capacity"

    @check("the label always agrees with the number")
    def _():
        seen = {}
        for chassis_id in ("spore", "vesper", "navis", "atlas", "testudo"):
            for share in (0.3, 0.7, 1.0):
                for heavy in (False, True):
                    ship = _build(chassis_id, share, heavy)
                    for hold in (0.0, 1.0):
                        ship.cargo = {"ore": CHASSIS_BY_ID[chassis_id].cargo * hold}
                        reads, _tint = loading.note(ship)
                        seen.setdefault(reads, []).append(loading.factor(ship))
        for reads, values in seen.items():
            if reads in ("light", "on the marks"):
                assert min(values) >= 0.95, (
                    f"{reads!r} covers a factor as low as {min(values):.2f}")
            if reads in ("overloaded", "grossly overloaded"):
                assert max(values) < 1.0, (
                    f"{reads!r} covers a factor as high as {max(values):.2f}")
        return " · ".join(f"{k} n={len(v)}" for k, v in sorted(seen.items()))

    @check("a full hold slows you without stranding you")
    def _():
        # Jump range is deliberately dampened against loading: a full hold
        # costing speed is a trade, a full hold leaving a captain unable to
        # reach a neighbour is the deadlock this project has hit before.
        worst_ratio = 1.0
        worst_reach = 9e9
        for seed in range(20):
            game = new_game(f"laden-{seed}")
            empty_jump = game.ship_stats.jump
            empty_speed = game.ship_stats.speed
            game.ship.cargo = {"ore": game.ship_stats.cargo}
            game.recompute()
            laden_jump = game.ship_stats.jump
            assert game.ship_stats.speed <= empty_speed, "a full hold is faster"
            worst_ratio = min(worst_ratio, laden_jump / empty_jump)

            here = game.system
            nearest = min((distance(s, here) for s in game.galaxy.systems
                           if s.id != here.id), default=0)
            worst_reach = min(worst_reach, laden_jump - nearest)
        assert worst_ratio > 0.85, (
            f"a full hold cut jump range to {worst_ratio:.0%} of empty")
        assert worst_reach > 0, (
            "a fully laden starting hull cannot reach its nearest neighbour")
        return (f"laden jump is {worst_ratio:.0%} of empty; nearest neighbour "
                f"still {worst_reach:.1f} ly inside range")

    @check("a heavy drive buys range with the speed it costs")
    def _():
        # The interesting case: heavy parts are not simply worse. A big drive
        # adds mass and jump, so the design question is what you want.
        base = make_ship("navis", ["reaction_organ", "opsin_eyes", "chemo_gut"])
        big = make_ship("navis", ["reaction_organ", "foldrunner", "opsin_eyes",
                                  "chemo_gut"])
        if "foldrunner" not in {p.id for p in PARTS}:
            return "no second drive in the parts table to test with"
        base_st, big_st = stats(base), stats(big)
        assert loading.part_mass(big) > loading.part_mass(base), "no mass added"
        assert big_st.jump > base_st.jump, "the extra drive bought no range"
        return (f"+{loading.part_mass(big) - loading.part_mass(base):.0f} t buys "
                f"{big_st.jump - base_st.jump:+.1f} ly")
