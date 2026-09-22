"""Standing in a Kith gathering: a phrase sung to you, and what you sing back.

The singing hall used to be one step — sing, and they were pleased or they
were not. It is an exchange now, and it is the Kith's own lexicon
(`sim/kith`) that it teaches:

1. **sing** — somebody sings you a phrase: one sign of their lexicon
   (`data/kith.SIGNS`), chosen by who they are and where;
2. **answer** — sing it back: Art and INT, easier the better the sign's
   domain is already understood. Answered, the sign is learned a little
   (`kith.teach`) and they warm to you; misread, they cool;
3. **passage** — an elder you have answered well sings you the song of
   passage: the whole of that domain, a little further.

Nothing here is bought and nothing is conjured; the lexicon is the thing
listening at a gathering (`kith.listen`) fills, taught by other means.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data import kith as lexicon
from . import afoot_talk, checks, kith
from .afoot_state import say

#: How much of the gap to a sign's ceiling one good answer closes, and how
#: much of each sign of the domain the song of passage closes.
ANSWER_TEACH = 0.3
PASSAGE_TEACH = 0.12
#: A domain understood this well makes an answer average, this well
#: difficult; less, very difficult.
EASY_AT, HARD_AT = 0.6, 0.3


def phrase(game, walk, other):
    """The sign this Kith sings, the same one every time you are here."""
    return RNG(f"{game.seed}:kith:phrase:{walk.site}:{other.id}").pick(
        lexicon.SIGNS)


def difficulty(game, other) -> str:
    sign = lexicon.SIGNS_BY_ID.get(other.note.split(":")[-1]) \
        if other.note.startswith("phrase:") else None
    grasp = kith.domain(game, sign.domain) if sign else 0.0
    return ("average" if grasp >= EASY_AT else "difficult"
            if grasp >= HARD_AT else "very_difficult")


def on_sing(game, walk, who, other, offered, rng):
    sign = phrase(game, walk, other)
    other.note = f"phrase:{sign.id}"
    if kith.standing(game) >= 0:
        afoot_talk.shift(other, 1)
    text = (f"They sing a phrase — {sign.glyph}, something like “{sign.gloss}”"
            f" — and wait for it back.")
    say(walk, text, "")
    return {"line": afoot_talk.line(game, walk, other), "text": text}


def on_answer(game, walk, who, other, offered, rng):
    sign = lexicon.SIGNS_BY_ID[other.note.split(":")[-1]]
    got = afoot_talk.terms(game, walk, who, other, "answer")
    roll = checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about="an answer", what="art")
    if roll.ok:
        learned = kith.teach(kith.ensure(game), sign.id, ANSWER_TEACH)
        afoot_talk.shift(other, 1)
        kith.note(kith.ensure(game), game.day, "sang",
                  f"{who.name} answered “{sign.gloss}” at {walk.name}.")
        text = (f"{who.name} sings it back. It lands: “{sign.gloss}” is a "
                f"little clearer ({learned:+.0%}).")
    else:
        afoot_talk.shift(other, -1)
        text = f"{who.name} sings it back wrong. The silence is pointed."
    say(walk, text, "good" if roll.ok else "warn")
    return {"line": afoot_talk.line(game, walk, other), "text": text,
            "check": roll}


def on_passage(game, walk, who, other, offered, rng):
    sign = lexicon.SIGNS_BY_ID[other.note.split(":")[-1]]
    state = kith.ensure(game)
    gained = sum(kith.teach(state, s.id, PASSAGE_TEACH)
                 for s in lexicon.SIGNS if s.domain == sign.domain)
    domain = lexicon.DOMAINS[sign.domain]
    kith.note(state, game.day, "passage",
              f"An elder at {walk.name} sang the song of passage: {domain}.")
    text = (f"The elder sings the song of passage — the whole of {domain}, "
            f"a little further ({gained / 6:+.0%}).")
    say(walk, text, "good")
    return {"line": afoot_talk.line(game, walk, other, "warm"), "text": text}
