"""Engines with places, a hull that has to point them, and a transfer in parts.

Three gaps the captain named, and they interlock: without geometry there is no
thrust axis, without a thrust axis attitude means nothing, and without either
a transfer cannot be broken into burns.

What was there before: drive slots were a *count*, `Conn.heading` was written
by nothing at all, and `flight._leg` handed back one lump of days and mass
with the braking burn living only in a comment.

Three faults surfaced while building it, all by playing:

* **A bigger engine made every hull worse.** One tick of a fusion torch on a
  SPORE is 124 m/s, so the computer lit it to trim ten, overshot, corrected
  the overshoot and never converged. The worst drift a hull could recover from
  ran 60, then 2, then 140 m/s across three drives of *increasing* thrust.
  Engines throttle now.
* **The old control law was a ladder of branches** — fix the drift, else the
  closing rate, else coast — each with its own threshold. It held together at
  the flat delta-v the conn used to assume and fell apart across a 160-fold
  range of real acceleration. It is one law now: `target_velocity` says what
  the velocity should be and the burn cancels the difference.
* **Thrust comes in six directions**, so the nearest axis to a correction is
  up to 45° off it. Burning the *whole* error along that axis overshoots and
  creates error elsewhere; a NAVIS was measured hunting between left, back,
  down, right and up at 650 m and never berthing. Only the component the axis
  can cancel is burned.

The claims:

- **More thrust is never worse.** The general one, and the one that caught
  all three faults above.
- **A hull's handling is its own**, and comes from mass and size rather than
  a stat line.
- **The main drive pushes along the nose and nowhere else**, and pointing it
  costs time and reaction mass.
- **The plan and the quote agree**, because the plan explains the quote
  rather than re-deriving it.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..data.mounts import DRIVE_THRUST, RCS_CLUSTERS
from ..sim import attitude as attitude_sim
from ..sim import autopilot as pilot_sim
from ..sim import burnplan
from ..sim import conn as conn_sim
from ..sim import thrusters
from ..sim import track as track_sim
from ..sim.ship import build_layers, make_ship
from .harness import Suite

#: Hulls spanning the range, smallest to largest.
HULLS = ("spore", "vesper", "navis", "atlas", "leviathan")

#: Drives in ascending thrust.
DRIVES = ("reaction_organ", "plasma_drive", "fusion_torch")


def _fitted(game, chassis: str, drive: str):
    """Put the captain in a named hull with a named engine."""
    game.ship = make_ship(chassis, [drive], "Trial")
    build_layers(game.ship, {})
    game.ship.cargo["volatiles"] = 60
    game.recompute()
    return game.ship


def _quay(game):
    return next(c for c in track_sim.contacts(game) if c.kind == "anchorage")


def _recovers(game, quay, drift: float) -> bool:
    """Can the computer berth from this much drift across the approach?"""
    for sign in (1.0, -1.0):
        conn = conn_sim.start(game, quay)
        conn.vel = [drift * sign, 1.0, drift * sign * 0.4]
        pilot_sim.fly(conn, "close", 6000)
        if conn.outcome != "alongside":
            return False
    return True


def _envelope(game, quay) -> float:
    """The worst drift this ship can still berth from, m/s."""
    best = 0.0
    for drift in (2, 5, 10, 20, 40, 80, 160, 320, 640, 1280):
        if _recovers(game, quay, float(drift)):
            best = float(drift)
        else:
            break
    return best


def run(suite: Suite) -> None:
    check = suite.check

    @check("more thrust is never worse")
    def _():
        # The general one. It caught the throttle fault, the branchy control
        # law and the six-axis overshoot, one after another — each time as a
        # hull that flew *worse* for having a better engine bolted to it.
        game = new_game("thrust-monotone")
        game.orbit_body = game.system.bodies[0].id
        quay = _quay(game)
        worse, table = [], []
        for chassis in HULLS:
            row = []
            for drive in DRIVES:
                _fitted(game, chassis, drive)
                row.append((drive, thrusters.main_accel(game.ship),
                            _envelope(game, quay)))
            table.append((chassis, row))
            for (before, accel_a, env_a), (after, accel_b, env_b) in zip(row, row[1:]):
                assert accel_b > accel_a, (chassis, before, after)
                if env_b < env_a:
                    worse.append(
                        f"{chassis}: {before} recovers {env_a:.0f} m/s and the "
                        f"stronger {after} only {env_b:.0f}")
        assert not worse, (
            f"{len(worse)} hull(s) fly worse for a better engine: {worse[:3]}")
        spread = [f"{c} {row[0][2]:.0f}→{row[-1][2]:.0f}" for c, row in table]
        return "worst drift berthed, weakest→strongest drive: " + " · ".join(spread)

    @check("a hull's handling is its own")
    def _():
        # Mass and size, not a stat line. A SPORE is nimble because it is
        # small; a LEVIATHAN is not, whatever is bolted to it.
        game = new_game("handling")
        seen = {}
        for chassis in HULLS:
            _fitted(game, chassis, "fusion_torch")
            seen[chassis] = {
                "mass": thrusters.mass_tonnes(game.ship),
                "accel": thrusters.main_accel(game.ship),
                "flip": thrusters.slew_seconds(game.ship, math.pi),
            }
        # Sorted by what they actually weigh, not by the order they are
        # listed in — ATLAS is a bigger ship than NAVIS in every other sense
        # and a lighter one on the scales.
        order = sorted(HULLS, key=lambda c: seen[c]["mass"])
        for lighter, heavier in zip(order, order[1:]):
            assert seen[heavier]["flip"] > seen[lighter]["flip"], (
                f"{heavier} is heavier than {lighter} and flips faster: "
                f"{seen[heavier]['flip']:.0f}s against "
                f"{seen[lighter]['flip']:.0f}s")
            assert seen[heavier]["accel"] < seen[lighter]["accel"], (
                f"{heavier} is heavier than {lighter} and out-accelerates it "
                "on the same engine")
        assert seen["spore"]["accel"] > seen["leviathan"]["accel"] * 8, (
            "the same engine barely differs between the smallest hull and "
            "the largest")
        assert seen["leviathan"]["flip"] > 120, (
            f"a LEVIATHAN swings end for end in "
            f"{seen['leviathan']['flip']:.0f} s, which is not a freighter")
        return (f"SPORE {seen['spore']['accel']:.2f} m/s² and flips in "
                f"{seen['spore']['flip']:.0f}s; LEVIATHAN "
                f"{seen['leviathan']['accel']:.3f} and "
                f"{seen['leviathan']['flip']:.0f}s")

    @check("the engines have places, and an empty station shows")
    def _():
        # The captain's question: where are they, and are they in the
        # inventory? Both, now — and a hull running one engine in a two-slot
        # transom pushes off the centreline, which the board says out loud.
        game = new_game("places")
        _fitted(game, "navis", "reaction_organ")          # 2 slots, 1 filled
        mounts = thrusters.drives(game.ship)
        assert len(mounts) == 1, mounts
        assert mounts[0].at[1] < -0.5, (
            f"the drive is not mounted aft: {mounts[0].at}")
        assert abs(mounts[0].at[0]) > 0.01, (
            "one engine in a two-slot transom is on the centreline")
        assert thrusters.offset(game.ship) > 0.01, (
            "the thrust is not off-axis with a station empty")
        rows = thrusters.board(game.ship)
        assert any("Empty station" in row[0] for row in rows), rows
        assert any("Attitude clusters" in row[0] for row in rows), rows
        assert any("centreline" in row[2] for row in rows), rows

        # Fill both and the thrust comes back onto the centreline.
        game.ship = make_ship("navis", ["reaction_organ", "plasma_drive"], "Pair")
        build_layers(game.ship, {})
        game.recompute()
        both = thrusters.drives(game.ship)
        assert len(both) == 2, both
        assert thrusters.main_thrust(game.ship) == (
            DRIVE_THRUST["reaction_organ"] + DRIVE_THRUST["plasma_drive"]), (
            "two engines do not add up")
        assert len(RCS_CLUSTERS) == 6, RCS_CLUSTERS
        return (f"one drive sits {abs(mounts[0].at[0]):.2f} off the "
                f"centreline and the board says so; two add to "
                f"{thrusters.main_thrust(game.ship):,.0f} kN")

    @check("a full hold is felt on the helm")
    def _():
        # The mutation sweep found nothing holding *mass*, only size: fixing
        # the moment of inertia to a constant, and dropping cargo from the
        # reckoning entirely, both passed every other check here. The rule
        # that bites is the one a captain feels — the same hull, loaded,
        # accelerates worse and takes longer to swing round.
        game = new_game("laden")
        _fitted(game, "atlas", "plasma_drive")
        game.ship.cargo.clear()
        game.ship.cargo["volatiles"] = 10
        game.recompute()
        light = {"mass": thrusters.mass_tonnes(game.ship),
                 "accel": thrusters.main_accel(game.ship),
                 "flip": thrusters.slew_seconds(game.ship, math.pi),
                 "rcs": thrusters.rcs_accel(game.ship)}

        game.ship.cargo["ore"] = 900
        game.ship.cargo["alloy"] = 600
        game.recompute()
        laden = {"mass": thrusters.mass_tonnes(game.ship),
                 "accel": thrusters.main_accel(game.ship),
                 "flip": thrusters.slew_seconds(game.ship, math.pi),
                 "rcs": thrusters.rcs_accel(game.ship)}

        assert laden["mass"] > light["mass"] * 1.5, (
            f"fifteen hundred tonnes in the hold moved the ship's mass from "
            f"{light['mass']:,.0f} to {laden['mass']:,.0f}")
        assert laden["accel"] < light["accel"] * 0.75, (
            f"a laden hull accelerates at {laden['accel']:.3f} against "
            f"{light['accel']:.3f} empty — the cargo is not being carried")
        assert laden["flip"] > light["flip"] * 1.15, (
            f"she swings end for end in {laden['flip']:.0f}s laden and "
            f"{light['flip']:.0f}s empty — the mass is not in the inertia")
        assert laden["rcs"] < light["rcs"] * 0.75, laden

        # And it shows in the flying, not merely in the arithmetic.
        game.orbit_body = game.system.bodies[0].id
        quay = _quay(game)
        game.ship.cargo["volatiles"] = 60
        game.recompute()
        heavy_envelope = _envelope(game, quay)
        game.ship.cargo.pop("ore", None)
        game.ship.cargo.pop("alloy", None)
        game.recompute()
        light_envelope = _envelope(game, quay)
        assert light_envelope >= heavy_envelope, (
            f"a laden hull berths from {heavy_envelope:.0f} m/s of drift and "
            f"an empty one only {light_envelope:.0f}")
        return (f"{light['mass']:,.0f} t empty → {laden['mass']:,.0f} t laden: "
                f"accel {light['accel']:.3f}→{laden['accel']:.3f}, flip "
                f"{light['flip']:.0f}s→{laden['flip']:.0f}s")

    @check("the main drive pushes along the nose and nowhere else")
    def _():
        # The whole physical content of attitude. Before this the drive
        # shoved whichever way the button said, which made the six clusters
        # decoration and `heading` a variable nothing wrote to.
        game = new_game("nose")
        game.orbit_body = game.system.bodies[0].id
        quay = _quay(game)
        conn = conn_sim.start(game, quay)
        assert attitude_sim.pointed_at(conn.nose, [-p for p in conn.pos]), (
            "an approach does not open with the nose on the target")

        for axis_id, _label, _vec in conn_sim.AXES:
            pushes = conn_sim.thrust_axis(conn, axis_id, main=True)
            assert attitude_sim.angle_between(pushes, conn.nose) < 1e-9, (
                f"the main drive pushes {pushes} on '{axis_id}' while the "
                f"nose is {conn.nose}")
        sideways = conn_sim.thrust_axis(conn, "left", main=False)
        assert abs(sideways[0] + 1.0) < 1e-9, (
            f"the thrusters cannot push to port: {sideways}")

        # And asking the drive for a new heading spends ticks turning.
        turned = burned = 0
        for _ in range(12):
            out = conn_sim.apply(conn, "left", main=True)
            if out["turning"]:
                turned += 1
            elif out["burned"]:
                burned += 1
                break
        assert turned >= 1, "the hull burned to port without turning first"
        assert burned == 1, "it never got round to burning at all"
        return (f"{turned} tick(s) swinging {90}° before the drive would fire, "
                "and the thrusters pushing sideways all along")

    @check("turning costs time and reaction mass")
    def _():
        game = new_game("turncost")
        game.orbit_body = game.system.bodies[0].id
        quay = _quay(game)
        spent, slower = [], []
        for chassis in ("spore", "navis", "leviathan"):
            ship = _fitted(game, chassis, "reaction_organ")
            plan = attitude_sim.plan_turn(ship, (0.0, 1.0, 0.0), (1.0, 0.0, 0.0))
            assert abs(plan["degrees"] - 90.0) < 1e-6, plan
            assert plan["seconds"] > 0 and plan["fuel"] > 0, plan
            spent.append((chassis, plan["seconds"], plan["fuel"]))
            slower.append(plan["seconds"])
        assert slower == sorted(slower), (
            f"a bigger hull does not take longer to turn: {spent}")

        # And the mass really leaves the tank.
        _fitted(game, "navis", "reaction_organ")
        conn = conn_sim.start(game, quay)
        before = conn.rcs
        attitude_sim.slew(conn, [1.0, 0.0, 0.0], conn_sim.TICK * 6)
        assert conn.rcs < before, "swinging the hull round was free"
        assert attitude_sim.angle_between(conn.nose, [1.0, 0.0, 0.0]) < 0.2, (
            "six minutes and the hull is still not round")
        return " · ".join(f"{c} {s:.0f}s {f:.3f}t" for c, s, f in spent)

    @check("the plan and the quote agree")
    def _():
        # The plan explains the quote rather than re-deriving it, so the two
        # screens cannot come apart. The first draft *did* re-derive, decided
        # every hull in the game was too feeble to fly, and was right about
        # the arithmetic and wrong about the game.
        game = new_game("planagree")
        checked = 0
        for chassis in ("spore", "navis", "leviathan"):
            _fitted(game, chassis, "reaction_organ")
            game.ship.cargo["volatiles"] = 400
            game.recompute()
            for index, body in enumerate(game.system.bodies[:3]):
                for burn in ("coast", "standard", "hard"):
                    out = burnplan.plan(game, body, burn)
                    quote = out["quote"]
                    fuel = sum(f for _n, _s, f, _d in out["phases"])
                    assert abs(fuel - quote["fuel"]) < 1e-6, (
                        f"the plan spends {fuel} against a quote of "
                        f"{quote['fuel']}")
                    assert abs(out["braking_fuel"] - quote["fuel"] / 2) < 1e-6
                    span = sum(s for _n, s, _f, _d in out["phases"])
                    assert span <= quote["days"] * burnplan.DAY_S + 1e-6, (
                        f"the phases take {span / burnplan.DAY_S:.2f} days "
                        f"against a quote of {quote['days']}")
                    assert out["ok"], out["why"]
                    checked += 1
        assert checked >= 20, checked
        return (f"{checked} plans, every one spending exactly its quote and "
                "fitting inside its days")

    @check("a hull with no drive fitted says so instead of flying")
    def _():
        game = new_game("nodrive")
        game.ship = make_ship("navis", [], "Adrift")
        build_layers(game.ship, {})
        game.recompute()
        assert thrusters.main_thrust(game.ship) == 0
        assert thrusters.main_accel(game.ship) == 0
        out = burnplan.plan(game, game.system.bodies[0])
        assert not out["ok"] and "No drive" in out["why"], out
        rows = thrusters.board(game.ship)
        assert any("Empty station" in row[0] for row in rows), rows
        # The attitude clusters are built in, so it can still turn.
        assert thrusters.slew_rate(game.ship) > 0, (
            "a hull with no drive cannot even rotate, so it could never be "
            "pointed at a rescue")
        return "no drive: no thrust, no plan, and the clusters still answer"
