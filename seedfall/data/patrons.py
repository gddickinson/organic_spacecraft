"""Who is actually asking, and what they did not say.

The contract board posts work from *offices*: the Charter wants tonnage
moved, the Concordat wants a system charted. That is how a freight desk
reads and it is not how Traveller reads. In Traveller the work comes from a
**patron** — a person, in a room, with a reason — and the first thing a
referee is told about a patron is that the job may not be what they said it
was.

Both halves are here.

**The person** is a `PatronKind`: what they are, what they post, how well
they pay, and how straight they play it. A Charter factor is dull and
honest; a fixer on a frontier quay pays better than the work is worth and
you should ask yourself why.

**The lie** is a `Twist`: one fact about the job that was true when it was
posted and was not on the posting. Every twist is something the game can
already do to you — a cargo the destination seizes (`sim/lawlevel.py`), a
fee that arrives short, a power that takes an interest — so a ticket that
turns is not a special case, it is the ordinary machinery finding you.

And every twist has a `tell`: the thing you could have noticed. A patron
you can read (`sim/patrons.reads`) is a patron you can refuse.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PatronKind:
    id: str
    #: What they are called to their face.
    name: str
    blurb: str
    #: Contract kinds this sort of patron posts. Empty means any.
    posts: tuple = ()
    #: What they add to the posted fee, as a multiple. A fixer pays over the
    #: odds because the work is worse than it looks.
    pays: float = 1.0
    #: How likely the ticket carries a twist, 0..1.
    slippery: float = 0.0
    #: How hard they are to read: subtracted from the check.
    guarded: int = 0
    #: How they open, in the room.
    line: str = ""


PATRONS: tuple = (
    PatronKind(
        "factor", "Factor", pays=1.0, slippery=0.05, guarded=0,
        blurb="A salaried buyer for an office that has existed longer than "
              "either of you. The fee is the fee, the paperwork is correct, "
              "and nothing about the afternoon will be memorable.",
        posts=("deliver", "prospect"),
        line="They have the posting printed out. They read the relevant "
             "clause aloud, in full, and ask whether you have questions."),
    PatronKind(
        "broker", "Broker", pays=1.08, slippery=0.14, guarded=1,
        blurb="Takes a cut from both ends and makes no secret of it. Knows "
              "the board better than the harbourmaster does.",
        line="They buy the coffee, which is how you know the margin is "
             "theirs. The terms come out in the order that suits them."),
    PatronKind(
        "agent", "Institute agent", pays=1.12, slippery=0.12,
        guarded=2, posts=("survey", "relic", "expedition"),
        blurb="Represents an institute, a collection, or somebody who "
              "prefers the word institute. Interested in the work and "
              "faintly surprised that money has come up.",
        line="They talk about the object for twenty minutes before they "
             "mention the fee, and the twenty minutes are the interesting "
             "part."),
    PatronKind(
        "shipmaster", "Shipmaster", pays=1.0, slippery=0.08,
        guarded=0, posts=("deliver", "bounty", "prospect"),
        blurb="Another captain, one hull and no office, subcontracting work "
              "they cannot reach. Treats you the way they would want to be "
              "treated, which cuts both ways.",
        line="They have flown the route. They tell you where the run is "
             "tight, and it costs them nothing to do it."),
    PatronKind(
        "fixer", "Fixer", pays=1.30, slippery=0.42, guarded=3,
        blurb="Names no employer and is not asked to. Pays over the odds, "
              "which is the single most reliable thing anyone can tell you "
              "about the work.",
        line="They do not write anything down, and they are already "
             "agreeing before you have finished asking."),
    PatronKind(
        "quartermaster", "Quartermaster", pays=1.05, slippery=0.10,
        guarded=1, posts=("deliver", "prospect", "bounty"),
        blurb="Holds a garrison's stores and a garrison's temper. The work "
              "is real, the deadline is not negotiable, and the standing is "
              "worth more than the fee.",
        line="They give you the tonnage, the date and the berth number, in "
             "that order, and then wait."),
)
PATRONS_BY_ID = {p.id: p for p in PATRONS}


@dataclass(frozen=True)
class Twist:
    id: str
    name: str
    #: What it turns out to be, read out when it fires.
    blurb: str
    #: What you could have noticed beforehand, read out when you read them.
    tell: str
    #: Contract kinds it can attach to. Empty means any.
    kinds: tuple = ()
    #: True for a twist in the captain's favour.
    good: bool = False


TWISTS: tuple = (
    Twist(
        "contraband", "The cargo is not what it says",
        "The manifest says one thing and the bond seals say another. "
        "Whatever is in those drums, the port you are taking it to will "
        "take it off you and charge you for the privilege.",
        "They are oddly specific about which bay it goes in, and they do "
        "not want it inspected before it is loaded.",
        kinds=("deliver",)),
    Twist(
        "short", "The fee is not the fee",
        "The money that arrives is a fraction of the money that was "
        "posted, with an explanation about a clause and a schedule. There "
        "is nobody to take it up with.",
        "The paperwork is signed by somebody who is not in the room, and "
        "they change the subject when you ask who that is."),
    Twist(
        "hot", "Somebody else wanted this",
        "The job is done and the wrong people know your hull did it. "
        "Whoever was on the other side of this has your transponder code "
        "and a long memory.",
        "They never once say whose hull it was, or whose seam, or whose "
        "charts — only that it needs doing and that you look capable.",
        kinds=("bounty", "relic", "survey")),
    Twist(
        "generous", "It was worth more than they said",
        "The work turns out to be worth more than the posting, and the "
        "patron pays the difference without being asked. It happens.",
        "They quote the fee as a floor rather than a figure, and seem "
        "faintly embarrassed about the number.",
        good=True),
)
TWISTS_BY_ID = {t.id: t for t in TWISTS}

#: What a short fee actually pays, and what a generous one adds.
SHORT_SHARE, GENEROUS_SHARE = 0.45, 0.35

#: How much heat a `hot` ticket puts on the power that lost by it.
HOT_HEAT = 0.35
