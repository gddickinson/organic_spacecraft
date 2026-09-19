"""The fittings a work is assembled from, and the geometry they share.

Split out of `data/works3d.py` when it reached 635 lines, along the seam the
file already drew with its own section rules: *what a structure is* (its
traits, its size, the catalogue) stays there, and *how each trait is drawn and
where a hull ties up to it* is here. The berth points live beside the parts
that draw them on purpose — a berth is a feature of the mesh, and a fitting
computed from one set of numbers and drawn from another is a picture that
lies about where you can make fast.

Nothing outside `works3d` needs to import this: every name the rest of the
game reads (`DRUM_R`, `WOMB_Z`, …) is re-exported there.
"""

from __future__ import annotations

import math

from .models3d import (GOLD, PLATE, PLATE_DARK, ROCK, ROCK_DARK, WARN, _box,
                       _cap, _tube)


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
    """Berths **inside** a drum, on its inner wall.

    A million people live in there; so do the ships. Standing them off the
    forward end was the timid answer and it made the biggest structure in the
    sector just another mast — `sim/bays` is what lets a hull fly in through
    the open end and tie up on the inside, which is the whole of #108's last
    piece.
    """
    return tuple(
        (f"bay {i + 1}", (DRUM_R * 0.55 * math.cos(math.tau * i / DRUM_BERTHS),
                          DRUM_R * 0.55 * math.sin(math.tau * i / DRUM_BERTHS),
                          -DRUM_Z * 0.30))
        for i in range(DRUM_BERTHS))


def _ring_points() -> tuple:
    return tuple(
        (f"mast {i + 1}", ((RING_R + MAST_OUT) * math.cos(math.tau * i / RING_MASTS),
                           (RING_R + MAST_OUT) * math.sin(math.tau * i / RING_MASTS),
                           0.0))
        for i in range(RING_MASTS))


def _womb_points() -> tuple:
    """**Inside** a gestation shell, where a hull is grown and handed out.

    Round the mouth was where these started, which is a hull hanging outside
    a womb rather than in one. `sim/bays` flies the corridor.
    """
    return tuple(
        (f"cradle {i + 1}", (WOMB_MOUTH * 0.72 * math.cos(math.tau * i / WOMB_BERTHS),
                             WOMB_MOUTH * 0.72 * math.sin(math.tau * i / WOMB_BERTHS),
                             -0.06))
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
