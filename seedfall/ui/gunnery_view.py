"""The gunnery school, and the way into any gun on any hull you command.

The screen has three states and they are the three things a gunner does:

- **Pick.** The ten drills in the order a school teaches them, each saying
  what it is for, with the one you have not passed yet marked.
- **Read.** The brief: what is out there, what is wanted, and what is merely
  worth having. FreeSpace's briefing, and for the same reason — a gunner who
  walks into an action without knowing the objective is being tested on
  guessing.
- **Debrief.** What you actually did, directive by directive, with a rating.

And beside all that, the part that is not practice: **the seats on your own
ship**. Every armament fitted to the hull is a mounting somebody can sit
behind, and this is where a captain takes one over.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data import drills as table
from ..data import turrets as turret_data
from ..sim import drills as drill_sim
from ..sim import manning
from . import theme
from .view_base import WrapRow
from .widgets import Card, Panel, View, button, label, note


class GunneryView(View):
    """Practice, and the guns you actually have."""

    heading = "Gunnery"

    def __init__(self, win):
        super().__init__(win)
        #: Which drill is being read about, or None on the list.
        self.reading = None
        #: The last debrief, kept until the gunner leaves it.
        self.verdict = None

    # ── acts ───────────────────────────────────────────────────────────────

    def read(self, drill_id: str) -> None:
        self.reading = table.DRILL_BY_ID.get(drill_id)
        self.verdict = None
        self.refresh()

    def back(self) -> None:
        self.reading = None
        self.verdict = None
        self.refresh()

    def fly(self, drill) -> None:
        """Open the seat and run the drill in it."""
        from .turret_window import open_turret
        action = drill_sim.begin(drill, RNG(f"{self.game.seed}:{drill.id}"))
        open_turret(self.win, action, drill, on_done=self._done)

    def man(self, seat: dict) -> None:
        """Take over one of the ship's own mountings, against live traffic."""
        from .turret_window import open_turret
        action, why = manning.take(self.game, seat["mount"])
        if action is None:
            self.win.toast(why, "warn")
            return
        open_turret(self.win, action, None, on_done=self._done)

    def _done(self, action, drill) -> None:
        """The seat was left. Bank what the gun did, and show the debrief."""
        if drill is None:
            # A gun manned in a real engagement: what it took off the enemy
            # comes off the enemy in the battle, once (`manning.land`).
            got = manning.land(self.game, action,
                               getattr(self.game, "battle", None))
            if got.get("dealt"):
                self.win.toast(
                    f"{got['dealt']:,.0f} put into them by hand.", "good")
            from .widgets import defer
            defer(self.refresh)
            return
        if drill is not None:
            self.verdict = drill_sim.judge(action, drill)
            passed = dict(self.game.flags.get("drills_passed", {}) or {})
            if self.verdict["won"]:
                best = passed.get(drill.id, "")
                if not best or self.verdict["share"] > 0.0:
                    passed[drill.id] = self.verdict["rating"]
                self.game.flags["drills_passed"] = passed
        self.reading = drill
        from .widgets import defer
        defer(self.refresh)

    # ── the screen ─────────────────────────────────────────────────────────

    def build(self) -> None:
        self.head("Gunnery",
                  "The school, and every gun on the hull you command.")
        if self.verdict is not None:
            self._debrief()
            return
        if self.reading is not None:
            self._brief(self.reading)
            return
        self._seats()
        self._school()

    def _passed(self) -> dict:
        return dict(self.game.flags.get("drills_passed", {}) or {})

    def _school(self) -> None:
        self.col.addWidget(label("The school", "h2"))
        self.col.addWidget(note(
            "Ten actions, in the order somebody would teach them. Each one "
            "is a situation the Verge can put you in, run where nobody dies "
            "for getting it wrong."))
        passed = self._passed()
        rows = WrapRow(10)
        for drill in table.in_order():
            seat = turret_data.for_part(drill.seat)
            mark = passed.get(drill.id, "")
            body = [note(drill.teaches),
                    note(f"{seat.seat}  ·  practice for {drill.about}")]
            if mark:
                body.append(note(f"Passed — {mark}."))
            tile = Card(False)
            tile.add(label(f"{drill.rung}.  {drill.name}", "h3"), *body,
                     button("Read the brief",
                            lambda _=False, d=drill.id: self.read(d),
                            kind="flat"))
            rows.add(tile, 1)
        self.col.addWidget(rows)

    def _seats(self) -> None:
        """Every mounting on the ship, and the one you can take now."""
        seats = manning.seats(self.game)
        self.col.addWidget(label("Your own guns", "h2"))
        if not seats:
            self.col.addWidget(note(
                "Nothing on the hull can be worked by hand. Fit an armament "
                "at the shipyard and the seat behind it opens."))
            return
        self.col.addWidget(note(
            "Every armament fitted is a mounting somebody can sit behind. "
            "Take one and the ship's computer keeps the rest."))
        rows = WrapRow(10)
        for seat in seats:
            kind = seat["kind"]
            body = [note(kind.note),
                    note(f"traverse {kind.traverse:,.0f}°/s  ·  "
                         f"arc ±{kind.arc:,.0f}°  ·  "
                         + (f"{kind.muzzle_kms:,.1f} km/s"
                            if kind.muzzle_kms else "beam"))]
            tile = Card(False)
            tile.add(label(seat["name"], "h3"), *body,
                     button("Take the seat",
                            lambda _=False, s=seat: self.man(s),
                            kind="primary"))
            rows.add(tile, 1)
        self.col.addWidget(rows)

    def _brief(self, drill) -> None:
        self.col.addWidget(label(drill.name, "h2"))
        seat = turret_data.for_part(drill.seat)
        self.col.addWidget(note(
            f"{seat.seat}  ·  {drill.teaches}  ·  practice for {drill.about}"))
        lines = drill_sim.brief(drill)
        board = Panel("The brief")
        board.add(*[note(line) for line in lines if line])
        self.col.addWidget(board)
        self.col.addWidget(self.row(
            button("Take the seat", lambda: self.fly(drill), kind="primary"),
            button("Back to the school", self.back, kind="flat")))

    def _debrief(self) -> None:
        got = self.verdict
        tint = "chloro" if got["won"] else "warn"
        self.col.addWidget(label(f"{got['name']} — {got['rating']}", "h2"))
        said = label(
            "Exercise complete." if got["won"] else "Exercise called.", "h3")
        said.setStyleSheet(f"color: {theme.tint(tint)};")
        self.col.addWidget(said)
        board = Panel("The debrief")
        board.add(*[note(line) for line in drill_sim.lines(got)])
        self.col.addWidget(board)
        acts = [button("Run it again",
                       lambda: self.fly(table.DRILL_BY_ID[got["drill"]]),
                       kind="flat")]
        nxt = got.get("next")
        if nxt is not None and got["won"]:
            acts.append(button(f"On to {nxt.name}",
                               lambda d=nxt: self.read(d.id), kind="primary"))
        acts.append(button("Back to the school", self.back, kind="flat"))
        self.col.addWidget(self.row(*acts))

