"""Owing somebody money who can do something about not being paid.

**The game had no debt instrument at all.** No loans, no liens, no creditors:
a grep for the whole vocabulary across `sim/`, `data/`, `core/` and `world/`
turned up one line of flavour text and one blackmail lever on an NPC. Twenty-
seven of the twenty-eight places credits leave the purse check first and
simply refuse, so an economy with wharfage, tolls, levies, administration and
payroll had no way for the captain to be *behind* on anything. The single
unguarded outflow (`robots.py`, hybrid machines charged wages as well as
parts) could put the treasury underwater and nothing anywhere read a negative
balance — the test suite treated it as a failure rather than a game state.

A judgment lands here, and that is what makes a fine a consequence rather than
a toll you either can or cannot pay today. Three things follow from a debt:

- **It grows.** Not ruinously — `JUDGMENT_RATE` doubles a sum in about four
  years — except for Freehold paper, which is priced by whoever bought it.
- **It is collected.** `distrain` lets a creditor take a share of every sale
  you make in their space, at the till, without asking. This is the answer to
  a fine you can decline to pay by never opening the screen again.
- **It is charged for.** Left past its due day, arrears go back to
  `sim/dockets` as a fresh offence, so ignoring a judgment is itself the
  thing that escalates. `chased` makes that happen exactly once per debt.

The Freeholds' paper is sold on (`sell_on`), which is the mechanical
expression of the one thing that faction actually believes: a claim is an
asset, and assets move. The holder who bought it at a discount wants more than
the power that raised it did.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from . import law as law_sim

#: Daily interest on an ordinary judgment. About 6% a year — noticeable over
#: a chronicle, never a spiral.
JUDGMENT_RATE = 0.00016

#: What Freehold paper costs to carry once somebody has bought it. Their whole
#: character in one constant: always available to settle, always dearer.
HOLDER_RATE = 0.00085

#: A bond is security, not a loan, so it does not grow. It is simply due.
BOND_RATE = 0.0

#: Days a judgment gets before arrears can be charged on it.
GRACE_DAYS = 180.0

#: The most a creditor takes from one sale. Confiscatory collection would
#: simply end the chronicle, and a captain who cannot trade cannot pay.
DISTRAIN_SHARE = 0.28

#: Below this the debt is treated as discharged — nobody chases a rounding.
SETTLED_UNDER = 1.0


def owe(game, creditor: str, principal: float, kind: str = "judgment",
        note: str = "", charge_id: int = -1, distrain: bool = False,
        rate: float | None = None, grace: float | None = None):
    """Enter a sum against the captain. The one way a debt is created."""
    if principal <= 0:
        return None
    state = law_sim.ensure(game)
    if rate is None:
        rate = BOND_RATE if kind == "bond" else JUDGMENT_RATE
    debt = law_sim.Debt(
        id=law_sim.next_id(game), creditor=creditor, holder=creditor,
        principal=float(principal), rate=float(rate), since=float(game.day),
        due=float(game.day) + (GRACE_DAYS if grace is None else float(grace)),
        kind=kind, note=note, charge_id=charge_id, distrain=bool(distrain))
    state.debts.append(debt)
    return debt


def balance(game, debt) -> float:
    """What is owed today: principal, plus what it has grown, less paid."""
    if debt.settled:
        return 0.0
    days = max(0.0, float(game.day) - debt.since)
    grown = debt.principal * (1.0 + debt.rate * days)
    return max(0.0, round(grown - debt.paid, 2))


def live(game, creditor: str | None = None, holder: str | None = None) -> list:
    rows = [d for d in law_sim.ensure(game).debts if not d.settled]
    if creditor:
        rows = [d for d in rows if d.creditor == creditor]
    if holder:
        rows = [d for d in rows if d.holder == holder]
    rows.sort(key=lambda d: d.due)
    return rows


def total_owed(game, creditor: str | None = None) -> float:
    return round(sum(balance(game, d) for d in live(game, creditor)), 2)


def overdue(game) -> list:
    return [d for d in live(game) if float(game.day) > d.due]


def pay(game, debt, amount: float | None = None) -> dict:
    """Pay some or all of a debt. Returns what happened, for a screen."""
    if debt is None or debt.settled:
        return {"ok": False, "why": "Nothing outstanding."}
    owed = balance(game, debt)
    want = owed if amount is None else min(float(amount), owed)
    if want <= 0:
        return {"ok": False, "why": "Nothing outstanding."}
    if game.credits < want:
        return {"ok": False,
                "why": f"That is ₡{want:,.0f} and you have "
                       f"₡{game.credits:,.0f}."}
    game.credits -= want
    debt.paid += want
    cleared = balance(game, debt) <= SETTLED_UNDER
    if cleared:
        debt.settled = True
    who = FACTIONS_BY_ID.get(debt.holder)
    short = who.short if who else debt.holder
    return {"ok": True, "paid": want, "cleared": cleared,
            "left": balance(game, debt),
            "said": (f"Paid ₡{want:,.0f} to {short}. The matter is closed."
                     if cleared else
                     f"Paid ₡{want:,.0f} to {short}; ₡{balance(game, debt):,.0f} "
                     "still stands.")}


def distrain_at(game, system, value: float) -> int:
    """A counter takes its cut of a sale toward what you owe. Returns credits.

    **Called from the till**, not from a screen the captain chooses to open —
    that is the entire point. `sim/wharfage.collect` is the one place money
    moves at a market, so this sits beside it and a creditor who holds the
    quay is paid before the captain is.
    """
    if value <= 0:
        return 0
    from . import wharfage
    holder = wharfage.holder(game, system)
    if not holder:
        return 0
    owing = [d for d in live(game, creditor=holder) if d.distrain]
    if not owing:
        return 0
    taken = 0.0
    room = float(value) * DISTRAIN_SHARE
    for debt in owing:
        if room <= 0:
            break
        bite = min(room, balance(game, debt))
        if bite <= 0:
            continue
        debt.paid += bite
        room -= bite
        taken += bite
        if balance(game, debt) <= SETTLED_UNDER:
            debt.settled = True
    return int(round(taken))


def distraint_note(game, system) -> str:
    """What the market screen warns before you sell here."""
    from . import wharfage
    holder = wharfage.holder(game, system)
    if not holder:
        return ""
    owing = [d for d in live(game, creditor=holder) if d.distrain]
    if not owing:
        return ""
    short = FACTIONS_BY_ID[holder].short if holder in FACTIONS_BY_ID else holder
    return (f"{short} holds this counter and a distraint against you: "
            f"{DISTRAIN_SHARE:.0%} of anything you sell here goes to them "
            f"first (₡{sum(balance(game, d) for d in owing):,.0f} outstanding).")


def sell_on(game, debt, rng) -> str:
    """Freehold paper changes hands. Returns a line, or "" if it did not.

    The Freeholds do not collect; they *sell*. What the buyer wants is more
    than what was raised, which is why `HOLDER_RATE` is five times the
    ordinary and why settling early with the Freeholds is always the move.
    """
    if debt.settled or debt.creditor != "freeholds" or debt.holder != "freeholds":
        return ""
    if not rng.chance(0.25):
        return ""
    debt.holder = "holder:freeholds"
    debt.rate = HOLDER_RATE
    return ("Your paper has been sold on at the Freeholds. Somebody bought it "
            "at a discount and will want rather more than that back.")


def tick(game, days: float, rng) -> list:
    """Interest, dunning, and arrears. Returns log lines."""
    out: list = []
    state = law_sim.ensure(game)
    if not state.debts:
        return out
    from . import dockets
    for debt in list(state.debts):
        if debt.settled:
            continue
        said = sell_on(game, debt, rng)
        if said:
            out.append(("warn", said))
        if float(game.day) <= debt.due or debt.chased:
            continue
        debt.chased = True
        who = FACTIONS_BY_ID.get(debt.creditor)
        short = who.short if who else debt.creditor
        # **Ignoring a judgment is itself the offence.** This is what stops
        # the whole layer being escapable by never opening the screen: a fine
        # you do not pay does not lapse, it grows a charge.
        charge = dockets.allege(
            game, debt.creditor, "arrears",
            f"a judgment of ₡{debt.principal:,.0f} left standing",
            weight=min(2.5, 0.6 + debt.principal / 8000.0), seen=1.0)
        if charge is not None:
            out.append(("bad", f"{short} has entered your arrears on the "
                               f"file — ₡{balance(game, debt):,.0f} "
                               "outstanding."))
        else:
            out.append(("warn", f"{short} want their "
                                f"₡{balance(game, debt):,.0f}."))
    return out


def note(game) -> str:
    """One line for the status bar. "" when the captain owes nobody."""
    owed = total_owed(game)
    if owed <= SETTLED_UNDER:
        return ""
    late = len(overdue(game))
    if late:
        return f"₡{owed:,.0f} owed, {late} past due"
    return f"₡{owed:,.0f} owed"
