"""Plotting against things that move: a forecast, and whether it comes true.

Split out of `tests/test_conn.py` when it reached 523 lines, along the seam
its own docstring names — flying the ship at close quarters there, plotting
against moving things here. What is held:

- **A prediction comes true**, checked by playing the chronicle forward.
- **An intercept costs what flying it charges** — the plot and the helm
  cannot disagree, because they are the same arithmetic.
- **A plot says how far it can be trusted**, a burn with no mass left is
  refused, the panel does not cry wolf at a good approach, and a forecast
  never writes to the chronicle it is forecasting.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..sim import autopilot as pilot_sim
from ..sim import conn as conn_sim
from ..sim import flight
from ..sim import track as track_sim
from .harness import Suite
from .test_conn import _contacts


def run(suite: Suite) -> None:
    check = suite.check

    @check("what the plot predicts is what the chronicle does")
    def _():
        # The prediction, played rather than asserted: forecast where each
        # contact will be, advance the sector for real, and look.
        held = moved = 0
        drift = []
        for seed in range(3):
            game = new_game(f"pred-{seed}")
            home_id = game.system.id
            said = {c.id: {ahead: track_sim.at(game, c, game.day + ahead)
                           for ahead in (7, 30, 90)}
                    for c in _contacts(game)}
            for ahead in (7, 30, 90):
                later = new_game(f"pred-{seed}")
                later.advance_days(ahead)
                home = later.galaxy.systems[home_id]
                now = {c.id: track_sim.at(later, c, later.day, home)
                       for c in track_sim.contacts(later, home)}
                for cid, byday in said.items():
                    if cid not in now:
                        drift.append(f"{cid} gone by +{ahead}d")
                        moved += 1
                        continue
                    gap = math.dist(byday[ahead], now[cid])
                    if gap <= 0.01:
                        held += 1
                    else:
                        moved += 1
                        drift.append(f"{cid} +{ahead}d off by {gap:.2f} AU")
        assert held > 60, held
        # Bodies are arithmetic and must never move; only traffic may.
        assert not [d for d in drift if "body:" in d or "quay:" in d], (
            f"an orbit did not come out where it was predicted: {drift[:3]}")
        rate = held / max(1, held + moved)
        assert rate > 0.9, (
            f"only {rate:.0%} of predictions came true — the forecast is not "
            "worth plotting against")
        return (f"{held} predictions exact after really advancing the sector, "
                f"{moved} moved ({rate:.0%} held)")

    @check("an intercept costs what the flying charges")
    def _():
        # The plot and the helm are the same arithmetic or the board lies.
        # For a body, `track.solve` must *be* `flight.intercept`.
        checked = 0
        # Several chronicles, because one system can hold a single body and
        # the first draft of this passed on a sample of four.
        for seed in range(6):
            game = new_game(f"agree-{seed}")
            for contact in _contacts(game, ("body", "anchorage")):
                for burn in ("coast", "economy", "standard", "hard"):
                    mine = track_sim.solve(game, contact, burn)
                    theirs = flight.intercept(
                        game, game.system.bodies[contact.body_index], burn)
                    assert mine["days"] == theirs["days"], (
                        f"{contact.name} on {burn}: the board says "
                        f"{mine['days']} days and the helm {theirs['days']}")
                    assert mine["fuel"] == theirs["fuel"], (
                        f"{contact.name} on {burn}: {mine['fuel']} against "
                        f"{theirs['fuel']} reaction mass")
                    checked += 1
        assert checked >= 30, checked

        # And a dated rendezvous is priced by the same `_leg`, so a plot that
        # says it can be there by a day either can be or says it cannot.
        game = new_game("agree")
        hulls = _contacts(game, ("hull",))
        assert hulls, "no traffic to plot against"
        wrong = []
        for contact in hulls:
            for share in (0.0, 0.25, 0.6, 1.0):
                day = game.day + 2 + (track_sim.HORIZON - 2) * share
                solved = track_sim.solve(game, contact, "standard", day)
                available = solved["arrive_day"] - game.day
                if solved["feasible"] != (solved["days"] <= available + 1e-6):
                    wrong.append(f"{contact.name} day {day:.0f}")
                _legs, au = flight.route(flight.ship_position(game),
                                         solved["aim"])
                if abs(au - solved["au"]) > 1e-9:
                    wrong.append(f"{contact.name}: {au:.3f} AU against "
                                 f"{solved['au']:.3f} quoted")
        assert not wrong, f"plots disagreeing with the route: {wrong[:4]}"
        return (f"{checked} body intercepts identical to the helm's, "
                f"{len(hulls) * 4} dated plots on the same route")

    @check("waiting is sometimes cheaper than burning")
    def _():
        # Why a dated plot exists at all. If every date cost the same there
        # would be nothing to choose and the slider would be decoration.
        game = new_game("windows")
        spreads = []
        for contact in _contacts(game, ("body", "hull")):
            windows = [w for w in track_sim.windows(game, contact, "standard")
                       if w["feasible"]]
            if len(windows) < 4:
                continue
            costs = [w["fuel"] for w in windows]
            if max(costs) > min(costs):
                spreads.append((contact.name, min(costs), max(costs)))
        assert spreads, (
            "every arrival date costs the same reaction mass for every "
            "contact — plotting against a date buys nothing")
        best = max(spreads, key=lambda s: s[2] - s[1])
        return (f"{len(spreads)} contacts price their dates differently; "
                f"{best[0]} runs {best[1]}–{best[2]} by arrival day")

    @check("a plot against a hull says how far it can be trusted")
    def _():
        # Bodies are arithmetic; hulls hold an errand that the growth can
        # redraw. The panel must not quote both the same way.
        game = new_game("trust")
        body = next(c for c in _contacts(game, ("body",)))
        hull = next(c for c in _contacts(game, ("hull",)))
        assert body.predictable and not hull.predictable

        clean = game.system.bloom
        game.system.bloom = 0.0
        assert track_sim.confidence(game, hull, game.day + 400) == 1.0, (
            "a hull in a clean system is doubted for no reason")
        assert track_sim.confidence(game, body, game.day + 400) == 1.0

        # Growing, and crossing the threshold that redraws the traffic.
        game.system.bloom = 0.13
        near = track_sim.confidence(game, hull, game.day + 400)
        assert near < 1.0, (
            "the growth crosses the threshold that reshuffles this system's "
            "errands before arrival and the plot is still quoted as certain")
        assert track_sim.confidence(game, body, game.day + 400) == 1.0, (
            "an orbit is being doubted because of the Bloom")
        # The thresholds are read from `traffic`, not invented here.
        assert min(track_sim.SHUFFLE_AT) <= 0.15, track_sim.SHUFFLE_AT
        # And it says something usable. The tripwire found this only pinned
        # as "below 1", so the figure could be set to anything at all: a plot
        # across a reshuffle is doubted, not worthless — the hull is very
        # likely still on the same leg — and it must not read as near-certain.
        assert 0.15 < near < 0.75, (
            f"a plot across a threshold crossing is quoted at {near:.0%}, "
            "which is either near-certain or not worth drawing")
        game.system.bloom = clean
        return (f"a hull reads {near:.0%} across a threshold crossing and "
                "100% below one; an orbit is never doubted")

    @check("a burn with no mass left is refused, and the panel says so")
    def _():
        # The gate against its act, the sweep this project runs on every
        # `can_*`. An empty tank must not silently move the ship.
        game = new_game("dry")
        contact = next(c for c in _contacts(game, ("hull",)))
        conn = conn_sim.start(game, contact)
        conn.rcs = 0.0
        ok, why = conn_sim.can_burn(conn, main=False)
        assert not ok and why, (ok, why)
        before = list(conn.vel)
        conn_sim.apply(conn, "forward")
        assert conn.vel == before, (
            "the thrusters fired on an empty tank")
        assert conn.elapsed > 0, (
            "a dry ship cannot even coast — which is the one thing it must "
            "still be able to do")

        # And enough for a pulse but not a main burn. On a *fresh* conn: an
        # approach with nothing left to burn and nothing still happening now
        # ends as `dry` (see `outcome.resolve`), and asking a finished approach
        # whether it can burn gets "the approach is finished" — which is true,
        # and not what this half of the check is about.
        conn = conn_sim.start(game, contact)
        conn.rcs = conn_sim.RCS_COST
        assert conn_sim.can_burn(conn, main=False)[0]
        assert not conn_sim.can_burn(conn, main=True)[0], (
            "the main drive fires on a thruster's worth of mass")
        return "dry refuses and still coasts; a pulse's worth is not a burn"

    @check("the panel does not cry wolf at a good approach")
    def _():
        # Every row was judged against berthing, so a ship correctly
        # established in a 360 km orbit at 5,728 m/s had both its range and
        # its speed marked in red — the two numbers it had just got right.
        # A panel that warns about success teaches the pilot to ignore it.
        game = new_game("panel")
        shouting = []
        for contact in _contacts(game):
            mode = "orbit" if contact.kind == "body" else "close"
            conn = conn_sim.start(game, contact)
            pilot_sim.fly(conn, mode, 1500)
            assert conn.outcome in ("orbit", "alongside"), conn.outcome
            for name, value, kind in conn_sim.readout(conn):
                if kind in ("warn", "bad"):
                    shouting.append(
                        f"{contact.name} ({conn.outcome}): {name} reads "
                        f"{value} and is marked {kind}")
        assert not shouting, (
            f"{len(shouting)} row(s) warning about an approach that "
            f"succeeded: {shouting[:4]}")

        # And it still warns when there is something to warn about.
        contact = next(c for c in _contacts(game, ("anchorage", "hull")))
        hot = conn_sim.start(game, contact)
        hot.vel = [0.0, conn_sim.SAFE_CLOSING * 4, 0.0]
        marks = [k for _n, _v, k in conn_sim.readout(hot)]
        assert "bad" in marks, (
            f"closing at {hot.closing:,.0f} m/s and the panel is calm: "
            f"{conn_sim.readout(hot)}")
        return ("every successful approach reads clean; a four-times-limit "
                "closing rate still reads bad")

    @check("a forecast never writes to the chronicle")
    def _():
        # `track` asks `traffic` about future days through a stand-in game.
        # If that stand-in could reach `game.rng()` — which advances the save
        # — then merely looking at the plotting board would alter the run.
        game = new_game("readonly")
        contact = next(c for c in _contacts(game, ("hull",)))
        before = (game.day, game.seed, len(game.log) if
                  hasattr(game, "log") else 0)
        for ahead in range(0, 200, 7):
            track_sim.at(game, contact, game.day + ahead)
        track_sim.history(game, contact)
        track_sim.forecast(game, contact)
        track_sim.windows(game, contact, "standard")
        after = (game.day, game.seed, len(game.log) if
                 hasattr(game, "log") else 0)
        assert before == after, (
            f"asking about the future changed the chronicle: {before} → "
            f"{after}")

        shifted = track_sim._AsOf(game, game.day + 50)
        assert shifted.day == game.day + 50
        try:
            shifted.rng("anything")
        except AttributeError:
            pass
        else:
            raise AssertionError(
                "a forecast can draw on the chronicle's luck, which would "
                "reshuffle the save every time the board was opened")
        return "thirty forecasts, the chronicle untouched, and the door shut"
