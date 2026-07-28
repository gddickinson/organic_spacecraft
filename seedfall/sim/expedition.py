"""Ground expeditions — the game you play standing on a world.

A lander puts a party down on a generated map of a landing zone. They see one
step at a time, spend supplies to move, and choose how to handle what they find.
Officers' skills decide the odds; the rover and the party's health decide how
long they can keep going. Everything found is only banked when they get back to
the lander, which is the whole tension of it.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.save import register
from . import weather as weather_sim
from ..data.expedition import (BASE_SUPPLY, FEATURES, HAZARDS, LORE,
                               PARTY_CAPACITY, REWARD_SCALE, TERRAIN)

_uid = itertools.count(1)

W, H = 7, 7          # landing-zone grid
LANDER = (3, 6)      # where the party sets down


@register
@dataclass
class Tile:
    x: int
    y: int
    terrain: str
    feature: str | None = None
    seen: bool = False
    visited: bool = False
    resolved: bool = False       # its feature has been dealt with


@register
@dataclass
class Expedition:
    id: int
    system_id: int
    body_id: str
    body_name: str
    tiles: list[Tile]
    x: int = LANDER[0]
    y: int = LANDER[1]
    supply: int = BASE_SUPPLY
    rover: int = 10
    days: int = 0
    officers: list[int] = field(default_factory=list)
    haul: dict[str, float] = field(default_factory=dict)
    study: dict[str, float] = field(default_factory=dict)
    lore: list[str] = field(default_factory=list)
    log: list = field(default_factory=list)
    injured: list[int] = field(default_factory=list)
    over: bool = False
    outcome: str = ""
    weather: str = "clear"
    weather_until: int = 0
    biome: str = ""

    def tile(self, x: int, y: int) -> Tile | None:
        if 0 <= x < W and 0 <= y < H:
            return self.tiles[y * W + x]
        return None

    @property
    def here(self) -> Tile:
        return self.tile(self.x, self.y)

    @property
    def at_lander(self) -> bool:
        return (self.x, self.y) == LANDER

    @property
    def carried(self) -> float:
        return sum(self.haul.values())


# ── generation ─────────────────────────────────────────────────────────────

_TERRAIN_BY_BIOME = {
    "barren": ("plain", "ridge", "scarp", "dunes"),
    "regolith": ("plain", "ridge", "dunes", "basin"),
    "cryo": ("shelf", "crevasse", "plain", "ridge"),
    "subsurface": ("shelf", "crevasse", "vent", "basin"),
    "microbial": ("basin", "plain", "vent", "forest"),
    "verdant": ("forest", "basin", "ridge", "plain"),
    "sulfuric": ("vent", "scarp", "plain", "crevasse"),
    "aerial": ("basin", "dunes", "plain", "ridge"),
}

_FEATURE_BY_BIOME = {
    "barren": ("seam", "wreck", "cache", "ruin"),
    "regolith": ("seam", "ruin", "cache", "wreck"),
    "cryo": ("shaft", "wreck", "cache", "monolith"),
    "subsurface": ("vent_field", "shaft", "monolith", "nest"),
    "microbial": ("nest", "vent_field", "garden", "seam"),
    "verdant": ("garden", "nest", "ruin", "monolith"),
    "sulfuric": ("vent_field", "seam", "wreck", "bloomscar"),
    "aerial": ("nest", "monolith", "wreck", "garden"),
}


def generate(rng, system, body, officers: list[int],
             supply: int = BASE_SUPPLY) -> Expedition:
    """Lay out a landing zone. Denser features further from the lander."""
    kinds = _TERRAIN_BY_BIOME.get(body.biome, ("plain", "ridge", "scarp"))
    feats = list(_FEATURE_BY_BIOME.get(body.biome, ("seam", "wreck", "ruin")))
    if body.relic and body.relic_found:
        feats = ["ruin", "monolith"] + feats
    if body.anomaly and body.anomaly.found:
        feats = ["wreck", "cache"] + feats

    tiles: list[Tile] = []
    for y in range(H):
        for x in range(W):
            t = Tile(x, y, rng.pick(kinds))
            # Nothing interesting on the pad itself.
            if (x, y) != LANDER:
                dist = abs(x - LANDER[0]) + abs(y - LANDER[1])
                if rng.chance(min(0.55, 0.10 + dist * 0.07)):
                    t.feature = rng.pick(feats)
            tiles.append(t)

    exp = Expedition(id=next(_uid), system_id=system.id, body_id=body.id,
                     body_name=body.name, tiles=tiles,
                     officers=list(officers), supply=supply,
                     biome=body.biome or "")
    weather_sim.roll(exp, rng, exp.biome)
    exp.tile(*LANDER).seen = True
    exp.tile(*LANDER).visited = True
    _reveal(exp)
    say(exp, f"The lander is down on {body.name}. "
             f"{exp.supply} days of supply aboard.", "good")
    return exp


def _reveal(exp: Expedition) -> None:
    """Mark what the party can see. A whiteout sees nothing but its own tile."""
    reach = weather_sim.sight(exp)
    here = exp.tile(exp.x, exp.y)
    if here:
        here.seen = True
    if reach <= 0:
        return
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            if abs(dx) + abs(dy) > reach:
                continue
            t = exp.tile(exp.x + dx, exp.y + dy)
            if t:
                t.seen = True


def say(exp: Expedition, text: str, kind: str = "") -> None:
    exp.log.append((exp.days, text, kind))
    if len(exp.log) > 120:
        exp.log.pop(0)


# ── movement ───────────────────────────────────────────────────────────────

def move(exp: Expedition, dx: int, dy: int, officers, rng) -> dict:
    """Step one tile. Costs supply, may spring a hazard."""
    dest = exp.tile(exp.x + dx, exp.y + dy)
    if dest is None or exp.over:
        return {"ok": False, "why": "There is nothing that way."}

    if weather_sim.pinned(exp):
        return {"ok": False,
                "why": f"{weather_sim.current(exp).name}: nothing moves in "
                       "this. Sit it out or lose people."}

    terrain = TERRAIN[dest.terrain]
    # Ground you have already crossed is cheap: the route is known and the
    # rover has a track to follow. Otherwise coming home is a death sentence.
    base = 1 if dest.visited else max(1, terrain.cost - (1 if exp.rover >= 8 else 0))
    cost = weather_sim.move_cost(exp, base)
    exp.x, exp.y = dest.x, dest.y
    exp.days += cost
    exp.supply -= cost
    dest.visited = True

    changed = weather_sim.tick(exp, cost, rng, exp.biome)
    _reveal(exp)
    say(exp, f"Crossed into {terrain.name}. {cost} day(s) of supply gone.")
    if changed:
        say(exp, f"{weather_sim.current(exp).name}. "
                 f"{weather_sim.current(exp).blurb}",
            "warn" if weather_sim.current(exp).danger > 1.2 else "")

    out = {"ok": True, "hazard": None, "weather": changed}
    if rng.chance(weather_sim.danger(exp, terrain.danger)):
        out["hazard"] = _spring_hazard(exp, officers, rng)
    _check_end(exp)
    return out


def _spring_hazard(exp: Expedition, officers, rng) -> dict:
    hz = rng.pick(HAZARDS)
    skill = max((o.level for o in officers if o.stat == hz.stat), default=0)
    beaten = rng.chance(min(0.85, 0.25 + skill * 0.14))
    if beaten:
        say(exp, f"{hz.name}: {hz.blurb} Handled.", "good")
        return {"hazard": hz, "beaten": True}

    exp.supply -= hz.supply
    exp.rover = max(0, exp.rover - hz.rover)
    hurt = None
    if hz.injury and rng.chance(hz.injury) and officers:
        victim = rng.pick([o for o in officers if o.id not in exp.injured] or officers)
        if victim.id not in exp.injured:
            exp.injured.append(victim.id)
            hurt = victim
    say(exp, f"{hz.name}: {hz.blurb}"
             + (f" {hurt.name} is hurt." if hurt else ""), "bad")
    return {"hazard": hz, "beaten": False, "injured": hurt}


# ── working a feature ──────────────────────────────────────────────────────

def options_here(exp: Expedition):
    t = exp.here
    if t.feature is None or t.resolved:
        return []
    return FEATURES[t.feature].options


def attempt(exp: Expedition, index: int, officers, rng) -> dict:
    """Try one of the options a feature offers."""
    t = exp.here
    opts = options_here(exp)
    if exp.over or not opts or index >= len(opts):
        return {"ok": False, "why": "Nothing here to attempt."}

    label, stat, difficulty, reward = opts[index]
    t.resolved = True
    exp.days += 1
    exp.supply -= 1

    if not stat:                       # walking away is always allowed
        say(exp, f"{label}. Nothing gained and nothing risked.", "dim")
        _check_end(exp)
        return {"ok": True, "label": label, "success": True, "reward": None}

    skill = max((o.level for o in officers if o.stat == stat), default=0)
    roll = rng.int(1, 6) + skill
    success = roll >= difficulty + 2
    margin = roll - (difficulty + 2)

    out = {"ok": True, "label": label, "success": success, "reward": None,
           "amount": 0, "lore": None}
    if success:
        lo, hi = REWARD_SCALE.get(reward, (0, 0))
        amount = rng.int(lo, hi) * (1 + max(0, margin) * 0.12) if hi else 0
        if reward == "lore":
            line = rng.pick([l for l in LORE if l not in exp.lore] or LORE)
            exp.lore.append(line)
            out["lore"] = line
            say(exp, f"{label}: {line}", "good")
        elif reward == "study":
            exp.study["__any__"] = exp.study.get("__any__", 0) + amount
            out["reward"], out["amount"] = reward, amount
            say(exp, f"{label}: {round(amount)} points of alien understanding.", "good")
        elif reward != "none":
            exp.haul[reward] = exp.haul.get(reward, 0) + amount
            out["reward"], out["amount"] = reward, amount
            say(exp, f"{label}: {round(amount)} {reward} secured.", "good")
        else:
            say(exp, f"{label}. Done.", "dim")
    else:
        say(exp, f"{label} — it does not go well.", "bad")
        if rng.chance(0.4):
            haz = _spring_hazard(exp, officers, rng)
            out["hazard"] = haz
    _check_end(exp)
    return out


def shelter(exp: Expedition, rng) -> dict:
    """Sit out the weather. A day of supply, and the front breaks sooner.

    Always available, because a party pinned by a gale with nothing it may do
    is a party that can neither move nor die — the expedition simply stops.
    """
    if exp.over:
        return {"ok": False, "why": "The expedition is over."}
    res = weather_sim.shelter(exp, rng)
    weather = res["weather"]
    say(exp, f"Sat out the {weather.name.lower()}. A day gone.", "")
    changed = weather_sim.tick(exp, 1, rng, exp.biome)
    if changed:
        say(exp, f"{weather_sim.current(exp).name}. "
                 f"{weather_sim.current(exp).blurb}", "")
    _check_end(exp)
    return {"ok": True, "weather": weather, "changed": changed}


def rest(exp: Expedition, officers, rng) -> dict:
    """Spend a day patching the rover and the party."""
    if exp.over:
        return {"ok": False, "why": "The expedition is over."}
    exp.days += 1
    exp.supply -= 1
    weather_sim.tick(exp, 1, rng, exp.biome)
    eng = max((o.level for o in officers if o.stat == "engineering"), default=0)
    med = max((o.level for o in officers if o.stat == "medicine"), default=0)
    exp.rover = min(10, exp.rover + 1 + eng // 2)
    healed = None
    if exp.injured and rng.chance(0.3 + med * 0.15):
        healed = exp.injured.pop(0)
    say(exp, "A day spent on repairs and rest." +
        (" Someone is back on their feet." if healed else ""), "good")
    _check_end(exp)
    return {"ok": True, "healed": healed}


# ── ending ─────────────────────────────────────────────────────────────────

def _check_end(exp: Expedition) -> None:
    if exp.over:
        return
    if exp.supply <= 0:
        if exp.at_lander:
            finish(exp, "recalled")
        else:
            finish(exp, "stranded")


def finish(exp: Expedition, outcome: str) -> None:
    exp.over = True
    exp.outcome = outcome
    lines = {
        "returned": "The party is back aboard with everything they carried.",
        "recalled": "Supplies ran out at the pad. They lift with what they have.",
        "stranded": "Supplies ran out in the field. The lander comes for them; "
                    "everything not on their backs stays where it fell.",
        "aborted": "Recalled early. The lander lifts.",
    }
    say(exp, lines.get(outcome, outcome), "bad" if outcome == "stranded" else "good")


def can_lift(exp: Expedition) -> bool:
    return exp.at_lander and not exp.over


def lift_off(exp: Expedition) -> None:
    finish(exp, "returned")


def haul_kept(exp: Expedition) -> dict[str, float]:
    """What actually comes home. Stranding costs most of it."""
    if exp.outcome == "stranded":
        return {k: v * 0.4 for k, v in exp.haul.items()}
    over = max(0.0, exp.carried - PARTY_CAPACITY)
    if over <= 0:
        return dict(exp.haul)
    scale = PARTY_CAPACITY / exp.carried
    return {k: v * scale for k, v in exp.haul.items()}


def study_kept(exp: Expedition) -> float:
    total = sum(exp.study.values())
    return total * (0.5 if exp.outcome == "stranded" else 1.0)
