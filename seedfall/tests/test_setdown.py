"""Coming down on a world: three endings where the game had one.

Not `test_landing`, which is about what the lander lifts home from the ground.
This is the ship itself meeting a surface.

Measured before `sim/landing.py` existed, by flying the gentlest touchdown the
sim can produce:

    The hull is down on Sable's Verge II at 17 m/s. That was not a landing.

The branch that said so had **no speed test at all**. Every contact with a
body, at any rate, was `aground` with quadratic damage — so a perfect descent
and a ballistic arrival were the same event, and there was no way to land.

The obvious fix is a rate threshold, and measuring says the obvious fix would
have been a lie. A rocky world pulls 10.371 m/s²; the ship this game starts you
with holds 0.071. **It cannot land on a world and never could** — which is why
`sim/expedition.py` sends a party down in a lander, a decision the code made
long ago and never wrote down.

So the claims here are about naming what is really there:

- **The gravity decides, not a rule.** One door: `surface_g` against
  `drive_g`, both read off numbers the tick loop is already flying with.
- **Setting down is real, rare, and never on a world** — eighteen bodies
  across six sectors, every one an asteroid or a comet.
- **Ditching is the way onto a world, and it is a wreck you walk away from.**
  It is an *order*: a hull that merely flew badly stays `aground`.
- **The quote and the bill are the same curve**, through `outcome.impact_at`.
- **You cannot force a landing on a world, and the number says why.** Ditching
  a rocky world costs 70,972 against a 336-point hull; ditching an asteroid
  costs 67 and she flies again. That is the honest answer to "or force a
  landing on the planet": the order can be given anywhere, and where it is
  fatal it is fatal because of the arithmetic and not because of a rule.
- **A landing is a single-tick event.** The tick is a minute and the rate is
  4 m/s, so the whole landing budget is sixty-eight seconds of freefall on the
  softest body in the sector. Let go from 84 m a hull arrives at 7.16 and
  wrecks; from 34 m it arrives at 3.61 and is down.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import berthing
from ..sim import conn as conn_sim
from ..sim import landing
from ..sim import outcome as outcome_sim
from ..sim import preview
from ..sim import targets as targets_sim
from .harness import Suite

SEEDS = ("a", "b", "c", "d", "e", "f")


def _soft_body():
    """A game and a body this hull's drive can actually hold itself off."""
    for seed in SEEDS:
        game = new_game(seed)
        for system in game.galaxy.systems[:14]:
            for body in getattr(system, "bodies", []):
                target = targets_sim.target_from_body(body, body.name, 1)
                if target.mu <= 0 or not landing.kind_allows(target):
                    continue
                if landing.can_hold(conn_sim.start(game, target)):
                    return game, body, target
    raise AssertionError("nothing in six sectors is soft enough to land on")


def _rocky(seed):
    """A game and a real world in it — not every home system has one."""
    for tag in (seed, seed + "-b", seed + "-c", seed + "-d", seed + "-e"):
        game = new_game(tag)
        for body in game.system.bodies:
            if body.kind in ("rocky", "ocean", "ice"):
                return game, body, targets_sim.target_from_body(
                    body, body.name, 1)
    raise AssertionError(f"no world in five sectors from {seed!r}")


def _drop(game, target, speed, ditch=False, high=1.0005):
    """Put the hull just off the surface and let it come down."""
    conn = conn_sim.start(game, target)
    conn.pos = [target.radius_km * high, 0.0, 0.0]
    conn.vel = [-abs(speed), 0.0, 0.0]
    if ditch:
        landing.ditch(conn)
    for _ in range(600):
        conn_sim.apply(conn, None, ticks=1)
        if conn.over:
            break
    return conn


def run(suite: Suite) -> None:
    check = suite.check

    @check("the gravity decides, and it is read off the flying")
    def _():
        game, rocky, target = _rocky("land")
        conn = conn_sim.start(game, target)
        pull, push = landing.surface_g(target), landing.drive_g(conn)
        assert pull > push * 10, (
            f"a rocky world pulls {pull:.3f} against a drive holding "
            f"{push:.3f}, which is not the impossibility this is built on")
        assert not landing.can_hold(conn)
        told = landing.why_not(conn)
        assert f"{pull:.2f}" in told and f"{push:.2f}" in told, told
        # And the figure is the tick loop's own, not a second one.
        assert abs(target.mu / target.radius_km ** 2 * 1000.0 - pull) < 1e-9
        return told

    @check("setting down is real, rare, and never on a world")
    def _():
        found, kinds = [], set()
        for seed in SEEDS:
            game = new_game(seed)
            for system in game.galaxy.systems[:14]:
                for body in getattr(system, "bodies", []):
                    target = targets_sim.target_from_body(body, body.name, 1)
                    if target.mu <= 0 or not landing.kind_allows(target):
                        continue
                    if landing.can_hold(conn_sim.start(game, target)):
                        found.append(body.name)
                        kinds.add(body.kind)
        assert found, "nowhere in six sectors can the ship be set down"
        worlds = kinds & {"rocky", "ocean", "ice", "moon"}
        assert not worlds, (
            f"the ship can be set down on {sorted(worlds)}, which would make "
            "the lander — and the whole expedition system — pointless")
        return (f"{len(found)} bodies across six sectors, all "
                f"{'/'.join(sorted(kinds))} and not one a world — "
                f"e.g. {found[0]}")

    @check("a gentle arrival is a landing, and it costs nothing")
    def _():
        game, body, target = _soft_body()
        # **A landing is a single-tick event, and the tick is a minute.**
        # Measured on the softest body in the sector: one tick of freefall
        # costs 3.5 m/s of the 4.0 the rate allows, so a hull let go from 84 m
        # takes two ticks and arrives at 7.16 — a wreck — while the same hull
        # let go from 34 m arrives at 3.61 and is down. That is the whole
        # landing budget: sixty-eight seconds of falling. Anything that is to
        # be flown down has to be flown down to the last thirty metres.
        conn = _drop(game, target, 0.05, high=1.0002)
        assert conn.outcome == "down", (
            f"set down on {body.name} at {conn.speed:.2f} m/s and it came "
            f"away {conn.outcome!r}: {conn.log[-1]}")
        assert conn.damage == 0.0, f"a landing cost {conn.damage}"
        assert conn.speed <= landing.SET_DOWN, conn.speed
        return f"{body.name}: {conn.log[-1]}"

    @check("ditching is an order, and flying badly is not one")
    def _():
        game, body, target = _soft_body()
        # The same descent twice, differing only in whether it was chosen.
        fell = _drop(game, target, 30.0)
        assert fell.outcome == "aground", fell.outcome
        chose = _drop(game, target, 30.0, ditch=True)
        assert chose.outcome == "ditched", chose.outcome
        assert chose.damage < fell.damage, (
            f"flying her in cost {chose.damage:,.0f} and falling cost "
            f"{fell.damage:,.0f} — choosing it bought nothing")
        return (f"{body.name}: fell {fell.damage:,.0f} · flew her in "
                f"{chose.damage:,.0f}")

    @check("you cannot force a landing on a world, and the number says why")
    def _():
        # The honest answer to "or force a landing on the planet". You can
        # give the order anywhere, and on a real world it kills you — not by
        # a rule but because the hull arrives at six hundred metres a second
        # whatever it does. One tick of freefall at 10.371 m/s² is 622 m/s,
        # so the speed you *start* the last kilometre at barely matters.
        game, world, at_world = _rocky("force-landing")
        whole = sum(layer.hp for layer in game.ship.layers)
        hard = _drop(game, at_world, 20.0, ditch=True)
        assert hard.outcome == "ditched", hard.outcome
        assert hard.damage > whole * 5, (
            f"put her down on {world.name} for {hard.damage:,.0f} against a "
            f"{whole} hull — that is survivable, and it must not be")
        hard.landed = False
        out = berthing.commit(game, hard)
        assert out["lost"], "ditched a world and flew away with it"

        # And on something small it is a repair bill, which is the gradient
        # that makes ditching a decision about *where*.
        small, body, at_small = _soft_body()
        kept = sum(layer.hp for layer in small.ship.layers)
        soft = _drop(small, at_small, 20.0, ditch=True)
        soft.landed = False
        alive = berthing.commit(small, soft)
        assert not alive["lost"], (
            f"ditching a {body.kind} for {soft.damage:,.0f} of {kept} killed "
            "the ship, so there is nowhere it can be done")
        return (f"{world.name} ({landing.surface_g(at_world):.2f} m/s²): "
                f"{hard.damage:,.0f} off a {whole} hull, broken up · "
                f"{body.name} ({landing.surface_g(at_small):.3f}): "
                f"{soft.damage:,.0f}, and she flies again")

    @check("the quote and the bill are the same curve")
    def _():
        # The rule this project learned from the docking forecast: a cost
        # quoted before an act must come from the act's own arithmetic.
        game, rocky, target = _soft_body()[0::2][0], None, None
        game, rocky, target = _soft_body()
        conn = conn_sim.start(game, target)
        conn.pos = [target.radius_km * 1.0005, 0.0, 0.0]
        conn.vel = [-25.0, 0.0, 0.0]
        said = landing.ditch(conn)
        assert conn.ditching, said
        quoted, rate = landing.toll(conn), conn.speed
        assert f"{quoted:,.0f}" in said, (said, quoted)
        for _ in range(600):
            conn_sim.apply(conn, None, ticks=1)
            if conn.over:
                break
        assert conn.outcome == "ditched", conn.outcome
        again = outcome_sim.impact_at(conn, rate * landing.DITCH_SHARE)
        assert abs(again - quoted) < 1e-6, (again, quoted)
        # The hull gathers speed on the way down, so the bill is the larger —
        # but it is the same curve, which is the claim being made.
        assert conn.damage >= quoted, (conn.damage, quoted)
        return (f"quoted {quoted:,.0f} at {rate:,.0f} m/s, billed "
                f"{conn.damage:,.0f} at {conn.speed:,.0f} — one curve")

    @check("a forecast knows the captain chose the ground")
    def _():
        game, rocky, target = _soft_body()
        conn = conn_sim.start(game, target)
        conn.pos = [target.radius_km * 1.0005, 0.0, 0.0]
        conn.vel = [-20.0, 0.0, 0.0]
        landing.ditch(conn)
        twin = preview._copy(conn)
        assert twin.ditching, "the twin forgot the order and forecasts a crash"
        for _ in range(600):
            conn_sim.apply(twin, None, ticks=1)
            if twin.over:
                break
        assert twin.outcome == "ditched", (
            f"the twin forecast {twin.outcome!r} for a descent the ship chose")
        return f"twin forecasts {twin.outcome} at {twin.damage:,.0f} hull"

    @check("the chronicle knows a landing from a wreck")
    def _():
        game, body, target = _soft_body()
        conn = _drop(game, target, 0.05, high=1.0002)
        conn.landed = False
        out = berthing.commit(game, conn)
        assert out["ok"] and not out["lost"], out
        assert out["damage"] == 0.0, out
        assert berthing._tone(conn) == "good", (
            f"setting the ship down was logged as {berthing._tone(conn)!r}")
        wrecked, rocky, hard_at = _rocky("wreck")
        hard = _drop(wrecked, hard_at, 30.0, ditch=True)
        assert berthing._tone(hard) == "warn", (
            "putting the ship down on a world it cannot leave read as good "
            "news")
        return (f"down on {body.name}: good, nothing owed · ditched on "
                f"{rocky.name}: warn, {hard.damage:,.0f} off the hull")
