"""Running the powers' own initiatives.

A venture is created, runs for a season or two, and resolves whether or not the
player did anything. Backing or opposing one moves the odds and costs standing
with somebody — there is no neutral way to be involved.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from ..core.save import register
from ..data.ventures import (BASE_ODDS, MAX_PER_POWER, ONSET_PER_MONTH,
                             RIGHT_BACKED, RIGHT_OPPOSED, SWAY,
                             VENTURES, VENTURES_BY_ID)
from ..data.diplomacy import AGENDAS
from ..data.factions import FACTIONS_BY_ID
from . import diplomacy as dip
from . import exchequer
from . import territory
from . import loyalty
from . import market as market_sim
from . import war as war_sim

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
    """Systems a power could plausibly take.

    This used to exclude anywhere the player held a colony, so the powers
    politely declined to contest your ground and the most interesting thing
    an empire game has to offer never happened. They will annex it now; what
    that means for the holding is `sim/territory.py`.
    """
    # Empty ground, plus anything held by somebody this power is at war with.
    # Until `sim/war` existed only the first clause was here, and the sector's
    # map could therefore fill in but never change hands: measured over 1,800
    # days across three seeds, 0 systems were ever taken from another power and
    # 0 ports ever changed flag.
    open_ground = [s for s in game.galaxy.systems
                   if s.faction is None and s.bloom < 0.5]
    return open_ground + [s for s in war_sim.spoils(game, power)
                          if s.bloom < 0.5 and s not in open_ground]


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
        # **A power at war goes for its enemy's quays, not for empty space.**
        # Merely making them claimable was not enough: measured over ten
        # sectors and 3,600 days, 46 of 49 annexations still landed on a
        # system with no port at all, because the open ground outnumbers the
        # spoils about three to one and the pick was uniform. Conquest is the
        # point of a war; expansion is what a power does the rest of the time.
        spoils = [s for s in war_sim.spoils(game, power) if s.bloom < 0.5]
        place = rng.pick(spoils or options).id

    # **Somebody has to pay for it.** A venture used to cost its sponsor
    # nothing at all, so a power stripped of every port ran the same number of
    # initiatives as one holding half the sector. The stake comes out of the
    # purse last, once the venture is known to be well formed, so a power is
    # never charged for an initiative it then declines to start.
    if not exchequer.stake(game, power):
        return None
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
        # A power with money to burn is a busier power, and one that cannot
        # find the stake is not restless at all. This is the sink that stops a
        # treasury growing forever with nothing to spend it on.
        if not rng.chance(chance * exchequer.appetite(game, power)):
            continue
        venture = start(game, rng, power)
        if venture is not None:
            events.append(("", describe(game, venture,
                                        venture.definition.premise)))
    return events


# ── the player leaning on it ───────────────────────────────────────────────

def hulls(game, power: str) -> int:
    """Completed levies. A power with more hulls gets its way more often."""
    return int(getattr(game, "faction_power", {}).get(power, 0))


def odds(game, venture) -> float:
    """How likely this is to come off, given who is leaning on it."""
    chance = BASE_ODDS
    if venture.stance == "backed":
        chance += SWAY
    elif venture.stance == "opposed":
        chance -= SWAY
    # A levy that came off is not a number in a save file: the hulls it bought
    # make everything that power tries next a little easier.
    chance += min(0.18, hulls(game, venture.power) * 0.06)
    # A power nobody can stand has a harder time of everything.
    standing = sum(dip.relation(game, venture.power, p)
                   for p in dip.POWERS if p != venture.power)
    chance += max(-0.12, min(0.12, standing / 600.0))
    return max(0.05, min(0.95, chance))


def preview(game, venture, stance: str) -> dict:
    """What taking this side would do, before you take it.

    The panel showed the odds as they stood and two buttons. It never said
    that pressing one takes a 51% venture to 81% and the other to 21% — a
    thirty-point swing either way, which is the entire reason to intervene.
    It stated what backing costs and bought, and said nothing at all about
    what opposing costs, or about what being right is worth afterwards.

    Everything here is read from the same constants `_resolve` reads.
    """
    kind = venture.definition
    was = venture.stance
    try:
        venture.stance = "backed" if stance == "back" else "opposed"
        after = odds(game, venture)
    finally:
        venture.stance = was

    out = {"stance": stance, "odds_now": odds(game, venture),
           "odds_after": after,
           "credits": -kind.back_cost if stance == "back" else 0,
           "rep": {}, "if_right": {}}
    move = kind.back_rep if stance == "back" else kind.oppose_rep
    out["rep"][venture.power] = float(move)
    if venture.other:
        out["rep"][venture.other] = -move * 0.6
    if stance == "back":
        out["if_right"][venture.power] = RIGHT_BACKED
    else:
        for power in dip.POWERS:
            if power != venture.power \
                    and dip.relation(game, power, venture.power) < 0:
                out["if_right"][power] = RIGHT_OPPOSED
    return out


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
        game.adjust_rep(venture.power, RIGHT_BACKED)
    elif venture.stance == "opposed" and not venture.succeeded:
        for power in dip.POWERS:
            if power != venture.power \
                    and dip.relation(game, power, venture.power) < 0:
                game.adjust_rep(power, RIGHT_OPPOSED)
    return events


def _apply(game, venture, rng) -> list[tuple[str, str]]:
    """The world after a venture that came off."""
    kind = venture.definition
    out: list[tuple[str, str]] = []

    if kind.id == "annex" and venture.place is not None:
        system = game.galaxy.systems[venture.place]
        held = getattr(system, "port", None)
        held = held.faction if held is not None else None
        taken = held is not None and war_sim.at_war(game, venture.power, held)
        if system.faction is None or taken:
            system.faction = venture.power
            if taken:
                # **A war moves the berth, not only the register.** Annexing
                # empty ground leaves `port.faction` alone on purpose — see
                # `exchequer.holdings`, which counts a power's income off the
                # quay and not off the claim — but taking a system from
                # somebody you are fighting is taking the quay, and that is
                # the whole of how a war reaches a captain who never fires:
                # the counter that cleared you last month now answers to
                # somebody who has your grudge on file.
                system.port.faction = venture.power
                out.append(("warn", f"{system.name} has struck its colours. "
                                    "The quay answers to somebody else now."))
            else:
                out.append(("", f"{system.name} is on the register now."))
            # If you hold ground there, this is not a news item, it is a
            # question somebody is waiting on an answer to.
            demand = territory.confront(game, system, venture.power)
            if demand:
                # `holdings` used to be set here too, and read by nobody:
                # `territory.holdings_in` is the live count, and a copy taken at
                # the moment of the demand can disagree with it the moment a
                # colony is lost. Deleted rather than wired up.
                game.demand = territory.Demand(
                    system_id=system.id, power=venture.power,
                    worth=round(demand["worth"]))
                out.append(("warn", f"{FACTIONS_BY_ID[venture.power].short} "
                                    f"wants to know about your holding at "
                                    f"{system.name}."))
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
        out.append(("", f"{FACTIONS_BY_ID[venture.power].short} is a harder "
                        "power to argue with than it was."))
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
