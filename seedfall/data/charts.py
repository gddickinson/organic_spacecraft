"""What a survey is worth, and to whom.

A chart used to be priced at a flat rate per body, so a dead rock and a system
with a relic in it and an ore grade nobody has seen since the Reach fetched
exactly the same money — and both fetched about a fiftieth of what an hour of
any other work in the game pays. Charting the whole sector, forty-two systems
and most of a career of flying, came to rather less than one run of unlicensed
seed.

Two things follow from a chart being *information*. It is worth what it says,
so the contents set the price. And it is worth it to somebody in particular:
the powers want different things and pay accordingly, which is what makes
where you sell a decision rather than a formality.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Appetite:
    faction: str
    #: Multiplies the whole valuation.
    keen: float
    #: What this power pays over the odds for, by valuation component.
    prizes: tuple[str, ...]
    #: How the office puts it.
    line: str


APPETITES: list[Appetite] = [
    Appetite(
        "charter", 1.25, ("life", "relic", "bloom"),
        "The registry buys everything and files most of it. What it actually "
        "wants is anything alive, anything old, and early warning."),
    Appetite(
        "concordat", 1.10, ("ore", "site"),
        "The Yards want to know where the rock is and whether a hull could sit "
        "on it. They are uninterested in your poetry about the biology."),
    Appetite(
        "freeholds", 1.0, ("port", "route"),
        "A chart is worth what a hauler will pay not to be surprised. Ports, "
        "distances, and who is holding the quay."),
    Appetite(
        "sanhedrin", 1.35, ("life", "anomaly"),
        "The Dry Choir pays over the odds for wet cognition and for anything "
        "the instruments cannot account for. They do not explain why."),
]

APPETITES_BY_FACTION = {a.faction: a for a in APPETITES}

#: Credits per unit of each valuation component.
#:
#: Scaled against the rest of the economy rather than chosen: the best contract
#: in the game pays about 27,000 and the dearest hull 900,000. A first pass at
#: these numbers put a remarkable system's chart at 92,000 — over three times
#: the best contract — which fixed exploration being worthless by making it the
#: best-paying thing in the sector. These land a median chart near 26,000 and a
#: remarkable one near 50,000, for roughly fifty days of surveying.
WORTH = {
    "base": 500,        # a complete chart at all
    "body": 130,        # per body surveyed
    "ore": 1450,        # summed richness of the useful resources
    "life": 820,        # per catalogued organism
    "anomaly": 1870,    # per body with something unaccounted for
    "relic": 2860,      # per buried alien site
    "site": 660,        # per body a colony could sit on
    "port": 1210,       # somewhere to tie up
    "route": 66,        # per light-year from the buyer's nearest holding
    "bloom": 2310,      # scaled by how much of it there is
}

#: A power pays this much over the odds for a component it prizes.
PRIZED = 1.8

#: Charts go stale. A survey this many days old is worth nothing extra for
#: being fresh; before that it carries a premium.
FRESH_DAYS = 720

#: What a stale chart still fetches, as a share of a fresh one.
STALE_FLOOR = 0.45

#: What being known is worth on a survey. A buyer that has dealt with you for
#: years takes your figures on trust; a stranger has no way to tell a complete
#: chart from a plausible one and discounts accordingly. `sim/memory.py` holds
#: the acquaintance itself — this is only what it is worth in credits, and it is
#: deliberately smaller than the freshness penalty: who you are matters, and it
#: matters less than whether the survey is still any good.
KNOWN_WORTH = 0.30
