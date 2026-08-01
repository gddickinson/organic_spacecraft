"""A settled world's authority over the sky above it.

The last piece of the approach-control brief. `sim/control.py` gave a structure
the right to hail, warn, fire on and refuse a hull; `sim/forcing.py` gave the
hull an answer back; `sim/landing.py` said what happens when it reaches the
ground. **The worlds themselves had no say in any of it.** A hull could come
down on somebody's colony and the only thing that ever objected was gravity.

What makes this cheap is refusing to write a second ladder. Everything a world
does about a hull it does not want is already built, tested and tuned in
`sim/control.py` — the rungs, the patience that spends against closing rate,
the ward that climbs, the grievance that reaches the sector's memory. A world
gets all of it by answering two questions the same machinery already asks:

- **Is anybody in charge here?** `claim`.
- **How far up the ladder can they go?** `Claim.means`.

And "in charge" is not the same as "living there", which is the second half of
this. Three kinds of claim, in the order they are asked:

- **settled** — people are down there. What they can do is a reading of the
  colony economy: `settlement.maturity` and `colony.ward_at`, so a sector
  whose powers are thriving is a sector whose skies are harder.
- **worked** — nobody lives on it and somebody is taking something off it.
  A power that holds the system and a body with grades worth having is a
  defended body, because the thing being protected is the seam and not the
  ground. This is most of the sector's teeth: worlds nobody would call
  inhabited that will still not have you landing on them.
- **quiet** — a site nobody admits to. Rare, always on a body with nothing
  else on it, and it is the one thing in the game that **does not hail**:
  `Claim.floor` starts it at the ward, so the first you hear of it is being
  shot at. A captain who survives that has found something, and finding out
  what is a thread for the sector rather than a line in a readout.

And one thing genuinely differs from a station, which is the whole character
of the feature: **a world does not mind you in orbit, it minds you coming
down.** A station's question is which berth you were given; a world has no
berths and no opinion whatever about the sky above it, right up until a hull
starts down through it. `control.welcome` is where that is said, and it is the
only line in the game that distinguishes the two authorities.

The rest falls out. A world cannot sheer off — it is a planet. It cannot be
forced — there is no collar to cut. What it can do is shoot for the whole
descent, and a descent is the one manoeuvre in the game whose length is set by
gravity rather than by the pilot.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.rng import RNG
from . import colony as colony_sim
from . import settlement as settlement_sim
from . import territory as territory_sim

#: The rung a settled world can reach on its own — hailing and warning.
#:
#: Two, the same as a wayside quay, and for the same reason: people who can
#: talk to you can always talk to you. A colony that has only just been put
#: down has a radio and a grievance and nothing else.
SPEAKS = 2

#: How grown a settlement has to be before it has anything to shoot with.
#:
#: `settlement.maturity` runs from NEWBORN to 1 over its first years, and this
#: is comfortably past the middle: a settlement acquires batteries at about the
#: point it stops being an outpost, which is also the point it has something
#: worth defending.
ARMED_AT = 0.7

#: What being warded from the ground gets a world to.
#:
#: Three — fire, but never `repelled`. A world cannot come out after you. It
#: can only make the sky expensive, and a captain who is willing to wear that
#: gets down. Reserving the top rung for things that can manoeuvre is what
#: keeps a planet from being strictly better than a fleet.
ARMED = 3

#: How good a body's best seam has to be before whoever holds the system will
#: *shoot* to keep it, and before they will merely tell you to go away.
#:
#: A gradient and not a threshold, and the first draft was a threshold: one
#: number at 0.35 made **93% of the sector's bodies armed**, because every home
#: system has a claimant and the median best seam is 0.72. A sky where nearly
#: everything shoots is the same as a sky where nothing does — the captain
#: learns one rule and stops reading.
#:
#: So two figures, at about the upper and lower quartiles of what the generator
#: actually produces: a seam worth a battery, and a seam worth a radio call.
WORTH_KEEPING = 0.82
WORTH_WATCHING = 0.60

#: One unsettled, unworked body in this many hides something.
#:
#: Rare enough that a captain can fly for years without meeting one, common
#: enough that the sector has some. Derived from a stable seed rather than
#: rolled, so the same rock is the same secret across a reload — see `_quiet`.
QUIET_IN = 14

#: What a site nobody admits to answers with.
#:
#: Everything. The top of the ladder, and from a standing start: whatever is
#: down there would rather kill a witness than be looked at, which is what
#: `Claim.floor` is for and the only use of it in the game.
QUIET_MEANS = 4


@dataclass(frozen=True)
class Claim:
    """Somebody's say over the sky above one body."""

    who: str          # the power's id, or "" for a thing that owns itself
    name: str         # what the approach is told it is dealing with
    sort: str         # settled | worked | quiet
    means: int        # the top of `control.LADDER` it can reach
    floor: int = 0    # the rung it opens at, for something that does not hail


def _body_of(game, target):
    """The `Body` this contact stands for, or None."""
    if getattr(target, "kind", "") != "body":
        return None
    system = getattr(game, "system", None)
    index = getattr(target, "body_index", None)
    bodies = (getattr(system, "bodies", None) or []) if system else []
    if index is None or not 0 <= int(index) < len(bodies):
        return None
    return bodies[int(index)]


def _quiet(game, body) -> bool:
    """Is there something on this rock that nobody has ever listed?

    Derived from a stable seed and not rolled, so the same body is the same
    secret across a reload and across every screen that asks — the discipline
    `sim/anchorage` uses for a quay's whole existence. A drawn number would
    make a site appear and disappear as the game was saved.
    """
    seed = f"{getattr(game, 'seed', '')}:quiet:{getattr(body, 'id', '')}"
    return RNG(seed).int(0, QUIET_IN - 1) == 0


def claim(game, target):
    """Who has a say over this world's sky, and what they can do about it.

    Asked in one order and it matters: **people, then property, then
    secrets.** Somebody living there outranks somebody working the seams; and
    a site nobody admits to is only ever on a rock with nothing else on it,
    because that is where you would put one.
    """
    body = _body_of(game, target)
    if body is None:
        return None
    system = game.system

    who = settlement_sim.on_body(game, system.id, body.id)
    if who is not None:
        grown = settlement_sim.maturity(game, who)
        warded = colony_sim.ward_at(game, who.system_id)
        return Claim(who=who.power, name=getattr(target, "name", "the colony"),
                     sort="settled",
                     means=ARMED if (grown >= ARMED_AT or warded > 0.0)
                     else SPEAKS)

    holder = territory_sim.claimant(game, system)
    grades = getattr(body, "resources", None) or {}
    best = max(grades.values()) if grades else 0.0
    if holder and best >= WORTH_WATCHING:
        # What the seam is worth decides what they will do about it, which is
        # the difference between a corporation with a battery on a rich body
        # and one that will only tell you to clear off a marginal one.
        return Claim(who=holder, name=f"the workings on {target.name}",
                     sort="worked",
                     means=ARMED if best >= WORTH_KEEPING else SPEAKS)

    if _quiet(game, body):
        # It answers for itself. Whatever flag it flies is not one it admits
        # to, and `who` being empty is the point — there is nobody to bear a
        # grudge, which is exactly what makes it frightening.
        return Claim(who="", name=f"something on {target.name}",
                     sort="quiet", means=QUIET_MEANS, floor=ARMED)
    return None


def means(game, target) -> int:
    """How far up `control.LADDER` whoever is down there can go."""
    said = claim(game, target)
    return said.means if said is not None else 0


def floor(game, target) -> int:
    """The rung this claim opens at. Nonzero only for something that hides."""
    said = claim(game, target)
    return said.floor if said is not None else 0


def contested(conn) -> bool:
    """Is this descent being made over somebody's objection?"""
    from . import control
    from . import landing
    return bool(landing.ditching(conn) and control.has_control(conn)
                and not control.welcome(conn))


#: What each sort of claim is called on a screen, and what it warns.
#:
#: A quiet site is deliberately *not* in here. It does not announce itself and
#: the game must not announce it either — a warning printed about a thing that
#: hides would be the readout giving away what the sim keeps.
TOLD = {
    "settled": ("{name} has people on it. They will have something to say "
                "about a hull coming down on them."),
    "worked": ("{name} — somebody is taking something off {where}, and they "
               "did not go to the trouble of holding this system to leave "
               "the seams open."),
}


def line(game, conn) -> str:
    """What a captain should be told *before* ordering the descent.

    Said before the act and not after it — a world that shoots at you on the
    way down without ever having been visible as a thing that would is the
    same fault as a berth that refuses silently. With one exception, and it is
    the interesting one: **a quiet site says nothing**, because a screen that
    warned about it would be handing over the thing the sim is keeping.
    """
    said = claim(game, getattr(conn, "target", None))
    if said is None or said.sort not in TOLD:
        return ""
    where = getattr(conn.target, "name", "it")
    # `capitalize()` would lowercase the rest — "the workings on drift gate
    # iv". Only the first letter is ours to change.
    name = said.name[:1].upper() + said.name[1:]
    told = TOLD[said.sort].format(name=name, where=where)
    if said.means >= ARMED:
        told += (" Anything coming down will be under fire the whole way, and "
                 "a descent takes as long as the gravity says it takes.")
    return told
