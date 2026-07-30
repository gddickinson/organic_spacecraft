"""What a signed treaty is actually worth — the two things it promises.

`data/diplomacy.ACTIONS` has offered "a signed instrument: mutual berthing,
shared charts, and a clause about the Bloom that nobody expects to be honoured"
for 30,000 credits and a 180-day cooldown since treaties were written. The third
clause is a joke on purpose. The other two were not meant to be, and were:
signing appended a faction id to `DiplomaticState.treaties`, which was read by
`diplomacy.treaty_bonus` (+3% on the trade stat, printed on no screen) and by
the matrix's "treaty" pill, and by nothing else at all. No berth was cheaper and
no chart changed hands.

So this module is the two clauses, and it is the only place either is worked out:

- **Mutual berthing.** `sim/wharfage.rate` asks `berth_relief` and takes that
  share off at the signatory's quays. Because `rate` is the single door for the
  charge, the relief reaches the market board, the freight forecast, a cargo
  contract's sourcing estimate and the power's own purse in one move.
- **Shared charts.** They hand over what they hold of their own space. `shared`
  is the list, `worth` prices it at what a broker would want for the same
  paper, and `share_charts` is the only thing that hands it over — so the figure
  the screen quotes before you sign is a dry run of the act, not a formula that
  resembles it.

`worth` is the whole quote in one call, and both the offer on the diplomacy desk
and the log line after signing are built from it. Nothing here reaches for Qt.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from ..data.wharfage import TREATY_RELIEF
from . import intel


def signed(game, faction: str | None) -> bool:
    """Is there an instrument with this power? The one reader of the list."""
    from . import diplomacy as dip
    if not faction:
        return False
    return dip.has_treaty(game, faction)


def berth_relief(game, faction: str | None) -> float:
    """The share of the wharfage a treaty takes off at this power's quays.

    Zero without one, so `sim/wharfage.rate` can multiply unconditionally.
    """
    return TREATY_RELIEF if signed(game, faction) else 0.0


def space(game, faction: str) -> list:
    """The systems that are this power's own — whose charts they would share."""
    return [s for s in game.galaxy.systems if s.faction == faction]


def shared(game, faction: str) -> list:
    """The systems a treaty with this power would open to you.

    What they hold and you cannot see. Systems already at Scanned or better are
    not part of the gift, which is why signing twice would be worth nothing —
    and why the quote falls as you explore their space yourself.
    """
    return [s for s in space(game, faction) if intel.level(game, s) < 1]


def _price(game, systems) -> int:
    """What a broker would want for these charts. One door for both callers.

    Private on purpose: `worth` already carries the figure to the screen and
    `share_charts` to the log, so a public second spelling of it would be one
    more door onto a price — which is the shape of half the defects this project
    has found. `tests/test_reachable.py` refused it as unreachable, which is the
    same objection from the other side.
    """
    return sum(intel.chart_price(game, s) for s in systems)


def quays(game, faction: str) -> list:
    """Their berths that take a due — the ones the relief would apply at.

    Asked of `sim/wharfage.holder`, so a free port of theirs is not counted as
    somewhere the relief saves you anything: it was already free.
    """
    from . import wharfage as wharfage_sim
    return [s for s in game.galaxy.systems
            if wharfage_sim.holder(game, s) == faction]


def worth(game, faction: str) -> dict:
    """The whole instrument, quoted. The screen and the log both read this."""
    got = shared(game, faction)
    return {
        "faction": faction,
        "signed": signed(game, faction),
        "charts": len(got),
        "names": [s.name for s in got],
        "worth": _price(game, got),
        "relief": TREATY_RELIEF,
        "quays": len(quays(game, faction)),
        "space": len(space(game, faction)),
    }


def charts_line(told: dict) -> str:
    """What the charts clause is worth, in a sentence, or why it is worth little."""
    if not told["charts"]:
        return ("Their charts add nothing — you already hold everything they "
                f"know of their {told['space']} systems.")
    return (f"Their charts: {told['charts']} system(s) of their own you had not "
            f"seen, which a broker would have wanted about "
            f"{told['worth']:,} credits for.")


def berth_line(told: dict) -> str:
    """What the berthing clause is worth, in a sentence."""
    if not told["quays"]:
        return "They hold no quay that charges a due, so berthing is moot."
    return (f"Berthing: {told['relief']:.0%} off the wharfage at their "
            f"{told['quays']} quays, on everything in and out, for good.")


def hand_over(game, faction: str) -> dict:
    """Deliver the instrument. Every door into signing one comes through here.

    There are two: `diplomacy.perform` when the captain proposes it, and
    `approach.answer` when a power's envoy offers it. `data/diplomacy.py` records
    what happened the last time they differed — proposing charged the signatory's
    enemies and accepting charged nobody, so the way to sign a treaty for free
    was to wait to be asked. The charts clause was one edit away from being the
    same bug in the other direction.
    """
    given = share_charts(game, faction)
    if given["count"]:
        game.add_log(f"Treaty with {FACTIONS_BY_ID[faction].short}: "
                     f"{given['count']} of their charts, worth about "
                     f"{given['worth']:,}.", "good")
    return given


def share_charts(game, faction: str) -> dict:
    """Hand over their charts. The only writer, and it reports what it gave.

    `territory.collect_tithe` is the cautionary tale here: it returned a full
    account of a levy and its one caller threw the return away, so 78 tonnes
    left the colony and the chronicle said nothing. This return is consumed by
    `diplomacy.perform`, which puts both figures in the dialogue.
    """
    got = shared(game, faction)
    paid = _price(game, got)
    charts = intel.ensure(game)
    for system in got:
        if system.id not in charts:
            charts.append(system.id)
    return {"count": len(got), "worth": paid, "names": [s.name for s in got]}
