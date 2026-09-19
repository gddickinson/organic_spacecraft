"""The memoir on the Aftermath screen, and the Hall of Captains on the title.

Both are `sim/memoir`'s pages drawn, nothing more: the memoir is the one
kept on the chronicle, the Hall is the file beside the save. The title's
Hall is folded to one line — a returning title measured 699 px tall with the
chronicle list in it (`ui/chronicle_picker._LIST_HEIGHT`), and the Hall is
for reading once in a while, not every launch.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from ..sim import memoir
from .widgets import Panel, button, label, note

#: The Hall window's list is at least twice this tall (the chronicle
#: list's own height, `ui/chronicle_picker._LIST_HEIGHT`).
HALL_HEIGHT = 150


def page(game) -> Panel | None:
    """The memoir, if the chronicle has one."""
    held = memoir.page_of(game)
    if not held:
        return None
    p = Panel("The memoir", "chloro" if held["outcome"] == "triumph"
              else "warn")
    p.setObjectName("memoir")
    for i, line in enumerate(held["lines"]):
        p.add(label(line, "h3" if i == 0 else "", wrap=True))
    p.add(note("Kept in the Hall of Captains, beside the save; it outlasts "
               "this chronicle and every one after it."))
    return p


def _line(row: dict) -> str:
    titles = f" «{row['titles'][0]}»" if row.get("titles") else ""
    return (f"{row.get('ship', '?')}{titles} — {row.get('rank', '?')}, "
            f"{row.get('score', 0)} renown · {row.get('ending', '?')} on day "
            f"{row.get('day', 0)} · seed {row.get('seed', '?')}")


def hall(dlg) -> QWidget:
    """The title's Hall: one line, and the whole Hall in a window of its own
    (unfolded in place it took the title to 793 px against 680)."""
    rows = memoir.hall()
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(0, 0, 0, 0)
    if not rows:
        return host
    panel = Panel(f"Hall of Captains · {len(rows)} "
                  f"{'career' if len(rows) == 1 else 'careers'}")
    panel.setObjectName("hall")
    panel.add(label(_line(rows[0]), "dim", wrap=True))
    more = button("Read the Hall", lambda: read_hall(dlg), kind="flat")
    more.setObjectName("hall_open")
    panel.add(more)
    v.addWidget(panel)
    return host


def read_hall(dlg) -> None:
    """Every career in the Hall, newest first, in a scrolling window."""
    listing = QWidget()
    lv = QVBoxLayout(listing)
    lv.setContentsMargins(0, 0, 0, 0)
    for row in memoir.hall():
        lv.addWidget(label(_line(row), "h3", wrap=True))
        for text in row.get("lines", [])[1:]:
            lv.addWidget(label(text, "dim", wrap=True))
    lv.addStretch(1)
    scroll = QScrollArea()
    scroll.setObjectName("hall_list")
    scroll.setWidgetResizable(True)
    scroll.setWidget(listing)
    scroll.setMinimumHeight(HALL_HEIGHT * 2)
    dlg.dialog("Hall of Captains", [scroll], (("Close", None),), width=720)
