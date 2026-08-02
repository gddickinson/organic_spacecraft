"""Machines you own, where they are, and how much of them survives the distance.

The one idea here: **a robot is worth what its autonomy can carry across the
gap between it and whoever is telling it what to do.**

That is not a game invention. Real spacecraft are rated on the ECSS ladder —
E1 real-time teleoperation, E2 preplanned, E3 adaptive, E4 goal-directed — and
the reason the ladder exists is light. A robot in low orbit answers in twenty
milliseconds; one on the Moon takes three to five seconds; one at Mars takes
between eight and forty minutes, which is why nobody drives a Mars rover with a
joystick. `grip` is that curve, and everything else in this file exists to feed
it a distance.

What it buys the game is a real decision instead of a shopping list. A Spar
Rigger is level four and teleoperated: alongside it is the best hand you own,
and posted to a holding one AU away it is a statue. An Anchorite is level three
and goal-directed: never the best, and the only thing worth leaving behind when
you sail out of the system. The catalogue does not need to say which is
better, because the answer is *where*.

Postings are deliberately few and all of them are places the game already has:
`aboard`, a holding of your own, or stowed in the hold doing nothing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.save import register
from ..data.robots import ROBOTS_BY_ID
from . import flight
# **The law of telepresence lives in its own file** (#138): how far a
# machine is and how much of it survives the delay. One way — that module
# imports the roster lazily, inside the two functions that need it.
from .telepresence import effective






#: How much of itself a machine wears out per day of work, as a share of
#: condition. Measured against the run it should give: at 0.0007 a fabricated
#: frame worked flat out is down to half after 990 days, which is a little
#: under three years and long enough that it is a maintenance decision rather
#: than a daily chore.
WEAR_PER_DAY = 0.0007

#: What a grown machine mends per day, being alive. Slower than it wears is no
#: use to anybody, so this is comfortably faster: a Myrmidon idle for a month
#: comes back whole.
MEND_PER_DAY = 0.02

#: Below this a machine stops being useful and says so. Not zero, because a
#: hand that fades to nothing without ever failing is a hand nobody notices
#: losing.
BROKEN_AT = 0.25

#: Families that mend themselves. Everything else needs a yard, which is the
#: trade the Compendium has always drawn between grown and built.
SELF_MENDING = ("grown", "xeno")

#: Where a robot can be. A posting is a string so a save carries it without a
#: migration; `colony:<id>` names one of your own holdings.
ABOARD = "aboard"
STOWED = ""


@register
@dataclass
class Robot:
    """One machine you own."""

    id: int
    class_id: str
    name: str
    #: `aboard`, `colony:<id>`, or "" for stowed in the hold.
    posting: str = ABOARD
    #: 0..1. Wear costs grip before it costs you the machine.
    condition: float = 1.0

    @property
    def definition(self):
        return ROBOTS_BY_ID[self.class_id]

    @property
    def broken(self) -> bool:
        return self.condition < BROKEN_AT

    @property
    def label(self) -> str:
        return f"{self.name} — {self.definition.name}"


# ── the roster ─────────────────────────────────────────────────────────────

def owned(game) -> list:
    return list(getattr(game, "robots", []))


def aboard(game) -> list:
    """Machines on the ship — standing a watch or stowed in the hold."""
    return [r for r in owned(game) if (r.posting or STOWED) in (ABOARD, STOWED)]


def at_colony(game, colony_id) -> list:
    want = f"colony:{colony_id}"
    return [r for r in owned(game) if r.posting == want]


@dataclass(frozen=True)
class Hand:
    """A machine on the bridge, in the shape the bridge already reads.

    `sim/ship.stats` and `sim/stations.officer_level` ask a hand for its
    `stat`, its `level` and whether it has `retired` — so a machine standing a
    watch goes through the existing door rather than through a second one
    bolted alongside it.

    It carries **no loyalty field on purpose**. `loyalty.effective_level` falls
    back to the neutral value for anything that has none, so a machine works at
    exactly its level: neither the 1.2 a devoted officer gives nor the 0.45 a
    mutinous one does. A machine is not loyal and is not disloyal, and this is
    the shape that says so.
    """

    stat: str
    level: float
    name: str
    role_name: str
    trait_id: None = None
    retired: bool = False


def standing(game) -> list:
    """Every machine holding a bridge station, as hands the bridge can read."""
    out = []
    for robot in owned(game):
        if (robot.posting or STOWED) != ABOARD:
            continue
        klass = robot.definition
        if not klass.stat or robot.broken:
            continue
        out.append(Hand(stat=klass.stat, level=effective(game, robot),
                        name=robot.name, role_name=klass.name))
    return out


#: What a duty **does**, as (the stat it lifts, per level of machine).
#:
#: Written because the first cut declared six duties in `data/robots.py` and
#: consumed exactly one of them. A Scarab Crawler said "Mining" on its card and
#: cut no rock; a Stevedore said "Cargo" and stowed nothing. That is the defect
#: this project has a guard for one layer down — `tests/test_declared` — and it
#: had been committed one layer up.
#:
#: Every one goes through `sim/ship.Stats`, which is the one door the whole game
#: already reads: `mining.rig_of` walks the rig stats, `repair_tick` reads
#: `regen`, a survey reads `scan`, and `damage` reads `crew_guard`. So nothing
#: here needed new plumbing — the duty had only to be pointed at the number that
#: already meant it.
#:
#: The magnitudes are one figure: **a level-three machine lifts its stat by
#: about fifteen per cent of a starting hull's**, the same share a Verger lifts
#: a holding by. Measured against a fresh NAVIS — regen 1.35, cargo 340 t, mine
#: 3.2, scan 0.63 — so a Scarab is half a tonne a day of rig and a Stevedore
#: thirty-odd tonnes of hold.
#:
#: `works` is deliberately absent: it is the duty that acts on a *holding*
#: rather than on the ship, through `works.crewed_yields`.
DUTY_FX = {
    "repair": ("regen", 0.065),
    "cargo": ("cargo", 16.0),
    "mine": ("mine", 0.17),
    "survey": ("scan", 0.035),
    "ground": ("crew_guard", 0.05),
}

#: How far `crew_guard` can be pushed by machines going in first. It starts at
#: zero and is subtracted from one in `sim/damage`, so uncapped a shelf of
#: Myrmidons would make a crew unkillable.
GUARD_CEILING = 0.6


def aboard_effects(game) -> dict:
    """What the machines on this ship add to its stats, by stat name.

    Aboard only. A Verger posted to a holding two AU away is working on the
    holding, and a ship that collected its repair rating from something in
    another orbit would be the two-doors fault this file exists to avoid.
    """
    out: dict = {}
    for robot in owned(game):
        if (robot.posting or STOWED) != ABOARD or robot.broken:
            continue
        got = effective(game, robot)
        if got <= 0:
            continue
        for duty in robot.definition.duties:
            fx = DUTY_FX.get(duty)
            if fx is None:
                continue
            stat, per = fx
            out[stat] = out.get(stat, 0.0) + got * per
    if "crew_guard" in out:
        out["crew_guard"] = min(GUARD_CEILING, out["crew_guard"])
    return out


def watchkeepers(game) -> int:
    """How many machines aboard could hold a watch if nobody else could.

    **The one door for "is this hull deserted".** Two places ask it — the air
    running out in `core/clock` and the stores running out in `sim/upkeep` —
    and both used to ask only whether any *person* was left:

        if game.ship.crew <= 0 and not lifespan.active(game.officers):
            game.die("Nobody left aboard to hold the watch.")

    Measured with three machines standing engineering, science and comms, and
    the ship's own stats reading regen 1.71 and research 1.38 off them: both
    lines fired. A hull the Dry Choir would call fully crewed was reported as
    abandoned, which is the opposite of what `hullforms` has said about the
    synthetic family since it was written — "crewless Dry Choir work".
    """
    return len([r for r in owned(game)
                if (r.posting or STOWED) == ABOARD and not r.broken
                and r.definition.stat])


def crewless(game) -> bool:
    """True when the machines are the crew: nobody alive, and a watch held."""
    from . import lifespan
    people = max(0, int(getattr(game.ship, "crew", 0) or 0))
    return (people <= 0 and not lifespan.active(getattr(game, "officers", []))
            and watchkeepers(game) > 0)


def working(game, colony, duty: str) -> float:
    """What this holding's machines add on this duty, in levels.

    Summed rather than best-of: three Vergers are three Vergers. What one is
    worth is `effective`, so a teleoperated frame left at a holding you have
    sailed away from contributes very nearly nothing, and says so on the
    screen rather than quietly.
    """
    total = 0.0
    for robot in at_colony(game, colony.id):
        if duty in robot.definition.duties:
            total += effective(game, robot)
    return total


# ── building and keeping ───────────────────────────────────────────────────

def can_build(game, class_id: str) -> tuple[bool, str]:
    """Whether this yard, this hold and this bench allow one."""
    klass = ROBOTS_BY_ID.get(class_id)
    if klass is None:
        return False, "No such class."
    if klass.tech and klass.tech not in game.research.unlocked:
        return False, f"Needs {klass.tech}."
    if klass.cost.get("credits", 0) > game.credits:
        return False, f"{klass.cost['credits']:,.0f} credits."
    for key, amount in klass.cost.items():
        if key == "credits":
            continue
        if _held(game, key) < amount:
            return False, f"Short of {key}."
    # A frame you cannot lift is a frame you cannot carry to the work.
    if klass.mass_t > _hold_free(game):
        return False, f"No room: it masses {klass.mass_t:g} t."
    return True, ""


def build(game, class_id: str, rng=None):
    """Pay for one and put it in the hold. Returns the Robot, or None."""
    ok, _why = can_build(game, class_id)
    if not ok:
        return None
    klass = ROBOTS_BY_ID[class_id]
    game.credits -= klass.cost.get("credits", 0)
    for key, amount in klass.cost.items():
        if key != "credits":
            _take(game, key, amount)
    made = Robot(id=_next_id(game), class_id=class_id,
                 name=_name_for(game, klass), posting=ABOARD)
    game.robots = owned(game) + [made]
    return made


def scrap(game, robot) -> dict:
    """Break one up. Half its materials back, and none of its credits."""
    back = {}
    for key, amount in robot.definition.cost.items():
        if key == "credits":
            continue
        got = round(amount * 0.5 * robot.condition, 3)
        if got > 0:
            game.stores[key] = game.stores.get(key, 0) + got
            back[key] = got
    game.robots = [r for r in owned(game) if r.id != robot.id]
    return back


def post(game, robot, posting: str) -> tuple[bool, str]:
    """Send one somewhere. A holding must be yours, here, and online."""
    if posting in (ABOARD, STOWED):
        robot.posting = posting
        return True, ""
    colony = None
    if posting.startswith("colony:"):
        want = posting.split(":", 1)[1]
        colony = next((c for c in getattr(game, "colonies", [])
                       if str(c.id) == want), None)
    if colony is None:
        return False, "No such holding."
    if not getattr(colony, "online", False):
        return False, f"{colony.name} is not running yet."
    if colony.system_id != game.system.id:
        return False, f"{colony.name} is not in this system — carry it there."
    robot.posting = posting
    return True, ""


def daily_upkeep(game) -> dict:
    """What every machine you own wants tomorrow, by commodity."""
    want: dict = {}
    for robot in owned(game):
        if robot.broken:
            continue
        for key, rate in robot.definition.upkeep.items():
            want[key] = want.get(key, 0.0) + rate
    return want


def tick(game, days: float, rng) -> list:
    """Feed them, wear them, and let the living ones mend. Log lines out."""
    if days <= 0 or not owned(game):
        return []
    out: list = []

    want = daily_upkeep(game)
    starved = []
    for key, rate in want.items():
        need = rate * days
        if need <= 1e-9:
            continue
        if key == "credits":
            game.credits -= need
            continue
        if _take(game, key, need) > need * 0.02:
            starved.append(key)

    for robot in owned(game):
        was = robot.condition
        klass = robot.definition
        if robot.posting == STOWED and klass.family not in SELF_MENDING:
            pass                      # stowed and dead metal: nothing changes
        elif robot.posting == STOWED:
            robot.condition = min(1.0, robot.condition + MEND_PER_DAY * days)
        else:
            wear = WEAR_PER_DAY * days
            if starved:
                # Unfed, it works itself apart at twice the rate. A machine
                # short of the metals it patches itself with is not idle; it
                # is spending itself.
                wear *= 2.0
            robot.condition = max(0.0, robot.condition - wear)
            if klass.family in SELF_MENDING and not starved:
                robot.condition = min(1.0, robot.condition
                                      + MEND_PER_DAY * days * 0.5)
        if was >= BROKEN_AT > robot.condition:
            out.append(("warn", f"{robot.name} has stopped. It wants a yard."))
    if starved:
        out.append(("warn", "The machines are short of "
                            f"{', '.join(sorted(starved))}."))
    return out


# ── plumbing ───────────────────────────────────────────────────────────────

def _held(game, key: str) -> float:
    return game.stores.get(key, 0) + game.ship.cargo.get(key, 0)


def _take(game, key: str, amount: float) -> float:
    """Draw from the hold first, then the depot. Returns what was missing."""
    left = amount
    have = game.ship.cargo.get(key, 0)
    if have > 0:
        spent = min(have, left)
        game.ship.cargo[key] = have - spent
        left -= spent
    if left > 0:
        have = game.stores.get(key, 0)
        spent = min(have, left)
        game.stores[key] = have - spent
        left -= spent
    return left


def _hold_free(game) -> float:
    stats = game.recompute() if hasattr(game, "recompute") else None
    cap = getattr(stats, "cargo", None)
    if cap is None:
        cap = float(getattr(game.ship.chassis_def, "cargo", 0) or 0)
    used = sum(game.ship.cargo.values())
    used += sum(r.definition.mass_t for r in aboard(game))
    return max(0.0, float(cap) - used)


def _next_id(game) -> int:
    return max((r.id for r in owned(game)), default=0) + 1


def _name_for(game, klass) -> str:
    """A hull number, not a person's name. These are not people."""
    seen = sum(1 for r in owned(game) if r.class_id == klass.id)
    prefix = "".join(word[0] for word in klass.name.split()[:2]).upper()
    return f"{prefix}-{seen + 1:02d}"


def summary(game) -> dict:
    """One reading of the whole roster, for a panel and for a check."""
    mine = owned(game)
    return {
        "count": len(mine),
        "aboard": len([r for r in mine if r.posting == ABOARD]),
        "posted": len([r for r in mine if (r.posting or "").startswith("colony:")]),
        "broken": len([r for r in mine if r.broken]),
        "watch": len(standing(game)),
        "upkeep": daily_upkeep(game),
    }
