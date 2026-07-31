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

import math
from dataclasses import dataclass

from .colonies import COLONIES
from .models3d import (CHLORO, GOLD, LUMEN, PLATE, PLATE_DARK, ROCK,
                       ROCK_DARK, WARN, _box, _build, _cap, _tube)

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

# ── the geometry every part of this file agrees about ──────────────────────
#
# Here at the top, once, because a berth is *a feature of the mesh* — the
# lesson `berths3d` learned and `sim/moorings` had to be fixed for: a structure
# whose fittings are computed from one set of numbers and drawn from another is
# a picture that lies about where you can tie up.

#: Half the length of the keel every work is built on. Long enough to be a
#: keel; at 0.84 it overtopped the masts and every card was a flagpole with a
#: station at the bottom of it.
SPINE = 0.60
#: The pressurised core's radius, and how far it runs each way.
CORE = 0.17
CORE_Z = 0.30
#: A habitation ring: its radius, and how far out of it the masts stand.
#: Wider than a cradle's bars on purpose — at 0.66 a ring sat just inside the
#: cage and an Orbital Drydock read 71% the same as a Fabricator Yard.
RING_R = 0.80
MAST_OUT = 0.12
RING_MASTS = 3
#: A cradle's bars — where a hull is built or opened up.
CRADLE_R = 0.52
CRADLE_BARS = 3
#: A megastructure's drum: people live *inside* this one. ARCA is a 2.5 km
#: cylinder holding a million, and `megastructure` was an effect nothing drew —
#: so the biggest thing anyone has ever built came out as a ring on a keel and
#: read 82% the same as a CORAL Reef.
DRUM_R = 0.82
DRUM_Z = 0.60
DRUM_BERTHS = 3
#: A gestation shell's mouth: how wide it opens and how far up it is.
WOMB_MOUTH = 0.26
WOMB_Z = 0.62
WOMB_BERTHS = 2
#: The arm a free port puts out, and the docking light on the end of it.
ARM_OUT = 0.95
ARM_Z = 0.18
#: A gantry stub: what a boom swings from when the structure will not have you
#: against its skin.
GANTRY_R = 0.34
GANTRY_Z = 0.32
GANTRIES = 3


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
    if "star" in sites:
        out.append("mirror")                       # it is parked at a star
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


# ── the parts ──────────────────────────────────────────────────────────────

def _keel(accent: str) -> list:
    """The spine and the pressurised core. Every work has both."""
    return [
        _box(0.035, 0.035, SPINE, PLATE, PLATE_DARK),
        _tube(CORE, -CORE_Z, CORE, CORE_Z, 9, 0, PLATE, PLATE_DARK),
        _cap(CORE, CORE_Z, 9, 0, PLATE, True),
        _cap(CORE, -CORE_Z, 9, 0, PLATE_DARK, False),
        _box(CORE * 1.05, 0.03, 0.035, accent, PLATE_DARK, dz=CORE_Z * 0.55),
    ]


def _roots(accent: str) -> list:
    """Legs driven into the body, and the heads that chew it."""
    out = []
    for i in range(3):
        angle = math.tau * i / 3 + 0.5
        dx, dy = 0.44 * math.cos(angle), 0.44 * math.sin(angle)
        out.append(_box(0.05, 0.05, 0.40, ROCK, ROCK_DARK, dx=dx, dy=dy,
                        dz=-0.62))
        out.append(_box(0.11, 0.11, 0.07, accent, ROCK_DARK, dx=dx, dy=dy,
                        dz=-1.00))
    return out


def _bell(accent: str) -> list:
    """A condenser bell: what a still puts its sublimate through."""
    return [_tube(0.14, 0.72, 0.54, 0.22, 12, 0, PLATE, PLATE_DARK),
            _cap(0.54, 0.22, 12, 0, PLATE_DARK, False),
            _box(0.05, 0.05, 0.10, accent, PLATE_DARK, dz=0.80)]


def _scoop(accent: str) -> list:
    """An intake funnel, mouth down into the cloud tops."""
    return [_tube(0.90, -0.88, 0.26, -0.26, 14, 0, PLATE, PLATE_DARK),
            _tube(0.26, -0.26, 0.20, -0.06, 10, 0, accent, PLATE_DARK)]


def _stacks(accent: str) -> list:
    """Chimneys. Nothing else in the sector has them.

    Stood outside the cradle, and measured: at 0.30 they were inside the
    cage of a Fabricator Yard, which is a cradle *and* stacks — so it rendered
    90% the same as a GRAVID Nursery, which is a cradle and no stacks.
    """
    out = []
    for i in range(3):
        angle = math.tau * i / 3 + 0.9
        dx, dy = 0.72 * math.cos(angle), 0.72 * math.sin(angle)
        out.append(_tube(0.07, 0.16, 0.07, 0.80, 7, 0, PLATE, PLATE_DARK))
        verts, faces = out[-1]
        out[-1] = ([(x + dx, y + dy, z) for x, y, z in verts], faces)
        out.append(_box(0.09, 0.09, 0.05, accent, PLATE_DARK, dx=dx, dy=dy,
                        dz=0.83))
    return out


def _fronds(accent: str) -> list:
    """Leaves. A work that makes biomass makes it in the light."""
    out = []
    for i in range(6):
        angle = math.tau * i / 6
        out.append(_box(0.30, 0.09, 0.012, accent, ROCK_DARK,
                        dx=0.62 * math.cos(angle),
                        dy=0.62 * math.sin(angle), dz=0.06))
    return out


def _dish(accent: str) -> list:
    """A paraboloid facing forward, and the feed on its axis."""
    rows = [(0.10, 0.30), (0.32, 0.40), (0.52, 0.56), (0.68, 0.78)]
    out = [_tube(a[0], a[1], b[0], b[1], 14, 0, PLATE, PLATE_DARK)
           for a, b in zip(rows, rows[1:])]
    out.append(_box(0.03, 0.03, 0.26, accent, PLATE_DARK, dz=0.60))
    return out


def _masts(accent: str) -> list:
    """Instrument masts with lit tips: a picket is mostly antenna.

    Stood well off the axis, and measured: at 0.24 they sat inside the mouth
    of a dish, so a Relay Choir — dish *and* masts — rendered as exactly the
    same silhouette as a CHORUS Node, which has only the dish. 100% of the
    outline shared, with the difference drawn and invisible.
    """
    out = []
    for i in range(3):
        angle = math.tau * i / 3 + 1.4
        dx, dy = 0.52 * math.cos(angle), 0.52 * math.sin(angle)
        out.append(_box(0.025, 0.025, 0.48, PLATE, PLATE_DARK, dx=dx, dy=dy,
                        dz=0.62))
        out.append(_box(0.05, 0.05, 0.05, accent, PLATE_DARK, dx=dx, dy=dy,
                        dz=1.08))
    return out


def _vault(accent: str) -> list:
    """A thick armoured drum with nothing on the outside of it."""
    out = [_tube(0.44, -0.40, 0.44, 0.34, 10, 0, ROCK, ROCK_DARK),
           _tube(0.52, 0.34, 0.44, 0.46, 10, 0, ROCK, ROCK_DARK),
           _cap(0.44, 0.46, 10, 0, ROCK, True),
           _cap(0.44, -0.40, 10, 0, ROCK_DARK, False)]
    # Anchored down, because a vault is put somewhere and left. The plain
    # drum was a compact blob and read 83% the same as a gestation shell.
    for i in range(3):
        angle = math.tau * i / 3 + 0.2
        dx, dy = 0.66 * math.cos(angle), 0.66 * math.sin(angle)
        out.append(_box(0.24, 0.06, 0.05, ROCK, ROCK_DARK,
                        dx=dx * 0.72, dy=dy * 0.72, dz=-0.34))
        out.append(_box(0.07, 0.07, 0.16, accent, ROCK_DARK,
                        dx=dx, dy=dy, dz=-0.50))
    return out


def _guns(accent: str) -> list:
    """Turrets. A monitor station is a gun emplacement with a kitchen."""
    out = []
    for i in range(4):
        angle = math.tau * i / 4 + 0.35
        dx, dy = 0.46 * math.cos(angle), 0.46 * math.sin(angle)
        out.append(_box(0.10, 0.10, 0.09, PLATE, PLATE_DARK, dx=dx, dy=dy))
        out.append(_box(0.20, 0.035, 0.035, accent, WARN, dx=dx * 1.5,
                        dy=dy * 1.5))
    return out


def _mirror(accent: str) -> list:
    """A collector disc held out at the star it is parked beside."""
    return [_tube(1.02, 0.84, 1.02, 0.88, 20, 0, GOLD, PLATE_DARK),
            _cap(1.02, 0.88, 20, 0, GOLD, True),
            _cap(1.02, 0.84, 20, 0, PLATE_DARK, False),
            _box(0.04, 0.04, 0.42, accent, PLATE_DARK, dz=0.44)]


def _shards(accent: str) -> list:
    """A xeno work does not explain itself, and is not symmetrical."""
    out = []
    for i in range(5):
        turn = 2.399 * i                  # the golden angle: never a pattern
        rise = 0.56 - 1.16 * ((i * 0.37) % 1.0)
        size = 0.16 + 0.14 * ((i * 0.53) % 1.0)
        out.append(_box(size, size * 0.45, size * 1.7, accent, ROCK_DARK,
                        dx=0.80 * math.cos(turn), dy=0.80 * math.sin(turn),
                        dz=rise))
    return out


def _vanes(accent: str) -> list:
    """Drift vanes. A work that holds no station hangs on what light there is.

    `drift` was one of the colony effects nothing drew, and the CHORUS Node is
    the only class that carries it — which mattered, because the Node and the
    Relay Choir are both a dish on a keel and rendered 93% alike. What tells
    them apart is the true thing: one of them is not station-keeping.
    """
    out = []
    for i in range(4):
        angle = math.tau * i / 4 + 0.4
        dx, dy = 0.74 * math.cos(angle), 0.74 * math.sin(angle)
        out.append(_box(0.34, 0.24, 0.010, PLATE_DARK, ROCK_DARK,
                        dx=dx, dy=dy, dz=-0.34))
        out.append(_box(0.20, 0.02, 0.02, accent, PLATE_DARK,
                        dx=dx * 0.5, dy=dy * 0.5, dz=-0.34))
    return out


def _bay(accent: str) -> list:
    """A lit bay under the hull: somewhere a sick crew is carried in."""
    return [_box(0.20, 0.20, 0.15, PLATE, PLATE_DARK, dz=-0.46),
            _box(0.05, 0.14, 0.10, WARN, PLATE_DARK, dx=0.22, dz=-0.46)]


def _dome(accent: str) -> list:
    """A pressure blister grown into the regolith under its own spoil."""
    rows = [(0.62, -0.30), (0.58, -0.06), (0.44, 0.16), (0.24, 0.30)]
    out = [_tube(a[0], a[1], b[0], b[1], 16, 0, PLATE, PLATE_DARK)
           for a, b in zip(rows, rows[1:])]
    out.append(_cap(0.24, 0.30, 16, 0, accent, True))
    # Spoil banked round the skirt, not a dark plate under the whole thing:
    # at 0.80 the base cap was the largest face in the picture and the dome
    # came out as a brown disc with a bump on it.
    out.append(_tube(0.62, -0.30, 0.70, -0.38, 16, 0, ROCK, ROCK_DARK))
    return out


def _quarters(accent: str) -> list:
    """A pressurised can. Somewhere a watch sleeps, not somewhere a town is."""
    return [_tube(0.26, 0.18, 0.26, 0.56, 9, 0, PLATE, PLATE_DARK),
            _cap(0.26, 0.56, 9, 0, PLATE, True),
            _box(0.27, 0.03, 0.03, accent, PLATE_DARK, dz=0.44)]


def _ring(accent: str) -> list:
    """A habitation ring, and the masts a hull makes fast to."""
    out = [_tube(RING_R, -0.06, RING_R, 0.06, 18, 0, PLATE, PLATE_DARK)]
    for i in range(6):
        angle = math.tau * i / 6
        out.append(_box(0.32, 0.03, 0.03, PLATE_DARK, PLATE_DARK,
                        dx=0.33 * math.cos(angle), dy=0.33 * math.sin(angle)))
    for name, at in _ring_points():
        out.append(_box(0.06, 0.06, 0.06, accent, PLATE_DARK,
                        dx=at[0], dy=at[1], dz=at[2]))
    return out


def _drum(accent: str) -> list:
    """A cylinder people live inside, end to end. The only one in the sector."""
    out = [_tube(DRUM_R, -DRUM_Z, DRUM_R, DRUM_Z, 20, 0, PLATE, PLATE_DARK),
           _cap(DRUM_R, DRUM_Z, 20, 0, PLATE, True),
           _cap(DRUM_R, -DRUM_Z, 20, 0, PLATE_DARK, False)]
    for z in (-DRUM_Z * 0.45, DRUM_Z * 0.45):
        out.append(_tube(DRUM_R + 0.03, z - 0.05, DRUM_R + 0.03, z + 0.05,
                         20, 0, accent, PLATE_DARK))
    for name, at in _drum_points():
        out.append(_box(0.08, 0.08, 0.07, accent, PLATE_DARK,
                        dx=at[0], dy=at[1], dz=at[2]))
    return out


def _cradle(accent: str) -> list:
    """An open cradle: where a hull is grown, built or opened up."""
    out = []
    for name, at in _cradle_points():
        out.append(_box(0.06, 0.06, 0.62, PLATE, PLATE_DARK,
                        dx=at[0], dy=at[1]))
        out.append(_box(0.08, 0.08, 0.05, accent, PLATE_DARK,
                        dx=at[0], dy=at[1], dz=at[2]))
    for z in (0.58, -0.58):
        out.append(_tube(CRADLE_R + 0.06, z - 0.04, CRADLE_R + 0.06, z + 0.04,
                         12, 0, PLATE, PLATE_DARK))
    return out


def _womb(accent: str) -> list:
    """A gestation shell, with a mouth a finished hull comes out of.

    Not the same thing as a cradle, and it was: a GRAVID Nursery and a
    Fabricator Yard both came out as the open cage, sharing 89% of their
    outline over a difference of three chimneys. One of them grows a hull
    inside a placenta and the other welds it on a slipway — the fiction had
    the answer and the picture was not using it.
    """
    rows = [(0.22, -0.62), (0.50, -0.38), (0.60, 0.06), (0.44, 0.44),
            (WOMB_MOUTH, WOMB_Z)]
    out = [_tube(a[0], a[1], b[0], b[1], 14, 0, PLATE, PLATE_DARK)
           for a, b in zip(rows, rows[1:])]
    out.append(_cap(0.22, -0.62, 14, 0, PLATE_DARK, False))
    for name, at in _womb_points():
        out.append(_box(0.07, 0.07, 0.05, accent, PLATE_DARK,
                        dx=at[0], dy=at[1], dz=at[2]))
    return out


def _arm(accent: str) -> list:
    """A quay arm with a light on the end. What a port is, minimally."""
    return [_box(ARM_OUT * 0.5, 0.05, 0.035, PLATE, PLATE_DARK,
                 dx=ARM_OUT * 0.5, dz=ARM_Z),
            _box(0.09, 0.09, 0.05, WARN, PLATE_DARK, dx=ARM_OUT, dz=ARM_Z),
            _box(0.05, 0.05, 0.22, accent, PLATE_DARK, dx=ARM_OUT * 0.55,
                 dz=ARM_Z + 0.22)]


def _gantry(accent: str) -> list:
    """Stubs a boom swings from. Nothing here wants a hull against its skin."""
    out = []
    for name, at in _gantry_points():
        out.append(_box(0.13, 0.035, 0.035, PLATE, PLATE_DARK,
                        dx=at[0] * 0.6, dy=at[1] * 0.6, dz=at[2]))
        out.append(_box(0.05, 0.05, 0.04, accent, PLATE_DARK,
                        dx=at[0], dy=at[1], dz=at[2]))
    return out


PARTS = {
    "roots": _roots, "bell": _bell, "scoop": _scoop, "stacks": _stacks,
    "fronds": _fronds, "dish": _dish, "masts": _masts, "vault": _vault,
    "guns": _guns, "mirror": _mirror, "shards": _shards, "dome": _dome,
    "quarters": _quarters, "ring": _ring, "cradle": _cradle, "arm": _arm,
    "gantry": _gantry, "vanes": _vanes, "bay": _bay, "womb": _womb,
    "drum": _drum,
}


# ── where a hull ties up ───────────────────────────────────────────────────

def _drum_points() -> tuple:
    """Masts standing off a drum's forward end."""
    return tuple(
        (f"mast {i + 1}", (DRUM_R * 0.62 * math.cos(math.tau * i / DRUM_BERTHS),
                           DRUM_R * 0.62 * math.sin(math.tau * i / DRUM_BERTHS),
                           DRUM_Z + 0.10))
        for i in range(DRUM_BERTHS))


def _ring_points() -> tuple:
    return tuple(
        (f"mast {i + 1}", ((RING_R + MAST_OUT) * math.cos(math.tau * i / RING_MASTS),
                           (RING_R + MAST_OUT) * math.sin(math.tau * i / RING_MASTS),
                           0.0))
        for i in range(RING_MASTS))


def _womb_points() -> tuple:
    """Round the mouth of a gestation shell, where a hull is handed out."""
    return tuple(
        (f"mouth {i + 1}", (WOMB_MOUTH * math.cos(math.tau * i / WOMB_BERTHS),
                            WOMB_MOUTH * math.sin(math.tau * i / WOMB_BERTHS),
                            WOMB_Z))
        for i in range(WOMB_BERTHS))


def _cradle_points() -> tuple:
    return tuple(
        (f"cradle {i + 1}", (CRADLE_R * math.cos(math.tau * i / CRADLE_BARS),
                             CRADLE_R * math.sin(math.tau * i / CRADLE_BARS),
                             0.34))
        for i in range(CRADLE_BARS))


def _gantry_points() -> tuple:
    return tuple(
        (f"gantry {i + 1}", (GANTRY_R * math.cos(math.tau * i / GANTRIES + 0.6),
                             GANTRY_R * math.sin(math.tau * i / GANTRIES + 0.6),
                             GANTRY_Z))
        for i in range(GANTRIES))


def _berths(traits: tuple) -> tuple:
    """Where this structure lets a hull make fast, and on what terms.

    Read off the same traits the mesh is built from, and returning the very
    points those builders drew, so a berth is always a fitting you can see.
    A structure with no berth of its own holds you off on a boom.
    """
    if "arm" in traits:
        return "fitting", (("the arm", (ARM_OUT, 0.0, ARM_Z)),)
    if "womb" in traits:
        return "fitting", _womb_points()
    if "cradle" in traits:
        return "fitting", _cradle_points()
    if "drum" in traits:
        return "fitting", _drum_points()
    if "ring" in traits:
        return "fitting", _ring_points()
    return "standoff", _gantry_points()


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
