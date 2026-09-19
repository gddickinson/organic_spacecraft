"""Taking work on, walking away from it, and putting a seed in the ground.

Three acts a screen used to finish itself. The rules were already in the sim
— `contracts.accept`, `contracts.abandon`, `colony.found` — but the line in
the log that says the captain did it was written by the button handler
(`ui/port_view.py`, `ui/seed_dialog.py`), so a contract taken over the bridge
or by a check went into the book without the chronicle hearing about it, and
walking away from one said nothing at all.

These are the doors: each performs the act through the rule that owns it,
writes the line, and answers `{ok, why, text}` so the screen has only to say
the refusal or redraw.
"""

from __future__ import annotations

from . import colony as colony_sim
from . import contracts as contract_sim


def take_contract(game, contract) -> dict:
    """Put a contract from the board in the book."""
    ok, why = contract_sim.accept(game, contract)
    if not ok:
        return {"ok": False, "why": why, "text": ""}
    text = f"Contract taken: {contract.title}."
    game.add_log(text, "good")
    return {"ok": True, "why": "", "text": text}


def abandon_contract(game, contract) -> dict:
    """Walk away from one. The issuer remembers, and now so does the log."""
    if contract.done or contract.failed:
        return {"ok": False, "why": "That contract is already closed.",
                "text": ""}
    contract_sim.abandon(game, contract)
    text = f"Contract abandoned: {contract.title}."
    game.add_log(text, "bad")
    return {"ok": True, "why": "", "text": text}


def plant_seed(game, system, body, class_id: str) -> dict:
    """Found a holding: the seed goes in and gestation starts."""
    col, why = colony_sim.found(game, system, body, class_id)
    if not col:
        return {"ok": False, "why": why, "text": ""}
    text = f"Seed planted at {body.name}. Gestation {col.need} days."
    game.add_log(text, "good")
    return {"ok": True, "why": "", "text": text, "colony": col}
