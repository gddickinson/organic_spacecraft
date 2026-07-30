"""What the powers say when your holdings and their claims meet.

The sector had claims and it had holdings and the two never touched. A power
would not annex a system you held — the venture code stepped around you — and
you could plant a colony inside somebody's declared space without anybody
mentioning it. Both halves are here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Answer:
    id: str
    name: str
    blurb: str


#: How you may answer a power that has just annexed a system you hold in.
ANSWERS: list[Answer] = [
    Answer("levy", "Pay the levy",
           "A share of what the holding produces, every year, to the power "
           "whose name is now on the system. Expensive, quiet, and it keeps "
           "the place running."),
    Answer("cede", "Hand it over",
           "Walk away from it. They take the works and the standing goes the "
           "other way for once — nobody dislikes a captain who reads a room."),
    Answer("defy", "Refuse",
           "It is your holding and you did the work. They will not forget it, "
           "and sooner or later somebody will come and take it."),
]

ANSWERS_BY_ID = {a.id: a for a in ANSWERS}

#: Share of a holding's yearly output owed under a levy.
LEVY_SHARE = 0.30

#: What a tonne of levied goods is worth to the power that takes it, as a share
#: of the commodity's reference price. Under the reference because a power
#: collecting ore on somebody else's asteroid is not selling it at a hub.
#:
#: It lived as a bare 0.55 inside `territory.yearly_worth`, which is what the
#: demand screen quotes — and the levy itself credited nobody at all, so the
#: figure the captain was shown had no act behind it to agree or disagree with.
#: Both read this now.
LEVY_VALUE = 0.55

#: Standing given up for planting inside a power's declared space, per colony.
TRESPASS = 9.0

#: Below this standing with the claimant they simply will not have you.
UNWELCOME = -25.0

DEMAND = (
    "{power} has put {system} on its register. Your holding there is inside "
    "somebody else's space now, and there is a man on the line who would like "
    "to know what you intend to do about it."
)

OUTCOMES = {
    "levy": "The paperwork is worse than the money. {system} keeps working.",
    "cede": "You take the crew off and leave the works standing. Somebody "
            "else's problem, and they know it was a gift.",
    "defy": "You tell them no. The line goes quiet in the particular way a "
            "line goes quiet when somebody is writing something down.",
}

SEIZED = (
    "They came for {colony} in the end, with the paperwork already filed. "
    "It was never going to be a fight."
)

TRESPASS_NOTE = (
    "{power} has this system on its register. Planting here without asking "
    "will cost you {cost:.0f} standing with them."
)
