"""Running the works a colony undertakes.

The colony module owns what a settlement *is*; this owns what it is becoming.
Everything the rest of the game asks about a colony — what it yields, what it
costs, what it can do — comes through the three combining functions here, so a
finished work is felt everywhere without anything else knowing works exist.
"""

from __future__ import annotations

from ..data.colonies import COLONIES_BY_ID
from ..data.works import ADMIN_STEP, MAX_WORKS, WORKS_BY_ID, WORKS
from . import loyalty


# ── what a colony is, once its works are counted ───────────────────────────

def done(col) -> list:
    return [WORKS_BY_ID[w] for w in getattr(col, "works", []) if w in WORKS_BY_ID]


def yields_of(col) -> dict:
    """Per-day production, with every finished work folded in."""
    out = dict(col.definition.yields)
    works = done(col)
    for work in works:
        for key, mul in work.yield_mul.items():
            if key in out:
                out[key] *= mul
    for work in works:
        for key, add in work.yield_add.items():
            out[key] = out.get(key, 0.0) + add
    return out


#: What one level of machine posted to a holding adds to its output.
#:
#: Measured against what a machine costs to have there. A Verger is level 3 and
#: 7,200 credits plus five silicon and four magnetite; on a RADIX Mine's 2.6 t
#: of ore a day it lifts production by 18%, which at the ore price pays the
#: build back in a little under two years and its own upkeep in about a month.
#: Slower than a trade run and it never sleeps, which is the shape a standing
#: asset should have.
YIELD_PER_LEVEL = 0.06


def hands_at(game, col) -> float:
    """Levels of machine posted to this holding and fit to work its plant.

    Through `sim/robots.working`, which is where the distance to whoever is
    supervising them is felt — so a teleoperated frame at a holding you have
    sailed away from contributes very nearly nothing, and this is the number
    that says so.
    """
    from . import robots
    return robots.working(game, col, "works")


def crewed_yields(game, col) -> dict:
    """**What this holding actually produces today**, machines included.

    The one door. `yields_of` is what the class and its works are worth on
    paper; nobody outside this module should be reading that when there is a
    game to hand, because a holding with three Vergers on it produces more
    than its card says and both the forecast and the tick must agree about
    how much.
    """
    lift = 1.0 + YIELD_PER_LEVEL * hands_at(game, col)
    return {key: amount * lift for key, amount in yields_of(col).items()}


def upkeep_of(col) -> dict:
    out = dict(col.definition.upkeep)
    for work in done(col):
        for key, add in work.upkeep_add.items():
            out[key] = out.get(key, 0.0) + add
    return out


def admin_total(held: int) -> float:
    """The daily administration bill for holding `held` colonies.

    Triangular rather than linear: each holding past the first makes every
    other one dearer to run, because what costs money is the traffic
    between them. One colony is free to administer; the twentieth is not.
    """
    held = max(0, int(held))
    return ADMIN_STEP * held * (held - 1) / 2


def admin_each(held: int) -> float:
    """One colony's share of that bill — what `colony.tick` charges."""
    return admin_total(held) / held if held > 0 else 0.0


def admin_next(held: int) -> float:
    """What planting one more would add to the bill, for the seed card."""
    return admin_total(held + 1) - admin_total(held)


def effects_of(col) -> dict:
    """Class effects plus work effects, added where they stack."""
    out = dict(col.definition.effects)
    for work in done(col):
        for key, value in work.effects.items():
            if isinstance(value, (int, float)) and isinstance(out.get(key), (int, float)):
                out[key] = out[key] + value
            else:
                out[key] = value
    return out


def pop_ceiling(col) -> float:
    ceiling = float(col.definition.pop)
    for work in done(col):
        ceiling *= work.pop_mul
    return ceiling


# ── choosing one ───────────────────────────────────────────────────────────

def _held(game, key: str) -> float:
    if key == "credits":
        return game.credits
    return game.stores.get(key, 0) + game.ship.cargo.get(key, 0)


def available(game, col) -> list[tuple]:
    """(work, ok, why) for everything this colony could be asked to do."""
    have = set(getattr(col, "works", []))
    family = col.definition.family
    produced = set(col.definition.yields)
    out = []
    for work in WORKS:
        ok, why = True, ""
        if work.id in have:
            continue
        if work.families and family not in work.families:
            continue
        if work.needs_yield and not (produced & set(work.needs_yield)):
            continue
        if not col.online:
            ok, why = False, "Still gestating."
        elif len(have) >= MAX_WORKS:
            ok, why = False, f"A colony holds at most {MAX_WORKS} works."
        elif getattr(col, "job", None):
            ok, why = False, "Something is already under way here."
        elif work.tech and work.tech not in game.research.unlocked:
            ok, why = False, "The research is not in hand."
        else:
            short = [f"{round(n)} {k}" for k, n in work.cost.items()
                     if _held(game, k) < n]
            if short:
                ok, why = False, "Short of " + ", ".join(short) + "."
        out.append((work, ok, why))
    return out


def _spend(game, cost: dict) -> None:
    for key, n in cost.items():
        if key == "credits":
            game.credits -= n
            continue
        from_ship = min(game.ship.cargo.get(key, 0), n)
        if from_ship:
            game.ship.cargo[key] = game.ship.cargo.get(key, 0) - from_ship
            if game.ship.cargo[key] <= 0.0001:
                game.ship.cargo.pop(key, None)
        rest = n - from_ship
        if rest > 0:
            game.stores[key] = max(0.0, game.stores.get(key, 0) - rest)


def begin(game, col, work_id: str) -> dict:
    """Commit a colony to a work. Materials are spent up front."""
    work = WORKS_BY_ID.get(work_id)
    if work is None:
        return {"ok": False, "why": "No such work."}
    ok, why = next(((o, w) for x, o, w in available(game, col) if x.id == work_id),
                   (False, "Not offered here."))
    if not ok:
        return {"ok": False, "why": why}
    _spend(game, work.cost)
    col.job = work.id
    col.job_days = 0.0
    game.add_log(f"{col.name}: {work.name.lower()} begun.", "good")
    return {"ok": True, "work": work}


def cancel(game, col) -> bool:
    """Abandon the work under way. The material is gone."""
    if not getattr(col, "job", None):
        return False
    work = WORKS_BY_ID.get(col.job)
    col.job = None
    col.job_days = 0.0
    if work:
        game.add_log(f"{col.name}: {work.name.lower()} abandoned.", "warn")
    return True


# ── the clock ──────────────────────────────────────────────────────────────

def advance(game, col, days: float) -> list[tuple[str, str]]:
    """Push the colony's work along. Returns log events."""
    job = getattr(col, "job", None)
    if not job or not col.online:
        return []
    work = WORKS_BY_ID.get(job)
    if work is None:
        col.job = None
        return []
    col.job_days = getattr(col, "job_days", 0.0) + days
    if col.job_days < work.days:
        return []
    col.works.append(work.id)
    col.job = None
    col.job_days = 0.0
    loyalty.record(game, "work_done")
    if work.effects.get("port"):
        loyalty.record(game, "harbour")
    return [("good", f"{col.name}: {work.name.lower()} complete.")]


def progress(col) -> float:
    work = WORKS_BY_ID.get(getattr(col, "job", None) or "")
    if work is None or not work.days:
        return 0.0
    return min(1.0, getattr(col, "job_days", 0.0) / work.days)
