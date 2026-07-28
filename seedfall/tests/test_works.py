"""Works checks — a written work has to be one somebody can build.

"Build a xenology annex" is a hundred days, eleven thousand credits and
twenty-two alloy, and it grants half a research point a day and four points of
diplomacy. It was gated on `tech="xenolinguistics"`, which is in neither the
sixty-one-node research tree nor the twelve xenotechnologies — so it was
buildable by 0 of 19 colony classes with *everything* in the game unlocked.

It stayed invisible partly because `test_verbs`' fixture appended the phantom
id to `research.unlocked`, so the sweep that clicks every control saw a work
that no real chronicle could reach.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.chassis import CHASSIS
from ..data.colonies import COLONIES
from ..data.parts import PARTS
from ..data.tech import TECH, TECH_BY_ID
from ..data.works import WORKS
from ..data.xenotech import XENOTECH_BY_ID
from ..sim import works as works_sim
from ..sim.colony import Colony
from .harness import Suite

KNOWN_TECH = set(TECH_BY_ID) | set(XENOTECH_BY_ID)


def _omniscient(seed: str = "works-all"):
    """A game that knows everything and has everything, to test reachability."""
    game = new_game(seed)
    game.credits = 9_000_000
    for key in ("alloy", "ore", "biomass", "volatiles", "phosphate", "silicon"):
        game.stores[key] = 900_000
    game.research.unlocked.extend(t.id for t in TECH)
    game.recompute()
    return game


def _colony(game, klass) -> Colony:
    return Colony(id=1, class_id=klass.id, name=klass.name,
                  system_id=game.location_id, body_id="0", need=1,
                  online=True, pop=klass.pop)


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing is gated behind a technology that does not exist")
    def _():
        # The general form. One entry in the whole content set was wrong and
        # it made a work permanently unbuildable; nothing would have caught the
        # next one either.
        broken = []
        for label, items in (("work", WORKS), ("colony", COLONIES),
                             ("part", PARTS), ("chassis", CHASSIS)):
            for item in items:
                gate = getattr(item, "tech", None)
                if gate and gate not in KNOWN_TECH:
                    broken.append(f"{label} {item.id} → {gate!r}")
        for tech in TECH:
            for need in getattr(tech, "needs", ()) or ():
                if need not in KNOWN_TECH:
                    broken.append(f"tech {tech.id} needs {need!r}")
        assert not broken, (
            f"{len(broken)} gate(s) naming a technology that is not in the "
            f"game:\n      " + "\n      ".join(broken[:6]))
        gated = sum(1 for group in (WORKS, COLONIES, PARTS, CHASSIS)
                    for item in group if getattr(item, "tech", None))
        return (f"{gated} gated entries across four tables, "
                f"every one naming one of {len(KNOWN_TECH)} technologies")

    @check("every work is one some colony can actually be asked to build")
    def _():
        game = _omniscient()
        reach = {work.id: 0 for work in WORKS}
        for klass in COLONIES:
            colony = _colony(game, klass)
            for work, ok, _why in works_sim.available(game, colony):
                if ok:
                    reach[work.id] += 1
        orphans = sorted(wid for wid, n in reach.items() if not n)
        assert not orphans, (
            f"works no colony in the game can build: {orphans}")
        return " · ".join(f"{wid} {n}" for wid, n in sorted(reach.items()))

    @check("a work changes something, and it is what the table says")
    def _():
        game = _omniscient("works-effect")
        klass = next(c for c in COLONIES if c.id == "radix_mine")
        checked = 0
        for work in WORKS:
            colony = _colony(game, klass)
            offers = {w.id for w, ok, _why in works_sim.available(game, colony)
                      if ok}
            if work.id not in offers:
                continue
            before_yield = dict(works_sim.yields_of(colony))
            before_fx = dict(works_sim.effects_of(colony))
            assert works_sim.begin(game, colony, work.id)["ok"]
            colony.works.append(work.id)
            colony.job = None
            after_yield = dict(works_sim.yields_of(colony))
            after_fx = dict(works_sim.effects_of(colony))

            moved = (after_yield != before_yield) or (after_fx != before_fx)
            assert moved, f"{work.id} finished and changed nothing at all"
            for key, value in work.effects.items():
                assert after_fx.get(key) == value, (
                    f"{work.id} promises {key}={value} and gives "
                    f"{after_fx.get(key)}")
            for key, value in work.yield_add.items():
                assert after_yield.get(key, 0) >= value - 0.001, (
                    f"{work.id} promises +{value} {key} and yields "
                    f"{after_yield.get(key, 0)}")
            checked += 1
        assert checked >= 5, f"only {checked} works could be tried"
        return f"{checked} works, each doing what its table says"

    @check("the annex is buildable and reaches the ship")
    def _():
        # The one that was dead. Its diplomacy has to arrive at the stat the
        # rest of the game reads, not merely sit in a dict.
        game = _omniscient("annex")
        klass = next(c for c in COLONIES if c.id == "radix_mine")
        colony = _colony(game, klass)
        offers = {w.id for w, ok, _why in works_sim.available(game, colony) if ok}
        assert "annex" in offers, "the annex is still unbuildable"

        annex = next(w for w in WORKS if w.id == "annex")
        assert annex.tech in KNOWN_TECH
        colony.works.append("annex")
        game.colonies.append(colony)
        before = game.ship_stats.diplomacy
        game.recompute()
        assert works_sim.yields_of(colony).get("research", 0) >= 0.5
        assert game.ship_stats.diplomacy > before, (
            "the annex's diplomacy never reaches the ship")
        return (f"gated on {annex.tech}, yields "
                f"{works_sim.yields_of(colony)['research']:g} research a day, "
                f"diplomacy {before:.2f} → {game.ship_stats.diplomacy:.2f}")

    @check("every colony class can be planted somewhere")
    def _():
        # The same question one level up: a class no body accepts is a class
        # nobody can found.
        from ..world.planets import BODY_KINDS
        homeless = [c.id for c in COLONIES
                    if not (set(c.sites) & set(BODY_KINDS))]
        assert not homeless, f"colony classes with nowhere to sit: {homeless}"
        return f"{len(COLONIES)} classes, every one with a site kind that exists"
