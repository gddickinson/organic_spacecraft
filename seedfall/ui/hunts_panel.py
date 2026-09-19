"""The Hunts tab on the Law screen: who has a grudge, what the board pays, and
a search whose odds you read before you spend a day on it.

The docket beside it is what the powers have on you; this is the other
direction — who you have, and who has you. Everything a button here promises
is quoted by the same `sim/hunts` function its act spends (`search_odds` and
`search`, `buy_off_terms` and `buy_off`, `trophy_terms` and the two trophy
acts), which is the rule the rest of the Law screen already keeps with
`tribunal.case` and `plead`.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..core.util import credits as cr
from ..data.factions import FACTIONS_BY_ID
from ..data.nemeses import TRAITS_BY_ID
from ..data.part_types import BANDS
from ..sim import hunts as hunts_sim
from ..sim import nemeses as nem_sim
from ..sim import rivals as rivals_sim
from ..sim import running_dark
from .thumb3d import Thumb
from .widgets import Panel, Pill, TabBar, button, label, note, spacer

#: The spans the desk quotes a search over, in days.
SPANS = (1, 3, 5, 10)

STATUS_TINT = {"active": "warn", "wounded": "osteo", "allied": "chloro",
               "dead": "dim", "retired": "dim"}


def _short(power: str) -> str:
    return getattr(FACTIONS_BY_ID.get(power), "short", power or "—")


def tabbed(view) -> bool:
    """The Docket/Hunts bar under the Law heading. Builds the Hunts tab and
    answers True when it is the one showing; the docket is the view's own."""
    tab = getattr(view, "hunts_tab", "docket")
    bar = TabBar([("docket", "Docket"), ("hunts", "Hunts")], tab)
    bar.changed.connect(lambda tid: _switch(view, tid))
    view.col.addWidget(bar)
    if tab != "hunts":
        return False
    build(view)
    return True


def _switch(view, tid: str) -> None:
    view.hunts_tab = tid
    view.refresh_later()          # the bar's own button dies in the rebuild


def build(view) -> None:
    g = view.game
    view.col.addWidget(label(running_dark.tradeoff(g), "sub", wrap=True))
    rivals = [n for n in nem_sim.roster(g)
              if n.status in ("active", "wounded", "allied")]
    if rivals:
        view.row(*[_dossier(view, n) for n in rivals[:2]])
        if len(rivals) > 2:
            view.row(*[_dossier(view, n) for n in rivals[2:4]])
    else:
        view.col.addWidget(Panel("Nobody has your name").add(
            "No rival is out there yet. They come out of what you do: a raider "
            "you ran from, a posted price, a Concordat captain you let go, the "
            "cartel you sold under, a Bloom hull you did not finish."))
    view.row(_search(view), _board(view))
    trophies = [r for r in nem_sim.state(g).trophies if r["state"] == "held"]
    if trophies:
        view.col.addWidget(_trophies(view, trophies))
    gone = [n for n in nem_sim.roster(g) if n.status in ("dead", "retired")]
    if gone:
        view.col.addWidget(note("Closed files: " + "; ".join(
            f"{n.name} ({n.status})" for n in gone[-6:]) + "."))
    view.buttons(button("Back to the chart", lambda: view.win.go("map")))


# ── the dossiers ───────────────────────────────────────────────────────────

def _dossier(view, nem) -> Panel:
    g = view.game
    arch = nem_sim.archetype(nem)
    panel = Panel(nem.name, STATUS_TINT.get(nem.status, ""))
    top = QWidget()
    across = QHBoxLayout(top)
    across.setContentsMargins(0, 0, 0, 0)
    if nem.ship is not None:
        across.addWidget(Thumb("hull", nem.ship.chassis_def, height=74,
                               width=150))
    words = QWidget()
    down = QVBoxLayout(words)
    down.setContentsMargins(0, 0, 0, 0)
    down.addWidget(label(f"{arch.name} · level {nem.level} · {nem.status}",
                         "", STATUS_TINT.get(nem.status, "")))
    down.addWidget(note(f"{arch.origin} {arch.style}"))
    pills = QWidget()
    row = QHBoxLayout(pills)
    row.setContentsMargins(0, 0, 0, 0)
    for tid in nem.traits:
        pill = Pill(TRAITS_BY_ID[tid].name, "osteo")
        pill.setToolTip(TRAITS_BY_ID[tid].blurb)
        row.addWidget(pill)
    row.addStretch(1)
    down.addWidget(pills)
    across.addWidget(words, 1)
    panel.add(top)
    seen = nem_sim.sighting(g, nem)
    panel.add_row("Last seen", seen["where"] if seen["age"] is None else
                  f"{seen['where']}, {seen['age']} d ago · {seen['conf']:.0%}",
                  "warn" if seen["conf"] >= 0.5 else "")
    panel.add_row("Their grudge · yours",
                  f"{nem.grudge.get('theirs', 0):.0f} · "
                  f"{nem.grudge.get('yours', 0):.0f}")
    if nem.bounty:
        panel.add_row("Price on the hull",
                      f"{cr(nem.bounty['reward'])} · "
                      f"{_short(nem.bounty['issuer'])}", "osteo")
    if nem.status == "wounded":
        panel.add_row("Back from the yard", f"in {max(0, nem.back_on - g.day)} d")
    if nem.status == "allied":
        panel.add(note("Spared, and says they owe you. Whether they mean it "
                       "is the one thing a dossier cannot tell you."))
    for day, where, _result, words_ in nem.history[-3:]:
        place = g.galaxy.systems[int(where)].name
        panel.add(note(f"Day {day} · {place} — {words_}."))
    terms = hunts_sim.buy_off_terms(g, nem.id)
    if nem_sim.archetype(nem).buy_off and nem.status != "allied":
        panel.add_buttons(button(
            f"Pay them off — {cr(terms['price'])}", _act(
                view, lambda: hunts_sim.buy_off(g, nem.id)),
            enabled=terms["ok"], why=terms["why"],
            tip="A better fee than the cartel's. They take it and go."))
    return panel


# ── the search ─────────────────────────────────────────────────────────────

def _targets(g) -> list:
    """What there is to look for here: paper you hold, and rivals whose last
    sighting is this system."""
    keys = [(r["key"], r["name"]) for r in hunts_sim.taken(g)]
    for nem in nem_sim.active(g):
        key = f"nemesis:{nem.id}"
        if key not in {k for k, _n in keys} and nem.last_seen \
                and int(nem.last_seen[0]) == g.location_id:
            keys.append((key, nem.name))
    return keys


def _search(view) -> Panel:
    g = view.game
    days = getattr(view, "hunt_days", 3)
    band = getattr(view, "hunt_band", rivals_sim.preferred_band(g.ship))
    panel = Panel(f"Search {g.system.name}")
    spans = TabBar([(str(d), f"{d} d") for d in SPANS], str(days))
    spans.changed.connect(lambda d: _set(view, "hunt_days", int(d)))
    bands = TabBar([(str(i), name) for i, name in enumerate(BANDS)], str(band))
    bands.changed.connect(lambda b: _set(view, "hunt_band", int(b)))
    panel.add(label("Days to spend", "dim"), spans,
              label("Open at", "dim"), bands)
    targets = _targets(g)
    if not targets:
        panel.add(note("Nothing on your paper here. Take a price off a "
                       "board, or wait for word of a rival in this system."))
        return panel
    for key, name in targets:
        quote = hunts_sim.search_odds(g, key, days)
        panel.add(spacer(2), label(name, "h3"))
        panel.add_row("If it is here", f"{quote['find']:.0%} in {quote['days']} "
                      f"d · {quote['hiding']}")
        panel.add_row("Is it here", f"{quote['here']:.0%}",
                      "warn" if quote["here"] < 0.3 else "")
        panel.add_buttons(button(
            f"Search — {quote['odds']:.0%}", _hunt(view, key, days, band),
            kind="primary" if quote["here"] > 0 else "",
            tip=("You pick the band; dark, you also fire first."
                 if running_dark.dark(g) else
                 "You pick the band. Run dark to fire first as well.")))
    return panel


def _set(view, name: str, value) -> None:
    setattr(view, name, value)
    view.refresh_later()


def _hunt(view, key: str, days: int, band: int):
    def go():
        out = hunts_sim.search(view.game, key, days, band)
        if not out.get("ok"):
            view.win.toast(out.get("why", "Refused."), "warn")
            return
        if out.get("encounter"):
            view.win.begin_combat(out["encounter"], "law")
            return
        view.win.toast(out["text"])
        view.win.refresh()
    return go


# ── the board ──────────────────────────────────────────────────────────────

def _board(view) -> Panel:
    g = view.game
    rows = hunts_sim.board(g)
    panel = Panel("The board" + (f" — {g.system.port.name}"
                                 if g.system.port else ""))
    if not rows:
        panel.add(note("No board here. Prices are posted on a quay." if
                       g.system.port is None else
                       "Nothing posted within reach of this quay."))
        return panel
    for row in rows:
        age = "" if not row["age"] else f", {row['age']} d old"
        panel.add(label(f"{row['name']} — {cr(row['reward'])}", "h3"))
        panel.add(note(f"{_short(row['issuer'])} paper · last seen at "
                       f"{row['where']}{age} · {row['conf']:.0%}"))
        panel.add_buttons(button(
            "Held" if row["taken"] else "Take the paper",
            _act(view, lambda k=row["key"]: hunts_sim.take(g, k)),
            enabled=not row["taken"], why="You already hold it.",
            tip="Comes with a fresh sighting, and lapses in "
                f"{hunts_sim.PAPER_DAYS} days."))
    return panel


def _trophies(view, held: list) -> Panel:
    g = view.game
    panel = Panel("Trophies", "osteo")
    for record in held:
        terms = hunts_sim.trophy_terms(g, record["id"])
        panel.add(label(terms["name"] or record["id"], "h3"))
        what = (f"Fits in place of the {terms['replaces']}."
                if terms["replaces"] else "Fits an empty mount.")
        panel.add(note(what if terms["ok"] else terms["why"]))
        panel.add_buttons(
            button("Fit it", _act(view, lambda t=record["id"]:
                                  hunts_sim.mount_trophy(g, t)),
                   enabled=terms["ok"], why=terms["why"]),
            button(f"Sell — {cr(terms['worth'])}",
                   _act(view, lambda t=record["id"]:
                        hunts_sim.sell_trophy(g, t)),
                   enabled=terms["sellable"], why="No yard here."))
    return panel


def _act(view, fn):
    def go():
        out = fn()
        view.win.toast(out.get("text") or out.get("why", ""),
                       "" if out.get("ok") else "warn")
        view.win.refresh()
    return go


def rival_lines(said: dict) -> list:
    """What the aftermath card adds when the fight was somebody's, or paid
    somebody's price (`rival_ends.settle`'s answer)."""
    lines = []
    if said.get("name"):
        lines.append(f"{said['name']}: {said['words'].lower()}."
                     + (f" Back from the yard by day {said['back_on']}."
                        if said.get("back_on") else ""))
    if said.get("bounty"):
        lines.append(f"{_short(said['issuer'])} pays the price: "
                     f"{cr(said['bounty'])}.")
    if said.get("trophy"):
        lines.append(f"Cut out of the wreck: {said['trophy']}.")
    if said.get("plundered"):
        lines.append("They took a quarter of your hold with them.")
    return lines
