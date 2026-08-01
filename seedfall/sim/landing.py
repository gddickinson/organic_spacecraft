"""Coming down on a world, and why it is almost never a landing.

Measured before this module existed, by flying the gentlest touchdown the sim
can produce and reading what it said:

    The hull is down on Sable's Verge II at 17 m/s. That was not a landing.

It was right, and it was right for a reason nobody had written down. The
outcome branch for a body had **no speed test at all** — every contact with a
world, at any rate, was `aground` with quadratic damage. So the game could not
distinguish setting down from crashing, and a captain who flew a perfect
descent was told they had wrecked.

The obvious fix is a rate threshold. Measuring what a hull can actually do
says the obvious fix would have been a lie:

    rocky world   3,771 km    10.371 m/s²   one 60 s tick of freefall: 622 m/s
    comet            11 km     0.278 m/s²   one 60 s tick of freefall:  17 m/s
    the ship this game starts you with:      0.071 m/s²

**A starship in this game cannot land on a world.** Not "it is difficult" — the
rocky world above pulls a hundred and forty times harder than the drive can
push, so there is no descent profile, no fuel budget and no piloting that ends
with the hull intact on that surface. That is not a defect to fix; it is why
`sim/expedition.py` sends a party down in a lander and the ship stays in orbit,
a design decision the code made and never justified.

Swept across six sectors, **eighteen bodies can be set down on** and every one
of them is an asteroid or a comet, 0.037 to 0.069 m/s². That is the right
shape: setting the ship down is a real thing that happens somewhere real, and
it is never a way onto a world.

And what ditching a world actually costs, flown: **70,972 against a 336-point
hull**, because one tick of freefall at 10.371 m/s² is 622 m/s and the damage
curve is quadratic. On an asteroid the same order costs 67 and the ship flies
again. So the answer to "or force a landing on the planet" is that the order
can be given anywhere and is fatal where the arithmetic says it is, which is
better than a rule forbidding it.

So there are three ways a hull meets a world, and this module names them:

- **down** — the drive held the fall and the ship is on the surface. Possible
  only where surface gravity is under what the drive delivers, which in
  practice means the smallest bodies. Rare, and worth something.
- **ditched** — the captain *chose* to put the ship down on a world it cannot
  land on, flying it in as slow as the drive allows. It is a wreck you walk
  away from, and it is the last door out of a sector where nothing will open
  for you: the answer to "or force a landing on the planet". It costs the hull
  and the cost is quadratic in the speed you arrive at, so ditching on a comet
  is a repair bill and ditching on a rocky world is the end of the chronicle.
- **aground** — everything else. You hit a planet.

The rule that keeps the middle one honest: **ditching is an order.** A hull that
merely flew badly does not get credited with a bold decision, the same way
`sim/forcing.py` will not let a cut start itself.
"""

from __future__ import annotations

from ..world.planets import BODY_KINDS

#: The rate under which a touch is a landing rather than an arrival, in m/s.
#:
#: The same figure as `conn.SAFE_CLOSING`, and deliberately so: the hull does
#: not know whether the thing it is touching is a quay or a rock, and a game
#: with two numbers for "gently enough" would eventually disagree with itself.
SET_DOWN = 4.0

#: How much of a ditching's speed the hull actually feels.
#:
#: Not all of it. A captain who flies it down under power arrives on a chosen
#: patch, nose up, with the drive taking some of the last of it — which is the
#: whole difference between ditching and falling: measured on an asteroid,
#: 401 off the hull for falling against 121 for flying her in. The cost stays
#: quadratic, so this is a gradient and not a discount — it decides *where*
#: the ship can be put down, not whether the ground is free.
DITCH_SHARE = 0.55


def kind_allows(body) -> bool:
    """Is this the sort of world anything can come down on?

    **The one door for the question**, and it had two. `BODY_KINDS` has
    carried a landable flag since the sector generator was written, read by
    `sim/fieldwork.py` and the system view — while `sim/contracts.py` asked
    the same question a second way, as `kind not in ("gas", "star")`. Two
    writers of one fact, and the day a kind was added they would have
    disagreed silently.
    """
    # `look`, not `kind`. A conn's `Target.kind` is *"body"* — the sort of
    # thing it is to an approach — while `Body.kind` is "rocky" or "comet",
    # the sort of world it is. `targets.target_from_body` carries the latter
    # through as `look`, so this reads `look` first and falls back to `kind`
    # for a `Body` handed in directly. Asking the wrong one of two fields
    # both called kind said every world in the sector had no surface.
    kind = (getattr(body, "look", "") or getattr(body, "kind", "") or "")
    entry = BODY_KINDS.get(kind)
    return bool(entry and entry[2])


def surface_g(target) -> float:
    """What the world pulls at its own surface, in m/s².

    From `mu` and the radius the approach already uses, so it is the same
    gravity the tick loop is flying against rather than a second figure that
    could drift from it.
    """
    radius = float(getattr(target, "radius_km", 0.0) or 0.0)
    mu = float(getattr(target, "mu", 0.0) or 0.0)
    if radius <= 0.0 or mu <= 0.0:
        return 0.0
    return mu / (radius * radius) * 1000.0        # km/s² → m/s²


def drive_g(conn) -> float:
    """What this hull's main drive delivers, in m/s².

    `Conn.main_dv` is the delta-v of one tick's burn, which is an acceleration
    once you divide by the tick — and that is the honest comparison to make
    against a world, because the thing a landing needs is to *hold* the fall
    for as long as the descent takes, not to make one impressive shove.
    """
    from .conn import TICK
    return float(getattr(conn, "main_dv", 0.0) or 0.0) / max(1e-9, TICK)


def can_hold(conn) -> bool:
    """Can this hull's drive out-push this world's gravity?

    The whole of whether a landing is even a manoeuvre. If the answer is no,
    no amount of flying produces a landing and the only choices are to stay
    off it or to put the ship down and pay for it.
    """
    target = getattr(conn, "target", None)
    if target is None or getattr(target, "kind", "") != "body":
        return False
    return drive_g(conn) > surface_g(target)


def why_not(conn) -> str:
    """Why this world cannot be landed on, or "" if it can.

    Written to be shown. A rule the physics enforces and no screen states is
    a rule the captain has to discover by dying.
    """
    target = getattr(conn, "target", None)
    if target is None or getattr(target, "kind", "") != "body":
        return "That is not a world."
    if not kind_allows(target):
        return f"There is no surface on {target.name} to come down on."
    pull, push = surface_g(target), drive_g(conn)
    if push <= pull:
        return (f"{target.name} pulls {pull:.2f} m/s² and the drive holds "
                f"{push:.2f}. Nothing you fly ends with the hull intact on "
                "that surface.")
    return ""


# ── putting the ship down anyway ───────────────────────────────────────────

def ditching(conn) -> bool:
    """Has the captain ordered the ship put down?"""
    return bool(getattr(conn, "ditching", False))


def ditch(conn) -> str:
    """Give the order, and say what it will cost. Returns what you are told."""
    target = getattr(conn, "target", None)
    if target is None or getattr(target, "kind", "") != "body":
        conn.ditching = False
        return "There is nothing here to put the ship down on."
    if not kind_allows(target):
        conn.ditching = False
        return f"There is no surface on {target.name} to put it down on."
    conn.ditching = True
    return quote(conn)


def toll(conn, speed: float | None = None) -> float:
    """What arriving at this speed will take out of the hull.

    Reads `outcome`'s own curve rather than a second one — the whole point of
    quoting a cost before an act is that the quote and the act agree, and this
    project has had that be false twice.
    """
    from .outcome import impact_at
    rate = conn.speed if speed is None else float(speed)
    return impact_at(conn, rate * DITCH_SHARE)


def quote(conn) -> str:
    """What putting it down here would cost, at the rate you are making now."""
    target = getattr(conn, "target", None)
    if target is None:
        return ""
    hurt = toll(conn)
    return (f"Putting her down on {target.name}. At {conn.speed:,.0f} m/s "
            f"that is about {hurt:,.0f} off the hull, and she does not come "
            "off that surface again without a yard.")


def ending(conn) -> str:
    """Which of the three this contact is: down, ditched or aground."""
    target = getattr(conn, "target", None)
    if target is None or not kind_allows(target):
        return "aground"
    if conn.speed <= SET_DOWN and can_hold(conn):
        return "down"
    if ditching(conn):
        return "ditched"
    return "aground"
