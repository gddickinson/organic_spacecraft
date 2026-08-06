"""The record: charges, debts and warrants, and the one door that makes them.

Everything the governance layer knows lives here, in one saved object, for the
same reason `sim/conn.py` holds one approach: the alternative is four modules
each keeping a private list, and the first thing that happens then is that a
charge is settled in one place and still outstanding in another.

The split above this file is by *verb*, not by noun — `sim/dockets` alleges and
files, `sim/tribunal` hears, `sim/debts` collects, `sim/warrants` enforces,
`sim/clemency` forgives — and every one of them reads and writes these three
lists through `ensure`. Nothing else may hold a `Charge`.

**Ids are allocated here and never reused.** A sanction points at the charge
that produced it and a debt points at the sanction; if ids were per-list or
recycled, a settled charge would silently pay off somebody else's judgment.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register


@register
@dataclass
class Charge:
    """One accusation, by one power, with a date and a place on it.

    `state` walks: **alleged** (they noticed; nothing is public yet) →
    **filed** (they are prosecuting, and a summons is out) → **closed**.
    `outcome` says how it closed: convicted, acquitted, settled, or spent —
    the last meaning it prescribed before anyone got round to it.

    The distinction between *alleged* and *filed* is what makes a power's
    reach matter. Being seen is not being charged; a power with nothing in
    the system may notice and never do anything about it, and one whose fleet
    is parked overhead files within the month.
    """

    id: int = 0
    power: str = ""
    offence: str = ""
    #: When the act happened, not when it was noticed.
    day: float = 0.0
    where: str = ""
    system_id: int = -1
    #: What actually happened, in words, for the docket and the verdict.
    detail: str = ""
    #: How bad this instance was. Scales the assessment on top of gravity —
    #: eleven tonnes of wildseed is not the same charge as one.
    weight: float = 1.0
    state: str = "alleged"
    outcome: str = ""
    verdict: str = ""
    filed_on: float = -1.0
    #: When the forum decides. A captain who wants to be in the room has
    #: until this day to get there.
    due: float = -1.0
    plea: str = ""
    #: Set when a verdict imposes something, so the docket can say what a
    #: conviction actually cost.
    sanction: str = ""


@register
@dataclass
class Debt:
    """A sum owed to somebody who can do something about not being paid.

    **The game had no debt instrument at all** — no loans, no liens, no
    creditors, and 27 of 28 credit outflows simply refused when you could not
    afford them, so the economy had wharfage, tolls, levies, admin overheads
    and payroll and no way to owe anybody anything. Every judgment now lands
    here, which is what makes a fine a consequence rather than a toll.

    `holder` is separate from `creditor` because of the Freeholds: their paper
    is sold on, and who is collecting changes how they collect.
    """

    id: int = 0
    creditor: str = ""
    holder: str = ""
    principal: float = 0.0
    paid: float = 0.0
    #: Daily interest, as a share of principal.
    rate: float = 0.0
    since: float = 0.0
    #: The day it falls due. Past this, arrears can be charged.
    due: float = 0.0
    #: "judgment" | "bond" | "levy" | "settlement"
    kind: str = "judgment"
    note: str = ""
    charge_id: int = -1
    #: Whether counters in the creditor's space take a cut of your sales.
    distrain: bool = False
    settled: bool = False
    #: Set once arrears have been charged for this debt, so a single unpaid
    #: judgment cannot generate a fresh charge every tick.
    chased: bool = False


@register
@dataclass
class Warrant:
    """An instrument in force: what a power will do to you, and how far.

    This is the thing the survey found missing everywhere. "Hunted" was the
    bottom reputation band and only a label; `grudge.hostile_open` — the
    game's own definition of "this power shoots on sight" — was called by
    nothing but a test; two purchasable favours were read by no code; and the
    only thing in the sector that ever hunted the player was the Bloom.
    """

    id: int = 0
    power: str = ""
    #: From `data/forums.Sanction.bite`: refuse | licence | shun | hunt | bond.
    bite: str = ""
    #: "system" (where it happened) | "holdings" (anywhere they hold) |
    #: "everywhere" (they will follow you off their own register).
    reach: str = "holdings"
    since: float = 0.0
    #: Day it lapses, or -1 for "until it is answered".
    until: float = -1.0
    why: str = ""
    charge_id: int = -1
    system_id: int = -1
    #: The posted sum, for a bounty. Whoever collects is paid this.
    price: float = 0.0
    lifted: bool = False


@register
@dataclass
class Law:
    """Everything the powers have on you, in one place."""

    charges: list = field(default_factory=list)
    debts: list = field(default_factory=list)
    warrants: list = field(default_factory=list)
    #: Never reused — see the module docstring.
    next_id: int = 1
    #: Day each power last swept its file, so filing is periodic rather than
    #: instantaneous and a captain has a window to get out of reach.
    swept: dict = field(default_factory=dict)
    #: Powers who have wiped the slate, and on what day, so an amnesty cannot
    #: be claimed twice out of the same treaty.
    amnesty: dict = field(default_factory=dict)


def ensure(game) -> Law:
    """The record. Created on first use, so old chronicles keep working."""
    if getattr(game, "law", None) is None:
        game.law = Law()
    return game.law


def next_id(game) -> int:
    state = ensure(game)
    got = state.next_id
    state.next_id = got + 1
    return got


def charges(game, power: str | None = None, state: str | None = None) -> list:
    """Charges, newest first, optionally filtered. The one query."""
    rows = list(ensure(game).charges)
    if power:
        rows = [c for c in rows if c.power == power]
    if state:
        rows = [c for c in rows if c.state == state]
    rows.sort(key=lambda c: -c.day)
    return rows


def charge_by_id(game, charge_id: int):
    return next((c for c in ensure(game).charges if c.id == charge_id), None)


def open_charges(game, power: str | None = None) -> list:
    """Everything still live: alleged or filed, but not closed."""
    return [c for c in charges(game, power) if c.state != "closed"]


def convictions(game, power: str | None = None) -> list:
    return [c for c in charges(game, power) if c.outcome == "convicted"]


def clear(game) -> None:
    """Wipe the record. Only `sim/clemency` and a new chronicle may."""
    state = ensure(game)
    state.charges.clear()
    state.debts.clear()
    state.warrants.clear()
