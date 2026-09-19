"""The Body tab: what the hull has been through, and what it is becoming.

Hosted by `ui/ship_view.py` as a third tab beside Readout and Plans. Three
things are on it, and each says its price before it is pressed:

- **The channels** as bars toward the next threshold each could still
  cross — what the body is learning, and how far along it is.
- **The emergence**, if one is growing, with both answers costed: what
  encouraging takes from the stores and the day it sets in, and how far
  suppressing starves the channel back. And what happens if you do nothing,
  which is the answer the organism gives for you.
- **What has set in**, with its gain and its cost, and a Prune button that
  is live only alongside a Fleet Hub's gestation bay.

A welded hull gets one panel saying it never adapts, as a trait of the
family rather than an empty screen. Every figure comes from `sim/adaptation`;
this file only lays it out.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..data.adaptations import ADAPTATIONS_BY_ID, CHANNELS, RATE
from ..data.chassis import CHASSIS_BY_ID, FAMILY_LABEL
from ..sim import adaptation as adaptation_sim
from .widgets import Bar, Card, Panel, Pill, body_or, button, label, note

#: How a `Stats` field reads to a captain.
STAT_WORDS = {
    "armour": "armour", "speed": "sublight", "regen": "regrowth",
    "evade": "evasion", "vent": "vent", "conceal": "concealment",
    "heat_cap": "heat cap", "jump": "jump", "morale": "morale",
    "o2_days": "air reserve", "sensor": "sensor reach", "scan": "survey quality",
    "crew_guard": "crew guard", "mine": "ore rate", "phos": "phosphate rate",
    "cargo": "hold",
}


def effect_text(effect) -> str:
    """One effect as a captain reads it: 'armour +1', 'sublight −3%'."""
    word = STAT_WORDS.get(effect.stat, effect.stat)
    if effect.pct:
        value = f"{effect.amount * 100:+.0f}%"
    elif effect.stat == "jump":
        value = f"{effect.amount:+.1f} ly"
    else:
        value = f"{effect.amount:+g}"
    return f"{word} {value.replace('-', '−')}"


def terms(grown) -> str:
    """Gain, then cost, on one line."""
    gain = ", ".join(effect_text(e) for e in grown.gives)
    cost = ", ".join(effect_text(e) for e in grown.takes)
    dose = (f", crew dose ×{grown.dose:.2f}" if grown.dose != 1.0 else "")
    return f"{gain}{dose} · at the cost of {cost}"


def build(view) -> None:
    """Lay the Body tab out on `view`'s column."""
    ship = view.game.ship
    family = CHASSIS_BY_ID[ship.chassis].family
    if not adaptation_sim.adapts(ship):
        panel = Panel("A body that does not remember")
        panel.add(note(f"{FAMILY_LABEL[family]} hulls never adapt. Metal "
                       "and substrate carry what they were built with and "
                       "nothing they have been through — a trait of the "
                       "family. Only grown, hybrid and xeno hulls change "
                       "with use."))
        view.col.addWidget(panel)
        return
    view.col.addWidget(body_or(view.hint(
        "The hull remembers what you do with it. Each channel fills from "
        "the act itself; cross a threshold and something starts to grow. "
        "Feed it, starve it, or leave it — left alone, it sets in anyway.")))
    view.row(_channels(ship), _emerging(view, ship))
    view.col.addWidget(_established(view, ship))


def _channels(ship) -> Panel:
    panel = Panel("What she has been through")
    family = adaptation_sim.family(ship)
    if RATE.get(family, 1.0) != 1.0:
        panel.add(note(f"{FAMILY_LABEL[family]}: the body answers at "
                       f"{RATE[family]:g}× the rate of a grown hull"
                       + (", and what it grows is drawn at random."
                          if family == "xeno" else ".")))
    for channel, (name, unit, what) in CHANNELS.items():
        ahead = adaptation_sim.next_step(ship, channel)
        have = float(ship.stress.get(channel, 0.0))
        if ahead is None and not any(ADAPTATIONS_BY_ID[a].channel == channel
                                     for a in ship.adaptations):
            continue                # nothing this family grows from it
        if ahead is None:
            panel.add_row(name, "everything it grows has grown", "dim")
            continue
        # Below zero is a channel starved back by a suppression or a prune,
        # and it reads as the debt it is rather than as an empty bar.
        reading = (f"{have:,.0f} of {ahead.threshold:,.0f} {unit}"
                   .replace("-", "−"))
        panel.add_row(f"{name} → {ahead.name.lower()}", reading,
                      "dim" if have <= 0 else "")
        bar = Bar(max(0.0, have) / ahead.threshold,
                  "osteo" if have >= ahead.threshold else "chloro")
        bar.setToolTip(f"{name}: {what}."
                       + (" Starved back; it has to be earned again."
                          if have < 0 else ""))
        panel.add(bar)
    return panel


def _emerging(view, ship) -> Panel:
    panel = Panel("Emerging")
    waiting = ship.emerging
    if waiting is None:
        room = adaptation_sim.budget(ship) - len(ship.adaptations)
        panel.add(note("Nothing is growing." if room > 0 else
                       "Nothing is growing, and nothing will: she carries "
                       "all she has room for. A surgeon can make room."))
        return panel
    grows = ADAPTATIONS_BY_ID[waiting["id"]]
    card = Card(selectable=False)
    card.add(label(grows.name, "h3", "osteo"))
    card.add(note(grows.text))
    card.add(label(terms(grows), "", "", wrap=True))
    left = max(0, waiting["due"] - view.game.ship_day)
    card.add(label(("Fed, it sets in" if waiting.get("encouraged")
                    else "Left alone, it sets in")
                   + f" within {left} days.", "", "warn", wrap=True))
    feed = adaptation_sim.encourage_quote(view.game, ship)
    starve = adaptation_sim.suppress_quote(ship)
    if "cost" in feed and not waiting.get("encouraged"):
        bill = ", ".join(f"{n:g} t {k}" for k, n in feed["cost"].items())
        card.add(note(f"Encourage: {bill}; it sets in within "
                      f"{feed['days']} days."))
    if starve["ok"]:
        unit = CHANNELS[starve["channel"]][1]
        card.add(note(f"Suppress: it fades, and the "
                      f"{CHANNELS[starve['channel']][0].lower()} channel "
                      f"starves back — {starve['relearn']:,.0f} {unit} before "
                      "it offers this again."))
    panel.add(card)
    panel.add_buttons(
        button("Encourage", lambda: _act(view, adaptation_sim.encourage),
               kind="primary", enabled=feed["ok"], why=feed["why"]),
        button("Suppress", lambda: _act(view, adaptation_sim.suppress),
               kind="danger", enabled=starve["ok"], why=starve["why"]))
    return panel


def _established(view, ship) -> Panel:
    room = adaptation_sim.budget(ship)
    panel = Panel(f"Set in — {len(ship.adaptations)} of {room}")
    if not ship.adaptations:
        panel.add(note(f"Nothing yet. A {CHASSIS_BY_ID[ship.chassis].name} "
                       f"has room for {room}."))
        return panel
    for aid in ship.adaptations:
        grown = ADAPTATIONS_BY_ID.get(aid)
        if grown is None:
            continue
        quote = adaptation_sim.prune_quote(view.game, aid, ship)
        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 4, 0, 0)
        line.addWidget(label(grown.name, "h3", "chloro"))
        line.addWidget(Pill(CHANNELS[grown.channel][0].lower(), "dim"))
        line.addStretch(1)
        line.addWidget(button("Prune", lambda a=aid: _act(
            view, lambda g: adaptation_sim.prune(g, a)), kind="danger",
            enabled=quote["ok"], why=quote["why"]))
        panel.add(row, label(terms(grown), "", "", wrap=True))
    panel.add(note(f"A surgeon at a Fleet Hub's gestation bay prunes one for "
                   f"{quote['credits']:,} credits and {quote['days']} days, "
                   "and the channel starves back as if it had been "
                   "suppressed."))
    dose = adaptation_sim.dose_multiplier(ship)
    if dose != 1.0:
        panel.add_row("Crew radiation dose", f"×{dose:.2f}", "lumen")
    return panel


def _act(view, act) -> None:
    """Run one answer through the sim; it logs itself. Then redraw."""
    res = act(view.game)
    if not res.get("ok"):
        view.win.toast(res.get("why", "No."), "warn")
        return
    view.win.save()
    view.win.refresh()
