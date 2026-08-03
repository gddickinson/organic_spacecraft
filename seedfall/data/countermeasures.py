"""How loud a thing is to somebody else's sensors, and what hides it.

`sim/traffic.py` has described one hull in five as an "Unmarked hull — no
transponder" since it was written, and nothing anywhere read that as a fact
about *detection*: a raider running dark was tracked exactly as precisely as
a lit quay, by every hull in the game, at any range.

A signature is a share of what a lit, transponding hull puts out. Everything
downstream is one multiplication — `sim/detection.py` turns it into a range
in kilometres against the looking ship's own array — so making something
harder to see is a number here rather than a special case there.

**Three ways to be quiet, and they are not the same trade.** Running dark
costs you nothing but the transponder you were supposed to be squawking,
which is why every raider does it. A shroud costs power and mass and is a
choice about this voyage. A cloak is alien work, it is rare, and a hull that
has one is inside your gun range before your board admits it exists.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Countermeasure:
    id: str
    name: str                 # what a board calls it, once it is known
    share: float              # signature, against a transponding hull
    blurb: str


#: Squawking, warm, and lit. What honest traffic does, because being seen is
#: how you are not run into — and how a harbourmaster clears you.
LOUD = Countermeasure(
    "loud", "transponding", 1.00,
    "Transponder squawking, drive warm, lights on. Anybody looking sees her.")

#: The raider's trade: no transponder, drive banked, hull cold. Costs nothing
#: but the squawk, and takes about three quarters of the range off you.
DARK = Countermeasure(
    "dark", "running dark", 0.28,
    "No transponder and a cold hull. Seen at about a quarter the range, and "
    "not at all until then.")

#: Chaff, a plasma shroud, or a skin that simply does not answer. Real
#: suppression: it costs power and mass, so it is a decision about a voyage
#: rather than a switch.
SHROUDED = Countermeasure(
    "shrouded", "shrouded", 0.10,
    "Actively suppressed — chaff and a plasma shroud, or something grown "
    "that does not answer a radar at all.")

#: Alien work. A hull carrying one is inside gun range before a board will
#: admit it is there, which is the whole of why the Weft's wrecks are worth
#: digging up.
CLOAKED = Countermeasure(
    "cloaked", "cloaked", 0.035,
    "A true cloak. Nothing in the Concordat's catalogues does this; the ones "
    "that have it did not build it.")

ALL = (LOUD, DARK, SHROUDED, CLOAKED)
BY_ID = {c.id: c for c in ALL}

#: What each errand runs as. Honest traffic is loud because being seen is the
#: point; only the unmarked hull is hiding, and `sim/traffic.ERRANDS` has
#: called it "no transponder" from the day it was written.
BY_ERRAND = {
    "trader": LOUD, "patrol": LOUD, "prospector": LOUD, "courier": LOUD,
    "raider": DARK,
}

#: How often a hull that is already hiding is hiding *better*. One raider in
#: six carries a shroud and one in twelve a cloak — so a quarter of them are
#: quieter than merely dark: rare enough that meeting a cloak is an event,
#: common enough that a captain who flies fast through raider country in a
#: cheap hull will eventually meet one.
#:
#: Which raider has which is `sim/detection.for_hull`, because deciding is a
#: rule and this file is a table. It is keyed off the hull's own id, so the
#: same raider is the same raider every time you look — and across saves.
SHROUD_IN = 6
CLOAK_IN = 12
