"""What a turn will do to the hull, before the captain commits to it.

Split out of `sim/stations.py`, which owns the seats and their acts; this owns
the *forecast* of a turn that contains one. They are different jobs and the file
was over five hundred lines carrying both.

The reason this module exists at all: `order_preview` used to cost an order in
isolation, and a captain does not give an order in isolation. They give it
inside a turn, in which the two seats they have just walked away from run
themselves. Measured on a Bastion at 45 of a 50 heat cap, sitting down at
engineering and ordering *vent* — the one order whose entire purpose is
cooling — the panel said `heat 45 → 20` and the turn ended at **74**, because
the gunner left at the guns fires everything that bears, always, whatever the
heat.

So every figure here is a dry run of the act rather than a formula beside it:

- `bearing_set` is the list `combat._salvo` fires and the log counts.
- `will_burn` drops the dry mounts, which are announced aloud and then put no
  heat into the hull, because `combat._fire` returns before `add_heat`.
- `idle_gunnery` and `idle_engineering` are what the seats you are not in do,
  and `combat._run_stations` asks the first of them rather than deciding again.
- `flown` flies this turn's helm order on a copy of the hull, because our guns
  fire from where our own helm has just put us and the enemy does not move
  until afterwards — so it is not an estimate, it is where the shot is taken
  from.
- `turn_heat` steps those in the order `combat.take_turn` steps them.

Exact, over thousands of played turns, for every turn the engagement carries on
past. On the turn it ends, `_finish` returns before `_end_of_turn` and the
radiators never shed; `tests/test_turnplan.py` counts those rather than hiding
them.
"""

from __future__ import annotations

from .ship import HEAT_CEILING
from .stations import (ORDERS_BY_ID, ROUTE_ACCURACY, ROUTE_SPEED, ROUTE_ACCEL,
                       UNATTENDED_VENT, VENT_PER_LEVEL, bears_on, doctrine,
                       officer_level, run_helm)


def _shots(side, other) -> list:
    """Each mount paired with `firing.solution`'s answer for it.

    `solution` is the one place in the game that answers "can this mount shoot",
    and it skips mounts with no weapon, so the pairing walks the same filtered
    list in the same order. Asking it here retires the fourth hand-rolled copy
    of arc-and-band-and-magazine.
    """
    from . import firing
    mounts = [w for w in side.st.weapons if w.wpn is not None]
    return list(zip(mounts, firing.solution(side, other)))


def bearing_set(side, other) -> list:
    """What a salvo will train on the target: in arc, and in range.

    One definition of "what bears" — `combat._salvo` fires this list and the log
    line counts it, so the count under the button and the count in the log are
    the same count. A dry mount is *in* it: the act names it aloud, which is how
    the captain learns the torpedoes are out.
    """
    from . import firing
    return [w for w, s in _shots(side, other)
            if s.in_arc and s.penalty <= firing.WORTH_FIRING]


def will_burn(side, other) -> list:
    """Of those, the mounts that actually put heat into the hull.

    Not the dry ones. `combat._fire` announces an empty magazine and returns
    *before* `add_heat`, and `gunnery.firing_set` has said since the gunner's
    board was written that "a quote that charged for it would be wrong in the
    direction that matters". The orders panel was charging for it: a Bastion
    carrying a Breach Torpedo with no alloy in the hold was quoted nine points
    of heat a turn that the hull never took.
    """
    return [w for w, s in _shots(side, other) if s.worth_it]


def heat_of(mounts) -> float:
    """What firing these puts into the hull."""
    return sum(w.wpn.heat for w in mounts)


def idle_gunnery(side, other, officers) -> dict:
    """What the guns do while the captain is standing in another seat.

    The gunner keeps working, and without a battle computer it is salvo,
    always, whatever the heat — which is deliberate, and is what a computer is
    bought to fix. What was *not* deliberate is that the orders panel forecast
    each order as though the other two seats did nothing: **vent promised to
    shed 25 on a 50 cap and the turn ended at 74**, because the gunner the
    captain had just walked away from fired everything that bore. The one order
    in the game whose whole purpose is cooling was quoted with the wrong sign.

    So this is the single door. `combat._run_stations` fires what it names and
    `order_preview` costs what it names, and neither can drift from the other.
    """
    chosen = doctrine.order_for(side, other, "gunnery")
    pick = chosen[0] if chosen else "salvo"
    bearing = bearing_set(side, other)
    if pick == "aimed" and bearing:
        bearing = [max(bearing, key=lambda w: w.wpn.dmg)]
    elif pick not in ("salvo", "aimed"):
        bearing = []
    hot = will_burn(side, other)
    return {"order": pick, "mounts": bearing,
            "heat": heat_of([w for w in bearing if w in hot]),
            "computer": chosen is not None}


def idle_engineering(side, other, officers) -> float:
    """What the engineering section does to the hull's heat, unattended.

    The other half of the same door: `run_engineering`'s undirected path sheds
    exactly this, so a forecast that asks here cannot disagree with the section
    that answers to it.
    """
    skill = officer_level(officers, "engineering")
    share = min(1.0, UNATTENDED_VENT + VENT_PER_LEVEL * skill)
    chosen = doctrine.order_for(side, other, "engineering") if other is not None \
        else None
    if chosen is None:
        return -min(side.ship.heat, side.st.vent * share)
    if chosen[0] == "vent":
        return -min(side.ship.heat, (side.st.vent * 2.2 + 12) * share)
    return 0.0


def flown(side, other, order_id: str, officers):
    """The hull where the guns will find it — a dry run of this turn's helm.

    Not an estimate. `combat.take_turn` runs `_run_stations` — our seats, then
    our guns — and only afterwards `_enemy_turn`, so a shot this turn is taken
    from where our own helm has just put us, against the enemy exactly where it
    stands now. Flying the order on a copy of the body is therefore the whole
    answer, and it is what turns "about 45" into 45.

    It matters most at *present the broadside*, whose own blurb says everything
    on the flanks bears: forecasting at the aspect before the turn said nothing
    bore and quoted the order as cooling, and the turn brought four mounts on
    and made 24. Eight turns in a thousand were quoted with the wrong sign, and
    every one of them was that order.
    """
    import copy
    from dataclasses import replace

    order = ORDERS_BY_ID.get(order_id or "")
    ghost = copy.copy(side)
    ghost.body = replace(side.body)
    # `run_engineering` clears the routing at the top of every turn and sets it
    # again only for this turn's order, and `run_helm` reads it — which is why
    # *power to the drive* moves the hull further on the turn it is given.
    ghost.route = ("engines" if order_id == "route_engines"
                   else "guns" if order_id == "route_guns" else None)
    at_helm = bool(order) and order.station == "helm"
    run_helm(ghost, other, order.id if at_helm else None, at_helm, officers)
    return ghost


def turn_heat(side, other, order_id: str, officers) -> dict:
    """Where the hull's heat ends the turn if this order is given.

    Not what the order does — what the *turn* does. The captain chooses one
    order and the other two seats run themselves, so a forecast of the order
    alone is a forecast of something nobody can buy. Stepped in the order
    `combat.take_turn` steps it: engineering, then the guns, then the hull sheds
    what its radiators shed.

    The range is taken as it stands. A helm order is about to change it, which
    is why `order_preview` says so under a helm order rather than pretending to
    a figure it cannot have.
    """
    order = ORDERS_BY_ID.get(order_id)
    seat = order.station if order else None
    cap = getattr(side.st, "heat_cap", 0.0) or 1.0
    ceiling = cap * HEAT_CEILING
    heat = getattr(side.ship, "heat", 0.0)
    #: The hull touched its physical ceiling somewhere in the turn, even if the
    #: radiators brought it back under by the end. Worth saying either way: heat
    #: past the ceiling is heat the hull could not hold and simply lost.
    pinned = False

    def put(delta: float) -> None:
        """Move the heat the way the hull moves it.

        The ceiling belongs to `ship.add_heat`, which is the only way heat goes
        *in*; shedding is a plain `max(0, heat - x)` and never consults it. That
        distinction matters exactly when a hull is already above its ceiling —
        which happens whenever a hit takes out a radiator and `heat_cap` falls
        under the heat already in the hull. Clamping on the way down as well
        cooled such a hull by five points a turn on paper and not at all in
        fact: 107 with a cap of 48 was forecast at 87 and came out at 92.

        Nothing added is not a small addition, either: `put(0.0)` must leave the
        hull alone, because `add_heat` is not called at all on a turn when no
        mount fires. Written `delta >= 0` it clamped anyway, which cooled an
        over-ceiling hull by five points for firing nothing.
        """
        nonlocal heat, pinned
        if delta > 0:
            if heat + delta >= ceiling - 1e-9:
                pinned = True
            heat = max(0.0, min(heat + delta, ceiling))
        else:
            heat = max(0.0, heat + delta)

    # Engineering first, exactly as `combat._run_seats` runs it: it decides
    # where the power goes and the other two seats spend it.
    if seat == "engineering":
        put(-min(heat, side.st.vent * 2.2 + 12) if order_id == "vent" else 0.0)
    else:
        put(idle_engineering(side, other, officers))

    # Then the guns — yours if you are sitting at them, the gunner's if not —
    # fired from where the helm has just put the hull, not from where it was
    # when the button was drawn.
    ghost = flown(side, other, order_id, officers)
    if seat == "gunnery":
        bearing = bearing_set(ghost, other)
        if order_id == "aimed" and bearing:
            bearing = [max(bearing, key=lambda w: w.wpn.dmg)]
        elif order_id != "salvo":
            bearing = []
        hot = will_burn(ghost, other)
        guns = heat_of([w for w in bearing if w in hot])
    else:
        guns = idle_gunnery(ghost, other, officers)["heat"]
    before_guns = heat
    put(guns)
    guns_did = heat - before_guns

    put(-min(heat, side.st.vent))
    return {"after": heat, "cap": cap, "ceiling": ceiling, "pinned": pinned,
            "guns": guns_did, "seat": seat}


def order_preview(side, other, order_id: str, officers, band: int = 0) -> dict:
    """What one order will actually do this turn, before it is given.

    The seats say what taking them is worth; the orders inside them were bare
    buttons with a sentence of prose. Since heat became a real constraint that
    matters most at gunnery: a Bastion at 30 of a 50 cap that fires everything
    makes 74 more and ends the turn pinned at the ceiling, and nothing on the
    screen said so before the button was pressed.

    Returns `{"lines": [...], "heat": delta, "over": bool}`. Helm orders are
    left to the firing picture, which already says what coming about would
    bring on.
    """
    out = {"lines": [], "heat": 0.0, "over": False}
    order = ORDERS_BY_ID.get(order_id)
    if order is None:
        return out
    cap = getattr(side.st, "heat_cap", 0.0) or 1.0
    now = getattr(side.ship, "heat", 0.0)

    # What bears and what that costs both come from the doors the act uses —
    # `bearing_set` is the list `combat._salvo` fires and counts in the log, and
    # `will_burn` drops the dry mounts, which are announced and then put no heat
    # into the hull at all.
    if order.id == "salvo":
        bearing = bearing_set(side, other)
        live = will_burn(side, other)
        out["heat"] = heat_of([w for w in bearing if w in live])
        out["lines"].append(
            f"{len(bearing)} of {len(side.st.weapons)} mounts bear"
            if bearing else "nothing bears — the turn is spent for nothing")
        empty = [w.name for w in bearing if w not in live]
        if empty:
            out["lines"].append(
                f"{', '.join(empty)} will train and cannot fire — no "
                "ammunition, and no heat either")
    elif order.id == "aimed":
        bearing = bearing_set(side, other)
        live = will_burn(side, other)
        if bearing:
            best = max(bearing, key=lambda w: w.wpn.dmg)
            out["heat"] = best.wpn.heat if best in live else 0.0
            out["lines"].append(f"{best.name}, {best.wpn.dmg} damage"
                                + ("" if best in live else " — and it is dry"))
        else:
            out["lines"].append("nothing bears for an aimed shot")
    elif order.id == "hold_fire":
        out["lines"].append("nothing fired; the mounts stay loaded")
    elif order.id == "vent":
        shed = side.st.vent * 2.2 + 12
        out["heat"] = -min(now, shed)
        out["lines"].append(f"sheds up to {shed:.0f}")
    elif order.id == "damage_control":
        skill = officer_level(officers, "engineering")
        hurt = next((l for l in reversed(side.ship.layers)
                     if 0 < l.hp < l.max), None)
        if hurt is None:
            out["lines"].append("nothing is breached")
        else:
            gain = hurt.max * (0.06 + 0.02 * skill) * (
                1.6 if side.st.regen > 0 else 1.0)
            out["lines"].append(
                f"patches about {min(gain, hurt.max - hurt.hp):.0f} of "
                f"{hurt.name}")
    elif order.id == "route_guns":
        out["lines"].append(f"{ROUTE_ACCURACY:+.0%} to hit, this turn")
    elif order.id == "route_engines":
        out["lines"].append(
            f"{ROUTE_SPEED - 1:+.0%} top speed and {ROUTE_ACCEL - 1:+.0%} "
            "acceleration, this turn")

    # Clamped, because the hull is: a salvo that would make 104 on a 50 cap
    # actually stops at the ceiling, and a forecast that quotes the raw sum is
    # the same defect this function exists to fix, one layer up.
    ceiling = cap * HEAT_CEILING
    out["heat"] = max(0.0, min(now + out["heat"], ceiling)) - now

    # And the rest of the turn. The captain gives one order; the other two
    # seats run themselves and the radiators shed what they shed. Quoting the
    # order alone made *vent* — the one order whose entire purpose is cooling —
    # promise 45 → 20 on a 50 cap when the turn actually ended at 74, because
    # the gunner the captain had just left fired everything that bore.
    told = turn_heat(side, other, order_id, officers)
    after = told["after"]
    out["after"] = after
    out["turn"] = after - now
    out["idle_guns"] = told["guns"] if order.station != "gunnery" else 0.0
    if out["idle_guns"] >= 0.5:
        # Short on purpose. The row on the battle screen joins these with " · ",
        # and the first draft spent forty characters repeating, under all five
        # helm orders, a warning the panel above already carries in red — which
        # pushed the one figure that varies off the end of the line. Say whose
        # heat it is and how much; the screen says why elsewhere.
        out["lines"].append(f"your gunner: +{out['idle_guns']:.0f}")
    out["over"] = after > cap
    out["pinned"] = told["pinned"]
    said = f"heat {now:.0f} → {after:.0f} of {cap:.0f} by the end of the turn"
    if told["pinned"]:
        said += " — pinned at the ceiling on the way"
    elif out["over"]:
        said += " — over the cap"
    out["lines"].append(said)
    return out


