"""The Afoot screen: the deck on the left, the party and its choices on the right.

With nobody out it is the start page (`ui/afoot_start.py`): where, who, and
how armed. With a party out it is the walk:

- **the deck** (`ui/afoot_canvas.py`) — left-click a square to walk there,
  or a person to shoot them if they are hostile and to go up to them if
  not; right-click to go up to whatever is there. Arrows and Home/End/PgUp/
  PgDn step, Tab takes the next person in hand, Space ends the turn;
- **the column** (`ui/afoot_panels.py`) — the party, what the one in hand
  can do from where they stand with the odds on every button, everybody in
  sight with a shot and a word, the goals, and what just happened;
- **a conversation** (`ui/afoot_talk_panel.py`) when somebody is being
  talked to, with the counter they stand behind when business is done.

Every press is one door in `sim/afoot`; the screen keeps only what it is
looking at (who is being talked to, what they last said) and decides
nothing. When a walk ends the start page comes back with what it came to.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..sim import afoot, afoot_map, afoot_people
from ..sim.afoot_state import actor, actor_at, party
from . import afoot_panels, afoot_start, afoot_talk_panel
from .afoot_canvas import AfootCanvas
from .view_base import Pane, View
from .widgets import Pill, TabBar, defer, label


def weight_name(deck) -> str:
    """The weight on a deck's floor, in words: weightless, or so many
    gravities, and whether it comes from spin."""
    if deck.g < afoot_map.WEIGHTLESS:
        return "weightless"
    return f"{deck.g:.2g} g" + (" · spun" if deck.wrap else "")


class AfootView(View):
    """Walking a deck."""

    fills = True

    def __init__(self, win):
        super().__init__(win)
        self.col.setContentsMargins(22, 14, 22, 10)
        self.canvas = None
        #: The start page's choices.
        self.site_key: str | None = None
        self.keys: list = ["captain"]
        self.arms_mode = "legal"
        #: How the party is to get across (`sim/crossing`), or None for the
        #: way the crew would take unasked.
        self.across: str | None = None
        #: Who is being talked to, what they have said, and which of their
        #: counters is open.
        self.talking: int | None = None
        self.said: list = []
        self.open_counter = ""

    # ── the screen ────────────────────────────────────────────────────────

    def build(self) -> None:
        walk = afoot.current(self.game)
        if walk is None:
            self.canvas = None
            afoot_start.build(self)
            self.col.addStretch(1)
            return
        who = actor(walk, walk.selected) or next(iter(party(walk)), None)
        deck = walk.decks[walk.viewing]
        head = QWidget()
        h = QHBoxLayout(head)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(label(f"{walk.name} — {deck.name}", "h2"))
        h.addWidget(Pill(walk.mode, "warn" if walk.mode == "action"
                         else "chloro"))
        h.addWidget(Pill(weight_name(deck), "lumen" if deck.g
                         < afoot_map.WEIGHTLESS else "dim"))
        h.addWidget(label(f"round {walk.round} · "
                          f"{walk.seconds // 60} min", "note"))
        h.addStretch(1)
        self.col.addWidget(head)
        if len(walk.decks) > 1:
            tabs = TabBar([(str(i), d.name) for i, d in enumerate(walk.decks)],
                          str(walk.viewing))
            tabs.changed.connect(lambda t: self._deck(int(t)))
            self.col.addWidget(tabs)
        body = QWidget()
        across = QHBoxLayout(body)
        across.setContentsMargins(0, 0, 0, 0)
        across.setSpacing(12)
        self.canvas = AfootCanvas(self)
        across.addWidget(self.canvas, 3)
        side = Pane(margins=(0, 0, 8, 10))
        side.setObjectName("afoot_side")
        side.setMinimumWidth(300)
        for part in self._side(walk, who):
            if part is not None:
                side.col.addWidget(part)
        side.col.addStretch(1)
        across.addWidget(side, 2)
        self.col.addWidget(body, 1)

    def _side(self, walk, who) -> list:
        parts = [afoot_panels.controls(self, walk),
                 afoot_panels.latest(walk),
                 afoot_panels.party_strip(self, walk)]
        other = actor(walk, self.talking) if self.talking is not None else None
        if other is not None and who is not None:
            parts.append(afoot_talk_panel.conversation(self, walk, who, other))
            if self.open_counter:
                parts.append(afoot_talk_panel.counter(self, walk, other,
                                                      self.open_counter))
        if who is not None:
            parts.append(afoot_panels.in_hand(self, walk, who))
            parts.append(afoot_panels.in_sight(self, walk, who))
        parts.append(afoot_panels.goals(walk))
        parts.append(afoot_panels.log(walk))
        return parts

    # ── the start page ────────────────────────────────────────────────────

    def pick_site(self, key: str) -> None:
        self.site_key, self.across = key, None
        self.refresh_later()

    def toggle(self, key: str) -> None:
        if key in self.keys:
            self.keys = [k for k in self.keys if k != key]
        elif len(self.keys) < afoot_people.PARTY_MOST:
            self.keys = self.keys + [key]
        self.refresh_later()

    def set_across(self, way: str) -> None:
        self.across = way
        self.refresh_later()

    def set_arms(self, mode: str) -> None:
        self.arms_mode = mode
        self.refresh_later()

    def go_afoot(self) -> None:
        got = afoot.begin(self.game, self.site_key, list(self.keys),
                          self.arms_mode, self.across)
        if not got.get("ok"):
            self.win.toast(got.get("why", "Nobody can go."), "warn")
            return
        self._after(got)

    # ── on the deck ───────────────────────────────────────────────────────

    def _walk(self):
        return afoot.current(self.game)

    def _who(self):
        walk = self._walk()
        return actor(walk, walk.selected) if walk else None

    def pick(self, actor_id: int) -> None:
        afoot.select(self.game, actor_id)
        self.refresh_later()

    def next_member(self) -> None:
        walk = self._walk()
        if walk is None:
            return
        standing = [a for a in party(walk, standing=True)]
        if not standing:
            return
        ids = [a.id for a in standing]
        at = ids.index(walk.selected) if walk.selected in ids else -1
        self.pick(ids[(at + 1) % len(ids)])

    def _deck(self, deck: int) -> None:
        afoot.view_deck(self.game, deck)
        self.refresh_later()

    def clicked(self, x: int, y: int) -> None:
        """A square pressed: shoot a hostile, go up to a person, walk there."""
        walk, who = self._walk(), self._who()
        if walk is None or who is None:
            return
        other = actor_at(walk, walk.viewing, x, y)
        seen = self.canvas.seen_now() if self.canvas is not None else set()
        if other is not None and other.side == "npc" and (x, y) in seen:
            from ..sim import afoot_talk
            if other.hostile:
                self.attack(other.id)
            elif afoot_talk.can_talk(walk, who, other)[0]:
                self.talk_to(other.id)
            else:
                self.approach(x, y)
            return
        if walk.viewing != who.deck:
            self.win.toast(f"{who.name} is on another deck.", "warn")
            return
        self._act(afoot.move(self.game, who.id, x, y))

    def approach(self, x: int, y: int) -> None:
        """Go up to whatever is on a square, rather than onto it."""
        walk, who = self._walk(), self._who()
        if walk is None or who is None or walk.viewing != who.deck:
            return
        from ..sim import afoot_map
        route = afoot_map.path(walk, who, x, y, near=True)
        if route:
            self._act(afoot.move(self.game, who.id, *route[-1]))

    def step(self, dx: int, dy: int) -> None:
        who = self._who()
        if who is None:
            return
        self._act(afoot.move(self.game, who.id, who.x + dx, who.y + dy))

    def attack(self, target_id: int) -> None:
        who = self._who()
        if who is None:
            return
        self._act(afoot.attack(self.game, who.id, target_id))

    def burst(self, target_id: int) -> None:
        who = self._who()
        if who is not None:
            self._act(afoot.attack(self.game, who.id, target_id, burst=True))

    def suppress(self, target_id: int) -> None:
        who = self._who()
        if who is not None:
            self._act(afoot.suppress(self.game, who.id, target_id))

    def throw(self, target_id: int, grenade: str) -> None:
        who = self._who()
        if who is not None:
            self._act(afoot.throw(self.game, who.id, target_id, grenade))

    def do_act(self, act) -> None:
        who = self._who()
        if who is None:
            return
        got = afoot.act(self.game, who.id, act.id, act.target)
        if got.get("talk", -1) >= 0:
            self.talk_to(got["talk"])
            return
        self._act(got)

    def end_turn(self) -> None:
        self._act(afoot.end_turn(self.game))

    def surrender(self) -> None:
        self._act(afoot.surrender(self.game))

    # ── talk ──────────────────────────────────────────────────────────────

    def talk_to(self, npc_id: int) -> None:
        who = self._who()
        if who is None:
            return
        self.talking, self.said, self.open_counter = npc_id, [], ""
        got = afoot.talk(self.game, who.id, npc_id, "greet")
        if got.get("line"):
            self.said.append(got["line"])
        elif not got.get("ok"):
            self.talking = None
            self.win.toast(got.get("why", "They will not talk."), "warn")
        self.refresh_later()

    def say(self, topic: str) -> None:
        who = self._who()
        if who is None or self.talking is None:
            return
        got = afoot.talk(self.game, who.id, self.talking, topic)
        if not got.get("ok"):
            self.win.toast(got.get("why", "No."), "warn")
        for key in ("line", "text"):
            if got.get(key) and (not self.said or self.said[-1] != got[key]):
                self.said.append(got[key])
        if got.get("goes_to"):
            self.open_counter = got["goes_to"]
            if got["goes_to"] == "despatches":
                self.win.go("despatches")
                return
        self._act(got, quiet=True)

    def stop_talking(self) -> None:
        self.talking, self.said, self.open_counter = None, [], ""
        self.refresh_later()

    def counter_act(self, fn, place, what) -> None:
        """A counter's own door, pressed from the deck."""
        got = fn(self.game, place, what)
        if not got.get("ok"):
            self.win.toast(got.get("why", "No."), "warn")
        elif got.get("text"):
            self.said.append(got["text"])
        self._act(got, quiet=True)

    def hire(self, officer) -> None:
        from ..sim import crew
        self.counter_act(lambda g, _p, o: crew.hire(g, o), None, officer)

    def to_concourse(self, tab: str) -> None:
        walk = self._walk()
        view = self.win.views.get("concourse")
        if view is not None and walk is not None:
            view.place_id, view.tab = walk.place_id, tab
        self.win.go("concourse")

    def to_port(self, tab: str) -> None:
        view = self.win.views.get("port")
        if view is not None:
            view.tab = tab
        self.win.go("port")

    # ── after every press ─────────────────────────────────────────────────

    def _act(self, got: dict, quiet: bool = False) -> None:
        if not got.get("ok") and got.get("why") and not quiet:
            self.win.toast(got["why"], "warn")
        from . import soundmap
        soundmap.afoot(self.win, got, getattr(self.game, "afoot", None))
        hail = next((e for e in got.get("events", []) or []
                     if e.get("kind") == "hail"), None)
        if hail is not None and afoot.current(self.game) is not None:
            # Somebody walked up and spoke first: the conversation is open.
            afoot.select(self.game, hail["to"])
            self.talking, self.open_counter = hail["who"], ""
            self.said = ["“Papers. All of you. What's that you're carrying?”"]
        self._after(got)

    def _after(self, got: dict) -> None:
        walk = getattr(self.game, "afoot", None)
        if walk is None or walk.over:
            self.talking, self.said, self.open_counter = None, [], ""
            self.game.save()
        defer(self.win.refresh)
