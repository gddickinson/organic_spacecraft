"""The cockpit: one seat, one hull, and everything the pilot has.

A player asked for single-seat fighters flown from their own screen, the way
the gunner has one. This is that screen — a pop-out, like the conn and the
turret, so the chronicle stays open behind it.

It owns no rules. The flight is `sim/craft.sortie` (a `sim/conn.Conn` built
from the craft's own numbers), the beat is `sim/craft.beat`, and every
button is a call into `sim/craft`: the stick, the drive, the three computer
modes, the guns, an hour's looking, and the cradle. What is shown is what
the pilot would have in front of them: hull, tank, speed, the range home,
and whatever is out there.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QWidget

from ..core.util import reaction_mass
from ..data.craft import ROLES
from ..data.mounts import AXES
from ..sim import craft as craft_sim
from ..sim import descent_flight
from ..sim import engage as engage_sim
from . import theme
from .viewport import Viewport
from .widgets import Panel, Pill, button, label, note

#: How often the cockpit's clock beats, in milliseconds.
BEAT_MS = 250
#: What the craft's computer will do, in the words a pilot would use.
#: These are the free-flight modes (`sim/flightdeck.computer`): a sortie is
#: flown in open space, not on an approach to a berth.
MODES = (("run", "Run for it"), ("brake", "All stop"),
         ("null", "Hold station"))
#: And the one a descent adds, which replaces them: a lander on her way
#: down has nothing to run at and nowhere to hold station
#: (`sim/descent_flight.py`).
DESCENT_MODES = (("down", "Take her down"), ("brake", "Hold her off"))


class CraftWindow(QDialog):
    """One seat, flown in its own window."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.game = win.game
        self.setWindowTitle("Cockpit — SEEDFALL")
        self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(theme.stylesheet())
        self.resize(1000, 700)
        #: What the pilot is pointed at, by contact id.
        self.aim: str | None = None
        self.held: str | None = None
        self.running = False
        self.timer = QTimer(self)
        self.timer.setInterval(BEAT_MS)
        self.timer.timeout.connect(self._beat)
        self.view = None
        self.col = QVBoxLayout(self)
        self._build()

    # ── what is being flown ───────────────────────────────────────────────

    @property
    def conn(self):
        return craft_sim.sortie(self.game)

    @property
    def craft(self):
        return craft_sim.flying(self.game)

    def contacts(self) -> list:
        from ..sim import track as track_sim
        conn = self.conn
        if conn is None:
            return []
        rows = [c for c in track_sim.contacts(self.game)
                if c.kind in ("hull", "body", "anchorage")]
        return sorted(rows,
                      key=lambda c: engage_sim.range_km(self.game, conn, c))[:8]

    def target(self):
        return next((c for c in self.contacts() if c.id == self.aim), None)

    # ── the screen ────────────────────────────────────────────────────────

    def _build(self) -> None:
        while self.col.count():
            item = self.col.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # Off the screen *now*, not when the event loop gets round
                # to it: a deferred delete left the last build's panels
                # painted over this one's.
                widget.setParent(None)
                widget.deleteLater()
        craft, conn = self.craft, self.conn
        if craft is None or conn is None:
            self.col.addWidget(label("Nothing is out.", "h2"))
            self.col.addWidget(button("Close", self.close, kind="primary"))
            return
        kind = craft_sim.kind_of(craft)
        head = QWidget()
        row = QHBoxLayout(head)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(label(f"{craft.name} — {kind.name}", "h2"))
        row.addWidget(Pill(kind.role, "chloro"))
        row.addWidget(label(craft_sim.name_of(self.game, craft.pilot)
                            + " at the stick", "note"))
        row.addStretch(1)
        self.col.addWidget(head)

        body = QWidget()
        across = QHBoxLayout(body)
        across.setContentsMargins(0, 0, 0, 0)
        self.view = Viewport(conn, "fore")
        across.addWidget(self.view, 3)
        side = QWidget()
        panel = QVBoxLayout(side)
        panel.setContentsMargins(0, 0, 0, 0)
        panel.addWidget(self._instruments(craft, kind, conn))
        panel.addWidget(self._console())
        panel.addWidget(self._errands())
        panel.addStretch(1)
        across.addWidget(side, 2)
        self.col.addWidget(body, 1)

    def _instruments(self, craft, kind, conn) -> Panel:
        p = Panel("Instruments")
        p.add_row("Hull", f"{craft.hp} / {kind.hull}",
                  "warn" if craft.hp * 3 < kind.hull else "")
        p.add_row("Reaction mass", reaction_mass(craft.fuel))
        p.add_row("Speed", f"{conn.speed:,.1f} m/s")
        p.add_row("Off the cradle", f"{craft_sim.out_km(self.game):,.2f} km")
        p.add_row("Flown", f"{conn.elapsed / 3600:,.2f} h")
        if descent_flight.under_way(self.game) is not None:
            p.add_row("Height", f"{descent_flight.height_km(conn):,.0f} km")
            catch = descent_flight.catch_rate(conn)
            p.add_row("The drive takes off", f"{catch:,.0f} m/s",
                      "" if conn.speed <= catch else "warn")
            p.add_row("Hold her under", f"{descent_flight.ceiling(conn):,.0f} m/s")
            p.add_row("She lands at", f"{descent_flight.gate_km(conn):,.1f} km")
        got = self.target()
        if got is not None:
            p.add_row(got.name,
                      f"{engage_sim.range_km(self.game, conn, got):,.0f} km")
        for line in conn.log[-3:]:
            p.add(label(line, "note", wrap=True))
        return p

    def _console(self) -> Panel:
        p = Panel("The stick")
        rows = []
        for axis_id, name, _vec in AXES:
            b = button(name, lambda _=False, a=axis_id: self._burn(a),
                       kind="flat")
            b.setObjectName(f"craft_burn_{axis_id}")
            rows.append(b)
        p.add_buttons(*rows[:3])
        p.add_buttons(*rows[3:])
        conn = self.conn
        drive = button("Main drive: on" if conn.arm_main else "Main drive: off",
                       self._toggle_drive,
                       kind="primary" if conn.arm_main else "flat")
        drive.setObjectName("craft_drive")
        offered = (DESCENT_MODES
                   if descent_flight.under_way(self.game) is not None
                   else MODES)
        modes = [button(("▶ " if conn.auto == mode else "") + text,
                        lambda _=False, m=mode: self._auto(m),
                        kind="primary" if conn.auto == mode else "flat")
                 for mode, text in offered]
        for mode, b in zip(offered, modes):
            b.setObjectName(f"craft_auto_{mode[0]}")
        p.add_buttons(drive, *modes)
        clock = button("Stop clock" if self.running else "Run clock",
                       self._toggle_clock,
                       kind="primary" if not self.running else "")
        clock.setObjectName("craft_clock")
        p.add_buttons(clock, button("Hands off", lambda: self._auto(None),
                                    kind="flat"))
        return p

    def _errands(self) -> Panel:
        p = Panel("The errand")
        got = self.target()
        for contact in self.contacts()[:5]:
            picked = contact.id == self.aim
            b = button(("✓ " if picked else "") + contact.name,
                       lambda _=False, c=contact.id: self._pick(c),
                       kind="primary" if picked else "flat")
            b.setObjectName(f"craft_aim_{contact.kind}")
            p.add(b)
        fire_ok, fire_why = (craft_sim.can_strike(self.game, got)
                             if got is not None else (False, "Pick something."))
        look_ok, look_why = (craft_sim.can_scout(self.game, got)
                             if got is not None else (False, "Pick something."))
        fire = button("Make a run at it", self._strike, kind="danger",
                      enabled=fire_ok, why=fire_why)
        fire.setObjectName("craft_strike")
        look = button("Go and look", self._scout, enabled=look_ok,
                      why=look_why)
        look.setObjectName("craft_scout")
        p.add_buttons(fire, look)
        home_ok, home_why = craft_sim.can_recover(self.game)
        home = button("Back on the cradle", self._recover, kind="primary",
                      enabled=home_ok, why=home_why)
        home.setObjectName("craft_recover")
        p.add_buttons(home, button("Leave the cockpit", self.close,
                                   kind="flat"))
        return p

    # ── the acts, every one of them the sim's ─────────────────────────────

    def _burn(self, axis: str) -> None:
        craft_sim.beat(self.game, axis, main=bool(self.conn.arm_main))
        self.refresh()

    def _toggle_drive(self) -> None:
        conn = self.conn
        if conn is not None:
            conn.arm_main = not conn.arm_main
        self.refresh()

    def _auto(self, mode) -> None:
        """Arm the computer — and lay the course on what is picked, which is
        what "run for it" runs at (`sim/freeflight.marked`)."""
        conn = self.conn
        if conn is None:
            return
        got = self.target()
        if mode == "run" and got is not None:
            from ..sim import freeflight as free_sim
            conn.mark = got.name
            free_sim.steer(self.game, conn, got)
        conn.auto = mode or ""
        self.refresh()

    def _toggle_clock(self) -> None:
        self.running = not self.running
        self.timer.start() if self.running else self.timer.stop()
        self.refresh()

    def _beat(self) -> None:
        got = craft_sim.beat(self.game, self.held,
                             main=bool(self.conn and self.conn.arm_main))
        if not got.get("ok") or got.get("outcome"):
            self.running = False
            self.timer.stop()
        if got.get("arrival") is not None:
            self._arrived(got["arrival"])
            return
        self.refresh()

    def _arrived(self, got: dict) -> None:
        """The descent is over, one way or the other (`descent_flight`)."""
        self.win.refresh()
        if got.get("down"):
            self.win.toast("She is down. The party is walking out of her."
                           if got.get("party") else
                           f"She is down. {got.get('why', '')}", "good")
            self.close()
            self.win.go("ground" if got.get("party") else "system")
            return
        self.win.toast("That was not a landing." if not got.get("lost")
                       else "She went in. Nobody is walking out of her.",
                       "bad")
        self.close()

    def _pick(self, contact_id: str) -> None:
        self.aim = contact_id
        self.refresh()

    def _strike(self) -> None:
        got = craft_sim.strike(self.game, self.target())
        self.win.toast(got.get("text") or got.get("why", ""),
                       "bad" if got.get("ok") else "warn")
        self.win.refresh()
        self.refresh()

    def _scout(self) -> None:
        got = craft_sim.scout(self.game, self.target())
        self.win.toast(got.get("text") or got.get("why", ""),
                       "good" if got.get("ok") else "warn")
        self.win.refresh()
        self.refresh()

    def _recover(self) -> None:
        got = craft_sim.recover(self.game)
        if not got.get("ok"):
            self.win.toast(got["why"], "warn")
            return
        self.win.toast(f"{reaction_mass(got['fuelled'])} into her tank.",
                       "good")
        self.win.refresh()
        self.close()

    # ── painting ──────────────────────────────────────────────────────────

    def refresh(self) -> None:
        if self.craft is None or self.conn is None:
            self.running = False
            self.timer.stop()
        self._build()

    def closeEvent(self, event) -> None:      # noqa: N802
        self.timer.stop()
        if getattr(self.win, "craft_window", None) is self:
            self.win.craft_window = None
        super().closeEvent(event)


def open_cockpit(win) -> CraftWindow:
    """Open the cockpit, or raise the one already up."""
    from . import popout
    return popout.open_one(win, "craft_window", lambda: CraftWindow(win))
