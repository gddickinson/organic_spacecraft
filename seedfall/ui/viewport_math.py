"""Where a direction lands on the screen, and nothing about painting.

Pulled out of `ui/viewport.py` so a feature could be added to that file
without growing it — it is a recorded debt at 533 lines and the ratchet does
not care what the extra lines are for.

Pure geometry: no Qt, no widgets, no state. `project` answers "given the
camera's three axes, where in this picture does that direction fall, and is it
in front of the lens at all", which is the one question every layer of the
window asks — the stars, the sky, the target and the mark all go through it.
"""

from __future__ import annotations

import math

#: Half the vertical field of view: a window, not a fisheye. It lives here
#: because `project` is the only thing that reads it, and `ui/viewport`
#: imports it back for the camera it builds.
HALF_FOV = math.radians(31.0)

def _unit(v) -> tuple:
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def project(vec, cam, width: int, height: int):
    """A direction in the target frame to a point on screen, or None.

    Returns `(x, y, distance_along_axis)`. Anything at or behind the lens is
    not in this camera's picture at all.
    """
    fwd, right, up = cam
    ahead = sum(a * b for a, b in zip(vec, fwd))
    if ahead <= 1e-9:
        return None
    focal = (min(width, height) * 0.5) / math.tan(HALF_FOV)
    x = sum(a * b for a, b in zip(vec, right)) / ahead * focal
    y = sum(a * b for a, b in zip(vec, up)) / ahead * focal
    return (width * 0.5 + x, height * 0.5 - y, ahead)
