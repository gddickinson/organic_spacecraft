"""The Concourse screen: everywhere people are, and everything they sell.

A concourse used to be a tab on the Port screen, which meant it was a fact
about a starport — so a habitat drum with a million people in it, a holding
of your own and a power's settlement on the ground all offered a crew exactly
nothing. `sim/places.py` fixed the model; this is the room.

**The place picker at the top is the screen.** Everything under it is read
against whichever place is selected, so walking from the quay to the drum in
orbit above it changes the shelves, the prices, the clinic's catalogue and
whether anybody here will admit to fitting a reflex lace. Four tabs:

- **Shops** — the chandler, the counters, the offices, the papers, the way
  about, and whatever the back room has.
- **Board and bed** — eating, lodging, and a night ashore for the watch.
- **Clinic** — what can be done to a person: care, surgery, grafts, years,
  cold storage, hardware and the germ line, one officer at a time.
- **The evening** — arts, sport, entertainment, the houses, and the other
  concourse.
- **Who runs this** — the government, the law level, who holds the ground,
  how hard it is policed, and what any of them currently has on you. Read
  off eight modules that were only ever reachable from the Law screen,
  which is about your charges rather than about where you are standing.

The screen decides nothing. `sim/shore.py` says what is open and what it
costs, `sim/clinic.py` says what can be done to somebody and quotes the odds,
and every button calls back into one of them. The price shown is the price
charged, which is this project's oldest rule.
"""

from __future__ import annotations

from ..sim import clinic as clinic_sim
from ..sim import places as places_sim
from . import (concourse_body, concourse_law, concourse_night,
               concourse_shops, place_scene)
from .widgets import Panel, TabBar, View, button, label, note

TABS = (("shops", "Shops"), ("board", "Board and bed"),
        ("clinic", "Clinic"), ("evening", "The evening"),
        ("rule", "Who runs this"))


class ConcourseView(View):
    """Everything a person can spend money on, wherever the hull is."""

    def __init__(self, win):
        super().__init__(win)
        self.tab = "shops"
        #: Which place is being walked. Kept as an id so a refresh after a
        #: purchase, a night ashore or thirty days in a surgery finds the
        #: same concourse rather than jumping back to the quay.
        self.place_id: str | None = None
        #: Whose body the Clinic tab is looking at.
        self.patient: int | None = None

    # ── the screen ─────────────────────────────────────────────────────────

    def _walk(self, place) -> None:
        """Open the Afoot screen on this place (`ui/afoot_view.py`)."""
        view = self.win.views.get("afoot")
        if view is not None:
            view.site_key = f"place:{place.id}"
        self.win.go("afoot")

    def build(self) -> None:
        g = self.game
        rows = places_sim.in_system(g)
        place = self.place()
        if place is None:
            self.head("The concourse", "nowhere to walk into")
            self.col.addWidget(Panel("Nobody is out here").add(
                note("There is no port in this system, no holding of yours, "
                     "and nobody else has put anybody on the ground. A "
                     "concourse is other people; there are none."),
                button("Back to the chart", lambda: self.win.go("map"),
                       kind="primary")))
            return
        self.head(place.name,
                  f"{place.kind_name} · {places_sim.population(place)}")
        if len(rows) > 1:
            self._picker(rows, place)
        # The place, drawn: what it is, what is open on it, and who is on it.
        # A class-A capital of ten million and a shed on a frontier rock used
        # to be the same screen with different lists.
        self.col.addWidget(place_scene.PlaceScene(g, place, 160))
        # Wrapped, not a `note`: a plain note does not fold, so its whole
        # sentence becomes the screen's minimum width and the Concourse ran
        # seven pixels past its column at 1040.
        self.col.addWidget(label(place_scene.legend(g, place), "note",
                                 wrap=True))
        for line in places_sim.says(place):
            self.col.addWidget(label(line, "note", wrap=True))
        if not place.here:
            self.col.addWidget(label(
                "The hull is not alongside. Prices and shelves are what they "
                "would be; nothing can be bought until you are there.",
                "note", "warn", wrap=True))
        elif place.kind != "ship":
            self.buttons(button("Walk it", lambda: self._walk(place),
                                tip="Afoot: go ashore on foot, and see it."))
        tabs = TabBar(list(TABS), self.tab)
        tabs.changed.connect(self._switch)
        self.col.addWidget(tabs)

        if self.tab == "board":
            concourse_night.board(self, place)
        elif self.tab == "clinic":
            concourse_body.build(self, place)
        elif self.tab == "evening":
            concourse_night.evening(self, place)
        elif self.tab == "rule":
            concourse_law.build(self, place)
        else:
            concourse_shops.build(self, place)

    def _picker(self, rows, place) -> None:
        """Every place in this system, so a crew can walk somewhere else."""
        bar = TabBar([(p.id, _short(p)) for p in rows], place.id)
        bar.changed.connect(self.go_place)
        self.col.addWidget(bar)

    def _switch(self, tid: str) -> None:
        self.tab = tid
        self.refresh()

    # ── where and who ──────────────────────────────────────────────────────

    def place(self):
        """The place being walked: the one chosen, else where the hull is."""
        rows = places_sim.in_system(self.game)
        if not rows:
            return None
        found = next((p for p in rows if p.id == self.place_id), None)
        if found is None:
            found = places_sim.current(self.game) or rows[0]
            self.place_id = found.id
        return found

    def go_place(self, place_id: str) -> None:
        self.place_id = place_id
        self.refresh()

    def officer(self):
        """Whose body the Clinic tab is looking at."""
        from ..sim import roster as roster_sim
        rows = roster_sim.active(self.game)
        if not rows:
            return None
        found = next((o for o in rows if o.id == self.patient), None)
        if found is None:
            found = rows[0]
            self.patient = found.id
        return found

    def see_patient(self, officer) -> None:
        self.patient = getattr(officer, "id", None)
        self.refresh()

    # ── the acts, every one of them the sim's ──────────────────────────────

    def can_trade(self, place) -> tuple:
        """Whether anything can actually be bought here, and why not."""
        if not place.here:
            return False, "The hull is not alongside."
        return True, ""

    def treat(self, place, officer, treatment_id: str, skill: str = "") -> None:
        got = clinic_sim.buy(self.game, place, officer, treatment_id, skill)
        if not got["ok"]:
            self.win.toast(got["why"], "warn")
            return
        self.win.toast(got["text"], "good" if got["went"] else "warn")
        if self.win.check_ending():
            return
        self.win.save()
        self.win.refresh()

    def freeze(self, place, officer, treatment_id: str) -> None:
        got = clinic_sim.freeze(self.game, place, officer, treatment_id)
        if not got["ok"]:
            self.win.toast(got["why"], "warn")
            return
        self.patient = None
        self.win.toast(f"{got['officer'].name} is on ice.", "")
        self.win.save()
        self.win.refresh()

    def thaw(self, place, officer_id: int) -> None:
        got = clinic_sim.thaw(self.game, place, officer_id)
        if not got["ok"]:
            self.win.toast(got["why"], "warn")
            return
        self.win.toast(f"{got['officer'].name} is up, after "
                       f"{got['years']:.1f} years.", "good")
        self.win.save()
        self.win.refresh()


def _short(place) -> str:
    """A place's name, short enough for a tab."""
    name = place.name
    return name if len(name) <= 16 else name[:15] + "…"
