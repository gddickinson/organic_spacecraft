"""What a finished approach costs, and what it buys.

`test_conn.py` holds the flying. This holds the consequences — and it exists
because for a whole cycle there were none. Measured on a fresh chronicle
before `sim/berthing.py`:

    flew into Fleet Hub at 20 m/s  ->  collision, damage 50.0
    berthed alongside              ->  0.54 t of reaction mass, 0.8 h elapsed

    day    0     -> 0        same
    fuel   20    -> 20       same
    hull   336   -> 336      same
    where  None  -> None     same

Every number the conn produced was thrown away. You could wreck the ship
against a station and walk off unharmed, berth alongside a quay and not be
docked, and spend reaction mass out of a tank the hull never had — the conn
invented 36.8 t for a ship carrying 20.

Two faults surfaced while wiring it up, both from playing:

* **Impact damage was linear and capped**, so putting the hull down on a
  world at five kilometres a second cost sixty points of three hundred and
  thirty-six. Energy goes as the square of the speed; so does the damage now,
  uncapped, and a bad enough approach ends the chronicle.
* **A fast approach passed straight through its target.** At 45 m/s the ship
  covered 2.7 km in one 60 s tick and crossed a station 400 m wide between
  two contact tests — reported **adrift**, no damage. Since the damage curve
  is quadratic, the most dangerous approaches were exactly the ones escaping.
  Contact is swept along the whole path now, not sampled at the endpoints.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..sim import autopilot as pilot_sim
from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from ..sim import track as track_sim
from .harness import Suite


def _contacts(game, kinds=("body", "anchorage", "hull")):
    return [c for c in track_sim.contacts(game) if c.kind in kinds]


def run(suite: Suite) -> None:
    check = suite.check

    @check("everything the conn spends and wins lands on the chronicle")
    def _():
        # The general one, and the fault it was written for. Before this,
        # measured on a fresh chronicle: flying into a station at 20 m/s
        # reported 50 damage and left the hull at 336; berthing alongside
        # left you not docked; 0.54 t of reaction mass came out of a tank the
        # ship did not have. Every one of those was thrown away.
        game = new_game("lands")
        game.orbit_body = game.system.bodies[0].id
        quay = next(c for c in _contacts(game, ("anchorage",)))
        before = (game.ship.cargo.get("volatiles", 0),
                  sum(layer.hp for layer in game.ship.layers))
        conn, why = berth_sim.begin(game, quay)
        assert conn is not None, why
        assert conn.rcs == before[0], (
            f"the conn opened with {conn.rcs} t and the ship carries "
            f"{before[0]} t — the tank is an invention")
        pilot_sim.fly(conn, "close", 1200)
        assert conn.outcome == "alongside", conn.outcome
        out = berth_sim.commit(game, conn)
        assert out["fuel"] > 0, "an approach that burned nothing"
        assert game.ship.cargo["volatiles"] == before[0] - out["fuel"], (
            f"spent {out['fuel']} t and the hold went "
            f"{before[0]} → {game.ship.cargo['volatiles']}")
        assert game._part_day > 0 or game.day > 0, (
            "the approach took hours and no time passed")
        assert berth_sim.commit(game, conn)["already"], (
            "committing twice charges twice")
        return (f"{out['fuel']:.2f} t off the hold, {out['hours']:.1f} hours "
                "on the clock, and the second commit is a no-op")

    @check("a berth is a place the rest of the game agrees with")
    def _():
        # `orbit_body` is what every other screen reads to know where the
        # hull is standing, so coming alongside has to write it — otherwise
        # you berth at a quay and the port screen says you are nowhere.
        from ..sim import anchorage as anchorage_sim
        game = new_game("berthed")
        game.orbit_body = None
        quay = next(c for c in _contacts(game, ("anchorage",)))
        assert anchorage_sim.docked_at(game) is None
        conn = conn_sim.start(game, quay)
        pilot_sim.fly(conn, "close", 1200)
        berth_sim.commit(game, conn)
        moored = anchorage_sim.docked_at(game)
        assert moored is not None and moored.name == quay.name, (
            f"came alongside {quay.name} and the game says the hull is at "
            f"{moored.name if moored else 'nowhere'}")
        assert "alongside" in anchorage_sim.where_am_i(game).lower()

        # And an approach that never arrived does not move the ship.
        game2 = new_game("berthed")
        game2.orbit_body = None
        adrift = conn_sim.start(game2, quay)
        adrift.outcome = "adrift"
        berth_sim.commit(game2, adrift)
        assert game2.orbit_body is None, (
            "losing the approach still put the hull alongside")
        return f"alongside {moored.name}, and a lost approach moves nothing"

    @check("the conn is refused on anything the ship is not already near")
    def _():
        # The gate. Measured, the distances are bimodal — a contact at your
        # body reads 0.000 AU and everything else reads 2.2 AU or more — so
        # this holds the *rule*, not the threshold.
        game = new_game("gate")
        game.orbit_body = game.system.bodies[0].id
        near = far = 0
        for contact in _contacts(game):
            away = berth_sim.reach_to(game, contact)
            ok, why = berth_sim.can_conn(game, contact)
            if away <= berth_sim.REACH_KM:
                near += 1
                assert ok, f"{contact.name} is alongside and refused: {why}"
            else:
                far += 1
                assert not ok, (
                    f"{contact.name} is {away / berth_sim.KM_PER_AU:.2f} AU "
                    "off and the conn opened on it anyway")
                assert "AU" in why and "transfer" in why, (
                    f"the refusal does not say what to do instead: {why!r}")
                assert berth_sim.begin(game, contact)[0] is None, (
                    "the gate says no and `begin` handed back an approach")
        assert near >= 2 and far >= 3, (near, far)

        # A dry tank is the other door.
        game.ship.cargo["volatiles"] = 0
        here = next(c for c in _contacts(game)
                    if berth_sim.reach_to(game, c) <= berth_sim.REACH_KM)
        ok, why = berth_sim.can_conn(game, here)
        assert not ok and "reaction mass" in why, (ok, why)
        return (f"{near} contacts in reach and openable, {far} refused with "
                "the burn they would need")

    @check("an impact is paid for in proportion to the speed")
    def _():
        # Damage was linear and capped at 80, so lithobraking into a world at
        # five kilometres a second cost less than a bad week in the Bloom.
        # Energy goes as the square of the speed, and so does this now.
        game0 = new_game("impact")
        hull = sum(layer.hp for layer in game0.ship.layers)
        seen = []
        for speed in (8.0, 20.0, 45.0):
            game = new_game("impact")
            game.orbit_body = game.system.bodies[0].id
            quay = next(c for c in _contacts(game, ("anchorage",)))
            conn, _why = berth_sim.begin(game, quay)
            conn.pos, conn.vel = [0.0, -1.0, 0.0], [0.0, speed, 0.0]
            while not conn.over:
                conn_sim.apply(conn, None)
            assert conn.outcome == "collision", (
                f"{speed:g} m/s into a station and the outcome is "
                f"{conn.outcome!r}")
            out = berth_sim.commit(game, conn)
            left = sum(layer.hp for layer in game.ship.layers)
            seen.append((speed, conn.damage, left, out["lost"], game.dead))

        assert seen[1][1] > seen[0][1] * 3, (
            f"twice the speed did {seen[1][1]} against {seen[0][1]} — that is "
            "not a square law")
        assert seen[0][2] > 0 and not seen[0][3], "a scrape wrote the ship off"
        assert seen[-1][3] and seen[-1][4], (
            f"{seen[-1][0]:g} m/s into a station left "
            f"{seen[-1][2]:.0f} of {hull:.0f} hull and the chronicle running")
        return " · ".join(f"{v:g} m/s → {d:,.0f} dmg" for v, d, _l, _x, _y in seen)

    @check("a fast approach cannot pass straight through the target")
    def _():
        # Found by playing the impact curve: at 45 m/s the ship covered 2.7 km
        # in one 60 s tick, passed clean through a station 400 m across, and
        # was reported **adrift** — no contact, no damage, hull untouched.
        # Since impact damage is quadratic, the fastest and most dangerous
        # approaches were precisely the ones getting away with it.
        game = new_game("tunnel")
        game.orbit_body = game.system.bodies[0].id
        quay = next(c for c in _contacts(game, ("anchorage",)))
        missed = []
        for speed in (30.0, 45.0, 120.0, 600.0, 3000.0):
            conn = conn_sim.start(game, quay)
            conn.pos, conn.vel = [0.0, -2.0, 0.0], [0.0, speed, 0.0]
            for _ in range(400):
                if conn.over:
                    break
                conn_sim.apply(conn, None)
            crossed = speed * conn_sim.TICK / 1000.0
            if conn.outcome != "collision":
                missed.append(
                    f"{speed:g} m/s (covering {crossed:.1f} km a tick against "
                    f"a {quay.name} {conn.target.radius_km * 2000:.0f} m "
                    f"across) → {conn.outcome!r}")
        assert not missed, (
            f"{len(missed)} approach(es) went through the target without "
            f"touching it: {missed}")
        return ("aimed dead at a station from 30 to 3,000 m/s, every one "
                "registered as a strike")

    @check("arriving fast is a collision, arriving slow is a berth")
    def _():
        # The rule that makes the whole mini-game a decision. Measured by
        # flying in at a spread of speeds rather than read off the constant.
        game = new_game("impact")
        contact = next(c for c in _contacts(game, ("anchorage",)))

        def flown(speed: float):
            """One arrival at `speed`, **down the berth's own line**.

            A ship arrives at a berth. This used to fly straight at the middle
            of the structure from wherever `start` put it, which since berths
            became places on the structure lands on the skin somewhere between
            the fittings — a scrape, correctly, and not the berthing this
            check is about. `sim/moorings.py` says where the fitting is; the
            approach opens a kilometre out along that line.
            """
            from ..sim import moorings
            conn = conn_sim.start(game, contact, range_km=1.0, drift=0.0)
            berth = moorings.nearest(conn)
            if berth is not None:
                out = math.dist(berth["at"], (0.0, 0.0, 0.0)) or 1.0
                conn.pos = [c * (out + 1.0) / out for c in berth["at"]]
                here = math.dist(conn.pos, (0.0, 0.0, 0.0)) or 1.0
                conn.vel = [-c / here * speed for c in conn.pos]
            else:
                conn.vel = [0.0, speed, 0.0]
            for _ in range(400):
                if conn.over:
                    break
                conn_sim.apply(conn, None)
            return conn

        table = []
        for speed in (0.5, 1.0, 2.0, 6.0, 20.0):
            conn = flown(speed)
            table.append((speed, conn.outcome, conn.damage))
        # A berth means alongside. The tripwire found nothing pinning how
        # near "near enough" is, so it could be set to five kilometres and
        # every check still passed — measured against the hull, not the
        # constant, because reading the constant here proves nothing.
        gentle = flown(1.0)
        assert gentle.outcome == "alongside", gentle.outcome
        gap = gentle.range_km - gentle.target.radius_km
        assert gap < 0.4, (
            f"the ship is called alongside with {gap * 1000:,.0f} m between "
            "it and the station's hull, which is not a berth")

        slow = [row for row in table if row[0] <= conn_sim.ALONGSIDE_RATE]
        fast = [row for row in table if row[0] > conn_sim.SAFE_CLOSING]
        assert slow and fast, table
        assert all(row[1] == "alongside" for row in slow), (
            f"a gentle arrival is not a berth: {slow}")
        assert all(row[1] == "collision" for row in fast), (
            f"arriving hard is not being punished: {fast}")
        assert all(row[2] > 0 for row in fast), (
            "a collision costs nothing, so there is no reason to slow down")
        assert fast[-1][2] > fast[0][2], (
            "hitting harder does no more damage than hitting softly")
        return " · ".join(f"{s:g} m/s → {o}" for s, o, _d in table)
