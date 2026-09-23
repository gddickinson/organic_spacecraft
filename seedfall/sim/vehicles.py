"""The machine a landing party crosses ground in: owning it, taking it down.

`Expedition.rover` was a number from nought to ten that bought one day off a
step while it stayed above eight. This is the machine that number belongs
to — bought at a yard, carried down in a lander's hold against the supplies
it competes with, driven by somebody with the ticket, worn by every hazard
it takes the party through, and mended between landings.

What it changes on the ground is deliberately small and legible:

- **Ground it is made for costs a day less** (`data/vehicles.GOOD_GROUND`),
  which is what the old rover bought on *all* ground.
- **Ground it refuses costs a day more**: the party leaves it at the camp
  and walks, and a scarp is a scarp on foot.
- **Everything else is what it always was.**

So a ROVER makes a dune sea cheap and a crevasse field dear, a CRAWLER is
the other way about, a KITE ignores the ground entirely and is dead weight
where there is no air, and a party with nothing walks — which is the state
the game shipped in and is still allowed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data import vehicles as table
from ..data.vehicles import GOOD_GROUND, ON_FOOT, VEHICLES_BY_ID, WHOLE

#: What state a machine is in while it is on a world with the party.
DOWN = "down"


@register
@dataclass
class Held:
    """One vehicle, in the hold or on the ground."""

    id: int
    class_id: str
    name: str
    condition: int = WHOLE
    #: stowed | down | lost
    state: str = "stowed"
    #: Days it has been driven, all told.
    days: float = 0.0
    log: list = field(default_factory=list)


def kind_of(held) -> table.VehicleClass:
    return VEHICLES_BY_ID[held.class_id]


def aboard(game) -> list:
    """Every vehicle this hull owns, stowed or down."""
    return [v for v in getattr(game, "vehicles", []) or []
            if v.state != "lost"]


def stowed(game) -> list:
    """The ones in the hold, ready to go down."""
    return [v for v in aboard(game) if v.state == "stowed"]


def on_the_ground(game):
    """The machine that is down with the party, or None."""
    return next((v for v in aboard(game) if v.state == DOWN), None)


def give(game, class_id: str = table.STARTING_VEHICLE,
         name: str = "") -> Held:
    """Put a vehicle in the hold. The one door for acquiring one."""
    kind = VEHICLES_BY_ID[class_id]
    held = Held(id=len(getattr(game, "vehicles", []) or []) + 1,
                class_id=class_id, name=name or _name_for(game, kind))
    game.vehicles = list(getattr(game, "vehicles", []) or []) + [held]
    return held


def _name_for(game, kind) -> str:
    """A machine is named off the hull that carries it."""
    hull = getattr(getattr(game, "ship", None), "name", "") or "the hull"
    return f"{hull}'s {kind.name.title()}"


# ── who drives ─────────────────────────────────────────────────────────────

def rating(game, key: str) -> int:
    """What this person's Drive ticket reads."""
    from . import afoot_people, lifepath
    if key == "captain":
        return afoot_people.captain_record(game).skill("drive")
    officer = afoot_people.officer_of(game, int(key.split(":")[-1]))
    return lifepath.of(game, officer).skill("drive") if officer else -3


def drivers(game, vehicle) -> list:
    """Everybody aboard who could drive this, in `afoot_people.pool`'s
    shape: `(key, name, what, ok, why)`."""
    from . import afoot_people
    from . import craft as craft_sim
    kind, out = kind_of(vehicle), []
    for key, name, what, ok, why in afoot_people.pool(game):
        skill = rating(game, key)
        if ok and skill < kind.needs:
            ok, why = False, (f"A {kind.name} is driven on Drive "
                              f"{kind.needs}; {name} is "
                              f"{craft_sim.ticket(skill)}.")
        elif ok and kind.needs <= table.ANYBODY:
            what = f"{what} · drives it, well or badly"
        out.append((key, name, what, ok, why))
    return out


def anybody_drives(game, vehicle) -> bool:
    return any(ok for _k, _n, _w, ok, _why in drivers(game, vehicle))


# ── taking one down ────────────────────────────────────────────────────────

def can_take(game, vehicle, lander, body, supplies_t: float = 0.0) -> tuple:
    """May this machine go down in that lander, on this world? `(ok, why)`."""
    from . import craft as craft_sim
    if vehicle is None:
        return False, "Nothing to take down."
    kind = kind_of(vehicle)
    if vehicle.state != "stowed":
        return False, f"{vehicle.name} is not in the hold."
    if vehicle.condition <= 0:
        return False, f"{vehicle.name} is a wreck."
    if lander is None:
        return False, "Nothing to carry it down in."
    room = craft_sim.kind_of(lander).hold_t - float(supplies_t)
    if kind.mass_t > room:
        return False, (f"{craft_sim.kind_of(lander).name} has {room:g} t of "
                       f"hold left after the supplies; a {kind.name} is "
                       f"{kind.mass_t:g} t.")
    if kind.needs_air and not has_air(game, body):
        return False, (f"A {kind.name} flies on air and {body.name} has "
                       "none worth the name.")
    if not anybody_drives(game, vehicle):
        return False, (f"Nobody aboard holds the ticket for a {kind.name} "
                       f"(Drive {kind.needs}).")
    return True, ""


def has_air(game, body) -> bool:
    """Is there enough atmosphere here to fly or float on?

    The Traveller profile's own answer (`sim/profile`), so one world reads
    the same to a KITE, a suit locker and a deck plan.
    """
    from . import profile as profile_sim
    got = profile_sim.profile(game, game.system, body)
    return int(getattr(got, "atmosphere", 0) or 0) >= AIR_ENOUGH


#: The thinnest atmosphere a lift fan or a ground-effect skirt will work in,
#: on `data/uwp.ATMOSPHERES`' ladder: 1 is a trace and 2 is very thin but
#: real. Below that there is nothing to push against.
AIR_ENOUGH = 2


def best_for(game, lander, body, supplies_t: float = 0.0):
    """The machine a captain would send down: whatever can go and crosses
    the most ground once it is there."""
    able = [v for v in stowed(game)
            if can_take(game, v, lander, body, supplies_t)[0]]
    return max(able, key=lambda v: (len(kind_of(v).crosses)
                                    - len(kind_of(v).refuses),
                                    v.condition), default=None)


def take_down(game, vehicle) -> dict:
    """It is on the world with them."""
    vehicle.state = DOWN
    return {"ok": True, "vehicle": vehicle}


def bring_up(game) -> dict:
    """Back in the hold, however it looks."""
    vehicle = on_the_ground(game)
    if vehicle is None:
        return {"ok": False, "why": "Nothing is down."}
    vehicle.state = "stowed"
    return {"ok": True, "vehicle": vehicle}


def lose(game, why: str) -> dict:
    """It does not come back up."""
    vehicle = on_the_ground(game)
    if vehicle is None:
        return {"ok": False, "why": "Nothing is down."}
    vehicle.state, vehicle.condition = "lost", 0
    game.add_log(f"{vehicle.name} is left where it stopped: {why}", "bad")
    return {"ok": True, "why": why}


# ── what it does on the ground ─────────────────────────────────────────────

def driving(game, exp):
    """The machine this expedition is driving, or None for on foot."""
    if exp is None or not getattr(exp, "vehicle", ""):
        return None
    return next((v for v in aboard(game)
                 if v.class_id == exp.vehicle and v.state == DOWN), None)


def ground(exp, terrain_id: str) -> str:
    """How this party's machine takes that ground: `good`, `ok` or `foot`.

    `foot` is ground the machine refuses — the party leaves it and walks —
    and it is also what a party with no machine at all gets everywhere.
    """
    kind = VEHICLES_BY_ID.get(getattr(exp, "vehicle", "") or "")
    if kind is None or int(getattr(exp, "rover", 0) or 0) <= 0:
        return "foot"
    if terrain_id in kind.refuses:
        return "foot"
    return "good" if terrain_id in kind.crosses else "ok"


def step_change(exp, terrain_id: str) -> int:
    """Days this party's machine adds to (or takes off) one step.

    The whole of what a vehicle is worth on the ground, in one number that
    `sim/expedition.step_cost` and `sim/wayhome` both read.
    """
    how = ground(exp, terrain_id)
    if how == "good":
        return -GOOD_GROUND
    if how == "foot":
        return ON_FOOT if getattr(exp, "vehicle", "") else 0
    return 0


def wear(exp, toll: int) -> int:
    """What a hazard's toll actually costs this machine, its own build
    taken into account. Returns the points knocked off."""
    kind = VEHICLES_BY_ID.get(getattr(exp, "vehicle", "") or "")
    if kind is None or toll <= 0:
        return 0
    return max(1, round(toll * kind.wear))


def says(exp) -> str:
    """One line for a screen: what they are crossing ground in."""
    kind = VEHICLES_BY_ID.get(getattr(exp, "vehicle", "") or "")
    if kind is None:
        return "On foot — nothing came down with them."
    good = ", ".join(sorted(kind.crosses))
    shut = ", ".join(sorted(kind.refuses))
    return (f"{kind.name}: a day off {good}"
            + (f"; will not enter {shut}" if shut else "")
            + f". Condition {int(getattr(exp, 'rover', 0))}/{WHOLE}.")
