"""Who you meet out there, and what happens when nothing meets you."""

from __future__ import annotations

from ..data.chassis import CHASSIS_BY_ID, accepts_family
from ..data.lore import HULL_NAMES
from ..data.factions import FACTIONS_BY_ID, is_hostile
from ..data.parts import parts_available
from ..data.tech import TECH
from .ship import add_cargo, build_layers, make_ship, stats

PERSONALITY = {
    "charter": "cautious", "concordat": "balanced", "freeholds": "balanced",
    "sanhedrin": "cautious", "bloom": "feral",
}

#: Rounds an NPC hull carries for each mount that needs feeding.
#:
#: It used to be given a flat 4–20 tonnes of ore, alloy and biomass — stores
#: meant for salvage, doing double duty as ammunition nobody had sized.
#: Measured over forty engagements: a mean of 12 rounds against a 31-turn
#: fight. NPCs ran dry in 35 of 40, on turn 11, and spent **63% of every
#: engagement unarmed** — which is why the player took no damage at all in 13
#: of 20 fights.
#:
#: Sized against what a fight actually eats rather than by taste. Over fifty
#: long engagements against a hull built to soak them, an NPC spends a median
#: 58% of its magazine and at worst 85%: enough to fight the whole engagement,
#: low by the end of a hard one, and dry only if it goes very long. Running
#: out is a real thing that happens to a ship in a long fight; being unarmed
#: for two-thirds of every fight is not.
ROUNDS_MIN = 22
ROUNDS_MAX = 38

#: How much nerve an opponent brings, by difficulty: `BASE + PER_SCALE × d`.
#:
#: Re-pitched when the enemy learned to fly and shoot in the same turn
#: (`sim/enemy_ai`). A competent opponent is worth about a difficulty step,
#: and at 60 + 14·d it made a *light patrol* — a scale-half contact, the
#: thing a new captain meets first — beat an armed hull three times in ten
#: (measured, 150 fights: 71% player wins against the 80% this game is
#: pitched at). Nerve is the honest lever, because the difference between a
#: patrol and a warship is mostly whether it will see the fight through.
#: Measured over 120 fights a scale: **0.5 → 82%, 2.5 → 33%, 4.0 → 15%**,
#: against 71/33/15 before — the patrol breaks off and the warship does not.
RESOLVE_BASE = 26.0
RESOLVE_PER_SCALE = 27.0

#: Damage at or above which a mount is a main gun rather than a specialist.
#: Below it sit the flash organ (3), the grapple (5), the point-defence cannon
#: (8) and the boarding pod (9); above it every gun in the game, against a
#: median mount damage of 30.
#:
#: `_weapon_pool` used to raise the tier until *some* weapon existed, and for
#: a fabricated hull the first to appear is the flak gun — so **40% of NPC
#: hulls arrived armed with nothing but point-defence**, Concordat warships at
#: difficulty two included. `test_balance` asked whether they were armed and
#: they were; nothing asked whether they were armed with anything that could
#: hurt you. Specialists are still fitted, alongside a battery, which is what
#: they are for.
MAIN_GUN_DAMAGE = 12


def _tier_for(rng, difficulty: float) -> int:
    """A fractional difficulty picks between the tiers either side of it.

    `round(difficulty)` is a step: everything from 1.5 to 2.4 drew the same
    parts, so win rates sat flat across a whole band and then fell off a cliff
    at the boundary. Rolling the fraction spreads the change out.
    """
    low = int(max(0, min(4, difficulty)))
    frac = max(0.0, min(1.0, difficulty - low))
    return min(4, low + (1 if rng.chance(frac) else 0))


def _main_guns(pool: list) -> list:
    """The mounts in a pool that can actually decide an engagement."""
    return [p for p in pool if p.wpn and p.wpn.dmg >= MAIN_GUN_DAMAGE]


def _rack(pool: list, difficulty: float) -> list:
    """The main guns a hull of this weight would actually be carrying.

    A fabricated hull cannot mount a main gun below tier three, and tier three
    holds the railgun, the mass driver and the breach torpedo — so simply
    handing it the pool at the reach where a gun first appears armed a light
    patrol like a battleship. Requiring a main gun turned the old cliff
    (flak, flak, flak, then 85 points of throw at scale three) into a curve;
    this is what gives the curve a bottom as well as a top.
    """
    guns = sorted(_main_guns(pool), key=lambda p: p.wpn.dmg)
    if not guns:
        return []
    reach = max(1, round(len(guns) * min(1.0, 0.2 + difficulty * 0.25)))
    return guns[:reach]


def _weapon_pool(chassis, tier: int) -> list:
    """Weapons this hull can mount, raising the tier until a main gun exists.

    Every low-tier weapon in the game is grown-family, so a fabricated hull at
    tier one has nothing whatever it can bolt on — which is why Concordat
    warships used to arrive completely unarmed and lose every fight without
    firing. A warship is armed; if its tech level says otherwise, the tech
    level is what gives.

    Raising it until *some* weapon existed was not enough: the first mount a
    fabricated hull can reach is the point-defence cannon, so warships came
    out carrying nothing but flak. The bar is a main gun, not a gun.
    """
    for reach in range(tier, 5):
        unlocked = [t.id for t in TECH if t.tier <= reach]
        pool = parts_available("weapon", chassis, unlocked)
        if _main_guns(pool):
            return pool
    return parts_available("weapon", chassis, [t.id for t in TECH])


def _outfit(rng, chassis, tier: int, difficulty: float = 1.0) -> list[str]:
    """Fit a plausible loadout for an NPC of a given faction and weight."""
    unlocked = [t.id for t in TECH if t.tier <= tier]
    fitted: list[str] = []
    for slot, n in chassis.slots.items():
        if slot == "weapon":
            continue
        pool = [p for p in parts_available(slot, chassis, unlocked)
                if not p.civilian]
        if not pool:
            continue
        want = max(0, n - (1 if rng.chance(0.4) else 0))
        for _ in range(want):
            fitted.append(rng.pick(pool).id)

    # Armament last and separately, so it is never the thing that goes missing.
    mounts = chassis.slots.get("weapon", 0)
    if mounts:
        pool = _weapon_pool(chassis, tier)
        if pool:
            # A light encounter carries one gun; a heavy one fills the rack.
            want = max(1, min(mounts, round(mounts * min(1.0, 0.35 + difficulty * 0.22))))
            # The first mount is a main gun. The rest may be anything the hull
            # can carry, so point-defence and grapples still turn up — beside
            # a battery, which is where they belong.
            # The first mount is a main gun this hull's weight would carry.
            # The rest may be anything at or below it, so point-defence and
            # grapples still turn up — beside a battery, where they belong.
            battery = _rack(pool, difficulty)
            heavy = {p.id for p in _main_guns(pool)} - {p.id for p in battery}
            allowed = [p for p in pool if p.id not in heavy] or pool
            fitted.append(rng.pick(battery or pool).id)
            for _ in range(want - 1):
                fitted.append(rng.pick(allowed).id)
    return fitted


def _pick_hull(rng, pool, difficulty: float):
    """Choose a hull whose silhouette matches the threat.

    Picking uniformly meant a scale-four patrol could arrive in a scout and a
    scale-half one in a battleship, which made difficulty very nearly
    meaningless next to the lottery.
    """
    if len(pool) <= 1:
        return pool[0]
    ranked = sorted(pool, key=lambda c: c.hull)
    # 0 at the bottom of the range, 1 at the top.
    want = min(1.0, max(0.0, (difficulty - 0.5) / 3.5))
    weights = []
    for index, chassis in enumerate(ranked):
        place = index / (len(ranked) - 1)
        weights.append((1.0 / (0.12 + abs(place - want)), chassis))
    return rng.weighted(weights)


#: How hard a hull the sector sends, as a range rather than a number. Both
#: figures were inline literals in `roll_encounter` — `1 + rng.float(0, 2)` —
#: written twice, and nothing else could ask what a typical opponent is.
#: `sim/readiness.py` quotes its report at the middle of this, so a readiness
#: board and an actual encounter describe the same sector.
THREAT_FLOOR = 1.0
THREAT_SPREAD = 2.0


def typical_threat() -> float:
    """The middle of what `roll_encounter` draws — the median opponent."""
    return THREAT_FLOOR + THREAT_SPREAD / 2.0


def make_enemy(rng, faction_id: str, difficulty: float = 1.0) -> dict:
    fac = FACTIONS_BY_ID.get(faction_id)
    tier = _tier_for(rng, difficulty)
    pool = [CHASSIS_BY_ID[c] for c in (fac.ships if fac and fac.ships else ("pike",))
            if c in CHASSIS_BY_ID]
    chassis = _pick_hull(rng, pool, difficulty)
    ship = make_ship(chassis.id, _outfit(rng, chassis, tier, difficulty))
    ship.name = rng.pick(HULL_NAMES.get(faction_id, HULL_NAMES["freeholds"]))
    ship.crew = chassis.crew

    # Difficulty scales the hull rather than the fittings, so the silhouette is honest.
    bonus = {"hull": 0.1 * difficulty}
    build_layers(ship, bonus)
    st = stats(ship, bonus)

    # Salvage worth taking off the wreck, and separately a magazine sized to
    # what this hull's own mounts actually eat.
    for cid in ("ore", "alloy", "biomass"):
        add_cargo(ship, cid, rng.int(4, 20))
    for mount in st.weapons:
        if not mount.wpn.ammo:
            continue
        cid, per = mount.wpn.ammo
        add_cargo(ship, cid, per * rng.int(ROUNDS_MIN, ROUNDS_MAX))

    return {
        "ship": ship,
        "stats": st,
        "name": f"{fac.short if fac else 'Unaligned'} {chassis.name} «{ship.name}»",
        "faction": faction_id,
        "personality": PERSONALITY.get(faction_id, "balanced"),
        "resolve": RESOLVE_BASE + difficulty * RESOLVE_PER_SCALE,
        "loot": {
            "credits": round(rng.int(400, 2200) * (1 + difficulty * 0.6)),
            "research": round(rng.int(4, 22) * (1 + difficulty * 0.4)),
        },
    }


#: How much of the chance of being jumped is simply how badly kept the system
#: is. The rest is what is actually on the chart — see `roll_encounter`.
#:
#: Calibrated to leave a well-kept system about where it was: the old term was
#: 0.04 with a port and 0.14 without, and lawlessness runs 0 to 1 with a
#: quarter of systems under 0.03, so 0.20 puts a policed capital under 0.01
#: and the far edge above 0.13 before anything on the chart is counted.
LAW_WORTH = 0.20


def roll_encounter(game, system, rng):
    """Does anything happen when you arrive? Returns an encounter dict or None.

    Weighted by who is *actually in the system*. Traffic gave other hulls a
    position, and a chart showing an unmarked hull loitering at the outer
    bodies should mean something — otherwise it is decoration, and the patrol
    that jumps you arrives with no warning it could possibly have given.
    """
    from . import traffic as traffic_sim

    from . import piracy as piracy_sim

    dark = traffic_sim.hostiles(game, system)
    # The same law `sim/traffic` asks about before it puts an unmarked hull
    # here at all. This used to be its own arithmetic over the same field —
    # `0.04 if system.port else 0.14` — so the two could disagree about the
    # same volume and nothing would notice.
    danger = (piracy_sim.lawlessness(game, system) * LAW_WORTH
              + 0.09 * len(dark))
    if not rng.chance(min(0.7, danger)):
        return None

    if system.bloom > 0.25 and rng.chance(system.bloom):
        return {
            "enemy": make_enemy(rng, "bloom", 1 + system.bloom * 3),
            "no_parley": True,
            "intro": "Something the size of a freighter uncoils off the rock and "
                     "starts toward you. It has no transponder, no markings and "
                     "no discernible bow.",
        }

    # Something running dark on the chart is the likeliest thing to meet you.
    if dark and rng.chance(0.55):
        hull = dark[0]
        enemy = make_enemy(rng, "freeholds",
                           THREAT_FLOOR + rng.float(0, THREAT_SPREAD))
        enemy["ship"].name = hull.name
        return {
            "enemy": enemy, "no_parley": False, "hull_id": hull.id,
            "intro": f"The unmarked hull you plotted at "
                     f"{system.bodies[hull.from_body].name} closes without "
                     "answering. No colours, no transponder, no hail.",
        }

    candidates = [f for f in ("freeholds", "concordat", "sanhedrin", "charter")
                  if is_hostile(f, game.rep.get(f, 0)) or rng.chance(0.10)]
    if not candidates:
        return None
    # A power with a hull actually here is likelier to be the one that stops
    # you than one whose nearest ship is three jumps away.
    present = set(traffic_sim.present_factions(game, system))
    weighted = [(3 if f in present else 1, f) for f in candidates]
    fid = rng.weighted(weighted)
    theirs = next((h for h in traffic_sim.in_system(game, system)
                   if h.faction == fid and not h.hostile), None)
    enemy = make_enemy(rng, fid, THREAT_FLOOR + rng.float(0, THREAT_SPREAD))
    if theirs is not None:
        enemy["ship"].name = theirs.name
        intro = (f"The {FACTIONS_BY_ID[fid].short} hull you had plotted — "
                 f"{theirs.name} — turns onto you and does not answer the "
                 "hail.")
    else:
        intro = (f"A {FACTIONS_BY_ID[fid].short} hull lights you up and does "
                 "not answer the hail.")
    return {"enemy": enemy, "no_parley": False,
            "hull_id": theirs.id if theirs else None, "intro": intro}


# ── flavour events ─────────────────────────────────────────────────────────
# (weight, text, effect builder)

def _ev(rng, **kw):
    return kw


EVENTS = [
    (3, "A dead Yards lifeboat tumbles past, hatch open, nobody aboard.",
     lambda r: _ev(r, credits=r.int(200, 900),
                   note="Salvaged: one lifeboat transponder.")),
    (3, "The star throws a particle event. Twenty grams per square centimetre "
        "would stop it; you have rather more than that.",
     lambda r: _ev(r, heat=r.int(6, 18),
                   note="Rind absorbs the dose. Crew stays inboard for a day.")),
    (3, "A sub-millimetre grain at fourteen kilometres a second flashes to "
        "plasma on the bumper.",
     lambda r: _ev(r, damage=r.int(6, 26),
                   note="Epidermis cratered. It is already regrowing.")),
    (2, "A cold hull, Charter markings, drifting with its docking sphincters "
        "iris-locked from inside.",
     lambda r: _ev(r, research=r.int(15, 45), cargo={"silicon": r.int(1, 4)},
                   note="You take the core and leave the rest.")),
    (3, "A Freehold skiff hails, offering a hold of volatiles at a price that is "
        "either generous or a mistake.",
     lambda r: _ev(r, cargo={"volatiles": r.int(8, 26)}, credits=-r.int(300, 900),
                   note="You take the deal.")),
    (2, "The hull sensors report germinating spores in a seam of the epidermis. "
        "Not yours.",
     lambda r: _ev(r, damage=r.int(10, 40),
                   note="Burned out with a surface flush. Watch that seam.")),
    (2, "A repeating pattern on the magnetometer, prime-numbered, from nowhere "
        "in the catalogue.",
     lambda r: _ev(r, research=r.int(25, 70),
                   note="Logged. Nobody on the bridge is quite comfortable.")),
    (2, "Two of the crew present with something the physician cannot name.",
     lambda r: _ev(r, morale=-0.08,
                   note="Quarantined in a polyp pod. They will likely recover.")),
    (2, "A rock ahead has been eaten hollow and left. The tissue in it is still, "
        "faintly, metabolising.",
     lambda r: _ev(r, research=r.int(20, 50),
                   note="Sampled. The lineage markers are Charter-canonical.")),
    (3, "Clean transit. The intima is running a little ahead of the oxygen budget.",
     lambda r: _ev(r, morale=0.05, note="The crew notices. It helps.")),
]


def roll_event(rng):
    """A transit vignette, or None."""
    if not rng.chance(0.34):
        return None
    weight, text, build = rng.weighted([(w, (w, t, b)) for w, t, b in EVENTS])
    return {"text": text, "effect": build(rng)}
