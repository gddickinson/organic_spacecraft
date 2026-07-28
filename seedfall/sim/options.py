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
    #: default and off unless `SEEDFALL_LLM` is also set — this switch cannot
    #: turn on something the environment has not permitted.
    voices: bool = False



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
     "If a language model is reachable and permitted, characters speak "
     "through it instead of through the game's own writing. The game is "
     "complete without it and this changes prose, never content.", None),
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
    else:
        try:
            value = int(value)
        except (TypeError, ValueError):
            return {"ok": False, "why": f"{name} takes a number."}
        low, high = bounds
        value = max(low, min(high, value))
    setattr(options, name, value)
    return {"ok": True, "name": name, "value": value}


def voices_live(game) -> bool:
    """Speech through a model needs both the player's switch and the machine's.

    Two switches on purpose. The environment one says a model may be used at
    all; this one says the player wants it. Neither implies the other, and the
    screen says so rather than showing a toggle that silently does nothing.
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


