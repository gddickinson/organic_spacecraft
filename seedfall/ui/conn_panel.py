"""The conn's side panel: what it says, and updating it without rebuilding it.

Split out of `ui/conn_window.py` for the same reason the Pilot screen grew
`shape`/`sync`: the panel was torn down and rebuilt — `takeAt(0)`,
`setParent(None)`, a fresh `QWidget`/`QHBoxLayout`/`QLabel` per row — on every
beat, four times a second once the one clock landed. The Pilot screen's fix
(#150) recorded why that class of churn matters; this is the same medicine for
the last screen still taking the old one.

`content` says *what* the panel shows — one list, so the words cannot drift
between a build and a sync — and `apply` decides *how*: same shape, update the
labels in place; different shape (a row appearing, a note arriving, the
engines refitted), rebuild. A readout's value changes every beat; the set of
readouts changes when the situation does.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..sim import conn as conn_sim
from ..sim import freeflight as free_sim
from ..sim import instruments as panel_sim
from . import theme
from .widgets import label, note


def content(window, conn) -> list:
    """Everything the side panel says, in order: (kind, *fields) entries.

    `("row", name, value, tint)` is an instrument; `("note", text)` is a
    line; `("head", text)` is a heading. One door for the words — the same
    rule as `pilot_panels.main_label` and for the same reason (#137).
    """
    game = window.game
    out = [("row", name, value, kind)
           for name, value, kind in panel_sim.readout(conn)]
    hint = conn_sim.orbit_note(conn)
    if hint:
        out.append(("note", hint))
    # What the structure is doing about you. Every one of these lines was
    # written into the sim and read by nobody but the suite: a hull could be
    # refused, shot at, stood off from, towed or half way through a collar
    # and the conn would say only what the last burn did.
    from ..sim import control as control_sim
    from ..sim import forcing as forcing_sim
    from ..sim import tug as tug_sim
    for said in (tug_sim.tug_line(conn), control_sim.refusal_line(conn),
                 control_sim.sheer_line(conn), forcing_sim.force_line(conn),
                 window.refused):
        if said:
            out.append(("note", said))
    # A tick the drive spent swinging rather than burning. The bridge and the
    # flight panel both said so; this window read the clock move, the mass
    # drop and the speed hold still, and explained none of it.
    if conn.fired_turning:
        out.append(("note", "Swinging the hull round — the drive only "
                            "pushes along the nose, so this tick is spent "
                            "turning."))
    # Where the nose is — **only on an approach.** `heading_note`'s default
    # bearing is `-conn.pos`, which in a free flight is *where she was let
    # go*: measured, nose exactly on the mark and this line read "Nose 180°
    # off" while the bridge read 0°. Out there the bearing that means
    # anything is to the mark, if one is laid.
    from ..sim import attitude as attitude_sim
    from ..sim import thrusters
    if not free_sim.is_free(conn):
        out.append(("note", attitude_sim.heading_note(conn)))
    else:
        aim = free_sim.marked(game, conn)
        if aim is not None:
            out.append(("note", attitude_sim.heading_note(
                conn, free_sim.toward(game, conn, aim))))
    out.append(("head", "Engines"))
    for what, howmuch, where in thrusters.board(game.ship):
        out.append(("note", f"{what} — {howmuch}, {where}"))
    return out


def _shape(entries) -> tuple:
    """What decides whether the panel must be rebuilt: the *set* of things
    said, not their readings. A row is identified by its name; a note by its
    position (its text is a reading)."""
    return tuple(e[1] if e[0] == "row" else e[0] for e in entries)


def apply(window, conn) -> None:
    """Show `content` — in place when the shape allows, rebuilt when not."""
    entries = content(window, conn)
    if getattr(window, "_side_shape", None) == _shape(entries):
        for entry, made in zip(entries, window._side_made):
            if entry[0] == "row":
                _kind, _name, value, tint = entry
                made.setText(value)
                made.setStyleSheet(_row_style(tint))
            elif entry[0] == "note":
                made.setText(entry[1])
        return
    while window.side.count():
        item = window.side.takeAt(0)
        if item.widget():
            # Now, not when the event loop next idles: a deferred delete
            # leaves the old readout painted under the new one.
            item.widget().setParent(None)
    made = []
    for entry in entries:
        if entry[0] == "row":
            _kind, name, value, tint = entry
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            left = QLabel(name)
            left.setStyleSheet(f"color: {theme.INK3}; font-size: 12px;")
            right = QLabel(value)
            right.setStyleSheet(_row_style(tint))
            line.addWidget(left)
            line.addStretch(1)
            line.addWidget(right)
            window.side.addWidget(row)
            made.append(right)
        elif entry[0] == "head":
            made.append(label(entry[1], "h3"))
            window.side.addWidget(made[-1])
        else:
            made.append(note(entry[1]))
            window.side.addWidget(made[-1])
    window.side.addStretch(1)
    window._side_shape = _shape(entries)
    window._side_made = made


def _row_style(tint: str) -> str:
    return (f"color: {theme.tint(tint) if tint in theme.TINTS else theme.INK};"
            f"font-family: '{theme.mono_family()}'; font-size: 12.5px;")
