"""The tutorial, as a curriculum: ten chapters, twenty-nine things to do.

Not a wall of text and not a script that assumes you complied. Each lesson
names one thing, and `sim/tutorial.py` watches the game until that thing has
genuinely happened — measured against a mark taken when the lesson opened, so
"survey a body" means one more than you had, not "a body is surveyed".

Each lesson carries what to do, where to do it, and — the part a tutorial
usually skips — **what just happened and why it matters**, shown after rather
than before, when there is something to point at.

**Chapters are scenarios.** A captain who wants to learn one thing — how to
get alongside, how a crossing works, how a fight opens — can take that course
on its own from the Academy tab under Help, rather than starting at lesson
one. The order here is the order a new captain meets the game, and running it
straight through is a guided first career.

Every `watch` here must have a matching watcher in `sim/tutorial_watch.py`,
and a check fails if one does not. The lists live in `lessons_early.py` and
`lessons_late.py`; this assembles them, the way `data/chassis.py` assembles
the hull tables.
"""

from __future__ import annotations

from .lesson_types import Chapter, Lesson  # noqa: F401  (re-exported)
from .lessons_early import EARLY
from .lessons_late import LATE

#: The ten courses, in the order a career meets them.
CHAPTERS = [
    Chapter("first-light", "First light",
            "The screens, the ship, and where to look things up.",
            "Find anything; read a hull; open the manual at the right page."),
    Chapter("the-wheel", "The wheel",
            "Flying her yourself, and handing her to the computer.",
            "Fly by hand or by computer, and get alongside a quay."),
    Chapter("bread-and-salt", "Bread and salt",
            "Prices, cargo, and the first money most captains make.",
            "Read a market, sell what you know, and keep a tank full."),
    Chapter("looking-closely", "Looking closely",
            "Four ways of looking, and the bench that turns them into work.",
            "Choose a survey method on purpose and finish a technology."),
    Chapter("the-long-crossing", "The long crossing",
            "Burns, watches, and the two clocks a crossing runs on.",
            "Plot a transfer, stand its watches, and jump to a new star."),
    Chapter("rock-and-ice", "Rock and ice",
            "Taking things out of a system: seams, trenches, and the ground.",
            "Mine a seam, work a dig, and bring a landing party home."),
    Chapter("iron", "Iron",
            "What a fight is, and how not to have one.",
            "Open a fight at a band you chose, and know when to talk."),
    Chapter("roots", "Roots",
            "Holdings: the only thing that pays you while you are away.",
            "Plant a colony and read what it yields against what it costs."),
    Chapter("powers", "Powers",
            "Six powers, two axes of opinion, and what standing buys.",
            "Move a power's opinion of you, and know what it costs elsewhere."),
    Chapter("the-long-game", "The long game",
            "Yards, refits, contracts, and the five ways this ends.",
            "Design and change a hull, take work, and read the record."),
]

CHAPTERS_BY_ID = {c.id: c for c in CHAPTERS}

#: Every lesson, in teaching order.
LESSONS = list(EARLY) + list(LATE)

LESSONS_BY_ID = {lesson.id: lesson for lesson in LESSONS}


def lessons_in(chapter_id: str) -> list:
    """The lessons of one course, in order."""
    return [l for l in LESSONS if l.chapter == chapter_id]


def first_step_of(chapter_id: str) -> int:
    """Where a chapter starts, as an index into `LESSONS`.

    What the Academy's "teach me this" button jumps the tutorial to.
    """
    for index, lesson in enumerate(LESSONS):
        if lesson.chapter == chapter_id:
            return index
    return 0


def chapter_of(lesson) -> Chapter | None:
    return CHAPTERS_BY_ID.get(getattr(lesson, "chapter", ""))
