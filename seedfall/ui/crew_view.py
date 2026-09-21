"""The Crew screen: the muster book, one person at a time, and every watch.

A crew was spread over four screens and none of them was about the crew. Who
was aboard was a grid of story cards on a tab of the Ship screen; hiring was
at a port; the long sleep was under the hold; wages were a line on a ledger;
and the twenty years somebody lived before the berth were printed nowhere at
all until `sim/lifepath.py` and `sim/person.py` existed to say them.

This is the one place. Four tabs, and the division between them is the
question being asked:

- **Roster** — *who is aboard.* The complement, the six stations with their
  holes showing, and a card each, in whatever order answers the question.
- **Sheet** — *who is this person.* Everything: characteristics, skills, the
  service record, where they are from, who they know, what they own, what
  they want, what they are owed and how long they have left.
- **Watches** — *what the crew costs and what mends it.* The bill, the mood,
  the mess deck, the long sleep, the ship's own abilities, and the ties that
  reach ashore.
- **The book** — *who has gone.* Retired, paid off, and the stories that were
  told to the end.

The screen decides nothing. `sim/roster.py` answers every question on it and
every button calls an act in `sim/crew.py`, `sim/lifespan.py` or
`sim/dormancy.py` — the same doors the Port screen and the Ship screen use.
"""

from __future__ import annotations

from ..sim import crew as crew_sim
from ..sim import dormancy as dormancy_sim
from ..sim import lifespan as lifespan_sim
from ..sim import roster as roster_sim
from . import crew_ops, crew_roster, crew_sheet
from .widgets import Panel, TabBar, View, button, label, note

TABS = (("roster", "Roster"), ("sheet", "Sheet"),
        ("watches", "Watches"), ("book", "The book"))


class CrewView(View):
    """The crew, whole."""

    def __init__(self, win):
        super().__init__(win)
        self.tab = "roster"
        #: Whose sheet is open. An id rather than the officer, so a save
        #: reloaded under the same screen finds the same person and a
        #: paid-off one quietly falls back to whoever is left.
        self.picked: int | None = None
        self.order = "station"

    # ── the screen ─────────────────────────────────────────────────────────

    def build(self) -> None:
        g = self.game
        said = roster_sim.muster(g)
        self.head("The crew", self._sub(said))
        tabs = TabBar(list(TABS), self.tab)
        tabs.changed.connect(self._switch)
        self.col.addWidget(tabs)

        if not roster_sim.active(g) and self.tab in ("roster", "sheet"):
            self._nobody()
            return
        if self.tab == "sheet":
            crew_sheet.build(self, self.officer())
        elif self.tab == "watches":
            crew_ops.build(self, said)
        elif self.tab == "book":
            crew_ops.book(self)
        else:
            crew_roster.build(self, said)

    def _sub(self, said: dict) -> str:
        line = (f"{said['heads']} aboard — {said['officers']} officer(s) and "
                f"{said['hands']} hands")
        if said["asleep"]:
            line += f", {said['asleep']} of them under"
        return line + f" · {said['wages']:,.0f} credits a day in wages"

    def _nobody(self) -> None:
        self.col.addWidget(Panel("Nobody on the bridge").add(
            note("You are standing every watch yourself. A ship can be flown "
                 "that way and very little else can be done from it — a "
                 "station nobody holds is a bonus nobody gets and a skill "
                 "nobody aboard has."),
            button("Find a berth board", lambda: self.win.go("port"),
                   kind="primary")))
        self.col.addWidget(crew_ops.hands_panel(self))

    def show_tab(self, tid: str) -> None:
        """Open one tab. The tab bar and the sheet's own way back share it."""
        self.tab = tid
        self.refresh()

    def _switch(self, tid: str) -> None:
        self.show_tab(tid)

    # ── who is being read ──────────────────────────────────────────────────

    def officer(self):
        """Whose sheet is open, falling back to whoever is first aboard."""
        rows = roster_sim.active(self.game)
        if not rows:
            return None
        found = next((o for o in rows if o.id == self.picked), None)
        if found is None:
            found = rows[0]
            self.picked = found.id
        return found

    def open_sheet(self, officer) -> None:
        """Show one person, whole. The roster's cards and the sheet's own
        name bar both come through here."""
        self.picked = getattr(officer, "id", None)
        self.tab = "sheet"
        self.refresh()

    def set_order(self, order: str) -> None:
        self.order = order
        self.refresh()

    # ── the acts, every one of them the sim's ──────────────────────────────

    def pay_off(self, officer) -> None:
        got = crew_sim.pay_off(self.game, officer)
        if not got["ok"]:
            self.win.toast(got["why"], "warn")
            return
        if self.picked == getattr(officer, "id", None):
            self.picked = None
        self.win.toast(got["text"], "")
        self.win.save()
        self.win.refresh()

    def bonus(self) -> None:
        got = crew_sim.pay_bonus(self.game)
        if not got["ok"]:
            self.win.toast(got["why"], "warn")
            return
        self.win.toast(f"A bonus went round the bridge: "
                       f"{got['cost']:,} credits.", "good")
        self.win.save()
        self.win.refresh()

    def shore_leave(self) -> None:
        got = crew_sim.shore_leave(self.game)
        if not got["ok"]:
            self.win.toast(got["why"], "warn")
            return
        if self.win.check_ending():
            return
        self.win.toast(got["text"], "good")
        self.win.save()
        self.win.refresh()

    def sign_on(self, count: int) -> None:
        got = lifespan_sim.sign_on(self.game, count)
        if not got.get("ok"):
            self.win.toast(got.get("why", "No."), "warn")
            return
        self.win.toast(f"{got['count']} signed on. The mess deck's average "
                       f"age is {got['mean']:.0f}, from {got['was']:.0f}.", "")
        self.win.save()
        self.refresh()

    # The long sleep is shared with the Ship screen, which means the panel
    # calls these two by name. Kept identical on purpose: one act, two doors.

    def sleep_crew(self, method_id: str, count: int) -> None:
        got = dormancy_sim.put_under(self.game, method_id, count)
        if not got.get("ok"):
            self.win.toast(got.get("why", "No."), "warn")
            return
        self.win.save()
        self.refresh()

    def wake_crew(self) -> None:
        got = dormancy_sim.bring_up(self.game)         # rolls and logs itself
        if not got.get("ok"):
            self.win.toast(got.get("why", "Nobody is under."), "warn")
            return
        body = [text for _kind, text in got["lines"]] or \
            ["They are all up, and none the worse."]
        self.win.dialog(f"Up after {got['days']} days", body,
                        [("Back to work", None)])
        self.win.save()
        self.refresh()

    def to_berths(self) -> None:
        """The berth board is the quay's, not the ship's, so it stays at the
        port — this is the door to it."""
        self.win.go("port")
        port = self.win.views.get("port")
        if port is not None:
            # The Port screen calls that tab "crew" and labels it "Berths".
            port.tab = "crew"
            port.refresh()


def empty_note(rows: list):
    """What the holes in the watch bill cost, or nothing if there are none."""
    holes = [r["name"] for r in rows if r["officer"] is None]
    if not holes:
        return label("Every station is held.", "note", "chloro")
    return label("Nobody holds " + ", ".join(h.lower() for h in holes)
                 + ". A station nobody holds is a bonus nobody gets.",
                 "note", "warn", wrap=True)
