"""The commissions desk: work that leads somewhere, and where you are in it."""

from __future__ import annotations

from ..core.util import credits as cr
from ..data.factions import FACTIONS_BY_ID
from ..sim import chains as chain_sim
from .widgets import Panel, Pill, button, label, mono_label, note, spacer


def held_panel(view, game) -> Panel | None:
    """Commissions under way, with the stage you are on drawn out."""
    running = chain_sim.active(game)
    finished = chain_sim.completed(game)
    if not running and not finished:
        return None

    p = Panel("Commissions")
    for held in running:
        chain = held.definition
        stages = chain.stages
        p.add(spacer(3))
        p.add(label(chain.name, "h3", "lumen"))
        p.add_row(FACTIONS_BY_ID[chain.issuer].short,
                  f"stage {min(held.stage + 1, len(stages))} of {len(stages)}")
        for line in held.history:
            p.add(note(f"— {line}"))
        contract = chain_sim.current_contract(game, held)
        if contract is not None:
            p.add(label(contract.title, "", "chloro"))
            p.add(note(f"{cr(contract.reward)} · "
                       f"{contract.days_left(game.day)} day(s) left"))
        p.add_bar(held.stage / len(stages), "lumen")

    for held in finished:
        chain = held.definition
        p.add(spacer(3))
        p.add(label(chain.name, "h3", "chloro"))
        p.add(Pill("discharged", "chloro"))
        p.add(note(chain.reward_note))
    return p


def offers_panel(view, game, system) -> Panel | None:
    """What this port would put to you, and what taking it would shut."""
    offers = chain_sim.offered(game, system)
    if not offers:
        return None

    p = Panel("Put to you privately")
    p.add(note("These are not postings. Somebody has decided you are the one "
               "they call, and the work escalates from there."))
    for chain, ok, why in offers:
        p.add(spacer(4))
        p.add(label(chain.name, "h3", "chloro" if ok else "dim"))
        p.add(note(chain.premise))
        p.add_row("Stages", f"{len(chain.stages)}")
        p.add_row("On completion",
                  f"{cr(chain.reward_credits)} · {chain.reward_rep:+g} standing",
                  "lumen" if ok else "dim")
        p.add(note(chain.reward_note))
        if chain.blocks:
            shut = ", ".join(chain_sim.CHAINS_BY_ID[b].name for b in chain.blocks
                             if b in chain_sim.CHAINS_BY_ID)
            if shut:
                p.add(label(f"Taking this closes: {shut}", "", "warn"))
        if not ok:
            p.add(label(why, "", "warn"))
        p.add_buttons(button("Take the commission",
                             lambda _=False, cid=chain.id: view.take_commission(cid),
                             kind="primary" if ok else "", enabled=ok))
    return p
