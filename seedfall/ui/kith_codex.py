"""The Kith on other people's screens: the Codex page and the chart's mark.

Two things, each hosted by a screen that belongs to somebody else and added
there in a line or two:

- `codex` — the Codex's "The Kith" tab, once they have been met: who they
  are, where things stand, and **the lexicon page** — every sign drawn, with
  its meaning once it is understood well enough to be read;
- `draw` — a ring of small lights on the Sector Chart round every gathering
  you have been to or been told the way to (`KithState.charted`).

Presentation only: every figure is `sim/kith`'s.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPen

from ..data import kith as data
from ..sim import kith as kith_sim
from . import theme
from .kith_panel import glyph_row, tint_for
from .widgets import Panel, Pill, label, note

#: The chart's mark: this many lights round a gathering, this far out.
LIGHTS = 7
RING = 11.0


def shown(game) -> bool:
    """Is there a Kith tab in the Codex yet? Only once they have been met."""
    return kith_sim.met(game)


def codex(view) -> None:
    """The Codex's Kith tab."""
    game = view.game
    state = kith_sim.ensure(game)
    progress = kith_sim.progress(game)
    who = Panel("The Kith", "lumen")
    who.add(label(data.BLURB, "", wrap=True))
    who.add_row("First sighting", f"day {state.met_day}")
    who.add_row("Standing", f"{kith_sim.standing(game):+.0f}")
    who.add_row("Exchanges", f"{progress['exchanges']}")
    who.add_row("Misread", f"{state.misreads} of {state.acts} acts",
                "warn" if state.misreads else "dim")
    who.add_row("Gatherings charted", f"{len(state.charted)}")
    who.add_row("Accord", f"sung on day {state.accord}" if progress["accord"]
                else "not yet", "chloro" if progress["accord"] else "dim")
    view.col.addWidget(who)

    page = Panel("The lexicon")
    page.add(note("A sign has no sound, so it has no name: it is drawn. Its "
                  f"meaning is written here once it is understood to "
                  f"{data.TRADE_NEEDS:.0%}."))
    for domain_id, name in data.DOMAINS.items():
        value = kith_sim.domain(game, domain_id)
        page.add(label(f"{name} · {value:.0%}", "h3", tint_for(value)))
        page.add(glyph_row(game, domain_id))
        for sign in (s for s in data.SIGNS if s.domain == domain_id):
            have = kith_sim.comprehension(game, sign.id)
            page.add_row(f"{sign.glyph}  {sign.id}" if have >= data.TRADE_NEEDS
                         else f"{sign.glyph}  ?",
                         f"{sign.gloss} · {have:.0%}"
                         if have >= data.TRADE_NEEDS else f"{have:.0%}",
                         tint_for(have))
    view.col.addWidget(page)

    songs = Panel("Songs worked on the bench")
    songs.add(Pill(f"{state.decoded} solved", "chloro" if state.decoded
                   else "dim"))
    for phrase, known in sorted(kith_sim.phrases(game),
                                key=lambda row: -row[1]):
        glyphs = " ".join(data.SIGNS_BY_ID[s].glyph for s in phrase.signs)
        songs.add_row(glyphs, phrase.gloss if known >= data.ACCORD_NEEDS
                      else f"{known:.0%} understood", tint_for(known))
    view.col.addWidget(songs)


def draw(chart, p, game) -> None:
    """A ring of lights round each charted gathering on the chart's tab."""
    state = getattr(game, "kith", None)
    if state is None or not state.charted:
        return
    colour = QColor(theme.tint("lumen"))
    p.setPen(QPen(colour, 1.2))
    p.setBrush(colour)
    for sid in state.charted:
        system = game.galaxy.systems[sid]
        if getattr(system, "region", "") != chart.region:
            continue
        at = chart._to_screen(system)
        for i in range(LIGHTS):
            angle = 2 * math.pi * i / LIGHTS
            p.drawEllipse(QPointF(at.x() + RING * math.cos(angle),
                                  at.y() + RING * math.sin(angle)), 1.4, 1.4)
    p.setBrush(Qt.BrushStyle.NoBrush)
