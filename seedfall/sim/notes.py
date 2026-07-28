"""Field notes: what the ground told you, kept.

A recovered note used to be a string in `expedition.lore`, shown once in the
report dialog and lost with the expedition object. Nothing stored it, nothing
consumed it, and the reward table valued it at zero — so three feature options
existed to print a sentence and take it away again.

A note is now filed against the `Game` with where and when it was found, so the
codex can show it, and it is evidence on an inquiry track, so going down and
reading the room is worth doing.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.save import register
from ..data.fieldnotes import NOTES, NOTES_BY_ID
from . import inquiry
from . import research as research_sim


@register
@dataclass
class Filed:
    """One note, and the circumstances it came out of."""
    note_id: str
    body: str
    system: str
    day: int

    @property
    def definition(self):
        return NOTES_BY_ID.get(self.note_id)


def held(game) -> list:
    if getattr(game, "field_notes", None) is None:
        game.field_notes = []
    return game.field_notes


def have(game, note_id: str) -> bool:
    return any(f.note_id == note_id for f in held(game))


def unfound(game) -> list:
    """Notes still out there. Drawn from so a party rarely repeats itself."""
    return [n for n in NOTES if not have(game, n.id)]


def draw(game, rng):
    """Pick a note this party could plausibly bring back."""
    pool = unfound(game) or NOTES
    return rng.pick(pool)


def file(game, note_id: str, body: str, system: str) -> dict:
    """Keep it, and count it. Returns what it was worth.

    A note already on the shelf is still worth reading — half, for the
    corroboration — but it is not filed twice.
    """
    note = NOTES_BY_ID.get(note_id)
    if note is None:
        return {"ok": False, "why": "No such note."}
    duplicate = have(game, note_id)
    worth = note.worth * (0.5 if duplicate else 1.0)
    inquiry.add(game.research, note.evidence, worth)
    research_sim.grant(game.research, round(worth * 0.4))
    if not duplicate:
        held(game).append(Filed(note_id=note.id, body=body, system=system,
                                day=game.day))
    return {"ok": True, "note": note, "worth": worth, "duplicate": duplicate}


def summary(game) -> dict:
    filed = held(game)
    return {"held": len(filed), "total": len(NOTES),
            "evidence": sum(NOTES_BY_ID[f.note_id].worth for f in filed
                            if f.note_id in NOTES_BY_ID)}
