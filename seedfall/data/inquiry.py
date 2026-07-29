"""What research is made of, and how hard you push it.

Points used to be points: everything you did anywhere fed one number, so
nothing you chose to do changed what you could learn. A project now wants
*evidence* of particular kinds, and where each kind comes from is a different
part of the game — charts from surveying, specimens from landing on things,
hardware from taking hulls apart, readings from digging up what the Abyssals
left. A propulsion programme cannot be fed by botany.

The mix is derived from a technology's branch rather than written out for each
of sixty-one entries, so adding a technology needs no work here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Evidence:
    id: str
    name: str
    tint: str
    blurb: str
    where: str


EVIDENCE: list[Evidence] = [
    Evidence("survey", "Survey data", "lumen",
             "Orbits, spectra, gravity maps — the dull backbone of everything.",
             "Surveying bodies, and charting systems properly."),
    Evidence("specimen", "Specimens", "chloro",
             "Tissue, spores, whole organisms where they will fit in a jar.",
             "Landing parties, ocean dives and catalogued lifeforms."),
    Evidence("hardware", "Hardware", "steel",
             "Somebody else's engineering, in pieces, on a bench.",
             "Salvage from hulls you destroy, and wrecks you find."),
    Evidence("reading", "Xenolith readings", "xeno",
             "What the Abyssals left, and what it does when you look at it.",
             "Digs, relic sites and the Dry Choir's own work."),
]

EVIDENCE_BY_ID = {e.id: e for e in EVIDENCE}

#: branch -> the evidence a programme in it consumes, in shares that sum to 1.
BRANCH_MIX: dict[str, dict[str, float]] = {
    "structure":     {"survey": 0.35, "hardware": 0.45, "specimen": 0.20},
    "metabolism":    {"specimen": 0.60, "survey": 0.25, "reading": 0.15},
    "morphogenesis": {"specimen": 0.65, "reading": 0.20, "survey": 0.15},
    "survival":      {"specimen": 0.45, "survey": 0.35, "hardware": 0.20},
    "cognition":     {"hardware": 0.40, "reading": 0.35, "specimen": 0.25},
    "industry":      {"hardware": 0.55, "survey": 0.30, "specimen": 0.15},
    "propulsion":    {"hardware": 0.55, "survey": 0.35, "reading": 0.10},
    "fabrication":   {"hardware": 0.50, "survey": 0.25, "specimen": 0.25},
    "governance":    {"survey": 0.50, "specimen": 0.25, "hardware": 0.25},
    "xenology":      {"reading": 0.65, "specimen": 0.20, "survey": 0.15},
}

#: What a branch falls back on if it is not listed above.
DEFAULT_MIX = {"survey": 0.4, "hardware": 0.3, "specimen": 0.3}

#: A programme never needs more than this share of its cost in one kind, so a
#: run of bad luck in one activity cannot lock a whole branch.
MAX_SHARE = 0.7


@dataclass(frozen=True)
class Approach:
    id: str
    name: str
    blurb: str
    #: Multiplies how fast progress accrues.
    speed: float
    #: Multiplies the evidence drawn down per day.
    draw: float
    #: Chance per season of a setback.
    setback: float
    #: Chance per season of a leap.
    breakthrough: float
    #: Requires alien technology or captured hardware in hand.
    needs_precedent: bool = False
    #: How often the result comes out unreplicated — a technology that works
    #: and does not deliver all of it until somebody confirms the work. This
    #: is the cost that "days to unlock" could not see, and without it `push`
    #: was the fastest approach with no downside at all.
    provisional: float = 0.0


APPROACHES: list[Approach] = [
    Approach("careful", "Work it carefully",
             "One question at a time, properly answered. Nothing is wasted and "
             "nothing is hurried.",
             speed=1.0, draw=1.0, setback=0.0, breakthrough=0.03),

    Approach("parallel", "Run parallel tracks",
             "Three benches on the same problem. It costs three benches' worth "
             "of material and it does get there sooner.",
             speed=1.45, draw=1.9, setback=0.05, breakthrough=0.08,
             provisional=0.08),

    Approach("push", "Push it",
             "Skip the confirmations, build on results nobody has replicated. "
             "You will either be a season ahead or back where you started.",
             speed=1.9, draw=1.3, setback=0.28, breakthrough=0.18,
             provisional=0.55),

    Approach("copy", "Reverse-engineer",
             "Do not solve it — find somebody who already has and take theirs "
             "apart. Cheap, fast, and you will not fully understand it.",
             speed=1.7, draw=0.55, setback=0.12, breakthrough=0.05,
             needs_precedent=True,
             provisional=0.35),
]

APPROACHES_BY_ID = {a.id: a for a in APPROACHES}
DEFAULT_APPROACH = "careful"

#: A bench with nothing on it still runs at this fraction: reading, arguing,
#: and going over old results. Evidence buys the other two thirds. Without a
#: floor here a captain who sets a project on turn one and flies makes no
#: progress at all, which reads as a broken game rather than a hungry one.
STARVED_FLOOR = 0.35

#: Days on the bench per point of a technology's cost to confirm a
#: provisional result.
CONFIRM_DAYS_PER_COST = 0.22

#: A setback costs this share of the progress made so far.
SETBACK_LOSS = 0.35
#: A breakthrough is worth this share of the whole programme.
BREAKTHROUGH_GAIN = 0.30
