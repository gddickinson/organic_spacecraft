"""Things that happen on a walk, and the state of the game that makes each one likely.

A deck with shops on it is a shopping trip. What makes it a *story* is
somebody coming up to you — and every incident here has a reason to exist
that the game already keeps:

- **stop** — you are carrying what this law level forbids, and the watch has
  noticed (`kit.legal_at`, the place's law level);
- **tie** — somebody out of one of your officers' pasts is here: a parent, a
  creditor, a rival, an old shipmate (`sim/person.py` has always dealt them;
  nothing ever put one in front of you);
- **hunter** — there is paper on you that reaches this system
  (`sim/warrants.bounty`), and somebody means to collect;
- **stowaway** — you are alongside a quay, and somebody got into the hold;
- **fault** — the hull is hurt, and something in engineering is failing;
- **quarrel** — two of your officers believe opposite things
  (`data/convictions`: the same act moves them opposite ways), and it has
  come to raised voices in one of the compartments;
- **shakedown** — the law here is thin, and somebody wants a toll for
  walking through;
- **brawl** — the law here is thin, the bar is full, and somebody has had
  enough of looking at you.

`odds` is the chance a walk that meets the condition gets the incident;
`sim/afoot_incidents.py` holds the conditions and puts the people on the deck.
"""

from __future__ import annotations

from dataclasses import dataclass


#: Where people live whom the law does not always reach.
LAWLESS = ("port", "habitat", "downside", "station", "base")
#: Your own holdings and drums, walked.
OWN_GROUND = ("holding", "habitat")


@dataclass(frozen=True)
class Incident:
    id: str
    name: str
    sites: tuple
    odds: float
    blurb: str


INCIDENTS: tuple = (
    Incident("stop", "Stop and search", ("port", "habitat", "downside"), 0.85,
             "The watch has seen what somebody is carrying, and it is not "
             "legal here."),
    Incident("tie", "Somebody from before", ("port", "habitat", "downside"),
             0.25, "One of your officers has been recognised."),
    Incident("hunter", "Paper on you", ("port", "habitat", "downside"), 0.5,
             "Somebody has come to collect on a warrant."),
    Incident("stowaway", "A stowaway", ("ship",), 0.3,
             "There is somebody in the hold who did not sign on."),
    Incident("fault", "A fault", ("ship",), 0.7,
             "Something in the hull is failing, and it will not fix itself."),
    Incident("quarrel", "A quarrel", ("ship",), 0.35,
             "Two of your officers, raised voices, and a crew listening."),
    Incident("shakedown", "A shakedown", LAWLESS, 0.4,
             "A toll for walking through, and friends to collect it."),
    Incident("brawl", "A brawl", LAWLESS, 0.3,
             "Somebody at the bar has picked you out."),
    # Your own ground (`sim/afoot_holdings`): the works, and the people in them.
    Incident("breakdown", "The works failing", OWN_GROUND, 0.35,
             "Something in the works is failing, and the yield with it."),
    Incident("strike", "A strike", OWN_GROUND, 0.25,
             "The hands have downed tools, and want to be heard."),
    Incident("sabotage", "Sabotage", OWN_GROUND, 0.2,
             "Somebody is at the works who should not be."),
)
INCIDENT_BY_ID = {i.id: i for i in INCIDENTS}

#: What fixing a fault aboard is worth: this share of the most hurt layer's
#: missing points, put back.
FAULT_MENDS = 0.25

#: A tie at the gangway: what settling with them is worth to the officer
#: whose past it is, what paying a creditor off costs, and what turning your
#: back on somebody who came to find you costs.
TIE_LOYALTY = 4.0
TIE_SNUB = -2.0

#: What somebody from an officer's past says, by whether they are glad of
#: them — in their own voice, to the officer by name, never a line of the
#: officer's record read out. `{name}` is the officer's first name.
TIE_LINES = {
    True: ("{name}! I heard your ship was in.",
           "Look at you, {name}. Still flying.",
           "{name}. I hoped it was you.",
           "Sit down a minute, {name}. It has been too long."),
    False: ("{name}. I wondered when you would turn up.",
            "Well. {name}.",
            "Don't walk off, {name}. We are not finished.",
            "You have some nerve, {name}, coming through here."),
}
DEBT_LEAST, DEBT_MOST = 200, 900

#: A quarrel: what knocking heads together is worth to each of the two when
#: it works, and costs when it does not; and walking past it.
QUARREL_SETTLED = 2.0
QUARREL_BUNGLED = -1.0
QUARREL_LEFT = -1.0
#: The law level a shakedown or a brawl needs to be at or under, the toll a
#: shakedown asks for each level under four, and a round at the bar.
THIN_LAW = 3
BRAWL_LAW = 4
TOLL_PER_LEVEL = 80
ROUND_COST = 30
#: Your own works: what setting them right by hand does to the holding's
#: yield, and walking away from the trouble; for how many days; and what a
#: strike's bonus costs.
WORKS_BOOST = 0.25
WORKS_SLUMP = -0.25
WORKS_DAYS = 30
STRIKE_BONUS = 400
