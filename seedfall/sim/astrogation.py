"""Plotting the jump, and where it actually puts you.

The 2d6 grammar landed in `sim/checks.py` and the life path teaches
thirty-one skills. Audited across the whole package, **three of them are
never asked for by anything**: `tactics`, `gunnery` and `astrogation` — and
those three are exactly the skills that describe running a starship. Every
skill the game rolls is person-scale, out of the Afoot layer; the ship's own
acts resolve on ratings and curves that no crew member's history touches.

This is the first of the three brought across, and it is the one Traveller
is clearest about: **astrogation is jump accuracy.** You do not roll to
arrive — you roll for *where*.

Which is a gift here, because a jump in SEEDFALL has always arrived at
exactly the same place: `flight.stand_off` with nothing to stand off at,
which is the point `(0, -ARRIVAL_RADIUS, 0)` in every system in the galaxy,
every time, for every captain. There is a whole in-system flight layer
downstream of that point — transfers, burns, days — and nothing upstream of
it ever varied.

So a plot moves the landfall, and the flight layer prices the difference in
the currency it already deals in: days. A clean plot brings you inside the
usual mark and saves a captain the transfer; a bad one throws you wide and
off the plane, and you fly it. Nothing is added to the jump's own economy —
the fuel and the crossing are what they were — and a captain with nobody
aboard who can plot is not *punished*, they are simply flying from where an
untrained plot left them.

**Whoever aboard is best at it does it**, the way a sortie is flown by
whoever holds the ticket (`sim/craft.best_pilot`). That is the whole reason
the skill exists: a hull with an astrogator aboard arrives better than one
without, and until now hiring one bought nothing at all.
"""

from __future__ import annotations

import math

from . import checks
from .flight import ARRIVAL_RADIUS

#: The skill this asks for, named once.
SKILL = "astrogation"

#: What the hull itself plots at, before anybody aboard improves on it.
#:
#: **Not `checks.UNTRAINED`.** A jump is plotted by a computer that every
#: hull in the Verge carries, and a crew with no astrogator is not *worse*
#: at it than no crew at all — they are simply no better than the machine.
#: Measured with the -3 an untrained person takes: the median leg came out
#: at an Effect of -2, so every chronicle in the game that has never hired
#: an astrogator would have started arriving 1.6 AU wide of a mark it has
#: arrived at exactly for its whole life. That is not a feature, it is a
#: tax. At nought the machine is competent, the arrival is about where it
#: always was, and what an astrogator buys is the *improvement* — which is
#: the whole reason the skill is in the game.
HULL_PLOTS = 0

#: And what the board throws for a characteristic. Seven is the middle of
#: the range and worth nothing either way (`checks.modifier`): a machine has
#: no Education, and borrowing the captain's made the hull's own plot better
#: or worse depending on who happened to own it.
BOARD_EDU = 7

#: How far a plot can move the landfall, as a share of the usual arrival
#: radius: in by this much on a clean plot, out by it on a poor one. Under a
#: half, so the arrival stays recognisably an arrival — a jump that can put
#: you nine tenths of the way to the star is not a plot, it is a lottery.
NEARER, WIDER = 0.35, 0.45

#: How much of the Effect is spent on the distance. Traveller's Effect runs
#: about -5 to +5 in ordinary play, so a fifth of it per point fills the
#: band above without needing a second curve.
PER_EFFECT = 0.2

#: How far off the line a failed plot throws you, as a share of what it cost
#: you in distance. A miss is not only long, it is *sideways* — which is
#: what makes it read as a miss rather than as a slow jump.
SIDEWAYS = 0.6

#: The light-years a plot is merely routine up to, and the light-years per
#: rung it climbs after that. Traveller makes a longer jump a harder plot
#: and so does this — but *which* distances are hard has to come off the
#: sector rather than out of the air. Measured over six galaxies, 756
#: near-neighbour legs: median 7.1 ly, tenth percentile 5.3, ninetieth 10.3.
#: So an ordinary leg is an ordinary plot, the short hops are routine, and
#: the long reaches bite. At 2.0 and 3.5 — the first draft's guess — a
#: median leg came out *difficult* and most arrivals in the game would have
#: been wide ones.
ROUTINE_LY, HARDER_PER = 5.0, 4.0

#: The ladder a plot is thrown against, easiest first. **These are ids, not
#: names.** `checks.DIFFICULTY_DM.get(how, 0)` answers 0 for anything it
#: does not know, so "very difficult" with a space in it is silently an
#: *average* plot — which is how the first draft of this made a twenty
#: light-year jump easier to plot than a twelve (72% against 42%).
LADDER = ("routine", "average", "difficult", "very_difficult", "formidable")


def plotter(game) -> tuple:
    """Who plots it, and what they bring. `(skill, score, name)`.

    **The best plot, not the best skill.** A check is the skill *and* the
    characteristic behind it, so picking whoever holds the most Astrogation
    and then throwing their own Education puts the worst plotter aboard on
    the board whenever their EDU is poor: measured, an officer with
    Astrogation 1 and Education 2 took the board off a machine that would
    have done it better, and the median leg came out at an Effect of -2.
    Whoever *plots best* plots.

    The captain is in the pool — it is their ship and somebody has to be —
    and under all of them is the hull's own board (`HULL_PLOTS`), which is
    a machine and throws no characteristic of its own.
    """
    from . import afoot_people, checks as checks_mod, lifepath
    record = afoot_people.captain_record(game)

    def worth(skill: int, score: int) -> int:
        return skill + checks_mod.modifier(score)

    best = (record.skill(SKILL), record.score("edu"),
            afoot_people.captain_name(game))
    for officer in getattr(game, "officers", []) or []:
        life = lifepath.of(game, officer)
        row = (life.skill(SKILL), life.score("edu"), officer.name)
        if worth(row[0], row[1]) > worth(best[0], best[1]):
            best = row
    board = (HULL_PLOTS, BOARD_EDU, "the plotting board")
    return best if worth(best[0], best[1]) >= worth(*board[:2]) else board


def how(ly: float) -> str:
    """How hard a plot of this length is. A long jump is a harder plot."""
    if ly <= ROUTINE_LY:
        return LADDER[0]
    step = 1 + int((float(ly) - ROUTINE_LY) // HARDER_PER)
    return LADDER[min(step, len(LADDER) - 1)]


def forecast(game, ly: float) -> dict:
    """What the plot is, before it is thrown. Quoted on the Helm.

    Preview equals act: the odds here come from the same table `plot` rolls
    against, so a captain deciding whether to hire an astrogator can read
    what one is worth.
    """
    skill, score, who = plotter(game)
    rung = how(ly)
    return {"skill": skill, "score": score, "who": who, "how": rung,
            "chance": checks.chance(skill, score, rung),
            "trained": skill > checks.UNTRAINED}


def plot(game, rng, ly: float):
    """Throw it. Returns the `checks.Check`, whose Effect is the accuracy."""
    skill, score, who = plotter(game)
    return checks.roll(rng, skill=skill, score=score, how=how(ly),
                       about=f"{ly:.1f} ly", what=f"{who} plotting the jump")


def _share(check) -> float:
    """How far in or out this plot moves the arrival, as a share of the mark.

    Positive is nearer. Nought is the arrival this game has always had, to
    the metre, which is what makes a plot something no existing chronicle
    has to notice.
    """
    effect = int(getattr(check, "effect", 0) or 0)
    return max(-WIDER, min(NEARER, effect * PER_EFFECT))


def landfall(check, rng) -> tuple:
    """Where the plot puts the hull, in AU. The usual mark, moved.

    The Effect decides it: positive brings the arrival in towards the system
    and leaves it on the line, negative throws it long and sideways. An
    Effect of nought is the arrival this game has always had, to the metre,
    which is what makes this a change nobody's existing chronicle has to
    notice.
    """
    share = _share(check)
    if share == 0.0:
        return 0.0, -ARRIVAL_RADIUS, 0.0
    radius = ARRIVAL_RADIUS * (1.0 - share)
    if share > 0:
        return 0.0, -radius, 0.0
    # A miss is sideways as well as long, and which way is the dice's.
    # The whole sideways budget goes into the offset, whichever way it
    # points. Flattening the z by a third read well and made `drift_au`
    # a lie — the real drift then depended on the bearing, so a screen
    # quoting "0.95 AU off" was describing an arrival 0.83 AU off.
    off = ARRIVAL_RADIUS * abs(share) * SIDEWAYS
    angle = rng.float(0.0, 2.0 * math.pi)
    return math.cos(angle) * off, -radius, math.sin(angle) * off


def drift_au(check) -> float:
    """How far from the usual mark this plot puts you, in AU.

    The *distance*, which needs no bearing and therefore no generator — a
    screen asking how far off a plot landed must not spend the chronicle's
    dice to find out.
    """
    share = _share(check)
    along = ARRIVAL_RADIUS * abs(share)
    if share >= 0:
        return along
    return math.hypot(along, ARRIVAL_RADIUS * abs(share) * SIDEWAYS)


def says(check, ly: float) -> tuple:
    """One line about a plot that has happened, and its tint."""
    effect = int(getattr(check, "effect", 0) or 0)
    if effect > 2:
        return ("The plot is a good one: you come out well inside the usual "
                "mark and the transfer is shorter for it.", "good")
    if effect >= 0:
        return ("The plot holds. You arrive about where anybody would.", "")
    if effect >= -3:
        return ("The plot is loose. You come out long and off the line, and "
                "the difference is yours to fly.", "warn")
    return ("The plot is badly out. You arrive a long way from where you "
            "meant to and nothing but flying will fix it.", "bad")
