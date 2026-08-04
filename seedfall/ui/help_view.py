"""Help and options: how the game works, and the handful of things you can set.

Two tabs. The manual reads out of `sim/manual.py`, whose facts are counted from
the tables they describe, so nothing here can go stale by being written down
twice. Options read and write `sim/options.py`, where the bounds live — a
screen that clamps its own values is a second place for the rule to be wrong.

Every option on this screen does something. The one that cannot — speech
through a language model, when the machine has not permitted one — says so in
words rather than offering a toggle that silently fails.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from ..data.help import TOPICS
from ..data.screens import KEY_FOR, NAV, NAV_KEYS
from ..sim import manual as manual_sim
from .widgets import (Panel, TabBar, View, button, defer, label, note,
                      spacer)


class HelpView(View):
    def __init__(self, win):
        super().__init__(win)
        self.tab = "manual"
        self.topic = TOPICS[0].id
        self.query = ""
        self._typing = False
        self._box = None

    def build(self) -> None:
        self.head("Help", "How the Verge works, and what you can change "
                          "about how it is shown to you.")
        tabs = TabBar([("manual", "Manual"), ("academy", "Academy"),
                       ("options", "Options"), ("keys", "Keys")], self.tab)
        tabs.changed.connect(self._switch)
        self.col.addWidget(tabs)
        {"options": self._options, "keys": self._keys,
         "academy": self._academy,
         "manual": self._manual}[self.tab]()

    def _academy(self) -> None:
        """The curriculum, and a way into any course — `ui/academy_panel`."""
        from .academy_panel import build as academy
        academy(self)

    def _switch(self, tid: str) -> None:
        self.tab = tid
        self.refresh()

    # ── manual ─────────────────────────────────────────────────────────────

    def _manual(self) -> None:
        search_row = QWidget()
        row = QHBoxLayout(search_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(label("Search", "label"))
        box = QLineEdit(self.query)
        box.setPlaceholderText("a word — heat, contraband, berth, ending")
        box.setFixedWidth(320)
        box.textChanged.connect(self._search)
        row.addWidget(box)
        self._box = box
        if self._typing:
            # The rebuild replaced the box the player was typing into, so put
            # them back in it with the cursor where they left it. Deferred
            # again: at this point the box is not yet in the visible layout,
            # so `setFocus` here sets the cursor and nothing else.
            self._typing = False
            defer(lambda b=box: (b.setFocus(),
                                 b.setCursorPosition(len(self.query))))
        row.addStretch(1)
        self.col.addWidget(search_row)

        found = manual_sim.search(self.query)
        if not found:
            self.col.addWidget(note(f"Nothing in the manual mentions "
                                    f"{self.query!r}."))
            return
        if self.topic not in {t.id for t in found}:
            self.topic = found[0].id
        self.row(self._contents(found), self._page())

    def _contents(self, found) -> Panel:
        p = Panel(f"Contents — {len(found)} of {len(TOPICS)}")
        for topic in found:
            p.add(button(topic.title, lambda t=topic: self._open(t.id),
                         kind="primary" if topic.id == self.topic else "flat"))
        return p

    def _open(self, topic_id: str) -> None:
        self.topic = topic_id
        self.refresh()

    def _search(self, text: str) -> None:
        """Filter as they type, without destroying the box they are typing in.

        `textChanged` fires *during* the keystroke. Rebuilding here freed the
        QLineEdit mid-event and segfaulted the process on the first character
        — not an exception, a signal 11. The rebuild is deferred to the next
        turn of the event loop and the cursor is restored afterwards.
        """
        self.query = text
        self._typing = True
        self.refresh_later()

    def _page(self) -> Panel:
        page = manual_sim.page(self.game, self.topic)
        p = Panel(page["title"])
        for paragraph in page["body"]:
            p.add(label(paragraph, "", wrap=True))
            p.add(spacer(3))
        if page["facts"]:
            p.add(spacer(4))
            p.add(label("As things stand", "label"))
            for line in page["facts"]:
                # Wrapped, not monospaced. A generated fact can be any length,
                # and an unwrapped label forces a minimum width wider than the
                # view — which pushed the whole manual off the right edge.
                p.add(label(line, "", "dim" if line.startswith("  ") else "",
                            wrap=True))
        if page["screen"] in KEY_FOR:
            # Only a rail screen can be walked to from here — an event view
            # (the battle, the ground) exists when its event does. And the
            # button carries the rail's name for it, not the internal id:
            # it used to read "GO TO THE EMPIRE SCREEN" over a rail that
            # says Holdings.
            name = dict(NAV)[page["screen"]].split("  ", 1)[-1]
            p.add(spacer(6))
            p.add(button(f"Go to {name}",
                         lambda s=page["screen"]: self.win.go(s),
                         kind="primary"))
        if page["see"]:
            p.add(spacer(4))
            p.add(label("See also", "label"))
            for other in page["see"]:
                p.add(button(other.title, lambda t=other: self._open(t.id),
                             kind="flat"))
        return p

    # ── options ───────────────────────────────────────────────────────────

    def _options(self) -> None:
        """The same panel the menu bar opens in a window. One implementation.

        Two options pages is two places for the bounds to disagree, and this
        project has spent enough cycles on screens that contradicted the thing
        they described.
        """
        from .options_view import OptionsPanel
        self.col.addWidget(OptionsPanel(self.win))

    # ── keys ───────────────────────────────────────────────────────────────

    def _restart_tutorial(self) -> None:
        from ..sim import tutorial as tutorial_sim
        tutorial_sim.begin(self.game)
        self.win.save()
        self.win.go(tutorial_sim.current(self.game).screen)

    def _keys(self) -> None:
        p = Panel("Keyboard")
        p.add(note("One key per screen. The table lives in "
                   "`data/screens.py`, which is also what the rail is built "
                   "from, so a screen cannot exist without a key."))
        for key, screen in NAV_KEYS:
            p.add_row(screen, key)
        self.col.addWidget(p)
        self.col.addWidget(note(
            "The chronicle saves itself whenever the calendar moves. There is "
            "one save and no way to take a roll again."))
        self.buttons(button("Walk me through it again",
                            self._restart_tutorial))
