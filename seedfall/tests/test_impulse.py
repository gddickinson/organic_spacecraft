"""Momentum: what two things do to each other, and not just to the player.

A collision used to be one-sided. `outcome.impact_damage(speed)` took a number
off the player's hull and that was the entire event — the quay a captain hit
at forty metres a second was neither moved nor marked, and could be used as a
backstop. Nothing in the game had a mass, so nothing could be shoved by
anything, and a hull moored to a station could open its main drive without
either of them going anywhere.

`sim/impulse.py` is the physics. Contact is perfectly inelastic — hulls do not
bounce off quays — so two masses meeting at a closing speed share a velocity,
and everything that was missing falls out of that: how hard the striker is
stopped, how hard the struck one is shoved, and the reduced-mass energy that
has to be absorbed by both.

The claims:

- **Momentum is conserved.** Not asserted from the formula that produced it —
  measured as `m₁v` before against `(m₁+m₂)V` after.
- **The change costs the player nothing they were not already charged.** The
  written consequences — a scrape at 8 m/s, half the hull at 20, the end of
  the chronicle at 45 — are calibrated against the old one-sided formula, and
  still hold.
- **The mass ratio decides who suffers**, which the old formula could not
  express at all.
- **Thrust against a mooring moves the pair**, and slower than the ship alone.
- **It reaches the chronicle**: ram a hub in a real approach and the log says
  what the hub took.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from ..sim import flight
from ..sim import impulse
from ..sim import track as track_sim
from .harness import Suite

#: The reference pair, and the hull the game actually ships with. A NAVIS is
#: 24,000 t and the Fleet Hub a captain starts beside is 400,000 t.
NAVIS_T = 24_000.0
HUB_T = impulse.BERTH_MASS_T["hub"]


def run(suite: Suite) -> None:
    check = suite.check

    @check("momentum is conserved, measured rather than asserted")
    def _():
        # From the two figures the function returns, not from the expression
        # inside it: total momentum before against total momentum after.
        worst = 0.0
        pairs = 0
        for m_a in (900.0, 24_000.0, 400_000.0):
            for m_b in (900.0, 24_000.0, 400_000.0, impulse.WORLD_MASS_T):
                for speed in (0.5, 4.0, 20.0, 45.0):
                    got = impulse.collide(m_a, m_b, speed)
                    before = m_a * speed
                    after = (m_a * (speed + got["dv_a"])
                             + m_b * got["dv_b"])
                    worst = max(worst, abs(after - before) / max(before, 1e-9))
                    pairs += 1
                    # And the struck one never ends up faster than the striker
                    # was, which is what an inelastic contact means.
                    assert 0.0 <= got["dv_b"] <= speed + 1e-9, got
        assert worst < 1e-9, f"momentum drifts by {worst:.2%}"
        assert pairs >= 40, pairs
        return (f"{pairs} pairs across four decades of mass: momentum holds "
                f"to {worst:.1e}")

    @check("the player is charged exactly what they always were")
    def _():
        # The calibration, against **written figures** and not against
        # `HARM_PER_MJ_PER_T`: the constant is derived from these, so reading
        # it here would be the definition rearranged. `outcome.impact_damage`
        # charged `(speed / 4)² · 6` — 6, 24, 150 and 759.4 points at the four
        # speeds the game's own prose describes.
        want = {4.0: 6.0, 8.0: 24.0, 20.0: 150.0, 45.0: 759.4}
        got = {}
        for speed, expect in want.items():
            got[speed] = impulse.collide(NAVIS_T, HUB_T, speed)["harm_a"]
            assert abs(got[speed] - expect) <= 0.1, (
                f"a NAVIS into a hub at {speed} m/s now costs {got[speed]} "
                f"and used to cost {expect}")
        # And the hub is no longer untouched by any of it.
        struck = impulse.collide(NAVIS_T, HUB_T, 45.0)
        assert struck["harm_b"] > 0 and struck["dv_b"] > 0, struck
        return (" · ".join(f"{s:.0f} m/s → {v}" for s, v in got.items())
                + f"; the hub takes {struck['harm_b']:.0f} and "
                f"{struck['dv_b']:.2f} m/s at 45")

    @check("the mass ratio decides who suffers")
    def _():
        # The thing a one-sided formula could not say. Same speed, same pair,
        # swapped roles: the light hull is wrecked either way.
        courier, navis = 900.0, NAVIS_T
        hit = impulse.collide(navis, courier, 20.0)
        rammed = impulse.collide(courier, navis, 20.0)
        assert hit["harm_b"] > hit["harm_a"] * 10, (
            f"a NAVIS into a courier: NAVIS {hit['harm_a']}, courier "
            f"{hit['harm_b']} — the light hull is not paying for it")
        assert abs(rammed["harm_a"] - hit["harm_b"]) < 0.5, (
            "the same collision gives the courier a different answer "
            "depending on which of them is called the striker")
        # And the shove: the courier is knocked nearly to the striker's speed,
        # the hub barely moves.
        assert hit["dv_b"] > 19.0, hit["dv_b"]
        assert impulse.collide(navis, HUB_T, 20.0)["dv_b"] < 2.0
        # A world is not shoved by anything a captain can fly into it.
        world = impulse.collide(navis, impulse.WORLD_MASS_T, 45.0)
        assert world["dv_b"] < 1e-6, world["dv_b"]
        return (f"NAVIS into a courier at 20: {hit['harm_a']:.0f} against "
                f"{hit['harm_b']:.0f}, and the courier knocked to "
                f"{hit['dv_b']:.1f} m/s")

    @check("a burn against a mooring moves both, and slowly")
    def _():
        alone = 12.0
        pair = impulse.push(NAVIS_T, HUB_T, alone)
        assert 0.0 < pair["pair_dv"] < alone, pair
        assert abs(pair["pair_dv"] - alone * NAVIS_T / (NAVIS_T + HUB_T)) < 1e-9
        # Against something light it is nearly the whole burn; against a gate
        # it is nearly none of it.
        light = impulse.push(NAVIS_T, 900.0, alone)
        heavy = impulse.push(NAVIS_T, impulse.BERTH_MASS_T["gate"], alone)
        assert light["pair_dv"] > pair["pair_dv"] > heavy["pair_dv"], (
            light["pair_dv"], pair["pair_dv"], heavy["pair_dv"])
        assert heavy["pair_dv"] < alone * 0.02, heavy["pair_dv"]
        return (f"12 m/s of burn moves the pair {pair['pair_dv']:.2f} m/s on a "
                f"hub, {light['pair_dv']:.1f} on a courier and "
                f"{heavy['pair_dv']:.2f} on a gate")

    @check("everything in the sky has a mass, and a star is not a pier")
    def _():
        # `mass_of` fell past every branch to the berth default, so a star
        # weighed 60,000 t — the mass of a quay. Nothing can fly into one, so
        # it never mattered; a fallback that quietly weighs a star the same as
        # a pier is what matters the first time something does.
        game = new_game("weights")
        flight.travel_to(game, 0)
        seen = {}
        for contact in track_sim.contacts(game):
            seen[contact.kind] = impulse.mass_of(game, contact)
        for kind in ("star", "body"):
            assert seen.get(kind, 0) >= impulse.WORLD_MASS_T, (
                f"a {kind} weighs {seen.get(kind)} t")
        assert seen["anchorage"] in impulse.BERTH_MASS_T.values(), seen
        assert 100.0 < seen["hull"] < 1e6, seen["hull"]
        assert impulse.ship_mass(game) == NAVIS_T, impulse.ship_mass(game)
        return " · ".join(f"{k} {v:,.0f} t" for k, v in sorted(seen.items()))

    @check("ramming a hub reaches the chronicle, for both of them")
    def _():
        game = new_game("ram")
        flight.travel_to(game, 0)
        quay = next(c for c in track_sim.contacts(game)
                    if c.kind == "anchorage")
        conn, why = berth_sim.begin(game, quay)
        assert conn is not None, why
        assert conn.target_mass_t == HUB_T, conn.target_mass_t
        conn.vel = [0.0, 30.0, 0.0]           # driven in on purpose
        for _ in range(400):
            conn_sim.apply(conn, None)
            if conn.over:
                break
        assert conn.outcome == "collision", conn.outcome
        assert conn.struck_damage > 0 and conn.struck_dv > 0, (
            conn.struck_damage, conn.struck_dv)
        berth_sim.commit(game, conn)
        said = " ".join(line for _day, line, _kind in game.log[-3:])
        assert quay.name in said and "shoved" in said, said
        return (f"30 m/s into a hub: {conn.damage:,.0f} off the hull, the hub "
                f"{conn.struck_damage:,.0f} and {conn.struck_dv:.2f} m/s off "
                "station, both in the log")
