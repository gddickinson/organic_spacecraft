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
    """Open an approach, or say why not."""
    ok, why = can_conn(game, contact)
    if not ok:
        return None, why
    return conn_sim.start(game, contact), ""


def spent(conn) -> float:
    """Reaction mass this approach has used so far, in tonnes."""
    return max(0.0, conn.opening_rcs - conn.rcs)


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


def commit(game, conn) -> dict:
    """Charge the chronicle for an approach and put the ship where it ended.

    Idempotent: the window calls this when the approach resolves, when the
    captain breaks off, and again when it closes, and only the first call
    does anything.
    """
    if conn is None or conn.landed:
        return {"ok": False, "already": True}
    conn.landed = True

    # Round *before* charging, so the figure in the ledger is the figure
    # taken out of the hold. `flight._incident` learned this the same way:
    # "report what was actually taken, not what was rolled".
    fuel = round(spent(conn), 2)
    if fuel > 0:
        add_cargo(game.ship, "volatiles", -fuel)
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
        game.add_log(
            f"{conn.target.name} took {conn.struck_damage:,.0f} and was "
            f"shoved {conn.struck_dv:.2f} m/s off station.", "bad")

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
    # above is something that happened before it did.
    if conn.elapsed > 0:
        game.advance_days(conn.elapsed / DAY_SECONDS)
    return out


def _tone(conn) -> str:
    return {"alongside": "good", "orbit": "good", "collision": "bad",
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
    return f"Broke off the approach on {name}: {cost}."
