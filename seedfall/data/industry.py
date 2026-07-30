"""Processes: the technologies somebody else would pay to be able to run.

**Sixty-two technologies and one economic effect.** Thirty-three of the tree's
nodes carry a bonus, and the only one of them that touched money was `trade` —
which is a haggling bonus. It moves the price *you* are quoted at a counter and
nothing else: no technology in the game changed what a market held, what a port
could make, or what anything cost anybody but the captain. The tree was a
shopping list of ship parts.

A process is the other kind of technology: one that makes a *thing*. Licence one
to a power and it becomes an industry at every berth that power holds — the good
gets made there, so the local supply rises and the price comes down. That is
technology changing market performance, and the captain is the one who sells it.

The trade is deliberately double-edged. A port that starts making structural
alloy is a port that stops paying well for structural alloy, so **licensing your
refining gut to the power whose quays you have been selling alloy at is a way to
put yourself out of business**. The panel says so before you sign.

Each process names a technology from `data/tech.py` and the commodity it makes.
The pairings are the ones the tree's own blurbs already claim — a Separation Gut
separates, a Magnetosome biomineralises magnetite, Xenopharmacology makes
xenopharma — because a table that invented its own links would be a second,
disagreeing account of what the technology is.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Process:
    #: The technology, by id in `data/tech.py`.
    tech: str
    #: What the industry is called on a manifest.
    name: str
    #: The commodity it makes.
    good: str
    #: What it multiplies the licensee's baseline supply of that good by, at
    #: every berth it holds. Above one is production: more of the thing about,
    #: and a lower price for it.
    supply: float
    #: Whether it opens a trade that was not there at all. Only the seed
    #: process does — every legal good is already stocked at every port, so for
    #: the rest an industry is a matter of how much and how dear.
    opens: bool = False
    #: Whether anyone will admit to it.
    illicit: bool = False
    #: What the licensee gets out of it, in their words.
    blurb: str = ""


PROCESSES: list[Process] = [
    Process("bioleach", "Bioleach Beds", "ore", 1.35,
            blurb="Bacterial leaching of grades nobody could smelt. Low-value "
                  "rock becomes ore pellets, in quantity, on site."),
    Process("waterrefinery", "Refinery Loops", "volatiles", 1.40,
            blurb="Cracking and cleaning what is already in the ice. A berth "
                  "that ran on shipped-in volatiles starts making its own."),
    Process("mineralgut", "Mineral Digestion", "phosphate", 1.30,
            blurb="Phosphate stripped from apatite by an engineered gut. The "
                  "concentrate is the most valuable ordinary thing in the "
                  "sector and it comes out of gravel."),
    Process("organics", "Organics Digestion", "biomass", 1.45,
            blurb="Anything carbonaceous becomes food. A hungry berth stops "
                  "being hungry, which is felt in the price of everything."),
    Process("tendon1", "Spidroin Spinning", "spidroin", 1.35,
            blurb="Spun to a hundred megapascals working stress. Every yard in "
                  "the sector wants fibre and nobody has enough of it."),
    Process("magnetite", "Magnetosome Beds", "magnetite", 1.40,
            blurb="Biomineralised chains, grown rather than mined. The navigation "
                  "trade has been paying alien prices for these."),
    Process("separation", "Separation Guts", "alloy", 1.50,
            blurb="A gut that separates a feedstock into its metals. Structural "
                  "alloy stops being something a berth imports."),
    Process("trehalose", "Cryptobiotic Glass", "trehalose", 1.45,
            blurb="Trehalose vitrified around anything that must survive being "
                  "dried. Medicine, seed stock and long crossings all want it."),
    Process("solforge", "Solar Foundries", "silicon", 1.55,
            blurb="Concentrated sunlight, zone refining, high-purity cores. The "
                  "single most valuable licence in the tree."),
    Process("xenopharma", "Xenopharmacy", "xenopharma", 1.50,
            blurb="Alien biochemistry turned into medicine. Twelve hundred "
                  "credits a tonne and nobody in the Verge can make it."),
    Process("charter", "The Licence Office", "licence", 1.35,
            blurb="Not a factory: the authority to issue reproduction licences "
                  "and the apparatus to enforce them. A power that can license "
                  "birth can charge for it."),
    Process("multifront", "Unlicensed Seed", "wildseed", 1.45, opens=True,
            illicit=True,
            blurb="Parallel growth fronts, no licence, no provenance. It opens "
                  "a trade at their berths that was not there before, and "
                  "everybody will know who taught them to do it."),
]

PROCESSES_BY_TECH = {p.tech: p for p in PROCESSES}

#: What a licence is worth, before anything else: this much per point the
#: technology cost to research. A Solar Foundry at 900 points is the dearest
#: thing in the tree and should read like it.
WORTH_PER_POINT = 26.0

#: How much of what it is worth a power can actually find. They pay from the
#: purse (`sim/exchequer.py`), and a power will not spend more than this share
#: of everything it has on one process however badly it wants it.
PURSE_SHARE = 0.55

#: What being liked is worth. A power at Kin pays this much more than one that
#: merely tolerates you.
STANDING_BONUS = 0.45

#: Below this they will not deal at all. Taken off the band table in
#: `data/factions.STANDINGS` rather than invented: -25 is the floor of
#: *Distrusted*, so a power has to think worse of you than "distrusted" before it
#: refuses an industry outright. The first draft used -10, which is inside
#: *Neutral* — measured on an idle chronicle, that refused three of the four
#: powers by the end of year one purely because nobody had done anything for
#: anybody. Indifference is not refusal.
MIN_STANDING = -25.0

#: What it is worth once a rival already has it. Exclusivity is most of the
#: value of a process, so the second buyer pays a good deal less than the first.
SECOND_HAND = 0.55

#: Standing gained with the licensee, and lost with each of its rivals — they
#: can all see who armed the competition.
LICENSEE_GAIN = 14.0
RIVAL_COST = -6.0

#: What an illicit licence costs you with everybody, on top of the above. The
#: Charter is the licensing authority in this sector and takes the view you
#: would expect.
ILLICIT_COST = -18.0

#: The baseline supply an opened trade starts from, where there was none.
OPENED_SUPPLY = 0.65
