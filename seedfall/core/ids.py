"""Identities that survive a restart.

Fifteen modules each kept ``_uid = itertools.count(1)`` — a counter that
lives in the *process*. A chronicle saved on day 900 and resumed in a fresh
process started every counter at 1 again, so the first hull laid down after
a reload was issued uid 1, which was the flagship's. Measured: transfer the
flag to it, save, load, and the fleet read ``[('Second Hull', 1),
('Second Hull', 1)]`` — the original flagship gone, because the relink that
makes ``game.ship`` the same object as its fleet entry matched the wrong one.
Contracts, settlements and memories collided the same way over two years.

So there is one counter per *kind* here, and a chronicle carries them:
`snapshot` is written into the save (``Game.ids``), and `restore` puts the
counters back **no lower than one past anything the save actually holds** —
which also mends a save written before the counters were kept at all.

Two id spaces that used to be told apart by an offset are one space now:
commissions drew contract ids from 9000 and a venture's rearming shock added
90000 to a venture id. Drawing both from the kind they belong to makes the
offsets unnecessary rather than merely larger.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass

#: The book of the chronicle most recently opened, loaded or advanced. Each
#: `Game` owns its own book (`Game.ids`); this is only where a call that has
#: no game in hand — making a ship, an officer, a memory — draws from.
_NEXT: dict[str, int] = {}

#: kind → (class name, field) — where each kind's ids live in a saved game,
#: so `observed` can find the largest one actually in use.
KINDS: dict[str, tuple[str, str]] = {
    "ship": ("Ship", "uid"),
    "officer": ("Officer", "id"),
    "colony": ("Colony", "id"),
    "contract": ("Contract", "id"),
    "shock": ("Shock", "id"),
    "venture": ("Venture", "id"),
    "memory": ("Memory", "id"),
    "settlement": ("Settlement", "id"),
    "dig": ("Dig", "id"),
    "expedition": ("Expedition", "id"),
    "transit": ("Transit", "id"),
    "build": ("BuildJob", "id"),
    "rumour": ("Rumour", "id"),
    "instar": ("Instar", "id"),
    "nemesis": ("Nemesis", "id"),
    # Innovation 5, freight lines: a trading house's lines and its masters.
    "line": ("FreightLine", "id"),
    "master": ("Master", "id"),
}
_BY_CLASS = {cls: (kind, attr) for kind, (cls, attr) in KINDS.items()}


def bind(book: dict) -> dict:
    """Make this chronicle's book the one a game-less call draws from.

    **Per chronicle, not per process.** The counters used to be process
    globals that `new_game` never reset, and ids reach the dice
    (`game.rng(f"instar-{id}")`): the same seed played differently after
    "Begin again" than in a fresh launch, and a check ran 153 days alone and
    151 after another suite. `new_game`, `load_game` and every
    `advance_days` bind the game they are about.
    """
    global _NEXT
    _NEXT = book
    return book


def next_id(kind: str, game=None) -> int:
    """A fresh id of this kind, never issued before in this chronicle —
    from `game`'s own book when the caller has one, else the bound book."""
    book = getattr(game, "ids", None) if game is not None else None
    if not isinstance(book, dict):
        book = _NEXT
    n = book.get(kind, 1)
    book[kind] = n + 1
    return n


def snapshot() -> dict[str, int]:
    """The bound book's counters, as they stand."""
    return dict(_NEXT)


def observed(root) -> dict[str, int]:
    """The largest id of each kind anywhere in a (decoded) game."""
    top: dict[str, int] = {}
    seen: set[int] = set()
    stack = [root]
    while stack:
        obj = stack.pop()
        if isinstance(obj, (list, tuple, set)):
            stack.extend(obj)
            continue
        if isinstance(obj, dict):
            stack.extend(obj.values())
            continue
        if not is_dataclass(obj) or isinstance(obj, type) or id(obj) in seen:
            continue
        seen.add(id(obj))
        mark = _BY_CLASS.get(type(obj).__name__)
        if mark:
            value = getattr(obj, mark[1], None)
            if isinstance(value, int):
                top[mark[0]] = max(top.get(mark[0], 0), value)
        for f in fields(obj):
            if not f.metadata.get("transient"):
                stack.append(getattr(obj, f.name, None))
    return top


def restore(saved: dict | None, root=None) -> dict:
    """A loaded chronicle's book: never below what was saved, and never at
    or below an id the chronicle already holds — which also mends a save
    written before the counters travelled with it."""
    book = {k: int(v) for k, v in (saved or {}).items()}
    seen = observed(root) if root is not None else {}
    for kind in set(book) | set(seen):
        book[kind] = max(book.get(kind, 1), seen.get(kind, 0) + 1)
    return book
