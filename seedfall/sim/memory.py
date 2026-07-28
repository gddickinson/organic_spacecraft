"""Minds: what characters, ships, factions and ports remember about you.

A named captain who watched you run from a fight, a harbourmaster you have sold
four charts to, a hull that has been breached twice under your command — each
of them holds an actual record, and that record is what conditions what they
say and how they treat you.

Three sources of memory, all requested and all here:

- **direct**, from things that happened between you and them;
- **heard**, from sector events an entity would plausibly know about, seeded
  from the game's own log rather than invented;
- **prior**, generated when a mind is first created so that somebody you have
  never met has a past.

Salience decays on the clock, so an old slight fades unless it was large or
repeated. Recall is by relevance to the situation at hand and not by recency,
because "the last thing that happened" is rarely the thing a person would
bring up.

This is data with rules, not prose. `sim/voice.py` turns it into speech, with
or without a language model.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.rng import RNG
from ..core.save import register

_uid = itertools.count(1)

#: How fast a memory fades, as a share of salience per day.
DECAY = 0.00055

#: Below this a memory stops being recalled, though it is not deleted — a
#: forgotten grievance that is reawakened by a similar event is the point.
FLOOR = 0.05

#: How many memories a mind keeps before the faintest are dropped.
KEEP = 60

#: What each kind of memory does to an impression, per unit of salience.
WEIGHT = {
    "kindness": 14.0, "trade": 5.0, "rescue": 22.0, "contract": 8.0,
    "alliance": 16.0, "gift": 10.0,
    "slight": -9.0, "theft": -18.0, "betrayal": -30.0, "kill": -34.0,
    "smuggling": -12.0, "trespass": -11.0,
    "news": 0.0, "prior": 0.0, "meeting": 1.0,
}


@register
@dataclass
class Memory:
    """One thing that happened, and how strongly it is still held."""
    id: int
    day: int
    kind: str
    text: str
    salience: float = 1.0
    tags: list = field(default_factory=list)
    about: str = ""            # who it concerns: "player", a faction id, …
    source: str = "direct"     # direct | heard | prior

    def weight(self) -> float:
        return WEIGHT.get(self.kind, 0.0) * self.salience


@register
@dataclass
class Mind:
    """One remembering thing: an officer, a captain, a ship, a power, a port."""
    key: str                   # "officer:3", "faction:charter", "ship:11"
    name: str
    kind: str                  # officer | captain | ship | faction | port
    persona: str = "plain"
    memories: list = field(default_factory=list)
    met: int = 0               # times the player has dealt with them
    first_met: int = -1

    # ── holding ────────────────────────────────────────────────────────────

    def remember(self, day: int, kind: str, text: str, salience: float = 1.0,
                 tags=None, about: str = "player",
                 source: str = "direct") -> Memory:
        made = Memory(id=next(_uid), day=day, kind=kind, text=text,
                      salience=max(0.05, salience), tags=list(tags or []),
                      about=about, source=source)
        self.memories.append(made)
        if len(self.memories) > KEEP:
            self.memories.sort(key=lambda m: m.salience)
            self.memories = self.memories[len(self.memories) - KEEP:]
        return made

    def decay(self, days: float) -> None:
        for memory in self.memories:
            memory.salience = max(0.0, memory.salience * (1 - DECAY) ** days)

    # ── recalling ──────────────────────────────────────────────────────────

    def recall(self, tags=None, about: str = "", limit: int = 4) -> list:
        """The memories this situation would actually bring up.

        Ranked by salience *and* by how well the tags match, so a mind meeting
        you at a customs desk brings up the last time it caught you rather than
        whatever happened most recently.
        """
        wanted = set(tags or [])
        scored = []
        for memory in self.memories:
            if memory.salience < FLOOR:
                continue
            if about and memory.about not in ("", about):
                continue
            overlap = len(wanted & set(memory.tags))
            # A backstory memory is colour, not the first thing anybody says.
            # Unweighted, every greeting opened with two pieces of somebody's
            # childhood instead of the business at hand.
            weight = {"prior": 0.25, "heard": 0.7}.get(memory.source, 1.0)
            scored.append((overlap * 1.6 + memory.salience * weight, memory))
        scored.sort(key=lambda pair: -pair[0])
        return [memory for _score, memory in scored[:limit]]

    def impression(self) -> float:
        """How this mind feels about the player, from what it holds. −100..100."""
        total = sum(m.weight() for m in self.memories if m.about == "player")
        return max(-100.0, min(100.0, total))

    def grudge(self) -> list:
        """The memories actually responsible for a poor impression."""
        bad = [m for m in self.memories
               if m.about == "player" and m.weight() < -1.0
               and m.salience >= FLOOR]
        bad.sort(key=lambda m: m.weight())
        return bad


# ── the store on the Game ──────────────────────────────────────────────────

def minds(game) -> dict:
    if getattr(game, "minds", None) is None:
        game.minds = {}
    return game.minds


def mind_for(game, key: str, name: str = "", kind: str = "captain",
             persona: str = "plain") -> Mind:
    """Find or make a mind. Making one gives it a past."""
    store = minds(game)
    existing = store.get(key)
    if existing is not None:
        return existing
    made = Mind(key=key, name=name or key, kind=kind, persona=persona)
    _prior(game, made)
    store[key] = made
    return made


def _prior(game, mind: Mind) -> None:
    """A life before you met them, drawn from the sector rather than invented."""
    rng = RNG(f"prior:{mind.key}:{game.seed}")
    day = max(0, game.day - rng.int(400, 3000))
    # Phrased to follow "Before any of this, …" — so third person, about the
    # speaker, and never starting with a pronoun. The first version mixed "I"
    # into the lead and "was refused" into the text and produced "Before any
    # of this, I was refused a berth and has not forgotten it".
    seeds = {
        "captain": [("prior", "they learned the trade running ore out of {port}"),
                    ("prior", "they lost a hull to the Bloom at {system}"),
                    ("prior", "they were refused a berth at {port}, and have "
                              "not forgotten it")],
        "officer": [("prior", "they served four years on a Yards hauler"),
                    ("prior", "they were at {system} when the colony failed"),
                    ("prior", "they took this berth to get away from {port}")],
        "ship": [("prior", "this hull was laid down at {port}"),
                 ("prior", "this hull has been breached once, and mended"),
                 ("prior", "this hull carried relief to {system} and arrived "
                           "late")],
        "faction": [("prior", "they have held {system} since before the Bloom"),
                    ("prior", "they lost three hulls in the Verge last year")],
        "port": [("prior", "this quay has stood two hundred years"),
                 ("prior", "this quay was blockaded once, and remembers who "
                           "broke it")],
    }
    pool = seeds.get(mind.kind, seeds["captain"])
    systems = [s.name for s in game.galaxy.systems] or ["the Verge"]
    ports = [s.port.name for s in game.galaxy.systems if s.port] or ["a quay"]
    for kind, template in rng.shuffle(list(pool))[:2]:
        mind.remember(day, kind,
                      template.format(system=rng.pick(systems),
                                      port=rng.pick(ports)),
                      salience=rng.float(0.4, 0.9), about="", source="prior")


def note(game, key: str, kind: str, text: str, salience: float = 1.0,
         tags=None, name: str = "", entity: str = "captain") -> Memory:
    """Record something against one mind. The ordinary way in."""
    mind = mind_for(game, key, name=name, kind=entity)
    if kind != "news":
        mind.met += 1
        if mind.first_met < 0:
            mind.first_met = game.day
    return mind.remember(game.day, kind, text, salience, tags)


def broadcast(game, kind: str, text: str, salience: float = 0.6,
              tags=None, among=("faction",)) -> int:
    """Something the sector heard. Everyone of these kinds picks it up."""
    told = 0
    for mind in minds(game).values():
        if mind.kind not in among:
            continue
        mind.remember(game.day, kind, text, salience * 0.7, tags,
                      about="player" if kind in WEIGHT and
                      WEIGHT.get(kind, 0) else "", source="heard")
        told += 1
    return told


def tick(game, days: float) -> None:
    """Fade everything a little. Called from the one clock."""
    for mind in minds(game).values():
        mind.decay(days)


def impression_of(game, key: str) -> float:
    mind = minds(game).get(key)
    return mind.impression() if mind else 0.0


def summary(game) -> list:
    """Every mind that holds anything, worst impression first."""
    rows = [(m, m.impression()) for m in minds(game).values() if m.memories]
    rows.sort(key=lambda pair: pair[1])
    return rows
