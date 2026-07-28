"""Who is asleep, what it saves them, and what it costs to wake them up.

The time system priced a crossing in people and offered one answer: fly harder
and pay in reaction mass. This is the other answer, and the two do not stack
into a free lunch — both cost you the ship's own work, so doing both costs it
twice, and only this one can fail to give somebody back.

Three rules hold the design together:

- **Somebody stays awake.** `MIN_WATCH` of the complement, always. The watch
  ages at the full rate and eats full rations, so a long crossing is always
  paid for by somebody.
- **The saving is on proper time.** Sleepers age and eat at their method's
  share of what an awake crew does — folded into `lifespan` and `upkeep`
  rather than special-cased, so it cannot drift away from them.
- **Waking is where it costs.** Risk is rolled once, on waking, against the
  days actually spent under. Sleeping a crew and never waking them buys
  nothing: `ship_day` is what the sim runs on, and the roll is waiting.

`game.sleep` is a plain record rather than something with an `.over` flag,
because it is a *state* rather than something you are part-way through — you
can fly, fight and trade with half the crew under. Waking is the event.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.dormancy import (METHODS, METHODS_BY_ID, MIN_WATCH, NOTICEABLE,
                             work_share)
from ..data.lineages import LINEAGES_BY_ID, of_stock
from .lifespan import active, lineage_of


@register
@dataclass
class Sleep:
    """Who went under, how, and when."""
    method: str
    since: int = 0
    #: Hands (the headcount) asleep, and officer ids asleep.
    hands: int = 0
    officers: list = field(default_factory=list)
    log: list = field(default_factory=list)

    @property
    def how(self):
        return METHODS_BY_ID.get(self.method)


def current(game):
    """The sleep in progress, or None."""
    got = getattr(game, "sleep", None)
    return got if got is not None and (got.hands or got.officers) else None


def crew_lineage(game) -> str:
    return of_stock(getattr(getattr(game, "beginning", None), "stock", None))


def suits(game, method) -> bool:
    """Can this hull's people use this method at all?"""
    if not method.lineages:
        return True
    aboard = {crew_lineage(game)}
    aboard |= {lineage_of(o, game).id for o in active(game.officers)}
    return bool(aboard & set(method.lineages))


def available(game) -> list:
    """(method, ok, why) for every way of putting the crew under."""
    out = []
    for method in METHODS:
        ok, why = True, ""
        if method.needs_tech and method.needs_tech not in game.research.unlocked:
            ok, why = False, f"Needs {method.needs_tech}."
        elif not suits(game, method):
            names = ", ".join(LINEAGES_BY_ID[x].name for x in method.lineages
                              if x in LINEAGES_BY_ID)
            ok, why = False, f"Only a {names} crew can."
        out.append((method, ok, why))
    return out


def complement(game) -> int:
    """Everyone aboard: hands and officers together."""
    return max(0, int(getattr(game.ship, "crew", 0))) + len(
        active(game.officers))


def most_that_can_sleep(game) -> int:
    """How many may go under, leaving a watch on the hull."""
    total = complement(game)
    return max(0, total - max(1, round(total * MIN_WATCH)))


def asleep(game) -> int:
    sleep = current(game)
    return (sleep.hands + len(sleep.officers)) if sleep else 0


def awake_share(game) -> float:
    """Fraction of the complement standing a watch. 1.0 when nobody sleeps."""
    total = complement(game)
    if total <= 0:
        return 1.0
    return max(0.0, min(1.0, (total - asleep(game)) / total))


def ship_work(game) -> float:
    """What share of the bench, workshop and smelter is actually manned."""
    return work_share(awake_share(game))


def is_asleep(game, officer) -> bool:
    sleep = current(game)
    return bool(sleep and officer.id in sleep.officers)


def rates(game, officer=None) -> tuple[float, float]:
    """Ageing and upkeep multipliers for somebody aboard right now.

    `officer` None means one of the hands. This is the one place the saving
    is expressed, and `lifespan` and `upkeep` both read it.
    """
    sleep = current(game)
    if sleep is None:
        return 1.0, 1.0
    method = sleep.how
    if method is None:
        return 1.0, 1.0
    if officer is None:
        # Hands sleep as a block: the share of them under is the share saved.
        total = max(1, int(getattr(game.ship, "crew", 0)))
        under = min(sleep.hands, total) / total
        return (1.0 - under + under * method.ageing,
                1.0 - under + under * method.upkeep)
    if officer.id in sleep.officers:
        return method.ageing, method.upkeep
    return 1.0, 1.0


def preview(game, method_id: str, count: int, days: float) -> dict:
    """What putting `count` people under for `days` will cost and save."""
    method = METHODS_BY_ID.get(method_id)
    if method is None:
        return {}
    total = max(1, complement(game))
    count = max(0, min(count, most_that_can_sleep(game)))
    awake = (total - count) / total
    out = {"method": method, "count": count, "days": days,
           "awake": awake, "work": work_share(awake),
           "cost": {}, "risk": 0.0, "lines": []}
    for cid, per in method.cost.items():
        out["cost"][cid] = per * count * days / 100.0
    out["risk"] = 1.0 - (1.0 - method.risk / 100.0) ** (days / 100.0)

    lineage = LINEAGES_BY_ID[crew_lineage(game)]
    saved_years = (days / 365.0) * lineage.ageing * (1 - method.ageing)
    if saved_years >= 0.08:
        out["lines"].append(
            f"{count} under saves each of them "
            + (f"{saved_years:.1f} years" if saved_years >= 1
               else f"{saved_years * 12:.0f} months") + " of their span.")
    if out["cost"]:
        bill = ", ".join(f"{v:.1f} t {k}" for k, v in out["cost"].items())
        out["lines"].append(f"Costs {bill} over the crossing.")
    if method.risk:
        expected = out["risk"] * count
        out["lines"].append(
            f"About {out['risk'] * 100:.1f}% of them do not come back up — "
            f"{expected:.1f} of {count}, on average.")
    if method.atrophy:
        out["lines"].append(
            f"Those who do lose {method.atrophy * days / 365:.2f} of a level "
            "to the cold.")
    out["lines"].append(
        f"The hull runs at {out['work'] * 100:.0f}% — research, repairs and "
        "refining all slow to what the watch can manage.")
    return out


def put_under(game, method_id: str, count: int) -> dict:
    """Send `count` of the complement to sleep, drawn proportionally."""
    method = METHODS_BY_ID.get(method_id)
    if method is None or method.id == "watch":
        return {"ok": False, "why": "That is not a way of sleeping."}
    ok, why = next(((o, w) for m, o, w in available(game)
                    if m.id == method_id), (False, "Not available."))
    if not ok:
        return {"ok": False, "why": why}
    if current(game) is not None:
        return {"ok": False, "why": "Somebody is already under."}
    room = most_that_can_sleep(game)
    if room <= 0:
        return {"ok": False, "why": "There are too few aboard to spare any."}
    count = max(1, min(count, room))

    # Proportionally, not hands-first. Sleeping the hands and keeping every
    # officer awake meant nobody with an *age* ever went under — and ageing is
    # the entire reason to do this. Officers carry the lifespans; if they never
    # sleep, the headline saving is unmeasurable and unreal.
    #
    # At least one officer stays up regardless: a watch with nobody on the
    # bridge is not a watch.
    crew_now = int(getattr(game.ship, "crew", 0))
    total = max(1, crew_now + len(active(game.officers)))
    share = count / total
    officers_up = active(game.officers)
    sleeping_officers = min(len(officers_up) - 1 if len(officers_up) > 1 else 0,
                            int(round(len(officers_up) * share)))
    officers = [o.id for o in officers_up[:max(0, sleeping_officers)]]
    hands = min(count - len(officers), crew_now)
    game.sleep = Sleep(method=method_id, since=game.ship_day,
                       hands=hands, officers=officers)
    game.add_log(f"{count} of the complement are under — {method.name.lower()}.",
                 "")
    return {"ok": True, "count": count, "method": method}


def tick(game, ship_days: float, rng) -> list:
    """Charge what sleeping costs to run. Returns lines for the log."""
    sleep = current(game)
    if sleep is None or ship_days <= 0:
        return []
    method = sleep.how
    if method is None or not method.cost:
        return []
    from .ship import add_cargo
    out = []
    count = sleep.hands + len(sleep.officers)
    for cid, per in method.cost.items():
        need = per * count * ship_days / 100.0
        held = game.ship.cargo.get(cid, 0) + game.stores.get(cid, 0)
        if held < need:
            # The medium ran out. They come up early, which is better than the
            # alternative and worse than planned.
            out.append(("bad", f"The {cid} for the sleepers has run out. They "
                               "are being brought up early."))
            out.extend(wake(game, rng, early=True)[1])
            return out
        taken = min(need, game.ship.cargo.get(cid, 0))
        add_cargo(game.ship, cid, -taken)
        if taken < need:
            game.stores[cid] = max(0.0, game.stores.get(cid, 0) - (need - taken))
    return out


def wake(game, rng, early: bool = False) -> tuple[dict, list]:
    """Bring them up, and find out who came. Rolls the risk once."""
    sleep = current(game)
    if sleep is None:
        return {"ok": False, "why": "Nobody is under."}, []
    method = sleep.how
    if method is None:
        game.sleep = None
        return {"ok": False, "why": "Nobody is under."}, []

    days = max(0, game.ship_day - sleep.since)
    odds = 1.0 - (1.0 - method.risk / 100.0) ** (days / 100.0)
    lines, lost_hands, lost_officers = [], 0, []

    for _ in range(sleep.hands):
        if odds > 0 and rng.chance(odds):
            lost_hands += 1
    for oid in list(sleep.officers):
        if odds > 0 and rng.chance(odds):
            lost_officers.append(oid)

    game.ship.crew = max(0, game.ship.crew - lost_hands)
    for officer in game.officers:
        if officer.id in lost_officers:
            officer.retired = True
            lines.append(("bad", f"{officer.name} did not come up."))

    # Atrophy, on everybody who did wake.
    shed = method.atrophy * days / 365.0
    if shed > 0.005:
        for officer in active(game.officers):
            if officer.id in sleep.officers and officer.id not in lost_officers:
                officer.wear = getattr(officer, "wear", 0.0) + shed
                if officer.wear >= 1.0 and officer.level > 1:
                    officer.level -= 1
                    officer.wear -= 1.0
                    lines.append(("warn", f"{officer.name} came up a step "
                                          "slower than they went down."))

    if lost_hands:
        lines.append(("bad", f"{lost_hands} of the crew did not come up."))
    if days >= NOTICEABLE and not lines:
        lines.append(("good", f"All hands up after {days} days under. "
                              "Nobody was lost."))
    game.sleep = None
    game.recompute()
    return ({"ok": True, "days": days, "lost": lost_hands + len(lost_officers),
             "early": early}, lines)


def note(game) -> str:
    """One line for a screen: who is under and for how long."""
    sleep = current(game)
    if sleep is None:
        return "Everyone aboard is awake."
    method = sleep.how
    days = max(0, game.ship_day - sleep.since)
    count = sleep.hands + len(sleep.officers)
    return (f"{count} under — {method.name.lower() if method else 'asleep'}, "
            f"{days} days so far. The hull runs at "
            f"{ship_work(game) * 100:.0f}%.")
