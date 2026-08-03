"""What the tutorial watches: the mark, the watchers, and the deeds.

Split from `sim/tutorial.py`, which keeps the state machine. The seam is the
one that was already there: this decides **whether a thing has happened**,
that decides **which thing to ask for next**.

A watcher is a function of game state against a *mark* — a snapshot taken
when the lesson opened — so "survey a body" means one more than you had
rather than "a body is surveyed". That is the whole reason the tutorial
cannot be fooled by a chronicle that had already done the thing.

**Some deeds leave no state behind**, and for those the sim records that they
happened. Flying under the computer, standing a watch, working a seam, a
trench, a landing, opening fire: each leaves nothing on the `Game` that could
be asked about afterwards — the flight is transient, the crossing is over,
the battle belongs to the window. `deed` writes one flag from the sim
function that actually performs the act, which is honest in a way that
watching a screen open is not: it is set by the doing.
"""

from __future__ import annotations

WATCHERS: dict = {}
SKIPS: dict = {}


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


def deed(game, key: str) -> None:
    """Record that something with no lasting state was actually done.

    Called from the sim function that performs the act — never from a
    screen, so pressing a button that refuses still records nothing.
    """
    flags = getattr(game, "flags", None)
    if flags is not None:
        flags[key] = True


def did(game, key: str) -> bool:
    return bool(getattr(game, "flags", {}).get(key))


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
        "colonies": len(getattr(game, "colonies", ())),
        "unlocked": len(getattr(game.research, "unlocked", ())),
        "systems": len(game.discovered.get("systems", ())),
        "standing": _best_standing(game),
        "docked": _docked(game),
        "deeds": sorted(k for k, v in getattr(game, "flags", {}).items()
                        if v is True),
        "seen": list(_seen(game)),
    }


def _docked(game) -> bool:
    from . import anchorage as anchorage_sim
    return anchorage_sim.docked_at(game) is not None


def _best_standing(game) -> float:
    """The warmest any power feels about you. Enough to see a gift land."""
    rep = getattr(game, "rep", None) or {}
    return round(max(rep.values()), 2) if rep else 0.0


def _seen(game) -> set:
    """Screens the player has opened since the tutorial began."""
    if getattr(game, "tutorial", None) is None:
        return set()
    return set(game.tutorial.seen)


def _fresh_deed(game, mark, key: str) -> bool:
    """A deed done *since this lesson opened*, not one done years ago."""
    return did(game, key) and key not in set(mark.get("deeds", ()))


# ── watchers: finding your way ─────────────────────────────────────────────

@watcher("saw_map")
def _saw_map(game, mark) -> bool:
    return "map" in _seen(game)


@watcher("saw_ship")
def _saw_ship(game, mark) -> bool:
    return "ship" in _seen(game)


@watcher("saw_manual")
def _saw_manual(game, mark) -> bool:
    return "help" in _seen(game)


@watcher("saw_empire")
def _saw_empire(game, mark) -> bool:
    return "empire" in _seen(game)


@watcher("saw_yard")
def _saw_yard(game, mark) -> bool:
    return "yard" in _seen(game)


@watcher("saw_codex")
def _saw_codex(game, mark) -> bool:
    return "codex" in _seen(game)


@watcher("saw_plans")
def _saw_plans(game, mark) -> bool:
    return "ship:plans" in _seen(game)


@watcher("saw_diplomacy")
def _saw_diplomacy(game, mark) -> bool:
    return "diplomacy" in _seen(game)


@watcher("saw_market")
def _saw_market(game, mark) -> bool:
    # Opening a port writes its prices into the register, so this is state
    # rather than a claim about which button was pressed.
    return len(game.register) > mark["register"] or "port" in _seen(game)


# ── watchers: flying ───────────────────────────────────────────────────────

@watcher("flew_conn")
def _flew_conn(game, mark) -> bool:
    # Five minutes at the conn since the lesson opened. `game.conn_seconds`
    # is bumped by `berthing.charge_flown` — the one door every flying screen
    # bills time through — so this is time genuinely flown, not a screen
    # merely opened.
    return (float(getattr(game, "conn_seconds", 0.0))
            >= float(mark.get("flown", 0.0)) + 300.0)


@watcher("computer_flew")
def _computer_flew(game, mark) -> bool:
    return _fresh_deed(game, mark, "computer_flew")


@watcher("took_the_guard_off")
def _took_the_guard_off(game, mark) -> bool:
    """Touched the safeties switch since the lesson opened.

    The flag is written by `collision.toggle_safeties`, which is the only
    thing that flips it — so this is the switch genuinely thrown, not a
    screen opened or a button that refused.
    """
    return _fresh_deed(game, mark, "safeties")


@watcher("berthed")
def _berthed(game, mark) -> bool:
    """Come alongside *since the lesson opened*.

    Derived from where she is standing, so a save reloaded still counts —
    and measured against the mark, so a captain who was already at a quay
    when the lesson opened is asked to do it rather than waved through.
    """
    return _docked(game) and not mark.get("docked", False)


# ── watchers: money and science ────────────────────────────────────────────

@watcher("sold_something")
def _sold(game, mark) -> bool:
    return (round(game.credits) > mark["credits"]
            and round(sum(game.ship.cargo.values()), 1) < mark["cargo"])


@watcher("bought_fuel")
def _bought_fuel(game, mark) -> bool:
    return round(game.ship.cargo.get("volatiles", 0), 1) > mark["volatiles"]


@watcher("surveyed_one")
def _surveyed(game, mark) -> bool:
    return sum(1 for s in game.galaxy.systems
               for b in s.bodies if b.surveyed) > mark["surveyed"]


@watcher("set_project")
def _set_project(game, mark) -> bool:
    return bool(getattr(game.research, "current", None))


@watcher("unlocked_tech")
def _unlocked(game, mark) -> bool:
    return len(getattr(game.research, "unlocked", ())) > mark["unlocked"]


# ── watchers: distance ─────────────────────────────────────────────────────

@watcher("moved")
def _moved(game, mark) -> bool:
    return (game.location_id != mark["location"]
            or (game.orbit_body or "") != mark["orbit"])


@watcher("stood_watch")
def _stood_watch(game, mark) -> bool:
    return _fresh_deed(game, mark, "stood_watch")


@watcher("jumped")
def _jumped(game, mark) -> bool:
    return len(game.discovered.get("systems", ())) > mark["systems"]


# ── watchers: working a system ─────────────────────────────────────────────

@watcher("mined")
def _mined(game, mark) -> bool:
    return _fresh_deed(game, mark, "mined")


@watcher("dug")
def _dug(game, mark) -> bool:
    return _fresh_deed(game, mark, "dug")


@watcher("landed")
def _landed(game, mark) -> bool:
    return _fresh_deed(game, mark, "landed")


# ── watchers: iron, roots, powers, career ──────────────────────────────────

@watcher("marked_hostile")
def _marked_hostile(game, mark) -> bool:
    from . import hostiles as hostiles_sim
    return bool(hostiles_sim.marked(game))


@watcher("fought")
def _fought(game, mark) -> bool:
    return _fresh_deed(game, mark, "fought")


@watcher("planted")
def _planted(game, mark) -> bool:
    return len(getattr(game, "colonies", ())) > mark["colonies"]


@watcher("courted")
def _courted(game, mark) -> bool:
    return _best_standing(game) > mark["standing"] + 0.5


@watcher("refitted")
def _refitted(game, mark) -> bool:
    return len(game.ship.fitted) != mark["fitted"]


@watcher("took_contract")
def _took_contract(game, mark) -> bool:
    return len([c for c in game.contracts if c.accepted]) > mark["contracts"]


# ── already true ───────────────────────────────────────────────────────────
#
# A skipper answers "has this captain demonstrably done this before?", and it
# is only consulted once a chronicle is old enough to trust — see
# `tutorial.SETTLED_IN_DAYS`. Not every lesson has one, because the chronicle
# keeps *state* and some of these questions are about *history*: it records
# that a body is surveyed and which systems have been visited, and keeps no
# record that cargo was ever sold. Those steps ask again, which for a step
# that takes one click is a fair price.

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


@skipper("have_played")
def _have_played(game) -> bool:
    """A career behind them: prices noted, ground surveyed, stars crossed.

    What lets a veteran restarting the tutorial past "open the Sector
    chart". Deliberately all three together — any one of them alone can be
    true of a captain on their first afternoon.
    """
    return (bool(game.register)
            and any(b.surveyed for s in game.galaxy.systems for b in s.bodies)
            and len(game.discovered.get("systems", ())) > 1)


@skipper("have_guarded")
def _have_guarded(game) -> bool:
    """Already thrown the safeties switch, ever.

    Without this the lesson would be a trap: `_fresh_deed` wants the deed
    done *since the lesson opened*, and the flag is never cleared, so a
    captain who had touched the switch before reaching this lesson could
    never satisfy it however many times they pressed it.
    """
    return did(game, "safeties")


@skipper("have_berthed")
def _have_berthed(game) -> bool:
    from . import anchorage as anchorage_sim
    return anchorage_sim.docked_at(game) is not None
