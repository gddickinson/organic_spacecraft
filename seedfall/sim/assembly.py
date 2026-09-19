"""The Assembly: the four powers in one room, and the door its law comes through.

Every season the powers sit at a capital in turn (`sim/assembly_session`),
vote on two or three instruments by their interest (`sim/assembly_vote`), and
the captain can move a vote beforehand or speak on the day
(`sim/assembly_lobby`). This module is the part everything else imports: the
saved state, and **`effect`, the one door every consuming system reads a
passed resolution through.**

It imports nothing from `sim/` at module level, on purpose. Eleven systems
read `effect` at one line each — wharfage, the purse, ventures, the law, the
counter, war, salvage, piracy, colonies, the drydock and the Weave — and a door
that pulled any of them in at import would be a knot of cycles.

**The effects are derived, never stored.** A passed resolution is stored with
its term; what it *does* is worked out from the table at read time and
memoised for the day. So an instrument that lapses on day N stops at day N for
every reader, with nothing to clean up — the same reason `sim/war` reads a war
off the matrix rather than keeping a flag.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.assembly import EFFECTS, RESOLUTIONS_BY_ID
from ..data.factions import FACTIONS_BY_ID

#: History kept, in sittings. Enough for a screen and a despatch to look back
#: two years; a save does not grow for ever.
HISTORY_KEPT = 8


@register
@dataclass
class Tabled:
    """One instrument on the order paper, and whom it names."""
    key: str
    res_id: str
    sponsor: str
    #: "power", "a", "b" and "systems", as the instrument's shape needs.
    params: dict = field(default_factory=dict)


@register
@dataclass
class Active:
    """A resolution in force, and the day it lapses."""
    key: str
    res_id: str
    sponsor: str
    params: dict = field(default_factory=dict)
    passed: int = 0
    until: int = 0


@register
@dataclass
class AssemblyState:
    #: Sittings held so far. The next sitting's number is this plus one, and
    #: it keys that sitting's luck (`assembly_session.luck`).
    session: int = 0
    next_day: int = 0
    #: Index into `data/assembly.SEAT_ORDER` of the next host.
    turn: int = 0
    #: Whether the next sitting's agenda has been published.
    announced: bool = False
    agenda: list = field(default_factory=list)
    #: key -> {power: swing}: what the captain has done to each vote.
    lobby: dict = field(default_factory=dict)
    #: key -> "for" | "against": where the captain stands.
    positions: dict = field(default_factory=dict)
    #: "act|power" -> times done this sitting, for the rising price.
    acts: dict = field(default_factory=dict)
    #: Intelligence already spent on a leak: "chart:<id>" or "note:<index>".
    spent: list = field(default_factory=list)
    active: list = field(default_factory=list)
    #: Recent sittings, newest last, as plain dicts: day, seat, results.
    history: list = field(default_factory=list)
    #: Tabled, passed and resisted, all time — the pass rate the manual quotes.
    tallies: dict = field(default_factory=dict)
    #: `effects`' memo: ((day, rev, count), {key: value}). Derived.
    memo: tuple = field(default=(), compare=False, repr=False,
                        metadata={"transient": True})
    rev: int = field(default=0, compare=False, repr=False,
                     metadata={"transient": True})


def state(game) -> AssemblyState | None:
    """The Assembly as it stands, or None before it has ever been convened."""
    return getattr(game, "assembly", None)


def ensure(game) -> AssemblyState:
    """Convened on first use, so a chronicle saved before it keeps loading."""
    got = state(game)
    if got is None:
        from . import assembly_session
        got = game.assembly = AssemblyState()
        assembly_session.schedule(game, got, first=True)
    return got


def pair_key(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


# ── the door ───────────────────────────────────────────────────────────────

def effects(game) -> dict:
    """Every key in force today, combined across instruments. Memoised on
    the day and on the list of instruments, which are the only inputs."""
    got = state(game)
    if got is None or not got.active:
        return {}
    stamp = (game.day, got.rev, len(got.active))
    if got.memo and got.memo[0] == stamp:
        return got.memo[1]
    out: dict = {}
    for act in got.active:
        if act.until <= game.day:
            continue
        res = RESOLUTIONS_BY_ID.get(act.res_id)
        if res is None:
            continue
        for key, value in res.effects.items():
            _merge(out, key, _value(res, act, value))
    got.memo = (stamp, out)
    return out


def effect(game, key: str, default=None):
    """What the Assembly has decided about `key` today — **the one door**.

    With nothing in force it is `default`, or the vocabulary's own when the
    reader gives none. A key outside the vocabulary is refused rather than
    answered: a misspelt read that quietly returns "no resolution" is a
    feature that exists on the order paper and nowhere else.
    """
    if key not in EFFECTS:
        raise KeyError(f"no Assembly effect called {key!r}")
    if default is None:
        default = EFFECTS[key].default
    return effects(game).get(key, default)


def _value(res, act, value):
    """What one instrument sets a key to, with its named parties filled in."""
    if value == "power":
        return (act.params.get("power", ""),)
    if value == "pair":
        return (pair_key(act.params.get("a", ""), act.params.get("b", "")),)
    if res.shape in ("lanes", "unclaimed"):
        return {int(s): float(value) for s in act.params.get("systems", ())}
    return value


def _merge(out: dict, key: str, value) -> None:
    rule = EFFECTS[key].combine
    if key not in out:
        out[key] = dict(value) if isinstance(value, dict) else value
        return
    had = out[key]
    if isinstance(value, dict):
        for sub, v in value.items():
            had[sub] = had.get(sub, 1.0) * v
    elif rule == "mul":
        out[key] = had * value
    elif rule == "add":
        out[key] = had + value
    elif rule == "set":
        out[key] = tuple(sorted(set(had) | set(value)))
    else:                                   # "any" and "floor": the stronger
        out[key] = max(had, value)


def in_force(game) -> list:
    """The instruments binding today, soonest to lapse first."""
    got = state(game)
    if got is None:
        return []
    return sorted((a for a in got.active if a.until > game.day),
                  key=lambda a: a.until)


def enact(game, tabled, day: int, term: int) -> Active:
    """Put an instrument in force. The only writer of `active`."""
    got = ensure(game)
    act = Active(key=tabled.key, res_id=tabled.res_id, sponsor=tabled.sponsor,
                 params=dict(tabled.params), passed=day, until=day + term)
    got.active = [a for a in got.active if a.key != tabled.key] + [act]
    got.rev += 1
    return act


# ── the readers that need more than a number ───────────────────────────────

def embargoed(game, faction: str | None, cid: str) -> str:
    """Why this counter will not buy `cid`, or "" — read by `trade.sell`.

    An embargo on a power bars *its exports* — the goods it lists as selling
    — from every other power's counter. Its own quays still trade.
    """
    for target in effect(game, "embargo", ()):
        if target == faction or target not in FACTIONS_BY_ID:
            continue
        if cid in FACTIONS_BY_ID[target].sells:
            short = FACTIONS_BY_ID[target].short
            return (f"The Assembly's embargo on the {short}: nothing they "
                    f"export crosses this counter until the term is out.")
    return ""


def local_power(game, system) -> str | None:
    """Who taxes salvage here: the quay's holder, else the register's."""
    from . import diplomacy as dip
    port = getattr(system, "port", None)
    for who in (getattr(port, "faction", None), getattr(system, "faction", None)):
        if who in dip.POWERS:
            return who
    return None


def tax_salvage(game, worth: float) -> int:
    """The Salvage Law's cut of what a wreck gave up, moved to the local
    purse. Returns what was taken; read once, by `aftermath._salvage`.

    Assessed on everything the wreck gave up — its credits and the base worth
    of the cargo (`aftermath.worth_of`) — because the cargo is the larger
    half: 1.5-10x the credit loot, measured there. Taken in credits, and never
    more than the captain holds.
    """
    rate = effect(game, "salvage_tax", 0.0)
    holder = local_power(game, game.system)
    if rate <= 0 or holder is None or worth <= 0:
        return 0
    from . import exchequer
    tax = min(round(worth * rate), max(0, int(game.credits)))
    if tax <= 0:
        return 0
    game.credits -= tax
    exchequer.purse(game, holder).credits += tax
    game.add_log(f"Salvage Law: {FACTIONS_BY_ID[holder].short} took "
                 f"{tax:,} of what the wreck was worth.", "warn")
    return tax


def founding_rebate(game, system, cost: dict) -> int:
    """The Colony Charter's share of a holding's price, paid back out of the
    four purses. Returns the credits returned; read by `colony.found`.

    Credits only, and only what the purses hold: a fund that paid out goods,
    or money nobody had, would be conjuring it.
    """
    share = effect(game, "founding", 0.0)
    from . import territory
    if share <= 0 or territory.claimant(game, system):
        return 0
    from . import diplomacy as dip
    from . import exchequer
    owed = float(cost.get("credits", 0.0)) * share / len(dip.POWERS)
    paid = 0
    for power in dip.POWERS:
        purse = exchequer.purse(game, power)
        part = int(min(owed, max(0.0, purse.credits)))
        purse.credits -= part
        paid += part
    if paid:
        game.credits += paid
        game.add_log(f"The Colony Charter returned {paid:,} of what the "
                     f"holding cost.", "good")
    return paid


def hold(game) -> None:
    """The Choir's recognised standing, held each day by the Assembly's own
    tick. (A ceasefire's floor is not held: it lifts the pair once, when it
    passes — `assembly_session.sit` says why.)"""
    floor = effect(game, "choir_floor", None)
    if floor is not None and game.rep.get("sanhedrin", 0.0) < floor:
        game.adjust_rep("sanhedrin", floor - game.rep.get("sanhedrin", 0.0))


def tick(game, days: float) -> None:
    """The Assembly's day: publish, sit, lapse, hold. Called once, from
    `core/sectortime.economy`, after the matrix drifts. Draws no luck from
    the day's stream — each sitting has its own (`assembly_session.luck`)."""
    if days <= 0:
        return
    from . import assembly_session
    assembly_session.tick(game, days)
