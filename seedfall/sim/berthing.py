"""What a finished approach does to the chronicle.

`sim/conn.py` flies the ship and `sim/autopilot.py` advises it, and neither
touches the save — which was right as far as it went, and left the conn a
sandbox. Measured on a fresh chronicle before this module existed:

    flew into Fleet Hub at 20 m/s  ->  collision, damage 50.0
    berthed alongside              ->  0.54 t of reaction mass, 0.8 h elapsed

    day    0     -> 0        same
    fuel   20    -> 20       same
    hull   336   -> 336      same
    where  None  -> None     same

Nothing. You could wreck the ship against a station and walk away, berth
alongside a quay and not be docked, and burn a tank the ship never had — the
conn invented 36.8 t of reaction mass for a hull carrying 20.

This is where it lands. Three rules, and they are the whole module:

* **Reaction mass is the ship's.** `conn.start` now opens the tank at the
  hull's actual volatiles; `commit` charges what the approach spent.
* **Time is the sector's.** An approach takes hours; the clock hears about it
  once, at the end, because `clock.advance_days` draws on `game.rng` every
  call and settling a hundred times would burn the save's luck for nothing.
* **A berth is a place.** Coming alongside a quay, or making orbit, sets
  `orbit_body` — which is what every other screen in the game reads to know
  where the hull is standing.

`commit` is idempotent and is called whether the approach ended well, badly,
or was broken off half-way. Breaking off does not refund the mass.
"""

from __future__ import annotations

import math

from . import conn as conn_sim
from . import flight
from . import track as track_sim
from .ship import add_cargo, apply_damage

#: How near you must already be to take the conn, in km.
#:
#: Derived, not tuned. The conn's own frame is at most a few thousand
#: kilometres across, so anything it can reach is somewhere the ship already
#: is. Measured across chronicles, the distances are bimodal and the gap is
#: enormous: a contact at your body reads **0.000 AU** and everything else
#: reads **2.2 AU or more**. So this threshold sits in empty space and the
#: check that holds it proves the rule rather than the number.
REACH_KM = 200_000.0

KM_PER_AU = 149_597_870.7

#: Seconds in a day, for handing the conn's clock to the sector's.
DAY_SECONDS = 86_400.0


def reach_to(game, contact) -> float:
    """How far the ship is from a contact right now, in km."""
    sx, sy = flight.ship_position(game)
    x, y = track_sim.at(game, contact, game.day)
    return math.hypot(x - sx, y - sy) * KM_PER_AU


def can_conn(game, contact) -> tuple[bool, str]:
    """May the ship take the conn on this? The gate the button greys on.

    The conn is the last few kilometres, not a transfer. Something on the far
    side of the system is not refused because it is hard — it is refused
    because closing it is a *burn*, and the plotting board is where you plot
    one.
    """
    if contact is None:
        return False, "Nothing selected."
    if contact.kind == "point":
        return False, ("A position in empty space is somewhere to steer for, "
                       "not something to come alongside.")
    if getattr(game, "docking", None) is not None:
        return False, "An approach is already running."
    away = reach_to(game, contact)
    if away > REACH_KM:
        return False, (
            f"{contact.name} is {away / KM_PER_AU:.2f} AU off. The conn is "
            "for the last few kilometres — plot a transfer to it first.")
    if float(game.ship.cargo.get("volatiles", 0)) < conn_sim.RCS_COST:
        return False, ("Not a gram of reaction mass aboard. The thrusters "
                       "cannot even nudge.")
    return True, ""


def begin(game, contact):
    """Open an approach, or say why not.

    **Two gates, and they ask different sides.** `can_conn` asks the ship —
    is it near enough, has it any reaction mass, is an approach already
    running. `sim/clearance.py` asks the *structure* — will it have you, and
    at which berth. Until the second existed a hostile patrol and a Charter
    Fleet Hub offered the same welcome, because neither was ever asked.
    """
    from . import clearance as clearance_sim
    ok, why = can_conn(game, contact)
    if not ok:
        return None, why
    conn = conn_sim.start(game, contact)
    cleared = clearance_sim.request(game, contact, conn)
    conn.cleared = cleared
    # **A clearance is for docking, not for flying near something.** The first
    # version refused any approach that was not granted one, which shut every
    # *orbit*: a world is not a thing that clears you, and going into orbit
    # round one needs nobody's permission. Two checks caught it — the climb
    # rungs and the conn's own screens — because a body approach stopped
    # opening at all.
    if not cleared.granted and contact.kind in ("anchorage", "hull"):
        return None, cleared.why
    if cleared.granted:
        # The berth is the one the *port* assigned, not the one the ship
        # fancied.
        conn.berth = cleared.berth
        game.add_log(clearance_sim.line(cleared), "")
    # What this structure could do about an uncleared hull, and how long it
    # would put up with one. Set whether or not the clearance was granted —
    # a refusal is precisely when it matters.
    from . import control
    conn.watch = control.post(game, contact)
    return conn, ""


def spent(conn) -> float:
    """Reaction mass this approach has used so far, in tonnes."""
    return max(0.0, conn.opening_rcs - conn.rcs)


def secure_underway(game) -> None:
    """Settle a live conn before the hull is moved out from under it.

    **The one door for every transfer.** `transit.begin` and
    `flight.travel_to` both teleport the hull across the system; a flight
    left on `game.conn` would carry its frame, its spend and its unbilled
    hours across the jump, and a conn window would re-apply the old offset
    on top of the new position. A free flight secures where it stands — the
    drift is real, and `flight.stand_off` writes it down before the transfer
    departs from there; an approach is broken off. Either way `commit` bills
    it, so nothing is flown for free.
    """
    conn = getattr(game, "conn", None)
    if conn is None or conn.landed:
        return
    from . import freeflight as free_sim
    if free_sim.is_free(conn):
        game.add_log(free_sim.secure(game, conn), "")
    elif not conn.over:
        conn.outcome = "broken off"
        conn.log.append("Secured for transfer.")
    commit(game, conn)
    game.conn = None


def preview(game, conn) -> dict:
    """What committing now would cost, in the terms the panel shows.

    The same fields `commit` reports, so what the window promises before the
    approach ends is what it charges when it does.
    """
    return {
        "fuel": round(spent(conn), 2),
        "days": conn.elapsed / DAY_SECONDS,
        "hours": conn.elapsed / 3600.0,
        "damage": conn.damage,
        "berths": _berth_index(conn) is not None,
    }


def _berth_index(conn) -> int | None:
    """Where this approach would leave the ship, if anywhere.

    Only an outcome that ends *at* something moves the hull. A collision is
    still a berth of sorts — you are alongside, and dented — but going aground
    on a world, drifting off, or breaking off leaves you where you were.
    """
    if conn.outcome not in ("alongside", "orbit", "collision"):
        return None
    return conn.target.body_index


def charge_flown(game, conn) -> float:
    """Bill the chronicle for time this conn has flown and not yet paid for.

    **The one door for turning flying into elapsed time**, and there have to
    be two callers: `commit`, which settles an approach at the end, and a
    screen that flies with the clock running and settles as it goes. Both
    charging the same minute would let a pilot who broke off pay twice for
    the same hour.

    Charging in pieces is *exactly* charging once, and that is not an
    approximation — `core/clock.MAX_STEP` is 1, so a jump of N days is N
    jumps of one (#116). Measured: three days billed in one call and in 4,320
    leave the same day and the same purse to the cent.

    Returns the seconds actually billed.
    """
    # **The mass too, as it burns (#149).** Reaction mass used to come off the
    # hull only in `commit`, unlike the hours — so a flight nobody ever ended
    # was never charged for its tonnes, and every screen reading the hold
    # while the clock ran showed a tank the flying had not touched.
    # `conn.charged_rcs` is the tonnes already taken, the same shape as
    # `charged` is for the seconds, so neither door can bill twice.
    owed_rcs = spent(conn) - float(getattr(conn, "charged_rcs", 0.0))
    if owed_rcs > 0.0:
        conn.charged_rcs = float(getattr(conn, "charged_rcs", 0.0)) + owed_rcs
        add_cargo(game.ship, "volatiles", -owed_rcs)
    owed = float(conn.elapsed) - float(getattr(conn, "charged", 0.0))
    if owed <= 0.0:
        return 0.0
    conn.charged = float(conn.elapsed)
    game.advance_days(owed / DAY_SECONDS)
    return owed


def commit(game, conn) -> dict:
    """Charge the chronicle for an approach and put the ship where it ended.

    Idempotent: the window calls this when the approach resolves, when the
    captain breaks off, and again when it closes, and only the first call
    does anything.
    """
    if conn is None or conn.landed:
        return {"ok": False, "already": True}
    conn.landed = True

    # **Exact, and only what nobody has billed yet (#148, #149).** This used
    # to charge `round(spent, 2)`, which *refunded* up to 0.005 t on securing
    # — measured, 2.715 t burned came back as 17.29 t aboard from 17.285. The
    # hold pays the exact figure now, through the same `charged_rcs` meter
    # `charge_flown` uses, so a screen that bills as it flies and a commit at
    # the end cannot take the same gram twice. The ledger line still reads to
    # two places, because that is a display of the charge and not the charge.
    fuel = round(spent(conn), 2)
    owed_rcs = spent(conn) - float(getattr(conn, "charged_rcs", 0.0))
    if owed_rcs > 0:
        conn.charged_rcs = float(getattr(conn, "charged_rcs", 0.0)) + owed_rcs
        add_cargo(game.ship, "volatiles", -owed_rcs)
    hurt = 0.0
    if conn.damage:
        hurt = apply_damage(game.ship, conn.damage)

    # **And what the other thing took.** A collision is two bodies, and until
    # `sim/impulse.py` it was one: the damage came off the player's hull and
    # the quay it was struck against was neither moved nor marked. The figures
    # come off the approach, worked out from both masses, and the chronicle
    # says so — a captain who uses a hub as a backstop should find it in the
    # log, and so should anyone reading back.
    if conn.struck_damage or conn.struck_dv:
        from . import knock as knock_sim
        hit = knock_sim.record(game, conn.target, conn.struck_dv,
                               damage=conn.struck_damage)
        peak = (knock_sim.km_after(hit, game.day + knock_sim.KEEPING_DAYS)
                if hit is not None else 0.0)
        game.add_log(
            f"{conn.target.name} took {conn.struck_damage:,.0f} and was "
            f"shoved {conn.struck_dv:.2f} m/s off station"
            + (f" — {peak:,.0f} km adrift at worst." if peak >= 1.0 else "."),
            "bad")

    # A structure that worked itself away from an unwelcome hull really is
    # somewhere else afterwards. Through `sim/knock`, the same door a shove
    # uses, so the plot, the ranges and every forecast agree about where it
    # now is — a station that ran from you is a station you have to chase.
    if getattr(conn, "sheered", 0.0) > 0.0:
        from . import control
        from . import knock as knock_sim
        knock_sim.record(game, conn.target, control.SHEER_RATE)
        game.add_log(
            f"{conn.target.name} stood off under power rather than take you "
            f"alongside — {conn.sheered * 1000:,.0f} m opened, and it is not "
            "back on station yet.", "warn")

    # **And what the power holding it will remember.** Until now an approach
    # could be hailed, warned, shot at and cut open, and the sector's politics
    # would not have heard of any of it: `control.provoked` was written the
    # day the ladder landed and read by nobody. `forcing.grievance` is the one
    # door, and it is deliberately quiet below being fired on — a sector where
    # every power bore a grudge over a radio call would have no room left for
    # the ones that matter.
    from . import forcing as forcing_sim
    grief = forcing_sim.grievance(conn)
    if grief and grief.get("faction"):
        from . import grudge as grudge_sim
        grudge_sim.note(game, grief["faction"], grief["kind"], grief["text"],
                        salience=grief["salience"])
        game.add_log(grief["text"] + " It is in their books now.", "bad")

    moved = None
    index = _berth_index(conn)
    if index is not None and 0 <= index < len(game.system.bodies):
        body = game.system.bodies[index]
        if game.orbit_body != body.id:
            moved = body
        flight.hold_at(game, body)
        # And *where* in the orbit, which is what the departure cost and the
        # survey resolution both read. An approach that ended alongside a
        # quay rather than in orbit carries no height, and neither does one
        # where the captain never chose.
        game.orbit_alt_km = (conn.range_km if conn.outcome == "orbit" else 0.0)

    game.add_log(_line(conn, fuel, hurt), _tone(conn))

    out = {"ok": True, "fuel": fuel, "damage": round(hurt, 1),
           "hours": round(conn.elapsed / 3600.0, 1),
           "moved": moved.name if moved is not None else None,
           "outcome": conn.outcome, "lost": False}

    # Impact damage is quadratic and uncapped, so an approach really can end
    # the chronicle. Nothing else in the game strips a hull to nothing without
    # saying so, and it must not be the exception.
    if conn.damage and not any(layer.hp > 0 for layer in game.ship.layers):
        out["lost"] = True
        game.die(f"Broken up against {conn.target.name}.")
        return out

    # The clock last, because it can end the chronicle too, and everything
    # above is something that happened before it did. Through `charge_flown`,
    # which only ever bills the minutes nobody has billed yet — a screen that
    # flies with the clock running has already paid for some of them.
    if conn.elapsed > 0:
        charge_flown(game, conn)
    return out


def _tone(conn) -> str:
    return {"alongside": "good", "orbit": "good", "collision": "bad",
            "down": "good", "ditched": "warn",
            "aground": "bad", "adrift": "warn", "dry": "warn"}.get(
                conn.outcome, "")


def _line(conn, fuel: float, hurt: float) -> str:
    """One line for the ledger, saying what it cost and what it bought."""
    name = conn.target.name
    cost = f"{fuel:.2f} t of reaction mass"
    if conn.elapsed >= 3600:
        cost += f" over {conn.elapsed / 3600:.1f} hours"
    if conn.outcome == "alongside":
        return f"Came alongside {name}: {cost}."
    if conn.outcome == "orbit":
        return f"Made orbit at {name}: {cost}."
    if conn.outcome == "collision":
        return (f"Struck {name} coming in: {round(hurt)} off the hull, "
                f"and {cost}.")
    if conn.outcome == "aground":
        return f"Put the hull down on {name}: {round(hurt)} off her, {cost}."
    if conn.outcome == "adrift":
        return f"Lost the approach on {name}. {cost.capitalize()} for nothing."
    if conn.outcome == "dry":
        return (f"Ran the thrusters dry off {name} without making orbit: "
                f"{cost}.")
    if conn.outcome == "secured":
        # A free flight was not an approach and did not fail: the ship went
        # somewhere because the captain flew it there. Saying "broke off the
        # approach on open space" would be two lies in one line.
        flew = math.dist(conn.pos, (0.0, 0.0, 0.0))
        return (f"Under way on the conn: {flew:,.0f} km flown, {cost}.")
    return f"Broke off the approach on {name}: {cost}."
