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
    #: The hands' age profile. They are a headcount rather than records — the
    #: game deliberately treats them as a mass — but a mass still gets older.
    #: Without these two numbers "your crew ages on a long crossing" was true
    #: of the three named officers and of nobody else aboard. See
    #: `sim/lifespan.py`.
    crew_age: float = 0.0
    crew_spread: float = 9.0
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
    #: How well the ship can fight itself. An unattended station repeats its
    #: last order forever; a battle computer lets it choose one. See
    #: `sim/doctrine.py`.
    doctrine: float = 0.0
    can_colonise: bool = False
    can_dive: bool = False
    has_drift: bool = False
    trade: float = 0
    conceal: float = 0
    diplomacy: float = 0
    morale: float = 0
    mass: float = 0
    weapons: list = field(default_factory=list)
    abilities: list = field(default_factory=list)


def next_uid() -> int:
    """A fresh hull identity. A captured ship keeps its layers and its cargo
    and cannot keep its uid — `consorts` and the fleet ledger both key on it."""
    return next(_uid)


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
            "crewGuard flak repair colony dive drift refine conceal doctrine").split()


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

    # What the bridge's *traits* add. Every one of the seven in `crew.TRAITS`
    # declares an effect and a magnitude and not one of them was ever applied:
    # `Officer.trait_id` was written when the candidate was generated and read
    # by nobody, so a Bloom veteran fought like anybody else while costing 25 a
    # month for the privilege.
    #
    # Six of the seven keys name a stat computed below. The seventh, `tactical`,
    # names the *skill* the combat numbers are derived from — so a first draft
    # converted it into levels, and measuring showed the conversion was nonsense:
    # it moved accuracy by 0.0026 where every other trait moved its stat by 0.03
    # to 0.05. A magnitude declared in stat units is a stat, so `tactical` adds
    # to accuracy and evade directly, which makes the combat trait a little
    # better than the two that do only one of them. That is the right shape for
    # the one that costs the same and reads as the strongest.
    from . import crew as crew_mod
    tr = crew_mod.trait_effects(officers)
    fight = tr.get("tactical", 0.0)

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
        evade=clamp((ch.evade + fx["evade"] + tr.get("evade", 0.0) + fight
                     + tac * 0.02) * brownout * load, 0, 0.7),
        accuracy=clamp(0.62 + fx["accuracy"] + tr.get("accuracy", 0.0) + fight
                       + tac * 0.035, 0.15, 0.98) * brownout,
        # `bonus["sensor"]` was not read here at all, so three colony works
        # promising longer reach — and any research that grants it — extended
        # your array by exactly nothing. Nothing depended on the number until
        # surveys started using it to decide what a sweep can reach.
        sensor=max(0.5, 2 + fx["sensor"] + bonus.get("sensor", 0) + sci * 0.2),
        scan=clamp(0.25 + fx["scan"] + bonus.get("scan", 0)
                   + tr.get("scan", 0.0) + sci * 0.06, 0, 1),
        doctrine=clamp(fx["doctrine"] + bonus.get("doctrine", 0), 0, 1),
        cargo=max(0, ch.cargo + fx["cargo"]),
        berths=int(ch.crew + fx["berths"]),
        armour=fx["armour"] + round(eng * 0.5),
        heat_cap=40 + fx["heatCap"] + eng * 4,
        vent=6 + fx["vent"] + eng * 1.5,
        regen=((1 + fx["regen"] + bonus.get("regen", 0)
                + tr.get("repair", 0.0) + eng * 0.05)
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
        trade=bonus.get("trade", 0) + tr.get("trade", 0.0) + com * 0.03,
        conceal=fx["conceal"],
        diplomacy=(bonus.get("diplomacy", 0) + tr.get("diplomacy", 0.0)
                   + com * 0.05),
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


#: Tonnes of biomass a grown hull eats to put back one point of itself.
#:
#: Sized against the hold rather than picked round. A full rebuild of the
#: starting hull is 336 points: at the old 0.004 that was 1.3 t and 89
#: credits, which is nothing, and at 0.05 it is 16.8 t and about 1,100 —
#: roughly the 20.5 t a new ship sails with, and 5% of a 340 t hold. So one
#: full rebuild is a hold-load you have to have thought about, and a ship
#: that has burned itself out with an empty hold does not heal at all.
FEED_PER_HP = 0.05


def excess_heat(ship: Ship, stats) -> float:
    """How far over its cap this hull is running, or 0 if it is not.

    **One door.** `cool` cooks on this and `repair_tick` refuses to rebuild
    on it, so a hull can never be regrowing the same layer the radiators are
    cooking. The two used to answer it separately — in fact only `cool` asked
    at all — and the honest clock showed what that was worth: over fourteen
    hard burns the ship cooked 225.8 hp and healed 239.7, so running 82 points
    over the cap for 74 days cost 7.5% of the hull. A hard burn bought the
    crossing in 87 days against economy's 234 and very nearly free.
    """
    return max(0.0, float(ship.heat) - float(getattr(stats, "heat_cap", 0.0)))


def repair_tick(ship: Ship, days: float, s: Stats) -> float:
    """Between-turn healing: seal first, then rebuild, innermost layer first."""
    if s.regen <= 0:
        return 0.0
    # Nothing regrows while it is cooking. Not a balance knob but the same
    # fact `cool` is already acting on, read through the one door.
    if excess_heat(ship, s) > 0:
        return 0.0
    # **A grown hull cannot rebuild itself out of nothing, and it did.**
    # The feedstack was computed and then thrown at whatever happened to be
    # aboard: `fed = min(cargo, budget * 0.004)` took what it could get and
    # healed the full amount regardless. Measured, a hull at 60% went to 100%
    # — 136 points — on 0.54 t of biomass, and healed exactly the same with
    # 20 t aboard as with 500, or with none at all. A cost that is calculated
    # and does not constrain is not a cost.
    # **And the answer must not depend on how the caller chopped the time.**
    # It did. The old loop worked a layer, and `break` only fired when that
    # layer was left *unfilled* — so a call standing for thirty days filled
    # the innermost layer and walked on to the next one still carrying all
    # thirty, while thirty calls of one day filled nothing and stopped each
    # time. Measured on a hull at 50% with feedstock to spare, the same thirty
    # days: **1.0000 hull in one call against 0.8384 in thirty.** That is
    # #116's claim in the one place it was not fixed, and note the direction —
    # the honest clock made repair *slower*, not faster.
    #
    # Days are the resource now, spent innermost-first. A layer takes the days
    # its own rate needs; whatever is left goes to the next one out. Thirty
    # days at once is thirty days one at a time, exactly, because spending is
    # additive. The cadence the docstring promises is unchanged: nothing outer
    # is touched while something inner is still open.
    budget = 0.0
    held = float(ship.cargo.get("biomass", 0.0))
    left = float(days)
    for L in reversed(ship.layers):
        if L.hp >= L.max:
            continue
        rate = L.max * L.regen * s.regen           # hit points a day, this layer
        if rate <= 0:
            break
        # No `if left <= 0: break` here, though the first draft had one and a
        # mutation proved it dead: once the days are gone `rate * left` is
        # zero, so `want` is zero and the `heal <= 0` below already stops the
        # loop. A branch that cannot change the answer is the same defect as a
        # field that is declared and never read.
        want = min(L.max - L.hp, rate * left)
        heal = min(want, held / FEED_PER_HP) if FEED_PER_HP > 0 else want
        if heal <= 0:
            break
        L.hp += heal
        budget += heal
        held -= heal * FEED_PER_HP
        left -= heal / rate                        # the days that work took
    if budget > 0:
        add_cargo(ship, "biomass", -(budget * FEED_PER_HP))
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




#: Share of a hull's combat vent rate that the radiators shed per day at rest.
#:
#: A combat turn is minutes and a day is a day, so this is not a physical
#: ratio — it is the rate that makes heat a state you fly in rather than one
#: that has gone by the time you arrive. At 0.5 a hard burn cleared in four
#: days and never stacked with the next one; at 0.14 it takes a fortnight, so
#: a captain who keeps burning hard keeps flying hot.
#:
#: Heat used to be a one-way ratchet outside combat: nothing added it but a
#: flight incident and nothing shed it, so a ship sat at thirty for twelve
#: hundred days with a vent rated at twenty-four a turn.
REST_VENT = 0.14


#: Damage a day per point of heat over the cap. The radiators complaining,
#: which is what the hard burn's blurb promised and nothing delivered.
COOK = 0.05


#: How far past its rated cap a hull's heat can climb, as a multiple.
#:
#: Every penalty for running hot scales with how far over the cap you are, so
#: an unbounded number makes them all compound. In combat that routed a
#: warship on turn five at 93% hull. Through the helm it was worse and quieter:
#: a hard burn adds heat on arrival, nothing but `cool()` takes it away at
#: 0.84 a day, so bouncing between two bodies drove a hull to 5.4x its cap —
#: and a captain who then met somebody routed on turn three, at 51% hull,
#: while holding fire. They lost to their own radiators, in a fight they never
#: shot in.
HEAT_CEILING = 2.0


def cook(ship: Ship, cap: float) -> float:
    """Hold a hull's heat at or below what it can physically hold.

    Called wherever heat is *added* — `combat._fire` and `flight.travel_to`
    are the only two places in the game that do — so the ceiling holds without
    anything having to remember to check it later.
    """
    ship.heat = max(0.0, min(ship.heat, cap * HEAT_CEILING))
    return ship.heat


def add_heat(ship: Ship, amount: float, cap: float) -> float:
    """Put heat into a hull and hold it under the ceiling.

    The one way to add heat, because `cook()` on its own asks every caller to
    remember, and four of the six did not. `INTERFACE.md` said there were two
    such places; there were six — a crossing watch, a flight incident, an
    action's own effects and taking a hit in combat all put heat in without
    ever consulting the ceiling. An incident alone took a hull sitting at the
    ceiling to 2.36x its cap, which is the compounding this was supposed to
    have ended.
    """
    # No floor here: `cook` floors at nothing and clamps at the ceiling, and
    # one guard in one place is the whole point of routing through it.
    ship.heat = ship.heat + amount
    return cook(ship, cap)


def cool(ship: Ship, stats, days: float) -> dict:
    """Shed heat on the clock, and cook the hull while it is over the cap."""
    out = {"shed": 0.0, "cooked": 0.0}
    if days <= 0 or ship.heat <= 0:
        return out
    over = excess_heat(ship, stats)
    if over > 0:
        # Only the excess cooks, and only for as long as it is excess.
        out["cooked"] = min(over, over * COOK * days)
        apply_damage(ship, out["cooked"])
    shed = min(ship.heat, stats.vent * REST_VENT * days)
    ship.heat -= shed
    out["shed"] = shed
    return out
