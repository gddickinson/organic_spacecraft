"""The 'Who runs this' tab: the noticeboard at the gate.

The governance layer has been deep for a long time and was reachable only
from the Law screen, which is about *your* charges rather than about where
you are standing. A captain walking down a gangway has one question — can I
be arrested here, and by whom — and nothing on any screen answered it.

Everything here is `sim/authority.py`, which reads eight existing modules and
writes none of them. The panel that matters is the last one: what the law
here actually has on you, and what it would do about it.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..sim import authority as auth_sim
from ..sim import officials as officials_sim
from ..sim import person as person_sim
from ..sim import shore
from .widgets import Panel, Pill, label, note


def build(view, place) -> None:
    """The whole tab."""
    game = view.game
    view.col.addWidget(note(
        "Who holds this ground, how hard they hold it, and what they have "
        "on you. Everything here is read; nothing on this tab changes "
        "anything."))
    view.row(_rule(game, place), _force(game, place))
    view.col.addWidget(_against(view, game, place))
    _desk(view, game, place)


def _rule(game, place) -> Panel:
    """The government and the law it keeps."""
    digit, name, about = auth_sim.government(game, place)
    p = Panel("The government")
    p.add_row("Sort", name + (f" ({digit})" if digit >= 0 else ""))
    p.add(note(about))
    p.add_row("Law level", str(place.law))
    p.add(label(auth_sim.law_words(place.law), "note",
                "warn" if place.law >= 8 else "", wrap=True))
    who = auth_sim.holder(game, place)
    p.add_row("Held by", who["name"],
              "warn" if who.get("hostile") else "")
    p.add(note(who["note"]))
    if who.get("hostile"):
        p.add(label("They open fire rather than hail. Being here is a "
                    "decision.", "note", "warn", wrap=True))
    return p


def _force(game, place) -> Panel:
    """What is actually out there, and what it is for."""
    watch = auth_sim.garrison(game, place)
    p = Panel("The watch")
    p.add_row("Policing", f"{watch['watch']:.0%}")
    p.add_bar(watch["watch"], "chloro" if watch["watch"] > 0.55 else "warn")
    p.add(label(watch["note"], "note", wrap=True))
    if watch["posts"]:
        p.add_row("Armed posts in system", str(watch["posts"]), "lumen")
    courts = shore.open_here(game, place, "law")
    if courts:
        p.add(label("Here at the gate", "h3"))
        for venue in courts:
            p.add(label(venue.name, "sub"))
            p.add(note(venue.note))
    else:
        p.add(note("No court, no constabulary and nobody to complain to. "
                   "Whatever is settled here is settled between the people "
                   "standing in the room."))
    return p


def _against(view, game, place) -> Panel:
    """What the law here has on you."""
    risk = auth_sim.against_you(game, place)
    bad = bool(risk["bites"]) or bool(risk["charges"])
    p = Panel("What they have on you", "warn" if bad else "")
    if not risk["charges"] and not risk["warrants"]:
        p.add(label("Nothing. You may walk down the gangway.", "note",
                    "chloro", wrap=True))
    for charge in risk["charges"]:
        p.add_row(getattr(charge, "what", "A charge"),
                  getattr(charge, "state", "open"), "warn")
    for warrant in risk["warrants"]:
        p.add(Pill(f"{getattr(warrant, 'bite', 'warrant')} · "
                   f"{getattr(warrant, 'power', '')}", "warn"))
        p.add(note(getattr(warrant, "why", "")))
    if risk["bites"]:
        p.add(label("A warrant here would: " + ", ".join(risk["bites"]) + ".",
                    "note", "warn", wrap=True))
    if risk["bounty"]:
        p.add_row("Bounty standing", cr(round(risk["bounty"])), "warn")
    # And what the *crew* is carrying, which is the other half of a gate.
    carried = person_sim.risk_ashore(game, place.law)
    if carried["people"]:
        p.add(label(f"{carried['people']} of the watch would be stopped at "
                    "this gate for what they are carrying.", "note", "warn",
                    wrap=True))
        for who, item in carried["items"][:8]:
            p.add_row(who, f"{item.name} — law {item.law}", "warn")
    else:
        p.add(label("Nothing the watch carries is forbidden here.", "note",
                    "chloro", wrap=True))
    return p


def _desk(view, game, place) -> None:
    """The harbourmaster, where there is one — a person, not a counter."""
    if place.kind != "port":
        return
    system = next((s for s in game.galaxy.systems
                   if s.id == place.system_id), None)
    if system is None or not getattr(system, "port", None):
        return
    who = officials_sim.identity(system)
    band, tint = officials_sim.band(officials_sim.regard(game, system))
    p = Panel("The harbourmaster")
    p.add_row(f"{who.get('title', 'Harbourmaster')} "
              f"{who.get('name', 'Somebody')}", band, tint)
    # `temper` is a record, not a string. Printing the dict's value put a
    # dataclass repr — `Temper(id='frightened', …, bend=1.5)` — on the
    # screen, which is the sort of thing a player screenshots.
    temper = who.get("temper")
    if temper is not None:
        p.add(label(getattr(temper, "name", ""), "sub"))
        p.add(note(getattr(temper, "blurb", "")))
    if officials_sim.has_lever(game, system):
        lever = who.get("lever")
        p.add(label("You know something about them"
                    + (f": {getattr(lever, 'name', '')}" if lever else "")
                    + ".", "note", "lumen", wrap=True))
    view.col.addWidget(p)
