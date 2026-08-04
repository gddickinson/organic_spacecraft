"""Contract templates — the work that is available if you want it.

Nothing here is required. The five endings are open from turn one and a captain
who ignores every posting will still finish the game. Contracts exist because a
sandbox needs reasons to go somewhere specific, and because being owed a favour
by the Concordat is worth more than the fee.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContractKind:
    id: str
    name: str
    tint: str
    blurb: str
    #: rough credits per unit of work, before distance and urgency
    rate: float
    rep: int          # standing gained on completion
    deadline: tuple[int, int]   # days allowed, low and high


KINDS: dict[str, ContractKind] = {k.id: k for k in [
    ContractKind(
        "deliver", "Delivery", "osteo",
        "Somebody needs tonnage moved and does not care how you came by it.",
        rate=95, rep=3, deadline=(120, 300)),
    ContractKind(
        "prospect", "Prospecting", "steel",
        "A standing order for material, payable on presentation, no questions "
        "about which rock it came off — brought in, though. Tonnes off their "
        "own counter do not count.",
        rate=120, rep=3, deadline=(150, 400)),
    ContractKind(
        "survey", "Survey Commission", "lumen",
        "A system nobody has charted properly, and an office that would like it "
        "charted properly.",
        rate=1400, rep=5, deadline=(180, 420)),
    ContractKind(
        "bounty", "Bounty", "warn",
        "A hull that has been a nuisance, and a fee for it ceasing to be one.",
        rate=9000, rep=6, deadline=(150, 360)),
    ContractKind(
        "relic", "Antiquities Commission", "xeno",
        "A collector — or an institute, the paperwork is identical — wants "
        "worked alien matter, intact.",
        rate=4200, rep=4, deadline=(200, 500)),
    ContractKind(
        "expedition", "Ground Contract", "chloro",
        "Somebody wants boots on a specific world and a report signed by the "
        "officer who walked it.",
        rate=5200, rep=5, deadline=(180, 460)),
]}

#: What a delivery or prospecting contract might call for.
CARGO_WANTED = ["ore", "volatiles", "biomass", "phosphate", "alloy", "silicon",
                "spidroin", "magnetite", "trehalose"]

#: Flavour openers, picked per contract so the board does not read the same twice.
POSTINGS = {
    "deliver": [
        "Cargo needs moving and the usual hauler is three months overdue.",
        "A yard is idle for want of feedstock and is paying to stop being idle.",
        "Standing order, renewed quarterly, honoured on arrival.",
    ],
    "prospect": [
        "The refinery will take everything you bring and ask nothing.",
        "A shortfall on the books that somebody would like closed quietly.",
        "Posted rate, no ceiling, first hull to present gets paid.",
    ],
    "survey": [
        "The charts for that system are forty years old and were wrong then.",
        "An office wants it catalogued before somebody else catalogues it.",
        "Nobody has been out that way since the Bloom, and it shows.",
    ],
    "bounty": [
        "They have taken three hulls this year. The fourth was ours.",
        "No trial, no arrest, no questions — just the transponder code.",
        "Posted by an office that would rather not be named on the paperwork.",
    ],
    "relic": [
        "Intact, please. The last three arrived as gravel.",
        "The institute is not asking where it came from and neither should you.",
        "A private collection with more money than provenance.",
    ],
    "expedition": [
        "Orbital survey is not enough. They want somebody to walk it.",
        "A previous party went down and the report never came back up.",
        "Ground truth, signed, on that specific world and no other.",
    ],
}
