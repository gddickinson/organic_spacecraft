"""Who you are before the first jump: stock, origin, hull, crew and posting.

Every chronicle used to open the same way — a NAVIS called *Patient Increment*,
three officers, five technologies, the Charter capital. That is a fine default
and a poor only option, because every one of those is already a real axis in
the simulation and none of them were yours to pick.

The rule the rest of the game follows applies here too: **a choice that does
not state its consequence is not a choice.** So every record below carries what
it gives *and* what it costs, and `sim/beginning.py` turns that into a preview
the screen shows before you commit. Nothing here is flavour with a number
bolted on; the numbers are the ones the sim already reads.

`stock` is substrate, not ancestry: wet crews breathe, dry ones do not, and
grafted hulls pay both bills. It maps onto the hull families that already exist
in `data/hull_types.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Stock:
    """What you are made of, which decides what you can fly and what you need."""
    id: str
    name: str
    families: tuple          # hull families this stock will crew
    fx: dict                 # applied as game bonuses
    gives: str
    costs: str
    blurb: str


STOCKS = [
    Stock("wet", "Wet", ("grown", "hybrid", "fabricated"),
          {"morale": 0.05},
          "Crewed hulls, self-repair, and people who notice things.",
          "Air, food, morale and berths. A breach is a countdown.",
          "Ordinary human stock under the Charter's reproduction licence. You "
          "grow your ships and you crew them, and both of those cost."),
    Stock("dry", "Dry", ("synthetic", "fabricated"),
          {"scan": 0.10, "research": 0.15, "morale": 0.0, "regen": -1.0},
          "Superb instruments, no air to run out of, no morale to lose.",
          "Nothing grown will graft to you, and nothing you fly ever mends.",
          "Dry Choir: the wet stack traded for a dry one. You are a lineage of "
          "recordings that has forgotten it was ever otherwise."),
    Stock("grafted", "Grafted", ("hybrid", "grown", "fabricated", "synthetic"),
          {"trade": 0.06, "repair": 0.06, "morale": -0.03},
          "Every family will take you, and the Freeholds count you kin.",
          "Both maintenance bills, and nobody's licence protects you.",
          "Freehold grafts — wet where it helps, dry where it does not. The "
          "Charter regards the practice as unlicensed and says so often."),
]
STOCKS_BY_ID = {s.id: s for s in STOCKS}


@dataclass(frozen=True)
class Origin:
    """What you did before this, which decides who owes you and who does not."""
    id: str
    name: str
    stocks: tuple            # which stocks this origin is open to
    rep: dict                # faction id -> delta on the starting standing
    tech: tuple              # technologies you already hold
    trait: str | None        # a crew trait id you personally carry
    credits: int             # delta on the opening purse
    stores: dict             # what is already in the hold
    evidence: dict           # what is already on the bench
    flags: dict = field(default_factory=dict)
    gives: str = ""
    costs: str = ""
    blurb: str = ""


#: The canonical opening is `surveyor` with everything at zero — it is exactly
#: the game as it shipped, so a no-argument `new_game()` is unchanged.
ORIGINS = [
    Origin("surveyor", "Charter Surveyor", ("wet", "grafted"),
           {}, (), "charter", 0, {}, {},
           gives="The commission the game was written around.",
           costs="Nothing, and nothing extra.",
           blurb="A licensed hull, a shakedown cruise's worth of data on the "
                 "bench, and orders that amount to: go and look."),
    Origin("journeyman", "Yards Journeyman", ("wet", "grafted", "dry"),
           {"concordat": 18, "charter": -10},
           ("monocoque", "plasmadrive"), "yards", 6000,
           {"alloy": 30, "silicon": 12}, {"reading": 40},
           gives="Two fabrication technologies, plate and silicon, and the "
                 "Concordat's goodwill.",
           costs="The Charter files you as a licence risk.",
           blurb="Seven years in the slips at Mereth's Mouth. You can weld a "
                 "hull that will never mend and you know why that is a bargain."),
    Origin("grafter", "Freehold Grafter", ("grafted", "wet"),
           {"freeholds": 22, "charter": -14},
           ("sailfilm",), "freehold", 3500,
           {"biomass": 24, "spidroin": 10}, {"specimen": 35},
           gives="Freehold standing, a sail drive, and an eye for a price.",
           costs="The Charter considers grafting a crime in progress.",
           blurb="You put living tissue into dead frames for people who could "
                 "not afford a licence, and you were good at it."),
    Origin("cantor", "Choir Cantor", ("dry",),
           {"sanhedrin": 25, "freeholds": -12},
           ("oect", "chorus"), "quiet", -12000,
           {"silicon": 20}, {"reading": 30, "survey": 20},
           flags={"canon_holder": True},
           gives="Two cognition technologies and the Choir's confidence.",
           costs="No purse to speak of; the Choir does not use money among "
                 "itself, and the Freeholds remember what you are.",
           blurb="You hold a stretch of the lineage canon in your own "
                 "substrate. It is not a metaphor and it is not light."),
    Origin("survivor", "Bloom Survivor", ("wet", "grafted"),
           {"charter": 12, "concordat": 8},
           (), "veteran", -2000, {}, {"specimen": 60},
           flags={"saw_the_heart": True},
           gives="Everyone's sympathy, specimens nobody else has, and the "
                 "location of something at Kessel's Reach.",
           costs="You came away with less than you left with.",
           blurb="Your colony is a smear of chitin now. You were on the last "
                 "lighter off and you have been looking at it ever since."),
    Origin("fugitive", "Registry Fugitive", ("wet", "grafted"),
           {"charter": -35, "freeholds": 16, "concordat": -8},
           ("morphogen",), "reckless", 14000,
           {"wildseed": 8}, {},
           flags={"unlicensed": True},
           gives="A great deal of money and eight tonnes of unlicensed seed.",
           costs="The Charter wants the hull back and will open your hold at "
                 "every quay it holds.",
           blurb="The licence on this hull belongs to somebody else. So, "
                 "arguably, does the hull."),
]
ORIGINS_BY_ID = {o.id: o for o in ORIGINS}


@dataclass(frozen=True)
class Posting:
    """Whose space you open in — which decides what is within reach."""
    id: str
    name: str
    faction: str | None
    capital: bool
    gives: str
    blurb: str


POSTINGS = [
    Posting("charter", "Charter space", "charter", True,
            "The largest market and the licence office.",
            "Where the game was written to start."),
    Posting("concordat", "Concordat of Yards", "concordat", True,
            "A slip that will lay down a fabricated hull on day one.",
            "Welded, punctual, and unsentimental about anything alive."),
    Posting("freeholds", "The Freeholds", "freeholds", True,
            "Loose customs and the best prices you will see.",
            "No capital worth the name, and no help coming either."),
    Posting("sanhedrin", "The Dry Choir", "sanhedrin", True,
            "Instruments, cognition work, and quiet.",
            "They will talk to you. Whether they are listening is separate."),
    Posting("far", "The far quays", None, False,
            "An independent port a long way from anybody's flag.",
            "Nobody's protection, nobody's paperwork. Often a smaller sector "
            "within reach — check the opening before you take it."),
]
POSTINGS_BY_ID = {p.id: p for p in POSTINGS}


#: Which hull each stock opens with if the player does not choose one.
DEFAULT_HULL = {"wet": "navis", "dry": "cantor", "grafted": "graft"}

#: Officers you may sign at the start, by station. A wet crew needs people; a
#: dry one is the ship, and takes fewer.
CREW_CHOICES = ("science", "nav", "engineering", "tactical", "comms", "medicine")
CREW_SLOTS = {"wet": 3, "dry": 2, "grafted": 3}
