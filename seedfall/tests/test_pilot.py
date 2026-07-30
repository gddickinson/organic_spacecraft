"""The console: a throttle and a coast the pilot can actually reach.

`sim/conn.apply` has taken a `throttle` since the drive learned to throttle, and
`ticks` since it was written. **The conn could reach neither.** The window fired
`apply(conn, axis, main=self.use_main)` and nothing else, so the pilot's main
drive was a switch — full power, one minute — while the flight computer beside
it throttled freely.

`conn.apply` still carries the note about why the computer needed it: "one tick
of a fusion torch on a SPORE is 124 m/s, so the computer lit it to trim ten,
overshot, corrected the overshoot, and never converged". The human was left with
the firework. Flown by hand: **a SPORE under a Fusion Torch cannot kill ten
metres a second of way on at all**, because its one press is 41.9 and every
press makes things worse. With the ladder it berths.

The claims:

- **The gate matches the act.** `can_burn` asked for a whole `MAIN_COST`
  whatever the throttle, so a hull holding 0.119 t was refused a burn costing
  0.012. One door now, and `apply` spends through it.
- **A press is worth what the console says**, at every rung.
- **A gentle press is genuinely gentler**, and cheaper in proportion.
- **The promise is the act**: `quote` and `apply` agree across the whole ladder
  and every coast, not merely at full power for one minute.
- **The coast is a coast, not a longer burn** — `apply` fires once and then
  steps time, and calling it a burn length would be a lie about the button.
- **It makes a hull flyable that was not**, measured by hand.
- **And the console says what is set**, in m/s rather than a bare percentage.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import conn as conn_sim
from ..sim import instruments
from ..sim import pilot
from ..sim import preview
from ..sim import track as track_sim
from ..sim.ship import build_layers, make_ship
from .harness import Suite


def _conn(game, chassis="navis", part="reaction_organ", drives=2, quay=False):
    game.ship = make_ship(chassis, [part] * drives + ["opsin_eyes"])
    build_layers(game.ship, game.bonuses)
    game.ship.cargo["volatiles"] = 900
    if quay:
        places = [c for c in track_sim.contacts(game, game.system)
                  if c.kind == "anchorage"]
        target = places[0]
    else:
        target = next(c for c in track_sim.contacts(game, game.system)
                      if c.body_index == 0)
    conn = conn_sim.start(game, target)
    conn.rcs = 9999.0
    return conn


def run(suite: Suite) -> None:
    check = suite.check

    @check("the gate asks at the throttle the burn will actually use")
    def _():
        # The fault: a whole `MAIN_COST` demanded whatever was set, so a hull
        # with mass enough for a gentle nudge was told the drive was dry. This
        # project has swept every other gate against the act it guards; this one
        # was created by the throttle being unreachable, so nobody had asked.
        game = new_game("gate")
        conn = _conn(game)
        refused = []
        for step in pilot.THROTTLE_STEPS:
            cost = pilot.burn_cost(conn, True, step)
            # Just enough, and just not enough, either side of the real cost.
            conn.rcs = cost * 1.01
            ok, _why = conn_sim.can_burn(conn, True, step)
            conn.rcs = cost * 0.99
            tight, why = conn_sim.can_burn(conn, True, step)
            assert ok, (
                f"at {step:.0%} the burn costs {cost:.4f} t and the gate "
                f"refused with {cost * 1.01:.4f} t aboard")
            assert not tight, (
                f"at {step:.0%} the gate allowed a burn costing {cost:.4f} t "
                f"with only {cost * 0.99:.4f} t aboard")
            refused.append((step, cost, why))
        # The old fault, stated as the number that showed it.
        conn.rcs = 0.119
        ok, _why = conn_sim.can_burn(conn, True, min(pilot.THROTTLE_STEPS))
        assert ok, (
            "0.119 t aboard and a tenth-throttle burn is still refused; that "
            "is the whole bug")

        # And **`apply` has its own gate call**, which is the one that decides
        # whether the ship moves. A sweep found this: asking it at full power
        # instead of at what was set left `can_burn` correct and the burn still
        # refused, with nothing to show it. So press it, with a tank that can
        # afford a tenth and could not afford everything.
        gentle = min(pilot.THROTTLE_STEPS)
        conn = _conn(game, quay=True)
        conn.rcs = pilot.burn_cost(conn, True, gentle) * 1.5
        assert conn.rcs < pilot.burn_cost(conn, True, 1.0), (
            "this tank is supposed to be too small for a full burn")
        conn.nose = list(conn_sim.thrust_axis(conn, "forward", main=False))
        out = conn_sim.apply(conn, "forward", main=True, throttle=gentle)
        assert out.get("burned"), (
            f"{conn.rcs:.4f} t aboard would pay for a {gentle:.0%} burn and "
            "`apply` refused it anyway — the gate inside the act is being "
            "asked the wrong question")
        return " · ".join(f"{s:.0%} costs {c:.4f} t"
                          for s, c, _w in refused)

    @check("a press is worth what the console says it is")
    def _():
        # Measured against the act, not against the formula: fire it and see.
        game = new_game("worth")
        looked = 0
        for chassis, part, drives in (("spore", "fusion_torch", 1),
                                      ("navis", "reaction_organ", 2),
                                      ("leviathan", "fusion_torch", 4)):
            for step in pilot.THROTTLE_STEPS:
                conn = _conn(game, chassis, part, drives, quay=True)
                pilot.set_throttle(conn, step)
                # Through `quote`, which is what the console actually reads: a
                # sweep found `quote["dv"]` could be computed at full power with
                # nothing to notice, because every other check either called
                # `dv_of` directly or compared range and closing instead.
                axis = "forward"
                conn.nose = list(conn_sim.thrust_axis(conn, axis, main=False))
                said = pilot.quote(conn, axis, main=True)["dv"]
                assert said == pilot.dv_of(conn, True), (said, step)
                before = list(conn.vel)
                out = conn_sim.apply(conn, axis, main=True, throttle=step)
                assert out.get("burned"), (chassis, step, out)
                got = sum((a - b) ** 2
                          for a, b in zip(conn.vel, before)) ** 0.5
                # Gravity is in there too at a quay, but it is tiny; the claim
                # is the thrust, so allow the coast its share and no more.
                assert abs(got - said) < max(0.05, said * 0.02), (
                    f"{chassis} at {step:.0%}: the console promised "
                    f"{said:.3f} m/s and the burn gave {got:.3f}")
                looked += 1
        assert looked == 3 * len(pilot.THROTTLE_STEPS), looked
        return f"{looked} presses, each within 2% of what was quoted"

    @check("a gentler press is gentler, and cheaper in proportion")
    def _():
        # Monotone in both, which is the property that makes the ladder a
        # decision rather than four buttons that do the same thing.
        game = new_game("ladder")
        conn = _conn(game, "spore", "fusion_torch", 1, quay=True)
        rungs = [(s, pilot.dv_of(conn, True, s), pilot.burn_cost(conn, True, s))
                 for s in pilot.THROTTLE_STEPS]
        for (s1, dv1, c1), (s2, dv2, c2) in zip(rungs, rungs[1:]):
            assert s2 > s1 and dv2 > dv1 and c2 > c1, (
                f"{s1:.0%} gives {dv1:.2f} m/s for {c1:.4f} t and {s2:.0%} "
                f"gives {dv2:.2f} for {c2:.4f} — the ladder is not monotone")
        # And the cheapest rung is a real fraction of the dearest, not a token.
        finest, fullest = rungs[0][1], rungs[-1][1]
        assert finest < fullest * 0.2, (finest, fullest)
        assert pilot.finest(conn) == finest
        return " · ".join(f"{s:.0%} {dv:.2f} m/s at {c:.4f} t"
                          for s, dv, c in rungs)

    @check("the promise is the act, across every rung and every coast")
    def _():
        # `quote` is the only door the console speaks through, so it has to
        # agree with `apply` at whatever is set — not merely at full power for
        # one minute, which is all the old tooltip ever tested.
        game = new_game("promise")
        worst: dict = {}
        counted = 0
        for step in pilot.THROTTLE_STEPS:
            for minutes in pilot.COAST_MINUTES:
                for main in (False, True):
                    for axis_id, _label, _vec in conn_sim.AXES:
                        conn = _conn(game)
                        pilot.set_throttle(conn, step)
                        pilot.set_coast(conn, minutes)
                        said = pilot.quote(conn, axis_id, main=main)
                        conn_sim.apply(conn, axis_id, main=main,
                                       ticks=conn.coast_min,
                                       throttle=conn.throttle)
                        for field, got in (("range_km", conn.range_km),
                                           ("closing", conn.closing),
                                           ("speed", conn.speed),
                                           ("rcs", conn.rcs)):
                            gap = abs(said[field] - got)
                            worst[field] = max(worst.get(field, 0.0), gap)
                            counted += 1
        assert counted > 500, counted
        for field, gap in worst.items():
            assert gap < 1e-6, (
                f"the quote's {field} is {gap:g} away from what the press "
                f"actually left, over {counted} comparisons")
        return (f"{counted} comparisons across {len(pilot.THROTTLE_STEPS)} "
                f"rungs and {len(pilot.COAST_MINUTES)} coasts, every field "
                "exact")

    @check("the coast lets time run; it is not a longer burn")
    def _():
        # Worth pinning, because naming it a burn length would be a lie about
        # what the button does and the name is the only thing a pilot has to go
        # on. `apply` fires once and *then* steps time, so a fifteen-minute
        # press spends one burn's mass and fifteen minutes of clock.
        game = new_game("coast")
        spent, elapsed = {}, {}
        for minutes in pilot.COAST_MINUTES:
            conn = _conn(game)
            pilot.set_coast(conn, minutes)
            held = conn.rcs
            conn_sim.apply(conn, "forward", main=True, ticks=conn.coast_min,
                           throttle=1.0)
            spent[minutes] = round(held - conn.rcs, 6)
            elapsed[minutes] = conn.elapsed
        one = spent[pilot.COAST_MINUTES[0]]
        for minutes, cost in spent.items():
            assert abs(cost - one) < 1e-9, (
                f"a {minutes}-minute press spent {cost:.4f} t against "
                f"{one:.4f} for one minute — the coast is charging like a burn")
        for minutes, secs in elapsed.items():
            assert abs(secs - minutes * conn_sim.TICK) < 1e-6, (
                f"a {minutes}-minute press let {secs / 60:.1f} minutes run")
        return (f"one burn's mass ({one:.4f} t) whatever the coast; "
                + ", ".join(f"{m} min → {e / 60:.0f} min"
                            for m, e in elapsed.items()))

    @check("the throttle makes a hull flyable that was not")
    def _():
        # The point of the whole thing, flown by hand rather than argued. A
        # SPORE under a Fusion Torch moves 41.9 m/s a press: a pilot with ten
        # metres a second of way on cannot improve it, because every press
        # overshoots further than the error. The ladder is what makes the hull
        # berthable at all.
        def fly(steps):
            game = new_game("hand")
            conn = _conn(game, "spore", "fusion_torch", 1, quay=True)
            conn.vel = [10.0, 0.0, 0.0]
            best = conn.speed
            for _ in range(60):
                if conn.over:
                    break
                index = max(range(3), key=lambda k: abs(conn.vel[k]))
                here = conn.vel[index]
                axis = ({0: "left", 1: "back", 2: "down"} if here > 0
                        else {0: "right", 1: "forward", 2: "up"})[index]
                pick, gain = None, None
                for step in steps:
                    after = abs(abs(here) - pilot.dv_of(conn, True, step))
                    if gain is None or after < gain:
                        pick, gain = step, after
                if gain >= abs(here) - 1e-9:
                    break                      # no rung improves matters
                conn_sim.apply(conn, axis, main=True, throttle=pick)
                best = min(best, conn.speed)
            return best

        switch = fly((1.00,))
        ladder = fly(pilot.THROTTLE_STEPS)
        limit = conn_sim.ALONGSIDE_RATE
        assert switch > limit, (
            f"a full-power-only pilot got to {switch:.2f} m/s, inside the "
            f"{limit} m/s berthing limit — this hull is supposed to be the "
            "one that cannot be flown by switch")
        assert ladder <= limit, (
            f"with the ladder the best was {ladder:.2f} m/s, still outside "
            f"the {limit} m/s limit")
        return (f"full power only: stuck at {switch:.2f} m/s · with the "
                f"ladder: {ladder:.2f} m/s, inside the {limit} limit")

    @check("the panel says what is set, in m/s")
    def _():
        # A bare percentage is not information: the pilot needs the number in
        # the unit every other row is judged in.
        game = new_game("says")
        conn = _conn(game, "spore", "fusion_torch", 1, quay=True)
        pilot.set_throttle(conn, 0.10)
        pilot.set_coast(conn, 5)
        rows = {label: (value, how)
                for label, value, how in instruments.readout(conn)}
        assert "Throttle" in rows and "Coast" in rows, sorted(rows)
        value, how = rows["Throttle"]
        assert "10%" in value and how == "ok", (value, how)
        worth = pilot.dv_of(conn, True)
        assert f"{worth:,.2f}" in value, (
            f"the panel says {value!r} but a press is worth {worth:.2f} m/s")
        assert rows["Coast"][0] == "5 min", rows["Coast"]
        return f"Throttle {value} · Coast {rows['Coast'][0]}"

    @check("a rung off the ladder snaps to one that exists")
    def _():
        # The console only offers the rungs, but `set_throttle` is a sim door
        # and a save, a script or the remote bridge could hand it anything.
        game = new_game("snap")
        conn = _conn(game)
        for asked, want in ((0.0, 0.10), (0.11, 0.10), (0.4, 0.50),
                            (0.9, 1.00), (7.0, 1.00), (-3.0, 0.10)):
            got = pilot.set_throttle(conn, asked)
            assert got == want and conn.throttle == want, (asked, got, want)
        for asked, want in ((0, 1), (2, 1), (4, 5), (99, 15)):
            got = pilot.set_coast(conn, asked)
            assert got == want and conn.coast_min == want, (asked, got, want)
        # And a throttle that came from nowhere still cannot spend more than the
        # drive would: `usable_throttle` clamps before anything is charged.
        assert pilot.usable_throttle(conn, True, 9.0) <= 1.0
        assert pilot.usable_throttle(conn, True, -9.0) == 0.0
        assert pilot.burn_cost(conn, True, -9.0) == 0.0
        ok, why = conn_sim.can_burn(conn, True, -9.0)
        assert not ok and "throttle" in why.lower(), why
        return "every rung snaps; a closed throttle is refused, not charged"

    @check("a forecast's twin carries the console settings")
    def _():
        # `preview._copy` is a hand-written field list that has been caught
        # short four times. The guard in `test_conn.py` covers the list; this
        # covers the consequence, which is the thing a player would see.
        game = new_game("twin")
        conn = _conn(game)
        pilot.set_throttle(conn, 0.25)
        pilot.set_coast(conn, 15)
        twin = preview._copy(conn)
        assert twin.throttle == 0.25 and twin.coast_min == 15, (
            f"the twin flies at {twin.throttle} for {twin.coast_min} min "
            "while the ship is set to 0.25 for 15")
        assert twin.hold == conn.hold and twin.orbit_want_km == conn.orbit_want_km
        return f"twin holds {twin.throttle:.0%} and {twin.coast_min} min"
