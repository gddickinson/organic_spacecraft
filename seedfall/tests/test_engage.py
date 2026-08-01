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
import math

from ..sim import consorts as consort_sim
from ..data.starclasses import mu_of
from ..sim import flight, traffic
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

    @check("burning toward a contact closes the range you would fight at")
    def _():
        # **The correction.** The first version ranged on `conn.pos` — how far
        # the hull had come from where it let go — because a hull sharing a
        # body with the ship sat at that body's exact position, 0 km off. That
        # was backwards for anything you flew *at*: closing on it increased
        # `conn.pos` and opened the fight further away. `sim/traffic` gives a
        # hull holding station a place of its own now, so there is a range.
        game, conn = _flying()
        hull = next(x for x in track.contacts(game) if x.kind == "hull")
        seen = {}
        for km in (0, 2000, 4000):
            conn.pos = [float(km), 0.0, 0.0]
            seen[km] = (engage.range_km(game, conn, hull),
                        engage.band_for(game, conn, hull))
        assert seen[2000][0] < seen[0][0], (
            f"burned 2,000 km toward it and the range went {seen[0][0]:,.0f} "
            f"-> {seen[2000][0]:,.0f} km")
        assert seen[4000][0] < seen[2000][0], "closing further did not close"
        assert seen[4000][1] < seen[0][1], (
            f"closed from {seen[0][0]:,.0f} to {seen[4000][0]:,.0f} km and "
            f"the fight still opens at band {seen[4000][1]}")
        assert seen[4000][1] == 0, (
            f"1,300 km off and opening at band {seen[4000][1]}")
        return " · ".join(f"{k:,}km flown → {v[0]:,.0f}km off, "
                          f"{combat_sim.BANDS[v[1]]}" for k, v in seen.items())

    @check("a hull holding station has a place of its own, and keeps it")
    def _():
        # Derived from the hull's id, never rolled: `traffic.in_system` is pure
        # in (system, day, sector state) and says why — the Kestrel you hailed
        # yesterday has to be the same Kestrel. Measured before this existed,
        # every hull at a body read 0 km from a ship at that body.
        # Measured from **its own body**, not from the ship: a hull holding
        # station at another world is half a billion kilometres off and that
        # is not what this is about. The first draft compared against the ship
        # and failed on exactly that.
        game, _conn = _flying()
        holding = [h for h in traffic.in_system(game)
                   if h.from_body == h.to_body]
        assert holding, "no hull in this system is holding station"
        offs = []
        for h in holding:
            body = game.system.bodies[h.from_body]
            at = flight.position(body, game.day, mu_of(game.system))
            x, y = traffic.position(game, h)
            offs.append(math.dist(at, (x, y)) * freeflight.KM_PER_AU)
        assert all(o > 100.0 for o in offs), (
            f"a hull is sitting exactly on its body: {offs}")
        assert all(o <= traffic.STATION_KM for o in offs), (
            f"a hull holds station {max(offs):,.0f} km out, past the "
            f"{traffic.STATION_KM:,.0f} km neighbourhood: {offs}")
        # And the same chronicle, built again, puts them in the same places.
        again = new_game("engage")
        was = {h.id: traffic.position(game, h) for h in traffic.in_system(game)}
        now = {h.id: traffic.position(again, h) for h in traffic.in_system(again)}
        assert was == now, "traffic moved when the chronicle was rebuilt"
        return (f"{len(holding)} holding station, "
                f"{min(offs):,.0f}..{max(offs):,.0f} km off, and stable")

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
