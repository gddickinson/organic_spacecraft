"""Choosing who you are, with every choice stating what it will do.

Four columns of picks and one column that answers "so what": the standing you
will open with, the technologies you will already hold, the hull, the purse,
and — because it is the thing a new captain cannot possibly know — how much of
the sector this posting can actually reach.

Nothing here computes anything. `sim/beginning.preview()` does, and a check
builds the game and compares it against that preview, so this screen cannot
promise what the opening does not deliver.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLineEdit, QScrollArea,
                             QVBoxLayout, QWidget)

from ..core.util import credits as cr
from ..data.beginnings import (CREW_CHOICES, ORIGINS, POSTINGS,
                               STOCKS)
from ..data.factions import FACTIONS_BY_ID
from ..sim import beginning as beginning_sim
from . import theme
from ..sim.crew import CREW_ROLES
from .widgets import (Card, Panel, button, label, mono_label,
                      note, spacer)

#: Filled in order, so the first three are the bridge the game has always
#: shipped. `CREW_CHOICES` is the one list of station ids.
DEFAULT_STATIONS = CREW_CHOICES


class BeginningDialog(QDialog):
    """Returns a `Choices` in :attr:`choices`, or None if dismissed."""

    def __init__(self, seed: str = "", parent=None):
        super().__init__(parent)
        self.choices = None
        self.seed = seed
        self.picked = beginning_sim.default()
        self.setWindowTitle("A commission of your own")
        self.setMinimumSize(1180, 800)
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(26, 20, 26, 20)
        self._outer.setSpacing(8)
        self._build()

    # ── frame ──────────────────────────────────────────────────────────────

    def _clear(self) -> None:
        while self._outer.count():
            item = self._outer.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _rebuild(self) -> None:
        self._clear()
        self._build()

    def _build(self) -> None:
        head = label("Before the first jump", "h1")
        head.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._outer.addWidget(head)
        self._outer.addWidget(note(
            "Every one of these is a real axis in the simulation. What each "
            "gives and what it costs is written on it, and the column on the "
            "right is the chronicle you would actually open."))

        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        for column in (self._stocks(), self._origins(), self._rest(),
                       self._outcome()):
            holder = QWidget()
            v = QVBoxLayout(holder)
            v.setContentsMargins(0, 0, 0, 0)
            v.addWidget(column)
            v.addStretch(1)          # let the panel keep its natural height
            h.addWidget(holder, 1)

        # Four columns of cards do not fit a dialog, and Qt's answer to that is
        # to squeeze them until the buttons are half a button tall. Scroll
        # instead of compressing.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(row)
        self._outer.addWidget(scroll, 1)

        name_row = QWidget()
        nh = QHBoxLayout(name_row)
        nh.setContentsMargins(0, 0, 0, 0)
        nh.addWidget(label("Hull name", "label"))
        self.name_box = QLineEdit(self.picked.name)
        self.name_box.setFixedWidth(300)
        nh.addWidget(self.name_box)
        nh.addStretch(1)
        nh.addWidget(button("Take the standard commission", self._standard))
        nh.addWidget(button("Begin", self._accept, kind="primary"))
        self._outer.addWidget(name_row)

    def _pick(self, field: str, value) -> None:
        setattr(self.picked, field, value)
        if field == "stock":
            allowed = beginning_sim.origins_for(value)
            if self.picked.origin not in {o.id for o in allowed}:
                self.picked.origin = allowed[0].id
        if field in ("stock", "origin"):
            hulls = beginning_sim.hulls_for(self.picked.stock,
                                            self.picked.origin)
            if self.picked.hull not in {c.id for c in hulls}:
                self.picked.hull = hulls[0].id
            self.picked.crew = ()
        self._rebuild()

    # ── the four columns of picks ──────────────────────────────────────────

    def _stocks(self) -> Panel:
        p = Panel("Stock")
        p.add(note("What you are made of. It decides which hull families will "
                   "have you, and what you need to stay alive."))
        for stock in STOCKS:
            p.add(self._card(stock.name, stock.blurb, stock.gives, stock.costs,
                             chosen=self.picked.stock == stock.id,
                             on_pick=lambda s=stock: self._pick("stock", s.id)))
        return p

    def _origins(self) -> Panel:
        p = Panel("Origin")
        p.add(note("What you did before this, which decides who owes you a "
                   "favour and who wants a word."))
        for origin in beginning_sim.origins_for(self.picked.stock):
            p.add(self._card(origin.name, origin.blurb, origin.gives,
                             origin.costs,
                             chosen=self.picked.origin == origin.id,
                             on_pick=lambda o=origin: self._pick("origin", o.id)))
        return p

    def _rest(self) -> Panel:
        p = Panel("Hull and posting")
        p.add(note("The frame you open in, and whose space you open in."))
        for chassis in beginning_sim.hulls_for(self.picked.stock,
                                               self.picked.origin)[:5]:
            p.add(self._card(
                chassis.name,
                f"{chassis.role} · {chassis.crew} berths · {chassis.cargo} t · "
                f"jump {chassis.jump:.1f}",
                "", "", chosen=self.picked.hull == chassis.id,
                on_pick=lambda c=chassis: self._pick("hull", c.id)))
        p.add(spacer(6))
        for posting in POSTINGS:
            p.add(self._card(posting.name, posting.blurb, posting.gives, "",
                             chosen=self.picked.posting == posting.id,
                             on_pick=lambda x=posting: self._pick("posting", x.id)))
        p.add(spacer(6), self._bridge())
        return p

    def _bridge(self) -> QWidget:
        """Which stations the opening bridge holds.

        `Choices.crew` has been honoured by `beginning.apply` from the day it
        was written, and no screen ever set it — so the card said "Officers:
        2" for a dry stack and every chronicle opened with the same three,
        whoever you were. Six stations exist; the lineage decides how many of
        them you take.
        """
        room = beginning_sim.crew_slots(self.picked.stock)
        chosen = list(self.picked.crew) or list(DEFAULT_STATIONS[:room])
        holder = QWidget()
        col = QVBoxLayout(holder)
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(mono_label("The bridge"))
        col.addWidget(note(f"Your lineage sails with {room}. Pick which "
                           f"{room} of the six stations you take out."))
        for station, role_name, _stat, what in CREW_ROLES:
            on = station in chosen
            full = len(chosen) >= room and not on
            row = button(("● " if on else "○ ") + role_name
                         + (f" — {what}" if not full else " — no berth left"),
                         lambda _=False, sid=station: self._toggle_station(sid),
                         kind="primary" if on else "", enabled=on or not full)
            col.addWidget(row)
        return holder

    def _toggle_station(self, station: str) -> None:
        room = beginning_sim.crew_slots(self.picked.stock)
        chosen = list(self.picked.crew) or list(DEFAULT_STATIONS[:room])
        if station in chosen:
            chosen.remove(station)
        elif len(chosen) < room:
            chosen.append(station)
        self.picked.crew = tuple(chosen)
        self._rebuild()

    def _card(self, title, blurb, gives, costs, chosen, on_pick) -> Card:
        card = Card()
        card.add(label(title, "h3", "chloro" if chosen else ""))
        if blurb:
            card.add(note(blurb))
        if gives:
            card.add(label(f"+ {gives}", "", "chloro", wrap=True))
        if costs:
            card.add(label(f"− {costs}", "", "warn", wrap=True))
        card.add(button("Chosen" if chosen else "Choose", on_pick,
                        kind="primary" if chosen else ""))
        return card

    # ── the column that answers "so what" ──────────────────────────────────

    def _outcome(self) -> Panel:
        forecast = beginning_sim.preview(self.picked)
        p = Panel("What you would open with")
        p.add_row("Hull", forecast["chassis"].name)
        p.add_row("Purse", cr(forecast["credits"]))
        p.add_row("Officers", str(forecast["crew"]))
        p.add_row("Technologies", str(len(forecast["tech"])))
        p.add(spacer(4))
        p.add(label("Standing", "label"))
        for fid, value in forecast["standing"].items():
            faction = FACTIONS_BY_ID.get(fid)
            if faction is None or faction.hidden:
                continue
            p.add_row(faction.short or faction.name, f"{value:+.0f}",
                      tint="warn" if value < -20 else
                      ("chloro" if value > 20 else None))
        if forecast["cargo"]:
            p.add(spacer(4))
            p.add(label("In the hold", "label"))
            for cid, tonnes in forecast["cargo"].items():
                p.add_row(cid, f"{tonnes:g} t")
        p.add(spacer(4))
        p.add(note(
            "The sector is generated from the seed, so how much of it this "
            "posting can reach is only known once it exists. The chart says "
            "so on the first screen."))
        return p

    # ── leaving ────────────────────────────────────────────────────────────

    def _standard(self) -> None:
        self.picked = beginning_sim.default()
        self.choices = self.picked
        self.accept()

    def _accept(self) -> None:
        self.picked.name = (self.name_box.text().strip()
                            or beginning_sim.default().name)
        self.choices = self.picked
        self.accept()
