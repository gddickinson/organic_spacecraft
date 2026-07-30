"""Somebody living on the ground, and what that does to the local price of it.

**Nothing on a planet produced or consumed anything.** Measured at turn zero:
161 bodies across 42 systems and **0 colonies** — the player could plant one, and
no power ever had. All trade in the sector happened at orbital berths, so a world
rich in phosphate was a number on a survey screen and never a place where
phosphate came from.

A settlement is deliberately *not* a player colony. `data/colonies.py` is
player-shaped — build costs in the captain's materials, works to commission,
effects that grant things to a ship — and reusing it would mean an NPC power
paying biomass out of a hold it does not have. A settlement here is four facts:
who put it there, which body, what the ground gives, and how long it has been
growing.

What it *does* is the point: it makes the thing the ground is rich in, and the
market in that system knows. That is the same mechanism a licensed industry uses
(`sim/industry.py`) and it goes through the same door, because "how much of this
is made here" should have one answer however it came to be made.
"""

from __future__ import annotations

#: What a settlement can be founded to work, in the order a power prefers it.
#: Each is a resource grade `world/planets.py` already puts on a body, so the
#: geography decides what a settlement is for — the same skew `make_market` uses.
WORKABLE = ("phosphate", "biomass", "ore", "volatiles")

#: A body with less of a grade than this is not worth settling for it. The
#: grades run 0..1 and `make_market` treats anything above about a half as
#: locally abundant, so this is "there is visibly something here".
WORTH_SETTLING = 0.45

#: What founding one costs a power, in credits, out of the treasury
#: `sim/exchequer.py` gave them. Dearer than promoting a berth and cheaper than a
#: Fleet Hub: putting people on the ground is a serious undertaking and not the
#: most serious one.
FOUND_COST = 32000

#: What holding it costs a day, and what it pays. A settlement is a slow, sound
#: investment — it clears less per day than a station and it grows, where a berth
#: does not.
UPKEEP = 14.0
YIELD = 46.0

#: How long a settlement takes to come up to full output, in days, and how much
#: of its output it manages on the day it is founded.
MATURE_DAYS = 900.0
NEWBORN = 0.25

#: What a mature settlement multiplies its system's baseline supply of its own
#: good by. Comparable to a licensed industry (1.30–1.55) because it is the same
#: kind of claim: this is a place the thing comes from now.
SUPPLY = 1.45

#: What it does to the *other* workable goods there. People eat: a settlement is
#: a customer for everything it does not make, which is what makes a settled
#: system a place worth carrying cargo to.
DEMAND = 0.92
