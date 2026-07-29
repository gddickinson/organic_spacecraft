"""Everything in a system you can fly to that is not a planet.

A player at the helm asked the obvious question: *"the map only shows the sun
and planets. What about stations, the fleet hub, other shipyards? How would I
navigate back to a shipyard if it is not on the map?"*

They could not, and the reason is worse than a missing marker. A `Port` hangs
off a `System` and has **no position at all** — no body, no orbit, no
coordinates. The quay you are standing on is nowhere in space. Docking was a
screen you switched to from the chart, so the one view you actually fly from
could not show you the one place you most need to fly back to.

So an anchorage is a *place*. Each is anchored to a body, which means it
inherits a real orbit that moves with the clock, and every piece of flight
machinery — intercepts, burn profiles, transfer quotes, arrival — works on it
unchanged, because flying to a quay *is* flying to the body it orbits.

Nothing here is stored. Anchorages are derived from the system and your own
holdings every time they are asked for, exactly like `ship.stats()`: one
source of truth, no save migration, and no way for a stored quay to disagree
with the port it belongs to.

(Not `stations.py` — that is the bridge's crew stations, and a file named for
two different things is a bug waiting to be written.)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data.factions import FACTIONS_BY_ID
from . import flight

#: What a berth can offer, in the words a captain would use.
SERVICE_NAMES = {
    "market": "market",
    "repair": "repairs",
    "shipyard": "shipyard",
    "recruit": "hiring hall",
    "research": "research bench",
    "gestation": "gestation bay",
    "xenoyard": "xeno yard",
}

#: Glyphs the chart draws. Here rather than in the widget so every view that
#: plots a system agrees about what a quay looks like.
GLYPHS = {"quay": "▣", "hub": "◈", "holding": "⬡", "gate": "◉"}


@dataclass
class Anchorage:
    id: str
    name: str
    #: quay | hub | holding
    kind: str
    #: The body it orbits. Its position *is* that body's position, which is
    #: why nothing in `sim/flight` needs a special case for it.
    body_id: str
    body_index: int
    what: str = ""
    services: tuple = ()
    faction: str | None = None
    #: True when the hull is already alongside.
    here: bool = False
    extras: dict = field(default_factory=dict)

    @property
    def glyph(self) -> str:
        return GLYPHS.get(self.kind, "▫")

    def offers(self, service: str) -> bool:
        return service in self.services


def gate_body(system):
    """Which body a Weave anchor stands off.

    The outermost, and deliberately not the one the quay is built over. An
    anchor predates every port in the Verge; it was put where there was room
    and no gravity to fight, and keeping it out at the edge means arriving
    through the Weave drops you at the *edge* of a system rather than in the
    middle of its traffic.
    """
    if not system.bodies:
        return None, -1
    from . import flight
    index = max(range(len(system.bodies)),
                key=lambda i: flight.orbit_radius(system.bodies[i]))
    return system.bodies[index], index


def anchor_body(system):
    """Which body a system's quay is built over.

    Deterministic, and chosen to read plausibly: the largest body that is not
    a comet, because that is where the traffic and the gravity well are. It
    must not wander between calls — an anchorage is derived fresh every time,
    and a quay that moved would be a quay you could never reach.
    """
    if not system.bodies:
        return None, -1
    ranked = sorted(
        enumerate(system.bodies),
        key=lambda pair: (pair[1].kind == "comet",
                          -getattr(pair[1], "radius", 0), pair[0]))
    index, body = ranked[0]
    return body, index


def in_system(game, system=None) -> list:
    """Every anchorage here, in the order a chart should draw them."""
    system = system or game.system
    out: list = []
    here_id = getattr(game, "orbit_body", None)

    port = getattr(system, "port", None)
    if port is not None:
        body, index = anchor_body(system)
        if body is not None:
            faction = FACTIONS_BY_ID.get(port.faction)
            offered = ", ".join(SERVICE_NAMES.get(s, s) for s in port.services)
            out.append(Anchorage(
                id=f"port-{system.id}",
                name=port.name, kind="hub" if port.capital else "quay",
                body_id=body.id, body_index=index,
                what=(f"{faction.short if faction else 'Independent'} berth in "
                      f"orbit of {body.name}. {offered.capitalize()}."),
                services=tuple(port.services), faction=port.faction,
                here=(here_id == body.id),
                extras={"level": port.level, "capital": port.capital}))

    # The Weave. An anchor was drawn on the sector chart and had no place
    # inside its own system at all: invisible on the helm, impossible to fly
    # to, and with nothing happening around it — which a player reported, and
    # which was fair. It is a berth like any other now, so every screen that
    # can plot an anchorage plots it for free.
    from . import weave as weave_sim
    anchor = weave_sim.gate_at(game, system.id)
    if anchor is not None:
        body, index = gate_body(system)
        if body is not None:
            lit = anchor.lit
            out.append(Anchorage(
                id=f"gate-{system.id}", name=anchor.name, kind="gate",
                body_id=body.id, body_index=index,
                what=(f"A Weave anchor standing off {body.name}. "
                      + ("Lit, and busy with it." if lit else
                         "Dark. Whatever it is waiting for, it is not us.")),
                services=(("refuel",) if lit else ()),
                here=(here_id == body.id),
                extras={"lit": lit, "gate": True, "kind": anchor.kind}))

    # Your own ground. A holding that can take a hull is exactly the thing a
    # captain wants to be able to find again.
    for colony in getattr(game, "colonies", []):
        if colony.system_id != system.id or not getattr(colony, "online", False):
            continue
        index = next((i for i, b in enumerate(system.bodies)
                      if b.id == colony.body_id), -1)
        if index < 0:
            continue
        body = system.bodies[index]
        services = tuple(_colony_services(colony))
        out.append(Anchorage(
            id=f"colony-{colony.id}", name=colony.name, kind="holding",
            body_id=body.id, body_index=index,
            what=f"Your holding on {body.name}."
                 + (" " + ", ".join(SERVICE_NAMES.get(s, s)
                                    for s in services).capitalize() + "."
                    if services else ""),
            services=services, here=(here_id == body.id),
            extras={"colony": colony.id}))
    return out


def _colony_services(colony) -> list:
    """What one of your settlements can actually do for a hull."""
    from . import works
    effects = works.effects_of(colony)
    out = []
    # `drydock` reads alongside `build_here` rather than instead of it. Every
    # class and work that grants a drydock today also grants `build_here`, so
    # this changes nothing that is currently plantable — but the key was read
    # by *nothing*, which made "refits and repairs here, without flying to a
    # yard" a promise resting entirely on a second flag happening to be set.
    # A future dock that is only a dock now works the way its card reads.
    dock = effects.get("build_here") or effects.get("drydock")
    if dock or effects.get("harbour"):
        out.append("repair")
    if dock:
        out.append("shipyard")
    if effects.get("xenoyard"):
        out.append("xenoyard")
    if effects.get("research"):
        out.append("research")
    return out


def where_am_i(game) -> str:
    """One line naming where the hull is standing. The chart never said.

    A captain could not tell they had launched from a shipyard except by
    opening the shipyard window, which is not an answer to "where am I".
    """
    if not getattr(game, "orbit_body", None):
        return "Holding at the system edge, not alongside anything."
    body = next((b for b in game.system.bodies
                 if b.id == game.orbit_body), None)
    where = body.name if body else "an unnamed body"
    here = [a for a in in_system(game) if a.here]
    if not here:
        return f"In orbit of {where}."
    return (f"In orbit of {where}, alongside "
            + ", ".join(a.name for a in here) + ".")


def docked_at(game):
    """The quay the hull is standing off, if any."""
    return next((a for a in in_system(game) if a.here
                 and a.kind in ("quay", "hub")), None)


def reach_to(game, anchorage) -> float:
    """How far the hull is from an anchorage, in AU."""
    body = game.system.bodies[anchorage.body_index]
    aim = flight.intercept(game, body, "standard")["aim"]
    ship = flight.ship_position(game)
    return ((aim[0] - ship[0]) ** 2 + (aim[1] - ship[1]) ** 2) ** 0.5


def quote(game, anchorage, profile: str = "standard") -> dict:
    """What flying there costs — the body's quote, because it is the body."""
    body = game.system.bodies[anchorage.body_index]
    out = dict(flight.quote(game, body, profile))
    out["anchorage"] = anchorage
    out["here"] = anchorage.here
    return out


def offering(game, service: str) -> list:
    """Every anchorage here offering something, nearest first.

    The answer to "how do I get back to a shipyard" is: ask for one.
    """
    have = [a for a in in_system(game) if a.offers(service)]
    return sorted(have, key=lambda a: reach_to(game, a))


def note(game, anchorage) -> str:
    """One line for the chart: what this place is and how far off it is."""
    if anchorage.here:
        return f"{anchorage.name} — you are alongside."
    span = reach_to(game, anchorage)
    q = quote(game, anchorage)
    return (f"{anchorage.name} — {span:.2f} AU off, {q['days']} day"
            f"{'' if q['days'] == 1 else 's'} at a standard burn.")
