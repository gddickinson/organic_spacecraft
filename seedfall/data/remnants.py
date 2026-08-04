"""What a dead star leaves behind, and how little of it there is.

Three of the nine classes the galaxy makes are stellar corpses — a white
dwarf, a neutron star and an eight-solar-mass black hole — and every one of
them was generating a system by the same table as a G-type: rocky worlds
inside, gas giants and ice outside, oceans in the middle, life where the
biome allowed it. A supernova remnant with an ocean world in the habitable
zone is not a rounding error; it is the wrong system.

**The three do not leave the same thing behind, and the difference is the
interesting part.**

* A **white dwarf** is not a supernova at all. A low-mass star swells to a
  red giant and sheds its envelope, and the swelling *engulfs* whatever was
  close in. The survivors are the outer ones, and as the star loses mass its
  planets' orbits widen — `a ∝ 1/M` — so what is left is sparse, cold and
  further out than it started. Real white dwarfs wear the evidence: their
  atmospheres are polluted with metal from asteroids torn up and swallowed,
  which is why the rubble here is worth a look and the worlds are not.
* A **neutron star** *is* the supernova, and the honest answer to what
  survives one is usually **nothing**. The explosion unbinds most of the
  system and the asymmetry kicks the remnant away at hundreds of kilometres
  a second, stripping the rest. Where planets are found — PSR B1257+12, the
  first exoplanets anybody detected — they are **second generation**,
  condensed out of fallback debris after the fact. So: few, rocky, metal,
  no volatiles worth the name, and sterile.
* A **black hole** is the same story with a heavier progenitor and less left
  over. What there is, is rubble.

Nothing here is a die roll about *whether* a star is a remnant — the galaxy
already decides that. This is only what it finds when it gets there.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Leavings:
    """What one kind of dead star has left in orbit."""

    star: str
    name: str
    #: How far out the innermost survivor sits, as a share of the system's
    #: span. Everything inside this was engulfed, unbound or never re-formed,
    #: and the survivors are pushed outward into what is left — which is also
    #: what mass loss does to an orbit, so one number carries both.
    inner_lost: float
    #: What is out there, as weights over body kinds.
    weights: tuple
    #: The most bodies this sort of corpse keeps. The galaxy's own roll is
    #: capped by it rather than replaced, so a rich draw round a dwarf is
    #: still poorer than a lean one round a G-type.
    keeps: int
    #: Nothing lives here. A supernova sterilises, and a red giant's envelope
    #: is not survivable either.
    lifeless: bool
    blurb: str


#: Sparse, cold, and further out than it started. The rubble is the reason to
#: come: metal-polluted dwarf atmospheres are the real signature.
WHITE_DWARF = Leavings(
    "D", "a shed envelope", 0.38,
    ((4, "asteroid"), (4, "ice"), (3, "comet"), (2, "rocky"), (1, "gas")),
    4, True,
    "The star swelled, swallowed what was close, and shrugged the rest off. "
    "What is left orbits wide and cold, and the rubble is worth more than "
    "the worlds.")

#: Second-generation bodies condensed from fallback debris. Metal, no
#: volatiles, and not many.
NEUTRON = Leavings(
    "N", "a supernova", 0.16,
    ((5, "rocky"), (4, "asteroid"), (1, "ice")),
    3, True,
    "Whatever was here when it went is gone. These condensed afterwards out "
    "of what fell back — metal, sterile, and younger than the corpse they "
    "circle.")

#: The same, with less left.
COLLAPSAR = Leavings(
    "X", "a collapse", 0.22,
    ((5, "asteroid"), (3, "rocky"), (2, "ice")),
    2, True,
    "Eight suns went into that and nothing came out. What orbits it is "
    "rubble that was too far away to be missed.")

BY_STAR = {"D": WHITE_DWARF, "N": NEUTRON, "X": COLLAPSAR}


def of(star_class: str):
    """What this class leaves, or None if the star is still burning."""
    return BY_STAR.get(star_class or "")


#: Radius and surface gravity for a recast body, by kind. Ranges rather than
#: rolls: a remnant's contents are *derived* from the body's identity, never
#: drawn, because drawing takes numbers out of the sector generator and every
#: seed in the game grows a different sector as a result. Measured the hard
#: way — the first version rolled, and thirty-five checks failed in places
#: with nothing to do with dead stars.
SHAPES = {
    "rocky": ((900, 7200), (0.09, 1.35)),
    "ice": ((900, 7200), (0.09, 1.10)),
    "gas": ((24000, 71000), (1.6, 2.9)),
    "asteroid": ((2, 240), (0.001, 0.04)),
    "comet": ((1, 18), (0.001, 0.04)),
    "moon": ((900, 4200), (0.05, 0.40)),
    "ocean": ((900, 7200), (0.09, 1.35)),
}


def recast(leavings, ident: str, share: float):
    """What a body round this corpse actually is: kind, radius, gravity.

    Derived from the body's own identity, so it is stable across saves and
    costs the generator nothing. `share` is a number in 0..1 drawn from the
    same identity by the caller — this module does no hashing of its own,
    which keeps `data/` a table rather than a rule.
    """
    total = sum(w for w, _k in leavings.weights)
    want = share * total
    kind = leavings.weights[-1][1]
    for weight, name in leavings.weights:
        want -= weight
        if want <= 0:
            kind = name
            break
    (r_lo, r_hi), (g_lo, g_hi) = SHAPES.get(kind, SHAPES["rocky"])
    # A second, independent number off the same share, so radius and gravity
    # do not march together across a whole system.
    spread = (share * 7.0) % 1.0
    return (kind,
            int(r_lo + (r_hi - r_lo) * spread),
            g_lo + (g_hi - g_lo) * ((share * 13.0) % 1.0))


def survivor_t(leavings, t: float) -> float:
    """Where a surviving body actually orbits, 0 hot to 1 cold.

    The band is squeezed outward rather than truncated: nothing is left
    inside `inner_lost`, and what remains keeps its order. That is also what
    a star losing mass does to the orbits of what it does not swallow, so
    the same number says both things.
    """
    if leavings is None:
        return t
    lost = max(0.0, min(0.95, leavings.inner_lost))
    return lost + t * (1.0 - lost)
