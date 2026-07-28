"""The read on an engagement: who is winning, why, and what to do about it."""

from __future__ import annotations

from ..core.util import num, pct
from ..data.part_types import BANDS
from ..sim import assessment
from ..sim import tactical as tac
from .widgets import Panel, Pill, label, mono_label, note, spacer


def _turns(value: float) -> str:
    """Anything past the turn cap will not happen; say so rather than a number.

    A hull with one small mount against heavy armour genuinely needs a
    thousand turns, and printing that reads as a broken calculation instead of
    the point it is making.
    """
    from ..sim.combat import MAX_TURNS
    if value == float("inf"):
        return "never — they cannot hurt you"
    if value > MAX_TURNS:
        return f"not inside {MAX_TURNS} turns"
    return f"{value:.0f} turn(s)"


def build(battle) -> Panel:
    read = assessment.read(battle)
    weight = read["weight"]

    p = Panel("The read")
    p.add(Pill(weight["verdict"], weight["tint"] or "dim"))
    p.add_row("They break you in", _turns(weight["their_turns"]),
              "warn" if weight["their_turns"] < weight["my_turns"] else "")
    p.add_row("You break them in", _turns(weight["my_turns"]),
              "chloro" if weight["my_turns"] <= weight["their_turns"] else "")
    p.add(note("Both assume everything bears every turn, which it will not. "
               "Most fights end when somebody's nerve goes, not their hull."))

    p.add(spacer(4), mono_label("Them"))
    p.add_row("Doing", read["intent"])
    their_band = read["their_band"]
    p.add_row("Armed for",
              f"{BANDS[their_band[0]].lower()} to {BANDS[their_band[1]].lower()}"
              if their_band else "nothing — they cannot hurt you",
              "" if their_band else "chloro")
    p.add_row("Damage a turn", num(round(weight["their_throw"])),
              "warn" if weight["their_throw"] > weight["my_throw"] else "")
    p.add_row("Can you outrun them", "yes" if read["outrun"] else "no",
              "chloro" if read["outrun"] else "warn")

    # The per-mount breakdown used to be repeated here. `ui/firing_panel.py`
    # sits beside this one and says the same thing with the range band, the
    # magazine and the enemy's arcs as well, so two panels disagreeing about
    # the same guns is the only thing that could come of keeping both.

    if read["advice"]:
        p.add(spacer(4), mono_label("What to do about it"))
        for tint, text in read["advice"]:
            p.add(label(text, "", tint, wrap=True))
    return p
