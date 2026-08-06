"""The heading bar: the stardate, the purse, the meters, and two buttons.

Lifted out of `window.py` when that file crossed five hundred lines. It is
presentation and nothing else — every number it shows is read from the game
each refresh, and it writes nothing.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

# Imported under its own name on purpose. `credits` is a *builtin* — the
# interpreter's easter-egg `_Printer` — so importing it as `cr` and then
# calling `credits(...)` by mistake does not raise NameError. It calls the
# builtin, and the failure surfaces two suites away as
# "_Printer.__call__() takes 1 positional argument but 2 were given".
from ..core.util import credits, mass, pct, stardate
from ..data.chassis import CHASSIS_BY_ID
from ..data.lore import TITLE
from ..sim.ship import cargo_used, hull_pct, is_breached
from . import theme
from .widgets import Bar, Pill, button, label, mono_label


def build(win) -> QWidget:
    bar = QWidget()
    bar.setFixedHeight(54)
    h = QHBoxLayout(bar)
    h.setContentsMargins(16, 6, 16, 6)
    h.setSpacing(20)

    brand = label(TITLE, "", "chloro")
    brand.setStyleSheet(
        f"color: {theme.tint('chloro')}; font-family: '{theme.mono_family()}';"
        "font-size: 11px; letter-spacing: 4px;")
    h.addWidget(brand)

    win.hud_stats: dict[str, QLabel] = {}
    for key, cap in (("date", "Stardate"), ("place", "Position"),
                     ("money", "Treasury"), ("hull", "Hull")):
        block = QWidget()
        v = QVBoxLayout(block)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(1)
        v.addWidget(mono_label(cap))
        val = label("—")
        val.setStyleSheet("font-size: 14px; font-weight: 600;")
        win.hud_stats[key] = val
        v.addWidget(val)
        h.addWidget(block)
    h.addStretch(1)

    win.meters: dict[str, tuple[QLabel, Bar]] = {}
    for key, cap, tintname in (("integrity", "Integrity", "chloro"),
                               ("air", "Air", "lumen"),
                               ("hold", "Hold", "osteo"),
                               ("crew", "Crew", "steel")):
        block = QWidget()
        block.setFixedWidth(132)      # wide enough for "Integrity · 100%"
        v = QVBoxLayout(block)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(3)
        cap_lb = mono_label(cap)
        bar_w = Bar(0, tintname)
        win.meters[key] = (cap_lb, bar_w)
        v.addWidget(cap_lb)
        v.addWidget(bar_w)
        h.addWidget(block)

    win.breach_pill = Pill("breached", "warn")
    win.breach_pill.hide()
    h.addWidget(win.breach_pill)
    # The flight clock, on the one bar every screen shows: the clock is
    # universal now — walking to the Helm no longer stops it — so its state
    # has to be readable from wherever the captain is standing.
    win.clock_pill = Pill("under way", "chloro")
    win.clock_pill.hide()
    h.addWidget(win.clock_pill)
    # Unread despatches, on the one bar every screen shows — the inbox
    # ticked for six passes with no way to know it held anything. A button,
    # not a Pill, because a count you cannot press is a taunt.
    win.despatch_btn = button("✉", lambda: win.go("despatches"), kind="flat",
                              tip="Despatches waiting on the board")
    win.despatch_btn.hide()
    h.addWidget(win.despatch_btn)
    # Instruments pop out into their own windows, so a player can watch
    # heat or the scope while flying rather than switching to a tab.
    h.addWidget(button("▣ Instruments", win.instruments, kind="flat"))
    h.addWidget(button("? Help", win.help_here, kind="flat",
                       tip="Help about the screen you are on"))
    return bar


def refresh(win) -> None:
    g = win.game
    st = g.ship_stats
    ch = CHASSIS_BY_ID[g.ship.chassis]
    win.hud_stats["date"].setText(stardate(g.day))
    win.hud_stats["place"].setText(g.system.name)
    win.hud_stats["money"].setText(credits(g.credits))
    win.hud_stats["hull"].setText(f"{ch.name} «{g.ship.name}»")

    hp = hull_pct(g.ship)
    used = cargo_used(g.ship)
    vals = {
        "integrity": (hp, pct(hp), "warn" if hp < 0.3 else
                      "osteo" if hp < 0.6 else "chloro"),
        "air": (g.ship.o2, pct(g.ship.o2), "warn" if g.ship.o2 < 0.4 else "lumen"),
        "hold": (used / st.cargo if st.cargo else 0,
                 f"{round(used)}/{round(st.cargo)} t", "osteo"),
        "crew": (g.ship.crew / st.berths if st.berths else 0,
                 str(g.ship.crew), "steel"),
    }
    for key, (frac, text, tintname) in vals.items():
        cap, bar = win.meters[key]
        cap.setText(f"{key.title()} · {text}")
        bar.set_value(frac, tintname)
    win.breach_pill.setVisible(is_breached(g.ship))
    from ..sim import comms as comms_sim
    waiting = comms_sim.unread(g)
    if waiting:
        win.despatch_btn.setText(f"✉ {waiting}")
    win.despatch_btn.setVisible(bool(waiting))
    conn = getattr(win, "conn", None)
    wanted = conn is not None and getattr(conn, "clock_on", False)
    if wanted:
        from .flight_clock import on_deck
        scale = int(getattr(win, "time_scale", 1))
        beating = on_deck(win)
        # Held rather than stopped: the pilot's intent survives a walk to the
        # market, and stepping back onto the deck picks it up again.
        win.clock_pill.setText(
            (("clock running" + (f" ×{scale}" if scale > 1 else ""))
             if beating else "clock held — off the deck").upper())
    win.clock_pill.setVisible(bool(wanted))

