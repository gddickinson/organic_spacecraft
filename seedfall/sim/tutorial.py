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


def watcher(name: str):
    def keep(fn):
        WATCHERS[name] = fn
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


def held(game):
    return getattr(game, "tutorial", None)


def running(game) -> bool:
    lesson = held(game)
    return lesson is not None and not lesson.over


def begin(game) -> Tutorial:
    game.tutorial = Tutorial(mark=mark_of(game))
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
            "screen": now.screen}
