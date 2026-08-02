"""Hulls the captain has decided are enemies, and remembers deciding.

**A contact's hostility was derived and only derived.** `sim/traffic` builds
each hull with `hostile=ERRANDS[errand][2]` — a raider is hostile, a freighter
is not — and `sim/track` copies that onto the `Contact` a screen shows. So the
game had an opinion about who your enemies were and the captain had none, which
is the wrong way round for the one thing a pilot is certain about.

**Marking is a player act, so it has to be stored.** A `Contact` is rebuilt
from nothing on every call and a `Hull` with it: both are pure in the system,
the day and the sector's state, which is what makes the Kestrel you hailed
yesterday the same Kestrel today. Writing `hostile = True` onto either would
last exactly until the next redraw. The mark lives here instead, on the
chronicle, and goes into the save with everything else.

**One door, and it is `traffic`.** The derived answer and the captain's mark
have to meet in exactly one place or a screen will disagree with a board about
the same hull. They meet where `hostile` is computed, so everything downstream
— the cross on the orrery, the top of the readiness board, the count in the
mesh panel, `traffic.hostiles`, `present_factions` — follows without knowing
this module exists.

**Marking costs nothing.** It is a note to yourself, not a declaration: no
standing moves, nothing is told. `sim/allegiance.price_attack` prices *moving
against* a power and is charged when you denounce one; what a mark buys is
that the sector's screens agree with you about who you are watching.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register


@register
@dataclass
class Grudges:
    """Hull ids the captain has marked, oldest first.

    A list rather than a set because a save is JSON and a set is not, and
    because the order is the order they were marked, which is worth keeping.
    """

    hulls: list = field(default_factory=list)


def ensure(game) -> Grudges:
    """The store, made on first use so older saves keep working."""
    if getattr(game, "hostiles_state", None) is None:
        game.hostiles_state = Grudges()
    return game.hostiles_state


def is_marked(game, hull_id: str) -> bool:
    """Has the captain called this hull an enemy?"""
    if not hull_id:
        return False
    return hull_id in ensure(game).hulls


def marked(game) -> list:
    """Every hull id under a mark, in the order they were marked."""
    return list(ensure(game).hulls)


def mark(game, hull_id: str) -> bool:
    """Call a hull an enemy. Returns whether anything changed."""
    if not hull_id or is_marked(game, hull_id):
        return False
    ensure(game).hulls.append(hull_id)
    return True


def clear(game, hull_id: str) -> bool:
    """Take the mark off. Returns whether anything changed."""
    state = ensure(game)
    if hull_id not in state.hulls:
        return False
    state.hulls.remove(hull_id)
    return True


def note(game, contact) -> str:
    """One line for a screen about what a mark would mean."""
    hull_id = getattr(contact, "hull_id", "") or ""
    name = getattr(contact, "name", "It")
    if getattr(contact, "kind", "") != "hull":
        return f"{name} is not a hull. There is nobody aboard to be an enemy."
    if is_marked(game, hull_id):
        return (f"{name} is marked. Every chart and board in the sector reads "
                f"her as an enemy.")
    return (f"Marking {name} costs nothing and tells nobody — it puts her on "
            f"the charts as an enemy and keeps her there.")
