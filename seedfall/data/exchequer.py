"""What the powers earn, what they owe, and what building costs.

**Nobody paid for anything.** A `Port` carried a level, a name and a list of
services, and not one of those ever changed after the galaxy was made. No power
had a budget; annexing a system, blockading a rival and censuring one all cost
exactly nothing. The sector's infrastructure was scenery: the only port that
could come into existence was the player's own Free Port, and the only one that
could ever vanish was that same one.

These are the numbers that make it a purse instead. They are chosen so the
sector has an *equilibrium* rather than a direction:

- **A port yields in proportion to its level**, and costs the square of it. So
  an outpost and a station both clear about sixty a day, and a Fleet Hub very
  nearly pays for itself and no more. Prestige is expensive.
- **A fully built sector therefore runs at break-even**, and any shock, war or
  venture pushes a power into deficit — where it must give something up.
- **A rich power is a busier power.** Surplus with nothing left to build goes
  into ventures, which is the sink that stops a treasury growing forever with
  nothing to spend it on. (The bench's banked research points were exactly that
  bug; see `sim/programmes.py`.)

The ladder itself is **not** here. It is `world.galaxy.PORT_KINDS`, which is
what made every port in the sector, and a second copy of it in `data/` would be
a second answer to what a station is.
"""

from __future__ import annotations

#: What one level of port yields its holder each day, in credits.
YIELD_PER_LEVEL = 90.0

#: What holding it costs each day: `UPKEEP_COEFF × level²`. Superlinear on
#: purpose — see the module docstring. Level 1 clears 60, level 2 clears 60,
#: level 3 clears nothing at all.
UPKEEP_COEFF = 30.0

#: A capital yields this much again: it is where the power's own business is
#: done, not merely a berth it owns.
CAPITAL_BONUS = 0.35

#: What each industry running at a power's berths adds to what they yield. This
#: is the whole reason a power buys a process off the captain (`sim/industry.py`):
#: without it a licence is money out for cheaper goods at home, and nobody would
#: sign. Measured at six per cent: one process across a five-berth power lifts
#: its income by 49 a day against a licence fee of 16,146, so it pays for itself
#: in about 330 days. A year for a permanent industry is a deal a power takes.
INDUSTRY_YIELD = 0.06

#: What a system under a shortage yields while the shortage lasts. This is how
#: a blockade finally costs its target something — `sim/ventures.py` puts a
#: scarcity on a rival's market, and the rival's purse feels it.
SHORTAGE_YIELD = 0.35

#: What each step up `world.galaxy.PORT_KINDS` costs, keyed by the level being
#: bought. Founding is dearer than promoting: there is nothing there yet.
STEP_COST = {2: 24000, 3: 60000}
FOUND_COST = 40000

#: What a power keeps back before it will build anything. Without a reserve a
#: power spends itself to the floor and then cannot pay next month's upkeep.
RESERVE = 12000

#: What a power stakes on one of its own ventures. A power that cannot find
#: this does not start one — which is the whole point of a purse.
VENTURE_STAKE = 9000

#: Above this, a power has more money than plans and gets restless: its
#: appetite for ventures is multiplied by `RICH_APPETITE`.
WAR_CHEST = 120000
RICH_APPETITE = 2.2

#: How often the books are done and decisions taken. Income accrues daily;
#: nobody promotes a station twice in a week.
SETTLE_DAYS = 30

#: What a founder takes from a Free Port of their own each day. This is the one
#: place the player is on the same side of the ledger as a power, and it is why
#: `player_built` is worth carrying: before this it was read by exactly one
#: function, the one that tears the harbour down again.
HARBOUR_DUE = 55.0

#: What each power has in hand on day one. Enough for one venture and a
#: promotion, so the first year is not a year of nothing happening.
OPENING_PURSE = 30000
