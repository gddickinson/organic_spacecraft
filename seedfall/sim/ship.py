"""The ship model.

A chassis, a set of fitted parts, a stack of hull layers and whatever is in the
hold. Everything the rest of the game asks about a ship derives from
:func:`stats`, which is pure — give it the same ship twice and it answers the
same way.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.save import register
from ..core.util import clamp
from ..data.chassis import (BASE_POWER, CHASSIS_BY_ID, LAYER_SETS, NO_REGEN,
                            Chassis)
from ..data.commodities import bulk_of
from ..data.parts import part
from . import loading

_uid = itertools.count(1)

# Chassis hull figures are written on a descriptive scale (a NAVIS reads as a far
# tougher thing than a SPORE, which it is). This converts that scale into combat
# hit points, tuned so a fair engagement lasts eight to fourteen turns rather
# than half an hour.
HULL_SCALE = 0.24


@register
@dataclass
class HullLayer:
    id: str
    name: str
    note: str
    critical: bool
    life: bool
    max: float
    hp: float
    regen: float


@register
@dataclass
class Ship:
    uid: int
    name: str
    chassis: str
    fitted: list[str]
    layers: list[HullLayer] = field(default_factory=list)
    heat: float = 0.0
    crew: int = 1
    morale: float = 0.75
    cargo: dict[str, float] = field(default_factory=dict)
    o2: float = 1.0
    disabled: list[str] = field(default_factory=list)
    docked_at: int | None = None
    #: Sails with the flag and fights alongside it, rather than sitting berthed.
    escort: bool = False

    @property
    def chassis_def(self) -> Chassis:
        return CHASSIS_BY_ID[self.chassis]


@dataclass
class Stats:
    """Derived numbers. Never stored — recomputed whenever anything changes."""
    family: str = "grown"
    power: float = 0
    draw: float = 0
    brownout: float = 1
    jump: float = 1
    speed: float = 1
    evade: float = 0
    accuracy: float = 0.6
    sensor: float = 2
    scan: float = 0.25
    cargo: float = 0
    berths: int = 0
    armour: float = 0
    heat_cap: float = 40
    vent: float = 6
    regen: float = 0
    mine: float = 0
    drink: float = 0
    graze: float = 0
    phos: float = 0
    research: float = 0
    o2_days: float = 14
    crew_guard: float = 0
    flak: int = 0
    refine: float = 0
    can_colonise: bool = False
    can_dive: bool = False
    has_drift: bool = False
    trade: float = 0
    diplomacy: float = 0
    morale: float = 0
    mass: float = 0
    weapons: list = field(default_factory=list)
    abilities: list = field(default_factory=list)


def make_ship(chassis_id: str, fitted=(), name: str | None = None) -> Ship:
    ch = CHASSIS_BY_ID.get(chassis_id)
    if ch is None:
        raise ValueError(f"unknown chassis {chassis_id!r}")
    ship = Ship(uid=next(_uid), name=name or ch.name, chassis=chassis_id,
                fitted=list(fitted), crew=max(1, round(ch.crew * 0.6)))
    build_layers(ship)
    return ship


def build_layers(ship: Ship, bonus: dict | None = None) -> Ship:
    """(Re)create the layer stack at full health, sized by hull points."""
    bonus = bonus or {}
    ch = ship.chassis_def
    mul = 1 + bonus.get("hull", 0.0)
    for pid in ship.fitted:
        p = part(pid)
        if p and "hullMul" in p.fx:
            mul += p.fx["hullMul"]
    total = ch.hull * mul * HULL_SCALE
    ship.layers = [
        HullLayer(L.id, L.name, L.note, L.critical, L.life,
                  round(total * L.w), round(total * L.w), L.regen)
        for L in LAYER_SETS[ch.family]
    ]
    return ship


_FX_KEYS = ("power draw jump speed evade sensor scan cargo berths regen vent "
            "heatCap mine drink graze phos research accuracy armour o2 morale "
            "crewGuard flak repair colony dive drift refine").split()


def stats(ship: Ship, bonus: dict | None = None, officers=()) -> Stats:
    """Derived stats: chassis base + parts + research bonuses + crew skill."""
    bonus = bonus or {}
    ch = ship.chassis_def
    fx = dict.fromkeys(_FX_KEYS, 0.0)

    for pid in ship.fitted:
        if pid in ship.disabled:
            continue
        p = part(pid)
        if p is None:
            continue
        for k, v in p.fx.items():
            if k in fx:
                fx[k] += v

    def skill(stat: str) -> int:
        return sum(o.level for o in officers if o.stat == stat)

    nav, eng = skill("nav"), skill("engineering")
    sci, tac = skill("science"), skill("tactical")
    med, com = skill("medicine"), skill("comms")

    # Power discipline: draw more than you generate and everything sags. A
    # synthetic hull is mostly reactor and carries the largest hotel load.
    power = fx["power"] + BASE_POWER.get(ch.family, 5)
    draw = fx["draw"]
    brownout = clamp(power / max(1, draw), 0.35, 1) if draw > power else 1.0

    # What the hull is carrying, against what it was built to carry. Fitted
    # mass used to be free, so every design was "the heaviest part that fits,
    # in every slot". Jump is deliberately dampened: a full hold slowing you
    # down is a trade, a full hold stranding you is a bug.
    load = loading.factor(ship, fx["speed"])
    jump_load = 1.0 + (load - 1.0) * 0.45

    s = Stats(
        family=ch.family, power=power, draw=draw, brownout=brownout,
        jump=max(1, ((ch.jump + fx["jump"]) * (1 + bonus.get("jump", 0))
                     + nav * 0.35) * jump_load),
        speed=max(0.2, (ch.speed * (1 + fx["speed"]) + nav * 0.03) * load),
        evade=clamp((ch.evade + fx["evade"] + tac * 0.02) * brownout * load, 0, 0.7),
        accuracy=clamp(0.62 + fx["accuracy"] + tac * 0.035, 0.15, 0.98) * brownout,
        sensor=2 + fx["sensor"] + sci * 0.2,
        scan=clamp(0.25 + fx["scan"] + bonus.get("scan", 0) + sci * 0.06, 0, 1),
        cargo=max(0, ch.cargo + fx["cargo"]),
        berths=int(ch.crew + fx["berths"]),
        armour=fx["armour"] + round(eng * 0.5),
        heat_cap=40 + fx["heatCap"] + eng * 4,
        vent=6 + fx["vent"] + eng * 1.5,
        regen=((1 + fx["regen"] + bonus.get("regen", 0) + eng * 0.05)
               * (0 if ch.family in NO_REGEN else 1)
               + ((0.5 + eng * 0.05) if fx["repair"] else 0)),
        mine=fx["mine"] * brownout,
        drink=fx["drink"] * brownout,
        graze=fx["graze"],
        phos=fx["phos"] * brownout,
        research=(fx["research"] + sci * 0.3) * (1 + bonus.get("research", 0)),
        o2_days=14 + fx["o2"] + med * 6,
        crew_guard=clamp(fx["crewGuard"] + med * 0.05, 0, 0.85),
        refine=fx["refine"],
        can_colonise=fx["colony"] > 0,
        can_dive=fx["dive"] > 0,
        has_drift=fx["drift"] > 0,
        trade=bonus.get("trade", 0) + com * 0.03,
        diplomacy=bonus.get("diplomacy", 0) + com * 0.05,
        morale=fx["morale"] + med * 0.1,
        mass=ch.mass_t + loading.laden(ship),
    )
    live = [pid for pid in ship.fitted if pid not in ship.disabled]
    s.weapons = [part(pid) for pid in live if part(pid) and part(pid).wpn]
    s.abilities = [part(pid) for pid in live if part(pid) and part(pid).ability]
    s.flak = int(fx["flak"]) + sum(1 for p in s.weapons if "flak" in p.wpn.traits)
    return s


# ── hull state ─────────────────────────────────────────────────────────────

def hull_total(ship: Ship) -> float:
    return sum(l.hp for l in ship.layers)


def hull_max(ship: Ship) -> float:
    return sum(l.max for l in ship.layers)


def hull_pct(ship: Ship) -> float:
    m = hull_max(ship)
    return hull_total(ship) / m if m > 0 else 0.0


def is_destroyed(ship: Ship) -> bool:
    return all(l.hp <= 0 for l in ship.layers)


def is_breached(ship: Ship) -> bool:
    """True once the pressure vessel is open — crew start dying."""
    p = next((l for l in ship.layers if l.critical), None)
    return p is None or p.hp <= 0


def apply_damage(ship: Ship, amount: float) -> float:
    """Damage from outside combat (hazards, Bloom attrition)."""
    left = amount
    for L in ship.layers:
        if L.hp <= 0:
            continue
        taken = min(L.hp, left)
        L.hp -= taken
        left -= taken
        if left <= 0:
            break
    return amount - left


def repair_tick(ship: Ship, days: float, s: Stats) -> float:
    """Between-turn healing: seal first, then rebuild, innermost layer first."""
    if s.regen <= 0:
        return 0.0
    budget = 0.0
    for L in reversed(ship.layers):
        if L.hp >= L.max:
            continue
        before = L.hp
        L.hp = min(L.max, L.hp + L.max * L.regen * s.regen * days)
        budget += L.hp - before
        if L.hp < L.max:
            break
    if budget > 0:
        fed = min(ship.cargo.get("biomass", 0), budget * 0.004)
        add_cargo(ship, "biomass", -fed)
    return budget


# ── cargo ──────────────────────────────────────────────────────────────────

def cargo_used(ship: Ship) -> float:
    return sum(n * bulk_of(cid) for cid, n in ship.cargo.items())


def cargo_free(ship: Ship, s: Stats) -> float:
    return max(0.0, s.cargo - cargo_used(ship))


def add_cargo(ship: Ship, cid: str, units: float) -> None:
    ship.cargo[cid] = ship.cargo.get(cid, 0) + units
    if ship.cargo[cid] <= 0.0001:
        ship.cargo.pop(cid, None)


