"""How the Bloom answers back.

The arc had two ends and very little in between: unlicensed growth is detected,
it spreads on a timer, and eventually you burn into the heart. Nothing you did
to it changed what it did to you.

It now keeps a count of what you have cost it. Past each threshold it answers,
and the answers escalate: first it simply grows harder, then it comes looking
for your holdings, then it starts arriving where *you* are. The last of them is
the point at which a captain who has been burning everything discovers that the
thing has been paying attention.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Response:
    id: str
    name: str
    tint: str
    #: Provocation at which it fires.
    at: float
    text: str
    #: Multiplies how fast growth accrues from here on.
    growth: float = 1.0
    #: Extra instars detached at once.
    instars: int = 0
    #: Sends the next instars at the player's own position.
    hunts: bool = False
    #: Locks in resistance to whatever has been hurting it most.
    adapts: bool = False


RESPONSES: list[Response] = [
    Response("stir", "Something has noticed", "osteo", at=120,
             text="Growth across the Verge has picked up in a way the Charter's "
                  "models did not predict. Whatever you have been burning, it "
                  "was being counted.",
             growth=1.18),

    Response("harden", "It has learned the taste", "warn", at=300,
             text="Tissue recovered from three separate systems shows the same "
                  "reinforcement, against the same thing. It is not adapting "
                  "where you hit it. It is adapting everywhere at once.",
             growth=1.25, adapts=True),

    Response("swarm", "A seeding wave", "warn", at=520,
             text="Four masses have detached inside a fortnight. They are not "
                  "drifting — they are going somewhere, and the somewhere is "
                  "yours.",
             growth=1.3, instars=3),

    Response("hunt", "It is coming for you", "bad", at=800,
             text="An instar has broken off and made straight for your hull "
                  "across nine light years of nothing. It did not stop at the "
                  "colonies on the way.",
             growth=1.35, instars=2, hunts=True, adapts=True),
]

RESPONSES_BY_ID = {r.id: r for r in RESPONSES}

#: What each thing you do to it is worth, in provocation.
PROVOCATION = {
    "burn": 45.0,          # burning back a system's mass
    "cleared": 90.0,       # clearing one outright
    "instar": 70.0,        # killing a roaming mass
    "heart": 260.0,        # striking the heart
    "colony_ward": 12.0,   # a warding station turning growth away
}

#: Provocation bleeds away when you leave it alone.
DECAY_PER_DAY = 0.10


@dataclass(frozen=True)
class Reading:
    """What studying a mass rather than burning it is worth."""
    xenolith: float
    readings: float
    #: Studying feeds it a little: you are not killing it while you look.
    growth: float


#: Scales with how much mass is present, so a heavy infestation is the prize
#: and also the thing most worth being rid of. That is the whole tension.
STUDY = Reading(xenolith=2.4, readings=90.0, growth=0.045)

#: Below this there is not enough left to learn anything from.
STUDY_FLOOR = 0.15
