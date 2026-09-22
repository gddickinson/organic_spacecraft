"""Assembling a deck plan: painted decks in, a walkable plan out.

The blueprints (`sim/afoot_hullplan`, `afoot_ringplan`, `afoot_structplan`,
`afoot_groundplan`) paint each deck as regions on a `afoot_blocks.Sheet`: the
shape of the thing and what is where in it. This turns those sheets into a
plan a party can walk:

- every sheet is **built** — walls where regions meet and where anything
  meets the outside, one door per room, every room reachable;
- doors take the **hull's own form**: a sphincter on anything grown or
  xeno, a bulkhead door on anything welded, and a room that asked for a lock
  gets one;
- **lifts** are paired: a shaft is two squares, the lift down on one deck
  arriving at the lift up on the deck below;
- every room is **furnished** from its kind (`sim/afoot_furnish`).

`Want` is a space a program asks for — its kind, name, the venue or fitting
it is, how much floor it needs and where along the structure it belongs.
"""

from __future__ import annotations

from dataclasses import dataclass

from .afoot_state import Deck
from . import afoot_furnish

#: Door kind by style: grown and xeno structures open with a sphincter.
HATCHED = ("grown", "xeno")


@dataclass
class Want:
    """A space a program asks for."""

    kind: str
    name: str = ""
    venue: str = ""
    part: str = ""
    #: A lock on its door, 0 for none (`data/afoot_things.LOCKS`).
    lock: int = 0
    #: Squares of floor it needs.
    area: int = 0
    #: Where along the structure it belongs: bow +1 to stern −1 on a hull,
    #: a ring or a band on a station — the blueprint says which.
    zone: float = 0.0


@dataclass
class Laid:
    """What a blueprint hands back, ready to be put on a `Walk`."""

    decks: list
    rooms: list
    things: list
    #: (deck, x, y) of the way in, where the party is set down.
    entry: tuple


class Ids:
    """Ids for rooms and things, unique across every deck of one plan."""

    def __init__(self, start: int = 1):
        self.n = start

    def __call__(self) -> int:
        self.n += 1
        return self.n - 1


@dataclass
class Painted:
    """One deck as a blueprint left it: the sheet, its name, and its air."""

    sheet: object
    name: str
    style: str
    air: bool = True
    outside_air: bool = True


def assemble(rng, painted: list, entry_kinds=("airlock", "gangway")) -> Laid:
    """Build every painted deck, pair the lifts, furnish every room."""
    ids = Ids()
    decks, rooms, things = [], [], []
    for index, deck_art in enumerate(painted):
        rows, laid, placed = deck_art.sheet.build(index, ids, deck_art.style)
        deck = Deck(name=deck_art.name, rows=rows,
                    seen=["0" * len(rows[0]) for _ in rows],
                    style=deck_art.style, air=deck_art.air,
                    outside_air=deck_art.outside_air)
        decks.append(deck)
        wants = {room.id: want for room, want in laid}
        for t in placed:
            if t.kind == "door":
                if deck_art.style in HATCHED:
                    t.kind = "hatch"
                want = wants.get(t.room)
                if want is not None and want.lock:
                    t.state, t.lock = "locked", want.lock
        things += placed
        for room, _want in laid:
            rooms.append(room)
            doors = [(t.x, t.y) for t in placed
                     if t.kind in ("door", "hatch") and _beside(room, t)]
            things += afoot_furnish.furnish(rng, deck, room, ids, doors)
    _pair_lifts(decks, things)
    entry = _entry(decks, things, entry_kinds)
    return Laid(decks, rooms, things, entry)


def _beside(room, t) -> bool:
    return any(room.holds(t.deck, t.x + dx, t.y + dy)
               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def _pair_lifts(decks: list, things: list) -> None:
    """Each lift down arrives at the lift up of the same shaft on the next
    deck that has one — so a hub's spine can run a lift straight to either
    of its rings. The note is `down:<shaft>` or `up:<shaft>`."""
    ups: dict = {}
    for t in things:
        if t.kind == "lift" and t.note.startswith("up"):
            ups.setdefault(t.note.split(":")[-1], []).append(t)
    for t in things:
        if t.kind != "lift" or not t.note.startswith("down"):
            continue
        shaft = t.note.split(":")[-1]
        below = sorted((u for u in ups.get(shaft, ()) if u.deck > t.deck
                        and u.link < 0), key=lambda u: u.deck)
        if below:
            t.link, below[0].link = below[0].id, t.id
    by_id = {t.id: t for t in things}
    for t in things:
        if t.kind == "lift":
            other = by_id.get(t.link)
            t.name = (f"lift to {decks[other.deck].name.lower()}" if other
                      else "a dead lift")


def _entry(decks, things, kinds) -> tuple:
    """Where the party comes aboard: beside the first way in on deck 0."""
    door = next((t for t in things if t.kind in kinds and t.deck == 0),
                None) or next((t for t in things if t.kind in kinds), None)
    if door is None:
        return (0, 1, 1)
    deck = decks[door.deck]
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1),
                   (1, -1), (-1, 1)):
        x, y = door.x + dx, door.y + dy
        if deck.at(x, y) in (".", ",", "_"):
            return (door.deck, x, y)
    return (door.deck, door.x, door.y)
