"""The gunner's station: which mounts speak this turn, and what it costs.

The player had two ways to shoot and nothing in between. One named mount, or
`_salvo` — "everything that can bear, fired together". `_salvo`'s own docstring
says the cost is heat and ammunition, "which is why a single aimed shot stays a
real option", and that reads like a trade until you measure it.

**A HAMMERFALL with five mounts puts 69 points of heat into itself in one
salvo, against a fault line of 40 and a vent of 6 a turn.** It faults on turn
one and never comes back: resolve bled from 92.9 to −34 across ten turns purely
from its own radiators, in a fight it was winning on damage. The alternative on
offer was one mount out of five. So the more armament a captain buys, the worse
the salvo button becomes — which is the question this project keeps asking about
every good thing, and here the answer was yes.

The missing control is the obvious one: **fire some of them.** `volley` takes
the mounts the gunner picked. `quote` says what that will do to the hull before
the trigger, and `advise` picks the heaviest set that will not fault, because a
gunner who has to do arithmetic every turn will stop reading it.

Nothing here decides whether a shot *hits* — `combat._fire` owns that and
`sim/firing.py` reports what will bear. This is what a turn's worth of shooting
costs the hull that does it.
"""

from __future__ import annotations

from . import firing
from . import tactical as tac
from .ship import HEAT_CEILING


def fault_line(side) -> float:
    """The heat a hull faults above.

    `combat._end_of_turn` tests `heat > st.heat_cap`, so that is the line —
    **not** `heat_cap * HEAT_CEILING`, which is the physical clamp on how much
    heat a hull can hold at all. Those two are a factor of two apart and I read
    them the wrong way round first, so it is worth one function rather than
    three call sites remembering which is which.
    """
    return side.st.heat_cap


def ceiling(side) -> float:
    """The most heat this hull can physically hold. `ship.cook` clamps here."""
    return side.st.heat_cap * HEAT_CEILING


def mounts(b, side=None, other=None) -> list:
    """Every mount and whether it can shoot, in the gunner's own order.

    Straight through `firing.solution`, which is the one place that answers
    this, so the board cannot disagree with the trigger.
    """
    side = side if side is not None else b.player
    other = other if other is not None else b.enemy
    band = tac.band_for(tac.separation(side.body, other.body))
    return firing.solution(side, other, band)


def _weapon(side, mount_id: str):
    return next((w for w in side.st.weapons if w.id == mount_id), None)


def firing_set(b, mount_ids, side=None, other=None) -> list:
    """Of the mounts asked for, the ones that will actually shoot.

    A mount outside its arc or its band puts no heat into the hull, because
    `combat._fire` returns before `add_heat`. A quote that charged for it would
    be wrong in the direction that matters — talking a gunner out of a volley he
    could afford.

    **A selection is a multiset, not a set.** A HAMMERFALL carries three Fusion
    Lances and every one of them is called `fusion_lance`: `Shot.mount_id` is a
    part id, so five mounts come back under three distinct names. They are
    genuinely interchangeable — the ammunition is drawn from one hold rather
    than from per-mount magazines, and identical parts sit in identical arcs —
    so "two of the three lances" is a *count* and not an identity, and asking
    for `["fusion_lance", "fusion_lance"]` has to fire two of them.

    Which means the count has to be capped at what the hull actually carries.
    A first draft filtered by `mid in live` and would happily have fired four
    lances off a hull with three, charging the heat for all four.
    """
    live: dict = {}
    for shot in mounts(b, side, other):
        if shot.can_fire:
            live[shot.mount_id] = live.get(shot.mount_id, 0) + 1
    out = []
    for mid in list(mount_ids or []):
        if live.get(mid, 0) > 0:
            live[mid] -= 1
            out.append(mid)
    return out


def heat_of(b, mount_ids, side=None) -> float:
    """Heat the chosen mounts will put into the hull."""
    side = side if side is not None else b.player
    total = 0.0
    for mid in firing_set(b, mount_ids, side):
        w = _weapon(side, mid)
        if w is not None and w.wpn is not None:
            total += w.wpn.heat
    return total


def quote(b, mount_ids, side=None, other=None) -> dict:
    """What this volley does to the hull, before the trigger.

    Modelled on the turn as it actually resolves: the heat goes in and is
    clamped as each shot is fired, then `_end_of_turn` vents, then the fault
    test runs against what is left. Doing the vent before the test is not a
    detail — a volley that lands one point over the line and vents six is not a
    fault, and quoting it as one would be crying wolf.
    """
    side = side if side is not None else b.player
    other = other if other is not None else b.enemy
    will = firing_set(b, mount_ids, side, other)
    added = heat_of(b, will, side)
    cap, top = fault_line(side), ceiling(side)
    now = side.ship.heat
    after = max(0.0, min(now + added, top) - side.st.vent)
    damage = 0.0
    for mid in will:
        w = _weapon(side, mid)
        if w is not None and w.wpn is not None:
            damage += w.wpn.dmg * max(0.0, 1.0 - w.wpn.bears_at(
                tac.band_for(tac.separation(side.body, other.body))))
    return {
        "mounts": will,
        "asked": list(mount_ids or []),
        "heat_added": added,
        "heat_now": now,
        "heat_after": after,
        "fault_line": cap,
        "faults": after > cap,
        "over_by": max(0.0, after - cap),
        "damage": damage,
    }


#: Above this many mounts the exhaustive search is abandoned for the greedy
#: ordering. No chassis in the game has more than five weapon slots, so this is
#: a guard against a future hull rather than a live path — but 2^n on a
#: twenty-mount station would be a hang, and a hang is a worse answer than a
#: slightly suboptimal volley.
SEARCH_LIMIT = 12


def advise(b, side=None, other=None) -> list:
    """The hardest-hitting volley that will not leave the hull faulting.

    **This has been wrong twice, and playing it is what showed both.**

    First it ordered mounts by damage *per point of heat*, reasoning that heat
    is the constraint so heat is what to economise. That favours the small guns
    — a PDC is 8 damage for 2 heat, four per point; a Fusion Lance is 48 for 20,
    barely over two — so it picked the pea-shooters and left the main armament
    cold. Over twelve engagements it won 3 of 12 while firing one Fusion Lance
    every turn won 6, despite faulting a fifth of the time. Economising heat is
    not the job; killing the other hull is.

    Then it could advise firing *nothing*: on a hull already warm no mount could
    be added without crossing the line, so the answer was to sit still. Played,
    it said fire, hold, fire, hold — shooting half as often as the enemy.
    `ship.py` records the same lesson beside `HEAT_CEILING` from the last time:
    they "lost to their own radiators, in a fight they never shot in."

    So: **the most damage of any set that does not fault**, found exhaustively,
    because no hull in the game carries more than five mounts and 32 subsets is
    nothing. Greedy-by-damage is close but not provably best, and the check that
    holds this brute-forces the optimum — so it may as well be the answer rather
    than the yardstick.

    The floor is the single hardest-hitting mount that bears. Faulting is a cost;
    being harmless is a loss.
    """
    side = side if side is not None else b.player
    other = other if other is not None else b.enemy
    ready = [s for s in mounts(b, side, other) if s.can_fire]
    if not ready:
        return []

    def hits(shot) -> float:
        w = _weapon(side, shot.mount_id)
        if w is None or w.wpn is None:
            return 0.0
        return w.wpn.dmg * max(0.0, 1.0 - shot.penalty)

    ids = [s.mount_id for s in ready]
    if len(ready) <= SEARCH_LIMIT:
        best, best_hit = None, -1.0
        for mask in range(1, 1 << len(ready)):
            pick = [ids[i] for i in range(len(ready)) if mask >> i & 1]
            if quote(b, pick, side, other)["faults"]:
                continue
            worth = sum(hits(ready[i]) for i in range(len(ready))
                        if mask >> i & 1)
            if worth > best_hit:
                best, best_hit = pick, worth
        if best:
            return best
    else:
        picked: list = []
        for shot in sorted(ready, key=hits, reverse=True):
            trial = picked + [shot.mount_id]
            if not quote(b, trial, side, other)["faults"]:
                picked = trial
        if picked:
            return picked

    # Nothing at all fits under the line. Fire the heaviest gun anyway.
    return [max(ready, key=hits).mount_id]


def volley(b, mount_ids, rng, side=None, other=None) -> dict:
    """Fire the mounts the gunner chose, and nothing else.

    The act `quote` promises. Returns what was fired so a caller can say so.
    """
    from . import combat
    side = side if side is not None else b.player
    other = other if other is not None else b.enemy
    will = firing_set(b, mount_ids, side, other)
    if not will:
        return {"fired": [], "why": "Nothing chosen will bear."}
    for mid in will:
        if combat.is_destroyed(other.ship):
            break
        combat._fire(b, side, other, mid, rng)
    return {"fired": will, "why": ""}
