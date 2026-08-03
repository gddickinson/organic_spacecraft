"""How far this hull's instruments actually see, and how well.

**The collision guard was omniscient, and that was the defect this fixes.**
`sim/collision.py` read `Conn.sky` — a perfect, noiseless list of everything
in the system — so a hull with the cheapest array got the same warnings as
one carrying a VESPER Organ, and a raider "running dark" was tracked as
precisely as a lit quay. The game had a sensor rating doing real work at
sector scale (`intel`, `survey.reach`, the scope) and nothing at all at the
scale where a collision happens.

Two questions, and they are different:

* **Is it seen at all?** A world is not a detection problem — a planet at
  five thousand kilometres subtends degrees, and a quay is lit and squawking
  because being found is its job. A *hull* is the question, and the answer is
  its signature (`data/countermeasures.py`) against your array.
* **How well is it seen?** A contact at the edge of your range is a smear
  with a closing rate you would not bet a hull on. `sim/minigames` has blurred
  the docking instruments by `NOISE_CEILING - sensor` since it was written;
  this is the same idea where it decides whether you live.

**Poor tracks are read pessimistically, not optimistically.** An uncertain
closing rate is treated as the worse end of its error bar, so a bad sensor
warns *early and loudly* rather than late and precisely. A guard that waits
for certainty is a guard that reports the wreck.

The geometry comes from the sky snapshot the approach was opened with, which
is fine for worlds and quays and is a known limitation for hulls: they are
placed where they were when the conn opened. See IMPROVEMENTS.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core import rng
from ..data import countermeasures as cm

#: Kilometres of detection per point of sensor rating, against a loud hull.
#:
#: The rating is quoted in light years because that is what it means on the
#: sector chart, and the conn works in kilometres — so exactly one number
#: bridges the two, and it lives here where it can be argued with.
#:
#: Chosen against `engage.REACH_KM` (10,000 km) and against the stopping
#: distance, which is what actually decides whether a sighting is any use.
#: Measured on opening hulls (3.6–4.2 ly across five chronicles): a
#: transponding contact at 16,800 km, well past gunnery range; running dark
#: 4,704; shrouded 1,680; cloaked 588. At 300 m/s she needs 1,019 km to
#: stop — so everything but the cloak is seen with room to spare, and the
#: cloak is on you before the board admits it. That is the point of a cloak,
#: and lowering this number is what would take it away from the rest.
SENSOR_KM = 4_000.0

#: The worst a track ever gets before it is simply not there, and the most a
#: poor one may inflate a closing rate. A smear at the edge of the envelope
#: is a real reading; treating it as exact is what kills you.
FLOOR_QUALITY = 0.15
NOISE_SHARE = 0.35


@dataclass(frozen=True)
class Track:
    """What the instruments have on something, and how much to trust it."""

    name: str
    kind: str
    km: float
    #: 0..1 — how good the fix is. 1 alongside, `FLOOR_QUALITY` at the edge.
    quality: float
    #: What it is doing about being seen, for a board to name.
    hiding: cm.Countermeasure
    #: How far this array would see it at all.
    range_km: float

    @property
    def estimated(self) -> bool:
        """Whether the numbers off this track want a word of warning."""
        return self.quality < 0.6

    @property
    def noise(self) -> float:
        """How wrong the rate off this track might be, as a share."""
        return (1.0 - self.quality) * NOISE_SHARE

    @property
    def note(self) -> str:
        if self.hiding is not cm.LOUD:
            return f"{self.name} — {self.hiding.name}"
        return self.name


def sensor_of(game, conn=None) -> float:
    """The array this hull is actually looking through, in ly.

    **The flight is asked first.** `Conn.array` is stamped when the approach
    opens, and it is the only answer every reader can get: the instrument
    panel (`sim/instruments.readout`) holds a Conn and no Game, so a guard
    that read the Game would have the panel guessing at a default array while
    the computer used the real one — two screens disagreeing about what is
    out there, which is the fault this deck was rebuilt to end.
    """
    if conn is not None:
        return max(0.1, float(getattr(conn, "array", 2.0)))
    if game is None:
        return 2.0
    return max(0.1, float(getattr(game.ship_stats, "sensor", 2.0)))


def for_hull(errand: str, hull_id) -> cm.Countermeasure:
    """What this hull is doing about being seen.

    Derived from what it is and which hull it is — never stored, so it cannot
    drift from the traffic that generates it, and never rolled at look time,
    so two screens asking about one hull get one answer.

    **`rng.hash_seed`, not `hash()`.** The first draft used the builtin, which
    is salted per process: the same raider came up cloaked this session and
    dark the next, and a chronicle reloaded was a different sky. That is the
    fault `core/rng` exists to prevent, and `sim/traffic` already avoids the
    same way for the same reason.
    """
    base = cm.BY_ERRAND.get(errand or "", cm.LOUD)
    if base is cm.LOUD:
        return base
    roll = rng.hash_seed(f"countermeasure:{hull_id}") % 10_000
    if roll < 10_000 // cm.CLOAK_IN:
        return cm.CLOAKED
    if roll < 10_000 // cm.CLOAK_IN + 10_000 // cm.SHROUD_IN:
        return cm.SHROUDED
    return base


def hiding_of(kind: str, look: str, name) -> cm.Countermeasure:
    """What a thing in the sky is doing about being seen.

    A hull sight carries its errand as its `look` — `sim/sky.build` sets it —
    so this needs nothing the sky has not already got.
    """
    if kind != "hull":
        return cm.LOUD
    return for_hull(look or "", name)


def always_seen(kind: str) -> bool:
    """Some things are not a detection problem, and pretending otherwise is
    worse than useless: a world is enormous and lit, a star more so, and a
    quay squawks because being found is what it is for. A guard that could
    lose a planet would be a guard nobody believed about a raider."""
    return kind in ("star", "body", "anchorage")


def range_for(game, kind: str, look: str, name, conn=None) -> float:
    """How far this array sees that, in km. Infinite for the unmissable."""
    if always_seen(kind):
        return float("inf")
    hiding = hiding_of(kind, look, name)
    return SENSOR_KM * sensor_of(game, conn) * hiding.share


def track(game, conn, name, kind: str, at, look: str = "") -> Track | None:
    """What the instruments have on this, or None if they have nothing.

    None is not "it is not there" — it is "you cannot see it", which is
    exactly the state a hull running dark is buying.
    """
    reach = range_for(game, kind, look, name, conn)
    km = math.dist(tuple(at), tuple(conn.pos))
    if km > reach:
        return None
    if reach == float("inf"):
        quality = 1.0
    else:
        quality = max(FLOOR_QUALITY, min(1.0, 1.0 - (km / reach) ** 2))
    return Track(name=name, kind=kind, km=km, quality=quality,
                 hiding=hiding_of(kind, look, name), range_km=reach)


def seen(game, conn) -> list:
    """Every track the instruments hold right now, nearest first.

    One door, so the collision guard, the panel and the window cannot
    disagree about what is out there.
    """
    out = []
    for sight in getattr(conn, "sky", ()) or ():
        kind = getattr(sight, "kind", "")
        if kind == "star":
            continue
        got = track(game, conn, getattr(sight, "name", "?"), kind,
                    getattr(sight, "at", (0.0, 0.0, 0.0)),
                    getattr(sight, "look", ""))
        if got is not None:
            out.append(got)
    return sorted(out, key=lambda t: t.km)


def line(game, conn, tracks=None) -> str:
    """One sentence about what the array is holding, for a screen.

    `tracks` is the answer `seen` already gave, if the caller has it — the
    panel rebuilds every beat and walking the sky twice for one row is how a
    console gets slow.
    """
    tracks = seen(game, conn) if tracks is None else tracks
    if not tracks:
        return "Nothing on the plot."
    quiet = [t for t in tracks if t.hiding is not cm.LOUD]
    said = f"{len(tracks)} contact{'' if len(tracks) == 1 else 's'} tracked"
    if quiet:
        said += f", {len(quiet)} of them not squawking"
    return said + f" · array {sensor_of(game, conn):.1f} ly."
