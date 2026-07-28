"""Officers.

Six bridge roles, straight out of the old survey-ship convention: science,
navigation, engineering, medicine, communications, tactical.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.save import register
from ..data import convictions
from ..data import lineages
from . import loyalty
from ..data.lore import CREW_FIRST, CREW_LAST, CREW_ROLES

_uid = itertools.count(1)

#: (id, name, note, effect key, magnitude)
TRAITS = [
    ("charter", "Charter-raised", "Grew up under the licence regime", "diplomacy", 0.04),
    ("yards", "Yards-trained", "Learned on fabricated hulls", "repair", 0.05),
    ("freehold", "Freehold-born", "Knows what things are really worth", "trade", 0.05),
    ("veteran", "Bloom veteran", "Was at Kessel's Reach and came back", "tactical", 0.05),
    ("wetwired", "Wet-wired", "Runs a direct bioelectric interface", "accuracy", 0.03),
    ("quiet", "Quiet", "Says little; misses less", "scan", 0.04),
    ("reckless", "Reckless", "Fast, and expensive about it", "evade", 0.04),
]


@register
@dataclass
class Officer:
    id: int
    name: str
    role: str
    role_name: str
    stat: str
    note: str
    level: int
    wage: int
    xp: int = 0
    trait_id: str | None = None
    trait_name: str = ""
    trait_note: str = ""
    conviction: str | None = None
    loyalty: float = convictions.START
    #: What they are made of, and how far through their run they are. See
    #: `data/lineages.py` — everyone used to be the same thing and immortal.
    lineage: str | None = None
    age: float | None = None
    #: Fractional levels shed to decline, carried so it is a slope not a step.
    wear: float = 0.0
    retired: bool = False

    @property
    def label(self) -> str:
        return f"{self.name} — {self.role_name}"


def make_officer(rng, role_id: str | None = None, min_level: int = 1) -> Officer:
    role = next((r for r in CREW_ROLES if r[0] == role_id), None) or rng.pick(CREW_ROLES)
    level = rng.weighted([(5, min_level), (4, min_level + 1),
                          (2, min_level + 2), (1, min_level + 3)])
    trait = rng.pick(TRAITS) if rng.chance(0.55) else None
    officer = Officer(
        id=next(_uid),
        name=f"{rng.pick(CREW_FIRST)} {rng.pick(CREW_LAST)}",
        role=role[0], role_name=role[1], stat=role[2], note=role[3],
        level=level, wage=40 + level * 55 + (25 if trait else 0),
        trait_id=trait[0] if trait else None,
        trait_name=trait[1] if trait else "",
        trait_note=trait[2] if trait else "",
    )
    loyalty.assign(rng, officer)
    return officer


def starting_crew(rng) -> list[Officer]:
    """A starting bridge: three core roles, modest experience.

    Names are made distinct: drawing three at random from a list of this size
    puts two Mareks on the same bridge about one game in ten, which reads as a
    bug even though it is only chance.
    """
    crew = [make_officer(rng, "science", 2),
            make_officer(rng, "nav", 2),
            make_officer(rng, "engineer", 2)]
    seen: set[str] = set()
    for officer in crew:
        first = officer.name.split()[0]
        guard = 0
        while first in seen and guard < 20:
            first = rng.pick(CREW_FIRST)
            guard += 1
        seen.add(first)
        officer.name = f"{first} {officer.name.split(' ', 1)[1]}"
    return crew


def hiring_lineage(rng) -> str:
    """What a quay's next candidate is made of.

    Mostly wet, because most of the Verge is. A graft turns up often enough to
    matter: they cost more to keep and they outlive the rest of the bridge by
    seventy years, which is a real reason to take one on before a long run.
    """
    pool = lineages.recruitable()
    return rng.weighted([(6 if l.id == "wet" else 2, l.id) for l in pool])


def recruit_pool(rng, port_level: int) -> list[Officer]:
    """Candidates on offer. Bigger ports attract better officers."""
    out = []
    for _ in range(2 + port_level):
        officer = make_officer(rng, None, port_level)
        # Left unset an officer is assumed to be of the captain's own stock,
        # which is right for the crew you launched with and wrong for a quay.
        officer.lineage = hiring_lineage(rng)
        out.append(officer)
    return out


def grant_xp(officers, stat: str, amount: float) -> list[Officer]:
    """Experience from doing the job. Levels cap at 6."""
    gained = []
    for o in officers:
        if stat != "*" and o.stat != stat:
            continue
        o.xp += amount
        need = o.level * 100
        if o.xp >= need and o.level < 6:
            o.xp -= need
            o.level += 1
            gained.append(o)
    return gained


def daily_wages(officers) -> float:
    return sum(o.wage for o in officers) / 30


def morale_tick(ship, days: float, paid: bool, breached: bool,
                morale_fx: float = 0.0) -> float:
    """Morale drifts toward a target set by pay, air and recent disasters."""
    target = 0.72 + morale_fx * 0.4
    if not paid:
        target -= 0.35
    if breached:
        target -= 0.30
    if ship.o2 < 0.5:
        target -= 0.25
    ship.morale += (target - ship.morale) * min(1.0, 0.08 * days)
    ship.morale = max(0.0, min(1.0, ship.morale))
    return ship.morale


# ── the berths ─────────────────────────────────────────────────────────────
# Signing somebody on and paying the bridge both spent credits from inside
# `berths_panel.py`, so neither could be done or measured without a screen.

def bonus_cost(officers) -> int:
    """What it costs to put a bonus round the bridge."""
    return int(sum(o.wage for o in officers) * 0.6)


def hire(game, officer) -> dict:
    """Sign an officer on. One station, one incumbent."""
    if any(x.stat == officer.stat for x in game.officers):
        return {"ok": False,
                "why": "That station is already crewed. Pay off the incumbent "
                       "first."}
    if game.credits < officer.wage:
        return {"ok": False, "why": "Not enough credits for the signing fee."}
    game.credits -= officer.wage
    game.officers.append(officer)
    game.add_log(f"{officer.name} signed on as {officer.role_name}.", "good")
    return {"ok": True, "officer": officer, "fee": officer.wage}


def pay_bonus(game) -> dict:
    """Money over the odds, and the bridge remembers it."""
    cost = bonus_cost(game.officers)
    if game.credits < cost:
        return {"ok": False, "why": "Not enough in the treasury for that."}
    game.credits -= cost
    loyalty.record(game, "bonus_paid")
    game.add_log("A bonus went round the bridge.", "good")
    return {"ok": True, "cost": cost}
