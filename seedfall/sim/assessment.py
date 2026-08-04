"""Reading an engagement while you are in it.

Combat grew arcs, bands, crew stations, consorts and abilities, and the screen
grew a scrolling list of damage lines. A captain losing a fight could see every
hit and not one reason for any of them: not that the enemy outweighs them three
to one, not that every mount aboard is a broadside and the target is dead ahead,
not that the hull is fast enough to leave whenever it likes.

Nothing here changes anything. It reads the same state the resolver does and
says what it means.
"""

from __future__ import annotations

from ..data.part_types import BANDS
from . import stations as st_mod
from . import tactical as tac
from .ship import hull_pct

#: Thresholds on the turns-to-break ratio, calibrated against measured
#: outcomes rather than guessed. Over 320 fights across two player hulls and
#: eight difficulties: below 0.3 the player won 1%, 0.3-1.0 won 5%, 1-2 won
#: 25%, above 2 won 44%. A first pass compared raw hull and raw damage and was
#: not even monotonic — enemy hull is a chassis lottery that ignores
#: difficulty, while armament and armour both track it.
OUTMATCHED = 0.30
EVEN = 1.0
DOMINANT = 2.0


#: Armour never nulls a weapon completely; combat floors the leak-through here.
LEAK = 0.15


def _throw(side, against) -> float:
    """Damage a side lands in a turn, after the other's armour.

    Comparing raw hull and raw damage is worse than useless here: enemy hull is
    a chassis lottery that does not track difficulty at all, while armament and
    armour both do. A scale-1 opponent often carries no armament whatever and a
    scale-3 one carries a hundred and twenty points of it.
    """
    total = 0.0
    from .abilities import armour_of
    for part in side.st.weapons:
        if part.wpn is None:
            continue
        total += max(part.wpn.dmg * LEAK, part.wpn.dmg - armour_of(against))
    return total


def turns_to_break(attacker, defender) -> float:
    """Turns of everything-bearing fire to take a hull apart."""
    throw = _throw(attacker, defender)
    hull = sum(layer.hp for layer in defender.ship.layers)
    if throw <= 0:
        return float("inf")
    return max(1.0, hull / throw)


def weight(battle) -> dict:
    """Who breaks whom first, which is the only comparison that matters."""
    mine = sum(layer.max for layer in battle.player.ship.layers) or 1.0
    theirs = sum(layer.max for layer in battle.enemy.ship.layers) or 1.0
    my_throw = _throw(battle.player, battle.enemy)
    their_throw = _throw(battle.enemy, battle.player)
    my_turns = turns_to_break(battle.player, battle.enemy)
    their_turns = turns_to_break(battle.enemy, battle.player)
    # Longer for them to break you than for you to break them is the good case.
    ratio = (their_turns / my_turns) if my_turns else 0.0
    if ratio < OUTMATCHED:
        verdict, tint = "outmatched", "bad"
    elif ratio < EVEN:
        verdict, tint = "the lighter hull", "warn"
    elif ratio < DOMINANT:
        verdict, tint = "a real fight", ""
    elif ratio < float("inf"):
        verdict, tint = "the heavier hull", "chloro"
    else:
        verdict, tint = "unopposed", "chloro"
    return {"ratio": ratio, "verdict": verdict, "tint": tint,
            "my_hull": mine, "their_hull": theirs,
            "my_throw": my_throw, "their_throw": their_throw,
            "my_turns": my_turns, "their_turns": their_turns}


def mounts(battle) -> dict:
    """Why your guns are or are not contributing.

    Delegates to `sim/firing.solution`, which is the one place that decides.
    This used to work it out again with its own threshold — 0.5 against the
    0.6 `combat._fire` actually enforces — so a marginal mount fired when
    ordered and was reported here as out of range.
    """
    from . import firing
    by_id = {m.id: m for m in battle.player.st.weapons}
    bearing, off_arc, out_of_range = [], [], []
    for shot in firing.solution(battle.player, battle.enemy, battle.band):
        part = by_id.get(shot.mount_id)
        if part is None:
            continue
        if shot.worth_it:
            bearing.append(part)
        elif not shot.in_arc:
            off_arc.append((part, shot.gap))
        else:
            out_of_range.append(part)
    return {"bearing": bearing, "off_arc": off_arc,
            "out_of_range": out_of_range,
            "total": len(battle.player.st.weapons)}


def preferred_band(side) -> tuple[int, int] | None:
    """The band envelope this side's armament actually wants."""
    weapons = [w for w in side.st.weapons if w.wpn]
    if not weapons:
        return None
    return (min(w.wpn.bands[0] for w in weapons),
            max(w.wpn.bands[1] for w in weapons))


def can_outrun(battle) -> bool:
    _turn, _accel, mine = tac.manoeuvrability(battle.player.st)
    _t, _a, theirs = tac.manoeuvrability(battle.enemy.st)
    return mine > theirs * 1.05


def advice(battle) -> list[tuple[str, str]]:
    """The two or three things actually worth saying, worst first."""
    out: list[tuple[str, str]] = []
    read = weight(battle)
    guns = mounts(battle)

    if read["ratio"] < OUTMATCHED:
        out.append(("bad", "You are outmatched. Breaking off costs you very "
                           "little; this does not."))
    if hull_pct(battle.player.ship) < 0.35:
        out.append(("bad", "The hull will not take much more. Disengage or "
                           "brace — a breach kills crew every turn it stays."))

    if guns["total"] and not guns["bearing"]:
        if guns["off_arc"]:
            worst = min(guns["off_arc"], key=lambda pair: pair[1])
            arc = tac.arc_name(tac.arc_of(worst[0])).lower()
            out.append(("warn", f"Nothing bears. Your {arc} mounts are "
                                f"{round(worst[1])}° off — take the helm and "
                                "turn before firing again."))
        else:
            want = preferred_band(battle.player)
            if want:
                where = ("close the range" if battle.band > want[1]
                         else "open the range")
                out.append(("warn", f"Nothing is in range. Your armament wants "
                                    f"{BANDS[want[0]].lower()} to "
                                    f"{BANDS[want[1]].lower()}; {where}."))

    if battle.player.ship.heat > battle.player.st.heat_cap * 0.85:
        out.append(("warn", "The hull is running hot. Another salvo and the "
                            "mounts start missing."))

    if not out and read["ratio"] >= DOMINANT:
        out.append(("chloro", "You have the weight of this. Keep the range "
                              "your guns want and it will not take long."))
    return out[:3]


def intent(battle) -> str:
    """What the enemy did with its helm last turn, in plain words."""
    order = getattr(battle.enemy, "helm_order", None)
    return {"close": "closing the range",
            "open": "opening the range and running",
            "comeabout": "coming about to bring its mounts on",
            "broadside": "presenting its broadside",
            "hold": "holding station"}.get(order or "", "manoeuvring")


def read(battle) -> dict:
    """Everything the assessment panel needs, in one call."""
    return {"weight": weight(battle), "mounts": mounts(battle),
            "advice": advice(battle), "intent": intent(battle),
            "outrun": can_outrun(battle),
            "their_band": preferred_band(battle.enemy),
            "my_band": preferred_band(battle.player)}
