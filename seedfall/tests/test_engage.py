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

    @check("a hull's flag survives the trip from traffic to the trigger")
    def _():
        # **It did not.** `Contact.faction` is set for a quay and was never
        # set for a hull, so `open_fire` read `None` and fought an *unaligned*
        # enemy whoever the ship belonged to. Measured across twelve systems,
        # every single traffic hull carries a flag — 85% Charter — so the
        # field was wrong for all of them, not for an edge case.
        from ..sim import traffic as traffic_sim
        game = new_game("price")
        hulls = traffic_sim.in_system(game)
        assert hulls, "no traffic to check"
        flagged = [h for h in hulls if h.faction]
        assert flagged, "no hull here flies a flag; the check proves nothing"
        contacts = {c.hull_id: c for c in track.contacts(game)
                    if c.kind == "hull"}
        for hull in flagged:
            seen = contacts.get(hull.id)
            assert seen is not None and seen.faction == hull.faction, (
                f"{hull.name} flies {hull.faction!r} and the contact says "
                f"{getattr(seen, 'faction', None)!r}")
        # And it reaches the fight, which is the whole reason it matters.
        conn, why = freeflight.begin(game)
        assert conn is not None, why
        target = contacts[flagged[0].id]
        battle, why = engage.open_fire(game, conn, target, RNG("flag"))
        assert battle is not None, why
        assert battle.enemy_faction == flagged[0].faction, (
            f"engaged a {flagged[0].faction} hull and fought a "
            f"{battle.enemy_faction} one")
        return (f"{len(flagged)} of {len(hulls)} hulls flagged; "
                f"{flagged[0].name} fought as {battle.enemy_faction}")

    @check("killing a power's hull is felt by everyone fond of it")
    def _():
        # `sim/aftermath` already dropped the victim's standing and pleased
        # its *rivals* — `_pleased` walks `allegiance.offended_by`. Nothing
        # walked `defenders_of`, so the people who like it did not mind, and a
        # captain could work through one power's shipping and stay welcome.
        from ..sim import aftermath as aftermath_sim
        from ..sim import diplomacy as dip
        from ..sim import allegiance as allegiance_sim

        seen = {}
        for warm in (False, True):
            game = new_game("price")
            if warm:
                dip.ensure(game).relations["charter|sanhedrin"] = 60.0
            conn, _why = freeflight.begin(game)
            hull = next(c for c in track.contacts(game)
                        if c.kind == "hull" and c.faction)
            battle, why = engage.open_fire(game, conn, hull, RNG("k"))
            assert battle is not None, why
            fid = battle.enemy_faction
            defenders = allegiance_sim.defenders_of(game, fid)
            was = dict(game.rep)
            battle.result = "destroyed"
            said = aftermath_sim.resolve(game, battle, RNG("a"))
            moved = dict(said["standing"])
            assert moved.get(fid) == -aftermath_sim.KILL_COST, moved
            seen[warm] = (defenders, moved, dict(game.rep), was)

        cold_def, cold_moved, _r, _w = seen[False]
        warm_def, warm_moved, warm_rep, warm_was = seen[True]
        assert not cold_def, (
            f"the fixture has friends on day one: {cold_def} — then the two "
            f"halves are not a comparison")
        assert set(cold_moved) == {"charter"}, (
            f"nobody is fond of anybody yet and {cold_moved} moved")
        # Warm: the friend is charged, and the rep really moved, not just the
        # report. That distinction is the one this project keeps being bitten
        # by.
        friend = warm_def[0][0]
        assert friend in warm_moved, (
            f"{friend} is devoted to the victim at {warm_def[0][1]:.2f} and "
            f"only {sorted(warm_moved)} paid")
        assert warm_moved[friend] < 0, warm_moved
        assert warm_rep[friend] < warm_was.get(friend, 0.0), (
            f"{friend} was reported as charged and its standing did not move: "
            f"{warm_was.get(friend)} -> {warm_rep[friend]}")
        return (f"day one: {sorted(cold_moved)} · warm: "
                + ", ".join(f"{k} {v:+.1f}" for k, v in sorted(warm_moved.items())))

    @check("the bill is quoted before the trigger, not after it")
    def _():
        # A cost the pilot only discovers afterwards is the same defect as a
        # greyed-out button. `engage.price` asks the two doors `aftermath`
        # spends through, at the same weight, so the board cannot promise a
        # bill the fight will not send.
        from ..sim import aftermath as aftermath_sim
        from ..sim import diplomacy as dip
        game = new_game("price")
        dip.ensure(game).relations["charter|sanhedrin"] = 60.0
        conn, _why = freeflight.begin(game)
        hull = next(c for c in track.contacts(game)
                    if c.kind == "hull" and c.faction)

        quoted = dict(engage.price(game, hull))
        assert quoted, "nothing was quoted for a flagged hull"
        assert quoted[hull.faction] == -aftermath_sim.KILL_COST, quoted
        assert len(quoted) > 1, (
            f"only the victim was quoted: {quoted} — the friends are the part "
            f"that was missing")

        # Fight it and compare the bill with what was actually taken.
        battle, why = engage.open_fire(game, conn, hull, RNG("q"))
        assert battle is not None, why
        battle.result = "destroyed"
        said = aftermath_sim.resolve(game, battle, RNG("a"))
        spent = dict(said["standing"])
        assert spent == quoted, (
            f"quoted {quoted} and spent {spent}")

        # A world has no flag and so no bill.
        body = next(c for c in track.contacts(game) if c.kind == "body")
        assert engage.price(game, body) == []
        assert "costs" in engage.note(game, conn, hull), (
            engage.note(game, conn, hull))
        return "quoted " + ", ".join(f"{k} {v:+.1f}"
                                     for k, v in sorted(quoted.items())) \
               + " and spent exactly that"

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
        # **Toward it, not along `+x`.** This used to fly the hull down the
        # x axis and assume that closed the range, which held only because
        # every hull holding station sat at a fixed offset in one shared
        # plane. Hulls keep their own circuits at their own tilts now, so
        # "toward" is a direction that has to be asked for — which is what
        # the claim was always about.
        start = list(conn.pos)
        aim = freeflight.toward(game, conn, hull)
        span = math.dist(aim, (0.0, 0.0, 0.0))
        unit = [c / span for c in aim]
        seen = {}
        for km in (0, 2000, 4000):
            conn.pos = [s + u * km for s, u in zip(start, unit)]
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
            offs.append(math.dist(at, traffic.position(game, h))
                        * freeflight.KM_PER_AU)
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
        # **Close the range, rather than assuming it.** This used to plant
        # the hull at a magic `[100, 0, 0]`, which happened to be inside gun
        # reach only because the ship sat at its body's exact centre. Now
        # that a hull in orbit has a place of its own
        # (`flight.ship_orbit_offset`) that assumption reads 12,758 km and
        # the guns refuse — correctly. The claim is about the escort coming
        # along, so the fixture flies to the mark the way a captain would.
        from ..sim import freeflight as free_sim
        toward = free_sim.toward(game, conn, hull)
        conn.pos = [conn.pos[i] + toward[i] for i in range(3)]
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
        # **Close the range, rather than assuming it.** This used to plant
        # the hull at a magic `[100, 0, 0]`, which happened to be inside gun
        # reach only because the ship sat at its body's exact centre. Now
        # that a hull in orbit has a place of its own
        # (`flight.ship_orbit_offset`) that assumption reads 12,758 km and
        # the guns refuse — correctly. The claim is about the escort coming
        # along, so the fixture flies to the mark the way a captain would.
        from ..sim import freeflight as free_sim
        toward = free_sim.toward(game, conn, hull)
        conn.pos = [conn.pos[i] + toward[i] for i in range(3)]
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
