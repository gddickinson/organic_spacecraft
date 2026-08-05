"""Talking to something: who it is, what it says, and what you can do about it.

**The general answer to "how do I interact with this?"** The game had a great
many things a captain can act on — a quay, a gate, a world, a hull, the office
that runs a port — and the acts were scattered across screens that each knew
about one of them. A player who flew to a Weave anchor found nothing there to
press, because the panel that rides a ring lives on the sector chart; the same
shape was waiting behind every other contact.

So there is one door. Given anything `sim/track` can put a cursor on, `about`
says who it is, `greeting` gives a line in their own voice, and `options`
lists what can be done — each option carrying whether it is available and, if
not, *why not*, in the words the captain would use.

**It owns no rules.** Every option is a door that already existed: berthing,
clearance, the port's services, the gate network, survey, mining, the officer
who runs the harbour, the guns. This module decides what to *offer* and the
existing sim decides what happens, which is what stops a menu promising
something the game will refuse.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Option:
    """One thing that can be done with a contact."""
    id: str
    label: str
    blurb: str
    ok: bool = True
    why: str = ""
    #: A screen this option hands the captain to, if that is what it does.
    goes_to: str = ""
    #: Sorted low to high; the thing you most likely came to do is first.
    order: int = 50


@dataclass
class Exchange:
    """What has been said to this contact, newest last."""
    said: list = field(default_factory=list)

    def add(self, who: str, text: str) -> None:
        self.said.append((who, text))


def about(game, contact) -> dict:
    """Who this is, in one place: name, kind, whose it is, how they read you."""
    from . import anchorage as anchorage_sim
    from ..data.factions import FACTIONS_BY_ID

    faction = getattr(contact, "faction", None)
    place = _place_of(game, contact)
    if place is not None and not faction:
        faction = getattr(place, "faction", None)
    power = FACTIONS_BY_ID.get(faction) if faction else None
    standing = game.rep.get(faction, 0.0) if faction else None
    return {
        "name": contact.name,
        "kind": contact.kind,
        "detail": getattr(contact, "detail", ""),
        "faction": faction,
        "power": power.name if power else "",
        "standing": standing,
        "here": bool(place.here) if place is not None else False,
        "what": getattr(place, "what", "") if place is not None else "",
        "services": tuple(getattr(place, "services", ()) or ())
        if place is not None else (),
        "kindname": anchorage_sim.kind_name(place)
        if place is not None and hasattr(anchorage_sim, "kind_name") else "",
    }


def _place_of(game, contact):
    """The anchorage behind an anchorage contact, if that is what this is."""
    if getattr(contact, "kind", "") != "anchorage":
        return None
    from . import anchorage as anchorage_sim
    return next((a for a in anchorage_sim.in_system(game)
                 if a.id == getattr(contact, "id", "").split(":", 1)[-1]
                 or a.name == contact.name), None)


def greeting(game, contact) -> str:
    """What they say when you open the channel. Their voice, not the game's.

    A body and a star do not answer, and saying so is better than an empty
    pane: what comes back is the instrument reading, which is the honest
    thing a hull gets from a rock.
    """
    from . import voice as voice_sim

    who = about(game, contact)
    if contact.kind in ("body", "star", "point"):
        return (f"{contact.name} — {who['detail'] or 'nothing is transmitting'}"
                ". Nothing there answers a hail; this is what the array sees.")
    if contact.kind == "anchorage":
        place = _place_of(game, contact)
        if place is not None and place.kind == "gate":
            from . import weave as weave_sim
            gate = weave_sim.gate_at(game, game.location_id)
            if gate is not None and not gate.lit:
                return (f"{contact.name} is dark. There is a carrier under it "
                        "and nothing riding the carrier.")
            return (f"{contact.name} is lit and holding. The ring answers "
                    "with a handshake and a toll schedule, and nothing else.")
        return voice_sim.speak(
            game, f"harbour:{contact.name}", name=contact.name,
            kind="official", persona="plain", situation="greet")["line"]
    if contact.kind == "hull":
        return voice_sim.speak(
            game, f"hull:{contact.id}", name=contact.name, kind="captain",
            persona="plain",
            situation="hostile" if getattr(contact, "hostile", False)
            else "greet")["line"]
    return f"{contact.name} does not answer."


def options(game, contact) -> list[Option]:
    """Everything that can be done with this contact, best guess first."""
    kind = getattr(contact, "kind", "")
    if kind == "anchorage":
        place = _place_of(game, contact)
        if place is not None and place.kind == "gate":
            return _gate_options(game, contact)
        return _quay_options(game, contact, place)
    if kind == "body":
        return _body_options(game, contact)
    if kind == "hull":
        return _hull_options(game, contact)
    return [Option("look", "Nothing to say to it", "It is a star.",
                   ok=False, why="Nothing there is listening.")]


def _fly_option(game, contact) -> Option:
    """Getting there is an option like any other, and it is usually first."""
    from . import berthing as berth_sim
    ok, why = berth_sim.can_conn(game, contact)
    return Option("conn", f"Take the conn on {contact.name}",
                  "Fly the last few kilometres yourself, or hand it to the "
                  "computer.", ok=ok, why=why, order=10)


def _quay_options(game, contact, place) -> list[Option]:
    from . import officials as officials_sim

    here = bool(place.here) if place is not None else False
    services = tuple(getattr(place, "services", ()) or ()) if place else ()
    said = {
        "market": ("Trade at the counter", "Buy and sell over their board; "
                   "the freight desk ranks what a run would actually clear."),
        "repair": ("Put the hull in for repair", "Patch what the sector has "
                   "done to her."),
        "shipyard": ("Open the shipyard", "Refit, lay down a hull, or take a "
                     "machine apart."),
        "recruit": ("Ask at the hiring hall", "Officers stand a watch better "
                    "than nobody does."),
        "research": ("Use their bench", "Somebody else's laboratory is still "
                     "a laboratory."),
        "gestation": ("Use the gestation bay", "Where a grown hull is grown."),
    }
    out = [_fly_option(game, contact)]
    if here:
        out.append(Option("dock", "Come alongside and open the port",
                          "Everything this berth offers, on one screen.",
                          goes_to="port", order=20))
    for service in services:
        label, blurb = said.get(service, (service.title(), ""))
        out.append(Option(f"service:{service}", label, blurb,
                          ok=here,
                          why="" if here else "Come alongside first.",
                          goes_to="port", order=30))
    system = game.galaxy.systems[game.location_id]
    who = officials_sim.mind(game, system)
    if who is not None:
        band, _tint = officials_sim.band(officials_sim.regard(game, system))
        out.append(Option("office", "Speak to the harbourmaster",
                          f"They think of you as {band.lower()}. Favours, "
                          "prices and what they will admit to knowing.",
                          ok=here,
                          why="" if here else "Come alongside first.",
                          goes_to="port", order=40))
    return out


def _gate_options(game, contact) -> list[Option]:
    """A ring is ridden from the chart — so say so, here, at the ring."""
    from . import gates as gates_sim
    from . import weave as weave_sim

    out = [_fly_option(game, contact)]
    gate = weave_sim.gate_at(game, game.location_id)
    if gate is None:
        return out
    if not gate.lit:
        ok, why = gates_sim.can_wake(game)
        out.append(Option("wake", "Wake the anchor",
                          "A dark ring runs nothing. Waking one takes the "
                          "Weavecraft technology, material and days.",
                          ok=ok, why=why, goes_to="map", order=20))
        return out
    runs = weave_sim.reachable(game, game.location_id)
    for dest in runs[:6]:
        said = gates_sim.quote(game, dest)
        target = game.galaxy.systems[dest]
        out.append(Option(
            f"step:{dest}", f"Step through to {target.name}",
            f"{said['ly_saved']:.0f} light years, instantly, for "
            f"{said['credits']:,.0f} credits in tolls.",
            ok=said["ok"], why=said["why"], goes_to="map", order=20))
    if not runs:
        out.append(Option("nowhere", "Nothing runs from here",
                          "A ring needs an anchor alight at both ends.",
                          ok=False,
                          why="Nothing this one is joined to is burning.",
                          order=20))
    return out


def _body_options(game, contact) -> list[Option]:
    from . import survey as survey_sim
    out = [_fly_option(game, contact)]
    index = getattr(contact, "body_index", None)
    if index is None:
        return out
    body = game.system.bodies[index]
    out.append(Option("survey", f"Survey {body.name}",
                      "What is on it, and what it would be worth working.",
                      ok=not body.surveyed,
                      why="" if not body.surveyed else "Already surveyed.",
                      goes_to="system", order=20))
    out.append(Option("work", "Put a rig on it",
                      "Four ways to work a body, from skimming the surface "
                      "to sinking a deep bore.",
                      ok=body.surveyed,
                      why="" if body.surveyed else "Survey it first.",
                      goes_to="system", order=30))
    out.append(Option("land", "Put a party on the ground",
                      "A zone revealed a tile at a time, and whatever is "
                      "down there.",
                      ok=body.surveyed,
                      why="" if body.surveyed else "Survey it first.",
                      goes_to="system", order=40))
    del survey_sim
    return out


def _hull_options(game, contact) -> list[Option]:
    from . import engage as engage_sim
    out = [_fly_option(game, contact)]
    out.append(Option("talk", "Hail her",
                      "Ask who they are and what they are carrying. Most of "
                      "them would rather talk than not.", order=20))
    hostile = bool(getattr(contact, "hostile", False))
    out.append(Option("mark", "Strike the mark" if hostile
                      else "Mark her hostile",
                      "Every chart and board in the game reads this mark.",
                      goes_to="pilot", order=40))
    ok, why = True, ""
    conn = getattr(game, "conn", None)
    if conn is not None:
        km = engage_sim.range_km(game, conn, contact)
        ok, why = engage_sim.may_engage(game, conn, contact, km)
    out.append(Option("fire", "Open fire", "There is no taking this back.",
                      ok=ok, why=why, goes_to="pilot", order=90))
    return out
