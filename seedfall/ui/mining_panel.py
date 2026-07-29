"""The workings: what is in a body, how deep, and how you mean to get it."""

from __future__ import annotations

from ..core.util import pct
from ..data.commodities import BY_ID
from ..data.mining import METHODS_BY_ID
from ..sim import mining
from ..sim.ship import cargo_free
from .widgets import Panel, Pill, TabBar, button, label, mono_label, note, spacer


def build(view, game, body, method_id: str) -> Panel:
    st = game.ship_stats
    p = Panel("The workings")

    if not body.surveyed:
        p.add(note("Nothing is known about what is down there. Survey it "
                   "first; a rig working blind finds the overburden."))
        return p

    found = mining.seams(body)
    if not found:
        p.add(note("Nothing here worth putting a rig on."))
        return p

    method = METHODS_BY_ID.get(method_id, METHODS_BY_ID[mining.DEFAULT_METHOD])
    within = {s["resource"] for s in mining.reachable(body, method.id)}

    p.add(mono_label("Seams"))
    for seam in found:
        reachable = seam["resource"] in within
        p.add_row(f"{BY_ID[seam['resource']].name} · {seam['depth_name']}",
                  f"grade {seam['grade']:.2f}"
                  + ("" if reachable else " · out of reach"),
                  "chloro" if reachable else "dim")
    if body.depleted > 0.01:
        p.add_row("Worked out", pct(body.depleted),
                  "warn" if body.depleted > 0.6 else "")

    p.add(spacer(4), mono_label("How to work it"))
    offers = mining.available(game, body)
    tabs = TabBar([(m.id, m.name) for m, _ok, _why in offers], method.id)
    tabs.changed.connect(view.set_mining_method)
    p.add(tabs)
    p.add(note(method.blurb))

    ok, why = next(((o, w) for m, o, w in offers if m.id == method.id),
                   (True, ""))
    rigs = {"ore": st.mine, "phosphate": st.phos,
            "volatiles": st.drink, "biomass": st.graze}
    perday = {cid: mining.rate_for(body, method.id, cid, rig)
              for cid, rig in rigs.items()}
    # A tenth of a tonne a day is not a seam, it is a rounding error on the
    # readout, and listing "0.0 t/day" makes the panel look broken.
    perday = {k: v for k, v in perday.items() if v >= 0.05}
    p.add_row("Yield", " · ".join(f"{v:.1f} t {k}/day" for k, v in perday.items())
              or "nothing this rig can lift", "chloro" if perday else "warn")
    p.add_row("Reaches", f"{method.name.lower()} — down to "
                         f"{mining.DEPTH_NAMES[method.reach].lower()}")
    # The rig eats the outermost layer, not overall integrity — quoting it as
    # hull loss reads five times worse than it is.
    p.add_row("Wear on the outer layer",
              f"{method.wear * 100 * 30:.1f}% a month" if method.wear else "none",
              "warn" if method.wear >= 0.004 else "")
    # What this method will take out of the body *in total*, and how long the
    # body will last under it. Rate and lifetime pull opposite ways — bore is
    # twice as fast as leach and gets less than half as much out of the seam
    # — and neither number is visible from the other.
    look = mining.prospect(body, method_id, game.ship_stats)
    if look["finished"]:
        p.add(label(f"{body.name} is worked out. There are other bodies.",
                    "", "warn", wrap=True))
    elif look["days"] > 0:
        p.add_row("Body lasts", f"{look['days']:.0f} more days at this rate",
                  "warn" if look["days"] < 60 else "")
        p.add_row("Total still in it, this way",
                  f"{look['total']:.0f} t",
                  "chloro" if look["total"] > 250 else "")
    p.add_row("Takes out of the body", f"×{method.depletion_mul:g}",
              "warn" if method.depletion_mul > 1.5 else "")
    p.add_row("Something goes wrong", pct(method.risk),
              "warn" if method.risk >= 0.2 else "")
    if method.upkeep:
        p.add_row("Consumes",
                  " · ".join(f"{v:g} t {k}/day" for k, v in method.upkeep.items()),
                  "osteo")
    if not ok:
        p.add(label(why, "", "warn"))

    # What a spell actually raises, and whether the hold can take it. The
    # panel used to quote t/day and nothing else, so a captain with a full
    # hold spent sixty days and a third of the body to recover ten tonnes.
    room = cargo_free(game.ship, st)
    p.add(spacer(4), mono_label("If you work it"))
    for spell in (30, 90):
        lasts = mining.days_of_room(body, method.id, st, room, spell)
        raised = mining.raise_rate(body, method.id, st) * lasts
        if lasts <= 0:
            p.add_row(f"{spell} days", "no room in the hold at all", "warn")
            continue
        short = lasts < spell
        p.add_row(f"{spell} days",
                  f"{raised:.0f} t in {lasts} day(s)"
                  + (" — the hold fills first" if short else ""),
                  "warn" if short else "chloro")
    if room < 20:
        p.add(label("There is almost nowhere to put it. Sell or dump "
                    "something before putting a rig down.", "", "warn",
                    wrap=True))

    p.add_buttons(
        button("Work it — 30 days", lambda: view.run_extract(30),
               kind="primary" if ok else "", enabled=ok),
        button("Work it — 90 days", lambda: view.run_extract(90), enabled=ok))
    return p
