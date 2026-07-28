"""The two mini-game screens: the docking loop and the decoding bench."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..core.util import credits as cr
from ..sim import minigames as mg
from ..sim import xeno as xeno_sim
from . import theme
from .widgets import (Bar, Panel, Pill, View, button, label, mono_label, note,
                      spacer)


class DockingView(View):
    """Sense, compute, act — one axis per pass, while the others drift."""

    def begin(self, port_name: str) -> None:
        g = self.game
        self.win.docking = mg.start_docking(g.rng("dock"), port_name,
                                            g.ship_stats, g.officers)

    def build(self) -> None:
        d = getattr(self.win, "docking", None)
        if d is None:
            self.head("Not docking", "Nothing to line up with.")
            self.buttons(button("Back", lambda: self.win.go("system")))
            return

        self.head(f"Approach — {d.port_name}",
                  f"{d.passes} correction pass(es) left · tolerance ±{mg.TOLERANCE}")
        self.col.addWidget(note(
            "The wet organs sense, the dry core computes, the muscles act, and "
            "the homeostat holds the rest steady. You get one axis per pass; the "
            "other two keep drifting while you work."))

        rng = self.game.rng("readout")
        for axis, name in mg.AXES:
            err = d.error[axis]
            shown = d.reading(axis, rng)
            inside = abs(err) <= mg.TOLERANCE
            p = Panel(name, "chloro" if inside else "")
            p.add_row("Reading", f"{shown:+d}" + (" (noisy)" if d.noise else ""),
                      "chloro" if inside else "warn")
            p.add_bar(min(1.0, abs(shown) / 50), "chloro" if inside else "warn")
            if not d.over:
                row = QWidget()
                h = QHBoxLayout(row)
                h.setContentsMargins(0, 0, 0, 0)
                h.setSpacing(6)
                for mult, tag in ((1, "fine"), (2, "half"), (4, "full")):
                    step = d.precision * mult
                    for sign in (1, -1):
                        h.addWidget(button(
                            f"{sign * step:+d}",
                            lambda _=False, a=axis, v=sign * step: self._fire(a, v),
                            tip=f"{tag} burst"))
                h.addStretch(1)
                p.add(row)
            self.col.addWidget(p)

        if d.over:
            self.col.addWidget(self._outcome(d))
        self.col.addWidget(self._log(d))

    def _fire(self, axis: str, amount: int) -> None:
        mg.correct(self.win.docking, axis, amount, self.game.rng("thrust"))
        self.win.refresh()

    def _outcome(self, d) -> Panel:
        res = mg.dock_result(d)
        p = Panel("Approach complete" if res["won"] else "Waved off",
                  "chloro" if res["won"] else "warn")
        if res["won"]:
            p.add(label(f"Clean approach, grade {res['grade']}. The harbourmaster "
                        "notices, and so does the fuel bill.", "", wrap=True))
        else:
            p.add(label("A tug brings you in. It is not free and it is not "
                        "dignified.", "", wrap=True))
        p.add_buttons(button("Dock", self._finish, kind="primary"))
        return p

    def _finish(self) -> None:
        d = self.win.docking
        res = mg.dock_result(d)
        g = self.game
        sysm = g.system
        if res["won"]:
            bonus = res["grade"] * 2
            g.adjust_rep(sysm.port.faction, bonus)
            g.add_log(f"Clean approach at {d.port_name}; standing +{bonus}.", "good")
        else:
            fee = 900
            g.credits = max(0.0, g.credits - fee)
            g.adjust_rep(sysm.port.faction, -1)
            g.add_log(f"Tugged in at {d.port_name}. {cr(fee)} for the service.",
                      "warn")
        self.win.docking = None
        g.flags["docked_at"] = sysm.id
        self.win.go("port")

    def _log(self, d) -> Panel:
        p = Panel("Approach log")
        for text, kind in reversed(d.log[-10:]):
            lb = label(text, "", wrap=True)
            lb.setStyleSheet(
                f"color: {theme.tint(kind) if kind in theme.TINTS else theme.INK2};"
                "font-size: 12.5px;")
            p.add(lb)
        return p


class DecodingView(View):
    """A hidden pattern, eight attempts, and feedback that withholds the where."""

    def begin(self, subject: str, tech_id: str) -> None:
        g = self.game
        self.win.decoding = mg.start_decoding(g.rng("decode"), subject,
                                              g.ship_stats, g.officers)
        self.win.decoding_tech = tech_id
        self.draft: list[int] = [0] * mg.CODE_LENGTH

    def build(self) -> None:
        d = getattr(self.win, "decoding", None)
        if d is None:
            self.head("Nothing to decode", "Record something first.")
            self.buttons(button("Back", lambda: self.win.go("tech")))
            return
        if not hasattr(self, "draft"):
            self.draft = [0] * mg.CODE_LENGTH

        self.head(f"Decoding — {d.subject}",
                  f"{d.tries} attempt(s) left · {d.palette} glyphs in the alphabet")
        self.col.addWidget(note(
            "The emission repeats with variation. Four positions, and a response "
            "that tells you how many you have exactly right and how many are "
            "right but misplaced — never which."))

        if not d.over:
            self.col.addWidget(self._composer(d))
        self.col.addWidget(self._history(d))
        if d.over:
            self.col.addWidget(self._outcome(d))

    def _composer(self, d) -> Panel:
        p = Panel("Compose a response")
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        for i in range(mg.CODE_LENGTH):
            cell = QWidget()
            v = QHBoxLayout(cell)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(2)
            v.addWidget(button("‹", lambda _=False, k=i: self._cycle(k, -1)))
            glyph = label(mg.GLYPHS[self.draft[i]], "h2")
            glyph.setFixedWidth(28)
            v.addWidget(glyph)
            v.addWidget(button("›", lambda _=False, k=i: self._cycle(k, 1)))
            h.addWidget(cell)
        h.addStretch(1)
        p.add(row)
        p.add_buttons(button("Transmit", self._guess, kind="primary"))
        return p

    def _cycle(self, index: int, step: int) -> None:
        d = self.win.decoding
        self.draft[index] = (self.draft[index] + step) % d.palette
        self.refresh()

    def _guess(self) -> None:
        d = self.win.decoding
        mg.guess(d, list(self.draft))
        self.win.refresh()

    def _history(self, d) -> Panel:
        p = Panel("Exchanges")
        if not d.guesses:
            p.add(note("Nothing sent yet."))
        for attempt, exact, near in reversed(d.guesses):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(10)
            h.addWidget(label(" ".join(mg.GLYPHS[i] for i in attempt), "h3"))
            h.addStretch(1)
            h.addWidget(Pill(f"{exact} exact", "chloro" if exact else "dim"))
            h.addWidget(Pill(f"{near} misplaced", "osteo" if near else "dim"))
            p.add(row)
        return p

    def _outcome(self, d) -> Panel:
        res = mg.decode_result(d)
        p = Panel("Resolved" if res["won"] else "The pattern defeats you",
                  "chloro" if res["won"] else "warn")
        if res["won"]:
            p.add(label(f"The sequence resolves. {res['points']} points of "
                        "understanding.", "", wrap=True))
        else:
            p.add(label("The recording is exhausted and the structure is still "
                        "opaque. Another sample, another day.", "", wrap=True))
        p.add_buttons(button("Close the bench", self._finish, kind="primary"))
        return p

    def _finish(self) -> None:
        d = self.win.decoding
        res = mg.decode_result(d)
        tech_id = getattr(self.win, "decoding_tech", None)
        if res["won"] and tech_id:
            _p, done = xeno_sim.add_study(self.game, tech_id, res["points"])
            self.game.add_log(f"Decoded a {d.subject} emission: "
                              f"{res['points']} points.", "good")
            if done:
                self.win.dialog("Incorporated",
                                [f"{xeno_sim.XENOTECH_BY_ID[tech_id].name} is "
                                 "now yours."], [("Log it", None)])
        self.win.decoding = None
        self.win.decoding_tech = None
        self.win.go("tech")
