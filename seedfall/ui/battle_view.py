"""Combat. Two layer stacks, a five-band range track, and the standing option of
not shooting at all."""

from __future__ import annotations

from PyQt6.QtCore import Qt

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget

from ..core.util import credits as cr
from ..core.util import num, pct
from ..data.chassis import CHASSIS_BY_ID
from ..data.part_types import BANDS
from ..sim import aftermath as aftermath_sim
from ..sim import prize as prize_sim
from ..sim import rivals as rivals_sim
from ..sim import stations as st_mod
from ..sim import tactical as tac
from ..sim import combat as combat_sim
from ..sim import consorts as consort_sim
from ..sim import firing
from . import assessment_panel
from ..data.consorts import ORDERS as CONSORT_ORDERS
from ..data.consorts import ORDERS_BY_ID as CONSORT_ORDERS_BY_ID
from ..sim.ship import hull_pct, is_destroyed
from . import theme
from . import soundmap
from . import hunt_marks
from .layer_row import layer_row
from .view_base import Pane, WrapRow
from .widgets import (Panel, TabBar, View, button, defer, label,
                      mono_label, note, spacer)


from .battle_text import aftermath_lines


class BattleView(View):
    def __init__(self, win):
        super().__init__(win)
        # The panes scroll themselves; a deep bottom margin on the screen
        # would only push the whole of it past the viewport.
        self.col.setContentsMargins(22, 14, 22, 10)

    def begin(self, encounter: dict) -> None:
        g = self.game
        self.win.battle = combat_sim.start(
            g.ship, g.ship_stats, encounter["enemy"],
            bonuses=g.bonuses, officers=g.officers,
            rep=g.rep.get(encounter["enemy"].get("faction"), 0),
            no_parley=encounter.get("no_parley", False), game=g,
            # Without an rng the opening is always bow-on at band 3, which left
            # the varied initial aspect the tactical model was built for unused.
            rng=g.rng("engagement"), fleet=consort_sim.escorts_of(g),
            band=encounter.get("band") or 3)
        self.win.battle.intro = encounter.get("intro", "")
        rivals_sim.opening(g, self.win.battle, encounter)     # first volley
        # Carried so the outcome can strike the roaming mass off the board.
        self.win.battle.instar = encounter.get("instar")

    #: The orders and the readout are panes of their own (`view_base.Pane`),
    #: so the screen fills the window rather than running down the page.
    fills = True

    def build(self) -> None:
        b = self.win.battle
        soundmap.battle(self.win, b)       # once a turn, however often drawn
        # And what the turn did to *you*, as a thing the picture does rather
        # than a number in a panel. Same rule as the sound: once a turn.
        from . import effect_clock, effects
        effects.gunfire(self.win)
        effect_clock.pump(self.win)
        if b is None:
            self.head("No engagement", "Nothing is shooting at you.")
            self.buttons(button("Back", lambda: self.win.go("system")))
            self.col.addStretch(1)
            return

        self.col.addWidget(label(f"Engagement — {b.enemy_name} · turn {b.turn}",
                                 "h2"))
        hunt_marks.battle_header(self.col, self.game, b)     # a named rival
        if b.intro and b.turn == 1:
            self.col.addWidget(label(b.intro, "", wrap=True))
        report = self._last_turn(b)
        if report is not None:
            self.col.addWidget(report)

        # **The orders are pinned; the readout scrolls beside them.** See
        # `ui/battle_orders.py` for what this replaced: every action button
        # sat below the fold at every window size up to 1560×1000.
        from . import battle_orders
        body = QWidget()
        across = QHBoxLayout(body)
        across.setContentsMargins(0, 0, 0, 0)
        across.setSpacing(14)
        orders = Pane(margins=(0, 0, 10, 12))
        orders.setObjectName("battle_orders")
        if b.over:
            orders.col.addWidget(self._outcome(b))
        else:
            orders.col.addWidget(battle_orders.acts(self, b))
            orders.col.addWidget(battle_orders.consequences(self, b))
        orders.col.addStretch(1)
        readout = Pane(margins=(0, 0, 10, 12))
        readout.setObjectName("battle_readout")
        for part in self._readout_parts(b):
            readout.col.addWidget(part)
        readout.col.addStretch(1)
        # Four to five: the readout's plot is a fixed 380 px square, and at
        # the 1040 px minimum an even split left it 4 px short of room.
        across.addWidget(orders, 4)
        across.addWidget(readout, 5)
        self.col.addWidget(body, 1)
        self._keep_places(orders, readout)

    def _readout_parts(self, b) -> list:
        """Everything that says how the fight stands, in reading order."""
        parts = [self._plot_row(b), assessment_panel.build(b),
                 self._band_track(b)]
        if b.consorts:
            parts.append(self._company(b))
        aloft = self._craft(b)
        if aloft is not None:
            parts.append(aloft)
        if b.enemy_flight:
            # What they launched at you, which is a threat your mounts have
            # to be spared for (`sim/craft_battle`).
            theirs = Panel("Their flight")
            theirs.add_row(f"{b.enemy_name}'s launches",
                           f"{len(b.enemy_flight)} still up", "warn")
            theirs.add(note("They run in every turn, wherever the range "
                            "track stands. Close-in fire is what answers "
                            "them: a mount that bears takes one apart."))
            parts.append(theirs)
        hulls = WrapRow()
        hulls.add(self._ship_panel(b, b.player, self.game.ship.name))
        hulls.add(self._ship_panel(b, b.enemy, b.enemy_name))
        parts.append(hulls)
        if not b.over:
            # What the seats you are not in will do, before the turn resolves.
            from .doctrine_panel import intentions
            parts.append(intentions(self, b))
        parts.append(self._log(b))
        return parts

    def _plot_row(self, b) -> QWidget:
        row = WrapRow(14)
        row.add(self._plot(b), 0)
        row.add(self._firing(b), 1)
        return row

    def _last_turn(self, b):
        """What happened last turn, under the heading, where it is read first.

        It was at the very bottom of the screen, below the orders — the one
        thing a captain wants after pressing a button was the furthest thing
        from it.
        """
        from .log_panel import marked
        if not b.log:
            return None
        last = b.log[-1][0]
        lines = [(text, kind) for turn, text, kind in b.log if turn == last]
        p = Panel()
        p.box.setContentsMargins(13, 8, 13, 8)
        p.box.setSpacing(3)
        p.add(mono_label(f"Last turn — turn {last}"))
        for text, kind in lines[-3:]:
            tinted = kind in theme.TINTS
            p.add(label(marked(text, kind), "", kind if tinted else "",
                        wrap=True))
        if len(lines) > 3:
            p.add(note(f"{len(lines) - 3} more in the action report."))
        return p

    def _keep_places(self, orders, readout) -> None:
        """A turn rebuilds both panes; put each back where it was scrolled to,
        so reading the enemy's hull does not end at the top every turn."""
        was = getattr(self, "_places", None)
        self._places = (orders, readout)
        if not was:
            return
        try:
            marks = [p.verticalScrollBar().value() for p in was]
        except RuntimeError:
            return

        def put_back():
            for pane, mark in zip((orders, readout), marks):
                try:
                    pane.verticalScrollBar().setValue(mark)
                except RuntimeError:
                    return
        defer(put_back)

    # ── display ────────────────────────────────────────────────────────────

    def _firing(self, b):
        from .firing_panel import gunnery_picture
        return gunnery_picture(self, b)

    def _plot(self, b) -> QWidget:
        """The geometry to decide with, and the picture of what happened.

        Two views of one engagement, stacked. The plot from above is what a
        captain chooses `come about` or `present the broadside` on; the view
        from the bridge is what the broadside looked like. Neither replaces
        the other, and the second one did not exist at all — a salvo of seven
        was a paragraph in a log.
        """
        from .battle3d import Battle3D
        from .tactical_plot import TacticalPlot

        holder = QWidget()
        column = QVBoxLayout(holder)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(8)
        column.addWidget(Battle3D(b), 5)
        column.addWidget(TacticalPlot(b), 4)
        return holder

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
            p.add(layer_row(L, 150))
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
            ranged = w.wpn.bears_at(b.band) <= firing.WORTH_FIRING
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

    def _craft(self, b):
        """The craft on a run, while there is one: what is left of her.

        A fighter is the one thing in the fight the captain cannot see on
        either hull panel, and she is the thing most likely to be gone by
        next turn."""
        from ..sim import craft as craft_sim
        from ..sim import craft_battle
        craft = craft_battle.flying(self.game)
        if craft is None:
            return None
        kind = craft_sim.kind_of(craft)
        p = Panel("On a run")
        p.add(label(craft.name, "h3", "lumen"))
        p.add_row("Pilot", craft_sim.name_of(self.game, craft.pilot))
        share = craft.hp / max(1, kind.hull)
        p.add_row("Hull", f"{craft.hp} / {kind.hull}",
                  "chloro" if share > 0.5 else "warn")
        p.add_row("Runs made", f"{craft.struck}, {craft.fuel:.1f} t left")
        p.add(note("She makes a run a turn on her own account. Call her in "
                   "before they get on her — a cradle is cheaper than a "
                   "pilot."))
        return p

    def _set_consort_order(self, consort, order_id: str) -> None:
        consort.order = order_id
        self.refresh()

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

    def _open_gunnery(self) -> None:
        from .gunner_window import open_gunnery
        open_gunnery(self.win)

    def _open_tactical(self) -> None:
        from .tactical_window import open_tactical
        open_tactical(self.win)

    def _act(self, action: dict) -> None:
        # Through the window, which is the one door: the gunner's station is a
        # second seat on the same engagement and both have to resolve a turn the
        # same way.
        self.win.battle_act(action)

    def _finish(self) -> None:
        """Read out what the engagement left behind. The rules are in `sim`."""
        b = self.win.battle
        g = self.game
        out = aftermath_sim.resolve(g, b, g.rng("seize"))

        if b.result == "lost":
            # `aftermath.resolve` has already killed the captain (or opened
            # the vault); the screen only reads out what happened.
            self.win.battle = None
            if not self.win.check_ending():
                self.win.go("system")
            return

        titles = {"destroyed": "They are gone", "driven-off": "They broke off",
                  "escaped": "Clear", "parley": "Stood down",
                  "routed": "You have nothing left",
                  "stalemate": "Neither of you could finish it"}
        body = [b.log[-1][1]] + [note(l) for l in aftermath_lines(out)]
        if b.result == "struck":
            if self._prize_choice(b, g, body):
                self.win.battle = None       # boarded: her deck decides
                self.win.game.save()
                self.win.go("afoot")
                return
        else:
            self.win.dialog(titles.get(b.result, "Engagement over"), body,
                            [("Back to the bridge", None)])
        self.win.end_combat()

    def _prize_choice(self, b, g, body) -> bool:
        """One decision per struck hull, through `sim/prize`'s doors.

        Dismissing the dialog lets them go — the release button and Escape
        are the same mercy, so a captain cannot dodge the choice and keep it.
        """
        told = prize_sim.offer(g, b)
        if told.get("cargo"):
            body.append(note("In her holds: " + ", ".join(
                f"{round(t)} t {cid}" for cid, t in told["cargo"].items())
                + " — worth about "
                + cr(aftermath_sim.worth_of(told["cargo"])) + "."))
        if not told.get("can_take") and told.get("why"):
            body.append(note(told["why"]))
        buttons = []
        if told.get("can_take"):
            buttons.append((f"Put a prize crew aboard — {told['need']} hands",
                            "take"))
        buttons += [("Strip her holds", "strip"),
                    ("Board her first", "board"),
                    ("Let them limp home", "release")]
        chose = self.win.dialog("They have struck their colours", body, buttons)
        if chose == "board" and self._board(b, g):
            return True
        act = {"take": prize_sim.take,
               "strip": prize_sim.strip}.get(chose, prize_sim.release)
        act(g, b)
        return False

    def _board(self, b, g) -> bool:
        """Put a party aboard her before deciding (`sim/afoot`): the captain
        and the three best with a gun. Her decision is then taken on her own
        deck, through the same three doors."""
        from ..sim import afoot
        got = afoot.begin_prize(g, b.enemy.ship, b.enemy_faction,
                                afoot.boarders(g))
        if not got.get("ok"):
            self.win.toast(got.get("why", "Nobody can go across."), "warn")
            return False
        b.prized = "boarded"
        return True

