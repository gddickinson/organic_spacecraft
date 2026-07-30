"""Being knocked off station, and getting back on it.

`sim/impulse.py` works out that a hull striking a quay at thirty metres a
second shoves the quay 1.7 m/s off station. Stage one of that could only
*say* so: the sector had nowhere to put it. An anchorage's position is its
body's, worked out from the calendar every time it is asked, and a traffic
hull's is interpolated between two bodies — neither of them has a place to
hold "and then somebody hit it".

This is that place. A knock is a velocity offset with a date on it, and
`track.at` — the one door for where anything is — adds what it has come to by
the day being asked about. So a shoved station is off station on the plot, in
the conn's approach, in the readiness board's ranges and in every forecast,
because all of them read the same function.

**Two ways of carrying a knock**, and the difference is whether anybody is
aboard to do something about it:

- **A manned berth or a hull under way** arrests the drift and works back.
  `x(t) = v·t·e^(−t/τ)` — it leaves at exactly the speed it was shoved, peaks
  at `v·τ/e` after `τ` days, and is home again after a few of those. A 1.7 m/s
  shove on a Fleet Hub puts it 649 km off station a fortnight later and back
  where it belongs inside two months.
- **A derelict holding or a Weave gate** has nobody aboard, so `x(t) = v·t`
  and it simply goes. A gate weighs 2,500,000 t and is barely moved by
  anything a captain can fly into it, which is the point of its mass rather
  than a rule about gates.

**On the bearing.** A knock is stored as a distance along a direction that is
*derived from the contact and the day*, not from the approach — because the
conn's frame carries no system orientation to derive it from. An approach
opens with the ship at `[0, −r, 0]` in the target's own frame, and that frame
is never aligned to the system: an anchorage and the body it orbits share a
position in the flight model, so at the moment of contact there is no bearing
in the sector to take. Rather than compute something that looks derived and is
not, the bearing is drawn once from the seed, the contact and the day, and
kept. It is stable across a reload and different for two knocks on the same
quay, which is everything a bearing has to be here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..core.rng import hash_seed
from ..core.save import register

#: Kilometres in an astronomical unit, and seconds in a day: a shove is in
#: m/s and a position is in AU, and the conversion is written once.
KM_PER_AU = 149_597_870.7
SECONDS_PER_DAY = 86_400.0

#: How long a manned structure takes to work back onto station, in days.
#: Not a guess about tugs: it is the time constant of the recovery, so the
#: displacement peaks at `v·τ/e` after this many days and is under a tenth of
#: its peak after four of them. Twelve days puts a hard ram's 1.7 m/s at
#: **649 km off station** at its worst — far enough that a conn notices, near
#: enough that a chart in AU does not, which is the right size for a thing
#: measured in kilometres inside a system measured in AU.
KEEPING_DAYS = 12.0

#: Below this the drift is not worth carrying: a tenth of a kilometre.
SETTLED_KM = 0.1


@register
@dataclass
class Knock:
    """One shove, and what it has come to since."""

    contact_id: str
    #: How hard, in m/s, and which way, as a bearing in radians.
    speed: float
    bearing: float
    #: The day it happened, and what it did to the thing struck.
    day: float
    damage: float = 0.0
    #: Is there anybody aboard to work back onto station?
    keeping: bool = True


def keeps_station(contact) -> bool:
    """Is this thing crewed enough to recover from being hit?

    A quay and a hub are manned ports with tugs; a hull under way has its own
    engines. A holding is a moored yard nobody lives on and a Weave gate is a
    relic, and neither of them is going to do anything about it.
    """
    kind = getattr(contact, "kind", "")
    if kind == "hull":
        return True
    if kind == "anchorage":
        return getattr(contact, "berth", "") in ("quay", "hub")
    return False


def _bearing_for(game, contact_id: str, day: float) -> float:
    """A stable direction for a knock. See the module docstring for why it is
    drawn rather than derived."""
    seed = getattr(game, "seed", "") if game is not None else ""
    return (hash_seed(f"{seed}|knock|{contact_id}|{int(day)}") % 3600) / 3600.0 \
        * math.tau


def record(game, contact, speed: float, day: float | None = None,
           damage: float = 0.0) -> Knock | None:
    """Write down that this contact was shoved, and by how much.

    Returns the knock, or None if the shove was too small to carry. Replaces
    any knock already on that contact rather than adding to it: a structure
    hit twice is dealing with the second one, and two records would have the
    older one still drifting under the newer.
    """
    if game is None or contact is None or speed <= 0.0:
        return None
    when = float(game.day if day is None else day)
    hit = Knock(contact_id=contact.id, speed=float(speed),
                bearing=_bearing_for(game, contact.id, when),
                day=when, damage=float(damage),
                keeping=keeps_station(contact))
    if km_after(hit, when + KEEPING_DAYS) < SETTLED_KM:
        return None
    store(game)[contact.id] = hit
    return hit


def store(game) -> dict:
    """Where knocks live on the chronicle, made on first use."""
    if not hasattr(game, "knocks") or game.knocks is None:
        game.knocks = {}
    return game.knocks


def km_after(hit: Knock, day: float) -> float:
    """How far off station this knock has carried it, in km, on a day.

    The two carriers, as one expression each. Both start at the speed the
    shove gave them, which is what makes this a shove and not a teleport.
    """
    elapsed = max(0.0, float(day) - hit.day)
    if elapsed <= 0.0:
        return 0.0
    km_per_day = hit.speed * SECONDS_PER_DAY / 1000.0
    if not hit.keeping:
        return km_per_day * elapsed
    return km_per_day * elapsed * math.exp(-elapsed / KEEPING_DAYS)


def offset(game, contact_id: str, day: float) -> tuple[float, float]:
    """Where this contact has been carried to, in AU, relative to its place.

    Zero for anything that has never been hit, which is almost everything —
    this is on the path of every position read in the game, so the miss is
    the case that has to be cheap.
    """
    knocks = getattr(game, "knocks", None)
    if not knocks:
        return 0.0, 0.0
    hit = knocks.get(contact_id)
    if hit is None:
        return 0.0, 0.0
    span = km_after(hit, day) / KM_PER_AU
    return math.cos(hit.bearing) * span, math.sin(hit.bearing) * span


def sweep(game) -> int:
    """Drop knocks that have settled, so the store does not grow for ever.

    Only the ones that are *coming back*: a derelict that was shoved is still
    going, and always will be.
    """
    knocks = getattr(game, "knocks", None)
    if not knocks:
        return 0
    gone = [key for key, hit in knocks.items()
            if hit.keeping and km_after(hit, game.day) < SETTLED_KM
            and game.day > hit.day + KEEPING_DAYS]
    for key in gone:
        del knocks[key]
    return len(gone)


def standing(game) -> list:
    """Everything currently off station, worst first — for a screen to say."""
    knocks = getattr(game, "knocks", None) or {}
    rows = [{"id": hit.contact_id, "km": km_after(hit, game.day),
             "speed": hit.speed, "damage": hit.damage,
             "keeping": hit.keeping, "day": hit.day}
            for hit in knocks.values()]
    return sorted(rows, key=lambda row: -row["km"])
