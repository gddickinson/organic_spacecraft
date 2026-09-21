"""Taking over one gun yourself, and leaving the computer the rest.

A ship's armament has always been fought as a whole: the captain says
*broadside* and `sim/gunnery.py` decides which mounts speak. That is the right
grain for commanding and it leaves no room at all for *being* a gunner — so
this is the door between the two.

Every armament fitted to a hull is a mounting somebody can sit behind. `seats`
lists them, `take` puts you in one, and the engagement it opens on is the real
one: the ship the game has actually matched you against, its consorts, and
yours. What you do at that gun comes back to the turn-based battle as damage
dealt, through `land`, so an action fought by hand and an action fought by
order are the same fight.

**The turn-based battle is still the battle.** A skirmish opened off one is a
window into it, not a replacement: it runs while the captain's turn is being
decided, it cannot move the ship, and what it kills is what the volley would
have killed. Two models of one engagement that disagreed would be the worst
kind of bug this project has, so there is exactly one number that crosses —
damage — and it crosses in one direction.
"""

from __future__ import annotations

from ..data import armaments, turrets as turret_data
from . import foes, skirmish, turret as turret_sim

#: Where a mounting sits on the hull, by how many are fitted — so two guns on
#: one ship are in different places and see different skies. In half-lengths,
#: `data/mounts.py`'s frame: dorsal first, because that is the seat with the
#: best arc and the one a captain takes.
BLISTERS = (
    ("Dorsal mounting", (0.0, 0.15, 0.95)),
    ("Ventral mounting", (0.0, 0.10, -0.95)),
    ("Starboard blister", (0.85, -0.10, 0.20)),
    ("Port blister", (-0.85, -0.10, 0.20)),
    ("Forward mounting", (0.0, 0.92, 0.18)),
    ("Aft mounting", (0.0, -0.90, 0.25)),
)


def seats(game) -> list:
    """Every gun on the player's hull that a person could work.

    One row per fitted armament, in the order they sit on the ship. A part
    with no `wpn` is not a gun and gets no seat — a Whipple screen is a good
    thing to have and a poor thing to sit behind.
    """
    ship = getattr(game, "ship", None)
    if ship is None:
        return []
    made = []
    by_id = {p.id: p for p in armaments.ARMAMENTS}
    for index, part_id in enumerate(getattr(ship, "fitted", []) or []):
        part = by_id.get(part_id)
        if part is None or part.wpn is None:
            continue
        where, at = BLISTERS[len(made) % len(BLISTERS)]
        kind = turret_data.for_part(part_id)
        made.append({
            "mount": part_id,
            "name": f"{part.name} — {where.lower()}",
            "seat": where,
            "at": at,
            "kind": kind,
            "part": part,
            "ready": True,
            "slot": index,
        })
    return made


def seat_for(game, part_id: str):
    """One seat by the armament in it, or None if the hull has no such gun."""
    return next((s for s in seats(game) if s["mount"] == part_id), None)


def take(game, part_id: str) -> tuple:
    """Sit down at one of your own guns. Returns `(action, why)`.

    Refused when there is nothing to shoot at, and the refusal says where to
    go instead — a gunner with an empty sky wants the school, not an empty
    window.
    """
    seat = seat_for(game, part_id)
    if seat is None:
        return None, "The hull has no such gun fitted."
    battle = getattr(game, "battle", None)
    if battle is None or getattr(battle, "over", False):
        return None, ("Nothing is shooting at you. The school is where a "
                      "gunner practises; take a drill.")
    turret = turret_sim.make(part_id, seat=seat["seat"], at=seat["at"])
    action = skirmish.open_action(
        turret, _from_battle(game, battle), hull=battle.player.ship.name,
        hp=_hull_left(battle.player.ship), max_hp=_hull_max(battle.player.ship),
        evade=min(0.8, max(0.0, float(getattr(battle.player.st, "evade", 0.3)))),
        setting="deep")
    action.log.append(
        f"{seat['seat']} manned against {battle.enemy_name}.")
    return action, ""


def _hull_left(ship) -> float:
    return sum(max(0.0, layer.hp) for layer in getattr(ship, "layers", []))


def _hull_max(ship) -> float:
    return max(1.0, sum(layer.max for layer in getattr(ship, "layers", [])))


def _from_battle(game, battle) -> list:
    """The engagement, as contacts a gunner can see and shoot.

    The enemy at its real range, its consorts and yours, and the fittings a
    gunner can take off each — which is the whole reason to man a gun rather
    than order a broadside: a volley cannot choose a turret.
    """
    from . import tactical as tac
    made = []
    span = max(0.6, tac.separation(battle.player.body, battle.enemy.body)
               / 24.0)
    made.append(foes.fit(foes.make(
        "enemy", battle.enemy_name, "hull", (0.0, span, 0.0),
        behaviour="strafe", stand_km=max(1.5, span * 0.7), pace=0.22,
        hostile=True, faction=battle.enemy_faction or "",
        guns=(foes.MEDIUM, foes.LIGHT),
        hp=_hull_left(battle.enemy.ship), max_hp=_hull_max(battle.enemy.ship)),
        "turret", "turret", "engine", "sensor"))
    for index, consort in enumerate(getattr(battle, "consorts", []) or []):
        name = getattr(consort, "name", None) or f"Consort {index + 1}"
        made.append(foes.make(
            f"consort-{index}", str(name), "consort",
            (2.6 if index % 2 else -2.6, 1.4, 0.4 * (1 if index % 2 else -1)),
            behaviour="escort", stand_km=3.0, pace=0.14, hostile=False))
    return made


def land(game, action, battle) -> dict:
    """Carry what the gun did back to the engagement it was fought in.

    The one number that crosses, and it crosses once: whatever the gunner
    took off the enemy in the skirmish comes off the enemy in the battle.
    Called when the seat is left, and idempotent — `action.banked` is the
    meter, the same shape `berthing.charged` uses for exactly this reason.
    """
    if action is None or battle is None or getattr(battle, "over", False):
        return {"ok": False, "dealt": 0.0}
    enemy = next((c for c in action.contacts if c.id == "enemy"), None)
    if enemy is None:
        return {"ok": False, "dealt": 0.0}
    dealt = max(0.0, enemy.max_hp - enemy.hp)
    owed = dealt - float(getattr(action, "banked", 0.0))
    if owed <= 0.0:
        return {"ok": True, "dealt": 0.0}
    action.banked = dealt
    # `ship.apply_damage` is the one door onto taking hull off a ship —
    # `sim/damage` is the *battle's* resolver and wants a Side and a trait
    # list, which a hand-fired round has neither of.
    from .ship import apply_damage
    took = apply_damage(battle.enemy.ship, owed)
    battle.player.dealt += took
    battle.enemy.taken += took
    battle.log.append(
        f"The {action.turret.seat.lower()} put {took:,.0f} into "
        f"{battle.enemy_name} by hand.")
    return {"ok": True, "dealt": took}
