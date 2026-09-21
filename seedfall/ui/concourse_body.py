"""The Clinic tab: what this place will do to a person, and to whom.

One officer at a time, because that is the decision — a captain does not buy
surgery, they buy surgery *for Corin*, who is fifty-one, two levels down on
decline and the only person aboard who can plot a crossing.

Everything on the page is `sim/clinic.py`'s quote, which is the same call the
button performs: the money, the days off the calendar, what it will do to
them in so many words, and the odds it goes wrong. A treatment nobody here
can do does not appear; one they will not *admit* to doing appears under the
unlicensed heading with a warning on it.
"""

from __future__ import annotations

from ..data import treatments as table
from ..sim import clinic as clinic_sim
from ..sim import lifepath as life_sim
from ..sim import lifespan as lifespan_sim
from ..sim import roster as roster_sim
from .widgets import Panel, Pill, TabBar, button, label, note

#: The order the tabs' panels are built in: what a clinic is asked for, in
#: roughly the order of how badly somebody needs it.
ORDER = ("care", "surgery", "graft", "years", "cyber", "gene", "train", "ice")

#: Every skill the game teaches, for the training panel's picker. The list
#: is long; these are the ones a hull actually uses.
TEACHABLE = ("astrogation", "pilot", "gunnery", "engineer", "mechanic",
             "medic", "sciences", "broker", "admin", "electronics",
             "vacc_suit", "tactics", "gun_combat", "leadership", "persuade",
             "computers", "recon", "streetwise")


def build(view, place) -> None:
    """The whole tab."""
    game = view.game
    rows = clinic_sim.offered(game, place)
    _racks(view, place)
    if not rows:
        view.col.addWidget(Panel("No clinic here").add(
            note("Nobody at this place does anything to anybody. A surgery "
                 "needs somewhere with the machine for it — and what can be "
                 "done to a person rises steeply with the tech level, which "
                 "is most of the reason to fly somewhere better.")))
        return
    officer = view.officer()
    if officer is None:
        view.col.addWidget(note("Nobody aboard to treat."))
        return
    _patient_bar(view, game, officer)
    view.col.addWidget(_who(game, officer))
    by_kind: dict = {}
    for row in rows:
        by_kind.setdefault(row["treatment"].kind, []).append(row)
    for kind in ORDER:
        here = by_kind.get(kind)
        if not here:
            continue
        view.col.addWidget(label(_HEADING[kind], "h2"))
        view.col.addWidget(note(_ABOUT[kind]))
        view.grid([_offer(view, place, officer, r) for r in here], cols=3)


_HEADING = {
    "care": "Care", "surgery": "Surgery", "graft": "Grafts",
    "years": "Years", "cyber": "Bodywork", "gene": "The germ line",
    "train": "Instruction", "ice": "Cold berths",
}
_ABOUT = {
    "care": "The ordinary repairs. Clears the wear a hard stretch leaves "
            "before it costs somebody a level.",
    "surgery": "The serious repairs, under. Buys back a level already shed "
               "to decline.",
    "graft": "Cloned tissue, grown from them, so nothing has to be "
             "suppressed afterwards.",
    "years": "Anagathics. The only thing in the Verge that moves a lifespan "
             "the right way, at a price that explains the Charter.",
    "cyber": "Fitted hardware. The best numbers on this screen, and the "
             "only ones that charge strain — what it costs a person to be "
             "partly a machine among people who are not.",
    "gene": "Permanent, expensive, and illegal almost everywhere the "
            "Charter runs.",
    "train": "A skill, taught properly, over weeks alongside.",
    "ice": "Somebody who is not needed for a while. They leave the bridge, "
           "they stop ageing, and the rack sends a bill every year.",
}


def _racks(view, place) -> None:
    """Anybody this chronicle has left in a rack, and what it is costing.

    Shown wherever you are, not only where they are: a person on ice is a
    bill that follows the ship, and forgetting one is exactly the mistake
    this panel exists to prevent.
    """
    game = view.game
    rows = clinic_sim.on_ice(game)
    if not rows:
        return
    owed = clinic_sim.ice_bill(game)
    p = Panel("On ice", "lumen")
    for row in rows:
        officer = row.get("officer")
        years = (float(getattr(game, "day", 0.0))
                 - float(row.get("since", 0))) / 365.0
        p.add_row(getattr(officer, "name", "somebody"),
                  f"{row.get('where', 'somewhere')} · {years:.1f} years")
    p.add_row("Owed to the racks", f"{owed:,.0f} credits",
              "warn" if owed > game.credits else "")
    can, why = view.can_trade(place)
    here = bool(clinic_sim.doors(game, place, "ice"))
    for row in rows:
        officer = row.get("officer")
        p.add(button(f"Bring {getattr(officer, 'name', '?').split()[0]} up",
                     lambda _=False, i=getattr(officer, "id", 0):
                     view.thaw(place, i),
                     enabled=can and here,
                     tip=why or "No rack here to open."))
    view.col.addWidget(p)


def _patient_bar(view, game, officer) -> None:
    """Whose body this is. One click reads the next person."""
    rows = roster_sim.active(game)
    named = roster_sim.short_names(rows)
    bar = TabBar([(str(o.id), named[o.id]) for o in rows], str(officer.id))
    bar.changed.connect(lambda oid: _pick(view, rows, oid))
    view.col.addWidget(bar)


def _pick(view, rows, oid: str) -> None:
    found = next((o for o in rows if str(o.id) == oid), None)
    if found is not None:
        view.see_patient(found)


def _who(game, officer) -> Panel:
    """The patient: the numbers a clinic would ask for."""
    record = life_sim.of(game, officer)
    p = Panel(f"{officer.name} — {officer.role_name}")
    p.add(note(life_sim.characteristics_line(record)))
    p.add_row("Age", f"{lifespan_sim.age_of(officer, game):.0f} · "
                     f"{lifespan_sim.stage(officer, game)}")
    p.add(note(lifespan_sim.note(officer, game)))
    wear = float(getattr(officer, "wear", 0.0) or 0.0)
    p.add_row("Wear", f"{wear:.2f} of a level",
              "warn" if wear > 0.5 else "")
    fitted = clinic_sim.fitted_to(game, officer)
    if fitted:
        p.add(label("Fitted", "h3"))
        for got in fitted:
            p.add(label(got.name, "note", "lumen"))
        strain = clinic_sim.strain_of(game, officer)
        p.add(Pill(f"strain {strain:.1g}", "warn" if strain >= 3 else "dim"))
        p.add(note(f"That is {strain * table.STRAIN_LOYALTY:.0f} of their "
                   "loyalty, permanently, and people notice."))
    taught = clinic_sim.taught_to(game, officer)
    if taught:
        p.add(label("Taught since signing on: " + ", ".join(
            f"{k.replace('_', ' ').title()} +{v}"
            for k, v in sorted(taught.items())), "note", "chloro", wrap=True))
    return p


def _offer(view, place, officer, row) -> Panel:
    """One piece of work, quoted exactly as it will be charged."""
    got = row["treatment"]
    p = Panel(got.name, "" if row["licensed"] else "warn")
    p.add(note(got.note))
    if got.kind == "train":
        for widget in _course(view, place, officer, got, row):
            p.add(widget)
        return p
    said = clinic_sim.quote(view.game, place, officer, got.id)
    p.add_row("Price", f"{row['cr']:,} credits")
    p.add_row("Alongside", f"{got.days} day(s)")
    if said.get("does"):
        p.add(label("  ·  ".join(said["does"]), "note", "chloro", wrap=True))
    if got.risk:
        p.add(label(f"{said['odds']:.0%} that it goes as it should. "
                    f"{got.mishap}", "note",
                    "warn" if said["odds"] < 0.75 else "", wrap=True))
    if not row["licensed"]:
        p.add(label("Nobody licensed here will admit to this.", "note",
                    "warn", wrap=True))
    can, why = view.can_trade(place)
    if got.kind == "ice":
        p.add(button(f"Put {officer.name.split()[0]} under",
                     lambda _=False, t=got.id: view.freeze(place, officer, t),
                     kind="primary", enabled=can and said["ok"],
                     tip=why or said["why"]))
        return p
    p.add(button("Have it done",
                 lambda _=False, t=got.id: view.treat(place, officer, t),
                 kind="primary", enabled=can and said["ok"],
                 tip=why or said["why"]))
    return p


def _course(view, place, officer, got, row) -> list:
    """A course teaches one skill, so the skill is the decision."""
    made = [label(f"{row['cr']:,} credits · {got.days} day(s) alongside",
                  "note")]
    record = life_sim.of(view.game, officer)
    can, why = view.can_trade(place)
    for name in TEACHABLE[:6]:
        level = record.skills.get(name)
        said = ("untrained" if level is None else f"at {level}")
        made.append(button(
            f"{name.replace('_', ' ').title()} — {said}",
            lambda _=False, t=got.id, s=name: view.treat(place, officer, t, s),
            kind="flat", enabled=can, tip=why))
    made.append(label("Six of the eighteen the halls teach; the rest need a "
                      "berth at an academy.", "note", "dim", wrap=True))
    return made
