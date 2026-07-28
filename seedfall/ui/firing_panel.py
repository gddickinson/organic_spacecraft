"""What each mount can do this turn, and what would fix the ones that cannot.

The log told you afterwards:

    The Mag Lance will not train that far — 47° outside its broadside arc.

which is the right sentence at the wrong time. Everything in it was knowable
before the turn: the arc, the bearing, the range band, whether the magazine is
dry. `sim/firing.py` works it out; this puts it where the decision is made.

The last line is the other half, and the half the plot never showed at all:
what *they* can bring to bear on *you*. Sitting in an enemy's forward arc is a
choice, and it should be one you know you are making.
"""

from __future__ import annotations

from ..sim import firing
from .widgets import Panel, label, note


def gunnery_picture(view, b):
    """Mount by mount: ready, or exactly what is stopping it."""
    side, other = b.player, b.enemy
    read = firing.readout(side, other, b.band)

    panel = Panel("What bears")
    panel.add(view.hint(read["summary"]))
    panel.add(label(
        f"Range {read['range']:.0f} · band {read['band']} · "
        f"{read['closing_word']}"
        + (f" {abs(read['closing']):.0f}/turn"
           if read["closing_word"] != "steady" else "")
        + f" · target {firing.compass(read['bearing'])}", "", "dim"))

    for shot in firing.solution(side, other, b.band):
        tint = "chloro" if shot.can_fire else (
            "warn" if shot.blocked_by == "dry" else "dim")
        panel.add_row(shot.name, shot.arc_name, tint)
        panel.add(label(shot.why, "note",
                        "" if shot.can_fire else "warn", wrap=True))

    turn = read["turn_to_bear"]
    if turn:
        panel.add(note(f"Coming about {turn:.0f}° would bring the first of "
                       "them on."))
    panel.add(label(read["danger"], "", "warn", wrap=True))
    return panel
