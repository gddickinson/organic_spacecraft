"""The shapes an officer's story is written in — shared by `data/arcs.py` and
`data/arcs_late.py`, which hold the twelve stories themselves.

Kept apart for the reason `data/help_types.py` is: the prose runs to two
modules, and each needs the shapes without importing the other.
"""

from __future__ import annotations

from dataclasses import dataclass

#: What can set a beat off. A **date** beat arrives when it arms; a **place**
#: beat when the ship is in the system the arc chose; a **loyalty** beat when
#: the officer trusts the captain enough to say it; an **event** beat when the
#: ship does the thing (`EVENTS`).
TRIGGERS = ("date", "place", "loyalty", "event")

#: The events a beat can wait on, and what counts: an engagement resolved
#: through `sim/aftermath`, a Bloom mass burned (`responses.fought` rising),
#: a holding founded.
EVENTS = ("fight", "burn", "colony")

#: How a place is chosen from the galaxy when a beat arms. `sim/arc_places`
#: owns the rules; these are the names the prose may use.
PLACES = ("bloom", "freehold_capital", "freehold_port", "choir_port",
          "charter_capital", "yards_port", "moon", "wreck", "race",
          "anchor:hollow", "anchor:cradle", "region:hollow", "region:cradle")


@dataclass(frozen=True)
class Choice:
    """One answer to a beat, and everything it does — stated before choosing.

    `credits` below zero is spent; above zero it is paid **out of `purse`**,
    a power's exchequer, because nothing in this game is conjured. `rep` and
    `cargo` are pairs so the table stays hashable and ordered.
    """

    key: str
    words: str
    thinks: str               # what the officer will think, in their voice
    outcome: str = ""         # the chronicle's line; "" says the words
    credits: int = 0
    purse: str = ""
    rep: tuple = ()           # ((power, delta), ...)
    loyalty: float = 0.0      # this officer
    bridge: float = 0.0       # everybody else aboard
    cargo: tuple = ()         # ((commodity, tonnes), ...) — negative is spent
    signature: bool = False   # the last beat, well resolved


@dataclass(frozen=True)
class Beat:
    """One step of a story: what sets it off, what they say, what you can say.

    `text` and `hint` take slots filled by `sim/arc_beats`: {place}, {ship},
    {hull}, {rival}, {seat}, {song}, {after}. `after` maps the previous beat's
    choice key ("" for a lapse) to a sentence, so a story remembers.
    """

    trigger: str
    arg: str
    title: str
    text: str
    hint: str
    choices: tuple
    window: int = 0           # days to meet the trigger; 0 is the default
    after: tuple = ()         # ((previous choice key, sentence), ...)


@dataclass(frozen=True)
class Signature:
    """What a story, well finished, leaves an officer able to do.

    `effects` are keyed like `crew.TRAITS` effects and summed by
    `sim/arcs.signature_effects`; each key is read at exactly one point in
    the game, listed above `data/arcs.SIGNATURES`.
    """

    id: str
    name: str
    blurb: str
    effects: tuple            # ((key, value), ...)


@dataclass(frozen=True)
class Arc:
    id: str
    title: str
    blurb: str
    beats: tuple
    signature: str            # an id in `data/arcs.SIGNATURES`


def choice(key, words, thinks, **fx) -> Choice:
    """A `Choice` with its effects as keywords — the tables read as prose."""
    return Choice(key, words, thinks, **fx)
