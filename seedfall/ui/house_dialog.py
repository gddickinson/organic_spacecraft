"""The new-line dialog: pick a hauler, a master, the ports and the rules,
and see what it will clear before you commit.

The forecast printed is `freightlines.open_terms` — the same call
`open_line` makes before it opens — so what the dialog says is what the house
is committing to. The three suggestions are `lineforecast.suggest`: the
freight desk's own ranking, priced as lines. Nothing here prices anything.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (QComboBox, QDialog, QGridLayout, QHBoxLayout,
                             QSpinBox, QVBoxLayout, QWidget)

from ..core.util import credits as cr
from ..data.commodities import BY_ID
from ..data.freightlines import CADENCES
from ..sim import freightlines as lines_sim
from ..sim import haulers as haulers_sim
from ..sim import lineforecast
from ..sim import lineroute
from .widgets import button, label, mono_label, note


class NewLineDialog(QDialog):
    """Sets :attr:`opened` to the new line, or leaves it None."""

    def __init__(self, view, parent=None):
        super().__init__(parent or view.win)
        self.view = view
        self.game = view.game
        self.opened = None
        self.setWindowTitle("A new freight line")
        self.setMinimumWidth(840)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 16)
        outer.setSpacing(8)
        outer.addWidget(label("A new freight line", "h2"))
        self.form = QGridLayout()
        self.form.setHorizontalSpacing(10)
        self.hauler = self._combo("Hauler", [
            (f"{s.name} ({s.chassis_def.name})", s.uid)
            for s, ok, _why in haulers_sim.haulers(self.game) if ok])
        self.master = self._combo("Master", [
            (f"{m.name} — {m.rating}, {cr(m.wage)}/mo", m.id)
            for m in self.game.house.masters if m.line_id is None])
        known = [s for s in self.game.galaxy.systems
                 if s.market is not None and str(s.id) in self.game.register]
        self.origin = self._combo("Home port", [(s.name, s.id) for s in known])
        self.dest = self._combo("Far port", [(s.name, s.id) for s in known])
        self.good = self._combo("Carrying", [])
        self.tonnes = self._spin("Tonnes a trip", 1, 99_999, 60)
        self.max_buy = self._spin("Buy under (0: any price)", 0, 999_999, 0)
        self.min_sell = self._spin("Sell over (0: what it fetches)", 0,
                                   999_999, 0)
        self.cadence = self._combo("Cadence", [
            ("continuous" if d == 0 else f"every {d} days", d)
            for d in CADENCES])
        grid = QWidget()
        grid.setLayout(self.form)
        outer.addWidget(grid)
        outer.addWidget(mono_label("The freight desk suggests"))
        self.suggested = QWidget()
        self.suggested_box = QVBoxLayout(self.suggested)
        self.suggested_box.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.suggested)
        outer.addWidget(mono_label("Forecast"))
        self.told = label("", "", wrap=True)
        outer.addWidget(self.told)
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 8, 0, 0)
        h.addStretch(1)
        self.go = button("Open the line", self.commit, kind="primary")
        h.addWidget(self.go)
        h.addWidget(button("Cancel", self.reject, kind="flat"))
        outer.addWidget(row)
        self.origin.currentIndexChanged.connect(lambda _i: self._goods())
        for combo in (self.hauler, self.master, self.dest, self.good,
                      self.cadence):
            combo.currentIndexChanged.connect(lambda _i: self.update_forecast())
        for spin in (self.tonnes, self.max_buy, self.min_sell):
            spin.valueChanged.connect(lambda _v: self.update_forecast())
        self._hauler_hold()
        self.hauler.currentIndexChanged.connect(lambda _i: self._hauler_hold())
        picks = self._suggestions()
        self._goods()
        if picks:
            self.use(picks[0]["line"])
        elif self.dest.count() > 1:
            self.dest.setCurrentIndex(1)

    # ── form ───────────────────────────────────────────────────────────────

    def _combo(self, name: str, items) -> QComboBox:
        combo = QComboBox()
        for text, value in items:
            combo.addItem(text, value)
        combo.setAccessibleName(name)
        self._place(name, combo)
        return combo

    def _spin(self, name: str, lo: int, hi: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(lo, hi)
        spin.setValue(value)
        spin.setAccessibleName(name)
        self._place(name, spin)
        return spin

    def _place(self, name: str, widget) -> None:
        """Two fields to a row, so the dialog fits a small window."""
        at = self._placed = getattr(self, "_placed", -1) + 1
        row, col = at // 2, (at % 2) * 2
        self.form.addWidget(label(name, "dim"), row, col)
        self.form.addWidget(widget, row, col + 1)

    def _hauler_hold(self) -> None:
        hull = self._hull()
        if hull is not None:
            self.tonnes.setValue(int(lineroute.hauler_stats(self.game,
                                                            hull).cargo))

    def _hull(self):
        uid = self.hauler.currentData()
        return next((s for s in self.game.fleet if s.uid == uid), None)

    def _goods(self) -> None:
        """The lawful goods the home port stocks."""
        origin = self.game.galaxy.systems[self.origin.currentData()] \
            if self.origin.count() else None
        was = self.good.currentData()
        self.good.blockSignals(True)
        self.good.clear()
        if origin is not None and origin.market is not None:
            for cid in origin.market.stock:
                good = BY_ID.get(cid)
                if good is not None and good.legal:
                    self.good.addItem(good.name, cid)
        index = self.good.findData(was)
        self.good.setCurrentIndex(max(0, index))
        self.good.blockSignals(False)
        self.update_forecast()

    def _suggestions(self) -> list:
        hull = self._hull()
        picks = lineforecast.suggest(self.game, hull,
                                     self.master.currentData() or 0) \
            if hull is not None else []
        if not picks:
            self.suggested_box.addWidget(note(
                "Nothing the desk knows of clears anything within her reach. "
                "Visit more ports: the house needs a factor at both ends."))
        systems = self.game.galaxy.systems
        for pick in picks:
            line, told = pick["line"], pick["forecast"]
            good = BY_ID[line.good]
            self.suggested_box.addWidget(button(
                f"{systems[line.origin].name} → {systems[line.dest].name} · "
                f"{good.short} · {cr(told['per90'])} in 90 days · "
                f"{told['p_cargo']:.1%} of cargoes lost",
                lambda _=False, ln=line: self.use(ln), kind="flat"))
        return picks

    def use(self, line) -> None:
        """Fill the form from a suggestion."""
        self.origin.setCurrentIndex(self.origin.findData(line.origin))
        self.dest.setCurrentIndex(self.dest.findData(line.dest))
        self.good.setCurrentIndex(self.good.findData(line.good))
        self.update_forecast()

    # ── the forecast, and the act ──────────────────────────────────────────

    def draft(self):
        return lines_sim.draft(
            self.game, self.hauler.currentData() or 0,
            self.master.currentData() or 0, self.origin.currentData() or 0,
            self.dest.currentData() or 0, self.good.currentData() or "",
            self.tonnes.value(), self.max_buy.value() or None,
            self.min_sell.value() or None, self.cadence.currentData() or 0)

    def update_forecast(self) -> dict:
        terms = lines_sim.open_terms(self.game, self.draft())
        self.terms = terms
        self.go.setEnabled(terms["ok"])
        self.told.setText(describe(self.game, terms))
        return terms

    def commit(self) -> None:
        res = lines_sim.open_line(self.game, self.draft())
        if not res["ok"]:
            self.view.win.toast(res["why"], "warn")
            return
        self.opened = res["line"]
        self.accept()


def describe(game, terms: dict) -> str:
    """The forecast in words — every figure straight from `open_terms`."""
    if not terms["ok"]:
        return terms["why"]
    told = terms["forecast"]
    lines = []
    if terms["ferry_days"]:
        lines.append(f"She reaches her home port in {terms['ferry_days']} "
                     "days, in ballast.")
    first = told["first"]
    if not told["ok"]:
        lines.append(f"As things stand she would wait: {told['why']}.")
    else:
        lines.append(
            f"First trip: {first['tonnes']:,} t at {cr(first['price'])}, "
            f"selling at about {cr(first['sell_price'])}; clears "
            f"{cr(told['per_trip'])} over {round(told['cycle'])} days, after "
            f"wages and upkeep.")
        lines.append(
            f"Next 90 days: {told['trips90']} trip(s), {cr(told['per90'])} — "
            "her own cargoes move both prices against her as they would.")
    lines.append(
        f"Risk: {told['p_cargo']:.1%} of cargoes lost, "
        f"{told['p_lost']:.1%} chance a trip loses the hull. Route: "
        + " → ".join(told["route"]) + ".")
    return " ".join(lines)
