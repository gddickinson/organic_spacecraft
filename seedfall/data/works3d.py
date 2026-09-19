"""What one of your holdings looks like, built out of what it actually is.

Measured before this file existed. Plant one of each of the nineteen colony and
station classes, ask the sky what it is looking at, and every one comes back
with the same mesh:

    colony anchorages: 19
    distinct meshes: 1

An ARCA Habitat holding a million people, a TARDIGRADE Vault, a VESPER Picket
and a Fabricator Yard were all `berths3d.holding()` — four tanks in a frame —
in the sky, on the approach, and at the berth you tie up to. The codex tab that
lists them had no picture at all: nineteen cards of pure text sitting on top of
a renderer the rest of the game had been using for cycles.

**Nothing is hand-drawn here.** A work's silhouette is read off its own entry in
`data/colonies.py`, exactly the way `hulls3d.proportions` reads a chassis: a
class that yields ore has roots down into the body, one that yields volatiles
has a condenser bell, one that holds people has somewhere for them to live, and
one the Yards throws up has the stacks to say so. Every one of those facts is
already printed in words on the same card, so the portrait and the specification
cannot disagree — and a new class added to `colonies.py` gets a structure of its
own without anybody drawing one.

**And they are the same size in the sky as at the berth.** `size_km` is the one
door for how big a structure is; `sim/sky` drew every anchorage at 0.6 km while
`sim/targets` handed the approach 0.4 km for the same object, so the thing you
picked out at forty kilometres was half again the size of the thing you came
alongside.

Model space is `berths3d`'s: a structure is authored about a unit long, drawn at
its own `radius_km`, nose along +z.
"""

from __future__ import annotations

from dataclasses import dataclass

from .colonies import COLONIES
from .models3d import CHLORO, GOLD, LUMEN, WARN, _build
# The parts and the geometry they share, split out at 635 lines; the
# constants are re-exported because `sim/bays` and the checks read them
# here.
from .works3d_parts import (PARTS,
                           _berths, _keel)
# Where the bays' mouths sit, read by `sim/bays.mouth_of` through this module.
from .works3d_parts import DRUM_R, DRUM_Z, WOMB_MOUTH, WOMB_Z  # noqa: F401  # noqa: F401 - re-exported

#: What family a work was made by, in the trim rather than the plate.
#:
#: The plate stays white: a holding of yours is a structure in the same sky as
#: every quay and Fleet Hub, and `#107` settled that structures are white and
#: lit by one hard sun. So the family shows in the fittings.
#:
#: Not `hullforms.skin`, which is the obvious one door and is the wrong one:
#: five families share four skins there — hybrid and grown are both LIVING,
#: synthetic and xeno are both SYSTEM — so half the sector would come out the
#: same colour as the other half. A hull's skin says what it is *made of*. This
#: says whose yard it came out of, and there are five of those.

#: The Dry Choir's pale steel. Not in `models3d`'s palette, which has no sixth
#: colour, and PLATE would have made a synthetic work white-on-white — a family
#: accent that says nothing is a family accent that is not there.
CHOIR = "#9fb6c0"

ACCENT = {
    "grown": CHLORO,
    "fabricated": GOLD,
    "hybrid": LUMEN,
    "synthetic": CHOIR,
    "xeno": WARN,
}
DEFAULT_ACCENT = GOLD


# ── how big a structure is ─────────────────────────────────────────────────

#: The size everything is measured against: what `sim/targets` already calls an
#: anchorage, which is a quay.
BERTH_KM = 0.4

#: The build time that comes out at exactly a quay. The median of the nineteen,
#: measured rather than chosen.
TYPICAL_DAYS = 120.0

#: How many inhabitants fill one quay-sized structure.
#:
#: Pinned to the one habitat whose true size the GESTALT documents state: ARCA
#: is a 2.5 km drum holding a million. Volume goes as build time plus crowd —
#: both are what a work is made of — so `0.4 · (days/120 + pop/4226)^⅓` has one
#: free number in it and this is it, set so ARCA comes out at 2.5 km and the
#: other eighteen fall where they fall. `tests/test_works3d.py` holds it there.
HEADS_PER_BERTH = 4226.0

#: Nothing smaller than this, whatever the arithmetic says. A structure a ship
#: can berth against is at least a few hundred metres of something.
FLOOR_KM = 0.25


def size_km(look: str) -> float:
    """How big this class of structure is, in kilometres of radius."""
    got = WORKS.get(look)
    return got.radius_km if got is not None else BERTH_KM


def _radius_km(c) -> float:
    volume = c.days / TYPICAL_DAYS + c.pop / HEADS_PER_BERTH
    return max(FLOOR_KM, BERTH_KM * volume ** (1.0 / 3.0))


# ── what a class is, from its own entry ────────────────────────────────────

#: Sites that are solid ground. A grown settlement that will only ever take
#: these is a blister dug into regolith rather than a thing in orbit.
GROUND = frozenset({"rocky", "moon", "asteroid", "ice"})

#: The crowd at which people stop living in a can and start living in a ring.
#: Between the two: 200 aboard a nursery is a crew, 2,000 on a reef is a town.
RING_FROM = 500


def traits_of(c) -> tuple:
    """Every feature this class carries, read off what it does.

    The whole vocabulary, in the order it is built. Each line is a fact the
    card already prints: what it yields, what it lets you do, where it will
    take root, and how many people are aboard.
    """
    out = []
    sites, yields, effects = set(c.sites), c.yields, c.effects
    # A cradle is where a *hull* is grown, built or opened up. `fabricate` is
    # not one of those — it makes alloy and parts, which is what the stacks
    # say — and counting it here gave the Refinery Platform the same feature
    # set as the Fabricator Yard, which is the defect this file exists to fix.
    builds = bool(effects.get("gestation") or effects.get("drydock")
                  or effects.get("build_here"))
    if c.id == "solforge" or "star" in sites:   # the furnace is the class —
        out.append("mirror")    # no generator grows a "star" site any more
    if sites == {"gas"}:
        out.append("scoop")                        # it can only work a gas giant
    if yields.get("ore") or yields.get("phosphate"):
        out.append("roots")
    if yields.get("volatiles"):
        out.append("bell")
    if yields.get("alloy"):
        out.append("stacks")
    if yields.get("biomass"):
        out.append("fronds")
    if yields.get("research"):
        out.append("dish")
    if yields.get("survey") or effects.get("sensor"):
        out.append("masts")
    if effects.get("vault"):
        out.append("vault")
    if effects.get("ward"):
        out.append("guns")
    if effects.get("drift"):
        out.append("vanes")                        # it holds no station
    if effects.get("medical"):
        out.append("bay")
    if effects.get("gestation"):
        out.append("womb")            # grown inside, not welded on a slipway
    elif builds:
        out.append("cradle")
    if effects.get("port"):
        out.append("arm")
    if c.family == "xeno":
        out.append("shards")
    if (c.family == "grown" and c.pop and not builds
            and not effects.get("megastructure") and sites <= GROUND):
        out.append("dome")                         # grown into the ground it sits on
    if effects.get("megastructure"):
        out.append("drum")            # they live inside it, not on a ring
    elif c.pop >= RING_FROM:
        out.append("ring")
    elif c.pop:
        out.append("quarters")
    # A structure with nowhere to make fast gets a gantry, because a boom has
    # to come out of something you can see.
    if not ({"arm", "cradle", "womb", "ring", "drum"} & set(out)):
        out.append("gantry")
    return tuple(out)


# ── one structure, assembled ───────────────────────────────────────────────

@dataclass(frozen=True)
class Work:
    """One class of holding: what it looks like, and where you tie up."""

    id: str
    mesh: tuple
    traits: tuple
    #: fitting | standoff, in `berths3d`'s vocabulary.
    sort: str
    #: Where a hull makes fast, in model space, before a boom is allowed for.
    points: tuple
    radius_km: float


def build(c) -> Work:
    """One colony class's structure, from its own entry and nothing else."""
    accent = ACCENT.get(c.family, DEFAULT_ACCENT)
    traits = traits_of(c)
    parts = _keel(accent)
    for trait in traits:
        maker = PARTS.get(trait)
        if maker is not None:
            parts.extend(maker(accent))
    sort, points = _berths(traits)
    return Work(id=c.id, mesh=_build([(v, f) for v, f in parts]),
                traits=traits, sort=sort, points=points,
                radius_km=_radius_km(c))


#: Every class, built once at import. Nineteen meshes of a few dozen faces
#: each — the same budget one shipyard cost, and it is the whole catalogue.
WORKS: dict = {c.id: build(c) for c in COLONIES}


def is_work(look: str) -> bool:
    """Whether this sort of berth is one of your own holdings."""
    return look in WORKS


def mesh_for(look: str):
    got = WORKS.get(look)
    return got.mesh if got is not None else None


def points_for(look: str) -> tuple:
    got = WORKS.get(look)
    return got.points if got is not None else ()


def sort_for(look: str) -> str:
    got = WORKS.get(look)
    return got.sort if got is not None else "fitting"
