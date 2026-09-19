"""What a structure does for a hull it *has* cleared, and the one that clears
nobody.

Split out of `tests/test_control.py` when it reached 560 lines. That file is
the ledger's refusing side — who holds a berth, what a dock will not open
for, how patience runs out. This is the other side: being cleared buys
something (the boats take you in for nothing), a wayside quay keeps no boats
to buy, and a Weave anchor has nobody in it to grant or withhold anything.
"""

from __future__ import annotations

from ..sim import clearance as clearance_sim
from ..sim import conn as conn_sim
from ..sim import control, tug
from ..sim import moorings
from ..sim import targets as targets_sim
from .harness import Suite
from .test_control import _hub, _park


def run(suite: Suite) -> None:
    check = suite.check

    @check("being cleared buys something: the boats take you in for nothing")
    def _():
        # The other side of the ledger. Everything else here is what a
        # structure does about a hull it does not want; this is what it does
        # for one it does, and without it clearance is a gate rather than a
        # service.
        from ..sim import autopilot as pilot

        game, hub = _hub("tug")
        target = targets_sim.target_from_contact(game, hub)

        def fly(wait):
            conn = conn_sim.start(game, target)
            said = clearance_sim.request(game, hub, conn)
            assert said.granted, said.why
            conn.cleared = said
            conn.watch = control.post(game, hub)
            opening = conn.rcs
            ticks = 0
            for ticks in range(20_000):
                if wait:
                    conn_sim.apply(conn, None, main=False, ticks=1)
                else:
                    axis, main, throttle = pilot.autopilot(conn, "close")
                    conn_sim.apply(conn, axis, main=main, throttle=throttle,
                                   ticks=1)
                if conn.over:
                    break
            return conn, opening - conn.rcs, ticks

        towed, tow_cost, tow_ticks = fly(True)
        flown, fly_cost, fly_ticks = fly(False)
        assert towed.outcome == "alongside", towed.outcome
        assert flown.outcome == "alongside", flown.outcome
        assert tug.under_tow(towed), "the boats never got a line on"
        assert towed.towed > 1.0, f"towed only {towed.towed:.3f} km"

        # Free, and slow. Both halves matter: a tug that saved nothing would
        # be a service nobody waits for, and one that cost no time would make
        # flying it yourself pointless.
        assert tow_cost < fly_cost * 0.1, (
            f"the boats cost {tow_cost:.2f} t against {fly_cost:.2f} flown — "
            "waiting has to be worth something")
        assert tow_ticks > fly_ticks * 1.5, (
            f"the boats took {tow_ticks} ticks against {fly_ticks} — waiting "
            "has to cost something too")
        told = tug.tug_line(towed)
        assert "boats have you" in told, told
        # And the clearance says so before you commit to waiting.
        assert "boats will take you in" in clearance_sim.line(towed.cleared)
        return (f"boats: {towed.towed:.1f} km towed, {tow_cost:.2f} t over "
                f"{tow_ticks / 60:.1f} h · flown: {fly_cost:.2f} t over "
                f"{fly_ticks / 60:.1f} h")

    @check("a wayside quay keeps no boats")
    def _():
        game, hub = _hub("noboats")
        port = game.system.port
        assert port is not None
        was = port.level
        try:
            port.level = 1
            assert not tug.has_tug(game, hub), "a level-1 quay has tugs"
            conn = conn_sim.start(
                game, targets_sim.target_from_contact(game, hub))
            said = clearance_sim.request(game, hub, conn)
            assert not said.tug
            assert "boats" not in clearance_sim.line(said)
            conn.cleared = said
            assert tug.tug_step(conn, 600.0) == 0.0
            port.level = tug.TUG_FROM
            assert tug.has_tug(game, hub)
        finally:
            port.level = was
        return (f"level 1 keeps none; level {tug.TUG_FROM} keeps boats")

    @check("a Weave anchor has nobody in it to defy")
    def _():
        # Control is a thing a station has. A ring somebody left grants
        # nothing, withholds nothing, and must not start refusing hulls
        # because a field was empty.
        game, gate = _hub("gate", kind="gate")
        target = targets_sim.target_from_contact(game, gate)
        conn = conn_sim.start(game, target)
        conn.cleared = clearance_sim.Clearance(False, "", station="")
        assert not control.has_control(conn)
        assert control.welcome(conn), "a gate refused somebody"
        assert not control.withheld(conn)
        assert control.refusal_line(conn) == ""
        name = [n for n, _at in moorings.points(target, 0.0)][0]
        _park(conn, target, name, moorings.spin_of(conn))
        assert moorings.at_berth(conn), "a gate would not take a hull"
        return f"{gate.name} clears nobody and stops nobody"
