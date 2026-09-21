"""What a career *is*, kept apart from the list of them.

Split out of `data/careers.py` when the civil services arrived
(`data/careers_civil.py`): two tables of lives, one shape, and neither file
importing the other's list. The shape is Traveller's — qualify, survive,
advance, ranks, skills, mishaps, events, benefits — and the one addition is
`station`, which is how a navigator's history comes out reading like a
navigator's rather than like a dice roll.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Career:
    """One service, and what it does to the people who go into it."""

    id: str
    name: str
    #: One line on a service record.
    blurb: str
    #: Getting in: the characteristic and the target on 2d6.
    qualify: tuple           # (characteristic id, target)
    #: Staying alive in it, and getting on in it.
    survive: tuple
    advance: tuple
    #: What a term teaches, by rank. The first list is what everybody picks
    #: up; the second is what only the commissioned learn.
    ranks: tuple
    skills: tuple
    officer_skills: tuple = ()
    #: What goes wrong. A mishap ends the career — that is the whole weight
    #: of it — and leaves the person with the line as their story.
    mishaps: tuple = ()
    #: What happens that does not end it.
    events: tuple = ()
    #: What they leave with, by how many terms they served.
    benefits: tuple = ()
    #: Which of the ship's stations this career most naturally fills, so a
    #: navigator's history reads like a navigator's.
    station: str = ""
