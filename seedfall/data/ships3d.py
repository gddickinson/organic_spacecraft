"""Other people's ships, by what they are out here doing.

The sky drew every hull in the system with the shipyard mesh — an ore
prospector and a patrol boat were both a station with docking arms. This gives
each errand a silhouette, on the same principle as `data/berths3d.py`: at the
range traffic is seen, the outline is the whole of it.

`sim/traffic.Hull.errand` is the key, and it has been on the object since
traffic was written. Five errands turn up in play — patrol, courier,
prospector, trader, and the unmarked hull that will not say — and every one of
them read as a Fleet Hub.

The vocabulary is deliberately narrow and mostly about **proportion**, because
that is what survives being 80 metres long at four kilometres:

- a courier is nearly all engine, and short
- a trader is a fat can with a fine bow
- a prospector carries its work on the outside
- a patrol boat is lean, with something on the nose
- an unmarked hull is a wedge that explains nothing

Nose is +z, as everywhere else in this package.
"""

from __future__ import annotations

import math

from .models3d import (GOLD, LUMEN, PLATE, PLATE_DARK, ROCK, ROCK_DARK, WARN,
                       _box, _build, _cap, _shift, _tube)


def _bell(radius: float, z: float, colour: str = WARN) -> list:
    """A drive bell hanging off the tail — the one thing every ship has."""
    return [_tube(radius * 0.55, z, radius, z - radius * 1.5, 8, 0,
                  colour, ROCK_DARK)]


def courier() -> tuple:
    """Short, and mostly engine. A hull built to be somewhere else soon."""
    parts = [
        _tube(0.20, -0.30, 0.16, 0.55, 9, 0, PLATE, PLATE_DARK),
        _cap(0.16, 0.55, 9, 0, LUMEN, True),
        _box(0.34, 0.03, 0.09, PLATE_DARK, PLATE_DARK, dz=0.10),
    ]
    parts += _bell(0.26, -0.30)
    return _build([(v, f) for v, f in parts])


def trader() -> tuple:
    """A fat can with a fine bow, and a hold that is most of the ship."""
    parts = [
        _tube(0.34, -0.55, 0.34, 0.35, 10, 0, PLATE, PLATE_DARK),
        _tube(0.34, 0.35, 0.10, 0.80, 10, 0, PLATE, PLATE_DARK),
        _cap(0.10, 0.80, 10, 0, LUMEN, True),
        _cap(0.34, -0.55, 10, 0, PLATE_DARK, False),
        _box(0.44, 0.05, 0.06, GOLD, PLATE_DARK, dz=-0.10),
    ]
    parts += _bell(0.30, -0.55)
    return _build([(v, f) for v, f in parts])


def prospector() -> tuple:
    """Work on the outside: a spine, an ore cradle slung off it, and a boom.

    **Spindly and lopsided on purpose.** The first version was a stubby can
    with a cradle behind it, and rendered against the trader it shared 73% of
    its silhouette — the check caught what the eye had already half-noticed.
    Both were a chunky body with a bell on the end. A prospector is not a hull
    with cargo in it; it is a frame with equipment hung on the frame, and the
    open space between the parts is most of what tells it apart at range.
    """
    parts = [
        # A thin spine, and no pressure hull to speak of.
        _box(0.055, 0.055, 0.72, PLATE_DARK, PLATE_DARK, dz=0.05),
        _box(0.13, 0.11, 0.15, PLATE, PLATE_DARK, dz=0.60),
        # The ore cradle, slung to one side and open to space.
        _tube(0.19, -0.50, 0.19, 0.02, 6, 0, ROCK, ROCK_DARK),
        _cap(0.19, -0.50, 6, 0, ROCK_DARK, False),
        # The boom: long, thin, and reaching well past the nose.
        _box(0.028, 0.028, 0.62, PLATE_DARK, PLATE_DARK, dx=0.02, dz=1.05),
        _box(0.10, 0.07, 0.07, GOLD, ROCK_DARK, dz=1.62),
        # And a counterweight on the other side, because it has to balance.
        _box(0.10, 0.08, 0.08, ROCK, ROCK_DARK, dx=-0.34, dz=-0.10),
        _box(0.17, 0.022, 0.022, PLATE_DARK, PLATE_DARK, dx=-0.20, dz=-0.10),
    ]
    parts[2] = _shift(parts[2], dx=0.26)
    parts[3] = _shift(parts[3], dx=0.26)
    parts += _bell(0.15, -0.36)
    return _build([(v, f) for v, f in parts])


def patrol() -> tuple:
    """Lean, and with something on the nose that is not a sensor."""
    parts = [
        _tube(0.17, -0.40, 0.13, 0.62, 8, 0, PLATE, PLATE_DARK),
        _cap(0.13, 0.62, 8, 0, WARN, True),
        _box(0.05, 0.05, 0.26, WARN, ROCK_DARK, dz=0.86),
    ]
    for side in (-1, 1):
        parts.append(_box(0.20, 0.04, 0.13, PLATE_DARK, PLATE_DARK,
                          dx=side * 0.30, dz=-0.12))
    parts += _bell(0.22, -0.40)
    return _build([(v, f) for v, f in parts])


def unmarked() -> tuple:
    """A wedge that explains nothing. No lights, no flag, no line of sight."""
    parts = [
        _box(0.30, 0.14, 0.30, ROCK_DARK, ROCK_DARK, dz=-0.10),
        _box(0.16, 0.09, 0.34, ROCK_DARK, ROCK, dz=0.42),
        _box(0.42, 0.05, 0.05, ROCK, ROCK_DARK, dz=-0.34),
    ]
    parts += _bell(0.18, -0.42, ROCK_DARK)
    return _build([(v, f) for v, f in parts])


#: One silhouette per errand, keyed by exactly what `sim/traffic.ERRANDS`
#: calls them. The first draft carried invented aliases — "trade", "prospect" —
#: alongside the real ids and no entry at all for `raider`, which is the one
#: errand that matters most to recognise. Guessing at a vocabulary that already
#: exists two modules over is how a table drifts from the thing it describes;
#: `tests/test_silhouettes.py` now refuses an errand with no silhouette.
#:
#: A raider gets `unmarked`, and that is the design rather than a fallback:
#: `ERRANDS["raider"]` is called "Unmarked hull" with "no transponder", so a
#: wedge that explains nothing is exactly the right picture. What you cannot do
#: is tell a raider from a stranger at four kilometres — which is the tension
#: the encounter is built on.
SHIPS = {"courier": courier(), "trader": trader(),
         "prospector": prospector(), "patrol": patrol(),
         "raider": unmarked(), "unmarked": unmarked()}

DEFAULT_SHIP = "unmarked"


def ship_mesh(errand: str) -> tuple:
    return SHIPS.get(errand) or SHIPS[DEFAULT_SHIP]
