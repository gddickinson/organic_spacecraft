"""The main window: status bar, navigation rail, the stack of screens, and the
ship's log. Also the host for dialogs and the combat hand-off."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
                             QVBoxLayout, QWidget)

from ..core import state as state_mod
from ..core.util import credits, num, pct, stardate
from ..data.chassis import CHASSIS_BY_ID
from ..data.screens import KEY_FOR, NAV as SCREENS_NAV
from ..data.lore import ENDINGS, TITLE, VICTORIES
from ..sim.ship import cargo_used, hull_pct, is_breached
from . import theme
from .widgets import (ALIGN_R, Bar, Pill, button, label, mono_label, spacer,
                      hrule)

#: The rail, and the key for each screen, from `data/screens.py` — which
#: `sim/manual.py` also reads, so the Keys page cannot drift from the rail.
NAV = list(SCREENS_NAV)


class MainWindow(QMainWindow):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.battle = None
        self._return_to = "system"
        self.setWindowTitle(f"{TITLE} — a GESTALT Programme Chronicle")
        self.resize(1360, 880)
        self.setMinimumSize(1040, 680)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.monitors: dict = {}
        from .menubar import build as build_menubar
        build_menubar(self)
        self.hud = self._build_hud()
        outer.addWidget(self.hud)
        outer.addWidget(hrule())
        from .tutorial_bar import TutorialBar
        self.tutorial_bar = TutorialBar(self)
        outer.addWidget(self.tutorial_bar)

        middle = QWidget()
        row = QHBoxLayout(middle)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self._build_nav())
        row.addWidget(self._vline())
        self.stack_host = QWidget()
        self.stack_layout = QVBoxLayout(self.stack_host)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.stack_host, 1)
        row.addWidget(self._vline())
        row.addWidget(self._build_log())
        outer.addWidget(middle, 1)

        self.views: dict[str, object] = {}
        self.current = None
        self._make_views()
        self.statusBar().setStyleSheet(
            f"color: {theme.INK3}; font-family: '{theme.mono_family()}'; font-size: 10px;")
        self.go("map")

    # ── chrome ─────────────────────────────────────────────────────────────

    def _vline(self) -> QFrame:
        f = QFrame()
        f.setFixedWidth(1)
        f.setStyleSheet(f"background: {theme.LINE};")
        return f

    def _build_hud(self) -> QWidget:
        from .hud import build
        return build(self)

    def save(self) -> None:
        """Write the chronicle now.

        Three call sites used `win.save()` before this existed — carrying on
        past an ending, answering an aftermath situation, and changing a
        setting — and every one of them raised `AttributeError` inside a Qt
        slot, where it is swallowed. The checks drove `sim/legacy.py` directly
        and never pressed the button.
        """
        self._saved_day = self.game.day
        self.game.save()

    def open_options(self) -> None:
        """The options page, in its own window, from the menu bar."""
        from .options_view import OptionsDialog
        OptionsDialog(self).exec()
        self.apply_options()
        self.refresh()

    def open_help(self, tab: str = "manual") -> None:
        view = self.views["help"]
        view.tab = tab
        self.go("help")

    def begin_again(self) -> None:
        if not self.confirm("Begin again",
                            "This chronicle is abandoned and another opens in "
                            "its place. There is one save and this overwrites "
                            "it."):
            return
        state_mod.clear_save()
        from .title import start_new_chronicle
        start_new_chronicle(self)

    def help_here(self) -> None:
        """Open the manual at whatever this screen is about.

        Contextual rather than a table of contents: `manual.for_screen` knows
        which topics belong to which view, so the Help key from the Helm opens
        the page about burns rather than the front of the book.
        """
        from ..sim import manual as manual_sim
        about = manual_sim.for_screen(self.current or "")
        view = self.views["help"]
        view.tab = "manual"
        view.query = ""
        if about:
            view.topic = about[0].id
        self.go("help")

    def instruments(self) -> None:
        from .monitors import chooser
        chooser(self).exec()

    def _build_nav(self) -> QWidget:
        rail = QWidget()
        rail.setFixedWidth(158)
        v = QVBoxLayout(rail)
        v.setContentsMargins(0, 10, 0, 10)
        v.setSpacing(0)
        self.nav_buttons: dict[str, object] = {}
        for i, (vid, text) in enumerate(NAV):
            b = button(f"{text}", kind="nav")
            b.setCheckable(True)
            # From the table, not from the position. Deriving it as "1-9 then
            # 0 for the rest" meant the tenth and eleventh screens both bound
            # 0, and the Aftermath had no key of its own at all.
            key = KEY_FOR.get(vid, "")
            if key:
                b.setShortcut(key)
            b.setToolTip(f"Shortcut: {key}" if key else "")
            b.clicked.connect(lambda _=False, v_=vid: self.go(v_))
            self.nav_buttons[vid] = b
            v.addWidget(b)
        v.addStretch(1)
        v.addWidget(label("  every screen has a key — see Help", "note"))
        return rail

    def _build_log(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(300)
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        cap = mono_label("  Ship's Log")
        cap.setContentsMargins(12, 12, 12, 8)
        v.addWidget(cap)
        v.addWidget(hrule())

        from PyQt6.QtWidgets import QScrollArea
        self.log_area = QScrollArea()
        self.log_area.setWidgetResizable(True)
        self.log_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log_inner = QWidget()
        self.log_col = QVBoxLayout(self.log_inner)
        self.log_col.setContentsMargins(12, 8, 12, 20)
        self.log_col.setSpacing(6)
        self.log_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.log_area.setWidget(self.log_inner)
        v.addWidget(self.log_area, 1)
        return panel

    def _make_views(self) -> None:
        from .battle_view import BattleView
        from .codex_view import CodexView
        from .diplomacy_view import DiplomacyView
        from .expedition_view import ExpeditionView
        from .helm_view import HelmView
        from .minigame_view import DecodingView, DockingView
        from .empire_view import EmpireView
        from .map_view import MapView
        from .port_view import PortView
        from .ship_view import ShipView
        from .system_view import SystemView
        from .tech_view import TechView
        from .dig_view import DigView
        from .help_view import HelpView
        from .legacy_view import LegacyView
        from .demand_view import DemandView
        from .envoy_view import EnvoyView
        from .transit_view import TransitView
        from .yard_view import YardView

        classes = {
            "map": MapView, "system": SystemView, "port": PortView,
            "ship": ShipView, "yard": YardView, "tech": TechView,
            "empire": EmpireView, "codex": CodexView, "battle": BattleView,
            "ground": ExpeditionView, "helm": HelmView,
            "diplomacy": DiplomacyView,
            "docking": DockingView, "decoding": DecodingView,
            "transit": TransitView, "dig": DigView, "legacy": LegacyView,
            "help": HelpView,
            "demand": DemandView,
            "envoy": EnvoyView,
        }
        for vid, cls in classes.items():
            view = cls(self)
            view.hide()
            self.stack_layout.addWidget(view)
            self.views[vid] = view

    # ── navigation ─────────────────────────────────────────────────────────

    # An approach, an exchange and a crossing all belong to the game rather
    # than to the window: a save taken in the middle of one used to lose it.
    # A battle stays on the window deliberately — `battle_state` says so, on
    # the grounds that no time passes while you are being shot at.
    def _on_game(name):
        return property(lambda self: getattr(self.game, name, None),
                        lambda self, value: setattr(self.game, name, value))

    transit = _on_game("transit")
    dig = _on_game("dig")
    situation = _on_game("situation")
    legacy = _on_game("legacy")
    demand = _on_game("demand")
    envoy = _on_game("envoy")
    docking = _on_game("docking")
    decoding = _on_game("decoding")
    decoding_tech = _on_game("decoding_tech")
    del _on_game

    def go(self, view_id: str) -> None:
        if self.battle is not None and not self.battle.over and view_id != "battle":
            self.toast("You are under fire. Finish the engagement first.", "warn")
            view_id = "battle"
        elif self.demand is not None and not self.demand.over \
                and view_id not in ("demand", "battle"):
            self.toast("A power is waiting on an answer about your holding.",
                       "warn")
            view_id = "demand"
        elif self.envoy is not None and not self.envoy.over \
                and view_id not in ("envoy", "battle"):
            self.toast("There is an envoy waiting on an answer.", "warn")
            view_id = "envoy"
        elif self.situation is not None and not self.situation.over \
                and view_id not in ("legacy", "battle"):
            self.toast("Something is waiting on an answer.", "warn")
            view_id = "legacy"
        elif self.dig is not None and not self.dig.over \
                and view_id not in ("dig", "battle"):
            self.toast("There is a trench open. Work it or backfill it.", "warn")
            view_id = "dig"
        elif self.transit is not None and not self.transit.over \
                and view_id not in ("transit", "battle"):
            self.toast("You are under way. Fly it or cut the burn.", "warn")
            view_id = "transit"
        elif self.docking is not None and not self.docking.over \
                and view_id not in ("docking", "battle"):
            self.toast("You are on final approach.", "warn")
            view_id = "docking"
        elif self.decoding is not None and not self.decoding.over \
                and view_id not in ("decoding", "battle"):
            self.toast("The bench is mid-exchange.", "warn")
            view_id = "decoding"
        elif (getattr(self.game, "expedition", None) is not None
              and view_id not in ("ground", "battle")):
            self.toast("A party is on the ground. Bring them up first.", "warn")
            view_id = "ground"
        if self.current is not None:
            self.views[self.current].hide()
        self.current = view_id
        # The tutorial watches state, not clicks — but "you looked at the
        # plans" is only observable here, so the window reports what it opened.
        from ..sim import tutorial as tutorial_sim
        tab = getattr(self.views[view_id], "tab", "")
        tutorial_sim.saw(self.game, view_id)
        if tab:
            tutorial_sim.saw(self.game, f"{view_id}:{tab}")
        view = self.views[view_id]
        view.show()
        for vid, b in self.nav_buttons.items():
            b.setChecked(vid == view_id)
        self.refresh()

    def refresh(self) -> None:
        """Redraw the status bar, the log and the active screen."""
        self.game.recompute()
        self._refresh_hud()
        self._refresh_log()
        if self.current:
            self.views[self.current].refresh()
        from ..sim import tutorial as tutorial_sim
        if tutorial_sim.check(self.game):
            self.tutorial_bar.refresh()
        elif tutorial_sim.running(self.game):
            self.tutorial_bar.refresh()
        # Autosave whenever the calendar has moved. Writing the whole sector on
        # every repaint would be wasteful; days only pass on real actions.
        # Autosave on the player's cadence. At zero it saves whenever the
        # calendar moves, which is what it always did.
        from ..sim import options as options_sim
        every = options_sim.get(self.game, "autosave_days") or 0
        since = self.game.day - getattr(self, "_saved_day", -10 ** 9)
        if since >= every:
            self._saved_day = self.game.day
            self.game.save()

    def _refresh_hud(self) -> None:
        from .hud import refresh
        refresh(self)

    def _refresh_log(self) -> None:
        while self.log_col.count():
            item = self.log_col.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        for day, text, kind in reversed(self.game.log[-60:]):
            entry = QWidget()
            v = QVBoxLayout(entry)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(1)
            v.addWidget(mono_label(stardate(day)))
            lb = label(text, "", kind if kind in theme.TINTS else "", wrap=True)
            lb.setStyleSheet(
                f"color: {theme.tint(kind) if kind in theme.TINTS else theme.INK2};"
                "font-size: 12.5px;")
            v.addWidget(lb)
            self.log_col.addWidget(entry)

    # ── dialogs ────────────────────────────────────────────────────────────

    def toast(self, text: str, kind: str = "") -> None:
        self.statusBar().setStyleSheet(
            f"color: {theme.tint(kind) if kind else theme.INK3};"
            f"font-family: '{theme.mono_family()}'; font-size: 10px;")
        self.statusBar().showMessage(text, 6000)

    def dialog(self, heading: str, widgets, buttons=(("Close", None),),
               width: int = 620):
        """A modal panel. ``buttons`` is a list of (label, value)."""
        dlg = QDialog(self)
        dlg.setWindowTitle(heading)
        dlg.setMinimumWidth(width)
        v = QVBoxLayout(dlg)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(10)
        v.addWidget(label(heading, "h2"))
        for w in widgets:
            v.addWidget(body_or(w))
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 8, 0, 0)
        h.addStretch(1)
        result = {"value": None}

        def choose(val):
            result["value"] = val
            dlg.accept()

        for i, (text, val) in enumerate(buttons):
            kind = "primary" if i == 0 else "flat"
            h.addWidget(button(text, lambda v_=val: choose(v_), kind=kind))
        v.addWidget(row)
        dlg.exec()
        return result["value"]

    def confirm(self, heading: str, text: str,
                yes: str = "Do it", no: str = "Belay that") -> bool:
        """Ask, unless the player has said not to be asked."""
        from ..sim import options as options_sim
        if not options_sim.get(self.game, "confirm"):
            return True
        return bool(self.dialog(heading, [text], [(yes, True), (no, False)]))

    def apply_options(self) -> None:
        """Push settings into the parts of the window that hold their own."""
        from ..sim import options as options_sim
        pace = options_sim.get(self.game, "instrument_ms") or 900
        for monitor in getattr(self, "monitors", {}).values():
            monitor.timer.setInterval(int(pace))

    # ── combat ─────────────────────────────────────────────────────────────

    def begin_combat(self, encounter: dict, return_to: str = "system") -> None:
        self._return_to = return_to
        self.views["battle"].begin(encounter)
        self.go("battle")

    def end_combat(self) -> None:
        self.battle = None
        self.game.save()
        self.go(self._return_to)

    # ── endings ────────────────────────────────────────────────────────────

    def check_ending(self) -> bool:
        g = self.game
        if g.victory:
            name = next((v[1] for v in VICTORIES if v[0] == g.victory), "Ending")
            self._ending(name, ENDINGS.get(g.victory, ""), ending=g.victory)
            return True
        if g.dead:
            key = g.ending or "lost"
            name = "Overgrown" if key == "overgrown" else "The chronicle ends"
            # The game has always known why; it simply never said.
            self._ending(name, ENDINGS.get(key, ENDINGS["lost"]),
                         g.death_reason)
            return True
        return False

    def _ending(self, heading: str, text: str, cause: str = "",
                ending: str = "") -> None:
        """An ending is a turn in the sector's history, not necessarily a stop.

        Every ending opens an epoch — the world is rewritten once and a new
        clock starts in place of the Bloom — so the dialog offers to carry on
        as well as to begin again.
        """
        from ..data.epochs import EPOCHS_BY_ID
        from ..sim import legacy as legacy_sim

        g = self.game
        stats_line = (f"Stardate {g.day} days · {len(g.discovered['systems'])} systems "
                      f"visited · {g.discovered['lifeforms']} organisms catalogued · "
                      f"{len(g.colonies)} colonies planted.")
        body = [text]
        if cause:
            body.append(label(cause, "", "warn", wrap=True))
        body.append(label(stats_line, "note", wrap=True))

        epoch = EPOCHS_BY_ID.get(ending)
        choices = [("Begin again", "again")]
        if epoch is not None:
            body.append(label(f"What follows: {epoch.name}. {epoch.pressure}",
                              "", "chloro", wrap=True))
            choices.insert(0, (f"Carry on into {epoch.name}", "carry"))

        picked = self.dialog(heading, body, choices)
        if picked == "carry" and epoch is not None:
            legacy_sim.begin(g, ending)
            self.save()
            self.go("legacy")
            return
        state_mod.clear_save()
        from .title import start_new_chronicle
        start_new_chronicle(self)


def body_or(w):
    """Accept either a widget or a paragraph of text."""
    if isinstance(w, str):
        return label(w, "", wrap=True)
    return w
