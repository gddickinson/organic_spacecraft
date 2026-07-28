"""Running the powers' own initiatives.

A venture is created, runs for a season or two, and resolves whether or not the
player did anything. Backing or opposing one moves the odds and costs standing
with somebody — there is no neutral way to be involved.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from ..core.save import register
from ..data.ventures import (BASE_ODDS, MAX_PER_POWER, ONSET_PER_MONTH, SWAY,
                             VENTURES, VENTURES_BY_ID)
from ..data.diplomacy import AGENDAS
from ..data.factions import FACTIONS_BY_ID
from . import diplomacy as dip
from . import loyalty
from . import market as market_sim

_uid = itertools.count(1)


@register
@dataclass
class Venture:
    id: int
    kind: str
    power: str
    other: str | None = None
    place: int | None = None
    until: int = 0
    stance: str = "none"        # none | backed | opposed
    resolved: bool = False
    succeeded: bool = False

    @property
    def definition(self):
        return VENTURES_BY_ID[self.kind]


def ensure(game) -> list:
    if getattr(game, "ventures", None) is None:
        game.ventures = []
    return game.ventures


def live(game) -> list:
    return [v for v in ensure(game) if not v.resolved]


def by_power(game, power: str) -> list:
    return [v for v in live(game) if v.power == power]


def describe(game, venture, template: str) -> str:
    place = (game.galaxy.systems[venture.place].name
             if venture.place is not None else "somewhere")
    return template.format(
        power=FACTIONS_BY_ID[venture.power].short,
        other=FACTIONS_BY_ID[venture.other].short if venture.other else "them",
        place=place)


# ── starting one ───────────────────────────────────────────────────────────

def _claimable(game, power: str) -> list:
    """Systems a power could plausibly take, excluding anywhere you hold."""
    held = {c.system_id for c in game.colonies}
    return [s for s in game.galaxy.systems
            if s.faction is None and s.id not in held and s.bloom < 0.5]


def _open_to(game, power: str, kind) -> bool:
    if kind.needs_place and not _claimable(game, power):
        return False
    return True


def start(game, rng, power: str):
    """Begin one venture for this power, if anything suits."""
    pool = [k for k in VENTURES if _open_to(game, power, k)]
    if not pool:
        return None
    # Prefer something nobody is already doing: four powers all running
    # embargoes at once reads as a broken generator rather than a tense sector.
    running = {v.kind for v in live(game)}
    fresh = [k for k in pool if k.id not in running]
    kind = rng.weighted([(k.weight, k) for k in (fresh or pool)])
    other = None
    place = None
    if kind.needs_other:
        rivals = [p for p in dip.POWERS if p != power]
        if not rivals:
            return None
        # Powers court those they already tolerate and censure those they do not.
        if kind.id == "courtship":
            rivals.sort(key=lambda p: -dip.relation(game, power, p))
        else:
            rivals.sort(key=lambda p: dip.relation(game, power, p))
        other = rivals[0]
    if kind.needs_place:
        options = _claimable(game, power)
        if not options:
            return None
        place = rng.pick(options).id

    venture = Venture(id=next(_uid), kind=kind.id, power=power, other=other,
                      place=place, until=game.day + rng.int(*kind.days))
    ensure(game).append(venture)
    return venture


def tick(game, days: float, rng) -> list[tuple[str, str]]:
    """Start and resolve ventures. Returns log events."""
    events: list[tuple[str, str]] = []

    for venture in list(live(game)):
        if game.day >= venture.until:
            events.extend(_resolve(game, venture, rng))

    chance = ONSET_PER_MONTH * (days / 30.0)
    for power in dip.POWERS:
        if len(by_power(game, power)) >= MAX_PER_POWER:
            continue
        if not rng.chance(chance):
            continue
        venture = start(game, rng, power)
        if venture is not None:
            events.append(("", describe(game, venture,
                                        venture.definition.premise)))
    return events


# ── the player leaning on it ───────────────────────────────────────────────

def odds(game, venture) -> float:
    """How likely this is to come off, given who is leaning on it."""
    chance = BASE_ODDS
    if venture.stance == "backed":
        chance += SWAY
    elif venture.stance == "opposed":
        chance -= SWAY
    # A power nobody can stand has a harder time of everything.
    standing = sum(dip.relation(game, venture.power, p)
                   for p in dip.POWERS if p != venture.power)
    chance += max(-0.12, min(0.12, standing / 600.0))
    return max(0.05, min(0.95, chance))


def can_intervene(game, venture, stance: str) -> tuple[bool, str]:
    kind = venture.definition
    if venture.resolved:
        return False, "It is already settled."
    if venture.stance != "none":
        return False, "You have already taken a side in this."
    if stance == "back" and game.credits < kind.back_cost:
        return False, f"Backing it costs {kind.back_cost:,} credits."
    return True, ""


def intervene(game, venture, stance: str) -> dict:
    """Back or oppose. Both cost you something with somebody."""
    ok, why = can_intervene(game, venture, stance)
    if not ok:
        return {"ok": False, "why": why}
    kind = venture.definition

    if stance == "back":
        game.credits -= kind.back_cost
        venture.stance = "backed"
        game.adjust_rep(venture.power, kind.back_rep)
        if venture.other:
            game.adjust_rep(venture.other, -kind.back_rep * 0.6)
        loyalty.record(game, "backed_venture")
    else:
        venture.stance = "opposed"
        game.adjust_rep(venture.power, kind.oppose_rep)
        if venture.other:
            game.adjust_rep(venture.other, -kind.oppose_rep * 0.6)
        loyalty.record(game, "opposed_venture")

    game.add_log(f"{FACTIONS_BY_ID[venture.power].short}'s "
                 f"{kind.name.lower()}: you have "
                 f"{'backed' if stance == 'back' else 'opposed'} it.", "")
    return {"ok": True, "venture": venture}


# ── what happens when it lands ─────────────────────────────────────────────

def _resolve(game, venture, rng) -> list[tuple[str, str]]:
    kind = venture.definition
    venture.resolved = True
    venture.succeeded = rng.chance(odds(game, venture))
    text = describe(game, venture,
                    kind.success if venture.succeeded else kind.failure)
    events = [("good" if venture.succeeded else "warn", text)]

    if venture.succeeded:
        events.extend(_apply(game, venture, rng))

    # Having been right about it is worth something either way.
    if venture.stance == "backed" and venture.succeeded:
        game.adjust_rep(venture.power, 8)
    elif venture.stance == "opposed" and not venture.succeeded:
        for power in dip.POWERS:
            if power != venture.power and dip.relation(game, power, venture.power) < 0:
                game.adjust_rep(power, 5)
    return events


def _apply(game, venture, rng) -> list[tuple[str, str]]:
    """The world after a venture that came off."""
    kind = venture.definition
    out: list[tuple[str, str]] = []

    if kind.id == "annex" and venture.place is not None:
        system = game.galaxy.systems[venture.place]
        if system.faction is None:
            system.faction = venture.power
            out.append(("", f"{system.name} is on the register now."))
    elif kind.id == "blockade" and venture.other:
        dip.shift_relation(game, venture.power, venture.other, -12)
        agenda = AGENDAS.get(venture.other)
        good = agenda.wants if agenda else None
        target = next((s for s in game.galaxy.systems
                       if s.market and s.faction == venture.other), None)
        if good and target:
            market_sim.all_shocks(game).append(market_sim.Shock(
                id=next(_uid) + 90000, kind="rearm", system_id=target.id,
                commodity=good, until=game.day + 150))
            market_sim.apply_to_markets(game)
    elif kind.id == "courtship" and venture.other:
        dip.shift_relation(game, venture.power, venture.other, 26)
    elif kind.id == "censure" and venture.other:
        dip.shift_relation(game, venture.power, venture.other, -15)
        for power in dip.POWERS:
            if power not in (venture.power, venture.other):
                dip.shift_relation(game, power, venture.other, -8)
    elif kind.id == "levy":
        state = getattr(game, "faction_power", None)
        if state is None:
            state = game.faction_power = {}
        state[venture.power] = state.get(venture.power, 0) + 1
    elif kind.id == "concession" and venture.place is not None:
        system = game.galaxy.systems[venture.place]
        if system.faction is None:
            system.faction = venture.power
    return out


def summary(game) -> dict:
    done = [v for v in ensure(game) if v.resolved]
    return {"live": len(live(game)), "resolved": len(done),
            "backed": len([v for v in done if v.stance == "backed"]),
            "opposed": len([v for v in done if v.stance == "opposed"])}
