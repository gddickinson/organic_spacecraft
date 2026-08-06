"""Four powers, four kinds of justice, and not one of them is a police force.

The failure the survey found was not that the game lacked courts. It was that
every power enforced its will the *same* way — a reputation delta — so the
difference between offending the Charter and offending the Freeholds was a
number, and numbers are not politics. What a captain should learn over a
chronicle is not "crime costs 14 standing" but **who you can afford to be
hated by**, which is only a question if being hated by each of them is a
different experience.

So each forum here is built out of what `data/factions.py` already says that
power is, and the four are deliberately not comparable:

- **The Charter** fields no armed vessel anywhere. It cannot come for you and
  it never will. Its law is *administrative*: a registrar reads the file and
  writes on it. It will decide without you, it will accept a defence sent by
  despatch from the far side of the sector, and its whole armoury is the word
  *no* — no clearance, no licence, no gate. The most powerful institution in
  the Verge is also the only one that will never fire on you, and living
  under an interdict is meant to feel like drowning in paper rather than
  being hunted.

- **The Concordat** sells anyone a battleship and thinks in property. Its law
  is *arbitration*: a panel of yards, weighing what was taken against what is
  owed. It does not care what you believe and it will not punish you for it —
  but it has hulls, and it will send one for its cargo. You can post a bond
  against your own hull and walk out of the hearing, which is either a
  reprieve or the worst decision of the chronicle.

- **The Freeholds** have no consistent position on anything except margin,
  and accordingly **no forum at all**. There is no hearing, no verdict and
  nothing to attend. A claim becomes a posted price on your hull the day it
  is made, and the paper is sold on to whoever fancies collecting. You cannot
  be acquitted by the Freeholds because nobody there has the standing to
  acquit you. You can always, always settle — with whoever holds it now, for
  more than it started at. This is the only power that puts a bounty on the
  player, and it is the one with the least authority to.

- **The Dry Choir** runs on stacks nobody living designed and trades for
  recordings of wet cognition. Its law is *attainder by computation*: the
  record is evaluated, a verdict falls out, and no part of the process is
  audible to you. There is nowhere to go and nobody to speak to. What it
  imposes is anathema — the network simply stops answering — and the one
  thing it will take instead is a recording of the mind that did it.

`default_multiple` is the spine of the whole thing: what not turning up
costs. Every forum here decides in your absence, because a legal system you
can escape by ignoring it is scenery, and the survey already found one of
those.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sanction:
    """Something a forum can do to you, and how it is actually carried out."""

    id: str
    name: str
    blurb: str
    #: How `sim/enforce` makes this bite. One of: "debt" (money owed, and
    #: collectable at counters), "refuse" (no clearance, no tolls), "licence"
    #: (no seed work), "shun" (nobody answers at all), "hunt" (hulls come for
    #: you), "bond" (a debt secured on the hull itself).
    bite: str
    #: Rough ordering, worst last. The docket sorts by it and `warrants.worst`
    #: picks by it.
    weight: float


SANCTIONS: list[Sanction] = [
    Sanction("fine", "Assessment",
             "A sum, entered against you and collectable at any counter they "
             "hold.", "debt", 1.0),
    Sanction("distraint", "Distraint",
             "They take a share of everything you sell in their space until "
             "it is paid, and they do not ask first.", "debt", 2.0),
    Sanction("bond", "Bond against the hull",
             "You walk out today against security posted on your own ship. "
             "Default and the ship is theirs.", "bond", 3.0),
    Sanction("interdict", "Interdiction",
             "No quay they hold will clear you and no ring they hold will "
             "pass you. Nobody stops you; nobody lets you in either.",
             "refuse", 4.0),
    Sanction("licence", "Licence suspended",
             "Your authorisation to germinate is withdrawn. No seed, no "
             "settlement, no lineage, until it is restored.", "licence", 5.0),
    Sanction("anathema", "Anathema",
             "You are removed from the record. Their markets do not price "
             "for you, their rings do not wake for you, and no hail of "
             "yours is answered again.", "shun", 6.0),
    Sanction("bounty", "A price on the hull",
             "Posted openly, and sold on. Anybody who wants the money may "
             "come and take it, and some of them will.", "hunt", 7.0),
]

SANCTIONS_BY_ID: dict[str, Sanction] = {s.id: s for s in SANCTIONS}


@dataclass(frozen=True)
class Forum:
    """Where a power's law is decided, and on what terms."""

    power: str
    name: str
    #: "administrative" | "arbitration" | "none" | "attainder". Chooses the
    #: prose everywhere and the branch in `sim/tribunal.hear`.
    form: str
    #: What this power calls the thing. A Charter captain attends a *review*;
    #: a Concordat captain attends a *hearing*; nobody attends a *reckoning*.
    occasion: str
    blurb: str
    #: Where you must be to answer. "quay" — any quay they hold; "seat" —
    #: their capital only; "" — there is nowhere, and you never attend.
    seat: str
    #: Days between the summons and the decision.
    notice: float
    #: What the sanction is multiplied by if you never answer at all.
    default_multiple: float
    #: The sanctions this forum may impose, worst last.
    sanctions: tuple[str, ...]
    #: Share of the assessment that settles it before a verdict, or 0 if this
    #: forum will not be bought off before it has decided.
    settle_share: float
    #: What it says when it decides without you.
    absent: str


FORUMS: list[Forum] = [
    Forum(
        "charter", "The Registry of Licences", "administrative", "review",
        "A registrar, a file and a stamp. Nobody will come for you and "
        "nothing will be explained to you. The file simply grows, and one "
        "day the quays stop answering.",
        seat="quay", notice=90.0, default_multiple=1.8,
        sanctions=("fine", "interdict", "licence"), settle_share=0.75,
        absent="Reviewed in absence. The file notes that you were written to."),
    Forum(
        "concordat", "The Panel of Yards", "arbitration", "hearing",
        "Eleven fabricators with a standing interest in property. They will "
        "hear you, they will weigh it, and if it goes against you they will "
        "send a hull for what they are owed.",
        seat="quay", notice=60.0, default_multiple=2.2,
        sanctions=("fine", "distraint", "bond"), settle_share=0.60,
        absent="Heard in absence. The panel notes that you were sent for."),
    Forum(
        "freeholds", "no forum", "none", "posting",
        "There is no hearing. There is a price, it is posted where people "
        "who collect prices can read it, and it is sold on to whoever wants "
        "the work. Nobody there can acquit you because nobody there is "
        "anybody in particular.",
        seat="", notice=0.0, default_multiple=1.0,
        sanctions=("bounty",), settle_share=1.35,
        absent="Posted. Nobody was waiting for you to comment."),
    Forum(
        "sanhedrin", "The Reckoning", "attainder", "reckoning",
        "The record is evaluated. No part of this is audible to you and "
        "there is nowhere to go and stand. What comes out the other end is "
        "not an opinion about you; it is a result.",
        seat="", notice=30.0, default_multiple=1.0,
        sanctions=("fine", "anathema"), settle_share=0.9,
        absent="Reckoned. Your presence was not an input."),
]

FORUMS_BY_POWER: dict[str, Forum] = {f.power: f for f in FORUMS}


def forum_of(power: str) -> Forum | None:
    return FORUMS_BY_POWER.get(power)


def attends(power: str) -> bool:
    """Is there anywhere at all to answer a charge from this power?

    False for the Freeholds and the Dry Choir, and the screens read this
    rather than testing `form` themselves — an "Answer the summons" button
    that does nothing is worse than no button.
    """
    forum = FORUMS_BY_POWER.get(power)
    return bool(forum and forum.seat)
