"""The officers' stories on the screens: the Ship screen's Crew tab, a beat's
answers on the Despatches board, and the Codex's crew page.

Everything shown is read from `sim/arcs` — `status`, `preview`, `record` —
and every answer goes through `sim/comms.answer`, the one door the board
already uses. Opening any of these changes nothing: an officer from an old
save shows the story `arcs.planned` says they will be dealt, without being
dealt it.
"""

from __future__ import annotations

from ..core.util import credits, stardate
from ..data.arcs import ARCS, ARCS_BY_ID, SIGNATURES
from ..sim import arcs as arcs_sim
from ..sim import loyalty as loyalty_sim
from ..sim import lifespan as lifespan_sim
from .widgets import Panel, Pill, button, label, note


# ── the Ship screen's Crew tab ─────────────────────────────────────────────

def crew(view) -> None:
    """One panel per officer standing a watch: who they are, their story,
    how far through it, what they want now and how long they will wait."""
    g = view.game
    view.col.addWidget(note(
        "Everyone aboard has a story of their own. A beat arrives as a "
        "despatch in their voice; answer it and the story moves, ignore it "
        "and they stop waiting — which costs their loyalty, and a neglected "
        "last beat can cost you the officer. Finish one well and they keep "
        "a signature: an ability nobody else aboard has."))
    officers = lifespan_sim.active(g.officers)
    if not officers:
        view.col.addWidget(Panel("Nobody aboard").add(
            note("No officers signed on, so nobody's story is being told.")))
        return
    view.grid([_officer(g, o) for o in officers], cols=2)


def _officer(g, officer) -> Panel:
    told = arcs_sim.status(g, officer)
    arc = told["arc"]
    band, tint = loyalty_sim.band(officer)
    p = Panel(f"{officer.name} — {officer.role_name}")
    p.add_row("Loyalty", f"{loyalty_sim.loyalty_of(officer):.0f} · {band}",
              tint)
    # **Who they were before the berth** (`sim/lifepath.py`). Their story is
    # what happens to them aboard; this is the twenty years before it, and an
    # officer without one was a name, a station and a number.
    from ..sim import lifepath as life_sim
    record = life_sim.of(g, officer)
    p.add(note(life_sim.characteristics_line(record)))
    p.add(note(life_sim.skills_line(record)))
    for line in life_sim.says(record):
        p.add(note(line))
    p.add(label(f"{arc.title}  {told['marks']}", "h3",
                "chloro" if told["signature"] else "lumen"))
    p.add(note(arc.blurb))
    if told["finished"]:
        p.add(label("Their story is told." if told["signature"] else
                    "Their story ended without you.", "",
                    "" if told["signature"] else "dim", wrap=True))
    elif told["hint"]:
        p.add(label(f"{officer.name.split()[0]} {told['hint']}.", "", "",
                    wrap=True))
    if told["left"] is not None:
        p.add_row("Lapses in", f"{max(0, told['left'])} days",
                  "warn" if told["left"] < 30 else "")
    if told["waiting"]:
        p.add(label(f"Waiting, and not counting: {told['waiting']}", "",
                    "osteo", wrap=True))
    spec = told["signature"]
    if spec is not None:
        p.add(Pill(spec.name, "chloro"))
        p.add(note(spec.blurb + (f" Paid so far: {credits(told['earned'])}."
                                 if told["earned"] else "")))
    return p


# ── a beat on the Despatches board ─────────────────────────────────────────

def owns(sig) -> bool:
    return sig.frm.startswith(arcs_sim.SENDER)


def beat(panel, game, sig, answer) -> None:
    """A beat's answers, one to a row with everything each does under it —
    the preview `arcs.answered` will perform. A choice the ship cannot pay
    for is greyed, and says why."""
    if sig.answered == arcs_sim.LAPSED:
        panel.add(note("Nobody answered in time. They stopped waiting."))
        return
    if sig.answered:
        said = dict(sig.replies).get(sig.answered, sig.answered)
        panel.add(note(f"Answered: {said}."))
        return
    if not sig.asks:
        return
    for key, words in sig.replies:
        said = arcs_sim.preview(game, sig, key)
        panel.add_buttons(button(words, answer(sig.id, key),
                                 enabled=bool(said) and not said["why"],
                                 why=said.get("why", "") if said else
                                 "That is no longer being asked."))
        if said:
            panel.add(note(f"{said['line']} — “{said['thinks']}”"))


# ── the Codex's crew page ──────────────────────────────────────────────────

def codex(view) -> None:
    """Stories finished aboard, and the twelve signatures a story can leave."""
    g = view.game
    done = arcs_sim.record(g)
    lived = arcs_sim.progress(g)
    view.col.addWidget(note(
        f"{len(done)} {'story' if len(done) == 1 else 'stories'} told to "
        f"the end aboard, {lived['finished']} with a signature; "
        f"{lived['beats_done']} beats answered in all."))
    p = Panel("Told")
    if not done:
        p.add(note("No officer's story has reached its end yet."))
    for row in reversed(done):
        arc = ARCS_BY_ID.get(row["arc"])
        spec = SIGNATURES.get(row.get("signature") or "")
        p.add_row(f"{row['officer']} — {arc.title if arc else row['arc']}",
                  f"{stardate(row['day'])} · "
                  + (spec.name if spec else "no signature"),
                  "chloro" if spec else "dim")
    view.col.addWidget(p)
    held = {o.signature for o in lifespan_sim.active(g.officers)}
    cards = []
    for arc in ARCS:
        spec = SIGNATURES[arc.signature]
        card = Panel(spec.name, "chloro" if spec.id in held else "")
        card.add(label(arc.title, "sub"))
        card.add(note(spec.blurb))
        cards.append(card)
    view.col.addWidget(label("Signatures", "h3"))
    view.grid(cards, cols=3)
