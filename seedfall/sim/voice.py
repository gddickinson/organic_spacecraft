"""Making somebody say something, with or without a language model.

One entry point, `speak()`. It assembles who is talking, what they remember
about you, and what is happening, and returns a line.

If a model is reachable *and* the player switched it on, the line comes from
there, conditioned on the same material. If not — which is the default, and
what the whole suite measures — the line is built from the persona's own
sentence frames and the same recalled memories. Both paths use one set of
facts, so turning the model on changes the prose and never the content.

The rules that keep it honest:

- **The mood is decided here, from the mind's impression and the situation.**
  A model is never asked to decide whether a character likes you; it is told.
- **A model's answer is checked before it is used** — length, single line, no
  leaked instructions — and any failure falls back silently.
- **Nothing a voice says changes the game.** Speech reads state; it never
  writes it. That is why this can be off without breaking anything.
"""

from __future__ import annotations

from ..core import llm
from ..core.rng import RNG
from ..data.personas import PERSONAS_BY_ID
from . import memory as memory_sim

#: Above this impression a speaker is warm; below the negative, cold.
WARM_AT = 18.0
COLD_AT = -18.0

#: What a model is allowed to return.
MAX_CHARS = 320


def persona_for(mind) -> object:
    return PERSONAS_BY_ID.get(mind.persona) or PERSONAS_BY_ID["plain"]


def mood_for(mind, situation: str = "") -> str:
    """Decided here, never by the model. Situation first, then impression."""
    if situation in ("refuse", "warn", "deal", "farewell", "greet"):
        if situation != "greet":
            return situation
    impression = mind.impression()
    if impression >= WARM_AT:
        return "warm"
    if impression <= COLD_AT:
        return "cold"
    return "greet" if situation in ("", "greet") else situation


def _facts(game, mind, tags, extra: str) -> list:
    """What this speaker would actually bring up, in their own words."""
    out = []
    if extra:
        out.append(extra.rstrip(". ") + ".")
    for recalled in mind.recall(tags=tags, about="player", limit=2):
        out.append(_as_said(mind, recalled))
    return out


def _as_said(mind, recalled) -> str:
    """A memory, phrased as somebody bringing it up rather than as a record."""
    # Every lead ends on a colon or a comma rather than on a pronoun. The
    # first version led with "I have not forgotten that you" and the memory
    # texts also begin "you left the…", so half the lines said "that you you".
    lead = {
        "betrayal": "I have not forgotten:",
        "theft": "You took from me:",
        "kill": "There is blood in this:",
        "slight": "There was the matter of this:",
        "smuggling": "The hold you brought through here:",
        "trespass": "You have been where you should not:",
        "rescue": "You came when you did not have to:",
        "kindness": "You did me a turn:",
        "trade": "We have done business:",
        "contract": "You finished what you took on:",
        "alliance": "We have stood together:",
        "gift": "You were generous:",
        "news": "Word is that",
        "prior": "Before any of this,",
        "meeting": "We have met before:",
    }.get(recalled.kind, "There was this:")
    body = recalled.text.rstrip(".")
    if recalled.source == "heard":
        return f"Word reached us: {body}."
    return f"{lead} {body}."


def offline(game, mind, mood: str, facts: list) -> str:
    """The line the game writes itself. The default, and not a placeholder."""
    persona = persona_for(mind)
    frames = persona.frames.get(mood) or persona.frames.get("greet") or ("{fact}",)
    rng = RNG(f"voice:{mind.key}:{mood}:{game.day}:{len(mind.memories)}")
    frame = rng.pick(list(frames))
    line = frame.format(me=mind.name, fact=facts[0] if facts else "")
    line = " ".join(line.split())
    if len(facts) > 1:
        line = f"{line} {facts[1]}"
    if persona.tics and rng.chance(0.28):
        line = f"{line} {rng.pick(list(persona.tics))}"
    return line.strip()


def _prompt(game, mind, mood: str, facts: list, situation: str) -> tuple:
    persona = persona_for(mind)
    held = "\n".join(f"- {f}" for f in facts) or "- nothing in particular"
    system = (
        f"{persona.register}\n"
        f"You are {mind.name}. You address the player as {persona.address}. "
        f"Your feeling toward them right now is: {mood}. That is settled — do "
        f"not contradict it.\n"
        "Reply with ONE short spoken line, at most two sentences. No "
        "narration, no stage directions, no quotation marks, no markdown. "
        "Never invent events; only draw on what you are told you remember.")
    prompt = (
        f"Situation: {situation or 'you have just met'}.\n"
        f"What you remember that bears on this:\n{held}\n"
        "Say your line.")
    return system, prompt


def _acceptable(text: str) -> bool:
    if not text or len(text) > MAX_CHARS:
        return False
    lowered = text.lower()
    if any(bad in lowered for bad in ("as an ai", "language model",
                                      "i cannot", "system:", "assistant:")):
        return False
    return "\n" not in text.strip()


def speak(game, key: str, *, name: str = "", kind: str = "captain",
          persona: str = "plain", situation: str = "", tags=(),
          fact: str = "") -> dict:
    """One line from one speaker. Always returns something."""
    mind = memory_sim.mind_for(game, key, name=name, kind=kind,
                               persona=persona)
    if mind.persona != persona and persona != "plain":
        mind.persona = persona
    mood = mood_for(mind, situation)
    facts = _facts(game, mind, list(tags), fact)
    line = offline(game, mind, mood, facts)
    source = "written"

    if llm.enabled():
        system, prompt = _prompt(game, mind, mood, facts, situation)
        got = llm.complete(prompt, system,
                           temperature=persona_for(mind).temperature)
        if got and _acceptable(got.strip()):
            line, source = got.strip(), "model"

    return {"line": line, "mood": mood, "source": source,
            "speaker": mind.name, "persona": mind.persona,
            "impression": mind.impression(), "facts": facts}


def hail(game, key: str, **kwargs) -> str:
    """The common case: just the words."""
    return speak(game, key, **kwargs)["line"]

