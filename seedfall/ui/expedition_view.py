"""The ground. A landing party, a map revealed one step at a time, and a finite
number of days before the supplies run out."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ..core.util import num, pct
from ..data.expedition import FEATURES, PARTY_CAPACITY, TERRAIN
from ..sim import expedition as exp_sim
from ..sim import wayhome as wayhome_sim
from ..sim import weather as weather_sim
from ..sim.fieldwork import conclude_expedition
from . import theme
from . import painting
from .widgets import (Bar, Panel, Pill, View, button, label, mono_label, note,
                      spacer)

CELL = 62


class ZoneMap(QWidget):
    """The landing zone: fogged tiles, terrain tint, feature marks."""

    picked = pyqtSignal(int, int)

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setFixedSize(CELL * exp_sim.W + 2, CELL * exp_sim.H + 2)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, ev):  # noqa: N802
        x = int(ev.position().x() // CELL)
        y = int(ev.position().y() // CELL)
        if 0 <= x < exp_sim.W and 0 <= y < exp_sim.H:
            self.picked.emit(x, y)

    @painting.safe_paint
    def paintEvent(self, _ev):  # noqa: N802
        exp = self.win.game.expedition
        if exp is None:
            return
        p = QPainter(self)
        if not painting.alive(self, p):
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#060f0d"))

        for t in exp.tiles:
            r = QRectF(t.x * CELL + 1, t.y * CELL + 1, CELL - 2, CELL - 2)
            if not t.seen:
                p.fillRect(r, QColor("#0b1512"))
                p.setPen(QPen(QColor(theme.LINE), 1))
                p.drawRect(r)
                continue

            terrain = TERRAIN[t.terrain]
            base = QColor(theme.tint(terrain.tint))
            base.setAlpha(38 if t.visited else 22)
            p.fillRect(r, base)
            p.setPen(QPen(QColor(theme.LINE2 if t.visited else theme.LINE), 1))
            p.drawRect(r)

            if t.feature and not t.resolved:
                f = FEATURES[t.feature]
                p.setPen(QPen(QColor(theme.tint(f.tint)), 1.6))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(r.center(), 9, 9)
            elif t.feature and t.resolved:
                p.setPen(QPen(QColor(theme.INK3), 1))
                c = r.center()
                p.drawLine(int(c.x() - 5), int(c.y() - 5),
                           int(c.x() + 5), int(c.y() + 5))
                p.drawLine(int(c.x() - 5), int(c.y() + 5),
                           int(c.x() + 5), int(c.y() - 5))

            if (t.x, t.y) == exp_sim.LANDER:
                p.setPen(QPen(QColor(theme.tint("chloro")), 1.4))
                p.drawRect(r.adjusted(9, 9, -9, -9))

            p.setFont(QFont(theme.mono_family(), 7))
            p.setPen(QColor(theme.INK3))
            p.drawText(r.adjusted(4, 2, -2, 0), Qt.AlignmentFlag.AlignLeft,
                       terrain.name.split()[0][:6].upper())

        # the party
        pr = QRectF(exp.x * CELL + 1, exp.y * CELL + 1, CELL - 2, CELL - 2)
        p.setPen(QPen(QColor(theme.tint("lumen")), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(pr.center(), 15, 15)
        p.end()


def _prize(odds: dict) -> str:
    """What success pays, in words rather than a range of zeroes."""
    reward = odds.get("reward")
    if reward == "lore":
        return "a field note"
    if reward in (None, "none"):
        return "nothing"
    low, high = odds.get("low", 0), odds.get("high", 0)
    if not high:
        return str(reward)
    if reward == "credits":
        return f"{low:,}–{high:,} credits"
    return f"{low}–{high} {reward}"


class ExpeditionView(View):
    # The zone map is rebuilt with the rest of the screen. Caching it on the
    # view does not work: refresh() destroys the container it sits in, and Qt
    # takes the child down with it.

    def build(self) -> None:
        exp = self.game.expedition
        if exp is None:
            self.head("No party in the field",
                      "Land one from the system screen, on a body you have surveyed.")
            self.buttons(button("Back to the system", lambda: self.win.go("system")))
            return

        self.head(f"Landing Zone — {exp.body_name}",
                  f"Day {exp.days} on the ground · {exp.supply} days of supply left")

        holder = QWidget()
        h = QHBoxLayout(holder)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(14)
        zone = ZoneMap(self.win)
        h.addWidget(zone, 0, Qt.AlignmentFlag.AlignTop)
        h.addWidget(self._status(exp), 1)
        self.col.addWidget(holder)

        if not exp.over:
            self.col.addWidget(self._here(exp))
            self.col.addWidget(self._move_panel(exp))
        else:
            self.col.addWidget(self._debrief(exp))
        self.col.addWidget(self._log(exp))

    # ── panels ─────────────────────────────────────────────────────────────

    def _status(self, exp) -> Panel:
        p = Panel("Party")
        sky = weather_sim.current(exp)
        p.add_row("Overhead", sky.name,
                  "warn" if sky.danger > 1.5 else ("osteo" if sky.cost else "dim"))
        p.add(note(weather_sim.note(exp)))
        if sky.cost or sky.danger > 1.0:
            p.add_row("Crossing costs", f"+{sky.cost} day(s)" if sky.cost else "—",
                      "warn" if sky.cost >= 2 else "")
            p.add_row("Hazards", f"×{sky.danger:g}",
                      "warn" if sky.danger >= 2 else "")
        p.add(spacer(3))
        p.add_row("Supply", f"{exp.supply} days",
                  "warn" if exp.supply <= 3 else "")
        p.add_bar(max(0, exp.supply) / 20, "warn" if exp.supply <= 3 else "chloro")
        # **How far the lander is, which nothing said.** The ground's one piece
        # of arithmetic: reach the pad and the haul comes up capped at what four
        # people can lift; run out of supply first and 60% of it stays where it
        # fell. `sim/wayhome.py` costs the cheapest known route with the same
        # function `move` charges, so the figure here is what walking it spends.
        way = wayhome_sim.standing(exp)
        if way["home"]:
            p.add_row("The lander", "you are standing on it", "chloro")
        elif way["stranding"]:
            p.add_row("The walk home", f"{way['days']} days — {way['why']}",
                      "warn")
        else:
            p.add_row("The walk home",
                      f"{way['days']} days over {way['steps']} step(s) of known "
                      f"ground · {way['spare']} day(s) to spare",
                      "warn" if way["spare"] <= 2 else "")
            if way["pinned"]:
                p.add(note(way["why"]))
        p.add_row("Rover", f"{exp.rover}/10", "warn" if exp.rover <= 3 else "")
        p.add_bar(exp.rover / 10, "osteo")
        p.add_row("Carrying", f"{round(exp.carried)} / {round(PARTY_CAPACITY)}",
                  "warn" if exp.carried > PARTY_CAPACITY else "")
        # What that actually means when the lander goes up. "140 / 60" in
        # amber left the captain to work out that eighty tonnes would cease
        # to exist, and said nothing about the further share stranding takes.
        if exp.carried > 0:
            land = exp_sim.landing_forecast(exp)
            if land["left"] > 0.5:
                p.add_row("Comes up", f"{round(land['kept'])} t — "
                                      f"{round(land['left'])} t stays", "warn")
            else:
                p.add_row("Comes up", f"{round(land['kept'])} t", "chloro")
            p.add_row("If they strand", f"{round(land['stranded'])} t", "warn")
        p.add(spacer(4), mono_label("On the ground"))
        for oid in exp.officers:
            o = next((x for x in self.game.officers if x.id == oid), None)
            if o is None:
                continue
            hurt = oid in exp.injured
            p.add_row(f"{o.name} · {o.role_name}",
                      "injured" if hurt else f"level {o.level}",
                      "warn" if hurt else "")
        if exp.haul:
            p.add(spacer(4), mono_label("Secured"))
            for k, v in exp.haul.items():
                p.add_row(k, f"{round(v)}")
        if exp.study:
            p.add_row("alien understanding", f"{round(sum(exp.study.values()))} pts")
        return p

    def _here(self, exp) -> Panel:
        t = exp.here
        terrain = TERRAIN[t.terrain]
        p = Panel(terrain.name)
        p.add(note(terrain.blurb))

        if t.feature and not t.resolved:
            f = FEATURES[t.feature]
            p.add(spacer(4))
            p.add(label(f.name, "h3", f.tint))
            p.add(label(f.blurb, "", wrap=True))
            # The odds, who would take it, what it pays and what a failure
            # risks. The screen used to say "(science, difficulty 3)", which is
            # a one-in-three with a green officer and five-in-six with a good
            # one, and never named the prize at all.
            for i, (text, stat, _difficulty, _reward) in enumerate(f.options):
                odds = exp_sim.odds_for(exp, i, self._party())
                p.add(spacer(3))
                p.add(label(text, "h3", "chloro" if odds["chance"] >= 0.6
                            else ("warn" if odds["chance"] < 0.35 else "")))
                if stat:
                    who = odds["who"] or "nobody aboard"
                    p.add_row(f"{odds['chance']:.0%} — {who} on {stat}",
                              _prize(odds),
                              "chloro" if odds["chance"] >= 0.6 else "warn")
                    # A near miss and an outright botch used to be the same
                    # outcome — nothing at all — so the screen only ever said
                    # what success paid. It says what a botch is worth now,
                    # because "it fails" and "it fails and you keep a third"
                    # are different decisions.
                    if odds.get("near", 0) > 0.01 and odds.get("spoiled"):
                        p.add_row("Close but botched",
                                  f"{odds['near']:.0%} of the time — about "
                                  f"{odds['spoiled']:.0%} of the prize still "
                                  "comes back", "")
                    if odds["hazard"] > 0.01:
                        p.add_row("If it goes wrong",
                                  f"{odds['hazard']:.0%} chance of springing "
                                  "something", "warn")
                else:
                    p.add_row("Safe", "nothing gained and nothing risked", "dim")
                p.add_buttons(button(text,
                                     lambda _=False, k=i: self._attempt(k)))
        elif t.feature:
            p.add(note("Dealt with."))
        else:
            p.add(note("Nothing here but ground."))
        return p

    def _move_panel(self, exp) -> Panel:
        p = Panel("Orders")
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        for text, dx, dy in (("North", 0, -1), ("South", 0, 1),
                             ("West", -1, 0), ("East", 1, 0)):
            dest = exp.tile(exp.x + dx, exp.y + dy)
            if dest is None:
                h.addWidget(button(text, lambda: None, enabled=False))
                continue
            base = 1 if dest.visited else max(
                1, TERRAIN[dest.terrain].cost - (1 if exp.rover >= 8 else 0))
            cost = weather_sim.move_cost(exp, base)
            h.addWidget(button(f"{text} ({cost}d)",
                               lambda _=False, a=dx, b=dy: self._move(a, b),
                               enabled=not weather_sim.pinned(exp)))
        h.addStretch(1)
        p.add(row)
        if weather_sim.pinned(exp):
            p.add(label(f"{weather_sim.current(exp).name}: nothing moves in "
                        "this. Sit it out.", "", "warn", wrap=True))
        p.add_buttons(
            button("Sit out the weather (1d)", self._shelter,
                   kind="primary" if weather_sim.pinned(exp) else "",
                   enabled=weather_sim.current(exp).id != "clear"),
            button("Camp and repair (1d)", self._rest),
            button("Lift off", self._lift, kind="primary",
                   enabled=exp_sim.can_lift(exp)),
            button("Abandon the site", self._abort, kind="danger"))
        if not exp.at_lander:
            p.add(note("The lander is the green square. Nothing is banked until "
                       "the party is back on it."))
        return p

    def _debrief(self, exp) -> Panel:
        p = Panel("The party is finished", "osteo")
        p.add(label(exp.log[-1][1] if exp.log else "", "", wrap=True))
        p.add_buttons(button("Recover them", self._conclude, kind="primary"))
        return p

    def _log(self, exp) -> Panel:
        p = Panel("Field log")
        for day, text, kind in reversed(exp.log[-14:]):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(8)
            d = label(f"D{day}", "label")
            d.setFixedWidth(28)
            h.addWidget(d)
            lb = label(text, "", wrap=True)
            lb.setStyleSheet(
                f"color: {theme.tint(kind) if kind in theme.TINTS else theme.INK2};"
                "font-size: 12.5px;")
            h.addWidget(lb, 1)
            p.add(row)
        return p

    # ── actions ────────────────────────────────────────────────────────────

    def _move(self, dx: int, dy: int) -> None:
        exp = self.game.expedition
        exp_sim.move(exp, dx, dy, self._party(), self.game.rng("ground"))
        self.win.refresh()

    def _attempt(self, index: int) -> None:
        exp = self.game.expedition
        res = exp_sim.attempt(exp, index, self._party(), self.game.rng("attempt"))
        found = res.get("lore")
        if found:
            self.win.dialog(found.title, [label(found.text, "", wrap=True),
                                          note("It goes in the codex if the "
                                               "party gets home.")],
                            [("Log it", None)])
        self.win.refresh()

    def _shelter(self) -> None:
        exp = self.game.expedition
        res = exp_sim.shelter(exp, self.game.rng("shelter"))
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        self.refresh()

    def _rest(self) -> None:
        exp_sim.rest(self.game.expedition, self._party(), self.game.rng("camp"))
        self.win.refresh()

    def _lift(self) -> None:
        exp_sim.lift_off(self.game.expedition)
        self.win.refresh()

    def _abort(self) -> None:
        if not self.win.confirm("Abandon the site",
                                "The lander lifts with whatever the party is "
                                "carrying. Anything left in the field stays there."):
            return
        exp_sim.finish(self.game.expedition, "aborted")
        self.win.refresh()

    def _conclude(self) -> None:
        res = conclude_expedition(self.game)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        lines = [f"{res['days']} days on {res['body']}. Outcome: {res['outcome']}."]
        if res["stowed"]:
            lines.append("Brought aboard: " + ", ".join(
                f"{round(v)} {k}" for k, v in res["stowed"].items()))
        else:
            lines.append("Nothing came back but the party.")
        if res["injured"]:
            lines.append(note(f"{res['injured']} of them will need time to recover."))
        if res["incorporated"]:
            lines.append(f"{res['incorporated'].name} is now understood.")
        for filed in res["notes"]:
            definition = filed["note"]
            lines.append(f"Field note — {definition.title}"
                         + (" (already on the shelf)" if filed["duplicate"]
                            else ""))
            lines.append(note(definition.text))
        self.win.dialog("Expedition report", lines, [("File it", None)])
        self.win.go("system")

    def _party(self):
        exp = self.game.expedition
        return [o for o in self.game.officers if o.id in exp.officers]
