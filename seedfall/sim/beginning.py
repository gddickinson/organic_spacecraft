"""Turning an opening choice into a chronicle, and saying what it will do first.

Two rules govern this module.

The first is the project's: a screen that offers a commitment must state its
consequence. `preview()` is that statement, and `test_beginnings.py` builds the
game and compares — so the opening screen cannot drift from what it opens.

The second is narrower and matters more to the suite: **`begin(default())` must
be exactly the game as it shipped.** Three hundred and seventy-four checks are
written against that opening. If choosing nothing quietly changed it, every one
of them would still pass while measuring something else, which is the worst
outcome available.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.rng import RNG
from ..core.save import register
from ..data.beginnings import (CREW_SLOTS, DEFAULT_HULL, ORIGINS_BY_ID,
                               POSTINGS_BY_ID, STOCKS_BY_ID)
from ..data.chassis import CHASSIS, CHASSIS_BY_ID
from ..data.factions import FACTIONS
from ..data.hull_types import ACCEPTS
from ..data.parts import PARTS, PARTS_BY_ID
from . import crew as crew_sim


@register
@dataclass
class Choices:
    """What the player picked. Defaults reproduce the game as it shipped."""
    stock: str = "wet"
    origin: str = "surveyor"
    hull: str = "navis"
    posting: str = "charter"
    crew: tuple = ()             # station ids; empty means the standard crew
    name: str = "Patient Increment"

    def resolved(self) -> tuple:
        return (STOCKS_BY_ID[self.stock], ORIGINS_BY_ID[self.origin],
                POSTINGS_BY_ID[self.posting])


def default() -> Choices:
    return Choices()


def is_default(choices: Choices) -> bool:
    return (choices.stock, choices.origin, choices.hull, choices.posting,
            tuple(choices.crew)) == ("wet", "surveyor", "navis", "charter", ())


# ── what each axis allows ──────────────────────────────────────────────────

def origins_for(stock_id: str) -> list:
    from ..data.beginnings import ORIGINS
    return [o for o in ORIGINS if stock_id in o.stocks]


def hulls_for(stock_id: str, origin_id: str) -> list:
    """Starting hulls: the tier the stock can crew, and can afford to open in.

    Restricted to tier-one hulls on purpose. Letting a new captain open in a
    battleship is not an opening choice, it is a different game, and the ones
    that matter — what will graft to it, what it needs to stay alive — are the
    same at every tier.
    """
    stock = STOCKS_BY_ID[stock_id]
    origin = ORIGINS_BY_ID[origin_id]
    known = set(origin.tech)
    out = []
    for chassis in CHASSIS:
        if chassis.family not in stock.families:
            continue
        if chassis.tier not in ("courier", "explorer", "light"):
            continue
        if chassis.tech and chassis.tech not in known and \
                chassis.tech not in _STARTING_TECH():
            continue
        out.append(chassis)
    return out or [CHASSIS_BY_ID[DEFAULT_HULL.get(stock_id, "navis")]]


def _STARTING_TECH() -> list:
    from ..data.tech import STARTING_TECH
    return list(STARTING_TECH)


def crew_slots(stock_id: str) -> int:
    return CREW_SLOTS.get(stock_id, 3)


def fit_for(chassis, known=None) -> list:
    """A working outfit for a hull nobody has chosen parts for yet.

    One part per slot, cheapest first among what grafts to the frame. It is
    *not* filtered by what the captain has researched, because a hull arrives
    with its parts already in it — see `tech_of` for the invariant that keeps
    that from becoming a trap. Filtering here instead left a Dry Choir opening
    with no drive at all: every fabricated drive is gated behind a technology
    a cantor does not start with.
    """
    known = set(known or ())
    fitted, used = [], {}
    for part in sorted(PARTS, key=lambda p: p.cost.get("credits", 0)):
        if part.family not in ACCEPTS.get(chassis.family, ()):
            continue
        cap = chassis.slots.get(part.slot, 0)
        if used.get(part.slot, 0) >= cap:
            continue
        used[part.slot] = used.get(part.slot, 0) + 1
        fitted.append(part.id)
    return fitted


def tech_of(fitted) -> list:
    """The technologies behind an outfit.

    The invariant: **you hold the technology for everything bolted to your
    hull.** Without it, removing a part in the yard is irreversible, because
    `parts_available` filters by what you have unlocked — which is exactly how
    pulling the Reaction-Mass Organ on day one left the drive slot permanently
    empty in the shipped game. Enforcing it structurally means no opening can
    ever reintroduce that, however the hulls change.
    """
    return [PARTS_BY_ID[pid].tech for pid in fitted
            if PARTS_BY_ID.get(pid) and PARTS_BY_ID[pid].tech]


# ── the statement of consequence ───────────────────────────────────────────

def preview(choices: Choices) -> dict:
    """Everything the opening will hand you, before it hands it to you."""
    stock, origin, posting = choices.resolved()
    chassis = CHASSIS_BY_ID.get(choices.hull) or \
        CHASSIS_BY_ID[DEFAULT_HULL.get(choices.stock, "navis")]

    standing = {}
    for faction in FACTIONS:
        if faction.hidden:
            continue
        standing[faction.id] = float(faction.start_rep) + origin.rep.get(
            faction.id, 0)

    known = set(_STARTING_TECH()) | set(origin.tech)
    if not is_default(choices):
        known |= set(tech_of(fit_for(chassis, known)))
    return {
        "stock": stock, "origin": origin, "posting": posting,
        "chassis": chassis,
        "credits": max(0, 18000 + origin.credits),
        "tech": sorted(known),
        "standing": standing,
        "cargo": dict(_opening_hold(origin)),
        "evidence": dict(origin.evidence),
        "trait": origin.trait,
        "flags": dict(origin.flags),
        "crew": crew_slots(choices.stock),
        "fx": dict(stock.fx),
    }


def _opening_hold(origin) -> dict:
    hold = {"ore": 12, "volatiles": 20, "biomass": 18}
    for key, amount in origin.stores.items():
        hold[key] = hold.get(key, 0) + amount
    return hold


def start_system(galaxy, posting_id: str):
    """The port this posting opens at."""
    posting = POSTINGS_BY_ID[posting_id]
    if posting.faction is None:
        loose = [s for s in galaxy.systems
                 if s.port and getattr(s.port, "independent", False)]
        return (loose or [s for s in galaxy.systems if s.port])[0]
    theirs = [s for s in galaxy.systems
              if s.faction == posting.faction and s.port]
    if not theirs:
        return next((s for s in galaxy.systems if s.port), galaxy.systems[0])
    if posting.capital:
        return next((s for s in theirs if s.port.capital), theirs[0])
    return theirs[0]


def apply(game, choices: Choices, rng) -> None:
    """Stamp the opening onto a freshly built game.

    Called by `new_game` after the standard construction, so the default path
    applies a set of no-op deltas and leaves the shipped opening untouched.
    """
    stock, origin, _posting = choices.resolved()
    game.beginning = choices

    for faction_id, delta in origin.rep.items():
        game.rep[faction_id] = game.rep.get(faction_id, 0) + delta
    for tech in origin.tech:
        if tech not in game.research.unlocked:
            game.research.unlocked.append(tech)
    game.credits = max(0, game.credits + origin.credits)
    for key, amount in origin.stores.items():
        game.ship.cargo[key] = game.ship.cargo.get(key, 0) + amount
    for kind, amount in origin.evidence.items():
        from . import inquiry as inquiry_sim
        inquiry_sim.add(game.research, kind, amount)
    # Whatever ended up bolted to the hull, the captain knows how it works.
    for tech in tech_of(game.ship.fitted):
        if tech not in game.research.unlocked:
            game.research.unlocked.append(tech)
    game.flags.update(origin.flags)
    if stock.fx:
        game.stock_fx = dict(stock.fx)

    if choices.crew:
        game.officers = [crew_sim.make_officer(rng, station)
                         for station in choices.crew]
    game.recompute()


def blurb(choices: Choices) -> str:
    """One line for the log, so the chronicle opens by saying who you are."""
    stock, origin, posting = choices.resolved()
    return (f"{origin.name}, {stock.name.lower()} stock, out of "
            f"{posting.name}.")
