"""The people who run the quays, what they want, and what can be held over them.

A port was a bag of services. You docked at a Fleet Hub, pressed *Buy*, and
dealt with an interface. Nobody was there. The game already had `sim/memory.py`
— minds that remember, keyed for "officer | captain | ship | faction | **port**"
— and at the start of a chronicle that store is empty and stays empty, because
nothing ever attaches a person to a place you return to fifty times.

So: every quay has a harbourmaster. They have a name, a temperament, something
they want, and — the part that makes this politics rather than shopkeeping —
something that can be held over them.

**A lever is not blackmail as a verb.** It is knowing a thing, and both of you
knowing you know it. What it buys is discretion: a search not run, a berth for
a captain whose standing does not merit one, a contract shown to you before it
is posted. What it costs is that it is spent, and that they remember being
leant on, which is not the same as remembering being helped.

The identity here is *derived* — same seed, same person, for the life of the
chronicle — while what they think of you lives in `minds`, which already
persists. See `sim/officials.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Temperaments. Each shapes what an official wants, what they will overlook,
#: and how much a favour costs them.
@dataclass(frozen=True)
class Temper:
    id: str
    name: str
    blurb: str
    #: How much regard one favour costs them, and how readily they bend.
    price: float
    bend: float


TEMPERS = [
    Temper("procedural", "Procedural",
           "Runs the quay by the schedule and expects everyone else to. Not "
           "hostile; simply unmoved.", price=1.4, bend=0.5),
    Temper("obliging", "Obliging",
           "Would rather the paperwork went smoothly for everybody, which "
           "makes them useful and slightly unreliable.", price=0.8, bend=1.3),
    Temper("acquisitive", "Acquisitive",
           "Has a list of things the office does not supply and a view about "
           "who might.", price=1.0, bend=1.1),
    Temper("frightened", "Careful",
           "Has been caught out once already and has no intention of being "
           "caught out again.", price=1.6, bend=1.5),
    Temper("ambitious", "Ambitious",
           "Intends to be running something larger than a quay, and is "
           "keeping a list of who was useful.", price=0.9, bend=0.9),
]
TEMPERS_BY_ID = {t.id: t for t in TEMPERS}


@dataclass(frozen=True)
class Lever:
    id: str
    name: str
    #: How it reads when you learn it.
    learned: str
    #: What holding it lets you say, in one line.
    holds: str
    #: Which tempers this can be true of. Empty means any.
    tempers: tuple = ()


LEVERS = [
    Lever("skim", "A discrepancy in the manifests",
          "The tonnages {who} signs off do not match the tonnages that land. "
          "It is not large. It is consistent.",
          "You know about the manifests, and they know you know.",
          tempers=("acquisitive", "ambitious")),

    Lever("debt", "A debt at the wrong table",
          "{who} owes money to people who do not post their rates, and the "
          "office would take a dim view of the company.",
          "You know who they owe, and it is not a bank.",
          tempers=("frightened", "obliging", "acquisitive")),

    Lever("kin", "Family on the wrong register",
          "{who} has kin working unlicensed ground two jumps out. The "
          "Charter's position on that is written down.",
          "You know where their family is registered, and where it is not.",
          tempers=("procedural", "frightened", "obliging")),

    Lever("passage", "A berth that was never logged",
          "A hull put in here last year and does not appear in the register. "
          "{who} was on duty and the entry is simply absent.",
          "You know about the hull that never docked.",
          tempers=("obliging", "acquisitive", "frightened")),

    Lever("ambition", "A letter to the wrong office",
          "{who} has been writing to a rival power about a post. It is not "
          "treason. It would end a career.",
          "You have seen who they have been writing to.",
          tempers=("ambitious", "procedural")),
]
LEVERS_BY_ID = {lever.id: lever for lever in LEVERS}


@dataclass(frozen=True)
class Favour:
    id: str
    name: str
    blurb: str
    #: What it costs: regard if asked as a friend, or a lever if leant on.
    regard: float
    #: Minimum regard to ask without a lever at all.
    needs_regard: float
    #: How long the favour holds, in days. 0 means it is instant.
    lasts: int = 0


FAVOURS = [
    Favour("wave_through", "Wave the search through",
           "The inspection is signed off without anybody opening a hold. "
           "Holds for a season at this quay.",
           regard=28.0, needs_regard=45.0, lasts=90),

    Favour("berth", "A berth regardless",
           "Docking rights here whatever the office thinks of you, for as "
           "long as it lasts.",
           regard=22.0, needs_regard=35.0, lasts=180),

    Favour("word_first", "First sight of the board",
           "You see what is coming in before it is posted. A better class of "
           "work, and less competition for it.",
           regard=18.0, needs_regard=30.0, lasts=120),

    Favour("quiet_price", "A quiet price",
           "Goods move at the office rate rather than the posted one, this "
           "once.",
           regard=14.0, needs_regard=25.0, lasts=0),

    Favour("warning", "A word before it happens",
           "If anything is coming your way from this office — a levy, a "
           "search, a claim — you hear about it first.",
           regard=20.0, needs_regard=40.0, lasts=240),
]
FAVOURS_BY_ID = {f.id: f for f in FAVOURS}

#: Regard bands, for a screen. A stranger sits in "correct" — somebody you
#: have never met is not cold to you, they are simply doing their job, and the
#: first version put `START_REGARD` in the cold band by accident.
BANDS = (
    (-100.0, "will not deal with you", "warn"),
    (-40.0, "cold", "warn"),
    (-5.0, "correct", "dim"),
    (35.0, "helpful", ""),
    (70.0, "on your side", "chloro"),
)

#: What a stranger starts at.
START_REGARD = 5.0

#: Leaning on somebody costs *more* of their regard than asking as a friend,
#: not less. The first cut made it cheaper as well as unconditional, which
#: made the lever strictly better than the relationship and removed the whole
#: decision.
LEAN_MULTIPLIER = 1.6

#: And each time you lean, the ceiling honest dealing can reach comes down.
#: You can buy your way back into being useful to them; you cannot buy your
#: way back into being liked.
CAP_PER_LEAN = 12.0

#: Regard gained per honest dealing at a quay, and the ceiling that route
#: reaches on its own. Trade alone should make somebody friendly, never
#: devoted — the last stretch has to be earned some other way.
PER_DEALING = 2.2
DEALING_CAP = 48.0
