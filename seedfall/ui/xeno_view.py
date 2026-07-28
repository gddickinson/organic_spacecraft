"""The xenology desk — what the four cultures left, and how far you understand it.

This is not the research tree. Nothing here can be reasoned out: every entry is
dug up, bought or taken, and the only thing you can do at a desk is take relics
apart and see what falls out.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..core.util import credits as cr
from ..core.util import num, pct
from ..data.xenotech import CULTURES, CULTURES_BY_ID, XENOTECH_BY_ID, by_culture
from ..sim import xeno as xeno_sim
from ..sim.fieldwork import analyse, has_laboratory
from .widgets import (Panel, Pill, View, button, label, mono_label, note, spacer)


class XenoPanel:
    """Mixin-style helper so the research screen can host this as a tab."""


def build_xeno(view: View) -> None:
    """Render the xenology desk into `view`'s column."""
    g = view.game
    relics = g.ship.cargo.get("xenolith", 0)
    lab = has_laboratory(g)
    done = len(xeno_sim.incorporated(g))
    total = len(XENOTECH_BY_ID)

    view.col.addWidget(note(
        f"{done} of {total} alien technologies incorporated. Understanding comes "
        "from digging a site, buying somebody else's notes at a port, or taking "
        "them off a hull that had them first — never from the research tree."))

    desk = Panel("Laboratory")
    desk.add(label(
        "Relics aboard can be taken apart for understanding. A polyp laboratory, "
        "a CORAL reef or a reactivated array in-system makes the work markedly "
        "more productive.", "", wrap=True))
    desk.add_row("Relics in the hold", f"{round(relics)}")
    desk.add_row("Laboratory available", "yes" if lab else "no",
                 "chloro" if lab else "warn")
    view.col.addWidget(desk)

    for culture in CULTURES:
        techs = by_culture(culture.id)
        got, count = xeno_sim.culture_standing(g, culture.id)
        seen = [t for t in techs if xeno_sim.is_known(g, t.id)]

        panel = Panel(f"{culture.name} — {got}/{count}", culture.tint)
        panel.add(label(culture.blurb, "", wrap=True))
        if not seen:
            panel.add(note("Nothing of theirs has been found yet. Survey the "
                           f"kinds of world they favour: {', '.join(culture.sites)}."))
            view.col.addWidget(panel)
            continue

        for tech in techs:
            if not xeno_sim.is_known(g, tech.id):
                panel.add(spacer(3))
                panel.add(label("· an unrecovered technology", "dim"))
                continue
            panel.add(spacer(4))
            head = QWidget()
            h = QHBoxLayout(head)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(label(tech.name, "h3", culture.tint))
            h.addStretch(1)
            if xeno_sim.is_incorporated(g, tech.id):
                h.addWidget(Pill("incorporated", "chloro"))
            elif not xeno_sim.prerequisites_met(g, tech):
                missing = ", ".join(XENOTECH_BY_ID[r].name for r in tech.requires
                                    if not xeno_sim.is_incorporated(g, r))
                h.addWidget(Pill(f"needs {missing}", "warn"))
            panel.add(head)
            panel.add(label(tech.blurb, "", wrap=True))
            if tech.grants:
                panel.add(note(tech.grants))

            if not xeno_sim.is_incorporated(g, tech.id):
                pr = xeno_sim.progress(g, tech.id)
                panel.add_bar(pr, culture.tint)
                panel.add_row(f"{round(xeno_sim.study_of(g, tech.id))} / "
                              f"{num(tech.study)} points", pct(pr))
                row = QWidget()
                rh = QHBoxLayout(row)
                rh.setContentsMargins(0, 0, 0, 0)
                rh.setSpacing(6)
                for n in (1, 3):
                    rh.addWidget(button(
                        f"Analyse {n} relic{'s' if n > 1 else ''}",
                        lambda _=False, tid=tech.id, k=n: _analyse(view, tid, k),
                        enabled=relics >= n))
                rh.addWidget(button(
                    "Decode a recording",
                    lambda _=False, tid=tech.id, nm=culture.name:
                        _decode(view, tid, nm),
                    tip="Work the emission by hand. Free, and it can be worth "
                        "more than a crate of relics."))
                rh.addStretch(1)
                panel.add(row)
        view.col.addWidget(panel)


def _decode(view: View, tech_id: str, subject: str) -> None:
    view.win.views["decoding"].begin(subject, tech_id)
    view.win.go("decoding")


def _analyse(view: View, tech_id: str, count: int) -> None:
    res = analyse(view.game, tech_id, count)
    if not res.get("ok"):
        view.win.toast(res["why"], "warn")
        return
    if view.win.check_ending():
        return
    tech = res["tech"]
    lines = [f"{res['used']} relic(s) reduced to fragments and notes over "
             f"{res['days']} days: {round(res['points'])} points toward "
             f"{tech.name}."]
    if not res["lab"]:
        lines.append(note("Done on a workbench in the hold. A proper laboratory "
                          "would have got far more out of them."))
    if res["incorporated"]:
        lines.append(f"{tech.name} is now yours. {tech.grants}")
    view.win.dialog("Analysis" + (" — incorporated" if res["incorporated"] else ""),
                    lines, [("Log it", None)])
    view.win.refresh()
