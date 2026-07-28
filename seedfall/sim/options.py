"""Settings a player can change, every one of which does something.

The rule this module lives under is the project's usual one, pointed at a
screen that normally escapes it: **an option that changes nothing is a lie.**
So there is no display-density slider that adjusts nothing and no difficulty
label that multiplies by one. Every field below is read somewhere, and
`test_options` fails if one stops being.

Settings live on the `Game` and go through the save codec with everything
else, so a chronicle carries its own preferences.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.save import register


@register
@dataclass
class Options:
    """Player preferences. Defaults are the game exactly as it was."""

    #: Ask before anything irreversible — jettisoning, backfilling, refusing a
    #: power. Off means the confirmation dialogs are skipped entirely.
    confirm: bool = True

    #: Days that must pass before the chronicle writes itself to disk. 0 saves
    #: whenever the calendar moves, which is what it always did.
    autosave_days: int = 0

    #: How often an open instrument window re-reads the game, in milliseconds.
    instrument_ms: int = 900

    #: Inline explanations on screens that have something to explain.
    hints: bool = True

    #: Let a language model write the speech, if one is reachable. Off by
    #: default. The player may turn it on from the options page; a fresh
    #: process still starts off, and no check ever turns it on.
    voices: bool = False

    #: Which provider to use — "" means whichever answers first.
    llm_provider: str = ""

    #: Which model to ask for. "" means each provider's own default.
    llm_model: str = ""

    #: Offer the tutorial when a new chronicle opens. Read by `title.py`.
    tutorial: bool = True



#: id -> (label, kind, what it does, bounds)
FIELDS = (
    ("confirm", "Confirm irreversible actions", "bool",
     "Ask before jettisoning cargo, backfilling a trench, or refusing a "
     "power. Turning it off skips the dialog, not the consequence.", None),
    ("hints", "Inline hints", "bool",
     "The short explanations under panel headings. They are how most of this "
     "game explains itself, so leaving them on is not a beginner setting.",
     None),
    ("autosave_days", "Autosave every", "days",
     "Days that must pass before the chronicle is written to disk. At zero it "
     "saves whenever the calendar moves, which is the safest and the "
     "slowest.", (0, 30)),
    ("instrument_ms", "Instrument refresh", "ms",
     "How often an open instrument window re-reads the game. Lower is more "
     "responsive and more work.", (200, 5000)),
    ("voices", "Let a model write the speech", "bool",
     "If a language model is reachable, characters speak through it instead "
     "of through the game's own writing. The game is complete without it, and "
     "this changes the prose and never the content.", None),
    ("tutorial", "Offer the tutorial", "bool",
     "Whether a new chronicle offers to walk you through the first few "
     "things. It can also be started from the Help screen at any time.", None),
    ("llm_provider", "Which model to use", "choice",
     "Whichever answers first, or one you name. What is on this machine is "
     "listed below with whether it is actually responding.", None),
    ("llm_model", "Model name", "text",
     "Left blank, each provider uses its own default — llama3.2 for Ollama, "
     "and the current Sonnet or GPT for the hosted ones.", None),
)


def held(game) -> Options:
    """The options for this chronicle, made on first use for old saves."""
    if getattr(game, "options", None) is None:
        game.options = Options()
    return game.options


def get(game, name: str):
    return getattr(held(game), name, None)


def set_to(game, name: str, value) -> dict:
    """Change one setting, with its own bounds enforced here rather than by UI."""
    options = held(game)
    if not hasattr(options, name):
        return {"ok": False, "why": f"No such setting: {name}."}
    entry = next((f for f in FIELDS if f[0] == name), None)
    if entry is None:
        return {"ok": False, "why": f"{name} is not a setting a player sets."}
    _id, _label, kind, _doc, bounds = entry
    if kind == "bool":
        value = bool(value)
    elif kind in ("choice", "text"):
        value = str(value or "").strip()
    else:
        try:
            value = int(value)
        except (TypeError, ValueError):
            return {"ok": False, "why": f"{name} takes a number."}
        low, high = bounds
        value = max(low, min(high, value))
    setattr(options, name, value)
    if name in ("voices", "llm_provider", "llm_model"):
        apply(game)
    return {"ok": True, "name": name, "value": value}


def apply(game) -> None:
    """Push the settings that live outside the Game into the modules that hold
    them.

    Only the speech settings need this: `core/llm.py` keeps its own state so
    that it stays a `core` module and knows nothing about a `Game`. Called
    whenever a setting changes and once when a chronicle is opened.
    """
    from ..core import llm
    options = held(game)
    llm.configure(enabled=bool(options.voices),
                  provider_id=options.llm_provider,
                  model=options.llm_model)


def voices_live(game) -> bool:
    """Whether speech is actually coming from a model right now.

    The player's switch is necessary and not sufficient: something has to be
    answering. The screen reports which half is missing rather than showing a
    toggle that silently does nothing.
    """
    from ..core import llm
    return bool(get(game, "voices")) and llm.enabled()


def summary(game) -> list:
    """Every setting, its value, and the sentence describing what it does."""
    options = held(game)
    out = []
    for name, label, kind, doc, bounds in FIELDS:
        out.append({"name": name, "label": label, "kind": kind, "doc": doc,
                    "value": getattr(options, name), "bounds": bounds})
    return out


