"""The Watches tab and the book: what a crew costs, what mends it, who has gone.

Every act a captain can perform on the people aboard that is not "hire
somebody standing on this quay" — that one stays at the port, because a berth
board is a fact about the quay and not about the ship, and there is a door to
it on the Roster tab.

What is gathered here was in four places and belonged in one: the bonus and
shore leave were buttons under the berths board, the long sleep was a panel
below the hold on the Ship screen, the mess deck was on the berths board, and
the wage bill was a line on a ledger. The ship's own abilities — the best
level in every skill anybody aboard holds — were nowhere at all, which meant
the answer to "can this crew do the job" had to be worked out by opening six
people one at a time.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..core.util import stardate
from ..data.arcs import ARCS_BY_ID, SIGNATURES
from ..sim import arcs as arcs_sim
from ..sim import crew as crew_sim
from ..sim import lifespan as lifespan_sim
from ..sim import person as person_sim
from ..sim import profile as profile_sim
from ..data import kindred as kin_table
from ..data import lineages as lineage_table
from ..sim import kindred as kindred_sim
from ..sim import places as places_sim
from ..sim import roster as roster_sim
from .dormancy_panel import who_sleeps
from .widgets import Panel, button, label, note

#: How many skills to print before saying there are more. A bridge of six can
#: hold forty between them and the table is read for the top of it.
ABILITIES_SHOWN = 14

#: How many of the crew's relationships to name. Eleven rows of "who, what
#: they are to somebody, and where they are" is a wall, and a key/value row
#: does not wrap — at 1040 px the sentences were clipped mid-word.
TIES_SHOWN = 10


def build(view, said: dict) -> None:
    """The whole Watches tab."""
    g = view.game
    view.row(_bill(g, said), _keeping(view, g, said))
    view.row(_abilities(g), _made_of(view, g))
    view.col.addWidget(hands_panel(view))
    view.col.addWidget(who_sleeps(view, g))
    view.row(_ties(g), _ashore(g))


# ── what they cost ─────────────────────────────────────────────────────────

def _bill(g, said: dict) -> Panel:
    p = Panel("The bill")
    p.add(note("A crew is the one running cost that cannot be switched off. "
               "Wages come out of the treasury; stores come out of the hold."))
    for days in (1, 30, 90):
        got = roster_sim.wage_bill(g, days)
        p.add_row(f"{days} day(s)" if days > 1 else "Each day",
                  f"{cr(round(got['wages']))} · {got['stores']:.1f} t")
    p.add_row("Power drawn", f"{said['power']:.1f} kW")
    p.add_row("In hand", cr(round(getattr(g, "credits", 0))))
    days = roster_sim.wage_bill(g)["afford"]
    p.add(label(
        "The treasury covers the wages for "
        + ("longer than anybody will be alive."
           if days == float("inf") else f"{days:,.0f} more days."),
        "note", "warn" if days != float("inf") and days < 60 else "",
        wrap=True))
    return p


def _keeping(view, g, said: dict) -> Panel:
    """The two things that mend a bridge, and what each costs."""
    p = Panel("Keeping them")
    p.add(note("A bonus buys goodwill outright and costs only money. Shore "
               "leave buys more of it and costs a week — the ship goes "
               "nowhere, and the week is charged to everybody's age."))
    bonus = said["bonus"]
    p.add_row("A bonus", cr(bonus))
    p.add_row("Shore leave", f"{crew_sim.SHORE_LEAVE_DAYS} days alongside")
    p.add_buttons(
        button(f"Pay a bonus — {cr(bonus)}", view.bonus, kind="primary",
               enabled=g.credits >= bonus and said["officers"] > 0,
               tip="Nobody on the bridge to pay." if not said["officers"]
               else "Not enough in the treasury."),
        button("Grant shore leave", view.shore_leave,
               enabled=said["officers"] > 0))
    if said["restless"]:
        p.add(label(f"{said['restless']} of the bridge are restless. Both of "
                    "these help, and neither answers what they believe.",
                    "note", "warn", wrap=True))
    p.add(label("The berth board", "h3"))
    p.add(note("Who is looking for a berth is a fact about the quay you are "
               "standing on, so it lives on the Port screen."))
    p.add_buttons(button("Open the berth board", view.to_berths))
    return p


# ── what the crew can do ───────────────────────────────────────────────────

def _abilities(g) -> Panel:
    """The best level in every skill anybody aboard holds."""
    p = Panel("What this crew can do")
    rows = roster_sim.abilities(g)
    if not rows:
        p.add(note("Nobody aboard has been taught anything the ship can use."))
        return p
    p.add(note("The best level aboard in each skill, and whose it is. A "
               "check about the ship asks this, not the captain."))
    # The name only, not the name and what the skill is for: a row does not
    # wrap, and a sentence in the right-hand column is clipped in a narrow
    # column rather than folded. What each skill is for is on the sheet.
    for row in rows[:ABILITIES_SHOWN]:
        p.add_row(f"{roster_sim.pretty(row['skill'])} {row['level']}",
                  row["who"].name,
                  "chloro" if row["level"] >= 2 else "")
    if len(rows) > ABILITIES_SHOWN:
        p.add(note(f"…and {len(rows) - ABILITIES_SHOWN} more."))
    gap = roster_sim.missing(g)
    if gap:
        p.add(label("Nobody aboard is trained in "
                    + ", ".join(roster_sim.pretty(s).lower() for s in gap)
                    + ".", "note", "warn", wrap=True))
    return p


def _made_of(view, g) -> Panel:
    """What the bridge is made of, and what carrying it costs.

    Eight substrates can stand a watch (`data/lineages.py`), the powers all
    have a view about which (`data/kindred.py`), and somebody aboard may
    have one too. A crew list that only counted heads was hiding all three.
    """
    read = kindred_sim.complement(g)
    p = Panel("What the bridge is made of")
    if not read["heads"]:
        p.add(note("Nobody aboard but you."))
        return p
    for lineage_id, count in sorted(read["lineages"].items(),
                                    key=lambda r: -r[1]):
        got = lineage_table.LINEAGES_BY_ID.get(lineage_id)
        if got is None:
            continue
        p.add_row(got.name, f"{count} · "
                  + kin_table.CLASS_NAME[kin_table.class_of(lineage_id)])
        p.add(note(got.what))
    rub = kindred_sim.friction(g)
    if rub["per_day"] > 0:
        names = ", ".join(o.name for o in rub["minders"])
        p.add(label(f"{names} will not call half this bridge shipmates. "
                    f"It costs about {rub['per_day']:.2f} of their "
                    "loyalty a day, and it does not stop.", "note", "warn",
                    wrap=True))
    elif read["kinds"] > 1:
        p.add(label(f"{read['kinds']} sorts of being aboard, and nobody "
                    "minds.", "note", "chloro", wrap=True))
    place = places_sim.current(g)
    if place is not None and place.kind != "ship":
        kept = kindred_sim.kept_aboard(g, place)
        if kept:
            p.add(label(f"{len(kept)} of them are not admitted ashore at "
                        f"{place.name}.", "note", "warn", wrap=True))
    return p


def hands_panel(view) -> Panel:
    """The mess deck: how many hands, how old, and taking more on."""
    g = view.game
    read = lifespan_sim.crew_profile(g)
    room = lifespan_sim.berths_free(g)
    p = Panel("The mess deck")
    p.add(label(lifespan_sim.crew_note(g), "note",
                "warn" if read["over"] > 0.1 else "", wrap=True))
    p.add_row("Berths free", str(room))
    p.add_row("Signing fee", cr(lifespan_sim.SIGNING_FEE) + " a head")
    p.add(note("Hands are a headcount, not people: they stand the watches "
               "nobody is named for, they eat, and they get older."))
    for count in (5, 20):
        take = min(count, room)
        ok, why = (lifespan_sim.can_sign_on(g, take) if take
                   else (False, "Every berth aboard is filled."))
        p.add_buttons(button(
            f"Sign on {take} — {cr(lifespan_sim.SIGNING_FEE * take)}"
            if take else "No berths free",
            lambda _=False, n=take: view.sign_on(n),
            kind="primary" if ok and count == 5 else "",
            enabled=ok, tip=why))
        if not ok and why:
            p.add(note(why))
            break
    return p


# ── who they know, and what they are carrying ──────────────────────────────

def _ties(g) -> Panel:
    """Everybody the crew knows out there, gathered off their sheets."""
    p = Panel("Who the crew knows")
    rows = roster_sim.ties_ashore(g)
    if not rows:
        p.add(note("Nobody aboard has named anybody."))
        return p
    helps = len([r for r in rows if r["tie"].helps])
    p.add(note(f"{len(rows)} people between them: {helps} who would help and "
               f"{len(rows) - helps} who would not. Where this ship puts in "
               "is somebody's home port and somebody else's creditor."))
    for row in rows[:TIES_SHOWN]:
        tie = row["tie"]
        # `tie.line` already names them — "Marek Wintermute, who will not
        # speak" — so the crew member goes in front, not the tie.
        p.add(label(f"{row['who']}: {tie.line}, {tie.where}.", "note",
                    "chloro" if tie.helps else "warn", wrap=True))
    if len(rows) > TIES_SHOWN:
        p.add(note(f"…and {len(rows) - TIES_SHOWN} more, on their own "
                   "sheets."))
    return p


def _ashore(g) -> Panel:
    """What walking the watch down the gangway here would cost."""
    p = Panel("Going ashore")
    system = getattr(g, "system", None)
    world = profile_sim.port_world(system) if system is not None else None
    if world is None:
        p.add(note("There is no world under this ship to go ashore on."))
        return p
    got = profile_sim.profile(g, system, world)
    p.add_row("Law level", f"{got.law} — {_law_words(got.law)}")
    risk = person_sim.risk_ashore(g, got.law)
    if not risk["people"]:
        p.add(label("Nothing the watch carries is forbidden here.", "note",
                    "chloro", wrap=True))
        return p
    p.add(label(f"{risk['people']} of the watch are carrying something this "
                "world forbids.", "note", "warn", wrap=True))
    for who, item in risk["items"]:
        p.add_row(who, f"{item.name} — law {item.law}", "warn")
    p.add(note("A customs desk takes what it finds, and remembers who was "
               "carrying it."))
    return p


def _law_words(law: int) -> str:
    if law <= 2:
        return "almost nothing is forbidden"
    if law <= 5:
        return "the obvious weapons"
    if law <= 8:
        return "most weapons, and some tools"
    return "they will search you"


# ── the book ───────────────────────────────────────────────────────────────

def book(view) -> None:
    """Who has left the bridge, and the stories that were told to the end."""
    g = view.game
    view.col.addWidget(note(
        "A crew outlasts a captain's memory of it. This is everyone who "
        "stood a watch on this hull and does not any more, and every story "
        "that was carried to its end aboard."))
    view.row(_gone(g), _told(g))


def _gone(g) -> Panel:
    p = Panel("Off the bridge")
    rows = roster_sim.departed(g)
    if not rows:
        p.add(note("Nobody has retired off this bridge yet."))
        return p
    for row in rows:
        officer = row["officer"]
        p.add(label(f"{officer.name} — {officer.role_name}, "
                    f"{row['age']:.0f} years. {row['note']}", "note", "dim",
                    wrap=True))
    return p


def _told(g) -> Panel:
    p = Panel("Stories told")
    done = arcs_sim.record(g)
    if not done:
        p.add(note("No officer's story has reached its end aboard yet."))
        return p
    lived = arcs_sim.progress(g)
    p.add(note(f"{len(done)} told to the end, {lived['finished']} with a "
               f"signature; {lived['beats_done']} beats answered in all."))
    for row in reversed(done):
        arc = ARCS_BY_ID.get(row["arc"])
        spec = SIGNATURES.get(row.get("signature") or "")
        p.add_row(f"{row['officer']} — {arc.title if arc else row['arc']}",
                  f"{stardate(row['day'])} · "
                  + (spec.name if spec else "no signature"),
                  "chloro" if spec else "dim")
    return p
