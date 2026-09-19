"""A deep anchor, where you are standing at one: what relighting it takes.

Hosted on the System screen, which is where a captain is when they are at the
anchor — the work is done there, and paid for there. The three parts of the
project are stated before any of them is spent, with what each still lacks,
and the Bloom's side of the bargain beside them: a relit gate is a road, and
growth crosses it a season at a time like any ring the captain woke.

Every number is `sim/relight.preview`'s, and the button does
`sim/relight.relight`, which spends exactly that — `test_reaches` performs
one and compares.
"""

from __future__ import annotations

from ..core.util import credits as cr
from .widgets import Panel, button, label, mono_label, note, spacer


def build(view, g) -> Panel | None:
    """The deep anchor here, or the far end of one. None if neither."""
    from ..sim import relight as relight_sim
    rid = relight_sim.region_at(g, g.location_id)
    if rid is not None:
        if relight_sim.is_open(g, rid):
            return _through(view, g, rid)
        return _project(view, g, rid)
    back = _far_end(g)
    return _way_back(view, g, back) if back is not None else None


def _far_end(g):
    """The opened region whose far end stands here, if any."""
    for opened in getattr(g.galaxy, "regions", ()) or ():
        if opened.entry_id == g.location_id:
            return opened
    return None


def _project(view, g, rid: str) -> Panel:
    from ..sim import relight as relight_sim
    said = relight_sim.preview(g, rid)
    spec = said["region"]
    p = Panel(f"A deep anchor — {spec.name} beyond it", "xeno")
    p.add(label(spec.character + " " + spec.blurb, "", wrap=True))
    p.add(spacer(4), mono_label("Relighting it"))
    _steps(p, said["steps"])
    p.add_row("Credits", f"{cr(said['credits'])} (have {cr(g.credits)})",
              "" if g.credits >= said["credits"] else "warn")
    for cid, need in said["goods"].items():
        have = said["have"][cid]
        p.add_row(f"{need} t {cid}", f"have {have:g}",
                  "" if have >= need else "warn")
    p.add_row("Work", f"{said['days']} days at the anchor")
    p.add(note(said["lanes"]))
    risk = said["bloom"]
    p.add(spacer(3), mono_label("What it opens the other way"))
    if risk["carries"]:
        p.add(label(f"This system is {round(risk['bloom'] * 100)}% overgrown. "
                    f"Lit, the gate hands {risk['per_season']:.3f} of it to "
                    f"{spec.name} every season, and more as it grows.",
                    "", "warn", wrap=True))
    else:
        p.add(note(f"Nothing here is growing hard enough to cross yet (under "
                   f"{round(risk['floor'] * 100)}%). Once something is, a lit "
                   f"gate hands {round(risk['share'] * 100)}% of it across "
                   "every season, like any ring you wake."))
    p.add_buttons(button(f"Relight it — {said['days']} d",
                         lambda _=False: _relight(view, g, rid),
                         kind="primary" if said["ok"] else "",
                         enabled=said["ok"], why=said["why"]))
    if said["why"]:
        p.add(note(said["why"]))
    return p


def _through(view, g, rid: str) -> Panel:
    from ..sim import relight as relight_sim
    opened = next(r for r in g.galaxy.regions if r.id == rid)
    spec = relight_sim.preview(g, rid)["region"]
    entry = g.galaxy.systems[opened.entry_id]
    p = Panel(f"The deep anchor is burning — {spec.name}", "xeno")
    p.add(note(f"Relit on day {opened.opened_day}. Nobody's gate, so nobody's "
               "toll; growth crosses it as easily as you do."))
    p.add(_step_button(view, g, entry.id, f"Through to {entry.name}"))
    return p


def _way_back(view, g, opened) -> Panel:
    anchor = g.galaxy.systems[opened.anchor_id]
    p = Panel(f"The far end of the deep gate — {opened.name}", "xeno")
    p.add(note(f"The Verge is on the other side of it, at {anchor.name}. "
               "No toll either way."))
    p.add(_step_button(view, g, anchor.id, f"Back to {anchor.name}"))
    return p


def _step_button(view, g, dest: int, text: str):
    from ..sim import gates as gates_sim
    said = gates_sim.quote(g, dest)
    return button(text, lambda _=False: _step(view, g, dest),
                  kind="primary" if said["ok"] else "", enabled=said["ok"],
                  why=said["why"])


def beyond(view, g, target) -> Panel:
    """For the chart: a star past the rim from where the ship stands."""
    from ..sim import relight as relight_sim
    from ..sim import regions as regions_sim
    names = regions_sim.names(g)
    p = Panel("Beyond the rim")
    here, there = regions_sim.region_of(g.system), regions_sim.region_of(target)
    p.add(label(f"{target.name} is in {names[there]}, and you are in "
                f"{names[here]}. No drive reaches across; a deep gate does, "
                "instantly, for nothing.", "", wrap=True))
    ways = [r for r in g.galaxy.regions if r.id in (here, there)]
    for opened in ways:
        anchor = g.galaxy.systems[opened.anchor_id]
        entry = g.galaxy.systems[opened.entry_id]
        p.add_row(relight_sim.preview(g, opened.id)["region"].name,
                  f"{anchor.name} ⇄ {entry.name}")
        if g.location_id in (anchor.id, entry.id):
            dest = entry.id if g.location_id == anchor.id else anchor.id
            p.add(_step_button(view, g, dest,
                               f"Through to {g.galaxy.systems[dest].name}"))
    return p


def sealed(view, g, rid: str) -> Panel:
    """For the chart's tab of a region nobody has opened."""
    from ..sim import relight as relight_sim
    said = relight_sim.preview(g, rid)
    spec = said["region"]
    p = Panel(f"{spec.name} — dark")
    p.add(label(spec.blurb, "", wrap=True))
    anchor = said["anchor"]
    if anchor is not None:
        p.add(label(f"The deep anchor stands at {anchor.name}.", "", "xeno",
                    wrap=True))
    _steps(p, said["steps"])
    p.add(note("Relit at the anchor itself, from the System screen."))
    return p


#: What each step reads as, met and not. Paying is not *done* until it is
#: spent, so the third says whether it is in hand.
_STATE = {"read": ("done", "to do"), "tech": ("done", "to do"),
          "pay": ("in hand", "short")}


def _steps(p: Panel, steps) -> None:
    """The three parts of a relight, each on its own wrapped line — a row
    with a sentence for a key is as wide as the sentence, and pushed the
    chart's side panel under the chart."""
    for key, done, text in steps:
        met, unmet = _STATE.get(key, ("done", "to do"))
        p.add(label(f"{'✓' if done else '·'} {text} — {met if done else unmet}",
                    "", "chloro" if done else "osteo", wrap=True))


def codex(g) -> list[tuple]:
    """(star class, name, what it is) per region, for the codex's sky tab:
    pictured by the star it has most of, and saying whether it is open."""
    from ..data.regions import REGIONS
    from ..sim import relight as relight_sim
    out = []
    for spec in REGIONS:
        star = max(spec.stars, key=lambda row: row[4])[0]
        said = relight_sim.preview(g, spec.id)
        anchor = said["anchor"].name if said["anchor"] else "nowhere"
        state = ("Open." if relight_sim.is_open(g, spec.id) else
                 f"Dark, behind the deep anchor at {anchor}.")
        out.append((star, spec.name,
                    f"{spec.character} {spec.blurb} {state}"))
    return out


def _relight(view, g, rid: str) -> None:
    from ..sim import relight as relight_sim
    out = relight_sim.relight(g, rid)
    if not out.get("ok"):
        view.win.toast(out.get("why", "Not yet."), "warn")
        return
    if view.win.check_ending():
        return
    view.win.toast(f"The anchor is burning. {out['region'].name} is open.",
                   "good")
    view.win.refresh()


def _step(view, g, dest: int) -> None:
    from ..sim import gates as gates_sim
    out = gates_sim.use(g, dest)
    if not out.get("ok"):
        view.win.toast(out["why"], "warn")
        return
    view.win.toast(f"Through the deep gate to {g.galaxy.systems[dest].name}.",
                   "good")
    view.win.refresh()
