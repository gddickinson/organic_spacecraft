"""Being knocked off station, and whether the sector notices.

Stage one of the docking physics worked out that a hull striking a Fleet Hub
at thirty metres a second shoves it 1.7 m/s off station — and could only
*say* so, in a log line. The sector had nowhere to put it: an anchorage's
position is its body's, worked out from the calendar every time it is asked,
and a traffic hull's is interpolated between two bodies. Neither has a place
to hold "and then somebody hit it".

`sim/knock.py` is that place, and `track.at` — the one door for where
anything is — adds it. The claims:

- **A struck quay is off station everywhere**, because everything reads the
  same function: the plot, an approach, the readiness board's ranges, and
  every forecast.
- **Two ways of carrying it**, and the difference is whether anybody is
  aboard: a manned berth works back onto station, a derelict simply goes.
- **It is the shove that decides how far**, not a number chosen here — the
  drift leaves at exactly the speed `sim/impulse.py` gave it.
- **Ramming a hub does it**, flown rather than posited.
- **It survives a reload**, because a chronicle that forgets a knock on load
  has quietly repaired a station.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from ..sim import flight
from ..sim import impulse
from ..sim import knock as knock_sim
from ..sim import track as track_sim
from .harness import Suite

KM_PER_AU = knock_sim.KM_PER_AU


def _quay(game):
    return next(c for c in track_sim.contacts(game) if c.kind == "anchorage")


def _apart(game, contact, day: float) -> float:
    """How far off its nominal place this contact is, in km, on a day.

    Measured against the *same day* unstruck, because a body sweeps tens of
    millions of kilometres in a fortnight and comparing across days measures
    the orbit rather than the knock. The first version of this check did
    exactly that and reported a 648 km shove as 42 million.
    """
    held = dict(getattr(game, "knocks", {}) or {})
    hit = track_sim.at(game, contact, day)
    game.knocks = {}
    clean = track_sim.at(game, contact, day)
    game.knocks = held
    return math.hypot(hit[0] - clean[0], hit[1] - clean[1]) * KM_PER_AU


def run(suite: Suite) -> None:
    check = suite.check

    @check("a shoved quay is off station, and the whole game reads it there")
    def _():
        game = new_game("shoved")
        flight.travel_to(game, 0)
        quay = _quay(game)
        assert _apart(game, quay, game.day) == 0.0, "unstruck and already adrift"
        knock_sim.record(game, quay, 1.7)
        peak = _apart(game, quay, game.day + knock_sim.KEEPING_DAYS)
        assert peak > 100.0, f"a 1.7 m/s shove moved it {peak:.1f} km"
        # And it is the *same* displacement every consumer sees, because they
        # all go through `track.at`. Asked of two of them that compute their
        # own distances from it.
        from ..sim import berthing, readiness
        reach = berthing.reach_to(game, quay)
        game_day = game.day
        game.day = game_day + knock_sim.KEEPING_DAYS
        moved_reach = berthing.reach_to(game, quay)
        rows = {r["name"]: r["range_au"] for r in readiness.threats(game)}
        game.day = game_day
        assert abs(moved_reach - reach) > 50.0, (
            f"berthing reads it {moved_reach:,.0f} km off against "
            f"{reach:,.0f} — it is not seeing the knock")
        assert rows, "no traffic to read"
        return (f"1.7 m/s: {peak:,.0f} km off station at worst, and berthing "
                f"measures {abs(moved_reach - reach):,.0f} km of it")

    @check("a manned berth works back onto station and a derelict does not")
    def _():
        # The one real distinction, and it is about who is aboard rather than
        # about what kind of thing it is.
        manned = knock_sim.Knock("a", speed=2.0, bearing=0.0, day=0.0,
                                 keeping=True)
        adrift = knock_sim.Knock("b", speed=2.0, bearing=0.0, day=0.0,
                                 keeping=False)
        walk = {d: (knock_sim.km_after(manned, d), knock_sim.km_after(adrift, d))
                for d in (1, 12, 40, 120)}
        # Both leave at the speed they were shoved: the first day is the same.
        assert abs(walk[1][0] - walk[1][1]) / walk[1][1] < 0.1, walk[1]
        # The manned one peaks and comes home; the derelict never turns round.
        assert walk[12][0] > walk[40][0] > walk[120][0], walk
        assert walk[1][1] < walk[12][1] < walk[40][1] < walk[120][1], walk
        assert walk[120][0] < walk[120][1] / 50, walk[120]
        # **And the time constant itself, which the ordering above does not
        # pin.** Quadrupling `KEEPING_DAYS` from 12 to 48 left every one of
        # those comparisons true, because they only ask about the shape.
        # `x(t) = v·t·e^(−t/τ)` peaks at `t = τ` and `v·τ/e`, so the peak is
        # where the constant lives — measured by walking the curve rather than
        # read off the constant, and checked against written figures: a 2 m/s
        # shove peaks on **day 12** at **763 km**.
        peak_day, peak_km = max(
            ((d, knock_sim.km_after(manned, d)) for d in range(1, 200)),
            key=lambda row: row[1])
        assert 11 <= peak_day <= 13, (
            f"a manned berth is furthest off station on day {peak_day}")
        assert 740.0 <= peak_km <= 790.0, f"peak {peak_km:,.0f} km"
        # And the game decides which by asking who is aboard.
        from ..sim.track import Contact
        quay = Contact(id="q", name="", kind="anchorage", tint="", berth="quay")
        hold = Contact(id="h", name="", kind="anchorage", tint="",
                       berth="holding")
        hull = Contact(id="s", name="", kind="hull", tint="")
        assert knock_sim.keeps_station(quay)
        assert knock_sim.keeps_station(hull)
        assert not knock_sim.keeps_station(hold)
        return (f"manned: {walk[12][0]:,.0f} km at 12 days, "
                f"{walk[120][0]:,.0f} at 120 · derelict: "
                f"{walk[120][1]:,.0f} and still going")

    @check("how far it goes is the shove, not a number chosen here")
    def _():
        # The knock's first day is the shove itself, converted and nothing
        # else: `speed · 86,400 s`. Checked against written figures rather
        # than against `SECONDS_PER_DAY`, which is the constant it would be
        # pinning — 1 m/s is 86.4 km a day, and that is arithmetic, not a
        # tuning decision.
        one = knock_sim.Knock("x", speed=1.0, bearing=0.0, day=0.0,
                              keeping=False)
        assert abs(knock_sim.km_after(one, 1.0) - 86.4) < 0.01, \
            knock_sim.km_after(one, 1.0)
        assert abs(knock_sim.km_after(one, 10.0) - 864.0) < 0.1
        # Twice the shove, twice the distance — it is linear in the impulse.
        two = knock_sim.Knock("y", speed=2.0, bearing=0.0, day=0.0,
                              keeping=False)
        assert abs(knock_sim.km_after(two, 5.0)
                   - 2 * knock_sim.km_after(one, 5.0)) < 1e-6
        # And a shove too small to matter is not carried at all.
        game = new_game("tiny")
        flight.travel_to(game, 0)
        assert knock_sim.record(game, _quay(game), 1e-9) is None
        assert not game.knocks
        return "1 m/s → 86.4 km a day, linear in the shove, and nothing under 0.1 km is kept"

    @check("ramming a hub puts it off station, flown")
    def _():
        game = new_game("ram-knock")
        flight.travel_to(game, 0)
        quay = _quay(game)
        conn, why = berth_sim.begin(game, quay)
        assert conn is not None, why
        conn.vel = [0.0, 30.0, 0.0]
        for _ in range(400):
            conn_sim.apply(conn, None)
            if conn.over:
                break
        assert conn.outcome == "collision", conn.outcome
        berth_sim.commit(game, conn)
        hits = knock_sim.standing(game)
        assert len(hits) == 1, hits
        assert hits[0]["id"] == quay.id, hits
        assert abs(hits[0]["speed"] - conn.struck_dv) < 1e-9, (
            "the knock and the collision disagree about the shove")
        assert hits[0]["damage"] == conn.struck_damage
        peak = _apart(game, quay, game.day + knock_sim.KEEPING_DAYS)
        said = " ".join(line for _d, line, _k in game.log[-3:])
        assert "adrift" in said, said
        return (f"30 m/s into a hub: shoved {hits[0]['speed']:.2f} m/s, "
                f"{peak:,.0f} km off station at worst")

    @check("a knock survives a reload, and settles when it is over")
    def _():
        # A chronicle that forgets a knock on load has quietly repaired a
        # station. `Knock` is registered with the saver for this.
        import json

        from ..core import save as save_mod
        game = new_game("saved-knock")
        flight.travel_to(game, 0)
        quay = _quay(game)
        knock_sim.record(game, quay, 3.0)
        # Through the encoder the saver actually uses — `encode`/`decode`, not
        # a `dumps`/`loads` pair I assumed and which do not exist. The first
        # version of this guessed the API, found `dumps` missing, and *skipped
        # the whole reload half without failing*: a check that quietly does
        # nothing is worse than no check, because it reads as coverage.
        blob = json.dumps(save_mod.encode(game.knocks))
        back = save_mod.decode(json.loads(blob))
        assert back, "the knock did not come back"
        kept = list(back.values())[0]
        assert isinstance(kept, knock_sim.Knock), type(kept)
        assert abs(kept.speed - 3.0) < 1e-9, kept
        mine = list(game.knocks.values())[0]
        for ahead in (1, 12, 60):
            assert abs(knock_sim.km_after(kept, game.day + ahead)
                       - knock_sim.km_after(mine, game.day + ahead)) < 1e-6, (
                "the reloaded knock is on a different curve")
        # And it is dropped once it is home, so the store does not grow.
        # Asked of `km_after` rather than at a day picked by hand — the first
        # version guessed 144 days, where a 3 m/s shove is still 0.23 km out.
        #
        # **Past the peak first.** At the instant of the knock the thing has
        # not drifted anywhere yet, so "still adrift" is false before it has
        # been anywhere: the loop below exited immediately on day zero and the
        # sweep correctly refused to drop a knock that had not happened yet.
        game.day = mine.day + knock_sim.KEEPING_DAYS
        assert knock_sim.km_after(mine, game.day) > knock_sim.SETTLED_KM
        # **Bounded, because an unbounded loop here is a check that hangs the
        # suite.** It did: the mutation that removes the recovery leaves the
        # drift growing for ever, and this ran until the harness was killed —
        # which is worse than a failure, because a failure says what is wrong.
        # The bound is the claim: a manned berth is home inside a year.
        steps = 0
        while knock_sim.km_after(mine, game.day) >= knock_sim.SETTLED_KM:
            game.day += knock_sim.KEEPING_DAYS
            steps += 1
            assert steps <= 30, (
                f"still {knock_sim.km_after(mine, game.day):,.1f} km out after "
                f"{game.day - mine.day:.0f} days — this berth is not working "
                "back onto station at all")
        dropped = knock_sim.sweep(game)
        assert dropped == 1 and not game.knocks, (game.day, dropped, game.knocks)
        # A derelict's drift is never swept: it is still going.
        game2 = new_game("derelict-knock")
        hit = knock_sim.Knock("d", speed=2.0, bearing=0.0, day=0.0,
                              keeping=False)
        game2.knocks = {"d": hit}
        game2.day = 4000.0
        assert knock_sim.sweep(game2) == 0 and game2.knocks
        return ("a knock reloads with its speed and its curve; a settled one "
                "is swept and a derelict's never is")
