"""The hearing: what is at stake, what your case is worth, and what it costs.

There was no judicial process anywhere in the game. No court, tribunal,
magistrate, verdict, sentence, appeal, warrant or pardon appears in `sim/`,
`data/`, `core/` or `world/` — every grep hit for those words was the English
word "sentence" meaning a line of prose or "verdict" meaning a colour band on
the combat forecast. The nearest thing in the fiction was the censure venture,
which has charges ("mostly true, which is not the point"), signatories and a
result, and in which the player's entire role is a `backed`/`opposed` flag.

Two rules shape everything here.

**The screen states the whole price before you commit.** `case()` returns what
each plea would do — the assessment, the odds, the sanction — and `plead()`
does exactly that and nothing else. This project has been bitten by a board
that promised one number and charged another more than once, so the preview
and the act read the same function.

**Not answering is a decision with a price, not an escape.** Every forum here
decides in your absence. Default and the assessment is multiplied, the forum
reaches for a heavier instrument, and failing to answer is itself an offence —
which is the part that makes the whole layer inescapable by simply never going
home again. A legal system you can ignore is scenery, and the survey already
found one of those.

The two favours that were purchasable and read by nothing get their jobs back
here: "a word before it happens" (whose own blurb says *a levy, a search, **a
claim** — you hear about it first*) is advance notice and a better hearing,
and "a berth regardless" is what gets you alongside under an interdict.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from ..data.forums import SANCTIONS_BY_ID, attends, forum_of
from ..data.offences import OFFENCES_BY_ID
from . import law as law_sim

#: Credits at stake per point of gravity, at weight 1. Pitched against the
#: early game: a first contraband conviction is a bad season, not the end.
ASSESS_BASE = 9000.0

#: What admitting it saves you. Enough to be a real choice against contesting.
ADMIT_RELIEF = 0.62

#: How much each thing is worth to your case, at best.
STANDING_WORTH = 0.35
ADVOCATE_WORTH = 0.30
WARNING_WORTH = 0.15

#: What each prior conviction with the same power adds to how hard they
#: come down. Four priors takes an ordinary offence to the top of the ladder.
PER_PRIOR = 0.22

#: The odds never reach either end. A hearing you cannot lose is not a
#: hearing, and one you cannot win is a formality with extra clicks.
ODDS_FLOOR = 0.04
ODDS_CEILING = 0.86


def assess(game, charge) -> float:
    """The sum at stake, before any plea. Round hundreds, so it reads."""
    offence = OFFENCES_BY_ID.get(charge.offence)
    if offence is None:
        return 0.0
    return round(ASSESS_BASE * offence.gravity * max(0.15, charge.weight), -2)


def advocate(game):
    """Who can speak for you. The `comms` officer — "Diplomacy and trade
    terms" — which is the job description, and gives that officer a second
    thing to be good at."""
    for officer in getattr(game, "officers", None) or []:
        if getattr(officer, "retired", False):
            continue
        if getattr(officer, "role", "") == "comms":
            return officer
    return None


def defence(game, charge) -> dict:
    """What your case is worth, itemised. The screen prints the items."""
    rows = []
    standing = float(game.rep.get(charge.power, 0.0))
    if standing > 0:
        worth = min(STANDING_WORTH, standing / 100.0 * STANDING_WORTH)
        rows.append(("Your standing with them", worth))
    speaker = advocate(game)
    if speaker is not None:
        worth = min(ADVOCATE_WORTH,
                    (getattr(speaker, "level", 1) / 9.0) * ADVOCATE_WORTH)
        rows.append((f"{speaker.name} speaks for you", worth))
    from . import officials as officials_sim
    if officials_sim.anywhere(game, "warning"):
        rows.append(("You had word of it first", WARNING_WORTH))
    return {"rows": rows, "total": round(sum(w for _n, w in rows), 3)}


def odds(game, charge) -> float:
    """The chance a contested charge is dismissed."""
    offence = OFFENCES_BY_ID.get(charge.offence)
    if offence is None:
        return 0.0
    against = offence.gravity * min(1.6, charge.weight)
    got = defence(game, charge)["total"] - against + 0.40
    return round(max(ODDS_FLOOR, min(ODDS_CEILING, got)), 3)


def settle_price(game, charge) -> float:
    """What closing it before a verdict costs, or 0 if it cannot be closed."""
    offence = OFFENCES_BY_ID.get(charge.offence)
    forum = forum_of(charge.power)
    if offence is None or forum is None or not offence.settleable:
        return 0.0
    if forum.settle_share <= 0:
        return 0.0
    return round(assess(game, charge) * forum.settle_share, -2)


def severity(game, charge) -> float:
    """How hard this forum comes down. 0..1.

    **Priors, not the first offence.** The smoke test caught the first draft
    suspending a captain's licence — the Charter's heaviest instrument, and
    the end of any plan involving ground — for one contraband charge on a
    first chronicle. A legal system whose opening move is its last move has
    nowhere to go and teaches nothing. Gravity sets the floor and the number
    of times they have convicted you before does the rest.
    """
    offence = OFFENCES_BY_ID.get(charge.offence)
    if offence is None:
        return 0.0
    priors = len([c for c in law_sim.convictions(game, charge.power)
                  if c.id != charge.id])
    scale = 0.55 + PER_PRIOR * min(4, priors) + 0.12 * min(1.5, charge.weight)
    return max(0.0, min(0.99, offence.gravity * scale))


def _step(forum, severity: float) -> str:
    """Which instrument this forum reaches for. Worse cases, heavier tools."""
    ladder = forum.sanctions
    if not ladder:
        return ""
    index = min(len(ladder) - 1, int(severity * len(ladder)))
    return ladder[max(0, index)]


def _settle_name(forum) -> str:
    """What buying your way out is called here. The Choir does not take money
    for its own sake — `data/factions` says the one thing it trades for is
    recordings of wet cognition, so that is what it wants and the price is
    what arranging one costs you."""
    if forum.form == "attainder":
        return "Submit the recording"
    if forum.form == "none":
        return "Buy the claim back"
    return "Settle it now"


def case(game, charge) -> dict:
    """**The whole price, before you choose.** What the screen shows.

    Returns every plea with what it would do, so the board cannot promise
    something `plead` does not deliver — they are the same numbers.
    """
    offence = OFFENCES_BY_ID.get(charge.offence)
    forum = forum_of(charge.power)
    if offence is None or forum is None:
        return {"ok": False, "why": "No such matter."}
    stake = assess(game, charge)
    hardness = severity(game, charge)
    pleas = []
    # **Only where there is somewhere to stand.** The Freeholds have no forum
    # and the Dry Choir holds no hearing — offering either of them a plea puts
    # a button on the screen that cannot mean anything, which is worse than
    # no button. What is left for both is money, and for the Choir that is
    # not money at all.
    if attends(charge.power):
        pleas.append({
            "id": "contest", "name": "Contest it",
            "cost": 0.0, "odds": odds(game, charge),
            "blurb": (f"Dismissed, or the full ₡{stake:,.0f} and "
                      f"{SANCTIONS_BY_ID[_step(forum, hardness)].name.lower()}.")})
        # One number. The first draft rounded the cost and not the blurb, so
        # the same button offered ₡4,200 and ₡4,154 in the same breath.
        admitted = round(stake * ADMIT_RELIEF, -2)
        pleas.append({
            "id": "admit", "name": "Admit it",
            "cost": admitted, "odds": 0.0,
            "blurb": (f"₡{admitted:,.0f} and the lighter instrument. No "
                      "dismissal, and it stands on the record.")})
    price = settle_price(game, charge)
    if price > 0:
        pleas.append({
            "id": "settle", "name": _settle_name(forum),
            "cost": price, "odds": 0.0,
            "blurb": (f"₡{price:,.0f} today. Closed, nothing on the record, "
                      "no instrument.")})
    return {
        "ok": True, "charge": charge.id, "power": charge.power,
        "who": FACTIONS_BY_ID[charge.power].short,
        "forum": forum.name, "occasion": forum.occasion, "form": forum.form,
        "offence": offence.name, "writ": offence.writ, "did": offence.did,
        "detail": charge.detail, "where": charge.where,
        "stake": stake, "severity": hardness,
        "defence": defence(game, charge),
        "sanction": _step(forum, hardness),
        "default_at": charge.due,
        "default_cost": round(stake * forum.default_multiple, -2),
        "absent": forum.absent,
        "pleas": pleas,
    }


def impose(game, charge, sanction_id: str, amount: float) -> list:
    """Carry a verdict out. Money becomes a debt; the rest becomes a warrant."""
    from . import debts as debts_sim
    from . import warrants as warrants_sim
    sanction = SANCTIONS_BY_ID.get(sanction_id)
    if sanction is None:
        return []
    offence = OFFENCES_BY_ID.get(charge.offence)
    charge.sanction = sanction_id
    who = FACTIONS_BY_ID[charge.power].short
    out = []
    system = getattr(game, "system", None)

    # **The assessment is always owed.** The first draft only entered a debt
    # when the sanction happened to be a monetary one, so a verdict that
    # reached for an interdict announced "assessed at ₡12,100" and charged
    # nothing at all — and `clemency.settled_up` then lifted the interdict on
    # the next tick, because a captain who owes nothing has paid. The
    # instrument is what they do *as well*, and paying discharges both.
    debts_sim.owe(game, charge.power, amount,
                  kind="bond" if sanction.bite == "bond" else "judgment",
                  note=f"{offence.name} at {charge.where or 'the Verge'}",
                  charge_id=charge.id,
                  distrain=(sanction_id == "distraint"),
                  grace=360.0 if sanction.bite == "bond" else None)

    if sanction.bite == "debt":
        out.append(("bad", f"{who}: {sanction.name} of ₡{amount:,.0f}"
                           + (", collectable at their counters."
                              if sanction_id == "distraint" else ".")))
    elif sanction.bite == "bond":
        warrants_sim.issue(game, charge.power, "bond",
                           f"security posted against the hull for "
                           f"{offence.writ}", reach="holdings",
                           charge_id=charge.id, system=system)
        out.append(("bad", f"{who}: ₡{amount:,.0f} posted against the hull. "
                           "Default and the ship is theirs."))
    elif sanction.bite == "hunt":
        price = warrants_sim.price_for(offence.gravity, charge.weight)
        warrants_sim.issue(game, charge.power, "hunt",
                           f"{offence.writ}, at {charge.where}",
                           reach="everywhere", charge_id=charge.id,
                           system=system, price=price)
        out.append(("bad", f"{who}: ₡{price:,.0f} posted on your hull, and "
                           "the paper is for sale."))
    else:
        warrants_sim.issue(game, charge.power, sanction.bite,
                           f"{offence.writ}, at {charge.where}",
                           reach="holdings", charge_id=charge.id,
                           system=system)
        out.append(("bad", f"{who}: ₡{amount:,.0f} assessed, and "
                           f"{sanction.name.lower()}. {sanction.blurb}"))
    return out


def plead(game, charge, plea: str, rng=None) -> dict:
    """Answer a charge. `contest`, `admit` or `settle`."""
    forum = forum_of(charge.power)
    if forum is None or charge.state != "filed":
        return {"ok": False, "why": "There is nothing to answer."}
    quote = case(game, charge)
    if not quote["ok"]:
        return quote
    allowed = {p["id"] for p in quote["pleas"]}
    if plea not in allowed:
        return {"ok": False, "why": "That is not open to you here."}
    if plea == "settle":
        price = settle_price(game, charge)
        if game.credits < price:
            return {"ok": False,
                    "why": f"Settling is ₡{price:,.0f} and you have "
                           f"₡{game.credits:,.0f}."}
        game.credits -= price
        charge.state = "closed"
        charge.outcome = "settled"
        charge.plea = plea
        charge.verdict = f"Settled before a {forum.occasion} for ₡{price:,.0f}."
        return {"ok": True, "outcome": "settled", "paid": price,
                "said": charge.verdict, "lines": [
                    ("", f"{quote['who']}: settled for ₡{price:,.0f}. "
                         "Nothing goes on the record.")]}
    charge.plea = plea
    charge.state = "answered"
    return {"ok": True, "outcome": "answered",
            "said": f"Your plea is entered. The {forum.occasion} will decide.",
            "lines": [("", f"{quote['who']}: plea entered — "
                           f"{'contested' if plea == 'contest' else 'admitted'}.")]}


def hear(game, charge, rng) -> list:
    """Decide it. Returns log lines. The only writer of a verdict."""
    forum = forum_of(charge.power)
    offence = OFFENCES_BY_ID.get(charge.offence)
    if forum is None or offence is None or charge.state == "closed":
        return []
    who = FACTIONS_BY_ID[charge.power].short
    stake = assess(game, charge)
    hardness = severity(game, charge)
    out: list = []

    if charge.plea == "contest" and rng.chance(odds(game, charge)):
        charge.state = "closed"
        charge.outcome = "acquitted"
        charge.verdict = f"Dismissed at the {forum.occasion}."
        return [("", f"{who}: dismissed. {_thanks(game, charge)}")]

    if charge.plea == "admit":
        amount, note = round(stake * ADMIT_RELIEF, -2), "admitted"
        hardness = max(0.0, hardness - 0.20)
    elif charge.plea == "contest":
        amount, note = stake, "contested and lost"
    else:
        # Never answered. The forum decided anyway, which every forum here
        # does, and it reached for something heavier because you were not
        # there to argue it down.
        amount = round(stake * forum.default_multiple, -2)
        note = "decided in absence"
        hardness = min(0.99, hardness + 0.25)
        out.append(("bad", f"{who}: {forum.absent}"))
        _default_charge(game, charge)

    charge.state = "closed"
    charge.outcome = "convicted"
    charge.verdict = (f"{offence.name} — {note}. Assessed at ₡{amount:,.0f}.")
    out.extend(impose(game, charge, _step(forum, hardness), amount))

    # A conviction is also a thing they remember about you, in the same file
    # every other grievance goes in, so it prices your cargo like the rest.
    from . import grudge as grudge_sim
    grudge_sim.note(game, charge.power, "conviction",
                    f"you were convicted of {offence.writ}",
                    salience=0.8 + offence.gravity * 0.7)
    return out


def _thanks(game, charge) -> str:
    speaker = advocate(game)
    if speaker is not None:
        return f"{speaker.name} earned their wage."
    return "Nothing is added to the file."


def _default_charge(game, charge) -> None:
    """Not turning up is its own offence, and it never prescribes."""
    from . import dockets
    dockets.allege(game, charge.power, "default",
                   f"you did not answer for {charge.where or 'the matter'}",
                   weight=1.0, seen=1.0)


def summons(game) -> list:
    """Everything filed and awaiting an answer, soonest first. For the UI."""
    rows = [c for c in law_sim.ensure(game).charges
            if c.state in ("filed", "answered")]
    rows.sort(key=lambda c: c.due)
    return rows


def tick(game, days: float, rng) -> list:
    """Hearings that have come due. Called from the clock."""
    out: list = []
    for charge in summons(game):
        if charge.due > float(game.day):
            continue
        out.extend(hear(game, charge, rng))
    return out
