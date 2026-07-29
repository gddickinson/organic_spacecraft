"""What each kind of star actually is: how big, how bright, what colour.

The sector has eight spectral classes and has had since it was written — an
M dwarf, a K, a G, an F, an A, a binary pair, a white dwarf and a neutron
star, each with its own name and tint on the chart. Every one of them was
drawn as the same seven-hundred-thousand-kilometre yellow ball, because the
sky had one number for a star's size and no idea which star it was looking at.

They are not remotely the same size. A white dwarf is about as big as Earth
and a neutron star is the size of a city; an A-type is nearly twice the Sun.
That is a range of a hundred thousand to one, it is free — the data already
says which is which — and it is the difference between a system that looks
like every other system and one you can recognise from the window.

Radii are in kilometres and taken from the real classes. Luminosity is
relative to the Sun and drives how hard the light falls on everything else,
which is why an M dwarf's worlds are dim and an A-type's are glaring.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The Sun, for scale.
SOLAR_RADIUS_KM = 695_700.0


@dataclass(frozen=True)
class StarClass:
    """One spectral class, as a thing you can see out of a window."""

    id: str
    name: str
    #: Radius in kilometres.
    radius_km: float
    #: Brightness relative to the Sun. Drives the light everything else gets.
    luminosity: float
    #: The colour of the disc itself.
    core: str
    #: The colour of the corona around it.
    halo: str
    blurb: str


#: Every class the galaxy generator makes, keyed by the letter it stores.
STAR_CLASSES = {
    "M": StarClass(
        "M", "M-type red dwarf", SOLAR_RADIUS_KM * 0.32, 0.04,
        "#ffb08a", "#e07a5f",
        "Small, cool and patient. It will still be burning when everything "
        "else in the Verge is a cinder."),
    "K": StarClass(
        "K", "K-type orange", SOLAR_RADIUS_KM * 0.78, 0.34,
        "#ffcf9a", "#e6ac6d",
        "An orange dwarf. The quiet, long-lived compromise, and the class "
        "under which most of the Verge's habitable ground sits."),
    "G": StarClass(
        "G", "G-type yellow", SOLAR_RADIUS_KM * 1.0, 1.0,
        "#fff4cf", "#f2e3a0",
        "A yellow dwarf, near enough the standard against which everything "
        "else is measured."),
    "F": StarClass(
        "F", "F-type white", SOLAR_RADIUS_KM * 1.28, 3.6,
        "#fdfdff", "#e8f0f5",
        "White, hot and burning through its hydrogen faster than is "
        "convenient for anything growing nearby."),
    "A": StarClass(
        "A", "A-type blue-white", SOLAR_RADIUS_KM * 1.8, 22.0,
        "#eaf3ff", "#b8d8ff",
        "Blue-white and violent. Anything living under one lives behind "
        "shielding or does not live long."),
    "B": StarClass(
        "B", "binary pair", SOLAR_RADIUS_KM * 0.9, 1.7,
        "#fff0d4", "#ffd9a0",
        "Two stars about a common centre. The light on a hull's plating "
        "shifts as they turn about each other."),
    "D": StarClass(
        "D", "white dwarf", 6_500.0, 0.002,
        "#f4faff", "#cfe6ff",
        "The exposed core of something that used to be a star, about the "
        "size of a rocky world and still too hot to look at."),
    "N": StarClass(
        "N", "neutron star", 12.0, 0.0004,
        "#ddf2ff", "#9fd8ff",
        "Twelve kilometres across and heavier than the Sun. It is a point "
        "of light with a wavelength that goes through a hull."),
}

#: What to use for a class the generator has invented since this was written.
DEFAULT = STAR_CLASSES["G"]

#: Below this radius a star cannot be drawn as a disc at any sane range and
#: is a point of blinding light instead. A white dwarf at one AU is
#: 0.0005° — a thousandth of the Sun — and a neutron star is not a disc at
#: any distance a hull would survive.
POINT_BELOW_KM = 30_000.0


def of(system) -> StarClass:
    """The class of a system's star."""
    return STAR_CLASSES.get(getattr(system, "star", "G") or "G", DEFAULT)
