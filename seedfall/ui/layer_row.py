"""One hull layer as a row: its name, what kind of layer it is, and how much
of it is left. Shared by the Ship screen and both hulls in a battle, which
had drawn the same row twice, a line apart in wording.

**The critical layer was a colour and nothing else.** The pressure vessel —
the one layer whose loss starts killing the crew — was told from the others
only by an amber name, and a layer shot away only by a red one. Under
deuteranopia amber, green and red close to within a few ΔE of each other, so
both facts vanished. Each now carries a word as well.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..core.util import pct
from .widgets import Bar, Pill, label

#: Wide enough for the "CRITICAL" pill at the theme's 8 px tracked capitals.
PILL_SLOT = 74


def layer_row(layer, name_width: int = 180) -> QWidget:
    frac = layer.hp / layer.max if layer.max else 0
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 1, 0, 1)
    h.setSpacing(6)
    gone = layer.hp <= 0
    name = label(layer.name, "", "warn" if gone else
                 ("osteo" if layer.critical else ""))
    name.setToolTip(getattr(layer, "note", "") or "")
    name.setMinimumWidth(name_width)
    h.addWidget(name)
    # A slot of the same width on every row, filled or not, so the bars of
    # a stack still start in one column and can be compared by eye.
    slot = QWidget()
    slot.setFixedWidth(PILL_SLOT)
    inner = QHBoxLayout(slot)
    inner.setContentsMargins(0, 0, 0, 0)
    if gone:
        inner.addWidget(Pill("gone", "warn"))
    elif layer.critical:
        inner.addWidget(Pill("critical", "osteo"))
    inner.addStretch(1)
    h.addWidget(slot)
    h.addWidget(Bar(frac, "warn" if frac < 0.3 else
                    ("osteo" if layer.critical else "chloro")), 1)
    v = label(pct(frac), "dim")
    v.setFixedWidth(42)
    h.addWidget(v)
    return row
