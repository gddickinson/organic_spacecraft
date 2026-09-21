"""The shape of a gunnery drill: what arrives, when, and what counts as a pass.

Kept apart from the drills themselves the way `part_types.py` is kept apart
from `armaments.py` — the records are a contract several modules read, and the
table is content that grows. `sim/drills.py` builds an action out of these and
judges it against them; nothing here does anything.

**The shape is FreeSpace 2's, deliberately.** That game solved the problem of
teaching a gunner twenty-five years ago and the answer has not been improved
on: a short brief, a *directive list* on the glass that ticks itself off while
you fly, primary goals you must meet and secondary ones worth having, waves
that arrive on a clock so the sky changes under you, and a debrief that says
what you actually did rather than whether you won.
"""

from __future__ import annotations

from dataclasses import dataclass

#: What a directive asks for. Each is a question `sim/drills` can answer about
#: an action in progress, which is what lets the list tick itself off on the
#: glass instead of being scored at the end.
#:
#: - **clear** — every hostile of a kind is gone.
#: - **silence** — a named thing has lost every turret it had.
#: - **cripple** — a named thing has lost its drives.
#: - **wreck** — a named fitting kind is off a named thing (the refinery, the
#:   reactor, the gantry): the drill that teaches shooting a *place*.
#: - **stop** — no seeker got through; the point-defence pass.
#: - **survive** — you are still here after so many seconds, or with a share
#:   of the hull still on.
#: - **under** — it was over inside so many seconds: a time limit, which is
#:   the opposite question and has to be asked as one.
#: - **protect** — a friend is still alive at the end.
#: - **accuracy** — a share of your rounds landed.
#: - **spare** — you did *not* shoot something: the discipline directive.
AIMS = ("clear", "silence", "cripple", "wreck", "stop", "survive",
        "under", "protect", "accuracy", "spare")


@dataclass(frozen=True)
class Spawn:
    """One group arriving at once."""

    kind: str
    name: str
    count: int = 1
    behaviour: str = "stand"
    #: Where it comes in, in km, and how far it wants to end up.
    at_km: float = 14.0
    stand_km: float = 8.0
    pace: float = 0.25
    #: What it shoots with — names from `sim/foes`, resolved there so this
    #: table holds no numbers of its own.
    guns: tuple = ()
    #: The places that can be shot off it, as `foes.SUBSYSTEMS` kinds.
    parts: tuple = ()
    #: How wide a piece of sky the group arrives across, in degrees, and how
    #: far above or below the hull's plane it sits.
    spread: float = 50.0
    rise: float = 18.0
    hostile: bool = True


@dataclass(frozen=True)
class Wave:
    """What turns up, and when. `at` is seconds into the action."""

    at: float
    say: str
    spawn: tuple


@dataclass(frozen=True)
class Aim:
    """One line of the directive list."""

    id: str
    say: str
    kind: str
    #: What it is about: a contact kind, a name, or a fitting kind for
    #: `wreck`. Empty means "everything hostile".
    of: str = ""
    count: int = 0
    seconds: float = 0.0
    share: float = 0.0
    primary: bool = True


@dataclass(frozen=True)
class Drill:
    """One training action, start to debrief."""

    id: str
    name: str
    #: One line on the picker, and the paragraph at the brief.
    teaches: str
    brief: str
    #: The seat you sit in, by armament id, and what the sky looks like.
    seat: str
    setting: str = "deep"
    #: How long it runs before it is called; 0 runs until the aims are met.
    seconds: float = 0.0
    waves: tuple = ()
    aims: tuple = ()
    #: What the hull you are standing on has, and how hard it is to hit.
    hull: float = 340.0
    evade: float = 0.25
    #: The order a gunnery school teaches them in, and a line for the list.
    rung: int = 1
    #: Which of the game's own situations this one is practice for.
    about: str = ""


def primary(drill: Drill) -> tuple:
    return tuple(a for a in drill.aims if a.primary)


def secondary(drill: Drill) -> tuple:
    return tuple(a for a in drill.aims if not a.primary)
