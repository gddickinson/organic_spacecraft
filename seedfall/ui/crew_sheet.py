"""The Sheet tab: one person, whole.

Everything the game knows about somebody, gathered off the three modules that
derive it — `sim/lifepath.py` for the service, `sim/person.py` for the life
round it, `sim/loyalty.py` and `sim/arcs.py` for how they feel about you and
what is happening to them now.

None of it is stored. Opening this page changes nothing and costs nothing: a
character sheet is a *reading* of a saved officer's id against the sector's
seed, so an officer signed on before any of this existed has a homeworld, a
mother on a belt and a service record the moment you look.

The name bar at the top is the point of the tab. Flicking between six people
and comparing their skills is the thing a captain actually does with a crew
list, and it was not possible anywhere in the game.
"""

from __future__ import annotations

from ..data import kit as kit_table
from ..sim import arcs as arcs_sim
from ..sim import checks
from ..sim import lifepath as life_sim
from ..sim import lifespan as lifespan_sim
from ..sim import loyalty as loyalty_sim
from ..sim import person as person_sim
from ..sim import profile as profile_sim
from ..sim import roster as roster_sim
from .widgets import Panel, Pill, TabBar, button, label, note


def build(view, officer) -> None:
    """One person's whole sheet."""
    g = view.game
    if officer is None:
        view.col.addWidget(note("Nobody aboard to read."))
        return
    _name_bar(view, g, officer)
    whole = person_sim.of(g, officer)
    record = whole.record
    view.row(_who(g, officer, record), _standing(g, officer))
    view.col.addWidget(_skills(record))
    view.row(_service(record), _life(whole))
    view.row(_people(whole), _owns(view, g, whole))
    told = arcs_sim.status(g, officer)
    view.buttons(
        button("Back to the roster", lambda: view.show_tab("roster")),
        # Their story is answered on the board, in their own voice. The sheet
        # says one is waiting; it does not try to be the board as well.
        button("Their despatches", lambda: view.win.go("despatches"),
               kind="primary" if told["waiting"] else ""),
        button(f"Pay {officer.name.split()[0]} off",
               lambda: view.pay_off(officer)))


def _name_bar(view, g, officer) -> None:
    """Everybody aboard, so one click reads the next person."""
    rows = roster_sim.roll(g, view.order)
    named = roster_sim.short_names(rows)
    bar = TabBar([(str(o.id), named[o.id]) for o in rows], str(officer.id))
    bar.changed.connect(lambda oid: _pick(view, rows, oid))
    view.col.addWidget(bar)


def _pick(view, rows, oid: str) -> None:
    found = next((o for o in rows if str(o.id) == oid), None)
    if found is not None:
        view.open_sheet(found)


# ── who they are ───────────────────────────────────────────────────────────

def _who(g, officer, record) -> Panel:
    p = Panel(officer.name)
    p.add(label(f"{officer.role_name} · level {officer.level}", "sub"))
    p.add(note(officer.note))
    if officer.trait_name:
        p.add(label(f"{officer.trait_name}: {officer.trait_note}", "note",
                    "lumen", wrap=True))
    p.add(label("Characteristics", "h3"))
    p.add(note(life_sim.characteristics_line(record)))
    p.add(note("A positive number beside a score is what it adds to a throw; "
               f"anything at or over {checks.TARGET} on two dice succeeds."))
    p.add(label("Years", "h3"))
    p.add_row("Age", f"{lifespan_sim.age_of(officer, g):.0f}")
    p.add_row("Stage", lifespan_sim.stage(officer, g))
    p.add(note(lifespan_sim.note(officer, g)))
    return p


def _standing(g, officer) -> Panel:
    """How they feel about the way you run the ship, and what is happening
    to them at the moment."""
    band, tint = loyalty_sim.band(officer)
    level = loyalty_sim.loyalty_of(officer)
    p = Panel("Standing")
    p.add_row("Loyalty", f"{level:.0f} · {band}", tint)
    p.add_bar(max(0.0, min(1.0, level / 100.0)), tint or "lumen")
    conviction = loyalty_sim.conviction_of(officer)
    if conviction is not None:
        p.add(label(conviction.name, "h3"))
        p.add(note(conviction.blurb))
        p.add(note("What they believe decides what moves their loyalty. Run "
                   "the ship against it for long enough and they go."))
    told = arcs_sim.status(g, officer)
    arc = told["arc"]
    if arc is not None:
        p.add(label(f"{arc.title}  {told['marks']}", "h3",
                    "chloro" if told["signature"] else "lumen"))
        p.add(note(arc.blurb))
        if told["finished"]:
            p.add(note("Their story is told." if told["signature"]
                       else "Their story ended without you."))
        elif told["hint"]:
            p.add(label(f"{officer.name.split()[0]} {told['hint']}.", "note",
                        wrap=True))
        if told["left"] is not None:
            p.add_row("Lapses in", f"{max(0, told['left'])} days",
                      "warn" if told["left"] < 30 else "")
        spec = told["signature"]
        if spec is not None:
            p.add(Pill(spec.name, "chloro"))
            p.add(note(spec.blurb))
    return p


def _skills(record) -> Panel:
    """Everything they have been taught, and what each is for."""
    p = Panel("Skills")
    rows = sorted(record.skills.items(), key=lambda r: (-r[1], r[0]))
    if not rows:
        p.add(note("No training anybody wrote down."))
        return p
    from ..data import careers as career_table
    for name, level in rows:
        p.add_row(f"{roster_sim.pretty(name)} {level}",
                  career_table.SKILLS.get(name, ""),
                  "chloro" if level >= 2 else "")
    p.add(note(f"Anything not on this list is untrained, which is "
               f"{checks.UNTRAINED} on the throw."))
    return p


def _service(record) -> Panel:
    """The twenty years before the berth."""
    p = Panel("Service")
    for line in life_sim.says(record):
        p.add(note(line))
    return p


def _life(whole) -> Panel:
    """Where they come from, what they are after, and the ships before this."""
    p = Panel("Life")
    home, raised, wants = whole.home, whole.raised, whole.wants
    if home is not None:
        p.add_row("From", home.name)
        p.add(note(home.note))
    if raised is not None:
        p.add_row("Raised", raised.name)
        p.add(note(raised.note))
    if wants is not None:
        p.add(label(f"Wants: {wants.name.lower()}", "h3", "lumen"))
        p.add(note(wants.note))
        if wants.served_by:
            p.add(note(f"Served by: {wants.served_by}."))
    if whole.berths:
        p.add(label("Berths before this one", "h3"))
        for berth in whole.berths:
            # Stacked, not a row: how a berth ended is a sentence, and a row
            # would put it against the right edge and clip it.
            p.add_stacked(berth.ship,
                          f"{berth.kind} · {berth.years} year(s) · "
                          f"{berth.ended}")
    else:
        p.add(note("This is the first ship they have signed to."))
    return p


def _people(whole) -> Panel:
    """Who is attached to them, and which way each leans."""
    p = Panel("People")
    if not whole.ties:
        p.add(note("Nobody out there they would name."))
        return p
    for tie in whole.ties:
        # One wrapped line each, not a key/value row: the sentence already
        # opens with their name, and a row does not fold in a narrow column.
        p.add(label(f"{tie.line}, {tie.where}.", "note",
                    "chloro" if tie.helps else "warn", wrap=True))
    friends, trouble = len(whole.friends()), len(whole.trouble())
    p.add(note(f"{friends} would help them; {trouble} would not. A tie is a "
               "fact about where this ship can put in and who will be "
               "pleased to see it."))
    return p


def _owns(view, g, whole) -> Panel:
    """What they carry, what it weighs, and what a desk here would take."""
    p = Panel("Possessions")
    rows = person_sim.kit_of(whole)
    if not rows:
        p.add(note("Nothing but the clothes and the berth."))
        return p
    law = _law_here(g)
    for item in rows:
        bad = law is not None and not kit_table.legal_at(item, law)
        p.add_row(item.name,
                  f"{item.mass:.1f} kg · TL {item.tl}"
                  + (f" · law {item.law}" if item.law else ""),
                  "warn" if bad else "")
        p.add(note(item.note))
    p.add_row("Carried", f"{person_sim.carried(whole):.1f} kg")
    if law is None:
        p.add(note("No world under this port, so nothing here is contraband "
                   "yet."))
        return p
    held = person_sim.contraband(whole, law)
    if held:
        p.add(label(f"At law level {law} the desk here would take: "
                    + ", ".join(i.name for i in held) + ".", "note", "warn",
                    wrap=True))
    else:
        p.add(label(f"Nothing they carry is against law level {law}.",
                    "note", "chloro", wrap=True))
    return p


def _law_here(g):
    """The law level of the world this ship is standing at, if any."""
    system = getattr(g, "system", None)
    if system is None:
        return None
    world = profile_sim.port_world(system)
    if world is None:
        return None
    return profile_sim.profile(g, system, world).law
