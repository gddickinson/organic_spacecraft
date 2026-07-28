"""Commissions — work that leads somewhere.

A posting on a board is a job. A commission is somebody deciding you are the
one they call, and it escalates: the first stage is a courtesy, the last is the
sort of thing that gets a hull impounded or a lineage named after you. Taking
one closes others, because the people who pay for this work know each other.

Stages are turned into ordinary contracts by `sim/chains.py`, so everything
that already knows how to track a delivery or a bounty needs no changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Stage:
    kind: str                  # a contract kind: deliver, prospect, survey, bounty…
    title: str
    posting: str
    #: Multiplies the fee the ordinary generator would have offered.
    pay: float = 1.0
    #: Multiplies the tonnage or count asked for.
    scale: float = 1.0
    days: int = 300
    #: Said when the stage is completed.
    outcome: str = ""


@dataclass(frozen=True)
class Chain:
    id: str
    name: str
    issuer: str
    premise: str
    #: Standing with the issuer needed before it is offered at all.
    min_rep: float
    stages: tuple[Stage, ...]
    #: What finishing it is actually worth, beyond the fee.
    reward_credits: int = 0
    reward_rep: int = 0
    reward_tech: str | None = None
    reward_note: str = ""
    #: Commissions this one shuts the door on the moment you accept it.
    blocks: tuple[str, ...] = ()
    #: Loyalty events raised when it completes.
    feels: tuple[str, ...] = ()


CHAINS: list[Chain] = [
    Chain(
        "assay", "The Assay Office", "charter", min_rep=15,
        premise="A Charter assayer wants a second opinion on a seam nobody "
                "will sign off, and is prepared to be quiet about who gave it.",
        stages=(
            Stage("prospect", "Bring the assayer a sample",
                  "Forty tonnes off the seam in question, unwashed, in the "
                  "state it came out of the rock.",
                  pay=1.2, scale=0.7, days=260,
                  outcome="The numbers came back better than the licence "
                          "says they should. The assayer wants more."),
            Stage("survey", "Chart the field properly",
                  "Whoever filed the original survey did it from orbit and in "
                  "a hurry. Do it again, and do it correctly.",
                  pay=1.5, scale=1.0, days=340,
                  outcome="Filed, stamped, and quietly at odds with three "
                          "existing claims."),
            Stage("deliver", "Carry the finding to the capital",
                  "Paper, not cargo, and it does not travel by relay. Take it "
                  "yourself and hand it to nobody but the registrar.",
                  pay=2.2, scale=0.5, days=300,
                  outcome="The registry reopened the field. Your name is on "
                          "the filing as the surveying master."),
        ),
        reward_credits=42000, reward_rep=22, reward_note=
        "The Charter owes you a survey of your own, and the assay office "
        "will take your word on a seam without sending anyone.",
        blocks=("sluice",), feels=("licence_served",)),

    Chain(
        "sluice", "The Sluice", "freeholds", min_rep=15,
        premise="A Freehold broker is running material past a Charter "
                "inspection and needs a hull whose paperwork nobody enjoys "
                "reading.",
        stages=(
            Stage("deliver", "Run the first load",
                  "It is not contraband where it is going. Getting it there "
                  "is the part they are paying for.",
                  pay=1.6, scale=0.9, days=200,
                  outcome="Delivered without an inspection. The broker has "
                          "stopped calling you the new hull."),
            Stage("bounty", "Discourage the competition",
                  "Another crew has been taking the same work at half the "
                  "rate and twice the noise. Make the arithmetic clear.",
                  pay=1.8, scale=1.0, days=260,
                  outcome="The competition has found other work. Nobody "
                          "filed anything."),
            Stage("prospect", "Stock the sluice",
                  "A standing order, filled in one run, off the books "
                  "entirely. After this the sluice runs itself.",
                  pay=2.0, scale=1.6, days=320,
                  outcome="The sluice is running. You have a share in it."),
        ),
        reward_credits=48000, reward_rep=20, reward_note=
        "A standing share of the sluice: Freehold ports will deal with you "
        "at rates they do not offer to the licensed.",
        blocks=("assay",), feels=("free_served",)),

    Chain(
        "reliquary", "The Reliquary", "sanhedrin", min_rep=25,
        premise="The Dry Choir has been reading a xenolith for eleven years "
                "and has run out of xenolith. They would like more, and they "
                "would like it handled by somebody who understands why.",
        stages=(
            Stage("relic", "Recover what the site will give",
                  "Not a dig — a recovery. What comes up is to arrive intact "
                  "or not at all.",
                  pay=1.4, scale=0.8, days=300,
                  outcome="Intact. The Choir has not said thank you, which "
                          "from them is effusive."),
            Stage("expedition", "Put a party on the surface",
                  "The rest of it is still down there and will not come up "
                  "by remote. Somebody has to walk on it.",
                  pay=1.9, scale=1.0, days=340,
                  outcome="The party came back, and so did the object. The "
                          "Choir has started a new reading."),
            Stage("deliver", "Carry the reading to the Choir",
                  "Eleven years of work and its object, in one hold, in one "
                  "hull. They have asked for yours.",
                  pay=2.4, scale=0.6, days=280,
                  outcome="Delivered to the Choir's own hands. They have "
                          "offered you the reading."),
        ),
        reward_credits=36000, reward_rep=26, reward_tech="xenolinguistics",
        reward_note="The Choir's reading, in full — and standing to ask them "
                    "for the next one.",
        feels=("xeno_served",)),

    Chain(
        "firebreak", "The Firebreak", "concordat", min_rep=20,
        premise="The Concordat wants a line held around a system the Bloom "
                "has been working on, and has stopped pretending its own "
                "hulls can hold it.",
        stages=(
            Stage("deliver", "Carry the materiel out",
                  "Alloy and ordnance to a station that has been asking for "
                  "both since the spring.",
                  pay=1.5, scale=1.1, days=220,
                  outcome="Landed and signed for. The station has stopped "
                          "rationing its ammunition."),
            Stage("bounty", "Burn what is already through",
                  "Something got past the line and is seeding behind it. It "
                  "is to be dealt with before it matures.",
                  pay=2.0, scale=1.0, days=280,
                  outcome="Burned out before it could seed. The line holds."),
            Stage("survey", "Chart the far side of the line",
                  "Nobody knows what is behind the infestation because "
                  "nobody has been able to look. Go and look.",
                  pay=2.3, scale=1.0, days=360,
                  outcome="Charted. The Concordat now knows what it is "
                          "holding a line against."),
        ),
        reward_credits=52000, reward_rep=24, reward_note=
        "Concordat fire support: their monitors will answer for a system you "
        "hold, and their yards will take your work first.",
        feels=("burner_served",)),
]

CHAINS_BY_ID = {c.id: c for c in CHAINS}
