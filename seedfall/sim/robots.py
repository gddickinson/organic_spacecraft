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

#: Seconds for light to cross one astronomical unit. 149,597,870.7 km over
#: 299,792.458 km/s — a real number, not a tuning knob.
LIGHT_S_PER_AU = 499.005

#: Astronomical units in a light year, for a robot left behind in a system you
#: have sailed out of. It is a very large number on purpose: at 63,241 AU per
#: light year the nearest neighbour is four light *years* of round trip, and
#: nothing below goal-directed is worth a gram of the mass it took to get there.
AU_PER_LY = 63_241.077

#: Round-trip lag, in seconds, that costs a class half of what it is worth.
#:
#: Each one is the real figure that defines its rung rather than a curve fitted
#: to feel right:
#:
#: - **E1** — teleoperation. The Moon is a three-to-five second round trip and
#:   is already at the edge of hand-flying; four seconds is where half of a
#:   teleoperated hand is gone.
#: - **E2** — preplanned. What matters is how long before the plan runs out and
#:   it needs a new one. Twenty minutes is the far end of the Mars round trip,
#:   which is exactly the delay that killed joystick control.
#: - **E3** — adaptive. It replans locally and reports; a watch is six hours.
#: - **E4** — goal-directed. Give it the objective and go, and the time
#:   constant is *how long the objective stays the one you wanted* — a season
#:   or a year for a caretaker left on a holding. One year.
#:
#: The last one was thirty days in the first draft, and the check caught it: an
#: Anchorite is bought precisely to be left behind, and at a month it kept a
#: thousandth of itself the moment the ship sailed. A rung that fails at the
#: one job its class exists for is the wrong number, not a hard trade.
HALF_LIFE_S = {1: 4.0, 2: 1_200.0, 3: 21_600.0, 4: 31_557_600.0}

#: What each rung delivers **with no contact at all** — its own account.
#:
#: The first draft had no such thing, and the checks caught the consequence: an
#: Anchorite is bought precisely to be left behind, and with grip decaying to
#: zero it kept a thousandth of itself the moment the ship sailed. The error was
#: the model, not the number. The ECSS ladder does not describe how well a
#: robot obeys — it describes *how much mission it executes on its own*, and E4
#: is "execution of goal-oriented mission operations". A goal-directed machine
#: out of contact is not idle. It is doing the job.
#:
#: So what the distance costs is the share that needed you: a change of mind, a
#: new objective, a judgement nobody wrote down.
#:
#: - **E1** — nothing. With no link a teleoperated frame is a statue, which is
#:   the definition rather than a penalty.
#: - **E2** — it finishes the plan it was given and stops.
#: - **E3** — it replans locally for ever. What it cannot do is decide the
#:   objective was wrong.
#: - **E4** — it executes the mission. You lose the part that was you.
STANDING = {1: 0.0, 2: 0.05, 3: 0.25, 4: 0.60}

#: A hull's own length is not a distance. Anything closer than this counts as
#: alongside, so a robot working on the ship it is posted to is not quietly
#: docked a few microseconds of grip.
ALONGSIDE_AU = 1e-6

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


# ── the law ────────────────────────────────────────────────────────────────

def grip(autonomy: int, lag_s: float) -> float:
    """How much of a machine's level survives the delay to its supervisor.

    Two parts, and the second is the one the first draft was missing. What it
    does **on its own account** never goes away — `STANDING` — and the rest is
    the share that needed you, which decays with the round trip.

    A hyperbola rather than an exponential for that second part, deliberately:
    teleoperation does not fall off a cliff at some latency, it gets steadily
    and unboundedly worse, and a hand at 4% is a hand you can still watch
    failing. Alongside, every rung is whole; out of contact, every rung falls
    to exactly what it can do by itself.
    """
    rung = int(autonomy)
    half = HALF_LIFE_S.get(rung, HALF_LIFE_S[2])
    alone = STANDING.get(rung, STANDING[2])
    return alone + (1.0 - alone) / (1.0 + max(0.0, float(lag_s)) / half)


def gap_au(game, robot) -> float:
    """How far this machine is from the ship, in AU.

    Aboard is zero. A holding in this system is the distance from the hull to
    the body it sits on — which moves, because both of them are in orbit. A
    holding in another system is measured across the sector and comes out in
    light *years* converted to AU, which is the honest answer and a brutal one.
    """
    posting = robot.posting or STOWED
    if posting in (ABOARD, STOWED):
        return 0.0
    colony = _colony_of(game, robot)
    if colony is None:
        return 0.0
    if colony.system_id == game.system.id:
        body = next((b for b in game.system.bodies if b.id == colony.body_id),
                    None)
        if body is None:
            return 0.0
        gap = flight.distance_to(game, body)
        # Alongside is alongside. Without this a machine on the very body the
        # hull is holding station over pays grip for a few hundred kilometres
        # of orbit, which is a lag of about a millisecond and reads on the
        # panel as a teleoperated frame mysteriously below its rating.
        return 0.0 if gap < ALONGSIDE_AU else gap
    from ..world import galaxy
    here = game.system
    there = next((s for s in game.galaxy.systems if s.id == colony.system_id),
                 None)
    if there is None:
        return 0.0
    return galaxy.distance(here, there) * AU_PER_LY


def lag_seconds(game, robot) -> float:
    """The round trip, in seconds. Out and back, because an order needs both."""
    return 2.0 * gap_au(game, robot) * LIGHT_S_PER_AU


def effective(game, robot) -> float:
    """What this machine is actually worth where it is standing.

    Its level, through its autonomy at this distance, through how worn it is.
    A broken one is worth nothing at all, which is the point of `BROKEN_AT`.
    """
    if robot.broken:
        return 0.0
    klass = robot.definition
    return klass.level * grip(klass.autonomy, lag_seconds(game, robot)) \
        * robot.condition


def _colony_of(game, robot):
    posting = robot.posting or ""
    if not posting.startswith("colony:"):
        return None
    want = posting.split(":", 1)[1]
    return next((c for c in getattr(game, "colonies", [])
                 if str(c.id) == want), None)


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
