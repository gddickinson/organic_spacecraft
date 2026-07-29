"""A party leader good enough to test the ground with.

The same gap combat had before `captain_ai`: driving an expedition by walking
at random and attempting whatever is underfoot measures nothing, because it
never goes back to the lander, so every party strands and every policy scores
the same. The one decision the ground actually poses — how much supply to keep
in hand for the walk home — was invisible to a driver that never walked home.

`margin` is that decision, in days of supply held back beyond the distance to
the pad. Sweeping it is how the ground is measured: the answer should have a
peak somewhere in the middle, because too little strands the party and too
much spends the trip walking.
"""

from __future__ import annotations

from ..sim import expedition as ex


def _towards(exp, tx: int, ty: int) -> tuple[int, int]:
    return (tx > exp.x) - (tx < exp.x), (ty > exp.y) - (ty < exp.y)


def steps_home(exp) -> int:
    """Tiles between the party and the lander, ignoring terrain."""
    return max(abs(exp.x - ex.LANDER[0]), abs(exp.y - ex.LANDER[1]))


def play(game, exp, rng, margin: int | None = 4, cap: int = 300) -> object:
    """Work the site, then bring them home with `margin` days in hand.

    `margin=None` never turns back — the party stays out until the supplies
    are gone. That is the baseline the fix had to beat and did not: stranding
    used to skip the carrying limit, so staying out was worth twenty-three
    times as much as walking back.
    """
    steps = 0
    while not exp.over and steps < cap:
        steps += 1
        if margin is not None and exp.supply <= steps_home(exp) + margin:
            if exp.at_lander:
                ex.lift_off(exp)
                break
            ex.move(exp, *_towards(exp, *ex.LANDER), game.officers, rng)
            continue
        if ex.options_here(exp):
            ex.attempt(exp, 0, game.officers, rng)
        else:
            ex.move(exp, *_towards(exp, rng.int(0, ex.W - 1),
                                   rng.int(0, ex.H - 1)), game.officers, rng)
    return exp
