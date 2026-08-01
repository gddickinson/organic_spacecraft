"""Forcing a berth: what a refusal costs the ship that ignores it.

`sim/control.py` gave a structure the authority to say no, and it was a very
good no: no boom swung out, no hatch opened, no lines across, and a hull could
sit perfectly on the berth for as long as it liked with nothing to show for it.
The gap that left is the one this file measures. **There was no answer to it.**
A captain determined to get in had exactly the same options as one who had
never been refused — which made the refusal a wall rather than a decision, and
made every defence above it decoration on a wall that already held.

The claims, each flown rather than reasoned about:

- **A refused berth can be cut into**, and the hull that does it is alongside.
  Not a die roll: it is ten minutes of station-keeping on somebody's fitting
  while grinding into it. And the station *turns*, so it really is
  station-keeping — the first draft of these checks parked the hull in
  inertial space and watched it slide off the collar at 40% cut.
- **What guns buy is the price, not a refusal.** This claim has been wrong
  twice and flying it said so both times: a capital port *can* be cut into,
  and a starting hull *does* survive it — on 93 of 336, inside a port it has
  just broken into, which is worse than dying. Nothing refuses the cut and
  nothing should. What stops you is arithmetic, and the arithmetic is the
  structure's own `means` on both sides of it: the same number buys the guns
  and buys the time they have to fire, so they cannot drift apart.
- **A standoff berth cannot be forced at all.** There is nothing to cut: the
  boom is inboard and a hull holding station in open space has nothing to get
  hold of. The berths that come out to meet you are the berths that can simply
  decline to, which is a real defensive property of a kind of dock.
- **The sector remembers.** Being fired on goes in the books, forcing goes in
  harder, and being merely hailed does not — because a grudge that everything
  triggers is a grudge that means nothing.
- **A twin forecasts the cut**, or the plot would quote an approach as though
  the hatch would never open.

The last claim is the one that found a defect: `control.provoked` was written
the day the ladder landed and read by nobody at all. The reachability guard
missed it because an unrelated local variable in `sim/threat.py` is also
called `provoked`, and a bare name credits every module that has one.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import berthing
from ..sim import clearance as clearance_sim
from ..sim import colony as colony_sim
from ..sim import conn as conn_sim
from ..sim import control
from ..sim import forcing
from ..sim import grudge as grudge_sim
from ..sim import autopilot as pilot
from ..sim import moorings
from ..sim import preview
from ..sim import targets as targets_sim
from ..sim import track as track_sim
from .harness import Suite


def _hub(seed="forcing", kind="hub"):
    for tag in (seed, seed + "-b", seed + "-c", seed + "-d"):
        game = new_game(tag)
        for contact in track_sim.contacts(game):
            if contact.kind == "anchorage" and contact.berth == kind:
                return game, contact
    raise AssertionError(f"no {kind} in four sectors")


def _refused(game, contact, means: int = 0):
    """A hull parked on a berth it was told it could not have.

    `means` is what the structure can do about it — the same number
    `control.post` derives from the port, handed in directly so a check can
    hold everything else still and move only the defences.
    """
    target = targets_sim.target_from_contact(game, contact)
    conn = conn_sim.start(game, target)
    conn.cleared = clearance_sim.Clearance(
        False, "You are not welcome here.", station=contact.name)
    conn.watch = {"means": means, "grace": 6,
                  "faction": getattr(contact, "faction", "") or "hearth"}
    name = control.free(game, contact)[0]
    at = dict(moorings.points(target, moorings.spin_of(conn)))[name]
    conn.pos = list(at)
    conn.vel = [0.0, 0.0, 0.0]
    return conn


def _grind(conn, ticks: int) -> int:
    """Hold the berth and cut, the way a captain actually would.

    **The station turns.** A hull parked exactly on a fitting is not on it a
    minute later, so cutting is not sitting still — it is station-keeping on a
    moving collar for as long as the cut takes, and it costs reaction mass on
    top of hull. The first draft of these checks left the ship in inertial
    space and it slid off the berth in five ticks with 40% cut; that is not a
    defect in the forcing, it is what the act is.
    """
    for spent in range(ticks):
        axis, main, throttle = pilot.autopilot(conn, "close")
        conn_sim.apply(conn, axis, main=main, throttle=throttle, ticks=1)
        if forcing.forced(conn) or conn.over:
            return spent + 1
    return ticks


def run(suite: Suite) -> None:
    check = suite.check

    @check("a refused berth can be cut into, and it costs")
    def _():
        game, hub = _hub("cut")
        conn = _refused(game, hub, means=0)
        assert control.withheld(conn), "nothing was being withheld to force"
        assert not moorings.at_berth(conn), "a refused hull was already moored"
        said = forcing.force(conn)
        assert conn.forcing, said
        assert "Cutting in" in said, said

        was, tank = conn.damage, conn.rcs
        took = _grind(conn, 40)
        assert forcing.forced(conn), (
            f"forty minutes of cutting and only {conn.cut * 100:.0f}% through")
        # And the whole point: the structure is open now.
        assert not control.withheld(conn), (
            "the collar was cut and the berth is still refusing")
        assert moorings.at_berth(conn), "cut in and moored to nothing"
        paid = conn.damage - was
        assert paid > 0, "cutting into somebody's dock cost the hull nothing"
        held = tank - conn.rcs
        assert held > 0, (
            "the station turns, so holding its collar cannot be free")
        return (f"{took} minutes on a turning collar, {paid:,.1f} hull and "
                f"{held:,.3f} t held there — and alongside")

    @check("what the guns buy is the price of getting in")
    def _():
        # This check has been wrong twice, and both times flying it said so.
        #
        # First claim: a capital port *cannot* be forced. It can — the cut went
        # through in half an hour. Nothing in the design refuses it and nothing
        # should: what stops you is arithmetic, and the arithmetic is the
        # structure's own `means` on both sides, the time and the guns.
        #
        # Second claim: you do not survive it. Measured, a starting hull comes
        # away with 93 of 336 — so it lives, on its last two layers, inside a
        # capital port that has just been broken into. Which is worse than
        # dying and is the actual answer.
        def price(seed, means, shot):
            game, hub = _hub(seed)
            whole = sum(layer.hp for layer in game.ship.layers)
            conn = _refused(game, hub, means=means)
            conn.told = 3 if shot else 0
            forcing.force(conn)
            _grind(conn, 60)
            assert forcing.forced(conn), (
                f"the cut was refused at means {means}")
            conn.outcome, conn.landed = "alongside", False
            berthing.commit(game, conn)
            left = sum(layer.hp for layer in game.ship.layers)
            return conn.damage, whole, left

        # A capital, firing for the whole half hour the cut takes.
        hard, whole, left = price("guns", 4, True)
        # A wayside quay, which cannot reach rung 3 and so cannot shoot at all:
        # `means` is the one number and it is not two knobs pretending to be.
        easy, whole2, spare = price("guns", 0, False)

        assert hard > easy * 10, (
            f"forcing a capital cost {hard:,.0f} against {easy:,.0f} at a "
            "quay, which is not the difference between guns and a radio")
        assert left < whole * 0.35, (
            f"broke into a capital port and kept {left} of {whole} hull")
        assert spare > whole2 * 0.9, (
            f"forcing an undefended quay cost {whole2 - spare} of {whole2}, "
            "which makes the guns mean nothing")
        return (f"capital: {hard:,.0f} hull, {left} of {whole} left — inside, "
                f"on the last layers · quay: {easy:,.0f}, {spare} of {whole2}")

    @check("a standoff berth has nothing to force")
    def _():
        # Falls out of the physics rather than being a rule: a hull at a
        # standoff berth is holding station in open space, and the boom that
        # would reach it is inboard.
        game = new_game("standoff-force")
        body = game.system.bodies[1]
        game.colonies.append(colony_sim.Colony(
            id=1, class_id="radix_mine", name="Deepcut",
            system_id=game.system.id, body_id=body.id, need=0, online=True))
        holding = next(c for c in track_sim.contacts(game)
                       if c.kind == "anchorage" and c.berth == "radix_mine")
        target = targets_sim.target_from_contact(game, holding)
        assert moorings.sort_of(target) == "standoff"
        conn = _refused(game, holding, means=0)
        why = forcing.forcible(conn)
        assert "nothing to get hold of" in why, why
        assert forcing.force(conn) == why and not conn.forcing
        for _tick in range(40):
            conn_sim.apply(conn, None, ticks=1)
        assert not forcing.forced(conn) and conn.cut == 0.0
        assert not moorings.at_berth(conn), "forced a standoff berth anyway"
        return why

    @check("you have to be on the berth, and the cut stays cut")
    def _():
        game, hub = _hub("presence")
        conn = _refused(game, hub, means=0)
        forcing.force(conn)
        _grind(conn, 4)
        part = conn.cut
        assert 0.0 < part < 1.0, part

        # Off the berth: no progress, and none lost either. Unlike the boom,
        # which runs back in — a cut is a cut, and the metal does not heal.
        conn.pos = [c * 6.0 for c in conn.pos]
        conn.vel = [0.0, 0.0, 0.0]
        for _tick in range(6):
            conn_sim.apply(conn, None, ticks=1)
        assert abs(conn.cut - part) < 1e-9, (
            f"drifting off the berth moved the cut from {part:.3f} to "
            f"{conn.cut:.3f}")
        assert "before you can cut" in forcing.forcible(conn)
        return (f"{part * 100:,.0f}% through, six minutes adrift, still "
                f"{conn.cut * 100:,.0f}% through")

    @check("the sector remembers being shot at, and remembers forcing worse")
    def _():
        # `control.provoked` was written the day the ladder landed and read by
        # nobody: an approach could be hailed, warned, fired on and cut open
        # and the politics would never hear of it.
        game, hub = _hub("books")
        who = getattr(hub, "faction", "") or "hearth"

        quiet = _refused(game, hub, means=0)
        quiet.told = 2                                     # warned, no more
        assert forcing.grievance(quiet) == {}, (
            "a radio warning went in somebody's books")

        shot = _refused(game, hub, means=3)
        shot.told = 3
        felt_before = grudge_sim.feeling(game, who)
        grief = forcing.grievance(shot)
        assert grief["kind"] == "trespass", grief
        assert forcing.provoked(shot) == 3

        cut = _refused(game, hub, means=0)
        cut.cut = 1.0
        assert forcing.provoked(cut) == forcing.FORCED_RUNG
        worse = forcing.grievance(cut)
        assert worse["kind"] == "forced", worse
        assert worse["salience"] > grief["salience"], (worse, grief)

        # And it lands, through the same door the approach already used.
        cut.landed = False
        cut.outcome = "alongside"
        berthing.commit(game, cut)
        felt_after = grudge_sim.feeling(game, who)
        assert felt_after < felt_before, (
            f"cut into their dock and they feel {felt_after:.2f} against "
            f"{felt_before:.2f}")
        why = grudge_sim.because(game, who)
        assert any("Cut into a berth" in str(line) for line in why), why
        return (f"{who}: {felt_before:+.2f} → {felt_after:+.2f}, and it can "
                f"say why — {why[0]}")

    @check("a forecast knows the collar is half cut")
    def _():
        # The ninth and tenth fields `preview._copy` has had to learn. A twin
        # that forgot the cut would quote an approach as though the hatch were
        # never going to open.
        game, hub = _hub("twin")
        conn = _refused(game, hub, means=0)
        forcing.force(conn)
        _grind(conn, 5)
        twin = preview._copy(conn)
        assert twin.forcing == conn.forcing
        assert twin.cut == conn.cut, (twin.cut, conn.cut)
        # And it goes on cutting, which is what carrying it is for.
        _grind(twin, 6)
        assert twin.cut > conn.cut, (
            f"the twin held at {twin.cut:.3f} while the ship was at "
            f"{conn.cut:.3f}")
        return (f"ship {conn.cut * 100:,.0f}% through, twin picks it up there "
                f"and forecasts {twin.cut * 100:,.0f}%")
