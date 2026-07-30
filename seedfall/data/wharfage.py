"""What a quay takes off the cargo that crosses it.

The purse cycle (`sim/exchequer.py`) left one connection out on purpose. The
powers earn from the sector's *own* trade at their berths — a number derived
from the port's level — and the captain's buying and selling at those same
berths paid the holder nothing at all. A captain could make a fortune over the
counter at a Fleet Hub the Charter built and maintains, and not one credit
reached the Charter.

So: **wharfage**, the oldest charge in shipping. A share of the value of what
crosses the quay, taken by whoever holds it, on the way in and on the way out.
`sim/exchequer.py` already owns the word "harbour due" for the other direction —
what a Free Port of the captain's own pays *them* — so this is wharfage and the
two never share a name.

Three things move it, and all three are decisions the player can make:

- **The size of the berth.** A Fleet Hub has the deep market and the yard, and
  it charges accordingly; an outpost is cheap and thin. So "where do I trade"
  stops being "wherever the spread is widest".
- **What they think of you.** Standing has always bought better prices; it now
  buys a smaller cut as well, and the spread between Kin and Hunted is the
  widest lever on this page.
- **Whose quay it is.** A free port is free: nobody takes a cut at an
  independent freehold or at a Free Port of your own. `exchequer.holdings`
  already refuses to pay a power for either of those, so this is the same rule
  read from the other side, and it gives the sector's independents a reason to
  exist on a trade route.

And what does *not* pay it, all three for the same reason — nothing crosses the
quay:

- **Contraband sold off the books** through `customs.sell_quietly`. Nobody signs
  anything and no harbourmaster writes it down, which is the smuggler's edge
  stated in money for the first time.
- **Survey sets**, sold through `trade.sell_survey_data`. Data is not cargo, and
  task #66 records that surveying already comes out close to break-even — a
  charge on it would tip a balance claim the game has measured, to say nothing
  of the fiction of a customs officer weighing a chart.
- **Services** — a refit, a repair, a berth. Those are bought *from* the port
  rather than shipped through it, and they are priced at the counter that sells
  them.
"""

from __future__ import annotations

#: The share of a transaction's value taken at an outpost. Measured against a
#: played chronicle rather than guessed: see `tests/test_wharfage.py`, which
#: trades a career's worth over the counter both ways and reports the dues as a
#: share of gross trading profit. Task #66 records that surveying is close to
#: break-even, so a number that quietly ate a quarter of trade margin would
#: have moved several balance claims at once.
WHARFAGE = 0.02

#: What each step up `world.galaxy.PORT_KINDS` adds to that share — an outpost
#: pays the base, a station a quarter more, a Fleet Hub half again. The deep
#: market and the yard are what you are paying for.
LEVEL_STEP = 0.25

#: How much of the charge standing can lift, or add. At `RELIEF_AT` regard and
#: better the captain pays `1 - RELIEF` of it; at `-RELIEF_AT` and worse,
#: `1 + RELIEF`. So the Kin-to-Hunted spread is a factor of four, which is the
#: point: standing has always bought a better price, and now it buys a smaller
#: cut of the deal as well.
RELIEF = 0.6

#: The standing at which relief is complete, either way. 70 is the Kin
#: threshold in `data/factions.STANDINGS`, so the best band and the best rate
#: begin together rather than at two numbers nobody can hold in their head.
RELIEF_AT = 70.0

#: How much of the charge a signed treaty takes off, at the signatory's quays.
#:
#: This is the first half of a promise the treaty has been making since it was
#: written. `data/diplomacy.ACTIONS` sells it as "mutual berthing, shared charts,
#: and a clause about the Bloom that nobody expects to be honoured" — the third
#: is a joke, and the other two were as well: signing appended a name to a list
#: read by `treaty_bonus` (a flat +3% on the trade stat, named on no screen) and
#: by the diplomacy matrix's "treaty" pill. Measured at Vesper Bight: wharfage
#: 1.71% before signing, 1.55% after — and the fall was the *standing* the treaty
#: granted, which tribute at a third of the price would have bought as well.
#: Berthing rights changed the rate by nothing.
#:
#: Half, and multiplied through rather than added, so `RELIEF` keeps the widest
#: spread on the page: standing is a factor of four across the Kin-to-Hunted
#: range, a treaty a factor of two on top of it. The two levers stay legible
#: apart, and 30,000 credits buys a berth cheaper than the best standing alone
#: can make it — which is what an instrument is *for*.
TREATY_RELIEF = 0.5
