"""What a concourse does to a person: mends, keeps, teaches, and changes.

The counter for `data/treatments.py`, in the same shape as `sim/shore.py` is
the counter for `data/kit.py` — and deliberately so, because they are the
same transaction with a different noun. A place either has a door that does
this kind of work (`venue.offers`), the machine for it (`tech`) and the
tolerance for it (`law`), or it does not.

Three rules run through all of it.

**The price quoted is the price charged.** `quote` says the money, the days,
the odds and exactly what it will do, and `buy` performs that and nothing
else. This project's oldest rule, pointed at a body.

**Nothing here is derived.** A service record is a reading of a saved
officer and may be recomputed at will; a fitted cortex link is a *fact*, and
facts are saved. `game.fitted` and `game.taught` hold them, keyed by the
officer's id as a string, and `sim/lifepath.of` folds both onto the record it
derives — so the good numbers show up in every check the ship makes without
any other module knowing this file exists.

**The good work charges something that is not money.** Every point of
`strain` is loyalty off the person who took it: the Verge is four cultures
and not one of them is relaxed about a crew that is partly machinery. That is
the whole cyberpunk bargain, stated as a subtraction.
"""

from __future__ import annotations

from ..data import treatments as table
from . import checks
from . import loyalty as loyalty_sim
from . import places as places_sim
from . import shore

#: Which treatment kinds a place must have a door for. One to one with the
#: `offers` tags, which is what makes a back room and a hospital the same
#: code path at different prices.
KINDS = tuple(sorted({t.kind for t in table.TREATMENTS}))

#: What a year in a cold berth costs, as a share of what going in cost. A
#: rack does not run itself, and somebody has to be paid to watch it.
ICE_PER_YEAR = 0.18

#: How long a person may be left on ice before the game stops pretending
#: anybody is still paying attention to the ledger.
ICE_LONGEST_YEARS = 60.0

#: A course of anagathics is a *standing arrangement*, not a purchase. It
#: takes years off on the day, and then it goes on costing every month for
#: as long as you want it to keep working — which is Traveller's own model
#: and the first recurring bill in the Verge that follows the ship.
COURSE_MONTH = 30.0
COURSE_SHARE = 0.05

#: What a paid-up course does: the person ages at this share of their
#: lineage's rate. Read by `sim/lifespan.tick`, which is the one clock that
#: moves an age — so the money and the years cannot drift apart.
COURSE_SLOW = 0.45


# ── what is on offer ───────────────────────────────────────────────────────

def doors(game, at, kind: str = "") -> list:
    """Every door here that does this sort of work."""
    if kind:
        return shore.selling(game, at, kind)
    out = []
    for got in KINDS:
        out.extend(shore.selling(game, at, got))
    return sorted(set(out), key=lambda v: (-v.cr, v.name))


def offered(game, at, kind: str = "") -> list:
    """Every treatment that can actually be had here, dearest first.

    Three gates, and a door for each: somebody has to do this sort of work,
    the place has to be advanced enough for the machine, and the law has to
    let them admit to it — except that an unlicensed clinic is *itself* gated
    on a low law level, so the two meet and a chop shop carries what a
    hospital will not.
    """
    place = shore._where(game, at)
    if place is None or not places_sim.livable(place):
        return []
    have = {v_kind for v_kind in KINDS if shore.selling(game, place, v_kind)}
    rows = []
    for got in table.TREATMENTS:
        if kind and got.kind != kind:
            continue
        if got.kind not in have:
            continue
        if not table.done_at(got, place.tech):
            continue
        licensed = table.legal_at(got, place.law)
        if not licensed and not _unlicensed(game, place, got.kind):
            continue
        rows.append({"treatment": got,
                     "cr": table.price_at(got, place.tech),
                     "licensed": licensed})
    return sorted(rows, key=lambda r: (r["treatment"].kind, -r["cr"]))


def _unlicensed(game, place, kind: str) -> bool:
    """Whether anybody here does this sort of work without a licence."""
    return any(v.kind == "vice" for v in shore.selling(game, place, kind))


# ── what one would do ──────────────────────────────────────────────────────

def fitted_to(game, officer) -> list:
    """What is in somebody, as treatments."""
    held = (getattr(game, "fitted", None) or {}).get(_key(officer), [])
    return [table.TREATMENT_BY_ID[i] for i in held
            if i in table.TREATMENT_BY_ID]


def taught_to(game, officer) -> dict:
    """What somebody has been taught since they signed on."""
    return dict((getattr(game, "taught", None) or {}).get(_key(officer), {}))


def strain_of(game, officer) -> float:
    """How much of them is not them any more."""
    return sum(t.strain for t in fitted_to(game, officer))


def _key(officer) -> str:
    return str(getattr(officer, "id", 0))


def quote(game, at, officer, treatment_id: str, skill: str = "") -> dict:
    """Everything about one piece of work, before anybody agrees to it."""
    place = shore._where(game, at)
    got = table.TREATMENT_BY_ID.get(treatment_id)
    if place is None or got is None:
        return {"ok": False, "why": "Nobody here does that."}
    row = next((r for r in offered(game, place, got.kind)
                if r["treatment"].id == treatment_id), None)
    if row is None:
        return {"ok": False, "why": "Nobody here does that."}
    cost = row["cr"]
    said = _does(game, got, officer, skill)
    why = shore.barred(game, place)
    if why:
        pass                   # aboard, not across: said first (`crossing`)
    elif got.kind == "train" and not skill:
        why = "Choose what they are to be taught."
    elif treatment_id in (getattr(game, "fitted", None) or {}).get(
            _key(officer), []):
        why = f"{officer.name} already has one."
    elif game.credits < cost:
        why = (f"{cost:,} credits, and the treasury holds "
               f"{int(game.credits):,}.")
    odds = 1.0 if not got.risk else checks.chance(
        _skill_here(game, place), _score(game, officer), got.risk)
    return {"ok": not why, "why": why, "cr": cost, "days": got.days,
            "treatment": got, "does": said, "odds": odds,
            "licensed": row["licensed"], "place": place, "skill": skill}


def _does(game, got, officer, skill: str) -> list:
    """What it will do, in the words the screen prints before the button."""
    said = []
    for cid, delta in sorted(got.gives.items()):
        said.append(f"{cid.upper()} {delta:+d}")
    if got.skill:
        said.append(f"{got.skill.replace('_', ' ').title()} taught")
    if skill:
        said.append(f"{skill.replace('_', ' ').title()} +1")
    if got.heals:
        said.append(f"{got.heals:.2g} of the wear cleared")
    kept = (getattr(game, "wounds", None) or {}).get(_key(officer))
    if got.kind == "care" and kept:
        said.append(f"the wound from the last walk closed ({kept:g})")
    if got.restores:
        said.append(f"{got.restores} level(s) back")
    if got.years:
        said.append(f"{got.years:.0f} years off {officer.name.split()[0]}'s "
                    "age")
    if got.strain:
        said.append(f"strain {got.strain:.1g} — "
                    f"{got.strain * table.STRAIN_LOYALTY:.0f} loyalty")
    return said


def _skill_here(game, place) -> int:
    """How good the people doing it are. A better place has better hands."""
    return max(checks.UNTRAINED, place.amenity - 2)


def _score(game, officer) -> int:
    """What the patient brings to it: their own endurance."""
    from . import lifepath
    return lifepath.of(game, officer).score("end")


# ── doing it ───────────────────────────────────────────────────────────────

def buy(game, at, officer, treatment_id: str, skill: str = "",
        rng=None) -> dict:
    """Have the work done. Money out, days off the calendar, person changed.

    The draw is the sim's, like every other act — a screen may not move the
    chronicle's luck (`tests/test_uirules`), and this can fail.
    """
    said = quote(game, at, officer, treatment_id, skill)
    if not said["ok"]:
        return {"ok": False, "why": said["why"]}
    got, cost = said["treatment"], said["cr"]
    rng = rng if rng is not None else game.rng("clinic")
    game.credits -= cost
    place = said["place"]
    check = None
    if got.risk:
        check = checks.roll(rng, _skill_here(game, place),
                            _score(game, officer), got.risk,
                            about=officer.name, what=got.name)
    if check is not None and not check.ok:
        _mishap(game, officer, got)
        game.add_log(f"{got.name} for {officer.name}, at {place.name}: it "
                     f"went wrong. {got.mishap}", "bad")
        game.advance_days(got.days)
        return {"ok": True, "went": False, "why": "", "cr": cost,
                "days": got.days, "text": got.mishap, "check": check}
    _apply(game, officer, got, skill)
    lines = ", ".join(said["does"]) or "nothing anybody can point at"
    game.add_log(f"{got.name} for {officer.name}, at {place.name}: "
                 f"{cost:,} credits. {lines}.", "good")
    game.advance_days(got.days)
    return {"ok": True, "went": True, "why": "", "cr": cost,
            "days": got.days, "text": lines, "check": check}


def _apply(game, officer, got, skill: str) -> None:
    """The whole of what a successful treatment changes."""
    if got.heals:
        officer.wear = max(0.0, getattr(officer, "wear", 0.0) - got.heals)
    if got.kind == "care":
        # Care closes a wound kept from a walk (`sim/afoot`), whatever else
        # it does: that is most of what a check-up is for.
        (getattr(game, "wounds", None) or {}).pop(_key(officer), None)
    if got.restores:
        officer.level = int(getattr(officer, "level", 1)) + got.restores
    if got.years:
        from . import lifespan
        was = lifespan.age_of(officer, game)
        officer.age = max(18.0, was - got.years)
    if got.strain:
        loyalty_sim.shift(officer, -got.strain * table.STRAIN_LOYALTY)
    # Anagathics are an arrangement, not a purchase: the years come off on
    # the day and the clinic bills every month after it.
    if got.kind == "years":
        start_course(game, officer, got)
    # What stays in them. `lifepath.of` folds these onto the record it
    # derives, which is how a fitted weave reaches every check the ship makes.
    if got.gives or got.skill:
        held = dict(getattr(game, "fitted", None) or {})
        mine = list(held.get(_key(officer), []))
        if got.id not in mine:
            mine.append(got.id)
        held[_key(officer)] = mine
        game.fitted = held
    if skill:
        learned = dict(getattr(game, "taught", None) or {})
        mine = dict(learned.get(_key(officer), {}))
        mine[skill] = mine.get(skill, 0) + 1
        learned[_key(officer)] = mine
        game.taught = learned


def _mishap(game, officer, got) -> None:
    """What a failed treatment costs. Always something, never everything."""
    officer.wear = getattr(officer, "wear", 0.0) + 0.5
    loyalty_sim.shift(officer, -4.0)


# ── cold storage ───────────────────────────────────────────────────────────

# ── standing courses ───────────────────────────────────────────────────────

def courses(game) -> list:
    """Every standing arrangement with a clinic."""
    return list(getattr(game, "courses", None) or [])


def course_of(game, officer):
    """The course this person is on, if any."""
    key = _key(officer)
    return next((c for c in courses(game) if c.get("who") == key), None)


def slows(game, officer) -> float:
    """How fast this person ages: `1.0` unless somebody is paying.

    Called by `sim/lifespan.tick`, which is the only thing in the game that
    moves an age. A course that had its own ageing model would be a second
    clock, and two clocks disagree.
    """
    got = course_of(game, officer)
    if got is None or not got.get("paid", True):
        return 1.0
    return COURSE_SLOW


def month_cost(game) -> float:
    """What the standing arrangements cost every month, all in."""
    out = 0.0
    for row in courses(game):
        got = table.TREATMENT_BY_ID.get(row.get("how", ""))
        if got is not None:
            out += got.cr * COURSE_SHARE
    return out


def tick(game, days: float) -> list:
    """Charge the standing bills. Returns `(kind, text)` lines for the log.

    Called once a day from `core/shiptime`, beside the crew's own upkeep,
    because that is what it is: a running cost of having people aboard who
    are not dying on schedule.
    """
    if days <= 0 or not courses(game):
        return []
    said, day = [], float(getattr(game, "day", 0.0))
    rows, kept = courses(game), []
    for row in rows:
        got = table.TREATMENT_BY_ID.get(row.get("how", ""))
        if got is None:
            continue
        due = float(row.get("paid_to", day))
        while day - due >= COURSE_MONTH:
            cost = got.cr * COURSE_SHARE
            if game.credits < cost:
                row["paid"] = False
                said.append(("warn", f"The clinic has stopped {row['name']}'s "
                                     f"course: {cost:,.0f} credits a month "
                                     "and the treasury could not find it."))
                due = day
                break
            game.credits -= cost
            due += COURSE_MONTH
            row["paid"] = True
        row["paid_to"] = due
        if row.get("paid", True):
            kept.append(row)
    game.courses = kept
    return said


def start_course(game, officer, treatment) -> None:
    """Put somebody on a standing arrangement, or renew the one they have."""
    day = float(getattr(game, "day", 0.0))
    rows = [c for c in courses(game) if c.get("who") != _key(officer)]
    rows.append({"who": _key(officer), "name": getattr(officer, "name", ""),
                 "how": treatment.id, "since": day, "paid_to": day,
                 "paid": True})
    game.courses = rows


def on_ice(game) -> list:
    """Everybody in a rack somewhere, as saved rows."""
    return list(getattr(game, "iced", None) or [])


def ice_bill(game, day: float | None = None) -> float:
    """What the racks cost, in credits, since anybody last paid.

    A cold berth is the only thing on a concourse that keeps charging after
    the ship has left, which is the point of it: somebody who is not needed
    for nine years is cheap to keep and not free.
    """
    day = getattr(game, "day", 0.0) if day is None else day
    owed = 0.0
    for row in on_ice(game):
        got = table.TREATMENT_BY_ID.get(row.get("how", ""))
        if got is None:
            continue
        years = max(0.0, (day - float(row.get("since", 0))) / 365.0)
        owed += got.cr * ICE_PER_YEAR * min(years, ICE_LONGEST_YEARS)
    return owed


def freeze(game, at, officer, treatment_id: str) -> dict:
    """Put somebody in a rack. They leave the bridge and stop ageing."""
    said = quote(game, at, officer, treatment_id)
    if not said["ok"]:
        return {"ok": False, "why": said["why"]}
    got = said["treatment"]
    if got.kind != "ice":
        return {"ok": False, "why": "That is not a cold berth."}
    game.credits -= said["cr"]
    game.officers = [o for o in game.officers if o is not officer]
    rows = list(getattr(game, "iced", None) or [])
    rows.append({"officer": officer, "how": got.id,
                 "since": float(getattr(game, "day", 0.0)),
                 "where": said["place"].name})
    game.iced = rows
    game.add_log(f"{officer.name} went into a cold berth at "
                 f"{said['place'].name}. {said['cr']:,} credits, and "
                 f"{got.cr * ICE_PER_YEAR:,.0f} a year while they are in it.")
    return {"ok": True, "why": "", "cr": said["cr"], "officer": officer}


def thaw(game, at, officer_id: int) -> dict:
    """Bring somebody up, and settle what the rack is owed."""
    rows = list(getattr(game, "iced", None) or [])
    row = next((r for r in rows if getattr(r.get("officer"), "id", None)
                == officer_id), None)
    if row is None:
        return {"ok": False, "why": "Nobody of that name is in a rack."}
    place = shore._where(game, at)
    if place is None or not shore.selling(game, place, "ice"):
        return {"ok": False, "why": "There is no rack here to open."}
    if shore.barred(game, place):
        return {"ok": False, "why": shore.barred(game, place)}
    owed = ice_bill(game)
    if game.credits < owed:
        return {"ok": False,
                "why": f"The racks are owed {owed:,.0f} credits."}
    game.credits -= owed
    rows.remove(row)
    game.iced = rows
    officer = row["officer"]
    years = (float(getattr(game, "day", 0.0)) - float(row["since"])) / 365.0
    game.officers = list(game.officers) + [officer]
    game.add_log(f"{officer.name} came up after {years:.1f} years on ice. "
                 f"{owed:,.0f} credits to the rack.", "good")
    return {"ok": True, "why": "", "cr": owed, "officer": officer,
            "years": years}
