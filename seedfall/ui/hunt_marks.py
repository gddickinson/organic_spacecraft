"""The rivalry's small marks on other people's screens.

Four things, each hosted by a screen that belongs to somebody else and each
added there as one line, so this is where they live:

- `dark_chip` / `sync_chip` — the transponder on the heading bar;
- `dark_row` — the same switch on the Ship screen, with its price stated;
- `draw_sightings` — fading rings on the Sector Chart where a rival was last
  seen, fainter as the sighting ages (`nemeses.confidence`);
- `battle_header` — who you are fighting, when it is somebody.

Presentation only: every number is `sim/`'s, and the switch is
`running_dark.set_dark`, which logs itself.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPen

from ..sim import nemeses as nem_sim
from ..sim import rivals as rivals_sim
from ..sim import running_dark
from . import theme
from .widgets import Panel, button, label, note


# ── the switch ─────────────────────────────────────────────────────────────

def _toggle(win) -> None:
    game = win.game
    out = running_dark.set_dark(game, not running_dark.dark(game))
    if not out["ok"]:
        win.toast(out["why"], "warn")
    win.refresh()


def dark_chip(win):
    """The heading bar's chip. A button, because a state you cannot change
    from where you read it is a taunt (the despatch button's rule)."""
    chip = button("LIT", lambda: _toggle(win), kind="flat")
    chip.setAccessibleName("Transponder")
    win.dark_chip = chip
    return chip


def sync_chip(win) -> None:
    chip = getattr(win, "dark_chip", None)
    if chip is None:
        return
    game = win.game
    sig = running_dark.signature(game)
    chip.setText("DARK" if running_dark.dark(game) else "LIT")
    chip.setToolTip(running_dark.tradeoff(game))
    chip.setStyleSheet(
        f"color: {theme.tint('warn' if running_dark.dark(game) else 'dim')};"
        f"font-family: '{theme.mono_family()}'; letter-spacing: 1.4px;")
    chip.setAccessibleDescription(sig.blurb)


def dark_row(view) -> Panel:
    """The Ship screen's one row: what the transponder is doing, and the
    switch, with the trade-off on its tooltip and under it."""
    game = view.game
    dark = running_dark.dark(game)
    sig = running_dark.signature(game)
    panel = Panel("Transponder", "warn" if dark else "")
    panel.add_row("Running", sig.name,
                  "warn" if dark else "")
    panel.add_row("Meetings that still find you",
                  f"{running_dark.exposure(game):.0%}")
    panel.add(note(running_dark.tradeoff(game)))
    panel.add_buttons(button(
        "Light her up" if dark else "Run dark", lambda: _toggle(view.win),
        kind="" if dark else "primary", tip=running_dark.tradeoff(game)))
    return panel


# ── the chart ──────────────────────────────────────────────────────────────

def draw_sightings(p, chart, game) -> None:
    """A ring where each rival was last seen, as sure as the sighting is.

    The ring *widens* as it fades: an old sighting is not merely less
    certain, it is somewhere larger — a rival moves about a system a week.
    """
    font = QFont(theme.mono_family(), 7)
    for nem in nem_sim.roster(game):
        if nem.status not in ("active", "wounded") or not nem.last_seen:
            continue
        seen = nem_sim.sighting(game, nem)
        conf = seen["conf"]
        if conf < 0.02:
            continue
        pt = chart._to_screen(game.galaxy.systems[seen["system_id"]])
        radius = 11.0 + min(26.0, seen["age"] / 3.0)
        colour = QColor(theme.tint("bad"))
        colour.setAlpha(int(50 + 190 * conf))
        pen = QPen(colour, 1.6)
        if conf < 0.3:
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(pt, radius, radius)
        p.setFont(font)
        tag = QRectF(pt.x() + radius * 0.72, pt.y() - radius * 0.72 - 12,
                     150, 12)
        p.drawText(tag, Qt.AlignmentFlag.AlignLeft, nem.name.split()[0]
                   + f" · {conf:.0%}")
        p.drawLine(QPointF(pt.x() + radius * 0.70, pt.y() - radius * 0.70),
                   QPointF(tag.x(), tag.bottom()))


# ── the battle ─────────────────────────────────────────────────────────────

def battle_header(col, game, battle) -> None:
    """Under the engagement's title: who this is, and what has gone before."""
    nid = getattr(battle, "nemesis", None)
    nem = (nem_sim.by_id(game, nid) if nid is not None
           else nem_sim.by_ship(game, battle.enemy.ship))
    if nem is None:
        return
    col.addWidget(label(rivals_sim.header(game, nem.id), "sub", "warn",
                        wrap=True))
