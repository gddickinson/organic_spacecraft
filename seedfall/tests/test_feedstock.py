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

**The one-layer-per-call cadence is fixed now too** (#119), and it turned out
to run the other way from the note that used to stand here. `break` only fired
when a layer was left *unfilled*, so a call standing for thirty days filled the
innermost layer and walked on to the next still carrying all thirty of them,
while thirty calls of one day filled nothing and stopped each time. The same
thirty days on a hull at 50%:

    one call of 30 days     1.0000 hull
    five calls of 6 days    0.9677
    thirty calls of 1 day   0.8384

So the honest clock made repair **slower**, not faster. Days are the resource
now, spent innermost-first: a layer takes the days its own rate needs and the
remainder goes to the next one out. Measured across every chopping from one
call to sixty, and in all three feedstock regimes, the spread is 3.3e-16.
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
        # The levels moved when #119 made the days a resource: a month now
        # heals 67.19 points rather than 136, so the drive rate caps the
        # larder at 3.36 t instead of 20.5. Both regions are still walked —
        # 1 t and 2 t are feedstock-bound, 5 t and 500 t are rate-bound.
        rows = []
        for feed in (1.0, 2.0, 5.0, 500.0):
            game = _hurt(biomass=feed)
            healed = repair_tick(game.ship, 30.0, stats(game.ship))
            rows.append((feed, healed, game.ship.cargo.get("biomass", 0.0)))
        assert rows[0][1] < rows[1][1] < rows[2][1], (
            f"more feedstock did not buy more hull: {rows}")
        # Above the drive's own rate, more feedstock buys nothing — the cap is
        # the regeneration, not the larder.
        assert abs(rows[2][1] - rows[3][1]) < 1e-9, (
            f"500 t healed {rows[3][1]:.1f} against {rows[2][1]:.1f} at 5 t "
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

    @check("a month of mending is a month however the clock hands it over")
    def _():
        # #119, and the same claim #116 makes of every other tick. `break`
        # only fired when a layer was left *unfilled*, so a call standing for
        # thirty days filled the innermost layer and walked on to the next one
        # still carrying all thirty. Measured on a hull at 50% before the fix:
        # 1.0000 hull in one call, 0.9677 in five, 0.8384 in thirty.
        #
        # All three feedstock regimes, because the larder is the other thing
        # that can bind and it has to stay additive too.
        out = []
        for larder, why in ((5000.0, "to spare"), (3.0, "short"),
                            (0.0, "none")):
            spread = []
            for chops in (1, 2, 5, 10, 30, 60):
                game = _hurt(share=0.5, biomass=larder)
                s = stats(game.ship)
                for _ in range(chops):
                    repair_tick(game.ship, 30.0 / chops, s)
                spread.append(hull_pct(game.ship))
            gap = max(spread) - min(spread)
            assert gap < 1e-9, (
                f"with feedstock {why}, thirty days healed {min(spread):.4f} "
                f"one way and {max(spread):.4f} the other — a gap of {gap:.2e}"
                " that depends only on how the caller chopped the time")
            out.append(f"{why} {spread[0]:.4f}")
        return "30 days, 1 to 60 calls, identical: " + " · ".join(out)

    @check("with a full larder it heals exactly what the days pay for")
    def _():
        # Guarding that with feedstock to spare the answer is the *rate* and
        # nothing else — worked out here a second way, against the layers, so
        # a change in `repair_tick` cannot quietly redefine what it is being
        # compared with.
        #
        # It used to spend the whole span on every layer in turn, which is the
        # #119 defect: sixty days filled the innermost layer and then bought
        # sixty more days of work on the next. Days are a resource now, so the
        # model below deducts what each layer's fill actually took.
        game = _hurt(share=0.5, biomass=10_000.0)
        s = stats(game.ship)
        want, left = 0.0, 60.0
        for layer in reversed(game.ship.layers):
            if left <= 0:
                break
            if layer.hp >= layer.max:
                continue
            rate = layer.max * layer.regen * s.regen
            if rate <= 0:
                break
            grew = min(layer.max - layer.hp, rate * left)
            want += grew
            left -= grew / rate
        healed = repair_tick(game.ship, 60.0, s)
        assert abs(healed - want) < 1e-6, (
            f"healed {healed:.3f} with feedstock to spare, against "
            f"{want:.3f} from the rate alone — this changed more than the "
            "constraint")
        assert left < 1e-9, (
            f"{left:.2f} of the sixty days went unspent with a hull at 50% "
            "and a full larder, so the model is not the binding thing")
        return (f"{healed:.1f} points on {60 - left:.0f} days of work; "
                f"{healed * FEED_PER_HP:.1f} t of feedstock")
