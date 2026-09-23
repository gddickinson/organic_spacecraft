"""The small craft a hull carries, and the pilot who takes one out.

A player asked for single-seat fighters: launched off a carrier or a
station, flown from their own cockpit, armed — and good for a look round or
a lift across as well as a fight. `data/craft.py` holds the classes; this is
what a chronicle does with one.

- **Carried, not crewed.** A craft rides in a cradle on the outside of the
  hull with a hatch through to the cradle deck (`sim/afoot_program`), so a
  pilot walks out to it. It is never in the fleet and never jumps.
- **Somebody has to fly it.** An officer with Pilot at `data.PILOT_SKILL`,
  awake and on their feet (`pilots`). While they are out they are not at
  their station, and the ship notices.
- **A sortie is a flight**, and it is the same flight the ship's own conn
  is: a `sim/conn.Conn` built from the craft's numbers instead of the
  hull's, so every instrument, autopilot mode and berthing rule already
  written works for it (`launch`). The cockpit window flies it.
- **What it is for**: `strike` — a firing run at a hull in this system;
  `scout` — an hour's looking at a body or a contact, which is worth real
  survey data; and a lift, since a carried craft is the ship's boat when a
  crew has to get across (`sim/crossing.has_boat`).
- **Recovery** is the cradle: back inside `RECOVER_KM` and slow, or she
  stays out. Reaction mass is the craft's own tank and does not come out of
  the hull's hold.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..core.save import register
from ..data import craft as table
from ..data.craft import CRAFT_BY_ID

#: How near the hull, in km, and how slow, in m/s, a craft is taken back on.
RECOVER_KM, RECOVER_RATE = 2.0, 4.0
#: The share of the ship's own reaction mass a cradle will put into a craft
#: when she comes home. **Never all of it.** Measured when a lander came up
#: from every landing with a full tank off the hull: a six-year chronicle
#: drained its volatiles to nothing, coasted seventeen days to the next
#: port with no mass to burn, could not buy food, and died of it on day
#: 1,233 with a crew of nobody. A cradle fills a craft out of what the ship
#: can spare.
TOP_UP_SHARE = 0.5
#: What a firing run costs the craft in reaction mass. What a run and a look
#: *do* is `sim/craft_errands.py`, split out at five hundred lines; this is
#: here because the cradle's own rules read it too.
STRIKE_T = 0.4


@register
@dataclass
class Carried:
    """One craft, in its cradle or out on a sortie."""

    id: int
    class_id: str
    name: str
    hp: int
    fuel: float
    #: cradled | out | lost
    state: str = "cradled"
    #: Who is flying her (`captain` or `officer:<id>`), or "" in the cradle.
    pilot: str = ""
    sorties: int = 0
    struck: int = 0
    #: Hours flown, all told.
    hours: float = 0.0
    log: list = field(default_factory=list)


def kind_of(craft) -> table.CraftClass:
    return CRAFT_BY_ID[craft.class_id]


def aboard(game) -> list:
    """Every craft this hull carries, cradled or out."""
    return [c for c in getattr(game, "craft", []) or []
            if c.state != "lost"]


def flying(game):
    """The craft out on a sortie, or None."""
    return next((c for c in aboard(game) if c.state == "out"), None)


def give(game, class_id: str = table.STARTING_CRAFT, name: str = "") -> Carried:
    """Put a craft in a cradle on this hull. The one door for acquiring one."""
    kind = CRAFT_BY_ID[class_id]
    craft = Carried(id=len(getattr(game, "craft", []) or []) + 1,
                    class_id=class_id, name=name or _name_for(game, kind),
                    hp=kind.hull, fuel=kind.fuel_t)
    game.craft = list(getattr(game, "craft", []) or []) + [craft]
    return craft


def _name_for(game, kind) -> str:
    """A craft is named off the hull she rides: the *Increment's* Wasp."""
    hull = getattr(getattr(game, "ship", None), "name", "") or "the hull"
    return f"{hull}'s {kind.name.title()}"


# ── who may fly her ────────────────────────────────────────────────────────

def pilots(game, craft) -> list:
    """Everybody aboard who could take this craft out, in the same shape the
    walking party is chosen by (`afoot_people.pool`): `(key, name, what, ok,
    why)`, the key `captain` or `officer:<id>`.

    The qualification is Pilot at the class's own certificate and nothing
    else — a craft is flown, not crewed, and the rating is the rating. The
    captain holds one: it is their ship.
    """
    from . import afoot_people
    kind, out = kind_of(craft), []
    for key, name, what, ok, why in afoot_people.pool(game):
        if key.startswith("robot:"):
            continue              # a frame does not fit the seat
        skill = rating(game, key)
        if ok and skill < kind.needs:
            ok, why = False, (f"{kind.name} is flown on Pilot "
                              f"{kind.needs}; {name} is {ticket(skill)}.")
        if ok and craft.state == "out" and craft.pilot == key:
            ok, why = False, f"{name} is already out in her."
        out.append((key, name, f"{what} · {ticket(skill).capitalize()}", ok,
                    why))
    return out


def ticket(skill: int) -> str:
    """A Pilot rating in words: untrained, trained, or the number."""
    from . import checks
    if skill <= checks.UNTRAINED:
        return "untrained"
    return "trained (Pilot 0)" if skill == 0 else f"Pilot {skill}"


def rating(game, key: str) -> int:
    """What this person's Pilot ticket reads."""
    from . import afoot_people, lifepath
    if key == "captain":
        return afoot_people.captain_record(game).skill("pilot")
    officer = afoot_people.officer_of(game, int(key.split(":")[-1]))
    return lifepath.of(game, officer).skill("pilot") if officer else -3


def name_of(game, key: str) -> str:
    from . import afoot_people
    if key == "captain":
        return afoot_people.captain_name(game)
    officer = afoot_people.officer_of(game, int(key.split(":")[-1]))
    return getattr(officer, "name", "nobody")


def away(game) -> set:
    """Whose station is empty because they are out in a craft.

    Keys as `pilots` gives them (`captain`, `officer:<id>`). One door, so
    everything that reads the bridge reads the same absence.
    """
    return {got.pilot for got in aboard(game)
            if got.state == "out" and got.pilot}


def at_stations(game) -> list:
    """The officers actually standing their watch.

    `pilots` has always said "whoever goes is off their station until she is
    back", and nothing made it so: an officer could fly a sortie and go on
    conning, shooting and mending from the cockpit, because `recompute` fed
    `ship.stats` the whole list. The ship notices now.
    """
    out = away(game)
    return [o for o in getattr(game, "officers", []) or []
            if f"officer:{o.id}" not in out]


def best_pilot(game, craft) -> str:
    """Whom a captain would send: the best ticket aboard that may go."""
    able = [key for key, _n, _w, ok, _why in pilots(game, craft) if ok]
    return max(able, key=lambda key: rating(game, key)) if able else ""


def who_flies(game, craft) -> str:
    """Whom a captain sends when they have not said — **not themselves**.

    A captain in a cockpit is not on the bridge: they cannot take a station
    in an engagement (`sim/craft_battle.on_the_bridge`), and a captain who
    flies the lander down is away for the whole of a landing party's weeks
    on the ground. Measured when `take_down` used `best_pilot` (which
    prefers the best rating, and the captain holds it): a six-year
    chronicle went from 54 landings and 18 parties walking home to 6
    landings, none home, and a crew of nobody — because every station order
    of every engagement in those weeks was refused.

    So the best ticket that is *not* the captain's goes, and the captain
    only if nobody else aboard holds one. `best_pilot` is still the answer
    where the captain flying is the point.
    """
    able = [key for key, _n, _w, ok, _why in pilots(game, craft) if ok]
    others = [key for key in able if key != "captain"]
    return max(others or able, key=lambda key: rating(game, key), default="")


# ── the sortie ─────────────────────────────────────────────────────────────

def can_launch(game, craft, pilot: str = "") -> tuple:
    """May this craft go out now?"""
    if craft is None or craft.state == "lost":
        return False, "There is no such craft aboard."
    if craft.state == "out":
        return False, f"{craft.name} is already out."
    if flying(game) is not None:
        return False, "Another craft is out; the cradle deck is busy."
    if getattr(game, "battle", None) is not None:
        return False, "Not in the middle of an engagement."
    if craft.hp <= 0:
        return False, f"{craft.name} is wrecked."
    if craft.fuel <= table.LAUNCH_T:
        return False, f"{craft.name} has no reaction mass in her."
    if pilot:
        row = next((r for r in pilots(game, craft) if r[0] == pilot), None)
        if row is None:
            return False, "Nobody of that name is aboard."
        if not row[3]:
            return False, row[4]
    elif not best_pilot(game, craft):
        return False, ("Nobody aboard holds the certificate for her "
                       f"(Pilot {kind_of(craft).needs}).")
    return True, ""


def launch(game, craft, pilot: str = "") -> dict:
    """Off the cradle and into her own flight (`sim/conn`).

    The flight is the ship's own machinery with the craft's numbers in it,
    so the cockpit's instruments, its autopilot and every berthing rule are
    the ones already written and already checked.
    """
    ok, why = can_launch(game, craft, pilot)
    if not ok:
        return {"ok": False, "why": why}
    pilot = pilot or best_pilot(game, craft)
    who = name_of(game, pilot)
    from . import freeflight
    conn, why = freeflight.begin(game)
    if conn is None:
        return {"ok": False, "why": why}
    _fit(conn, craft)
    conn.log.append(f"{craft.name} away, {who} at the stick.")
    game.sortie = conn
    craft.state, craft.pilot = "out", pilot
    craft.sorties += 1
    craft.fuel = max(0.0, craft.fuel - table.LAUNCH_T)
    conn.rcs = conn.opening_rcs = craft.fuel
    game.add_log(f"{craft.name} launched — {who} flying.", "")
    return {"ok": True, "conn": conn, "pilot": pilot, "who": who,
            "craft": craft}


def _fit(conn, craft) -> None:
    """Put the craft's own numbers into a flight built for the ship."""
    from .conn import TICK
    kind = kind_of(craft)
    conn.mass_t = kind.mass_t
    conn.main_dv = kind.thrust_g * 9.80665 * TICK
    conn.rcs_dv = kind.rcs
    conn.slew_rate = kind.slew
    conn.array = kind.sensor
    conn.hold = 1.0
    conn.rcs = conn.opening_rcs = craft.fuel


def sortie(game):
    """The flight a craft is out on, or None."""
    return getattr(game, "sortie", None)


def out_km(game) -> float:
    """How far the craft is from the hull she flew off, in km."""
    conn = sortie(game)
    if conn is None:
        return 0.0
    from . import freeflight
    from .anchorage import KM_PER_AU
    from .flight import base_position
    where = freeflight.where(game, conn)
    return math.dist(where, base_position(game)) * KM_PER_AU


def bill(game) -> float:
    """Charge the chronicle for the sortie's flying, the way the conn's own
    clock does — and take the mass off the *craft's* tank, not the hull's."""
    conn, craft = sortie(game), flying(game)
    if conn is None or craft is None:
        return 0.0
    seconds = max(0.0, conn.elapsed - float(getattr(conn, "billed", 0.0)))
    if seconds <= 0.0:
        return 0.0
    conn.billed = conn.elapsed
    craft.hours += seconds / 3600.0
    craft.fuel = max(0.0, conn.rcs)
    game.advance_days(seconds / 86400.0)
    return seconds


def beat(game, axis: str | None = None, main: bool = False,
         ticks: int = 1) -> dict:
    """One beat of the sortie — the cockpit's clock, and the bridge's.

    The same shape as the ship's own beat (`ui/flight_clock.fly_beat`): the
    pilot's hand on the stick outranks the computer, the computer flies
    whatever mode is armed (`sim/flightdeck.computer`), and the minute is
    billed to the chronicle and to the craft's tank. It lives here because
    it is a rule, and a window owns none.
    """
    conn, craft = sortie(game), flying(game)
    if conn is None or craft is None:
        return {"ok": False, "why": "Nothing is out."}
    from . import conn as conn_sim
    from . import flightdeck, freeflight
    for _ in range(max(1, int(ticks))):
        freeflight.hold_course(game, conn)
        if axis or main:
            conn_sim.apply(conn, axis, main=main, ticks=1)
        else:
            order, drive, throttle = flightdeck.computer(game, conn)
            conn_sim.apply(conn, order, main=drive, ticks=1,
                           throttle=throttle)
        if conn.over:
            break
    bill(game)
    # The bridge's own window is not beating while the cockpit is, so its
    # view of her is refreshed from here too (`sim/sky.company`).
    from . import sky as sky_sim
    if getattr(game, "conn", None) is not None:
        sky_sim.refresh_company(game, game.conn)
    craft.hp = min(craft.hp, kind_of(craft).hull)
    out = {"ok": True, "km": round(out_km(game), 2),
           "fuel": round(craft.fuel, 2), "outcome": conn.outcome or ""}
    if craft.fuel <= 0.0 and out_km(game) > RECOVER_KM:
        # Dry, and not within reach of the cradle: the hull has to come and
        # get her, which is the ship's time rather than the craft's.
        out["adrift"] = True
    return out


def top_up(game, craft) -> float:
    """Fill a craft's tank from the ship's own reaction mass, up to what the
    ship can spare (`TOP_UP_SHARE`). Returns the tonnes moved.

    The one door: a cradle that took whatever it needed starved the hull
    that carried it.
    """
    kind = kind_of(craft)
    want = max(0.0, kind.fuel_t - craft.fuel)
    spare = float(game.ship.cargo.get("volatiles", 0.0))
    took = max(0.0, min(want, spare * TOP_UP_SHARE))
    if took:
        game.ship.cargo["volatiles"] = spare - took
        craft.fuel += took
    return took

def can_recover(game) -> tuple:
    """Is she in a state to be taken back aboard?"""
    craft, conn = flying(game), sortie(game)
    if craft is None or conn is None:
        return False, "Nothing is out."
    far = out_km(game)
    if far > RECOVER_KM:
        return False, (f"{far:,.1f} km off the cradle — bring her inside "
                       f"{RECOVER_KM:g} km.")
    if conn.speed > RECOVER_RATE:
        return False, (f"{conn.speed:,.1f} m/s — a cradle takes a craft at "
                       f"{RECOVER_RATE:g} or under.")
    return True, ""


def recover(game) -> dict:
    """Back on the cradle: the pilot to their station, the tank topped up
    from the hull's own reaction mass if there is any to spare."""
    craft, conn = flying(game), sortie(game)
    ok, why = can_recover(game)
    if not ok:
        return {"ok": False, "why": why}
    bill(game)
    kind = kind_of(craft)
    craft.state, craft.pilot = "cradled", ""
    took = top_up(game, craft)
    game.sortie = None
    game.add_log(f"{craft.name} is back on the cradle.", "good")
    return {"ok": True, "fuelled": round(took, 2),
            "hours": round(craft.hours, 2)}


def lose(game, why: str) -> dict:
    """She does not come back. The pilot goes with her unless they got out."""
    craft = flying(game)
    if craft is None:
        return {"ok": False, "why": "Nothing is out."}
    craft.state, craft.hp = "lost", 0
    game.sortie = None
    game.add_log(f"{craft.name} is lost: {why}", "bad")
    return {"ok": True, "why": why}


# The two errands a single seat is sent on live in `sim/craft_errands.py`
# (split out at 500 lines); re-exported so `craft.strike` stays the door.
from .craft_errands import (RETURN_FIRE, SCOUT_DATA,  # noqa: E402,F401
                            SCOUT_HOURS, can_scout, can_strike, scout,
                            strike, targets)
