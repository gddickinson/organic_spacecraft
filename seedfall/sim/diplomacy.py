"""Diplomacy — actions, treaties, and how the powers regard one another.

Your standing with a faction is one axis. The other is how the factions feel
about each other, which you can move by taking sides, by brokering, and by being
seen to be worth listening to. Concord requires both.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.diplomacy import (AGENDAS,
                              CONCORD_RELATION, CONCORD_STANDING,
                              COURTSHIP_FALLOFF, COURTSHIP_FLOOR,
                              COURTSHIP_KNEE,
                              INITIAL_RELATIONS, RELATION_BANDS)
from ..data.factions import FACTIONS_BY_ID  # noqa: F401 - read as dip.FACTIONS_BY_ID
# The overtures themselves, split out at 500 lines; re-exported so every
# screen, check and caller keeps asking this module.
from .diplomacy_acts import (_merged, _remember, _spend,  # noqa: F401
                             _work_key, available, perform, preview, refusal)

POWERS = ("charter", "concordat", "freeholds", "sanhedrin")
#: A power will not sit down at your invitation below this standing.
BROKER_INVITE = 40.0


@register
@dataclass
class DiplomaticState:
    relations: dict[str, float] = field(default_factory=dict)
    treaties: list[str] = field(default_factory=list)
    cooldowns: dict[str, int] = field(default_factory=dict)   # "action|faction" -> day
    #: faction -> the day its last envoy came (`sim/approach.py`), which is
    #: what holds the next one off for `QUIET_DAYS`. A runtime attribute
    #: until 2026-09, so a reload let the next envoy straight in.
    approached: dict[str, int] = field(default_factory=dict)
    #: `favours` used to sit here, read by nobody: the favours the game
    #: actually keeps are per-official, in `officials._store(...)["favours"]`,
    #: and it was that unrelated dict which made the declared-field guard
    #: excuse this one for a whole cycle.


def _key(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


def ensure(game) -> DiplomaticState:
    """Created on first use so existing saves keep working."""
    if getattr(game, "diplomacy", None) is None:
        state = DiplomaticState()
        for (a, b), value in INITIAL_RELATIONS.items():
            state.relations[_key(a, b)] = float(value)
        game.diplomacy = state
    return game.diplomacy


# ── relations between the powers ───────────────────────────────────────────

def relation(game, a: str, b: str) -> float:
    return ensure(game).relations.get(_key(a, b), 0.0)


def shift_relation(game, a: str, b: str, delta: float) -> float:
    state = ensure(game)
    k = _key(a, b)
    state.relations[k] = max(-100.0, min(100.0, state.relations.get(k, 0.0) + delta))
    return state.relations[k]


def relation_band(value: float) -> tuple[str, str]:
    out = RELATION_BANDS[0]
    for band in RELATION_BANDS:
        if value >= band[0]:
            out = band
    return out[1], out[2]


def drift(game, days: float) -> None:
    """Grievances fade toward where the sector rests.

    Without this the powers ratchet one way: every blockade and censure is a
    permanent debit, and a decade of background politics quietly forecloses
    the Concord ending no matter what the player does. Events still dominate
    over any short period — this only pulls at what nobody is maintaining.
    """
    state = ensure(game)
    for (a, b), base in INITIAL_RELATIONS.items():
        key = _key(a, b)
        value = state.relations.get(key)
        if value is None:
            continue
        state.relations[key] = value + (base - value) * min(0.5, 0.00035 * days)


def courtship(rep: float) -> float:
    """What an overture is worth to a power that already thinks well of you.

    Full value while they barely know you, tapering as they come to regard
    you as Kin. Diplomacy had no diminishing return of any kind: the same
    forty tonnes of biomass moved a power at 95 exactly as far as one at 0,
    so standing was a commodity bought at a flat rate and the Concord — the
    sector's whole political condition — could be shopped for in two years
    without leaving port.
    """
    if rep <= COURTSHIP_KNEE:
        return 1.0
    span = 100.0 - COURTSHIP_KNEE
    reached = min(1.0, (rep - COURTSHIP_KNEE) / span)
    return max(COURTSHIP_FLOOR, (1.0 - reached) ** COURTSHIP_FALLOFF)


#: What `state.adjust_rep` clamps standing to. Diplomacy could not see the
#: cap: at rep 100 an overture quoted "+3", charged 12,000 credits, delivered
#: +0.00 — and its rivals' displeasure still landed, so the act was strictly
#: negative while the screen printed a gain.
REP_CAP = 100.0


def offer_gain(game, action, faction: str) -> float:
    """The standing an overture actually *delivers* — the one place this is
    decided.

    `preview` and `perform` each carried their own copy of this expression,
    which is the arrangement that has produced a free treaty, an ungranted
    favour and a phantom haggle payment in this file's history. Capped at
    the room the ledger has left, so the quoted number is the delivered one.
    """
    base = action.gain * (1 + game.ship_stats.diplomacy)
    room = max(0.0, REP_CAP - game.rep.get(faction, 0.0))
    return min(base * courtship(game.rep.get(faction, 0.0)), room)


def rivals_of(game, faction: str) -> list[str]:
    """Powers this one is currently on bad terms with."""
    return [p for p in POWERS
            if p != faction and relation(game, faction, p) < -15]


# ── treaties ───────────────────────────────────────────────────────────────

def has_treaty(game, faction: str) -> bool:
    return faction in ensure(game).treaties


def treaty_bonus(game) -> float:
    """Signed treaties make everyone slightly easier to trade with."""
    return 0.03 * len(ensure(game).treaties)


# ── acting: `sim/diplomacy_acts.py` ─────────────────────────────────────


def agenda_bonus(game, faction: str, commodity: str) -> float:
    """Selling a power what it is chronically short of is worth extra standing."""
    agenda = AGENDAS.get(faction)
    return 1.6 if agenda and agenda.wants == commodity else 1.0


# ── the Concord condition ──────────────────────────────────────────────────

def concord_progress(game) -> dict:
    """Kin with four powers, and those powers not at each other's throats."""
    kin = [p for p in POWERS if game.rep.get(p, 0) >= CONCORD_STANDING]
    pairs = [(a, b) for i, a in enumerate(POWERS) for b in POWERS[i + 1:]]
    at_peace = [(a, b) for a, b in pairs if relation(game, a, b) >= CONCORD_RELATION]
    return {"kin": kin, "kin_need": len(POWERS),
            "peace": at_peace, "peace_need": len(pairs),
            "done": len(kin) == len(POWERS) and len(at_peace) == len(pairs)}


def summary(game) -> dict:
    state = ensure(game)
    return {"treaties": list(state.treaties),
            "relations": {f"{a}|{b}": relation(game, a, b)
                          for i, a in enumerate(POWERS) for b in POWERS[i + 1:]}}
