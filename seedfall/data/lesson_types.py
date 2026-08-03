"""The shapes a curriculum is made of: a chapter, and a lesson inside it.

Split from `data/lessons.py` the way `data/hull_types.py` is split from the
hull tables — the lists live in `lessons_early.py` and `lessons_late.py`, and
`lessons.py` assembles them. A shape module in the middle is what stops the
lists and the assembler importing each other.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Lesson:
    """One thing to do, and what it taught once it is done.

    `watch` names a watcher in `sim/tutorial_watch.py` that decides — from
    the state of the chronicle, measured against a mark taken when the lesson
    opened — whether the thing has genuinely happened. A lesson whose watcher
    could not tell would be a lesson that takes your word for it, and a check
    fails if any lesson names a watcher that does not exist.
    """

    id: str
    title: str
    ask: str                 # the thing to do
    screen: str              # where it is done
    watch: str               # which watcher decides it has happened
    then: str                # what just happened, and why it matters
    chapter: str = ""        # which course this belongs to
    skip_if: str = ""        # a watcher that means this is already true


@dataclass(frozen=True)
class Chapter:
    """A course of lessons: one scenario a captain is walked through."""

    id: str
    title: str
    blurb: str               # what this course is about, in one line
    #: What a captain should be able to do by the end of it. Shown on the
    #: Academy page, so a player choosing where to start can read the
    #: destination rather than guessing from a title.
    teaches: str = ""
