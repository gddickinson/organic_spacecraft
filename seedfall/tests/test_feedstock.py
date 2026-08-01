"""A grown hull cannot rebuild itself out of nothing, and it did.

Found while opening #116. The clock fix that task needs is blocked on a
balance problem — hard burning stops costing anything once repair ticks
honestly — and this is why: **repair was free.**

`ship.repair_tick` worked out what the healing should eat and then took
whatever happened to be aboard:

    fed = min(ship.cargo.get("biomass", 0), budget * 0.004)

`min` against the hold, and the healing went ahead regardless. Measured, a hull
at 60% going to 100% — 136 points:

    with 500 t aboard   healed 136.0    with 20 t   healed 136.0
    with no biomass     healed 136.0

A cost that is calculated and does not constrain is not a cost. It is the same
family as a field that is declared and never read, one level up: the arithmetic
was there, the consequence was not.

And the rate made it moot anyway. A full rebuild of the starting hull is 336
points; at 0.004 t a point that is **1.3 tonnes and 89 credits**, against a
340-tonne hold. `FEED_PER_HP` is 0.05 now, so a full rebuild is 16.8 t and
about 1,100 credits — roughly the 20.5 t a new ship sails with, and 5% of the
hold.

What that buys, measured across a hull at 60%:

    0 t aboard     heals nothing at all
    2 t            40 points   0.595 → 0.714
    5 t            100 points  0.595 → 0.893
    20.5 t         136 points  0.595 → 1.000, 13.7 t left
    500 t          136 points  — the drive rate caps it, not the feedstock

So a ship that has burned itself out with an empty hold does not heal, and one
that has thought about it carries the tonnage to put itself back together.

**Deliberately not fixed here:** the one-layer-per-*call* cadence. Making that
a rate heals a great deal more and is what broke the burn-cost balance when
#116 was attempted — it is task #119, and it belongs with the clock.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim.ship import FEED_PER_HP, hull_pct, repair_tick, stats
from .harness import Suite


def _hurt(seed="feed", share=0.6, biomass=0.0):
    game = new_game(seed)
    for layer in game.ship.layers:
        layer.hp = int(layer.max * share)
    game.ship.cargo["biomass"] = float(biomass)
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("a hull with nothing to eat does not heal")
    def _():
        game = _hurt(biomass=0.0)
        before = hull_pct(game.ship)
        healed = repair_tick(game.ship, 30.0, stats(game.ship))
        assert healed == 0.0, f"healed {healed:.1f} points on nothing"
        assert hull_pct(game.ship) == before
        return f"a month at {before:.1%}, still {hull_pct(game.ship):.1%}"

    @check("what it eats is what it is limited by")
    def _():
        # The defect exactly: the old line took `min(cargo, want)` and healed
        # the full amount either way, so 500 t and 0 t did the same thing.
        rows = []
        for feed in (2.0, 5.0, 20.5, 500.0):
            game = _hurt(biomass=feed)
            healed = repair_tick(game.ship, 30.0, stats(game.ship))
            rows.append((feed, healed, game.ship.cargo.get("biomass", 0.0)))
        assert rows[0][1] < rows[1][1] < rows[2][1], (
            f"more feedstock did not buy more hull: {rows}")
        # Above the drive's own rate, more feedstock buys nothing — the cap is
        # the regeneration, not the larder.
        assert abs(rows[2][1] - rows[3][1]) < 1e-9, (
            f"500 t healed {rows[3][1]:.1f} against {rows[2][1]:.1f} at 20.5 "
            "— the drive rate is not capping it")
        # And it is actually taken out of the hold.
        for feed, healed, left in rows:
            assert abs((feed - left) - healed * FEED_PER_HP) < 1e-6, (
                f"healed {healed:.1f} points and the hold moved "
                f"{feed - left:.2f} t, not {healed * FEED_PER_HP:.2f}")
        return " · ".join(f"{f:.1f} t → {h:.0f} hp" for f, h, _l in rows)

    @check("a rebuild is a hold-load, not a rounding error")
    def _():
        # The rate was 0.004 t a point, so putting a whole hull back cost 1.3
        # tonnes of a 340 tonne hold. A cost nobody can feel is not one.
        game = new_game("size")
        hull = sum(layer.max for layer in game.ship.layers)
        whole = hull * FEED_PER_HP
        carried = new_game("size").ship.cargo.get("biomass", 0.0)
        assert whole > carried * 0.5, (
            f"a full rebuild is {whole:.1f} t against the {carried:.1f} t a "
            "ship sails with — it would never be thought about")
        assert whole < stats(game.ship).cargo * 0.15, (
            f"a full rebuild is {whole:.1f} t of a "
            f"{stats(game.ship).cargo:.0f} t hold — that is a tax, not a cost")
        return (f"{hull} points of hull = {whole:.1f} t, against "
                f"{carried:.1f} t carried and a "
                f"{stats(game.ship).cargo:.0f} t hold")

    @check("with a full larder it heals exactly what it always did")
    def _():
        # Guarding that this only *added a constraint*. The claim is not about
        # the cadence — my first version asserted repair stops after one layer
        # and that was never true: a layer that fills lets the loop carry on,
        # and six came back full in a sixty-day call before this change as
        # much as after. What must hold is that with feedstock to spare the
        # healing is identical to the old formula.
        game = _hurt(share=0.5, biomass=10_000.0)
        s = stats(game.ship)
        want = 0.0
        for layer in reversed(game.ship.layers):
            if layer.hp >= layer.max:
                continue
            grew = min(layer.max - layer.hp,
                       layer.max * layer.regen * s.regen * 60.0)
            want += grew
            if layer.hp + grew < layer.max:
                break
        healed = repair_tick(game.ship, 60.0, s)
        assert abs(healed - want) < 1e-6, (
            f"healed {healed:.3f} with feedstock to spare, against "
            f"{want:.3f} from the rate alone — this changed more than the "
            "constraint")
        return (f"{healed:.1f} points either way; only the larder is new "
                f"({healed * FEED_PER_HP:.1f} t of it)")
