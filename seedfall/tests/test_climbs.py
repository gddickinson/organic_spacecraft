"""What a climb costs, and whether the conn will sell one it cannot fly.

`orbits.heights_for` has offered rungs on `holdable` since the ladder was
written — whether the thrusters are *fine* enough to settle on one. Nobody ever
asked whether the tank was *big* enough to get there. Measured across three
sectors on the tank a NAVIS carries: **every high rung at every body was
offered, and not one of them was reachable** — 25 to 264 tonnes of reaction mass
quoted against the 20 t a captain opens with, so the answer arrived as an empty
tank at 63–76% of the height asked for, with nothing left to leave on.

The claims here:

- **Nothing is offered that cannot be flown on the tank in hand**, checked by
  flying every offered rung on the real tank rather than on the unlimited one
  the older suite uses.
- **The quote is what the climb spends**, within the margin the quote carries.
- **A refused rung is shown, priced, and refused** — not hidden. The tank is
  volatiles in the hold, so a high orbit is a fuel decision, and the screen has
  to be where that decision is visible.
- **And it really is a decision**: the same rung at the same body is refused on
  an opening tank and offered to a hull that has taken on mass.
- **The figures are pinned** against arithmetic written here, not against the
  constants under test.

What is deliberately *not* claimed: that the flight computer is efficient. It is
not — measured, a climb costs 1.08 to 1.16 times the ideal at a world and far
more at a body where the thrusters have little authority, which is what
`orbits.QUOTABLE` refuses to quote for. Three control laws were written and
measured against the shipped one during this work and none of them was better on
the tank the game actually flies; the findings are in `sim/autopilot.py`.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..sim import autopilot, conn as conn_sim, orbits, pilot
from ..sim import track as track_sim
from .harness import Suite

#: Sectors flown for the sweeps. Five, because a body's size decides
#: everything here and one system is one draw of the dice — three seeds
#: came up almost all rock and offered nine rungs between them.
SEEDS = ("climb-a", "climb-b", "climb-c", "climb-d", "climb-e",
         "climb-f", "climb-g", "climb-h")


def _bodies(game):
    for index, body in enumerate(game.system.bodies):
        contact = next((c for c in track_sim.contacts(game, game.system)
                        if c.body_index == index), None)
        if contact is not None:
            yield index, body, contact


def _fly(game, contact, want_km: float, tank: float | None = None,
         limit: int = 60000):
    """Fly to a height on the tank the hull actually has. Returns the conn."""
    conn = conn_sim.start(game, contact)
    if tank is not None:
        conn.rcs = tank
    conn.orbit_want_km = want_km
    spent_from = conn.rcs
    for _tick in range(limit):
        axis, main, throttle = autopilot.autopilot(conn, "orbit")
        conn_sim.apply(conn, axis, main, throttle=throttle)
        if conn.over:
            break
    conn.spent = spent_from - conn.rcs
    return conn


def run(suite: Suite) -> None:
    check = suite.check

    @check("the conn offers no climb the tank in hand cannot make")
    def _():
        # The whole point, and it is flown rather than reasoned about. Note the
        # tank is left exactly as `conn.start` found it: the older suite hands
        # the hull 99,999 t so it can ask a different question, and that is the
        # very substitution that hid this for as long as the ladder has existed.
        offered = arrived = 0
        for seed in SEEDS:
            game = new_game(seed)
            for _index, body, contact in _bodies(game):
                probe = conn_sim.start(game, contact)
                for hid, _label, want in orbits.heights_for(
                        probe.target, probe.rcs_dv,
                        pilot.dv_left(probe), probe.range_km):
                    offered += 1
                    conn = _fly(game, contact, want)
                    got = orbits.semi_major_km(conn)
                    assert conn.outcome != "dry", (
                        f"{body.name} {hid}: offered, and the tank ran out at "
                        f"{100 * got / want:.0f}% of the height")
                    assert conn.outcome != "aground", (
                        f"{body.name} {hid}: offered, and it hit the body")
                    assert abs(got - want) <= want * 0.1, (
                        f"{body.name} {hid}: asked for {want:,.0f} km and "
                        f"settled at {got:,.0f}")
                    assert orbits.in_orbit(conn), (
                        f"{body.name} {hid}: arrived, and it is not an orbit")
                    arrived += 1
        assert offered >= 12, (
            f"only {offered} rungs offered across {len(SEEDS)} sectors — the\n"
            "gates have closed the ladder rather than trimmed it")
        return (f"{arrived} of {offered} offered rungs flown on the opening "
                "tank, every one a sound orbit within a tenth of the height")

    @check("the price on the rung is what the climb takes off the hold")
    def _():
        # Forecast against act, in the direction that matters: **the quote is
        # never less than the climb spends.** That is the promise a captain
        # commits a tank to.
        #
        # It is deliberately not "the quote equals the spend". A hull arrives with
        # its axis a few per cent off a rung and `in_orbit` is already true —
        # measured, 2.97% below the standard rung at Vesper's Crossing I with
        # e=0.031 — so the approach resolves before a single burn and the climb
        # priced at 3.22 t costs nothing at all. Where a climb really happens,
        # the spend is asked to sit inside the margin, so the quote cannot be
        # padded into meaninglessness either.
        worst = 0.0
        tightest = 9e9
        flown = 0
        checked = 0
        for seed in SEEDS:
            game = new_game(seed)
            for _index, body, contact in _bodies(game):
                probe = conn_sim.start(game, contact)
                for row in pilot.climb_options(probe):
                    if not row["afford"] or row["dv"] <= 0:
                        continue
                    conn = _fly(game, contact, row["radius"])
                    bare = pilot.mass_for(probe, row["dv"])
                    assert conn.spent <= row["mass"] + 1e-6, (
                        f"{body.name} {row['id']}: quoted {row['mass']:.2f} t "
                        f"and spent {conn.spent:.2f}")
                    checked += 1
                    if conn.spent <= 0 or bare <= 0:
                        continue
                    flown += 1
                    worst = max(worst, conn.spent / bare)
                    tightest = min(tightest, conn.spent / bare)
        assert checked >= 5, checked
        assert flown >= 2, (
            f"only {flown} of {checked} offered rungs needed a burn at all, so "
            "this check is not measuring a climb")
        assert worst <= orbits.CLIMB_MARGIN, (
            f"a climb took {worst:.2f}x the ideal and the quote allows only "
            f"{orbits.CLIMB_MARGIN:.2f}x")
        return (f"{checked} climbs, every one inside its quote; the {flown} that "
                f"needed a burn took {tightest:.2f}–{worst:.2f}x the ideal "
                f"against a quoted {orbits.CLIMB_MARGIN:.2f}x")

    @check("a rung the tank cannot buy is priced and refused, not hidden")
    def _():
        # The tank is volatiles in the hold, so this is a fuel decision — and a
        # screen that quietly drops the rung drops the decision too. Read off
        # the rendered console, because that is where the captain reads it.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..ui.conn_window import ConnWindow
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        # Through `berthing.begin`, which is the door the window itself uses:
        # the conn is refused on anything the ship is not already near, and a
        # window opened on a refusal is watching rather than flying. Building the
        # search on `conn.start` instead found a body the window then could not
        # open, and the check read as "nothing was refused".
        from ..sim import berthing as berth_sim
        found = None
        for seed in SEEDS:
            game = new_game(seed)
            for _index, body, contact in _bodies(game):
                # Put the ship in orbit round the body first, the way
                # `test_cameras` does: a captain opens the conn on what they are
                # already alongside, and at the opening a hull is at a quay.
                game.orbit_body = body.id
                if not berth_sim.can_conn(game, contact)[0]:
                    continue
                live, _why = berth_sim.begin(game, contact)
                if live is None or live.target.kind != "body":
                    continue
                rows = pilot.climb_options(live)
                if any(not row["afford"] for row in rows) and \
                        any(row["afford"] for row in rows):
                    found = (game, contact, body)
                    break
            if found:
                break
        assert found, (
            "no body the conn will open on, in eight sectors, both offers and "
            "refuses a rung")
        game, contact, body = found

        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        conn = ConnWindow(win, contact)
        conn.refresh()
        for _ in range(3):
            app.processEvents()
        # `isHidden`, not `isVisible`: the window is never shown, so everything
        # in it reads invisible either way. Hiding a refused rung is the failure
        # mode this check exists for — it passed a mutation that did exactly
        # that until the assertion below was added.
        said = {}
        for hid, (btn, _text) in conn.controls.height_buttons.items():
            said[hid] = (btn.text(), btn.isEnabled(), btn.toolTip(),
                         not btn.isHidden())
        rows = {row["id"]: row for row in conn.controls.window._climbs()}
        conn.close()
        win.close()

        refused = [hid for hid, row in rows.items() if not row["afford"]]
        assert refused, refused
        for hid in refused:
            text, enabled, tip, shown = said[hid]
            assert shown, (
                f"{hid} is refused and hidden — the price is the whole point, "
                "and a rung nobody can see is a decision nobody can make")
            assert not enabled, f"{hid} is refused and the button is live"
            assert "✕" in text, f"{hid} is refused and reads {text!r}"
            assert "t of" in tip and "you have" in tip, (
                f"{hid} is refused and never says what it would cost: {tip!r}")
            assert "volatiles" in tip, (
                f"{hid} is refused and does not say what would fix it: {tip!r}")
        for hid, row in rows.items():
            if row["afford"] and row["dv"] > 0:
                assert said[hid][1], f"{hid} is affordable and not offered"
                assert said[hid][3], f"{hid} is affordable and hidden"
        return (f"{body.name}: {len(refused)} rung(s) refused with a price on "
                f"them — {said[refused[0]][0]!r}, "
                f"{rows[refused[0]]['mass']:,.0f} t against "
                f"{rows[refused[0]]['tank']:,.0f} aboard")

    @check("a high orbit is a fuel decision, not a wall")
    def _():
        # The gate is only honest if taking on mass opens the rung. It is the
        # ship's own volatiles — see `conn.start` — so this is a thing a captain
        # can go and do something about, at the same counter as everything else.
        opened = None
        for seed in SEEDS:
            game = new_game(seed)
            for _index, body, contact in _bodies(game):
                probe = conn_sim.start(game, contact)
                shut = [row for row in pilot.climb_options(probe)
                        if not row["afford"]]
                if not shut:
                    continue
                want = shut[0]
                game.ship.cargo["volatiles"] = want["mass"] * 1.2 + 10
                richer = conn_sim.start(game, contact)
                after = {row["id"]: row["afford"]
                         for row in pilot.climb_options(richer)}
                assert after[want["id"]], (
                    f"{body.name} {want['id']}: {want['mass']:.0f} t quoted, "
                    f"{richer.rcs:.0f} t aboard, and still refused")
                conn = _fly(game, contact, want["radius"])
                assert conn.outcome != "dry", (
                    f"{body.name} {want['id']}: bought the mass and still ran "
                    f"out — {conn.spent:.1f} t against a quote of "
                    f"{want['mass']:.1f}")
                got = orbits.semi_major_km(conn)
                assert abs(got - want["radius"]) <= want["radius"] * 0.1, (
                    f"{got:,.0f} km against {want['radius']:,.0f} asked")
                opened = (body.name, want, conn.spent, richer.rcs)
                break
            if opened:
                break
        assert opened, "nothing was refused anywhere, so nothing could be opened"
        name, want, spent, tank = opened
        return (f"{name} {want['id']}: refused on 20 t, flown on {tank:,.0f} for "
                f"{spent:,.0f} — the quote said {want['mass']:,.0f}")

    @check("the climb figures are pinned to arithmetic written here")
    def _():
        # Against numbers computed in the check, never against the constants
        # under test. A spiral between two circular orbits costs the difference
        # of their circular speeds, so this is `|sqrt(mu/r1) - sqrt(mu/r2)|`
        # worked out longhand for one case.
        mu = 398600.0                       # km³/s², Earth, to hand-check by
        low, high = 7000.0, 42164.0
        want = abs(math.sqrt(mu / low) - math.sqrt(mu / high)) * 1000.0
        got = orbits.climb_dv(mu, low, high)
        assert abs(got - want) < 1e-6, (got, want)
        assert 4400 < got < 4500, f"{got:.0f} m/s from LEO to geostationary"
        assert orbits.climb_dv(mu, low, low) == 0.0, "standing still costs"
        assert orbits.climb_dv(mu, high, low) == got, "downhill is not uphill"
        assert orbits.climb_dv(0.0, low, high) == 0.0, "no gravity, no climb"

        # And the two gates are the two questions, which is the distinction the
        # whole fix turns on: fine enough thrusters, and enough of them to be
        # worth quoting a price against.
        assert orbits.QUOTABLE > 2.0, (
            "the quotable line has to be stricter than `holdable`, or it is "
            "not asking a second question at all")
        game = new_game(SEEDS[0])
        _i, _b, contact = next(iter(_bodies(game)))
        probe = conn_sim.start(game, contact)
        assert pilot.dv_left(probe) > 0
        assert pilot.mass_for(probe, 0.0) == 0.0
        one = pilot.mass_for(probe, probe.rcs_dv * 0.5)
        assert abs(one - pilot.burn_cost(probe, False)) < 1e-9, (
            f"half a pulse costs {one} and a whole one is "
            f"{pilot.burn_cost(probe, False)} — pulses do not come in halves")
        return (f"LEO→geostationary {got:,.0f} m/s longhand; a half pulse "
                f"charged as one; the quotable line at {orbits.QUOTABLE:g} "
                "pulses against holdable's 2")
