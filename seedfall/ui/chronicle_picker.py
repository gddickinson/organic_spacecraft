"""The chronicles on this machine, as the title screen offers them, and the
menu's "Save as…".

The title screen had one way back in — Resume — onto one save, and "Begin
again" warned that it would be written over. The slots themselves live in
`core/slots.py`; this is where they are drawn and pressed. Every row is read
from the summary at the head of its file, so drawing the list decodes
nothing and cannot quarantine a damaged slot just by looking at it.

Loading, keeping and deleting are all commitments, so each one says what it
does to the chronicle in play before it does it.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (QHBoxLayout, QLineEdit, QScrollArea, QVBoxLayout,
                             QWidget)

from ..core import slots
from ..core import state as state_mod
from ..core.util import credits, stardate
from ..data.beginnings import ORIGINS_BY_ID
from ..data.chassis import CHASSIS_BY_ID
from ..data.lore import VICTORIES
from .widgets import Panel, button, defer, label, note

_ENDING_NAMES = {vid: name for vid, name, *_rest in VICTORIES}

#: What the two rows that exist because something went wrong are, said on
#: the row, because loading either is a different decision from loading a
#: slot somebody kept on purpose.
_WHY_HERE = {
    "recovery": "Written when the game hit an error. It may hold the state "
                "that caused it — the save in play was not touched then.",
    "backup": "What the save in play held before its last write.",
}

#: The list scrolls past this height rather than pushing the title's own
#: buttons off a short screen: two rows and the top of a third, so it is
#: plain that it scrolls. At 150 the returning title measured 699 px tall.
_LIST_HEIGHT = 150


def describe(summary) -> str:
    """One line about a chronicle, from the summary at the head of its file."""
    if not summary:
        return ("This file cannot be read. It may be damaged, or written by "
                "another build of the game.")
    chassis = CHASSIS_BY_ID.get(summary.get("chassis", ""))
    hull = f"{chassis.name} «{summary.get('ship', '')}»" if chassis \
        else f"«{summary.get('ship', '')}»"
    origin = ORIGINS_BY_ID.get(summary.get("origin", ""))
    parts = [stardate(summary.get("day", 0)),
             credits(summary.get("credits", 0)),
             f"{hull} at {summary.get('system') or 'somewhere'}"]
    if origin is not None:
        parts.append(origin.name.lower())
    parts.append(f"seed {summary.get('seed', '?')}")
    ending = summary.get("ending")
    if ending:
        parts.append(f"ended: {_ENDING_NAMES.get(ending, ending)}")
    return " · ".join(parts)


def build(dlg) -> QWidget:
    """The picker, for the title dialog: every chronicle on disk, and a box to
    keep the one in play under a name. Rebuilt in place by `rebuild`."""
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(6)
    entries = slots.listing()
    if entries:
        panel = Panel("Chronicles on this machine")
        rows = QWidget()
        rv = QVBoxLayout(rows)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(8)
        for entry in entries:
            rv.addWidget(_row(dlg, entry))
        rv.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(rows)
        scroll.setMaximumHeight(_LIST_HEIGHT)
        panel.add(scroll)
        v.addWidget(panel)
    v.addWidget(_keeper(dlg))
    return host


def rebuild(dlg) -> None:
    """Swap the picker for a fresh one. Called through `defer`, never from
    inside the click that asked for it — the button that emitted is in the
    picker being replaced."""
    old = dlg.picker
    dlg.picker = build(dlg)
    dlg.picker_slot.addWidget(dlg.picker)
    old.hide()
    old.deleteLater()


def _row(dlg, entry) -> QWidget:
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(8)
    text = QWidget()
    tv = QVBoxLayout(text)
    tv.setContentsMargins(0, 0, 0, 0)
    tv.setSpacing(1)
    kind = entry["kind"]
    tv.addWidget(label(entry["name"] if kind != "slot" else f"«{entry['name']}»",
                       "h3", "" if kind in ("play", "slot") else "osteo"))
    tv.addWidget(label(describe(entry["summary"]), "dim", wrap=True))
    if kind in _WHY_HERE:
        # Always drawn, not a `note`: with hints off a note is hidden, and
        # this is the row's consequence rather than an explanation.
        tv.addWidget(label(_WHY_HERE[kind], "note", wrap=True))
    h.addWidget(text, 1)
    if kind == "play":
        h.addWidget(button("Resume", dlg._resume, kind="primary",
                           tip="Carry on where the save in play left off"))
    else:
        h.addWidget(button("Load", lambda e=entry: load(dlg, e),
                           tip="Make this the chronicle in play"))
    if kind == "slot":
        h.addWidget(button("Delete", lambda e=entry: delete(dlg, e),
                           kind="danger", tip="Remove this slot from disk"))
    return w


def _keeper(dlg) -> QWidget:
    """The box that keeps the chronicle in play under a name of its own."""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.addStretch(1)
    dlg.slot_box = QLineEdit()
    dlg.slot_box.setPlaceholderText("a name for the chronicle in play")
    dlg.slot_box.setFixedWidth(260)
    h.addWidget(dlg.slot_box)
    h.addWidget(button("Keep it as a slot", lambda: keep(dlg),
                       tip="Copy the chronicle in play into a named slot; "
                           "the chronicle in play carries on unchanged"))
    h.addStretch(1)
    # Nothing in play, nothing to keep: a first launch is not shown a box it
    # can only be refused by.
    w.setVisible(dlg.current is not None or state_mod.has_save())
    return w


def _say(dlg, text: str) -> None:
    dlg.problem.setText(text)
    dlg.problem.show()


def load(dlg, entry) -> None:
    """Make a slot (or the crash copy, or the `.bak`) the chronicle in play."""
    in_play = dlg.current is not None or state_mod.has_save()
    if in_play and dlg.dialog(
            "Load another chronicle",
            [f"«{entry['name']}» becomes the chronicle in play and is saved "
             "over the one in play the moment it opens. That one survives "
             "only as the .bak, and the next save after that writes over the "
             ".bak too.",
             note("Keep it as a slot first — the box below — if you want to "
                  "come back to it.")],
            [("Load it", True), ("Belay that", False)]) is not True:
        return
    game = state_mod.load_game(entry["path"])
    if game is None:
        why = state_mod.load_problem() or "no reason given"
        _say(dlg, f"«{entry['name']}» could not be read — {why}. It has been "
                  "moved aside as a .bad file beside where it was, not "
                  "deleted.")
        defer(lambda: rebuild(dlg))
        return
    dlg.game = game
    dlg.accept()


def delete(dlg, entry) -> None:
    """Remove one slot from disk, having said that nothing else holds it."""
    if dlg.dialog(
            "Delete a slot",
            [f"«{entry['name']}» — {describe(entry['summary'])} — is deleted "
             "from disk, with its .bak. There is no other copy and it cannot "
             "be brought back.",
             note("The chronicle in play is not touched.")],
            [("Delete it", True), ("Keep it", False)]) is not True:
        return
    res = slots.delete(entry["name"])
    _say(dlg, res["text"] if res["ok"] else res["why"])
    defer(lambda: rebuild(dlg))


def keep(dlg) -> None:
    """Keep the chronicle in play as a named slot, from the title screen."""
    name = dlg.slot_box.text()
    path = slots.slot_path(name)
    if path is not None and path.is_file() and dlg.dialog(
            "Write over a slot",
            [f"«{path.stem}» already holds "
             f"{describe(slots.read_summary(path))}. It is written over with "
             "the chronicle in play."],
            [("Write over it", True), ("Belay that", False)]) is not True:
        return
    res = slots.save_as(name, dlg.current)
    _say(dlg, res["text"] if res["ok"] else res["why"])
    if res["ok"]:
        defer(lambda: rebuild(dlg))


def save_as(win) -> None:
    """The menu's "Save as…": keep the live chronicle under a name.

    The name is asked inside `win.dialog`, never through the static
    `QInputDialog.getText`, which does not go through `exec` and so cannot be
    seen or dismissed by a driven session — the shipyard's hull name waited
    ten minutes on one.
    """
    g = win.game
    box = QLineEdit(f"{g.ship.name} {stardate(g.day)}")
    box.selectAll()
    if win.dialog("Save as a slot",
                  [note("A copy of this chronicle under a name of its own. "
                        "The chronicle in play carries on, and goes on saving "
                        "itself; the slot stays as it is now until you load it "
                        "from the title screen."), box],
                  [("Keep it", True), ("Belay that", None)]) is not True:
        return
    path = slots.slot_path(box.text())
    if path is not None and path.is_file() and not win.confirm(
            "Write over a slot",
            f"«{path.stem}» already holds "
            f"{describe(slots.read_summary(path))}. It is written over with "
            "this chronicle."):
        return
    res = slots.save_as(box.text(), g)
    win.toast(res["text"] if res["ok"] else res["why"],
              "chloro" if res["ok"] else "warn")
