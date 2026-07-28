"""Who you meet out there, and what happens when nothing meets you."""

from __future__ import annotations

from ..data.chassis import CHASSIS_BY_ID, accepts_family
from ..data.factions import FACTIONS_BY_ID, is_hostile
from ..data.parts import parts_available
from ..data.tech import TECH
from .ship import add_cargo, build_layers, make_ship, stats

HULL_NAMES = {
    "charter": ["Patient Ledger", "Quiet Increment", "Second Signature",
                "Long Consent", "Held Breath"],
    "concordat": ["Rolled Plate", "Hard Union", "Tolerance Stack",
                  "Nine Millimetres", "Certified"],
    "freeholds": ["Margin Call", "Nobody's Business", "Cut and Run",
                  "Posted Price", "Third Owner"],
    "sanhedrin": ["Enumerating", "Cold Inference", "Substrate Question", "Nine Ninths"],
    "bloom": ["Unlicensed Mass", "Ninth Instar", "Uncounted", "Still Growing",
              "No Second Clause"],
}

PERSONALITY = {
    "charter": "cautious", "concordat": "balanced", "freeholds": "balanced",
    "sanhedrin": "cautious", "bloom": "feral",
}


def _tier_for(rng, difficulty: float) -> int:
    """A fractional difficulty picks between the tiers either side of it.

    `round(difficulty)` is a step: everything from 1.5 to 2.4 drew the same
    parts, so win rates sat flat across a whole band and then fell off a cliff
    at the boundary. Rolling the fraction spreads the change out.
    """
    low = int(max(0, min(4, difficulty)))
    frac = max(0.0, min(1.0, difficulty - low))
    return min(4, low + (1 if rng.chance(frac) else 0))


def _weapon_pool(chassis, tier: int) -> list:
    """Weapons this hull can actually mount, raising the tier until some exist.

    Every low-tier weapon in the game is grown-family, so a fabricated hull at
    tier one has nothing whatever it can bolt on — which is why Concordat
    warships used to arrive completely unarmed and lose every fight without
    firing. A warship is armed; if its tech level says otherwise, the tech
    level is what gives.
    """
    for reach in range(tier, 5):
        unlocked = [t.id for t in TECH if t.tier <= reach]
        pool = parts_available("weapon", chassis, unlocked)
        if pool:
            return pool
    return parts_available("weapon", chassis, [t.id for t in TECH])


def _outfit(rng, chassis, tier: int, difficulty: float = 1.0) -> list[str]:
    """Fit a plausible loadout for an NPC of a given faction and weight."""
    unlocked = [t.id for t in TECH if t.tier <= tier]
    fitted: list[str] = []
    for slot, n in chassis.slots.items():
        if slot == "weapon":
            continue
        pool = parts_available(slot, chassis, unlocked)
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
            for _ in range(want):
                fitted.append(rng.pick(pool).id)
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

    for cid in ("ore", "alloy", "biomass"):
        add_cargo(ship, cid, rng.int(4, 20))

    return {
        "ship": ship,
        "stats": st,
        "name": f"{fac.short if fac else 'Unaligned'} {chassis.name} «{ship.name}»",
        "faction": faction_id,
        "personality": PERSONALITY.get(faction_id, "balanced"),
        "resolve": 60 + difficulty * 14,
        "loot": {
            "credits": round(rng.int(400, 2200) * (1 + difficulty * 0.6)),
            "research": round(rng.int(4, 22) * (1 + difficulty * 0.4)),
        },
    }


def roll_encounter(game, system, rng):
    """Does anything happen when you arrive? Returns an encounter dict or None."""
    danger = system.bloom * 0.9 + (0.04 if system.port else 0.14)
    if not rng.chance(min(0.62, danger)):
        return None

    if system.bloom > 0.25 and rng.chance(system.bloom):
        return {
            "enemy": make_enemy(rng, "bloom", 1 + system.bloom * 3),
            "no_parley": True,
            "intro": "Something the size of a freighter uncoils off the rock and "
                     "starts toward you. It has no transponder, no markings and "
                     "no discernible bow.",
        }

    candidates = [f for f in ("freeholds", "concordat", "sanhedrin", "charter")
                  if is_hostile(f, game.rep.get(f, 0)) or rng.chance(0.10)]
    if not candidates:
        return None
    fid = rng.pick(candidates)
    return {
        "enemy": make_enemy(rng, fid, 1 + rng.float(0, 2)),
        "no_parley": False,
        "intro": f"A {FACTIONS_BY_ID[fid].short} hull lights you up and does not "
                 "answer the hail.",
    }


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
