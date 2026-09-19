"""The sky, on the screens: the System screen's Sky strip and the shelter mark.

- **The Sky strip** (System screen): what the star here is doing, how long it
  has left, what it does in words, what is forecast for here, and Observe —
  with its preview, which is `phenomena_science.observe_quote`'s, and the
  button does `observe`, which spends exactly that. At a Charter or Dry Choir
  counter, the sale of what was watched, priced the same way.
- **The shelter mark** (Pilot board and Helm): while a flare or the nova's
  light is on this system, whether the crew is out of it and how — the same
  `phenomena.shelter` the dose reads — and on the Helm a way into a body's
  lee.
- **The codex's "Observed phenomena"**, and the two sound cues.

Reads state and calls `sim`; decides nothing. Nothing here writes the game
except through an act, so opening a screen never changes the sky.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..data import phenomena as data
from ..sim import phenomena as sky_sim
from ..sim import phenomena_forecast as forecast_sim
from ..sim import phenomena_nova as nova_sim
from ..sim import phenomena_science as science
from ..sim import phenomena_shelter as shelter_sim
from .widgets import Panel, button, label, mono_label, note, spacer


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def build(view, g) -> Panel | None:
    """The strip, or None when the sky here has nothing to say."""
    live = sky_sim.active(g)
    ahead = [e for e in sky_sim.forecasts(g) if e.system_id == g.location_id]
    said = science.observe_quote(g)
    sale = science.sale_quote(g)
    exposed = sky_sim.exposed(g)
    far = _far_nova(g)
    if not (live or ahead or said["ok"] or sale["ok"] or exposed or far):
        return None
    tint = live[0].spec.tint if live else ("bad" if far else "dim")
    p = Panel("The sky", tint)
    if far:
        p.add_row(*far, "bad")
    for event in live:
        spec = event.spec
        p.add_row(f"{spec.glyph} {spec.name}",
                  _plural(event.left(g.day), "day") + " left", spec.tint)
        p.add(label(spec.effect, "", wrap=True))
    for event in ahead:
        conf = round(forecast_sim.confidence(g, event.kind) * 100)
        p.add_row(f"Forecast: {event.spec.name.lower()}",
                  f"in {_plural(event.start - g.day, 'day')}, {conf}%", "dim")
    if exposed:
        p.add(spacer(3))
        _shelter_rows(p, g)
        lee = _lee_button(view, g)
        if lee is not None:
            p.add_buttons(lee)
    p.add(spacer(3), mono_label("Observing it"))
    if said["ok"]:
        p.add(note(f"{said['name']}: {_plural(said['days'], 'day')} at the "
                   f"array for {said['evidence']:g} phenomena evidence, and "
                   f"data worth about {cr(said['worth'])} to the Charter."))
    p.add_buttons(button(
        f"Observe — {_plural(said['days'], 'day')}" if said["ok"]
        else "Observe", lambda: _observe(view, g),
        kind="primary" if said["ok"] else "", enabled=said["ok"],
        why=said["why"]))
    if sale["ok"]:
        n = len(sale["lots"])
        p.add(note(f"{n} lot{'s' if n != 1 else ''} of sky data aboard; this "
                   f"counter pays {cr(sale['total'])} for them"
                   + (f", less {cr(sale['due'])} wharfage." if sale["due"]
                      else ".")))
        p.add_buttons(button(f"Sell sky data — {cr(sale['net'])}",
                             lambda: _sell(view, g)))
    return p


def _far_nova(g):
    """(key, value) for a nova seen from another star, or None."""
    star = nova_sim.event(g)
    if star is None or star.system_id == g.location_id:
        return None
    name = g.galaxy.systems[star.system_id].name
    if nova_sim.dose_at(g, g.system) > 0:
        return (f"{data.NOVA.glyph} Nova at {name}",
                f"brightening, {star.end - g.day} days to the burst")
    if nova_sim.burst_visible(g):
        left = star.end + data.NOVA_WATCH_DAYS - g.day
        return (f"{data.NOVA.glyph} Nova at {name}",
                f"burst — its light for {left} more days")
    return None


def _shelter_rows(p, g) -> None:
    said = sky_sim.shelter(g)
    share = said["share"] if sky_sim.flare_power(g) > 0 else 0.0
    if share >= 1.0:
        p.add_row("Shelter", "out of the light", "chloro")
    else:
        p.add_row("Shelter", f"exposed — {round((1 - share) * 100)}% of the "
                             f"dose, {sky_sim.dose(g):.2f} a day",
                  "warn")
    p.add(note(said["text"]))


def _lee_button(view, g):
    said = shelter_sim.lee_quote(g)
    if not said["ok"] or sky_sim.flare_power(g) <= 0:
        return None
    return button(f"Keep to the shadow of {said['body']}",
                  lambda: _lee(view, g),
                  tip=f"{data.LEE_FUEL:g} t of reaction mass a day while the "
                      "flare lasts.")


def shelter_row(board, g) -> None:
    """One row on the Pilot's board, only while there is light to hide from."""
    if not sky_sim.exposed(g):
        return
    said = sky_sim.shelter(g)
    if sky_sim.flare_power(g) > 0 and said["share"] >= 1.0:
        board.add_row("Flare", f"sheltered — {said['text']}", "chloro")
    else:
        board.add_row("Flare", f"exposed, {sky_sim.dose(g):.2f} a day — "
                               f"{said['text']}", "warn")


def shelter(view, g) -> Panel | None:
    """The Helm's panel: the same mark, and the way into a shadow."""
    if not sky_sim.exposed(g):
        return None
    p = Panel("Hard light on this system", "warn")
    _shelter_rows(p, g)
    lee = _lee_button(view, g)
    if lee is not None:
        p.add_buttons(lee)
    return p


def _observe(view, g) -> None:
    out = science.observe(g)
    if not out.get("ok"):
        view.win.toast(out.get("why", "Not now."), "warn")
        return
    if view.win.check_ending():
        return
    view.win.toast(out["text"], "good")
    view.win.refresh()


def _sell(view, g) -> None:
    out = science.sell(g)
    view.win.toast(out.get("text") or out.get("why", ""),
                   "good" if out.get("ok") else "warn")
    view.win.refresh()


def _lee(view, g) -> None:
    out = sky_sim.keep_lee(g)
    view.win.toast(out.get("text") or out.get("why", ""),
                   "good" if out.get("ok") else "warn")
    view.win.refresh()


# ── the codex, and the ear ─────────────────────────────────────────────────

def codex(view) -> None:
    """The codex's sky tab: every kind, and what this captain has watched."""
    g = view.game
    view.col.addWidget(spacer(8))
    view.col.addWidget(label("Observed phenomena", "h3", "osteo"))
    seen = list(getattr(sky_sim.peek(g), "observed", ()) or ())
    view.col.addWidget(note(
        f"{_plural(len(seen), 'phenomenon')} watched. What the sky does for "
        "a while, and what each is worth to watch."))
    p = Panel()
    for spec in (*data.KINDS, data.NOVA):
        mine = [o for o in seen if o.kind == spec.id]
        p.add_row(f"{spec.glyph} {spec.name}",
                  f"watched {len(mine)}" if mine else "not yet",
                  spec.tint if mine else "dim")
        p.add(note(spec.blurb))
    for obs in seen[-8:]:
        where = g.galaxy.systems[obs.system_id].name
        p.add_row(f"Day {obs.day}", f"{data.KINDS_BY_ID[obs.kind].name}"
                                    f"{', ' + obs.stage if obs.stage else ''}"
                                    f" at {where}"
                                    f"{' — sold' if obs.sold else ''}")
    view.col.addWidget(p)


def sound(win, ear) -> None:
    """From `soundmap.hud`: a flare warning when one is live where the hull
    is, and the nova when it starts to brighten and when it goes — once
    each, remembered on the window's ear, never saved."""
    from . import audio
    g = win.game
    flare = next((e.id for e in sky_sim.active(g) if e.kind == "flare"), "")
    if flare and flare != ear.get("flare"):
        audio.play("flare")
    ear["flare"] = flare
    phase = nova_sim.phase(g)
    if ear.get("nova") not in (None, phase) and phase != "unknown":
        audio.play("nova")
    ear["nova"] = phase
