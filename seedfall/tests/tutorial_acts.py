"""How to actually *do* each lesson, for the walk in `test_tutorial.py`.

Split out of it when that file passed five hundred lines. The seam is the
right one: this module knows how a captain performs an act, and the suite
next door makes claims about the curriculum. When a lesson is added and its
watcher is not taught here, the walk fails with the watcher's name — which is
the point, because a lesson nothing knows how to do is a lesson nobody can
finish.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game  # noqa: F401 - kept for parity with callers
from ..sim import contracts as contract_sim
from ..sim import market as market_sim
from ..sim import trade as trade_sim
from ..sim import tutorial as tutorial_sim
from ..sim.actions import survey


def _do(game, watch: str) -> None:
    """Actually perform the thing lesson `watch` is waiting for."""
    if watch == "surveyed_one":
        # The starting system can be as small as two bodies, so find one
        # that is still unsurveyed rather than assuming there is one here.
        index = next((i for i, b in enumerate(game.system.bodies)
                      if not b.surveyed), None)
        if index is None:
            elsewhere = next(s for s in game.galaxy.systems
                             if any(not b.surveyed for b in s.bodies))
            game.location_id = elsewhere.id
            index = next(i for i, b in enumerate(elsewhere.bodies)
                         if not b.surveyed)
        survey(game, index)
    elif watch == "saw_market":
        market_sim.note_prices(game, game.system, 0, 0)
    elif watch == "sold_something":
        # Sell what is already aboard. Adding cargo and then selling it puts
        # the hold back where the mark was, so the watcher — which wants
        # credits up *and* the hold lighter — correctly saw nothing.
        held = next((c for c, t in game.ship.cargo.items()
                     if c != "volatiles" and t > 0), None)
        assert held, "nothing aboard to sell"
        trade_sim.sell(game, held, game.ship.cargo[held])
    elif watch == "bought_fuel":
        trade_sim.buy(game, "volatiles", 10)
    elif watch.startswith("saw_") and watch != "saw_market":
        # "open this screen" lessons: the screen is the watcher's own name.
        tutorial_sim.saw(game, {"saw_manual": "help",
                                "saw_plans": "ship:plans"}.get(
                                    watch, watch[4:]))
    elif watch == "computer_flew":
        from ..sim import flightdeck as deck_sim, freeflight
        conn, _why = freeflight.begin(game)
        conn.auto = "null"
        deck_sim.computer(game, conn)
    elif watch == "berthed":            # standing at a quay: derived state
        from ..sim import anchorage as anchorage_sim
        places = anchorage_sim.in_system(game)
        assert places, "no quay in this system to berth at"
        game.orbit_body = game.system.bodies[places[0].body_index].id
    elif watch == "set_project":
        from ..data import tech as tech_data
        from ..sim import research as research_sim
        game.research.points = 4000
        opts = tech_data.researchable(game.research.unlocked)
        research_sim.set_project(game.research, opts[0].id)
    elif watch == "unlocked_tech":
        from ..data import tech as tech_data
        game.research.unlocked.append(
            tech_data.researchable(game.research.unlocked)[0].id)  # one more
    elif watch == "jumped":
        seen = list(game.discovered.get("systems", ()))
        game.discovered.setdefault("systems", []).append(
            next(s.id for s in game.galaxy.systems if s.id not in seen))
    elif watch in ("mined", "dug", "landed", "fought", "stood_watch"):
        from ..sim import tutorial_watch
        tutorial_watch.deed(game, watch)
    elif watch == "marked_hostile":
        from ..sim import hostiles as h_sim
        h_sim.mark(game, "a-hull")
    elif watch == "planted":
        from ..sim.colony import Colony
        game.colonies.append(Colony(
            id=len(game.colonies) + 1, class_id="radix_mine", name="Taught",
            system_id=game.system.id, body_id=game.system.bodies[0].id,
            need=0, online=True))   # the watcher is a count; this is one
    elif watch == "courted":
        from ..data.factions import FACTIONS as F
        game.rep[F[0].id] = game.rep.get(F[0].id, 0) + 5
    elif watch == "refitted":
        game.ship.fitted.append(game.ship.fitted[0] if game.ship.fitted else "hold")
    elif watch == "flew_conn":
        from ..sim import berthing as berth_sim
        from ..sim import conn as conn_sim
        from ..sim import freeflight
        conn, why = freeflight.begin(game)
        assert conn is not None, why
        game.conn = conn
        for _ in range(6):
            conn_sim.apply(conn, "forward", ticks=1)
        berth_sim.charge_flown(game, conn)
        berth_sim.commit(game, conn)
        game.conn = None
    elif watch == "took_the_guard_off":
        # Through the sim door the buttons use, so the walk fails if the
        # switch stops recording the deed — which is the whole claim.
        from ..sim import collision
        from ..sim import freeflight
        conn, why = freeflight.begin(game)
        assert conn is not None, why
        collision.toggle_safeties(game, conn)
        collision.toggle_safeties(game, conn)
        assert conn.safeties, "the switch did not come back on"
    elif watch == "moved":
        game.orbit_body = "1"
    elif watch == "took_contract":
        offered = contract_sim.generate(RNG("tut"), game, game.system)
        contract_sim.accept(game, offered[0])
    else:
        raise AssertionError(f"the check does not know how to do {watch!r}")
