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
from ..data.lessons import LESSONS, LESSONS_BY_ID

WATCHERS = {}

#: Watchers of a different kind: *is this already true?* rather than *has it
#: happened since the step opened?*
#:
#: **The tutorial can be started from the Help screen at any time**, which is what
#: makes the distinction matter. `WATCHERS` all compare against a `mark` taken
#: when the step opened, so a captain who has surveyed thirty bodies and starts
#: the tutorial in year two is told to "survey one of the bodies here" and has to
#: go and survey another. Every step demanded a fresh action for something long
#: since learned. `Lesson.skip_if` was declared for this from the day lessons were
#: written, was set on **no lesson at all**, and was read by nothing.
#:
#: These take only the game: "already true" is not relative to anything.
SKIPS = {}


def watcher(name: str):
    def keep(fn):
        WATCHERS[name] = fn
        return fn
    return keep


def skipper(name: str):
    def keep(fn):
        SKIPS[name] = fn
        return fn
    return keep


# ── the mark: what the world looked like when this lesson opened ───────────

def mark_of(game) -> dict:
    """A snapshot of everything any watcher compares against."""
    return {
        "surveyed": sum(1 for s in game.galaxy.systems
                        for b in s.bodies if b.surveyed),
        "credits": round(game.credits),
        "volatiles": round(game.ship.cargo.get("volatiles", 0), 1),
        "cargo": round(sum(game.ship.cargo.values()), 1),
        "location": game.location_id,
        "orbit": game.orbit_body or "",
        "day": game.day,
        "contracts": len([c for c in game.contracts if c.accepted]),
        "register": len(game.register),
        "fitted": len(game.ship.fitted),
        "flown": round(float(getattr(game, "conn_seconds", 0.0)), 1),
        "seen": list(_seen(game)),
    }


def _seen(game) -> set:
    """Screens the player has opened since the tutorial began."""
    if getattr(game, "tutorial", None) is None:
        return set()
    return set(game.tutorial.seen)


def saw(game, screen: str) -> None:
    """Called by the window whenever a screen is opened."""
    lesson = held(game)
    if lesson is None or lesson.over:
        return
    if screen not in lesson.seen:
        lesson.seen.append(screen)


# ── watchers ───────────────────────────────────────────────────────────────

@watcher("surveyed_one")
def _surveyed(game, mark) -> bool:
    return sum(1 for s in game.galaxy.systems
               for b in s.bodies if b.surveyed) > mark["surveyed"]


@watcher("saw_market")
def _saw_market(game, mark) -> bool:
    # Opening a port writes its prices into the register, so this is state
    # rather than a claim about which button was pressed.
    return len(game.register) > mark["register"] or "port" in _seen(game)


@watcher("sold_something")
def _sold(game, mark) -> bool:
    return (round(game.credits) > mark["credits"]
            and round(sum(game.ship.cargo.values()), 1) < mark["cargo"])


@watcher("bought_fuel")
def _bought_fuel(game, mark) -> bool:
    return round(game.ship.cargo.get("volatiles", 0), 1) > mark["volatiles"]


@watcher("flew_conn")
def _flew_conn(game, mark) -> bool:
    # Five minutes at the conn since the lesson opened. `game.conn_seconds`
    # is bumped by `berthing.charge_flown` — the one door every flying
    # screen bills time through — so this is time genuinely flown, not a
    # screen merely opened. The counter is ephemeral (the `Conn` itself is
    # transient), which only means a reload mid-lesson starts the five
    # minutes over.
    return (float(getattr(game, "conn_seconds", 0.0))
            >= float(mark.get("flown", 0.0)) + 300.0)


@watcher("moved")
def _moved(game, mark) -> bool:
    return (game.location_id != mark["location"]
            or (game.orbit_body or "") != mark["orbit"])


@watcher("took_contract")
def _took_contract(game, mark) -> bool:
    return len([c for c in game.contracts if c.accepted]) > mark["contracts"]


@watcher("saw_plans")
def _saw_plans(game, mark) -> bool:
    return "ship:plans" in _seen(game)


@watcher("saw_diplomacy")
def _saw_diplomacy(game, mark) -> bool:
    return "diplomacy" in _seen(game)


# ── already true ───────────────────────────────────────────────────────────
#
# Four of the eight lessons, and **only four**, because the chronicle keeps
# *state* and these questions are about *history*. It records that a body is
# surveyed, that a port's prices are in the register, which systems have been
# visited and which contracts are accepted — so those four can be asked. It keeps
# no record that cargo was ever sold, that volatiles were ever bought rather than
# mined, or that the Ship and Diplomacy screens were ever opened, and inventing
# one to feed a tutorial would be the tail wagging the dog. Those four steps ask
# again, which for a step that takes one click is a fair price.

@skipper("have_surveyed")
def _have_surveyed(game) -> bool:
    return any(b.surveyed for s in game.galaxy.systems for b in s.bodies)


@skipper("have_prices")
def _have_prices(game) -> bool:
    """Prices written down somewhere. Standing in a market is what does it."""
    return bool(game.register)


@skipper("have_travelled")
def _have_travelled(game) -> bool:
    return len(game.discovered.get("systems", ())) > 1


@skipper("have_worked")
def _have_worked(game) -> bool:
    return any(c.accepted for c in game.contracts)


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
