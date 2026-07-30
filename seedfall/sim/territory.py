"""Where your holdings and the powers' claims meet.

`ventures._claimable()` used to step around any system the player held a colony
in, and `colony.can_found()` never looked at who claimed a system at all. So
the powers would not contest your ground and you could squat on theirs, and the
most interesting thing an empire game has to offer never happened once.

A claim now lands on your holding and asks you a question, and planting inside
somebody's declared space is a priced act rather than a free one.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.save import register
from ..data.factions import FACTIONS_BY_ID
from ..data.territory import ANSWERS_BY_ID, LEVY_SHARE, TRESPASS, UNWELCOME
from . import allegiance
from . import loyalty

#: Yearly chance a defied power takes a holding off you.
SEIZURE_PER_YEAR = 0.22


@register
@dataclass
class Demand:
    """A power waiting on an answer about ground you hold.

    On the `Game` rather than the window, like every other thing a player can
    be in the middle of: a save taken between the annexation and the answer
    would otherwise lose the question and leave the holding in limbo.
    """
    #: `holdings` used to sit here as a count of what was at stake, set by
    #: nobody and read by nobody. `holdings_in(game, system_id)` is the live
    #: answer, and a stored copy that can disagree with it is the two-doors
    #: fault this project has found more often than any other.
    system_id: int
    power: str
    worth: float = 0.0
    over: bool = False


def claimant(game, system) -> str | None:
    """Which power has this system on its register, if any."""
    fid = getattr(system, "faction", None)
    if not fid:
        return None
    fac = FACTIONS_BY_ID.get(fid)
    if fac is None or fac.hostile or fac.hidden:
        return None
    return fid


def holdings_in(game, system_id: int) -> list:
    return [c for c in game.colonies if c.system_id == system_id]


# ── planting on somebody else's register ───────────────────────────────────

def trespass_cost(game, system) -> float:
    """Standing given up for planting here. Zero on unclaimed ground."""
    power = claimant(game, system)
    if power is None:
        return 0.0
    return TRESPASS


def welcome(game, system) -> tuple[bool, str]:
    """Whether the claimant will tolerate you planting at all."""
    power = claimant(game, system)
    if power is None:
        return True, ""
    if game.rep.get(power, 0) < UNWELCOME:
        short = FACTIONS_BY_ID[power].short
        return False, (f"{short} holds this system and thinks too little of "
                       "you to let you put anything down in it.")
    return True, ""


def charge_trespass(game, system) -> list[tuple[str, float]]:
    """Apply the cost of planting here. Returns what moved, for the log."""
    power = claimant(game, system)
    if power is None:
        return []
    cost = trespass_cost(game, system)
    game.adjust_rep(power, -cost)
    moved = [(power, cost)]
    # Their enemies rather enjoy it, which is the other half of taking sides.
    moved += [(other, -round(cost * sev * 0.4, 1))
              for other, sev in allegiance.offended_by(game, power)]
    for other, delta in moved[1:]:
        game.adjust_rep(other, -delta)
    return moved


# ── a claim landing on your holding ────────────────────────────────────────

def confront(game, system, power: str) -> dict | None:
    """A power has annexed a system you hold in. Returns the demand, or None."""
    held = holdings_in(game, system.id)
    if not held or claimant(game, system) is None:
        return None
    return {"system": system, "power": power, "colonies": held,
            "worth": sum(yearly_worth(game, c) for c in held)}


def yearly_worth(game, colony) -> float:
    """Roughly what a holding turns out in a year, in credits."""
    from . import works as works_sim
    from ..data.commodities import BY_ID
    total = 0.0
    for cid, rate in works_sim.yields_of(colony).items():
        good = BY_ID.get(cid)
        if good:
            total += rate * 365 * good.base * 0.55
    return total


def answer(game, system, power: str, choice: str) -> dict:
    """Pay, cede or refuse. Every one of them costs something different."""
    if choice not in ANSWERS_BY_ID:
        return {"ok": False, "why": "Not an answer."}
    held = holdings_in(game, system.id)
    if not held:
        # Nothing left to argue about — the Bloom or a seizure got there first.
        if game.demand is not None:
            game.demand.over = True
        return {"ok": False, "why": "You hold nothing there."}

    from . import grudge as grudge_sim
    where = system.name
    if choice == "levy":
        for col in held:
            col.tithe_to = power
            col.defiant = False
        game.adjust_rep(power, 3)
        grudge_sim.note(game, power, "trade",
                        f"you paid the levy on {where} rather than argue", 0.8,
                        tags=["politics", "territory"])
    elif choice == "cede":
        for col in held:
            body = next((b for b in system.bodies if b.id == col.body_id), None)
            if body:
                body.colony = None
        game.colonies = [c for c in game.colonies if c not in held]
        game.adjust_rep(power, 12)
        grudge_sim.note(game, power, "kindness",
                        f"you handed {where} over when we asked", 1.2,
                        tags=["politics", "territory"])
        loyalty.record(game, "colony_lost", scale=len(held))
    else:                                    # defy
        for col in held:
            col.tithe_to = None
            col.defiant = True
        game.adjust_rep(power, -18)
        allegiance.charge(game, power, -6)   # their enemies approve
        grudge_sim.note(game, power, "trespass",
                        f"you refused us {where} to our face", 1.5,
                        tags=["politics", "territory"])
        loyalty.record(game, "defied_power")

    if game.demand is not None:
        game.demand.over = True
    return {"ok": True, "choice": choice, "power": power,
            "colonies": list(held), "system": system}


# ── living with the answer ─────────────────────────────────────────────────

def collect_tithe(game, colony, gains: dict, days: float) -> dict:
    """Skim the levy off a holding's output before it reaches your stores."""
    power = getattr(colony, "tithe_to", None)
    if not power or not gains:
        return {}
    taken = {}
    for cid, amount in list(gains.items()):
        share = amount * LEVY_SHARE
        if share <= 0:
            continue
        gains[cid] = amount - share
        taken[cid] = share
    return taken


def seizures(game, days: float, rng) -> list:
    """Powers eventually come for what a defiant captain would not hand over."""
    lost = []
    for col in list(game.colonies):
        if not getattr(col, "defiant", False):
            continue
        system = game.galaxy.systems[col.system_id]
        power = claimant(game, system)
        if power is None:                    # the claim lapsed; so does the risk
            col.defiant = False
            continue
        if rng.chance(SEIZURE_PER_YEAR * days / 365):
            body = next((b for b in system.bodies if b.id == col.body_id), None)
            if body:
                body.colony = None
            game.colonies = [c for c in game.colonies if c is not col]
            lost.append((col, power))
    if lost:
        loyalty.record(game, "colony_lost", scale=len(lost))
    return lost


def status(game, colony) -> tuple[str, str]:
    """How a holding stands with whoever claims the ground under it."""
    system = game.galaxy.systems[colony.system_id]
    power = claimant(game, system)
    if power is None:
        return "yours outright", "chloro"
    short = FACTIONS_BY_ID[power].short
    if getattr(colony, "defiant", False):
        return f"held against {short}", "warn"
    if getattr(colony, "tithe_to", None):
        return f"levied by {short}", "osteo"
    return f"on {short}'s register", "dim"
