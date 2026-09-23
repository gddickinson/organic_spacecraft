"""The trading house: its account, its lines, its masters and its books.

Hosted as the "Trading house" tab on Holdings (`ui/empire_view.py`). Nothing
here decides anything: the charter's terms, a master's fee, a line's forecast
and the ledger's totals are the sim's (`sim/freightlines`, `sim/masters`,
`sim/lineforecast`, `sim/lineledger`), and every button is one of their doors.
Opening a line is `ui/house_dialog.py`.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QSpinBox, QWidget

from ..core.util import credits as cr
from ..core.util import pct
from ..data.commodities import BY_ID
from ..data.freightlines import CHARTER_UPKEEP, INSURANCE_LOADING, KINDS
from ..data.factions import FACTIONS_BY_ID
from ..sim import freightlines as lines_sim
from ..sim import haulers as haulers_sim
from ..sim import lineledger as ledger
from ..sim import lineroute
from ..sim import masters as masters_sim
from ..sim.ship import hull_pct
from .widgets import Panel, Pill, button, label, mono_label, note, spacer

#: What each phase of a trip is called on the lines table.
PHASES = {"ferry": "on passage to her home port", "load": "loading at home",
          "out": "laden, outbound", "sell": "alongside to sell",
          "home": "in ballast, homeward", "idle": "stood down"}


def build(view) -> None:
    """Everything on the tab, into the view's column."""
    g = view.game
    house = getattr(g, "house", None)
    if house is None:
        view.col.addWidget(_charter(view))
        view.col.addWidget(_haulers(view))
        return
    view.col.addWidget(_lines(view, house))
    view.row(_account(view, house), _masters(view, house))
    view.row(_haulers(view), _ledger(view, house))


# ── the charter ─────────────────────────────────────────────────────────────

def _charter(view) -> Panel:
    g = view.game
    terms = lines_sim.charter_terms(g)
    p = Panel("Charter a trading house", "osteo")
    p.add(note("A house puts your own haulers on freight lines: two ports, "
               "a good, a rule for buying and one for selling, and a master "
               "to sail her. The lines trade through the real counters while "
               "you are elsewhere — they pay the quay, move the price, and "
               "wear out a route that is worked too hard."))
    if "fee" in terms:
        power = FACTIONS_BY_ID.get(terms["power"])
        p.add_row("Chartered at", terms["port"])
        p.add_row("Issued by", power.name if power else terms["power"])
        p.add_row("Fee, once", cr(terms["fee"]), "osteo")
        p.add_row("Upkeep, a month", cr(terms["upkeep"]), "osteo")
    if terms["ok"]:
        p.add_buttons(button(f"Charter the house · {cr(terms['fee'])}",
                             lambda: _do_charter(view, terms), kind="primary"))
    else:
        p.add(label(terms["why"], "", "warn", wrap=True))
    return p


def _do_charter(view, terms) -> None:
    if not view.win.confirm(
            "Charter a trading house",
            f"{cr(terms['fee'])} now to {terms['port']}, and "
            f"{cr(terms['upkeep'])} a month from the house account for as "
            "long as you hold it."):
        return
    _act(view, lines_sim.charter(view.game))


def _act(view, res: dict) -> bool:
    """Every button's ending: say why not, or redraw."""
    if not res.get("ok"):
        view.win.toast(res.get("why", "No."), "warn")
        return False
    view.win.refresh()
    return True


# ── the account ─────────────────────────────────────────────────────────────

def _account(view, house) -> Panel:
    g = view.game
    power = FACTIONS_BY_ID.get(house.power)
    p = Panel("The house")
    p.add(note(f"Chartered at {g.galaxy.systems[house.chartered_at].name} "
               f"by {power.name if power else house.power}, on day "
               f"{house.founded}. Upkeep {cr(CHARTER_UPKEEP)} a month."))
    p.add_row("Account", cr(house.account),
              "chloro" if house.account >= lines_sim.kept(house) else "osteo")
    p.add_row("Kept back on a sweep", cr(lines_sim.kept(house)))
    owed = house.owed_charter + house.owed_hands
    if owed > 0:
        p.add_row("In arrears", cr(owed), "warn")
    books = ledger.reconcile(g, house)
    p.add_row("Books", "balance" if books["balanced"] and books["purse_ok"]
              else "do not balance", "chloro" if books["balanced"] else "warn")
    p.add_row("Paid in · swept out", f"{cr(house.purse_out)} · "
                                     f"{cr(house.purse_in)}")
    amount = QSpinBox()
    amount.setRange(0, 9_999_999)
    amount.setSingleStep(1000)
    amount.setValue(10_000)
    amount.setObjectName("house_amount")
    amount.setAccessibleName("Credits to pay in or draw out")
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(amount)
    h.addWidget(button("Pay in", lambda: _act(
        view, lines_sim.deposit(g, amount.value()))))
    # Nothing to draw is not an act to offer: the button was lit on an empty
    # account and answered "the account is empty".
    h.addWidget(button("Draw out", lambda: _act(
        view, lines_sim.withdraw(g, amount.value())),
        enabled=house.account > 0,
        why="Nothing in the account to draw out."))
    h.addStretch(1)
    p.add(row)
    p.add_buttons(
        button(f"Sweep monthly: {'on' if house.sweep else 'off'}",
               lambda: _act(view, lines_sim.set_terms(g, sweep=not house.sweep)),
               tip="Once a month, everything above what is kept back goes to "
                   "your purse."),
        button(f"Insured: {'yes' if house.insured else 'no'}",
               lambda: _act(view, lines_sim.set_terms(
                   g, insured=not house.insured)),
               tip=f"Each sailing pays a premium of {INSURANCE_LOADING:g} "
                   "times the expected claim; a lost cargo or hull is paid "
                   "for out of the underwriting power's purse."))
    reserve = QSpinBox()
    reserve.setRange(0, 9_999_999)
    reserve.setSingleStep(1000)
    reserve.setValue(round(house.reserve))
    reserve.setObjectName("house_reserve")
    reserve.setAccessibleName("Reserve kept for wages and upkeep")
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(label("Reserve", "dim"))
    h.addWidget(reserve)
    h.addWidget(button("Set", lambda: _act(
        view, lines_sim.set_terms(g, reserve=reserve.value()))))
    h.addStretch(1)
    p.add(row)
    p.add(note("Cargoes are bought only with what is above the reserve: it "
               "is the payroll's."))
    return p


# ── the lines ───────────────────────────────────────────────────────────────

def _lines(view, house) -> Panel:
    g = view.game
    p = Panel("Lines")
    free = [m for m in house.masters if m.line_id is None]
    ready = [s for s, ok, _why in haulers_sim.haulers(g) if ok]
    why = ("" if free and ready else
           "Hire a master first." if not free else
           "No hauler is free — lay one down at a yard.")
    p.add_buttons(button("New line…", lambda: _new_line(view),
                         kind="primary", enabled=not why, why=why))
    shown = [l for l in house.lines if l.active] + [
        l for l in reversed(house.lines) if not l.active][:3]
    if not shown:
        p.add(note("No lines yet. A line is chosen from the freight desk's "
                   "own ranking, with its forecast shown before you commit."))
    for line in shown:
        p.add(spacer(4))
        p.add(_line_card(view, house, line))
    return p


def _line_card(view, house, line) -> QWidget:
    g = view.game
    systems = g.galaxy.systems
    good = BY_ID.get(line.good)
    hull = lineroute.hull_of(g, line)
    master = lineroute.master_of(g, line)
    box = Panel()
    top = QWidget()
    h = QHBoxLayout(top)
    h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(label(f"{systems[line.origin].name} → "
                      f"{systems[line.dest].name} · "
                      f"{good.name if good else line.good}", "h3",
                      "chloro" if line.active else "dim"))
    h.addStretch(1)
    h.addWidget(Pill(PHASES.get(line.phase, line.phase),
                     "lumen" if line.active else "dim"))
    box.add(top)
    cadence = ("continuous" if not line.cadence
               else f"every {line.cadence} days")
    rules = [f"{line.tonnes:,} t", f"buy under {cr(line.max_buy)}"
             if line.max_buy else "buy at any price",
             f"sell over {cr(line.min_sell)}" if line.min_sell
             else "sell for what it fetches", cadence]
    box.add_row("Rules", " · ".join(rules))
    box.add_row("Master", (f"{master.name}, {master.rating} · loyalty "
                           f"{pct(master.loyalty)}") if master else "—")
    box.add_row("Hauler", (f"{hull.name} · {pct(hull_pct(hull))} hull")
                if hull else "lost", "" if hull else "bad")
    last = ("—" if not line.last else
            f"{line.last} · {cr(line.last_net or 0)} · day {line.last_day}")
    box.add_row("Last trip", last,
                "bad" if line.last in ("lost", "robbed", "seized") else "")
    recent = ledger.net(ledger.recent(g, house, line.id))
    lifetime = ledger.net(ledger.lifetime(house, line.id))
    box.add_row("Profit, 90 days · lifetime",
                f"{cr(recent)} · {cr(lifetime)}",
                "chloro" if lifetime >= 0 else "osteo")
    if line.waiting:
        box.add(label(f"Waiting: {line.waiting}.", "", "warn", wrap=True))
    if line.active:
        box.add_buttons(button(
            "Stand down" if not line.stopping else "Standing down at next port",
            lambda _=False, ln=line: _act(view, lines_sim.stop(g, ln)),
            enabled=not line.stopping, why="She stands down at her next port."))
    return box


def _new_line(view) -> None:
    from .house_dialog import NewLineDialog
    dlg = NewLineDialog(view)
    dlg.exec()
    if dlg.opened:
        view.win.refresh()


# ── masters ─────────────────────────────────────────────────────────────────

def _masters(view, house) -> Panel:
    g = view.game
    p = Panel("Masters")
    if not house.masters:
        p.add(note("Nobody yet. Masters sign on at a recruit desk — any "
                   "Station or Fleet Hub — for a month's wage."))
    for master in house.masters:
        where = ("on a line" if master.line_id is not None else "free")
        where += f" · signed day {master.hired}"
        p.add_row(f"{master.name} · {master.rating}",
                  f"{cr(master.wage)}/mo · loyalty {pct(master.loyalty)} · "
                  f"{where}", "warn" if master.loyalty < 0.35 else "")
        if master.owed >= 1:
            p.add_buttons(button(
                f"Pay back wages · {cr(master.owed)}",
                lambda _=False, m=master: _act(view,
                                               masters_sim.pay_owed(g, m))))
        terms = masters_sim.dismiss_terms(g, master)
        if terms["ok"]:
            p.add_buttons(button(
                f"Pay off · {cr(terms['cost'])}",
                lambda _=False, m=master: _dismiss(view, m), kind="danger"))
    pool = masters_sim.pool_at(g, g.system)
    if pool:
        p.add(spacer(4), mono_label(f"Looking for a hull at {g.system.name}"))
        for cand in pool:
            ok, why = masters_sim.can_hire(g, cand)
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(label(f"{cand.name} · {cand.rating} · skill "
                              f"{cand.skill:.2f}", "dim"))
            h.addStretch(1)
            h.addWidget(button(
                f"Sign on · {cr(cand.wage)}/mo",
                lambda _=False, m=cand: _act(view, masters_sim.hire(g, m)),
                enabled=ok, why=why))
            p.add(row)
    return p


def _dismiss(view, master) -> None:
    terms = masters_sim.dismiss_terms(view.game, master)
    if not terms["ok"]:
        view.win.toast(terms["why"], "warn")
        return
    if view.win.confirm("Pay a master off",
                        f"{master.name} leaves with {cr(terms['cost'])}: "
                        "what they are owed and a month besides."):
        _act(view, masters_sim.dismiss(view.game, master))


# ── haulers and the books ───────────────────────────────────────────────────

def _haulers(view) -> Panel:
    g = view.game
    p = Panel("Haulers")
    rows = haulers_sim.haulers(g)
    if not rows:
        p.add(note("No hull built to carry freight. A TENDER is the cheapest "
                   "the Yards weld; a DRAYHORSE out-carries anything. Fit a "
                   "drive: a bare hull will not reach its neighbours."))
    for ship, ok, why in rows:
        p.add_row(ship.name, "free" if ok else why, "chloro" if ok else "dim")
    p.add_buttons(button("Lay down a hauler", lambda: view.win.go("yard")))
    for chassis_id in haulers_sim.USED_FIT:
        terms = haulers_sim.used_terms(g, chassis_id)
        if "price" not in terms:
            continue
        name = terms["chassis"].name
        p.add_buttons(button(
            f"Buy a used {name} · {cr(terms['price'])}",
            lambda _=False, cid=chassis_id, t=terms: _buy(view, cid, t),
            enabled=terms["ok"], why=terms["why"],
            tip=(f"{terms['chassis'].cargo} t of hold, sold with an ion "
                 f"drive and {pct(terms['hull'])} of her hull.")))
    return p


def _buy(view, chassis_id: str, terms: dict) -> None:
    if view.win.confirm("Buy a used hull",
                        f"{cr(terms['price'])} to the yard at {terms['port']} "
                        f"for a used {terms['chassis'].name}, berthed here."):
        _act(view, haulers_sim.buy_used(view.game, chassis_id))


def _ledger(view, house) -> Panel:
    g = view.game
    p = Panel("Ledger")
    recent = ledger.recent(g, house)
    life = ledger.lifetime(house)
    p.add_row("", "90 days · lifetime")
    for kind, name in KINDS:
        if kind not in life:
            continue
        p.add_row(name, f"{cr(recent.get(kind, 0.0))} · {cr(life[kind])}",
                  "chloro" if life[kind] > 0 else "")
    p.add_row("Clear profit", f"{cr(ledger.net(recent))} · "
                              f"{cr(ledger.net(life))}", "lumen")
    p.add(note(f"The charter itself cost {cr(house.fee)} from the purse. "
               "Money paid in and swept out is the captain's own, and is not "
               "counted as profit."))
    return p
