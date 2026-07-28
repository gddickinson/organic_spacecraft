"""Combat. Two layer stacks, a five-band range track, and the standing option of
not shooting at all."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..core.util import credits as cr
from ..core.util import num, pct
from ..data.chassis import CHASSIS_BY_ID
from ..data.factions import FACTIONS_BY_ID
from ..data.part_types import BANDS
from ..sim import combat as combat_sim
from ..sim import research as research_sim
from ..sim.actions import seize_notes
from ..sim.ship import add_cargo, cargo_free, hull_pct
from . import theme
from .widgets import (Bar, Panel, Pill, View, button, label, mono_label, note,
                      spacer)


class BattleView(View):
    def begin(self, encounter: dict) -> None:
        g = self.game
        self.win.battle = combat_sim.start(
            g.ship, g.ship_stats, encounter["enemy"],
            bonuses=g.bonuses, officers=g.officers,
            rep=g.rep.get(encounter["enemy"].get("faction"), 0),
            no_parley=encounter.get("no_parley", False))
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

        self.col.addWidget(self._band_track(b))
        self.row(self._ship_panel(b, b.player, self.game.ship.name),
                 self._ship_panel(b, b.enemy, b.enemy_name))
        self.col.addWidget(self._orders(b) if not b.over else self._outcome(b))
        self.col.addWidget(self._log(b))

    # ── display ────────────────────────────────────────────────────────────

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

    def _orders(self, b) -> Panel:
        st = b.player.st
        p = Panel("Orders")

        p.add(mono_label("Fire"))
        fire_row = QWidget()
        fh = QHBoxLayout(fire_row)
        fh.setContentsMargins(0, 0, 0, 0)
        fh.setSpacing(6)
        if not st.weapons:
            fh.addWidget(note("No armament fitted. Charter doctrine, or an oversight "
                              "— either way you must outlast them, talk them down, "
                              "or run."))
        if len(st.weapons) > 1:
            fh.addWidget(button("Full salvo", lambda: self._act({"type": "salvo"}),
                                kind="primary",
                                tip="Fire every mount that will bear. More damage, "
                                    "far more heat and ammunition."))
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

        p.add(spacer(3), mono_label("Manoeuvre"))
        p.add_buttons(
            button("Close", lambda: self._act({"type": "move", "dir": -1}),
                   enabled=b.band > 0),
            button("Open range", lambda: self._act({"type": "move", "dir": 1}),
                   enabled=b.band < 4),
            button("Brace and vent", lambda: self._act({"type": "brace"})),
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

        if b.result == "lost":
            self.win.battle = None
            g.die("Destroyed in action.")
            if not self.win.check_ending():
                self.win.go("system")
            return

        lines: list[str] = []
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
