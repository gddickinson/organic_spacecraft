"""What the powers are doing while you are not looking.

Diplomacy modelled how four factions regarded you and each other, and then
waited for you to move. Nothing they wanted ever made them *do* anything. A
venture is a faction acting on its own account over a season or two — annexing
a system nobody else has claimed, closing a lane to a rival, courting one, or
raising a fleet — and finishing whether or not you were involved.

You can back one, oppose it, or let it happen. Letting it happen is a choice
too, because the sector it finishes in is not the one it started in.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VentureKind:
    id: str
    name: str
    tint: str
    #: {power}, {other} and {place} are filled in.
    premise: str
    #: Said when it succeeds.
    success: str
    #: Said when it fails.
    failure: str
    #: Days it runs before resolving, low and high.
    days: tuple[int, int]
    #: Needs a rival power as its object.
    needs_other: bool = False
    #: Needs a system as its object.
    needs_place: bool = False
    #: What backing it costs, in credits.
    back_cost: int = 6000
    #: Standing gained with the sponsor for backing it.
    back_rep: float = 12
    #: Standing lost with the sponsor for opposing it.
    oppose_rep: float = -14
    weight: float = 1.0


VENTURES: list[VentureKind] = [
    VentureKind(
        "annex", "Annexation", "osteo",
        "{power} has filed a claim on {place} and is moving a registry cutter "
        "out there to make it stick. Nobody else has a better claim; that is "
        "not the same as nobody minding.",
        success="{place} now flies {power} colours. The filing was uncontested.",
        failure="The claim on {place} lapsed. Somebody made enough noise.",
        days=(160, 320), needs_place=True, back_cost=7000, weight=3),

    VentureKind(
        "blockade", "Embargo", "warn",
        "{power} has closed its quays to {other} cargo and is inspecting "
        "anything that smells of it. Prices are already moving.",
        success="The embargo held. {other} is paying to route around it.",
        failure="The embargo collapsed — too many people were quietly breaking "
                "it, possibly including you.",
        days=(120, 260), needs_other=True, back_cost=5000, weight=3),

    VentureKind(
        "courtship", "Rapprochement", "chloro",
        "{power} and {other} have people talking in a room nobody will name. "
        "Forty years of not speaking may be about to end.",
        success="{power} and {other} have signed something. The room has a "
                "name now and it is on the document.",
        failure="The talks broke down. Both sides are briefing that it was the "
                "other one.",
        days=(140, 300), needs_other=True, back_cost=9000, back_rep=16,
        weight=2),

    VentureKind(
        "levy", "Levy", "steel",
        "{power} is raising hulls — buying them, building them, and pressing "
        "anything with a drive. They are not saying what for.",
        success="The levy is complete. {power} has more hulls than it had, and "
                "the same number of explanations.",
        failure="The levy fell apart over money, as levies do.",
        days=(150, 300), back_cost=8000, weight=2),

    VentureKind(
        "concession", "Concession", "lumen",
        "{power} is opening {place} to licensed working and taking bids. "
        "Whoever holds the concession holds it for a generation.",
        success="The {place} concession has been let. {power} took its cut "
                "and the quays are busy.",
        failure="The concession was withdrawn. Somebody found something in the "
                "survey they did not like.",
        days=(130, 280), needs_place=True, back_cost=6500, weight=2),

    VentureKind(
        "censure", "Censure", "warn",
        "{power} is assembling a case against {other} and inviting everyone "
        "to sign it. The charges are mostly true, which is not the point.",
        success="The censure carried. {other} is diminished and knows who did "
                "it.",
        failure="The censure failed to carry and {power} looks foolish for "
                "having tried.",
        days=(110, 240), needs_other=True, back_cost=4500, weight=2),
]

VENTURES_BY_ID = {v.id: v for v in VENTURES}

#: Chance per power per 30 days of starting something new.
ONSET_PER_MONTH = 0.13

#: A power runs at most this many at once.
MAX_PER_POWER = 1

#: How far backing or opposing moves the odds.
SWAY = 0.30

#: What being right is worth once it lands. Read by `ventures.preview` as well
#: as by `_resolve`, so the screen cannot promise one figure and the outcome
#: pay another — the mistake `TREATY_WEIGHT` was extracted to end.
RIGHT_BACKED = 8.0
#: Opposing something that then failed is worth this with every power that
#: already disliked the one that tried it.
RIGHT_OPPOSED = 5.0

#: Base chance a venture succeeds if nobody interferes.
BASE_ODDS = 0.62
