"""Watching the game until the player has actually done the thing.

The rule that shapes this: **a tutorial must not take your word for it.** A
step that says "survey a body" and advances because you clicked Next has
taught nobody anything, and worse, it will happily march a confused player
through eight screens of congratulation.

So every lesson names a `watch`, and a watcher is a function of game state
compared against a **mark** taken when the lesson opened. "Survey a body"
means one more than you had, not "a body is surveyed" — otherwise a captain
who surveyed something before the tutorial started would be advanced for free.

It lives on the `Game` with an `.over` flag, like everything else you can be
in the middle of, so it survives a save. It never diverts navigation: it is a
strip along the top, not a cage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.lessons import (CHAPTERS, CHAPTERS_BY_ID, LESSONS,
                            LESSONS_BY_ID, first_step_of, lessons_in)
# The watchers and the mark live next door; re-exported because eight
# checks and the Academy page read them through this module.
from .tutorial_watch import (SKIPS, WATCHERS, deed, did,  # noqa: F401
                            mark_of, skipper, watcher)

# ── the thing on the Game ──────────────────────────────────────────────────

@register
@dataclass
class Tutorial:
    step: int = 0
    mark: dict = field(default_factory=dict)
    seen: list = field(default_factory=list)
    #: Set when the current step's watcher fires, so the explanation is shown
    #: before the next lesson replaces it.
    explaining: bool = False
    over: bool = False
    skipped: bool = False
    #: Steps stepped over because the captain had already done them. Read by
    #: `state` so the bar can say so — a tutorial that silently started at step
    #: five would look broken.
    known: int = 0


def saw(game, screen: str) -> None:
    """Called by the window whenever a screen is opened.

    The only thing the tutorial learns from a *click* rather than from the
    world, and it is deliberately weak: it records that a screen was opened,
    which is all a "go and look at this" lesson asks for.
    """
    lesson = held(game)
    if lesson is None or lesson.over:
        return
    if screen not in lesson.seen:
        lesson.seen.append(screen)


def held(game):
    return getattr(game, "tutorial", None)


def running(game) -> bool:
    lesson = held(game)
    return lesson is not None and not lesson.over


#: How long a chronicle has to have been running before the tutorial will step
#: over anything.
#:
#: **This is what reconciles two claims that both sound right.** "A tutorial step
#: that is already true should skip itself" (task #87) and "a captain who did it
#: already is not advanced for free" (a check that has been here since the
#: tutorial was written) are in flat contradiction until you ask *why* the
#: tutorial is running. A new captain who happened to survey a body five minutes
#: before opening it should still be taught — waving them through step one teaches
#: nothing, which is what that check protects. A captain in year two starting it
#: from the Help screen should not be told to survey a body when they have
#: surveyed thirty.
#:
#: From state alone those two are the same fact at different scales, so the
#: distinction is the scale: a month. Inside it, everything is taught; outside it,
#: what the chronicle can show you have done is stepped over.
SETTLED_IN_DAYS = 30


def already(game, lesson) -> bool:
    """Is this lesson's `skip_if` already satisfied, and old enough to trust?"""
    if game.day < SETTLED_IN_DAYS:
        return False
    fn = SKIPS.get(getattr(lesson, "skip_if", "") or "")
    return bool(fn and fn(game))


def _past_known(game) -> int:
    """Step over anything the captain has demonstrably already done.

    Called when the tutorial opens and after every step, because a lesson can
    become already-true while a later one is being taught — buying fuel takes you
    to a port, which writes prices into the register, which is the whole of the
    lesson after next.
    """
    lesson = held(game)
    if lesson is None:
        return 0
    moved = 0
    while lesson.step < len(LESSONS) and already(game, LESSONS[lesson.step]):
        lesson.step += 1
        lesson.known += 1
        moved += 1
    if lesson.step >= len(LESSONS):
        lesson.over = True
    lesson.mark = mark_of(game)
    return moved


def begin(game) -> Tutorial:
    game.tutorial = Tutorial(mark=mark_of(game))
    _past_known(game)
    return game.tutorial


def skip(game) -> None:
    lesson = held(game)
    if lesson is not None:
        lesson.over = True
        lesson.skipped = True


def current(game):
    """The lesson being taught, or None."""
    lesson = held(game)
    if lesson is None or lesson.over or lesson.step >= len(LESSONS):
        return None
    return LESSONS[lesson.step]


def check(game) -> bool:
    """Has the current lesson been done? Called whenever the window refreshes.

    Returns True when something changed, so the caller knows to redraw.
    """
    lesson = held(game)
    if lesson is None or lesson.over or lesson.explaining:
        return False
    now = current(game)
    if now is None:
        lesson.over = True
        return True
    fn = WATCHERS.get(now.watch)
    if fn is None or not fn(game, lesson.mark or mark_of(game)):
        return False
    lesson.explaining = True
    return True


def acknowledge(game) -> bool:
    """The player has read the explanation; open the next lesson."""
    lesson = held(game)
    if lesson is None or lesson.over or not lesson.explaining:
        return False
    lesson.explaining = False
    lesson.step += 1
    lesson.mark = mark_of(game)
    if lesson.step >= len(LESSONS):
        lesson.over = True
        return True
    _past_known(game)
    return True


def jump_to(game, chapter_id: str) -> bool:
    """Start the tutorial at a course, or move a running one to it.

    What the Academy's "teach me this" button does. A captain who wants to
    learn one thing — how a crossing works, how a fight opens — should not
    have to walk twenty lessons to reach it, and a curriculum you can only
    take from the beginning is one most players abandon at lesson three.
    """
    if chapter_id not in CHAPTERS_BY_ID:
        return False
    lesson = held(game)
    if lesson is None or lesson.over:
        begin(game)
        lesson = held(game)
    lesson.step = first_step_of(chapter_id)
    lesson.over = False
    lesson.skipped = False
    lesson.explaining = False
    lesson.known = 0
    lesson.mark = mark_of(game)
    # And step over anything already earned at the new place, exactly as
    # opening the tutorial does — a course you can demonstrably already fly
    # should not be re-taught because you jumped to it.
    _past_known(game)
    return True


def progress(game) -> list[dict]:
    """The whole curriculum with what has been done, for the Academy page.

    One row per chapter: its lessons, and how many of them lie behind the
    step the captain has reached. A tutorial you cannot see the shape of is
    one you cannot choose your way around.
    """
    lesson = held(game)
    at = lesson.step if lesson is not None else 0
    done_all = bool(lesson is not None and lesson.over and not lesson.skipped)
    out = []
    for chapter in CHAPTERS:
        rows = lessons_in(chapter.id)
        first = first_step_of(chapter.id)
        done = len(rows) if done_all else max(
            0, min(len(rows), at - first))
        out.append({
            "chapter": chapter, "lessons": rows, "done": done,
            "of": len(rows), "here": bool(rows) and first <= at < first + len(rows),
        })
    return out


def state(game) -> dict:
    """Everything the bar needs, and nothing it has to work out."""
    lesson = held(game)
    if lesson is None or lesson.over:
        return {"running": False,
                "finished": bool(lesson and not lesson.skipped)}
    now = current(game)
    if now is None:
        return {"running": False, "finished": True}
    return {"running": True, "lesson": now, "step": lesson.step + 1,
            "of": len(LESSONS), "explaining": lesson.explaining,
            "text": now.then if lesson.explaining else now.ask,
            "screen": now.screen, "known": lesson.known}
