"""The screens, in order, and the key that reaches each.

Both `ui/window.py` and `sim/manual.py` need this, and they are on opposite
sides of the layer rule — the manual may not import Qt — so the table lives
here, where both can read it.

Keeping the keys here rather than deriving them from position also fixes a
real defect: the window assigned `str(i + 1)` for the first nine and `"0"` for
*everything after*, so when an eleventh screen was added the Codex and the
Aftermath both bound `0` and one of them was unreachable from the keyboard.
"""

from __future__ import annotations

#: (screen id, rail label, key). Keys must be unique — `test_manual` checks.
SCREENS = (
    ("map", "✦  Sector", "1"),
    ("system", "◉  System", "2"),
    ("helm", "◐  Helm", "3"),
    ("pilot", "▲  Pilot", "p"),
    ("port", "⌂  Port", "4"),
    ("ship", "❖  Ship", "5"),
    ("yard", "⚙  Shipyard", "6"),
    ("tech", "⌘  Research", "7"),
    ("empire", "◈  Holdings", "8"),
    ("diplomacy", "⚖  Diplomacy", "9"),
    ("codex", "§  Codex", "0"),
    ("legacy", "∞  Aftermath", "-"),
    ("help", "?  Help", "?"),
)

NAV = tuple((sid, label) for sid, label, _key in SCREENS)
NAV_KEYS = tuple((key, label.split("  ", 1)[-1]) for _sid, label, key in SCREENS)
KEY_FOR = {sid: key for sid, _label, key in SCREENS}
