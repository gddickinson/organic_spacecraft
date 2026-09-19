"""The research tree's cards, kept between refreshes and changed in place.

**The tree was rebuilt from nothing on every click.** Sixty-two cards of four
or five labels each, three hundred widgets, each one made, styled and laid out
again whenever anything on the window changed — measured at 242 ms a refresh
on the Research screen, of which the Python building them was 32 ms: the rest
was Qt styling and laying out widgets identical to the ones it had just
thrown away. Choosing a project, which changes one card, cost the
same as opening the screen.

Now each branch's tree is built once and kept. A refresh asks every card for
its state (known, open, or what it still needs) and replaces only the cards
whose state moved; a branch visited before is shown again rather than made
again. And the technologies already known fold into one line by default —
in a long chronicle they are most of the tree, and a card that says "known"
fifty times is not information.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QSizePolicy, QVBoxLayout, QWidget

from ..data.tech import TECH, TECH_BY_ID
from ..sim import research as research_sim
from . import widgets
from .widgets import Panel, button, label

COLS = 3


def state(game, t) -> tuple:
    """Everything about one technology that its card shows."""
    done = t.id in game.research.unlocked
    open_now = research_sim.can_research(t.id, game.research.unlocked)
    missing = tuple(r for r in t.reqs if r not in game.research.unlocked)
    return done, open_now, missing


class TechTree(QWidget):
    """One branch of the tree (or all of it), as cards that update in place."""

    def __init__(self, view, branch: str):
        super().__init__()
        self.view = view
        self.branch = branch
        self.show_known = False
        self._ids: list[str] = []
        self._cards: dict[str, tuple] = {}     # id -> (state, card)
        self._hints = widgets.HINTS
        down = QVBoxLayout(self)
        down.setContentsMargins(0, 0, 0, 0)
        down.setSpacing(10)
        self._known = Panel()
        self._known_text = label("", "", "dim", wrap=True)
        self._known_btn = button("Show them as cards", self._flip_known,
                                 kind="flat")
        self._known.add(self._known_text)
        self._known.add_buttons(self._known_btn)
        down.addWidget(self._known)
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(12)
        for c in range(COLS):
            self._grid.setColumnStretch(c, 1)
        down.addWidget(self._grid_host)

    def _in_branch(self) -> list:
        techs = [t for t in TECH if self.branch in ("all", t.branch)]
        techs.sort(key=lambda t: (t.tier, t.name))
        return techs

    def sync(self, game) -> int:
        """Bring the cards up to date with the game. Returns how many cards
        had to be made — none, on a refresh where nothing changed."""
        techs = self._in_branch()
        known = [t for t in techs if t.id in game.research.unlocked]
        shown = [t.id for t in techs
                 if self.show_known or t.id not in game.research.unlocked]
        self._say_known(known)
        if shown != self._ids or self._hints != widgets.HINTS:
            return self._rebuild(game, shown)
        made = 0
        for i, tid in enumerate(shown):
            now = state(game, TECH_BY_ID[tid])
            was, card = self._cards[tid]
            if now != was:
                self._replace(i, tid, card, now)
                made += 1
        return made

    def _say_known(self, known: list) -> None:
        self._known.setVisible(bool(known))
        names = " · ".join(t.name for t in known)
        self._known_text.setText(
            f"Known — {len(known)}: {names}" if not self.show_known
            else f"{len(known)} known, shown as cards below.")
        self._known_btn.setText("Fold them away" if self.show_known
                                else "Show them as cards")

    def _flip_known(self) -> None:
        self.show_known = not self.show_known
        # Through the screen's own refresh, deferred like every rebuild: it
        # re-measures the scroll area, which a bare `sync` would not.
        self.view.refresh_later()

    def _rebuild(self, game, shown: list) -> int:
        for _state, card in self._cards.values():
            self._grid.removeWidget(card)
            self.view.park(card)
        self._cards = {}
        for i, tid in enumerate(shown):
            self._place(i, tid, state(game, TECH_BY_ID[tid]))
        self._ids = list(shown)
        self._hints = widgets.HINTS
        return len(shown)

    def _replace(self, i: int, tid: str, old, now: tuple) -> None:
        self._grid.removeWidget(old)
        self.view.park(old)
        self._place(i, tid, now)

    def _place(self, i: int, tid: str, now: tuple) -> None:
        card = self.view._card(TECH_BY_ID[tid])
        # Cards hold wrapped text, so let them shrink rather than demand their
        # natural width — otherwise the last column is clipped off.
        card.setSizePolicy(QSizePolicy.Policy.Ignored,
                           QSizePolicy.Policy.MinimumExpanding)
        self._grid.addWidget(card, i // COLS, i % COLS)
        if self.isVisible():
            card.show()
        self._cards[tid] = (now, card)
