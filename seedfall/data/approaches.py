"""The powers coming to *you*, and what each of them wants when they do.

Diplomacy ran one way. Six actions, all of them player→faction: send a
tribute, share intelligence, propose a treaty. The powers themselves did
exactly one thing — `drift`, pulling their grievances back toward a baseline —
so a captain could ignore the whole board indefinitely and nothing in the
Verge would ever knock on the door.

That makes the four powers a vending machine. You put standing in and take
tariffs out. They have no wants, no timing, and no opinion about the fact that
you spent last year running cargo for their rival.

An approach is the other direction. A power with a *reason* — a rivalry going
badly, a shortage its own quays cannot cover, a record of you helping the
people it is losing to, or a standing high enough that it wants the thing
formalised — sends somebody to put a proposition to you, with a price, a
deadline, and a stated cost for saying no.

Each kind names four things, because leaving any of them out makes it a
demand rather than a decision:

- **why they came** — built from the state that triggered it, not flavour;
- **what they want** — cargo, a denunciation, a signature, forbearance;
- **what you get** — credits, standing, a tariff line, a lifted grudge;
- **what refusing costs** — always something, never a hidden something.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Approach:
    id: str
    name: str
    #: How the envoy opens. `{power}`, `{rival}`, `{goods}`, `{amount}` and
    #: `{credits}` are filled from the situation that triggered it.
    opening: str
    #: One line stating the ask in plain terms.
    ask: str
    #: What accepting is worth, and what refusing costs. Both stated.
    gives: str
    costs: str
    #: Days before the offer lapses. Letting it lapse is refusing quietly and
    #: costs the same — an offer with no clock is not a decision.
    window: int = 60
    #: Standing swing on accept and on refuse.
    accept_rep: float = 6.0
    refuse_rep: float = -6.0
    #: How much they will move if you push back, as a share of the payment.
    haggle: float = 0.25


APPROACHES = [
    Approach(
        "requisition", "Requisition",
        "{power} has a shortage its own quays cannot cover. Somebody has "
        "looked at what you are carrying and made a note of it.",
        "They want {amount} t of {goods}, and they are offering "
        "{credits:,} credits — under the posted price, and they know it.",
        gives="Paid on the spot, and the office remembers who filled the gap.",
        costs="Refusing is noted. They have other captains.",
        window=45, accept_rep=7.0, refuse_rep=-5.0, haggle=0.3),

    Approach(
        "denounce_rival", "Request to denounce",
        "{power} is losing ground to {rival} and has stopped pretending "
        "otherwise. They would like it said out loud, by somebody who is not "
        "them.",
        "They want you to denounce {rival} publicly.",
        gives="Their gratitude, in standing and in a line of credit.",
        costs="{rival} will hear about the refusal too, and think less of "
              "you for having been asked.",
        window=40, accept_rep=11.0, refuse_rep=-7.0, haggle=0.2),

    Approach(
        "warning", "A word about your associations",
        "{power} has been reading your manifest. You have been useful to "
        "{rival} lately, and somebody senior has noticed.",
        "They want you to stop taking {rival}'s work for a season.",
        gives="The file is closed and nothing further is said.",
        costs="The file stays open, and open files get quoted at quays.",
        window=30, accept_rep=4.0, refuse_rep=-12.0, haggle=0.0),

    Approach(
        "treaty_offer", "An offer of terms",
        "{power} has decided you are worth writing down. This is the office "
        "approaching you, which does not happen often and is not repeated.",
        "They are proposing a treaty — berthing rights and a tariff line, "
        "signed at their expense rather than yours.",
        gives="A treaty for nothing but the signature, and standing besides.",
        costs="They will not offer twice, and proposing it yourself later "
              "costs the usual fee.",
        window=60, accept_rep=9.0, refuse_rep=-8.0, haggle=0.0),

    Approach(
        "levy", "A levy on your holdings",
        "You are working ground inside {power}'s declared space. They have "
        "sent somebody with a figure rather than a fleet, which is the polite "
        "version.",
        "They want {credits:,} credits against what your holdings have taken "
        "out of their register.",
        gives="The claim is settled and the register is marked paid.",
        costs="An unpaid levy is a standing grievance, and they collect "
              "grievances.",
        window=35, accept_rep=5.0, refuse_rep=-14.0, haggle=0.35),
]
APPROACHES_BY_ID = {a.id: a for a in APPROACHES}

#: Days after any approach before the same power sends another. Without this
#: a bad standing turns into a queue of envoys and the screen becomes a
#: nagging inbox rather than a decision.
QUIET_DAYS = 120

#: Chance per day that a power with a live reason actually sends somebody.
#: Deliberately low: an approach should feel like something happening to you,
#: not a weekly appointment.
ODDS_PER_DAY = 0.014
