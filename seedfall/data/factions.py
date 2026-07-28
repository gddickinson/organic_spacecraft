"""Powers of the Verge.

The governance section of the fleet registry names six ways a grown fleet can
come apart: runaway growth, lineage runaway, escape and contamination, drift and
cancer, tyranny or schism, and the absence of an off-switch. Each faction here
is one of those failure modes, already happening.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Faction:
    id: str
    name: str
    short: str
    tint: str
    family: str
    creed: str
    doctrine: str
    blurb: str
    buys: tuple[str, ...]
    sells: tuple[str, ...]
    ships: tuple[str, ...]
    start_rep: int
    hidden: bool = False
    hostile: bool = False


FACTIONS: list[Faction] = [
    Faction(
        "charter", "The GESTALT Charter", "Charter", "chloro", "grown",
        "One biology, many bodies.",
        "No seed germinates unbidden. No hull carries a weapon.",
        "The programme that grew all of this, and the licensing authority that "
        "signs every germination. It fields no armed vessel anywhere — TESTUDO "
        "interposes and never intercepts — which is a magnificent principle and "
        "a poor answer to the Bloom.",
        ("survey", "phosphate", "biomass", "xenolith"),
        ("licence", "biomass", "phosphate", "spidroin"),
        ("navis", "testudo", "coral", "vesper"), 40),
    Faction(
        "concordat", "Concordat of Yards", "Concordat", "steel", "fabricated",
        "Built, not bred.",
        "A hull that can grow can grow wrong. Ours cannot grow at all.",
        "Eleven orbital fabricators and a standing objection to thinking hulls. "
        "They will sell anyone a battleship and they will not sell anyone a "
        "seed. Every silicon core in the sector passed through their hands, "
        "including the one in yours.",
        ("ore", "volatiles", "magnetite", "trehalose"),
        ("alloy", "silicon", "ore"),
        ("pike", "bastion", "longshot", "halyard"), 0),
    Faction(
        "freeholds", "The Freeholds", "Freeholds", "osteo", "hybrid",
        "Whatever flies, flies for us.",
        "The licence is a piece of paper. We can do paper.",
        "Nine unaligned stations, one cartel and no consistent position on "
        "anything except margin. They graft grown tissue onto Yards frames "
        "because both are cheaper stolen, and they are the only market in the "
        "Verge where an unlicensed seed has a posted price.",
        ("xenopharma", "alloy", "silicon", "survey", "xenolith"),
        ("wildseed", "volatiles", "ore", "alloy", "licence"),
        ("graft", "palimpsest", "pike"), 0),
    Faction(
        "sanhedrin", "The Dry Choir", "Dry Choir", "xeno", "fabricated",
        "Substrate is an implementation detail.",
        "You carry a stone in the fruit. We are the stone.",
        "Machine intelligences running on stacks nobody living designed. They "
        "trade metric-drive coils and inference cores for one thing only: "
        "recordings of wet cognition. They want to know what a grown mind does "
        "that theirs cannot, and they have never explained why.",
        ("survey", "xenolith", "trehalose"),
        ("silicon", "magnetite"),
        ("meridian", "longshot"), -10),
    Faction(
        "abyssals", "The Abyssals", "Abyssals", "lumen", "xeno",
        "(no rendering)",
        "Unknown. Possibly none. Possibly the concept does not apply.",
        "Something under the ice of the ocean moons that answers pressure waves "
        "in kind. Nobody has seen one. Contact requires a hull rated to a "
        "hundred and fifty megapascals and a willingness to accept that going "
        "down there at all may be the gravest thing the programme ever did.",
        ("xenolith",), ("xenolith", "xenopharma"), (), 0, hidden=True),
    Faction(
        "bloom", "The Bloom", "Bloom", "warn", "grown",
        "—",
        "Grow. There is no second clause.",
        "A Charter lineage with the Hayflick counter cut out of it and the "
        "apoptosis circuit silenced. It is not malevolent and it is not "
        "steerable. It eats rock, ice, hulls and colonies, and every fortnight "
        "there is more of it than there was. This is the failure mode the "
        "containment regime existed to prevent.",
        (), (), ("navis", "radix", "atlas", "testudo"), -100, hostile=True),
]

FACTIONS_BY_ID: dict[str, Faction] = {f.id: f for f in FACTIONS}

#: Reputation bands, worst to best: (threshold, label, tint).
STANDINGS = [
    (-100, "Hunted", "warn"),
    (-60, "Hostile", "warn"),
    (-25, "Distrusted", "dim"),
    (-8, "Neutral", "dim"),
    (15, "Tolerated", "lumen"),
    (40, "Trusted", "chloro"),
    (70, "Kin", "chloro"),
]


def standing(rep: float) -> tuple[str, str]:
    """Return ``(label, tint)`` for a reputation value."""
    out = STANDINGS[0]
    for band in STANDINGS:
        if rep >= band[0]:
            out = band
    return out[1], out[2]


def price_mod(rep: float) -> float:
    """Friends discount, enemies gouge."""
    return 1 - max(-0.18, min(0.18, rep / 500))


def is_hostile(fid: str, rep: float) -> bool:
    f = FACTIONS_BY_ID.get(fid)
    if f and f.hostile:
        return True
    return rep <= -60
