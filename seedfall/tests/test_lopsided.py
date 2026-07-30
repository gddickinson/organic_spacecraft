"""A hull flying lopsided: what one missing engine of a pair actually costs.

Three things in the tables had said this for a long time and none of them was
true.

`data/mounts.py`, on why drive stations are spread across the transom: "so
losing one leaves the thrust off-axis". `thrusters.offset`, computing exactly
how far off: "which the flight computer has to trim against". And
`Mount.axis`, the direction each engine pushes — declared, and read by nobody,
because `drives()` set every one of them to the same constant and nothing ever
looked.

So a hull on one of two engines flew exactly as straight as one on two, only
slower. The consequence the prose promised did not exist.

`thrusters.yaw_torque` is `r × F` summed over the engines fitted, which is the
one place `Mount.axis` is read for what it is: a cross product needs to know
which way the force points. On a balanced hull the pair cancel. On a NAVIS
running one engine the torque is real — 0.0012 rad/s² against 0.0008 of
attitude authority.

**A first draft let the hull tumble, and that was wrong about the tick.** An
unopposed 0.0012 rad/s² across a sixty-second conn tick is 126 degrees: not a
ship that needs trimming, a ship spinning like a top. It also made the
measurements nonsense, because the nose wrapped past 360° and read as 0.
No flight computer would permit it — it holds attitude and limits the throttle
to what it can hold. So the consequence is `holdable_throttle`: **a lopsided
hull has less usable engine**, and pays extra reaction mass for the clusters
firing throughout to answer the torque.

The claims:

- **An unbalanced drive costs usable throttle**, and a balanced one costs
  nothing.
- **The cap is derived**, not invented: authority over torque.
- **`Mount.axis` is genuinely read** — change it and the torque changes.
- **The two doors agree**: an offset off the centreline and a yaw torque are
  the same fact, and neither is ever true without the other.
- **It costs more mass for the same speed**, measured by differencing.
- **And it is still flyable**, because a penalty that ends the game is a bug.
- **What decides the cap is off-axis thrust against attitude authority.** A
  first draft of that claim said a *heavy hull* shrugs a missing engine off,
  measured on one engine, and generalised too far: the same LEVIATHAN holds 1.00
  under a Reaction-Mass Organ and 0.20 under a Fusion Torch. Mass helps at equal
  thrust; thrust is the term that varies most.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..data.mounts import DRIVE_STATIONS, MAIN_AXIS, Mount
from ..sim import autopilot, conn as conn_sim, instruments, orbits
from ..sim import thrusters as thrust_sim
from ..sim import track as track_sim
from ..sim.ship import build_layers, make_ship
from .harness import Suite

#: A hull with two drive stations, so one engine is a real state.
PAIRED = "navis"


def _ship(game, drives: int, chassis: str = PAIRED):
    ship = make_ship(chassis, ["reaction_organ"] * drives + ["opsin_eyes"])
    build_layers(ship, game.bonuses)
    ship.cargo["volatiles"] = 900
    return ship


def _one_burn(game, drives: int, throttle: float = 1.0):
    """One full-throttle tick. Returns (delta-v, reaction mass spent)."""
    game.ship = _ship(game, drives)
    contact = next(c for c in track_sim.contacts(game, game.system)
                   if c.body_index == 0)
    conn = conn_sim.start(game, contact)
    conn.rcs = 99999.0
    before, held = list(conn.vel), conn.rcs
    conn_sim.apply(conn, "forward", main=True, throttle=throttle)
    moved = math.dist(conn.vel, before)
    return moved, held - conn.rcs, conn.hold


def run(suite: Suite) -> None:
    check = suite.check

    @check("an unbalanced drive costs usable throttle, a balanced one nothing")
    def _():
        game = new_game("lopsided")
        _dv_both, _m_both, hold_both = _one_burn(game, 2)
        _dv_one, _m_one, hold_one = _one_burn(game, 1)
        assert hold_both == 1.0, (
            f"a hull with both engines lit can only open to {hold_both:.2f} — "
            "a balanced drive should cost nothing")
        assert 0.2 < hold_one < 0.9, (
            f"a hull on one of two engines holds {hold_one:.2f}; the thrust is "
            "off the centreline and either nothing is limiting it or it has "
            "been limited into uselessness")

        # A single-station hull has nothing to be unbalanced about.
        game.ship = _ship(game, 1, "spore")
        assert thrust_sim.yaw_torque(game.ship) == 0.0, (
            "a hull with one drive station puts its engine on the centreline, "
            "so there is nothing for it to yaw about")
        assert thrust_sim.holdable_throttle(game.ship) == 1.0
        return (f"both engines hold {hold_both:.2f}, one engine "
                f"{hold_one:.2f}; a single-station hull, nothing to hold")

    @check("the throttle a hull can hold is authority over torque")
    def _():
        # Derived rather than picked, and worth asserting as arithmetic: the
        # torque scales with the throttle and the clusters do not, so the
        # answer is simply the ratio at which the two meet.
        game = new_game("ratio")
        ship = _ship(game, 1)
        yaw = abs(thrust_sim.yaw_rate(ship))
        authority = thrust_sim.slew_rate(ship)
        assert yaw > authority, (
            f"a NAVIS on one engine yaws at {yaw:.6f} against {authority:.6f} "
            "of authority — this case is supposed to be the hard one")
        want = authority / yaw
        got = thrust_sim.holdable_throttle(ship)
        assert abs(got - want) < 1e-9, (got, want)
        assert got >= thrust_sim.HOLD_FLOOR

        # And the floor is a floor: a drive that cannot be opened at all is a
        # stranding, and a stranding that follows silently from a refit is a
        # worse fault than a sluggish ship.
        assert 0 < thrust_sim.HOLD_FLOOR < 0.5, thrust_sim.HOLD_FLOOR
        return (f"{authority:.6f} of authority against {yaw:.6f} of yaw makes "
                f"{got:.2f} usable, floored at {thrust_sim.HOLD_FLOOR}")

    @check("the axis a mount pushes along is genuinely read")
    def _():
        # `Mount.axis` was declared when the mounts were written and read by
        # nobody: every drive was given the same constant, so the field was
        # decoration. The torque needs it, because `r × F` cannot be computed
        # without knowing which way F points.
        game = new_game("axis")
        ship = _ship(game, 1)
        real = thrust_sim.yaw_torque(ship)
        assert real != 0.0, real

        # Substitute a mount pushing sideways and the torque must change: an
        # engine at the same place shoving athwartships turns the hull the
        # other way about.
        fitted = thrust_sim.drives(ship)
        assert fitted and fitted[0].axis == MAIN_AXIS, fitted
        station = DRIVE_STATIONS[2][0]
        sideways = Mount(at=station, axis=(1.0, 0.0, 0.0),
                         thrust=fitted[0].thrust, label="probe")
        arm = thrust_sim.half_length_m(ship)
        force = sideways.thrust * 1000.0
        want = ((station[0] * arm) * (force * sideways.axis[1])
                - (station[1] * arm) * (force * sideways.axis[0]))
        assert abs(want) > 1.0 and (want > 0) != (real > 0), (
            f"an engine pushing athwartships from the same station gives "
            f"{want:,.0f} N·m against {real:,.0f} for one pushing forward — "
            "the axis is not deciding anything")
        return (f"forward from port: {real:,.0f} N·m; athwartships from the "
                f"same station: {want:,.0f} N·m")

    @check("an offset and a yaw torque are the same fact")
    def _():
        # Two doors into one question, which this project has watched disagree
        # more than once. `offset` is how far off the centreline the thrust
        # acts and `yaw_torque` is what that does; neither may be true alone.
        game = new_game("agree")
        looked = 0
        for chassis in ("spore", "navis", "leviathan"):
            for drives in (1, 2, 3, 4):
                try:
                    ship = _ship(game, drives, chassis)
                except Exception:
                    continue
                off = thrust_sim.offset(ship)
                yaw = thrust_sim.yaw_torque(ship)
                fitted = thrust_sim.drives(ship)
                if not fitted:
                    continue
                looked += 1
                assert (off > 1e-9) == (abs(yaw) > 1e-6), (
                    f"{chassis} with {len(fitted)} engine(s): offset "
                    f"{off:.3f} and torque {yaw:,.1f} disagree about whether "
                    "the thrust is off the centreline")
                # And the conn is told the same thing the board is.
                kit = thrust_sim.summary(ship)
                assert kit["offset"] == off and abs(
                    kit["yaw_rate"] - thrust_sim.yaw_rate(ship)) < 1e-12, kit
        assert looked >= 6, looked
        return f"{looked} hull-and-loadout pairs, the two readings agreeing"

    @check("a lopsided hull spends more mass for the same speed")
    def _():
        # The cost, differenced on one identical tick so nothing else can be
        # responsible: the cap takes the thrust down and the trim surcharge
        # puts the mass up, and both land on the same ratio.
        game = new_game("dear")
        dv_both, mass_both, _h = _one_burn(game, 2)
        dv_one, mass_one, _h = _one_burn(game, 1)
        assert dv_both > 0 and dv_one > 0, (dv_both, dv_one)

        per_both = mass_both / dv_both
        per_one = mass_one / dv_one
        assert per_one > per_both * 1.4, (
            f"a lopsided hull spends {per_one:.4f} t per m/s against "
            f"{per_both:.4f} balanced — holding the burn straight is free")
        # And the surcharge is on the mass, not only on the thrust — asserted
        # as arithmetic, because a cap that quietly saved mass by throttling
        # back would read as a *reward* for losing an engine.
        hold = _one_burn(game, 1)[2]
        bare = conn_sim.MAIN_COST * hold
        want = bare * (1.0 + thrust_sim.TRIM_COST_SHARE * (1.0 - hold))
        # Tolerance is the tank's own quantisation: `apply` rounds the
        # remaining mass to four places, so a single pulse can land 5e-5 out.
        # (Harmless here — the smallest spend the game can make is 0.018 t at
        # the throttle floor, 360 granules, so no pulse is ever free.)
        assert abs(mass_one - want) < 1e-4, (
            f"one engine spent {mass_one:.4f} t where the trim surcharge "
            f"predicts {want:.4f} (throttle alone would be {bare:.4f})")
        assert mass_one > bare * 1.05, (
            f"{mass_one:.4f} t against {bare:.4f} — the clusters are holding "
            "the nose for nothing")
        return (f"{per_both:.4f} t per m/s balanced against {per_one:.4f} "
                f"lopsided — {per_one / per_both:.1f} times the mass")

    @check("what decides the cap is off-axis thrust, not the hull's mass")
    def _():
        # **I wrote this check the other way round and it was too narrow.** It
        # compared a NAVIS with a LEVIATHAN, both under Reaction-Mass Organs,
        # found the LEVIATHAN held 1.00, and concluded that a heavy hull shrugs
        # a missing engine off because its inertia beats the torque. True of
        # that engine. Fit the same LEVIATHAN with a Fusion Torch — seven and a
        # half times the thrust — and it holds **0.20**. Mass is not what
        # decides it; off-axis thrust against attitude authority is, and thrust
        # is the term that varies most.
        #
        # So the claim is now the ratio itself, checked across both engines,
        # which is the thing that is actually true.
        game = new_game("cap-rule")
        seen = []
        for chassis in ("navis", "leviathan"):
            for part in ("reaction_organ", "fusion_torch"):
                ship = make_ship(chassis, [part, "opsin_eyes"])
                build_layers(ship, game.bonuses)
                ship.cargo["volatiles"] = 900
                kit = thrust_sim.summary(ship)
                if kit["offset"] <= 1e-9:
                    continue
                seen.append((chassis, part, kit["hold"], kit["yaw_rate"]))
        assert len(seen) == 4, seen

        # A bigger engine on the same hull is always harder to hold, never
        # easier — the property the mass story got backwards.
        for chassis in ("navis", "leviathan"):
            small = next(h for c, p, h, _y in seen
                         if c == chassis and p == "reaction_organ"
                         for h in [h])
            big = next(h for c, p, h, _y in seen
                       if c == chassis and p == "fusion_torch" for h in [h])
            assert big < small, (
                f"a {chassis} holds {big:.2f} on a Fusion Torch against "
                f"{small:.2f} on a Reaction-Mass Organ — more off-axis thrust "
                "has to be harder to hold, not easier")

        # And the heavier hull still helps, at equal thrust: same engine, more
        # inertia, more of the drive usable. Both halves are true; only the
        # first was, on its own, the whole story.
        light = next(h for c, p, h, _y in seen
                     if c == "navis" and p == "fusion_torch" for h in [h])
        heavy = next(h for c, p, h, _y in seen
                     if c == "leviathan" and p == "fusion_torch" for h in [h])
        assert heavy > light, (heavy, light)
        return " · ".join(f"{c[:4]}/{p.split('_')[0]} {h:.2f}"
                          for c, p, h, _y in seen)

    @check("the panel says why the throttle will not open")
    def _():
        # A penalty the pilot cannot see is a bug report. The cap is silent by
        # construction — the drive simply stops responding past six tenths —
        # so the panel has to name it, and name it only when there is
        # something to name: a row reading "100% usable" forever is a row the
        # pilot learns to skip past, which is how the first draft of this
        # panel came to mark a good orbit in red.
        game = new_game("panel")
        rows = {}
        for drives in (2, 1):
            game.ship = _ship(game, drives)
            contact = next(c for c in track_sim.contacts(game, game.system)
                           if c.body_index == 0)
            conn = conn_sim.start(game, contact)
            rows[drives] = {label: (value, how)
                            for label, value, how in instruments.readout(conn)}
        assert "Drive trim" not in rows[2], (
            "a hull with a balanced drive is being told about its trim, which "
            "is a row that is always fine")
        assert "Drive trim" in rows[1], (
            f"a hull holding 0.62 of its throttle says nothing about it: "
            f"{sorted(rows[1])}")
        value, how = rows[1]["Drive trim"]
        assert "62" in value, value
        # And it must not cry wolf. My first draft marked it amber, and
        # `test_conn.py`'s "the panel does not cry wolf at a good approach"
        # caught it warning on fourteen approaches that *succeeded* — the very
        # fault this panel was rebuilt to stop. A 62% drive is a fact about the
        # hull, not a fault in the flying.
        assert how == "ok", (
            f"the trim row reads {how!r}: a hull that flew a good orbit on one "
            "engine is being told something went wrong")
        return f"balanced: no row · lopsided: Drive trim {value} ({how})"

    @check("a lopsided hull still makes orbit, slower and dearer")
    def _():
        # The proportionality claim, and the one that matters most: a penalty
        # that turns a manoeuvre from possible into impossible is a stranding
        # wearing a handicap's clothes. Paired per seed, because comparing
        # counts across two runs would let one lucky seed stand in for the
        # property.
        reached = {1: set(), 2: set()}
        cost = {1: {}, 2: {}}
        for drives in (2, 1):
            for seed in range(4):
                game = new_game(f"climb-{seed}")
                game.ship = _ship(game, drives)
                contact = next(c for c in track_sim.contacts(game, game.system)
                               if c.body_index == 0)
                conn = conn_sim.start(game, contact)
                conn.rcs = 99999.0
                held = conn.rcs
                conn.orbit_want_km = orbits.height_km(conn.target.radius_km,
                                                      "high")
                ticks = 0
                for ticks in range(1, 6001):
                    axis, main, throttle = autopilot.autopilot(conn, "orbit")
                    conn_sim.apply(conn, axis, main, throttle)
                    if conn.over:
                        break
                if conn.outcome == "orbit":
                    reached[drives].add(seed)
                    cost[drives][seed] = (ticks, held - conn.rcs)
        lost = reached[2] - reached[1]
        assert not lost, (
            f"seeds {sorted(lost)} climbed to a high orbit on two engines and "
            "could not on one — the throttle cap has stranded them, which is "
            "not a handicap")
        assert len(reached[2]) >= 3, sorted(reached[2])

        # Priced only on the climbs *both* hulls made. A first draft summed
        # across each hull's own successes and read "4/3" — the lopsided hull
        # reached a high orbit on a seed the balanced one missed, because too
        # much thrust overshoots at a small body (task #83), so the cap gentles
        # the approach. A real finding, and a ratio over two different
        # populations either way.
        both = sorted(reached[1] & reached[2])
        assert len(both) >= 3, both
        slow = sum(cost[1][s][0] for s in both) / sum(cost[2][s][0] for s in both)
        dear = sum(cost[1][s][1] for s in both) / sum(cost[2][s][1] for s in both)
        assert slow > 1.05 and dear > 1.05, (
            f"one engine took {slow:.2f}x the time and {dear:.2f}x the mass "
            f"over the {len(both)} climbs both hulls made — losing half the "
            "drive should be felt")
        return (f"{len(both)} climbs made on either drive, one engine taking "
                f"{slow:.2f}x the time and {dear:.2f}x the mass")

    @check("a damaged hull can still be brought alongside")
    def _():
        # Berthing is thruster work, so the yaw should barely show — and it
        # must not stop a crippled ship reaching a quay, which is the one
        # manoeuvre a captain in trouble actually needs.
        outcomes = {}
        for drives in (1, 2):
            got = {}
            for seed in range(6):
                game = new_game(f"limp-{seed}")
                game.ship = _ship(game, drives)
                quays = [c for c in track_sim.contacts(game, game.system)
                         if c.kind == "anchorage"]
                if not quays:
                    continue
                conn = conn_sim.start(game, quays[0])
                conn.rcs = 99999.0
                for _ in range(6000):
                    axis, main, throttle = autopilot.autopilot(conn, "close")
                    conn_sim.apply(conn, axis, main, throttle)
                    if conn.over:
                        break
                got[conn.outcome or "never"] = got.get(conn.outcome or "never",
                                                       0) + 1
            outcomes[drives] = got
        for drives, got in outcomes.items():
            assert got.get("alongside", 0) >= sum(got.values()) - 1, (
                f"with {drives} engine(s) the approaches ended {got} — a hull "
                "that cannot reach a quay is stranded, not handicapped")
        return " · ".join(f"{d} engine(s): {g}" for d, g in outcomes.items())
