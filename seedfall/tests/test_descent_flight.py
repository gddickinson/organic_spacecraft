"""Flying her down: the descent as a flight rather than a fee.

A player looked at a game with a cockpit in it, a lander on the cradle and a
map of a world's surface, and asked the one question none of it answered:

    How does the player pilot a ship down to the surface of a planet?

They could not. `sim/fieldwork.launch_expedition` spent three days and the
party was on the ground; the cockpit flew sorties in open space and had no
control that pointed at a world. `sim/descent_flight.py` is the answer, and
these are its claims.

- **It is the flight model already written.** A conn on the world, fitted
  with the craft's own numbers, flown by `sim/craft.beat` — the same beat
  the fighter's sortie uses.
- **The de-orbit is spent before the cockpit opens**, and paid for out of
  her tank. Flying it against a sixty-second tick is what made every rocky
  world unlandable.
- **She is judged at a gate**, three ticks of the world's own gravity above
  the surface, because below that this clock has nothing to say: the drive
  is an impulse at the top of a minute and the world owns the other
  fifty-nine seconds.
- **Flown, she lands. Not flown, she does not.** The computer's own descent
  law puts her down on every world a lander may go down on; letting her
  fall wrecks her on the worlds worth walking on.
- **A landing is the landing the rest of the game already has** — the same
  party, supplies, vehicle, camp and zone `launch_expedition` builds — and
  it does not charge the three days a second time.
- **A crash costs.** Her hull, and everybody who rode her down.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import craft as craft_sim
from ..sim import descent as descent_sim
from ..sim import descent_flight, flight, landing
from ..world.planets import BODY_KINDS
from .harness import Suite


def _worlds(game) -> list:
    return [(i, b) for i, b in enumerate(game.system.bodies)
            if BODY_KINDS[b.kind][2]]


def _ready(seed: str, want=None):
    """A chronicle in orbit of something a lander may go down on."""
    for n in range(14):
        game = new_game(f"{seed}-{n}")
        game.ship.cargo["biomass"] = 400
        for index, body in _worlds(game):
            if want is not None and not want(body):
                continue
            body.surveyed = True
            flight.hold_at(game, body)
            if descent_sim.best(game, body) is not None:
                return game, index, body
    raise AssertionError(f"nothing to land on in fourteen sectors ({seed})")


def _fly(game, index, body, arm: str = "down", most: int = 3000,
         party=()) -> dict:
    """Begin a descent and beat it to its end. Returns the arrival."""
    craft = descent_sim.best(game, body)
    got = descent_flight.begin(game, craft, index, cell=(5, 5), load=0,
                               officer_ids=party)
    assert got["ok"], got
    got["conn"].auto = arm
    for _ in range(most):
        beat = craft_sim.beat(game)
        if not beat.get("ok") or beat.get("arrival") is not None:
            return beat.get("arrival") or {"ok": False, "beat": beat}
    return {"ok": False, "why": "never arrived"}


def run(suite: Suite) -> None:
    check = suite.check

    @check("the descent is a flight, on the world, with the craft's own numbers")
    def _():
        game, index, body = _ready("flight")
        craft = descent_sim.best(game, body)
        kind = craft_sim.kind_of(craft)
        got = descent_flight.begin(game, craft, index, cell=(3, 4), load=1,
                                   officer_ids=[o.id for o in game.officers[:1]])
        assert got["ok"], got
        conn = got["conn"]
        assert craft_sim.sortie(game) is conn, "the cockpit flies it"
        assert craft_sim.flying(game) is craft, craft.state
        assert conn.target.kind == "body", conn.target.kind
        assert abs(conn.mass_t - kind.mass_t) < 1e-6, conn.mass_t
        assert landing.can_hold(conn), "the drive cannot hold this world"
        plan = descent_flight.under_way(game)
        assert plan.cell == (3, 4) and plan.body_index == index, plan
        assert craft.pilot and craft.pilot != "captain", (
            "the captain does not fly the lander off her own bridge")
        return (f"{craft.name} flying {conn.target.name} at "
                f"{conn.mass_t:,.0f} t, {descent_flight.height_km(conn):,.0f} "
                f"km up, judged at {descent_flight.gate_km(conn):,.1f} km")

    @check("the de-orbit is spent before the cockpit opens, and paid for")
    def _():
        game, index, body = _ready("deorbit", lambda b: b.gravity > 0.3)
        craft = descent_sim.best(game, body)
        before = craft.fuel
        conn = descent_flight.begin(game, craft, index)["conn"]
        # Falling, not going round: what is left is the drift, and every
        # bit of it is down the radius.
        assert conn.speed <= descent_flight.OPEN_DRIFT * 1.2, conn.speed
        assert craft.fuel < before, "the burn was free"
        # And it is a real burn, not a dispensation.
        assert before - craft.fuel > 0.1, before - craft.fuel
        return (f"{body.name} at {body.gravity:.2f} g: cast off falling at "
                f"{conn.speed:,.0f} m/s for {before - craft.fuel:.2f} t of "
                "her tank")

    @check("flown by her own law she lands, on every world she may land on")
    def _():
        rows, down = [], 0
        for n in range(6):
            game, index, body = _ready(f"flown-{n}")
            got = _fly(game, index, body)
            rows.append((body.name, body.gravity, got))
            down += 1 if got.get("down") else 0
        assert len(rows) >= 6, len(rows)
        assert down == len(rows), [r for r in rows if not r[2].get("down")]
        worst = max(rows, key=lambda r: r[1])
        return (f"{down} of {len(rows)} descents put her on her legs, "
                f"the heaviest {worst[0]} at {worst[1]:.2f} g")

    @check("let her fall and she is a wreck on the worlds worth walking on")
    def _():
        rows = []
        for n in range(8):
            game, index, body = _ready(f"fell-{n}", lambda b: b.gravity > 0.3)
            rows.append((body.gravity, _fly(game, index, body, arm="")))
        bad = [r for r in rows if not r[1].get("down")]
        assert len(rows) >= 6, len(rows)
        assert len(bad) >= len(rows) * 0.6, (
            f"only {len(bad)} of {len(rows)} hands-off descents went wrong")
        assert any(r[1].get("lost") for r in rows), (
            "nothing was ever lost falling into a planet")
        return (f"{len(bad)} of {len(rows)} hands-off descents ended badly, "
                f"{sum(1 for r in rows if r[1].get('lost'))} of them with "
                "nothing left of her")

    @check("a landing is the landing the rest of the game already builds")
    def _():
        game, index, body = _ready("party")
        party = [o.id for o in game.officers[:2]]
        day, biomass = game.day, game.ship.cargo.get("biomass", 0)
        got = _fly(game, index, body, party=party)
        assert got.get("down") and got.get("party"), got
        exp = game.expedition
        assert exp is not None and not exp.over, exp
        assert exp.cell == (5, 5), exp.cell
        assert exp.tiles, "no ground to walk"
        craft = descent_sim.on_the_ground(game)
        assert craft is not None and exp.craft == craft.id, exp.craft
        assert game.ship.cargo.get("biomass", 0) < biomass, "supplies were free"
        # The minutes of the flight, and not a day more: the three days an
        # order to an officer costs are not charged to a captain who flew it.
        assert game.day - day < 1.0, game.day - day
        assert craft_sim.sortie(game) is None, "the flight is over"
        assert descent_flight.under_way(game) is None
        return (f"party of {len(party)} down at {exp.cell} on "
                f"{len(exp.tiles)} tiles of ground, {game.day - day:.2f} "
                "days of calendar against the three an order costs")

    @check("a crash costs her hull and everybody who rode her down")
    def _():
        for n in range(10):
            game, index, body = _ready(f"crash-{n}", lambda b: b.gravity > 0.5)
            party = [o.id for o in game.officers[:2]]
            craft = descent_sim.best(game, body)
            hull = craft.hp
            got = _fly(game, index, body, arm="", party=party)
            if got.get("down"):
                continue
            assert game.expedition is None or game.expedition.over, (
                "a party is walking about after a crash")
            hurt = getattr(game, "wounds", None) or {}
            assert hurt, "nobody was hurt putting a lander into a planet"
            for who in party:
                assert hurt.get(str(who), 0) > 0, (who, hurt)
            if got.get("lost"):
                assert craft.state == "lost" and craft.hp == 0, craft
            else:
                assert craft.hp < hull, (craft.hp, hull)
            return (f"{body.name} at {body.gravity:.2f} g: "
                    + (f"nothing left of {craft.name}" if got.get("lost")
                       else f"{got['harm']} off her hull")
                    + f", and {len(hurt)} aboard hurt")
        raise AssertionError("ten hands-off descents and not one crash")

    @check("the gate is thick enough that a tick cannot step over it")
    def _():
        rows = []
        for n in range(6):
            game, index, body = _ready(f"gate-{n}")
            craft = descent_sim.best(game, body)
            conn = descent_flight.begin(game, craft, index)["conn"]
            pull = landing.surface_g(conn.target)
            fell = pull * 60.0 * 60.0 / 2.0 / 1000.0        # one tick, km
            gate = descent_flight.gate_km(conn)
            assert gate >= min(descent_flight.GATE_LEAST_KM, fell), (gate, fell)
            assert gate >= fell * (descent_flight.GATE_FALL - 0.01) or \
                gate == descent_flight.GATE_LEAST_KM, (gate, fell)
            # And the drive can always take off what a gate crossing leaves.
            assert descent_flight.catch_rate(conn) > pull * 60.0, (
                f"{body.name}: the drive takes "
                f"{descent_flight.catch_rate(conn):,.0f} and a tick of "
                f"falling is {pull * 60.0:,.0f}")
            rows.append((body.name, gate, fell))
        assert len(rows) >= 6, len(rows)
        return (f"{len(rows)} worlds, gates from {min(r[1] for r in rows):,.1f} "
                f"to {max(r[1] for r in rows):,.1f} km, every one of them at "
                "least three ticks of its own gravity")

    @check("nothing goes down that has no business going down")
    def _():
        game, index, body = _ready("refuse")
        craft = descent_sim.best(game, body)
        # Not in orbit of it.
        flight.stand_off(game)
        ok, why = descent_flight.can_fly(game, craft, body)
        assert not ok and "orbit" in why.lower(), why
        flight.hold_at(game, body)
        # Mid-engagement.
        game.battle = object()
        assert not descent_flight.can_fly(game, craft, body)[0]
        game.battle = None
        # One at a time.
        assert descent_flight.begin(game, craft, index)["ok"]
        again = descent_flight.begin(game, craft, index)
        assert not again["ok"], again
        # And a hull is not a lander: nothing on a gas giant, ever.
        gas = next((b for b in game.system.bodies
                    if not BODY_KINDS[b.kind][2]), None)
        if gas is not None:
            assert not descent_sim.can_land(game, craft, gas)[0]
        return ("refused out of orbit, refused mid-engagement, refused "
                "twice over, and refused anywhere there is nothing to "
                "stand on")
