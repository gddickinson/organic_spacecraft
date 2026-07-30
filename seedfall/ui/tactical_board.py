"""The readiness board: what a fight would look like, in figures.

Lifted out of `ui/tactical_window.py` to keep both files small. It renders a
`sim/readiness.report` and knows nothing else — no rules, no arithmetic of its
own, no second opinion about who would win.

Four blocks, in the order a captain would ask them:

- **the verdict** — who breaks whom first, and how many turns each way;
- **the guns** — which mounts bear at the opening range, and what stops the
  ones that do not;
- **the hull** — what a full volley costs in heat, against the fault line
  rather than against the ceiling, because the fault line is where a hull
  starts cooking itself;
- **the seats** — what taking each station personally is worth this turn.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ..data.part_types import BANDS
from .widgets import label, mono_label, note

#: Seats in the order the bridge is laid out, and how each reads when nobody
#: is describing a gain in the same units.
SEATS = (("helm", "Helm"), ("gunnery", "Gunnery"), ("engineering", "Engineering"))

#: Beyond this many turns a figure stops being information. A starting NAVIS
#: with one photic flash against a Charter warship reads "break them in 895.6
#: turns", and an engagement that runs past twenty is already a different
#: kind of problem. Past the bar the board says so in words instead.
TOO_LONG = 60.0


def _turns(count: float) -> str:
    return f"{count:.1f}" if count <= TOO_LONG else "never, in practice"


class TacticalBoard(QWidget):
    """Everything `sim/readiness.report` found, as text a captain can read."""

    def __init__(self):
        super().__init__()
        self.col = QVBoxLayout(self)
        self.col.setContentsMargins(0, 0, 0, 0)
        self.col.setSpacing(5)
        self.col.addStretch(1)

    def _clear(self) -> None:
        while self.col.count():
            item = self.col.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def show_report(self, report: dict, engaged: bool = False) -> None:
        self._clear()
        head = ("Against the hull actually shooting at you" if engaged
                else "If it came to it, right now")
        self.col.addWidget(label(head, "h3"))
        self.col.addWidget(label(report["against"], "", wrap=True))
        self._verdict(report)
        self._guns(report)
        self._hull(report)
        self._seats(report)
        self.col.addStretch(1)

    def _verdict(self, report: dict) -> None:
        weight = report["weight"]
        self.col.addWidget(label(f"You are {weight['verdict']}.", "",
                                 tint=weight["tint"]))
        self.col.addWidget(mono_label(
            f"you break them: {_turns(weight['my_turns'])} · "
            f"they break you: {_turns(weight['their_turns'])}"))
        wants = report["wants"]
        if wants is not None:
            self.col.addWidget(note(
                f"Opening at {report['band_name'].lower()} range; your "
                f"armament wants {BANDS[wants[0]].lower()} to "
                f"{BANDS[wants[1]].lower()}."))
        self.col.addWidget(note(
            "You are the faster hull and can break off."
            if report["outrun"] else
            "They are the faster hull — breaking off is their choice, not "
            "yours."))

    def _guns(self, report: dict) -> None:
        guns = report["guns"]
        self.col.addWidget(label("Guns", "h3"))
        self.col.addWidget(mono_label(
            f"{len(guns['bearing'])} of {guns['total']} bear at this range"))
        for part, gap in guns["off_arc"]:
            self.col.addWidget(note(
                f"{part.name}: {round(gap)}° outside its arc — come about."))
        for part in guns["out_of_range"]:
            self.col.addWidget(note(f"{part.name}: not worth firing this far."))
        if report["turn_to_bear"]:
            self.col.addWidget(note(
                f"{round(report['turn_to_bear'])}° of turn brings the most "
                "onto them."))

    def _hull(self, report: dict) -> None:
        heat = report["heat"]
        self.col.addWidget(label("The hull", "h3"))
        tint = "bad" if heat["over"] else ""
        self.col.addWidget(mono_label(
            f"a full volley: {heat['mounts']} mount(s), "
            f"+{heat['heat']:.0f} heat → {heat['after']:.0f} "
            f"of a {heat['fault']:.0f} fault line"))
        if heat["over"]:
            self.col.addWidget(label(
                "Everything at once takes the hull over its fault line and it "
                "starts cooking itself. Pick the mounts.", "", tint=tint,
                wrap=True))

    def _seats(self, report: dict) -> None:
        seats = report["seats"]
        self.col.addWidget(label("The bridge", "h3"))
        for key, name in SEATS:
            seat = seats.get(key)
            if seat is None:
                continue
            says = seat.get("says") or f"{seat['gain']:+.2f} to hit"
            self.col.addWidget(mono_label(
                f"{name:<12} officer {seat['level']:.1f}"))
            self.col.addWidget(note(f"    taking it yourself: {says}"))
        if report["consorts"]:
            self.col.addWidget(note(
                "In company: " + ", ".join(report["consorts"])))
