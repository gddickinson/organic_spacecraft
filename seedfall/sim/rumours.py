"""Hearing things, and finding out whether they were true.

A rumour is generated against a system that could plausibly bear it out, and
carries a truth value decided when it is created rather than when you arrive —
so the sector does not rearrange itself around whatever you happened to be
told. Arriving resolves it either way.

**Where you heard it decides how much it is worth.** `Rumour.heard_at` was
recorded from the day rumours were written and read by nothing: truth was
`not rng.chance(kind.unreliable)`, a per-kind coin flip. A story about the far
side of the sector, told at a lonely outpost by people who have never been
within forty light-years of it, was exactly as good as one about the next star
over told at a Fleet Hub where a dozen hulls a week put in.

Word travels by ship, so `provenance` is about distance and traffic — and it is
**one door**: the truth roll, the trust the desk shows, and the price all read
it. A price that did not follow the provenance would be charging for volume.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from ..core.save import register
from ..data.rumours import (BEST_ODDS, FAR_LY, FAR_UNRELIABLE, KINDS,
                            KINDS_BY_ID, LOCAL_LY, PER_PORT, PRICE_FLOOR,
                            PRICE_RANGE, QUAY_TRUST, WORST_ODDS)
from ..world.galaxy import distance

_uid = itertools.count(1)


@register
@dataclass
class Rumour:
    id: int
    kind: str
    system_id: int
    heard_at: int          # system id where you were told
    true: bool = False
    resolved: bool = False
    paid: bool = False

    @property
    def definition(self):
        return KINDS_BY_ID[self.kind]


def ensure(game) -> list:
    if getattr(game, "rumours", None) is None:
        game.rumours = []
    return game.rumours


def held(game) -> list:
    return [r for r in ensure(game) if not r.resolved]


def about(game, system_id: int) -> list:
    return [r for r in held(game) if r.system_id == system_id]


def _plausible(game, kind, system) -> bool:
    """Whether this system could bear the claim out at all."""
    if system.id == game.location_id:
        return False
    if kind.id == "bloom":
        return system.bloom < 0.35          # a claim about growth nobody filed
    if kind.id == "relic":
        return bool(system.bodies)
    return True


def provenance(game, rumour) -> dict:
    """Where this story came from, and what that is worth.

    The one door onto it. `_truth` rolls against `unreliable`, the desk shows
    `trust`, and `price_of` charges for it — three readings of one figure
    rather than three opinions about it.
    """
    kind = rumour.definition
    quay = game.galaxy.systems[rumour.heard_at]
    target = game.galaxy.systems[rumour.system_id]
    span = distance(quay, target)
    # How far it has come, as a share of the way from "local business" to
    # "somebody's cousin heard it somewhere".
    far = max(0.0, min(1.0, (span - LOCAL_LY) / (FAR_LY - LOCAL_LY)))
    level = quay.port.level if quay.port else 0
    unreliable = kind.unreliable * (1.0 + (FAR_UNRELIABLE - 1.0) * far)
    unreliable = max(1.0 - BEST_ODDS,
                     min(1.0 - WORST_ODDS, unreliable - QUAY_TRUST * level))
    return {
        "quay": quay,
        "target": target,
        "light_years": span,
        "far": far,
        "level": level,
        "unreliable": unreliable,
        "trust": 1.0 - unreliable,
        "words": _sourced(far, level),
    }


def _sourced(far: float, level: int) -> str:
    """How the desk describes where a story came from."""
    if far < 0.25:
        place = "local business — somebody here has been"
    elif far < 0.6:
        place = "a few jumps out, secondhand"
    else:
        place = "the far side of the sector, through too many hands"
    if level >= 3:
        quay = "and this is a hub, so the traffic is worth something"
    elif level >= 2:
        quay = "and enough hulls call here to have heard it twice"
    elif level >= 1:
        quay = "and this quay hears from whoever last docked"
    else:
        quay = "and there is no quay here to hear anything"
    return f"{place}, {quay}"


def price_of(game, rumour) -> int:
    """What being told it properly costs. Follows the source, not the volume."""
    trust = provenance(game, rumour)["trust"]
    return max(1, round(rumour.definition.price
                        * (PRICE_FLOOR + PRICE_RANGE * trust)))


def _truth(game, rumour, rng) -> bool:
    """Whether this story is true. Decided when it is told, and pure.

    No side effects here: `circulating()` runs every time the desk is drawn,
    and a truth test that changed the galaxy would seed bloom and bury relics
    across the sector merely because somebody looked at a noticeboard.
    """
    return not rng.chance(provenance(game, rumour)["unreliable"])


def plant(game, rumour, rng) -> bool:
    """Make a true story true, once you have actually taken it up.

    Testing a claim against whatever the galaxy happened to generate made
    almost every rumour false and the whole system worthless, so a true one
    puts the thing it describes where it says it is.
    """
    if not rumour.true:
        return False
    kind = rumour.definition
    system = game.galaxy.systems[rumour.system_id]

    if kind.id == "bloom":
        system.bloom = max(system.bloom, rng.float(0.06, 0.16))
        return True
    if kind.id == "relic":
        bare = [b for b in system.bodies if b.relic is None]
        if not bare:
            return any(b.relic for b in system.bodies)
        from ..data.xenotech import XENOTECH
        rng.pick(bare).relic = rng.pick(XENOTECH).id
        return True
    if kind.id == "rich":
        bodies = [b for b in system.bodies if b.resources]
        if not bodies:
            return False
        body = rng.pick(bodies)
        for key in list(body.resources):
            body.resources[key] = min(1.0, body.resources[key] * rng.float(1.4, 1.9))
        return True
    if kind.id == "wreck":
        bodies = [b for b in system.bodies if b.anomaly is None]
        if not bodies:
            return False
        from ..world.planets import Anomaly
        rng.pick(bodies).anomaly = Anomaly(
            "hull", "Derelict hull", "steel", 30,
            "A hull that stopped under its own power and was never come back "
            "for. The underwriters paid out; nobody swept it.")
        return True
    if kind.id == "quiet":
        if system.note is None:
            system.note = ("The filed charts for this system are wrong in ways "
                           "that took a while to notice.")
        return True
    return True


def circulating(game, system, rng) -> list:
    """What is being said at this port. Stable for a given port and day."""
    if not system.port:
        return []
    candidates = [s for s in game.galaxy.systems if s.id != system.id]
    if not candidates:
        return []
    out = []
    used: set[str] = set()
    for _index in range(PER_PORT * 3):
        if len(out) >= PER_PORT:
            break
        pick = rng.pick(KINDS)
        target = rng.pick(candidates)
        # One of each kind at a port: three "nobody goes there" in a row reads
        # like a bug in the generator rather than a rumour mill.
        if pick.id in used or not _plausible(game, pick, target):
            continue
        used.add(pick.id)
        if any(r.kind == pick.id and r.system_id == target.id
               for r in ensure(game)):
            continue
        # Built before the roll, because whether it is true now depends on
        # where it is being told — which is a property of the rumour.
        story = Rumour(id=next(_uid), kind=pick.id, system_id=target.id,
                       heard_at=system.id)
        story.true = _truth(game, story, rng)
        out.append(story)
    return out


def take(game, rumour, paid: bool = False) -> None:
    """Take a story up. Only now does the sector commit to it being true."""
    rumour.paid = paid
    if rumour.true:
        rumour.true = plant(game, rumour,
                            game.rng(f"plant-{rumour.kind}-{rumour.system_id}"))
    ensure(game).append(rumour)
    kind = rumour.definition
    system = game.galaxy.systems[rumour.system_id]
    game.add_log(f"Word going round: {kind.name.lower()} at {system.name}.", "")


def resolve(game, system_id: int) -> list[tuple[str, str]]:
    """Arriving somewhere settles anything said about it."""
    events = []
    for rumour in about(game, system_id):
        rumour.resolved = True
        kind = rumour.definition
        if rumour.true:
            events.append(("good", f"{kind.name}: {kind.confirmed}"))
        else:
            events.append(("", f"{kind.name}: {kind.denied}"))
    return events


def summary(game) -> dict:
    all_of = ensure(game)
    done = [r for r in all_of if r.resolved]
    return {"held": len(held(game)), "resolved": len(done),
            "true": len([r for r in done if r.true]),
            "paid": len([r for r in done if r.paid]),
            "paid_true": len([r for r in done if r.paid and r.true])}
