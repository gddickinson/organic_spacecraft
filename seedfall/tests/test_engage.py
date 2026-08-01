"""Opening fire from the pilot's seat, and the range the flying earned.

Everything else the request asked for already existed and was measured before a
line was written: `sim/freeflight` takes the conn with no target and no
clearance, it does **not** run on the game clock (200 conn ticks advanced
`game.day` by 0; the hours are charged once, on `berthing.commit`), nothing
ends a free flight but the pilot, and `hand_over` turns one into an approach
carrying the way already on. Leaving a dock and leaving orbit are not stored
states to clear — `anchorage.docked_at` and `where_am_i` are derived from
position, so flying away *is* leaving.

The gap was the guns. Measured on `sim/conn.py`: the word "weapon" appeared **0**
times and "hostile" **0**. There was no door from live flight into a fight.

`sim/engage` is that door and resolves nothing itself. What it decides is
whether a pilot may fire and **at what range the fight starts**, which is the
one thing the flying can earn.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import combat as combat_sim
from ..sim import consorts as consort_sim
from ..sim import engage, freeflight, track
from ..sim import ship as ship_sim
from .harness import Suite


def _flying(seed: str = "engage"):
    game = new_game(seed)
    conn, why = freeflight.begin(game)
    assert conn is not None, why
    return game, conn


def run(suite: Suite) -> None:
    check = suite.check

    @check("the range a fight opens at is the range the pilot flew to")
    def _():
        # The whole point of the seam. A captain still alongside fights at
        # contact range; one who has drifted to the edge of what the
        # free-flight screens call far opens at extreme, where `sim/firing`
        # will tell them most of their mounts cannot reach.
        game, conn = _flying()
        seen = {}
        for km in (0, 3000, 5000, 7000, 9000):
            conn.pos = [float(km), 0.0, 0.0]
            seen[km] = engage.band_for(conn)
        assert seen[0] == 0, f"alongside and opening at band {seen[0]}"
        assert seen[9000] == len(combat_sim.BANDS) - 1, (
            f"9,000 km out and opening at band {seen[9000]}")
        rising = sorted(seen.values())
        assert rising == list(seen.values()), (
            f"flying further did not open the fight further off: {seen}")
        assert len(set(seen.values())) >= 4, (
            f"five ranges and only {len(set(seen.values()))} bands: {seen}")
        # And it saturates rather than running off the end of the table.
        conn.pos = [10.0 ** 6, 0.0, 0.0]
        assert engage.band_for(conn) == len(combat_sim.BANDS) - 1
        return " · ".join(f"{k:,}km→{combat_sim.BANDS[v]}"
                          for k, v in seen.items())

    @check("the same hull, engaged from close and from far, is a different fight")
    def _():
        # The claim the task set: fly differently and the outcome differs.
        # Same seed, same hull, same dice — only the flying changes.
        game, conn = _flying()
        hull = next(x for x in track.contacts(game) if x.kind == "hull")
        conn.pos = [200.0, 0.0, 0.0]
        near, why = engage.open_fire(game, conn, hull, RNG("same"))
        assert near is not None, why
        game2, conn2 = _flying()
        hull2 = next(x for x in track.contacts(game2) if x.kind == "hull")
        conn2.pos = [9000.0, 0.0, 0.0]
        far, why = engage.open_fire(game2, conn2, hull2, RNG("same"))
        assert far is not None, why
        assert near.band < far.band, (
            f"closed to 200 km and opened at band {near.band}; drifted to "
            f"9,000 and opened at band {far.band}")
        assert near.range_units < far.range_units, (
            f"the two fights start {near.range_units} and {far.range_units} "
            "units apart, which is not a difference the pilot earned")
        return (f"200 km → {combat_sim.BANDS[near.band]} at "
                f"{near.range_units:.0f} units; 9,000 km → "
                f"{combat_sim.BANDS[far.band]} at {far.range_units:.0f}")

    @check("a refusal says which kind of no it is")
    def _():
        # A world is not a thing to shoot at, an approach is not a free
        # flight, and each refusal carries its own sentence — the discipline
        # `sim/clearance` already holds for a berth.
        game, conn = _flying()
        said = {}
        body = next(x for x in track.contacts(game) if x.kind == "body")
        said["a world"] = engage.may_engage(game, conn, body)
        star = next((x for x in track.contacts(game) if x.kind == "star"), None)
        if star is not None:
            said["a star"] = engage.may_engage(game, conn, star)
        quay = next((x for x in track.contacts(game)
                     if x.kind == "anchorage"), None)
        if quay is not None:
            said["a quay"] = engage.may_engage(game, conn, quay)
        for why, (ok, line) in said.items():
            assert not ok, f"{why} was cleared to be fired on"
            assert len(line) > 20, (why, line)
        # **Not "the messages differ".** Each carries the contact's name, so
        # three identical refusals read as three different strings — measured:
        # deleting the world clause left every check here green because
        # "Loam Fall I is not a hull" and "Fleet Hub is not a hull" are not
        # equal. Assert the *kind* of refusal instead.
        assert "world" in said["a world"][1], said["a world"][1]
        if "a star" in said:
            assert "world" in said["a star"][1], said["a star"][1]
        if "a quay" in said:
            assert "not a hull" in said["a quay"][1], said["a quay"][1]
        # And a hull is not refused.
        hull = next(x for x in track.contacts(game) if x.kind == "hull")
        ok, line = engage.may_engage(game, conn, hull)
        assert ok, f"a hull could not be engaged at all: {line}"
        return " · ".join(f"{w}: {l.split('.')[0][:34]}"
                          for w, (_o, l) in said.items())

    @check("the guns answer to the conn, and only while it is free")
    def _():
        # An approach is the computer flying a berth. The pilot does not open
        # fire in the middle of one without breaking off first, and the
        # refusal says so.
        game, conn = _flying()
        hull = next(x for x in track.contacts(game) if x.kind == "hull")
        assert engage.may_engage(game, conn, hull)[0]
        conn.target = next(x for x in track.contacts(game)
                           if x.kind == "anchorage")
        assert not freeflight.is_free(conn), "the fixture did not stop being free"
        ok, line = engage.may_engage(game, conn, hull)
        assert not ok, "opened fire in the middle of an approach"
        assert "break off" in line.lower(), line
        # And with no conn at all there is nothing to fire from.
        assert not engage.may_engage(game, None, hull)[0]
        return f"refused mid-approach: “{line}”"

    @check("a hull that sails with the flag sails into a conn fight too")
    def _():
        # **This was missing from the first version and the flight found it.**
        # `ui/battle_view.begin` passes `consorts.escorts_of` when an encounter
        # starts a fight; `open_fire` did not. Measured: a captain sailing with
        # one consort opened fire from the conn and fought alone, while the
        # same captain jumped by the same enemy fought two-to-one. Who picked
        # the fight is not a reason to leave your escort behind.
        game, conn = _flying("escort")
        extra = ship_sim.make_ship("navis", name="Consort")
        extra.escort = True
        game.fleet.append(extra)
        assert [s.name for s in consort_sim.escorts_of(game)] == ["Consort"]
        hull = next(x for x in track.contacts(game) if x.kind == "hull")
        conn.pos = [100.0, 0.0, 0.0]
        battle, why = engage.open_fire(game, conn, hull, RNG("escort"))
        assert battle is not None, why
        aboard = [c.name for c in getattr(battle, "consorts", [])]
        assert aboard == ["Consort"], (
            f"sailing with {[s.name for s in consort_sim.escorts_of(game)]} "
            f"and fought with {aboard}")
        return f"opened fire in company: {', '.join(aboard)}"

    @check("the enemy comes from the one door that builds one")
    def _():
        # `encounters.make_enemy` is what a hull of a given flag is carrying.
        # A second answer here would let a conn engagement and an encounter
        # disagree about the same ship.
        game, conn = _flying()
        hull = next(x for x in track.contacts(game) if x.kind == "hull")
        conn.pos = [100.0, 0.0, 0.0]
        battle, why = engage.open_fire(game, conn, hull, RNG("mk"))
        assert battle is not None, why
        assert battle.enemy_name == hull.name, (
            f"engaged {hull.name!r} and fought {battle.enemy_name!r}")
        assert battle.enemy.ship.layers, "the enemy has no hull to shoot at"
        assert battle.enemy_faction == (getattr(hull, "faction", None)
                                        or "unaligned")
        assert battle.game is game, "the fight is not attached to the chronicle"
        return (f"{battle.enemy_name}: {len(battle.enemy.ship.layers)} layers, "
                f"flying {battle.enemy_faction}")
