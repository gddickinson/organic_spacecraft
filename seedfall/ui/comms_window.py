"""The comms window: talk to a thing, and see what can be done with it.

**The general answer to "how do I interact with this?"** A player flew to a
Weave anchor and could not find a way to use it, because the panel that rides
a ring lives on the sector chart — and that shape was waiting behind every
other contact in the game. The acts existed; they were scattered across
screens that each knew about one kind of object.

This is one window that opens on *anything*: a quay, a gate, a world, a hull.
It shows who they are, what they say when you open the channel, and a menu of
what can be done — every entry either available or greyed with the reason in
the words the captain would use.

It decides nothing. `sim/hail.py` says what to offer and the existing doors do
the work, so a menu here cannot promise something the game will refuse.

**And it never waits on a language model.** The greeting was asked for on
the window's own thread, and against an endpoint that accepts a connection
and never answers the whole game froze for twelve seconds per line. Now the
written line goes up at once and, when speech is on, the model is asked on
a worker thread; its line replaces the written one if it arrives while the
same channel is still open, and is dropped if it does not.
"""

from __future__ import annotations

import threading
import weakref

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QWidget

from ..sim import hail as hail_sim
from ..sim import voice as voice_sim
from . import theme
from .widgets import Panel, button, label, mono_label, note, spacer


class CommsWindow(QDialog):
    """One channel, one contact, and everything you can do about it."""

    def __init__(self, win, contact):
        super().__init__(win)
        self.win = win
        self.game = win.game
        self.contact = contact
        self.exchange = hail_sim.Exchange()
        #: Bumped whenever the channel changes hands, so a model's line that
        #: arrives for the last contact is not put in this one's mouth.
        self.channel = 0
        self.setWindowTitle(f"Comms — {contact.name}")
        self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(theme.stylesheet())
        self.resize(620, 700)
        self.col = QVBoxLayout(self)
        self.col.setContentsMargins(16, 14, 16, 14)
        self.col.setSpacing(8)
        self._greet(contact)
        self._build()

    # ── the greeting, and a model's better one when it comes ───────────────

    def _greet(self, contact) -> None:
        """Say the written line now; ask a model for a better one elsewhere."""
        said = hail_sim.opening(self.game, contact)
        self.exchange.add(contact.name, said["line"])
        if said["ask"] is not None:
            _ask_later(self, self.channel, len(self.exchange.said) - 1,
                       said["ask"])

    def heard(self, channel: int, index: int, line: str) -> None:
        """A model's line has arrived: swap it in, if it is still wanted."""
        if channel != self.channel or index >= len(self.exchange.said):
            return
        who, _written = self.exchange.said[index]
        self.exchange.said[index] = (who, line)
        self._build()

    # ── building ───────────────────────────────────────────────────────────

    def _build(self) -> None:
        while self.col.count():
            item = self.col.takeAt(0)
            if item.widget() is not None:
                item.widget().setParent(None)

        who = hail_sim.about(self.game, self.contact)
        head = QWidget()
        v = QVBoxLayout(head)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        v.addWidget(label(self.contact.name, "h2"))
        line = who["kind"].title()
        if who["power"]:
            line += f" · {who['power']}"
        if who["standing"] is not None:
            line += f" · standing {who['standing']:+.0f}"
        v.addWidget(note(line))
        if who["what"]:
            v.addWidget(label(who["what"], "", "dim", wrap=True))
        self.col.addWidget(head)

        # **The picker lives here.** One control on the bridge opens the
        # channel; switching who you are talking to is done inside it, which
        # keeps the bridge's control set stable on a beat and its content
        # above the fold.
        others = _in_reach(self.game)
        if len(others) > 1:
            switch = Panel("On the array")
            for other in others[:8]:
                if other.id == self.contact.id:
                    continue
                switch.add(button(other.name,
                                  lambda _=False, c=other: self._switch(c),
                                  kind="flat",
                                  tip=f"Open the channel on {other.name}."))
            self.col.addWidget(switch)

        said = Panel("The channel")
        for speaker, text in self.exchange.said[-6:]:
            said.add(mono_label(speaker))
            said.add(label(text, "", "", wrap=True))
            said.add(spacer(3))
        self.col.addWidget(said)

        acts = Panel("What you can do")
        for option in sorted(hail_sim.options(self.game, self.contact),
                             key=lambda o: (o.order, o.label)):
            acts.add(spacer(3))
            acts.add(button(option.label,
                            lambda _=False, o=option: self._do(o),
                            kind="primary" if option.ok and option.order <= 20
                            else "flat",
                            enabled=option.ok,
                            tip=option.why or option.blurb))
            acts.add(note(option.blurb if option.ok
                          else (option.why or option.blurb)))
        self.col.addWidget(acts)
        self.col.addStretch(1)
        self.col.addWidget(button("Close the channel", self.close, kind="flat"))

    def _switch(self, contact) -> None:
        """Talk to something else without closing the channel."""
        self.contact = contact
        self.setWindowTitle(f"Comms — {contact.name}")
        self.exchange = hail_sim.Exchange()
        self.channel += 1
        self._greet(contact)
        self._build()

    # ── acting ─────────────────────────────────────────────────────────────

    def _do(self, option) -> None:
        """Carry out an option, or hand the captain to the screen that does.

        Nothing here performs a rule of its own: an act goes through the door
        that already owns it, and anything with a screen behind it opens that
        screen with the window closed behind the captain.
        """
        game, contact = self.game, self.contact
        oid = option.id

        if oid == "conn":
            # The conn window is the door that opens a flight on a contact,
            # and it already refuses with a reason when it cannot.
            from .conn_window import open_conn
            self.close()
            open_conn(self.win, contact)
            return
        if oid == "talk":
            self.exchange.add("You", "This is the Patient Increment. Who are "
                                     "you and what are you carrying?")
            self._greet(contact)
            self._build()
            return
        if oid == "mark":
            # `sim/hostiles` is the one door for a mark — `traffic` and every
            # board read it, which is what keeps the screens agreeing.
            from ..sim import hostiles as hostiles_sim
            hull_id = getattr(contact, "hull_id", None) or contact.id
            if hostiles_sim.is_marked(game, hull_id):
                hostiles_sim.clear(game, hull_id)
                self.exchange.add("You", f"The mark on {contact.name} is struck.")
            else:
                hostiles_sim.mark(game, hull_id)
                self.exchange.add("You", f"{contact.name} is marked hostile.")
            self.win.refresh()
            self._build()
            return
        if oid.startswith("step:"):
            from ..sim import gates as gates_sim
            out = gates_sim.use(game, int(oid.split(":", 1)[1]))
            if not out.get("ok"):
                self.win.toast(out["why"], "warn")
                return
            self.win.toast(f"{out['ly_saved']:.0f} light years, no time at "
                           f"all. ₡{out['credits']:,.0f} in tolls.", "good")
            self.close()
            self.win.go("map")
            return

        if option.goes_to:
            self.close()
            self.win.go(option.goes_to)
            return
        self.win.toast(option.why or "Nothing came of it.", "warn")


class _Courier(QObject):
    """Carries a model's line from the worker back to the window's thread.

    One for the process, made on the main thread the first time it is
    needed and never destroyed, so a worker never emits on an object Qt has
    already deleted. A queued connection is what puts `_deliver` on the
    thread the window lives on.
    """

    heard = pyqtSignal(object)


_COURIER: list = []


def _courier() -> _Courier:
    if not _COURIER:
        courier = _Courier()
        courier.heard.connect(_deliver, Qt.ConnectionType.QueuedConnection)
        _COURIER.append(courier)
    return _COURIER[0]


def _ask_later(window, channel: int, index: int, ask) -> threading.Thread:
    """Ask the model on a worker thread; deliver its line if it gives one.

    The worker holds only the `Ask` — plain strings built from the game on
    this thread — and a weak reference to the window, so nothing it does can
    touch the chronicle or keep a closed window alive.
    """
    courier = _courier()
    ref = weakref.ref(window)

    def work() -> None:
        line = voice_sim.model_line(ask)
        if line:
            courier.heard.emit((ref, channel, index, line))

    worker = threading.Thread(target=work, daemon=True, name="seedfall-voice")
    worker.start()
    return worker


def _deliver(packet) -> None:
    ref, channel, index, line = packet
    window = ref()
    if window is None:
        return
    try:
        window.heard(channel, index, line)
    except RuntimeError:
        # Closed and deleted on the C++ side while the model was talking.
        pass


def _in_reach(game) -> list:
    """Everything the array holds, nearest first — the channel's own list."""
    from ..sim import track as track_sim
    contacts = [c for c in track_sim.contacts(game) if c.kind != "star"]
    conn = getattr(game, "conn", None)
    if conn is None:
        return contacts
    from ..sim import engage as engage_sim
    return [c for _km, c in
            sorted(((engage_sim.range_km(game, conn, c), c)
                    for c in contacts), key=lambda row: row[0])]


def open_comms(win, contact) -> CommsWindow:
    """Open the channel on this contact, or raise the one already open."""
    existing = getattr(win, "comms_window", None)
    if existing is not None:
        try:
            existing.close()
        except RuntimeError:
            pass
    window = CommsWindow(win, contact)
    win.comms_window = window
    window.show()
    return window
