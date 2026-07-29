"""Diplomacy — what the powers want, and what you can do about it.

Standing with a faction was a number that went up when you sold them charts.
This gives it a surface: things you can offer, treaties that mean something, and
a relations matrix between the powers themselves, so that getting four of them
to sign one canon is a matter of getting them to stop hating each other rather
than of grinding four separate meters.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    id: str
    name: str
    blurb: str
    min_rep: float          # standing you need before they will hear it
    cooldown: int           # days before you may try again
    cost_credits: int = 0
    cost_goods: tuple[str, int] | None = None
    gain: float = 0.0       # standing gained on success


ACTIONS: list[Action] = [
    # The only door at rock bottom, on purpose. At -60 every overture was
    # refused and the sole remaining move was `denounce`, which makes it
    # worse — measured, a captain at -100 with unlimited credits courted a
    # power for 120 sessions and moved them not one point. Tribute is the
    # crude one that works on people who cannot stand you, which is exactly
    # what its own blurb says it is.
    Action("tribute", "Send a tribute",
           "Credits, delivered without conditions. Crude, effective, and "
           "everyone involved knows exactly what it is.",
           min_rep=-100, cooldown=60, cost_credits=12000, gain=9),
    Action("intelligence", "Share intelligence",
           "Charts, ore grades, Bloom sightings. Costs you nothing you have not "
           "already learned, and they know that too.",
           min_rep=-25, cooldown=45, cost_goods=("survey", 6), gain=7),
    Action("relief", "Send relief supplies",
           "Biomass and volatiles to a station that is short of both. Worth more "
           "than its tonnage in a bad year.",
           min_rep=-25, cooldown=60, cost_goods=("biomass", 40), gain=11),
    Action("treaty", "Propose a treaty",
           "A signed instrument: mutual berthing, shared charts, and a clause "
           "about the Bloom that nobody expects to be honoured.",
           min_rep=45, cooldown=180, cost_credits=30000, gain=14),
    Action("denounce", "Denounce a rival",
           "Say publicly what everyone says privately. It costs you with them "
           "and buys you with whoever they have wronged.",
           min_rep=-100, cooldown=90, gain=0),
    Action("broker", "Broker a settlement",
           "Sit two powers down. It requires them both to think well of you, "
           "and it is the only way anybody has ever unpicked a grudge out here.",
           min_rep=55, cooldown=150, cost_credits=20000, gain=6),
]

ACTIONS_BY_ID = {a.id: a for a in ACTIONS}


#: Standing below which an overture is worth its full declared value. A power
#: that does not know you yet is glad of forty tonnes of biomass.
COURTSHIP_KNEE = 25.0
#: And what it is worth at the ceiling. Never nothing — a gift is a gift — but
#: a power that already regards you as Kin has less to gain by saying so.
#: Without this, the thirty-first relief parcel bought exactly as much as the
#: first, and Concord was a shopping list: 460,000 credits and 1,270 tonnes of
#: biomass over 2.3 years, without leaving port.
#:
#: Not lower than this. Standing erodes on its own — the sector's churn takes
#: a power at 90 down to 83 inside two years — so an ally has to stay worth
#: courting or high standing becomes unholdable and the Concord unreachable,
#: which is a worse fault than the one being fixed. Measured at 0.08 and 0.15,
#: a determined broker reached it in only two games of four.
COURTSHIP_FLOOR = 0.30
#: How sharply it falls away. Squared, so the early climb is untouched — four
#: relief parcels still carry a stranger to Correct — and the last stretch to
#: Kin is where the work is: seven parcels at a flat rate, eleven now.
COURTSHIP_FALLOFF = 2.0


@dataclass(frozen=True)
class Agenda:
    faction: str
    name: str
    wants: str          # a commodity id the faction is chronically short of
    blurb: str


#: What each power is chronically after. Bringing it earns more than its price.
AGENDAS: dict[str, Agenda] = {a.faction: a for a in [
    Agenda("charter", "The Licence Regime", "phosphate",
           "Every hull they gestate is bone, and bone is phosphorus. They will "
           "take every tonne you can dig and ask where you got it afterwards."),
    Agenda("concordat", "The Yards", "ore",
           "Eleven fabricators, all of them hungry, none of them willing to "
           "admit that a grown miner feeds them better than their own rigs."),
    Agenda("freeholds", "The Margin", "xenopharma",
           "Whatever is scarce and legal, and a good deal that is neither. "
           "Compounds off surveyed worlds move fastest."),
    Agenda("sanhedrin", "The Question", "survey",
           "Recordings. Of anything, but especially of wet cognition doing what "
           "theirs cannot. They have never explained why and they pay well."),
]}


#: Starting relations between the powers. Symmetric; -100 to 100.
INITIAL_RELATIONS = {
    ("charter", "concordat"): -20,   # thinking hulls versus rolled plate
    ("charter", "freeholds"): -35,   # the licence, and who forges it
    ("charter", "sanhedrin"): -10,
    ("concordat", "freeholds"): -45,  # they keep buying stolen Yards frames
    ("concordat", "sanhedrin"): 5,
    ("freeholds", "sanhedrin"): 15,
}

#: Relations bands, for display.
RELATION_BANDS = [
    (-100, "At daggers", "warn"),
    (-45, "Hostile", "warn"),
    (-15, "Cold", "dim"),
    (15, "Correct", "dim"),
    (45, "Cordial", "lumen"),
    (75, "Allied", "chloro"),
]

#: Concord needs the powers at peace with each other, not merely with you.
#: How heavily a treaty registers with the signatory's enemies. Read by both
#: doors into signing one — `diplomacy.perform` when you propose it, and
#: `approach.answer` when their envoy offers it. They disagreed: proposing it
#: charged the signatory's enemies and accepting the identical instrument
#: charged nobody, so the way to sign a treaty for free was to wait to be
#: asked.
TREATY_WEIGHT = 8.0

#: How large a settlement is, for the purpose of who resents it.
#:
#: Priced on what brokering *moves* — twenty-eight points of relation between
#: two powers — rather than on the six standing you are thanked with. The
#: first attempt used the thanks, and at any decent standing `courtship` had
#: already shrunk that to under two, so the most public act on the board cost
#: a third power six tenths of a point. `TREATY_WEIGHT` exists for exactly
#: this reason and this is its companion: bigger, because a settlement moves
#: two powers where a treaty moves one.
BROKER_WEIGHT = 12.0

#: How loud a denunciation is, for the purpose of who takes offence.
#:
#: The act moves the denounced power by -14 and thanks everyone already at
#: odds with them. This is the weight its *friends* price their displeasure
#: against — the mirror of that thanks, and the half nobody was charged for.
DENOUNCE_WEIGHT = 10.0

CONCORD_RELATION = 15
CONCORD_STANDING = 70

#: Envoy requests: a power asks for something and remembers the answer.
REQUESTS = [
    ("supply", "{faction} asks for {amount} t of {goods}. They are short and "
               "they have asked you rather than the open market, which is "
               "itself a statement."),
    ("denounce", "{faction} asks you to denounce {rival} publicly. It would "
                 "cost you with {rival} and settle something with them."),
    ("bounty", "{faction} asks you to remove a {rival} hull that has been "
               "taking their tonnage."),
]
