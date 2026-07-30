"""What the things in the sky actually look like, one silhouette each.

Measured before this file existed. `ui/viewport._sky` drew **everything that is
not a world** with a single mesh:

    render3d.draw(p, camera, models3d.SHIPYARD, sight.at, ...)

— so a quay, a Fleet Hub, a Weave gate, a patrol boat, a courier and an ore
prospector were the same object at different sizes. Across four sectors the sky
holds 67 quays, 36 gates and 16 hubs, and five errands of traffic; all of it
came out as one shipyard. That is the catalogue defect in its purest form: not
the same shape recoloured, the same shape *unrecoloured*.

The information to do better was already there and thrown away. `track.Contact`
has carried `berth` — quay, hub, holding or gate — since it was written, with a
docstring saying "a screen should not have to read an id to know whether it is
looking at a shipyard or at something older than the Charter", and `sky.build`
set `look=""` for every anchorage and every hull in the system.

Silhouettes, not detail. At the ranges these are seen — a station is 0.6 km and
sits kilometres off — what reads is the outline: how long, how spindly, whether
it has rings, arms, a spine, a bell. Each is a few dozen faces, which is the
same budget the one shipyard cost.
"""

from __future__ import annotations

import math

from .models3d import (GOLD, LUMEN, PLATE, PLATE_DARK, ROCK, ROCK_DARK, WARN,
                       _box, _build, _cap, _ring, _shift, _tube)


def quay() -> tuple:
    """An outpost: a single can with a mast and one arm. Cheap and thin.

    The smallest thing anybody calls a port. It should read as *not much* —
    a Fleet Hub beside it has to look like a different order of place.
    """
    parts = [
        _tube(0.30, -0.42, 0.30, 0.42, 8, 0, PLATE, PLATE_DARK),
        _cap(0.30, 0.42, 8, 0, PLATE, True),
        _cap(0.30, -0.42, 8, 0, PLATE_DARK, False),
        _box(0.055, 0.055, 0.62, LUMEN, PLATE_DARK, dz=0.0),
        _box(0.46, 0.05, 0.035, PLATE, PLATE_DARK, dx=0.46, dz=0.30),
        _box(0.10, 0.10, 0.05, WARN, PLATE_DARK, dx=0.86, dz=0.30),
    ]
    return _build([(v, f) for v, f in parts])


def hub() -> tuple:
    """A Fleet Hub: two habitation rings on a long spine, and four arms.

    The big one. Its whole job is to look like somewhere a fleet lives, so it
    keeps the rings — a torus reads as *inhabited* in a way a box never does —
    and it is twice the length of a quay.
    """
    parts = [_box(0.075, 0.075, 1.10, PLATE, PLATE_DARK)]
    for z in (-0.42, 0.46):
        parts.append(_tube(0.62, z - 0.05, 0.62, z + 0.05, 18, 0,
                           PLATE, PLATE_DARK))
        for i in range(6):
            angle = math.tau * i / 6
            parts.append(_box(0.30, 0.028, 0.028, PLATE_DARK, PLATE_DARK,
                              dx=0.31 * math.cos(angle),
                              dy=0.31 * math.sin(angle), dz=z))
    for i in range(4):
        angle = math.tau * i / 4 + 0.4
        parts.append(_box(0.055, 0.055, 0.34, LUMEN, PLATE_DARK,
                          dx=0.44 * math.cos(angle),
                          dy=0.44 * math.sin(angle), dz=1.02))
    parts.append(_box(0.20, 0.20, 0.14, GOLD, PLATE_DARK, dz=-1.14))
    return _build([(v, f) for v, f in parts])


def holding() -> tuple:
    """A holding: tanks and a gantry. Somewhere cargo waits, not somewhere you live.

    No ring, because nobody lives here. Four cylinders in a frame, which is
    what a bonded store looks like when it does not have to be pretty.
    """
    parts = [_box(0.06, 0.06, 0.78, PLATE_DARK, PLATE_DARK)]
    for i in range(4):
        angle = math.tau * i / 4 + 0.78
        dx, dy = 0.40 * math.cos(angle), 0.40 * math.sin(angle)
        parts.append(_tube(0.20, -0.46, 0.20, 0.46, 7, 0, GOLD, ROCK_DARK))
        parts[-1] = _shift(parts[-1], dx=dx, dy=dy)
        parts.append(_shift(_cap(0.20, 0.46, 7, 0, GOLD, True), dx=dx, dy=dy))
        parts.append(_shift(_cap(0.20, -0.46, 7, 0, ROCK_DARK, False),
                            dx=dx, dy=dy))
        parts.append(_box(0.21, 0.03, 0.03, PLATE, PLATE_DARK,
                          dx=dx * 0.5, dy=dy * 0.5, dz=0.40))
    return _build([(v, f) for v, f in parts])


def gate() -> tuple:
    """A Weave gate: a torus of something older, and nothing else.

    Deliberately unlike every other berth in this file — no spine, no arms, no
    boxes. It is not architecture, it is a ring somebody left.
    """
    parts = [
        _tube(0.94, -0.10, 1.06, 0.0, 26, 0, WARN, ROCK_DARK),
        _tube(1.06, 0.0, 0.94, 0.10, 26, 0, WARN, ROCK_DARK),
        _tube(0.80, -0.05, 0.80, 0.05, 20, 0, GOLD, ROCK_DARK),
    ]
    for i in range(3):
        angle = math.tau * i / 3
        parts.append(_box(0.16, 0.06, 0.14, ROCK, ROCK_DARK,
                          dx=1.0 * math.cos(angle), dy=1.0 * math.sin(angle)))
    return _build([(v, f) for v, f in parts])


#: One mesh per sort of berth. `sky.build` puts the sort on the Sight and
#: `ui/viewport` reads it here, so what the plot calls a gate is drawn as one.
BERTHS = {"quay": quay(), "hub": hub(), "holding": holding(), "gate": gate()}

#: What a berth of an unknown sort gets. A quay: the humblest thing that is
#: still recognisably a port, so a new sort nobody has drawn yet under-promises
#: rather than turning up as a Fleet Hub.
DEFAULT_BERTH = "quay"


def berth_mesh(sort: str) -> tuple:
    return BERTHS.get(sort) or BERTHS[DEFAULT_BERTH]
