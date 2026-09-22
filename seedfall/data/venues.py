"""The concourse: every door a person can walk through, assembled.

Until this existed a port was a market, a services desk and a berths board. A
captain with forty thousand credits could buy a fuel bunker and a hull refit
and had nowhere at all to buy a meal — which is strange, because the whole of
the Verge's social life happens on a concourse.

Fifteen kinds of place now (`data/venue_types.py`), across three themed
tables, and **what is open depends on where you are standing**: how much of a
place it is, how many people are in it, how advanced it is, and how hard the
law runs. A Charter arcology of ten million has four floors of chandlery, a
rejuvenation clinic, an opera house and a bank that will lend against a hull;
a class-D rock with four hundred people has a shed, a bunkroom and somewhere
selling noodles — and a chop shop, because the law does not reach that far.

**None of this is a fact about a starport any more.** `sim/places.py` made a
*place* out of anything with people in it — a quay, a habitat drum, a holding
of yours, a power's settlement on the ground — and every door here is gated
against that, so an ARCA Habitat holding a million people is a city to walk
into rather than a number in the upkeep model.

Nothing here creates credits, which is the one rule this game holds above all
others, and the bank is a place to *keep* money and move it, not to make it.
"""

from __future__ import annotations

from .venue_types import (KIND_NAME, KIND_NOTE, KINDS, OFFER_NAME, OFFERS,
                          Venue, open_to)
from .venues_aboard import ABOARD, ABOARD_RATING, rating
from .venues_body import BODY
from .venues_establishments import ESTABLISHED
from .venues_night import NIGHT
from .venues_trade import TRADE

VENUES: tuple = TRADE + BODY + NIGHT + ABOARD + ESTABLISHED

VENUE_BY_ID = {v.id: v for v in VENUES}
BY_KIND = {kid: tuple(v for v in VENUES if v.kind == kid)
           for kid, _n, _note in KINDS}

#: Every door that sells one thing, so a module that sells beds or surgery
#: can find its own counters without knowing the tables.
BY_OFFER = {oid: tuple(v for v in VENUES if oid in v.offers)
            for oid, _note in OFFERS}

#: How much a night ashore costs per head beyond the venue's own price —
#: the berth, the transit, the things nobody itemises.
ASHORE_OVERHEAD = 8

#: What a rumour heard on a concourse is worth knowing, and how often a place
#: that offers them actually produces one. Both kept here so the screen can
#: quote the odds before the captain spends anything.
RUMOUR_WORTH = "a name, a cargo, or where somebody has gone"

__all__ = ["ABOARD", "ABOARD_RATING", "ASHORE_OVERHEAD", "BY_KIND",
           "BY_OFFER", "KIND_NAME", "KIND_NOTE", "KINDS", "OFFER_NAME",
           "OFFERS", "RUMOUR_WORTH", "VENUES", "VENUE_BY_ID", "Venue",
           "open_to", "rating"]
