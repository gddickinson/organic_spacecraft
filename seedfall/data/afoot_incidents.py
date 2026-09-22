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
- **fault** — the hull is hurt, and something in engineering is failing.

`odds` is the chance a walk that meets the condition gets the incident;
`sim/afoot_incidents.py` holds the conditions and puts the people on the deck.
"""

from __future__ import annotations

from dataclasses import dataclass


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
DEBT_LEAST, DEBT_MOST = 200, 900
