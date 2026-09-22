"""What a place has to have room for: the program of a quay, a hub, a
habitat, a holding, a settlement and a Kith gathering.

A hull's program is `sim/afoot_program.ship`. A place's is this, and it is
read off the same things the rest of the game reads the place by:

- **its open doors** (`sim/shore.open_here`) — every kind of venue the place
  supports gets a room, two where it is big enough to have two;
- **what it is built for** — a quay has docks, customs, a harbour office
  and traffic control; a holding has a room for each of its structural
  traits (`data/works3d.traits_of`, `data/afoot_programs.TRAIT_SPACE`), so a
  mine has its drill hall and a picket its mast room;
- **what keeps it running** (`STATION_CORE`) — control, air, power, water,
  stores, maintenance — and somewhere for the people who run it to sleep;
- **the people who live there** — residences, as many as its headcount
  and amenity call for.

Zones here are *bands*, not positions along an axis: **+1** is by the way
in, where the public goes; **0** the middle; **−1** the back, where the
plant is. A blueprint lays the bands out in whatever shape the place is.
"""

from __future__ import annotations

from ..data import afoot_programs as table
from .afoot_gen import Want

#: The order the concourse's kinds are laid out in: what a crew wants first
#: nearest the gangway, what nobody advertises furthest from it.
CONCOURSE_ORDER = ("chandler", "eatery", "market", "tech", "bank", "clinic",
                   "lodging", "office", "law", "transport", "entertainment",
                   "arts", "sport", "temple", "vice")
#: Floor a venue's room takes, by kind, before it is grown to fill a band.
VENUE_AREA = {"market": 24, "entertainment": 22, "lodging": 20, "eatery": 14,
              "sport": 18, "temple": 14, "arts": 16, "transport": 12,
              "clinic": 12, "vice": 12}
#: People a residential block stands for, and the most blocks a plan
#: draws. A plan is of the public decks and a slice of where people live;
#: the block's name says how many it houses.
HEADS_PER_HOME = 3_000
MOST_HOMES = 12


def concourse(site, venues: list) -> list:
    """**A room for every door the Concourse lists**, in the order a crew
    walks them — so what the Concourse says is open is what can be walked
    into, by the same name. A vice house behind a law level that will not
    have it keeps its door locked."""
    out = []
    for n, kind in enumerate(CONCOURSE_ORDER):
        for venue in (v for v in venues if v.kind == kind):
            out.append(Want(kind, venue.name, venue=venue.id,
                            lock=2 if kind == "vice" and site.law >= 4 else 0,
                            area=VENUE_AREA.get(kind, 10),
                            zone=0.9 - 1.4 * n / len(CONCOURSE_ORDER)))
    return out


def core(heads: int, control: str = "Station control") -> list:
    """What keeps a structure running, and where its keepers live."""
    out = []
    for kind, name, count, area in table.STATION_CORE:
        for n in range(count):
            out.append(Want(kind, control if kind == "command" else name,
                            area=area + (4 if heads >= 10_000 else 0),
                            zone=-0.6 if kind != "command" else 0.2,
                            lock=1 if kind in ("command", "power") else 0))
    if heads > 0:
        out.append(Want("dormitory" if heads >= 200 else "quarters",
                        "Staff quarters", area=12 + min(20, heads // 60),
                        zone=-0.3))
        out.append(Want("galley", "Staff mess", area=8, zone=-0.2))
    return out


def homes(site, most: int = MOST_HOMES) -> list:
    """Residential blocks for the people who live here, as many as its own
    headcount calls for, each named for how many it houses."""
    if site.heads <= 0:
        return []
    count = max(1, min(most, -(-site.heads // HEADS_PER_HOME)))
    each = max(1, site.heads // count)
    return [Want("homes", f"Residential block {n + 1} — {each:,} people",
                 area=18, zone=-0.1 - 0.05 * n) for n in range(count)]


def traits(klass) -> list:
    """A room for each structural trait the class carries."""
    from ..data.works3d import traits_of
    out = []
    for trait in traits_of(klass):
        for kind, name, count, area in table.TRAIT_SPACE.get(trait, ()):
            for n in range(count):
                out.append(Want(kind, name if count == 1 else
                                f"{name} {n + 1}", area=area,
                                zone=_trait_zone(kind),
                                lock=2 if kind in ("vault", "magazine")
                                else 0))
    return out


def _trait_zone(kind: str) -> float:
    if kind in ("airlock",):
        return 1.0
    if kind in ("park", "clinic", "wards", "surgery"):
        return 0.5
    if kind in ("works", "vault", "magazine", "weapons"):
        return -0.8
    return 0.0


# ── by kind of place ───────────────────────────────────────────────────────

def quay(rng, site, venues: list, hub: bool) -> tuple:
    """(the quay's own rooms, the concourse). A hub has more of both."""
    berths = 4 if hub else 2
    own = [Want("docks", f"Berth {n + 1}", area=14, zone=1.0)
           for n in range(berths)]
    own += [Want("customs", "Customs", area=12, zone=0.9),
            Want("harbour", "Harbour office", area=10, zone=0.8),
            Want("traffic", "Traffic control", area=10, zone=0.3, lock=1)]
    if site.amenity >= 3:
        own.append(Want("admin", "Port administration", area=12, zone=0.2))
    if site.law >= 5:
        own.append(Want("cells", "The cells", area=10, zone=-0.2, lock=2))
    if hub:
        own += [Want("drydock", "Drydock", area=30, zone=-0.5),
                Want("hangar", "Cargo terminal", area=26, zone=0.6)]
    own += core(site.heads, "Port control")[1:]
    halls = concourse(site, venues)
    halls += homes(site)
    return own, halls


def works(rng, site, klass, venues: list) -> list:
    """A habitat's or a holding's whole program."""
    out = traits(klass) if klass is not None else []
    out += core(site.heads)
    out += concourse(site, venues)
    if site.heads >= 1_000:
        out += homes(site)
    if not any(w.kind in ("airlock", "docks") for w in out):
        out.append(Want("airlock", "Docking lock", area=6, zone=1.0))
    return out


def settlement(rng, site, venues: list, good: str = "") -> list:
    """A power's people on the ground, working one thing."""
    out = [Want("works", f"The works{f' — {good}' if good else ''}",
                area=26, zone=-0.8),
           Want("works", "Loading shed", area=16, zone=0.6),
           Want("store", "Stores", area=10, zone=-0.4),
           Want("bunkhouse", "Bunkhouse", area=18, zone=-0.2),
           Want("admin", "Site office", area=10, zone=0.7),
           Want("power", "Power shed", area=10, zone=-0.9, lock=1),
           Want("workshop", "Machine shop", area=12, zone=-0.5)]
    if site.law >= 5:
        out.append(Want("cells", "Lock-up", area=6, zone=0.0, lock=2))
    out += concourse(site, venues)
    return out


def establishment(rng, site, kind, venues: list) -> list:
    """A yard, a hotel, a wheel, a den: the rooms its trade needs, the
    doors it keeps, and what keeps it running."""
    out = []
    for room, name, count, area in kind.rooms:
        for n in range(count):
            out.append(Want(room, name if count == 1 else f"{name} {n + 1}",
                            area=area, zone=_trait_zone(room) or 0.1 - 0.1 * n,
                            lock=2 if room in ("vault", "magazine") else 0))
    out += core(site.heads, "Operations")
    out += concourse(site, venues)
    if not any(w.kind in ("airlock", "docks") for w in out):
        out.append(Want("docks" if kind.kind == "station" else "airlock",
                        "Berth" if kind.kind == "station" else "Vehicle lock",
                        area=10, zone=1.0))
    return out


def gathering() -> list:
    """A Kith gathering: the halls they sing in, and what they keep."""
    return [Want("song_hall", "The singing hall", area=40, zone=0.0),
            Want("song_hall", "The listening hall", area=22, zone=0.5),
            Want("park", "The garden", area=28, zone=-0.3),
            Want("nest", "The nest", area=18, zone=-0.8),
            Want("store", "Gift room", area=8, zone=0.8),
            Want("docks", "The mooring", area=10, zone=1.0)]
