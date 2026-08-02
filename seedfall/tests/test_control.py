"""Approach control: whose berth it is, and whether being told matters.

Measured by flying it, before `sim/control.py` existed:

    Fleet Hub: cleared for mast 4, hold at 555 m, 1.5 m/s or under.
    ... flew in regardless -> berthed at mast 3

The clearance was advisory. `Conn.cleared` had carried the assignment since the
protocol landed, with a docstring promising a berth "cannot be quietly swapped
for one the ship preferred" — and nothing downstream read the field, so the
promise was false in the one way that mattered.

And the berths were never full. Four masts on a hub and five hulls of traffic
working the same system, and `moorings.assign` chose between the masts with no
notion of anybody being there.

The claims:

- **Berths are held by somebody**, derived from where the traffic actually is,
  so a structure's capacity is a fact about the sector rather than a constant.
- **A full structure refuses, and says which berths are taken by whom.**
- **The berth you were cleared for is the berth you may use.** Fly a perfect
  approach to somebody else's and you are alongside nothing.
- **A dock that has not cleared you does not open**, and does not swing its
  boom out either — the quiet defence, available to every structure whatever
  else it has.
- **A Weave anchor has nobody in it**, so there is nothing there to defy.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..sim import clearance as clearance_sim
from ..sim import conn as conn_sim
from ..sim import control, tug
from ..sim import moorings
from ..sim import targets as targets_sim
from ..sim import track as track_sim
from .harness import Suite


def _hub(seed="control", kind="hub"):
    """A game, and a contact for the first structure of this sort in it."""
    for tag in (seed, seed + "-b", seed + "-c", seed + "-d"):
        game = new_game(tag)
        for contact in track_sim.contacts(game):
            if contact.kind == "anchorage" and contact.berth == kind:
                return game, contact
    raise AssertionError(f"no {kind} in four sectors")


def _park(conn, target, berth_name, spin=0.0, gap=0.0):
    """Put the hull exactly on a named berth, stopped."""
    at = dict(moorings.points(target, spin))[berth_name]
    reach = moorings.reach_km(target)
    conn.pos = [c * (1.0 + gap) for c in at]
    conn.vel = [0.0, 0.0, 0.0]
    return reach


def run(suite: Suite) -> None:
    check = suite.check

    @check("a berth is held by somebody, and the holding is derived")
    def _():
        # Nothing stored: who is in a berth is a function of where the traffic
        # is, the same discipline `sim/anchorage` uses to build a quay fresh
        # every call.
        game, hub = _hub()
        names = [n for n, _at in moorings.points(
            targets_sim.target_from_contact(game, hub), 0.0)]
        taken = control.holders(game, hub)
        assert set(taken) <= set(names), (taken, names)
        # Reading it twice gives the same answer, and nothing was written.
        assert control.holders(game, hub) == taken
        # Somewhere in the sector, a structure has somebody on it.
        anywhere = {}
        for tag in ("occ-a", "occ-b", "occ-c"):
            other = new_game(tag)
            for contact in track_sim.contacts(other):
                if contact.kind != "anchorage":
                    continue
                got = control.holders(other, contact)
                if got:
                    anywhere[contact.name] = got
        assert anywhere, "no berth anywhere in three sectors is occupied"
        said = control.waiting_line(game, hub)
        assert "berth" in said, said
        return (f"{len(names)} berths here, {len(taken)} taken · "
                f"{len(anywhere)} occupied structures across three sectors")

    @check("a full structure refuses, and says who is on it")
    def _():
        # Built rather than hunted for: every berth held, and the answer to
        # "may I come in" becomes a real and common no.
        game, hub = _hub("full")
        target = targets_sim.target_from_contact(game, hub)
        names = [n for n, _at in moorings.points(target, 0.0)]
        held = {name: f"Hull {i}" for i, name in enumerate(names)}
        real = control.holders
        control.holders = lambda g, c: dict(held) if c is hub else real(g, c)
        try:
            assert control.full(game, hub)
            conn = conn_sim.start(game, target)
            said = clearance_sim.request(game, hub, conn)
            assert not said.granted, "a full structure cleared a hull anyway"
            assert "full" in said.why, said.why
            for name in names:
                assert name in said.why, (name, said.why)
            assert said.station, "a refusal with nobody speaking it"
        finally:
            control.holders = real
        return said.why[:96]

    @check("the berth you were cleared for is the berth you may use")
    def _():
        game, hub = _hub("assign")
        target = targets_sim.target_from_contact(game, hub)
        conn = conn_sim.start(game, target)
        said = clearance_sim.request(game, hub, conn)
        assert said.granted, said.why
        conn.cleared = said
        # The *far* side of the structure, deliberately. `moorings.assign` has
        # reach-sized hysteresis — added so a hand-flown approach could not
        # flap between two masts a few metres apart — so a berth barely
        # further away than the one being held is still the one being held.
        # That is right for flying and it means this check has to move the
        # hull somewhere the sim will genuinely re-pick.
        places = dict(moorings.points(target, moorings.spin_of(conn)))
        free = sorted((n for n in control.free(game, hub) if n != said.berth),
                      key=lambda n: -math.dist(places[n], places[said.berth]))
        assert free, "a structure with only one free berth; move the check"

        # On the berth you were given: the equipment works.
        _park(conn, target, said.berth, moorings.spin_of(conn))
        assert control.at_own_berth(conn), "not recognised on its own berth"
        assert not control.withheld(conn)
        assert moorings.at_berth(conn), "the assigned berth would not take it"

        # On somebody else's, flown just as well: nothing. And the reason is
        # structural rather than a rule — `moorings.nearest` measures the gap
        # to the berth the port gave, so sitting on another one is simply a
        # long way from the only fitting that counts.
        conn.berth = ""            # a fresh look, not the one it was holding
        _park(conn, target, free[0], moorings.spin_of(conn))
        found = moorings.nearest(conn)
        assert found["name"] == said.berth, (
            f"the computer re-aimed at {found['name']} instead of holding the "
            f"assignment {said.berth}")
        assert not found["at_it"], (
            f"parked on {free[0]} and read as arrived at {said.berth}")
        assert not control.at_own_berth(conn)
        assert not moorings.at_berth(conn), (
            f"cleared for {said.berth} and moored to {free[0]}")
        gap = found["km"] * 1000
        return (f"cleared for {said.berth}: it takes the lines, and from "
                f"{free[0]} the hull is {gap:,.0f} m off the only berth that "
                "counts")

    @check("a dock that has not cleared you does not open")
    def _():
        # However well it is flown. This is the defence every structure has
        # whatever else it has, and it costs the station nothing.
        game, hub = _hub("uncleared")
        target = targets_sim.target_from_contact(game, hub)
        conn = conn_sim.start(game, target)
        conn.cleared = clearance_sim.Clearance(
            False, "You are not welcome here.", station=hub.name)
        name = control.free(game, hub)[0]
        _park(conn, target, name, moorings.spin_of(conn))
        assert not control.welcome(conn)
        assert control.withheld(conn)
        assert not moorings.at_berth(conn), "an uncleared hull moored"
        told = control.refusal_line(conn)
        assert "not opening" in told, told
        return told

    @check("a boom is not swung out for a hull nobody cleared")
    def _():
        # The standoff case, which is the one where the structure has to *do*
        # something to complete the berthing — so declining is the whole of it.
        # No generic "holding" occurs in the sector any more: every holding a
        # captain plants carries its own class. So plant one that stands its
        # visitors off — a RADIX Mine does — and use that.
        from ..sim import colony as colony_sim
        game = new_game("boom")
        body = game.system.bodies[1]
        game.colonies.append(colony_sim.Colony(
            id=1, class_id="radix_mine", name="Deepcut",
            system_id=game.system.id, body_id=body.id, need=0, online=True))
        holding = next(c for c in track_sim.contacts(game)
                       if c.kind == "anchorage" and c.berth == "radix_mine")
        target = targets_sim.target_from_contact(game, holding)
        assert moorings.sort_of(target) == "standoff", moorings.sort_of(target)

        def hold(cleared):
            conn = conn_sim.start(game, target)
            conn.cleared = cleared
            name = (cleared.berth if cleared.granted
                    else control.free(game, holding)[0])
            _park(conn, target, name, moorings.spin_of(conn))
            for _ in range(400):
                moorings.boom_step(conn, 60.0)
            return conn.boom

        welcome = clearance_sim.request(game, holding,
                                        conn_sim.start(game, target))
        assert welcome.granted, welcome.why
        out = hold(welcome)
        shut = hold(clearance_sim.Clearance(False, "No.", station=holding.name))
        assert out >= 1.0, f"a cleared hull never got the boom: {out:.2f}"
        assert shut <= 0.0, f"an uncleared hull got the boom to {shut:.2f}"
        return (f"cleared: the arm runs out to {out:.2f} · refused: it stays "
                f"in at {shut:.2f}")

    @check("a docked ship is drawn on the berth it is holding")
    def _():
        # The occupancy has to be *visible*, or it is a rule with no picture:
        # a pilot flying up to a full station would see four empty masts.
        # Measured before this: a hull holding mast 3 was drawn 418 km out,
        # because `sky.build`'s co-location lift moves anything sharing the
        # target's position clear of it — and a berth is the one thing that
        # must not be moved.
        from ..sim import sky as sky_sim
        for tag in ("gap", "control", "occ-a", "occ-b", "occ-c"):
            game = new_game(tag)
            for hub in [c for c in track_sim.contacts(game)
                        if c.kind == "anchorage"]:
                held = control.holders(game, hub)
                if not held:
                    continue
                target = targets_sim.target_from_contact(game, hub)
                spots = dict(moorings.points(
                    target, moorings.spin_at(target, 0.0)))
                seen = {s.name: s for s in sky_sim.build(game, hub)}
                for berth, who in held.items():
                    assert who in seen, f"{who} holds {berth} and is not drawn"
                    off = math.dist(seen[who].at, spots[berth])
                    assert off < 0.001, (
                        f"{who} holds {berth} and is drawn {off * 1000:,.0f} m "
                        "from it")
                # And a hull that is *not* docked is still out where it is.
                loose = [s for s in seen.values() if s.kind == "hull"
                         and s.name not in held.values()]
                if loose:
                    assert math.dist(loose[0].at, (0.0, 0.0, 0.0)) > 1.0, (
                        f"{loose[0].name} is not docked and is drawn on top "
                        "of the structure")
                return (f"{hub.name}: {', '.join(f'{w} on {b}' for b, w in held.items())}"
                        ", drawn on the fitting itself")
        raise AssertionError("no occupied berth in five sectors to draw")

    @check("the ladder climbs in order, and only while you keep closing")
    def _():
        # The whole point of a warning rather than a countdown: it is a
        # conversation about your vector. Check up and the structure stops
        # climbing; keep coming and it does not.
        game, hub = _hub("ladder")
        target = targets_sim.target_from_contact(game, hub)

        def fly(comply_at=None):
            conn = conn_sim.start(game, target)
            conn.cleared = clearance_sim.Clearance(
                False, "You are not welcome.", station=hub.name)
            conn.watch = control.post(game, hub)
            rungs = []
            for tick in range(240):
                if comply_at is not None and tick >= comply_at:
                    conn.vel = [0.0, 0.0, 0.0]
                    conn_sim.apply(conn, None, main=False, ticks=1)
                else:
                    conn_sim.apply(conn, "forward", main=False, ticks=1)
                if conn.told and (not rungs or rungs[-1] != conn.told):
                    rungs.append(conn.told)
                if conn.over:
                    break
            return conn, rungs

        kept, rungs = fly()
        assert rungs == sorted(rungs), f"the ladder went backwards: {rungs}"
        assert rungs == list(range(1, len(rungs) + 1)), (
            f"a rung was skipped: {rungs}")
        assert kept.told >= 2, f"a hull that ignored everything got {kept.told}"
        said = " ".join(kept.log)
        assert "State your intentions" in said, "nobody was hailed"
        assert "Come about" in said, "nobody was warned"

        # The same flight, corrected.
        gave, _r = fly(comply_at=14)
        assert gave.told < kept.told, (
            f"checking up did not help: {gave.told} against {kept.told}")
        assert gave.damage == 0.0, (
            f"a hull that checked up was still shot for {gave.damage}")
        return (f"ignored: {control.LADDER[kept.told]} and {kept.damage:.0f} "
                f"damage · corrected at tick 14: "
                f"{control.LADDER[gave.told]} and none")

    @check("what a structure can do is what it has")
    def _():
        # Off `Port.level`, `Port.capital` and the system's ward — three
        # figures that already existed and touched no approach.
        game, hub = _hub("means")
        port = game.system.port
        assert port is not None, "no port in this system to read"
        top = control.means(game, hub)
        assert 2 <= top <= 4, top
        was = (port.level, port.capital)
        try:
            port.level, port.capital = 1, False
            assert control.means(game, hub) == 2, (
                "a wayside quay can do more than shout")
            port.level = 2
            assert control.means(game, hub) == 3, "a station cannot ward"
            port.capital = True
            assert control.means(game, hub) == 4, "a capital cannot repel"
        finally:
            port.level, port.capital = was
        # A hull is not a station and has no approaches to control.
        loose = next((c for c in track_sim.contacts(game) if c.kind == "hull"),
                     None)
        if loose is not None:
            assert control.means(game, loose) == 0
        return (f"quay 2 · station 3 · capital 4 — and {port.name} at level "
                f"{port.level} is {control.LADDER[top]}-capable")

    @check("standing buys patience, and never a bigger gun")
    def _():
        game, hub = _hub("patience")
        game.rep = dict(getattr(game, "rep", {}))
        seen = {}
        for rep in (80.0, 0.0, -80.0):
            if hub.faction:
                game.rep[hub.faction] = rep
            seen[rep] = control.post(game, hub)
        assert seen[80.0]["grace"] > seen[0.0]["grace"] > seen[-80.0]["grace"], (
            {k: v["grace"] for k, v in seen.items()})
        ceilings = {v["means"] for v in seen.values()}
        assert len(ceilings) == 1, (
            f"standing changed what the structure could do: {ceilings}")
        return " · ".join(f"rep {rep:+.0f}: {v['grace']} ticks"
                          for rep, v in seen.items())

    @check("being fired on costs more the longer you take it")
    def _():
        # Ranging shots first. A captain who turns away after one is barely
        # scratched; one who keeps coming is being killed by degrees and can
        # watch it happening.
        class Probe:
            told = 3
            warded_for = 0
        probe = Probe()
        bites = []
        for held in range(6):
            probe.warded_for = held
            bites.append(control.ward_bite(probe))
        assert bites == sorted(bites), bites
        assert bites[-1] > bites[0] * 2, (bites[0], bites[-1])
        probe.told = 2
        assert control.ward_bite(probe) == 0.0, "warned is not fired on"
        return (f"first tick {bites[0]:.2f}, sixth {bites[-1]:.2f} — "
                f"{bites[-1] / bites[0]:.1f}x for persisting")

    @check("a hull that is welcome is never told anything")
    def _():
        game, hub = _hub("welcome")
        target = targets_sim.target_from_contact(game, hub)
        conn = conn_sim.start(game, target)
        said = clearance_sim.request(game, hub, conn)
        assert said.granted, said.why
        conn.cleared = said
        conn.watch = control.post(game, hub)
        for _ in range(120):
            conn_sim.apply(conn, "forward", main=False, ticks=1)
            if conn.over:
                break
        assert conn.told == 0, f"a cleared hull was escalated to {conn.told}"
        assert conn.damage == 0.0 or conn.outcome == "collision", (
            f"a cleared hull was shot for {conn.damage}")
        return f"cleared, flown right in, and told nothing: {conn.outcome}"

    @check("a station simply leaves, and is off station afterwards")
    def _():
        # The measure a structure has when it has no guns and takes as well
        # when it does. Through `sim/knock`, the door a shove already uses, so
        # a station that ran from you is off station on every screen.
        from ..sim import berthing as berthing_sim
        from ..sim import knock as knock_sim
        game, hub = _hub("sheer")
        target = targets_sim.target_from_contact(game, hub)
        conn = conn_sim.start(game, target)
        conn.cleared = clearance_sim.Clearance(
            False, "No.", station=hub.name, max_closing=1.5)
        conn.watch = control.post(game, hub)
        for _ in range(300):
            conn_sim.apply(conn, "forward", main=False, ticks=1)
            if conn.over:
                break
        assert conn.told >= control.SHEER_FROM, conn.told
        assert conn.sheered > 0.0, "the station stood its ground"
        assert control.sheers(conn)
        told = control.sheer_line(conn)
        assert "opening the range" in told, told

        # And it lands on the sector, not just on the approach.
        before = dict(knock_sim.store(game))
        berthing_sim.commit(game, conn)
        after = knock_sim.store(game)
        assert target.id in after and target.id not in before, (
            "the station sheered off and the sector never heard")
        assert any("stood off under power" in text
                   for _day, text, _kind in game.log), "nothing said so"
        return (f"{hub.name} opened {conn.sheered * 1000:,.0f} m and is off "
                "station on the plot afterwards")

    @check("a structure with nobody aboard does not run")
    def _():
        # Sheering off takes somebody to do it. A Weave anchor is a ring
        # somebody left; it neither clears you nor flees you.
        game, gate = _hub("gate", kind="gate")
        target = targets_sim.target_from_contact(game, gate)
        conn = conn_sim.start(game, target)
        conn.cleared = clearance_sim.Clearance(False, "", station="")
        conn.watch = control.post(game, gate)
        conn.told = 4
        assert not control.sheers(conn), "a gate ran away"
        assert control.sheer_step(conn, 60.0) == 0.0
        assert conn.sheered == 0.0
        return f"{gate.name} does not move for anybody"

    @check("a station's patience is the range, not the calendar")
    def _():
        # Measured, and it was wrong: a hull pressed in at full drive covered
        # twelve kilometres in twenty ticks and got a hail and a warning,
        # while one merely *drifting* in took two hundred ticks and collected
        # all four rungs. Patience counted in ticks is counted in the wrong
        # thing.
        game, hub = _hub("haste")
        target = targets_sim.target_from_contact(game, hub)

        def fly(axis):
            conn = conn_sim.start(game, target)
            conn.cleared = clearance_sim.Clearance(
                False, "No.", station=hub.name, max_closing=1.5)
            conn.watch = control.post(game, hub)
            ticks = 0
            for ticks in range(300):
                conn_sim.apply(conn, axis, main=False, ticks=1)
                if conn.over:
                    break
            return conn, ticks

        hard, fast_ticks = fly("forward")
        soft, slow_ticks = fly(None)
        assert fast_ticks < slow_ticks, (fast_ticks, slow_ticks)
        assert hard.told >= soft.told, (
            f"pressing in reached {hard.told} and drifting reached "
            f"{soft.told} — the ladder is counting ticks")
        assert hard.damage > soft.damage * 4, (
            f"pressing in cost {hard.damage} and drifting {soft.damage}")
        # (Haste is read during the flight, not after: both end stopped.)
        return (f"pressed in: {control.LADDER[hard.told]} in {fast_ticks} "
                f"ticks and {hard.damage:.0f} damage · drifted: "
                f"{control.LADDER[soft.told]} in {slow_ticks} and "
                f"{soft.damage:.0f}")

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
