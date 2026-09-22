"""Before a walk: where to go, who goes, and what they carry.

Everything on this page is a forecast from the sim that will be the fact once
the party sets out: the sites are `afoot.sites`, the people are
`afoot.pool` with the reason anybody cannot go, and what each will carry is
`afoot.preview_kit` — the same function that dresses them at the gangway —
so a pistol the law here forbids is shown left behind before it is.
"""

from __future__ import annotations

from ..data import afoot_arms as arms
from ..data import kit as kit_table
from ..sim import afoot, afoot_people
from ..sim import places as places_sim
from .widgets import Panel, Pill, button, label, note

#: What each way of going armed means, in the words the screen uses.
ARMS = (("legal", "Only what is legal here",
         "Whatever this law level forbids stays aboard."),
        ("all", "Everything",
         "Carry it anyway — and answer to anybody who sees it."),
        ("none", "Unarmed", "Nobody carries a weapon at all."))


def build(view) -> None:
    game = view.game
    view.head("Afoot", "Walk the decks: your own hull, the quay, the drum, "
                       "the wreck adrift out there.")
    last = (game.walked or {}).get("last")
    if last:
        view.col.addWidget(_last(last))
    sites = afoot.sites(game)
    if view.site_key not in {s.key for s in sites}:
        view.site_key = next((s.key for s in sites if s.kind != "ship"
                              and s.ok), sites[0].key)
    site = next(s for s in sites if s.key == view.site_key)
    view.row(_where(view, sites), _who(view, site))
    view.col.addWidget(_arms(view, site))
    across = _across(view, site)
    if across is not None:
        view.col.addWidget(across)
    ok, why = afoot.can_begin(game, site, view.keys)
    if ok and view.across:
        _way, why = afoot.crossing_for(game, site, view.keys, view.across)
        ok = not why
    go = button(f"Go afoot — {site.name}", view.go_afoot, kind="primary",
                enabled=ok, why=why)
    go.setObjectName("afoot_go")
    view.buttons(go)
    if not ok:
        view.col.addWidget(note(why))
    history = (game.walked or {}).get("history", [])
    if history:
        view.col.addWidget(_history(history))


def _where(view, sites) -> Panel:
    chosen = next((s for s in sites if s.key == view.site_key), None)
    p = Panel(f"Where — {chosen.name}" if chosen else "Where")
    for site in sites:
        picked = site.key == view.site_key
        b = button(("✓ " if picked else "") + site.name,
                   lambda _=False, k=site.key: view.pick_site(k),
                   kind="primary" if picked else "flat", enabled=site.ok,
                   why=site.why)
        b.setObjectName(f"afoot_site_{site.kind}")
        p.add(b)
        bits = [site.kind.title()]
        if site.kind not in ("ship", "wreck", "prize"):
            bits.append(places_sim.population(site))
            bits.append(f"law {site.law}")
        if afoot.airless(site):
            bits.append("no air aboard")
        p.add(label(" · ".join(bits) + " — " + site.what, "note",
                    wrap=True))
    return p


def _who(view, site) -> Panel:
    game = view.game
    p = Panel("Who goes")
    p.add(note(f"Up to {afoot_people.PARTY_MOST}. The first chosen "
               "leads."))
    for key, name, what, ok, why in afoot.pool(game):
        chosen = key in view.keys
        b = button(("✓ " if chosen else "") + name,
                   lambda _=False, k=key: view.toggle(k),
                   kind="primary" if chosen else "flat", enabled=ok, why=why)
        b.setObjectName(f"afoot_who_{key.replace(':', '_')}")
        p.add(b)
        if ok:
            weapon, armour, _kit = afoot.preview_kit(game, key, site,
                                                     view.arms_mode)
            worn = kit_table.ITEM_BY_ID.get(armour)
            carries = arms.arm(weapon).name + (
                f", {worn.name.lower()}" if worn else "")
            hurt = (game.wounds or {}).get(
                "captain" if key == "captain" else key.split(":")[-1])
            p.add(label(f"{what} · {carries}"
                        + (f" · still hurt ({hurt:g})" if hurt else ""),
                        "note", "osteo" if hurt else "", wrap=True))
        else:
            p.add(label(f"{what} · {why}", "note", "warn", wrap=True))
    return p


def _arms(view, site) -> Panel:
    p = Panel("Going armed")
    buttons = []
    for mode, text, blurb in ARMS:
        b = button(text, lambda _=False, m=mode: view.set_arms(m),
                   kind="primary" if view.arms_mode == mode else "flat",
                   tip=blurb)
        b.setObjectName(f"afoot_arms_{mode}")
        buttons.append(b)
    p.add_buttons(*buttons)
    blurb = next(b for m, _t, b in ARMS if m == view.arms_mode)
    p.add(note(f"{blurb} Law here is {site.law}."
               if site.kind not in ("wreck", "prize", "ship") else
               "Nobody is minding the law out here. A boarding party takes "
               "the ship's issue if it has nothing better."))
    return p


def _across(view, site):
    """How the party gets from the hull to the site (`sim/crossing`): a
    button for each way, what it costs, and why the others are shut."""
    from ..sim import crossing, places
    game = view.game
    if site.kind in ("ship", "prize"):
        return None
    if site.kind == "wreck":
        options = crossing.wreck_ways(game)
    else:
        place = places.by_id(game, site.place_id)
        if place is None:
            return None
        if crossing.across(game, place):
            p = Panel("Getting across")
            p.add(note("Made fast alongside, or across already: the party "
                       "walks straight on."))
            return p
        options = crossing.ways(game, place, len(view.keys) or 1)
    chosen, _why = afoot.crossing_for(game, site, view.keys, view.across)
    p = Panel("Getting across", "osteo")
    for way in options:
        picked = chosen is not None and way.id == chosen.id
        cost = ", ".join(bit for bit in (
            f"{way.cr:,} cr" if way.cr else "", f"{way.minutes} min") if bit)
        b = button(("✓ " if picked else "") + f"{way.label} — {cost}",
                   lambda _=False, w=way.id: view.set_across(w),
                   kind="primary" if picked else "flat", enabled=way.ok,
                   why=way.why, tip=way.note)
        b.setObjectName(f"afoot_across_{way.id}")
        p.add(b)
    return p


def _last(outcome: dict) -> Panel:
    p = Panel("The last walk", "chloro" if outcome.get("outcome") == "left"
              else "osteo")
    p.add(label(outcome.get("text", ""), "", wrap=True))
    for line in outcome.get("said", [])[:6]:
        p.add(note(line))
    return p


def _history(history: list) -> Panel:
    p = Panel("Walked before")
    for day, kind, name, outcome in history[-5:][::-1]:
        row = label(f"Day {day} · {name}", "note")
        p.add(row)
        p.add(Pill(f"{kind} · {outcome}", "dim"))
    return p
