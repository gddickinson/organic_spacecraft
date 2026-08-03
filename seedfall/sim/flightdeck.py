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
    if tug_sim.under_tow(conn):
        return None, False, 1.0
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


