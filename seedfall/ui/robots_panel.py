"""The machines you own, and what each is worth where it is standing.

Split out of `ui/ship_view.py`, which was already at the edge of the file
limit, and along a real seam: the complement panel is about people — morale,
loyalty, how far through their run they are — and none of that applies to a
frame with a hull number.

**The one thing this screen must say** is the thing the design turns on: a
machine's level is not what it gives you. A Spar Rigger is level four and
teleoperated, and posted to a holding two AU away it works at 0.008 of a level,
which is a statue with an upkeep bill. If the panel showed "Spar Rigger · lvl 4"
it would be lying in exactly the way this project keeps finding — so every row
carries the *effective* figure, the round trip that produced it, and, when the
two disagree, the reason.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..data.robots import (ROBOTS_BY_ID, autonomy_name, autonomy_note,
                           autonomy_tint)
from ..sim import robots as robots_sim, telepresence as tele_sim
from .widgets import Panel, Pill, label, note, spacer

#: Below this share of its rated level, a machine is doing nothing useful and
#: the row says so in the warning tint. A tenth: at that point a level-four
#: frame is worth less than the cheapest hand aboard.
USEFUL = 0.10


def where_line(game, robot) -> str:
    """Where it is, in the words a captain would use."""
    posting = robot.posting or robots_sim.STOWED
    if posting == robots_sim.ABOARD:
        return "aboard"
    if posting == robots_sim.STOWED:
        return "stowed in the hold"
    colony = next((c for c in getattr(game, "colonies", [])
                   if f"colony:{c.id}" == posting), None)
    return f"at {colony.name}" if colony else "posted, and out of contact"


def lag_line(game, robot) -> str:
    """The round trip to it, said the way the distance deserves."""
    seconds = tele_sim.lag_seconds(game, robot)
    if seconds < 1.0:
        return "no delay worth the name"
    if seconds < 120:
        return f"{seconds:.0f} s round trip"
    if seconds < 7200:
        return f"{seconds / 60:.0f} min round trip"
    if seconds < 86400 * 2:
        return f"{seconds / 3600:.1f} h round trip"
    return f"{seconds / 86400:,.0f} days round trip"


def build(game) -> Panel:
    """One panel listing every machine, what it does and what it costs."""
    mine = robots_sim.owned(game)
    panel = Panel(f"Machines — {len(mine)}")
    if not mine:
        panel.add(note("None. A yard will build you hands that do not "
                       "breathe, do not sleep and do not ask; what they are "
                       "worth depends entirely on how far from you they end "
                       "up working."))
        return panel

    reading = robots_sim.summary(game)
    panel.add_row("On watch", f"{reading['watch']} of {reading['aboard']} aboard")
    if robots_sim.crewless(game):
        # The state the whole slice exists for, said plainly. A hull like
        # this needs no air and no food and cannot mutiny; what it needs is
        # metals and a yard.
        panel.add_row("Complement", "machines only", "lumen")
        panel.add(note("Nobody alive aboard. The machines hold the watches, "
                       "so this hull wants no air and no food — only the "
                       "metals they patch themselves with, and a yard to "
                       "mend at when they wear through."))
    if reading["posted"]:
        panel.add_row("Posted away", str(reading["posted"]))
    if reading["broken"]:
        panel.add_row("Stopped", str(reading["broken"]), "warn")
    panel.add_row("Upkeep a day", ", ".join(
        f"{amount:.3g} {key}" for key, amount in sorted(reading["upkeep"].items()))
        or "nothing")
    panel.add(spacer(4))

    for robot in mine:
        klass = ROBOTS_BY_ID[robot.class_id]
        got = tele_sim.effective(game, robot)
        share = got / klass.level if klass.level else 0.0
        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.addWidget(label(f"{robot.name} · {klass.name}"))
        line.addStretch(1)
        line.addWidget(Pill(autonomy_name(klass.autonomy),
                            autonomy_tint(klass.autonomy)))
        # The number that matters, against the number on the card. A machine
        # working at its rating says one figure; one that is not says both.
        line.addWidget(Pill(
            f"lvl {got:.1f}" if share > 0.995 else f"lvl {got:.2f}/{klass.level}",
            "warn" if share < USEFUL else "lumen"))
        panel.add(row)

        told = f"{where_line(game, robot)} · {lag_line(game, robot)}"
        if robot.broken:
            told += " · stopped, and wants a yard"
        elif robot.condition < 0.85:
            told += f" · {robot.condition * 100:.0f}% condition"
        panel.add(label(told, "note",
                        "warn" if robot.broken or share < USEFUL else ""))
        if share < USEFUL and not robot.broken:
            panel.add(label(
                f"{autonomy_note(klass.autonomy)} At this range it is doing "
                "nothing you are paying for.", "note", "warn"))
    return panel
