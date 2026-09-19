"""The battle's orders: every act open this turn, and what each will do.

Split out of `ui/battle_view.py`, whose `_orders` had grown to 136 lines.

**Every one of the orders was below the fold.** The screen stacked the plots,
the gunnery picture, the read, the band track, both hulls and the seats'
intentions above the orders, so measured on a shown window **none of the
twenty action buttons was in view at any size up to 1560×1000**, and at the
1040×680 minimum the screen scrolled 2,037 px to reach them. The fight was
played by scrolling down to press something and back up to see what it did.

So the orders are a column of their own, pinned at the left of the screen:
first the buttons — all of them, in one block, wrapping to the width they are
given (`ui/flow.py`) — and then, under them, what each one will do. The
readout scrolls beside it without taking the orders with it.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..sim import abilities as abilities_sim
from ..sim import firing
from ..sim import parley as parley_sim
from ..sim import stations as st_mod
from ..sim import turnplan
from .battle_text import parley_lines, parley_tip
from .flow import Flow
from .widgets import Panel, button, label, mono_label, note, spacer


def acts(view, b) -> Panel:
    """Every button that spends this turn, and nothing else."""
    p = Panel("Orders")
    p.add(mono_label("Fire a single mount"))
    p.add(fire_buttons(view, b))
    p.add(spacer(2), mono_label("Stations — you may take one this turn"))
    for sid, name, stat, _blurb in st_mod.STATIONS:
        level = st_mod.officer_level(b.officers, stat)
        p.add(label(f"{name} · officer level {level}", "",
                    "chloro" if sid == b.player.station else "dim"))
        p.add(Flow([button(order.name, tip=order.blurb,
                           on_click=lambda _=False, o=order.id: view._act(
                               {"type": "station", "order": o}))
                    for order in st_mod.orders_for(sid)]))
    systems = ability_buttons(view, b)
    if systems is not None:
        p.add(spacer(2), mono_label("Systems"), systems)
    p.add(spacer(2), mono_label("Other"), other_buttons(view, b))
    return p


def fire_buttons(view, b):
    """One button per mount, live only when the whole rule says it can fire.

    Enabled on the whole rule, not just the range. These buttons tested
    `bears_at` alone, so a mount sixty degrees off the beam or with an empty
    magazine was offered, taken, and spent the turn on a log line explaining
    why it had not fired.
    """
    st = b.player.st
    if not st.weapons:
        return note("No armament fitted. Charter doctrine, or an oversight — "
                    "either way you must outlast them, talk them down, or run.")
    picture = {x.mount_id: x for x in
               firing.solution(b.player, b.enemy, b.band)}
    made = []
    for w in st.weapons:
        shot = picture.get(w.id)
        live = shot.can_fire if shot else False
        tag = ("" if not shot or shot.in_band
               else " (long shot)" if live else "")
        made.append(button(w.name + tag,
                           lambda _=False, wid=w.id: view._act(
                               {"type": "fire", "weapon_id": wid}),
                           tip=(shot.why if shot else w.blurb),
                           enabled=live,
                           why=(shot.why if shot else "Nothing to fire with.")))
    return Flow(made)


def ability_buttons(view, b):
    """The hull's systems, each saying through `abilities.preview` — which
    is what `use_ability` reads — what it will do or why it cannot."""
    st = b.player.st
    if not st.abilities:
        return None
    made = []
    for part_ in st.abilities:
        ab = part_.ability
        cd = b.player.cd.get(ab.id, 0)
        say = abilities_sim.preview(b, b.player, ab.id)
        made.append(button(f"{ab.name}" + (f" ({cd})" if cd else ""),
                           lambda _=False, aid=ab.id: view._act(
                               {"type": "ability", "id": aid}),
                           tip=(part_.blurb + "  "
                                + (" · ".join(say["lines"]) if say["can"]
                                   else say["why"])),
                           enabled=say["can"], why=say["why"]))
    return Flow(made)


def other_buttons(view, b):
    """The stations' windows, and the three acts that are not a seat.

    A mute enemy's hail button is off, with the reason on it — the sim
    deliberately charges no turn for that press ("a category error, not a
    gamble"), so the screen must refuse it rather than let it read as a free
    re-roll.
    """
    mute = parley_sim.odds(b).get("mute", False)
    return Flow([
        button("Gunnery…", view._open_gunnery, kind="flat",
               tip="The gunner's station: every mount's arc, and which of "
                   "them fire this turn."),
        button("Tactical…", view._open_tactical, kind="flat",
               tip="The tactical station, which is open whether or not "
                   "anybody is shooting."),
        button("Brace", lambda: view._act({"type": "brace"}), kind="flat",
               tip="Turn the thickest tissue into the fire and hold: vents "
                   "heat, steadies the crew, and the gunner keeps working."),
        button("Hail them", lambda: view._act({"type": "hail"}),
               enabled=not mute, tip=parley_tip(b, "hail"),
               why=parley_tip(b, "hail")),
        button("Disengage", lambda: view._act({"type": "flee"}), kind="flat",
               tip=parley_tip(b, "flee")) if b.fleeable else None,
    ])


def consequences(view, b) -> Panel:
    """What each order will do, under the buttons that give them.

    The station orders were bare buttons with a sentence of prose, so a
    captain at 30 of a 50 cap could fire everything, make 74 more, and find
    out afterwards. And the hail and the burn are the only acts here whose
    failing side is "they shoot you for free", so their odds are on the panel
    and not only under a hover.
    """
    p = Panel("What each order does")
    seats = st_mod.seat_value(b.player, b.officers)
    for sid, name, _stat, blurb in st_mod.STATIONS:
        p.add(spacer(2), mono_label(name))
        p.add(note(blurb))
        # What sitting here yourself is worth, rather than only who is holding
        # it. A green officer makes the seat worth twice what a veteran does.
        seat = seats.get(sid, {})
        worth = (f"+{seat.get('gain', 0):.0%} to hit over the officer"
                 if sid == "gunnery" else seat.get("says", ""))
        if worth:
            _row(p, "Taking it yourself", worth,
                 "chloro" if seat.get("gain", 0) > 0 else "dim")
        for order in st_mod.orders_for(sid):
            plan = turnplan.order_preview(b.player, b.enemy, order.id,
                                          b.officers, b.band)
            if plan["lines"]:
                _row(p, order.name, " · ".join(plan["lines"]),
                     "warn" if plan["over"] else "dim")
    if b.player.st.abilities:
        p.add(spacer(2), mono_label("Systems"))
        for part_ in b.player.st.abilities:
            say = abilities_sim.preview(b, b.player, part_.ability.id)
            if say["can"]:
                _row(p, say["name"], " · ".join(say["lines"]), "chloro")
            else:
                _row(p, say["name"], say["why"], "dim")
    p.add(spacer(2), mono_label("Talking, and running"))
    for line, tint in parley_lines(b):
        p.add(note(line) if tint == "dim" else label(line, "", tint, wrap=True))
    return p


def _row(panel, key: str, value: str, tint: str = "") -> None:
    """A key and a value that wraps — `Panel.add_row` keeps the value on one
    line, and a forecast of three clauses on one line set the orders column
    wider than the screen allows it."""
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 1, 0, 1)
    h.setSpacing(10)
    k = label(key, "dim")
    k.setAlignment(Qt.AlignmentFlag.AlignTop)
    h.addWidget(k)
    v = label(value, "", tint, wrap=True)
    v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
    h.addWidget(v, 1)
    panel.add(row)
