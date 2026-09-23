"""The yard's cradles and garage: what a hull carries, and what it costs.

The Shipyard screen's fifth tab, in its own module for the same reason
`ui/machineshop.py` is — `ui/yard_view.py` is at the edge of the file limit,
and a cradle has nothing to do with a slot editor.

It owns no rules. Every number and every refusal is `sim/hangar.py`'s: the
cradles fitted and the most the hull will take, a class's cost, matter and
days, what a yard charges to make a craft whole, and what it pays for her.
The Ship screen's Cradle tab (`ui/craft_panel.py`) is where she is *flown*
from; this is where she is bought, mended and sold.

The same tab keeps the **garage** — the surface vehicles a lander carries
down (`sim/vehicles.py`) — for the same reason `sim/hangar.py` holds both:
a rover is not a craft, and the yard side of one is the yard side of the
other.
"""

from __future__ import annotations

from ..core.util import reaction_mass
from ..data.chassis import FAMILY_LABEL, FAMILY_TINT
from ..data.craft import ROLES
from ..sim import craft as craft_sim
from ..sim import hangar as hangar_sim
from .widgets import Card, Panel, Pill, button, label, note, spacer


def bill(cost: dict) -> str:
    """What a thing costs, in the order a captain reads it."""
    bits = []
    if cost.get("credits"):
        bits.append(f"₡{cost['credits']:,.0f}")
    bits += [f"{amount:g} {key}" for key, amount in sorted(cost.items())
             if key != "credits"]
    return " · ".join(bits) or "nothing"


class CraftYard:
    """Builds the tab's panels. Holds no state; the view refreshes it."""

    def __init__(self, view):
        self.view = view

    # ── what is on the cradles now ────────────────────────────────────────

    def cradles(self) -> Panel:
        game = self.view.game
        ship = game.ship
        has, most = hangar_sim.cradles(ship), hangar_sim.most(ship)
        p = Panel(f"Cradles — {has} of {most}")
        p.add(note("A cradle is a deck, a hatch and hands to turn a craft "
                   "round. A hull carries as many as its complement can "
                   "work, and a yard cuts them one at a time."))
        ok, why = hangar_sim.can_fit_cradle(game)
        fit = button(f"Fit another cradle — {bill(hangar_sim.CRADLE_COST)}, "
                     f"{hangar_sim.CRADLE_DAYS} days",
                     self._fit, kind="primary", enabled=ok, why=why)
        fit.setObjectName("yard_cradle_fit")
        p.add(fit)
        for craft in craft_sim.aboard(game):
            p.add(spacer(6))
            p.add(self._aboard(game, craft))
        if not craft_sim.aboard(game):
            p.add(note("Nothing on them. A slip below will lay one down."))
        return p

    def _aboard(self, game, craft):
        kind = craft_sim.kind_of(craft)
        card = Card(selectable=False)
        card.add(label(f"{craft.name} — {kind.name}", "h3",
                       FAMILY_TINT.get(kind.family, "")))
        card.add(label(f"{craft.hp} / {kind.hull} of hull · "
                       f"{reaction_mass(craft.fuel)} · "
                       f"{craft.sorties} sortie"
                       f"{'' if craft.sorties == 1 else 's'}", "sub"))
        quote = hangar_sim.mend_cost(craft)
        mend_ok, mend_why = hangar_sim.can_mend(game, craft)
        mend = button(f"Make her whole — {bill(quote)}" if quote
                      else "She is whole",
                      (lambda _=False, c=craft: self._mend(c)),
                      kind="primary" if mend_ok else "flat",
                      enabled=mend_ok, why=mend_why)
        mend.setObjectName("yard_craft_mend")
        sell_ok, sell_why = hangar_sim.can_sell(game, craft)
        sell = button(f"Sell her — ₡{hangar_sim.worth(craft):,}",
                      (lambda _=False, c=craft: self._sell(c)),
                      kind="flat", enabled=sell_ok, why=sell_why)
        sell.setObjectName("yard_craft_sell")
        card.add(mend)
        card.add(sell)
        if kind.family == "grown":
            card.add(note("Grown: she knits her own hull back in the cradle "
                          "off the hold's biomass, slowly, without a bill."))
        return card

    # ── what a slip will lay down ─────────────────────────────────────────

    def slips(self) -> None:
        view = self.view
        view.col.addWidget(note(
            "A craft is laid down where its family's hulls are — a grown one "
            "at a nursery, a welded one at a shipyard — and it takes the "
            "money, the matter and the days it takes."))
        view.grid([self._card(row) for row in hangar_sim.offers(view.game)],
                  cols=2)

    def _card(self, row) -> Card:
        kind = row["kind"]
        card = Card(selectable=False)
        card.add(label(kind.name, "h3",
                       FAMILY_TINT.get(kind.family, "") if row["ok"] else "dim"))
        card.add(Pill(kind.role, "chloro"))
        card.add(label(f"{FAMILY_LABEL.get(kind.family, kind.family)} · "
                       f"{ROLES[kind.role]}", "sub"))
        card.add(label(kind.blurb, "", wrap=True))
        card.add(note(f"{kind.hull} of hull · {kind.armour} armour · "
                      + (", ".join(f"{name} {dice}d"
                                   for name, dice in kind.guns) or "unarmed")
                      + f" · {kind.seats} seat"
                      f"{'' if kind.seats == 1 else 's'}, "
                      f"{kind.hold_t:g} t hold · Pilot {kind.needs}"))
        card.add(note(f"{bill(kind.cost)} · {row['days']} days in the slip"))
        lay = button("Lay one down" if row["ok"] else row["why"],
                     (lambda _=False, cid=kind.id: self._buy(cid))
                     if row["ok"] else None,
                     kind="primary" if row["ok"] else "flat",
                     enabled=row["ok"], why=row["why"])
        lay.setObjectName(f"yard_craft_buy_{kind.id}")
        card.add(lay)
        return card

    # ── the acts, every one of them the sim's ─────────────────────────────

    def _fit(self) -> None:
        got = hangar_sim.fit_cradle(self.view.game)
        self._said(got, f"Cradle fitted — {got.get('cradles', 0)} on her now.")

    def _buy(self, class_id: str) -> None:
        got = hangar_sim.buy(self.view.game, class_id)
        self._said(got, (f"{got['craft'].name} is yours — {got['days']} days "
                         f"and ₡{got['paid']:,}." if got.get("ok") else ""))

    def _mend(self, craft) -> None:
        got = hangar_sim.mend(self.view.game, craft)
        self._said(got, (f"{craft.name} made whole: {got.get('points', 0)} "
                         f"points, ₡{got.get('paid', 0):,}."))

    def _sell(self, craft) -> None:
        got = hangar_sim.sell(self.view.game, craft)
        self._said(got, f"{craft.name} sold for ₡{got.get('paid', 0):,}.")

    def _said(self, got: dict, text: str) -> None:
        view = self.view
        if not got.get("ok"):
            view.win.toast(got.get("why", "The yard will not."), "warn")
            return
        view.win.toast(text, "good")
        view.game.recompute()
        view.win.refresh()
        view.refresh()

    # ── the garage ────────────────────────────────────────────────────────

    def garage(self) -> None:
        """What crosses ground, and what a yard will build."""
        view = self.view
        game = view.game
        from ..data.vehicles import WHOLE
        from ..sim import vehicles as vehicles_sim
        held = vehicles_sim.aboard(game)
        p = Panel(f"Garage — {len(held)} aboard")
        p.add(note("What a landing party crosses ground in. It rides down in "
                   "the lander's hold against the supplies, so what fits is "
                   "a choice: a day off the ground a machine is made for, a "
                   "day on the ground it will not enter."))
        for machine in held:
            p.add(spacer(6))
            p.add(self._held(game, machine, WHOLE))
        if not held:
            p.add(note("Nothing in the hold. The party walks."))
        view.col.addWidget(p)
        view.col.addWidget(spacer(8))
        view.col.addWidget(note(
            "Built where its family's hulls are, the way a craft is."))
        view.grid([self._machine(row)
                   for row in hangar_sim.vehicle_offers(game)], cols=2)

    def _held(self, game, machine, whole: int) -> Card:
        from ..sim import vehicles as vehicles_sim
        kind = vehicles_sim.kind_of(machine)
        card = Card(selectable=False)
        card.add(label(f"{machine.name} — {kind.name}", "h3",
                       FAMILY_TINT.get(kind.family, "")))
        card.add(label(f"{machine.condition} / {whole} · {machine.days:.0f} "
                       "days driven"
                       + (" · on the ground" if machine.state == "down"
                          else ""), "sub"))
        quote = hangar_sim.vehicle_mend_cost(machine)
        mend_ok, mend_why = hangar_sim.can_mend_vehicle(game, machine)
        mend = button(f"Put it right — {bill(quote)}" if quote
                      else "It is whole",
                      (lambda _=False, m=machine: self._mend_vehicle(m)),
                      kind="primary" if mend_ok else "flat",
                      enabled=mend_ok, why=mend_why)
        mend.setObjectName("yard_vehicle_mend")
        sell_ok, sell_why = hangar_sim.can_sell_vehicle(game, machine)
        sell = button(f"Sell it — ₡{hangar_sim.vehicle_worth(machine):,}",
                      (lambda _=False, m=machine: self._sell_vehicle(m)),
                      kind="flat", enabled=sell_ok, why=sell_why)
        sell.setObjectName("yard_vehicle_sell")
        card.add(mend)
        card.add(sell)
        return card

    def _machine(self, row) -> Card:
        kind = row["kind"]
        card = Card(selectable=False)
        card.add(label(kind.name, "h3",
                       FAMILY_TINT.get(kind.family, "") if row["ok"]
                       else "dim"))
        card.add(label(f"{FAMILY_LABEL.get(kind.family, kind.family)} · "
                       f"{kind.mass_t:g} t · {kind.seats} seats", "sub"))
        card.add(label(kind.blurb, "", wrap=True))
        card.add(note("A day off " + ", ".join(sorted(kind.crosses))
                      + ("; will not enter " + ", ".join(sorted(kind.refuses))
                         if kind.refuses else "")
                      + (" · needs air" if kind.needs_air else "")))
        card.add(note(bill(kind.cost)))
        buy = button("Build one" if row["ok"] else row["why"],
                     (lambda _=False, cid=kind.id: self._buy_vehicle(cid))
                     if row["ok"] else None,
                     kind="primary" if row["ok"] else "flat",
                     enabled=row["ok"], why=row["why"])
        buy.setObjectName(f"yard_vehicle_buy_{kind.id}")
        card.add(buy)
        return card

    def _buy_vehicle(self, class_id: str) -> None:
        got = hangar_sim.buy_vehicle(self.view.game, class_id)
        self._said(got, (f"{got['vehicle'].name} is in the hold — "
                         f"₡{got['paid']:,}." if got.get("ok") else ""))

    def _mend_vehicle(self, machine) -> None:
        got = hangar_sim.mend_vehicle(self.view.game, machine)
        self._said(got, f"{machine.name} put right.")

    def _sell_vehicle(self, machine) -> None:
        got = hangar_sim.sell_vehicle(self.view.game, machine)
        self._said(got, f"{machine.name} sold for ₡{got.get('paid', 0):,}.")
