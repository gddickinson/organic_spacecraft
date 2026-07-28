"""Colonies — the empire layer.

You plant a seed and leave; it gestates for a year or two and then yields, every
day, wherever you happen to be.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.save import register
from ..data.colonies import COLONIES_BY_ID, colonies_for

_uid = itertools.count(1)


@register
@dataclass
class Colony:
    id: int
    class_id: str
    name: str
    system_id: int
    body_id: str
    need: int
    days: float = 0.0
    online: bool = False
    pop: float = 0.0
    starving: float = 0.0

    @property
    def definition(self):
        return COLONIES_BY_ID[self.class_id]


def _held(game, key: str) -> float:
    """How much of a material the player can reach: depot plus the hold."""
    if key == "credits":
        return game.credits
    return game.stores.get(key, 0) + game.ship.cargo.get(key, 0)


def can_found(game, system, body, class_id: str) -> tuple[bool, str]:
    c = COLONIES_BY_ID.get(class_id)
    if c is None:
        return False, "Unknown class."
    if body.kind not in c.sites:
        return False, f"{c.name} will not take root on that."
    if body.colony is not None:
        return False, "Something is already growing there."
    if c.tech and c.tech not in game.research.unlocked:
        return False, "Not yet researched."
    if system.bloom > 0.5:
        return False, "The Bloom holds this system."
    if c.family == "grown" and not game.ship_stats.can_colonise:
        return False, ("No seed bay fitted — you cannot gestate a seed out here. "
                       "Refit one at a port.")
    for key, need in c.cost.items():
        have = _held(game, key)
        if have < need:
            return False, f"Short of {key}: need {need:g}, have {int(have)}."
    return True, ""


def _spend(game, cost: dict) -> None:
    for key, need in cost.items():
        if key == "credits":
            game.credits -= need
            continue
        owed = need
        from_store = min(game.stores.get(key, 0), owed)
        game.stores[key] = game.stores.get(key, 0) - from_store
        owed -= from_store
        if owed > 0:
            game.ship.cargo[key] = game.ship.cargo.get(key, 0) - owed
            if game.ship.cargo[key] <= 0.0001:
                game.ship.cargo.pop(key, None)


def _gestation_help(game, system_id: int) -> float:
    """A GRAVID nursery in-system speeds every gestation around it."""
    for k in game.colonies:
        if (k.online and k.system_id == system_id
                and COLONIES_BY_ID[k.class_id].effects.get("gestation")):
            return 0.8
    return 0.0


def found(game, system, body, class_id: str):
    ok, why = can_found(game, system, body, class_id)
    if not ok:
        return None, why
    c = COLONIES_BY_ID[class_id]
    _spend(game, c.cost)

    speed = 1 + game.bonuses.get("growth", 0) + _gestation_help(game, system.id)
    col = Colony(id=next(_uid), class_id=class_id,
                 name=f"{c.name} · {body.name}", system_id=system.id,
                 body_id=body.id, need=max(10, round(c.days / speed)))
    body.colony = col.id
    game.colonies.append(col)
    return col, ""


def tick(game, days: float) -> tuple[dict, list]:
    """Advance every colony. Returns (materials gained, log events)."""
    gains: dict[str, float] = {}
    events: list[tuple[str, str]] = []

    for col in game.colonies:
        c = col.definition
        if not col.online:
            col.days += days
            if col.days >= col.need:
                col.online = True
                col.pop = c.pop
                events.append(("good", f"{col.name} has matured and is online."))
            continue

        affordable = True
        for key, n in c.upkeep.items():
            owed = n * days
            have = game.credits if key == "credits" else game.stores.get(key, 0)
            if have < owed:
                affordable = False
                break
            if key == "credits":
                game.credits -= owed
            else:
                game.stores[key] -= owed
        if not affordable:
            col.starving += days
            if col.starving > 30:
                events.append(("bad", f"{col.name} is starving — yields have stopped."))
            continue
        col.starving = 0

        for key, n in c.yields.items():
            amount = n * days
            if key == "credits":
                game.credits += amount
            elif key == "research":
                game.research.banked += amount
            else:
                game.stores[key] = game.stores.get(key, 0) + amount
                gains[key] = gains.get(key, 0) + amount
        if c.pop:
            col.pop = min(c.pop, col.pop + c.pop * 0.0008 * days)
    return gains, events


def effects(game) -> dict:
    """Aggregate colony effects the rest of the game asks about."""
    out = {"sensor_by_system": {}, "build_systems": set(), "watch_systems": set(),
           "has_vault": False, "has_medical": False, "has_fabricator": False,
           "research": 0.0, "diplomacy": 0.0, "pop": 0.0, "count": 0}
    for col in game.colonies:
        if not col.online:
            continue
        e = col.definition.effects
        out["count"] += 1
        out["pop"] += col.pop
        if e.get("sensor"):
            key = col.system_id
            out["sensor_by_system"][key] = out["sensor_by_system"].get(key, 0) + e["sensor"]
        if e.get("build_here"):
            out["build_systems"].add(col.system_id)
        if e.get("watch"):
            out["watch_systems"].add(col.system_id)
        out["has_vault"] |= bool(e.get("vault"))
        out["has_medical"] |= bool(e.get("medical"))
        out["has_fabricator"] |= bool(e.get("fabricate"))
        out["diplomacy"] += e.get("diplomacy", 0)
    return out


def bloom_attack(game, system, rng) -> list[Colony]:
    """The Bloom eats colonies it reaches."""
    here = [c for c in game.colonies if c.system_id == system.id]
    lost = []
    for col in here:
        if rng.chance(0.30 * system.bloom):
            body = next((b for b in system.bodies if b.id == col.body_id), None)
            if body:
                body.colony = None
            lost.append(col)
    if lost:
        game.colonies = [c for c in game.colonies if c not in lost]
    return lost


__all__ = ["Colony", "can_found", "found", "tick", "effects", "bloom_attack",
           "colonies_for", "COLONIES_BY_ID"]
