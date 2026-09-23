"""Ground expeditions — the game you play standing on a world.

A lander puts a party down on a generated map of a landing zone. They see one
step at a time, spend supplies to move, and choose how to handle what they find.
Officers' skills decide the odds; the rover and the party's health decide how
long they can keep going. Everything found is only banked when they get back to
the lander, which is the whole tension of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from . import weather as weather_sim
from ..data.expedition import (BASE_SUPPLY, FEATURES, HAZARDS,
                               HAZARD_ON_FAILURE, MARGIN_BONUS,
                               NEAR_MISS,
                               REWARD_SCALE, SPOILED, TERRAIN)
from ..data.fieldnotes import NOTES
# Generation and the haul, split out at 499 lines; re-exported so every caller
# keeps asking this module.
from .expedition_gen import (STRANDED_SHARE, generate, haul_kept,  # noqa: F401
                             landing_forecast, study_kept)


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
    #: The class of machine they are driving (`data/vehicles.py`), or "" for
    #: a party on foot. `rover` is that machine's condition.
    vehicle: str = ""
    #: The craft they came down in (`sim/craft.Carried.id`), or -1 for a
    #: party the old door put down before landers were things you owned.
    craft: int = -1
    #: Where on the world they are, as a cell of `sim/worldmap` — or
    #: (-1, -1) for a party the old door put down before worlds had maps.
    cell: tuple = (-1, -1)
    #: The camp that came down with them (`sim/camps.py`): its class id,
    #: where it stands once it is up, and the days of supply left in it.
    #: Field state lives here for the same reason `rover` does — the game
    #: on the ground is played out of one object.
    camp: str = ""
    camp_x: int = -1
    camp_y: int = -1
    camp_supply: int = 0
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


# ── generation: `sim/expedition_gen.py` ──────────────────────────────────


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
    cost = step_cost(exp, dest)
    exp.x, exp.y = dest.x, dest.y
    exp.days += cost
    exp.supply = max(0, exp.supply - cost)
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


def step_cost(exp: Expedition, dest: Tile) -> int:
    """Days of supply one step onto `dest` spends, at the weather it is now.

    **The one door**, so a route home can be costed with the same arithmetic
    that will charge for walking it. `sim/wayhome.py` adds up this function over
    a path; `move` spends it. Before the split it lived inside `move` alone and
    nothing could quote a walk in advance — which is the ground's one real
    decision, since a party that runs out of supply before it reaches the lander
    keeps `STRANDED_SHARE` of what it is carrying and leaves the rest.

    Ground already crossed is cheap: the route is known and the rover has a
    track to follow. Otherwise coming home is a death sentence.
    """
    terrain = TERRAIN[dest.terrain]
    # What they are crossing it *in* (`sim/vehicles.py`): a day off ground
    # the machine is made for, a day on ground it will not enter and the
    # party walks. A rover was a flat day off everything.
    from . import vehicles as vehicles_sim
    base = (1 if dest.visited
            else max(1, terrain.cost
                     + vehicles_sim.step_change(exp, dest.terrain)))
    return weather_sim.move_cost(exp, base)


def _spring_hazard(exp: Expedition, officers, rng) -> dict:
    hz = rng.pick(HAZARDS)
    skill = max((o.level for o in officers if o.stat == hz.stat), default=0)
    beaten = rng.chance(min(0.85, 0.25 + skill * 0.14))
    if beaten:
        say(exp, f"{hz.name}: {hz.blurb} Handled.", "good")
        return {"hazard": hz, "beaten": True}

    exp.supply = max(0, exp.supply - hz.supply)
    from . import vehicles as vehicles_sim
    exp.rover = max(0, exp.rover - vehicles_sim.wear(exp, hz.rover))
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



def odds_for(exp: Expedition, index: int, officers) -> dict:
    """The chance, the officer, the prize and the risk, before you try it.

    The screen said "(science, difficulty 3)" and stopped there. Resolution is
    `1d6 + level >= difficulty + 2`, so that same string is a one-in-three with
    a green officer and five-in-six with a level-three one — and the reward was
    unpacked into a discarded variable, so nobody was ever told what success
    paid.
    """
    options = options_here(exp)
    if index >= len(options):
        return {}
    label, stat, difficulty, reward = options[index]
    if not stat:
        return {"label": label, "chance": 1.0, "stat": None, "level": 0,
                "reward": reward, "low": 0, "high": 0, "hazard": 0.0,
                "who": None}

    holder = max((o for o in officers if o.stat == stat),
                 key=lambda o: o.level, default=None)
    level = holder.level if holder else 0
    # 1d6 + level >= difficulty + 2  →  the die must show this or better.
    need = difficulty + 2 - level
    faces = 6 - max(1, min(7, need)) + 1
    chance = max(0.0, min(1.0, faces / 6))
    # Lucky (`sim/arcs`): a failure is rolled again that often, so the odds
    # quoted are the odds of either roll landing — as `attempt` rolls them.
    luck = _luck(officers)
    first = chance
    chance = first + (1 - first) * luck * first
    low, high = REWARD_SCALE.get(reward, (0, 0))
    # And what it pays *for this officer*. `attempt` multiplies the roll by
    # `1 + margin * MARGIN_BONUS`, so a clean success pays well over the bare
    # scale — but this quoted the scale itself at every level. Measured on
    # "Cut a sample": 8–26 ore on the card whatever you sent, against a real
    # 47.8 at level five. Skill moved the odds on screen and moved the prize
    # in secret, which is the half of an officer's worth nobody was told.
    if high:
        best = max(0, 6 + level - (difficulty + 2))
        worst = max(0, min(best, 1 + level - (difficulty + 2)))
        low = round(low * (1 + worst * MARGIN_BONUS))
        high = round(high * (1 + best * MARGIN_BONUS))
    # What a near miss is worth, and how likely one is: the die faces that
    # fall short by `NEAR_MISS` or less. Stated, because "it fails" and "it
    # fails and you get half" are different decisions.
    near_faces = 0 if reward in ("lore", "none") else \
        max(0, min(NEAR_MISS, 6 - faces))
    return {"label": label, "chance": chance, "stat": stat, "level": level,
            "who": holder.name if holder else None, "reward": reward,
            "low": low, "high": high,
            "near": near_faces / 6 * (1 - luck * first),
            "spoiled": SPOILED if high else 0.0,
            "hazard": HAZARD_ON_FAILURE * (1 - chance)}


def _luck(officers) -> float:
    from . import arcs
    return arcs.signature_effects(officers).get("reroll", 0.0)


def attempt(exp: Expedition, index: int, officers, rng) -> dict:
    """Try one of the options a feature offers."""
    t = exp.here
    opts = options_here(exp)
    if exp.over or not opts or index >= len(opts):
        return {"ok": False, "why": "Nothing here to attempt."}

    label, stat, difficulty, reward = opts[index]
    t.resolved = True
    exp.days += 1
    exp.supply = max(0, exp.supply - 1)

    if not stat:                       # walking away is always allowed
        say(exp, f"{label}. Nothing gained and nothing risked.", "dim")
        _check_end(exp)
        return {"ok": True, "label": label, "success": True, "reward": None}

    skill = max((o.level for o in officers if o.stat == stat), default=0)
    roll = rng.int(1, 6) + skill
    success = roll >= difficulty + 2
    luck = _luck(officers)
    if not success and luck and rng.chance(luck):
        roll = rng.int(1, 6) + skill        # drawn only when it is owed
        success = roll >= difficulty + 2
    margin = roll - (difficulty + 2)

    out = {"ok": True, "label": label, "success": success, "reward": None,
           "amount": 0, "lore": None,
           # How far the roll fell short. Zero or better on a success; a
           # positive number of pips on a failure, which is what decides
           # whether anything is salvaged and how much.
           "short": max(0, -margin)}
    if success:
        lo, hi = REWARD_SCALE.get(reward, (0, 0))
        amount = rng.int(lo, hi) * (1 + max(0, margin) * MARGIN_BONUS) if hi else 0
        if reward == "lore":
            # Notes are drawn by id and filed on recovery, so what the ground
            # told you survives the flight home. It used to be a string shown
            # once and dropped with the expedition object.
            note = rng.pick([n for n in NOTES if n.id not in exp.lore] or NOTES)
            exp.lore.append(note.id)
            out["lore"] = note
            say(exp, f"{label}: {note.text}", "good")
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
        # A near miss brings something back. `margin` is negative here; within
        # `NEAR_MISS` of the mark the party salvages a share of what a clean
        # attempt would have paid.
        short = -margin
        salvage = 0.0
        if short <= NEAR_MISS and reward not in ("lore", "none"):
            lo, hi = REWARD_SCALE.get(reward, (0, 0))
            if hi:
                base = rng.int(lo, hi)
                salvage = base * SPOILED * (1 - (short - 1) / (NEAR_MISS + 1))
        if salvage > 0.01:
            out["spoiled"] = True
            out["reward"], out["amount"] = reward, salvage
            if reward == "study":
                exp.study["__any__"] = exp.study.get("__any__", 0) + salvage
            else:
                exp.haul[reward] = exp.haul.get(reward, 0) + salvage
            say(exp, f"{label} — botched, but {round(salvage)} {reward} came "
                     "back with them.", "warn")
        else:
            say(exp, f"{label} — it does not go well.", "bad")
        if rng.chance(HAZARD_ON_FAILURE):
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
    # Under a roof the day still goes; the supply does not (`sim/camps`).
    from . import camps as camps_sim
    indoors = camps_sim.shelters(exp)
    res = weather_sim.shelter(exp, rng)
    if indoors:
        exp.supply += 1
    weather = res["weather"]
    say(exp, f"Sat out the {weather.name.lower()}. A day gone"
             + (", and the camp kept the stores." if indoors else "."), "")
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
    exp.supply = max(0, exp.supply - 1)
    weather_sim.tick(exp, 1, rng, exp.biome)
    eng = max((o.level for o in officers if o.stat == "engineering"), default=0)
    med = max((o.level for o in officers if o.stat == "medicine"), default=0)
    # A day in a camp is worth more than a day on regolith (`sim/camps`).
    from . import camps as camps_sim
    worth = camps_sim.rest_worth(exp)
    exp.rover = min(10, exp.rover + round((1 + eng // 2) * worth))
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
