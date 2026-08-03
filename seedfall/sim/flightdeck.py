"""The flight deck: one front door to the one flight computer.

The player asked for it in as many words: "the same system responsible for
all operations (docking, berthing, moving away, flying to set destinations,
orbiting) — not split up among different controllers." This is that system's
front door. `can_arm` is the gate every autopilot button in the game greys
on, and `computer` is the dispatcher every beat asks: null, brake, close,
orbit, run and depart are all verbs of the *same* computer — the law lives
in `sim/autopilot`, the free-flight mechanics in `sim/freeflight`, and no
screen owns a private one.
"""

from __future__ import annotations

from .freeflight import ALONGSIDE_KM, alongside, marked, run_for
from .targets import is_open


def depart_rung(conn) -> float | None:
    """The lowest orbit rung above this one the tank can actually buy.

    Departing a world is a climb, and a climb is a fuel decision — the same
    rule `pilot.climb_options` already prices for the height picker, asked
    here so the computer and the picker cannot offer different ladders.
    """
    from . import orbits
    from . import pilot as pilot_sim
    here = orbits.semi_major_km(conn)
    if here == float("inf") or here <= 0:
        here = conn.range_km
    for row in pilot_sim.climb_options(conn):
        if row["afford"] and row["radius"] > here * 1.05:
            return float(row["radius"])
    return None


def can_arm(game, conn, mode: str) -> tuple[bool, str]:
    """May this mode be armed on this flight? The gate every console greys on.

    `close` and `orbit` on an open-space target used to arm, stay lit, and
    coast for ever — `autopilot.target_velocity` refuses them (correctly),
    the window read the refusal as "still flying", and the clock ran with
    nothing at the controls. Refuse at the *button*, with the reason.
    """
    if conn is None or conn.over:
        return False, "Nothing is being flown."
    if not mode:
        return True, ""
    if mode == "run":
        if marked(game, conn) is None:
            return False, "Lay a course on something first."
        return True, ""
    if mode in ("close", "orbit", "depart") and is_open(conn.target):
        return False, ("Nothing to " + {"close": "berth at", "orbit": "orbit",
                       "depart": "move away from"}[mode] + " out here — lay "
                       "a course and run, or take the conn on something.")
    if mode == "orbit" and conn.target.mu > 0 and conn.orbit_want_km <= 0:
        # **"Make orbit" in the orbit you are already in ends the flight.**
        # Armed with no height asked for, `at_wanted_height` is satisfied on
        # the spot and `outcome.resolve` writes "orbit" — the approach over
        # before anything was flown. There is nothing to do here, so say so
        # and point at the control that *can* change it.
        from . import orbits
        if orbits.in_orbit(conn):
            return False, (f"She is already in a sound orbit of "
                           f"{conn.target.name}. Pick a height to move it, "
                           "or move away.")
    if mode == "depart" and conn.target.mu > 0 and depart_rung(conn) is None:
        # Leaving a world is a climb — and there are two reasons there may
        # be no climb, which want different answers from the captain. A
        # refusal that blames the tank when the truth is "you are already
        # higher than this world's ladder" sends them to buy volatiles they
        # do not need.
        from . import orbits
        from . import pilot as pilot_sim
        here = orbits.semi_major_km(conn)
        if here == float("inf") or here <= 0:
            here = conn.range_km
        above = [r for r in pilot_sim.climb_options(conn)
                 if r["radius"] > here * 1.05]
        if not above:
            return False, (f"She is already above every orbit "
                           f"{conn.target.name} offers. Leaving a world is a "
                           "transfer — plot one at the helm.")
        # There *are* rungs above and the ladder is selling none of them.
        # Why is the height picker's business — it prices every rung and
        # says on each what refuses it — and repeating the gate here is how
        # two screens come to give a captain different reasons.
        return False, (f"No higher orbit at {conn.target.name} is on offer "
                       "on this hull — the height picker prices each rung and "
                       "says why. Leaving a world is a transfer, plotted at "
                       "the helm.")
    if mode == "close" and getattr(conn.target, "kind", "") == "hull":
        # `moorings.aim` has no fitting to fly to on another ship, so the
        # computer would close on its *centre* — which is a collision worn
        # as a mode. Coming alongside a hull is hand-flying.
        return False, ("Another hull keeps no mast for you. The computer "
                       "will not fly it — take her alongside by hand.")
    return True, ""


def computer(game, conn) -> tuple:
    """What the one flight computer does this beat, under `conn.auto`.

    `(axis, main, throttle)` — the shape `sim/autopilot` returns, because
    every branch is `sim/autopilot`. This is the single dispatcher every
    window's beat asks, so the bridge, the conn and the flight panel cannot
    fly three different computers at one hull.

    **The tug outranks it.** `tug_step` walks the hull in and zeroes the
    velocity every substep, and an armed mode reading that stillness as error
    burned against the boats each tick — spending the mass the tug exists to
    save, under a console printing "Hands off the drive". The computer keeps
    its hands off.
    """
    from . import autopilot as auto_sim
    from . import tug as tug_sim
    mode = getattr(conn, "auto", "")
    if not mode or conn is None or conn.over:
        return None, False, 1.0
    from . import tutorial_watch
    tutorial_watch.deed(game, "computer_flew")   # the computer has her
    if tug_sim.under_tow(conn):
        return None, False, 1.0
    # **The computer does not fly her into things.** Whatever mode is armed,
    # if something is in the way and the room is running out, the burn this
    # tick is the one that sheds the excess — the whole of "calculate the
    # braking so it does not drive you into something". A pilot who *means*
    # to hit it turns the safeties off, and then this says nothing.
    if getattr(conn, "safeties", True):
        from . import collision
        threat = collision.scan(game, conn)
        if threat is not None and threat.must_brake:
            if conn.avoiding != threat.name:
                conn.avoiding = threat.name
                game.add_log(collision.line(threat), collision.tint(threat))
            return auto_sim.hold(conn, collision.brake_velocity(conn, threat))
        conn.avoiding = ""
    if mode == "run":
        aim = marked(game, conn)
        if aim is None:
            return None, False, 1.0
        if alongside(game, conn, aim):
            # Arrived. Say so once and hold station.
            conn.auto = "null"
            game.add_log(f"Alongside {aim.name}, "
                         f"{ALONGSIDE_KM:,.0f} km off.", "")
            return auto_sim.autopilot(conn, "null")
        return run_for(game, conn, aim)
    if mode == "brake":
        # Null with a hand-back: kill the way on; when still, say so and
        # give the conn back — was three presses for the commonest manoeuvre.
        if conn.speed <= conn.rcs_dv * 0.75:
            conn.auto = ""
            game.add_log("All stopped. The conn is yours.", "")
            return None, False, 1.0
        return auto_sim.hold(conn, [0.0, 0.0, 0.0])
    if mode == "depart" and conn.target.mu > 0:
        # **In a gravity well, moving away is climbing.** The radial demand
        # below is right where nothing pulls and catastrophic where
        # something does: it asks the drive to cancel the whole orbital
        # velocity — measured at a world, 2,779 m/s of it — so the hull
        # simply decayed and went **aground**. The same fault
        # `autopilot.target_velocity` records twice about purely tangential
        # and purely radial demands. Departing a world is a climb to a
        # higher rung, flown by the orbit law that `test_climbs` holds.
        from . import orbits
        here = orbits.semi_major_km(conn)
        if here == float("inf") or here <= 0:
            here = conn.range_km
        # A climb already under way is *not* re-asked of the ladder every
        # tick: she rises out of the rungs she is buying, and re-asking
        # abandoned the climb halfway up.
        if conn.orbit_want_km <= here * 1.02:
            want = depart_rung(conn)
            if want is None:
                conn.auto = ""
                game.add_log(f"No orbit above this one at "
                             f"{conn.target.name} is within the tank. Plot a "
                             "transfer from the helm to leave.", "warn")
                return None, False, 1.0
            conn.orbit_want_km = want
        return auto_sim.autopilot(conn, "orbit")
    if mode == "depart":
        # Moving away, by the same computer that comes alongside: out to
        # clear space — past the corridor, past the arrival range — then
        # stop, say so, and hand back. The one operation the system had no
        # mode for: leaving was manual or it was a transfer.
        from . import moorings
        goal = max(conn.start_km, moorings.corridor_km(conn.target)) * 1.1
        if conn.range_km >= goal:
            if conn.speed <= conn.rcs_dv * 0.75:
                conn.auto = ""
                game.add_log(f"Standing clear of {conn.target.name}, "
                             f"{conn.range_km:,.1f} km off. The conn is "
                             "yours.", "")
                return None, False, 1.0
            return auto_sim.hold(conn, [0.0, 0.0, 0.0])
        r = conn.range_km or 1e-6
        out = [c / r for c in conn.pos]
        rate = auto_sim.rate_for(max(0.0, goal - conn.range_km), conn.rcs_dv)
        return auto_sim.hold(conn, [c * rate for c in out])
    return auto_sim.autopilot(conn, mode)


