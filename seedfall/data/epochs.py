"""What the Verge becomes after each ending, and what it wants from you next.

An ending used to be a dialog and a fresh chronicle. That is a strange thing
for this game to do: containment leaves four powers with no common enemy and a
cleared sector to divide, and *that* is a situation. Concord leaves a unified
Verge with nothing left to unify against. Dominion makes you a power, with
everything a power has to answer for, including secession.

So every ending opens an **epoch**: the world is rewritten once, a new pressure
starts running on the clock in place of the Bloom, and situations arrive that
have to be answered. Each epoch can itself end — well or badly — and the
chronicle keeps its whole history.

`sim/legacy.py` runs these. Nothing here is logic; it is what each world looks
like and what it asks.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Epoch:
    """The sector after an ending, and the clock that now runs on it."""
    id: str                  # matches the ending id
    name: str
    tint: str
    opening: str             # what changed, read once
    pressure: str            # what is now running against you
    #: How fast the pressure builds, per day. At 1.0 the epoch turns over.
    rate: float
    #: What the rising pressure is called on the readout.
    gauge: str
    #: Reached 1.0 without holding it back: this is how the epoch closes badly.
    failure: str
    #: Held it under control for `hold_days`: this is how it closes well.
    triumph: str
    hold_days: int = 1460    # four years of keeping the lid on
    scenarios: tuple = ()


EPOCHS = [
    Epoch("containment", "The Division", "chloro",
          "The last mass senesced eleven days ago and the Verge has been quiet "
          "since. Quiet, and full of cleared worlds with nobody's flag on them. "
          "Four powers who spent a decade pointed the same way are now pointed "
          "at each other, and every one of them has written to you.",
          "The powers are carving up what you cleaned. Every claim they file "
          "without you is a lane you no longer have a say in.",
          1.0 / 1900, "Partition",
          "The Verge is partitioned without you. You cleared it and you are a "
          "guest in it.",
          "Four powers, one settlement, and your signature on it. The worlds "
          "you burned clean got a charter instead of an owner.",
          scenarios=("claim-jump", "cleared-world", "old-serial", "the-vote")),

    Epoch("exodus", "The Rearguard", "osteo",
          "The LEVIATHAN made its burn eight days ago with ten million aboard "
          "and is no longer answering. Everyone else is still here. You are the "
          "largest hull left in the Verge and the only one anybody trusts.",
          "The Bloom does not care that the ark left. What is still here has "
          "to be got out, or dug in, before it arrives.",
          1.0 / 1400, "Encroachment",
          "The rearguard is overrun. Whatever was still here, still was.",
          "Everyone who could be moved was moved, and the rest are dug in deep "
          "enough to argue with. You held the door.",
          scenarios=("last-lighter", "the-holdouts", "seed-vault", "a-signal")),

    Epoch("concord", "The Long Silence", "lumen",
          "Four powers signed one canon and the shooting stopped. In the sixty "
          "days since, three separate deep arrays have logged the same thing "
          "from outside the Verge: something large, slow, and on a heading.",
          "Whatever made the Bloom is coming to see what happened to it. The "
          "Concord holds only as long as it is useful.",
          1.0 / 2200, "Approach",
          "It arrives to find the Concord already arguing. It does not stay "
          "long and it does not leave much.",
          "The Verge meets it as one thing rather than four, which is the only "
          "reason there is anybody left to record what it said.",
          scenarios=("the-array", "first-word", "schism-again", "the-heading")),

    Epoch("genesis", "The Correspondence", "xeno",
          "Contact holds. Twenty kilometres down, something that has been "
          "thinking for longer than the species has existed is now answering, "
          "and it has questions about the licence regime.",
          "The Abyssals are forming a view of us. What they conclude, they will "
          "act on, and they are not slow so much as certain.",
          1.0 / 2000, "Verdict",
          "They reach a conclusion about what we are for. It is not the one "
          "you were arguing for.",
          "A correspondence rather than a verdict: they decide we are worth "
          "the trouble of talking to, which is more than we managed.",
          scenarios=("the-question", "a-gift", "the-registry-asks", "deep-water")),

    Epoch("dominion", "The Accounting", "steel",
          "Twelve worlds, a million citizens, and a flag that is now yours "
          "whether or not you wanted one. The first tax assessment has been "
          "drafted. The second colony has already refused it.",
          "You are a power now. Powers are held together, and the holding is "
          "the job.",
          1.0 / 1700, "Secession",
          "It comes apart the way the Charter said it would, in the order the "
          "Charter said it would, and you had all the same warnings they had.",
          "Twelve worlds and a constitution none of them had to be forced to "
          "sign. You built a thing that does not need you.",
          scenarios=("the-refusal", "a-governor", "the-levy", "old-friends")),

    Epoch("lineage", "The Line", "chloro",
          "Four hulls of your own gestation are flying, signed for, licensed, "
          "and increasingly disinclined to wait for orders. The Registry has "
          "convened. So, in its own way, has the line.",
          "A line that reproduces is a line that can get away from you. That "
          "is the whole reason for the licence, and you are the test case.",
          1.0 / 1600, "Drift",
          "The line drifts out of canon and out of reach, and the Registry's "
          "worst paragraph turns out to have been written about you.",
          "Four hulls, one canon, held by consent rather than by licence. The "
          "regime is rewritten around what you proved could be done.",
          scenarios=("the-fifth", "canon-drift", "a-hearing", "the-cradle")),

    Epoch("xenarch", "The Inheritance", "xeno",
          "Twelve technologies, four dead cultures, and every one of them now "
          "understood. The odd part is how ordinary each looks from inside. "
          "The other odd part is what they have in common.",
          "Four cultures learned all of this and none of them are here. "
          "Working out why is not an academic question.",
          1.0 / 2400, "Pattern",
          "You work out why they are all gone at roughly the same time as the "
          "reason arrives.",
          "You work out why they are all gone with enough of a margin to do "
          "something about it, which none of them managed.",
          scenarios=("the-common-factor", "a-fifth-culture", "the-warning",
                     "reading-again")),

    Epoch("cartel", "The Settlement", "osteo",
          "You never fired a shot. You knew every price in the Verge before "
          "anybody else did, and the powers have discovered they are "
          "negotiating with a freight desk. The Charter has asked for a "
          "meeting, very politely.",
          "Nobody elected you and everybody depends on you. That is a position "
          "with a short natural life.",
          1.0 / 1500, "Redress",
          "Four powers agree on one thing at last, and the thing is you.",
          "You hand the register over to something that outlives you, and the "
          "lanes stay open because they are nobody's to close.",
          scenarios=("the-meeting", "a-squeeze", "the-audit", "open-books")),

    Epoch("apostasy", "The Canon", "lumen",
          "The wet stack is in the vault at Wick Gate and the hull came back up "
          "empty and singing. The Choir opened the canon a hand's width. What "
          "came across was not welcome so much as recognition.",
          "The canon is not a library, it is a consensus, and consensus is "
          "maintained. Yours is the newest and least agreed-with voice in it.",
          1.0 / 1800, "Dissent",
          "The canon closes over the gap where you were. Nothing is lost, "
          "which is the part that ought to worry somebody.",
          "The canon holds a stretch that is recognisably yours, and the Choir "
          "is one voice larger and one certainty smaller.",
          scenarios=("a-recension", "the-wet-vault", "consensus", "a-visitor")),

    Epoch("ruin", "The Quiet", "warn",
          "Forty-two systems of chitin and slow motion, and one hull with a "
          "good tank moving through the middle of it. You were right about all "
          "of it. There is nobody left who needs telling.",
          "There is nothing to fight and nothing to reach. What runs down now "
          "is the hull, the tank, and whatever you were keeping going for.",
          1.0 / 1200, "Attrition",
          "The tank, or the hull, or the reason. One of the three, and it "
          "hardly matters which.",
          "You find something still alive that did not know it was, and stop "
          "being the last of anything.",
          scenarios=("a-transponder", "the-vault-holds", "green-water",
                     "still-there")),
]
EPOCHS_BY_ID = {e.id: e for e in EPOCHS}
