"""What a dead star leaves, and that it is not what a living one keeps.

Three of the nine classes the galaxy makes are stellar corpses — a white
dwarf, a neutron star and an eight-solar-mass black hole — and every one of
them was generating its system from the same table as a G-type. A supernova
remnant could hold an ocean world with lifeforms in it, which is not a
rounding error; it is the wrong system.

The claims are the ones that make a corpse read as a corpse:

* what orbits one is **not what orbits a living star**;
* **nothing lives there** — a supernova sterilises and a red giant's envelope
  is not survivable either;
* **the inner system is gone**, engulfed or unbound, and what is left sits
  further out than it started, which is also what mass loss does to an orbit;
* a corpse **keeps fewer bodies**;
* and none of this touched the stars that are still burning.
"""

from __future__ import annotations

from collections import Counter

from ..core.state import new_game
from ..data import remnants
from ..sim import flight
from .harness import Suite

SEEDS = ("a", "b", "c", "d", "e", "f", "g", "h", "verge-7", "kite")


def _sweep():
    """Every system in ten galaxies, split by whether its star still burns."""
    live, dead = [], []
    for seed in SEEDS:
        game = new_game(seed)
        for system in game.galaxy.systems:
            (dead if remnants.of(system.star) else live).append(system)
    return live, dead


def run(suite: Suite) -> None:
    check = suite.check

    @check("a dead star does not keep what a living one keeps")
    def _():
        live, dead = _sweep()
        assert dead, "ten galaxies and not one stellar corpse in them"
        lived = Counter(b.kind for s in live for b in s.bodies)
        left = Counter(b.kind for s in dead for b in s.bodies)
        assert left, "corpses hold nothing at all, which is too little"
        # Rubble is the thing a corpse is rich in, and worlds the thing it is
        # poor in: a white dwarf's atmosphere is metal-polluted because it is
        # eating its own asteroids, and that is the system to fly into.
        rubble = ((left["asteroid"] + left["comet"]) / sum(left.values()))
        living_rubble = ((lived["asteroid"] + lived["comet"])
                         / sum(lived.values()))
        assert rubble > living_rubble, (
            f"corpses are {rubble:.0%} rubble against a living star's "
            f"{living_rubble:.0%} — the same system twice")
        # And the thing that cannot be there: an ocean round a corpse.
        assert not left["ocean"], (
            f"{left['ocean']} ocean world(s) survive a star's death")
        return (f"{sum(left.values())} bodies round {len(dead)} corpses: "
                f"{rubble:.0%} rubble against {living_rubble:.0%} round the "
                f"{len(live)} stars still burning")

    @check("nothing lives at a corpse")
    def _():
        live, dead = _sweep()
        gone = sum(len(b.lifeforms) for s in dead for b in s.bodies)
        alive = sum(len(b.lifeforms) for s in live for b in s.bodies)
        assert gone == 0, f"{gone} lifeform(s) survived a supernova"
        assert alive > 0, (
            "nothing is alive anywhere, so this proves nothing about corpses")
        return f"{alive} lifeforms round living stars, {gone} round the dead"

    @check("the inner system is gone, and what is left sits further out")
    def _():
        live, dead = _sweep()
        near_live = min(flight.semi_major(b) for s in live for b in s.bodies)
        near_dead = min(flight.semi_major(b) for s in dead for b in s.bodies)
        assert near_dead > near_live * 2.0, (
            f"a corpse's innermost body is {near_dead:.2f} AU against a "
            f"living star's {near_live:.2f} — nothing was engulfed")
        # Every surviving body, not merely the closest.
        for system in dead:
            leavings = remnants.of(system.star)
            for body in system.bodies:
                assert body.orbit >= leavings.inner_lost - 1e-9, (
                    f"{body.name} orbits at {body.orbit:.2f} inside "
                    f"{system.star}'s {leavings.inner_lost:.2f}")
        return (f"nearest body round a corpse {near_dead:.2f} AU, round a "
                f"living star {near_live:.2f} AU")

    @check("a corpse keeps fewer bodies than a star that is still burning")
    def _():
        live, dead = _sweep()
        held = sum(len(s.bodies) for s in dead) / len(dead)
        burning = sum(len(s.bodies) for s in live) / len(live)
        assert held < burning, (
            f"corpses hold {held:.1f} bodies against {burning:.1f} — the "
            "cap is not biting")
        for system in dead:
            keeps = remnants.of(system.star).keeps
            assert len(system.bodies) <= keeps, (
                f"{system.name} keeps {len(system.bodies)} past its {keeps}")
        return f"{held:.1f} bodies round a corpse against {burning:.1f}"

    @check("the stars still burning were not touched")
    def _():
        # The whole point of doing this in the generator is that it changes
        # what a *remnant* holds and nothing else. A living system still runs
        # the full range: worlds close in, giants and ice further out, oceans
        # where the warmth allows, and things living in them.
        live, _dead = _sweep()
        kinds = Counter(b.kind for s in live for b in s.bodies)
        for want in ("rocky", "ocean", "gas", "ice", "asteroid", "comet"):
            assert kinds[want], f"living stars have stopped making {want}"
        inner = [b for s in live for b in s.bodies if b.orbit < 0.15]
        assert inner, "no living system has anything close in any more"
        return (f"{len(kinds)} kinds still made round living stars, "
                f"{len(inner)} bodies still orbiting close in")
