"""Playing the captain's own life out, one term at a time.

The beginning screen asks who you are with three choices and works the rest
out. Traveller asks it by making you live it: enlist somewhere, and then
answer the same question four or five times — **another term, or out?**

This is that dialog, and it owns no rules. The service list, the odds, the
term and the muster-out are all `sim/captain_path.py`; every figure shown is
quoted from it before the button that risks it is pressed, because the whole
point of the throw is that the captain chose to take it.

Split out of `ui/beginning_view.py` rather than added to it: a screen that
runs a sequence is a different shape from one that lays out four columns of
cards, and the beginning view was already most of the way to the ceiling.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from ..core.util import pct
from ..sim import captain_path as path_sim
from . import theme
from .widgets import Card, Panel, button, label, mono_label, note


class LifePathDialog(QDialog):
    """Enlist, serve, and get out while you still can."""

    def __init__(self, choices, parent=None, game=None):
        super().__init__(parent)
        self.choices = choices
        self.game = game
        self.path = None
        self.taken = False
        self.setWindowTitle("Before the ship — SEEDFALL")
        self.setStyleSheet(theme.stylesheet())
        self.setModal(True)
        self.resize(900, 720)
        self._outer = QVBoxLayout(self)
        self._build()

    # ── the screen ────────────────────────────────────────────────────────

    def _clear(self) -> None:
        while self._outer.count():
            item = self._outer.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _rebuild(self) -> None:
        self._clear()
        self._build()

    def _build(self) -> None:
        head = label("Before the ship", "h1")
        head.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._outer.addWidget(head)
        self._outer.addWidget(note(
            "Four years a term. Each one is survived or it is not, and a "
            "career that throws you out is over. Everything you learn you "
            "keep — and so does everything that happens to you."))
        body = QWidget()
        across = QHBoxLayout(body)
        across.setContentsMargins(0, 0, 0, 0)
        across.setSpacing(10)
        across.addWidget(self._left(), 1)
        across.addWidget(self._record(), 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(body)
        self._outer.addWidget(scroll, 1)
        self._outer.addWidget(self._along_the_bottom())

    def _left(self) -> QWidget:
        return self._services() if self.path is None else self._term()

    def _services(self) -> Panel:
        p = Panel("Who would have you")
        p.add(note("Every service will take a look at you. What they ask you "
                   "to survive, and how fast they promote, is what tells "
                   "them apart."))
        for career in path_sim.services():
            card = Card(selectable=False)
            card.add(label(career.name, "h3", "chloro"))
            card.add(label(career.blurb, "", wrap=True))
            stat, target = career.survive
            up_stat, up_target = career.advance
            card.add(note(f"Survival on {stat.upper()} {target}+ · "
                          f"advancement on {up_stat.upper()} {up_target}+"))
            card.add(note("Teaches: " + ", ".join(
                s.replace("_", " ") for s in career.skills[:5])))
            card.add(button(f"Enlist in the {career.name}",
                            lambda _=False, c=career.id: self._enlist(c),
                            kind="primary"))
            p.add(card)
        return p

    def _term(self) -> Panel:
        odds = path_sim.odds(self.path)
        p = Panel(f"{self.path.career.name} — {self.path.terms} term(s)")
        ok, why = path_sim.may_serve(self.path)
        if odds:
            p.add(mono_label(f"Term {odds['term']}, as a "
                             f"{odds['rank'].lower()}"))
            p.add_row(f"Survive it — {odds['survive_stat'].upper()} "
                      f"{odds['survive_score']}", pct(odds["survive"]),
                      "chloro" if odds["survive"] >= 0.7 else "warn")
            p.add_row(f"Be promoted — {odds['advance_stat'].upper()} "
                      f"{odds['advance_score']}", pct(odds["advance"]))
            p.add(note("Four more years. If it goes wrong the career ends "
                       "there and you leave with what you have."))
        else:
            p.add(label(self.path.record.ended or "That is the end of it.",
                        "", "warn", wrap=True))
        p.add_buttons(
            button("Serve another term", self._serve, kind="primary",
                   enabled=ok, why=why),
            button("Muster out", self._muster,
                   enabled=self.path.terms > 0,
                   why="You have not served a day yet."))
        return p

    def _record(self) -> Panel:
        p = Panel("The record so far")
        if self.path is None:
            p.add(note("Nothing yet. Enlist, and it starts."))
            return p
        record = self.path.record
        p.add(mono_label("Characteristics"))
        from ..sim.checks import CHARACTERISTICS
        for cid, name, _blurb in CHARACTERISTICS:
            p.add_row(name, str(record.score(cid)))
        if record.skills:
            p.add(mono_label("Skills"))
            for name, level in sorted(record.skills.items(),
                                      key=lambda kv: -kv[1]):
                p.add_row(name.replace("_", " ").title(), str(level))
        if record.terms:
            p.add(mono_label("What happened"))
            for term in record.terms:
                p.add(label(f"{term.number}. {term.rank} — {term.skill}",
                            "note",
                            "warn" if term.mishap else ""))
                if term.event:
                    p.add(label(term.event, "note", wrap=True))
                if term.mishap:
                    p.add(label(term.mishap, "note", "warn", wrap=True))
        return p

    def _along_the_bottom(self) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        done = self.path is not None and self.path.over
        h.addWidget(note("A life you played is the life your captain had. "
                         "Skip it and they get the one their origin implies, "
                         "as before."))
        h.addStretch(1)
        h.addWidget(button("Skip it", self.reject))
        take = button("Take this life", self._accept, kind="primary",
                      enabled=done,
                      why=("Serve at least one term, then muster out."
                           if self.path is not None else
                           "Enlist somewhere first."))
        take.setObjectName("path_take")
        h.addWidget(take)
        return row

    # ── the acts, every one of them the sim's ─────────────────────────────

    def _enlist(self, service: str) -> None:
        self.path = path_sim.begin(self.game, service)
        self._rebuild()

    def _serve(self) -> None:
        path_sim.serve(self.path)
        self._rebuild()

    def _muster(self) -> None:
        path_sim.muster(self.path)
        self._rebuild()

    def _accept(self) -> None:
        if self.path is None or not self.path.over:
            return
        path_sim.finish(self.path, self.choices)
        self.taken = True
        self.accept()


def play(choices, parent=None, game=None) -> bool:
    """Open it. True when a life was played and taken."""
    dialog = LifePathDialog(choices, parent, game)
    dialog.exec()
    return dialog.taken
