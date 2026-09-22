"""The cradle deck: what she carries, who may fly it, and the way out.

The Ship screen's own tab. Every number is `sim/craft.py`'s and every button
is a call into it: the pilot list is `craft.pilots` with the reason anybody
is not on it, and launching hands the chronicle a sortie and opens the
cockpit (`ui/craft_window.py`).
"""

from __future__ import annotations

from ..core.util import reaction_mass
from ..data.craft import ROLES
from ..sim import craft as craft_sim
from .widgets import Panel, Pill, button, label, note


def build(view) -> None:
    """The tab: one panel a craft, and the flight line under them."""
    game = view.game
    carried = craft_sim.aboard(game)
    if not carried:
        view.col.addWidget(Panel("No cradles").add(
            note("This hull carries no small craft. A yard fits a cradle "
                 "and sells you something to put in it.")))
        return
    for craft in carried:
        view.col.addWidget(_craft(view, game, craft))


def _craft(view, game, craft) -> Panel:
    kind = craft_sim.kind_of(craft)
    out = craft.state == "out"
    p = Panel(f"{craft.name} — {kind.name}",
              "warn" if out else "")
    p.add(label(kind.blurb, "note", wrap=True))
    p.add_row("What she is", f"{kind.role.title()}: {ROLES[kind.role]}")
    p.add_row("Hull", f"{craft.hp} / {kind.hull}",
              "warn" if craft.hp * 3 < kind.hull else "")
    p.add_row("Reaction mass", f"{reaction_mass(craft.fuel)} of "
                               f"{reaction_mass(kind.fuel_t)}")
    p.add_row("Guns", ", ".join(f"{name} ({dice}d)" for name, dice in
                                kind.guns) or "none")
    p.add_row("Seats", f"{kind.seats}, and {kind.hold_t:g} t of hold")
    p.add_row("Certificate", f"Pilot {kind.needs}")
    if craft.sorties:
        p.add_row("Flown", f"{craft.sorties} sortie"
                           f"{'' if craft.sorties == 1 else 's'}, "
                           f"{craft.hours:.1f} h, {craft.struck} run"
                           f"{'' if craft.struck == 1 else 's'} made")
    if out:
        p.add(label(f"Out, with {craft_sim.name_of(game, craft.pilot)} "
                    f"flying — {craft_sim.out_km(game):,.1f} km off.", "",
                    "warn", wrap=True))
        open_ = button("Open the cockpit", lambda: _cockpit(view),
                       kind="primary")
        open_.setObjectName("craft_cockpit")
        home_ok, home_why = craft_sim.can_recover(game)
        home = button("Back on the cradle", lambda: _recover(view),
                      enabled=home_ok, why=home_why)
        home.setObjectName("craft_home")
        p.add_buttons(open_, home)
        return p
    p.add(note("Who takes her out — a Pilot ticket and nothing else, and "
               "whoever goes is off their station until she is back."))
    for key, name, what, ok, why in craft_sim.pilots(game, craft):
        b = button(f"Launch — {name}",
                   lambda _=False, k=key: _launch(view, craft, k),
                   kind="primary" if ok else "flat", enabled=ok, why=why)
        b.setObjectName(f"craft_launch_{key.replace(':', '_')}")
        p.add(b)
        p.add(label(what + ("" if ok else f" · {why}"), "note",
                    "" if ok else "warn", wrap=True))
    return p


def _launch(view, craft, key: str) -> None:
    got = craft_sim.launch(view.game, craft, key)
    if not got.get("ok"):
        view.win.toast(got.get("why", "She stays on the cradle."), "warn")
        view.refresh()
        return
    view.win.toast(f"{craft.name} away — {got['who']} flying.", "good")
    view.refresh()
    _cockpit(view)


def _cockpit(view) -> None:
    from .craft_window import open_cockpit
    open_cockpit(view.win)


def _recover(view) -> None:
    got = craft_sim.recover(view.game)
    view.win.toast(got.get("why") or "Back on the cradle.",
                   "warn" if not got.get("ok") else "good")
    view.refresh()
