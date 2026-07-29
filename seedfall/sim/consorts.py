"""Consorts — the hulls that fight alongside your flag.

A consort is a `Side` like any other, so every routine that already knows how
to shoot at something, breach a layer or check an arc works on one unmodified.
What it adds is a standing order, a captain who follows it without being told
again each turn, and the possibility of being shot at instead of you — which is
the entire reason to bring one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..data.consorts import DEFAULT_ORDER, ORDERS_BY_ID, WITHDRAW_AT
from . import tactical as tac
from .battle_state import Side
from .ship import is_destroyed, stats as ship_stats


@dataclass
class Consort(Side):
    """A fleet hull under its own captain."""
    name: str = "Consort"
    order: str = DEFAULT_ORDER
    withdrawn: bool = False
    uid: int = 0

    @property
    def out(self) -> bool:
        return self.withdrawn or is_destroyed(self.ship)


def escorts_of(game) -> list:
    """The hulls sailing with the flag, in fleet order."""
    return [s for s in getattr(game, "fleet", [])
            if s is not game.ship and getattr(s, "escort", False)
            and not is_destroyed(s)]


def hull_fraction(ship) -> float:
    total = sum(layer.max for layer in ship.layers) or 1.0
    return sum(max(0.0, layer.hp) for layer in ship.layers) / total


# ── deployment ─────────────────────────────────────────────────────────────

def deploy(battle, ships, rng, bonuses=None) -> None:
    """Put the escorts on the plane, spread around the flag."""
    for index, ship in enumerate(ships):
        st = ship_stats(ship, bonuses or {})
        side = (1 if index % 2 == 0 else -1)
        offset = tac.BAND_UNITS * (0.35 + 0.2 * (index // 2))
        body = tac.Body2D(
            battle.player.body.x + side * offset,
            battle.player.body.y + offset * 0.35,
            battle.player.body.heading,
            0.0)
        consort = Consort(ship, st, "consort", body=body,
                          name=ship.name, order=DEFAULT_ORDER, uid=ship.uid)
        consort.resolve = 100.0
        battle.consorts.append(consort)


def active(battle) -> list:
    return [c for c in battle.consorts if not c.out]


# ── their turn ─────────────────────────────────────────────────────────────

def run(battle, rng, say, fire_one) -> None:
    """Every consort manoeuvres to its order, then fires what bears."""
    for consort in list(battle.consorts):
        if consort.out:
            continue
        if hull_fraction(consort.ship) < WITHDRAW_AT:
            consort.withdrawn = True
            say(battle, f"{consort.name} is holed and falls out of the line.",
                "warn")
            continue
        _manoeuvre(battle, consort)
        _shoot(battle, consort, rng, say, fire_one)


def _manoeuvre(battle, consort) -> None:
    order = ORDERS_BY_ID.get(consort.order, ORDERS_BY_ID[DEFAULT_ORDER])
    enemy, flag = battle.enemy, battle.player
    turn_limit, accel, top = tac.manoeuvrability(consort.st)

    if order.id == "screen":
        # Make for the point between the enemy and the flag, and sit on it.
        #
        # A station hugging the flag on the threat side was tried instead, on
        # the reasoning that the midpoint moves whenever either ship does and
        # so cannot be held. Measured, that reasoning was wrong: over ten
        # engagements the midpoint had the escort interposed on 95% of the
        # turns it was alive against 85% for the flag-hugging station, because
        # the midpoint is *on* the line between the two by construction. The
        # change was reverted rather than kept — and a claim that it had
        # improved matters from 21% to 82% was withdrawn, having compared two
        # different measurements as though they were one.
        goal = ((enemy.body.x + flag.body.x) / 2, (enemy.body.y + flag.body.y) / 2)
        speed = top * 0.75
    elif order.id == "flank":
        # Aim for a point off the enemy's quarter rather than its bow.
        wide = tac.bearing_to(enemy.body, flag.body) + 115
        rad = math.radians(wide)
        reach = tac.BAND_UNITS * 1.1
        goal = (enemy.body.x + math.sin(rad) * reach,
                enemy.body.y - math.cos(rad) * reach)
        speed = top
    else:
        goal = (enemy.body.x, enemy.body.y)
        speed = top

    target = tac.Body2D(goal[0], goal[1], 0, 0)
    want = (tac.bearing_to(consort.body, target) - consort.body.heading + 540) % 360 - 180
    tac.steer(consort.body, want, turn_limit)
    tac.throttle(consort.body, speed, accel)
    tac.advance(consort.body)


def _shoot(battle, consort, rng, say, fire_one) -> None:
    """Fire the heaviest mount that bears. One shot per hull per turn."""
    order = ORDERS_BY_ID.get(consort.order, ORDERS_BY_ID[DEFAULT_ORDER])
    band = tac.band_for(tac.separation(consort.body, battle.enemy.body))
    rel = tac.relative_bearing(consort.body, battle.enemy.body)

    best, best_dmg = None, -1.0
    for part in consort.st.weapons:
        w = part.wpn
        if w is None or not (w.bands[0] <= band <= w.bands[1]):
            continue
        if not tac.bears(tac.arc_of(part), rel):
            continue
        if w.dmg > best_dmg:
            best, best_dmg = part, w.dmg
    if best is None:
        return
    fire_one(battle, consort, battle.enemy, best.id, rng, scale=order.bite)


# ── being shot at ──────────────────────────────────────────────────────────

def choose_target(battle, rng):
    """Who the enemy shoots this turn: the flag, or something screening it.

    A screen is only worth its hull if it actually pulls the guns around, so
    the draw of each order is weighted against the flag's own share of one.
    """
    live = active(battle)
    if not live:
        return battle.player
    pairs = [(1.0, battle.player)]
    for consort in live:
        order = ORDERS_BY_ID.get(consort.order, ORDERS_BY_ID[DEFAULT_ORDER])
        weight = order.draw
        # Something parked between you and the enemy is hard to shoot past.
        if _is_between(battle, consort):
            weight *= 1.5
        pairs.append((max(0.05, weight), consort))
    return rng.weighted(pairs)


#: The share of a blow meant for the flag that a fully committed screen takes
#: instead of it — `shield` 1.0, and only while actually interposed.
#:
#: `draw` already sends whole shots at a screen. This is the residual: what
#: happens to the shots that come at you anyway. Measured before it existed,
#: screening was a pure cost — over six engagements the flag took 228.5 with
#: two escorts screening against 223.6 with them flanking, while the screens
#: lost 36 more hull for the privilege. The order's own blurb promises it
#: "draws fire that would otherwise land on you, and takes it on a smaller
#: hull", and only the first half was true.
SHIELD_SHARE = 0.30

#: However many hulls are interposed, the flag takes at least this much of
#: every blow. Three screens must not add up to invulnerability — "does more
#: of a good thing ever make it worse" is a question this project asks, and
#: the answer here has to be that it saturates.
SHIELD_FLOOR = 0.45


def interception(battle, dmg: float) -> tuple[float, list]:
    """How much of a blow at the flag a screen takes, and which hulls take it.

    Returns the damage still bound for the flag, and a list of
    `(consort, share)` for the parts somebody else is wearing. Reads
    `ConsortOrder.shield`, which was declared when the orders were written and
    then read by nobody at all — so "hold between the enemy and your flag"
    was a line of prose with no arithmetic behind it.

    Only a consort that is *actually* between the two counts. That is the
    physical justification for the whole mechanism, and it makes station-keeping
    matter: an escort under orders to screen that has not got there yet shields
    nothing.
    """
    if dmg <= 0:
        return dmg, []
    shares = []
    for consort in active(battle):
        order = ORDERS_BY_ID.get(consort.order, ORDERS_BY_ID[DEFAULT_ORDER])
        if order.shield <= 0 or not _is_between(battle, consort):
            continue
        shares.append((consort, order.shield * SHIELD_SHARE))
    if not shares:
        return dmg, []
    asked = sum(share for _c, share in shares)
    keeps = max(SHIELD_FLOOR, 1.0 - asked)
    # Scaled so the parts add up to exactly what the flag is not taking, which
    # is what makes the floor a saturation rather than a leak.
    scale = (1.0 - keeps) / asked
    return dmg * keeps, [(c, dmg * share * scale) for c, share in shares]


def _is_between(battle, consort) -> bool:
    flag, enemy = battle.player.body, battle.enemy.body
    span = tac.separation(enemy, flag)
    if span <= 1e-6:
        return False
    legs = (tac.separation(enemy, consort.body)
            + tac.separation(consort.body, flag))
    return legs < span * 1.25


def losses(battle) -> list:
    """Consorts that did not survive, for the after-action report."""
    return [c for c in battle.consorts if is_destroyed(c.ship)]
