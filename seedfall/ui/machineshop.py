"""The machine shop: where a captain actually gets a robot, and sends it away.

Written because the first robots cycle shipped a roster, a law and a panel and
**no door**. `sim/robots.build`, `post` and `scrap` existed and nothing in the
game called any of them, so twenty classes of machine were a catalogue entry a
player could read and never own. That is the same defect this project keeps
finding one layer up — a system the simulation runs and the interface cannot
reach — and it is worse here, because the reachability guard counts a call from
a check as a call.

Its own module rather than another tab's worth of `ui/yard_view.py`, which was
already at 438 lines.

**What the shop has to say**, and the reason it is not just a shopping list:
a machine's rating is not what it gives you. So the build cards quote the
autonomy rung beside the level, and the posting control quotes what the machine
would be worth *at the place you are about to send it* — before you send it,
not after.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QWidget

from ..data.chassis import FAMILY_LABEL, FAMILY_ORDER, FAMILY_TINT
from ..data.robots import (DUTIES, ROBOTS, ROBOTS_BY_ID, autonomy_name,
                           autonomy_note, autonomy_tint, by_family)
from ..sim import robots as robots_sim, telepresence as tele_sim
from .robots_panel import lag_line, where_line
from .thumb3d import Thumb
from .widgets import Card, Panel, Pill, button, label, note, spacer


def cost_line(klass) -> str:
    """What one costs, in the order a captain reads it."""
    bits = []
    if klass.cost.get("credits"):
        bits.append(f"₡{klass.cost['credits']:,.0f}")
    bits += [f"{amount:g} {key}" for key, amount in sorted(klass.cost.items())
             if key != "credits"]
    return " · ".join(bits) or "nothing"


def postings(game) -> list[tuple[str, str]]:
    """Everywhere a machine can be sent from here, as (posting, label).

    Only holdings in **this** system, because a machine is carried to its
    posting rather than teleported to it — `sim/robots.post` refuses the rest
    and this list is the same door read forwards, so the picker cannot offer
    what the sim will turn down.
    """
    out = [(robots_sim.ABOARD, "Aboard — standing a watch"),
           (robots_sim.STOWED, "Stowed in the hold")]
    for colony in getattr(game, "colonies", []):
        if colony.system_id == game.system.id and getattr(colony, "online", False):
            out.append((f"colony:{colony.id}", f"Post to {colony.name}"))
    return out


def worth_at(game, robot, posting: str) -> float:
    """What this machine would be worth if you sent it there — **before** you
    do. The whole decision is which rung survives the distance, and a screen
    that only tells you afterwards is not offering the decision at all."""
    was = robot.posting
    try:
        robot.posting = posting
        return tele_sim.effective(game, robot)
    finally:
        robot.posting = was


class MachineShop:
    """Builds the two panels. Holds no state; the view refreshes it."""

    def __init__(self, view):
        self.view = view

    # ── what you can build ────────────────────────────────────────────────

    def picker(self) -> None:
        view = self.view
        game = view.game
        view.col.addWidget(note(
            f"{len(ROBOTS)} classes. Every one is rated on the ladder real "
            "spacecraft are — and that rating, not the level, decides where it "
            "is worth putting. A teleoperated frame is the best hand you own "
            "alongside and a statue at one AU."))
        for family in FAMILY_ORDER:
            classes = by_family(family)
            if not classes:
                continue
            view.col.addWidget(spacer(6))
            view.col.addWidget(label(f"{FAMILY_LABEL[family]} — {len(classes)}",
                                     "h3", FAMILY_TINT[family]))
            view.grid([self._card(game, k) for k in classes], cols=3)

    def _card(self, game, klass) -> Card:
        ok, why = robots_sim.can_build(game, klass.id)
        card = Card(selectable=False)
        card.add(Thumb("robot", klass.id, height=88))
        card.add(label(klass.name, "h3",
                       FAMILY_TINT[klass.family] if ok else "dim"))
        card.add(Pill(autonomy_name(klass.autonomy),
                      autonomy_tint(klass.autonomy)))
        # The species name where there is one, and the yard where there is
        # not. The first draft fell back to the opening sentence of the blurb,
        # which is the line printed immediately below it — so every fabricated
        # card said the same thing twice.
        card.add(label(f"{klass.binomial} · {FAMILY_LABEL[klass.family]}"
                       if klass.binomial else FAMILY_LABEL[klass.family],
                       "sub"))
        card.add(label(klass.blurb, "", wrap=True))
        does = [DUTIES[d][0] for d in klass.duties if d in DUTIES]
        if klass.stat:
            does.insert(0, f"stands {klass.stat}")
        card.add(note(f"Level {klass.level} · {klass.mass_t:g} t · "
                      + (", ".join(does) or "no posting")))
        card.add(note(f"Build {cost_line(klass)} · keeps " + ", ".join(
            f"{amount:.3g} {key}"
            for key, amount in sorted(klass.upkeep.items())) + " a day"))
        card.add(button("Build" if ok else why,
                        (lambda _=False, cid=klass.id: self._build(cid))
                        if ok else None,
                        kind="primary" if ok else "flat",
                        tip=autonomy_note(klass.autonomy)))
        return card

    def _build(self, class_id: str) -> None:
        game = self.view.game
        made = robots_sim.build(game, class_id)
        if made is None:
            self.view.win.toast(robots_sim.can_build(game, class_id)[1])
            return
        game.add_log(f"{ROBOTS_BY_ID[class_id].name} {made.name} came off the "
                     "shop floor.", "good")
        game.recompute()
        self.view.refresh()

    # ── what you own, and where it goes ───────────────────────────────────

    def roster(self) -> Panel:
        game = self.view.game
        mine = robots_sim.owned(game)
        panel = Panel(f"Machines — {len(mine)}")
        if not mine:
            panel.add(note("Nothing built yet."))
            return panel
        places = postings(game)
        for robot in mine:
            klass = ROBOTS_BY_ID[robot.class_id]
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            line.addWidget(label(f"{robot.name} · {klass.name}"))
            line.addStretch(1)
            line.addWidget(Pill(autonomy_name(klass.autonomy),
                                autonomy_tint(klass.autonomy)))
            picker = QComboBox()
            for posting, said in places:
                # Quoted for *this* machine at *that* place. Two machines in
                # the same list will read differently against the same holding,
                # which is the point.
                got = worth_at(game, robot, posting)
                picker.addItem(f"{said} — lvl {got:.2f}", posting)
            here = [p for p, _ in places]
            picker.setCurrentIndex(here.index(robot.posting)
                                   if robot.posting in here else 0)
            picker.activated.connect(
                lambda index, r=robot, box=picker: self._post(
                    r, box.itemData(index)))
            line.addWidget(picker)
            line.addWidget(button("Scrap",
                                  lambda _=False, r=robot: self._scrap(r),
                                  kind="flat"))
            panel.add(row)
            panel.add(label(f"{where_line(game, robot)} · "
                            f"{lag_line(game, robot)}"
                            + (" · stopped" if robot.broken else ""),
                            "note", "warn" if robot.broken else ""))
        return panel

    def _post(self, robot, posting: str) -> None:
        game = self.view.game
        ok, why = robots_sim.post(game, robot, posting)
        if not ok:
            self.view.win.toast(why)
        else:
            game.recompute()
        self.view.refresh()

    def _scrap(self, robot) -> None:
        game = self.view.game
        name = robot.name
        back = robots_sim.scrap(game, robot)
        got = ", ".join(f"{amount:g} {key}" for key, amount in sorted(back.items()))
        game.add_log(f"{name} was broken up" + (f" for {got}." if got else "."),
                     "warn")
        game.recompute()
        self.view.refresh()
