"""A hull's functional program: every space it needs, sized, and where it goes.

Read off the chassis card and the fitted list, with the tables in
`data/afoot_programs.py`:

- **fittings** — a room for each drive, power plant, sensor, core and gun
  fitted, placed at *that slot's own mount* along the hull
  (`data/hullforms.FORMS`), so the plan and the 3D model agree where the
  guns are;
- **the crew** — a bridge sized to the watch, berths for the whole
  complement, a master's cabin and officers' cabins, a galley, heads, a
  sickbay, air, water, stores, a workshop, lifeboats, suit lockers;
- **the cargo** — holds as big as the card's rating;
- **the role** — what the tier adds: a liner's cabins and saloon, a
  hospital's wards, a warship's magazine and marines, a miner's root chamber.

A hull with nobody aboard (a Dry Choir frame) needs no galley and no air: it
gets a substrate vault, a coolant plant and a service hatch instead.

The doors open aboard your own hull (`places.ship`, `venues_aboard`) take
over the spaces they are: the mess deck *is* the galley, the sickbay *is*
the sickbay, and each keeps its venue so business can be done in it.
"""

from __future__ import annotations

from ..data import afoot_programs as table
from ..data.afoot_rooms import SLOT_ROOM, UTILITY_ROOM
from ..data.chassis import accepts_family
from ..data.hullforms import form_for
from ..data.parts import PARTS_BY_ID
from .afoot_gen import Want
from .crossing import BOAT_CREW

#: The floor a ship's boat and its cradle take, in squares.
BOAT_BAY = 14

#: Which program space an open door aboard takes over, by the venue's kind.
VENUE_SPACE = {"eatery": "galley", "clinic": "clinic", "sport": "gym",
               "arts": "library", "tech": "workshop", "chandler": "store"}

#: The most rooms of one sort a program asks for, however big the hull: the
#: map is a plan of the ship, not a census of it.
MOST_OF = {"quarters": 6, "hold": 4, "weapons": 4, "drive": 2, "power": 2,
           "sensors": 2, "core": 2, "suites": 4, "wards": 4, "dormitory": 4}


def _add(out: list, kind: str, name: str, area: float, zone: float,
         **kw) -> None:
    if sum(1 for w in out if w.kind == kind) >= MOST_OF.get(kind, 99):
        return
    out.append(Want(kind, name, area=max(3, int(round(area))),
                    zone=max(-1.0, min(1.0, zone)), **kw))


def ship(chassis, fitted, venues=()) -> list:
    """Every space this hull needs, bow to stern."""
    form = form_for(chassis.family)
    crew = int(chassis.crew or 0)
    crewed = crew > 0 and chassis.family != "synthetic"
    out: list = []
    _command(out, chassis, crew, crewed)
    _fittings(out, chassis, fitted, form)
    if crewed:
        _habitation(out, chassis, crew)
    else:
        _add(out, "lifesupport", "Coolant plant", 8, -0.1)
        _add(out, "airlock", "Service hatch", 4, -0.8)
    _engineering(out, chassis, crew, fitted)
    _cargo(out, chassis)
    for kind, name, count, area, zone in table.ROLE.get(chassis.tier, ()):
        for n in range(count):
            _add(out, kind, name if count == 1 else f"{name} {n + 1}", area,
                 zone if zone is not None else table.ZONE.get(kind, 0.0)
                 - 0.12 * n)
    _venues(out, venues)
    if "crew_girdle" in (fitted or ()):
        # The berths are the girdle: spun, with weight in them.
        for w in out:
            if w.kind == "quarters":
                w.part = "crew_girdle"
    return out


def _command(out, chassis, crew, crewed) -> None:
    if crewed:
        # A grown hull is flown from its cap, behind the eye; a Yards hull
        # from behind its armoured bow slab; anything else near the bow.
        zone = {"grown": 0.86, "fabricated": 0.62, "hybrid": 0.72,
                "xeno": 0.66}.get(chassis.family, table.ZONE["bridge"])
        # A two-seat craft is flown from a cockpit, not a bridge.
        _add(out, "bridge", "Cockpit" if crew <= 3 else "Bridge",
             table.AREA["bridge"] + min(20, crew * 0.4), zone)
    else:
        _add(out, "core", "Substrate vault", 10, 0.3)


def _fittings(out, chassis, fitted, form) -> None:
    """A room per fitting, at the z of its slot's own mount."""
    counts: dict = {}
    for pid in fitted or ():
        part = PARTS_BY_ID.get(pid)
        if part is None or part.slot == "defence":
            continue                   # armour is in the walls, not a room
        i = counts.get(part.slot, 0)
        counts[part.slot] = i + 1
        mounts = form.mounts.get(part.slot) or []
        zone = mounts[i % len(mounts)].at[2] if mounts else 0.0
        if part.slot == "utility":
            kind = UTILITY_ROOM.get(pid, "utility")
            if kind == "quarters":
                continue               # a crew girdle is the berths
            _add(out, kind, part.name, table.AREA.get(kind, 10), zone,
                 part=pid)
            continue
        kind = SLOT_ROOM.get(part.slot, "utility")
        name = {"weapons": f"Gun position — {part.name}"}.get(kind, part.name)
        area = table.AREA.get(kind, 6) + (2 if part.slot == "drive" else 0)
        _add(out, kind, name, area, zone, part=pid)


def _habitation(out, chassis, crew) -> None:
    if crew >= 4:
        _add(out, "cabin", "Master's cabin", table.AREA["cabin"],
             table.ZONE["cabin"])
    if crew >= 12:
        _add(out, "officers", "Officers' cabins",
             table.AREA["officers"] + crew / 12, table.ZONE["officers"])
    total = max(4, crew * table.BERTH_PER_HEAD)
    rooms = max(1, min(MOST_OF["quarters"],
                       -(-int(total) // table.BERTHS_MOST)))
    for n in range(rooms):
        _add(out, "quarters", "Berths" if rooms == 1 else
             f"Berths {'ABCDEF'[n]}", total / rooms,
             table.ZONE["quarters"] - 0.10 * n)
    if crew >= 3:
        _add(out, "galley", "Galley", table.AREA["galley"] + crew * 0.3,
             table.ZONE["galley"])
        for n in range(1 if crew < 40 else 2):
            _add(out, "heads", "Heads", table.AREA["heads"] + crew / 20,
                 table.ZONE["heads"] - 0.2 * n)
    if crew >= 8:
        _add(out, "clinic", "Sickbay", table.AREA["clinic"] + crew / 15,
             table.ZONE["clinic"])
    if crew >= 30:
        _add(out, "gym", "Gym", table.AREA["gym"], table.ZONE["gym"])
    if crew >= 40:
        _add(out, "library", "Library", table.AREA["library"],
             table.ZONE["library"])
    kind, name = table.AIR_PLANT.get(chassis.family, ("lifesupport",
                                                       "Air plant"))
    _add(out, kind, name, table.AREA["lifesupport"] + min(16, crew * 0.15),
         table.ZONE["lifesupport"])
    if crew >= 10:
        _add(out, "reclaim", "Water reclamation", table.AREA["reclaim"],
             table.ZONE["reclaim"])
    _add(out, "store", "Stores", table.AREA["store"] + min(12, crew * 0.15),
         table.ZONE["store"])
    if crew >= 6:
        for n in range(max(1, min(3, crew // 40 + 1))):
            _add(out, "pods", "Lifeboat bay", table.AREA["pods"],
                 table.ZONE["pods"] - 0.25 * n)
    if crew >= BOAT_CREW:
        # The ship's boat (`sim/crossing`): how a crew gets across to
        # somewhere the hull is not made fast to.
        _add(out, "hangar", "Boat bay", BOAT_BAY, table.ZONE["hangar"])
    for n in range(max(1, min(3, crew // 60 + 1))):
        _add(out, "airlock", "Suit locker", table.AREA["airlock"],
             table.ZONE["airlock"] - 0.08 * n)


def _engineering(out, chassis, crew, fitted) -> None:
    drives = [p for p in fitted or () if getattr(PARTS_BY_ID.get(p), "slot",
                                                  "") == "drive"]
    if drives or crew:
        mass = float(chassis.mass_t or 1)
        _add(out, "tanks", "Reaction mass" if chassis.family in (
            "grown", "hybrid") else "Tankage",
            table.AREA["tanks"] + min(12, mass ** (1 / 3) / 3),
            table.ZONE["tanks"])
    if crew >= 8 or chassis.tier == "Tug":
        _add(out, "workshop", "Damage control", table.AREA["workshop"],
             table.ZONE["workshop"])
    weapons = [p for p in fitted or () if getattr(PARTS_BY_ID.get(p), "slot",
                                                   "") == "weapon"]
    if len(weapons) >= 2 and crew >= 8:
        _add(out, "magazine", "Magazine", table.AREA["magazine"],
             table.ZONE["magazine"])


def _cargo(out, chassis) -> None:
    cargo = float(chassis.cargo or 0)
    if cargo <= 0 or any(w.kind == "hold" for w in out):
        return
    total = max(8.0, min(150.0, 4 + cargo ** 0.6))
    rooms = max(1, min(MOST_OF["hold"], int(total // 40) + 1))
    for n in range(rooms):
        _add(out, "hold", "Hold" if rooms == 1 else f"Hold {n + 1}",
             total / rooms, table.ZONE["hold"] - 0.12 * n)


def _venues(out, venues) -> None:
    """Doors open aboard take over the spaces they are."""
    for venue in venues:
        space = VENUE_SPACE.get(venue.kind)
        got = next((w for w in out if w.kind == space and not w.venue), None)
        if got is not None:
            got.venue, got.name = venue.id, venue.name
            continue
        kind = space or "utility"
        _add(out, kind, venue.name, table.AREA.get(kind, 8),
             table.ZONE.get(kind, 0.0), venue=venue.id)


def area(wants: list) -> int:
    """Squares of floor a program asks for, all told."""
    return sum(w.area for w in wants)


def typical_fit(rng, chassis) -> list:
    """What a hull of this class usually carries when nobody has said: a
    part or two in every slot it has, of its own family — enough for its
    rooms to be hers. For a wreck, a prize drawn from a stand-in, a probe."""
    by_slot: dict = {}
    for part in PARTS_BY_ID.values():
        if accepts_family(chassis, part.family):
            by_slot.setdefault(part.slot, []).append(part.id)
    out = []
    for slot, count in chassis.slots.items():
        pool = sorted(by_slot.get(slot, []))
        if pool and count > 0:
            out.extend(rng.sample(pool, min(count, 2)))
    return out
