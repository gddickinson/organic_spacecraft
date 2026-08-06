"""Despatches and the chronicle: the sector's mail, and the ship's own record.

`sim/comms.py` has been a complete, ticking, saved inbox since the ninth pass
— senders, channels, courier lag, questions with reply keys, a staleness note
per signal — and **nothing in `ui/` ever called it**: signals accumulated
unbounded in the save because nothing could mark one read, and the sidebar
showed sixty of the chronicle's three hundred stored lines with the rest
unreachable. This screen is both halves: the despatches, and the full log.

Not `ui/comms_window.py` — that is the hail window over `sim/hail`, "talk to
a thing your cursor is on". This is everything that arrived while you were
not looking.

Every action here is a `sim/comms` door (`read`, `answer`); the screen
decides nothing, which is what keeps a reply button from promising an answer
the inbox would refuse.
"""

from __future__ import annotations

from ..core.util import stardate
from ..data import signals as signals_data
from ..sim import comms as comms_sim
from . import theme
from .widgets import Panel, TabBar, View, button, label, note, spacer

#: How many despatches the tab lays out at once. The inbox is capped by
#: `comms.sweep`, but a wall of every bulletin ever kept is not a screen.
SHOWN = 40


class DespatchView(View):
    """The inbox and the chronicle, one tab each."""

    tab = "despatches"

    def build(self) -> None:
        g = self.game
        unread = comms_sim.unread(g)
        self.head("Despatches",
                  "What the sector has sent you, and what the ship has "
                  "recorded. A courier is not a radio: distant word arrives "
                  "as old as the crossing made it.")
        bar = TabBar([("despatches", "Despatches"), ("chronicle", "Chronicle")],
                     current=self.tab)
        bar.changed.connect(self._switch)
        self.col.addWidget(bar)
        if self.tab == "chronicle":
            self._chronicle(g)
        else:
            self._inbox(g, unread)
        self.buttons(button("Back to the chart", lambda: self.win.go("map")))

    def _switch(self, tab_id: str) -> None:
        self.tab = tab_id
        # The tab bar's own button is destroyed by the rebuild — defer.
        self.refresh_later()

    # ── the inbox ──────────────────────────────────────────────────────────

    def _inbox(self, g, unread: int) -> None:
        arrived = comms_sim.inbox(g)
        if not arrived:
            self.col.addWidget(Panel("Nothing on the board").add(
                "No despatch has reached the ship. Traffic control writes "
                "when a clearance is granted; the powers write when their "
                "opinion of you changes band; the sector's news rides "
                "couriers and arrives late.",
                note("Where there is no Weave anchor, word travels aboard "
                     "ordinary hulls — eleven days a light year.")))
            return
        self.col.addWidget(label(
            f"{len(arrived)} despatch(es), {unread} unread.", "sub"))
        asking = [s for s in arrived if s.asks]
        if asking:
            self.col.addWidget(label(
                f"{len(asking)} waiting on an answer.", "sub", "warn"))
        if unread:
            self.buttons(button("Mark the rest read", self._read_all,
                                kind="flat",
                                tip="Questions stay open; only the telling "
                                    "is put away."))
        for sig in arrived[:SHOWN]:
            self.col.addWidget(self._signal(sig))
        if len(arrived) > SHOWN:
            self.col.addWidget(note(
                f"…and {len(arrived) - SHOWN} older, further down the spike. "
                "The oldest read traffic is swept on its own."))

    def _signal(self, sig) -> Panel:
        channel = signals_data.of(sig.channel)
        p = Panel(f"{sig.name} — {sig.subject}",
                  "" if sig.read else channel.tint)
        p.add(label(f"{channel.name} · {sig.note}"
                    + ("" if sig.read else " · UNREAD"), "sub"))
        p.add(sig.body)
        if sig.asks:
            row = [button(words, self._answer(sig.id, key),
                          kind="primary" if index == 0 else "")
                   for index, (key, words) in enumerate(sig.replies)]
            p.add_buttons(*row)
        elif sig.answered:
            said = dict(sig.replies).get(sig.answered, sig.answered)
            p.add(note(f"Answered: {said}."))
        elif not sig.read:
            p.add_buttons(button("Noted", self._read(sig.id), kind="flat"))
        return p

    def _read(self, signal_id: str):
        def go():
            comms_sim.read(self.game, signal_id)
            self.win.refresh()
        return go

    def _read_all(self) -> None:
        for sig in comms_sim.inbox(self.game):
            if not sig.asks:
                comms_sim.read(self.game, sig.id)
        self.win.refresh()

    def _answer(self, signal_id: str, key: str):
        def go():
            if not comms_sim.answer(self.game, signal_id, key):
                self.win.toast("That is no longer being asked.", "warn")
                return
            self.win.toast("Sent.")
            self.win.refresh()
        return go

    # ── the chronicle ──────────────────────────────────────────────────────

    def _chronicle(self, g) -> None:
        """The whole stored log, newest first — the sidebar shows sixty of
        three hundred and the rest were unreachable anywhere."""
        if not g.log:
            self.col.addWidget(Panel("A clean page").add(
                "Nothing has been entered in the ship's log yet."))
            return
        kinds = sorted({k for _d, _t, k in g.log if k})
        want = getattr(self, "_kind", "")
        if want and want not in kinds:
            want = ""                 # a filter for a kind no longer held
        if kinds:
            bar = TabBar([("", "All")] + [(k, k.title()) for k in kinds],
                         current=want)
            bar.changed.connect(self._filter)
            self.col.addWidget(bar)
        shown = 0
        p = Panel(f"The chronicle — {len(g.log)} lines held")
        for day, text, kind in reversed(g.log):
            if want and kind != want:
                continue
            tint = kind if kind in theme.TINTS else ""
            p.add_row(stardate(day), "", "")
            p.add(label(text, "", tint, wrap=True))
            shown += 1
        p.add(spacer(2))
        self.col.addWidget(p)
        if not shown:
            self.col.addWidget(note("Nothing of that kind in the record."))

    def _filter(self, kind: str) -> None:
        self._kind = kind
        self.refresh_later()
