"""The GESTALT visual identity, as Qt palette and stylesheet.

Dark-field-microscopy ground, three tissue colours (chlorophyll green,
bioluminescent cyan, osteoid amber) plus two outsider colours, an old-style
serif for display and a wide-tracked monospace for every label.
"""

from __future__ import annotations

from PyQt6.QtGui import QFontDatabase

GROUND = "#0a1512"
PANEL = "#0e1c18"
PANEL2 = "#122320"
LINE = "#25382f"
LINE2 = "#334d41"

INK = "#e2f0e8"
INK2 = "#a9c2b6"
INK3 = "#7c9689"
#: A button that cannot be pressed. **Not the flat button's colours** — they
#: were the same pair (INK3 on LINE), so 88 flat buttons, Disengage and Brace
#: among them, read as switched off. Dimmer than INK3, and drawn with a dashed
#: border so the difference is a shape as well as a shade.
INK_OFF = "#4f6459"

TINTS = {
    "chloro": "#54cf7c",
    "lumen": "#4fd6d0",
    "osteo": "#e6ac6d",
    "steel": "#8fb3d9",
    "xeno": "#b98fe0",
    "warn": "#e0685f",
    "dim": INK3,
    "ink": INK,
    # The log's two commonest kinds — 61 call sites between them — and
    # neither was in this table, so a completed contract, a lost colony and
    # neutral chatter all rendered the same grey. The game's only
    # notification channel could not tell good news from bad.
    "good": "#54cf7c",
    "bad": "#e0685f",
}

FACTION_TINT = {
    "charter": "chloro", "concordat": "steel", "freeholds": "osteo",
    "sanhedrin": "xeno", "abyssals": "lumen", "bloom": "warn",
}


def tint(name: str) -> str:
    return TINTS.get(name, INK2)


def _first_family(candidates: list[str], fallback: str) -> str:
    have = set(QFontDatabase.families())
    for c in candidates:
        if c in have:
            return c
    return fallback


def serif_family() -> str:
    return _first_family(
        ["Iowan Old Style", "Palatino Linotype", "Book Antiqua", "Palatino",
         "Georgia", "Times New Roman"], "serif")


def mono_family() -> str:
    return _first_family(
        ["SF Mono", "Menlo", "Cascadia Mono", "Consolas", "DejaVu Sans Mono",
         "Courier New"], "monospace")


def stylesheet() -> str:
    return f"""
QWidget {{
    background: {GROUND};
    color: {INK};
    font-family: "{serif_family()}";
    font-size: 14px;
}}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {GROUND}; border: 0; }}
/* **What sits on a panel, a card or a dialog shows it through.** The rule
   above paints every QWidget with the ground, so each label and each row
   inside a panel drew a dark band across the panel's lighter fill. `.QWidget`
   is the plain container only — inputs keep their own fill below. */
QFrame[role="panel"] .QWidget, QFrame[role="panel"] QLabel,
QFrame[role="panel"] QCheckBox, QFrame[role="panel"] QRadioButton,
QFrame[role="card"] .QWidget, QFrame[role="card"] QLabel,
QFrame[role="card"] QCheckBox, QFrame[role="card"] QRadioButton,
QDialog .QWidget, QDialog QLabel, QDialog QCheckBox, QDialog QRadioButton,
QFrame[role="panel"] QScrollArea {{
    background: transparent;
}}

QLabel[role="h1"] {{ font-size: 26px; font-weight: 600; }}
QLabel[role="h2"] {{ font-size: 19px; font-weight: 600; }}
QLabel[role="h3"] {{ font-size: 16px; font-weight: 600; }}
QLabel[role="sub"]  {{ color: {INK2}; font-style: italic; }}
QLabel[role="note"] {{ color: {INK3}; font-size: 12px; font-style: italic; }}
QLabel[role="dim"]  {{ color: {INK3}; }}
QLabel[role="label"] {{
    font-family: "{mono_family()}"; font-size: 9px; color: {INK3};
    letter-spacing: 2px; text-transform: uppercase;
}}

QFrame[role="panel"] {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 3px;
}}
QFrame[role="card"] {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 3px;
}}
QFrame[role="card"]:hover {{ border-color: {LINE2}; }}
QFrame[role="card"]:focus {{ border-color: {TINTS['lumen']}; }}
QFrame[role="hr"] {{ background: {LINE}; max-height: 1px; border: 0; }}

QPushButton {{
    font-family: "{mono_family()}"; font-size: 9px; letter-spacing: 1.4px;
    text-transform: uppercase;
    color: {INK}; background: transparent;
    border: 1px solid {LINE2}; border-radius: 11px;
    padding: 6px 14px;
}}
QPushButton:hover:enabled {{ border-color: {TINTS['chloro']}; color: {TINTS['chloro']}; }}
QPushButton[kind="primary"] {{ border-color: {TINTS['chloro']}; color: {TINTS['chloro']}; }}
QPushButton[kind="danger"] {{ border-color: {TINTS['warn']}; color: {TINTS['warn']}; }}
QPushButton[kind="flat"] {{ border-color: {LINE2}; color: {INK2}; }}
QPushButton:focus {{ border-color: {INK}; }}
/* Last, so it beats the kinds above: a disabled primary button used to keep
   its green and read as the thing to press. */
QPushButton:disabled, QPushButton[kind="primary"]:disabled,
QPushButton[kind="danger"]:disabled, QPushButton[kind="flat"]:disabled {{
    color: {INK_OFF}; border: 1px dashed {LINE};
}}

QPushButton[kind="nav"] {{
    text-align: left; border: 0; border-left: 2px solid transparent;
    border-radius: 0; padding: 9px 14px; color: {INK2}; font-size: 9px;
}}
QPushButton[kind="nav"]:hover {{ color: {INK}; background: {PANEL}; }}
QPushButton[kind="nav"]:focus {{ color: {INK}; background: {PANEL2}; }}
QPushButton[kind="nav"]:checked {{
    color: {TINTS['chloro']}; border-left: 2px solid {TINTS['chloro']};
    background: {PANEL};
}}

QPushButton[kind="tab"] {{
    border: 0; border-bottom: 2px solid transparent; border-radius: 0;
    padding: 7px 12px; color: {INK3};
}}
QPushButton[kind="tab"]:hover {{ color: {INK}; }}
QPushButton[kind="tab"]:focus {{ color: {INK}; background: {PANEL2}; }}
QPushButton[kind="tab"]:checked {{
    color: {TINTS['chloro']}; border-bottom: 2px solid {TINTS['chloro']};
}}

QLineEdit, QSpinBox, QComboBox {{
    background: {PANEL2}; border: 1px solid {LINE}; border-radius: 3px;
    padding: 4px 8px; color: {INK};
    font-family: "{mono_family()}"; font-size: 11px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {TINTS['chloro']}; }}
QComboBox QAbstractItemView {{
    background: {PANEL2}; border: 1px solid {LINE2};
    selection-background-color: {LINE2}; color: {INK};
}}

QListWidget {{
    background: {PANEL2}; border: 1px solid {LINE}; border-radius: 3px;
    color: {INK}; font-family: "{mono_family()}"; font-size: 11px;
}}
QListWidget:focus {{ border-color: {TINTS['chloro']}; }}
QListWidget::item {{ padding: 2px 4px; }}
QListWidget::item:selected {{ background: {LINE2}; color: {INK}; }}

QScrollBar:vertical {{ background: transparent; width: 9px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {LINE2}; border-radius: 4px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {INK3}; }}
QScrollBar:horizontal {{ background: transparent; height: 9px; }}
QScrollBar::handle:horizontal {{ background: {LINE2}; border-radius: 4px; min-width: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QToolTip {{
    background: {PANEL2}; color: {INK}; border: 1px solid {LINE2};
    padding: 6px 8px;
}}
QDialog {{ background: {PANEL}; }}
QMenuBar {{ background: {GROUND}; color: {INK2}; }}
QMenuBar::item:selected {{ background: {PANEL2}; color: {INK}; }}
QMenu {{ background: {PANEL2}; color: {INK}; border: 1px solid {LINE2}; }}
QMenu::item:selected {{ background: {LINE}; }}
"""
