"""Combat. Two layer stacks, a five-band range track, and the standing option of
not shooting at all."""

from __future__ import annotations

from PyQt6.QtCore import Qt
import math

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ..core.util import credits as cr
from ..core.util import num, pct
from ..data.chassis import CHASSIS_BY_ID
from ..data.factions import FACTIONS_BY_ID
from ..data.part_types import BANDS
from ..sim import stations as st_mod
from ..sim import tactical as tac
from ..sim import combat as combat_sim
from ..sim import consorts as consort_sim
from ..data.consorts import ORDERS as CONSORT_ORDERS
from ..data.consorts import ORDERS_BY_ID as CONSORT_ORDERS_BY_ID
from ..sim import research as research_sim
from ..sim.fieldwork import seize_notes
from ..sim import contracts as contract_sim
from ..sim.ship import add_cargo, cargo_free, hull_pct, is_destroyed
from . import theme
from .widgets import (Bar, Panel, Pill, TabBar, View, button, label,
                      mono_label, note, spacer)


class BattleView(View):
    def begin(self, encounter: dict) -> None:
        g = self.game
        self.win.battle = combat_sim.start(
            g.ship, g.ship_stats, encounter["enemy"],
            bonuses=g.bonuses, officers=g.officers,
            rep=g.rep.get(encounter["enemy"].get("faction"), 0),
            no_parley=encounter.get("no_parley", False), game=g,
            # Without an rng the opening is always bow-on at band 3, which left
            # the varied initial aspect the tactical model was built for unused.
            rng=g.rng("engagement"), fleet=consort_sim.escorts_of(g))
        self.win.battle.intro = encounter.get("intro", "")

    def build(self) -> None:
        b = self.win.battle
        if b is None:
            self.head("No engagement", "Nothing is shooting at you.")
            self.buttons(button("Back", lambda: self.win.go("system")))
            return

        self.head("Engagement", f"{b.enemy_name} · turn {b.turn}")
        if b.intro and b.turn == 1:
            self.col.addWidget(label(b.intro, "", wrap=True))

        holder = QWidget()
        hh = QHBoxLayout(holder)
        hh.setContentsMargins(0, 0, 0, 0)
        hh.setSpacing(14)
        hh.addWidget(self._plot(b), 0)
        hh.addWidget(self._readout(b), 1)
        self.col.addWidget(holder)
        self.col.addWidget(self._band_track(b))
        if b.consorts:
            self.col.addWidget(self._company(b))
        self.row(self._ship_panel(b, b.player, self.game.ship.name),
                 self._ship_panel(b, b.enemy, b.enemy_name))
        self.col.addWidget(self._orders(b) if not b.over else self._outcome(b))
        self.col.addWidget(self._log(b))

    # ── display ────────────────────────────────────────────────────────────

    def _plot(self, b) -> QWidget:
        return TacticalPlot(b)

    def _band_track(self, b) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(4)
        for i, name in enumerate(BANDS):
            lb = label(name, "label")
            here = i == b.band
            lb.setStyleSheet(
                f"font-family: '{theme.mono_family()}'; font-size: 9px;"
                f"letter-spacing: 1.4px; padding: 6px 4px;"
                f"color: {theme.tint('lumen') if here else theme.INK3};"
                f"border: 1px solid {theme.tint('lumen') if here else theme.LINE};"
                f"border-radius: 3px;"
                + ("background: rgba(79,214,208,0.09);" if here else ""))
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.addWidget(lb, 1)
        return w

    def _ship_panel(self, b, side, name: str) -> Panel:
        ch = CHASSIS_BY_ID[side.ship.chassis]
        p = Panel(name)
        p.add(note(f"{ch.name} · {ch.family} hull · {side.ship.crew} crew"))
        for L in side.ship.layers:
            frac = L.hp / L.max if L.max else 0
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            lb = label(L.name, "", "warn" if L.hp <= 0 else
                       ("osteo" if L.critical else ""))
            lb.setMinimumWidth(168)
            h.addWidget(lb)
            h.addWidget(Bar(frac, "warn" if frac < 0.3 else
                            ("osteo" if L.critical else "chloro")), 1)
            v = label(pct(frac), "dim")
            v.setFixedWidth(40)
            h.addWidget(v)
            p.add(row)
        p.add(spacer(3))
        p.add_row("Integrity", pct(hull_pct(side.ship)))
        p.add_row("Resolve", num(max(0, side.resolve)))
        p.add_bar(max(0, side.resolve) / 100, "warn" if side.resolve < 35 else "lumen")
        p.add_row("Heat", f"{round(side.ship.heat)} / {num(side.st.heat_cap)}",
                  "warn" if side.ship.heat > side.st.heat_cap else "")
        flags = [n for n, on in (("dazzled", side.blind), ("jammed", side.jammed),
                                 ("grappled", side.grappled)) if on]
        if flags:
            p.add(label(", ".join(flags), "", "warn"))
        return p

    def _readout(self, b) -> Panel:
        p = Panel("Plot")
        p.add_row("Range", f"{round(b.range_units)} · {BANDS[b.band].lower()}")
        p.add_row("Your speed", f"{round(b.player.body.speed)}")
        p.add_row("Their speed", f"{round(b.enemy.body.speed)}")
        rel = tac.relative_bearing(b.player.body, b.enemy.body)
        p.add_row("Target bearing", f"{round(rel)}° off the bow")
        p.add(spacer(4), mono_label("Mounts"))
        if not b.player.st.weapons:
            p.add(note("No armament fitted."))
        for w in b.player.st.weapons:
            arc = tac.arc_of(w)
            bears, gap = st_mod.bears_on(b.player, b.enemy, w)
            ranged = w.wpn.bears_at(b.band) <= 0.5
            if bears and ranged:
                statusd, tint = "bears", "chloro"
            elif not bears:
                statusd, tint = f"{round(gap)}° off arc", "warn"
            else:
                statusd, tint = "out of range", "osteo"
            p.add_row(f"{w.name} · {tac.arc_name(arc)}", statusd, tint)
        return p

    def _company(self, b) -> Panel:
        """The hulls sailing with you, and what you have told them to do."""
        p = Panel("In company")
        p.add(note("A consort follows its standing order until you change it. "
                   "You are not flying it — you are telling its captain what "
                   "you want to happen."))
        for consort in b.consorts:
            hull = consort_sim.hull_fraction(consort.ship)
            if is_destroyed(consort.ship):
                state, tint = "lost", "bad"
            elif consort.withdrawn:
                state, tint = "fallen out of the line", "warn"
            else:
                state, tint = f"{pct(hull)} integrity", (
                    "chloro" if hull > 0.5 else "warn")
            p.add(spacer(3))
            p.add(label(consort.name, "h3", "lumen"))
            p.add_row(CHASSIS_BY_ID[consort.ship.chassis].name, state, tint)
            if consort.out:
                continue
            p.add_row("Dealt", f"{round(consort.dealt)} · taken "
                               f"{round(consort.taken)}")
            row = TabBar([(o.id, o.name) for o in CONSORT_ORDERS], consort.order)
            row.changed.connect(
                lambda oid, c=consort: self._set_consort_order(c, oid))
            p.add(row)
            p.add(note(CONSORT_ORDERS_BY_ID[consort.order].blurb))
        return p

    def _set_consort_order(self, consort, order_id: str) -> None:
        consort.order = order_id
        self.refresh()

    def _orders(self, b) -> Panel:
        st = b.player.st
        p = Panel("Orders")

        p.add(mono_label("Fire a single mount"))
        fire_row = QWidget()
        fh = QHBoxLayout(fire_row)
        fh.setContentsMargins(0, 0, 0, 0)
        fh.setSpacing(6)
        if not st.weapons:
            fh.addWidget(note("No armament fitted. Charter doctrine, or an oversight "
                              "— either way you must outlast them, talk them down, "
                              "or run."))
        for w in st.weapons:
            pen = w.wpn.bears_at(b.band)
            fh.addWidget(button(w.name + (" (long shot)" if pen > 0 else ""),
                                lambda _=False, wid=w.id: self._act(
                                    {"type": "fire", "weapon_id": wid}),
                                tip=w.blurb, enabled=pen <= 0.6))
        fh.addStretch(1)
        p.add(fire_row)

        if st.abilities:
            p.add(spacer(3), mono_label("Systems"))
            ab_row = QWidget()
            ah = QHBoxLayout(ab_row)
            ah.setContentsMargins(0, 0, 0, 0)
            ah.setSpacing(6)
            for part_ in st.abilities:
                ab = part_.ability
                cd = b.player.cd.get(ab.id, 0)
                ah.addWidget(button(f"{ab.name}" + (f" ({cd})" if cd else ""),
                                    lambda _=False, aid=ab.id: self._act(
                                        {"type": "ability", "id": aid}),
                                    tip=part_.blurb, enabled=cd == 0))
            ah.addStretch(1)
            p.add(ab_row)

        p.add(spacer(4), mono_label("Stations — you may take one this turn"))
        p.add(note("The officers hold the other two at their own level, which is "
                   "competent and not as good as you."))
        for sid, name, stat, blurb in st_mod.STATIONS:
            level = st_mod.officer_level(b.officers, stat)
            p.add(spacer(3))
            p.add(label(f"{name}  ·  officer level {level}", "h3",
                        "chloro" if sid == b.player.station else ""))
            p.add(note(blurb))
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            for order in st_mod.orders_for(sid):
                h.addWidget(button(order.name, tip=order.blurb,
                                   on_click=lambda _=False, o=order.id:
                                       self._act({"type": "station", "order": o})))
            h.addStretch(1)
            p.add(row)

        p.add(spacer(4), mono_label("Other"))
        p.add_buttons(
            button("Hail them", lambda: self._act({"type": "hail"})),
            button("Disengage", lambda: self._act({"type": "flee"}), kind="flat")
            if b.fleeable else None)
        return p

    def _outcome(self, b) -> Panel:
        p = Panel("Engagement over")
        if b.log:
            p.add(label(b.log[-1][1], "", wrap=True))
        p.add_buttons(button("Return to the bridge", self._finish, kind="primary"))
        return p

    def _log(self, b) -> Panel:
        p = Panel("Action report")
        for turn, text, kind in reversed(b.log[-24:]):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(8)
            t = label(f"T{turn}", "label")
            t.setFixedWidth(28)
            h.addWidget(t)
            lb = label(text, "", wrap=True)
            lb.setStyleSheet(
                f"color: {theme.tint(kind) if kind in theme.TINTS else theme.INK2};"
                "font-size: 12.5px;")
            h.addWidget(lb, 1)
            p.add(row)
        return p

    # ── driving ────────────────────────────────────────────────────────────

    def _act(self, action: dict) -> None:
        b = self.win.battle
        combat_sim.take_turn(b, action, self.game.rng("combat"))
        self.game.recompute()
        b.player.st = self.game.ship_stats
        self.win.refresh()

    def _finish(self) -> None:
        b = self.win.battle
        g = self.game
        fid = b.enemy_faction

        # Consorts lost in the action are lost for good, whatever the outcome.
        dead = consort_sim.losses(b)
        if dead:
            gone = {c.uid for c in dead}
            g.fleet = [s for s in g.fleet if s.uid not in gone]
            for c in dead:
                g.add_log(f"{c.name} was lost with all hands.", "bad")

        if b.result == "lost":
            self.win.battle = None
            g.die("Destroyed in action.")
            if not self.win.check_ending():
                self.win.go("system")
            return

        lines: list[str] = []
        if dead:
            lines.append("Lost in the action: "
                         + ", ".join(c.name for c in dead) + ".")
        if b.result == "destroyed":
            loot = b.loot or {}
            g.credits += loot.get("credits", 0)
            research_sim.grant(g.research, loot.get("research", 0))
            lines.append(f"Salvage: {cr(loot.get('credits', 0))} and "
                         f"{loot.get('research', 0)} points of research.")
            room = cargo_free(g.ship, g.ship_stats)
            for cid, n in list(b.enemy.ship.cargo.items()):
                take = min(n, room)
                if take > 0.5:
                    add_cargo(g.ship, cid, take)
                    room -= take
                    lines.append(f"{round(take)} t of {cid} pulled out of the wreck.")
            for c in contract_sim.note_kill(g, fid):
                lines.append(f"Bounty progress: {c.title} "
                             f"({int(c.progress)}/{int(c.amount)})"
                             + (" — paid." if c.done else "."))
            seized = seize_notes(g, fid, g.rng("seize")) if fid else None
            if seized:
                lines.append(f"Their xenology files came out intact: "
                             f"{round(seized['points'])} points toward "
                             f"{seized['tech'].name}.")
                if seized["incorporated"]:
                    lines.append(f"{seized['tech'].name} is now yours.")
            if fid and fid != "bloom":
                g.adjust_rep(fid, -14)
                lines.append(f"{FACTIONS_BY_ID[fid].short} standing has fallen.")
            elif fid == "bloom":
                g.adjust_rep("charter", 4)
                lines.append("The Charter notes the kill approvingly.")
        elif b.result == "parley":
            if fid:
                g.adjust_rep(fid, 8)
                lines.append(f"{FACTIONS_BY_ID[fid].short} standing has improved.")
            g.credits += 400
            lines.append("They pay a courtesy for the trouble.")
        elif b.result == "driven-off":
            research_sim.grant(g.research, 10)
            lines.append("They broke first. Your hull held and theirs did not want "
                         "to find out how long.")
            if fid and fid != "bloom":
                g.adjust_rep(fid, -4)

        g.add_log(f"Engagement with {b.enemy_name}: {b.result}.",
                  "good" if b.result in ("destroyed", "parley", "driven-off") else "warn")
        titles = {"destroyed": "They are gone", "driven-off": "They broke off",
                  "escaped": "Clear", "parley": "Stood down",
                  "routed": "You have nothing left",
                  "stalemate": "Neither of you could finish it"}
        body = [b.log[-1][1]] + [note(l) for l in lines]
        self.win.dialog(titles.get(b.result, "Engagement over"), body,
                        [("Back to the bridge", None)])
        self.win.end_combat()


class TacticalPlot(QWidget):
    """The engagement from above: two hulls, their headings, and the arcs.

    Range bands are drawn as rings around your ship so the abstract numbers the
    weapons are specified in have somewhere to live on the picture.
    """

    SIZE = 380

    def __init__(self, battle):
        super().__init__()
        self.b = battle
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _scale(self):
        span = max(tac.BAND_UNITS * 5.2, self.b.range_units * 2.3)
        for consort in self.b.consorts:
            if not consort.out:
                span = max(span, tac.separation(self.b.player.body,
                                                consort.body) * 2.4)
        return (self.SIZE / 2 - 14) / (span / 2)

    def _pt(self, body, origin, s) -> QPointF:
        return QPointF(self.SIZE / 2 + (body.x - origin.x) * s,
                       self.SIZE / 2 + (body.y - origin.y) * s)

    def paintEvent(self, _ev):  # noqa: N802
        b = self.b
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#060f0d"))
        s = self._scale()
        mid = b.player.body

        # range rings, one per band
        for band in range(1, 5):
            r = tac.BAND_UNITS * band * s
            p.setPen(QPen(QColor(150, 196, 176, 34), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(self.SIZE / 2, self.SIZE / 2), r, r)

        for consort in b.consorts:
            if consort.out:
                continue
            self._draw_ship(p, consort, mid, s, theme.tint("lumen"), True)
        self._draw_ship(p, b.player, mid, s, theme.tint("chloro"), True)
        self._draw_ship(p, b.enemy, mid, s, theme.tint("warn"), False)

        # the line of sight, labelled with the range
        a = self._pt(b.player.body, mid, s)
        c = self._pt(b.enemy.body, mid, s)
        p.setPen(QPen(QColor(150, 196, 176, 60), 1, Qt.PenStyle.DashLine))
        p.drawLine(a, c)
        p.setFont(QFont(theme.mono_family(), 8))
        p.setPen(QColor(theme.INK3))
        p.drawText(QRectF((a.x() + c.x()) / 2 - 40, (a.y() + c.y()) / 2 - 14, 80, 14),
                   Qt.AlignmentFlag.AlignHCenter, f"{round(b.range_units)}")
        p.end()

    def _draw_ship(self, p, side, origin, s, colour, mine: bool) -> None:
        pos = self._pt(side.body, origin, s)
        rad = math.radians(side.body.heading)
        nose = QPointF(pos.x() + math.sin(rad) * 13, pos.y() - math.cos(rad) * 13)
        left = QPointF(pos.x() + math.sin(rad + 2.5) * 9,
                       pos.y() - math.cos(rad + 2.5) * 9)
        right = QPointF(pos.x() + math.sin(rad - 2.5) * 9,
                        pos.y() - math.cos(rad - 2.5) * 9)
        p.setPen(QPen(QColor(colour), 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(QPolygonF([nose, left, right]))

        if mine:
            # sketch the forward arc so turning to bear is legible
            p.setPen(QPen(QColor(colour).darker(160), 1, Qt.PenStyle.DotLine))
            for sign in (1, -1):
                edge = math.radians(side.body.heading + sign * 60)
                p.drawLine(pos, QPointF(pos.x() + math.sin(edge) * 46,
                                        pos.y() - math.cos(edge) * 46))
